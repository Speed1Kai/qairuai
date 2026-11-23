"""Extend the playable city with three designed districts and a river ford."""
from datetime import datetime
import hashlib
import json
import math
import random
import runpy
import shutil

import unreal
from Build_RuinedUrbanCampus import (
    A,B,GROUND,LEVEL,MAIN,OFFSET,Site,V,actors,compile_bp,components,content,
    levels,local,save,saved,tools,
)
from Industrial_Common import G, Graph, pin, val

ROOT='/Game/Environment/CityExpansion'
SOURCE=content.parent/'SourceAssets/CityExpansion'
ENV='/Game/Surface/BP_SurfaceEnvironment'
RIVER='/Game/Surface/RiverForest/BP_RiverForest'
DEPARTURE='/Game/Surface/BP_SurfaceDeparture'
DISTRICTS=(
    ('ZHK_Klen_A','BrickWalkup',-650,39770,90),
    ('ZHK_Klen_B','BrickWalkup',2010,37630,0),
    ('ZHK_Klen_C','CivicResidence',1990,42150,180),
    ('ZHK_Sever_A','PanelResidence',-2760,45030,90),
    ('ZHK_Sever_B','PanelResidence',-2850,47930,90),
    ('ZHK_Sever_C','CivicResidence',-130,49200,180),
    ('Business_Atlas','OfficeTower',9470,38250,0),
    ('Business_Annex','BusinessAnnex',12640,38900,0),
    ('Business_Exchange','OfficeTower',12300,43030,-90),
    ('Business_Service','RetailPavilion',9400,43800,180),
    ('Mall_Orbit','ShoppingCenter',1690,55200,0),
    ('Mall_Retail','RetailPavilion',-2800,52960,90),
    ('Mall_Corner','RetailPavilion',8980,52900,-90),
)
RNG=random.Random(57)
M=unreal.MaterialEditingLibrary


def asset(path):
    value=A.load_asset(path)
    assert value,path
    return value


def bpy_asset(name):
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return asset(path)
    factory=unreal.BlueprintFactory()
    factory.set_editor_property('parent_class',unreal.Actor)
    return tools.create_asset(name,ROOT,unreal.Blueprint,factory)


def finish_mat(m):
    M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(m)
    save(m)
    return m


def facade(key,color):
    name='M_District_'+key
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return asset(path)
    m=tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    p=M.create_material_expression(m,unreal.MaterialExpressionWorldPosition,-500,40)
    normal=M.create_material_expression(m,unreal.MaterialExpressionVertexNormalWS,-500,-140)
    tint=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-500,185)
    tint.set_editor_property('constant',unreal.LinearColor(*color,1))
    h=M.create_material_expression(m,unreal.MaterialExpressionCustom,-200,20)
    ins=[]
    for k in ('P','N','Tint'):
        i=unreal.CustomInput()
        i.set_editor_property('input_name',k)
        ins.append(i)
    h.set_editor_property('inputs',ins)
    h.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    brick='''
float2 q=float2(lerp(P.y,P.x,step(abs(N.x),abs(N.y))),P.z);
float row=floor(q.y/7.8);
float u=q.x/24.3+fmod(abs(row),2)*.5;
float edge=min(min(frac(u),1-frac(u))*2.8,min(frac(q.y/7.8),1-frac(q.y/7.8)));
col=lerp(col*lerp(.66,1.22,n.hash(float2(floor(u),row))),float3(.118,.107,.090),1-smoothstep(.04,.13,edge));
''' if key=='Brick' else ''
    h.set_editor_property('code','''
struct Noise {
float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float field(float2 p){
  float2 i=floor(p),f=frac(p); f=f*f*(3-2*f);
  return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}}; Noise n;
float2 p=P.xy+P.z*float2(.59,.76);
float a=n.field(p*.006), b=n.field(p*.049),grain=n.field(p*.43);
float stains=n.field(float2(p.x*.031,p.y*.0032));
float fissure=1-smoothstep(.016,.061,abs(n.field(p*.018+b*.14)-.48));
float3 col=Tint*(.62+.38*a+.22*b+.10*grain);
'''+brick+'''
float coal=smoothstep(.52,.81,a*.7+stains*.3);
return lerp(col,float3(.046,.038,.031),coal*.74)*(1-fissure*.25);
''')
    for n,k in ((p,'P'),(normal,'N'),(tint,'Tint')):
        assert M.connect_material_expressions(n,'',h,k)
    assert M.connect_material_property(h,'',unreal.MaterialProperty.MP_BASE_COLOR)
    q=M.create_material_expression(m,unreal.MaterialExpressionConstant,0,120)
    q.set_editor_property('r',.89)
    assert M.connect_material_property(q,'',unreal.MaterialProperty.MP_ROUGHNESS)
    return finish_mat(m)


