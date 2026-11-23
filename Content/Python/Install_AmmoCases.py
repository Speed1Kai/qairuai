"""Create hinges, white interaction outlines, and checkpoint-aware ammunition cases."""
from array import array
from datetime import datetime
import json
import math
from pathlib import Path
import random
import shutil
from tempfile import TemporaryDirectory
import wave

import unreal

from CityCombat_Common import A, B, G, add, compile_bp, link, pin, save, val, var
from Install_DemoCheckpoint import JSON
from Install_EvacuationRelay import camera
from Install_StoryMemory import MAIN, MISSION, PLAYER, PROJECT, Story, bp_asset, insert_entry, load, setprop
from Shelter07_Waterworks import position

ROOT = '/Game/Story/AmmoCases'
CASE = ROOT+'/BP_AmmoCase'
OPEN = ROOT+'/Audio/S_AmmoCase_Open'
TAKE = ROOT+'/Audio/S_AmmoCase_Take'
MASK = 'AmmoCaseMask'
CUBE = '/Engine/BasicShapes/Cube'
CYLINDER = '/Engine/BasicShapes/Cylinder'
IND = '/Game/LabTutorial/Industrial/'
ARMOR = IND+'M_DoorArmor'
SCUFFED = IND+'M_DistressedMetal'
STEEL = '/Game/Surface/Materials/M_RuinSteel'
RUBBER = '/Game/Surface/Materials/M_Charcoal'
BRASS = '/Game/Surface/Materials/M_Oxide'
LATCH = '/Game/Surface/Materials/M_ExitAmber'
V = unreal.Vector

# Origin is the bottom of the case. Each bit is stable across saves.
CASES = (
    ('Armory', (-570., 551., 0.), 0., 1, 42, 0),
    ('Power', (3420., -1835., 0.), 0., 2, 24, 0),
    ('UpperBay', (3990., 372., 1150.), 0., 4, 30, 0),
    ('ShelterRadio', position(9.20,-1.48,-1.55), 0., 8, 120, 2),
)

def create_sound(folder, name, duration, events):
    rate = 44100
    samples = [0.] * int(duration * rate)
    generator = random.Random(name)
    for onset, decay, gain, frequency, rattle in events:
        smooth_noise = 0.
        start = int(onset * rate)
        length = min(int(decay*6*rate), len(samples)-start)
        for index in range(length):
            t = index/rate
            white = generator.uniform(-1., 1.)
            smooth_noise = .77*smooth_noise+.23*white
            envelope = (1.-math.exp(-t/.00048))*math.exp(-t/decay)
            tone = (.55*math.sin(math.tau*frequency*t) + .24*math.sin(math.tau*frequency*2.71*t)
                    + .12*math.sin(math.tau*frequency*4.13*t))
            samples[start+index] += gain*envelope*(tone+rattle*(white-smooth_noise))
    peak = max(abs(sample) for sample in samples)
    path = folder/(name+'.wav')
    with wave.open(str(path),'wb') as output:
        output.setparams((1,2,rate,0,'NONE','not compressed'))
        output.writeframes(array('h',(int(sample/peak*25800) for sample in samples)).tobytes())
    asset_path = ROOT+'/Audio/'+name
    if not A.does_asset_exist(asset_path):
        asset = unreal.AssetImportTask()
        asset.filename = str(path)
        asset.destination_path = ROOT+'/Audio'
        asset.automated = True
        asset.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([asset])
    assert isinstance(load(asset_path),unreal.SoundWave),asset_path

def sounds():
    with TemporaryDirectory(prefix='FinalProtocol_AmmoCase_') as folder:
        directory = Path(folder)
        create_sound(directory,'S_AmmoCase_Open',.93,(
            (.013,.027,.52,374.,.71),(.073,.019,.38,594.,.62),
            (.118,.021,.11,475.,.42),(.221,.089,.13,212.,.32),(.304,.070,.16,245.,.26),
            (.398,.061,.14,230.,.24),(.663,.050,.78,172.,.55),(.687,.034,.24,453.,.60)))
        create_sound(directory,'S_AmmoCase_Take',.40,(
            (.018,.024,.45,394.,.84),(.071,.038,.76,633.,.68),
            (.124,.025,.39,781.,.81),(.195,.035,.31,490.,.64)))

