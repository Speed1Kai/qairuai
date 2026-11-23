"""Hunter auto-fire, live enemy telemetry, and occlusion-aware visor graphics."""
from datetime import datetime
from pathlib import Path
import shutil

import unreal

from Build_Firearms import GunGraph, PLAYER
from CityCombat_Common import A, B, G, actorref, add, asset, compile_bp, hook, link, pin, save, val, var

ROOT = '/Game/Combat/TargetLock'
MACHINES = '/Game/Enemies/CityMachines/'
TYPES = {
    'StrikeDrone/BP_StrikeDrone': 'УДАРНЫЙ ДРОН',
    'BP_Marauder': 'МАРОДЁР',
    'BP_Bastion': 'БАСТИОН',
    'BP_Lynx': 'РЫСЬ',
    'Colossus/BP_Colossus': 'КОЛОСС',
    'BP_PoliceMech': 'ПОЛИЦЕЙСКИЙ МЕХ',
}
CLOAK = 'CyborgSensorCloaked'
RANGE = 6600.
FONT = '/Engine/EngineFonts/Roboto'
RED = '(R=1,G=.14,B=.20,A=.97)'
RED_DIM = '(R=.8,G=.29,B=.31,A=.85)'
WHITE = '(R=.94,G=.87,B=.88,A=.98)'
GLASS = '(R=.024,G=.009,B=.013,A=.84)'