def import_architecture():
    A.make_directory(ROOT)
    materials={
        'Brick':facade('Brick',(.27,.129,.085)),
        'Panel':facade('Panel',(.217,.239,.23)),
        'Stone':facade('Stone',(.234,.202,.159)),
        **{k:asset('/Game/Surface/Materials/'+v) for k,v in (
            ('Concrete','M_RuinConcrete'),('Dark','M_Charcoal'),('Steel','M_RuinSteel'),
            ('Glass','M_DeadGlass'),('Rust','M_Oxide'))},
    }
    result={}
    for kind in sorted({row[1] for row in DISTRICTS}):
        name='SM_District_'+kind
        path=ROOT+'/'+name
        if not A.does_asset_exist(path):
            ui=unreal.FbxImportUI()
            for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                            mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
                ui.set_editor_property(k,v)
            ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
            ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
            task=unreal.AssetImportTask()
            for k,v in dict(filename=str(SOURCE/(name+'.fbx')),destination_path=ROOT,destination_name=name,
                            automated=True,options=ui,save=False).items():
                task.set_editor_property(k,v)
            tools.import_asset_tasks([task])
        m=asset(path)
        for i,slot in enumerate(m.static_materials):
            key=next(k for k in materials if str(slot.material_slot_name).startswith(k))
            m.set_material(i,materials[key])
        b=m.get_bounding_box()
        span=b.max-b.min
        assert 1500<span.x<5100 and 930<span.y<3500 and 720<span.z<5800, (name,str(span))
        sm=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        sm.remove_collisions(m)
        m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
            unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(m)
        result[kind]=m
    return result


def replace_bp(actor,bp):
    label,folder=actor.get_actor_label(),actor.get_folder_path()
    p,r=actor.get_actor_location(),actor.get_actor_rotation()
    assert actors.destroy_actor(actor)
    a=actors.spawn_actor_from_class(B.generated_class(bp),p,r)
    a.set_actor_label(label)
    a.set_folder_path(folder)


def trim_environment(bp):
    removed={}
    for _,c,name in components(bp):
        if not isinstance(c,unreal.InstancedStaticMeshComponent) or not c.static_mesh or name in removed:
            continue
        mesh=c.static_mesh.get_name()
        overpass=mesh=='SM_FallenOverpass'
        old_ruin=mesh.startswith('SM_Ruin_')
        support=name.startswith('Boxes_M_RuinConcrete') or name.startswith('Boxes_M_Charcoal')
        if not (overpass or old_ruin or support):
            continue
        n=0
        for i in range(c.get_instance_count()-1,-1,-1):
            p=c.get_instance_transform(i,False).translation
            # SURF_Environment actor local origin is at (5850,23500,2150).
            if (overpass or (support and abs(p.y-7900)<2 and abs(p.z-850)<2) or
                ((old_ruin or support) and -13000<p.x<15000 and 11700<p.y<36000)):
                c.modify()
                assert c.remove_instance(i)
                n+=1
        removed[name]=n
    compile_bp(bp)
    save(bp)
    return sum(removed.values())