def geometry(bp):
    root='CaseRoot'
    add(bp,unreal.SceneComponent,root)
    hinge=add(bp,unreal.SceneComponent,'Hinge',root)
    hinge.set_mobility(unreal.ComponentMobility.MOVABLE)
    hinge.set_editor_property('relative_location',V(0,18,25.))
    add(bp,unreal.SceneComponent,'Contents',root)
    cube=load(CUBE)
    cylinder=load(CYLINDER)

    def mesh(name, where, size, mat, parent=root, tube=False, roll=0., offset=None):
        c=add(bp,unreal.StaticMeshComponent,name,parent)
        c.set_static_mesh(cylinder if tube else cube)
        if mat:
            c.set_material(0,load(mat))
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_location',V(*where))
        c.set_editor_property('relative_scale3d',V(*(d/100. for d in size)))
        if offset:
            c.set_editor_property('relative_rotation',offset)
        else:
            c.set_editor_property('relative_rotation',unreal.Rotator(roll=roll))
        c.set_collision_profile_name('NoCollision')
        c.set_custom_depth_stencil_value(253)
        return c

    mesh('CaseBottom',(0,0,2.6),(69,39,5.2),ARMOR)
    mesh('CaseFront',(0,-18.8,13.3),(70,2.8,25),ARMOR)
    mesh('CaseBack',(0,18.8,13.3),(70,2.8,25),ARMOR)
    for i,x in enumerate((-34.,34.)):
        mesh(f'CaseEnd{i}',(x,0,13.),(2.3,36,24),ARMOR)
        mesh(f'CaseCorner{i}',(x*.91,-20.25,13.5),(4.6,1.7,22),STEEL)
        mesh(f'CaseRib{i}',(x*.65,-20.55,11.3),(2.4,1.4,15),SCUFFED)
        mesh(f'CaseHinge{i}',(x*.67,19,24.8),(4.7,4.7,9.2),STEEL,tube=True,
             offset=unreal.Rotator(pitch=90.))
        mesh(f'CaseBaseRail{i}',(x*.74,0,1.),(5.4,40,3.8),RUBBER)
        mesh(f'LidLatch{i}',(x*.65,-37.4,-3.9),(5.4,3.9,11.3),STEEL,'Hinge')
    mesh('Lid',(0,-18.2,2.1),(70.2,39.9,4.2),ARMOR,'Hinge')
    mesh('LidInset',(0,-18.1,4.3),(58.1,29.7,2.0),SCUFFED,'Hinge')
    mesh('LidLeadingEdge',(0,-37.2,-.9),(69.8,3.2,4.1),STEEL,'Hinge')
    for i,x in enumerate((-25.,25.)):
        mesh(f'LidStrip{i}',(x,-18,5.2),(3.4,30.8,2.3),STEEL,'Hinge')
    mesh('CaseHandleLeft',(-9,-22,11),(3.7,6.5,5.1),STEEL)
    mesh('CaseHandleRight',(9,-22,11),(3.7,6.5,5.1),STEEL)
    mesh('CaseHandle',(0,-25,11),(20,3.5,4.2),RUBBER)
    mesh('StencilBacking',(0,-20.35,18.8),(29,.6,7.4),RUBBER)
    mesh('TagStripe',(25,-20.32,17.35),(9,.8,1.8),LATCH)

    mesh('Insert',(0,0,6.3),(60,31,3.4),RUBBER,'Contents')
    magazine=load('/Game/Combat/Firearms/SM_Hunter_Magazine')
    for index,x in enumerate((-20.,-7.,7.,20.)):
        c=mesh('Magazine'+str(index),(x,-1.,11.6),(46,43,48),None,'Contents',
               offset=unreal.Rotator(roll=90.,yaw=6. if index%2 else -6.))
        c.set_static_mesh(magazine)
        mesh('CaseDivider'+str(index),(x-4.8,1.,9.),(2.,27.,5.),SCUFFED,'Contents')
    for index,x in enumerate((-21.,-12.,-3.,6.,15.,24.)):
        mesh('Round'+str(index),(x,-11.2,13.8),(2.6,2.6,9.),BRASS,'Contents',True,90.)

    def text(name, msg, pos, size, active=True):
        label=add(bp,unreal.TextRenderComponent,name,root)
        label.set_editor_property('relative_location',V(*pos))
        label.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90.))
        label.set_text(unreal.Text(msg))
        label.set_world_size(size)
        label.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        label.set_text_render_color(unreal.Color(238,231,212,255))
        label.set_visibility(active)
    text('CaseStencil','SUPPLIES',(0,-20.85,18.3),5.2)
    text('OpenHint','F / OPEN',(0,-21.5,36.8),8.)
    text('TakeHint','F / AMMO',(0,-21.5,36.8),8.,False)
    text('EmptyHint','EMPTY',(0,-21.5,18.3),5.2,False)

    aim=add(bp,unreal.BoxComponent,'InteractionTrace',root)
    aim.set_editor_property('relative_location',V(0,0,14.5))
    aim.set_box_extent(V(37,22,15.8))
    aim.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    aim.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
    aim.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
    aim.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY,unreal.CollisionResponseType.ECR_BLOCK)
    aim.set_editor_property('generate_overlap_events',False)
    aim.set_editor_property('can_ever_affect_navigation',False)

