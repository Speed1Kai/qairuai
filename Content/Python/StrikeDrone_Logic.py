"""Blueprint graphs for swept flight, two-axis gun mounts and burst fire."""
import unreal

from CityCombat_Common import compile_bp, link, pin, var
from CityMachine_Logic import Logic, patrol, variables

ROOT='/Game/Enemies/CityMachines/StrikeDrone'
WEAPONS='/Game/Combat/Firearms'
SHOTS=tuple(WEAPONS+'/S_Hunter_Shot_'+str(i) for i in range(1,4))
STREAK_SPEED=24000.
BURST_ROUNDS=6
SHOT_INTERVAL=.085


class DroneGraph(Logic):
    def loc(self,component):
        return self.out(self.call('Engine.SceneComponent.K2_GetComponentLocation',target=self.get(component)))

    def rotation(self,component):
        return self.out(self.call('Engine.SceneComponent.K2_GetComponentRotation',target=self.get(component)))

    def rot(self,pitch=0.,yaw=0.,roll=0.):
        return self.math('MakeRotator',Pitch=pitch,Yaw=yaw,Roll=roll)

    def rpart(self,rotation,axis):
        return self.out(self.call('Engine.KismetMathLibrary.BreakRotator',InRot=rotation),axis)

    def limit(self,value,lo,hi):
        return self.math('FClamp',Value=value,Min=lo,Max=hi)

    def unit(self,vector):
        return self.math('Normal',A=vector,Tolerance=.001)

    def interpolate(self,current,target,speed):
        return self.math('FInterpTo',Current=current,Target=target,DeltaTime=self.dt(),InterpSpeed=speed)

    def both(self,a,b):
        return self.math('BooleanAND',A=a,B=b)

    def opposite(self,b):
        return self.math('Not_PreBool',A=b)

    def location(self,p):
        return self.do(self.call('Engine.Actor.K2_SetActorLocation',NewLocation=p,bSweep=True,bTeleport=False))

    def turn(self,component,rotation):
        return self.do(self.call('Engine.SceneComponent.K2_SetRelativeRotation',target=self.get(component),
                                 NewRotation=rotation,bSweep=False,bTeleport=False))

    def shot_sound(self,sound,origin):
        self.do(self.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=sound,Location=origin,
            VolumeMultiplier=.74,PitchMultiplier=self.math('RandomFloatInRange',Min=.84,Max=.99),
            AttenuationSettings=ROOT+'/ATT_StrikeGun'))


def state(bp):
    variables(bp)
    for name,kind,initial in (
        ('AvoidUntil','real','0'),('NextPass','real','0'),('StrafeSide','real','1'),
        ('NextBurst','real','0'),('BurstLeft','int','0'),('Bursts','int','0'),
        ('RotorAngle','real','0'),('RecoilL','real','0'),('RecoilR','real','0'),
        ('MaxObservedSpeed','real','0'),('Hits','int','0'),('Streaks','int','0'),
    ):
        var(bp,name,kind,initial)
    from CityCombat_Common import B
    vec=B.get_struct_type(unreal.Vector.static_struct())
    for name in ('FlightVelocity','AvoidPoint','RoundOrigin','RoundDir','RoundEnd'):
        var(bp,name,vec,'(X=0,Y=0,Z=0)')
    compile_bp(bp)


