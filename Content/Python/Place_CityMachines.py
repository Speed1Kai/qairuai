"""Install modular city mech and scout Blueprints and populate the connected level."""
from datetime import datetime
import json
import shutil

import unreal

from Build_CityReclaim import ROOT as CITY, material
from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, V, actors, add, components, content, levels, local, save, saved, tools
from CityCombat_Common import FX, asset as blueprint, compile_bp
from CityMachine_Logic import variables, patrol, plan, motion, firing, events
from SurfacePolish_Materials import import_file

ROOT='/Game/Enemies/CityMachines'
SOURCE=content.parent/'SourceAssets/CityMachines'
ROLES={
    # Mesh scale, hip height in meters, hull half-height and radius in cm.
    'Bastion':(1.59,2.63,390.,222.,((0,-1.04),(0,1.04)),(1.78,-1.29,3.40),390,555,4700,2700,1330,20,1.52,.68,1600,'Shotgun'),
    'Lynx':(1.52,2.06,300.,187.,((.90,-.85),(.90,.85),(-.90,-.85),(-.90,.85)),(2.65,0,3.23),355,455,6600,4350,2630,32,2.40,1.05,1080,'Plasma'),
    'Marauder':(1.41,2.08,240.,141.,((0,-.52),(0,.52)),(1.09,.85,2.53),475,745,4750,2240,850,9,.61,.25,740,'Carbine'),
    'Relay':(.98,0,85.,84.,(),(.64,0,0),520,600,5300,0,0,0,0,0,210,''),
    'Wasp':(.94,0,86.,85.,(),(1.03,.30,-.15),660,795,4600,3250,730,7,.78,.22,270,'Carbine'),
}
# Paths are authored in world-aligned offsets from spawn. They stay on the
# existing avenues and separate flight lanes from heavy street traffic.
SECTORS=(
    ('Marauder',5850,27650,0,90,((-120,-850,0),(180,1430,0),(-165,2620,0),(-235,360,0))),
    ('Relay',4970,25800,1080,80,((1240,950,300),(1540,3250,160),(-350,3700,-130),(-610,1150,180))),
    ('Wasp',6880,31700,840,90,((-940,1550,150),(260,2950,455),(-420,4250,120),(-1320,1800,-100))),
    ('Bastion',5850,57320,0,90,((100,-1060,0),(145,1300,0),(-1070,1630,0),(-180,510,0))),
    ('Relay',4880,56800,1310,90,((1200,920,310),(1980,2300,0),(-1230,3100,130),(-780,540,-160))),
    ('Lynx',15500,80400,0,90,((30,-1950,0),(115,1200,0),(-80,3630,0),(-210,240,0))),
    ('Wasp',15620,81200,980,90,((-920,-1300,120),(450,1150,420),(-370,3850,80),(-1280,800,-110))),
    ('Bastion',33400,92750,0,90,((200,-1080,0),(180,1390,0),(-140,2630,0),(-170,650,0))),
)


def load(path):
    obj=A.load_asset(path)
    assert obj,path
    return obj