class Lock(GunGraph):
    def parameter(self, name, kind):
        entry = self.e.find_graph_entry_pin().get_owning_node()
        existing = entry.find_output_pin(name)
        if existing.is_valid():
            return existing
        return self.e.add_graph_input_parameter(name,kind)

    def trace_actor(self, start, end):
        ray = self.do(self.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=start,End=end,
                         TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
        hit=self.call('Engine.GameplayStatics.BreakHitResult',Hit=self.out(ray,'OutHit'))
        return self.out(hit,'HitActor')

    def is_actor(self, a, b):
        return self.math('EqualEqual_ObjectObject',A=a,B=b)

    def info(self, enemy, klass):
        return self.out(self.do(self.call('Engine.Actor.GetComponentByClass',target=enemy,ComponentClass=klass)))

    def read(self, owner, klass, name):
        node=self.node(self.e.add_get_member_variable_node(name,klass))
        val(node.find_self_pin(),owner)
        return pin(node,name,True)

    def eye(self):
        return self.out(self.call('Engine.PlayerCameraManager.GetCameraLocation',target=self.view()))

    def rotation(self):
        return self.out(self.call('Engine.PlayerCameraManager.GetCameraRotation',target=self.view()))

    def bounds(self, enemy):
        q=self.do(self.call('Engine.Actor.GetActorBounds',target=enemy,bOnlyCollidingComponents=True))
        return self.out(q,'Origin'),self.out(q,'BoxExtent')

    def xyz(self, v):
        q=self.call('Engine.KismetMathLibrary.BreakVector',InVec=v)
        return [self.out(q,key) for key in 'XYZ']

    def draw_text(self, label, x, y, color, scale=.86):
        self.do(self.call('Engine.HUD.DrawText',target=self.get('ModeCanvasHUD'),Text=label,TextColor=color,
                         ScreenX=x,ScreenY=y,Scale=scale,Font=FONT,bScalePosition=False))

    def rect(self,x,y,w,h,color):
        self.do(self.call('Engine.HUD.DrawRect',target=self.get('ModeCanvasHUD'),RectColor=color,
                         ScreenX=x,ScreenY=y,ScreenW=w,ScreenH=h))

    def line(self,x,y,u,v,color,thick=1.6):
        self.do(self.call('Engine.HUD.DrawLine',target=self.get('ModeCanvasHUD'),LineColor=color,
                         StartScreenX=x,StartScreenY=y,EndScreenX=u,EndScreenY=v,LineThickness=thick))

    def project(self, point):
        q=self.do(self.call('Engine.PlayerController.ProjectWorldLocationToScreen',target=self.pc(),
                            WorldLocation=point,bPlayerViewportRelative=True))
        self.branch(self.out(q))
        xy=self.call('Engine.KismetMathLibrary.BreakVector2D',InVec=self.out(q,'ScreenLocation'))
        return self.out(xy,'X'),self.out(xy,'Y')

    def concat(self,*parts):
        out=parts[0]
        for item in parts[1:]:
            out=self.out(self.call('Engine.KismetStringLibrary.Concat_StrStr',A=out,B=item))
        return out

    def hp_text(self,n):
        return self.out(self.call('Engine.KismetStringLibrary.Conv_IntToString',InInt=self.math('FCeil',A=n)))


def update_hull(g, klass, field, value):
    node=g.node(g.e.add_set_member_variable_node(field,klass))
    val(node.find_self_pin(),g.get('TargetTelemetry'))
    val(pin(node,field),value)
    return g.do(node)


def tag_enemy(bp, component, display):
    klass=B.generated_class(component).get_path_name()
    add(bp,B.generated_class(component),'TargetTelemetry')
    compile_bp(bp)
    g=Lock(bp,'Lock_InitializeTelemetry')
    g.branch(g.valid(g.get('TargetTelemetry')))
    update_hull(g,klass,'MaxHP',g.get('HullHealth'))
    update_hull(g,klass,'HP',g.get('HullHealth'))
    update_hull(g,klass,'TargetLabel',display)
    compile_bp(bp)
    g=Lock(bp)
    if not any(n.get_name()=='TelemetryInit' for n in g.e.list_all_nodes()):
        hook(bp,g.e.find_event_node('ReceiveBeginPlay').find_then_pin(),'Lock_InitializeTelemetry','TelemetryInit')
    wire_damage(bp,klass)


def wire_damage(bp,klass):
    g=Lock(bp)
    event=g.e.find_event_node('ReceiveAnyDamage')
    assert event
    pending=[event]
    seen=set()
    setter=None
    while pending:
        node=pending.pop()
        if node.get_name() in seen:
            continue
        seen.add(node.get_name())
        if node.get_class().get_name()=='K2Node_VariableSet' and node.find_input_pin('HullHealth').is_valid():
            setter=node
            break
        outputs=[node.find_output_pin(str(p.get_pin_name())) for p in node.list_all_pins()
                 if str(p.get_pin_name()) in ('then','else') or str(p.get_pin_name()).startswith('then_')]
        pending.extend(q.get_owning_node() for p in outputs if p.is_valid() for q in p.list_connected_pins())
    assert setter, bp.get_name()
    if any(n.get_name()=='TelemetryOnDamageLive' for n in g.e.list_all_nodes()):
        return
    old_hook=next((n for n in g.e.list_all_nodes() if n.get_name()=='TelemetryOnHit'),None)
    if old_hook:
        predecessor,=old_hook.find_execute_pin().list_connected_pins()
        if predecessor.get_owning_node().get_name()==setter.get_name():
            old_hook.rename('TelemetryOnDamageLive')
            compile_bp(bp)
            return
        sinks=list(old_hook.find_then_pin().list_connected_pins())
        old_hook.find_execute_pin().break_pin_links()
        old_hook.find_then_pin().break_pin_links()
        for sink in sinks:
            link(predecessor,sink)
        # Remove only the private pure inputs created for the misplaced setter.
        inputs=[q.get_owning_node() for p in (old_hook.find_self_pin(),pin(old_hook,'HP'))
                for q in p.list_connected_pins()]
        value_tree=[q.get_owning_node() for n in inputs if n.find_input_pin('A').is_valid()
                    for q in n.find_input_pin('A').list_connected_pins()]
        g.e.remove_nodes([old_hook,*inputs,*value_tree])
    g.cursor=setter.find_then_pin()
    previous=list(g.cursor.list_connected_pins())
    g.cursor.break_pin_links()
    n=update_hull(g,klass,'HP',g.math('FMax',A=g.get('HullHealth'),B=0.))
    n.rename('TelemetryOnDamageLive')
    for sink in previous:
        link(g.cursor,sink)
    compile_bp(bp)

def player_vars(bp):
    vec=B.get_struct_type(unreal.Vector.static_struct())
    for name,kind,value in (
        ('LockEnabled','bool','false'), ('LockKeyDown','bool','false'), ('LockAutoShot','bool','false'),
        ('LockTarget',actorref(),'None'), ('LockBest',actorref(),'None'),
        ('LockList',B.get_array_type(actorref()),'()'), ('LockAim',vec,'(X=0,Y=0,Z=0)'),
        ('LockProbePoint',vec,'(X=0,Y=0,Z=0)'), ('LockProbeValid','bool','false'),
        ('LockProbeScore','real','0'), ('LockBestScore','real','-1'),
        ('LockNextScan','real','0'), ('LockNextTick','real','0'), ('LockShots','int','0'),
    ):
        var(bp,name,kind,value)
    compile_bp(bp)
    # Players can opt in with T. Automatic fire would compromise the silent patrol route.
    unreal.get_default_object(B.generated_class(bp)).set_editor_property('LockEnabled',False)


def author_acquisition(bp, klass):
    g=Lock(bp,'Lock_Probe')
    enemy=g.parameter('Enemy',actorref())
    min_dot=g.parameter('MinDot',B.get_basic_type_by_name('real'))
    g.set('LockProbeValid',False)
    g.branch(g.valid(enemy))
    telemetry=g.info(enemy,klass)
    g.branch(g.valid(telemetry))
    g.branch(g.gt(g.read(telemetry,klass,'HP'),0.))
    center,_=g.bounds(enemy)
    delta=g.vs(center,g.eye())
    dist=g.math('VSize',A=delta)
    g.branch(g.math('Less_DoubleDouble',A=dist,B=RANGE))
    view=g.math('GetForwardVector',InRot=g.rotation())
    direction=g.math('Normal',A=delta,Tolerance=.001)
    dot=g.math('Dot_VectorVector',A=direction,B=view)
    g.branch(g.gt(dot,min_dot))
    hit=g.trace_actor(g.eye(),center)
    g.branch(g.is_actor(hit,enemy))
    g.set('LockProbePoint',center)
    g.set('LockProbeScore',g.minus(dot,g.mul(dist,.000009)))
    g.set('LockProbeValid',True)
    compile_bp(bp)

    g=Lock(bp,'Lock_Consider')
    candidate=g.parameter('Candidate',actorref())
    node=g.own('Lock_Probe')
    val(pin(node,'Enemy'),candidate)
    val(pin(node,'MinDot'),.945)
    g.do(node)
    g.branch(g.get('LockProbeValid'))
    g.branch(g.gt(g.get('LockProbeScore'),g.get('LockBestScore')))
    g.set('LockBestScore',g.get('LockProbeScore'))
    g.set('LockBest',candidate)
    g.set('LockAim',g.get('LockProbePoint'))
    compile_bp(bp)

    g=Lock(bp,'Lock_ScanAt')
    index=g.parameter('Index',B.get_basic_type_by_name('int'))
    length=g.out(g.call('Engine.KismetArrayLibrary.Array_Length',TargetArray=g.get('LockList')))
    g.branch(g.yes(g.math('Less_IntInt',A=index,B=length),g.math('Less_IntInt',A=index,B=32)))
    item=g.out(g.call('Engine.KismetArrayLibrary.Array_Get',TargetArray=g.get('LockList'),Index=index),'Item')
    call=g.own('Lock_Consider')
    val(pin(call,'Candidate'),item)
    g.do(call)
    compile_bp(bp)
    recurse=g.own('Lock_ScanAt')
    val(pin(recurse,'Index'),g.math('Add_IntInt',A=index,B=1))
    g.do(recurse)
    compile_bp(bp)

    g=Lock(bp,'Lock_Acquire')
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('LockNextScan')))
    g.set('LockNextScan',g.plus(g.now(),.12))
    found=g.do(g.call('Engine.GameplayStatics.GetAllActorsWithTag',Tag='CyborgHostile'))
    g.set('LockList',g.out(found,'OutActors'))
    g.set('LockBest','None')
    g.set('LockBestScore',-1.)
    recurse=g.own('Lock_ScanAt')
    val(pin(recurse,'Index'),0)
    g.do(recurse)
    g.set('LockTarget',g.get('LockBest'))
    compile_bp(bp)


