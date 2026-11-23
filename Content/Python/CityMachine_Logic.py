"""Blueprint authoring for bounded patrols, pursuit, flight and ranged combat."""
import unreal

from CityCombat_Common import A, B, G, Graph, actorref, compile_bp, link, pin, var


class Logic(Graph):
    def self(self, component='Hull'):
        return super().self(component)

    def addv(self,a,b):
        return self.math('Add_VectorVector',A=a,B=b)

    def subv(self,a,b):
        return self.math('Subtract_VectorVector',A=a,B=b)

    def scale(self,a,b):
        return self.math('Multiply_VectorFloat',A=a,B=b)

    def vector(self,x=0.,y=0.,z=0.):
        return self.math('MakeVector',X=x,Y=y,Z=z)

    def axis(self,v,axis):
        return self.out(self.call('Engine.KismetMathLibrary.BreakVector',InVec=v),axis)

    def position(self,target=None):
        return self.out(self.call('Engine.Actor.K2_GetActorLocation',target=target))

    def select(self,a,b,condition,kind='Vector'):
        return self.math('Select'+kind,A=a,B=b,bPickA=condition)

    def num(self,op,a,b):
        return self.math(op+'_DoubleDouble',A=a,B=b)

    def compare(self,op,a,b):
        return self.math(op+'_IntInt',A=a,B=b)

    def flatten(self,v):
        return self.vector(self.axis(v,'X'),self.axis(v,'Y'))

    def distance(self,a,b):
        return self.math('VSize',A=self.subv(a,b))

    def trace(self,a,b):
        t=self.do(self.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=a,End=b,
                     TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
        return self.out(t),self.call('Engine.GameplayStatics.BreakHitResult',Hit=self.out(t,'OutHit'))

    def event_call(self,event,fn):
        node=self.override(event)
        self.do(self.own(fn))
        return node

    def sound(self,key,location,volume):
        return self.do(self.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=key,
                    Location=location,VolumeMultiplier=volume))


def variables(bp):
    for n,kind,default in (
        ('HullHeight','real',245),('HullHealth','real',980),
        ('CruiseSpeed','real',340),('CombatSpeed','real',580),('SensorRange','real',4200),
        ('FireRange','real',2300),('KeepRange','real',1250),('ShotDamage','real',17),
        ('FireCooldown','real',1.4),('Windup','real',.55),('PlanAt','real',0),
        ('NextShot','real',0),('ChargeUntil','real',0),('LastSeen','real',-100),
        ('PatrolIndex','int',0),('Mode','int',0),('Shots','int',0),('Sightings','int',0),
        ('DistanceMoved','real',0),('HasSight','bool','false'),('Charging','bool','false'),
        ('Flying','bool','false'),('Destroyed','bool','false'),
    ):
        var(bp,n,kind,str(default))
    for n in ('Target','RelayContact'):
        var(bp,n,actorref(),'None')
    vec=B.get_struct_type(unreal.Vector.static_struct())
    for n in ('Home','Goal','LastPoint','BeforeMove','NextPosition'):
        var(bp,n,vec,'(X=0,Y=0,Z=0)')
    for n in ('PointA','PointB','PointC','PointD'):
        var(bp,n,vec,'(X=0,Y=0,Z=0)')
    compile_bp(bp)
    for n in ('PointA','PointB','PointC','PointD'):
        B.set_blueprint_variable_instance_editable(bp,n,True)
    compile_bp(bp)


def patrol(bp):
    g=Logic(bp,'Patrol')
    g.set('Mode',0)
    current=g.get('PatrolIndex')
    choice=g.select(g.get('PointC'),g.get('PointD'),g.compare('EqualEqual',current,2))
    choice=g.select(g.get('PointB'),choice,g.compare('EqualEqual',current,1))
    g.set('Goal',g.addv(g.get('Home'),g.select(g.get('PointA'),choice,g.compare('EqualEqual',current,0))))
    g.branch(g.num('Less',g.distance(g.position(),g.get('Goal')),150.))
    g.set('PatrolIndex',g.math('Percent_IntInt',A=g.math('Add_IntInt',A=current,B=1),B=4))
    compile_bp(bp)