def import_models():
    A.make_directory(ROOT)
    ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(ed.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    mats={key:load(CITY+'/M_Reclaim_'+key) for key in ('Armor','Frame')}
    mats['Oxide']=load('/Game/Surface/Materials/M_Oxide')
    wear='''
float2 p=float2(P.x+P.y*.37,P.z+P.y*.68);
float g=n.sample(p/12.0), grit=n.sample(p/2.2);
float rust=smoothstep(.62,.87,n.sample(p*float2(.093,.043))*.64+g*.36);
return lerp(Tint*(.66+g*.56+grit*.10),float3(.125,.053,.024),rust*.73);
'''
    for key,tint,metal,rough in (
        ('Olive',(.17,.205,.082),.43,.57),('Ivory',(.36,.34,.255),.45,.55),
        ('Crimson',(.31,.072,.031),.49,.51),('Teal',(.035,.194,.16),.48,.54),
        ('Ochre',(.39,.235,.059),.43,.55),('Bare',(.235,.245,.216),.77,.39),
        ('Tire',(.041,.045,.037),.08,.86),('Stripe',(.61,.34,.068),.3,.64),
    ):
        mats[key]=material('Machine'+key,tint,metal,rough,field=wear)
    mats['Red']=material('MachineRed',(4.5,.10,.037),emission=True)
    mats['Optic']=material('MachineOptic',(.12,2.2,1.92),emission=True)
    opt=unreal.FbxImportUI()
    for key,val in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                        mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        opt.set_editor_property(key,val)
    opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    result={}
    for role,data in ROLES.items():
        for kind in (('Body','Leg') if data[4] else ('Body',)):
            name=role+'_'+kind
            mesh=import_file(SOURCE/(name+'.fbx'),root=ROOT,options=opt)
            for i,slot in enumerate(mesh.static_materials):
                mesh.set_material(i,mats[str(slot.material_slot_name)])
            save(mesh)
            result[name]=mesh
    return result


def root(bp):
    c=add(bp,unreal.CapsuleComponent,'Hull')
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library=unreal.SubobjectDataBlueprintFunctionLibrary
    records=components(bp)
    h=next(h for h,_,n in records if n=='Hull')
    if not library.is_root_component(library.get_data(h)):
        assert subsystem.make_new_scene_root(records[0][0],h,bp)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name('BlockAllDynamic')
    c.set_editor_property('can_ever_affect_navigation',False)
    return c


def mesh_component(bp,name,mesh,xyz,scale):
    c=add(bp,unreal.StaticMeshComponent,name,'Hull')
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_static_mesh(mesh)
    c.set_collision_profile_name('NoCollision')
    c.set_editor_property('can_ever_affect_navigation',False)
    c.set_editor_property('relative_location',V(xyz))
    c.set_editor_property('relative_scale3d',V((scale,)*3))
    return c


def make_role(role,data,meshes,contact,tracer):
    scale,hip,half,radius,legs,muzzle,*config,sound=data
    bp=blueprint(ROOT+'/BP_'+role)
    c=root(bp)
    c.set_capsule_size(radius,half)
    lift=0. if not legs else -half-4.
    mesh_component(bp,'Chassis',meshes[role+'_Body'],(0.,0.,lift),scale)
    for i,(x,y) in enumerate(legs):
        mesh_component(bp,'Leg'+str(i),meshes[role+'_Leg'],(x*100*scale,y*100*scale,
                        hip*100*scale+lift),scale)
    for name,pos in (('Sensor',(muzzle[0]*.57,0.,muzzle[2]+.44)),('Muzzle',muzzle)):
        c=add(bp,unreal.SceneComponent,name,'Hull')
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_location',V((pos[0]*100*scale,pos[1]*100*scale,pos[2]*100*scale+lift)))
    variables(bp)
    patrol(bp)
    plan(bp,contact,role)
    motion(bp,role,len(legs))
    firing(bp,role,tracer,FX+'/S_'+sound)
    events(bp,role)
    cdo=unreal.get_default_object(B.generated_class(bp))
    props=('CruiseSpeed','CombatSpeed','SensorRange','FireRange','KeepRange','ShotDamage','FireCooldown','Windup','HullHealth')
    for name,value in zip(props,config):
        cdo.set_editor_property(name,float(value))
    cdo.set_editor_property('HullHeight',float(half+4.))
    cdo.set_editor_property('Flying',not legs)
    cdo.set_editor_property('tags',[unreal.Name('CyborgHostile'),unreal.Name('CityMachine'),unreal.Name(role)])
    save(bp)
    return bp


def prepare():
    meshes=import_models()
    pulse=blueprint(ROOT+'/BP_RelayContact')
    compile_bp(pulse)
    pulse_cls=B.generated_class(pulse)
    unreal.get_default_object(pulse_cls).set_editor_property('initial_life_span',2.45)
    save(pulse)
    contact=pulse_cls.get_path_name()
    tracer=B.generated_class(load(FX+'/BP_EnemyTracer')).get_path_name()
    for role,data in ROLES.items():
        unreal.log('CITY MACHINES: authoring '+role)
        make_role(role,data,meshes,contact,tracer)
    (saved/'city_machines_assets.txt').write_text(' '.join(ROLES),encoding='utf-8')


def ground(world,x,y):
    p=local(x,y,GROUND+100)
    hit=unreal.SystemLibrary.line_trace_single_by_profile(world,p,p-V((0,0,260)), 'Pawn',False,[],
             unreal.DrawDebugTrace.NONE,False)
    return hit.to_tuple()[5].z+GROUND if hit else GROUND


def main():
    world=levels.load_map(LEVEL)
    assert world
    sectors=[(i,data) for i,data in enumerate(SECTORS) if ROLES[data[0]][4]]
    labels={f'CITY_Machine_{i:02d}_{data[0]}' for i,data in sectors}
    bp={data[0]:load(ROOT+'/BP_'+data[0]) for _,data in sectors}
    backup=saved/'Backups/CityMachines'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    for actor in actors.get_all_level_actors():
        label=actor.get_actor_label()
        if label.startswith('CITY_Enceladus_') or label in labels or label=='CITY_CombatNavBounds':
            assert actors.destroy_actor(actor),label
    spawned=[]
    for i,(role,x,y,altitude,yaw,route) in sectors:
        half=ROLES[role][2]
        z=ground(world,x,y)+(altitude if altitude else half+4.)
        actor=actors.spawn_actor_from_class(B.generated_class(bp[role]),local(x,y,z),unreal.Rotator(yaw=yaw))
        assert actor,role
        label=f'CITY_Machine_{i:02d}_{role}'
        actor.set_actor_label(label)
        actor.set_folder_path('SURFACE/City Machines')
        actor.modify()
        actor.set_editor_property('tags',[unreal.Name('CyborgHostile'),unreal.Name('CityMachine'),unreal.Name(role)])
        for name,point in zip(('PointA','PointB','PointC','PointD'),route):
            actor.set_editor_property(name,V(point))
        spawned.append((label,role,x,y,z))
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    for row,(_,data) in zip(spawned,sectors):
        p=scene[row[0]].get_editor_property('PointB')
        assert (p.x,p.y,p.z)==data[-1][1],(row[0],p)
    (saved/'city_machines_placement.json').write_text(json.dumps(dict(
        saved=True,machines=spawned,backup=str(backup)),indent=2),encoding='utf-8')
