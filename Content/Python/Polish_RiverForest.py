"""Weather the actual laboratory shells and refine the river bank and materials."""
from datetime import datetime
import json
import math
import random
import shutil

import unreal
from Build_RiverForest import A, B, FAR, GROUND, LEVEL, MAIN, M, ROOT, actors, bounds, import_task
from RiverForest_Geometry import NEAR, ground_tile
from Build_RiverForest import compile_bp, constant, content, custom, expr, levels, load, local, material, output, persist, rebuild, save, saved, template_map, V
from Industrial_Common import add

INTERIORS='/Game/Surface/Interiors/BP_CampusInteriors'
BASIN=ROOT+'/BP_RiverForest'
PLAN='/Game/Surface/ReferencePlan/BP_ReferenceCampus'
rng=random.Random(5312)

NOISE = """
struct NoiseField {
float hash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
float get(float2 p) {
    float2 i=floor(p),f=frac(p); f=f*f*(3.0-2.0*f);
    return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                lerp(hash(i+float2(0,1)),hash(i+1.0),f.x),f.y);
}
}; NoiseField n;
"""

FOOTPRINTS=(
    (3000,6360,-300,900,1280), (6550,7450,250,950,1280),
    (6630,8742,-1500,60,1200), (9606,11118,4248,7320,1600),
    (9666,11070,8904,11628,1200), (9606,11118,12924,15744,400),
    (366,1746,4308,7752,1200), (366,1746,9732,13704,1600),
)


def material_pass():
    for path in ('M_RiverCliff','M_ForestFloor','M_FirNeedles','M_FlowingRiver'):
        obj=load(ROOT+'/'+path)
        for node in unreal.ObjectIterator(unreal.MaterialExpressionCustom):
            if node.get_outer()!=obj:
                continue
            code=node.get_editor_property('code')
            if path=='M_FirNeedles':
                code='return max(C.rgb, float3(0.014,0.022,0.008)) * lerp(0.41,0.81,R);'
            elif path=='M_FlowingRiver' and 'float3 base' not in code:
                code=NOISE+"""
float2 p = float2(UV.x*535.0-T*.91,UV.y*43.0);
float2 warp=float2(n.get(p*.39),n.get(p*.47+4.0))*3.0;
float2 q=p+warp;
float a=(n.get(q+float2(.07,0))-n.get(q-float2(.07,0)))*.36;
float b=(n.get(q+float2(0,.18))-n.get(q-float2(0,.18)))*.42;
a+=sin(p.x*2.4+p.y*1.7+warp.x*2.2)*.025;
b+=cos(p.x*.71+p.y*2.1+warp.y*2.4)*.035;
return normalize(float3(a,b,1.0));"""
            elif path=='M_FlowingRiver':
                code=NOISE+"""
float edge=min(UV.y,1.0-UV.y);
float2 p=float2(UV.x*480.0-T*.92,UV.y*32.0);
float a=n.get(p)*.57+n.get(p*.47+9.3)*.31+n.get(p*2.2+21.0)*.12;
float foam=(1.0-smoothstep(.018,.095,edge))*smoothstep(.58,.87,a);
float facing=pow(1.0-saturate(abs(V.z)),3.8);
float3 base=lerp(float3(.024,.063,.066),float3(.152,.227,.233),facing);
return lerp(base*(.81+.26*a),float3(.45,.54,.51),foam*.73);"""
            else:
                mixture='smoothstep(.54,.93,slope)*.94' if path=='M_ForestFloor' else 'smoothstep(.71,.97,slope)*(.4+.28*m)'
                code=NOISE+"""
float2 p=P.xy*.0072+P.z*float2(.0054,-.0068);
float m=n.get(p*.34),a=n.get(p)*.62+n.get(p*3.4)*.29+n.get(p*13.1)*.09;
float cracks=1.0-smoothstep(.017,.08,abs(n.get(p*.57+float2(m*2,0))-.5));
float slope=abs(N.z);
float3 stone=lerp(float3(.045,.047,.045),float3(.19,.183,.159),a)*(1-cracks*.22);
float3 grass=lerp(float3(.029,.040,.015),float3(.097,.125,.042),a)*(.65+.43*m);
return lerp(stone,grass,MIX);
""".replace('MIX',mixture)
            node.set_editor_property('code',code)
        if path=='M_FirNeedles':
            obj.set_editor_property('opacity_mask_clip_value',.20)
        persist(obj)
    soot=material('M_CampusWeatheredConcrete')
    base=custom(soot,NOISE+"""
float2 q=P.xy*.0046+P.z*float2(.0023,.0029);
float l=n.get(q*.56);
float grime=n.get(q*2.2)*.68+n.get(q*12.1)*.19+n.get(q*46.9)*.13;
float scar=smoothstep(.37,.69,l)*smoothstep(.34,.74,grime);
float fracture=1.0-smoothstep(.018,.049,abs(n.get(q*.65+grime*.16)-.5));
float3 dry=lerp(float3(.132,.139,.132),float3(.264,.258,.231),grime);
return lerp(dry,float3(.045,.039,.029),scar*.86)*(1-fracture*.23);
""",{'P':expr(soot,'WorldPosition')})
    output(base,'BASE_COLOR')
    constant(soot,'ROUGHNESS',.91)
    persist(soot)
    paving=material('M_CampusWeatheredPavement')
    surface=custom(paving,NOISE+"""
float2 p=P.xy*.0051;
float broad=n.get(p*.33);
float grit=n.get(p*2.9)*.72+n.get(p*16.3)*.28;
float cracks=1.0-smoothstep(.014,.046,abs(n.get(p*.81+grit*.12)-.5));
float moss=smoothstep(.56,.82,broad)*smoothstep(.41,.77,grit);
float3 concrete=lerp(float3(.086,.091,.087),float3(.188,.179,.156),grit);
return lerp(concrete,float3(.053,.070,.027),moss*.78)*(1-cracks*.24);
""",{'P':expr(paving,'WorldPosition')})
    output(surface,'BASE_COLOR')
    constant(paving,'ROUGHNESS',.94)
    return soot,persist(paving)