def plan(bp,contact,role):
    g=Logic(bp,'Plan')
    g.set('Target',g.player())
    g.set('HasSight',False)
    g.do(g.own('Patrol'))
    g.branch(g.valid(g.get('Target')))
    g.branch(g.num('Less',g.distance(g.get('Home'),g.position(g.get('Target'))),7400.))
    eye=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('Sensor')))
    target=g.position(g.get('Target'))
    g.branch(g.num('Less',g.distance(eye,target),g.get('SensorRange')))
    _,hit=g.trace(eye,target)
    seen=g.branch(g.math('EqualEqual_ObjectObject',A=g.out(hit,'HitActor'),B=g.get('Target')))
    missing=seen.find_else_pin()
    g.set('HasSight',True)
    g.count('Sightings')
    g.set('LastSeen',g.now())
    g.set('LastPoint',target)
    g.set('Mode',2)
    offset=g.subv(target,g.position())
    direction=g.math('Normal',A=g.flatten(offset),Tolerance=.001)
    side=g.vector(g.num('Multiply',g.axis(direction,'Y'),-1.),g.axis(direction,'X'))
    if role=='Relay':
        g.set('Goal',g.addv(g.get('Home'),g.addv(g.scale(side,490.),g.vector(z=300.))))
        g.branch(g.num('GreaterEqual',g.now(),g.get('NextShot')))
        g.set('NextShot',g.num('Add',g.now(),2.2))
        g.spawn(contact,target,owner=g.self())
        g.sound('/Game/Combat/CyborgModes/S_ModeSelect',eye,.57)
        g.count('Shots')
    elif role=='Wasp':
        sway=g.num('Multiply',g.math('Sin',A=g.num('Multiply',g.now(),.64)),970.)
        orbit=g.addv(g.subv(target,g.scale(direction,730.)),g.scale(side,sway))
        g.set('Goal',g.addv(orbit,g.vector(z=730.)))
    else:
        distance=g.math('VSize',A=g.flatten(offset))
        wanted=g.get('KeepRange')
        if role=='Lynx':
            escape=g.subv(g.position(),g.scale(direction,540.))
            attack=g.select(escape,g.position(),g.num('Less',distance,g.num('Multiply',wanted,.73)))
        elif role=='Marauder':
            sweep=g.num('Multiply',g.math('Sin',A=g.num('Multiply',g.now(),.85)),460.)
            attack=g.addv(g.position(),g.scale(side,sweep))
        else:
            attack=g.position()
        chase=g.addv(target,g.scale(side,390.)) if role=='Marauder' else target
        g.set('Goal',g.select(chase,attack,g.num('Greater',distance,wanted)))
    g.cursor=missing
    in_memory=g.branch(g.num('Less',g.num('Subtract',g.now(),g.get('LastSeen')),4.5))
    try_relay=in_memory.find_else_pin()
    g.branch(g.num('Less',g.distance(g.position(),g.get('Home')),7000.))
    g.set('Mode',1)
    g.set('Goal',g.addv(g.get('LastPoint'),g.vector(z=730.)) if role in ('Wasp','Relay') else g.get('LastPoint'))
    if role not in ('Relay','Wasp'):
        g.cursor=try_relay
        relay=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=contact))
        g.set('RelayContact',g.out(relay))
        g.branch(g.valid(g.get('RelayContact')))
        marked=g.position(g.get('RelayContact'))
        g.branch(g.num('Less',g.distance(g.get('Home'),marked),4800.))
        g.set('Mode',1)
        g.set('Goal',marked)
    compile_bp(bp)


