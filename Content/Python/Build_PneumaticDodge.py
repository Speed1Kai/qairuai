"""Bounded Blueprint authoring: two helper actors, tap dodge / hold air lift.
Uses public editor graph APIs; no runtime Python dependency.
Preview unless Saved/pneumatic_mode.txt explicitly contains LIVE.
"""
import unreal,os,sys,json,shutil,datetime,time,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,Graph,add,components,compile_bp,save,pin,val,link
ROOT='/Game/Characters/AirJet'; PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
S=os.path.abspath(unreal.Paths.project_saved_dir())
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
class Flow(Graph):
    def __init__(self,bp,name=None):
        super().__init__(bp)
        if name:
            assert name not in map(str,B.list_graph_names(bp)),name
            self.e=G.create_and_edit_function_graph(bp,name);self.cursor=self.e.find_graph_entry_pin()
    def do(self,n):
        if n.find_execute_pin().is_valid():return super().do(n)
        return n
    def prop(self,name,cls,target,value=None):
        n=self.node(self.e.add_get_member_variable_node(name,'/Script/Engine.'+cls) if value is None else self.e.add_set_member_variable_node(name,'/Script/Engine.'+cls))
        val(n.find_self_pin(),target)
        if value is None:return pin(n,name,True)
        val(pin(n,name),value);return self.do(n)
    def cmget(self,n):return self.prop(n,'CharacterMovementComponent',self.get('CharacterMovement'))
    def cmset(self,n,v):return self.prop(n,'CharacterMovementComponent',self.get('CharacterMovement'),v)
    def velocity(self,v):return self.prop('Velocity','MovementComponent',self.get('CharacterMovement'),v)
    def own(self,n):return self.node(self.e.add_call_function_node(B.generated_class(self.bp).get_path_name()+'.'+n))
    def math(self,n,**kw):
        # Explicit scalar products avoid UE's promoted vector operator silently
        # selecting component-wise vector multiplication for literal scalars.
        if n=='Multiply_VectorFloat':
            v=self.call('Engine.KismetMathLibrary.BreakVector',InVec=kw['A'])
            return super().math('MakeVector',**{k:super(Flow,self).math('Multiply_DoubleDouble',A=self.out(v,k),B=kw['B']) for k in ('X','Y','Z')})
        return super().math(n,**kw)
    def now(self):return self.out(self.call('Engine.GameplayStatics.GetTimeSeconds'))
    def dt(self):return self.out(self.call('Engine.GameplayStatics.GetWorldDeltaSeconds'))
    def grounded(self):return self.out(self.call('Engine.NavMovementComponent.IsMovingOnGround',target=self.get('CharacterMovement')))
    def blocked(self):
        pc=self.out(self.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
        return self.math('BooleanOR',A=self.get('bAdminFlight'),B=self.out(self.call('Engine.Controller.IsMoveInputIgnored',target=pc)))
    def count(self,n):self.set(n,self.math('Add_IntInt',A=self.get(n),B=1))
    def fx(self,on):
        for side in ('Left','Right'):
            self.do(self.call('Engine.ActorComponent.'+('Activate' if on else 'Deactivate'),target=self.get('AirJet'+side),**({'bReset':True} if on else {})))
            self.do(self.call('Engine.SceneComponent.SetVisibility',target=self.get('AirJetPlume'+side),bNewVisibility=on))
        self.do(self.call('Engine.AudioComponent.'+('FadeIn' if on else 'FadeOut'),target=self.get('AirJetHiss'),**(dict(FadeInDuration=.025,FadeVolumeLevel=.6,StartTime=0.) if on else dict(FadeOutDuration=.1,FadeVolumeLevel=0.))))

R={'saved':False}
try:
    assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE first'
    mode=open(os.path.join(S,'pneumatic_mode.txt')).read().strip() if os.path.exists(os.path.join(S,'pneumatic_mode.txt')) else 'PREVIEW'
    R['mode']=mode
    backup=os.path.join(S,'Backups/PneumaticDodge',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
    shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),backup);R['backup']=backup
    path=PLAYER if mode=='LIVE' else ROOT+'/BP_PneumaticPreview_'+str(int(time.time()))
    bp=A.load_asset(path) if mode=='LIVE' else A.duplicate_asset(PLAYER,path);R['player']=path
    assert bp
    ev=G.get_graph_editor_by_name(bp,'EventGraph')
    assert 'Pneumatic_Update' not in map(str,B.list_graph_names(bp)),'Already installed'
    # Separate spherical helper actor, instanced exactly twice by the character.
    mp=ROOT+'/M_PneumaticOrb'
    mat=A.load_asset(mp) if A.does_asset_exist(mp) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_PneumaticOrb',ROOT,unreal.Material,unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(mat)
    for prop,cls,value in [(unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialExpressionConstant3Vector,unreal.LinearColor(r=.085,g=.105,b=.125,a=1)),(unreal.MaterialProperty.MP_METALLIC,unreal.MaterialExpressionConstant,1.),(unreal.MaterialProperty.MP_ROUGHNESS,unreal.MaterialExpressionConstant,.24)]:
        n=M.create_material_expression(mat,cls,0,0);n.set_editor_property('constant' if cls==unreal.MaterialExpressionConstant3Vector else 'r',value);M.connect_material_property(n,'',prop)
    M.recompile_material(mat);save(mat)
    op=ROOT+'/BP_PneumaticOrb'
    if A.does_asset_exist(op):orb=A.load_asset(op)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        orb=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_PneumaticOrb',ROOT,unreal.Blueprint,f)
    mesh=add(orb,unreal.StaticMeshComponent,'MetallicSphere')
    mesh.set_static_mesh(A.load_asset('/Engine/BasicShapes/Sphere'));mesh.set_material(0,mat);mesh.set_mobility(unreal.ComponentMobility.MOVABLE);mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    mesh.set_editor_property('relative_scale3d',V(.29,.29,.29));mesh.set_editor_property('cast_shadow',True)
    compile_bp(orb);save(orb)
    for sign,side in [(-1,'Left'),(1,'Right')]:
        c=add(bp,unreal.ChildActorComponent,'AssistOrb'+side,'CapsuleComponent');c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_child_actor_class(B.generated_class(orb));c.set_editor_property('relative_location',V(-75,sign*61,38))
        for h,nozzle,name in components(bp):
            if name=='AirJetNozzle'+side:
                nozzle.set_static_mesh(None);nozzle.set_visibility(False);nozzle.set_hidden_in_game(True);nozzle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    defs={'bPneumaticPending':('bool','false'),'bPneumaticDash':('bool','false'),'bPneumaticOrbsReady':('bool','false'),
          'PneumaticDashSpeed':('real','1600'),'PneumaticDashDuration':('real','.24'),'PneumaticDashCooldown':('real','.55'),
          'PneumaticDashUntil':('real','0'),'PneumaticNextDash':('real','0'),'PneumaticDashStarted':('real','0'),
          'PneumaticSavedSpeed':('real','180'),'PneumaticSavedFriction':('real','8'),'PneumaticSavedBrake':('real','2000'),
          'bPneumaticSavedOrient':('bool','true'),'PneumaticDashCount':('int','0')}
    for n,(typ,d) in defs.items():assert ev.add_member_variable(n,B.get_basic_type_by_name(typ),d),n
    for n in ('PneumaticDirection','PneumaticMoveAxis','PneumaticOrbWorldLeft','PneumaticOrbWorldRight'):
        assert ev.add_member_variable(n,B.get_struct_type(unreal.load_object(None,'/Script/CoreUObject.Vector')),'(X=0,Y=0,Z=0)'),n
    compile_bp(bp)
    # Stop restores captured movement settings and caps residual horizontal speed.
    g=Flow(bp,'Pneumatic_StopDash');g.branch(g.get('bPneumaticDash'));g.set('bPneumaticDash',False)
    for var,prop in [('PneumaticSavedSpeed','MaxWalkSpeed'),('PneumaticSavedFriction','GroundFriction'),('PneumaticSavedBrake','BrakingDecelerationWalking'),('bPneumaticSavedOrient','bOrientRotationToMovement')]:g.cmset(prop,g.get(var))
    vel=g.out(g.call('Engine.Actor.GetVelocity'));bv=g.call('Engine.KismetMathLibrary.BreakVector',InVec=vel)
    flat=g.math('MakeVector',X=g.out(bv,'X'),Y=g.out(bv,'Y'),Z=0.)
    capped=g.math('ClampVectorSize',A=flat,Min=0.,Max=g.get('PneumaticSavedSpeed'))
    g.velocity(g.math('Add_VectorVector',A=capped,B=g.math('MakeVector',X=0.,Y=0.,Z=g.out(bv,'Z'))));g.fx(False)
    compile_bp(bp)
    g=Flow(bp,'Pneumatic_CaptureDirection')
    pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
    def key(k):return g.out(g.call('Engine.PlayerController.IsInputKeyDown',target=pc,Key='(KeyName="'+k+'")'))
    def num(b):return g.math('SelectFloat',A=1.,B=0.,bPickA=b)
    raw=g.math('MakeVector',X=g.math('Subtract_DoubleDouble',A=num(key('D')),B=num(key('A'))),Y=g.math('Subtract_DoubleDouble',A=num(key('W')),B=num(key('S'))),Z=0.)
    axis=g.math('SelectVector',A=raw,B=g.get('PneumaticMoveAxis'),bPickA=g.math('Greater_DoubleDouble',A=g.math('VSizeSquared',A=raw),B=.01))
    a=g.call('Engine.KismetMathLibrary.BreakVector',InVec=axis)
    rot=g.call('Engine.KismetMathLibrary.BreakRotator',InRot=g.out(g.call('Engine.Controller.GetControlRotation',target=pc)))
    yaw=g.math('MakeRotator',Pitch=0.,Yaw=g.out(rot,'Yaw'),Roll=0.)
    fw=g.math('GetForwardVector',InRot=yaw);rt=g.math('GetRightVector',InRot=yaw)
    direction=g.math('Add_VectorVector',A=g.math('Multiply_VectorFloat',A=fw,B=g.out(a,'Y')),B=g.math('Multiply_VectorFloat',A=rt,B=g.out(a,'X')))
    chosen=g.math('SelectVector',A=direction,B=g.math('Multiply_VectorFloat',A=fw,B=-1.),bPickA=g.math('Greater_DoubleDouble',A=g.math('VSizeSquared',A=direction),B=.01))
    g.set('PneumaticDirection',g.math('Normal',A=chosen,Tolerance=.0001))
    compile_bp(bp)
    g=Flow(bp,'Pneumatic_StartDash')
    g.branch(g.grounded());g.branch(g.math('Not_PreBool',A=g.blocked()));g.branch(g.math('Not_PreBool',A=g.get('bAirJetActive')));g.branch(g.math('Not_PreBool',A=g.get('bPneumaticDash')))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('PneumaticNextDash')))
    for var,prop in [('PneumaticSavedSpeed','MaxWalkSpeed'),('PneumaticSavedFriction','GroundFriction'),('PneumaticSavedBrake','BrakingDecelerationWalking'),('bPneumaticSavedOrient','bOrientRotationToMovement')]:g.set(var,g.cmget(prop))
    g.set('bPneumaticDash',True);g.count('PneumaticDashCount');g.set('PneumaticDashStarted',g.now())
    g.set('PneumaticDashUntil',g.math('Add_DoubleDouble',A=g.now(),B=g.get('PneumaticDashDuration')));g.set('PneumaticNextDash',g.math('Add_DoubleDouble',A=g.now(),B=g.get('PneumaticDashCooldown')))
    g.cmset('GroundFriction',0.);g.cmset('BrakingDecelerationWalking',0.);g.cmset('bOrientRotationToMovement',False);g.cmset('MaxWalkSpeed',g.get('PneumaticDashSpeed'))
    g.velocity(g.math('Multiply_VectorFloat',A=g.get('PneumaticDirection'),B=g.get('PneumaticDashSpeed')));g.fx(True)
    compile_bp(bp)
    g=Flow(bp,'Pneumatic_InputPressed');g.do(g.own('Pneumatic_StopDash'));g.set('bPneumaticPending',True);g.set('AirJetHoldTime',0.);g.do(g.own('Pneumatic_CaptureDirection'));g.do(g.own('AirJet_Pressed'))
    g=Flow(bp,'Pneumatic_InputReleased')
    cond=g.math('BooleanAND',A=g.get('bPneumaticPending'),B=g.math('Less_DoubleDouble',A=g.get('AirJetHoldTime'),B=g.get('AirJetHoldThreshold')))
    br=g.branch(cond);otherwise=br.find_else_pin()
    for cursor,dash in [(g.cursor,True),(otherwise,False)]:
        g.cursor=cursor;g.set('bPneumaticPending',False);g.do(g.own('AirJet_Released'));g.do(g.call('Engine.Character.StopJumping'))
        if dash:g.do(g.own('Pneumatic_StartDash'))
    g=Flow(bp,'Pneumatic_InputCanceled');g.set('bPneumaticPending',False);g.do(g.own('AirJet_Released'));g.do(g.call('Engine.Character.StopJumping'));g.do(g.own('Pneumatic_StopDash'))
    compile_bp(bp)
    g=Flow(bp,'Pneumatic_Orbs')
    t=g.now();transform=g.out(g.call('Engine.Actor.GetTransform'))
    for sign,side in [(-1,'Left'),(1,'Right')]:
        phase=g.math('Add_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=t,B=2.1),B=sign*.7)
        bob=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=phase),B=5.)
        local=g.math('MakeVector',X=-75.,Y=sign*61.,Z=g.math('Add_DoubleDouble',A=bob,B=38.))
        target=g.math('TransformLocation',T=transform,Location=local)
        old=g.get('PneumaticOrbWorld'+side)
        far=g.math('Greater_DoubleDouble',A=g.math('VSizeSquared',A=g.math('Subtract_VectorVector',A=target,B=old)),B=1000000.)
        snap=g.math('BooleanOR',A=g.math('Not_PreBool',A=g.get('bPneumaticOrbsReady')),B=far)
        p=g.math('SelectVector',A=target,B=g.math('VInterpTo',Current=old,Target=target,DeltaTime=g.dt(),InterpSpeed=18.),bPickA=snap)
        g.set('PneumaticOrbWorld'+side,p)
        g.do(g.call('Engine.SceneComponent.K2_SetWorldLocation',target=g.get('AssistOrb'+side),NewLocation=g.get('PneumaticOrbWorld'+side),bSweep=False,bTeleport=True))
        air=g.math('Add_VectorVector',A=g.math('Multiply_VectorFloat',A=g.out(g.call('Engine.Actor.GetActorForwardVector')),B=-.45),B=g.math('MakeVector',X=0.,Y=0.,Z=-1.))
        exhaust=g.math('SelectVector',A=g.math('Multiply_VectorFloat',A=g.get('PneumaticDirection'),B=-1.),B=air,bPickA=g.get('bPneumaticDash'))
        rotation=g.math('MakeRotFromZ',Z=exhaust)
        for component in ('AirJet'+side,'AirJetPlume'+side):
            g.do(g.call('Engine.SceneComponent.K2_SetWorldLocation',target=g.get(component),NewLocation=g.get('PneumaticOrbWorld'+side),bSweep=False,bTeleport=True))
            g.do(g.call('Engine.SceneComponent.K2_SetWorldRotation',target=g.get(component),NewRotation=rotation,bSweep=False,bTeleport=True))
    g.set('bPneumaticOrbsReady',True)
    compile_bp(bp)
    g=Flow(bp,'Pneumatic_Update');g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')));g.do(g.own('Pneumatic_Orbs'))
    blocked=g.branch(g.blocked());normal=blocked.find_else_pin();g.do(g.own('Pneumatic_InputCanceled'))
    g.cursor=normal
    # A hold must launch from the ground only after the tap window has elapsed.
    hold=g.branch(g.math('BooleanAND',A=g.get('bPneumaticPending'),B=g.math('BooleanAND',A=g.get('bAirJetHeld'),B=g.math('GreaterEqual_DoubleDouble',A=g.get('AirJetHoldTime'),B=g.get('AirJetHoldThreshold')))))
    g.set('bPneumaticPending',False);g.do(g.call('Engine.Character.Jump'))
    # Both hold paths converge before the independent dash state update.
    dash=g.node(g.e.add_branch_node());val(pin(dash,'Condition'),g.get('bPneumaticDash'));link(g.cursor,dash.find_execute_pin());link(hold.find_else_pin(),dash.find_execute_pin());g.cursor=dash.find_then_pin()
    stopcond=g.math('BooleanOR',A=g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('PneumaticDashUntil')),B=g.math('Not_PreBool',A=g.grounded()))
    stop=g.branch(stopcond);running=stop.find_else_pin();g.do(g.own('Pneumatic_StopDash'));g.cursor=running
    g.cmset('MaxWalkSpeed',g.get('PneumaticDashSpeed'))
    taper=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=g.get('PneumaticDashUntil'),B=g.now()),B=.065),Min=.15,Max=1.)
    g.velocity(g.math('Multiply_VectorFloat',A=g.get('PneumaticDirection'),B=g.math('Multiply_DoubleDouble',A=g.get('PneumaticDashSpeed'),B=taper)))
    compile_bp(bp)
    # Exact event rewires: preserve all original movement, camera, interaction,
    # native touch-jump graphs, landing and the existing air-jet tick.
    jump=next(n for n in ev.list_all_nodes() if str(n.get_node_title())=='EnhancedInputAction IA_Jump')
    for event,fn in [('Started','Pneumatic_InputPressed'),('Completed','Pneumatic_InputReleased'),('Canceled','Pneumatic_InputCanceled')]:
        source=pin(jump,event,True);source.break_pin_links();n=ev.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+fn);n.rename('Pneumatic'+event);link(source,n.find_execute_pin())
    air=next(n for n in ev.list_all_nodes() if n.get_name()=='AirJetRuntimeTick')
    incoming=list(air.find_execute_pin().list_connected_pins());assert incoming
    air.find_execute_pin().break_pin_links();n=ev.add_call_function_node(B.generated_class(bp).get_path_name()+'.Pneumatic_Update');n.rename('PneumaticRuntimeTick')
    for source in incoming:link(source,n.find_execute_pin())
    link(n.find_then_pin(),air.find_execute_pin())
    # Cache the action's two-axis value without disturbing its current consumers.
    move=next(n for n in ev.list_all_nodes() if str(n.get_node_title())=='EnhancedInputAction IA_Move')
    for event,zero in [('Triggered',False),('Completed',True),('Canceled',True)]:
        source=pin(move,event,True);old=list(source.list_connected_pins());source.break_pin_links()
        setter=ev.add_set_member_variable_node('PneumaticMoveAxis');link(source,setter.find_execute_pin())
        if zero:val(pin(setter,'PneumaticMoveAxis'),'(X=0,Y=0,Z=0)')
        else:
            make=ev.add_call_function_node('/Script/Engine.KismetMathLibrary.MakeVector');link(pin(move,'ActionValue_X',True),pin(make,'X'));link(pin(move,'ActionValue_Y',True),pin(make,'Y'));val(pin(make,'Z'),0.);link(pin(make,'ReturnValue',True),pin(setter,'PneumaticMoveAxis'))
        for p in old:link(setter.find_then_pin(),p)
    compile_bp(bp);save(bp)
    R.update(saved=True,orbs=2,hold_threshold=.18,dash_speed=1600,dash_duration=.24,dash_cooldown=.55)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
finally:json.dump(R,open(os.path.join(S,'pneumatic_authoring.json'),'w'),indent=2)
if not R['saved']:raise RuntimeError('Pneumatic authoring incomplete; see Saved/pneumatic_authoring.json')
