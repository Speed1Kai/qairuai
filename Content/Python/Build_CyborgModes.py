"""Native Blueprint cyborg modes and rapid hitscan laser; preserve laboratory maps."""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
P='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter';MOD='/Game/Combat/CyborgModes';S=os.path.abspath(unreal.Paths.project_saved_dir());R={'saved':False}
def hook_event(bp,event,fn,tag):
 e=G.get_graph_editor_by_name(bp,'EventGraph');q=e.find_event_node(event)
 if not q:q=B.add_event_override(bp,event,unreal.IntPoint(x=0,y=11000))
 if not any(n.get_name()==tag for n in e.list_all_nodes()):hook(bp,q.find_then_pin(),fn,tag)
def arg(g,n,t):
 entry=g.e.find_graph_entry_pin().get_owning_node()
 if n in [str(p.get_pin_name()) for p in entry.list_all_pins()]:return pin(entry,n,True)
 return g.e.add_graph_input_parameter(n,B.get_basic_type_by_name(t) if isinstance(t,str) else t)
def pcset(g,n,value):
 q=g.e.add_set_member_variable_node(n,'/Script/Engine.PlayerController');val(q.find_self_pin(),g.pc());val(pin(q,n),value);g.do(q)
def choose(g,a,b,c):return g.math('SelectFloat',A=a,B=g.math('SelectFloat',A=b,B=c,bPickA=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=1)),bPickA=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=0))
def mat(name,col):
 p=MOD+'/'+name;m=A.load_asset(p) if A.does_asset_exist(p) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,MOD,unreal.Material,unreal.MaterialFactoryNew());M.delete_all_material_expressions(m);m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(r=col[0],g=col[1],b=col[2],a=1));M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(m);save(m);return m
