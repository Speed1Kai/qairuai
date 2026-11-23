"""Place coherent abandoned street scenes and walkable city interiors on the live map."""
from collections import Counter
from datetime import datetime
from math import hypot
from pathlib import Path
from random import Random
import json
import shutil

import unreal

from Build_CityReclaim import ROADS, material
from Build_RuinedUrbanCampus import (
    A,B,GROUND,LEVEL,OFFSET,Site,V,actors,add,compile_bp,content,levels,local,save,saved,
)
from CityCombat_Common import asset
from Install_CityAftermath import CORRIDORS, ground, ray
from SurfacePolish_Materials import import_file

ROOT='/Game/Environment/CityLife'
SOURCE=content.parent/'SourceAssets/CityLife'
REPORT=saved/'CityLife'
DRESSING=ROOT+'/BP_CityStreetLife'
LABEL='CITY_StreetLife'
ROOMS={
    'Clinic': (4310.,53760.,22.,90.,'DISTRICT MEDICAL 08'),
    'Depot': (34785.,72720.,-5.,-90.,'MUNICIPAL SUPPLY 12'),
}
VEHICLES='/Game/Environment/Vehicles/'
SIEGE='/Game/Surface/RuinedCampus/Siege/'
RECLAIM='/Game/Environment/CityReclaim/M_Reclaim_'
PROPS='/Game/CityDowntown/Geometry/Props/'
CLEAR_Z=455.
LIFE_MESHES=(
    'ClinicShell','ClinicInterior','ClinicDetails','DepotShell','DepotInterior','DepotDetails',
    'Leaf11','Leaf47','Leaf73','PaperDrift','FightingPosition',
)
MAJOR={'Tank','Carrier','Bus','Wagon','Van','Sedan','Truck','FightingPosition'}
LEAVES=('Leaf11','Leaf47','Leaf73')
GRASS=('GrassA','GrassB','GrassC','GrassD','GrassE')


def load(path):
    value=A.load_asset(path)
    assert value,path
    return value


def get_assets(world):
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    paint='return Tint*(.61+.33*n.sample(P.xy*.027)+.20*n.sample(P.xy*.22));'
    materials={
        'Concrete':load('/Game/Environment/SurfacePolish/M_Scan_Concrete'),
        'Plaster':load(RECLAIM+'StationPlaster'),'Timber':load(RECLAIM+'StationTimber'),
        'Frame':load(RECLAIM+'Frame'),'Glass':load(RECLAIM+'StationScreen'),
        'Shards':load(RECLAIM+'Shards'),'Oxide':load(VEHICLES+'M_Wreck_Oxide'),
        'Steel':load(VEHICLES+'M_Wreck_Steel'),'Warm':load(RECLAIM+'StationWarm'),
    }
    for key,tint in {
        'Dry':(.29,.141,.044),'DarkLeaf':(.127,.075,.034),'Green':(.088,.147,.052),
        'Sand':(.24,.174,.09),'Paper':(.50,.437,.315),'White':(.48,.52,.48),
        'Cloth':(.14,.195,.145),'Brick':(.25,.124,.079),
    }.items():
        materials[key]=material('StreetLife'+key,tint,rough=.84,two_sided=True,field=paint)
    ui=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,import_materials=False,
                          import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        ui.set_editor_property(key,value)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    meshes={}
    for name in LIFE_MESHES:
        file=SOURCE/('SM_Life_'+name+'.fbx')
        assert file.is_file(),file
        mesh=import_file(file,ROOT,ui)
        for index,slot in enumerate(mesh.static_materials):
            mesh.set_material(index,materials[str(slot.material_slot_name)])
        if name.endswith(('Shell','Interior')) or name=='FightingPosition':
            body=mesh.get_editor_property('body_setup')
            body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            body.set_editor_property('double_sided_geometry',True)
        save(mesh)
        meshes[name]=mesh
    for name,path in {
        'Tank':SIEGE+'SM_Siege_BurnedTank', 'Carrier':SIEGE+'SM_Siege_TrackedCarrier',
        'Bus':VEHICLES+'SM_FP_BurnedBus','Wagon':VEHICLES+'SM_FP_SecurityWagon',
        'Van':VEHICLES+'SM_FP_BurnedServiceVan','Sedan':VEHICLES+'SM_FP_AbandonedSedan',
        'Truck':VEHICLES+'SM_FP_BurnedCargoTruck',
        'Rifle':'/Game/Combat/Firearms/SM_Hunter_Carbine',
        'Cases':'/Game/Environment/CityAftermath/SM_War_SpentCases',
        'Rubble':'/Game/Environment/CityAftermath/SM_War_RubblePile',
        'Scorch':'/Game/Environment/CityAftermath/SM_War_Scorch',
        'FirA':'/Game/Surface/RiverForest/SM_Fir_A','FirB':'/Game/Surface/RiverForest/SM_Fir_B',
        'Shrub':'/Game/Environment/CityReclaim/SM_Reclaim_Shrub',
        'Ivy':'/Game/Environment/CityAftermath/SM_War_ClimbingIvy',
        **{name:PROPS+model for name,model in (('Box','SM_box02'),('Bin','SM_streetBin'),
            ('Bag','SM_trashBag01'),('Mailbox','SM_mailbox'),('Cone','SM_RoadConstruction_cone'),
            ('Bottle','SM_beerBottle'),('Can','SM_sodaCan'),('Newspaper','SM_NewspaperBox'))},
        **{name:'/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_'+name[-1] for name in GRASS},
    }.items():
        meshes[name]=load(path)
    return meshes


