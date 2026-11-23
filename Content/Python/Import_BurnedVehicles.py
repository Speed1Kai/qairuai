"""Reimport the two existing car meshes as burned wrecks and weather the vans."""
from datetime import datetime
import json
import runpy
import shutil
import time

import unreal
from Import_BlenderVehicles import A,M,ROOT,MAPS,source,saved,editor,levels,tools,save,V

VAN='/Game/City/Props/DeliveryVan/SM_CityDeliveryVan/StaticMeshes/SM_CityDeliveryVan'
PALETTE={
    'Body':(.074,.050,.035),'Wagon':(.112,.073,.041),'Rubber':(.018,.018,.016),
    'Steel':(.123,.110,.093),'Trim':(.039,.032,.026),'Glass':(.045,.068,.062),
    'Tail':(.091,.022,.016),'Headlamp':(.161,.143,.106),'Oxide':(.168,.058,.022),
}
names=('SM_FP_AbandonedSedan','SM_FP_SecurityWagon')


def burn(key):
    name='M_Wreck_'+key
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return A.load_asset(path)
    mat=tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    tint=M.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-440,90)
    tint.set_editor_property('constant',unreal.LinearColor(*PALETTE[key],1))
    pos=M.create_material_expression(mat,unreal.MaterialExpressionWorldPosition,-440,-110)
    custom=M.create_material_expression(mat,unreal.MaterialExpressionCustom,-175,0)
    inputs=[]
    for name in ('P','Tint'):
        n=unreal.CustomInput()
        n.set_editor_property('input_name',name)
        inputs.append(n)
    custom.set_editor_property('inputs',inputs)
    custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property('code','''
struct N {
  float hash(float3 p){return frac(sin(dot(p,float3(127.1,311.7,47.3)))*43758.5453);}
  float field(float3 p){
    float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
    float a=lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y);
    float3 j=i+float3(0,0,1);
    float b=lerp(lerp(hash(j),hash(j+float3(1,0,0)),f.x),lerp(hash(j+float3(0,1,0)),hash(j+float3(1,1,0)),f.x),f.y);
    return lerp(a,b,f.z);
  }
}; N n;
float scorch=n.field(P*.023)*.69+n.field(P*.066)*.24+n.field(P*.26)*.07;
float grain=n.field(P*.49);
float coal=smoothstep(.31,.72,scorch);
float ash=smoothstep(.62,.83,scorch)*smoothstep(.39,.8,grain);
return lerp(Tint*(.68+.44*grain),float3(.008,.007,.006),coal*.87)+ash*.034;
''')
    assert M.connect_material_expressions(pos,'',custom,'P')
    assert M.connect_material_expressions(tint,'',custom,'Tint')
    assert M.connect_material_property(custom,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for value,prop in ((.84,unreal.MaterialProperty.MP_ROUGHNESS),(.16,unreal.MaterialProperty.MP_METALLIC)):
        value_node=M.create_material_expression(mat,unreal.MaterialExpressionConstant,50,180)
        value_node.set_editor_property('r',value)
        assert M.connect_material_property(value_node,'',prop)
    if key in ('Glass','Oxide'):
        mat.set_editor_property('two_sided',True)
    M.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(mat)
    save(mat)
    return mat


def reimport(name,materials):
    existing=A.load_asset(ROOT+'/'+name)
    old=existing.get_bounding_box()
    ui=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                    import_materials=False,import_textures=False).items():
        ui.set_editor_property(k,v)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    task=unreal.AssetImportTask()
    for k,v in dict(filename=str(source/(name+'.fbx')),destination_path=ROOT,destination_name=name,
                    automated=True,save=False,replace_existing=True,replace_existing_settings=True,options=ui).items():
        task.set_editor_property(k,v)
    tools.import_asset_tasks([task])
    mesh=A.load_asset(ROOT+'/'+name)
    assert mesh and task.get_editor_property('imported_object_paths'),name
    bounds=mesh.get_bounding_box()
    dims=bounds.max-bounds.min
    old_dims=old.max-old.min
    assert all(abs(a-b)<18 for a,b in zip((dims.x,dims.y,dims.z),(old_dims.x,old_dims.y,old_dims.z))),str(dims)
    for i,slot in enumerate(mesh.static_materials):
        raw=str(slot.material_slot_name)
        key=next((k for k in PALETTE if raw.lower().startswith(k.lower())),None)
        assert key,raw
        if key=='Body' and name==names[1]:
            key='Wagon'
        mesh.set_material(i,materials[key])
    sm=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sm.remove_collisions(mesh)
    assert sm.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)>=0
    save(mesh)
    return len(mesh.static_materials)


def main():
    backup=saved/'Backups/BurnedVehicles'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    content=source.parent.parent/'Content'
    for p in (*(ROOT+'/'+name for name in names),VAN):
        shutil.copy2(content/(p.removeprefix('/Game/')+'.uasset'),backup)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    materials={k:burn(k) for k in PALETTE}
    report={name:reimport(name,materials) for name in names}
    van=A.load_asset(VAN)
    for i,slot in enumerate(van.static_materials):
        n=str(slot.material_slot_name).lower()
        key=next((v for k,v in [('white','Body'),('black','Trim'),('glass','Glass'),('tail','Tail'),
                  ('lamp','Headlamp'),('rubber','Rubber'),('chrome','Steel'),('steel','Steel')] if k in n),'Trim')
        van.set_material(i,materials[key])
    save(van)
    assert levels.load_map(MAPS[0])
    (saved/'burned_vehicles.json').write_text(json.dumps(dict(saved=True,slots=report,van_slots=len(van.static_materials)),indent=2))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
    offset=V((10006.289955343997,6612.598659341473,2150))
    p,q=V((5130,13035,2400)),V((5540,13320,2220))
    editor.set_level_viewport_camera_info(p-offset,unreal.MathLibrary.find_look_at_rotation(p,q))
    shot=unreal.AutomationLibrary.take_high_res_screenshot(1450,820,str(saved/'BurnedVehiclesParking.png'),delay=2.)
    start=time.monotonic()
    def tick(dt):
        if time.monotonic()-start>4 and (shot.is_task_done() or time.monotonic()-start>17):
            unreal.unregister_slate_post_tick_callback(handle)
            runpy.run_path(str(saved/'Test_BurnedVehicles.py'),run_name='__main__')
    handle=unreal.register_slate_post_tick_callback(tick)


if __name__=='__main__':
    main()
