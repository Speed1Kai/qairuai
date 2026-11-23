"""Add the evacuation relay chapter to the existing streamed-city mission."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal

from CityCombat_Common import B, G, add, compile_bp, link, pin, save, val, var
from Install_StoryMemory import L, MISSION, PROJECT, Story, insert_entry, load
from Install_DemoCheckpoint import JSON, SLOTS, campaign_save_enabled, file_path, file_struct
from Install_SecondVoice import OUT
from Install_VisorSubtitles import publish_fields

TITLE = 'СПИСОК ОСТАВШИХСЯ'
PANEL = (32898, 83630, 2315)
BOARD = (32918, 83220, 2322)
RADIO = (32918, 83930, 2315)
LEVER = (32929, 83630, 2373)
LEADS = (
    ('A', (32920, 83596, 2318), (32920, 83664, 2339), (32899, 83568, 2357), '1   LINK',
     '/Game/LabTutorial/Industrial/M_DoorStatus_Green'),
    ('B', (32920, 83664, 2288), (32920, 83596, 2303), (32899, 83692, 2357), '2   POWER',
     '/Game/LabTutorial/Industrial/M_AmberIndicator'),
)
STEEL = '/Game/Surface/Materials/M_RuinSteel'
DARK = '/Game/Surface/Materials/M_Charcoal'
ARMOR = '/Game/LabTutorial/Industrial/M_DoorArmor'
RED = '/Game/LabTutorial/Industrial/M_DoorStatus_Red'
GREEN = '/Game/LabTutorial/Industrial/M_DoorStatus_Green'
STAGES = (
    (1, BOARD, 'Прочитай табель у эвакуационного реле'),
    (2, LEVER, 'Обесточь щиток: наведи прицел на рычаг и нажми F'),
    (4, LEVER, 'Подними рычаг: наведи прицел и удерживай F'),
    (5, RADIO, 'Проверь переговорное устройство у таблички «Пост 12»'),
)
CUES = {
    'Dispatch': ('[РАДИОСИГНАЛ] РАДИСТ · УБЕЖИЩЕ 07',
                 'Техник вспомнил последний вызов. Пост двенадцать, у эвакуационного проезда. Осмотри табель у реле.'),
    'Roster': ('ЭВАКУАЦИОННЫЙ ТАБЕЛЬ',
               'Рейс ушёл. Пост 12 остался на земле. Последний вызов оборвался, когда погасло реле.'),
    'Reply': ('[РАДИОСИГНАЛ] ПОСТ 12',
              'Слышим вас. Мы трое, в старой проходной. На посадку не успели. Вода кончается. Вы правда можете добраться до нас?'),
    'Next': ('[РАДИОСИГНАЛ] РАДИСТ · УБЕЖИЩЕ 07',
             'Пост двенадцать, оставайтесь на линии. Я передам медику, что вы живы. Сентинел, ищи выход к старой проходной.'),
}


def hardware(bp):
    cube = load('/Engine/BasicShapes/Cube')
    cylinder = load('/Engine/BasicShapes/Cylinder')
    materials = {p: load(p) for p in (ARMOR, STEEL, DARK, RED, GREEN, *(lead[-1] for lead in LEADS))}
    add(bp, unreal.SceneComponent, 'EvacuationSite', 'Root')

    def part(name, pos, size, material, shape=cube, rotation=None):
        component = add(bp, unreal.StaticMeshComponent, 'Evac' + name, 'EvacuationSite')
        component.set_static_mesh(shape)
        component.set_material(0, materials[material])
        component.set_collision_profile_name('NoCollision')
        component.set_custom_depth_stencil_value(253)
        component.set_editor_property('relative_location', unreal.Vector(*pos))
        component.set_editor_property('relative_scale3d', unreal.Vector(*(x / 100 for x in size)))
        if rotation:
            component.set_editor_property('relative_rotation', rotation)
        return component

    def sign(name, text, pos, size):
        # Text faces the pavement, from the same side as the plugs.
        component = add(bp, unreal.TextRenderComponent, 'Evac' + name, 'EvacuationSite')
        component.set_text(unreal.Text(text))
        component.set_world_size(size)
        component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        component.set_text_render_color(unreal.Color(240, 228, 193, 255))
        component.set_editor_property('relative_location', unreal.Vector(*pos))
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        return component

    def tube(name, a, b, diameter, material, visible=True):
        start, end = unreal.Vector(*a), unreal.Vector(*b)
        d = end - start
        middle = (start + end) * .5
        # The engine cylinder's long axis is Z.
        c = part(name, (middle.x, middle.y, middle.z), (diameter, diameter, d.length()),
                 material, cylinder, unreal.MathLibrary.make_rot_from_z(d))
        c.set_visibility(visible, False)
        return c

    for name, y in (('Panel', PANEL[1]), ('Board', BOARD[1]), ('Radio', RADIO[1])):
        for j, offset in enumerate((-30, 30)):
            part(f'{name}Foot{j}', (32889, y+offset, 2187), (42, 24, 13), STEEL)
            part(f'{name}Leg{j}', (32888, y+offset, 2242), (11, 11, 112), STEEL)
    part('Housing', PANEL, (27, 171, 136), ARMOR)
    part('Backing', (32912, 83630, 2315), (5, 155, 124), DARK)
    part('Cap', (32902, 83630, 2387), (43, 181, 13), STEEL)
    for y in (83547, 83713):
        part('Edge' + str(y), (32915, y, 2315), (17, 5, 133), STEEL)
    part('LeverMount', (32918, LEVER[1], LEVER[2]), (11, 37, 17), ARMOR)
    part('Lever', LEVER, (9, 9, 29), LEADS[1][-1], rotation=unreal.Rotator(pitch=32))
    part('Status', (32921, 83562, 2370), (4, 16, 7), RED)
    sign('PanelName', 'EVAC  /  RELAY', (32926, 83630, 2398), 8)
    sign('LeverLegend', '0   /   I', (32928, 83631, 2355), 6)
    part('BoardBacking', (32900, BOARD[1], BOARD[2]), (18, 134, 92), ARMOR)
    sign('BoardName', 'EVACUATION', (32912, BOARD[1], BOARD[2]+27), 10)
    sign('BoardPlate', 'POST 12\nLAST CALL\nLINE LOST', (32913, BOARD[1], BOARD[2]+7), 7)
    part('RadioHousing', (32901, RADIO[1], RADIO[2]), (16, 83, 77), ARMOR)
    part('Speaker', (32912, RADIO[1]+6, RADIO[2]+3), (8, 46, 39), DARK)
    for i in range(6):
        part('Vent'+str(i), (32917, RADIO[1]+6, RADIO[2]-13+i*6), (2, 39, 2), STEEL)
    part('RadioStatus', (32920, RADIO[1]-27, RADIO[2]+11), (4, 6, 11), RED)
    sign('RadioName', 'POST 12  /  INTERCOM', (32914, RADIO[1], RADIO[2]+30), 6.7)
    for index, (key, source, target, anchor, legend, color) in enumerate(LEADS, 1):
        part(key+'Socket', (target[0]-3, target[1], target[2]), (7, 18, 13) if index == 1 else (7, 12, 16), color)
        part(key+'Port', (target[0]+1, target[1], target[2]), (3, 10, 6) if index == 1 else (3, 5, 10), DARK)
        part(key+'Plug', source, (11, 16, 10) if index == 1 else (11, 10, 16), color)
        part(key+'Lug', (anchor[0]+10, anchor[1], anchor[2]), (14, 13, 12), ARMOR)
        sign(key+'HomeLabel', str(index), (32926, source[1], source[2]-11), 6)
        sign(key+'SocketLabel', legend, (32927, target[1], target[2]+10), 5.7)
        root = (32923, anchor[1], anchor[2])
        elbow = (32925, anchor[1], source[2]-10)
        tube(key+'Drop', root, elbow, 3.2, DARK)
        tube(key+'Lead', elbow, source, 3.2, color)
        bend = (32925, (elbow[1] + target[1])*.5, min(elbow[2], target[2])-7)
        tube(key+'Fitted0', elbow, bend, 3.2, color, False)
        tube(key+'Fitted1', bend, target, 3.2, color, False)
    compile_bp(bp)


def player_outside(g):
    return g.num('Greater', g.axis(g.position(g.get('Player')), 'Z'), 2000.)


def phase(g, number):
    return g.compare('EqualEqual', g.get('EvacuationStage'), number)


def positioned(g, point, radius=218.):
    return g.near(point, radius)


def down(g):
    return g.get('EvacFHeld')


def camera(g):
    manager = g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager', PlayerIndex=0))
    eye = g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation', target=manager))
    rot = g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation', target=manager))
    return eye, g.math('GetForwardVector', InRot=rot)


def focus(mission, name, point, diameter, reach=218.):
    g = Story(mission, 'EvacFocus' + name)
    g.set('EvacFocus', False)
    g.branch(positioned(g, point, reach))
    eye, ray = camera(g)
    offset = g.subv(L(point), eye)
    along = g.math('Dot_VectorVector', A=offset, B=ray)
    g.branch(g.num('Greater', along, 0.))
    g.branch(g.num('Less', g.distance(g.scale(ray, along), offset), diameter))
    trace = g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle', Start=L(point), End=eye,
                        TraceChannel='TraceTypeQuery1', bTraceComplex=False, bIgnoreSelf=True, DrawDebugType='None'))
    hit = g.call('Engine.GameplayStatics.BreakHitResult', Hit=g.out(trace, 'OutHit'))
    pawn = g.math('EqualEqual_ObjectObject', A=g.out(hit, 'HitActor'), B=g.get('Player'))
    g.branch(g.math('BooleanOR', A=g.not_(g.out(trace)), B=pawn))
    g.set('EvacFocus', True)


def part(g, name):
    return g.get('Evac' + name)


def move(g, name, location):
    g.do(g.call('Engine.SceneComponent.K2_SetWorldLocation', target=part(g, name),
                NewLocation=location, bSweep=False, bTeleport=True))


def move_loose_cable(g, key, source, anchor, location):
    pivot = g.vector(32925., float(anchor[1]), float(source[2]-10))
    span = g.subv(location, pivot)
    center = g.addv(pivot, g.scale(span, .5))
    rotation = g.math('MakeRotFromZ', Z=span)
    length = g.math('Divide_DoubleDouble', A=g.math('VSize', A=span), B=100.)
    cable = part(g, key+'Lead')
    g.do(g.call('Engine.SceneComponent.K2_SetWorldLocationAndRotation', target=cable,
                NewLocation=center, NewRotation=rotation, bSweep=False, bTeleport=True))
    g.do(g.call('Engine.SceneComponent.SetWorldScale3D', target=cable,
                NewScale=g.vector(.032, .032, length)))
    move(g, key+'Plug', location)


def rotate(g, fraction):
    angle = g.math('Lerp', A=-48., B=32., Alpha=fraction)
    rotation = g.math('MakeRotator', Roll=0., Pitch=angle, Yaw=0.)
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation', target=part(g, 'Lever'),
                NewRotation=rotation, bSweep=False, bTeleport=True))


def indicator(g, name, color):
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial', target=part(g, name),
                ElementIndex=0, Material=color))


def outline(g, name, ready):
    g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth', target=part(g, name), bValue=ready))


def sound(g, point):
    g.sound('/Game/Combat/CyborgModes/S_ModeSelect', L(point), .42)


def cue(g, name, seconds):
    speaker, text = CUES[name]
    g.set('VisorRadioSource', speaker)
    publish_fields(g, 'VisorRadio', {'text': text}, seconds)
    sound(g, RADIO if name in ('Reply', 'Next') else BOARD)


def mark_if_changed(g, text, point):
    changed = g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr', A=g.get('Objective'), B=text))
    g.branch(changed)
    g.goal(text, point)


def snap_lead(g, key, target):
    move(g, key+'Plug', L(target))
    g.visibility('Evac'+key+'Lead', False)
    for index in range(2):
        g.visibility('Evac'+key+'Fitted'+str(index), True)
    outline(g, key+'Plug', False)
    g.set('Evac'+key+'Connected', True)


def checkpoint_graphs(mission, max_milestone=3):
    for write in (True, False):
        g = Story(mission, 'EvacSave' if write else 'EvacLoad')
        g.branch(campaign_save_enabled(g))
        g.branch(g.compare('EqualEqual', g.get('CheckpointWrittenRank'), 8))
        path = file_path(g, SLOTS[0])
        g.branch(g.out(g.call('Engine.BlueprintPathsLibrary.FileExists', InPath=path)))
        read = g.do(g.call(JSON+'FromFile', File=file_struct(g, path)))
        g.branch(g.out(read))
        data = g.out(read, 'OutJsonObject')
        def read_integer(field):
            read_field = g.do(g.call(JSON+'GetField', JsonObject=data, FieldName=field))
            g.branch(g.out(read_field))
            name = 'Loaded'+field
            if name not in map(str, g.e.list_local_variable_names()):
                assert g.e.add_local_variable(name, B.get_basic_type_by_name('int'), '0')
            node = g.node(g.e.add_set_local_variable_node(name))
            val(pin(node, name), g.out(read_field, 'OutValue'))
            g.do(node)
            return pin(g.node(g.e.add_get_local_variable_node(name)), name, True)

        g.branch(g.compare('EqualEqual', read_integer('Milestone'), 8))
        if write:
            node = g.do(g.call(JSON+'SetField', JsonObject=data, FieldName='EvacuationMilestone',
                               Value=g.get('EvacuationMilestone')))
            g.branch(g.out(node))
            written = g.do(g.call(JSON+'ToFile', JsonObject=data, File=file_struct(g, path)))
            g.branch(g.out(written))
            g.set('EvacuationSaved', g.get('EvacuationMilestone'))
        else:
            has = g.out(g.do(g.call(JSON+'HasField', JsonObject=data, FieldName='EvacuationMilestone')))
            g.branch(has)
            milestone = read_integer('EvacuationMilestone')
            valid = g.both(g.compare('GreaterEqual', milestone, 1), g.compare('LessEqual', milestone, max_milestone))
            g.branch(valid)
            g.set('EvacuationSaved', milestone)
            g.set('EvacuationMilestone', milestone)
            g.set('EvacuationResume', True)


def interaction_graphs(mission):
    g = Story(mission, 'EvacRepaired')
    for key, _, target, _, _, _ in LEADS:
        snap_lead(g, key, target)
    rotate(g, 1.)
    indicator(g, 'Status', GREEN)
    indicator(g, 'RadioStatus', GREEN)

    g = Story(mission, 'EvacDragUpdate')
    held = g.get('EvacDrag')
    for slot, (key, source, target, anchor, _, _) in enumerate(LEADS, 1):
        active = g.branch(g.compare('EqualEqual', held, slot))
        release = g.branch(g.both(down(g), positioned(g, PANEL)))
        eye, ray = camera(g)
        toward = g.axis(ray, 'X')
        aim = g.branch(g.num('Less', toward, -.14))
        factor = g.math('Divide_DoubleDouble',
                        A=g.math('Subtract_DoubleDouble', A=target[0], B=g.axis(eye, 'X')),
                        B=toward)
        hit = g.addv(eye, g.scale(ray, factor))
        y = g.math('FClamp', Value=g.axis(hit, 'Y'), Min=83561., Max=83699.)
        z = g.math('FClamp', Value=g.axis(hit, 'Z'), Min=2270., Max=2351.)
        move_loose_cable(g, key, source, anchor, g.vector(target[0], y, z))
        g.cursor = aim.find_else_pin()
        move_loose_cable(g, key, source, anchor, g.vector(*map(float,source)))
        g.cursor = release.find_else_pin()
        g.set('EvacDrag', 0)
        g.do(g.own('EvacFocusSocket'+key))
        correct = g.branch(g.both(g.not_(down(g)), g.get('EvacFocus')))
        snap_lead(g, key, target)
        sound(g, target)
        match = g.branch(g.both(g.get('EvacAConnected'), g.get('EvacBConnected')))
        g.set('EvacuationStage', 4)
        outline(g, 'Lever', True)
        g.cursor = correct.find_else_pin()
        move_loose_cable(g, key, source, anchor, g.vector(*map(float,source)))
        g.set('EvacHintUntil', g.math('Add_DoubleDouble', A=g.now(), B=2.25))
        g.cursor = active.find_else_pin()

    g = Story(mission, 'EvacLiftUpdate')
    g.branch(g.get('EvacLeverHeld'))
    g.do(g.own('EvacFocusLever'))
    holding = g.branch(g.both(down(g), g.get('EvacFocus')))
    duration = g.math('Subtract_DoubleDouble', A=g.now(), B=g.get('EvacHoldStart'))
    fraction = g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=duration, B=1.25), Min=0., Max=1.)
    rotate(g, fraction)
    g.branch(g.num('GreaterEqual', duration, 1.25))
    g.set('EvacLeverHeld', False)
    g.do(g.own('EvacRepaired'))
    outline(g, 'Lever', False)
    outline(g, 'RadioHousing', True)
    sound(g, LEVER)
    g.set('EvacuationStage', 5)
    g.set('EvacuationMilestone', 2)
    g.do(g.own('EvacSave'))
    g.cursor = holding.find_else_pin()
    g.set('EvacLeverHeld', False)
    rotate(g, 0.)

    g = Story(mission, 'EvacUse')
    for stage, target in ((1, 'Board'), (2, 'Lever'), (4, 'Lever'), (5, 'Radio')):
        branch = g.branch(phase(g, stage))
        g.do(g.own('EvacFocus'+target))
        g.branch(g.get('EvacFocus'))
        if stage == 1:
            outline(g, 'BoardBacking', False)
            outline(g, 'Lever', True)
            cue(g, 'Roster', 7.)
            g.set('EvacuationStage', 2)
        elif stage == 2:
            rotate(g, 0.)
            outline(g, 'Lever', False)
            g.visibility('EvacStatus', False)
            for key, *_ in LEADS:
                outline(g, key+'Plug', True)
            sound(g, LEVER)
            g.set('EvacuationStage', 3)
        elif stage == 4:
            g.branch(g.not_(g.get('EvacLeverHeld')))
            g.set('EvacFHeld', True)
            g.set('EvacHoldStart', g.now())
            g.set('EvacLeverHeld', True)
            g.visibility('EvacStatus', True)
        else:
            outline(g, 'RadioHousing', False)
            cue(g, 'Reply', 9.)
            g.set('EvacReplyAt', g.math('Add_DoubleDouble', A=g.now(), B=9.25))
            g.set('EvacuationStage', 6)
            g.set('EvacuationMilestone', 3)
            g.do(g.own('EvacSave'))
        g.cursor = branch.find_else_pin()
    g.branch(phase(g, 3))
    g.branch(g.compare('EqualEqual', g.get('EvacDrag'), 0))
    for slot, (key, *_) in enumerate(LEADS, 1):
        g.do(g.own('EvacFocusPlug'+key))
        select = g.branch(g.both(g.get('EvacFocus'), g.not_(g.get('Evac'+key+'Connected'))))
        g.set('EvacFHeld', True)
        g.set('EvacDrag', slot)
        g.set('EvacHintUntil', 0.)
        g.cursor = select.find_else_pin()


def guide_graphs(mission):
    g = Story(mission, 'EvacRestoreVisuals')
    g.set('ShelterStep', 5)
    g.set('SecondVoiceStep', 7)
    g.set('SecondVoiceConfirmed', True)
    value = g.get('EvacuationMilestone')
    g.set('EvacuationStage', g.math('SelectInt', A=1, B=g.math('SelectInt', A=5, B=6,
                bPickA=g.compare('EqualEqual', value, 2)), bPickA=g.compare('EqualEqual', value, 1)))
    g.set('EvacuationResume', False)
    restart = g.branch(g.compare('EqualEqual', value, 1))
    outline(g, 'BoardBacking', True)
    join = g.node(g.e.add_branch_node())
    val(join.find_condition_pin(), True)
    link(g.cursor, join.find_execute_pin())
    link(restart.find_else_pin(), join.find_execute_pin())
    g.cursor = join.find_then_pin()
    g.do(g.call('Engine.Actor.K2_TeleportTo', target=g.get('Player'), DestLocation=L(OUT),
                DestRotation='(Pitch=0,Yaw=0,Roll=0)'))
    restore = g.branch(g.compare('GreaterEqual', value, 2))
    g.do(g.own('EvacRepaired'))
    outline(g, 'RadioHousing', g.compare('EqualEqual', value, 2))

    g = Story(mission, 'EvacTick')
    begin = g.branch(phase(g, 0))
    g.set('EvacuationStage', 1)
    g.set('EvacuationMilestone', 1)
    g.do(g.own('EvacSave'))
    cue(g, 'Dispatch', 7.5)
    outline(g, 'BoardBacking', True)
    g.cursor = begin.find_else_pin()
    hud = g.get('StoryHUD')
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName', Object=hud,
                PropertyName='ShelterChapter', Value=TITLE))
    for stage, point, text in STAGES:
        branch = g.branch(phase(g, stage))
        if stage == 4:
            g.do(g.own('EvacLiftUpdate'))
        mark_if_changed(g, text, point)
        g.cursor = branch.find_else_pin()
    wiring = g.branch(phase(g, 3))
    g.do(g.own('EvacDragUpdate'))
    wrong = g.num('Greater', g.get('EvacHintUntil'), g.now())
    dragging = g.compare('Greater', g.get('EvacDrag'), 0)
    held_b = g.compare('EqualEqual', g.get('EvacDrag'), 2)
    match = g.math('SelectString', A='Наведи штекер 2 на гнездо «ПИТАНИЕ» и отпусти F',
                   B='Наведи штекер 1 на гнездо «СВЯЗЬ» и отпусти F', bPickA=held_b)
    idle = g.math('SelectString', A='Штекер вернулся. Сверь номер на кабеле и гнезде.',
                  B='Наведи прицел на штекер и зажми F. Совмести номера на кабеле и гнезде.', bPickA=wrong)
    mark_if_changed(g, g.math('SelectString', A=match, B=idle, bPickA=dragging), PANEL)
    g.cursor = wiring.find_else_pin()
    g.branch(phase(g, 6))
    ready = g.branch(g.num('Greater', g.get('EvacReplyAt'), 0.))
    g.branch(g.num('GreaterEqual', g.now(), g.get('EvacReplyAt')))
    g.set('EvacReplyAt', 0.)
    cue(g, 'Next', 8.)
    g.cursor = ready.find_else_pin()
    done = 'Список оставшихся · пост 12 на связи'
    g.set('Objective', done)
    g.pset('StoryGoalActive', False, 'Bool')


def install():
    mission = load(MISSION)
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert mission.get_outermost() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    relative = Path('Content') / (MISSION.removeprefix('/Game/')+'.uasset')
    backup = PROJECT/'Saved/Backups/EvacuationRelay'/datetime.now().strftime('%Y%m%d_%H%M%S')/relative
    backup.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(PROJECT/relative, backup)

    hardware(mission)
    for name, kind, initial in (
        ('EvacuationStage','int','0'), ('EvacuationMilestone','int','0'), ('EvacuationSaved','int','0'),
        ('EvacuationResume','bool','false'), ('EvacFocus','bool','false'), ('EvacDrag','int','0'),
        ('EvacFHeld','bool','false'),
        ('EvacAConnected','bool','false'), ('EvacBConnected','bool','false'), ('EvacLeverHeld','bool','false'),
        ('EvacHoldStart','real','0'), ('EvacHintUntil','real','0'), ('EvacReplyAt','real','0'),
    ):
        var(mission, name, kind, initial)
    for name in ('EvacSave','EvacLoad','EvacRepaired','EvacDragUpdate','EvacLiftUpdate',
                 'EvacUse','EvacTick','EvacRestoreVisuals'):
        Story(mission, name)
    for name, point, span in (('Board',BOARD,31.),('Lever',LEVER,18.),('Radio',RADIO,24.),
                              *((name, point, 10.) for key, source, target, *_ in LEADS
                                for name, point in (('Plug'+key,source),('Socket'+key,target)))):
        focus(mission, name, point, span)
    compile_bp(mission)
    checkpoint_graphs(mission)
    interaction_graphs(mission)
    guide_graphs(mission)
    compile_bp(mission)

    def relay_owns(g):
        return g.both(player_outside(g), g.both(g.compare('EqualEqual',g.get('SecondVoiceStep'),7),
                                               g.compare('EqualEqual',g.get('ShelterStep'),5)))

    def tick(g, old, tag):
        resume = g.branch(g.get('EvacuationResume'))
        g.do(g.own('EvacRestoreVisuals'))
        gate = g.node(g.e.add_branch_node())
        val(gate.find_condition_pin(), relay_owns(g))
        link(g.cursor, gate.find_execute_pin())
        link(resume.find_else_pin(), gate.find_execute_pin())
        gate.rename(tag)
        g.cursor = gate.find_then_pin()
        g.do(g.own('EvacTick'))
        for previous in old:
            link(gate.find_else_pin(), previous)

    def use(g, old, tag):
        driven = g.branch(g.both(relay_owns(g), g.compare('Greater',g.get('EvacuationStage'),0)))
        driven.rename(tag)
        g.do(g.own('EvacUse'))
        for previous in old:
            link(driven.find_else_pin(), previous)

    def restore(g, old, tag):
        g.do(g.own('EvacLoad')).rename(tag)
        for previous in old:
            link(g.cursor, previous)

    for fn, callback in (('ShelterTick',tick),('ShelterUse',use),('DemoCheckpointApply',restore)):
        insert_entry(mission, fn, 'EvacuationDispatch'+fn, callback)
    graph = Story(mission)
    event = next((n for n in graph.e.list_all_nodes() if n.get_name() == 'EvacuationReleaseKey'), None)
    if event is None:
        key = next(key for key in graph.e.list_available_nodes([])
                   if str(key).endswith('|KeyboardEvents|F'))
        event = graph.e.create_node_from_name(key, unreal.Vector2D(x=1900, y=1600), [])
        event.rename('EvacuationReleaseKey')
        event.set_editor_property('bConsumeInput', False)
        graph.cursor = pin(event, 'Released', True)
        graph.set('EvacFHeld', False)

    compile_bp(mission)
    save(mission)
    out = PROJECT/'Saved/EvacuationRelay'
    out.mkdir(exist_ok=True)
    (out/'Installed.json').write_text(json.dumps({'backup':str(backup),'mission':MISSION,'stage':TITLE,
        'board':BOARD,'panel':PANEL,'lever':LEVER,'radio':RADIO,'cues':CUES},ensure_ascii=False,indent=2),encoding='utf8')


if __name__ == '__main__':
    install()