def tactics(bp):
    patrol(bp)
    g=DroneGraph(bp,'Plan')
    g.do(g.own('Patrol'))
    g.set('HasSight',False)
    g.set('Target',g.player())
    g.branch(g.valid(g.get('Target')))
    target=g.position(g.get('Target'))
    g.branch(g.num('Less',g.distance(g.get('Home'),target),6800.))
    eye=g.loc('Sensor')
    g.branch(g.num('Less',g.distance(eye,target),g.get('SensorRange')))
    _,hit=g.trace(eye,target)
    visible=g.branch(g.math('EqualEqual_ObjectObject',A=g.out(hit,'HitActor'),B=g.get('Target')))
    g.set('HasSight',True)
    g.set('LastSeen',g.now())
    g.set('LastPoint',target)
    g.set('Mode',2)
    g.count('Sightings')
    direction=g.unit(g.flatten(g.subv(target,g.position())))
    normal=g.vector(g.num('Multiply',g.axis(direction,'Y'),-1.),g.axis(direction,'X'))
    distance=g.distance(g.flatten(target),g.flatten(g.position()))
    close=g.num('Less',distance,950.)
    approach=g.select(1800.,1260.,close,'Float')
    side=g.scale(normal,g.num('Multiply',g.get('StrafeSide'),1270.))
    altitude=g.num('Add',760.,g.num('Multiply',g.math('Sin',A=g.num('Multiply',g.now(),2.1)),245.))
    flank=g.addv(g.subv(target,g.scale(direction,approach)),g.addv(side,g.vector(z=altitude)))
    g.set('Goal',flank)
    g.branch(g.num('GreaterEqual',g.now(),g.get('NextPass')))
    g.set('NextPass',g.num('Add',g.now(),g.math('RandomFloatInRange',Min=1.75,Max=2.45)))
    g.set('StrafeSide',g.num('Multiply',-1.,g.get('StrafeSide')))
    g.cursor=visible.find_else_pin()
    g.branch(g.num('Less',g.num('Subtract',g.now(),g.get('LastSeen')),2.0))
    g.set('Mode',1)
    g.set('Goal',g.addv(g.get('LastPoint'),g.vector(z=920.)))
    compile_bp(bp)


def flight(bp):
    g=DroneGraph(bp,'MoveMachine')
    g.set('BeforeMove',g.position())
    avoid=g.num('Less',g.now(),g.get('AvoidUntil'))
    goal=g.select(g.get('AvoidPoint'),g.get('Goal'),avoid)
    delta=g.subv(goal,g.get('BeforeMove'))
    distance=g.math('VSize',A=delta)
    speed=g.select(g.get('CombatSpeed'),g.get('CruiseSpeed'),g.compare('Greater',g.get('Mode'),0),'Float')
    wanted=g.scale(g.unit(delta),g.math('FMin',A=speed,B=g.num('Multiply',distance,3.4)))
    smooth=g.math('VInterpTo',Current=g.get('FlightVelocity'),Target=wanted,DeltaTime=g.dt(),InterpSpeed=3.8)
    g.set('FlightVelocity',smooth)
    move=g.location(g.addv(g.get('BeforeMove'),g.scale(g.get('FlightVelocity'),g.dt())))
    moved=g.distance(g.get('BeforeMove'),g.position())
    g.set('DistanceMoved',g.num('Add',g.get('DistanceMoved'),moved))
    speed=g.math('VSize',A=g.get('FlightVelocity'))
    g.set('MaxObservedSpeed',g.math('FMax',A=g.get('MaxObservedSpeed'),B=speed))
    hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(move,'SweepHitResult'))
    g.branch(g.out(hit,'bBlockingHit'))
    g.set('FlightVelocity',g.scale(g.get('FlightVelocity'),.17))
    normal=g.out(hit,'ImpactNormal')
    tangent=g.vector(g.num('Multiply',g.axis(normal,'Y'),-1.),g.axis(normal,'X'))
    safe=g.addv(g.scale(normal,360.),g.addv(g.scale(tangent,g.num('Multiply',g.get('StrafeSide'),380.)),g.vector(z=235.)))
    g.set('AvoidPoint',g.addv(g.position(),safe))
    g.set('AvoidUntil',g.num('Add',g.now(),.65))
    g.branch(g.compare('EqualEqual',g.get('Mode'),0))
    g.set('PatrolIndex',g.math('Percent_IntInt',A=g.math('Add_IntInt',A=g.get('PatrolIndex'),B=1),B=4))
    compile_bp(bp)


