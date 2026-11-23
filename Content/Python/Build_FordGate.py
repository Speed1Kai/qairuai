"""Build the crossing office, pedestrian approach and service spur on the connected city map."""
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
import unreal
from Build_RuinedUrbanCampus import LEVEL, OFFSET, Site, actors, levels
from Industrial_Common import A, B, compile_bp, save
from Build_KlenStreet import asset, FINISH, FLOOR, IN, WEST, QW
from SurfacePolish_Materials import import_file

ROOT='/Game/Environment/FordGate'
PATH=ROOT+'/BP_FordGate'
LABEL='CITY_FordGate_DutyOffice'
SOURCE=Path(unreal.Paths.project_dir()).resolve()/'SourceAssets/FordGate'

def prepare(world):
    finishes={'Concrete':FLOOR+'Concrete','Frame':FINISH+'Frame','Glass':FINISH+'Glass',
              'Paint':FINISH+'StationCladding','Rust':'/Game/Surface/Materials/M_Oxide',
              'Safety':FINISH+'StationSafety','Paper':FINISH+'StationPaper'}
    ui=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                    mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():ui.set_editor_property(k,v)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for n in ('SM_FordGatehouse','SM_FordMarker'):
        if A.does_asset_exist(ROOT+'/'+n):continue
        m=import_file(SOURCE/(n+'.fbx'),ROOT,ui)
        for i,slot in enumerate(m.static_materials):
            m.set_material(i,asset(finishes[str(slot.get_editor_property('imported_material_slot_name'))]))
        m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(m)
    for name in ('CrossingMarker','GateOffice'):
        if A.does_asset_exist(ROOT+'/M_'+name):continue
        tex=import_file(SOURCE/(name+'.png'),ROOT)
        save(tex)
        m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
        lib=unreal.MaterialEditingLibrary
        t=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample)
        t.set_editor_property('texture',tex)
        lib.connect_material_property(t,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        lib.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        lib.recompile_material(m)
        save(m)

def lay_out(site):
    cube=asset('/Engine/BasicShapes/Cube')
    def slab(key,mat,x,y,top,width,depth,h,solid=False,pitch=0):
        site.mesh(key,cube,x,y,top-h/2,(width/100,depth/100,h/100),pitch=pitch,collide=solid)
        site.batches[key].set_material(0,asset(mat))
    def mesh(path,x,y,z,yaw=0,scale=1,solid=True):
        m=asset(path)
        b=m.get_bounding_box()
        c=(b.min+b.max)*.5
        a=math.radians(yaw)
        site.mesh(m.get_name(),m,x-scale*(c.x*math.cos(a)-c.y*math.sin(a)),y-scale*(c.x*math.sin(a)+c.y*math.cos(a)),
                  z-scale*b.min.z,(scale,)*3,yaw=yaw,collide=solid)
    def sign(name,x,y,z,width,height,yaw):
        site.mesh(name,asset('/Engine/BasicShapes/Plane'),x,y,z,(width/100,height/100,1),yaw=yaw,roll=90)
        site.batches[name].set_material(0,asset(ROOT+'/M_'+name))
    # Keep the original road crest and river landing. Only the new east-side spur crosses the curb.
    slab('Forecourt',FLOOR+'Concrete',7520,23730,2192,1470,862,49,True)
    slab('CrewYard',FLOOR+'Mixed',8580,23510,2154,1040,1180,12,True)
    slab('ServiceAsphalt',FLOOR+'Asphalt',7740,22815,2163,2350,550,19,True)
    slab('CurbTable',FLOOR+'Asphalt',6760,22815,2193,450,550,44,True)
    slab('RoadRamp',FLOOR+'Asphalt',6440,22815,2182,203,550,22,True,6.3)
    slab('YardRamp',FLOOR+'Asphalt',7085,22815,2178,210,550,30,True,-8.2)
    # Paving from the river landing to the actual scanner, with a flush break in the service drive.
    p=asset(WEST+'ground_walkways/SM_ground_mod_walk_tile_a_4m')
    for i in range(15):
        y=22240+i*207
        if abs(y-22815)<360:continue
        site.fitted('Footpath',p,6845,y,2188,(225,206.6,5),collide=True)
    paint='/Game/Surface/Materials/M_LanePaint'
    for j in range(5):slab('Crosswalk',paint,6815,22623+j*94,2193.8,157,33,.6)
    for y in (22566,23065):
        for j in range(5):slab('YardStripe',paint,7410+j*300,y,2163.8,150,9,.6)
    # Unshifted origin preserves the relation between the observation window and its inspection shelf.
    site.mesh('Gatehouse',asset(ROOT+'/SM_FordGatehouse'),7480,23750,2192,collide=True)
    site.mesh('MarkerMast',asset(ROOT+'/SM_FordMarker'),6680,23350,2190,collide=True)
    sign('CrossingMarker',6680,23341.7,2536,119,208,180)
    # Identity board hung on the south side of the office, facing approaching pedestrians.
    slab('SignHousing',FINISH+'Frame',7500,23515,2479,263,12,66)
    sign('GateOffice',7500,23508,2446,257,62,180)
    for x in (7388,7612):
        slab('BoardHangers',FINISH+'InfillSteel',x,23523,2494,5,23,63)
    mesh(IN+'ServiceGarage',8670,23815,2154,0,.66)
    mesh(QW+'ElectricalPanel',7820,24203,2192,180,.78)
    mesh(QW+'CableSpool',8150,23840,2154,22,.79)
    mesh(QW+'HandTruck',8385,23380,2154,20,.83)
    # Covered cable trench from the service room to the scanner pedestal. Removable access lids at both ends.
    for x,y,w,d in ((7848,24114,52,193),(7274,24200,1199,35),(6681,24699,36,1035),(6633,25200,116,36)):
        top=2193 if y<24250 else 2191
        slab('CableChannel',FINISH+'InfillSteel',x,y,top,w,d,5)
    for y in (24200,24630,25172):
        slab('CableLid',FINISH+'Frame',6681,y,2194,52,57,4)
        for dy in (-15,0,15):slab('LidRib',FINISH+'InfillSteel',6681,y+dy,2195,40,3,1)
    mesh(WEST+'props/prop_sewer_caps/SM_sewer_cap_c',7700,22755,2164,13,.72,False)

def clear_lot():
    # Only autogenerated dressing that was occupying the building, new lane or pedestrian strip.
    labels={'RECLAIM_City':('StreetFir','LowShrub','Grass'),
            'CITY_StreetLife':('Grass','Shrub','Bag','Bin'),
            'SURF_Environment':('SM_RubbleCluster','SM_DeadTree'),
            'CITY_Aftermath':('RippedSlab','TwistedGuardrail','RootedIvy')}
    removed={}
    for actor in actors.get_all_level_actors():
        label=actor.get_actor_label()
        if label not in labels:continue
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.get_name().startswith(labels[label]):continue
            indices=[]
            for i in range(c.get_instance_count()):
                p=c.get_instance_transform(i,True).translation;x=p.x+OFFSET[0];y=p.y+OFFSET[1]
                if (6720<x<9150 and 22500<y<24240) or (6690<x<7010 and 22090<y<25270):
                    indices.append(i)
            if indices:
                actor.modify();c.modify()
                for i in reversed(indices):assert c.remove_instance(i)
                removed[c.get_path_name()]=len(indices)
    return removed

def install():
    project=SOURCE.parent.parent
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not any(p.get_name().startswith(ROOT+'/') for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    w=levels.load_map(LEVEL)
    backup=project/'Saved/Backups/FordGate'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path,ext in ((LEVEL,'.umap'),(PATH,'.uasset')):
        f=project/'Content'/(path[6:]+ext)
        if f.exists():shutil.copy2(f,backup/f.name)
    prepare(w)
    if A.does_asset_exist(PATH):bp=A.load_asset(PATH)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_FordGate',ROOT,unreal.Blueprint,f)
    site=Site(bp)
    lay_out(site);compile_bp(bp);save(bp)
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(matches)<=1
    if matches:
        for comp in matches[0].get_components_by_class(unreal.InstancedStaticMeshComponent):
            templ=site.batches.get(comp.get_name())
            if templ:
                comp.modify();comp.clear_instances()
                comp.add_instances([templ.get_instance_transform(i,False) for i in range(templ.get_instance_count())],False,False)
    else:
        placed=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
        placed.set_actor_label(LABEL);placed.set_folder_path('SURFACE/Ford')
    removed=clear_lot()
    w.modify();assert levels.save_map(w,LEVEL) and levels.load_map(LEVEL)
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(matches)==1
    counts={c.get_name():c.get_instance_count() for c in matches[0].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert all(counts.get(n)==1 for n in ('Gatehouse','MarkerMast','GateOffice','CrossingMarker','SM_Infill_ServiceGarage'))
    out=project/'Saved/FordGate19';out.mkdir(exist_ok=True)
    (out/'Build.json').write_text(json.dumps(dict(backup=str(backup),counts=counts,cleared=removed),indent=2))
if __name__=='__main__':install()

