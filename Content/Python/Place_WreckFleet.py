"""Install the burned fleet on the playable campus and city route."""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import runpy
import shutil
import time

import unreal
from Import_BlenderVehicles import M,ROOT,MAIN,source,saved,editor,levels,tools,actors
from Industrial_Common import A, B, V, components, compile_bp, save

LEVEL='/Game/Surface/Lvl_CampusConnected'
YARD='/Game/Surface/RuinedCampus/BP_RuinedUrbanCampus'
OFFSET=V((10006.289955343997,6612.598659341473,2150))
VEHICLES={'Bus':'SM_FP_BurnedBus','Truck':'SM_FP_BurnedCargoTruck','Van':'SM_FP_BurnedServiceVan',
          'Sedan':'SM_FP_AbandonedSedan','Wagon':'SM_FP_SecurityWagon'}

# World-frame pullouts and curbs. The several candidates per position let the
# collision and terrain check reject locations already occupied by props.
PLOTS=(
 ('Campus_ParkingBus','Bus',89,[(6940,12440),(6900,12420),(4250,12520),(4100,12550)]),
 ('Campus_RepairTruck','Truck',6,[(10415,3940),(10670,3960),(11280,4050),(11040,3820)]),
 ('Campus_WarehouseTruck','Truck',-8,[(1510,3890),(1900,3940),(1250,3730),(1480,4100)]),
 ('Campus_GardenSedan','Sedan',31,[(4650,4180),(4660,4540),(4870,3850),(4560,4390)]),
 ('Campus_CheckpointVan','Van',104,[(7000,16040),(6910,16500),(4760,16440),(7160,15780)]),
 ('Campus_ServiceWagon','Wagon',-83,[(8630,13710),(8530,13380),(8280,14050),(8200,14200)]),
 ('City_EntryBus','Bus',88,[(6340,25030),(6380,25080),(6315,24980),(5400,25030)]),
 ('City_FirstBlockSedan','Sedan',81,[(6340,25450),(6310,25580),(6310,26000),(5350,25790)]),
 ('City_CurbWagon','Wagon',101,[(6350,27900),(6360,28180),(6330,27560),(5350,28080)]),
 ('City_CrossStreetTruck','Truck',4,[(4290,32420),(3800,32420),(7690,32430),(4420,31500)]),
 ('City_ServiceYardTruck','Truck',84,[(7910,33420),(7960,33760),(3770,33680),(3870,33910)]),
 ('City_FarBlockVan','Van',96,[(6320,33710),(6280,34120),(5380,33880),(6260,34520)]),
)


def finish_material(m):
    M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(m)
    save(m)


def body_shader(m,tint):
    M.delete_all_material_expressions(m)
    c=M.create_material_expression(m,unreal.MaterialExpressionCustom,-120,-40)
    pos=M.create_material_expression(m,unreal.MaterialExpressionWorldPosition,-480,-120)
    col=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-480,120)
    col.set_editor_property('constant',unreal.LinearColor(*tint,1))
    inputs=[]
    for name in ('P','Paint'):
        i=unreal.CustomInput()
        i.set_editor_property('input_name',name)
        inputs.append(i)
    c.set_editor_property('inputs',inputs)
    c.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    c.set_editor_property('code','''
struct Noise {
float hash(float3 p){return frac(sin(dot(p,float3(127.1,311.7,47.3)))*43758.5453);}
float sample(float3 p){
  float3 i=floor(p), f=frac(p); f=f*f*(3-2*f);
  float a=lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y);
  i.z+=1;
  float b=lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y);
  return lerp(a,b,f.z);
}
}; Noise n;
float broad=n.sample(P*.010)*.60+n.sample(P*.026)*.30+n.sample(P*.093)*.10;
float fine=n.sample(P*.24);
float streak=n.sample(P*float3(.11,.11,.027));
float coal=smoothstep(.52,.76,broad+.17*streak);
float oxide=smoothstep(.32,.52,broad+fine*.075)*(1-coal);
float bare=(1-smoothstep(.22,.45,broad))*smoothstep(.24,.74,fine);
float3 clean=lerp(Paint,float3(.27,.25,.22),bare*.83);
float3 rust=lerp(float3(.039,.020,.011),float3(.22,.093,.040),fine);
return lerp(lerp(clean,rust,oxide*.84),float3(.009,.008,.007),coal*.95)*(.77+.37*fine);
''')
    assert M.connect_material_expressions(pos,'',c,'P')
    assert M.connect_material_expressions(col,'',c,'Paint')
    assert M.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for val,prop in ((.78,unreal.MaterialProperty.MP_ROUGHNESS),(.25,unreal.MaterialProperty.MP_METALLIC)):
        node=M.create_material_expression(m,unreal.MaterialExpressionConstant,0,200)
        node.set_editor_property('r',val)
        assert M.connect_material_property(node,'',prop)
    finish_material(m)