def motion(bp,role,parts,custom_gait=False):
    flying=role in ('Relay','Wasp')
    g=Logic(bp,'MoveMachine')
    g.set('BeforeMove',g.position())
    where=g.get('BeforeMove')
    delta=g.subv(g.get('Goal'),where)
    if not flying:
        delta=g.flatten(delta)
    g.branch(g.num('Greater',g.math('VSize',A=delta),28.))
    direction=g.math('Normal',A=delta,Tolerance=.001)
    if custom_gait:
        facing=g.out(g.call('Engine.Actor.GetActorForwardVector'))
        g.branch(g.num('Greater',g.math('Dot_VectorVector',A=direction,B=facing),.57))
    speed=g.select(g.get('CombatSpeed'),g.get('CruiseSpeed'),g.compare('Greater',g.get('Mode'),0),'Float')
    step=g.math('FMin',A=g.num('Multiply',speed,g.dt()),B=g.math('VSize',A=delta))
    g.set('NextPosition',g.addv(where,g.scale(direction,step)))
    if not flying:
        next_pos=g.get('NextPosition')
        foot=g.subv(next_pos,g.vector(z=g.get('HullHeight')))
        floor,hit=g.trace(g.addv(foot,g.vector(z=100.)),g.subv(foot,g.vector(z=165.)))
        floor_check=g.branch(floor)
        g.cursor=floor_check.find_else_pin()
        g.set('PatrolIndex',g.math('Percent_IntInt',A=g.math('Add_IntInt',A=g.get('PatrolIndex'),B=1),B=4))
        g.set('Goal',g.get('Home'))
        g.cursor=floor_check.find_then_pin()
        g.set('NextPosition',g.addv(g.out(hit,'ImpactPoint'),g.vector(z=g.get('HullHeight'))))
    g.do(g.call('Engine.Actor.K2_SetActorLocation',NewLocation=g.get('NextPosition'),bSweep=True,bTeleport=False))
    moved=g.distance(g.position(),where)
    g.set('DistanceMoved',g.num('Add',g.get('DistanceMoved'),moved))
    g.branch(g.num('Less',moved,.18))
    g.branch(g.num('LessEqual',g.get('PlanAt'),g.num('Add',g.now(),.10)))
    g.set('PatrolIndex',g.math('Percent_IntInt',A=g.math('Add_IntInt',A=g.get('PatrolIndex'),B=1),B=4))
    # Small swept tangent offset lets the next planning step take a different line.
    side=g.vector(g.axis(direction,'Y'),g.num('Multiply',g.axis(direction,'X'),-1.),80. if flying else 0.)
    g.do(g.call('Engine.Actor.K2_SetActorLocation',NewLocation=g.addv(g.position(),g.scale(side,24.)),
                bSweep=True,bTeleport=False))
    compile_bp(bp)

    if custom_gait:
        return
    g=Logic(bp,'AnimateMachine')
    current=g.out(g.call('Engine.Actor.K2_GetActorRotation'))
    look=g.select(g.get('LastPoint'),g.get('Goal'),g.get('HasSight'))
    look_direction=g.flatten(g.subv(look,g.position()))
    facing=g.math('MakeRotFromX',X=look_direction)
    turning=g.math('RInterpTo',Current=current,Target=facing,DeltaTime=g.dt(),InterpSpeed=4.2 if flying else 2.7)
    yaw=g.branch(g.num('Greater',g.math('VSize',A=look_direction),36.))
    turn=g.do(g.call('Engine.Actor.K2_SetActorRotation',NewRotation=turning,bTeleportPhysics=False))
    if parts:
        gait=g.num('Multiply',g.get('DistanceMoved'),.014 if role=='Bastion' else .022)
        g.cursor=yaw.find_else_pin()
        idle=g.math('MakeRotator',Roll=0.,Pitch=0.,Yaw=0.)
        for i in range(parts):
            g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('Leg'+str(i)),
                        NewRotation=idle,bSweep=False,bTeleport=False))
        g.cursor=turn.find_then_pin()
        for i in range(parts):
            angle=g.num('Add',gait,math_pi(i))
            pitch=g.num('Multiply',g.math('Sin',A=angle),16. if role!='Bastion' else 11.)
            g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('Leg'+str(i)),
                    NewRotation=g.math('MakeRotator',Roll=0.,Pitch=pitch,Yaw=0.),bSweep=False,bTeleport=False))
    compile_bp(bp)


def math_pi(i):
    return 3.141592653589793 * (i in (1,2))


