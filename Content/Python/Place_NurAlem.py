"""Place the ruined Astana Expo pavilion at the end of a city avenue."""
from datetime import datetime
import json
import math
import shutil

import unreal

from Build_CityReclaim import material, ROOT as CITY
from Build_RuinedUrbanCampus import (
    A, B, GROUND, LEVEL, OFFSET, Site, V, actors, add, compile_bp, components,
    content, levels, local, save, saved, tools,
)

ROOT = '/Game/Environment/ExpoAstana'
SOURCE = content.parent/'SourceAssets/ExpoAstana'
X,Y,Z = 16500.,105150.,GROUND+345.
MODEL_NAMES = ('SM_NurAlem_Ruined','SM_NurAlem_Plaza')
LABEL = 'EXPO_NurAlem'
CITY_LABEL = 'RECLAIM_City'
CITY_BP = CITY+'/BP_ReclaimedCity'


def asset(path):
    result=A.load_asset(path)
    assert result,path
    return result


def import_meshes(reimport_pavilion=False):
    A.make_directory(ROOT)
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    materials={key:asset(CITY+'/M_Reclaim_'+key) for key in
               ('Concrete','Frame','Armor','Interior','Shards','Cyan')}
    materials['Plaza']=asset('/Game/Environment/SurfacePolish/M_Scan_Concrete')
    materials['Oxide']=asset('/Game/Surface/Materials/M_Oxide')
    wear='''
float2 p=float2(P.x+P.y*.71,P.z+P.y*.17);
float dirt=n.sample(p/430.0)*.71+n.sample(p/105.0)*.29;
return Tint*lerp(.57,1.20,dirt);
'''
    materials['ExpoGlass']=material('ExpoGlazing',(.027,.066,.088),.51,.29,field=wear)
    materials['ExpoLight']=material('ExpoGlazingFaded',(.052,.111,.133),.43,.37,field=wear)
    options=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,import_materials=False,
                          import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(key,value)
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    meshes=[]
    for name in MODEL_NAMES:
        path=ROOT+'/'+name
        if not A.does_asset_exist(path) or reimport_pavilion and name==MODEL_NAMES[0]:
            task=unreal.AssetImportTask()
            for key,value in dict(filename=str(SOURCE/(name+'.fbx')),destination_path=ROOT,
                                  destination_name=name,automated=True,save=False,replace_existing=True,options=options).items():
                task.set_editor_property(key,value)
            tools.import_asset_tasks([task])
            assert task.get_objects(),name
        mesh=asset(path)
        for i,slot in enumerate(mesh.static_materials):
            mesh.set_material(i,materials[str(slot.material_slot_name)])
        body=mesh.get_editor_property('body_setup')
        body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        body.set_editor_property('double_sided_geometry',True)
        save(mesh)
        meshes.append(mesh)
    sphere,plaza=meshes
    b=sphere.get_bounding_box()
    assert 7950<b.max.x-b.min.x<8160 and 9800<b.max.z<10350,str(b)
    p=plaza.get_bounding_box()
    assert p.min.y < -4600 and p.max.y > 4100,str(p)
    return sphere,plaza


def author(meshes):
    path=ROOT+'/BP_NurAlem'
    if A.does_asset_exist(path):
        bp=asset(path)
    else:
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.Actor)
        bp=tools.create_asset('BP_NurAlem',ROOT,unreal.Blueprint,factory)
    site=Site(bp)
    for label,mesh in zip(('Pavilion','Forecourt'),meshes):
        site.mesh(label,mesh,X,Y,Z,collide=True)
        site.batches[label].set_cull_distances(0,0)
        site.batches[label].set_editor_property('can_ever_affect_navigation',False)
    site.box('steel',X,Y-3175,Z+938,1150,35,178)
    sign=add(bp,unreal.TextRenderComponent,'EntranceSign','SiteRoot')
    sign.set_mobility(unreal.ComponentMobility.STATIC)
    sign.set_text(unreal.Text('NUR ALEM'))
    sign.set_world_size(132.)
    sign.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    sign.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    sign.set_text_render_color(unreal.Color(176,199,198,255))
    sign.set_editor_property('relative_location',local(X,Y-3195,Z+938))
    sign.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90))
    sign.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    ivy=asset(CITY+'/SM_Reclaim_IvyCurtain')
    debris=asset('/Game/Surface/Meshes/SM_RubbleCluster')
    for index,angle in enumerate((.29,.76,1.37,2.06,2.54,3.07,3.54,4.07,4.82,5.47,5.98)):
        x,y=math.cos(angle),math.sin(angle)
        site.mesh('Ivy',ivy,X+x*3135,Y+y*3135,Z+860,(1.14,1.,1.38),
                  yaw=math.degrees(angle)-90)
        if abs(x)>.36:
            s=.42+.14*(index%3)
            site.mesh('FacadeDebris',debris,X+x*3470,Y+y*3470,Z+2,(s,s,s),yaw=index*47)
    site.batches['Ivy'].set_cull_distances(12500,29000)
    compile_bp(bp)
    save(bp)
    return bp


def clear_forecourt(city):
    removed=0
    for c in city.get_components_by_class(unreal.InstancedStaticMeshComponent):
        if not c.get_name().startswith(('HorizonFir','StreetFir','LowShrub','Grass_')):
            continue
        trim=[]
        for i in range(c.get_instance_count()):
            p=c.get_instance_transform(i,True).translation
            x,y=p.x+OFFSET[0],p.y+OFFSET[1]
            plaza=(x-X)**2+(y-Y)**2<4530.**2
            approach=abs(x-X)<590 and Y-4850<y<Y-3030
            if plaza or approach:
                trim.append(i)
        if trim:
            c.modify()
            for i in reversed(trim):
                assert c.remove_instance(i)
            removed+=len(trim)
    return removed


def main():
    world=levels.load_map(LEVEL)
    assert world
    meshes=import_meshes()
    bp=author(meshes)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    backup=saved/'Backups/NurAlem'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    removed=clear_forecourt(scene[CITY_LABEL])
    if LABEL in scene:
        assert actors.destroy_actor(scene[LABEL])
    expo=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    assert expo
    expo.set_actor_label(LABEL)
    expo.set_folder_path('SURFACE/Expo Astana')
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    expo=scene[LABEL]
    assert all(str(c.get_collision_profile_name())=='BlockAll' for c in
               expo.get_components_by_class(unreal.InstancedStaticMeshComponent) if c.get_name() in ('Pavilion','Forecourt'))
    assert clear_forecourt(scene[CITY_LABEL])==0,'Forecourt vegetation override did not persist'
    (saved/'nur_alem_placement.json').write_text(json.dumps(dict(saved=True,actor=LABEL,
        map=LEVEL,position_cm=[X,Y,Z],vegetation_cleared=removed,backup=str(backup)),indent=2),encoding='utf-8')
