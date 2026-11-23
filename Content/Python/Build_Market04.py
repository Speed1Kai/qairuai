"""Build the sheltered market entrance and north receiving yard on the connected city map."""
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

ROOT='/Game/Environment/Market04'
PATH=ROOT+'/BP_Market04'
LABEL='CITY_Market04_Access'
SOURCE=Path(unreal.Paths.project_dir()).resolve()/'SourceAssets/Market04'

def prepare(world):
    finishes={'Concrete':FLOOR+'Concrete','Frame':FINISH+'Frame','Glass':FINISH+'Glass',
              'Paint':FINISH+'StationCladding','Rust':'/Game/Surface/Materials/M_Oxide',
              'Safety':FINISH+'StationSafety','Paper':FINISH+'StationPaper','Ivory':FINISH+'StationPaper','Canvas':FINISH+'StationSafety','Wood':FINISH+'StationTimber','Enamel':FINISH+'InfillPaint'}
    ui=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                    mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():ui.set_editor_property(k,v)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for n in ('SM_MarketArcade','SM_MarketReceiving'):
        if A.does_asset_exist(ROOT+'/'+n):continue
        m=import_file(SOURCE/(n+'.fbx'),ROOT,ui)
        for i,slot in enumerate(m.static_materials):
            m.set_material(i,asset(finishes[str(slot.get_editor_property('imported_material_slot_name'))]))
        m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(m)
    for name in ('MarketEntry','GoodsIn'):
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
    def box(key,mat,x,y,base,w,d,h,solid=False):
        site.mesh(key,cube,x,y,base+h/2,(w/100,d/100,h/100),collide=solid)
        site.batches[key].set_material(0,asset(mat))
    def sign(name,x,y,z,w,h,yaw):
        site.mesh(name,asset('/Engine/BasicShapes/Plane'),x,y,z,(w/100,h/100,1),yaw=yaw,roll=90)
        site.batches[name].set_material(0,asset(ROOT+'/M_'+name))
    arc_x,arc_y=13015,49430
    market_z=2163
    # The clear centre aisle points from the public square into the old hall.
    paving=asset(WEST+'ground_walkways/SM_ground_mod_walk_tile_a_4m')
    for j in range(7):
        site.fitted('EntryPavers',paving,arc_x,48490+j*280,2158,(270,279.5,5),collide=True)
    box('MarketPlinth',FLOOR+'Concrete',arc_x,arc_y,2158,1020,480,5,True)
    site.mesh('Arcade',asset(ROOT+'/SM_MarketArcade'),arc_x,arc_y,market_z,collide=True)
    box('SignFascia',FINISH+'Frame',arc_x,arc_y-192,market_z+291,290,10,61)
    for x in (arc_x-138,arc_x+138):box('SignClips',FINISH+'InfillSteel',x,arc_y-186,market_z+300,5,18,50)
    sign('MarketEntry',arc_x,arc_y-198,market_z+321,282,55,180)

    # North delivery spur joins the existing asphalt. Turning and unloading areas stay clear.
    road_z=2158
    box('LoadingCourt',FLOOR+'Mixed',13800,52670,2144,2200,1020,14,True)
    box('ServiceDrive',FLOOR+'Asphalt',14815,53020,2145,1300,522,13,True)
    site.mesh('Receiving',asset(ROOT+'/SM_MarketReceiving'),13345,52350,road_z,collide=True)
    box('FreightFascia',FINISH+'Frame',13345,52585,road_z+338,278,10,59)
    sign('GoodsIn',13345,52591,road_z+367,272,53,0)
    roadpaint='/Game/Surface/Materials/M_LanePaint'
    for x in (13055,13666):
        for j in range(4):box('DockBoundary',roadpaint,x,52700+85*j,2158.5,8,65,1)
    for x in (12915,13780):
        box('GuardBase',FLOOR+'Concrete',x,52550,2158,52,46,14,True)
        box('DockGuard',FINISH+'StationSafety',x,52550,2172,16,16,69,True)
        box('GuardBand',FINISH+'Frame',x,52550,2217,17,17,10)
    def item(key,x,y,z,yaw=0,s=1):
        m=asset(QW+key);b=m.get_bounding_box();c=(b.min+b.max)*.5
        a=math.radians(yaw)
        site.mesh(key,m,x-s*(c.x*math.cos(a)-c.y*math.sin(a)),y-s*(c.x*math.sin(a)+c.y*math.cos(a)),z-s*b.min.z,(s,)*3,yaw=yaw,collide=True)
    item('Pallet',13175,52470,2223,2,.77)
    item('WrappedCrate',13175,52470,2235,2,.64)
    item('HandTruck',13785,52475,2158,43,.80)
    item('MetalCabinet',12945,52355,2158,89,.66)
    # A grated drain on the low side of the service drive carries runoff away from the dock.
    for j in range(4):
        y=52762+82*j
        box('Drain',FINISH+'Frame',14362,y,2158.7,29,81,1.2)
        for i in range(5):box('Slats',FINISH+'InfillSteel',14362,y-30+i*15,2160,27,3,1)


def install():
    project=SOURCE.parent.parent
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not any(p.get_name().startswith(ROOT+'/') for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    w=levels.load_map(LEVEL)
    backup=project/'Saved/Backups/Market04'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path,ext in ((LEVEL,'.umap'),(PATH,'.uasset')):
        f=project/'Content'/(path[6:]+ext)
        if f.exists():shutil.copy2(f,backup/f.name)
    prepare(w)
    if A.does_asset_exist(PATH):bp=A.load_asset(PATH)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_Market04',ROOT,unreal.Blueprint,f)
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
    w.modify();assert levels.save_map(w,LEVEL) and levels.load_map(LEVEL)
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(matches)==1
    counts={c.get_name():c.get_instance_count() for c in matches[0].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert all(counts.get(n)==1 for n in ('Arcade','Receiving','MarketEntry','GoodsIn'))
    out=project/'Saved/Market04';out.mkdir(exist_ok=True)
    (out/'Build.json').write_text(json.dumps(dict(backup=str(backup),counts=counts),indent=2))
if __name__=='__main__':install()

