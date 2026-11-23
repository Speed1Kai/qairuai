"""Build the market passage and the signed pedestrian approach to Station 07."""
from pathlib import Path
from datetime import datetime
import json
import math
import shutil
import unreal
from Industrial_Common import A, B, add, compile_bp, save
from Build_RuinedUrbanCampus import LEVEL, OFFSET, Site, actors, levels
from Build_KlenStreet import WEST, FINISH, FLOOR, asset
from SurfacePolish_Materials import import_file

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SOURCE=PROJECT/'SourceAssets/Passage07'
ROOT='/Game/Environment/Passage07'
PATH=ROOT+'/BP_Passage07'
LABEL='CITY_Passage07'
SIGNS=('OfficeSign','NorthSign','EastSign','TurnSign','Inventory')
MODELS=('SM_LostOffice','SM_BlueSuitcase')
PAINT='/Game/Surface/Materials/M_LanePaint'

def prepare(world):
    finishes={'Brick':'/Game/Downtown_West/Materials/Buildings_Shared/MI_Building_Bricks_A_red_WS',
              'Plaster':FLOOR+'Concrete','Wood':FINISH+'StationTimber','Tile':FLOOR+'Mixed',
              'Green':FINISH+'InfillPaint','Ivory':FINISH+'StationPaper','Curtain':FINISH+'StationSafety',
              'Blue':'/Game/LabTutorial/FirstFloor/M_LabTeal','Frame':FINISH+'Frame',
              'Armor':FINISH+'InfillSteel','Amber':FINISH+'StationSafety','Glass':FINISH+'Glass'}
    opts=unreal.FbxImportUI()
    opts.set_editor_property('automated_import_should_detect_type',False)
    opts.set_editor_property('import_materials',False)
    opts.set_editor_property('import_textures',False)
    opts.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
    opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
    opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for name in MODELS:
        if A.does_asset_exist(ROOT+'/'+name):continue
        model=import_file(SOURCE/(name+'.fbx'),ROOT,opts)
        for i,slot in enumerate(model.static_materials):
            model.set_material(i,asset(finishes[str(slot.get_editor_property('imported_material_slot_name'))]))
        model.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(model)
    lib=unreal.MaterialEditingLibrary
    for name in SIGNS:
        if A.does_asset_exist(ROOT+'/M_'+name):continue
        tex=import_file(SOURCE/(name+'.png'),ROOT)
        save(tex)
        mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
        node=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
        node.set_editor_property('texture',tex)
        lib.connect_material_property(node,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        lib.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        lib.recompile_material(mat);save(mat)

def layout(site):
    cube=asset('/Engine/BasicShapes/Cube')
    plane=asset('/Engine/BasicShapes/Plane')
    sidewalk=asset(WEST+'ground_walkways/SM_ground_mod_walk_tile_a_4m')
    def box(name,mat,x,y,base,w,d,h,solid=False):
        site.mesh(name,cube,x,y,base+h/2,(w/100,d/100,h/100),collide=solid)
        site.batches[name].set_material(0,asset(mat))
    def tile(group,x,y,z,w,d):
        site.fitted(group,sidewalk,x,y,z,(w,d,4.5),collide=True)
    def prop(name,path,x,y,base,yaw=0,s=1,solid=False):
        mesh=asset(path);b=mesh.get_bounding_box()
        c=(b.min+b.max)*.5
        a=math.radians(yaw)
        site.mesh(name,mesh,x-s*(c.x*math.cos(a)-c.y*math.sin(a)),y-s*(c.x*math.sin(a)+c.y*math.cos(a)),base-b.min.z*s,(s,)*3,yaw=yaw,collide=solid)
    def sign(name,x,y,z,width,height,yaw=180):
        site.mesh(name,plane,x,y,z,(width/100,height/100,1),roll=90,yaw=yaw)
        site.batches[name].set_material(0,asset(ROOT+'/M_'+name))
    def street_sign(name,x,y,yaw=180):
        box('WayfindingPosts',FINISH+'InfillSteel',x,y,2154,7,7,232,True)
        dx,dy=math.sin(math.radians(yaw))*6,math.cos(math.radians(yaw))*6
        sign(name,x+dx,y+dy,2368,212,53,yaw)
    def row(group,a,b,fixed,across=False,base=2156,width=230):
        n=math.ceil((b-a)/365)
        step=(b-a)/n
        for i in range(n):
            mid=a+(i+.5)*step
            tile(group,mid if across else fixed,fixed if across else mid,base,step-.5 if across else width,width if across else step-.5)
    # Flush links between the market floor, loading curb, and front of the old office.
    row('MarketLink',13010,14740,50325,True,2155,306)
    row('MarketEastWalk',50410,53850,14783,False,2155,267)
    row('FrontWalk',14210,14792,53980,True,2155,276)
    row('PassageFloor',53940,55760,14220,False,2155,282)
    row('ExitWalk',14210,14900,55710,True,2155,276)
    row('OfficeForecourt',13210,14114,54080,True,2155,400)
    site.mesh('LostOffice',asset(ROOT+'/SM_LostOffice'),13768,55000,2155,collide=True)
    box('OfficePlaque',FINISH+'Frame',13578,54587,2457,495,7,72)
    sign('OfficeSign',13578,54582,2493,478,64)
    sign('NorthSign',14220,54568,2526,226,57)
    prop('OfficeLuggage',ROOT+'/SM_BlueSuitcase',13272,55152,2165,8,.93)
    prop('OfficeLuggage',ROOT+'/SM_BlueSuitcase',13332,55183,2165,-17,.73)
    box('NoticeCase',FINISH+'Frame',13493,55384,2264,82,5,82)
    sign('Inventory',13493,55380,2307,75,75)
    prop('QueueBench',WEST+'props/prop_bench_wood/SM_bench_wood_a',13195,54154,2160,0,.90,True)
    lamp=add(site.bp,unreal.PointLightComponent,'OfficeDeskLight','SiteRoot')
    lamp.set_editor_property('relative_location',unreal.Vector(13480-OFFSET[0],55125-OFFSET[1],2420-OFFSET[2]))
    lamp.set_editor_property('attenuation_radius',360.)
    lamp.set_editor_property('intensity',280.)
    lamp.set_editor_property('light_color',unreal.Color(255,185,131))
    lamp.set_editor_property('cast_shadows',False)
    lamp.set_mobility(unreal.ComponentMobility.MOVABLE)
    # Paved walking side beside the northbound street and three flush intersections.
    for a,b in ((55710,58210),(59720,67290),(68935,73460)):
        row('WestPavement',a,b,14691,False,2156,290)
        box('Kerb',FLOOR+'Concrete',14841,(a+b)/2,2154,12,b-a,10,True)
    row('RubbleBypass',74150,76275,14400,False,2155,225)
    row('CrossingSouth',25800,30900,77712,True,2155,230)
    # Short cuts in the asphalt surface follow service inlets along the street.
    for x,y,w,d in ((14968,61520,165,364),(15028,67140,222,497),(23480,78153,382,171),(33080,82010,98,302)):
        box('TarmacRepairs','/Game/Surface/Materials/M_Asphalt',x,y,2155.72,w,d,.45)
    for y in (58950,68100,78100):
        for x in range(14591,15022,79):box('Crosswalk',PAINT,x,y,2155.6,40,168,.3)
    street_sign('EastSign',14815,77430)
    # Follow the east-west road past uphill blocks. Paver guides sit at both ends, away from debris.
    row('CornerPavement',14900,18550,77448,True,2155.5,255)
    row('StationCorner',30550,33170,78760,True,2155.5,227)
    street_sign('TurnSign',33052,78365,90)
    row('StationApproach',78720,83580,33045,False,2155.5,277)
    for y in (80550,82320,83750):
        prop('RoadDrain',WEST+'props/prop_sewer_caps/SM_sewer_cap_c',33250,y,2156,8,.72)


def remove_vegetation():
    """Keep the paving and the office foundations clear of pre-existing plants."""
    total=0
    for actor in actors.get_all_level_actors():
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.static_mesh or not any(t in c.static_mesh.get_name().lower() for t in ('grass','fir','shrub','weed','reed')):continue
            remove=[]
            for i in range(c.get_instance_count()):
                p=c.get_instance_transform(i,True).translation
                x,y=p.x+OFFSET[0],p.y+OFFSET[1]
                if ((13095<x<14890 and 53850<y<55780) or (14602<x<14980 and 50414<y<53850)
                    or (14540<x<14865 and any(a<y<b for a,b in ((55710,58210),(59720,67290),(68935,73460))))):
                    remove.append(i)
            if remove:
                actor.modify();c.modify()
                for i in reversed(remove):c.remove_instance(i)
                total+=len(remove)
    return total

def install():
    assert not levels.get_dirty_map_packages()
    backup=PROJECT/'Saved/Backups/Passage07'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True)
    for package,ext in ((LEVEL,'.umap'),(PATH,'.uasset')):
        f=PROJECT/'Content'/(package[6:]+ext)
        if f.exists():shutil.copy2(f,backup/f.name)
    world=levels.load_map(LEVEL);assert world
    prepare(world)
    if A.does_asset_exist(PATH):bp=asset(PATH)
    else:
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_Passage07',ROOT,unreal.Blueprint,factory)
    site=Site(bp)
    layout(site)
    compile_bp(bp);save(bp)
    matching=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(matching)<=1
    if not matching:
        actor=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
        actor.set_actor_label(LABEL);actor.set_folder_path('CITY/Passage07')
    else:
        for c in matching[0].get_components_by_class(unreal.InstancedStaticMeshComponent):
            template=site.batches.get(c.get_name())
            if template:
                c.modify();c.clear_instances()
                c.add_instances([template.get_instance_transform(i,False) for i in range(template.get_instance_count())],False,False)
    changed=remove_vegetation()
    world.modify();assert levels.save_map(world,LEVEL) and levels.load_map(LEVEL)
    found=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(found)==1
    counts={c.get_name():c.get_instance_count() for c in found[0].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert all(counts.get(name)==1 for name in ('LostOffice',*SIGNS)),counts
    out=PROJECT/'Saved/CityPassage19';out.mkdir(exist_ok=True)
    report=out/'Build.json'
    first=json.loads(report.read_text()) if report.exists() else {}
    report.write_text(json.dumps(dict(backup=first.get('backup',str(backup)),latest_backup=str(backup),instances=counts,removed_plants=first.get('removed_plants',0)+changed),indent=2))

if __name__=='__main__':install()