def ensure_body(key,tint):
    name='M_Wreck_'+key
    path=ROOT+'/'+name
    m=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    body_shader(m,tint)
    return m


def vehicle(key,paint):
    name=VEHICLES[key]
    path=ROOT+'/'+name
    if not A.does_asset_exist(path):
        opts=unreal.FbxImportUI()
        for k,v in dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                        import_materials=False,import_textures=False).items():
            opts.set_editor_property(k,v)
        opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
        opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        task=unreal.AssetImportTask()
        for k,v in dict(filename=str(source/(name+'.fbx')),destination_path=ROOT,destination_name=name,
                        automated=True,save=False,options=opts).items():
            task.set_editor_property(k,v)
        tools.import_asset_tasks([task])
    mesh=A.load_asset(path)
    assert mesh,path
    for i,slot in enumerate(mesh.static_materials):
        raw=str(slot.material_slot_name)
        use=next((k for k in ('Body','Steel','Rubber','Trim','Tail','Headlamp','Oxide')
                  if raw.lower().startswith(k.lower())),None)
        assert use,raw
        m=paint if use=='Body' else A.load_asset(ROOT+'/M_Wreck_'+use)
        assert m,use
        mesh.set_material(i,m)
    bounds=mesh.get_bounding_box()
    size=bounds.max-bounds.min
    low,high={'Bus':(1030,1140),'Truck':(720,810),'Van':(540,640)}[key]
    assert low<size.x<high and 170<size.y<305 and size.z>190, str(size)
    sm=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sm.remove_collisions(mesh)
    assert sm.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)>=0
    save(mesh)
    return mesh


def van_fit(old,new,t):
    a,b=old.get_bounding_box(),new.get_bounding_box()
    ac,bc=(a.min+a.max)*.5,(b.min+b.max)*.5
    e,d=a.max-a.min,b.max-b.min
    s=t.scale3d
    xforward=e.x>e.y
    sx=(e.x*s.x if xforward else e.y*s.y)/d.x
    sy=(e.y*s.y if xforward else e.x*s.x)/d.y
    sz=e.z*s.z/d.z
    local=unreal.Rotator(yaw=0. if xforward else 90.)
    rotation=unreal.MathLibrary.compose_rotators(local,t.rotation.rotator())
    old_bottom=unreal.MathLibrary.transform_location(t,V((ac.x,ac.y,a.min.z)))
    new_bottom=V((bc.x*sx,bc.y*sy,b.min.z*sz))
    shift=unreal.MathLibrary.transform_direction(unreal.Transform(rotation=rotation),new_bottom)
    return unreal.Transform(location=old_bottom-shift,rotation=rotation,scale=V((sx,sy,sz)))


def swap_parked_van(c,old,new):
    if c.static_mesh==new:
        return c.get_instance_count()
    assert c.static_mesh==old
    c.modify()
    transforms=[van_fit(old,new,c.get_instance_transform(i,False)) for i in range(c.get_instance_count())]
    c.set_static_mesh(new)
    for i,t in enumerate(transforms):
        assert c.update_instance_transform(i,t,False,True,True)
    return len(transforms)


def height(world,x,y,ignore):
    start=V((x,y,2420))-OFFSET
    end=V((x,y,2080))-OFFSET
    h=unreal.SystemLibrary.capsule_trace_single_by_profile(world,start,end,5.,7.,'Pawn',False,ignore,unreal.DrawDebugTrace.NONE,True)
    return h.to_tuple()[5].z+OFFSET.z if h else None


def locate(world,mesh,x,y,yaw,ignore=()):
    b=mesh.get_bounding_box()
    size=b.max-b.min
    c=(b.max+b.min)*.5
    a=math.radians(yaw)
    dx,dy=math.cos(a),math.sin(a)
    z=[]
    for u,v in ((0,0),(-.45,-.41),(-.45,.41),(.45,-.41),(.45,.41)):
        q=height(world,x+dx*u*size.x-dy*v*size.y,y+dy*u*size.x+dx*v*size.y,list(ignore))
        if q is None or not 2136<q<2225:
            return None
        z.append(q)
    if max(z)-min(z)>35:
        return None
    return V((x-dx*c.x+dy*c.y,y-dy*c.x-dx*c.y,max(z)+1-b.min.z))-OFFSET