def claimed(g, mask, bit):
    quotient=g.math('Divide_IntInt',A=mask,B=bit)
    return g.compare('EqualEqual',g.math('Percent_IntInt',A=quotient,B=2),1)

def hinge_rotation(g, angle):
    rotation=g.math('MakeRotator',Roll=angle,Pitch=0.,Yaw=0.)
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('Hinge'),
                NewRotation=rotation,bSweep=False,bTeleport=False))

def case_outline(g, enabled):
    for name in ('Lid','CaseFront','CaseEnd0','CaseEnd1'):
        g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=g.get(name),bValue=enabled))

def make_case():
    bp=bp_asset(CASE)
    geometry(bp)
    for name, kind, default in (
            ('CaseBit','int','1'),('CarbineRounds','int','30'),('EmitterCells','int','0'),
            ('CaseStage','int','0'),('OpeningAt','real','0'),('LoadedCaseState','bool','false'),('CaseTriggered','bool','false')):
        var(bp,name,kind,default)
    for member in ('CaseBit','CarbineRounds','EmitterCells'):
        # Clear DisableEditOnInstance so each placed box can carry a different supply.
        B.set_blueprint_variable_instance_editable(bp,member,True)
    for name in ('StartOpening','EmptyCase','AnimateLid','RestoreAmmoCase','UseCase'):
        Story(bp,name)
    compile_bp(bp)

    graph=Story(bp,'StartOpening')
    graph.branch(graph.compare('EqualEqual',graph.get('CaseStage'),0))
    graph.set('CaseStage',1)
    graph.set('OpeningAt',graph.now())
    graph.visibility('OpenHint',False)
    case_outline(graph,False)
    graph.sound(OPEN,graph.position(),.72)
    graph.do(graph.call('Engine.Actor.SetActorTickEnabled',bEnabled=True))

    graph=Story(bp,'EmptyCase')
    graph.set('CaseStage',3)
    hinge_rotation(graph,105.)
    for name in ('Contents','OpenHint','TakeHint','CaseStencil'):
        graph.visibility(name,False)
    graph.visibility('EmptyHint',True)
    case_outline(graph,False)
    graph.do(graph.call('Engine.Actor.SetActorTickEnabled',bEnabled=False))

    graph=Story(bp,'AnimateLid')
    graph.branch(graph.compare('EqualEqual',graph.get('CaseStage'),1))
    age=graph.num('Subtract',graph.now(),graph.get('OpeningAt'))
    amount=graph.math('FClamp',Value=graph.num('Divide',age,.73),Min=0.,Max=1.)
    smooth=graph.num('Multiply',graph.num('Multiply',amount,amount),
                     graph.num('Subtract',3.,graph.num('Multiply',2.,amount)))
    hinge_rotation(graph,graph.num('Multiply',smooth,105.))
    graph.branch(graph.num('GreaterEqual',amount,1.))
    graph.set('CaseStage',2)
    graph.visibility('TakeHint',True)
    graph.do(graph.call('Engine.Actor.SetActorTickEnabled',bEnabled=False))

    graph=Story(bp,'RestoreAmmoCase')
    mission=graph.out(graph.do(graph.call('Engine.GameplayStatics.GetActorOfClass',
                       ActorClass=B.generated_class(load(MISSION)).get_path_name())))
    graph.branch(graph.valid(mission))
    graph.branch(graph.compare('GreaterEqual',graph.ext(mission,'CheckpointBootState',MISSION),2))
    graph.set('LoadedCaseState',True)
    restored=graph.branch(claimed(graph,graph.ext(mission,MASK,MISSION),graph.get('CaseBit')))
    graph.do(graph.own('EmptyCase'))
    graph.cursor=restored.find_else_pin()
    state=graph.branch(graph.compare('EqualEqual',graph.get('CaseStage'),0))
    case_outline(graph,True)
    graph.do(graph.call('Engine.Actor.SetActorTickEnabled',bEnabled=False))
    graph.cursor=state.find_else_pin()
    graph.do(graph.own('AnimateLid'))

    graph=Story(bp,'UseCase')
    graph.branch(graph.get('CaseTriggered'))
    graph.set('CaseTriggered',False)
    stage=graph.get('CaseStage')
    closed=graph.branch(graph.compare('EqualEqual',stage,0))
    graph.do(graph.own('StartOpening'))
    graph.cursor=closed.find_else_pin()
    already_empty=graph.branch(graph.compare('EqualEqual',stage,3))
    graph.do(graph.call('Engine.Actor.SetActorTickEnabled',bEnabled=False))
    graph.cursor=already_empty.find_else_pin()
    graph.branch(graph.compare('EqualEqual',stage,2))
    mission_cls=B.generated_class(load(MISSION)).get_path_name()
    owner=graph.out(graph.do(graph.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=mission_cls)))
    graph.branch(graph.valid(owner))
    player=graph.ext(owner,'Player',MISSION)
    graph.branch(graph.valid(player))
    mask=graph.ext(owner,MASK,MISSION)
    bit=graph.get('CaseBit')
    duplicate=graph.branch(claimed(graph,mask,bit))
    graph.do(graph.own('EmptyCase'))
    graph.cursor=duplicate.find_else_pin()
    setprop(graph,owner,MASK,graph.math('Add_IntInt',A=mask,B=bit),'Int')
    for attr, member in (('HunterReserve','CarbineRounds'),('BreakerReserve','EmitterCells')):
        previous=graph.ext(player,attr,PLAYER)
        setprop(graph,player,attr,graph.math('Add_IntInt',A=previous,B=graph.get(member)),'Int')
    graph.do(graph.own('EmptyCase'))
    graph.sound(TAKE,graph.position(),.74)
    save_node=graph.node(graph.e.add_call_function_node(mission_cls+'.EvacSave'))
    val(save_node.find_self_pin(),owner)
    graph.do(save_node)

    graph=Story(bp)
    graph.override('ReceiveTick')
    loaded=graph.branch(graph.get('LoadedCaseState'))
    graph.do(graph.own('UseCase'))
    graph.do(graph.own('AnimateLid'))
    graph.cursor=loaded.find_else_pin()
    graph.do(graph.own('RestoreAmmoCase'))
    compile_bp(bp)
    unreal.get_default_object(B.generated_class(bp)).set_editor_property('tags',[unreal.Name('AmmoCase')])
    return bp

