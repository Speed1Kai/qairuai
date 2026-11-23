"""Expand the streamed city with playable streets, reclaimed facades and a forest basin."""
from datetime import datetime
import json
import math
import random
import shutil
import sys

import unreal
from Build_RuinedUrbanCampus import (
    A, B, CYLINDER, GROUND, LEVEL, MAT, OFFSET, Site, V, actors,
    compile_bp, components, content, levels, local, save, saved, tools,
)
from Place_CityExpansion import DISTRICTS, ROOT as DISTRICT_ASSETS, replace_bp

ROOT='/Game/Environment/CityReclaim'
TOWER_KINDS=('Spire','Gate','Crown')
ENV='/Game/Surface/BP_SurfaceEnvironment'
GRADE='/Game/Surface/BP_SciFi_CityGrade'
SOURCE=content.parent/'SourceAssets/CityReclaim'
sys.path.insert(0,str(SOURCE))
from Reclaim_Terrain import smooth, terrain_z

M=unreal.MaterialEditingLibrary
RNG=random.Random(745)
TOWERS=(
    ('Crown', -11600, 30300, 0.8, 7), ('Spire', -17800, 41700, 0.76, -8), ('Gate', -9300, 48100, 0.64, 12),
    ('Crown', 19400, 29500, 0.83, 16), ('Gate', 22750, 38100, 0.78, -12), ('Spire', 23250, 47800, 0.89, 10),
    ('Spire', -16800, 55800, 1.03, -7), ('Crown', -2300, 65200, 0.72, 8), ('Gate', 1020, 62100, 0.79, 0),
    ('Spire', 11100, 64500, 0.9, 6), ('Crown', 20700, 62700, 0.87, -13), ('Gate', 29200, 63800, 0.79, 10),
    ('Crown', -22700, 81300, 0.84, -5), ('Gate', -8930, 73400, 0.88, -9), ('Crown', -1510, 72200, 0.53, 16),
    ('Crown', 11700, 72600, 0.72, -11), ('Spire', 20800, 73500, 0.95, 10), ('Crown', 28500, 74800, 0.72, 7),
    ('Gate', -16800, 84200, 1.03, 12), ('Spire', -6500, 84200, 0.88, 0), ('Gate', 1300, 83700, 0.74, -14),
    ('Gate', 10600, 84600, 0.84, 12), ('Crown', 20200, 86400, 1.0, -14), ('Spire', 28700, 86200, 0.95, -6),
    ('Crown', -18500, 95500, 0.72, 18), ('Gate', -5200, 96900, 0.68, -11), ('Spire', 11900, 95900, 0.8, 8),
    ('Crown', 26500, 96900, 0.83, 11),
)
ROADS=(
    (5850,78200,1780,44100),(5850,102750,1330,5000),
    (-12600,77000,1500,39000),(15500,77000,1500,39000),(33400,78300,1340,36200),
    (7200,58950,54000,1400),(6700,68100,53500,1500),(6600,78300,54000,1480),
    (7000,90900,54000,1530),(7600,100000,53200,1310),
    (-12350,50600,1440,15500),(15500,55400,1410,5800),
)
FOCUS=((5850,78000),(5850,100000),(-12600,78300),(15500,90900),(33400,78300))
NEAR_SHELLS=((3524,25224,1752,3448),(8493,25365,2385,3729),(3156,29046,2489,3293),(8452,29050,2304,2900))


def load(path):
    obj=A.load_asset(path)
    assert obj,path
    return obj


def native_asset(name,cls,factory):
    path=ROOT+'/'+name
    return load(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,cls,factory)


