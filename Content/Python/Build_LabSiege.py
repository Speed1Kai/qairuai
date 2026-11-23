"""Author the assault damage on the playable laboratory exterior."""
from datetime import datetime
import hashlib
import json
import math
import random
import shutil

import unreal
from Build_RuinedUrbanCampus import (
    A, B, CYLINDER, GROUND, LEVEL, MAIN, MAT, OFFSET, PLAN, ROOT, Site, V, actors,
    add, compile_bp, components, content, crater_mesh, levels, local, save, saved, subtract, tools,
)
from Break_LaboratoryShell import INTERIORS
from Place_WreckFleet import body_shader

ASSETS = ROOT+'/Siege'
YARD = ROOT+'/BP_RuinedUrbanCampus'
ENVIRONMENT = '/Game/Surface/BP_SurfaceEnvironment'
ENV_ORIGIN = (5850.,23500.)
SOURCE = content.parent/'SourceAssets/LabSiege'
VEHICLES = '/Game/Environment/Vehicles/'
M = unreal.MaterialEditingLibrary
RNG = random.Random(7431)

# x0, x1, y0, y1, lowest damaged elevation. The protected arrival door and
# first-floor main route at x=5850 have separate load-bearing geometry.
COLLAPSES = {
    'A_North': ((6940, 8760, -1140, 125, 600), (7460, 8760, -1050, 120, 360)),
    'A_South': ((3390, 5148, -1520, 165, 740),),
    'A_Entry': ((4120, 6460, -370, 990, 610), (5620, 6490, 245, 975, 435)),
    'Research': ((4140, 6000, 5320, 8360, 610), (4220, 5350, 5320, 6290, 350),
                 (6420, 7565, 7800, 10980, 730), (5710, 7240, 8720, 10790, 1130)),
    'Equipment': ((9560, 11140, 4200, 5730, 620), (9560, 10560, 4220, 5050, 410)),
    'Power': ((9640, 11085, 10020, 11180, 490), (9640, 10500, 10330, 10980, 250)),
    'Hangar': ((9580, 11135, 13410, 15190, 220),),
    'Bio': ((335, 1780, 4610, 6370, 520), (810, 1780, 4880, 5420, 310)),
    'Housing': ((335, 1765, 11260, 13260, 720), (890, 1765, 12190, 13030, 380)),
}
# Off-axis on roads, parking and the paved square. The central travel lanes
# are kept out of the blast bounds so the route stays usable on foot.
CRATERS = ((4100,3570,405,144), (6835,3730,360,176), (8625,8550,465,160),
           (5690,12475,440,195), (6815,14600,415,141))
VEHICLE_SPOTS = (
    ('Tank_Arrival', 'BurnedTank', 4890, 3020, -39),
    ('Tank_Checkpoint', 'BurnedTank', 7480, 15070, 154),
    ('Carrier_Research', 'TrackedCarrier', 7765, 5610, -61),
)


def asset(path):
    value = A.load_asset(path)
    assert value, path
    return value


def editor_asset(name, cls, factory):
    path=ASSETS+'/'+name
    return asset(path) if A.does_asset_exist(path) else tools.create_asset(name, ASSETS, cls, factory)


