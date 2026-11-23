"""Coordinate navigation, recovery terminal and the OMEGA city map."""
from datetime import datetime
from pathlib import Path
import json
import operator
import shutil
import wave

import unreal

from CityCombat_Common import A, B, G, Graph, compile_bp, components, link, pin, save, var
from Build_CityReclaim import ROADS
from Build_OmegaGuide import GuideGraph, ROOT, line_graph
from Place_ServiceStation import ROOT as SERVICE, station_point

PLAYER = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
GUIDE = ROOT + '/BP_OmegaGuide'
STATION = SERVICE + '/BP_ServiceStation'
GROUND = 2150.
ENTRANCE = station_point(0., 5.75, 0.)
TERMINAL = station_point(-3.93, 2.03, 1.05)
POINTS = (
    ('ЛАБ. 02', ENTRANCE[0], ENTRANCE[1]),
    ('ЛАБ. 03', 15500., 90900.),
    ('ЖИЛОЙ БЛОК', 5850., 35500.),
    ('РАДИО / СТ. 07', 34526., 87526.),
)
MEMORY_TAG = 'OmegaCityMemoryRestored'
CYAN = '(R=.42,G=.88,B=.96,A=.98)'
WHITE = '(R=.82,G=.93,B=.96,A=.98)'
MUTED = '(R=.52,G=.69,B=.73,A=.93)'
AMBER = '(R=1,G=.73,B=.36,A=.98)'
FONT = '/Engine/EngineFonts/Roboto'


def vector(x, y, z):
    return f'(X={x},Y={y},Z={z})'


