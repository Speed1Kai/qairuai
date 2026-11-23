"""Install and validate the first mission checkpoints on the existing Unreal levels."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal

from Install_StoryMemory import (A, B, G, DRONE, ENTRANCE, GUIDE, MAIN, MISSION, PLAYER, TERMINAL,
    L, Story, compile_bp, insert_entry, link, load, pin, save, setprop, val, var)
from Install_OwnFrequency import FIRST, SECOND, LOCK, LOBBY, WORKSHOP, END, CUT, HAND, RESCUE, DONE, SCREEN

POWER = '/Game/LabTutorial/Basement/BP_BuildingPower'
ROUTE = '/Game/Surface/HiddenExit/BP_HiddenLabRoute'
RECORD = '/Game/Story/DemoIntro/BP_DemoCheckpoint'
SLOTS = ('FP_DemoCheckpoint_v2_A.json', 'FP_DemoCheckpoint_v2_B.json')
JSON = 'JsonBlueprintUtilities.JsonBlueprintFunctionLibrary.'
FORMAT = 2
POWER_POINT = (3300, -1700, 107.15)
SURFACE = (6375, 3320, 2257.15)
PATROL_POINT = (5850, 36500, 2257)
POSITIONS = (POWER_POINT, SURFACE, PATROL_POINT, ENTRANCE, ENTRANCE, LOBBY, WORKSHOP, END)
GEAR = (
    ('OwnsCarbine', 'bool', 'Bool'), ('OwnsDischarge', 'bool', 'Bool'),
    ('ArmoryAmmoCollected', 'bool', 'Bool'), ('CyborgMode', 'int', 'Int'),
    ('HunterMagazine', 'int', 'Int'), ('HunterReserve', 'int', 'Int'),
    ('BreakerMagazine', 'int', 'Int'), ('BreakerReserve', 'int', 'Int'),
)
HEARD = ('Wake', 'Mission', 'Power', 'PowerReady', 'Upper', 'Archive', 'Courtyard', 'City', 'Recovery')
PICKUPS = tuple('/Game/LabTutorial/Armory/BP_Lab'+kind+'Pickup' for kind in ('Carbine', 'Discharge', 'Ammo'))

def generated(path):
    klass = A.load_blueprint_class(path)
    assert klass, path
    return klass

def actor_of(graph, klass):
    node = graph.do(graph.call('Engine.GameplayStatics.GetActorOfClass', ActorClass=klass))
    return graph.out(node)

def ordered(graph, extra, label):
    """Run an optional cosmetic operation and then rejoin the executive path."""
    gate = graph.branch(graph.valid(extra))
    label()
    tail = graph.cursor
    gate2 = graph.node(graph.e.add_branch_node())
    val(pin(gate2, 'Condition'), True)
    link(tail, gate2.find_execute_pin())
    link(gate.find_else_pin(), gate2.find_execute_pin())
    graph.cursor = gate2.find_then_pin()

def typeref(klass):
    return B.get_object_reference_type(klass)

def save_object():
    if A.does_asset_exist(RECORD):
        asset = load(RECORD)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.SaveGame)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'BP_DemoCheckpoint', RECORD.rsplit('/', 1)[0], unreal.Blueprint, factory)
    for name, kind, value in (
        ('FormatVersion', 'int', '0'), ('Milestone', 'int', '0'), ('PowerOn', 'bool', 'false'),
        ('RepairCapacity', 'real', '100'), ('PatrolSpared', 'bool', 'false'),
        ('Position', B.get_struct_type(unreal.Vector.static_struct()), L((0, 0, 0))),
        *[(name, kind, 'false' if kind == 'bool' else '0') for name, kind, _ in GEAR],
        *[('Heard'+cue, 'bool', 'false') for cue in HEARD],
    ):
        var(asset, name, kind, value)
    compile_bp(asset)
    return asset

def cast_record(graph, source):
    key = next(name for name in graph.e.list_available_nodes([]) if str(name).endswith('|Casting|CastToBP_DemoCheckpoint'))
    cast = graph.node(graph.e.create_node_from_name(key, unreal.Vector2D(), []))
    val(pin(cast, 'Object'), source)
    graph.do(cast)
    result = next(p for p in cast.list_all_pins() if str(p.get_pin_name()).startswith('As'))
    return result

def snapshot_get(graph, name, obj=None):
    return graph.ext(graph.get('CheckpointRecord') if obj is None else obj, name, RECORD)

def init_mission(mission):
    for name, kind, value in (
        ('CheckpointBootState', 'int', '0'), ('CheckpointWrittenRank', 'int', '0'),
        ('CheckpointRecord', typeref(generated(RECORD)), 'None'),
        ('CheckpointPowerActor', typeref(generated(POWER)), 'None'),
        ('CheckpointRouteActor', typeref(generated(ROUTE)), 'None'),
        ('CheckpointOpening', typeref(unreal.LevelSequenceActor), 'None'),
        ('CheckpointStreamDeadline', 'real', '0'),
        ('CheckpointOriginalSpawn', B.get_struct_type(unreal.Vector.static_struct()), L((0, 0, 0))),
    ):
        var(mission, name, kind, value)
    methods = ('DemoCheckpointTick', 'DemoCheckpointBoot', 'DemoCheckpointNewRun',
        'DemoCheckpointLoadA', 'DemoCheckpointLoadB', 'DemoCheckpointCapture', 'DemoCheckpointWrite',
        'DemoCheckpointApply', 'DemoCheckpointInventory', 'DemoCheckpointRadio')
    for name in methods:
        if name not in map(str, B.list_graph_names(mission)):
            G.create_and_edit_function_graph(mission, name)
    for name in ('DemoCheckpointLoadA', 'DemoCheckpointLoadB'):
        Story(mission,name)
    compile_bp(mission)

def restore_power(power):
    graph = Story(power, 'DemoCheckpointRestorePower')
    graph.branch(graph.not_(graph.get('bBuildingPowered')))
    graph.set('bBuildingPowered', True)
    graph.do(graph.call('Engine.SceneComponent.K2_SetRelativeRotation', target=graph.get('SwitchLever'),
                        NewRotation='(Pitch=50,Yaw=0,Roll=0)', bSweep=False, bTeleport=False))
    graph.do(graph.call('Engine.AudioComponent.FadeIn', target=graph.get('GeneratorAudio'),
                        FadeInDuration=.4, FadeVolumeLevel=.3, StartTime=0))
    for name in sorted(map(str, B.list_member_variable_names(power))):
        if name.startswith('CircuitLight_'):
            light = graph.get(name)
            ordered(graph, light, lambda: graph.do(graph.call('Engine.Actor.SetActorHiddenInGame',
                                                             target=light, bNewHidden=False)))
        elif name.startswith('CircuitSurface_'):
            surface = graph.get(name)
            ordered(graph, surface, lambda: graph.do(graph.call('Engine.MeshComponent.SetScalarParameterValueOnMaterials',
                       target=surface, ParameterName='BuildingPower', ParameterValue=1.)))
        elif name.startswith('PowerNotice_'):
            notice = graph.get(name)
            caption = graph.out(graph.call('Engine.KismetTextLibrary.Conv_StringToText',
                          InString='ПИТАНИЕ ВОССТАНОВЛЕНО · Л-1 ЗАБЛОКИРОВАН'))
            ordered(graph, notice, lambda: graph.do(graph.call('Engine.TextRenderComponent.K2_SetText', target=notice, Value=caption)))
    compile_bp(power)

def concat(graph, a, b):
    return graph.out(graph.call('Engine.KismetStringLibrary.Concat_StrStr', A=a, B=b))

def file_path(graph, slot):
    saved = graph.out(graph.call('Engine.KismetSystemLibrary.GetProjectSavedDirectory'))
    return concat(graph, saved, slot)

def file_struct(graph, path):
    key = next(name for name in graph.e.list_available_nodes([])
               if str(name).endswith('|MakeFilePath'))
    node = graph.node(graph.e.create_node_from_name(key, unreal.Vector2D(), []))
    val(pin(node, 'FilePath'), path)
    result = node.find_output_pin('FilePath')
    return result if result.is_valid() else node.list_all_pins()[0]

def integer_json(graph, payload):
    fields = '{'
    for index, (name, number) in enumerate(payload):
        if index:
            fields = concat(graph, fields, ',')
        fields = concat(graph, fields, '"'+name+'":')
        value = graph.out(graph.call('Engine.KismetStringLibrary.Conv_IntToString', InInt=number))
        fields = concat(graph, fields, value)
    return concat(graph, fields, '}')

def int_bool(graph, value):
    return graph.math('SelectInt', A=1, B=0, bPickA=value)

def write_graphs(mission):
    g = Story(mission, 'DemoCheckpointWrite')
    entry = g.e.find_graph_entry_pin().get_owning_node()
    rank = entry.find_output_pin('Milestone')
    if not rank.is_valid():
        rank = g.e.add_graph_input_parameter('Milestone', B.get_basic_type_by_name('int'))
    position = entry.find_output_pin('SafePosition')
    if not position.is_valid():
        position = g.e.add_graph_input_parameter('SafePosition', B.get_struct_type(unreal.Vector.static_struct()))
    g.branch(g.compare('Greater', rank, g.get('CheckpointWrittenRank')))
    data = [('FormatVersion',FORMAT), ('Milestone',rank), ('PowerOn',1),
            ('RepairCapacity',g.math('Round',A=g.pget('VisorMaxIntegrity'))),
            ('PatrolSpared',int_bool(g,g.get('PatrolPassedPeacefully')))]
    data += [(axis,g.math('Round',A=g.axis(position,axis))) for axis in 'XYZ']
    data += [(name,int_bool(g,g.pget(name)) if kind=='bool' else g.pget(name)) for name,kind,_ in GEAR]
    data += [('Heard'+cue,int_bool(g,g.ext(g.get('Guide'),'Heard'+cue,GUIDE))) for cue in HEARD]
    parsed = g.do(g.call(JSON+'FromString', JsonString=integer_json(g,data)))
    g.branch(g.out(parsed))
    ordinal = g.math('Percent_IntInt', A=rank, B=2)
    slot = g.math('SelectString', A=SLOTS[0], B=SLOTS[1], bPickA=g.compare('EqualEqual', ordinal, 0))
    saved = g.do(g.call(JSON+'ToFile', JsonObject=g.out(parsed,'OutJsonObject'), File=file_struct(g,file_path(g,slot))))
    g.branch(g.out(saved))
    g.set('CheckpointWrittenRank', rank)
    compile_bp(mission)

    g = Story(mission, 'DemoCheckpointCapture')
    g.branch(g.valid(g.get('Player')))
    g.branch(g.valid(g.get('Guide')))
    g.branch(g.valid(g.get('CheckpointPowerActor')))
    g.branch(g.ext(g.get('CheckpointPowerActor'), 'bBuildingPowered', POWER))
    g.branch(g.not_(g.get('Failed')))
    g.branch(g.num('Greater', g.pget('VisorIntegrity'), 0.))
    phase = g.get('FrequencyStep')
    recovered = g.both(g.isstage(6), g.get('RecoveryGranted'))
    stable = (
        g.both(g.isstage(0), g.not_(g.pget('DemoReachedSurface'))),
        g.both(g.isstage(0), g.pget('DemoReachedSurface')),
        g.isstage(2),
        g.both(g.isstage(3), g.compare('EqualEqual', g.get('CheckpointStage'), 3)),
        g.both(recovered, g.compare('EqualEqual', phase, 0)),
        g.both(recovered, g.compare('EqualEqual', phase, 1)),
        g.both(recovered, g.compare('EqualEqual', phase, 2)),
        g.both(recovered, g.compare('EqualEqual', phase, 4)),
    )
    for rank_value, (condition, point) in enumerate(zip(stable, POSITIONS), 1):
        choice = g.branch(condition)
        node = g.own('DemoCheckpointWrite')
        val(pin(node, 'Milestone'), rank_value)
        val(pin(node, 'SafePosition'), L(point))
        g.do(node)
        g.cursor = choice.find_else_pin()
    compile_bp(mission)

def load_graphs(mission):
    for name, slot in zip(('DemoCheckpointLoadA', 'DemoCheckpointLoadB'), SLOTS):
        g = Story(mission, name)
        path = file_path(g,slot)
        g.branch(g.out(g.call('Engine.BlueprintPathsLibrary.FileExists', InPath=path)))
        read = g.do(g.call(JSON+'FromFile', File=file_struct(g,path)))
        g.branch(g.out(read))
        data = g.out(read,'OutJsonObject')
        def required(field):
            node = g.do(g.call(JSON+'GetField', JsonObject=data, FieldName=field))
            g.branch(g.out(node))
            local = 'Loaded'+field
            if local not in map(str,g.e.list_local_variable_names()):
                assert g.e.add_local_variable(local,B.get_basic_type_by_name('int'),'0')
            reader = g.node(g.e.add_set_local_variable_node(local))
            val(pin(reader,local),g.out(node,'OutValue'))
            g.do(reader)
            return pin(g.node(g.e.add_get_local_variable_node(local)),local,True)
        version = required('FormatVersion')
        g.branch(g.compare('EqualEqual',version,FORMAT))
        rank = required('Milestone')
        g.branch(g.compare('Greater', rank, g.get('CheckpointWrittenRank')))
        g.branch(g.compare('LessEqual', rank, len(POSITIONS)))
        g.branch(g.compare('EqualEqual',required('PowerOn'),1))
        new = g.do(g.call('Engine.GameplayStatics.CreateSaveGameObject', SaveGameClass=generated(RECORD).get_path_name()))
        record = cast_record(g,g.out(new))
        for field, value, kind in (
            ('FormatVersion',version,'Int'),('Milestone',rank,'Int'),('PowerOn',True,'Bool'),
            ('RepairCapacity',required('RepairCapacity'),'Double'),
            ('PatrolSpared',g.compare('EqualEqual',required('PatrolSpared'),1),'Bool'),
            ('Position',g.vector(*(required(axis) for axis in 'XYZ')),'Vector'),
        ):
            setprop(g,record,field,value,kind)
        for field, value_type, kind in GEAR:
            value=required(field)
            if value_type=='bool':
                value=g.compare('EqualEqual',value,1)
            setprop(g,record,field,value,kind)
        for cue in HEARD:
            field='Heard'+cue
            setprop(g,record,field,g.compare('EqualEqual',required(field),1),'Bool')
        g.set('CheckpointRecord', record)
        g.set('CheckpointWrittenRank', rank)
        compile_bp(mission)

def restore_inventory(mission):
    g = Story(mission, 'DemoCheckpointInventory')
    for name, _, kind in GEAR:
        g.pset(name, snapshot_get(g, name), kind)
    g.pcall('Weapon_Sync')
    for (member, _, _), path in zip(GEAR[:3], PICKUPS):
        gate = g.branch(g.pget(member))
        pickup = actor_of(g, generated(path).get_path_name())
        ordered(g, pickup, lambda: g.do(g.call('Engine.Actor.K2_DestroyActor', target=pickup)))
        join = g.node(g.e.add_branch_node())
        val(pin(join, 'Condition'), True)
        link(g.cursor, join.find_execute_pin())
        link(gate.find_else_pin(), join.find_execute_pin())
        g.cursor = join.find_then_pin()
    for cue in HEARD:
        setprop(g, g.get('Guide'), 'Heard'+cue, snapshot_get(g, 'Heard'+cue), 'Bool')
    compile_bp(mission)

def restore_radio(mission):
    g = Story(mission, 'DemoCheckpointRadio')
    rank = g.get('CheckpointWrittenRank')
    g.branch(g.compare('GreaterEqual', rank, 6))
    g.visibility('UplinkBeacon', False)
    g.visibility('UplinkGlow', False)
    def screen(component, material):
        g.do(g.call('Engine.PrimitiveComponent.SetMaterial', target=g.get(component),
                    ElementIndex=0, Material=SCREEN+'/MI_'+material))
    screen('TrackingDisplay07', 'Quiet')
    g.branch(g.compare('GreaterEqual', rank, 7))
    screen('BroadcastDisplay07', 'OnAir')
    for stripe in range(4):
        g.visibility('EscapeStripe'+str(stripe), True)
    g.branch(g.compare('EqualEqual', rank, 8))
    screen('MedicalDisplay', 'Open')
    g.visibility('ReserveLight', True)
    g.do(g.call('Engine.SceneComponent.SetRelativeScale3D', target=g.get('MedicalRoll'), NewScale3D=L((1, 1, .05))))
    compile_bp(mission)

def recover_graph(mission):
    g = Story(mission, 'DemoCheckpointApply')
    rank = g.get('CheckpointWrittenRank')
    target = g.get('CheckpointPowerActor')
    apply_power = g.node(g.e.add_call_function_node(generated(POWER).get_path_name()+'.DemoCheckpointRestorePower'))
    val(apply_power.find_self_pin(), target)
    g.do(apply_power)
    g.do(g.own('DemoCheckpointInventory'))
    capacity = g.math('FClamp', Value=snapshot_get(g, 'RepairCapacity'), Min=100., Max=125.)
    g.pset('VisorMaxIntegrity', capacity)
    g.pset('VisorIntegrity', capacity)
    g.pset('VisorEnergy', g.pget('VisorMaxEnergy'))
    for module in ('Head', 'Core', 'ArmL', 'ArmR', 'LegL', 'LegR'):
        g.pset('Module'+module+'HP', 100.)
    repaired = g.compare('GreaterEqual', rank, 5)
    finished = g.compare('EqualEqual', rank, 8)
    g.pset('DemoReachedSurface', g.compare('GreaterEqual', rank, 2), 'Bool')
    g.pset('NavMemoryReady', repaired, 'Bool')
    g.pset('NavMapOpen', False, 'Bool')
    g.pset('FrequencyFinished', finished, 'Bool')
    g.set('RecoveryGranted', repaired)
    g.set('PatrolPassedPeacefully', snapshot_get(g, 'PatrolSpared'))
    g.do(g.own('DemoCheckpointRadio'))
    guard = g.branch(repaired)
    g.pset('NavTargetIndex', 3, 'Int')
    g.pcall('Story_TagMemory')
    join = g.set('CheckpointMax', capacity)
    link(guard.find_else_pin(), join.find_execute_pin())

    resume = (
        (0, 0, None, POWER_POINT, 0),
        (0, 0, None, SURFACE, 90),
        (2, 0, ('Станция 07 · минуй патруль по флангу или вступи в бой', (5850, 44500, 2257)), PATROL_POINT, 90),
        (3, 0, ('Приёмная станции · F у сервисного терминала', TERMINAL), ENTRANCE, 0),
        (6, 0, (CUT, FIRST), ENTRANCE, 0),
        (6, 1, (HAND, SECOND), LOBBY, 0),
        (6, 2, (RESCUE, LOCK), WORKSHOP, -90),
        (6, 4, (DONE, LOCK), END, 0),
    )
    for index, (stage, frequency, objective, position, yaw) in enumerate(resume, 1):
        choice = g.branch(g.compare('EqualEqual', rank, index))
        g.set('Stage', stage)
        g.set('FrequencyStep', frequency)
        g.set('FrequencyReplay', False)
        g.set('CheckpointStage', stage)
        g.set('CheckpointReady', stage >= 2)
        g.set('CheckpointPosition', L(position))
        if objective:
            g.goal(*objective)
        if index == 8:
            g.pset('StoryGoalActive', False, 'Bool')
        if index >= 3:
            patrol = actor_of(g, generated(DRONE).get_path_name())
            g.set('Patrol', patrol)
            if index >= 4:
                dead = g.branch(g.not_(snapshot_get(g, 'PatrolSpared')))
                g.clear_enemy('Patrol')
                merge = g.set('Beat', 0)
                link(dead.find_else_pin(), merge.find_execute_pin())
        stored = snapshot_get(g,'Position')
        near_saved = g.num('Less',g.distance(stored,L(position)),1.5)
        safe_position = g.select(stored,L(position),near_saved)
        finish_restore(g, safe_position, yaw)
        g.set('CheckpointBootState', 2)
        g.cursor = choice.find_else_pin()
    compile_bp(mission)

def movement(graph, mode):
    graph.do(graph.call('Engine.CharacterMovementComponent.SetMovementMode',
                        target=graph.ext(graph.get('Player'), 'CharacterMovement'), NewMovementMode=mode))

def controls(graph, paused):
    for motion in ('Move', 'Look'):
        graph.do(graph.call('Engine.Controller.SetIgnore'+motion+'Input', target=graph.pc(), **{'bNew'+motion+'Input': paused}))

def move_player(graph, position):
    graph.do(graph.call('Engine.Actor.K2_SetActorLocation', target=graph.get('Player'), NewLocation=position,
                         bSweep=False, bTeleport=True))

def camera(graph):
    return graph.out(graph.call('Engine.GameplayStatics.GetPlayerCameraManager', PlayerIndex=0))

def finish_restore(graph, position, yaw):
    move_player(graph, position)
    graph.do(graph.call('Engine.Controller.SetControlRotation', target=graph.pc(),
                        NewRotation=graph.math('MakeRotator', Roll=0., Pitch=0., Yaw=float(yaw))))
    movement(graph, 'MOVE_Walking')
    controls(graph, False)
    graph.do(graph.call('Engine.PlayerCameraManager.StartCameraFade', target=camera(graph),
                       FromAlpha=1., ToAlpha=0., Duration=.45, bHoldWhenFinished=False))

def boot_graphs(mission):
    g = Story(mission, 'DemoCheckpointNewRun')
    g.set('CheckpointBootState', 2)
    player = g.out(g.call('LevelSequence.LevelSequenceActor.GetSequencePlayer', target=g.get('CheckpointOpening')))
    g.do(g.call('MovieScene.MovieSceneSequencePlayer.Play', target=player))
    compile_bp(mission)

    g = Story(mission, 'DemoCheckpointBoot')
    g.do(g.own('FindActors'))
    g.branch(g.valid(g.get('Player')))
    g.branch(g.valid(g.get('Guide')))
    g.set('CheckpointPowerActor', actor_of(g, generated(POWER).get_path_name()))
    g.set('CheckpointRouteActor', actor_of(g, generated(ROUTE).get_path_name()))
    g.set('CheckpointOpening', actor_of(g, '/Script/LevelSequence.LevelSequenceActor'))
    for name in ('CheckpointPowerActor', 'CheckpointRouteActor', 'CheckpointOpening'):
        g.branch(g.valid(g.get(name)))
    g.do(g.own('DemoCheckpointLoadA'))
    g.do(g.own('DemoCheckpointLoadB'))
    loaded = g.branch(g.valid(g.get('CheckpointRecord')))
    g.cursor = loaded.find_else_pin()
    g.do(g.own('DemoCheckpointNewRun'))
    g.cursor = loaded.find_then_pin()
    g.set('CheckpointOriginalSpawn', g.position(g.get('Player')))
    controls(g, True)
    movement(g, 'MOVE_None')
    g.do(g.call('Engine.PlayerCameraManager.StartCameraFade', target=camera(g),
                FromAlpha=1., ToAlpha=1., Duration=0., bHoldWhenFinished=True))
    outside = g.branch(g.compare('GreaterEqual', g.get('CheckpointWrittenRank'), 2))
    g.cursor = outside.find_else_pin()
    g.do(g.own('DemoCheckpointApply'))
    g.cursor = outside.find_then_pin()
    # The authored route preloads at this height. Movement remains frozen until visible.
    move_player(g, L(SURFACE))
    g.set('CheckpointStreamDeadline', g.num('Add', g.now(), 45.))
    g.set('CheckpointBootState', 1)
    compile_bp(mission)

    g = Story(mission, 'DemoCheckpointTick')
    initial = g.branch(g.compare('EqualEqual', g.get('CheckpointBootState'), 0))
    g.do(g.own('DemoCheckpointBoot'))
    g.cursor = initial.find_else_pin()
    waiting = g.branch(g.compare('EqualEqual', g.get('CheckpointBootState'), 1))
    deadline = g.branch(g.num('GreaterEqual', g.now(), g.get('CheckpointStreamDeadline')))
    finish_restore(g, g.get('CheckpointOriginalSpawn'), 0)
    g.set('CheckpointRecord', 'None')
    g.set('CheckpointWrittenRank', 0)
    g.do(g.own('DemoCheckpointNewRun'))
    g.cursor = deadline.find_else_pin()
    stream = g.ext(g.get('CheckpointRouteActor'), 'CampusStreaming', ROUTE)
    g.branch(g.valid(stream))
    g.branch(g.out(g.call('Engine.LevelStreaming.IsLevelVisible', target=stream)))
    g.do(g.own('DemoCheckpointApply'))
    g.cursor = waiting.find_else_pin()
    g.do(g.own('DemoCheckpointCapture'))
    compile_bp(mission)


def campaign_save_enabled(g):
    mode=g.out(g.call('Engine.GameplayStatics.GetGameMode'))
    field=g.e.add_get_member_variable_node('OptionsString','/Script/Engine.GameModeBase')
    val(field.find_self_pin(),mode)
    options=pin(field,'OptionsString',True)
    return g.not_(g.out(g.call('Engine.GameplayStatics.HasOption',Options=options,InKey='FPReplay')))

def install_front_end_guard(mission):
    for function in ('DemoCheckpointLoadA','DemoCheckpointLoadB','DemoCheckpointWrite'):
        def guard(g,old,tag):
            gate=g.branch(campaign_save_enabled(g))
            gate.rename(tag)
            for p in old:
                link(g.cursor,p)
        insert_entry(mission,function,'FrontEndReplayGuard',guard)
    compile_bp(mission)



def entry_hook(mission):
    def inject(g, old, tag):
        runner = g.do(g.own('DemoCheckpointTick'))
        runner.rename(tag)
        g.branch(g.compare('EqualEqual', g.get('CheckpointBootState'), 2))
        for previous in old:
            link(g.cursor, previous)
    insert_entry(mission, 'MissionTick', 'DemoCheckpointEntry', inject)
    compile_bp(mission)

def install():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    actor_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    save_utils = unreal.EditorLoadingAndSavingUtils
    assert not editor.get_game_world()
    assert editor.get_editor_world().get_path_name().split('.')[0] == MAIN or levels.load_level(MAIN)
    existing = {MISSION, POWER, RECORD}
    dirty = {package.get_name() for package in save_utils.get_dirty_content_packages()}
    assert not dirty.intersection(existing), dirty.intersection(existing)
    assert not save_utils.get_dirty_map_packages()
    sequences = [actor for actor in actor_editor.get_all_level_actors() if isinstance(actor, unreal.LevelSequenceActor)]
    opening, = sequences
    assert opening.get_actor_label() == 'INTRO_OpeningSequence'
    project = Path(unreal.Paths.project_dir()).resolve()
    backup = project/'Saved/Backups/DemoCheckpoint'/datetime.now().strftime('%Y%m%d-%H%M%S_%f')
    for package in (MISSION, POWER, MAIN, RECORD):
        rel = Path('Content')/(package.removeprefix('/Game/')+('.umap' if package == MAIN else '.uasset'))
        source = project/rel
        if source.is_file():
            dest = backup/rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
    record = save_object()
    mission, power = load(MISSION), load(POWER)
    init_mission(mission)
    restore_power(power)
    write_graphs(mission)
    load_graphs(mission)
    install_front_end_guard(mission)
    restore_inventory(mission)
    restore_radio(mission)
    recover_graph(mission)
    boot_graphs(mission)
    entry_hook(mission)
    for asset in (record, power, mission):
        save(asset)
    settings = opening.get_editor_property('playback_settings')
    opening.modify()
    settings.set_editor_property('auto_play', False)
    opening.set_editor_property('playback_settings', settings)
    assert save_utils.save_map(editor.get_editor_world(), MAIN)
    report = dict(backup=str(backup), compiled=[RECORD, POWER, MISSION], map=MAIN,
                  slots=list(SLOTS), runtime='Blueprint + Unreal JsonBlueprintUtilities')
    return report

if __name__ == '__main__':
    out = Path(unreal.Paths.project_dir()).resolve()/'Saved/DemoCheckpoint'
    out.mkdir(exist_ok=True)
    (out/'Installed.json').write_text(json.dumps(install(), ensure_ascii=False, indent=2), encoding='utf8')