def weathered_material(name, surface):
    m=editor_asset(name, unreal.Material, unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(m)
    pos=M.create_material_expression(m,unreal.MaterialExpressionWorldPosition,-560,-70)
    normal=M.create_material_expression(m,unreal.MaterialExpressionVertexNormalWS,-450,220)
    n=M.create_material_expression(m,unreal.MaterialExpressionCustom,-230,0)
    inputs=[]
    for name in ('P','N'):
        inp=unreal.CustomInput()
        inp.set_editor_property('input_name',name)
        inputs.append(inp)
    n.set_editor_property('inputs',inputs)
    n.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    flags=f'float isRoad = {float(surface=="road")}; float isWall = {float(surface=="wall")};'
    n.set_editor_property('code',flags+'''
struct Noise {
float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float2 rand2(float2 p) {return float2(hash(p),hash(p+float2(17.13,42.74)));}
float val(float2 p) {
    float2 c=floor(p), f=frac(p); f=f*f*(3-2*f);
    return lerp(lerp(hash(c),hash(c+float2(1,0)),f.x),
                lerp(hash(c+float2(0,1)),hash(c+1),f.x),f.y);
}
}; Noise n;
float vertical=isWall*(1-smoothstep(.35,.85,abs(N.z)));
float2 p=lerp(P.xy,float2(P.x+P.y*.79,P.z),vertical);
float broad=n.val(p*.0051)*.62+n.val(p*.019)*.38;
float rough=n.val(p*.31);
float grit=n.val(p*.84);
float drips=n.val(p*float2(.029,.004));
float ash=smoothstep(.46,.75,broad+.15*n.val(p*.032)+vertical*(drips-.36)*.32);
float moss=(1-ash)*smoothstep(.49,.75,n.val(p*.012)*.68+n.val(p*.045)*.32);
float2 q=p*.0073+float2(n.val(p*.061),n.val(p*.073+17))*.18;
float2 base=floor(q),f=frac(q);
float a=8,b=8;
float2 closest=0;
[unroll] for(int y=-1;y<=1;y++) {
    [unroll] for(int x=-1;x<=1;x++) {
        float2 off=float2(x,y);
        float2 v=off+n.rand2(base+off)-f;
        float d=dot(v,v);
        if(d<a) {b=a;a=d;closest=off;} else {b=min(b,d);}
    }
}
float seams=1-smoothstep(.011,.042,b-a);
float crack=seams*smoothstep(.31,.50,n.hash(base+closest)*.52+broad*.48);
float3 material=lerp(lerp(float3(.092,.076,.051),float3(.081,.083,.079),isRoad),float3(.157,.137,.107),isWall);
material*=.68+.46*rough+.21*grit;
material=lerp(material,float3(.018,.014,.010)*(.68+.62*grit),ash*.85);
material=lerp(material,float3(.069,.083,.030)*(.69+.67*rough),moss*(1-isRoad*.68-isWall*.71));
material=lerp(material,float3(.012,.009,.006),crack*.87);
return float4(material,(rough*.54+grit*.21-crack*.52)*.34);
''')
    assert M.connect_material_expressions(pos,'',n,'P')
    assert M.connect_material_expressions(normal,'',n,'N')
    for name,prop in (('color',unreal.MaterialProperty.MP_BASE_COLOR),('height',None)):
        mask=M.create_material_expression(m,unreal.MaterialExpressionComponentMask,10,0)
        for channel in 'rgba':
            mask.set_editor_property(channel,(channel=='a')==(name=='height'))
        assert M.connect_material_expressions(n,'',mask,'')
        if prop:
            assert M.connect_material_property(mask,'',prop)
        else:
            height=mask
    bump=M.create_material_expression(m,unreal.MaterialExpressionCustom,170,110)
    inputs=[]
    for name in ('P','N','H'):
        inp=unreal.CustomInput()
        inp.set_editor_property('input_name',name)
        inputs.append(inp)
    bump.set_editor_property('inputs',inputs)
    bump.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    bump.set_editor_property('code','float3 n=normalize(N);float3 a=cross(ddy(P),n),b=cross(n,ddx(P));float d=dot(ddx(P),a);return normalize(abs(d)*n-sign(d)*(ddx(H)*a+ddy(H)*b)+n*1e-6);')
    for node,name in ((pos,'P'),(normal,'N'),(height,'H')):
        assert M.connect_material_expressions(node,'',bump,name)
    m.set_editor_property('tangent_space_normal',False)
    assert M.connect_material_property(bump,'',unreal.MaterialProperty.MP_NORMAL)
    roughness=M.create_material_expression(m,unreal.MaterialExpressionConstant,20,240)
    roughness.set_editor_property('r',.91)
    assert M.connect_material_property(roughness,'',unreal.MaterialProperty.MP_ROUGHNESS)
    M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(m)
    save(m)
    return m


def import_models():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    armor=editor_asset('M_Siege_ScorchedArmor',unreal.Material,unreal.MaterialFactoryNew())
    body_shader(armor,(.15,.17,.105))
    result={}
    for name in ('BurnedTank','TrackedCarrier','ReinforcedFracture'):
        target='SM_Siege_'+name
        path=ASSETS+'/'+target
        if not A.does_asset_exist(path):
            opts=unreal.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,
                 mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                 import_materials=False,import_textures=False).items():
                opts.set_editor_property(key,value)
            opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
            opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
            task=unreal.AssetImportTask()
            for key,value in dict(filename=str(SOURCE/(target+'.fbx')),destination_path=ASSETS,
                                  destination_name=target,automated=True,save=False,options=opts).items():
                task.set_editor_property(key,value)
            tools.import_asset_tasks([task])
        mesh=asset(path)
        slots={'Armor':armor,'Steel':asset(VEHICLES+'M_Wreck_Steel'),
               'Trim':asset(VEHICLES+'M_Wreck_Trim'),'Oxide':asset(VEHICLES+'M_Wreck_Oxide'),
               'Concrete':MAT['concrete'],'Char':MAT['black']}
        for i,slot in enumerate(mesh.static_materials):
            raw=str(slot.material_slot_name)
            key=next((k for k in slots if raw.lower().startswith(k.lower())),None)
            assert key,raw
            mesh.set_material(i,slots[key])
        if name!='ReinforcedFracture':
            b=mesh.get_bounding_box()
            assert 520<b.max.x-b.min.x<900 and 280<b.max.y-b.min.y<430 and b.max.z>180, str(b)
            editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            editor.remove_collisions(mesh)
            assert editor.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)>=0
        save(mesh)
        result[name]=mesh
    return result