class Nav(Graph):
    def number(self, operation, a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return {'Add': operator.add, 'Subtract': operator.sub, 'Multiply': operator.mul,
                    'Divide': operator.truediv}[operation](float(a), float(b))
        return self.math(operation + '_DoubleDouble',
                         A=float(a) if isinstance(a, int) else a,
                         B=float(b) if isinstance(b, int) else b)

    def both(self, a, b):
        return self.math('BooleanAND', A=a, B=b)

    def inverse(self, a):
        return self.math('Not_PreBool', A=a)

    def position(self):
        return self.out(self.call('Engine.Actor.K2_GetActorLocation'))

    def split(self, v):
        node = self.call('Engine.KismetMathLibrary.BreakVector', InVec=v)
        return [self.out(node, axis) for axis in 'XYZ']

    def range_test(self, v, low, high):
        return self.both(self.number('Greater', v, low), self.number('Less', v, high))

    def inside(self, x, y, z):
        return self.both(self.range_test(x, 34535., 35680.),
                         self.both(self.range_test(y, 86265., 87545.), self.range_test(z, 2160., 2460.)))

    def near_console(self, x, y, z):
        planar = self.math('MakeVector', X=x, Y=y, Z=0.)
        distance = self.math('Vector_Distance', V1=planar, V2=vector(*TERMINAL[:2], 0.))
        return self.both(self.inside(x, y, z), self.number('LessEqual', distance, 165.))

    def concat(self, *parts):
        result = parts[0]
        for value in parts[1:]:
            result = self.out(self.call('Engine.KismetStringLibrary.Concat_StrStr', A=result, B=value))
        return result

    def metres(self, cm):
        n = self.math('Round', A=self.number('Multiply', cm, .01))
        return self.out(self.call('Engine.KismetStringLibrary.Conv_IntToString', InInt=n))

    def xyz(self, x, y, z):
        return self.concat('X ', self.metres(x), '   Y ', self.metres(y), '   Z ', self.metres(z))

    def text(self, label, x, y, color=WHITE, scale=1.):
        self.do(self.call('Engine.HUD.DrawText', target=self.get('NavCanvas'), Text=label,
                          TextColor=color, ScreenX=x, ScreenY=y, Font=FONT,
                          Scale=self.number('Multiply', self.get('NavScale'), scale), bScalePosition=False))

    def rectangle(self, x, y, w, h, tint):
        self.do(self.call('Engine.HUD.DrawRect', target=self.get('NavCanvas'), RectColor=tint,
                          ScreenX=x, ScreenY=y, ScreenW=w, ScreenH=h))

    def line(self, x1, y1, x2, y2):
        self.do(self.call('Engine.HUD.DrawLine', target=self.get('NavCanvas'), StartScreenX=x1,
                          StartScreenY=y1, EndScreenX=x2, EndScreenY=y2,
                          LineColor='(R=.28,G=.51,B=.58,A=.47)', LineThickness=1.25))

    def scaled(self, size):
        return self.number('Multiply', size, self.get('NavScale'))

    def offset(self, anchor, displacement):
        return self.number('Add', anchor, self.scaled(displacement))

    def input_enabled(self):
        self.branch(self.valid(self.pc()))
        ignored = self.out(self.call('Engine.Controller.IsMoveInputIgnored', target=self.pc()))
        self.branch(self.inverse(ignored))


def graph_start(bp, name, function, tag, wire=None):
    g = Nav(bp)
    g.e = G.get_graph_editor_by_name(bp, name)
    if any(n.get_name() == tag for n in g.e.list_all_nodes()):
        return
    start = g.e.find_graph_entry_pin()
    connections = list(start.list_connected_pins())
    assert len(connections) == 1, name
    start.break_pin_links()
    g.cursor = start
    n = g.own(function)
    n.rename(tag)
    n.set_node_pos(unreal.IntPoint(x=-430, y=-300))
    if wire:
        wire(start.get_owning_node(), n)
    g.do(n)
    link(g.cursor, connections[0])


def add_key(bp, key, method):
    g = Nav(bp)
    name = 'OmegaNavInput_' + key
    event = next((n for n in g.e.list_all_nodes() if n.get_name() == name), None)
    row = 14800 + ('FMN'.index(key))*350
    if event is None:
        menu = next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|' + key))
        event = g.e.create_node_from_name(menu, unreal.Vector2D(x=-7500, y=row), [])
        event.rename(name)
        event.set_editor_property('bConsumeInput', False)
        g.cursor = pin(event, 'Pressed', True)
        n = g.own(method)
        n.set_node_pos(unreal.IntPoint(x=-7150, y=row))
        g.do(n)
    release = pin(event, 'Released', True)
    if key in ('M', 'N') and not release.list_connected_pins():
        g.cursor = release
        n = g.set('Nav'+key+'Down', False)
        n.set_node_pos(unreal.IntPoint(x=-6700, y=row))


def nav_target(bp):
    g = Nav(bp, 'Nav_RefreshTarget')
    x, y, z = g.split(g.position())
    inside = g.inside(x, y, z)
    active = g.get('NavTargetIndex')
    lab = g.branch(g.math('EqualEqual_IntInt', A=active, B=0))
    console = g.branch(g.both(inside, g.inverse(g.get('NavMemoryReady'))))
    g.set('NavGoal', vector(*TERMINAL))
    g.set('NavGoalName', 'ЛАБ. 02 / ТЕРМИНАЛ')
    g.cursor = console.find_else_pin()
    g.set('NavGoal', vector(*ENTRANCE))
    g.set('NavGoalName', 'ЛАБ. 02 / ВХОД')
    g.cursor = lab.find_else_pin()
    for i, (name, x, y) in enumerate(POINTS[1:], 1):
        branch = g.branch(g.math('EqualEqual_IntInt', A=active, B=i))
        g.set('NavGoal', vector(x, y, GROUND))
        g.set('NavGoalName', name)
        g.cursor = branch.find_else_pin()


def interactions(bp):
    g = Nav(bp, 'Nav_RecoverMemory')
    g.input_enabled()
    g.branch(g.inverse(g.get('NavMemoryReady')))
    g.branch(g.near_console(*g.split(g.position())))
    station = g.out(g.do(g.call('Engine.GameplayStatics.GetActorOfClass',
                                ActorClass=A.load_blueprint_class(STATION).get_path_name())))
    g.branch(g.valid(station))
    g.set('NavMemoryReady', True)
    g.set('NavTargetIndex', 1)
    g.set('NavMapOpen', True)
    g.set('VisorMaxIntegrity', g.number('Add', g.get('VisorMaxIntegrity'), 25.))
    g.set('VisorIntegrity', g.get('VisorMaxIntegrity'))
    g.set('VisorEnergy', g.get('VisorMaxEnergy'))
    tags = g.node(g.e.add_get_member_variable_node('Tags', '/Script/Engine.Actor'))
    g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique', TargetArray=pin(tags, 'Tags', True),
                NewItem=MEMORY_TAG))
    g = Nav(bp, 'Nav_ToggleMap')
    g.branch(g.inverse(g.get('NavMDown')))
    g.set('NavMDown', True)
    g.input_enabled()
    g.branch(g.get('NavMemoryReady'))
    g.set('NavMapOpen', g.inverse(g.get('NavMapOpen')))
    g = Nav(bp, 'Nav_SelectNext')
    g.branch(g.inverse(g.get('NavNDown')))
    g.set('NavNDown', True)
    g.input_enabled()
    g.branch(g.both(g.get('NavMemoryReady'), g.get('NavMapOpen')))
    g.set('NavTargetIndex', g.math('Percent_IntInt',
          A=g.math('Add_IntInt', A=g.get('NavTargetIndex'), B=1), B=len(POINTS)))


