"""Connect the retained upper laboratory to a hatch in the ruined surface corner."""
from datetime import datetime
import json
import math
import shutil

import unreal

from Build_RuinedUrbanCampus import A, B, CUBE, GROUND, MAIN, V, actors, add, compile_bp, content, levels, make_static_root, save, saved
from CityCombat_Common import asset as blueprint, link, pin, var
from CityMachine_Logic import Logic
from SurfacePolish_Materials import import_file

ROOT = '/Game/Surface/ServiceHatch'
SOURCE = content.parent/'SourceAssets'/'SurfaceHatch'
REPORT = saved/'SurfaceHatch'
BP = ROOT+'/BP_SurfaceHatch'
LABEL = 'LAB_SurfaceHatch'
AXIS = 5850.
START = 1560.
RISE_STEPS = 34
TREAD = 32.
GRADE = 2730.
END = START + TREAD*RISE_STEPS
DECK_END = 3145.
DOWN_STEPS = 34
DOWN_TREAD = 33.
EXIT_Y = DECK_END + DOWN_STEPS*DOWN_TREAD
OPENING = (5652.,6048.,2070.,2660.)
HINGE = (6050.,2365.,GRADE+5.)
TRIGGER = (AXIS,1765.,2360.)
MAT = {
    'steel':'/Game/LabTutorial/FirstFloor/M_LabSteel',
    'iron':'/Game/LabTutorial/Industrial/M_DistressedMetal',
    'concrete':'/Game/Environment/SurfacePolish/M_Scan_Concrete',
    'chip':'/Game/Surface/RuinedCampus/Siege/M_Siege_BlastConcrete',
    'ash':'/Game/Surface/RuinedCampus/Siege/M_Siege_BurnedGround',
    'earth':'/Game/Surface/Materials/M_Dust',
    'oxide':'/Game/Environment/Vehicles/M_Wreck_Oxide',
    'amber':'/Game/Surface/Materials/M_ExitAmber',
    'stripe':'/Game/Surface/Materials/M_LanePaint',
}
SOUNDS = '/Game/LabTutorial/Industrial/S_BlastDoor'


def asset(path):
    value = A.load_asset(path)
    assert value, path
    return value


class Structure:
    def __init__(self,bp,materials):
        self.bp = bp
        self.materials = materials
        self.batches = {}
        root = add(bp,unreal.SceneComponent,'SiteRoot')
        make_static_root(bp,root)

    def place(self,key,mesh,location,scale=(1.,1.,1.),*,material=None,solid=False,yaw=0.,pitch=0.):
        if key not in self.batches:
            component = add(self.bp,unreal.HierarchicalInstancedStaticMeshComponent,key,'SiteRoot')
            component.clear_instances()
            component.set_mobility(unreal.ComponentMobility.STATIC)
            component.set_static_mesh(mesh)
            component.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
            component.set_editor_property('can_ever_affect_navigation',False)
            if material:
                component.set_material(0,self.materials[material])
            self.batches[key] = component
        self.batches[key].add_instance(unreal.Transform(
            location=V(location), scale=V(scale), rotation=unreal.Rotator(pitch=pitch,yaw=yaw)),False)

    def box(self,material,x0,x1,y0,y1,z0,z1,*,solid=True):
        scale = ((x1-x0)/100.,(y1-y0)/100.,(z1-z0)/100.)
        key = 'Boxes_'+material+('_Solid' if solid else '_Detail')
        self.place(key,CUBE,((x0+x1)/2.,(y0+y1)/2.,(z0+z1)/2.),scale,material=material,solid=solid)