def pos(t):
    p=t.translation
    return p.x+OFFSET[0],p.y+OFFSET[1],p.z


def edit_boxes(t, holes, origin=OFFSET[:2]):
    p=t.translation
    x,y,z=p.x+origin[0],p.y+origin[1],p.z
    s,r=t.scale3d,t.rotation.rotator()
    cardinal=round(r.yaw/90)
    if abs(r.yaw-cardinal*90)>.1 or abs(r.pitch)+abs(r.roll)>.1:
        return None
    sx,sy=(s.y,s.x) if cardinal%2 else (s.x,s.y)
    bounds=(x-50*sx,x+50*sx,y-50*sy,y+50*sy)
    pieces=[bounds]
    for hole in holes:
        pieces=[part for rect in pieces for part in subtract(rect,hole)]
    if pieces==[bounds]:
        return None
    result=[]
    for x0,x1,y0,y1 in pieces:
        dx,dy=(x1-x0)/100,(y1-y0)/100
        if cardinal%2:
            dx,dy=dy,dx
        result.append(unreal.Transform(location=V(((x0+x1)*.5-origin[0],(y0+y1)*.5-origin[1],z)),
                                       rotation=r,scale=V((dx,dy,s.z))))
    return result


def active_cuts(x,y,z):
    return [zone[:4] for zones in COLLAPSES.values() for zone in zones if z>=zone[4]
            and zone[0]-700<x<zone[1]+700 and zone[2]-1700<y<zone[3]+1700]


def trim_buildings(bp, architecture):
    tally={}
    seen=set()
    for _,c,name in components(bp):
        if name in seen or not isinstance(c,unreal.InstancedStaticMeshComponent) or not c.static_mesh:
            continue
        seen.add(name)
        if architecture=='plan' and not name.startswith(('Box_wall','Box_glass','Box_steel_Detail','Box_dark_Detail')):
            continue
        removed,insert=[],[]
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,False)
            x,y,z=pos(t)
            if z<210 or y>15900:
                continue
            cuts=active_cuts(x,y,z+14 if name=='Box_floor_Solid' else z)
            if not cuts:
                continue
            in_blast=any(x0-21<x<x1+21 and y0-21<y<y1+21 for x0,x1,y0,y1 in cuts)
            if name in ('Box_floor_Solid','WeatheredRoofPanels','Box_dark_Detail') and t.scale3d.z<.85:
                pieces=edit_boxes(t,cuts)
                if pieces is not None:
                    removed.append(i)
                    insert.extend(pieces)
                    continue
            if in_blast:
                removed.append(i)
        if removed:
            c.modify()
            for i in reversed(removed):
                c.remove_instance(i)
            for t in insert:
                c.add_instance(t,False)
            tally[name]=len(removed)
    return tally


