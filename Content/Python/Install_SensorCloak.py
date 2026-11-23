"""Add a five-second sensor cloak to the player and the active city combat machines."""
from datetime import datetime
from pathlib import Path
import shutil

import unreal

from CityCombat_Common import A, B, G, Graph, compile_bp, hook, link, pin, save, var
from CityMachine_Logic import Logic

PLAYER = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
MACHINES = '/Game/Enemies/CityMachines/'
COMBAT_CLASSES = ('BP_Marauder', 'BP_Bastion', 'BP_Lynx', 'Colossus/BP_Colossus',
                  'StrikeDrone/BP_StrikeDrone', 'BP_PoliceMech')
CLOAK_TAG = 'CyborgSensorCloaked'
DURATION = 5.0


def existing_graph(bp, name):
    g = Logic(bp)
    g.e = G.get_graph_editor_by_name(bp, name)
    return g


def has_cloak(g, target=None):
    return g.out(g.call('Engine.Actor.ActorHasTag', target=target, Tag=CLOAK_TAG))


def cloak_tags(g):
    tags = g.node(g.e.add_get_member_variable_node('Tags', '/Script/Engine.Actor'))
    return pin(tags, 'Tags', True)


def player_cloak(bp):
    var(bp, 'CloakUntil', 'real', '0')
    compile_bp(bp)

    g = Graph(bp, 'Cloak_Activate')
    g.branch(g.math('Not_PreBool', A=has_cloak(g)))
    g.set('CloakUntil', g.math('Add_DoubleDouble', A=g.now(), B=DURATION))
    g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique', TargetArray=cloak_tags(g), NewItem=CLOAK_TAG))

    g = Graph(bp, 'Cloak_Update')
    g.branch(g.math('Greater_DoubleDouble', A=g.get('CloakUntil'), B=0.))
    g.branch(g.math('GreaterEqual_DoubleDouble', A=g.now(), B=g.get('CloakUntil')))
    g.do(g.call('Engine.KismetArrayLibrary.Array_RemoveItem', TargetArray=cloak_tags(g), Item=CLOAK_TAG))
    g.set('CloakUntil', 0.)
    compile_bp(bp)

    g = Graph(bp)
    nodes = g.e.list_all_nodes()
    key = next((n for n in nodes if n.get_name() == 'SensorCloakInput'), None)
    if key is None:
        menu = next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|X'))
        key = g.e.create_node_from_name(menu, unreal.Vector2D(x=-5500, y=13100), [])
        key.rename('SensorCloakInput')
        key.set_editor_property('bConsumeInput', True)
    if not any(n.get_name() == 'SensorCloakStart' for n in nodes):
        pressed = pin(key, 'Pressed', True)
        if pressed.list_connected_pins():
            # Replace the isolated prototype activation chain that used a latent Delay.
            old = {}
            pending = [p.get_owning_node() for p in pressed.list_connected_pins()]
            while pending:
                node = pending.pop()
                name = node.get_name()
                if name == key.get_name() or name in old:
                    continue
                old[name] = node
                assert len(old) <= 16, 'Unexpected nodes attached to cloak input'
                pending.extend(p.get_owning_node() for q in node.list_all_pins() for p in q.list_connected_pins())
            g.e.remove_nodes(list(old.values()))
        call = g.own('Cloak_Activate')
        call.rename('SensorCloakStart')
        call.set_node_pos(unreal.IntPoint(x=-5100, y=13100))
        link(pressed, call.find_execute_pin())
    if not any(n.get_name() == 'SensorCloakTick' for n in nodes):
        tick = g.e.find_event_node('ReceiveTick')
        hook(bp, tick.find_then_pin(), 'Cloak_Update', 'SensorCloakTick')
    compile_bp(bp)

    hud = Graph(bp, 'Cloak_DrawStatus')
    entry = hud.e.find_graph_entry_pin().get_owning_node()
    for name, kind in (('Canvas', B.get_object_reference_type(unreal.HUD)), ('Width', B.get_basic_type_by_name('int'))):
        if name not in [str(p.get_pin_name()) for p in entry.list_all_pins()]:
            hud.e.add_graph_input_parameter(name, kind)
    canvas = pin(entry, 'Canvas', True)
    width = pin(entry, 'Width', True)
    hud.branch(has_cloak(hud))
    left = hud.math('Subtract_DoubleDouble', A=hud.get('CloakUntil'), B=hud.now())
    seconds = hud.math('FCeil', A=hud.math('FClamp', Value=left, Min=0., Max=DURATION))
    suffix = hud.out(hud.call('Engine.KismetStringLibrary.Conv_IntToString', InInt=seconds))
    label = hud.out(hud.call('Engine.KismetStringLibrary.Concat_StrStr', A='МАСКИРОВКА  /  ', B=suffix))
    center = hud.math('Multiply_DoubleDouble', A=width, B=.5)
    x = hud.math('Subtract_DoubleDouble', A=center, B=90.)
    hud.do(hud.call('Engine.HUD.DrawText', target=canvas, Text=label,
                   TextColor='(R=0.38,G=0.96,B=0.84,A=0.93)', ScreenX=x, ScreenY=98.,
                   Font='/Engine/EngineFonts/Roboto', Scale=1., bScalePosition=False))
    compile_bp(bp)

    g = existing_graph(bp, 'Modes_DrawHUD')
    start = g.e.find_graph_entry_pin()
    if not any(n.get_name() == 'SensorCloakHud' for n in g.e.list_all_nodes()):
        original = list(start.list_connected_pins())
        assert len(original) == 1
        start.break_pin_links()
        g.cursor = start
        call = g.own('Cloak_DrawStatus')
        call.rename('SensorCloakHud')
        call.set_node_pos(unreal.IntPoint(x=-360, y=-330))
        entry = start.get_owning_node()
        link(pin(entry, 'HUD', True), pin(call, 'Canvas'))
        link(pin(entry, 'Width', True), pin(call, 'Width'))
        g.do(call)
        link(g.cursor, original[0])