def city_map(bp):
    g = Nav(bp, 'Nav_DrawCityMap')
    g.branch(g.both(g.get('NavMemoryReady'), g.get('NavMapOpen')))
    width, height = g.get('NavWidth'), g.get('NavHeight')
    left = g.offset(g.number('Multiply', width, .5), -267.)
    top = g.offset(g.number('Multiply', height, .5), -183.)
    px = lambda v: g.offset(left, v)
    py = lambda v: g.offset(top, v)
    g.rectangle(left, top, g.scaled(534.), g.scaled(386.), '(R=.014,G=.039,B=.052,A=.96)')
    g.rectangle(left, top, g.scaled(534.), g.scaled(2.), CYAN)
    g.text('OMEGA   /   КАРТА ГОРОДА', px(16.), py(12.), CYAN, 1.12)
    g.text('M — закрыть   N — выбрать точку', px(16.), py(40.), MUTED, .91)

    def project(x, y):
        u = g.number('Multiply', g.number('Add', x, 23200.), .00435)
        v = g.number('Multiply', g.number('Subtract', 108000., y), .00350)
        return px(g.number('Add', 20., u)), py(g.number('Add', 76., v))

    for x, y, w, h in (*ROADS, (5850., 41800., 1640., 35800.)):
        x1, y1 = project(x-w*.5 if w>h else x, y if w>h else y-h*.5)
        x2, y2 = project(x+w*.5 if w>h else x, y if w>h else y+h*.5)
        g.line(x1, y1, x2, y2)

    for i, (name, x, y) in enumerate(POINTS):
        if i==3:continue  # Reception and radio share the same building on this city-scale map.
        if i==0:name='СТАНЦИЯ 07 / ЛАБ. 02'
        ax, ay = project(x, y)
        selected = g.math('EqualEqual_IntInt', A=g.get('NavTargetIndex'), B=i)
        if i==0:selected=g.math('BooleanOR',A=selected,B=g.math('EqualEqual_IntInt',A=g.get('NavTargetIndex'),B=3))
        color = g.math('SelectColor', A=AMBER, B=CYAN, bPickA=selected)
        g.rectangle(g.offset(ax, -3.), g.offset(ay, -3.), g.scaled(6.), g.scaled(6.), color)
        g.text(name, g.offset(ax, 8.), g.offset(ay, -9.), color, .78)
    x, y, _ = g.split(g.position())
    x = g.math('FClamp', Value=x, Min=-23000., Max=68000.)
    y = g.math('FClamp', Value=y, Min=22900., Max=107500.)
    ax, ay = project(x, y)
    g.rectangle(g.offset(ax, -4.), g.offset(ay, -4.), g.scaled(8.), g.scaled(8.), WHITE)
    g.text('ВЫ', g.offset(ax, -20.), g.offset(ay, 6.), WHITE, .8)
    g.text(g.concat('ЦЕЛЬ   ', g.get('NavGoalName')), px(16.), py(360.), AMBER, .9)