def remove_river_bridge(bp):
    seen=set()
    removed=0
    for _,c,name in components(bp):
        if not isinstance(c,unreal.InstancedStaticMeshComponent) or name in seen:
            continue
        seen.add(name)
        if name in ('BridgeCampusHalf','BridgeCityHalf','BridgeDebris'):
            c.modify()
            removed+=c.get_instance_count()
            c.clear_instances()
        elif name=='Box_concrete_Solid':
            for i in range(c.get_instance_count()-1,-1,-1):
                p=c.get_instance_transform(i,False).translation
                if abs(p.z+635)<3 and min(abs(p.y+OFFSET[1]-v) for v in (18230,21080))<3:
                    c.modify()
                    assert c.remove_instance(i)
                    removed+=1
        elif name=='Box_soil_Solid':
            assert c.get_instance_count()>=1
            original=c.get_instance_transform(0,False)
            s=original.scale3d
            if s.x<700:
                continue
            x,y=original.translation.x+OFFSET[0],original.translation.y+OFFSET[1]
            x0,x1=x-s.x*50,x+s.x*50
            y0,y1=y-s.y*50,y+s.y*50
            c.modify()
            c.remove_instance(0)
            # Leave a notch only in the landing apron, allowing the east ramp to rise.
            for left,right,bottom,top in ((x0,5210,y0,y1),(6490,x1,y0,y1),(5210,6490,21610,y1)):
                if top>bottom:
                    c.add_instance(unreal.Transform(location=local((left+right)/2,(bottom+top)/2,2106),
                                                   scale=V(((right-left)/100,(top-bottom)/100,s.z))),False)
    compile_bp(bp)
    save(bp)
    return removed


def ford(site):
    profile=((17690,2155),(17805,2155),(19240,1097),(20030,1097),(21480,2157),(21920,2157))
    for (ya,za),(yb,zb) in zip(profile,profile[1:]):
        rise,run=zb-za,yb-ya
        pitch=math.degrees(math.atan2(rise,run))
        length=math.hypot(run,rise)
        site.box('concrete',5850,(ya+yb)/2,(za+zb)/2-13,length+22,1180,26,
                 collide=True,yaw=90,pitch=pitch)
        for x in (5270,6430):
            site.box('steel',x,(ya+yb)/2,(za+zb)/2+18,length+12,18,18,yaw=90,pitch=pitch)
        for frac in (.2,.49,.78):
            y=ya+run*frac
            z=za+rise*frac
            site.box('stripe',5850,y,z+1,80,12,2,yaw=90,pitch=pitch)
    rubble=asset('/Game/Surface/Meshes/SM_RubbleCluster')
    for i in range(10):
        x=5850+RNG.choice((-1,1))*RNG.uniform(635,870)
        ya,za=RNG.choice(profile[1:-1])
        s=RNG.uniform(.38,.73)
        site.mesh('FordRiprap',rubble,x,ya+RNG.uniform(-110,110),za-22,(s,s,s),yaw=RNG.randrange(360))


def protect_ford_streaming():
    bp=asset(DEPARTURE)
    graph=Graph(bp)
    graph.e=G.get_graph_editor_by_name(bp,'Exit_UpdateStreaming')
    nodes=graph.e.list_all_nodes()
    if any(n.get_name()=='BelowLaboratoryAndInside' for n in nodes):
        return
    # The comparison node is identified by the existing altitude constant.
    low=[n for n in nodes if n.find_input_pin('B').is_valid()
         and str(n.find_input_pin('B').get_pin_value()).split('.')[0]=='1400']
    assert len(low)==1,[(n.get_name(),str(n.get_node_title())) for n in nodes]
    [altitude]=pin(low[0],'A').list_connected_pins()
    [condition]=graph.out(low[0]).list_connected_pins()
    assert str(altitude.get_pin_name())=='Z' and str(condition.get_pin_name())=='Condition'
    position=altitude.get_owning_node()
    bp.modify()
    # At the lower laboratory floors the pawn is inside the Y=1500 exit.
    # The ford also dips below the altitude threshold, far beyond the exit.
    inside=graph.call('Engine.KismetMathLibrary.Less_DoubleDouble',A=pin(position,'Y',True),B=1600.)
    inside.set_node_pos(unreal.IntPoint(x=1500,y=1000))
    both=graph.call('Engine.KismetMathLibrary.BooleanAND',A=graph.out(low[0]),B=graph.out(inside))
    both.set_node_pos(unreal.IntPoint(x=1800,y=1000))
    both.rename('BelowLaboratoryAndInside')
    condition.break_pin_links()
    val(condition,graph.out(both))
    compile_bp(bp)
    save(bp)