def wire_aim_point(bp):
    g=Lock(bp,'Laser_Fire',keep=True)
    setter=next(n for n in g.e.list_all_nodes()
                if n.get_class().get_name()=='K2Node_VariableSet' and n.find_input_pin('WeaponAimPoint').is_valid())
    aim_pin=pin(setter,'WeaponAimPoint')
    original,=aim_pin.list_connected_pins()
    if original.get_owning_node().get_name()=='TargetLockAimPoint':
        return
    aim_pin.break_pin_links()
    selected=g.pick('Vector',g.get('LockAim'),original,g.get('LockAutoShot'))
    selected.get_owning_node().rename('TargetLockAimPoint')
    val(aim_pin,selected)
    compile_bp(bp)

def author_firing(bp):
    g=Lock(bp,'Lock_FireIfClear')
    target=g.get('LockTarget')
    g.branch(g.valid(target))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('LaserNextFire')))
    g.branch(g.eq(g.get('WeaponReloadMode'),0))
    g.branch(g.math('Greater_IntInt',A=g.get('HunterMagazine'),B=0))
    muzzle=g.pick('Vector',g.loc('AtomicFPMuzzle'),g.loc('AtomicTPMuzzle'),g.get('bFirstPerson'))
    aim=g.get('LockAim')
    near=g.trace_actor(g.eye(),muzzle)
    g.branch(g.no(g.valid(near)))
    hit=g.trace_actor(muzzle,aim)
    g.branch(g.is_actor(hit,target))
    g.set('LockAutoShot',True)
    g.do(g.own('Laser_Fire'))
    g.set('LockAutoShot',False)
    g.count('LockShots')
    compile_bp(bp)

    g=Lock(bp,'Lock_Update')
    g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
    g.branch(g.valid(g.pc()))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('LockNextTick')))
    g.set('LockNextTick',g.plus(g.now(),.043))
    ignored=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))
    cloak=g.out(g.call('Engine.Actor.ActorHasTag',Tag=CLOAK))
    allowed=g.get('LockEnabled')
    for condition in (g.mode(1),g.get('bFirstPerson'),g.no(ignored),g.no(cloak),
                      g.no(g.get('bModeMenuOpen')),g.no(g.get('NavMapOpen')),g.no(g.get('bAdminFlight')),
                      g.gt(g.get('VisorIntegrity'),0.)):
        allowed=g.yes(allowed,condition)
    enabled=g.branch(allowed)
    holding=g.branch(g.valid(g.get('LockTarget')))
    probe=g.own('Lock_Probe')
    val(pin(probe,'Enemy'),g.get('LockTarget'))
    val(pin(probe,'MinDot'),.88)
    g.do(probe)
    visible=g.branch(g.get('LockProbeValid'))
    g.set('LockAim',g.get('LockProbePoint'))
    shot=g.do(g.own('Lock_FireIfClear'))
    g.cursor=visible.find_else_pin()
    g.set('LockTarget','None')
    g.cursor=holding.find_else_pin()
    g.do(g.own('Lock_Acquire'))
    link(g.cursor,shot.find_execute_pin())
    g.cursor=enabled.find_else_pin()
    g.set('LockTarget','None')
    compile_bp(bp)

    g=Lock(bp,'Laser_Fire',keep=True)
    setter=next(n for n in g.e.list_all_nodes()
                if n.get_class().get_name()=='K2Node_VariableSet' and n.find_input_pin('WeaponRayDirection').is_valid())
    direction=pin(setter,'WeaponRayDirection')
    previous,=direction.list_connected_pins()
    direction.break_pin_links()
    aim=g.math('Normal',A=g.vs(g.get('LockAim'),g.eye()),Tolerance=.001)
    val(direction,g.pick('Vector',aim,previous,g.get('LockAutoShot')))
    kick=next(n for n in g.e.list_all_nodes()
              if 'AddControllerPitchInput' in str(n.get_node_title()).replace(' ',''))
    value=pin(kick,'Val')
    manual,=value.list_connected_pins()
    value.break_pin_links()
    val(value,g.pick('Float',0.,manual,g.get('LockAutoShot')))
    compile_bp(bp)
    wire_aim_point(bp)

    g=Lock(bp,'Lock_Toggle')
    g.branch(g.no(g.get('LockKeyDown')))
    g.set('LockKeyDown',True)
    g.set('LockEnabled',g.no(g.get('LockEnabled')))
    g.set('LockTarget','None')
    compile_bp(bp)
    g=Lock(bp)
    menu=next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|T'))
    key=g.e.create_node_from_name(menu,unreal.Vector2D(x=-9000,y=12500),[])
    key.rename('TargetLockToggle')
    key.set_editor_property('bConsumeInput',False)
    g.cursor=pin(key,'Pressed',True)
    g.do(g.own('Lock_Toggle'))
    g.cursor=pin(key,'Released',True)
    g.set('LockKeyDown',False)
    hook(bp,g.e.find_event_node('ReceiveTick').find_then_pin(),'Lock_Update','TargetLockTick')
    compile_bp(bp)