def hud(bp):
    g = Nav(bp, 'Nav_DrawHUD')
    entry = g.e.find_graph_entry_pin().get_owning_node()
    parameters = (('Canvas', B.get_object_reference_type(unreal.HUD)),
                  ('Width', B.get_basic_type_by_name('int')), ('Height', B.get_basic_type_by_name('int')))
    present = {str(p.get_pin_name()) for p in entry.list_all_pins()}
    for name, kind in parameters:
        if name not in present:
            g.e.add_graph_input_parameter(name, kind)
    g.input_enabled()
    g.set('NavCanvas', pin(entry, 'Canvas', True))
    g.set('NavWidth', pin(entry, 'Width', True))
    g.set('NavHeight', pin(entry, 'Height', True))
    size = g.math('FMin', A=g.number('Divide', g.get('NavHeight'), 780.),
                  B=g.number('Divide', g.get('NavWidth'), 800.))
    g.set('NavScale', g.math('FClamp', Value=size, Min=.48, Max=1.))
    g.do(g.own('Nav_RefreshTarget'))
    x, y, z = g.split(g.position())
    tx, ty, tz = g.split(g.get('NavGoal'))
    left = g.offset(g.number('Multiply', g.get('NavWidth'), .5), -229.)
    top = g.scaled(126.)
    row = lambda d: g.offset(top, d)
    xx = g.offset(left, 11.)
    g.rectangle(left, top, g.scaled(458.), g.scaled(91.), '(R=.013,G=.036,B=.05,A=.80)')
    g.rectangle(left, top, g.scaled(2.), g.scaled(91.), CYAN)
    half_height = g.out(g.call('Engine.CapsuleComponent.GetScaledCapsuleHalfHeight', target=g.get('CapsuleComponent')))
    feet_z = g.number('Subtract', z, half_height)
    g.text(g.concat('ВЫ   ', g.xyz(x, y, g.number('Subtract', feet_z, GROUND)), ' м'), xx, row(5.), CYAN)
    g.text(g.concat(g.get('NavGoalName'), '   ', g.xyz(tx, ty, g.number('Subtract', tz, GROUND))), xx, row(25.))
    dx, dy, dz = [g.number('Subtract', b, a) for a, b in zip((x,y,feet_z),(tx,ty,tz))]
    delta = g.math('MakeVector', X=dx, Y=dy, Z=0.)
    distance = g.math('VSize', A=delta)
    g.text(g.concat('ОСТАЛОСЬ   ', g.metres(distance), ' м    Δ ', g.xyz(dx,dy,dz)), xx, row(45.), MUTED, .92)
    near = g.both(g.near_console(x,y,z), g.inverse(g.get('NavMemoryReady')))
    hint = g.math('SelectString', A='F — восстановить память и усилить корпус',
                  B='КАРТА ПОВРЕЖДЕНА   /   ВОССТАНОВЛЕНИЕ В ЛАБ. 02', bPickA=near)
    hint = g.math('SelectString', A='M — карта города   N — сменить цель на карте',
                  B=hint, bPickA=g.get('NavMemoryReady'))
    g.text(hint, xx, row(65.), AMBER, .82)
    g.do(g.own('Nav_DrawCityMap'))
    g.branch(g.inverse(g.get('NavMemoryReady')))
    g.branch(g.inverse(g.inside(x,y,z)))
    g.branch(g.number('Greater',y,21950.))
    east = g.number('Greater',x,31800.)
    crossing = g.number('Greater',y,77600.)
    route = g.math('SelectString', A='УЛИЦА Y 783  →  ПРОЕЗД X 334',
                   B='ПРОСПЕКТ X 59  →  ПЕРЕКРЁСТОК Y 783', bPickA=crossing)
    route = g.math('SelectString', A='ПРОЕЗД X 334  →  ВХОД НА Y 869', B=route, bPickA=east)
    g.rectangle(left, row(88.), g.scaled(458.), g.scaled(20.), '(R=.013,G=.036,B=.05,A=.80)')
    g.text(route, xx, row(87.), MUTED, .8)


