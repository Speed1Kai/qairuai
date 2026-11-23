"""Refit the lab workshop, campus rooms and service court on both playable maps."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import unreal
from Industrial_Common import A, B, components, compile_bp, save
from Build_RuinedUrbanCampus import MAIN,LEVEL,Site,actors,levels,V
from Build_KlenStreet import FINISH,FLOOR,QW,asset
from SurfacePolish_Materials import import_file

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SOURCE=PROJECT/'SourceAssets/LabService'
ROOT='/Game/Environment/LabService'
YARD=ROOT+'/BP_LabYardService'
BASE='/Game/LabTutorial/Basement/BP_BasementExpansion'
INTERIOR='/Game/Surface/Interiors/BP_CampusInteriors'
BASE_LABEL='BASE_Expansion'
INT_LABEL='INT_AllCampusBuildings'
MODELS=('SM_LabWashSink','SM_LabRepairBench','SM_LabTransitCases','SM_LabTransferCanopy','SM_LabAirHandler')
FURNITURE=('SM_ModernConsole','SM_ModernChair','SM_LabUtilityBench','SM_ModernServerRack')
TANKS={'Cylinder_darkTrue','Cylinder_glassTrue','Cylinder_screenFalse','Cylinder_cyanFalse','Cylinder_steelTrue'}
BASE_FURN={'SM_ModernConsole','SM_LabUtilityBench','SM_ModernServerRack'}
BASE_PROXIES={(1460,-2825),(1970,-2825),(3515,-2190)}
def prepare(world):
    palette={'Concrete':FINISH+'StationCladding','Armor':FINISH+'InfillSteel','Frame':FINISH+'Frame','Amber':FINISH+'StationSafety','Cyan':'/Game/LabTutorial/FirstFloor/M_LabTeal'}
    ui=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():ui.set_editor_property(k,v)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for name in MODELS:
        if A.does_asset_exist(ROOT+'/'+name):continue
        m=import_file(SOURCE/(name+'.fbx'),ROOT,ui)
        for i,slot in enumerate(m.static_materials):m.set_material(i,asset(palette[str(slot.get_editor_property('imported_material_slot_name'))]))
        m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(m)
    for name in ('Wash','Transfer'):
        if A.does_asset_exist(ROOT+'/M_'+name):continue
        t=import_file(SOURCE/(name+'.png'),ROOT);save(t)
        m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
        graph=unreal.MaterialEditingLibrary
        n=graph.create_material_expression(m,unreal.MaterialExpressionTextureSample)
        n.set_editor_property('texture',t)
        graph.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        graph.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        graph.recompile_material(m);save(m)

def removed_instances(name,c,basement):
    if basement:
        all_items=name in BASE_FURN
        if name=='InvisibleBlockers':
            return [i for i in range(c.get_instance_count()) if tuple(round(n) for n in (c.get_instance_transform(i,False).translation.x,c.get_instance_transform(i,False).translation.y)) in BASE_PROXIES]
    else:
        all_items=name in TANKS or any(name==tag+m for tag in ('Prop_','Collision_') for m in FURNITURE)
    return list(range(c.get_instance_count())) if all_items else []

def clear_furniture(records,basement):
    result={}
    for name,c in records:
        if not isinstance(c,unreal.InstancedStaticMeshComponent):continue
        indices=removed_instances(name,c,basement)
        if indices:
            c.modify()
            for idx in reversed(indices):c.remove_instance(idx)
            result[name]=len(indices)
    return result

def named(label):
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==label]
    assert len(matches)<=1,label
    return matches[0] if matches else None

def clear_old(path,label,basement):
    bp=asset(path);placed=named(label);assert placed
    before=clear_furniture([(c.get_name(),c) for c in placed.get_components_by_class(unreal.InstancedStaticMeshComponent)],basement)
    clear_furniture([(n,c) for _,c,n in components(bp)],basement)
    compile_bp(bp);save(bp)
    placed=named(label)
    clear_furniture([(c.get_name(),c) for c in placed.get_components_by_class(unreal.InstancedStaticMeshComponent)],basement)
    return before

def basement_piece(label,mesh,x,y,z,yaw,scale=(1,1,1),roll=0,material=None):
    name='BASE_Service_'+label
    actor=named(name) or actors.spawn_actor_from_class(unreal.StaticMeshActor,V((x,y,z)))
    actor.modify();actor.set_actor_label(name);actor.set_folder_path('LAB/Basement/Maintenance')
    actor.set_actor_location_and_rotation(V((x,y,z)),unreal.Rotator(yaw=yaw,roll=roll),False,True)
    actor.set_actor_scale3d(V(scale))
    c=actor.static_mesh_component;c.modify();c.set_static_mesh(asset(mesh))
    c.set_collision_profile_name('NoCollision' if material else 'BlockAll')
    if material:c.set_material(0,asset(material))

def exterior():
    if A.does_asset_exist(YARD):bp=asset(YARD)
    else:
        factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_LabYardService',ROOT,unreal.Blueprint,factory)
    site=Site(bp)
    def piece(model,x,y,z,yaw=0):
        site.mesh(model,asset(ROOT+'/'+model),x,y,z,yaw=yaw,collide=True)
    def box(name,x,y,z,sx,sy,sz,mat,solid=False):
        site.mesh(name,asset('/Engine/BasicShapes/Cube'),x,y,z+sz/2,(sx/100,sy/100,sz/100),collide=solid)
        site.batches[name].set_material(0,asset(mat))
    cx,cy=6800,4890
    box('Apron',cx,cy-80,2149,875,595,6,FLOOR+'Concrete',True)
    piece('SM_LabTransferCanopy',cx,cy,2155,180)
    # Sign faces the loading lane south of the canopy.
    site.mesh('TransferSign',asset('/Engine/BasicShapes/Plane'),cx,cy-156,2448,(4.9,.34,1),yaw=180,roll=90)
    site.batches['TransferSign'].set_material(0,asset(ROOT+'/M_Transfer'))
    piece('SM_LabTransitCases',cx+156,cy-70,2155,22)
    for x in (cx-335,cx+335):
        box('BayEnds',x,cy-246,2155.2,8,205,.8,'/Game/Surface/Materials/M_LanePaint')
    for j in range(4):box('DrainFrame',cx-258+j*90,cy-354,2155.2,88,18,1,FINISH+'Frame')
    for j in range(30):box('DrainGrate',cx-297+j*12,cy-354,2156.2,3,16,.6,FINISH+'InfillSteel')
    # Independent condenser pair connects to the workshop facade. Its service face opens west.
    box('PlantBase',9494,6500,2149,192,367,13,FLOOR+'Concrete',True)
    piece('SM_LabAirHandler',9502,6500,2162,90)
    for y in (6341,6659):
        box('PlantGuards',9406,y,2162,12,12,60,FINISH+'StationSafety',True)
    for y in (6420,6580):
        box('DuctCollars',9598,y,2360,17,67,33,FINISH+'Frame')
    # Room positions follow surviving ground-floor furniture footprints. Keep door and stair axes clear.
    for x,y,yaw in [(5250,6400,90),(6948,-1095,90),(6450,7700,-90),(481,4774,90),(1631,6537,-90)]:
        piece('SM_LabWashSink',x,y,2154,yaw)
    for x,y,yaw in [(9774,4652,90),(10950,6167,-90),(9857,9260,90),(10879,10222,-90)]:
        piece('SM_LabRepairBench',x,y,2154,yaw)
    for x,y in [(5350,6500),(9910,4738),(10830,6130),(10150,13980),(8480,-1040)]:
        piece('SM_LabTransitCases',x,y,2154,13)
    compile_bp(bp);save(bp)
    a=named('LAB_ServiceCourt')
    if a:
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            t=site.batches.get(c.get_name())
            if t:
                c.modify();c.clear_instances();c.add_instances([t.get_instance_transform(i,False) for i in range(t.get_instance_count())],False,False)
    else:
        a=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector());a.set_actor_label('LAB_ServiceCourt');a.set_folder_path('SURFACE/Laboratory')
    return {n:t.get_instance_count() for n,t in site.batches.items()}

def planted_inside_service_pads(comp):
    if not isinstance(comp,unreal.InstancedStaticMeshComponent) or not comp.static_mesh:return []
    name=comp.static_mesh.get_name().lower()
    if not any(k in name for k in ('grass','weed','shrub','reed')):return []
    from Build_RuinedUrbanCampus import OFFSET
    result=[]
    for i in range(comp.get_instance_count()):
        t=comp.get_instance_transform(i,True).translation
        x,y,z=t.x+OFFSET[0],t.y+OFFSET[1],t.z+OFFSET[2]
        if 2090<z<2185 and ((6343<x<7257 and 4492<y<5128) or (9380<x<9620 and 6295<y<6705)):result.append(i)
    return result

def clear_pad_vegetation():
    total=0
    for actor in actors.get_all_level_actors():
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            indices=planted_inside_service_pads(c)
            if indices:
                actor.modify();c.modify()
                for idx in reversed(indices):c.remove_instance(idx)
                total+=len(indices)
    return total

def verify(level,label,basement):
    w=levels.load_map(level);assert w
    target=named(label);assert target
    for c in target.get_components_by_class(unreal.InstancedStaticMeshComponent):
        assert not removed_instances(c.get_name(),c,basement),c.get_name()
    if basement:
        assert named('BASE_Service_Sink') and named('BASE_Service_Bench') and named('BASE_Service_Cases')
        assert any(a.get_class().get_name()=='BP_BuildingPower_C' for a in actors.get_all_level_actors())
    else:
        assert named('LAB_ServiceCourt')
        assert any(a.get_actor_label()=='CITY_ServiceStation_07' for a in actors.get_all_level_actors())

def install():
    assert not levels.get_dirty_map_packages()
    backup=PROJECT/'Saved/Backups/LabService'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path,suffix in [(MAIN,'.umap'),(LEVEL,'.umap'),(BASE,'.uasset'),(INTERIOR,'.uasset'),(YARD,'.uasset')]:
        f=PROJECT/'Content'/(path[6:]+suffix)
        if f.exists():shutil.copy2(f,backup/f.name)
    world=levels.load_map(MAIN);prepare(world)
    main_changes=clear_old(BASE,BASE_LABEL,True)
    basement_piece('Bench',ROOT+'/SM_LabRepairBench',1480,-2839,2,0)
    basement_piece('Sink',ROOT+'/SM_LabWashSink',1940,-2839,2,0)
    basement_piece('Cases',ROOT+'/SM_LabTransitCases',2090,-2730,2,-17)
    basement_piece('WashSign','/Engine/BasicShapes/Plane',1940,-2884,165,0,(.94,.28,1),90,ROOT+'/M_Wash')
    world.modify();assert levels.save_map(world,MAIN)
    verify(MAIN,BASE_LABEL,True)
    world=levels.load_map(LEVEL)
    campus_changes=clear_old(INTERIOR,INT_LABEL,False)
    counts=exterior()
    vegetation=clear_pad_vegetation()
    world.modify();assert levels.save_map(world,LEVEL)
    verify(LEVEL,INT_LABEL,False)
    out=PROJECT/'Saved/LabService19';out.mkdir(exist_ok=True)
    result=out/'Build.json'
    first=json.loads(result.read_text()) if result.exists() else {}
    result.write_text(json.dumps(dict(backup=first.get('backup',str(backup)),latest_backup=str(backup),main=main_changes or first.get('main',{}),campus=campus_changes or first.get('campus',{}),new=counts,cleared_vegetation=vegetation or first.get('cleared_vegetation',0),verified_after_reload=True),indent=2))
if __name__=='__main__':install()