def machine_cloak(bp):
    g = existing_graph(bp, 'MachineTick')
    if any(n.get_name() == 'SensorCloakGuard' for n in g.e.list_all_nodes()):
        return
    nodes = g.e.list_all_nodes()
    alive = g.e.find_graph_entry_pin().list_connected_pins()[0].get_owning_node()
    assert alive.get_class().get_name() == 'K2Node_IfThenElse'
    assert alive.find_then_pin().is_valid()
    live = alive.find_then_pin()
    original = list(live.list_connected_pins())
    assert len(original) == 1
    move, = [n for n in nodes if n.get_class().get_name() == 'K2Node_CallFunction'
             and str(n.get_node_title()).replace(' ', '') == 'MoveMachine']
    live.break_pin_links()
    g.cursor = live
    g.i = 0

    def place(n):
        if not n:
            raise RuntimeError('Cannot create machine cloak node')
        n.set_node_pos(unreal.IntPoint(x=-2250 + (g.i % 5) * 330, y=1900 + (g.i // 5) * 340))
        g.i += 1
        return n

    g.node = place
    gate = g.branch(has_cloak(g, g.player()))
    gate.rename('SensorCloakGuard')
    link(gate.find_else_pin(), original[0])
    g.set('HasSight', False)
    g.set('Target', 'None')
    g.set('LastSeen', -100.)
    variables = set(map(str, B.list_member_variable_names(bp)))
    if 'BurstLeft' in variables:
        g.set('BurstLeft', 0)
    if 'Charging' in variables:
        g.set('Charging', False)
    g.do(g.own('Patrol'))
    link(g.cursor, move.find_execute_pin())


def install():
    paths = [PLAYER, *(MACHINES + name for name in COMBAT_CLASSES)]
    saved = Path(unreal.Paths.project_saved_dir())
    content = Path(unreal.Paths.project_content_dir())
    backup = saved / 'Backups' / 'SensorCloak' / datetime.now().strftime('%Y%m%d_%H%M%S')
    for path in paths:
        relative = Path(path.removeprefix('/Game/') + '.uasset')
        copy = backup / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(content / relative, copy)
    blueprints = [A.load_asset(path) for path in paths]
    assert all(blueprints)
    player_cloak(blueprints[0])
    for bp in blueprints[1:]:
        machine_cloak(bp)
    for bp in blueprints:
        compile_bp(bp)
    for bp in blueprints:
        save(bp)
    unreal.log('Sensor cloak saved: ' + ', '.join(paths))


if __name__ == '__main__':
    install()

