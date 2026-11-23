"""Dress three previously empty blocks in the streamed city at pedestrian scale."""
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
from random import Random
import shutil

import unreal
from Build_CityReclaim import material
from Build_RuinedUrbanCampus import (
    A,B,GROUND,LEVEL,MAT,OFFSET,Site,V,actors,add,compile_bp,content,levels,local,save,saved,
)
from CityCombat_Common import asset
from Install_CityAftermath import ray
from SurfacePolish_Materials import import_file
from Build_RiverForest import persist

ROOT = '/Game/Environment/CityInfill'
SOURCE = content.parent/'SourceAssets'/'CityInfill'
WORK = saved/'CityInfill'
LABEL = 'CITY_Infill'
KINDS = ('MarketHall','ShopRow','TransitShelter','PlanterBench','ServiceGarage','CourtyardPergola','StreetLight')
BLOCKS = {
    'Market': (9500,15100,46350,52150),
    'Court': (7940,9520,70030,75220),
    'Repair': (-11660,-10000,61245,63915),
}
SCENE = (
    ('MarketHall',13410,51225,180), ('ShopRow',10280,49530,-90),
    ('ShopRow',10360,47425,-105), ('TransitShelter',14350,48350,-90),
    ('CourtyardPergola',8760,72920,90), ('ShopRow',8680,74530,-90),
    ('TransitShelter',8240,70610,-90), ('ServiceGarage',-10830,63210,180),
    ('ShopRow',-10830,61610,0),
)
PLANTERS = ((11250,48700,0),(12120,50030,90),(13670,49890,0),(11150,51610,0),
            (14400,47500,90),(14520,51680,90),(8800,70180,0),(8330,71780,90),
            (9220,71040,90),(8290,73320,90),(9230,73900,90),(-11430,62710,90),
            (-10230,62150,90))
WAREHOUSE = ('RustyDrum','CrushedDrum','Crate','Pallet','WrappedCrate','HandTruck','MetalCabinet')
SIGNAGE = (
    ('MarketSign','TRANSIT MARKET / 04',13855,50772,343,28,-90),
    ('WorkshopSign','MUNICIPAL REPAIR',-10830,62790,360,26,-90),
    ('MarketStop','04 / CIVIC LOOP',14215,48350,256,18,180),
    ('CourtStop','07 / KLEN',8105,70610,256,16,180),
    ('MarketShop','REPAIR  /  FOOD  /  SUPPLY',10740,49530,294,17,0),
)
ROUTES = (
    ((11310,49270),(14010,49270)), ((13285,48380),(13285,50610)),
    ((13743,50670),(13743,51240)), ((9240,71520),(9240,73540)),
    ((-10830,62070),(-10830,63240)),
)


def load(path):
    obj=A.load_asset(path)
    assert obj,path
    return obj


def prepare_instanced_props():
    root='/Game/Environment/QuixelWarehouse/Materials/M_QW_'
    for name in WAREHOUSE:
        persist(load(root+name))