def room_point(kind,x,y,z):
    cx,cy,floor,yaw,_=ROOMS[kind]
    sign=1. if yaw==90. else -1.
    return (cx+sign*y*100.,cy+sign*x*100.,GROUND+floor+z*100.)


def room_reserved(x,y,padding=0):
    return any(abs(x-cx)<530+padding and abs(y-cy)<565+padding
               for cx,cy,*_ in ROOMS.values())


def on_road(x,y,margin=0.):
    for cx,cy,w,d in (*ROADS,(5850,41000,1560,34900)):
        if abs(x-cx)<w*.5+margin and abs(y-cy)<d*.5+margin:
            return True
    return False


def surface(world,x,y,ignored):
    q=ground(world,x-OFFSET[0],y-OFFSET[1],ignored)
    if q is None:
        return None
    return q.z+GROUND


def floor_align(mesh, scale, yaw, roll):
    bounds=mesh.get_bounding_box()
    transform=unreal.Transform(rotation=unreal.Rotator(yaw=yaw,roll=roll))
    return min(transform.transform_location(V((x*scale,y*scale,z*scale))).z
               for x in (bounds.min.x,bounds.max.x) for y in (bounds.min.y,bounds.max.y)
               for z in (bounds.min.z,bounds.max.z))


def put(world,site,meshes,key,x,y,scale,yaw,ignored,*,collide=False,roll=0,allow_road=True):
    if room_reserved(x,y,50.) or (not allow_road and on_road(x,y,40.)):
        return False
    z=surface(world,x,y,ignored)
    if z is None:
        return False
    mesh=meshes[key]
    bottom=mesh.get_bounding_box().min.z*scale if not roll else floor_align(mesh,scale,yaw,roll)
    site.mesh(key,mesh,x,y,z-bottom+(.65 if key in (*LEAVES,'PaperDrift','Scorch') else 0.),
              (scale,)*3,yaw=yaw,roll=roll,collide=collide)
    return True


def roof_and_signs(bp,site,meshes):
    for kind,(x,y,z,yaw,title) in ROOMS.items():
        for suffix in ('Shell','Interior','Details'):
            key=kind+suffix
            site.mesh(key,meshes[key],x,y,GROUND+z,yaw=yaw,collide=suffix!='Details')
        sign=add(bp,unreal.TextRenderComponent,kind+'ExteriorSign','SiteRoot')
        sign.set_mobility(unreal.ComponentMobility.STATIC)
        sign.set_text(unreal.Text(title))
        sign.set_world_size(25.)
        sign.set_text_render_color(unreal.Color(168,193,188,255) if kind=='Clinic' else unreal.Color(219,170,102,255))
        sign.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        sign.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
        sign.set_editor_property('relative_location',local(*room_point(kind,0.,3.86,3.23)))
        sign.set_editor_property('relative_rotation',unreal.Rotator(yaw=0. if yaw==90. else 180.))
        sign.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