def import_ruins(world,materials):
    A.make_directory(ROOT)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    options = unreal.FbxImportUI()
    options.set_editor_property('automated_import_should_detect_type',False)
    options.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property('import_materials',False)
    options.set_editor_property('import_textures',False)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    names = ('WallTall','WallLow','EarthBank')
    result = {}
    for name in names:
        mesh = import_file(SOURCE/('SM_Hatch_'+name+'.fbx'),ROOT,options)
        for index,slot in enumerate(mesh.static_materials):
            key = str(slot.material_slot_name)
            mesh.set_material(index,materials['chip' if key=='Mortar' else key.lower()])
        mesh.get_editor_property('body_setup').set_editor_property(
            'collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(mesh)
        result[name] = mesh
    return result


def stairs(structure):
    for i in range(RISE_STEPS):
        y = START + TREAD*i
        z = GROUND + (GRADE-GROUND)*(i+1)/RISE_STEPS
        structure.box('steel',5652,6048,y,y+TREAD+.15,z-25,z)
        structure.box('oxide',5665,6035,y+.25,y+3,z-.9,z+.15,solid=False)
        if i%5 == 0:
            structure.box('stripe',5671,5737,y+.3,y+2.5,z+.1,z+.6,solid=False)
            structure.box('stripe',5963,6029,y+.3,y+2.5,z+.1,z+.6,solid=False)
    for i in range(DOWN_STEPS):
        y = DECK_END + DOWN_TREAD*i
        z = GRADE - (GRADE-GROUND)*(i+1)/DOWN_STEPS
        structure.box('chip',5660,6040,y,y+DOWN_TREAD+.15,z-28,z)
    # A continuous foundation joins the two levels at either end.
    structure.box('concrete',5652,6048,1495,START,GROUND-36,GROUND)
    structure.box('concrete',5660,6040,EXIT_Y,EXIT_Y+150,GROUND-21,GROUND)


def architecture(s,ruins):
    left,right,low,high = OPENING
    s.box('concrete',2860,6516,-1080,1518,2596,GRADE)
    s.box('ash',2860,6516,-1080,1518,GRADE,GRADE+4,solid=False)
    for x0,x1,y0,y1 in ((5170,left,1500,DECK_END),(right,6570,1500,DECK_END),
                         (left,right,1516,low),(left,right,high,DECK_END)):
        s.box('chip',x0,x1,y0,y1,GRADE-35,GRADE)
    for x in (5632.,6068.):
        s.box('concrete',x-20,x+20,1518,high,GROUND-23,GRADE-2)
        s.box('steel',x-14,x+14,1520,low,GROUND+1,GROUND+43)
    for x0,x1 in ((5170,5208),(6532,6570)):
        s.box('chip',x0,x1,1500,DECK_END,GROUND-18,GRADE-3)
    for x0,x1 in ((5170,5660),(6040,6570)):
        s.box('chip',x0,x1,DECK_END-26,DECK_END,GROUND-12,GRADE)
    # Surface collar, leaving the north edge flush with the last stair.
    s.box('iron',5637,left,low,high,GRADE-3,GRADE+10)
    s.box('iron',right,6063,low,high,GRADE-3,GRADE+10)
    s.box('iron',left,right,low-14,low,GRADE-3,GRADE+10)
    s.box('iron',left,right,high,high+12,GRADE-4,GRADE+3)
    # Exposed, fractured corner walls stand on the cap around the service shaft.
    for key,x,y,sx,sy,sz,yaw,z in (
            ('WallTall',5515,2330,1.46,1.3,1.,90,GRADE),
            ('WallLow',5800,1988,.86,1.15,1.25,180,GRADE),
            ('WallLow',6420,2790,1.14,1.25,.90,90,GRADE),
            ('WallTall',5850,1375,1.02,1.05,1.83,180,GRADE),
            ('WallLow',4740,1387,1.30,1.2,1.3,0,GRADE),
            ('WallLow',3740,1405,1.60,1.1,.79,0,GRADE),
            ('WallTall',6255,3410,.8,1.,.73,90,GROUND),
            ('WallLow',5410,3420,.9,1.,.70,-90,GROUND),
        ):
        s.place(key,ruins[key],(x,y,z),(sx,sy,sz),yaw=yaw,solid=True)
    for x,y,sx,sy,yaw in ((6568,2260,8.2,15.12,0),(5171,2280,7.8,15.1,180),
                          (6512,235,7.2,24.4,0),(2862,-753,6.7,6.53,180),(2862,942,5.8,9.3,180)):
        s.place('EarthBank',ruins['EarthBank'],(x,y,GROUND-3),(sx,sy,(GRADE-GROUND+3)/100.),yaw=yaw,solid=True)
    rubble = '/Game/Environment/CityAftermath/SM_War_'
    for i,(x,y,z,k,yaw,sx) in enumerate((
            (5520,2810,GRADE,'RubblePile',20,.69),(6320,2650,GRADE,'RippedSlabA',-21,.92),
            (6190,3020,GRADE,'RippedSlabB',52,.56),(5430,3030,GRADE,'TwistedGuardrail',-70,.68),
            (4840,760,GRADE,'RubblePile',-3,1.15),(5220,1380,GRADE,'RippedSlabA',43,.89),
            (3610,1335,GRADE,'RubblePile',59,1.1),(6480,1510,GRADE,'RippedSlabB',29,1.01),
            (5530,3510,GROUND,'RubblePile',90,.94),(6190,3970,GROUND,'RubblePile',49,1.21),
            (5525,4100,GROUND,'RippedSlabA',-72,.86),(6175,4310,GROUND,'TwistedGuardrail',-52,1.05),
        )):
        mesh = asset(rubble+k)
        s.place('Wreck_'+k,mesh,(x,y,z),(sx,)*3,yaw=yaw)
    for x in (5680,6020):
        for y,z in ((1605,2303),(1840,2455),(2020,2520)):
            s.box('iron',x-12,x+12,y-21,y+21,z-12,z+12,solid=False)
            s.box('amber',x-10,x+10,y-15,y+15,z+11,z+14,solid=False)


def lid(bp,materials):
    pivot = add(bp,unreal.SceneComponent,'HatchPivot','SiteRoot')
    pivot.set_mobility(unreal.ComponentMobility.MOVABLE)
    pivot.set_editor_property('relative_location',V(HINGE))

    def detail(name,location,size,material,collision=False):
        c = add(bp,unreal.StaticMeshComponent,name,'HatchPivot')
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(CUBE)
        c.set_material(0,materials[material])
        c.set_editor_property('relative_location',V(location))
        c.set_editor_property('relative_scale3d',V(tuple(value/100. for value in size)))
        c.set_editor_property('can_ever_affect_navigation',False)
        c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')

    detail('ArmoredLid',(-198,0,0),(394,586,10),'iron',True)
    for i,y in enumerate((-262,-130,0,130,262)):
        detail('LidRib'+str(i),(-190,y,-7),(346,13,7),'steel')
    for i,x in enumerate((-23,-370)):
        detail('LidEdge'+str(i),(x,0,7),(13,551,6),'oxide')
    detail('Grip',(-330,0,13),(25,54,13),'steel')
    for i,y in enumerate((-234,234)):
        detail('Hinge'+str(i),(-3,y,-2),(27,53,23),'steel')


def hatch_graph(bp):
    var(bp,'HatchRequested','bool','false')
    var(bp,'HatchOpenAmount','real','0')
    compile_bp(bp)
    g = Logic(bp,'UpdateHatch')
    branch = g.branch(g.get('HatchRequested'))
    opened = branch.find_then_pin()
    g.cursor = branch.find_else_pin()
    player = g.player()
    g.branch(g.valid(player))
    pos = g.position(player)
    g.branch(g.num('Less',g.distance(pos,g.vector(*TRIGGER)),218.))
    g.set('HatchRequested',True)
    sound = g.sound(SOUNDS+'Motor',g.vector(*HINGE),.36)
    start = g.cursor
    g.cursor = opened
    dt = g.dt()
    alpha = g.math('FInterpTo_Constant',Current=g.get('HatchOpenAmount'),Target=1.,DeltaTime=dt,InterpSpeed=1.13)
    update = g.set('HatchOpenAmount',alpha)
    link(start,update.find_execute_pin())
    amount = g.get('HatchOpenAmount')
    smooth = g.num('Multiply',g.num('Multiply',amount,amount),g.num('Subtract',3.,g.num('Multiply',2.,amount)))
    rotation = g.math('MakeRotator',Pitch=g.num('Multiply',smooth,-98.),Yaw=0.,Roll=0.)
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('HatchPivot'),
                NewRotation=rotation,bSweep=False,bTeleport=False))
    g.branch(g.num('GreaterEqual',amount,1.))
    g.sound(SOUNDS+'Thud',g.vector(*HINGE),.30)
    g.do(g.call('Engine.Actor.SetActorTickEnabled',bEnabled=False))
    compile_bp(bp)
    g = Logic(bp)
    g.event_call('ReceiveTick','UpdateHatch')
    compile_bp(bp)