def import_assets(world):
    prepare_instanced_props()
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    mats={key:load(path) for key,path in {
        'Concrete':'/Game/Environment/SurfacePolish/M_Scan_Concrete',
        'Brick':'/Game/Environment/CityExpansion/M_District_Brick',
        'Frame':'/Game/Environment/CityReclaim/M_Reclaim_Frame',
        'Armor':'/Game/Environment/Vehicles/M_Wreck_Steel',
        'Shards':'/Game/Environment/CityReclaim/M_Reclaim_Shards',
        'Interior':'/Game/Environment/CityReclaim/M_Reclaim_Frame',
        'Oxide':'/Game/Environment/Vehicles/M_Wreck_Oxide',
        'Timber':'/Game/Environment/CityReclaim/M_Reclaim_StationTimber',
        'Soil':'/Game/Environment/SurfacePolish/M_Scan_Forest',
        'Plaster':'/Game/Environment/CityReclaim/M_Reclaim_StationPlaster',
    }.items()}
    wear='''
float m=n.sample(P.xy*.008+P.z*.012)*.61+n.sample(P.xy*.073)*.39;
float d=smoothstep(.51,.79,n.sample(P.xy*.029+P.z*.018));
return lerp(Tint*(.52+.70*m), Tint*.24+float3(.045,.022,.01),d*.58);
'''
    mats.update({
        'Steel':material('InfillSteel',(.22,.25,.245),metal=.38,rough=.76,field=wear,two_sided=True),
        'Tile':material('InfillCeramic',(.13,.29,.275),metal=.06,rough=.76,field=wear,two_sided=True),
        'Paper':material('InfillPaper',(.49,.47,.36),rough=.94,field=wear),
        'Warm':material('InfillAmber',(.65,.34,.10),emission=True),
        'Signal':material('InfillSignal',(.20,.49,.50),emission=True),
    })
    MAT.update({
        'infill_concrete':mats['Concrete'],
        'infill_service':load('/Game/Environment/SurfacePolish/M_Scan_Asphalt'),
        'infill_seam':material('InfillSeam',(.072,.073,.068),rough=.94),
        'infill_paint':material('InfillPaint',(.49,.46,.34),rough=.90,field=wear),
    })
    ui=unreal.FbxImportUI()
    for name,value in dict(automated_import_should_detect_type=False,import_materials=False,
        import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        ui.set_editor_property(name,value)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    meshes={}
    for kind in KINDS:
        m=import_file(SOURCE/('SM_Infill_'+kind+'.fbx'),ROOT,ui)
        for index,slot in enumerate(m.static_materials):
            m.set_material(index,mats[str(slot.material_slot_name)])
        body=m.get_editor_property('body_setup')
        body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        body.set_editor_property('double_sided_geometry',True)
        save(m)
        meshes[kind]=m
    for key,path in {
        'Fir':'/Game/Surface/RiverForest/SM_Fir_A','Shrub':'/Game/Environment/CityReclaim/SM_Reclaim_Shrub',
        'Leaves':'/Game/Environment/CityLife/SM_Life_Leaf47','PaperDrift':'/Game/Environment/CityLife/SM_Life_PaperDrift',
        'RootedIvy':'/Game/Environment/CityAftermath/SM_War_RootedIvy','Rubble':'/Game/Environment/CityAftermath/SM_War_RubblePile',
        'GrassA':'/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_A','GrassC':'/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_C',
        'Van':'/Game/Environment/Vehicles/SM_FP_BurnedServiceVan','Sedan':'/Game/Environment/Vehicles/SM_FP_AbandonedSedan',
        'Truck':'/Game/Environment/Vehicles/SM_FP_BurnedCargoTruck',
        **{name:'/Game/CityDowntown/Geometry/Props/SM_'+file for name,file in (
            ('TrashBag','trashBag01'),('Hydrant','hydrant'),('Newspaper','NewspaperBox'),
            ('RoadBarrier','metallicBarrier'),('Cone','RoadConstruction_cone'))},
        **{name:'/Game/Environment/QuixelWarehouse/Meshes/SM_QW_'+name for name in WAREHOUSE},
    }.items():
        meshes[key]=load(path)
    return meshes


def pavement(site):
    # Heights are offsets in cm from the surveyed outdoor datum. Base terrain
    # is flat here, so the sidewalk slab can stay a single low-cost instance.
    for x,y,w,d,level in ((12300,49250,5550,5800,8),(8730,72625,1580,5190,2),(-10830,62580,1660,2670,2)):
        site.box('infill_concrete',x,y,GROUND+level-7,w,d,14,collide=True)
        for delta in range(-int(w*.5)+275,int(w*.5)-240,420):
            site.box('infill_seam',x+delta,y,GROUND+level+.8,2.1,d-12,1.3)
        for delta in range(-int(d*.5)+300,int(d*.5)-210,470):
            site.box('infill_seam',x,y+delta,GROUND+level+.8,w-12,2.1,1.3)
    for x,y,w,d,level in ((13325,47200,3370,970,10),(-11215,62090,610,830,4),(8650,71390,780,690,4)):
        site.box('infill_service',x,y,GROUND+level-3,w,d,6,collide=True)
        for dx in range(-int(w*.5)+115,int(w*.5)-50,278):
            site.box('infill_paint',x+dx,y,GROUND+level+.8,8,d*.82,1.4)
        site.box('infill_paint',x,y+d*.38,GROUND+level+.8,w-188,8,1.4)
    for x,y,yaw in ((13310,48010,0),(12100,49260,90),(-10830,62500,0),(9150,72240,90)):
        for i in range(8):
            z=GROUND+(9 if x>0 and y<53000 else 3)
            site.box('infill_paint',x+(i-3.5)*51 if yaw==0 else x,
                     y if yaw==0 else y+(i-3.5)*51,z,25,174,1.4,yaw=yaw)


def level_at(y):
    return GROUND+(8.5 if y<53000 else 2.5)


def place(site, meshes, key, x, y, yaw=0, scale=1., solid=False, lift=0.):
    mesh=meshes[key]
    bounds=mesh.get_bounding_box()
    bottom=0. if key in KINDS else bounds.min.z*scale
    site.mesh(key+('Solid' if solid and key not in KINDS else ''),mesh,x,y,level_at(y)+lift-bottom,
              (scale,scale,scale),collide=solid,yaw=yaw)


def street_layout(site,meshes):
    for key,x,y,yaw in SCENE:
        place(site,meshes,key,x,y,yaw,solid=True)
    rng=Random(2241)
    for x,y,yaw in PLANTERS:
        place(site,meshes,'PlanterBench',x,y,yaw,solid=True)
        a=math.radians(yaw)
        for i,d in enumerate((-190,-99,-35,58,143,198)):
            s=rng.uniform(-55,51)
            px,py=x+math.cos(a)*d-math.sin(a)*s,y+math.sin(a)*d+math.cos(a)*s
            key='Shrub' if i in (1,4) else 'GrassA' if i%2==0 else 'GrassC'
            place(site,meshes,key,px,py,rng.randrange(360),rng.uniform(.65,1.10),lift=33.)
        if (x+y)%4!=2:
            place(site,meshes,'Fir',x+math.cos(a)*104,y+math.sin(a)*104,rng.randrange(360),.39,lift=27.)
        for i in range(4):
            side=-1 if i%2 else 1
            d=rng.uniform(-240,240)
            s=side*rng.uniform(111,156)
            px,py=x+math.cos(a)*d-math.sin(a)*s,y+math.sin(a)*d+math.cos(a)*s
            place(site,meshes,'Leaves',px,py,rng.randrange(360),rng.uniform(.8,1.5),lift=.7)
    details=(
        ('Van',14070,47225,98),('Sedan',12440,47350,80),('Truck',-11235,62125,4),
        ('Van',-10315,62080,3),('Sedan',8610,71375,12),
        ('RustyDrum',14135,50955,-11),('HandTruck',13730,50880,87),
        ('WrappedCrate',12635,51305,9),('Crate',14075,51305,-10),
        ('CrushedDrum',12925,50732,-33),('Crate',13980,51024,24),
        ('Pallet',-11185,62710,6),('WrappedCrate',-11175,62710,7),
        ('HandTruck',-10585,63025,22),('RustyDrum',-10455,63015,16),
        ('MetalCabinet',-10455,63455,-2),('CrushedDrum',-11240,62965,-27),
        ('Pallet',-10405,62420,-14),('Crate',-10385,62375,12),
        ('RoadBarrier',-11325,62420,4),('RoadBarrier',-10310,62595,-23),
        ('Newspaper',14225,48580,90),('Newspaper',10680,49225,80),
        ('Hydrant',14595,48885,0),('Hydrant',8270,71230,20),
        ('Rubble',11125,47150,75),('Rubble',14360,51905,-12),('Rubble',-11355,63450,25),
        ('StreetLight',13695,48140,0),('StreetLight',12790,50200,180),
        ('StreetLight',11330,51530,0),('StreetLight',8420,72240,90),
        ('StreetLight',9370,73510,-90),('StreetLight',-10380,62645,0),
    )
    for key,x,y,yaw in details:
        lift=13. if key=='WrappedCrate' and x<0 else 0.
        place(site,meshes,key,x,y,yaw,solid=key in ('Van','Sedan','Truck','WrappedCrate','MetalCabinet'),lift=lift)
    for center_x,center_y in ((11010,47570),(10690,49470),(14350,48530),(13410,51620),
                             (8460,72880),(8840,74120),(-11170,63440),(-10340,62440)):
        for i in range(9):
            key=('Leaves','GrassA','PaperDrift','GrassC','TrashBag','Rubble','RootedIvy','GrassA','Leaves')[i]
            x=center_x+rng.uniform(-150,150)
            y=center_y+rng.uniform(-130,130)
            place(site,meshes,key,x,y,rng.randrange(360),rng.uniform(.58,1.10),lift=.8)
    for x,y,yaw in ((-11460,62010,-22),(-11180,62490,5),(-10400,62810,13),(-10335,63385,-10),
                    (13990,47745,20),(14440,47850,-6),(8270,71530,-30)):
        place(site,meshes,'Cone',x,y,yaw)


def street_cues(bp):
    for name,text,x,y,height,size,yaw in SIGNAGE:
        sign=add(bp,unreal.TextRenderComponent,name,'SiteRoot')
        sign.set_mobility(unreal.ComponentMobility.STATIC)
        sign.set_text(unreal.Text(text))
        sign.set_world_size(float(size))
        sign.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        sign.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
        sign.set_text_render_color(unreal.Color(171,199,187,255))
        sign.set_editor_property('relative_location',local(x,y,level_at(y)+height))
        sign.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw))
        sign.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    lights=((13100,50800,360,3800,850,(1.,.76,.55)),(13765,51330,370,1900,655,(1.,.77,.62)),
            (14340,48350,247,1580,550,(.66,.87,.91)),(8770,72920,245,1850,655,(.77,.87,.78)),
            (-10830,63080,372,2900,740,(1.,.72,.51)),(10480,49360,280,1000,420,(.80,.94,.90)),
            (13200,49710,320,1800,1050,(.67,.79,.88)),(9320,72110,295,1400,645,(.69,.81,.85)),
            (-10550,62500,290,1650,685,(.77,.84,.88)))
    for i,(x,y,height,flux,radius,tint) in enumerate(lights):
        c=add(bp,unreal.PointLightComponent,'StreetPractical'+str(i),'SiteRoot')
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_location',local(x,y,level_at(y)+height))
        c.set_intensity_units(unreal.LightUnits.LUMENS)
        c.set_intensity(flux)
        c.set_attenuation_radius(radius)
        c.set_cast_shadows(False)
        c.set_light_color(unreal.LinearColor(*tint,1.))
        c.set_source_radius(22.)
        c.set_editor_property('volumetric_scattering_intensity',0.)