def material(key,color,metal=0.,rough=.9,emission=False,two_sided=False,field=None):
    name='M_Reclaim_'+key
    if A.does_asset_exist(ROOT+'/'+name):
        return load(ROOT+'/'+name)
    m=native_asset(name,unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property('two_sided',two_sided)
    tint=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-430,60)
    tint.set_editor_property('constant',unreal.LinearColor(*color,1.))
    rgb=tint
    if field:
        rgb=M.create_material_expression(m,unreal.MaterialExpressionCustom,-150,50)
        rgb.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        p=M.create_material_expression(m,unreal.MaterialExpressionWorldPosition,-440,-170)
        normal=M.create_material_expression(m,unreal.MaterialExpressionVertexNormalWS,-440,-50)
        inputs=[]
        for k in ('P','N','Tint'):
            entry=unreal.CustomInput()
            entry.set_editor_property('input_name',k)
            inputs.append(entry)
        rgb.set_editor_property('inputs',inputs)
        rgb.set_editor_property('code','''
struct Noise {
float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float sample(float2 p){
    float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
    return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
}; Noise n;
''' + field)
        for node,k in ((p,'P'),(normal,'N'),(tint,'Tint')):
            assert M.connect_material_expressions(node,'',rgb,k)
    if emission:
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    assert M.connect_material_property(rgb,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if emission else unreal.MaterialProperty.MP_BASE_COLOR)
    if not emission:
        for value,prop in ((metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)):
            n=M.create_material_expression(m,unreal.MaterialExpressionConstant,10,230)
            n.set_editor_property('r',value)
            assert M.connect_material_property(n,'',prop)
    M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(m)
    save(m)
    return m


def build_materials():
    soil=material('Soil',(.073,.108,.041),field='''
float a=n.sample(P.xy*.00054), b=n.sample(P.xy*.0041), c=n.sample(P.xy*.11);
float3 base=Tint*(.45+a*.91+b*.29+c*.16);
float3 rock=float3(.17,.155,.126)*(.64+b*.52+c*.26);
float t=saturate((.86-abs(N.z))*2.1 + .26*smoothstep(.62,.83,b));
return lerp(base,rock,t);
''')
    concrete=material('Concrete',(.17,.184,.162),field='''
float2 p=float2(P.x+P.y*.91,P.z+P.y*.11);
float k=n.sample(p*.016)*.5+n.sample(p*float2(.039,.004))*.33+n.sample(p*.12)*.17;
float algae=smoothstep(.52,.76,k);
return lerp(Tint*(.55+k*.65),float3(.058,.087,.027),algae*.78);
''')
    moss=material('Moss',(.090,.145,.030),two_sided=True,field='''
float2 p=float2(P.x+P.y*.72,P.z+P.y*.18);
float d=n.sample(p*.055)*.63+n.sample(p*.31)*.37;
return lerp(float3(.032,.057,.012),Tint,d);
''')
    return dict(Soil=soil,Concrete=concrete,Moss=moss,
        Armor=material('Armor',(.119,.151,.161),.69,.47),
        Frame=material('Frame',(.052,.067,.071),.53,.66),
        Glass=material('Glass',(.026,.069,.091),.59,.26),
        Scorch=material('Scorch',(.060,.036,.023),rough=.96,field='''
float2 p=float2(P.x+P.y*.67,P.z+P.y*.23);
float ash=n.sample(p*.021)*.58+n.sample(p*.11)*.30+n.sample(p*.43)*.12;
return lerp(float3(.012,.012,.010),Tint*(.9+ash*.92),smoothstep(.24,.84,ash));
'''),
        Interior=material('Interior',(.025,.027,.026),rough=.97,two_sided=True),
        Shards=material('Shards',(.091,.164,.196),.35,.36,two_sided=True),
        Cyan=material('Cyan',(.033,1.10,1.55),emission=True),
        Amber=material('Amber',(1.9,.53,.075),emission=True),
        Leaf=material('Leaf',(.065,.145,.028),two_sided=True),
        LeafPale=material('LeafPale',(.118,.210,.046),two_sided=True),
        Stem=material('Stem',(.071,.051,.023)))


