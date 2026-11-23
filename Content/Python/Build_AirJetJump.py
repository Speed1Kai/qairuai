"""Additive compressed-air long jump. Preview by default, LIVE explicitly selected.
Public Blueprint APIs, backed-up player package, no original event/function deletion.
Native runtime only; no Python callbacks are used by the shipped ability.
"""
import unreal,os,sys,json,math,wave,struct,random,shutil,datetime,time,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,Graph,add,components,compile_bp,save,pin,val,link
ROOT='/Game/Characters/AirJet';PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
project=os.path.abspath(unreal.Paths.project_dir());saved=os.path.abspath(unreal.Paths.project_saved_dir())
modefile=os.path.join(saved,'airjet_authoring_mode.txt')
mode=open(modefile).read().strip() if os.path.exists(modefile) else 'PREVIEW'
report={'saved':False,'mode':mode,'gameplay_tested':False}
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
class Flow(Graph):
    def __init__(self,bp,name=None):
        super().__init__(bp)
        if name:
            if name in map(str,B.list_graph_names(bp)):raise RuntimeError('Function already exists: '+name)
            self.e=G.create_and_edit_function_graph(bp,name);self.cursor=self.e.find_graph_entry_pin()
    def do(self,n):
        if any(str(p.get_pin_name())=='execute' for p in n.list_all_pins()):return super().do(n)
        return n
    def cmget(self,name):
        n=self.node(self.e.add_get_member_variable_node(name,'/Script/Engine.CharacterMovementComponent'));val(n.find_self_pin(),self.get('CharacterMovement'));return pin(n,name,True)
    def cmset(self,name,value):
        n=self.node(self.e.add_set_member_variable_node(name,'/Script/Engine.CharacterMovementComponent'));val(n.find_self_pin(),self.get('CharacterMovement'));val(pin(n,name),value);self.do(n)
    def own(self,name):return self.node(self.e.add_call_function_node(B.generated_class(self.bp).get_path_name()+'.'+name))
    def dt(self):return self.out(self.call('Engine.GameplayStatics.GetWorldDeltaSeconds'))
    def comment(self,text):
        self.e.add_comment_to_nodes(text,self.e.list_all_nodes(),45)
    def count(self,name):self.set(name,self.math('Add_IntInt',A=self.get(name),B=1))
    def stop(self):self.do(self.own('AirJet_Stop'))
