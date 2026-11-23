"""Install the Final Protocol score and spatial mechanical audio in native Blueprints."""
from datetime import datetime
from pathlib import Path
import shutil

import unreal

from CityCombat_Common import A, B, G, Graph, compile_bp, components, hook, link, pin, save, val, var

ROOT = '/Game/Audio/FinalProtocol'
PLAYER = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
GUIDE = '/Game/LabTutorial/OmegaGuide/BP_OmegaGuide'
LIFT = '/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional'
MACHINE = '/Game/Enemies/CityMachines/'
ROBOTS = {
    'BP_Marauder': ('Scout', 'Scout', 144., .51),
    'BP_PoliceMech': ('Heavy', 'Scout', 202., .61),
    'BP_Bastion': ('Heavy', 'Heavy', 192., .68),
    'BP_Lynx': ('Scout', 'Plasma', 162., .53),
    'Colossus/BP_Colossus': ('Siege', 'Siege', 0., .79),
}
FLOORS = {
    'Metal': (
        'LabTutorial/Industrial/M_DistressedMetal', 'LabTutorial/FirstFloor/M_LabSteel',
        'FinalProtocol/Materials/MI_FP_RustedSteel', 'Surface/Materials/M_RuinSteel',
        'LabTutorial/Industrial/M_RustyIron',
    ),
    'Soil': (
        'Environment/SurfacePolish/M_Scan_Forest', 'Environment/CityReclaim/M_Reclaim_Soil',
        'Surface/RuinedCampus/Siege/M_Siege_BurnedGround', 'CityDowntown/Materials/MI_dirt',
    ),
    'Asphalt': (
        'Environment/SurfacePolish/M_Scan_Asphalt', 'FinalProtocol/Materials/MI_FP_Asphalt',
        'Surface/Materials/M_Asphalt', 'Surface/Materials/CampusPaving/M_CampusAsphalt',
        'Surface/RuinedCampus/Siege/M_Siege_FracturedAsphalt', 'CityDowntown/Materials/MI_Asphalt',
    ),
}
LOOPS = {'S_FP_QuietSignal', 'S_FP_LabAir', 'S_FP_CityWind'}
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def install_sounds(source):
    A.make_directory(ROOT)
    tasks = []
    for file in sorted(source.glob('S_FP_*.wav')):
        path = ROOT + '/' + file.stem
        if A.does_asset_exist(path):
            continue
        task = unreal.AssetImportTask()
        for key, value in dict(filename=str(file), destination_path=ROOT, destination_name=file.stem,
                               automated=True, save=False).items():
            task.set_editor_property(key, value)
        tasks.append(task)
    if tasks:
        TOOLS.import_asset_tasks(tasks)
        assert all(task.get_objects() for task in tasks)
    sounds = {}
    for file in sorted(source.glob('S_FP_*.wav')):
        sound = A.load_asset(ROOT + '/' + file.stem)
        assert sound, file
        sound.set_editor_property('looping', file.stem in LOOPS)
        if file.stem in LOOPS:
            sound.set_editor_property('virtualization_mode', unreal.VirtualizationMode.PLAY_WHEN_SILENT)
        save(sound)
        sounds[file.stem] = sound.get_path_name()
    return sounds