def author_player(bp):
    for name, kind, default in (
        ('NavMDown','bool','false'), ('NavNDown','bool','false'),
        ('NavMemoryReady','bool','false'), ('NavMapOpen','bool','false'), ('NavTargetIndex','int','0'),
        ('NavGoal',B.get_struct_type(unreal.Vector.static_struct()),vector(*ENTRANCE)),
        ('NavGoalName','string','ЛАБ. 02 / ВХОД'), ('NavWidth','real','1920'), ('NavHeight','real','1080'),
        ('NavScale','real','1'), ('NavCanvas',B.get_object_reference_type(unreal.HUD),'None'),
    ):
        var(bp,name,kind,default)
    compile_bp(bp)
    nav_target(bp)
    interactions(bp)
    city_map(bp)
    compile_bp(bp)
    hud(bp)
    compile_bp(bp)
    for key, method in (('F','Nav_RecoverMemory'), ('M','Nav_ToggleMap'), ('N','Nav_SelectNext')):
        add_key(bp,key,method)

    def wire(entry, call):
        for a,b in (('HUD','Canvas'), ('Width','Width'), ('Height','Height')):
            link(pin(entry,a,True),pin(call,b))
    graph_start(bp,'Modes_DrawHUD','Nav_DrawHUD','OmegaNavHUD',wire)
    compile_bp(bp)


def import_voice(cue, row, index, source):
    filename=source/('S_Omega_'+cue+'.wav')
    task=unreal.AssetImportTask()
    for key,value in dict(filename=str(filename),destination_path=ROOT,destination_name=filename.stem,
                          automated=True,replace_existing=True,save=False).items():
        task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound=A.load_asset(ROOT+'/'+filename.stem)
    assert sound
    with wave.open(str(filename),'rb') as wav:
        seconds=wav.getnframes()/wav.getframerate()
    assert abs(sound.get_editor_property('duration')-seconds)<.05
    subtitle=unreal.SubtitleCue()
    subtitle.set_editor_property('text',unreal.Text('OMEGA  ·  '+row['text']))
    subtitle.set_editor_property('time',.12)
    sound.set_editor_property('subtitles',[subtitle])
    save(sound)
    return index,sound,row['text'],seconds


def author_guide(bp, source):
    lines=json.loads((source/'Lines.json').read_text(encoding='utf-8-sig'))
    var(bp,'HeardRecovery','bool','false')
    compile_bp(bp)
    index=next(i for i,row in enumerate(lines) if row['id']=='Recovery')
    for i,row in enumerate(lines):
        cue=row['id']
        if cue in ('City','Recovery'):
            line_graph(bp,cue,import_voice(cue,row,i,source))
    g=GuideGraph(bp,'Nav_CheckRecovery')
    g.branch(g.valid(g.player()))
    g.branch(g.no(g.get('HeardRecovery')))
    g.branch(g.get('HeardCity'))
    g.branch(g.out(g.call('Engine.Actor.ActorHasTag',target=g.player(),Tag=MEMORY_TAG)))
    g.do(g.own('Speak_Recovery'))
    compile_bp(bp)
    graph_start(bp,'Omega_Poll','Nav_CheckRecovery','OmegaNavRecovery')
    g=GuideGraph(bp)
    g.e=G.get_graph_editor_by_name(bp,'Omega_Repeat')
    if not any(n.get_name()=='OmegaNavRepeat' for n in g.e.list_all_nodes()):
        start=g.e.find_graph_entry_pin()
        before=list(start.list_connected_pins())
        start.break_pin_links()
        g.cursor=start
        gate=g.branch(g.math('EqualEqual_IntInt',A=g.get('LastLine'),B=index))
        gate.rename('OmegaNavRepeat')
        g.do(g.own('Speak_Recovery'))
        for p in before:
            link(gate.find_else_pin(),p)
    compile_bp(bp)


def install():
    content=Path(unreal.Paths.project_content_dir())
    saved=Path(unreal.Paths.project_saved_dir())
    backup=saved/'Backups/OmegaNavigation'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for path in (PLAYER,GUIDE,STATION,ROOT+'/S_Omega_City'):
        relative=Path(path.removeprefix('/Game/')+'.uasset')
        dest=backup/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(content/relative,dest)
    player,guide,station=[A.load_asset(path) for path in (PLAYER,GUIDE,STATION)]
    author_player(player)
    author_guide(guide,content.parent/'SourceAssets/OmegaVoice')
    for _,component,name in components(station):
        if name=='FacadeSign':
            component.set_text(unreal.Text('LAB 02  /  RECOVERY STATION'))
        elif name=='ReceptionSign':
            component.set_text(unreal.Text('MEMORY RECOVERY'))
    compile_bp(station)
    for bp in (player,guide,station):
        save(bp)
    unreal.log('OMEGA navigation installed')


if __name__=='__main__':
    install()