def clear_footprints(scene):
    prefixes=('StreetFir','LowShrub','Grass_','Shrub','Ivy','RippedSlab','RubblePile','TwistedGuardrail',
              'RootedIvy','ClimbingIvy','Scorch','Bag','Bottle','Can','SpentCases','Lichen','SmallFir','Fir',
              'Leaves','Leaf','Grass','PaperDrift','BrokenUrbanConcrete','RustedTrafficBlock')
    extents={'MarketHall':(905,520),'ShopRow':(550,475),'TransitShelter':(380,145),
             'CourtyardPergola':(425,185),'ServiceGarage':(655,450)}
    footprints=[(x,y,yaw,*extents[key]) for key,x,y,yaw in SCENE]
    footprints += [(x,y,yaw,286,112) for x,y,yaw in PLANTERS]
    removed=0
    for label in ('RECLAIM_City','CITY_Aftermath','CITY_StreetLife'):
        actor=scene.get(label)
        if not actor:
            continue
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.get_name().startswith(prefixes):
                continue
            for i in range(c.get_instance_count()-1,-1,-1):
                p=c.get_instance_transform(i,True).translation
                for x,y,yaw,w,d in footprints:
                    dx,dy=p.x+OFFSET[0]-x,p.y+OFFSET[1]-y
                    if abs(dx)>980 or abs(dy)>980:
                        continue
                    a=math.radians(yaw)
                    if abs(dx*math.cos(a)+dy*math.sin(a))<=w and abs(dy*math.cos(a)-dx*math.sin(a))<=d:
                        c.modify()
                        assert c.remove_instance(i)
                        removed+=1
                        break
    return removed