def use_cases(bp):
    g=Story(bp,'TryAmmoCase')
    g.set('UsedAmmoCase',False)
    player=g.get('Player')
    g.branch(g.valid(player))
    g.branch(g.not_(g.get('Failed')))
    g.branch(g.not_(g.pget('NavMapOpen')))
    controller=g.pc()
    g.branch(g.not_(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=controller))))
    eye, ray=camera(g)
    trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=eye,
                End=g.addv(eye,g.scale(ray,635.)),TraceChannel='TraceTypeQuery1',
                bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
    array_action=next(action for action in g.e.list_available_nodes([])
                      if str(action).split('|')[-1] in ('Сделатьмассив','MakeArray','Make Array'))
    ignored=g.node(g.e.create_node_from_name(array_action,unreal.Vector2D(),[]))
    val(pin(trace,'ActorsToIgnore'),pin(ignored,'Array',True))
    val(pin(ignored,'[0]'),player)
    parts=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'))
    g.branch(g.out(trace))
    impact=g.out(parts,'ImpactPoint')
    g.branch(g.num('LessEqual',g.distance(g.position(player),impact),178.))
    case=g.out(parts,'HitActor')
    g.branch(g.valid(case))
    g.branch(g.out(g.call('Engine.Actor.ActorHasTag',target=case,Tag='AmmoCase')))
    g.set('UsedAmmoCase',True)
    setprop(g,case,'CaseTriggered',True,'Bool')
    g.do(g.call('Engine.Actor.SetActorTickEnabled',target=case,bEnabled=True))

    def prepend(graph, old, tag):
        graph.do(graph.own('TryAmmoCase')).rename(tag)
        consumed=graph.branch(graph.get('UsedAmmoCase'))
        for prev in old:
            link(consumed.find_else_pin(),prev)
    insert_entry(bp,'RequestRecovery','OpenNearbyAmmoCase',prepend)