def build_districts(site,models):
    # Existing northbound street ends around Y=34600. Connect it to a street grid.
    site.road(5850,45800,1640,22700)
    for y in (36500,46100,51300):
        site.road(4860,y,20320,1360)
    for x in (-4780,14700):
        site.road(x,45000,1260,17800)
    for side in (-1,1):
        site.box('concrete',5850+side*1120,45700,GROUND+11,570,22000,22,collide=True)
    for x,y,sx,sy in ((550,39870,5450,4700),(-150,46650,5250,4700),
                      (10450,40750,6750,6900),(1720,54200,7900,3900)):
        site.box('concrete',x,y,GROUND+5,sx,sy,10,collide=True)
    for label,kind,x,y,yaw in DISTRICTS:
        site.mesh('Building_'+kind,models[kind],x,y,GROUND+9,yaw=yaw,collide=True)
    # Shared dressing arranged around three distinct public spaces.
    for x,y,w,d in ((590,39880,1750,1300),(-670,46850,1960,1120),(9690,41620,1660,850)):
        site.box('soil',x,y,GROUND+13,w,d,26)
        for s in (-1,1):
            site.box('concrete',x+s*w*.5,y,GROUND+21,24,d,36)
            site.box('concrete',x,y+s*d*.5,GROUND+21,w,24,36)
            for i in range(3):
                xx=x-w*.30+i*w*.30
                site.box('steel',xx,y+s*(d*.5+150),GROUND+42,210,46,19)
                for dx in (-79,79):
                    site.box('concrete',xx+dx,y+s*(d*.5+150),GROUND+18,24,45,36)
    tree=asset('/Game/Surface/Meshes/SM_DeadTree')
    fir=asset('/Game/Surface/RiverForest/SM_Fir_A')
    rubble=asset('/Game/Surface/Meshes/SM_RubbleCluster')
    for x,y in ((80,39460),(1090,39560),(290,40360),(1020,40380),(-1320,46630),(-700,47190),
                (180,46960),(9310,41610),(10080,41700),(10650,41400),(-2220,51850),(3530,52390)):
        size=RNG.uniform(.62,1.02)
        mesh=fir if x>8000 or y>51400 else tree
        site.mesh('DistrictFirs' if mesh==fir else 'DistrictDeadTrees',mesh,x,y,GROUND+10,
                  (size,size,size),yaw=RNG.randrange(360))
    for _,_,x,y,yaw in DISTRICTS:
        for i in range(4):
            s=RNG.uniform(.37,.84)
            angle=math.radians(yaw)
            u,v=RNG.uniform(-700,700),RNG.uniform(960,1130)
            xx,yy=x+u*math.cos(angle)-v*math.sin(angle),y+u*math.sin(angle)+v*math.cos(angle)
            site.mesh('FacadeDebris',rubble,xx,yy,GROUND+8,(s,s,s),yaw=RNG.randrange(360))
    site.road(1480,52280,3950,1420,stripes=False)
    for i in range(12):
        site.box('stripe',-350+i*330,52280,GROUND+8,10,520,2)
    for mesh,x,y,yaw in (('SM_FP_AbandonedSedan',610,52390,79),('SM_FP_SecurityWagon',1880,52280,-91),
                         ('SM_FP_BurnedServiceVan',3020,52415,94),('SM_FP_AbandonedSedan',13070,45720,179),
                         ('SM_FP_SecurityWagon',-1700,46010,14)):
        site.mesh('ExpansionCar_'+mesh,asset('/Game/Environment/Vehicles/'+mesh),x,y,GROUND+10,collide=True,yaw=yaw)


