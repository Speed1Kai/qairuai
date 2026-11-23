"""Import Blender cars and swap the old blockout mesh in the existing scenes."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import shutil
import runpy
import time

import unreal
from Industrial_Common import A, M, V, components, compile_bp, save

ROOT='/Game/Environment/Vehicles'
OLD='/Game/Surface/Meshes/SM_WreckedSedan'
MAPS=('/Game/Surface/Lvl_CampusConnected','/Game/Surface/Lvl_SurfaceArrival')
MAIN='/Game/Lvl_LabTutorial'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.EditorLoadingAndSavingUtils
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
project=Path(unreal.Paths.project_dir()).resolve()
source=project/'SourceAssets/Vehicles'
saved=project/'Saved'
palette={
    'Body':(.105,.163,.172,.57,.30),'Rubber':(.016,.019,.019,.91,0.),
    'Steel':(.23,.24,.23,.53,.67),'Trim':(.03,.039,.04,.63,.16),
    'Glass':(.035,.074,.087,.25,.29),'Tail':(.33,.025,.017,.35,.18),
    'Headlamp':(.58,.65,.62,.28,.24),'Oxide':(.19,.076,.039,.84,.12),
}


def material(key, wagon):
    name='M_FP_'+('WagonPaint' if wagon and key=='Body' else key)
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return A.load_asset(path)
    m=tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    r,g,b,rough,metal=(.32,.295,.22,.59,.32) if wagon and key=='Body' else palette[key]
    base=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-360,0)
    base.set_editor_property('constant',unreal.LinearColor(r,g,b,1))
    assert M.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop in ((rough,unreal.MaterialProperty.MP_ROUGHNESS),(metal,unreal.MaterialProperty.MP_METALLIC)):
        n=M.create_material_expression(m,unreal.MaterialExpressionConstant,-350,160)
        n.set_editor_property('r',value)
        assert M.connect_material_property(n,'',prop)
    if key=='Glass':
        m.set_editor_property('two_sided',True)
    M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(m)
    save(m)
    return m


def car(name, wagon):
    path=ROOT+'/'+name
    if not A.does_asset_exist(path):
        ui=unreal.FbxImportUI()
        ui.set_editor_property('automated_import_should_detect_type',False)
        ui.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
        ui.set_editor_property('import_materials',False)
        ui.set_editor_property('import_textures',False)
        ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
        ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        task=unreal.AssetImportTask()
        for k,v in dict(filename=str(source/(name+'.fbx')),destination_path=ROOT,destination_name=name,
                        automated=True,save=False,options=ui).items():
            task.set_editor_property(k,v)
        tools.import_asset_tasks([task])
    mesh=A.load_asset(path)
    assert isinstance(mesh,unreal.StaticMesh), path
    keys=[]
    for i,slot in enumerate(mesh.static_materials):
        raw=str(slot.material_slot_name)
        key=next((k for k in palette if raw.lower().startswith(k.lower())),None)
        assert key,(raw,path)
        keys.append(key)
        mesh.set_material(i,material(key,wagon))
    assert len(set(keys))>=7,keys
    box=mesh.get_bounding_box()
    size=box.max-box.min
    assert 430<size.x<520 and 170<size.y<235 and 118<size.z<155,str(size)
    sm=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sm.remove_collisions(mesh)
    assert sm.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)>=0
    save(mesh)
    return mesh


def fit(old,new,t):
    a,b=old.get_bounding_box(),new.get_bounding_box()
    d,e=a.max-a.min,b.max-b.min
    sx,sy,sz=d.x/e.x,d.y/e.y,d.z/e.z
    c0,c1=(a.min+a.max)*.5,(b.min+b.max)*.5
    s=t.scale3d
    offset=V(((c0.x-c1.x*sx)*s.x,(c0.y-c1.y*sy)*s.y,(a.min.z-b.min.z*sz)*s.z))
    rotation=t.rotation.rotator()
    rigid=unreal.Transform(rotation=rotation)
    return unreal.Transform(location=t.translation+unreal.MathLibrary.transform_direction(rigid,offset),
                            rotation=rotation,scale=V((s.x*sx,s.y*sy,s.z*sz)))


def swap(c,old,new):
    if c.static_mesh!=old:
        return 0
    c.modify()
    if isinstance(c,unreal.InstancedStaticMeshComponent):
        count=c.get_instance_count()
        transformed=[fit(old,new,c.get_instance_transform(i,False)) for i in range(count)]
        c.set_static_mesh(new)
        for i,t in enumerate(transformed):
            c.update_instance_transform(i,t,False,True,True)
        return count
    t=unreal.Transform(location=c.get_editor_property('relative_location'),
                       rotation=c.get_editor_property('relative_rotation'),
                       scale=c.get_editor_property('relative_scale3d'))
    fitted=fit(old,new,t)
    c.set_static_mesh(new)
    c.set_editor_property('relative_location',fitted.translation)
    c.set_editor_property('relative_rotation',fitted.rotation.rotator())
    c.set_editor_property('relative_scale3d',fitted.scale3d)
    return 1


def main():
    assert not levels.get_dirty_map_packages()
    backup=saved/'Backups/BlenderVehicles'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    lab=project/'Content/Lvl_LabTutorial.umap'
    digest=hashlib.sha256(lab.read_bytes()).hexdigest()
    A.make_directory(ROOT)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    old=A.load_asset(OLD)
    sedan=car('SM_FP_AbandonedSedan',False)
    wagon=car('SM_FP_SecurityWagon',True)
    paths={str(p) for p in A.find_package_referencers_for_asset(OLD,False)}
    paths.update(('/Game/Surface/BP_SurfaceEnvironment','/Game/Surface/RuinedCampus/BP_RuinedUrbanCampus',
                  '/Game/Surface/RiverForest/BP_RiverForest'))
    report={}
    for path in sorted(paths):
        if not path.startswith('/Game/Surface/') or '/BP_' not in path:
            continue
        bp=A.load_asset(path)
        if not isinstance(bp,unreal.Blueprint):
            continue
        matches={n:c for _,c,n in components(bp) if isinstance(c,unreal.StaticMeshComponent) and c.static_mesh==old}
        if matches:
            shutil.copy2(project/'Content'/(path.removeprefix('/Game/')+'.uasset'),backup)
            report[path]=sum(swap(c,old,wagon if 'Parking' in name else sedan) for name,c in matches.items())
            compile_bp(bp)
            save(bp)
    for path in MAPS:
        shutil.copy2(project/'Content'/(path.removeprefix('/Game/')+'.umap'),backup)
        world=levels.load_map(path)
        assert world,path
        for a in actors.get_all_level_actors():
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                if c.static_mesh==old:
                    a.modify()
                    swap(c,old,wagon if 'Parking' in c.get_name() else sedan)
        world.modify()
        assert levels.save_map(world,path)
        del world
        assert levels.load_map(path)
        scene=[c for a in actors.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        assert all(c.static_mesh!=old for c in scene),path
        report[path]=sum(c.get_instance_count() if isinstance(c,unreal.InstancedStaticMeshComponent) else 1
                         for c in scene if c.static_mesh in (sedan,wagon))
        assert report[path]>0,path
    assert hashlib.sha256(lab.read_bytes()).hexdigest()==digest
    (saved/'blender_vehicles.json').write_text(json.dumps(report,indent=2))
    assert levels.load_map(MAPS[0])
    lev=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    lev.editor_set_game_view(True)
    offset=V((10006.289955343997,6612.598659341473,2150))
    p=V((5230,12380,2460))
    q=V((5370,13100,2250))
    editor.set_level_viewport_camera_info(p-offset,unreal.MathLibrary.find_look_at_rotation(p,q))
    shot=unreal.AutomationLibrary.take_high_res_screenshot(1450,820,str(saved/'BlenderVehiclesParking.png'),delay=2.)
    start=time.monotonic()
    def tick(dt):
        if time.monotonic()-start>4 and (shot.is_task_done() or time.monotonic()-start>16):
            unreal.unregister_slate_post_tick_callback(handle)
            runpy.run_path(str(saved/'Test_BlenderVehicles.py'),run_name='__main__')
    handle=unreal.register_slate_post_tick_callback(tick)


if __name__=='__main__':
    main()