def edit_paving(bp, asphalt, dirt, plan):
    source_names=(('Box_floor_Collision','Box_asphalt_Detail','ExteriorWalkwayPaving',
                   'Box_amber_Detail','RestoredCheckpointGround','RestoredCheckpointRoad') if plan
                   else ('Box_asphalt','Box_stripe','Box_soil'))
    groups={n:c for _,c,n in components(bp) if n in source_names}
    tally={}
    holes=[(x-r,x+r,y-r,y+r) for x,y,r,_ in CRATERS]
    for name,c in groups.items():
        paint='stripe' not in name and 'amber' not in name
        if paint:
            target=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,'Siege_'+name,'PlanRoot' if plan else 'SiteRoot')
            target.modify()
            target.clear_instances()
            target.set_mobility(c.get_editor_property('mobility'))
            target.set_static_mesh(c.static_mesh)
            target.set_collision_profile_name(c.get_collision_profile_name())
            target.set_material(0,asphalt if 'asphalt' in name or 'Road' in name else dirt)
        removed=[]
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,False)
            x,y,z=pos(t)
            if not -85<z<22 or y>17800 or x<-1800 or x>13200:
                continue
            fragments=edit_boxes(t,holes)
            if paint:
                for part in ([t] if fragments is None else fragments):
                    target.add_instance(part,False)
                removed.append(i)
            elif fragments is not None:
                removed.append(i)
        if removed:
            c.modify()
            for i in reversed(removed):
                c.remove_instance(i)
        tally[name]=len(removed)
    return tally


def cut_ground_under_craters(bp):
    # Older town terrain extends under the campus ring road at Z=2145.
    # Cut only the crater footprints; all other terrain retains its collision.
    holes=[(x-r,x+r,y-r,y+r) for x,y,r,_ in CRATERS]
    c=next(c for _,c,name in components(bp) if name=='Boxes_M_Dust_Block')
    removed,insert=[],[]
    for i in range(c.get_instance_count()):
        t=c.get_instance_transform(i,False)
        if t.translation.y+ENV_ORIGIN[1]>=17800:
            continue
        pieces=edit_boxes(t,holes,ENV_ORIGIN)
        if pieces is not None:
            removed.append(i)
            insert.extend(pieces)
    if removed:
        c.modify()
        for i in reversed(removed):
            c.remove_instance(i)
        for t in insert:
            c.add_instance(t,False)
    return len(removed)


def break_windows(bp):
    randomizer=random.Random(168)
    broken=0
    for _,c,name in components(bp):
        if name not in ('Box_glass_Solid','Box_glass_Detail'):
            continue
        c.modify()
        for i in range(c.get_instance_count()-1,-1,-1):
            x,y,z=pos(c.get_instance_transform(i,False))
            if 0<x<11200 and -1650<y<15800 and 195<z<2000 and randomizer.random()<.38:
                c.remove_instance(i)
                broken+=1
    return broken