def clear_bus(world,mesh,p,yaw,scene,ignore):
    b=mesh.get_bounding_box()
    c=(b.min+b.max)*.5
    d=(b.max-b.min)*.5
    rotation=unreal.Rotator(yaw=yaw)
    frame=unreal.Transform(location=p,rotation=rotation)
    center=unreal.MathLibrary.transform_location(frame,c)
    for a in scene:
        if not a.get_actor_label().startswith('CITY_Enceladus_'):
            continue
        q=unreal.MathLibrary.inverse_transform_location(frame,a.get_actor_location())-c
        if abs(q.x)<d.x+100 and abs(q.y)<d.y+100:
            return False
    half=V((d.x*.96,d.y*.98,max(8,d.z-37)))
    center.z+=24
    hit=unreal.SystemLibrary.box_trace_single_by_profile(world,center+V((0,0,2)),center,half,
        rotation,'Pawn',False,ignore,unreal.DrawDebugTrace.NONE,False)
    return not hit


def decorate(world,assets):
    placed={}
    skipped=[]
    for label,key,yaw,points in PLOTS:
        mesh=assets[key]
        for x,y in points:
            p=locate(world,mesh,x,y,yaw)
            if p is not None and (key!='Bus' or clear_bus(world,mesh,p,yaw,actors.get_all_level_actors(),[])):
                a=actors.spawn_actor_from_class(unreal.StaticMeshActor,p,unreal.Rotator(yaw=yaw))
                a.set_actor_label('FLEET_'+label)
                a.set_folder_path('SURFACE/Burned Vehicles')
                c=a.static_mesh_component
                c.set_static_mesh(mesh)
                c.set_collision_profile_name('BlockAll')
                c.set_mobility(unreal.ComponentMobility.STATIC)
                placed[label]={'mesh':mesh.get_name(),'x':x,'y':y,'yaw':yaw}
                break
        else:
            skipped.append(label)
    assert len(placed)>=8 and all(any(name.startswith(k) for name in placed) for k in ('Campus','City')), (placed,skipped)
    return placed,skipped


def main():
    assert not levels.get_dirty_map_packages()
    content=source.parent.parent/'Content'
    start=content/'Lvl_LabTutorial.umap'
    start_hash=hashlib.sha256(start.read_bytes()).hexdigest()
    backup=saved/'Backups/WreckFleet'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path,ext in ((LEVEL,'.umap'),(YARD,'.uasset'),(ROOT+'/M_Wreck_Body','.uasset'),(ROOT+'/M_Wreck_Wagon','.uasset')):
        shutil.copy2(content/(path.removeprefix('/Game/')+ext),backup)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    assets={k:vehicle(k,ensure_body(k,tint)) for k,tint in
            (('Bus',(.18,.19,.17)),('Truck',(.139,.109,.068)),('Van',(.19,.175,.145)))}
    for k in ('Sedan','Wagon'):
        assets[k]=A.load_asset(ROOT+'/'+VEHICLES[k])
    ensure_body('Body',(.12,.107,.09))
    ensure_body('Wagon',(.15,.127,.088))
    old=A.load_asset('/Game/City/Props/DeliveryVan/SM_CityDeliveryVan/StaticMeshes/SM_CityDeliveryVan')
    yard=A.load_asset(YARD)
    vans=next(c for _,c,n in components(yard) if n=='ParkingUtilityVan')
    assert swap_parked_van(vans,old,assets['Van'])==1
    compile_bp(yard)
    save(yard)

    world=levels.load_map(LEVEL)
    van_count=0
    for a in list(actors.get_all_level_actors()):
        label=a.get_actor_label()
        if label.startswith('FLEET_'):
            assert actors.destroy_actor(a)
        elif label in ('CITY_Detail_ServiceVan','CITY_Detail_EvacuationVan'):
            a.modify()
            c=a.static_mesh_component
            if c.static_mesh==old:
                t=van_fit(old,assets['Van'],a.get_actor_transform())
                c.modify()
                c.set_static_mesh(assets['Van'])
                assert actors.set_actor_transform(a,t)
            assert c.static_mesh==assets['Van']
            van_count+=1
        elif label=='RUIN_Exterior':
            c=next(c for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)
                   if c.get_name()=='ParkingUtilityVan')
            swap_parked_van(c,old,assets['Van'])
            van_count+=1
    placed,skipped=decorate(world,assets)
    assert van_count==3,van_count
    world.modify()
    assert levels.save_map(world,LEVEL)
    del world
    assert levels.load_map(LEVEL)
    labels={a.get_actor_label() for a in actors.get_all_level_actors()}
    assert all('FLEET_'+label in labels for label in placed)
    assert hashlib.sha256(start.read_bytes()).hexdigest()==start_hash
    (saved/'wreck_fleet.json').write_text(json.dumps(dict(placed=placed,skipped=skipped,
        updated_vans=van_count,backup=str(backup)),indent=2))
    runpy.run_path(str(saved/'Test_WreckFleet.py'),run_name='__main__')


if __name__=='__main__':
    main()