def animate(bp,spec):
    g=DroneGraph(bp,'AnimateMachine')
    velocity=g.get('FlightVelocity')
    forward=g.out(g.call('Engine.Actor.GetActorForwardVector'))
    right=g.out(g.call('Engine.Actor.GetActorRightVector'))
    to_target=g.flatten(g.subv(g.get('LastPoint'),g.position()))
    to_goal=g.flatten(g.subv(g.get('Goal'),g.position()))
    aim=g.select(to_target,to_goal,g.get('HasSight'))
    actual=g.out(g.call('Engine.Actor.K2_GetActorRotation'))
    desired=g.select(g.math('MakeRotFromX',X=aim),actual,g.num('Greater',g.math('VSize',A=aim),18.),'Rotator')
    yaw=g.math('RInterpTo',Current=actual,Target=desired,DeltaTime=g.dt(),InterpSpeed=7.5)
    g.do(g.call('Engine.Actor.K2_SetActorRotation',NewRotation=yaw,bTeleportPhysics=False))
    lateral=g.math('Dot_VectorVector',A=velocity,B=right)
    longitudinal=g.math('Dot_VectorVector',A=velocity,B=forward)
    roll=g.limit(g.num('Multiply',lateral,.021),-25.,25.)
    pitch=g.limit(g.num('Multiply',longitudinal,-.012),-16.,12.)
    g.turn('Chassis',g.rot(pitch,0.,roll))
    speed=g.math('VSize',A=velocity)
    effort=g.limit(g.num('Divide',speed,2060.),0.,1.)
    rpm=g.math('Lerp',A=1120.,B=2680.,Alpha=effort)
    angle=g.num('Add',g.get('RotorAngle'),g.num('Multiply',rpm,g.dt()))
    g.set('RotorAngle',g.num('Multiply',360.,g.math('Fraction',A=g.num('Divide',angle,360.))))
    for side,sign in (('L',1.),('R',-1.)):
        g.turn('Rotor'+side,g.rot(yaw=g.num('Multiply',g.get('RotorAngle'),sign)))
    pitch_audio=g.math('Lerp',A=.82,B=1.19,Alpha=effort)
    g.do(g.call('Engine.AudioComponent.SetPitchMultiplier',target=g.get('RotorAudio'),NewPitchMultiplier=pitch_audio))
    body=g.out(g.call('Engine.SceneComponent.K2_GetComponentToWorld',target=g.get('Chassis')))
    target=g.math('InverseTransformLocation',T=body,Location=g.get('LastPoint'))
    for side in ('L','R'):
        key='Gun'+side
        x,y,z=spec[key]['pivot']
        recoil='Recoil'+side
        g.set(recoil,g.interpolate(g.get(recoil),0.,18.))
        base=g.vector(x,y,z)
        local_aim=g.math('MakeRotFromX',X=g.subv(target,base))
        cannon_pitch=g.limit(g.num('Add',g.rpart(local_aim,'Pitch'),9.5),-52.,22.)
        cannon_yaw=g.limit(g.rpart(local_aim,'Yaw'),-19.,19.)
        kick=g.num('Multiply',g.get(recoil),.68)
        pitch=g.num('Add',g.select(cannon_pitch,0.,g.get('HasSight'),'Float'),kick)
        rotation=g.rot(pitch,g.select(cannon_yaw,0.,g.get('HasSight'),'Float'))
        shift=g.scale(g.math('GetForwardVector',InRot=rotation),g.num('Multiply',g.get(recoil),-1.))
        g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocationAndRotation',target=g.get(key),
             NewLocation=g.addv(base,shift),NewRotation=rotation,bSweep=False,bTeleport=False))
    compile_bp(bp)