def import_models(reimport_basin=False, *, only_towers=False):
    mats=build_materials()
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    models={}
    for kind in TOWER_KINDS if only_towers else ('Basin',*TOWER_KINDS,'IvyCurtain','IvyFall','Lichen','Shrub'):
        name='SM_Reclaim_'+kind
        path=ROOT+'/'+name
        if only_towers or not A.does_asset_exist(path) or (kind=='Basin' and reimport_basin):
            options=unreal.FbxImportUI()
            for k,v in dict(automated_import_should_detect_type=False,
                    mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                    import_materials=False,import_textures=False).items():
                options.set_editor_property(k,v)
            options.static_mesh_import_data.set_editor_property('combine_meshes',True)
            options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
            task=unreal.AssetImportTask()
            for k,v in dict(filename=str(SOURCE/(name+'.fbx')),destination_path=ROOT,
                    destination_name=name,automated=True,save=False,replace_existing=True,options=options).items():
                task.set_editor_property(k,v)
            tools.import_asset_tasks([task])
            assert task.get_objects(),name
        mesh=load(path)
        for i,slot in enumerate(mesh.static_materials):
            key=next(k for k in mats if str(slot.material_slot_name).lower().startswith(k.lower()))
            mesh.set_material(i,mats[key])
        if kind in ('Basin','Spire','Gate','Crown'):
            mesh.get_editor_property('body_setup').set_editor_property(
                'collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        b=mesh.get_bounding_box()
        if kind=='Basin':
            assert b.max.x-b.min.x>265000 and b.max.y-b.min.y>195000,str(b)
        if kind in ('Spire','Gate','Crown'):
            assert b.max.z>12500 and b.min.z>-.5,(name,str(b))
            if only_towers:
                slots={str(slot.material_slot_name) for slot in mesh.static_materials}
                assert {'Scorch','Interior'}.issubset(slots),(name,slots)
        save(mesh)
        models[kind]=mesh
    return models


def style_batch(site,key,cull,shadow):
    c=site.batches[key]
    c.set_editor_property('can_ever_affect_navigation',False)
    c.set_cull_distances(*cull)
    c.set_cast_shadow(shadow)


def place_ground(site,models):
    b=models['Basin'].get_bounding_box()
    assert b.max.y>170000,str(b)
    site.mesh('CityBasin',models['Basin'],0,0,GROUND,collide=True)
    style_batch(site,'CityBasin',(0,0),True)
    MAT['reclaim_asphalt']=load('/Game/Surface/RuinedCampus/Siege/M_Siege_FracturedAsphalt')
    for i,(x,y,w,d) in enumerate(ROADS):
        site.box('reclaim_asphalt',x,y,GROUND+2+i*.055,w,d,4.,collide=True)
        along=d>w
        length=d if along else w
        for shift in range(-int(length*.5)+380,int(length*.5)-250,620):
            if RNG.random()<.14:
                continue
            px,py=(x,y+shift) if along else (x+shift,y)
            site.box('stripe',px,py,GROUND+5.5,12 if along else 133,133 if along else 12,1.1)
        if not along:
            continue
        for side in (-1,1):
            site.box('concrete',x+side*(w/2+170),y,GROUND+5,335,d-340,10)
    for key in ('Box_reclaim_asphalt_Solid','Box_concrete','Box_stripe'):
        style_batch(site,key,(0,90000),True)


def place_towers(site,models):
    for key,x,y,scale,yaw in TOWERS:
        site.mesh('Skyline_'+key,models[key],x,y,GROUND-8,(scale,scale,scale),yaw=yaw,collide=True)
    for key in ('Spire','Gate','Crown'):
        style_batch(site,'Skyline_'+key,(0,0),True)


def take_road(x,y,padding=0):
    return any(abs(x-u)<w*.5+padding and abs(y-v)<d*.5+padding for u,v,w,d in ROADS)


def in_tower_plot(x,y,padding=200):
    return any(abs(x-u)<scale*2600+padding and abs(y-v)<scale*2040+padding for _,u,v,scale,_ in TOWERS)


def trees_and_streets(site,models):
    firroot='/Game/Surface/RiverForest/SM_Fir_'
    firs={k:load(firroot+k) for k in ('A','B','C','Distance')}
    dry={k:load('/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_'+k) for k in 'ABCD'}
    rock=load('/Game/Surface/Meshes/SM_RubbleCluster')
    lamp=load('/Game/Surface/Meshes/SM_ConcreteBarrier')
    for y0 in range(-28000,172000,2100):
        for x0 in range(-126000,141000,2100):
            x=x0+RNG.uniform(-840,840)
            y=y0+RNG.uniform(-840,840)
            lateral=max(-28300-x,x-39100,0)
            northern=max(y-101000,0)
            if max(lateral,northern)<600 or abs(x-5850)<46000 and y<22400:
                continue
            south=21750-54500*smooth((abs(x-5850)-32500)/22200)
            if y<south+280:
                continue
            cluster=math.sin(x/4200+y/3900)+.66*math.cos(x/2150-y/1950)
            if RNG.random()>.62+.15*cluster or take_road(x,y,155) or in_tower_plot(x,y,270):
                continue
            s=RNG.uniform(.54,1.17)
            z=GROUND+terrain_z(x,y)-24
            site.mesh('HorizonFir',firs['Distance'],x,y,z,(s,s,s*RNG.uniform(.91,1.12)),yaw=RNG.randrange(360))
    for x0,x1,y0,y1 in ((-55400,-31000,24500,122000),(40300,62000,24500,122000),
                         (-31000,40300,103500,125000)):
        for x in range(x0,x1,1180):
            for y in range(y0,y1,1180):
                if RNG.random()<.22:
                    continue
                px,py=x+RNG.uniform(-405,405),y+RNG.uniform(-405,405)
                if take_road(px,py,240) or in_tower_plot(px,py,260):
                    continue
                s=RNG.uniform(.60,1.19)
                site.mesh('HorizonFir',firs['Distance'],px,py,GROUND+terrain_z(px,py)-20,
                          (s,s,s),yaw=RNG.randrange(360))
    style_batch(site,'HorizonFir',(0,0),False)

    # Add groves to plazas and sidewalks, leaving travel lanes and junctions open.
    plots=[(-9500,61400),(-16300,65000),(7800,65750),(18600,65350),(25200,66600),
           (-18200,76700),(-3900,76700),(8650,76600),(21400,76800),(27800,80100),
           (-21400,89900),(-2800,88900),(8730,88300),(22800,89800),
           (-18600,100400),(16000,102200),(27900,104500)]
    plots+= [(5850+s*d,y) for s in (-1,1) for d in (860,1260)
             for y in range(23600,57000,1250)]
    plots +=[(5850+s*1430,y) for s in (-1,1) for y in range(59900,98700,1600)]
    for i,(px,py) in enumerate(plots):
        close=py<57500
        for j in range(5 if close else 7):
            x,y=px+RNG.uniform(-315,315),py+RNG.uniform(-390,390)
            if ((abs(x-5850)<795 and close) or take_road(x,y,125) or in_tower_plot(x,y,40)):
                continue
            s=RNG.uniform(.32,.70) if close else RNG.uniform(.47,.89)
            kind='ABC'[(i+j)%3]
            site.mesh('StreetFir_'+kind,firs[kind],x,y,GROUND+15,(s,s,s),yaw=RNG.randrange(360))
        for j in range(21):
            x,y=px+RNG.uniform(-460,460),py+RNG.uniform(-485,485)
            if (abs(x-5850)<735 and close) or take_road(x,y,15):
                continue
            if j%5==0:
                s=RNG.uniform(.51,1.23)
                site.mesh('LowShrub',models['Shrub'],x,y,GROUND+17,(s,s,s),yaw=RNG.randrange(360))
            else:
                k=RNG.choice('AABBCD')
                s=RNG.uniform(.67,1.44)
                site.mesh('Grass_'+k,dry[k],x,y,GROUND+13,(s,s,s),yaw=RNG.randrange(360))
        if i<17 and not take_road(px,py,250):
            s=RNG.uniform(.61,1.10)
            site.mesh('BrokenUrbanConcrete',rock,px,py,GROUND+9,(s,s,s),yaw=RNG.randrange(360))
            site.mesh('RustedTrafficBlock',lamp,px+180,py-260,GROUND+4,(.74,.74,.74),yaw=RNG.randrange(360))
    for key in site.batches:
        if key.startswith('StreetFir_'):
            style_batch(site,key,(29000,57500),True)
        elif key.startswith('Grass_') or key=='LowShrub':
            style_batch(site,key,(8200,15700),False)
        elif key in ('BrokenUrbanConcrete','RustedTrafficBlock'):
            style_batch(site,key,(0,34000),True)


def wall_hit(world,a,b):
    h=unreal.SystemLibrary.capsule_trace_single_by_profile(world,local(*a),local(*b),4.,6.,'Pawn',
                                                           False,[],unreal.DrawDebugTrace.NONE,False)
    if not h:
        return None
    parts=h.to_tuple()
    actor=parts[9]
    if not actor or not actor.get_actor_label().startswith(('CITY_Shell_','CITY_FirstDowntownBlock','DISTRICT_Expansion')):
        return None
    p,n=parts[5],parts[7]
    if abs(n.z)>.38:
        return None
    return (p.x+OFFSET[0],p.y+OFFSET[1],p.z+GROUND),n


def cover_facades(site,models,world):
    bounds=list(NEAR_SHELLS)
    for _,kind,x,y,yaw in DISTRICTS:
        b=load(DISTRICT_ASSETS+'/SM_District_'+kind).get_bounding_box()
        span=b.max-b.min
        w,d=(span.y,span.x) if abs(round(yaw/90))%2 else (span.x,span.y)
        bounds.append((x,y,w,d))
    for x,y,w,d in bounds:
        for nx,ny in ((0,-1),(0,1),(-1,0),(1,0)):
            normal_span=(d if ny else w)*.5
            tangent_span=(w if ny else d)*.5
            for i in range(10):
                u=RNG.uniform(-.84,.84)*tangent_span
                z=GROUND+RNG.uniform(285.,1330.) if i else GROUND+160.
                tx=x-ny*u
                ty=y+nx*u
                result=wall_hit(world,(tx+nx*(normal_span+380),ty+ny*(normal_span+380),z),(tx,ty,z))
                if result:
                    (px,py,pz),n=result
                else:
                    # Exterior walls have a regular footprint even when a decorative
                    # window module cannot be queried in the editor physics scene.
                    px,py,pz=tx+nx*(normal_span-24),ty+ny*(normal_span-24),z
                    n=V((nx,ny,0))
                yaw=math.degrees(math.atan2(n.y,n.x))-90.
                s=RNG.uniform(.48,.98)
                if i%3!=0 and pz>GROUND+290:
                    k='IvyCurtain' if i%2 else 'IvyFall'
                    site.mesh(k,models[k],px+n.x*13,py+n.y*13,pz,(s,.85,min(s,(pz-GROUND)/530.)),yaw=yaw)
                site.mesh('Lichen',models['Lichen'],px+n.x*2.5,py+n.y*2.5,pz+55,
                          (s*1.26,1.,s*1.35),yaw=yaw)
    for kind,x,y,s,yaw in TOWERS:
        angle=math.radians(yaw)
        # The podium dimensions match the tower source. Ivy drapes from its ledge.
        podium={'Spire':(20.36,15.18),'Gate':(18.36,13.66),'Crown':(24.66,16.19)}[kind]
        for side in (-1,1):
            for i in range(4):
                dx=(i-1.5)*.47*podium[0]*s
                dy=side*(podium[1]*100*s+10)
                px=x+dx*100*math.cos(angle)-dy*math.sin(angle)
                py=y+dx*100*math.sin(angle)+dy*math.cos(angle)
                z=GROUND+450*s
                q=RNG.uniform(.57,1.03)
                a=yaw+(0 if side>0 else 180)
                site.mesh('IvyCurtain',models['IvyCurtain'],px,py,z,(q,1.,min(q,s*.81)),yaw=a)
                site.mesh('Lichen',models['Lichen'],px,py,z-65,(q,1.,q),yaw=a)
    for key in ('IvyCurtain','IvyFall','Lichen'):
        style_batch(site,key,(11000,28500),False)


def props(site):
    for i,(x,y,w,d) in enumerate(ROADS):
        if d<w:
            continue
        for yy in range(int(y-d/2)+600,int(y+d/2)-300,2600):
            if yy<57300 or any(abs(yy-q)<850 for q in (58950,68100,78300,90900,100000)):
                continue
            side=1 if i%2==0 else -1
            px=x+side*(w*.5+230)
            if in_tower_plot(px,yy,0):
                continue
            site.box('steel',px,yy,GROUND+190,16,16,375)
            site.box('steel',px-side*76,yy,GROUND+376,176,27,27)
            site.box('amber',px-side*134,yy,GROUND+363,46,30,4)
            if i%2==0:
                site.box('concrete',px+side*70,yy+310,GROUND+29,137,72,57)
    for name,x,y,yaw in (('SM_FP_AbandonedSedan',4850,68550,90),
                       ('SM_FP_BurnedServiceVan',14550,77880,18),
                       ('SM_FP_BurnedCargoTruck',-13380,87900,91),
                       ('SM_FP_AbandonedSedan',7350,91850,-85),
                       ('SM_FP_SecurityWagon',17800,91430,-28),
                       ('SM_FP_AbandonedSedan',-4340,68720,17),
                       ('SM_FP_BurnedBus',6850,96830,-90)):
        site.mesh('Wreck_'+name,load('/Game/Environment/Vehicles/'+name),x,y,GROUND+11,yaw=yaw,collide=True)


def configure_city_fog(fog):
    # The city grade volume is centered high above the streets.
    fog.set_editor_property('relative_location',V((0.,0.,-40850.)))
    fog.set_editor_property('enable_volumetric_fog',True)
    fog.set_fog_density(.19)
    fog.set_fog_height_falloff(.095)
    fog.set_second_fog_density(.044)
    fog.set_second_fog_height_falloff(.30)
    fog.set_second_fog_height_offset(-100.)
    fog.set_fog_max_opacity(.98)
    fog.set_start_distance(350.)
    fog.set_fog_inscattering_color(unreal.LinearColor(.15,.19,.22,1.))
    fog.set_volumetric_fog_albedo(unreal.Color(172,186,198,255))
    fog.set_volumetric_fog_emissive(unreal.LinearColor(.055,.068,.083,1.))
    fog.set_volumetric_fog_scattering_distribution(.27)
    fog.set_volumetric_fog_extinction_scale(1.)
    fog.set_volumetric_fog_distance(12000.)
    fog.set_volumetric_fog_start_distance(260.)
    fog.set_volumetric_fog_near_fade_in_distance(750.)
    fog.set_visibility(False)


def remove_old_haze_and_tower(scene):
    env=load(ENV)
    rows={name:c for _,c,name in components(env)}
    tower=rows['SM_ArchitectTower']
    hidden=tower.get_instance_count()
    tower.clear_instances()
    smoke=rows['SmokePlumes']
    plumes=smoke.get_instance_count()
    smoke.clear_instances()
    compile_bp(env)
    save(env)
    replace_bp(scene['SURF_Environment'],env)
    grade=load(GRADE)
    for _,c,name in components(grade):
        if name=='CityFog':
            configure_city_fog(c)
        elif name=='CityBounds':
            c.set_box_extent(V((145000,81000,55000)))
    compile_bp(grade)
    save(grade)
    label='CITY_Night_Grade'
    replace_bp(scene[label],grade)
    current=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==label)
    assert current.set_actor_location(local(5850,99000,43000),False,True)
    for label,actor in scene.items():
        if isinstance(actor,unreal.ExponentialHeightFog):
            c=actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
            c.set_editor_property('enable_volumetric_fog',False)
            c.set_fog_density(0.)
            c.set_visibility(False)
    return hidden,plumes