def crack_mesh():
    name='SM_Siege_FractureNetwork'
    if A.does_asset_exist(ASSETS+'/'+name):
        return asset(ASSETS+'/'+name)
    file=SOURCE/(name+'.obj')
    points,faces=[],[]
    def ribbon(start,direction,length,width,steps):
        x,y=start
        for i in range(steps):
            angle=direction+RNG.uniform(-.62,.62)
            dx,dy=math.cos(angle),math.sin(angle)
            span=length/steps*RNG.uniform(.65,1.25)
            nx,ny=x+dx*span,y+dy*span
            w=width*(1-i/(steps+.3))*.5
            edge=((x-dy*w,y+dx*w),(nx-dy*w*.9,ny+dx*w*.9),
                  (nx+dy*w*.9,ny-dx*w*.9),(x+dy*w,y-dx*w))
            k=len(points)+1
            points.extend(edge)
            faces.append((k,k+1,k+2,k+3))
            x,y=nx,ny
            if steps>5 and i in (1,3,5):
                ribbon((x,y),direction+RNG.choice((-1,1))*RNG.uniform(.70,1.10),
                       length*RNG.uniform(.21,.38),width*.53,4)
    for i in range(6):
        ribbon((0,0),i*math.tau/6,RNG.uniform(125,215),RNG.uniform(3,9),7)
    with file.open('w',encoding='ascii') as out:
        out.write(f'o {name}\n')
        for x,y in points:
            out.write(f'v {x:.4f} {-y:.4f} 0\n')
        for face in faces:
            out.write('f '+' '.join(str(i) for i in face)+'\n')
    task=unreal.AssetImportTask()
    opts=unreal.FbxImportUI()
    opts.set_editor_property('import_materials',False)
    opts.set_editor_property('import_textures',False)
    for key,value in dict(filename=str(file),destination_path=ASSETS,
                          automated=True,save=False,options=opts).items():
        task.set_editor_property(key,value)
    tools.import_asset_tasks([task])
    mesh=asset(ASSETS+'/'+name)
    mesh.set_material(0,MAT['black'])
    save(mesh)
    return mesh


def crater_materials(component, shape, asphalt, dirt):
    for i,slot in enumerate(shape.static_materials):
        material={'soil':dirt,'concrete':asphalt,'black':MAT['black']}.get(str(slot.material_slot_name))
        if material:
            component.set_material(i,material)


def dress_surviving_surfaces(interior, plan, yard, asphalt, dirt, concrete):
    trim=MAT['steel']
    glass=asset('/Game/Surface/Materials/M_DeadGlass')
    assignments=dict.fromkeys(('Box_white_Solid','Box_white_Trim','Box_floor_Solid',
                              'WeatheredRoofPanels','Box_wall_Detail'),concrete)
    assignments.update(Box_steel_Solid=trim,Box_teal_Trim=trim,Box_glass_Solid=glass,Box_glass_Detail=glass)
    for bp in (interior,plan,yard):
        for _,c,name in components(bp):
            if not isinstance(c,unreal.InstancedStaticMeshComponent):
                continue
            if name in assignments:
                c.modify()
                c.set_material(0,assignments[name])
            elif bp==yard and name.startswith('Crater_'):
                c.modify()
                crater_materials(c,c.static_mesh,asphalt,dirt)