def shots(bp,flash,streak,spark):
    g=DroneGraph(bp,'FireRound')
    side=g.compare('EqualEqual',g.math('Percent_IntInt',A=g.get('Shots'),B=2),0)
    origin=g.select(g.loc('MuzzleL'),g.loc('MuzzleR'),side)
    g.set('RoundOrigin',origin)
    target=g.position(g.get('Target'))
    _,clearance=g.trace(g.get('RoundOrigin'),target)
    sight=g.branch(g.math('EqualEqual_ObjectObject',A=g.out(clearance,'HitActor'),B=g.get('Target')))
    fresh=g.branch(g.compare('EqualEqual',g.get('BurstLeft'),BURST_ROUNDS))
    g.count('Bursts')
    recoil=g.set('RecoilL',g.select(10.,g.get('RecoilL'),side,'Float'))
    link(fresh.find_else_pin(),recoil.find_execute_pin())
    g.set('RecoilR',g.select(g.get('RecoilR'),10.,side,'Float'))
    aim=g.unit(g.subv(target,g.get('RoundOrigin')))
    g.set('RoundDir',g.math('RandomUnitVectorInConeInDegrees',ConeDir=aim,ConeHalfAngleInDegrees=1.70))
    end=g.addv(g.get('RoundOrigin'),g.scale(g.get('RoundDir'),g.get('FireRange')))
    hit,hit_parts=g.trace(g.get('RoundOrigin'),end)
    g.set('RoundEnd',g.select(g.out(hit_parts,'ImpactPoint'),end,hit))
    d=g.get('RoundDir')
    base=g.math('MakeRotFromX',X=d)
    roll=g.math('RandomFloatInRange',Min=0.,Max=360.)
    flash_rot=g.rot(g.rpart(base,'Pitch'),g.rpart(base,'Yaw'),roll)
    g.spawn(flash,g.get('RoundOrigin'),flash_rot,g.self())
    g.do(g.own('RoundSound'))
    g.do(g.own('RoundStreak'))
    g.count('Shots')
    g.set('BurstLeft',g.math('Subtract_IntInt',A=g.get('BurstLeft'),B=1))
    g.set('NextShot',g.math('FMax',A=g.num('Add',g.get('NextShot'),SHOT_INTERVAL),
                          B=g.num('Add',g.now(),.012)))
    recovery=g.math('RandomFloatInRange',Min=1.40,Max=2.15)
    g.set('NextBurst',g.num('Add',g.now(),recovery))
    g.branch(hit)
    target=g.get('Target')
    player_hit=g.branch(g.math('EqualEqual_ObjectObject',A=g.out(hit_parts,'HitActor'),B=target))
    g.count('Hits')
    g.do(g.call('Engine.GameplayStatics.ApplyDamage',DamagedActor=target,BaseDamage=g.get('ShotDamage'),
                DamageCauser=g.self()))
    g.cursor=player_hit.find_else_pin()
    g.branch(g.compare('EqualEqual',g.math('Percent_IntInt',A=g.get('Shots'),B=3),1))
    g.spawn(spark,g.get('RoundEnd'),g.math('MakeRotFromX',X=g.out(hit_parts,'ImpactNormal')),g.self())
    g.cursor=sight.find_else_pin()
    g.set('BurstLeft',0)
    g.set('NextBurst',g.math('FMax',A=g.get('NextBurst'),B=g.num('Add',g.now(),.22)))
    compile_bp(bp)


def round_helpers(bp,streak):
    g=DroneGraph(bp,'RoundSound')
    index=g.math('Percent_IntInt',A=g.get('Shots'),B=3)
    for i,sound in enumerate(SHOTS):
        route=g.branch(g.compare('EqualEqual',index,i))
        g.shot_sound(sound,g.get('RoundOrigin'))
        g.cursor=route.find_else_pin()
    compile_bp(bp)
    g=DroneGraph(bp,'RoundStreak')
    index=g.math('Percent_IntInt',A=g.get('Shots'),B=3)
    g.branch(g.compare('EqualEqual',index,0))
    distance=g.distance(g.get('RoundOrigin'),g.get('RoundEnd'))
    g.branch(g.num('Greater',distance,250.))
    start=g.addv(g.get('RoundOrigin'),g.scale(g.get('RoundDir'),95.))
    trace=g.spawn(streak,start,g.math('MakeRotFromX',X=g.get('RoundDir')),g.self())
    life=g.limit(g.num('Divide',g.num('Subtract',distance,200.),STREAK_SPEED),.020,.215)
    g.do(g.call('Engine.Actor.SetLifeSpan',target=trace,InLifespan=life))
    g.count('Streaks')
    compile_bp(bp)