def physical_materials():
    types = {}
    for name, materials in FLOORS.items():
        asset_name = 'PM_FP_' + name
        path = ROOT + '/' + asset_name
        physical = A.load_asset(path) if A.does_asset_exist(path) else TOOLS.create_asset(
            asset_name, ROOT, unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
        assert physical
        save(physical)
        types[name] = physical.get_path_name()
        for material_name in materials:
            path = '/Game/' + material_name
            if not A.does_asset_exist(path):
                continue
            material = A.load_asset(path)
            old = material.get_editor_property('phys_material')
            # Retain any physical behavior explicitly set by an imported material.
            if old and old != physical:
                unreal.log_warning('Soundscape retained physical material on ' + path)
                continue
            material.set_editor_property('phys_material', physical)
            if isinstance(material, unreal.MaterialInstance):
                try:
                    material.set_editor_property('override_phys_material', True)
                except Exception:
                    # On versions where PhysMaterial is used whenever non-null the
                    # additional override property is absent.
                    pass
            save(material)
    return types


def attenuation(name, radius, falloff):
    path = ROOT + '/ATT_FP_' + name
    att = A.load_asset(path) if A.does_asset_exist(path) else TOOLS.create_asset(
        path.rsplit('/', 1)[1], ROOT, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    settings = att.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents', unreal.Vector(radius, 0., 0.))
    settings.set_editor_property('falloff_distance', falloff)
    att.set_editor_property('attenuation', settings)
    save(att)
    return att.get_path_name()


class Audio(Graph):
    def num(self, op, a, b):
        return self.math(op+'_DoubleDouble', A=a, B=b)

    def no(self, v):
        return self.math('Not_PreBool', A=v)

    def location(self, target=None):
        return self.out(self.call('Engine.Actor.K2_GetActorLocation', target=target))

    def axis(self, v, axis):
        return self.out(self.call('Engine.KismetMathLibrary.BreakVector', InVec=v), axis)

    def offset(self, v, z):
        return self.math('Add_VectorVector', A=v, B=self.math('MakeVector', X=0., Y=0., Z=z))

    def play(self, sound, location, gain, att=None, pitch=(.93, 1.06)):
        kw = {'AttenuationSettings': att} if att else {}
        return self.do(self.call('Engine.GameplayStatics.PlaySoundAtLocation', Sound=sound,
            Location=location, VolumeMultiplier=gain,
            PitchMultiplier=self.math('RandomFloatInRange', Min=pitch[0], Max=pitch[1]), **kw))


def open_graph(bp, name):
    g = Audio(bp)
    g.e = G.get_graph_editor_by_name(bp, name)
    return g


def after(bp, graph, node, function, name):
    g = open_graph(bp, graph)
    if any(n.get_name() == name for n in g.e.list_all_nodes()):
        return
    old = list(node.find_then_pin().list_connected_pins())
    g.cursor = node.find_then_pin()
    g.cursor.break_pin_links()
    call = g.own(function)
    call.rename(name)
    pos = node.get_node_pos()
    call.set_node_pos(unreal.IntPoint(x=pos.x+310, y=pos.y-110))
    g.do(call)
    for sink in old:
        link(g.cursor, sink)


def boot_surfaces(bp, types, sounds):
    for name in (*types, 'Concrete'):
        g = Audio(bp, 'Audio_Boot'+name)
        g.set('AudioBootSurface', name)
        g.count('AudioBootPlays')
        location = g.get('AudioBootLocation')
        sprint = g.num('Greater', g.get('AudioBootSpeed'), 420.)
        volume = g.math('SelectFloat', A=.69, B=.54, bPickA=sprint)
        for i in range(1, 4):
            branch = None
            if i != 3:
                branch = g.branch(g.math('EqualEqual_IntInt', A=g.get('AudioBootVariant'), B=i))
            g.play(sounds[f'S_FP_Boot{name}_{i}'], location, volume)
            if branch:
                g.cursor = branch.find_else_pin()
    compile_bp(bp)

    g = Audio(bp, 'Audio_Footfall')
    g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
    g.set('AudioBootVariant', g.math('RandomIntegerInRange', Min=1, Max=3))
    start = g.location()
    capsule = g.get('CapsuleComponent')
    height = g.out(g.call('Engine.CapsuleComponent.GetScaledCapsuleHalfHeight', target=capsule))
    down = g.num('Subtract', -42., height)
    end = g.offset(start, down)
    trace = g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle', Start=start, End=end,
                       TraceChannel='TraceTypeQuery1', bTraceComplex=True, bIgnoreSelf=True,
                       DrawDebugType='None'))
    hit = g.call('Engine.GameplayStatics.BreakHitResult', Hit=g.out(trace, 'OutHit'))
    floor = g.math('SelectVector', A=g.out(hit, 'ImpactPoint'), B=g.offset(start,g.num('Multiply',height,-1.)),
                   bPickA=g.out(trace))
    g.set('AudioBootLocation', floor)
    for name, material in types.items():
        same = g.math('EqualEqual_ObjectObject', A=g.out(hit,'PhysMat'), B=material)
        branch = g.branch(same)
        g.do(g.own('Audio_Boot'+name))
        g.cursor = branch.find_else_pin()
    g.do(g.own('Audio_BootConcrete'))
    compile_bp(bp)
    g = Audio(bp, 'Audio_UpdateFootsteps')
    g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
    speed = g.math('VSizeXY', A=g.out(g.call('Engine.Actor.GetVelocity')))
    g.set('AudioBootSpeed', speed)
    ground = g.out(g.call('Engine.NavMovementComponent.IsMovingOnGround', target=g.get('CharacterMovement')))
    moving = g.branch(g.math('BooleanAND', A=ground, B=g.num('Greater',g.get('AudioBootSpeed'),35.)))
    step = g.num('Multiply', g.get('AudioBootSpeed'), g.dt())
    g.set('AudioBootDistance',g.num('Add',g.get('AudioBootDistance'),step))
    stride = g.math('FClamp',Value=g.num('Multiply',g.get('AudioBootSpeed'),.40),Min=84.,Max=192.)
    g.branch(g.num('GreaterEqual',g.get('AudioBootDistance'),stride))
    g.set('AudioBootDistance',0.)
    g.do(g.own('Audio_Footfall'))
    g.cursor=moving.find_else_pin()
    g.set('AudioBootDistance',0.)
    compile_bp(bp)