def author_hud(bp, klass):
    g=Lock(bp,'Modes_DrawOneThreat')
    enemy=g.parameter('Enemy',actorref())
    g.branch(g.no(g.get('NavMapOpen')))
    g.branch(g.valid(enemy))
    telemetry=g.info(enemy,klass)
    g.branch(g.valid(telemetry))
    hp=g.read(telemetry,klass,'HP')
    cap=g.math('FMax',A=g.read(telemetry,klass,'MaxHP'),B=1.)
    g.branch(g.gt(hp,0.))
    center,extent=g.bounds(enemy)
    delta=g.vs(center,g.eye())
    g.branch(g.math('Less_DoubleDouble',A=g.math('VSize',A=delta),B=RANGE))
    facing=g.math('Dot_VectorVector',A=delta,B=g.math('GetForwardVector',InRot=g.rotation()))
    g.branch(g.gt(facing,20.))
    g.branch(g.is_actor(g.trace_actor(g.eye(),center),enemy))
    locked=g.is_actor(enemy,g.get('LockTarget'))
    ex,ey,ez=g.xyz(extent)
    up=g.vec(0.,0.,g.plus(ez,15.))
    right=g.vm(g.math('GetRightVector',InRot=g.rotation()),g.plus(g.math('FMax',A=ex,B=ey),22.))
    cx,cy=g.project(center)
    _,top=g.project(g.va(center,up))
    _,bottom=g.project(g.vs(center,up))
    rx,_=g.project(g.va(center,right))
    for axis,limit in ((cx,g.get('ModeScreenW')),(cy,g.get('ModeScreenH'))):
        g.branch(g.yes(g.gt(axis,32.),g.math('Less_DoubleDouble',A=axis,B=g.minus(limit,32.))))
    xhalf=g.limit(g.math('Abs',A=g.minus(rx,cx)),22.,260.)
    yhalf=g.limit(g.mul(g.math('Abs',A=g.minus(bottom,top)),.5),16.,245.)
    left=g.minus(cx,xhalf)
    right=g.plus(cx,xhalf)
    upper=g.minus(cy,yhalf)
    lower=g.plus(cy,yhalf)
    percent=g.limit(g.div(hp,cap))
    rail_width=g.pick('Float',132.,94.,locked)
    rail_x=g.minus(cx,g.mul(rail_width,.5))
    rail_y=g.math('FMax',A=24.,B=g.minus(upper,12.))
    tint=g.pick('Color',RED,RED_DIM,locked)
    g.rect(g.minus(rail_x,2.),g.minus(rail_y,2.),g.plus(rail_width,4.),8.,GLASS)
    g.rect(rail_x,rail_y,g.mul(rail_width,percent),3.,tint)
    number=g.concat(g.hp_text(hp),' / ',g.hp_text(cap))
    g.draw_text(number,g.minus(cx,25.),g.minus(rail_y,17.),WHITE,.76)
    g.count('ModeDetectedCount')

    h=g.limit(g.mul(xhalf,.37),10.,26.)
    v=g.limit(g.mul(yhalf,.32),9.,24.)
    for x,y,dx,dy in ((left,upper,h,v),(right,upper,g.mul(h,-1.),v),
                       (left,lower,h,g.mul(v,-1.)),(right,lower,g.mul(h,-1.),g.mul(v,-1.))):
        g.line(x,y,g.plus(x,dx),y,tint,1.6)
        g.line(x,y,x,g.plus(y,dy),tint,1.6)
    g.branch(locked)
    title=g.concat('ЗАХВАТ  /  ',g.read(telemetry,klass,'TargetLabel'))
    g.draw_text(title,g.minus(cx,80.),g.math('FMax',A=6.,B=g.minus(rail_y,35.)),RED,.84)
    compile_bp(bp)

    g=Lock(bp,'Lock_DrawStatus')
    g.branch(g.mode(1))
    g.branch(g.get('bFirstPerson'))
    status=g.pick('String','T  АВТОЗАХВАТ  ВКЛ','T  АВТОЗАХВАТ  ВЫКЛ',g.get('LockEnabled'))
    g.draw_text(status,g.minus(g.get('ModeScreenW'),178.),g.minus(g.get('ModeScreenH'),131.),
                '(R=.69,G=.80,B=.83,A=.94)',.72)
    compile_bp(bp)
    g=Lock(bp,'Modes_DrawHUD',keep=True)
    if any(n.get_name()=='LockStatusHUD' for n in g.e.list_all_nodes()):
        return
    set_canvas=next(n for n in g.e.list_all_nodes() if n.get_class().get_name()=='K2Node_VariableSet'
                    and n.find_input_pin('ModeUIScale').is_valid())
    g.cursor=set_canvas.find_then_pin()
    old=list(g.cursor.list_connected_pins())
    g.cursor.break_pin_links()
    existing=next((n for n in g.e.list_all_nodes() if str(n.get_node_title()).replace(' ','')=='Lock_DrawStatus'),None)
    if existing:
        existing.rename('LockStatusHUD')
        for sink in old:
            link(g.cursor,sink)
        compile_bp(bp)
        return
    g.do(g.own('Lock_DrawStatus')).rename('LockStatusHUD')
    for sink in old:
        link(g.cursor,sink)
    compile_bp(bp)


def install():
    content=Path(unreal.Paths.project_content_dir())
    backup=Path(unreal.Paths.project_saved_dir())/'Backups/TargetLock'/datetime.now().strftime('%Y%m%d_%H%M%S')
    paths=[PLAYER,*(MACHINES+name for name in TYPES)]
    for path in paths:
        rel=Path(path.removeprefix('/Game/')+'.uasset')
        dest=backup/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(content/rel,dest)
    component=asset(ROOT+'/BP_TargetTelemetry',unreal.ActorComponent)
    for name,kind,initial in (('HP','real','0'),('MaxHP','real','0'),('TargetLabel','string','')):
        var(component,name,kind,initial)
    compile_bp(component)
    save(component)
    enemies=[]
    for path,title in TYPES.items():
        bp=A.load_asset(MACHINES+path)
        tag_enemy(bp,component,title)
        enemies.append(bp)
    player=A.load_asset(PLAYER)
    player_vars(player)
    klass=B.generated_class(component).get_path_name()
    author_acquisition(player,klass)
    author_firing(player)
    author_hud(player,klass)
    for bp in (player,*enemies):
        save(bp)
    unreal.log('Target lock and live hostile health saved')


if __name__=='__main__':
    install()