def burst(bp):
    g=DroneGraph(bp,'Combat')
    visible=g.branch(g.get('HasSight'))
    valid=g.valid(g.get('Target'))
    g.branch(valid)
    direction=g.unit(g.flatten(g.subv(g.get('LastPoint'),g.position())))
    facing=g.out(g.call('Engine.Actor.GetActorForwardVector'))
    yaw_aligned=g.num('Greater',g.math('Dot_VectorVector',A=facing,B=direction),.89)
    in_range=g.num('Less',g.distance(g.loc('Sensor'),g.position(g.get('Target'))),g.get('FireRange'))
    ready=g.branch(g.both(yaw_aligned,in_range))
    active=g.branch(g.compare('Greater',g.get('BurstLeft'),0))
    g.branch(g.num('GreaterEqual',g.now(),g.get('NextShot')))
    g.do(g.own('FireRound'))
    g.cursor=active.find_else_pin()
    g.branch(g.num('GreaterEqual',g.now(),g.get('NextBurst')))
    g.set('BurstLeft',BURST_ROUNDS)
    g.set('NextShot',g.now())
    g.do(g.own('FireRound'))
    for route in (visible,ready):
        g.cursor=route.find_else_pin()
        g.set('BurstLeft',0)
    compile_bp(bp)


def lifecycle(bp):
    g=DroneGraph(bp,'MachineInit')
    g.set('Home',g.position())
    g.set('Goal',g.addv(g.position(),g.get('PointA')))
    g.set('StrafeSide',g.select(-1.,1.,g.num('Less',g.axis(g.get('PointA'),'X'),0.),'Float'))
    tags=g.e.add_get_member_variable_node('Tags','/Script/Engine.Actor')
    hostile=g.out(g.call('Engine.KismetSystemLibrary.MakeLiteralName',Value='CyborgHostile'))
    g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=pin(tags,'Tags',True),NewItem=hostile))
    compile_bp(bp)
    g=DroneGraph(bp,'MachineTick')
    live=g.branch(g.opposite(g.get('Destroyed')))
    cadence=g.branch(g.num('GreaterEqual',g.now(),g.get('PlanAt')))
    g.set('PlanAt',g.num('Add',g.now(),.18))
    g.do(g.own('Plan'))
    move=g.do(g.own('MoveMachine'))
    link(cadence.find_else_pin(),move.find_execute_pin())
    g.do(g.own('AnimateMachine'))
    g.do(g.own('Combat'))
    g.cursor=live.find_else_pin()
    fall=g.vector(z=g.num('Multiply',-980.,g.dt()))
    g.set('FlightVelocity',g.addv(g.get('FlightVelocity'),fall))
    drop=g.location(g.addv(g.position(),g.scale(g.get('FlightVelocity'),g.dt())))
    hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(drop,'SweepHitResult'))
    g.branch(g.out(hit,'bBlockingHit'))
    g.do(g.call('Engine.Actor.SetActorEnableCollision',bNewActorEnableCollision=False))
    g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=.15))
    compile_bp(bp)
    g=DroneGraph(bp)
    for event,method in (('ReceiveBeginPlay','MachineInit'),('ReceiveTick','MachineTick')):
        ev=g.override(event)
        ev.find_then_pin().break_pin_links()
        g.do(g.own(method))
    ev=g.override('ReceiveAnyDamage')
    ev.find_then_pin().break_pin_links()
    g.branch(g.opposite(g.get('Destroyed')))
    g.set('HullHealth',g.num('Subtract',g.get('HullHealth'),pin(ev,'Damage',True)))
    g.branch(g.num('LessEqual',g.get('HullHealth'),0.))
    g.set('Destroyed',True)
    g.do(g.call('Engine.AudioComponent.Stop',target=g.get('RotorAudio')))
    g.turn('Chassis',g.rot(-31.,0.,24.))
    g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=1.8))
    compile_bp(bp)