def music(bp, guide, sounds):
    g = Audio(bp, 'Audio_StartBed')
    g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
    g.branch(g.valid(g.pc()))
    g.branch(g.no(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
    for name, sound in (('AudioScore','S_FP_QuietSignal'), ('AudioLab','S_FP_LabAir'), ('AudioCity','S_FP_CityWind')):
        spawn=g.do(g.call('Engine.GameplayStatics.SpawnSound2D', Sound=sounds[sound], VolumeMultiplier=.001,
                         bAutoDestroy=False, bPersistAcrossLevelTransition=False))
        g.set(name, g.out(spawn))
    found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass', ActorClass=B.generated_class(guide).get_path_name()))
    g.set('AudioOmega', g.out(found))
    g.set('AudioBedStarted', True)
    compile_bp(bp)

    g = Audio(bp, 'Audio_UpdateBed')
    g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
    init=g.branch(g.no(g.get('AudioBedStarted')))
    g.do(g.own('Audio_StartBed'))
    g.cursor=init.find_else_pin()
    g.branch(g.valid(g.get('AudioScore')))
    g.branch(g.valid(g.get('AudioLab')))
    g.branch(g.valid(g.get('AudioCity')))
    y, z = (g.axis(g.location(), axis) for axis in ('Y','Z'))
    high = g.math('BooleanAND', A=g.num('Greater', y, 2510.), B=g.num('Greater', z, 2080.))
    outside = g.math('BooleanOR', A=high, B=g.num('Greater', y, 5100.))
    mix = g.math('SelectFloat', A=1., B=0., bPickA=outside)
    g.set('AudioOutdoor', g.math('FInterpTo', Current=g.get('AudioOutdoor'), Target=mix,
                                DeltaTime=g.dt(), InterpSpeed=.74))
    voice = g.branch(g.valid(g.get('AudioOmega')))
    read = g.node(g.e.add_get_member_variable_node('BusyUntil', B.generated_class(guide).get_path_name()))
    val(read.find_self_pin(),g.get('AudioOmega'))
    talking=g.num('Greater', pin(read,'BusyUntil',True), g.now())
    set_gain=g.set('AudioDuckTarget', g.math('SelectFloat', A=.31, B=1., bPickA=talking))
    g.cursor=voice.find_else_pin()
    fallback=g.set('AudioDuckTarget',1.)
    g.cursor=set_gain.find_then_pin()
    gain=g.set('AudioGain',g.math('FInterpTo',Current=g.get('AudioGain'),Target=g.get('AudioDuckTarget'),
                                 DeltaTime=g.dt(),InterpSpeed=3.))
    link(fallback.find_then_pin(),gain.find_execute_pin())
    outdoor=g.get('AudioOutdoor')
    for field,vol in (
        ('AudioScore',g.num('Multiply',g.get('AudioGain'),.58)),
        ('AudioLab',g.num('Multiply',g.num('Subtract',1.,outdoor),.42)),
        ('AudioCity',g.num('Multiply',outdoor,.54)),
    ):
        g.do(g.call('Engine.AudioComponent.SetVolumeMultiplier',target=g.get(field),NewVolumeMultiplier=vol))
    compile_bp(bp)

    g=Audio(bp,'Audio_UpdateFrame')
    g.do(g.own('Audio_UpdateFootsteps'))
    g.do(g.own('Audio_UpdateBed'))
    compile_bp(bp)
    g=Audio(bp)
    if not any(n.get_name()=='FPAtmosphereTick' for n in g.e.list_all_nodes()):
        hook(bp,g.e.find_event_node('ReceiveTick').find_then_pin(),'Audio_UpdateFrame','FPAtmosphereTick')


def player(bp, types, sounds):
    guide=A.load_asset(GUIDE)
    vec=B.get_struct_type(unreal.Vector.static_struct())
    audio=B.get_object_reference_type(unreal.AudioComponent)
    for name,kind,value in (
        ('AudioBootSurface','string',''),('AudioBootPlays','int','0'),
        ('AudioBootSpeed','real','0'),('AudioBootDistance','real','0'),
        ('AudioBootVariant','int','1'),('AudioBootLocation',vec,'(X=0,Y=0,Z=0)'),
        ('AudioBedStarted','bool','false'),('AudioGain','real','0'),
        ('AudioDuckTarget','real','1'),('AudioOutdoor','real','0'),
        ('AudioScore',audio,'None'),('AudioLab',audio,'None'),('AudioCity',audio,'None'),
        ('AudioOmega',B.get_object_reference_type(B.generated_class(guide)),'None'),
    ):
        var(bp,name,kind,value)
    compile_bp(bp)
    boot_surfaces(bp,types,sounds)
    music(bp,guide,sounds)
    compile_bp(bp)


def replace_sound(g, node, new_sound, att, gain, pitch):
    val(pin(node,'Sound'),new_sound)
    val(pin(node,'AttenuationSettings'),att)
    val(pin(node,'VolumeMultiplier'),gain)
    pitch_pin=pin(node,'PitchMultiplier')
    pitch_pin.break_pin_links()
    val(pitch_pin,g.math('RandomFloatInRange',Min=pitch[0],Max=pitch[1]))


def alternate_siege_step(g, step, sound, att, gain):
    if any(n.get_name() == 'FPAlternateStomp' for n in g.e.list_all_nodes()):
        return
    execute = step.find_execute_pin()
    before, = execute.list_connected_pins()
    location, = pin(step, 'Location').list_connected_pins()
    execute.break_pin_links()
    g.cursor = before
    parity = g.math('Percent_IntInt', A=g.get('LastStomp'), B=2)
    alternate = g.branch(g.math('EqualEqual_IntInt', A=parity, B=0))
    alternate.rename('FPAlternateStomp')
    link(alternate.find_else_pin(),execute)
    g.play(sound,location,gain,att,(.90,1.08))

def robot(bp, role, sounds, att):
    gait, weapon, stride, gain=role
    g=open_graph(bp,'Combat')
    nodes=[n for n in g.e.list_all_nodes() if n.find_input_pin('Sound').is_valid()
           and n.find_input_pin('AttenuationSettings').is_valid()]
    fire=next(n for n in nodes if 'S_ModeSelect' not in pin(n,'Sound').get_pin_value())
    replace_sound(g,fire,sounds['S_FP_Enemy'+weapon],att['Weapons'+('Siege' if gait=='Siege' else '')],
                  .67 if gait!='Siege' else .81,(.94,1.06))
    if gait=='Siege':
        g=open_graph(bp,'AnimateMachine')
        step=next(n for n in g.e.list_all_nodes() if n.find_input_pin('Sound').is_valid()
                  and n.find_input_pin('AttenuationSettings').is_valid())
        replace_sound(g,step,sounds['S_FP_MechSiege_1'],att['Siege'],gain,(.90,1.08))
        alternate_siege_step(g,step,sounds['S_FP_MechSiege_2'],att['Siege'],gain)
        compile_bp(bp)
        return

    for name,kind,value in (('AudioMechAt','real',str(stride)),('AudioMechSteps','int','0')):
        var(bp,name,kind,value)
    compile_bp(bp)
    g=Audio(bp,'Audio_MechFootfall')
    distance=g.get('DistanceMoved')
    g.branch(g.num('GreaterEqual',distance,g.get('AudioMechAt')))
    g.set('AudioMechAt',g.num('Add',distance,stride))
    target=g.player()
    g.branch(g.valid(target))
    dist=g.math('Vector_Distance',V1=g.location(),V2=g.location(target))
    g.branch(g.num('Less',dist,3700. if gait=='Heavy' else 2400.))
    g.count('AudioMechSteps')
    heel=g.offset(g.location(),g.num('Multiply',g.get('HullHeight'),-1.))
    parity=g.math('Percent_IntInt',A=g.get('AudioMechSteps'),B=2)
    leg=g.branch(g.math('EqualEqual_IntInt',A=parity,B=0))
    g.play(sounds['S_FP_Mech'+gait+'_1'],heel,gain,att[gait])
    g.cursor=leg.find_else_pin()
    g.play(sounds['S_FP_Mech'+gait+'_2'],heel,gain,att[gait])
    compile_bp(bp)
    graph=open_graph(bp,'MachineTick')
    anim=next(n for n in graph.e.list_all_nodes() if str(n.get_node_title()).replace(' ','')=='AnimateMachine')
    after(bp,'MachineTick',anim,'Audio_MechFootfall','FPMechAudio')
    compile_bp(bp)


def install():
    content=Path(unreal.Paths.project_content_dir())
    saved=Path(unreal.Paths.project_saved_dir())
    backup=saved/'Backups/FinalProtocolAudio'/datetime.now().strftime('%Y%m%d_%H%M%S')
    materials=['/Game/'+name for values in FLOORS.values() for name in values]
    for path in [PLAYER, LIFT, *(MACHINE+name for name in ROBOTS), *materials]:
        relative=Path(path.removeprefix('/Game/')+'.uasset')
        if (content/relative).exists():
            dest=backup/relative
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(content/relative,dest)
    sounds=install_sounds(content.parent/'SourceAssets/Soundscape')
    types=physical_materials()
    lift=A.load_asset(LIFT)
    cabin_floor=next(c for _,c,n in components(lift) if n=='CabinFloor')
    cabin_floor.set_phys_material_override(A.load_asset(ROOT+'/PM_FP_Metal'))
    compile_bp(lift)
    att={name: attenuation(name,radius,falloff) for name,radius,falloff in (
        ('Scout',160.,1720.), ('Heavy',240.,3100.), ('Siege',370.,5100.),
        ('Weapons',190.,3900.), ('WeaponsSiege',420.,6100.),
    )}
    pawn=A.load_asset(PLAYER)
    player(pawn,types,sounds)
    enemies=[]
    for name,settings in ROBOTS.items():
        bp=A.load_asset(MACHINE+name)
        robot(bp,settings,sounds,att)
        enemies.append(bp)
    for bp in (pawn,lift,*enemies):
        save(bp)
    unreal.log('Final Protocol soundscape installed')


if __name__=='__main__':
    install()