try:
 assert not unreal.EditorLevelLibrary.get_game_world();A.make_directory(MOD)
 backup=os.path.join(S,'Backups/CyborgModes',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);R['backup']=backup
 for p in [P,'/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode',FX+'/BP_ProtocolBlast']:
  f=os.path.join(unreal.Paths.project_content_dir(),p.removeprefix('/Game/')+'.uasset');shutil.copy2(f,backup)
 for name in ('S_HunterLaser','S_ModeSelect'):
  p=MOD+'/'+name
  if not A.does_asset_exist(p):
   t=unreal.AssetImportTask();t.set_editor_property('filename',os.path.join(unreal.Paths.project_dir(),'SourceAssets/Combat',name+'.wav'));t.set_editor_property('destination_path',MOD);t.set_editor_property('destination_name',name);t.set_editor_property('automated',True);t.set_editor_property('save',True);unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
 beam=asset(MOD+'/BP_HunterLaserBeam');c=add(beam,unreal.StaticMeshComponent,'Beam');c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cylinder'));c.set_material(0,mat('M_HunterLaser',(1.2,10.,18.)));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);compile_bp(beam);unreal.get_default_object(B.generated_class(beam)).set_editor_property('initial_life_span',.075);save(beam)
 impact=asset(MOD+'/BP_HunterLaserImpact');c=add(impact,unreal.StaticMeshComponent,'Spark');c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Sphere'));c.set_material(0,A.load_asset(MOD+'/M_HunterLaser'));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('relative_scale3d',V(.065,.065,.065));c.set_editor_property('cast_shadow',False)
 l=add(impact,unreal.PointLightComponent,'Glow','Spark');l.set_intensity(350.);l.set_attenuation_radius(120.);l.set_light_color(unreal.LinearColor(r=.04,g=.65,b=1.,a=1.));l.set_editor_property('cast_shadows',False);compile_bp(impact);unreal.get_default_object(B.generated_class(impact)).set_editor_property('initial_life_span',.09);save(impact)
 bp=A.load_asset(P)
 for n,k,d in [('CyborgMode','int','1'),('bModeMenuOpen','bool','false'),('bLaserHeld','bool','false'),('LaserNextFire','real','0'),('LaserInterval','real','.09'),('LaserDamage','real','22'),('LaserShots','int','0'),('LaserHits','int','0'),('ModeSwitches','int','0'),('ModeTriggerPulls','int','0'),('ModeLockedAttempts','int','0'),('ModeInitialized','bool','false')]:var(bp,n,k,d)
 var(bp,'LaserLastHit',actorref(),'None');var(bp,'LaserLastPoint',B.get_struct_type(unreal.Vector.static_struct()),'(X=0,Y=0,Z=0)')
 compile_bp(bp)
 fp=add(bp,unreal.StaticMeshComponent,'FP_LaserWeapon','FirstPersonCamera');tp=add(bp,unreal.StaticMeshComponent,'TP_LaserWeapon','Mesh')
 for c in (fp,tp):c.set_static_mesh(A.load_asset(FX+'/SM_Plasma'));c.set_collision_profile_name('NoCollision');c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('cast_shadow',False);c.set_editor_property('relative_scale3d',V(.65,.65,.65))
 fp.set_editor_property('relative_location',V(28,18,-18));fp.set_editor_property('only_owner_see',True);tp.set_editor_property('relative_location',V(6,-3,2));compile_bp(bp)
 g=Graph(bp,'Modes_CloseMenu');g.branch(g.get('bModeMenuOpen'));g.set('bModeMenuOpen',False);g.set('bLaserHeld',False);pcset(g,'bShowMouseCursor',False);pcset(g,'bEnableClickEvents',False);g.do(g.call('Engine.Controller.ResetIgnoreLookInput',target=g.pc()));g.do(g.call('UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly',PlayerController=g.pc(),bFlushInput=True))
 compile_bp(bp)
 g=Graph(bp,'Modes_ToggleMenu');g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))));q=g.branch(g.get('bModeMenuOpen'));opening=q.find_else_pin();g.do(g.own('Modes_CloseMenu'));g.cursor=opening;g.set('bModeMenuOpen',True);g.set('bLaserHeld',False);pcset(g,'bShowMouseCursor',True);pcset(g,'bEnableClickEvents',True);g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=True));g.do(g.call('UMG.WidgetBlueprintLibrary.SetInputMode_GameAndUIEx',PlayerController=g.pc(),InMouseLockMode='DoNotLock',bHideCursorDuringCapture=False,bFlushInput=True))
 compile_bp(bp)
 g=Graph(bp,'Modes_UpdateSpeed');g.branch(g.math('Not_PreBool',A=g.get('bAdminFlight')));g.branch(g.math('Not_PreBool',A=g.get('bPneumaticDash')));g.branch(g.math('Not_PreBool',A=g.get('bAirJetActive')))
 walk=choose(g,1100.,700.,190.);run=choose(g,1500.,1000.,260.);g.set('RobotWalkSpeed',walk);g.set('RobotRunSpeed',run)
 shift=g.out(g.call('Engine.PlayerController.IsInputKeyDown',target=g.pc(),Key='(KeyName="LeftShift")'));speed=g.math('SelectFloat',A=run,B=walk,bPickA=shift)
 g.cmset('MaxWalkSpeed',speed);g.cmset('MaxAcceleration',choose(g,2400.,3200.,700.));g.cmset('BrakingDecelerationWalking',choose(g,2200.,2600.,1000.));g.cmset('GroundFriction',choose(g,8.,8.,6.));g.cmset('RotationRate',g.math('MakeRotator',Yaw=choose(g,450.,600.,240.),Pitch=0.,Roll=0.))
 g.set('PneumaticDashSpeed',choose(g,2000.,2300.,900.));g.set('PneumaticDashCooldown',choose(g,.45,.32,1.2))
 compile_bp(bp)
 g=Graph(bp,'Modes_ApplyVisuals');armed=g.math('NotEqual_IntInt',A=g.get('CyborgMode'),B=0)
 for name,first in [('FP_LaserWeapon',True),('TP_LaserWeapon',False)]:
  show=g.math('BooleanAND',A=armed,B=g.get('bFirstPerson') if first else g.math('Not_PreBool',A=g.get('bFirstPerson')));g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=show,bPropagateToChildren=True))
 compile_bp(bp)
 g=Graph(bp,'Laser_Fire');g.branch(g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=1));g.branch(g.math('Not_PreBool',A=g.get('bModeMenuOpen')));g.branch(g.math('Not_PreBool',A=g.get('bAdminFlight')));g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))));g.branch(g.math('Greater_DoubleDouble',A=g.get('VisorIntegrity'),B=0.));g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('LaserNextFire')))
 g.set('LaserNextFire',g.math('Add_DoubleDouble',A=g.now(),B=g.get('LaserInterval')));g.count('LaserShots')
 cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam));fw=g.math('GetForwardVector',InRot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=cam)));end=g.math('Add_VectorVector',A=eye,B=g.math('Multiply_VectorFloat',A=fw,B=12000.))
 t=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=eye,End=end,TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'));h=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(t,'OutHit'));aim=g.math('SelectVector',A=g.out(h,'ImpactPoint'),B=end,bPickA=g.out(t))
 fpos=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('FP_LaserWeapon')));tpos=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('TP_LaserWeapon')));muzzle=g.math('Add_VectorVector',A=g.math('SelectVector',A=fpos,B=tpos,bPickA=g.get('bFirstPerson')),B=g.math('Multiply_VectorFloat',A=fw,B=48.))
 trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=muzzle,End=g.math('Add_VectorVector',A=aim,B=g.math('Multiply_VectorFloat',A=fw,B=8.)),TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'));hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'));point=g.math('SelectVector',A=g.out(hit,'ImpactPoint'),B=aim,bPickA=g.out(trace));g.set('LaserLastPoint',point);g.set('LaserLastHit',g.out(hit,'HitActor'))
 mid=g.math('Multiply_VectorFloat',A=g.math('Add_VectorVector',A=muzzle,B=point),B=.5);ray=g.spawn(B.generated_class(beam).get_path_name(),mid,g.math('MakeRotFromZ',Z=g.math('Subtract_VectorVector',A=point,B=muzzle)),g.self());g.do(g.call('Engine.Actor.SetActorScale3D',target=ray,NewScale3D=g.math('MakeVector',X=.023,Y=.023,Z=g.math('Divide_DoubleDouble',A=g.math('VSize',A=g.math('Subtract_VectorVector',A=point,B=muzzle)),B=100.))))
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=MOD+'/S_HunterLaser',Location=muzzle,VolumeMultiplier=.4))
 g.branch(g.valid(g.out(hit,'HitActor')));g.count('LaserHits');g.do(g.call('Engine.GameplayStatics.ApplyPointDamage',DamagedActor=g.out(hit,'HitActor'),BaseDamage=g.get('LaserDamage'),HitFromDirection=fw,HitInfo=g.out(trace,'OutHit'),EventInstigator=g.pc(),DamageCauser=g.self()))
 g.spawn(B.generated_class(impact).get_path_name(),g.math('Add_VectorVector',A=point,B=g.math('Multiply_VectorFloat',A=g.out(hit,'ImpactNormal'),B=2.)),owner=g.self())
 compile_bp(bp)
 g=Graph(bp,'Modes_StartFire');g.branch(g.math('Not_PreBool',A=g.get('bModeMenuOpen')));g.count('ModeTriggerPulls');hunter=g.branch(g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=1));other=hunter.find_else_pin();g.set('bLaserHeld',True);g.do(g.own('Laser_Fire'));g.cursor=other;g.set('bLaserHeld',False);g.branch(g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=2));g.do(g.own('Protocol_Fire'))
 compile_bp(bp)
 g=Graph(bp,'Modes_StopFire');g.set('bLaserHeld',False)
 compile_bp(bp)
 g=Graph(bp,'Modes_Update');g.do(g.own('Modes_UpdateSpeed'));g.do(g.own('Modes_ApplyVisuals'));g.branch(g.get('bLaserHeld'));down=g.branch(g.out(g.call('Engine.PlayerController.IsInputKeyDown',target=g.pc(),Key='(KeyName="LeftMouseButton")')));up=down.find_else_pin();g.do(g.own('Laser_Fire'));g.cursor=up;g.set('bLaserHeld',False)
 compile_bp(bp)
 g=Graph(bp,'Modes_Init');g.set('ModeInitialized',True);g.set('bLaserHeld',False);g.set('bModeMenuOpen',False);g.do(g.own('Modes_UpdateSpeed'));g.do(g.own('Modes_ApplyVisuals'));g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get('TP_LaserWeapon'),Parent=g.get('Mesh'),SocketName='hand_r',LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
 compile_bp(bp)
 # Public selector: the reserved fourth protocol cannot be activated.
 g=Graph(bp,'Modes_Select');requested=arg(g,'RequestedMode','int');g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
 ok=g.branch(g.math('BooleanAND',A=g.math('GreaterEqual_IntInt',A=requested,B=0),B=g.math('LessEqual_IntInt',A=requested,B=2)));locked=ok.find_else_pin()
 g.do(g.own('Pneumatic_StopDash'));g.set('bLaserHeld',False);g.set('CyborgMode',requested);g.count('ModeSwitches');g.do(g.own('Modes_UpdateSpeed'));g.do(g.own('Modes_ApplyVisuals'));g.do(g.own('Modes_CloseMenu'));g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound=MOD+'/S_ModeSelect',VolumeMultiplier=.45))
 g.cursor=locked;g.count('ModeLockedAttempts');g.print('НЕЙРОКОНТРОЛЬ: МОДУЛЬ НЕДОСТУПЕН',color='(R=.8,G=.35,B=.18,A=1)',duration=1.)
 compile_bp(bp);ev=G.get_graph_editor_by_name(bp,'EventGraph');fire=next(n for n in ev.list_all_nodes() if n.get_name()=='ProtocolFireInput')
 for output,fn in [('Pressed','Modes_StartFire'),('Released','Modes_StopFire')]:
  pin(fire,output,True).break_pin_links();q=ev.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+fn);link(pin(fire,output,True),q.find_execute_pin())
 menus=json.load(open(os.path.join(S,'cyborg_modes_api.json')))['cast_menus']
 for key,mode in [('1',0),('2',1),('3',2),('4',3),('Tab',None)]:
  tag='CyborgModeKey_'+key
  if any(n.get_name()==tag for n in ev.list_all_nodes()):continue
  menu=next(m for m in menus if m.endswith('|KeyboardEvents|'+key));n=ev.create_node_from_name(menu,unreal.Vector2D(x=0,y=12000),[]);n.rename(tag);n.set_editor_property('bConsumeInput',False)
  call=ev.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+('Modes_ToggleMenu' if mode is None else 'Modes_Select'));link(pin(n,'Pressed',True),call.find_execute_pin())
  if mode is not None:val(pin(call,'RequestedMode'),mode)
 hook_event(bp,'ReceiveBeginPlay','Modes_Init','CyborgModesInit');hook_event(bp,'ReceiveTick','Modes_Update','CyborgModesTick');compile_bp(bp);save(bp)
 # Strengthen the existing atomic impulse; its eight-second recharge remains global.
 blast=A.load_asset(FX+'/BP_ProtocolBlast');cd=unreal.get_default_object(B.generated_class(blast));cd.set_editor_property('BlastDamage',1800.);cd.set_editor_property('BlastRadius',1100.)
 for h,c,n in components(blast):
  if isinstance(c,unreal.RadialForceComponent):c.set_editor_property('radius',1150.);c.set_editor_property('impulse_strength',3200.)
 save(blast)
 # Mark actual hostile Blueprint actors at BeginPlay; no distance-only fake detection.
 for path in ['/Game/Enemies/Architect/BP_EnemyRobot']+[ROOT+'/'+n for n in ('BP_CityEnceladus','BP_Enceladus_Carbine','BP_Enceladus_Shotgun','BP_Enceladus_Plasma')]:
  enemy=A.load_asset(path);g=Graph(enemy,'Combat_TagHostile');n=g.e.add_get_member_variable_node('Tags','/Script/Engine.Actor');g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=pin(n,'Tags',True),NewItem=g.out(g.call('Engine.KismetSystemLibrary.MakeLiteralName',Value='CyborgHostile'))));compile_bp(enemy);hook_event(enemy,'ReceiveBeginPlay','Combat_TagHostile','CombatTagHostile');compile_bp(enemy);save(enemy)
 R.update(saved=True,laser_interval=.09,laser_damage=22,atomic_damage=1800,atomic_radius=1100)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
json.dump(R,open(os.path.join(S,'cyborg_modes_gameplay.json'),'w'),indent=2)
assert R['saved'],R