def move_old_towers():
    positions=((16800,36150),(17230,39350),(17520,42500),
               (17170,45650),(17110,49200),(17220,52600))
    moved=0
    for actor in actors.get_all_level_actors():
        name=actor.get_actor_label()
        if not name.startswith('CITY_Residential_'):
            continue
        number=name.removeprefix('CITY_Residential_')
        if not number.isdecimal() or not 5<=int(number)<=10:
            continue
        x,y=positions[int(number)-5]
        p=actor.get_actor_location()
        actor.modify()
        assert actor.set_actor_location(V((x-OFFSET[0],y-OFFSET[1],p.z)),False,True)
        moved+=1
    return moved

def signage(code,text,x,y,z,scale,yaw):
    a=actors.spawn_actor_from_class(unreal.TextRenderActor,local(x,y,z),unreal.Rotator(yaw=yaw))
    a.set_actor_label('DISTRICT_'+code)
    a.set_folder_path('SURFACE/City Expansion')
    c=a.text_render
    c.set_text(unreal.Text(text))
    c.set_world_size(scale)
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    c.set_text_render_color(unreal.Color(r=184,g=187,b=174,a=255))


def main():
    assert not levels.get_dirty_map_packages()
    lab=content/'Lvl_LabTutorial.umap'
    digest=hashlib.sha256(lab.read_bytes()).hexdigest()
    backup=saved/'Backups/CityExpansion'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path,ext in ((LEVEL,'.umap'),(ENV,'.uasset'),(RIVER,'.uasset'),(DEPARTURE,'.uasset')):
        shutil.copy2(content/(path.removeprefix('/Game/')+ext),backup)
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    models=import_architecture()
    bp=bpy_asset('BP_ExpandedDistricts')
    site=Site(bp)
    ford(site)
    build_districts(site,models)
    compile_bp(bp)
    save(bp)
    env,river=asset(ENV),asset(RIVER)
    erased=trim_environment(env)
    bridge=remove_river_bridge(river)
    world=levels.load_map(LEVEL)
    for a in list(actors.get_all_level_actors()):
        label=a.get_actor_label()
        if label=='SURF_Environment':
            replace_bp(a,env)
        elif label=='RIVER_ForestBasin':
            replace_bp(a,river)
        elif label.startswith('DISTRICT_') or label in ('RIVER_BridgeWarning','REF_BridgeSafety'):
            assert actors.destroy_actor(a)
    old_towers=move_old_towers()
    protect_ford_streaming()
    a=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    a.set_actor_label('DISTRICT_Expansion')
    a.set_folder_path('SURFACE/City Expansion')
    signage('Ford','БРОД / ГОРОД',5190,17548,2420,41,-90)
    signage('Klen','ЖК КЛЁН',2010,36800,2520,69,-90)
    signage('Sever','ЖК СЕВЕР',-130,49823,2550,65,90)
    signage('Atlas','ДЕЛОВОЙ ЦЕНТР / АТЛАС',9470,37280,2560,64,-90)
    signage('Mall','ТРЦ  ОРБИТА',1690,53520,2710,122,-90)
    world.modify()
    assert levels.save_map(world,LEVEL)
    del world
    assert levels.load_map(LEVEL)
    assert hashlib.sha256(lab.read_bytes()).hexdigest()==digest
    (saved/'city_expansion.json').write_text(json.dumps(
        dict(buildings=len(DISTRICTS),models=len(models),river_bridge_parts=bridge,
             legacy_instances_removed=erased,towers_relocated=old_towers,backup=str(backup)),indent=2))
    runpy.run_path(str(saved/'Test_CityExpansion.py'),run_name='__main__')


if __name__=='__main__':
    main()