def verify(world):
    a=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL)
    counts={c.get_name():c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert counts.get('MarketHall')==1 and counts.get('PlanterBench')==len(PLANTERS),counts
    routes=[]
    for (x1,y1),(x2,y2) in ROUTES:
        h=ray(world,local(x1,y1,level_at(y1)+108),local(x2,y2,level_at(y2)+108))
        assert not h or h[9]!=a,(x1,y1,x2,y2,h[10].get_name(),str(h[5]))
        routes.append([x1,y1,x2,y2])
    for x,y in ((13300,49300),(8760,72865),(-10830,62710)):
        h=ray(world,local(x,y,GROUND+80),local(x,y,GROUND-40))
        assert h and h[9]==a,(x,y)
    return dict(counts=counts,routes=routes)


def install():
    world=levels.load_map(LEVEL)
    assert world
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    backup=saved/'Backups'/'CityInfill'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    meshes=import_assets(world)
    bp=asset(ROOT+'/BP_CityInfill')
    site=Site(bp)
    pavement(site)
    street_layout(site,meshes)
    street_cues(bp)
    for key,c in site.batches.items():
        c.set_editor_property('can_ever_affect_navigation',False)
        if key in ('Leaves','GrassA','GrassC','PaperDrift','RootedIvy') or key.startswith('Box_infill_seam'):
            c.set_cast_shadow(False)
            c.set_cull_distances(0,13000)
        elif key not in KINDS and not key.startswith('Box_infill_concrete'):
            c.set_cull_distances(0,29000)
    compile_bp(bp)
    save(bp)
    removed=clear_footprints(scene)
    if LABEL in scene:
        assert actors.destroy_actor(scene[LABEL])
    new=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    new.set_actor_label(LABEL)
    new.set_folder_path('SURFACE/City Infill')
    verify(world)
    assert levels.save_map(world,LEVEL)
    report=verify(levels.load_map(LEVEL))
    report.update(saved=True,plots=BLOCKS,cleared_overlaps=removed,backup=str(backup))
    (WORK/'Installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    install()