def firing(bp,role,tracer,sound):
    if role=='Relay':
        return
    g=Logic(bp,'Combat')
    ready=g.branch(g.get('HasSight'))
    g.branch(g.valid(g.get('Target')))
    muzzle=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('Muzzle')))
    if role=='Colossus':
        alternate=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('MuzzleRight')))
        even=g.compare('EqualEqual',g.math('Percent_IntInt',A=g.get('Shots'),B=2),0)
        muzzle=g.select(muzzle,alternate,even)
    target=g.position(g.get('Target'))
    g.branch(g.num('Less',g.distance(muzzle,target),g.get('FireRange')))
    charging=g.branch(g.get('Charging'))
    start_charge=charging.find_else_pin()
    g.branch(g.num('GreaterEqual',g.now(),g.get('ChargeUntil')))
    g.set('Charging',False)
    g.set('NextShot',g.num('Add',g.now(),g.get('FireCooldown')))
    aim=g.addv(target,g.vector(g.math('RandomFloatInRange',Min=-26.,Max=26.),
                              g.math('RandomFloatInRange',Min=-25.,Max=25.),0.))
    direction=g.math('Normal',A=g.subv(aim,muzzle),Tolerance=.001)
    end=g.addv(muzzle,g.scale(direction,g.get('FireRange')))
    hit,parts=g.trace(muzzle,end)
    impact=g.select(g.out(parts,'ImpactPoint'),end,hit)
    d=g.subv(impact,muzzle)
    fx=g.spawn(tracer,g.addv(muzzle,g.scale(d,.5)),g.math('MakeRotFromZ',Z=d),g.self())
    beam={'Colossus':.115,'Lynx':.065,'Bastion':.044}.get(role,.024)
    g.do(g.call('Engine.Actor.SetActorScale3D',target=fx,NewScale3D=g.vector(beam,beam,
        g.num('Divide',g.math('VSize',A=d),100.))))
    g.sound(sound,muzzle,.69)
    g.count('Shots')
    g.branch(g.math('EqualEqual_ObjectObject',A=g.out(parts,'HitActor'),B=g.get('Target')))
    g.do(g.call('Engine.GameplayStatics.ApplyDamage',DamagedActor=g.get('Target'),BaseDamage=g.get('ShotDamage'),
                DamageCauser=g.self()))
    g.cursor=start_charge
    g.branch(g.num('GreaterEqual',g.now(),g.get('NextShot')))
    g.set('ChargeUntil',g.num('Add',g.now(),g.get('Windup')))
    g.set('Charging',True)
    if role in ('Bastion','Lynx','Colossus'):
        g.sound('/Game/Combat/CyborgModes/S_ModeSelect',muzzle,.38)
    g.cursor=ready.find_else_pin()
    g.set('Charging',False)
    compile_bp(bp)


def events(bp,role,custom_init=False):
    if not custom_init:
        g=Logic(bp,'MachineInit')
        g.set('Home',g.position())
        g.set('Goal',g.addv(g.get('Home'),g.get('PointA')))
        tags=g.e.add_get_member_variable_node('Tags','/Script/Engine.Actor')
        hostile=g.out(g.call('Engine.KismetSystemLibrary.MakeLiteralName',Value='CyborgHostile'))
        g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=pin(tags,'Tags',True),NewItem=hostile))
        compile_bp(bp)
    g=Logic(bp,'MachineTick')
    g.branch(g.math('Not_PreBool',A=g.get('Destroyed')))
    cadence=g.branch(g.num('GreaterEqual',g.now(),g.get('PlanAt')))
    skip=cadence.find_else_pin()
    g.set('PlanAt',g.num('Add',g.now(),.32))
    g.do(g.own('Plan'))
    move=g.do(g.own('MoveMachine'))
    link(skip,move.find_execute_pin())
    g.do(g.own('AnimateMachine'))
    if role!='Relay':
        g.do(g.own('Combat'))
    compile_bp(bp)
    g=Logic(bp)
    g.event_call('ReceiveBeginPlay','MachineInit')
    g.event_call('ReceiveTick','MachineTick')
    ev=g.override('ReceiveAnyDamage')
    g.branch(g.math('Not_PreBool',A=g.get('Destroyed')))
    g.set('HullHealth',g.num('Subtract',g.get('HullHealth'),pin(ev,'Damage',True)))
    g.branch(g.num('LessEqual',g.get('HullHealth'),0.))
    g.set('Destroyed',True)
    g.do(g.call('Engine.Actor.SetActorEnableCollision',bNewActorEnableCollision=False))
    g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=1.1))
    tilt=g.out(g.call('Engine.Actor.K2_GetActorRotation'))
    g.do(g.call('Engine.Actor.K2_SetActorRotation',NewRotation=g.math('MakeRotator',
                 Roll=27.,Pitch=-14.,Yaw=g.out(g.call('Engine.KismetMathLibrary.BreakRotator',InRot=tilt),'Yaw')),
                 bTeleportPhysics=True))
    compile_bp(bp)