def build_city_assets(reimport_basin=False):
    RNG.seed(745)
    models=import_models(reimport_basin)
    world=levels.load_map(LEVEL)
    assert world
    factory=unreal.BlueprintFactory()
    factory.set_editor_property('parent_class',unreal.Actor)
    bp=native_asset('BP_ReclaimedCity',unreal.Blueprint,factory)
    site=Site(bp)
    place_ground(site,models)
    place_towers(site,models)
    trees_and_streets(site,models)
    cover_facades(site,models,world)
    props(site)
    compile_bp(bp)
    save(bp)
    return bp


def main():
    backup=saved/'Backups/CityReclaim'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for package,ext in ((LEVEL,'.umap'),(ENV,'.uasset'),(GRADE,'.uasset')):
        shutil.copy2(content/(package.removeprefix('/Game/')+ext),backup)
    bp=load(ROOT+'/BP_ReclaimedCity')
    world=levels.load_map(LEVEL)
    assert world
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    towers,smoke=remove_old_haze_and_tower(scene)
    old=scene.get('RECLAIM_City')
    if old:
        assert actors.destroy_actor(old)
    fresh=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    fresh.set_actor_label('RECLAIM_City')
    fresh.set_folder_path('SURFACE/Reclaimed City')
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    assert 'DISTRICT_Expansion' in scene and 'SIEGE_Battlefield' in scene
    counts={c.get_name():c.get_instance_count() for c in scene['RECLAIM_City'].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert sum(n for name,n in counts.items() if name.startswith('Skyline_'))==len(TOWERS)
    assert counts['HorizonFir']>1800 and counts['IvyCurtain']>120,counts
    (saved/'city_reclaim.json').write_text(json.dumps(dict(saved=True,backup=str(backup),instances=counts,
                      old_tower_hidden=towers,smoke_cards_removed=smoke),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()