def move_weathered(bp, soot):
    cs=template_map(bp)
    source=cs['Box_floor_Solid']
    dest=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,'WeatheredRoofPanels','InteriorRoot')
    dest.set_static_mesh(source.static_mesh)
    dest.set_material(0,soot)
    dest.set_mobility(unreal.ComponentMobility.MOVABLE)
    dest.set_collision_profile_name('BlockAll')
    source.modify()
    dest.modify()
    n=0
    for i in range(source.get_instance_count()-1,-1,-1):
        t=source.get_instance_transform(i,False)
        p=t.translation
        x,y,z=p.x+10006.289955343997,p.y+6612.598659341473,p.z
        roof=abs(z-1988)<1 or any(x0-3<x<x1+3 and y0-3<y<y1+3 and abs(z-(h-12))<1
                                  for x0,x1,y0,y1,h in FOOTPRINTS)
        if roof:
            dest.add_instance(t,False)
            source.remove_instance(i)
            n+=1
    n=dest.get_instance_count()
    assert n>25,n
    compile_bp(bp)
    save(bp)
    return n


def soften_city_bank(bp):
    cs=template_map(bp)
    soil=cs['Box_soil_Solid']
    soil.modify()
    assert soil.get_instance_count()==1
    t=soil.get_instance_transform(0,False)
    t.translation=local(5500,(FAR-650+23700)/2,GROUND-44)
    t.scale3d=V((770.,(23700-FAR+650)/100,.76))
    assert soil.update_instance_transform(0,t,False,True,True)
    fir=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,'FarBankTrees','SiteRoot')
    fir.clear_instances()
    fir.set_static_mesh(load(ROOT+'/SM_Fir_Distance'))
    fir.set_mobility(unreal.ComponentMobility.STATIC)
    fir.set_collision_profile_name('NoCollision')
    fir.set_cull_distances(27000,63000)
    fir.set_cast_shadow(False)
    count=0
    for row in range(5):
        for k in range(111):
            x=-29800+k*655+rng.uniform(-220,220)
            y=21870+row*370+rng.uniform(-120,160)
            if abs(x-5850)<2200 or rng.random()<.22 or y<bounds(x)[1]+170:
                continue
            s=rng.uniform(.42,.86)
            fir.add_instance(unreal.Transform(location=local(x,y,GROUND-5),
                 rotation=unreal.Rotator(yaw=rng.randrange(360)),scale=V((s,s,s))),False)
            count+=1
    compile_bp(bp)
    save(bp)
    return count


def close_near_bank(bp):
    name='SM_NearBankApron'
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        mesh=load(path)
    else:
        file=saved/'RiverForestSource'/(name+'.obj')
        ground_tile((-1820,13220,17360,NEAR)).write(file)
        opts=unreal.FbxImportUI()
        for key,value in dict(import_mesh=True,import_materials=False,import_textures=False,
                              automated_import_should_detect_type=False,
                              mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
            opts.set_editor_property(key,value)
        opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        mesh=import_task(file,opts)
    mesh.set_material(0,load(ROOT+'/M_RiverCliff'))
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
                                                              unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh)
    apron=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,'NearBankApron','SiteRoot')
    apron.clear_instances()
    apron.set_static_mesh(mesh)
    apron.set_mobility(unreal.ComponentMobility.STATIC)
    apron.set_collision_profile_name('BlockAll')
    apron.add_instance(unreal.Transform(location=local(0,0,GROUND-1.)),False)


def main():
    assert not levels.get_dirty_map_packages()
    backup=saved/'Backups/RiverForestPolish'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for name in (LEVEL,BASIN,INTERIORS,PLAN):
        shutil.copy2(content/(name.removeprefix('/Game/')+('.umap' if name==LEVEL else '.uasset')),backup)
    soot,paving=material_pass()
    plan=load(PLAN)
    plan_components=template_map(plan)
    for name in ('Box_floor_Collision','ExteriorWalkwayPaving'):
        plan_components[name].modify()
        plan_components[name].set_material(0,paving)
    compile_bp(plan)
    save(plan)
    interiors=load(INTERIORS)
    basin=load(BASIN)
    roofs=move_weathered(interiors,soot)
    close_near_bank(basin)
    trees=soften_city_bank(basin)
    world=levels.load_map(LEVEL)
    scene={actor.get_actor_label():actor for actor in actors.get_all_level_actors()}
    for name,bp in (('RIVER_ForestBasin',basin),('INT_AllCampusBuildings',interiors),('REF_LaboratoryComplex',plan)):
        rebuild(scene[name],bp)
    world.modify()
    assert levels.save_map(world,LEVEL)
    del world
    assert levels.load_map(MAIN)
    (saved/'river_forest_polish.json').write_text(json.dumps(
        dict(weathered_roof_pieces=roofs,far_bank_trees=trees,backup=str(backup)),indent=2))


if __name__=='__main__':
    main()