def fit_exterior(departure):
    # The old outer casing stands above the new terrain. The actual furnished
    # interior and lift are separate actors and are kept at their original height.
    departure.modify()
    actor_z = departure.get_actor_location().z
    for c in departure.get_components_by_class(unreal.StaticMeshComponent):
        name = c.get_name()
        if name == 'ExteriorRoof':
            c.modify()
            c.set_visibility(False)
            c.set_hidden_in_game(True)
            c.set_collision_profile_name('NoCollision')
        elif name.startswith(('Facade','Exterior')):
            loc = c.get_editor_property('relative_location')
            scale = c.get_editor_property('relative_scale3d')
            low,high = actor_z+loc.z-50.*scale.z, actor_z+loc.z+50.*scale.z
            if high > GRADE and low < GRADE:
                c.modify()
                loc.z = (low+GRADE)*.5-actor_z
                scale.z = (GRADE-low)/100.
                c.set_relative_location(loc,False,False)
                c.set_relative_scale3d(scale)


def place_light(position):
    actor = actors.spawn_actor_from_class(unreal.PointLight,V(position))
    component = actor.point_light_component
    component.set_intensity(650.)
    component.set_attenuation_radius(290.)
    component.set_light_color(unreal.LinearColor(1.,.65,.34,1.))
    component.set_cast_shadows(False)
    return actor