def practical_lights(bp,batches):
    def point(name,position,power,reach,color):
        light=add(bp,unreal.PointLightComponent,name,'SiteRoot')
        light.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.set_editor_property('relative_location',local(*position))
        light.set_intensity_units(unreal.LightUnits.LUMENS)
        light.set_intensity(power)
        light.set_attenuation_radius(reach)
        light.set_source_radius(23.)
        light.set_light_color(unreal.LinearColor(*color,1.))
        light.set_cast_shadows(False)
        light.set_editor_property('volumetric_scattering_intensity',0.)

    for kind in ROOMS:
        tint=(.78,.90,1.) if kind=='Clinic' else (1.,.75,.48)
        for i,(u,v,w) in enumerate(((-2.32,2.30,3.01),(2.30,-1.32,3.03))):
            point(f'{kind}Practical{i}',room_point(kind,u,v,w),1250.,565.,tint)
        point(kind+'EntryPractical',room_point(kind,0.,4.25,3.23),2175.,850.,(1.,.78,.54))

    for name in ('Tank','Carrier','Bus'):
        component=batches.get(name)
        if not component:
            continue
        for i in range(min(component.get_instance_count(),2)):
            p=component.get_instance_transform(i,False).translation+V(OFFSET)
            point(f'{name}StreetPool{i}',(p.x-110.,p.y-205.,p.z+370.),
                  2350.,1120.,(1.,.70,.43))

def roadside(world,site,meshes,ignored):
    rng=Random(30172)
    cells=set()
    sections=Counter()
    strips=[(name,axis,line,first,last,half) for name,axis,line,first,last,half,_ in CORRIDORS]
    strips += [(f'Cross{i}','X',y,-16000,33000,750.) for i,y in enumerate((68100,90900,100000))]
    for name,axis,line,first,last,half in strips:
        for marker in range(first,last,390):
            for side in (-1,1):
                along=marker+rng.uniform(-135.,135.)
                lateral=line+side*(half+rng.uniform(55.,355.))
                x,y=(lateral,along) if axis=='Y' else (along,lateral)
                cell=round(x/190),round(y/190)
                if cell in cells or room_reserved(x,y,135.):
                    continue
                cells.add(cell)
                before=sum(c.get_instance_count() for c in site.batches.values())
                for i in range(3):
                    px,py=x+rng.uniform(-132,132),y+rng.uniform(-157,157)
                    put(world,site,meshes,rng.choice(LEAVES),px,py,rng.uniform(.75,1.65),
                        rng.randrange(360),ignored)
                for i in range(rng.randrange(2,5)):
                    px,py=x+rng.uniform(-235,235),y+rng.uniform(-235,235)
                    put(world,site,meshes,rng.choice(GRASS),px,py,rng.uniform(.83,1.7),
                        rng.randrange(360),ignored,allow_road=False)
                if rng.random()<.66:
                    px,py=x+rng.uniform(-120,120),y+rng.uniform(-180,180)
                    put(world,site,meshes,rng.choice(('PaperDrift','Bottle','Can','Bag')),
                        px,py,rng.uniform(.85,1.5),rng.randrange(360),ignored)
                if rng.random()<.56:
                    px,py=(x+side*rng.uniform(110.,465.),y) if axis=='Y' else (x,y+side*rng.uniform(110.,465.))
                    put(world,site,meshes,'Shrub',px,py,rng.uniform(.70,1.40),rng.randrange(360),
                        ignored,allow_road=False)
                if rng.random()<.21:
                    put(world,site,meshes,rng.choice(('Bin','Box','Mailbox','Newspaper','Rubble')),
                        x,y,rng.uniform(.78,1.18),rng.randrange(360),ignored,allow_road=False)
                sections[name]+=sum(c.get_instance_count() for c in site.batches.values())-before
    return sections