def litter(site, models, asphalt, dirt):
    slab=models['ReinforcedFracture']
    rock=asset('/Game/Surface/Meshes/SM_RubbleCluster')
    crack=crack_mesh()
    shrub=asset('/Game/Surface/Meshes/SM_DeadTree')
    grass={v:asset('/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_'+v) for v in 'ABCD'}
    paved=[(3410,3470),(4120,3444),(4750,3540),(5360,3420),(6180,3570),(6850,3410),(7540,3450),
           (8625,4400),(8646,7120),(8630,8500),(8610,9720),(8650,12030),(8625,13620),
           (2850,4800),(2860,7500),(2830,11150),(2850,12820),(5430,12400),(5960,12870),
           (4470,14620),(5260,14604),(6820,14602),(6130,15830)]
    for x,y in paved:
        if any(abs(x-a)<r*.73 and abs(y-b)<r*.73 for a,b,r,_ in CRATERS):
            continue
        s=RNG.uniform(.78,1.50)
        site.mesh('AsphaltFractures',crack,x,y,GROUND+15,(s,s,s),yaw=RNG.randrange(360))
    for i,(x,y,r,depth) in enumerate(CRATERS,4):
        shape=crater_mesh(i,r,depth)
        key='SiegeCrater'+str(i)
        site.mesh(key,shape,x,y,GROUND+.42,collide=True)
        crater_materials(site.batches[key],shape,asphalt,dirt)
        for j in range(18):
            angle=(j+RNG.uniform(-.22,.22))*math.tau/18
            rad=RNG.uniform(.93,1.25)*r
            xx,yy=x+math.cos(angle)*rad,y+math.sin(angle)*rad
            if abs(xx-5850)<290 and (yy<3990 or yy>14000):
                continue
            s=RNG.uniform(.21,.67)
            site.mesh('DisplacedAsphalt',slab,xx,yy,GROUND+RNG.uniform(7,42),(s,s,s*.72),
                      yaw=RNG.randrange(360),pitch=RNG.uniform(-24,27),roll=RNG.uniform(-15,21))
            if j%3==0:
                site.mesh('AsphaltFractures',crack,xx,yy,GROUND+15,(.65,.60,.70),yaw=RNG.randrange(360))

    # Demolition piles sit under the missing bays, never on the exit lane.
    piles=((4060,1620,340,16),(5030,1830,330,24),(6720,1350,345,20),(7610,465,360,23),
           (8730,-360,315,19),(4160,5250,355,25),(5040,5230,375,22),(7120,7630,375,30),
           (7570,9110,365,21),(9470,4530,280,18),(9420,10500,350,20),(9460,13930,420,20),
           (1850,5040,365,20),(1910,12430,345,23),(410,7340,270,16))
    for x,y,spread,count in piles:
        for i in range(count):
            angle=RNG.random()*math.tau
            d=spread*RNG.uniform(.10,1)
            xx,yy=x+d*math.cos(angle),y+d*math.sin(angle)
            if abs(xx-5850)<390 and yy<3790:
                continue
            scale=RNG.uniform(.32,1.28)*(1.08-d/spread*.33)
            z=GROUND+18+(1-d/spread)**2*RNG.uniform(65,180)
            pitch,roll=RNG.uniform(-35,39),RNG.uniform(-27,28)
            site.mesh('CollapsedConcrete',slab,xx,yy,z,(scale,scale,scale),yaw=RNG.randrange(360),
                      pitch=pitch,roll=roll)
            if i%3==0:
                site.mesh('ScatteredMasonry',rock,xx,yy,GROUND+5,(scale,scale,scale),yaw=RNG.randrange(360))
        if (x,y) in ((5030,1830),(7610,465),(5040,5230),(9470,4530),(1910,12430)):
            site.box('concrete',x,y,GROUND+62,175,118,78,collide=True,yaw=RNG.randrange(360))

    # Reinforcement sits at the surviving slab edges, and individual broken
    # beams angle into open space where their walls and ceilings were lost.
    edges=((4120,6460,218,870),(6940,8700,-1140,801),(3390,5180,-1520,960),
           (4140,5960,6290,1195),(4180,5960,8350,1610),(6420,7510,7815,1210),
           (9560,11100,5720,810),(9690,11065,10050,798),(9600,11110,15170,407),
           (355,1740,6380,810),(345,1740,11280,1210))
    for left,right,y,height in edges:
        for i in range(max(3,int((right-left)/260))):
            x=left+(i+.52)*250
            if x>right:
                break
            z=GROUND+height+RNG.uniform(-40,43)
            scale=RNG.uniform(.41,.87)
            site.mesh('HangingConcrete',slab,x,y,z,(scale,scale,scale),yaw=RNG.uniform(37,142),
                      pitch=RNG.uniform(-27,44),roll=RNG.uniform(-32,27))
            site.beam('rust',(x-33,y-14,z-4),(x+RNG.uniform(-72,100),y+RNG.uniform(70,200),
                         z-RNG.uniform(75,221)),3.8)

    # Entrenched angles away from navigation. Broad military silhouettes
    # face the damaged buildings and checkpoint.
    for label,name,x,y,yaw in VEHICLE_SPOTS:
        mesh=models[name]
        site.mesh(label,mesh,x,y,GROUND+8-mesh.get_bounding_box().min.z,collide=True,yaw=yaw)
        for i in range(4):
            angle=math.radians(yaw)
            u=RNG.uniform(-270,210)
            off=RNG.choice((-1,1))*RNG.uniform(155,245)
            xx,yy=x+u*math.cos(angle)-off*math.sin(angle),y+u*math.sin(angle)+off*math.cos(angle)
            site.mesh('AsphaltFractures',crack,xx,yy,GROUND+14,(.9,.9,.9),yaw=RNG.randrange(360))
    for x,y,yaw in ((4890,3325,-10),(5110,14510,20),(7730,14530,-18),(8000,6220,80)):
        for row in range(2):
            for i in range(5-row):
                a=math.radians(yaw)
                step=(i-2+row*.5)*53
                obj=(x+math.cos(a)*step,y+math.sin(a)*step,GROUND+19+row*26)
                site.box('soil',*obj,55,32,30,yaw=yaw+RNG.uniform(-14,13),pitch=RNG.uniform(-6,10))
        for i in range(12):
            xx,yy=x+RNG.uniform(-136,136),y+RNG.uniform(-110,124)
            site.box('rust',xx,yy,GROUND+12,6,1.7,1.9,yaw=RNG.randrange(360))

    # Small dark impact craters and pale concrete spalling on standing walls.
    for cx,cy,cz,width,count in ((4950,1523,2300,340,28),(5410,1523,2460,200,16),
                                (6190,1523,2400,205,19),(6460,1523,2510,205,15),
                                (5320,5336,2460,220,14),(7120,5336,2360,190,21)):
        for i in range(count):
            dx=RNG.gauss(0,width*.32)
            x,z=cx+dx,cz+RNG.gauss(0,54)+dx*.21
            if cy==1523 and x>6360:
                continue
            size=RNG.uniform(.025,.102)
            site.mesh('SpalledBulletEdges',CYLINDER,x,cy,z,
                      (size*1.45,size*1.20,.019),material='concrete',roll=90)
            site.mesh('BulletImpactPits',CYLINDER,x+.9,
                      cy+(2. if cy==1523 else -2.),z-.7,(size*.91,size*.83,.021),material='black',roll=90)

    patches=((3190,1660),(3890,3500),(4810,3510),(5050,2260),(6550,1730),(6850,3660),(7810,3200),
             (8020,2100),(2830,4450),(2450,5250),(2000,4780),(1800,6060),(1880,7820),(2950,7920),
             (3520,8540),(3660,10830),(2320,12110),(1930,12390),(3300,13200),(4510,12860),
             (6190,12100),(6900,13310),(7310,13720),(7790,14980),(8030,15700),(9380,14530),
             (9260,13000),(9180,10580),(9350,9480),(8210,9030),(8290,8260),(8190,7240),
             (8010,5830),(9240,4940),(9580,4120),(7190,3720),(6370,4420),(5130,4820),
             (4470,5300),(11930,4630),(11850,6670),(2340,14880),(3600,14750),(7050,16310))
    for cx,cy in patches:
        for i in range(39):
            a,d=RNG.random()*math.tau,RNG.uniform(12,305)
            x,y=cx+math.cos(a)*d,cy+math.sin(a)*d
            if (abs(x-5850)<315 and (y<4000 or y>13800)) or any(
                    abs(x-u)<r*.79 and abs(y-v)<r*.79 for u,v,r,_ in CRATERS):
                continue
            kind=RNG.choice('AABBBCCCD')
            s=RNG.uniform(.57,1.16)
            site.mesh('ReclaimedGrass_'+kind,grass[kind],x,y,GROUND+5,(s,s,s*1.03),yaw=RNG.randrange(360))
    for x,y in ((3190,1660),(8010,3690),(2430,7910),(9360,9590),(11830,5000),(3610,14520)):
        site.mesh('ScorchedTrunks',shrub,x,y,GROUND+7,(.57,.57,.60),pitch=RNG.uniform(-28,28),yaw=RNG.randrange(360))

    # Partly exposed slab edges give footholds for plants on the ruined levels.
    for cx,cy,cz in ((4170,790,480),(5540,260,880),(7060,20,800),(4320,5395,800),
                     (5920,5840,806),(7400,7840,1200),(9650,5730,800),(10730,11220,800),
                     (10010,15195,400),(1450,6410,800),(1010,11195,800)):
        for i in range(9):
            v=RNG.choice('BCD')
            s=RNG.uniform(.5,.82)
            site.mesh('ReclaimedGrass_'+v,grass[v],cx+RNG.uniform(-72,72),cy+RNG.uniform(-23,23),
                      GROUND+cz+5,(s,s,s),yaw=RNG.randrange(360))