def wayfinding():
    sign = actors.spawn_actor_from_class(unreal.TextRenderActor,V((5660.,1675.,2450.)),unreal.Rotator(yaw=0.))
    t = sign.text_render
    t.set_text(unreal.Text('ЛЮК НА ПОВЕРХНОСТЬ'))
    t.set_world_size(22.)
    t.set_text_render_color(unreal.Color(206,175,128,255))
    t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    t.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    result = [sign]
    for p in ((5680.,1640.,2520.),(6020.,1850.,2575.),(5680.,2045.,2620.)):
        result.append(place_light(p))
    return result


def install(world):
    assert world.get_path_name().split('.')[0] == MAIN
    backup = saved/'Backups'/'SurfaceHatch'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True)
    shutil.copy2(content/'Lvl_LabTutorial.umap',backup)
    materials = {k:asset(v) for k,v in MAT.items()}
    ruins = import_ruins(world,materials)
    bp = blueprint(BP)
    structure = Structure(bp,materials)
    stairs(structure)
    architecture(structure,ruins)
    lid(bp,materials)
    hatch_graph(bp)
    save(bp)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(LABEL):
            assert actors.destroy_actor(actor)
    departure = next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='SURFACE_Departure')
    fit_exterior(departure)
    unit = actors.spawn_actor_from_class(B.generated_class(bp),V((0.,0.,0.)))
    assert unit
    unit.set_actor_label(LABEL)
    unit.set_folder_path('LAB/Surface Hatch')
    for i,actor in enumerate(wayfinding()):
        actor.set_actor_label(LABEL+'_'+str(i))
        actor.set_folder_path('LAB/Surface Hatch')
    return dict(map=MAIN,blueprint=BP,grade=GRADE,rise=GRADE-GROUND,arrival_y=EXIT_Y,backup=str(backup))


def commit(world,report):
    assert levels.save_map(world,MAIN)
    (REPORT/'Install.json').write_text(json.dumps(report,indent=2))