def spread_yards(world,site,meshes,ignored):
    rng=Random(4202)
    zones=((-4900,55200,5150,5900),(11400,62750,3900,3700),(-7000,73500,4860,4050),
           (26400,72100,4950,5650),(26100,85400,4100,3700),(36900,94000,2100,3850))
    count=0
    for cx,cy,sx,sy in zones:
        for i in range(165):
            x,y=cx+rng.uniform(-sx,sx),cy+rng.uniform(-sy,sy)
            name=rng.choices(('Shrub',*GRASS,*LEAVES,'FirA','FirB'),
                             weights=(20,7,7,7,7,7,12,12,12,4,3))[0]
            size=rng.uniform(.45,.77) if name.startswith('Fir') else rng.uniform(.85,1.55)
            count+=put(world,site,meshes,name,x,y,size,rng.randrange(360),ignored,allow_road=False)
    return count


def parking(world,site,meshes,ignored):
    proposals=json.loads((REPORT/'Plots.json').read_text())
    desired=(
        ('Tank',7730,55000),('Carrier',4280,62000),('Tank',-14100,72700),
        ('Carrier',34950,68700),('Tank',16680,73300),
        ('Bus',7600,52900),('Bus',4150,59500),('Truck',7560,63600),
        ('Wagon',17600,64000),('Van',4200,56250),('Sedan',7880,57500),
        ('Wagon',-11300,66200),('Van',32400,71900),('Sedan',16800,73800),
        ('Truck',34785,73900),('Van',34560,70200),('Wagon',4050,69800),
        ('Sedan',7530,73700),('Bus',-14100,70500),('Van',-11050,74400),
    )
    rng=Random(333)
    vehicles=[]
    for name,goal_x,goal_y in desired:
        for x,y,z,yaw,lane,_ in sorted(proposals,key=lambda p:hypot(p[0]-goal_x,p[1]-goal_y)):
            if hypot(x-goal_x,y-goal_y)>5600.:
                break
            if on_road(x,y,260.) or room_reserved(x,y,530.):
                continue
            if any(hypot(x-a,y-b)<850. for _,a,b,_,_ in vehicles):
                continue
            scale=rng.uniform(.94,1.04)
            orientation=(0. if y%2 else 180.)+90.+rng.uniform(-10.,10.)
            bounds=meshes[name].get_bounding_box()
            length=min(560.,max(bounds.max.x-bounds.min.x,bounds.max.y-bounds.min.y)*scale*.48)
            max_width=min(250.,min(bounds.max.x-bounds.min.x,bounds.max.y-bounds.min.y)*scale*.49)
            if any(room_reserved(x+dx,y+dy,85.) or on_road(x+dx,y+dy,45.)
                   for dx in (-max_width,max_width) for dy in (-length,length)):
                continue
            if not put(world,site,meshes,name,x,y,scale,orientation,ignored,collide=True,allow_road=False):
                continue
            vehicles.append((name,x,y,orientation,z))
            break
    return vehicles


def battle_sites(world,site,meshes,vehicles,ignored):
    rng=Random(92)
    count=Counter()
    for name,x,y,_,_ in vehicles:
        military=name in ('Tank','Carrier','Wagon')
        for i in range(14 if military else 10):
            px,py=x+rng.uniform(-405,405),y+rng.uniform(-510,510)
            key=rng.choice((*LEAVES,'PaperDrift','Bag','Box','Rubble','Can','Bottle'))
            count[key]+=put(world,site,meshes,key,px,py,rng.uniform(.78,1.26),
                            rng.randrange(360),ignored,allow_road=False)
        if not military:
            continue
        for idx in range(3):
            px=x+(-1 if idx%2 else 1)*rng.uniform(220.,410.)
            py=y+(-1 if idx==2 else 1)*rng.uniform(390.,620.)
            for key in ('Scorch','Cases','Rifle'):
                count[key]+=put(world,site,meshes,key,px,py,1.,rng.randrange(360),
                                ignored,roll=88. if key=='Rifle' else 0,allow_road=False)
        for side in (-1,1):
            px,py=x+side*50.,y+side*680.
            count['FightingPosition']+=put(world,site,meshes,'FightingPosition',px,py,
                rng.uniform(.90,1.12),rng.uniform(-26,26),ignored,collide=True,allow_road=False)
    return count