def refresh(scene,label,bp):
    old=scene[label]
    pos,rot,folder=old.get_actor_location(),old.get_actor_rotation(),old.get_folder_path()
    assert actors.destroy_actor(old)
    actor=actors.spawn_actor_from_class(B.generated_class(bp),pos,rot)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)


def main():
    assert not levels.get_dirty_map_packages(), 'Map has unsaved edits'
    start=content/'Lvl_LabTutorial.umap'
    start_hash=hashlib.sha256(start.read_bytes()).hexdigest()
    backup=saved/'Backups/LabSiege'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for package,ext in ((LEVEL,'.umap'),(PLAN,'.uasset'),(INTERIORS,'.uasset'),(YARD,'.uasset'),(ENVIRONMENT,'.uasset')):
        shutil.copy2(content/(package.removeprefix('/Game/')+ext),backup)
    model=import_models()
    asphalt=weathered_material('M_Siege_FracturedAsphalt','road')
    dirt=weathered_material('M_Siege_BurnedGround','soil')
    concrete=weathered_material('M_Siege_BlastConcrete','wall')
    factory=unreal.BlueprintFactory()
    factory.set_editor_property('parent_class',unreal.Actor)
    bp=editor_asset('BP_LabSiege',unreal.Blueprint,factory)
    site=Site(bp)
    litter(site,model,asphalt,dirt)
    compile_bp(bp)
    save(bp)
    plan,interior,yard,environment=[asset(p) for p in (PLAN,INTERIORS,YARD,ENVIRONMENT)]
    damaged=trim_buildings(interior,'interior')
    assert damaged.get('Box_floor_Solid',0)>=35 and damaged.get('Box_white_Solid',0)>=100,damaged
    facade=trim_buildings(plan,'plan')
    windows=sum(break_windows(bp) for bp in (plan,interior))
    road=edit_paving(plan,asphalt,dirt,True)
    aprons=edit_paving(yard,asphalt,dirt,False)
    dress_surviving_surfaces(interior,plan,yard,asphalt,dirt,concrete)
    underlying=cut_ground_under_craters(environment)
    for changed in (plan,interior,yard,environment):
        compile_bp(changed)
        save(changed)
    world=levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    for label,blueprint in (('REF_LaboratoryComplex',plan),('INT_AllCampusBuildings',interior),
                            ('RUIN_Exterior',yard),('SURF_Environment',environment)):
        refresh(scene,label,blueprint)
    lights=0
    for label,actor in scene.items():
        if label in ('RUIN_LaboratoryShell','SIEGE_Battlefield'):
            assert actors.destroy_actor(actor)
        if not (label.startswith('INT_Light_') and isinstance(actor,unreal.PointLight)):
            continue
        # Burnt-out exterior wings no longer have bright office lighting.
        actor.modify()
        actor.point_light_component.set_visibility(False)
        lights+=1
    fresh=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    fresh.set_actor_label('SIEGE_Battlefield')
    fresh.set_folder_path('SURFACE/Laboratory Siege')
    world.modify()
    assert levels.save_map(world,LEVEL)
    del world
    assert levels.load_map(LEVEL)
    assert hashlib.sha256(start.read_bytes()).hexdigest()==start_hash
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    props=scene['SIEGE_Battlefield']
    counts={c.get_name():c.get_instance_count() for c in props.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert all(counts.get(label)==1 for label,*_ in VEHICLE_SPOTS),counts
    assert sum(n for k,n in counts.items() if k.startswith('ReclaimedGrass_'))>=1100
    assert 'DISTRICT_Expansion' in scene
    (saved/'lab_siege.json').write_text(json.dumps(dict(saved=True,backup=str(backup),
        building_cuts=damaged,old_facade_cuts=facade,road_batches=road,aprons=aprons,
        underlying_terrain_cuts=underlying,broken_windows=windows,disabled_lights=lights,
        craters=CRATERS,vehicles=VEHICLE_SPOTS,instances=counts),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