def store_mask(bp, method):
    g=Story(bp)
    g.e=G.get_graph_editor_by_name(bp,method)
    if any(n.get_name()=='SaveAmmoCaseMask' for n in g.e.list_all_nodes()):
        return
    writer=next(n for n in g.e.list_all_nodes()
                if n.find_input_pin('File').is_valid() and n.find_input_pin('JsonObject').is_valid())
    dest=writer.find_execute_pin()
    incoming=list(dest.list_connected_pins())
    data=pin(writer,'JsonObject').list_connected_pins()[0]
    # Two EvacSave paths converge on the same file write.
    dest.break_pin_links()
    g.cursor=incoming[0]
    field=g.do(g.call(JSON+'SetField',JsonObject=data,FieldName=MASK,Value=g.get(MASK)))
    field.rename('SaveAmmoCaseMask')
    for other in incoming[1:]:
        link(other,field.find_execute_pin())
    link(g.cursor,dest)

def load_mask(bp, method):
    g=Story(bp)
    g.e=G.get_graph_editor_by_name(bp,method)
    if any(n.get_name()=='LoadAmmoCaseMask' for n in g.e.list_all_nodes()):
        return
    rank=next(n for n in g.e.list_all_nodes()
              if n.get_class().get_name()=='K2Node_VariableSet'
              and n.find_input_pin('CheckpointWrittenRank').is_valid())
    read=next(n for n in g.e.list_all_nodes()
              if n.find_output_pin('OutJsonObject').is_valid() and n.find_input_pin('File').is_valid())
    dest=rank.find_execute_pin()
    g.cursor=dest.list_connected_pins()[0]
    dest.break_pin_links()
    g.set(MASK,0).rename('LoadAmmoCaseMask')
    data=g.out(read,'OutJsonObject')
    has=g.do(g.call(JSON+'HasField',JsonObject=data,FieldName=MASK))
    available=g.branch(g.out(has))
    field=g.do(g.call(JSON+'GetField',JsonObject=data,FieldName=MASK))
    typed=g.branch(g.out(field))
    g.set(MASK,g.out(field,'OutValue'))
    link(g.cursor,dest)
    link(available.find_else_pin(),dest)
    link(typed.find_else_pin(),dest)

def place(case):
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.load_level(MAIN)
    actor_system=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cls=B.generated_class(case)
    existing={actor.get_actor_label():actor for actor in actor_system.get_all_level_actors()}
    for name, origin, yaw, bit, rounds, cells in CASES:
        label='SUPPLY_AmmoCase_'+name
        actor=existing.get(label)
        if not actor:
            actor=actor_system.spawn_actor_from_class(cls,V(*origin),unreal.Rotator(yaw=yaw))
            assert actor,label
            actor.set_actor_label(label)
        else:
            assert actor.set_actor_location(V(*origin),False,True)
            actor.set_actor_rotation(unreal.Rotator(yaw=yaw),True)
        actor.set_editor_property('tags',[unreal.Name('AmmoCase')])
        actor.set_folder_path('LAB/05_Armory' if bit<8 else 'Campaign/Shelter 07')
        for member,value in (('CaseBit',bit),('CarbineRounds',rounds),('EmitterCells',cells)):
            actor.set_editor_property(member,value)
    assert levels.save_current_level()

def install():
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    backup=PROJECT/'Saved/Backups/AmmoCases'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for path,ext in ((MISSION,'.uasset'),(CASE,'.uasset'),(MAIN,'.umap')):
        rel=Path('Content')/(path[6:]+ext)
        dest=backup/rel
        if (PROJECT/rel).exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PROJECT/rel,dest)
    mission=load(MISSION)
    var(mission,MASK,'int','0')
    var(mission,'UsedAmmoCase','bool','false')
    Story(mission,'TryAmmoCase')
    compile_bp(mission)
    sounds()
    case=make_case()
    use_cases(mission)
    for method in ('DemoCheckpointWrite','EvacSave'):
        store_mask(mission,method)
    for method in ('DemoCheckpointLoadA','DemoCheckpointLoadB'):
        load_mask(mission,method)
    compile_bp(mission)
    save(case)
    save(mission)
    place(case)
    output=PROJECT/'Saved/AmmoCases'
    output.mkdir(exist_ok=True)
    (output/'Installed.json').write_text(json.dumps({'asset':CASE,'cases':CASES,'backup':str(backup)},
                                           indent=2),encoding='utf-8')

if __name__=='__main__':
    install()
