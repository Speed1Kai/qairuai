"""Build the first CityPlan block in the streamed city, in world centimetres."""
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import json
import math
import shutil
import unreal
from Industrial_Common import A, B, compile_bp, save
from Build_RuinedUrbanCampus import LEVEL, OFFSET, Site, actors, levels

ROOT = '/Game/Environment/KlenStreet'
BP = ROOT + '/BP_KlenStreet'
LABEL = 'CITY_Klen_PostOffice'
IN = '/Game/Environment/CityInfill/SM_Infill_'
WEST = '/Game/Downtown_West/Assets/'
QW = '/Game/Environment/QuixelWarehouse/Meshes/SM_QW_'
FINISH = '/Game/Environment/CityReclaim/M_Reclaim_'
FLOOR = '/Game/Environment/SurfacePolish/M_Scan_'
CONFIG = {'PostOffice': (300,75), 'KlenStop': (69,103.5), 'CourtyardNotes': (138,92)}

@lru_cache(None)
def asset(path):
    obj = unreal.load_asset(path)
    if not obj: raise RuntimeError(path)
    return obj

def sign_material(name, project):
    path = ROOT + '/M_' + name
    if A.does_asset_exist(path): return asset(path)
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(project/'SourceAssets'/'KlenStreet'/(name+'.png')),
                           destination_path=ROOT, automated=True, save=True).items():
        task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    tex = lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
    tex.set_editor_property('texture',asset(ROOT+'/'+name))
    lib.connect_material_property(tex,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
    lib.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    lib.recompile_material(mat)
    save(mat)
    return mat

def layout(site,project):
    def place(path,x,y,z,yaw=0,scale=1,solid=True):
        m=asset(path)
        b=m.get_bounding_box()
        center=(b.min+b.max)*.5
        a=math.radians(yaw)
        dx=scale*(center.x*math.cos(a)-center.y*math.sin(a))
        dy=scale*(center.x*math.sin(a)+center.y*math.cos(a))
        site.mesh(m.get_name(),m,x-dx,y-dy,z-scale*b.min.z,(scale,)*3,yaw=yaw,collide=solid)
    def box(key,material,x,y,base,width,depth,height,solid=True):
        site.mesh(key,asset('/Engine/BasicShapes/Cube'),x,y,base+height/2,(width/100,depth/100,height/100),collide=solid)
        site.batches[key].set_material(0,asset(material))
    def board(name,x,y,z,bottom):
        width,height=CONFIG[name]
        box('Frame',FINISH+'Frame',x-4,y,z-height/2-2,6,width+4,height+4)
        for yy in (y-width*.37,y+width*.37):
            box('Posts',FINISH+'InfillSteel',x-6,yy,bottom,6,6,z-height/2-bottom)
        site.mesh(name,asset('/Engine/BasicShapes/Plane'),x,y,z,(width/100,height/100,1),yaw=-90,roll=90)
        site.batches[name].set_material(0,sign_material(name,project))
    # Flush stone forecourt at the height of the older retaining slab; two low risers meet the sidewalk.
    box('Plinth',FLOOR+'Concrete',3945,38045,2149,1060,1570,51)
    box('Strip',FLOOR+'Concrete',4501,38045,2171,52,1570,20)
    box('Toe',FLOOR+'Concrete',4550,38045,2171,46,1570,10)
    paving=asset(WEST+'ground_walkways/SM_ground_mod_walk_tile_a_4m')
    for x in (4210,4390):
        for i in range(6):
            site.fitted('PublicPaving',paving,x,37405+i*255,2200,(179.8,254.8,4),collide=True)
    place(IN+'ShopRow',3760,37970,2200,-90,.97)
    board('PostOffice',4150,37870,2499,2204)
    # Secondary entrance from the residential courtyard for receiving parcels.
    box('ServiceCourt',FLOOR+'Mixed',3680,38970,2149,1120,965,13)
    place(IN+'CourtyardPergola',3405,39200,2162,90,.64)
    place(QW+'SteelRack',3470,38695,2200,90,.78)
    place(QW+'WrappedCrate',3535,38645,2200,4,.54)
    place(QW+'HandTruck',3565,38780,2200,23,.85)
    # Signed side entrance at the landing, with fittings accessible from the loading side.
    frame=FINISH+'Frame'
    steel=FINISH+'InfillSteel'
    box('DoorTrim',frame,3760,38479,2200,128,13,229)
    box('ServiceDoor',FINISH+'StationCladding',3760,38489,2201,111,9,215)
    box('DoorTrim',frame,3760,38496,2234,102,3,4)
    box('Handle',steel,3800,38500,2298,14,5,3)
    box('DoorTrim',frame,3760,38498,2373,62,4,33)
    box('FrostedGlass',FINISH+'StationPaper',3760,38502,2378,52,2,23)
    box('Hood',steel,3760,38507,2432,158,72,6)
    box('Step',FLOOR+'Concrete',3770,38853,2162,159,45,26)
    box('Step',FLOOR+'Concrete',3770,38897,2162,159,43,13)
    # Letter box on the public forecourt, with collection slot and timetable card.
    box('MailboxStand',steel,4180,37585,2204,10,16,62)
    box('MailboxBody',FINISH+'StationSafety',4180,37585,2266,33,52,59)
    box('MailboxCap',frame,4180,37585,2325,37,57,4)
    box('MailSlot',frame,4197.2,37585,2310,2,37,4)
    box('CollectionTimes',FINISH+'StationPaper',4197.2,37585,2281,2,18,13)
    board('CourtyardNotes',3910,38945,2315,2162)
    place(IN+'TransitShelter',4924,39285,2172,-90,.90)
    board('KlenStop',4938,38885,2341,2172)
    place(WEST+'props/prop_recycle_bin/SM_prop_recycle_bin',4945,39680,2172,12,.82)
    place(WEST+'props/prop_sewer_caps/SM_sewer_cap_c',5115,39035,2155,27,.80,False)
    place(IN+'PlanterBench',3700,39670,2150,0,.78)
    place(WEST+'foliage/bush/SM_bush_low',3700,39670,2175,24,.38,False)

def clear_forecourt():
    """Remove only old autogenerated vegetation and road debris occupying the new public frontage."""
    counts=Counter()
    allowed={'RECLAIM_City':('StreetFir','Grass','LowShrub'),
             'CITY_StreetLife':('Grass','Shrub'),
             'SURF_Environment':('SM_RubbleCluster','SM_DeadTree'),
             'CITY_Aftermath':('TwistedGuardrail','RippedSlab')}
    for actor in actors.get_all_level_actors():
        label=actor.get_actor_label()
        if label not in allowed:continue
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.get_name().startswith(allowed[label]):continue
            remove=[]
            for i in range(c.get_instance_count()):
                p=c.get_instance_transform(i,True).translation
                x,y=p.x+OFFSET[0],p.y+OFFSET[1]
                if 3190<x<5150 and 36900<y<39880:remove.append(i)
            if remove:
                actor.modify()
                c.modify()
                for i in reversed(remove):assert c.remove_instance(i)
                counts[label]+=len(remove)
    return counts

def install():
    project=Path(unreal.Paths.project_dir()).resolve()
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not any(p.get_name()==BP for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    world=levels.load_map(LEVEL)
    backup=project/'Saved/Backups/KlenStreet'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for package,ext in ((LEVEL,'.umap'),(BP,'.uasset')):
        src=project/'Content'/(package[6:]+ext)
        if src.exists():shutil.copy2(src,backup/src.name)
    if A.does_asset_exist(BP): bp=A.load_asset(BP)
    else:
        f=unreal.BlueprintFactory()
        f.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_KlenStreet',ROOT,unreal.Blueprint,f)
    site=Site(bp)
    layout(site,project)
    compile_bp(bp)
    save(bp)
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(matches)<=1
    if matches:
        placed=matches[0]
        for comp in placed.get_components_by_class(unreal.InstancedStaticMeshComponent):
            template=site.batches.get(comp.get_name())
            if template:
                comp.modify()
                comp.clear_instances()
                comp.add_instances([template.get_instance_transform(i,False) for i in range(template.get_instance_count())],False,False)
    else:
        placed=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
        placed.set_actor_label(LABEL)
        placed.set_folder_path('SURFACE/Klen')
    removed=clear_forecourt()
    world.modify()
    assert levels.save_map(world,LEVEL) and levels.load_map(LEVEL)
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(matches)==1
    counts={c.get_name():c.get_instance_count() for c in matches[0].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert counts['PostOffice']==counts['KlenStop']==counts['CourtyardNotes']==1
    out=project/'Saved/CityPlan19'
    out.mkdir(exist_ok=True)
    (out/'Built.json').write_text(json.dumps(dict(map=LEVEL,backup=str(backup),removed=removed,instances=counts),indent=2))
if __name__=='__main__':install()