try:
    backup=os.path.join(saved,'Backups','AirJetJump',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
    shutil.copy2(os.path.join(project,'Content/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),backup)
    report['backup']=backup
    path=PLAYER if mode=='LIVE' else ROOT+'/BP_AirJetPreview_'+str(int(time.time()))
    A.make_directory(ROOT)
    bp=A.load_asset(path) if mode=='LIVE' else A.duplicate_asset(PLAYER,path)
    if not bp:raise RuntimeError('Character unavailable')
    ev=G.get_graph_editor_by_name(bp,'EventGraph')
    if 'AirJet_Update' in map(str,B.list_graph_names(bp)):raise RuntimeError('Ability is already installed; use a targeted repair')
    variables={
      'bAirJetHeld':('bool','false'),'bAirJetActive':('bool','false'),'bAirJetNeedsRelease':('bool','false'),
      'AirJetCapacity':('real','4'),'AirJetRemaining':('real','4'),'AirJetHoldTime':('real','0'),
      'AirJetHoldThreshold':('real','.18'),'AirJetForwardSpeed':('real','900'),
      'AirJetLiftSpeed':('real','380'),'AirJetMaxRise':('real','950'),'AirJetStartZ':('real','0'),
      'AirJetSavedWalkSpeed':('real','180'),'AirJetSavedAirControl':('real','.35'),
      'AirJetSavedFallingBrake':('real','1500'),'AirJetSavedFallingFriction':('real','0'),
      'AirJetActivations':('int','0'),'AirJetExpirations':('int','0'),'AirJetLandings':('int','0'),
      'AirJetInputPresses':('int','0'),'AirJetInputReleases':('int','0')}
    for name,(kind,default) in variables.items():
        assert ev.add_member_variable(name,B.get_basic_type_by_name(kind),default),name
    for n in ('AirJetCapacity','AirJetForwardSpeed','AirJetLiftSpeed','AirJetMaxRise','AirJetHoldThreshold'):
        B.set_blueprint_variable_instance_editable(bp,n,True)
    compile_bp(bp)
    # Reuse the project's real translucent steam artwork. No protected particle
    # emitter/module fields are read or modified.
    particle_path=ROOT+'/P_AirJetSteam'
    steam=A.load_asset(particle_path) if A.does_asset_exist(particle_path) else A.duplicate_asset('/Game/CityDowntown/Effects/P_Steam_Lit2',particle_path)
    assert steam
    # Original, deterministically generated air hiss, looped and faded at runtime.
    source=os.path.join(project,'SourceAssets/AirJet');os.makedirs(source,exist_ok=True)
    wavpath=os.path.join(source,'AirJet_PressureLoop.wav')
    if not os.path.exists(wavpath):
        rng=random.Random(27102026);sr=22050;n=sr*2;values=[];lo=0.;slow=0.
        for i in range(n):
            white=rng.uniform(-1,1);lo=.64*lo+.36*white;slow=.975*slow+.025*white
            # A bright turbulent hiss without the tonal quality of a rocket engine.
            values.append((lo-.7*slow)*(.9+.1*math.sin(i/sr*math.tau*11)))
        fade=220
        for i in range(fade):
            a=i/fade;values[i]*=a;values[-1-i]*=a
        with wave.open(wavpath,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(b''.join(struct.pack('<h',int(max(-1,min(1,v))*.44*32767)) for v in values))
    sound_path=ROOT+'/AirJet_PressureLoop'
    if not A.does_asset_exist(sound_path):
        task=unreal.AssetImportTask()
        for k,v in {'filename':wavpath,'destination_path':ROOT,'destination_name':'AirJet_PressureLoop','automated':True,'save':True}.items():task.set_editor_property(k,v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound=A.load_asset(sound_path);assert sound;sound.set_editor_property('looping',True);save(sound)
    for side,name in [(-1,'Left'),(1,'Right')]:
        c=add(bp,unreal.ParticleSystemComponent,'AirJet'+name,'CapsuleComponent')
        c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_template(steam)
        c.set_editor_property('auto_activate',False)
        c.set_editor_property('relative_location',V(-29,side*18,32))
        c.set_editor_property('relative_rotation',unreal.Rotator(pitch=145,yaw=0,roll=0))
        c.set_editor_property('relative_scale3d',V(.22,.22,.4));c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('cast_shadow',False)
        nozzle=add(bp,unreal.StaticMeshComponent,'AirJetNozzle'+name,'CapsuleComponent')
        nozzle.set_mobility(unreal.ComponentMobility.MOVABLE);nozzle.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cylinder'))
        nozzle.set_material(0,A.load_asset('/Game/LabTutorial/FirstFloor/M_LabSteel'))
        nozzle.set_editor_property('relative_location',V(-25,side*18,36));nozzle.set_editor_property('relative_rotation',unreal.Rotator(pitch=145,yaw=0,roll=0));nozzle.set_editor_property('relative_scale3d',V(.12,.12,.20));nozzle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    audio=add(bp,unreal.AudioComponent,'AirJetHiss','CapsuleComponent');audio.set_mobility(unreal.ComponentMobility.MOVABLE)
    audio.set_sound(sound);audio.set_editor_property('auto_activate',False);audio.set_editor_property('volume_multiplier',.55)
    audio.set_editor_property('relative_location',V(-25,0,30))
    compile_bp(bp)
    # Stop is idempotent. Only a running jet restores its captured physics.
    g=Flow(bp,'AirJet_Stop');g.branch(g.get('bAirJetActive'));g.set('bAirJetActive',False)
    for var,prop in [('AirJetSavedWalkSpeed','MaxWalkSpeed'),('AirJetSavedAirControl','AirControl'),('AirJetSavedFallingBrake','BrakingDecelerationFalling'),('AirJetSavedFallingFriction','FallingLateralFriction')]:g.cmset(prop,g.get(var))
    for side in ('Left','Right'):g.do(g.call('Engine.ActorComponent.Deactivate',target=g.get('AirJet'+side)))
    g.do(g.call('Engine.AudioComponent.FadeOut',target=g.get('AirJetHiss'),FadeOutDuration=.12,FadeVolumeLevel=0.))
    g.comment('Release / empty / landing / disabled controls: stop thrust and spawning, fade hiss, restore captured walking/falling settings. Collision and movement mode are never disabled.')
    compile_bp(bp)
    g=Flow(bp,'AirJet_Pressed');g.set('bAirJetHeld',True);g.count('AirJetInputPresses')
    g=Flow(bp,'AirJet_Released');g.set('bAirJetHeld',False);g.set('bAirJetNeedsRelease',False);g.set('AirJetHoldTime',0.);g.count('AirJetInputReleases');g.stop()
    g=Flow(bp,'AirJet_Landed');g.stop();g.set('AirJetRemaining',g.get('AirJetCapacity'));g.set('AirJetHoldTime',0.);g.set('bAirJetNeedsRelease',g.get('bAirJetHeld'));g.count('AirJetLandings')
    compile_bp(bp)
    g=Flow(bp,'AirJet_Start');g.branch(g.math('Not_PreBool',A=g.get('bAirJetActive')))
    for var,prop in [('AirJetSavedWalkSpeed','MaxWalkSpeed'),('AirJetSavedAirControl','AirControl'),('AirJetSavedFallingBrake','BrakingDecelerationFalling'),('AirJetSavedFallingFriction','FallingLateralFriction')]:g.set(var,g.cmget(prop))
    pos=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.Actor.K2_GetActorLocation')))
    g.set('AirJetStartZ',g.out(pos,'Z'));g.set('bAirJetActive',True);g.count('AirJetActivations')
    g.cmset('AirControl',.25);g.cmset('BrakingDecelerationFalling',0.);g.cmset('FallingLateralFriction',.08)
    for side in ('Left','Right'):g.do(g.call('Engine.ActorComponent.Activate',target=g.get('AirJet'+side),bReset=True))
    g.do(g.call('Engine.AudioComponent.FadeIn',target=g.get('AirJetHiss'),FadeInDuration=.06,FadeVolumeLevel=.55,StartTime=0.))
    v=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.Actor.GetVelocity')))
    g.do(g.call('Engine.Character.LaunchCharacter',LaunchVelocity=g.math('MakeVector',X=g.out(v,'X'),Y=g.out(v,'Y'),Z=800.),bXYOverride=True,bZOverride=True))
    g.comment('Initial pneumatic kick. Horizontal momentum is preserved; subsequent ticks accelerate smoothly toward the aimed direction.')
    compile_bp(bp)
    g=Flow(bp,'AirJet_Update')
    g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
    pc=g.out(g.call('Engine.Pawn.GetController'))
    # Existing project uses one local player. This resolves the PlayerController
    # type without changing possession or the camera.
    pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
    blocked=g.math('BooleanOR',A=g.get('bAdminFlight'),B=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=pc)))
    split=g.branch(blocked);normal=split.find_else_pin();g.stop();g.set('AirJetHoldTime',0.);g.set('bAirJetNeedsRelease',g.get('bAirJetHeld'))
    g.cursor=normal
    held=g.branch(g.get('bAirJetHeld'));released=held.find_else_pin()
    g.branch(g.math('Not_PreBool',A=g.get('bAirJetNeedsRelease')))
    g.set('AirJetHoldTime',g.math('Add_DoubleDouble',A=g.get('AirJetHoldTime'),B=g.dt()))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.get('AirJetHoldTime'),B=g.get('AirJetHoldThreshold')))
    g.branch(g.out(g.call('Engine.NavMovementComponent.IsFalling',target=g.get('CharacterMovement'))))
    g.branch(g.math('Greater_DoubleDouble',A=g.get('AirJetRemaining'),B=0.))
    g.do(g.own('AirJet_Start'))
    # All velocity updates remain CharacterMovement launches, with the real
    # capsule sweeping against walls/ceilings; no teleport or noclip is used.
    g.cmset('MaxWalkSpeed',g.get('AirJetForwardSpeed'))
    rot=g.call('Engine.KismetMathLibrary.BreakRotator',InRot=g.out(g.call('Engine.Controller.GetControlRotation',target=pc)))
    flat=g.math('MakeRotator',Pitch=0.,Yaw=g.out(rot,'Yaw'),Roll=0.)
    forward=g.math('GetForwardVector',InRot=flat)
    desired=g.math('Multiply_VectorFloat',A=forward,B=g.get('AirJetForwardSpeed'))
    current=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.Actor.GetVelocity')))
    smooth=g.math('VInterpTo_Constant',Current=g.math('MakeVector',X=g.out(current,'X'),Y=g.out(current,'Y'),Z=0.),Target=desired,DeltaTime=g.dt(),InterpSpeed=1600.)
    planar=g.call('Engine.KismetMathLibrary.BreakVector',InVec=smooth)
    pos=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.Actor.K2_GetActorLocation')))
    ceiling=g.math('Add_DoubleDouble',A=g.get('AirJetStartZ'),B=g.get('AirJetMaxRise'))
    ascent=g.math('FClamp',Value=g.math('Multiply_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=ceiling,B=g.out(pos,'Z')),B=2.),Min=-100.,Max=g.get('AirJetLiftSpeed'))
    g.do(g.call('Engine.Character.LaunchCharacter',LaunchVelocity=g.math('MakeVector',X=g.out(planar,'X'),Y=g.out(planar,'Y'),Z=ascent),bXYOverride=True,bZOverride=True))
    # Total fuel per flight: releasing/repressing cannot reset the 4 second cap.
    g.set('AirJetRemaining',g.math('FMax',A=g.math('Subtract_DoubleDouble',A=g.get('AirJetRemaining'),B=g.dt()),B=0.))
    empty=g.branch(g.math('LessEqual_DoubleDouble',A=g.get('AirJetRemaining'),B=0.))
    g.count('AirJetExpirations');g.set('bAirJetNeedsRelease',True);g.stop()
    g.cursor=released;g.set('AirJetHoldTime',0.);g.set('bAirJetNeedsRelease',False);g.stop()
    g.comment('Hold jump >0.18s while falling. Four seconds of total thrust per landing; aim with mouse. Soft rise cap 9.5m, forward 9m/s. Input lock / F6 stops jet. Tap remains the original jump.')
    compile_bp(bp)
    # Append an independent Sequence output, preserving all existing consumers.
    def hook(source,fn,tag):
        old=list(source.list_connected_pins());options=[str(x) for x in ev.list_available_nodes([]) if str(x).split('|')[-1] in ('Sequence','Последовательность')]
        assert len(options)==1
        seq=ev.create_node_from_name(options[0],unreal.Vector2D(x=400,y=7000),[])
        source.break_pin_links();link(source,seq.find_execute_pin())
        for p in old:link(pin(seq,'then_0',True),p)
        n=ev.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+fn);n.rename(tag);n.set_node_pos(unreal.IntPoint(x=760,y=7000));link(pin(seq,'then_1',True),n.find_execute_pin())
    tick=ev.find_event_node('ReceiveTick');assert tick
    hook(tick.find_then_pin(),'AirJet_Update','AirJetRuntimeTick')
    jumps=[n for n in ev.list_all_nodes() if str(n.get_node_title())=='Jump']
    stops=[n for n in ev.list_all_nodes() if str(n.get_node_title())=='StopJumping']
    assert len(jumps)==1 and len(stops)==1
    hook(jumps[0].find_then_pin(),'AirJet_Pressed','AirJetJumpPressed')
    hook(stops[0].find_then_pin(),'AirJet_Released','AirJetJumpReleased')
    for n in ev.list_all_nodes():
        if str(n.get_node_title())=='EnhancedInputAction IA_Jump':hook(pin(n,'Canceled',True),'AirJet_Released','AirJetJumpCanceled')
    landed=ev.find_event_node('OnLanded')
    if not landed:
        options=[str(m) for m in ev.list_available_nodes([]) if str(m).endswith('|СобытиеOnLanded')]
        assert len(options)==1;landed=ev.create_node_from_name(options[0],unreal.Vector2D(x=0,y=7300),[])
    hook(landed.find_then_pin(),'AirJet_Landed','AirJetLandingRecharge')
    compile_bp(bp);save(bp)
    report.update(saved=True,player=path,capacity_seconds=4.,hold_threshold=.18,forward_cm_s=900,max_rise_cm=950,steam=particle_path,sound=sound_path,collision_preserved=True)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:json.dump(report,open(os.path.join(saved,'airjet_authoring_report.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Air jet authoring incomplete; see Saved/airjet_authoring_report.json')



