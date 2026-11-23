"""Replace the campus bypass with a forested river crossing and heavier ruins."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math
import random
import shutil

import unreal
from Build_RuinedUrbanCampus import (
    A, B, MAT, LEVEL, MAIN, OFFSET, Site, V, actors, compile_bp, components,
    content, levels, local, save, saved, tools,
)
from RiverForest_Geometry import (
    BRIDGE_Y, FAR, GROUND, MAX_X, MIN_X, NEAR, WATER_Z, bounds, generate, hillside,
)

ROOT = '/Game/Surface/RiverForest'
PROJECT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = PROJECT/'SourceAssets/RiverForest'
PLAN = '/Game/Surface/ReferencePlan/BP_ReferenceCampus'
ENV = '/Game/Surface/BP_SurfaceEnvironment'
YARD = '/Game/Surface/RuinedCampus/BP_RuinedUrbanCampus'
M = unreal.MaterialEditingLibrary
COLOR = unreal.LinearColor
rng = random.Random(3813)


def load(path):
    obj = A.load_asset(path)
    assert obj, path
    return obj


def import_task(file, options=None):
    task = unreal.AssetImportTask()
    for key,value in dict(filename=str(file), destination_path=ROOT, automated=True, save=False).items():
        task.set_editor_property(key,value)
    if options:
        task.set_editor_property('options', options)
    tools.import_asset_tasks([task])
    return load(ROOT+'/'+file.stem)


def texture(name, ext, srgb=True):
    path = ROOT+'/'+name
    obj = load(path) if A.does_asset_exist(path) else import_task(SOURCE/(name+ext))
    obj.set_editor_property('srgb', srgb)
    obj.set_editor_property('max_texture_size', 1024)
    save(obj)
    return obj


def material(name):
    path = ROOT+'/'+name
    obj = load(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(obj)
    return obj


def expr(mat, kind, **props):
    n = M.create_material_expression(mat,getattr(unreal,'MaterialExpression'+kind))
    for key,value in props.items():
        n.set_editor_property(key,value)
    return n


def connect(source, target, slot, pin=''):
    assert M.connect_material_expressions(source,pin,target,slot), slot


def output(source, name, pin=''):
    assert M.connect_material_property(source,pin,getattr(unreal.MaterialProperty,'MP_'+name)), name


def custom(mat, code, inputs, out=unreal.CustomMaterialOutputType.CMOT_FLOAT3):
    slots = []
    for name in inputs:
        slot = unreal.CustomInput()
        slot.set_editor_property('input_name',name)
        slots.append(slot)
    n=expr(mat,'Custom',code=code,inputs=slots,output_type=out)
    for name,value in inputs.items():
        connect(value,n,name)
    return n


def constant(mat, key, value):
    output(expr(mat,'Constant',r=value),key)


def persist(mat, instanced=True):
    if instanced:
        M.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(mat)
    save(mat)
    return mat


def make_materials():
    bark = material('M_FirBark')
    s=expr(bark,'TextureSample',texture=texture('T_FirBark','.jpg'))
    output(s,'BASE_COLOR','RGB')
    constant(bark,'ROUGHNESS',.92)

    needles=material('M_FirNeedles')
    needles.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
    needles.set_editor_property('two_sided',True)
    needles.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    s=expr(needles,'TextureSample',texture=texture('T_FirNeedles','.jpg'))
    mask=expr(needles,'TextureSample',texture=texture('T_FirNeedlesMask','.png',False),
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    shade=custom(needles,'return max(C.rgb, float3(0.018,0.031,0.009)) * lerp(0.75,1.26,R);',
                 {'C':s,'R':expr(needles,'PerInstanceRandom')})
    output(shade,'BASE_COLOR')
    output(shade,'SUBSURFACE_COLOR')
    output(mask,'OPACITY_MASK','R')
    constant(needles,'ROUGHNESS',.88)

    terrain=material('M_ForestFloor')
    rough=material('M_RiverCliff')
    noise = """