def clear_rooms(scene):
    removed=0
    prefixes=('HorizonFir','StreetFir','LowShrub','Grass_','Shrub','Ivy','RippedSlab','RubblePile',
              'TwistedGuardrail','RootedIvy','ClimbingIvy','Scorch','Bag','Bottle','Can','SpentCases',
              'Lichen','SmallFir','Fir')
    for key in ('RECLAIM_City','CITY_Aftermath'):
        a=scene.get(key)
        if not a:
            continue
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.get_name().startswith(prefixes):
                continue
            for i in range(c.get_instance_count()-1,-1,-1):
                p=c.get_instance_transform(i,True).translation
                if room_reserved(p.x+OFFSET[0],p.y+OFFSET[1],90.):
                    c.modify()
                    assert c.remove_instance(i)
                    removed+=1
    return removed


def open_wreck_sightlines(scene, city):
    military={'Tank','Carrier'}
    points=[]
    for c in city.get_components_by_class(unreal.InstancedStaticMeshComponent):
        if c.get_name() in military:
            points.extend(c.get_instance_transform(i,True).translation for i in range(c.get_instance_count()))
    avenues=(5850.,15500.,-12600.,33400.)
    removed=0
    for actor in (*scene.values(),city):
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if not mesh or not mesh.get_name().startswith('SM_Fir_'):
                continue
            for i in range(c.get_instance_count()-1,-1,-1):
                p=c.get_instance_transform(i,True).translation
                for wreck in points:
                    near=hypot(p.x-wreck.x,p.y-wreck.y)<420.
                    avenue=min(avenues,key=lambda x:abs(x-(wreck.x+OFFSET[0]))) - OFFSET[0]
                    view=V((avenue-wreck.x,-650.,0.))
                    t=((p.x-wreck.x)*view.x+(p.y-wreck.y)*view.y)/(view.x**2+view.y**2)
                    in_view=.0<=t<=1.05 and hypot(p.x-wreck.x-t*view.x,p.y-wreck.y-t*view.y)<210.
                    if near or in_view:
                        c.modify()
                        assert c.remove_instance(i)
                        removed+=1
                        break
    return removed

def install():
    world=levels.load_map(LEVEL)
    assert world
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    backup=saved/'Backups'/'CityStreetLife'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    ignored=(scene[LABEL],) if LABEL in scene else ()
    meshes=get_assets(world)
    bp=asset(DRESSING)
    site=Site(bp)
    roof_and_signs(bp,site,meshes)
    strip=roadside(world,site,meshes,ignored)
    yard=spread_yards(world,site,meshes,ignored)
    vehicles=parking(world,site,meshes,ignored)
    battles=battle_sites(world,site,meshes,vehicles,ignored)
    practical_lights(bp,site.batches)
    counts={key:c.get_instance_count() for key,c in site.batches.items()}
    assert sum(strip.values())>1400 and yard>130, (strip,yard)
    assert sum(key in ('Tank','Carrier') for key,*_ in vehicles)>=4 and battles['Rifle']>=9,(vehicles,battles)
    for key,c in site.batches.items():
        c.set_editor_property('can_ever_affect_navigation',False)
        far=42000 if key.endswith(('Shell','Details','Interior')) or key in MAJOR else 17500
        if key.startswith('Fir'):
            far=42000
        if key in (*LEAVES,*GRASS,'PaperDrift','Cases','Bottle','Can'):
            far=11200
        c.set_cull_distances(0,far)
        if key in (*LEAVES,*GRASS,'PaperDrift','Cases','Scorch','Bottle','Can'):
            c.set_cast_shadow(False)
    compile_bp(bp)
    save(bp)
    removed=clear_rooms(scene)
    if LABEL in scene:
        assert actors.destroy_actor(scene[LABEL])
    a=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    assert a
    a.set_actor_label(LABEL)
    a.set_folder_path('SURFACE/Street Life')
    old_scene={key:value for key,value in scene.items() if key!=LABEL}
    cleared_views=open_wreck_sightlines(old_scene,a)
    counts={c.get_name():c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    final=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL)
    actual={c.get_name():c.get_instance_count() for c in final.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert all(actual.get(name)==n for name,n in counts.items()),actual
    report=dict(saved=True, counts=counts, districts=dict(strip), yards=yard, vehicles=vehicles,
                battles=dict(battles), rooms=ROOMS, removed_from_rooms=removed,
                opened_wreck_views=cleared_views, backup=str(backup))
    (REPORT/'Installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('City street life saved: '+str(sum(counts.values()))+' placements')


if __name__=='__main__':
    install()