float p = sin(P.x*0.0037 + sin(P.y*0.0052)*1.5) * cos(P.y*0.0043+P.x*0.0033);
float grains = sin(P.x*0.071 + P.z*0.113)*sin(P.y*0.083-P.z*0.067);
float layers = sin(P.z*0.041+sin(P.x*0.006)*1.7+sin(P.y*0.007))*0.18;
float slope = saturate(abs(N.z));
float3 slate = lerp(float3(0.065,0.073,0.071),float3(0.23,0.223,0.202),saturate(0.5+0.28*p+0.11*grains+layers));
float3 moss = lerp(float3(0.026,0.043,0.013),float3(0.115,0.143,0.052),saturate(0.56+0.32*p+0.12*grains));
return lerp(slate, moss, mix);
"""
    for obj, mixture in ((terrain,'smoothstep(0.57, 0.95, slope)*0.96'), (rough,'smoothstep(0.65, 0.99, slope)*saturate(0.48+0.55*p)')):
        n=custom(obj,noise.replace('mix',mixture),
                 {'P':expr(obj,'WorldPosition'),'N':expr(obj,'VertexNormalWS')})
        output(n,'BASE_COLOR')
        constant(obj,'ROUGHNESS',.92)

    water=material('M_FlowingRiver')
    uv=expr(water,'TextureCoordinate')
    t=expr(water,'Time')
    cam=expr(water,'CameraVectorWS')
    ripple=custom(water,'''
float x=UV.x*1820.0-T*2.5; float y=UV.y*78.0;
float a=sin(x+y*.71)*.088+sin(x*1.73-y*.93)*.055;
float b=cos(y*1.28+x*.65)*.102+cos(x*.89-y*.42)*.036;
return normalize(float3(a,b,1.0));''',{'UV':uv,'T':t})
    output(ripple,'NORMAL')
    surface=custom(water,'''
float edge=min(UV.y,1.0-UV.y);
float flow=sin(UV.x*357.0-T*1.72+cos(UV.y*40.0))*.5+.5;
float fine=sin(UV.x*1310.0-T*3.7+UV.y*74.0)*.5+.5;
float foam=(1.0-smoothstep(.027,.113,edge))*smoothstep(.51,.98,flow*.57+fine*.43);
float facing=pow(1.0-saturate(abs(V.z)),4.0);
float3 base=lerp(float3(.024,.077,.088),float3(.125,.225,.253),facing);
return lerp(base*(.9+.16*flow),float3(.47,.58,.57),foam*.66);''',{'UV':uv,'T':t,'V':cam})
    output(surface,'BASE_COLOR')
    constant(water,'ROUGHNESS',.21)
    constant(water,'SPECULAR',.73)
    constant(water,'METALLIC',.10)
    water.set_editor_property('two_sided',True)

    sky=material('M_RiverOvercastSky')
    sky.set_editor_property('two_sided',True)
    sky.set_editor_property('is_sky',True)
    sky.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    cloud=custom(sky,'''
float3 d=normalize(-C);
float h=saturate(d.z);
float2 p=d.xy/(.33+abs(d.z));
float cloud=sin(p.x*3.8+p.y*2.3)+.48*cos(p.x*7.0-p.y*9.0)+.16*sin(dot(p,float2(17,13)));
float factor=smoothstep(-1.25,1.02,cloud);
float3 base=lerp(float3(.34,.40,.44),float3(.18,.245,.31),pow(h,.6));
float sun=pow(saturate(dot(d,normalize(float3(-.53,-.28,.8)))),24.0);
return base*lerp(.59,1.36,factor)+sun*float3(.32,.30,.25);''',{'C':expr(sky,'CameraVectorWS')})
    output(cloud,'EMISSIVE_COLOR')
    return {k:persist(v,k!='sky') for k,v in dict(
        bark=bark,needles=needles,forest=terrain,rock=rough,water=water,sky=sky).items()}


def meshes(mats):
    generated=saved/'RiverForestSource'
    names=generate(generated)
    options=unreal.FbxImportUI()
    for k,v in dict(import_mesh=True,import_materials=False,import_textures=False,
                    automated_import_should_detect_type=False,
                    mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(k,v)
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    result={}
    for name in names:
        path=ROOT+'/'+name
        obj=load(path) if A.does_asset_exist(path) else import_task(generated/(name+'.obj'),options)
        for i,slot in enumerate(obj.static_materials):
            material=str(slot.material_slot_name)
            obj.set_material(i, (mats|MAT)[material])
        if name.startswith(('SM_ForestSlope','SM_RiverGorge','SM_ImpactSlab','SM_Cliff')):
            obj.get_editor_property('body_setup').set_editor_property(
                'collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(obj)
        result[name]=obj
    return result


def template_map(bp):
    return {name:c for _,c,name in components(bp) if isinstance(c,unreal.InstancedStaticMeshComponent)}


def world_xy(t):
    p=t.translation
    return p.x+OFFSET[0],p.y+OFFSET[1]


def trim_old_ground(plan, env, yard):
    counts={}
    for bp, keys in ((plan,('RestoredCheckpointGround','RestoredCheckpointRoad')),
                     (env,('Boxes_M_Dust_Block',))):
        cs=template_map(bp)
        for name in keys:
            c=cs[name]
            c.modify()
            if bp==plan:
                counts[name]=c.get_instance_count()
                c.clear_instances()
                continue
            for i in range(c.get_instance_count()-1,-1,-1):
                t=c.get_instance_transform(i,False)
                # This batch belongs to SURF_Environment at world (5850,23500,2150).
                y=t.translation.y+23500
                s=t.scale3d
                low,high=y-s.y*50,y+s.y*50
                if low>=NEAR-400 or high<=NEAR-400:
                    continue
                c.remove_instance(i)
                stop=NEAR-400
                q=t.translation
                c.add_instance(unreal.Transform(location=V((q.x,(low+stop)*.5-23500,q.z)),
                                                scale=V((s.x,(stop-low)/100,s.z))),False)
                counts['old_subgrade_cut']=1
    for name,c in template_map(yard).items():
        c.modify()
        if name.startswith('UrbanBlock_') or name=='Box_soil_Solid':
            counts[name]=c.get_instance_count()
            c.clear_instances()
            continue
        for i in range(c.get_instance_count()-1,-1,-1):
            t=c.get_instance_transform(i,False)
            x,y=world_xy(t)
            if ((name=='Box_asphalt' and (y>17500 or abs(y-6870)<2))
                or (name=='Box_concrete' and abs(y-6870)<2)
                or (name=='Box_stripe' and (y>17400 or abs(x+2530)<2 or abs(x-14300)<2))):
                c.remove_instance(i)
    for bp in (plan,env,yard):
        compile_bp(bp)
        save(bp)
    return counts


def plant(site, geo):
    cylinder=load('/Engine/BasicShapes/Cylinder')
    count=0
    for row in range(106):
        y=-23900+row*395
        for col in range(195):
            x=MIN_X+175+col*395
            xx,yy=x+rng.uniform(-145,145),y+rng.uniform(-145,145)
            if xx>MAX_X-200 or yy>bounds(xx)[0]-410:
                continue
            if -1720<xx<13120 and yy>-4450:
                continue
            if min(abs(yy-5900),abs(yy-13100))<570 and -4000<xx<-1700:
                continue
            if abs(yy-6100)<560 and 13120<xx<15500:
                continue
            cluster=.72+.19*math.sin(xx/2100+yy/2760)+.13*math.cos(yy/1300)
            distance=math.hypot(max(-1800-xx,xx-13200,0),max(-4500-yy,0))
            if rng.random()>cluster*(.76 if distance>13000 else 1.):
                continue
            if distance>15000 and rng.random()>.25:
                continue
            z=hillside(xx,yy)
            key='Fir_Distance' if distance>8800 else rng.choice(('Fir_A','Fir_B','Fir_C'))
            s=rng.uniform(.63,1.35)*(1.15 if distance>10000 else 1.)
            site.mesh(key,geo['SM_'+key],xx,yy,z,(s,s,rng.uniform(.85,1.16)*s),
                      yaw=rng.uniform(0,360))
            count+=1
            if distance<1800 and rng.random()<.49:
                site.mesh('ForestTrunkCollision',cylinder,xx,yy,z+143,(.34*s,.34*s,2.86),
                          collide=True)
    blocker=site.batches['ForestTrunkCollision']
    blocker.set_visibility(False)
    blocker.set_hidden_in_game(True)
    blocker.set_cast_shadow(False)
    for n,c in site.batches.items():
        if n.startswith('Fir_'):
            c.set_cull_distances(26000,65000)
            c.set_editor_property('cast_shadow',n!='Fir_Distance')
    return count


def crossing(site, geo):
    for name in ('ForestSlope_West','ForestSlope_East','ForestSlope_South','RiverGorge','RiverCurrent'):
        site.mesh(name,geo['SM_'+name],0,0,GROUND,collide=name!='RiverCurrent')
        site.batches[name].set_cull_distances(0,0)
    site.box('soil',5500,(FAR+23700)/2,GROUND-42,77000,23700-FAR,76,collide=True)
    site.box('asphalt',5850,22880,GROUND+2,1710,1250,6)
    for suffix in ('CampusHalf','CityHalf'):
        mesh=load('/Game/Surface/Bridge/SM_Bridge'+suffix)
        site.mesh('Bridge'+suffix,mesh,5850,BRIDGE_Y,GROUND+4,collide=True)
    fallen=load('/Game/Surface/Bridge/SM_BridgeFallenSpan')
    site.mesh('BridgeDebris',fallen,6330,BRIDGE_Y,925,(.93,.93,.80),yaw=15,pitch=9,collide=True)
    for x in (5130,6570):
        for y in (18230,21080):
            site.box('concrete',x,y,1515,242,309,1140,collide=True)
    # An emergency stair on the laboratory bank lets a fallen player climb out.
    x=8250
    a,_=bounds(x)
    for i in range(43):
        top=GROUND-i*28
        site.box('concrete',x,a-130+i*36,top-18,240,40,36,collide=True)
    for i in range(155):
        x=rng.uniform(-27900,37500)
        bank=rng.randrange(2)
        lo,hi=bounds(x)
        if abs(x-5850)<1630 or abs(x-8250)<260:
            continue
        y=(lo+rng.uniform(265,510)) if bank==0 else (hi-rng.uniform(270,535))
        s=rng.uniform(1.25,4.8)
        key='CliffTalus' if i%2 else 'CliffBroken'
        z=GROUND-320-(abs(y-(lo if bank==0 else hi))-270)*1.46
        site.mesh(key,geo['SM_'+key],x,y,z,(s,s,s*rng.uniform(.62,1.38)),yaw=rng.uniform(0,360))
    for i in range(82):
        x=rng.uniform(-14000,24500)
        y=rng.uniform(-11900,17650)
        if -2200<x<13600 and y>-5150:
            continue
        key='CliffTalus' if i%2 else 'CliffBroken'
        s=rng.uniform(.6,2.25)
        site.mesh(key,geo['SM_'+key],x,y,hillside(x,y)-35,(s,s,s),yaw=rng.uniform(0,360))


def greenhouse(site, cx, cy, radius, height):
    # Broken greenhouse cage, with open ribs and cracked planters.
    steps=18
    for i in range(steps):
        angle=i*math.tau/steps
        if i in (3,4,5,11):
            continue
        a=(cx+radius*math.cos(angle),cy+radius*math.sin(angle),GROUND+30)
        b=(cx+radius*math.cos(angle+math.tau/steps),cy+radius*math.sin(angle+math.tau/steps),GROUND+30)
        site.beam('concrete',a,b,48)
        count=3 if i in (2,6,10,12) else 6
        previous=a
        for j in range(1,count+1):
            theta=j*math.pi/12
            p=(cx+radius*math.cos(angle)*math.cos(theta),
               cy+radius*math.sin(angle)*math.cos(theta),GROUND+30+height*math.sin(theta))
            site.beam('rust',previous,p,9)
            if j in (2,4):
                q=(cx+radius*math.cos(angle+math.tau/steps)*math.cos(theta),
                   cy+radius*math.sin(angle+math.tau/steps)*math.cos(theta),p[2])
                site.beam('steel',p,q,6)
            previous=p


def debris(site, geo):
    greenhouse(site,7680,12100,520,310)
    greenhouse(site,3550,12380,400,245)
    for x,y,s in ((4700,3850,1.0),(7075,4020,1.05),(4880,5360,1.4),(6630,5260,1.2),
                  (2610,4650,1.25),(7030,13410,.8),(8240,10520,1.05),(5520,16780,1.18),
                  (7660,2840,.72),(3630,2190,.78),(5840,9100,1.1),(3500,13600,.89)):
        for i in range(9):
            xx,yy=x+rng.uniform(-290,290),y+rng.uniform(-270,275)
            if 5400<xx<6300 and (1430<yy<3600 or yy>16200):
                continue
            key='ImpactSlab' if i%2 else 'ImpactShards'
            a=s*rng.uniform(.30,1.24)
            site.mesh(key,geo['SM_'+key],xx,yy,GROUND+rng.uniform(18,74),
                      (a,a,rng.uniform(.65,1.25)*a),yaw=rng.randrange(360),
                      pitch=rng.uniform(-30,27),roll=rng.uniform(-24,26))
            if i%2==0:
                site.beam('rust',(xx-30,yy-8,GROUND+45),(xx+rng.uniform(35,158),yy-56,GROUND+105),5)
    wreck=load('/Game/Surface/Meshes/SM_WreckedSedan')
    site.fitted('OverturnedCar',wreck,6830,11120,GROUND+22,(462,181,140),-34,True)
    for i,(x,y) in enumerate(((4980,17180),(6720,17470),(6970,17620))):
        site.box('concrete',x,y,GROUND+105,235,130,162,yaw=18+i*38,pitch=25,roll=13)
        site.beam('steel',(x-88,y,GROUND+48),(x+123,y+55,GROUND+278),16)


def author_site(geo):
    path=ROOT+'/BP_RiverForest'
    if A.does_asset_exist(path):
        bp=load(path)
    else:
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.Actor)
        bp=tools.create_asset('BP_RiverForest',ROOT,unreal.Blueprint,factory)
    site=Site(bp)
    crossing(site,geo)
    count=plant(site,geo)
    debris(site,geo)
    compile_bp(bp)
    save(bp)
    return bp,count


def rebuild(actor,bp):
    label,folder=actor.get_actor_label(),actor.get_folder_path()
    p,rot=actor.get_actor_location(),actor.get_actor_rotation()
    assert actors.destroy_actor(actor)
    a=actors.spawn_actor_from_class(B.generated_class(bp),p,rot)
    a.set_actor_label(label)
    a.set_folder_path(folder)


def main():
    assert not levels.get_dirty_map_packages()
    lab=content/'Lvl_LabTutorial.umap'
    digest=hashlib.sha256(lab.read_bytes()).hexdigest()
    backup=saved/'Backups/RiverForest'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path in (LEVEL,PLAN,ENV,YARD):
        shutil.copy2(content/(path.removeprefix('/Game/')+('.umap' if path==LEVEL else '.uasset')),backup)
    mats=make_materials()
    geo=meshes(mats)
    bp,tree_count=author_site(geo)
    plan,env,yard=(load(p) for p in (PLAN,ENV,YARD))
    edits=trim_old_ground(plan,env,yard)
    world=levels.load_map(LEVEL)
    scene={actor.get_actor_label():actor for actor in actors.get_all_level_actors()}
    for key,obj in (('REF_LaboratoryComplex',plan),('SURF_Environment',env),('RUIN_Exterior',yard)):
        rebuild(scene[key],obj)
    for label in ('REF_ClosedSteelCheckpoint','RIVER_ForestBasin','RIVER_BridgeWarning'):
        if label in scene:
            assert actors.destroy_actor(scene[label])
    dome=scene['SURF_AshSky'].static_mesh_component
    dome.modify()
    dome.set_material(0,mats['sky'])
    moon=scene['SURF_LateSun'].get_component_by_class(unreal.DirectionalLightComponent)
    moon.modify()
    moon.set_intensity(2.4)
    moon.set_light_color(COLOR(.78,.85,.96,1))
    moon.set_editor_property('volumetric_scattering_intensity',.55)
    sky=scene['SURF_SkyFill'].get_component_by_class(unreal.SkyLightComponent)
    sky.modify()
    sky.set_intensity(.95)
    sky.set_light_color(COLOR(.83,.91,1,1))
    sky.recapture_sky()
    basin=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    basin.set_actor_label('RIVER_ForestBasin')
    basin.set_folder_path('SURFACE/River and Forest')
    sign=actors.spawn_actor_from_class(unreal.TextRenderActor,local(4840,17545,2390),unreal.Rotator(yaw=-90))
    sign.set_actor_label('RIVER_BridgeWarning')
    sign.set_folder_path('SURFACE/River and Forest')
    sign.text_render.set_text(unreal.Text('МОСТ ОБРУШЕН / ИМПУЛЬСНЫЙ ПРЫЖОК'))
    sign.text_render.set_world_size(37)
    sign.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    world.modify()
    assert levels.save_map(world,LEVEL)
    del world
    assert levels.load_map(LEVEL)
    restored={a.get_actor_label():a for a in actors.get_all_level_actors()}
    assert 'RUIN_LaboratoryShell' in restored and 'REF_ClosedSteelCheckpoint' not in restored
    basin=restored['RIVER_ForestBasin']
    assert basin.root_component.get_name()=='SiteRoot'
    assert hashlib.sha256(lab.read_bytes()).hexdigest()==digest
    (saved/'river_forest.json').write_text(json.dumps(dict(saved=True,tree_instances=tree_count,
        river_width_cm=FAR-NEAR,bridge_center_y=BRIDGE_Y,water_z=WATER_Z,edits=edits,backup=str(backup)),indent=2))
    assert levels.load_map(MAIN)


if __name__=='__main__':
    main()
