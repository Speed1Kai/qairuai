"""Additive, modular city combat. All shipped logic is saved native Blueprint.
Preserves laboratory map, existing player movement/camera/interaction and elite AI.
"""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
S=os.path.abspath(unreal.Paths.project_saved_dir());R={'saved':False,'stages':[]}
def material(name,color,glow=False,translucent=False):
 path=FX+'/'+name;folder,n=path.rsplit('/',1)
 m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(n,folder,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m)
 if glow:m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 if translucent:m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE);m.set_editor_property('two_sided',True)
 c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1));assert M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if glow else unreal.MaterialProperty.MP_BASE_COLOR)
 if translucent:
  a=M.create_material_expression(m,unreal.MaterialExpressionScalarParameter);a.set_editor_property('parameter_name','Alpha');a.set_editor_property('default_value',.5);assert M.connect_material_property(a,'',unreal.MaterialProperty.MP_OPACITY)
 if not glow:
  for v,p in [(.8,unreal.MaterialProperty.MP_METALLIC),(.32,unreal.MaterialProperty.MP_ROUGHNESS)]:
   a=M.create_material_expression(m,unreal.MaterialExpressionConstant);a.set_editor_property('r',v);M.connect_material_property(a,'',p)
 M.recompile_material(m);save(m);return m
def event_hook(bp,event,fn,tag):
 e=G.get_graph_editor_by_name(bp,'EventGraph');n=e.find_event_node(event)
 if not n:n=B.add_event_override(bp,event,unreal.IntPoint(x=0,y=8500))
 if not any(n.get_name()==tag for n in e.list_all_nodes()):hook(bp,n.find_then_pin(),fn,tag)
try:
 assert not unreal.EditorLevelLibrary.get_game_world()
 A.make_directory(FX)
 backup=os.path.join(S,'Backups/CityCombat',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),backup);R['backup']=backup
 tools=unreal.AssetToolsHelpers.get_asset_tools();metal=material('M_WeaponSteel',(.045,.055,.065));cyan=material('M_ProtocolCyan',(1.5,9.,15.),True);red=material('M_EnemyTracer',(15.,1.8,.08),True);pulse=material('M_ProtocolPulse',(.18,2.5,4.),True,True)
 media={}
 for name in ('SM_Carbine','SM_Shotgun','SM_Plasma','S_Carbine','S_Shotgun','S_Plasma','S_ProtocolBlast'):
  path=FX+'/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask();kw=dict(filename=os.path.join(unreal.Paths.project_dir(),'SourceAssets/Combat',name+('.obj' if name.startswith('SM_') else '.wav')),destination_path=FX,destination_name=name,automated=True,save=True)
   if name.startswith('SM_'):
    opt=unreal.FbxImportUI()
    for k,v in dict(import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opt.set_editor_property(k,v)
    opt.static_mesh_import_data.set_editor_property('combine_meshes',True);kw['options']=opt
   for k,v in kw.items():task.set_editor_property(k,v)
   tools.import_asset_tasks([task])
  media[name]=A.load_asset(path);assert media[name],name
  if name.startswith('SM_'):media[name].set_material(0,metal);save(media[name])
 # Short-lived rendered tracers, rather than debug lines.
 for name,mat,radius in [('BP_EnemyTracer',red,.018),('BP_ProtocolTracer',cyan,.065)]:
  bp=asset(FX+'/'+name);c=add(bp,unreal.StaticMeshComponent,'Beam');c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cylinder'));c.set_material(0,mat);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
  compile_bp(bp);unreal.get_default_object(B.generated_class(bp)).set_editor_property('initial_life_span',.10 if name=='BP_EnemyTracer' else .22);save(bp)
 # The impact actor owns radial damage, sound, physics impulse and visual pulse.
 blast=asset(FX+'/BP_ProtocolBlast');c=add(blast,unreal.StaticMeshComponent,'Pulse');c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Sphere'));c.set_material(0,pulse);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
 force=add(blast,unreal.RadialForceComponent,'BlastForce','Pulse');force.set_editor_property('radius',850.);force.set_editor_property('impulse_strength',2200.);force.set_editor_property('impulse_vel_change',True);force.set_editor_property('ignore_owning_actor',True)
 light=add(blast,unreal.PointLightComponent,'Flash','Pulse');light.set_intensity(14000.);light.set_attenuation_radius(1000.);light.set_light_color(unreal.LinearColor(r=.1,g=.75,b=1,a=1));light.set_editor_property('cast_shadows',False)
 for n,t,d in [('BlastBirth','real','0'),('BlastDamage','real','900'),('BlastRadius','real','800')]:var(blast,n,t,d)
 var(blast,'Ignored',B.get_array_type(actorref()),'()');compile_bp(blast)
 g=Graph(blast);g.override('ReceiveBeginPlay');g.set('BlastBirth',g.now());owner=g.out(g.call('Engine.Actor.GetOwner'))
 g.do(g.call('Engine.KismetArrayLibrary.Array_Add',TargetArray=g.get('Ignored'),NewItem=owner))
 pos=g.out(g.call('Engine.Actor.K2_GetActorLocation'))
 g.do(g.call('Engine.GameplayStatics.ApplyRadialDamageWithFalloff',BaseDamage=g.get('BlastDamage'),MinimumDamage=140.,Origin=pos,DamageInnerRadius=250.,DamageOuterRadius=g.get('BlastRadius'),DamageFalloff=1.,IgnoreActors=g.get('Ignored'),DamageCauser=owner,InstigatedByController=g.pc(),DamagePreventionChannel='ECC_Visibility'))
 g.do(g.call('Engine.RadialForceComponent.FireImpulse',target=g.get('BlastForce')))
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=media['S_ProtocolBlast'].get_path_name(),Location=pos,VolumeMultiplier=.9))
 g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=.42))
 g.override('ReceiveTick');age=g.math('Subtract_DoubleDouble',A=g.now(),B=g.get('BlastBirth'));s=g.math('Add_DoubleDouble',A=.15,B=g.math('Multiply_DoubleDouble',A=age,B=38.))
 g.do(g.call('Engine.Actor.SetActorScale3D',NewScale3D=g.math('MakeVector',X=s,Y=s,Z=s)))
 compile_bp(blast);save(blast);R['stages'].append('weapons, tracers, radial blast')
 # Clone the existing working AI so its melee elite and laboratory are untouched.
 path=ROOT+'/BP_CityEnceladus';npc=A.load_asset(path) if A.does_asset_exist(path) else A.duplicate_asset('/Game/Enemies/Architect/BP_EnemyRobot',path)
 sk=A.load_asset(ROOT+'/SK_Enceladus');assert sk,'Enceladus skin preparation must complete first'
 cdo=unreal.get_default_object(B.generated_class(npc));mesh=cdo.get_component_by_class(unreal.SkeletalMeshComponent);mesh.set_skeletal_mesh_asset(sk);mesh.set_physics_asset(sk.physics_asset)
 for i,slot in enumerate(sk.materials):mesh.set_material(i,slot.material_interface)
 ev=G.get_graph_editor_by_name(npc,'EventGraph')
 for n in ev.list_all_nodes():
  title=str(n.get_node_title())
  if title=='SetSkeletalMeshAsset':val(pin(n,'NewMesh'),sk.get_path_name())
  if title=='SetPhysicsAsset':val(pin(n,'NewPhysicsAsset'),sk.physics_asset.get_path_name())
  if title=='SetMaterial' and pin(n,'Material').get_pin_value().find('M_CyberBoss_Gunmetal')>=0:
   idx=int(pin(n,'ElementIndex').get_pin_value());val(pin(n,'Material'),sk.materials[idx].material_interface.get_path_name())
 for n,t,d in [('CityShotInterval','real','.55'),('CityProjectileDamage','real','3'),('CitySpread','real','55'),('CityFireRange','real','1900'),('CityPreferredRange','real','900'),('CityNextShot','real','0'),('CityShotCount','int','0'),('CityGunKind','int','0'),('CityLastFireTime','real','-100')]:var(npc,n,t,d)
 var(npc,'CityTarget',actorref(),'None');compile_bp(npc)
 gun=add(npc,unreal.StaticMeshComponent,'CityWeapon','CapsuleComponent');gun.set_static_mesh(media['SM_Carbine']);gun.set_material(0,metal);gun.set_mobility(unreal.ComponentMobility.MOVABLE);gun.set_collision_profile_name('NoCollision');gun.set_editor_property('relative_location',V(35,22,25));gun.set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=0,roll=0))
 muzzle=add(npc,unreal.SceneComponent,'CityMuzzle','CapsuleComponent');muzzle.set_editor_property('relative_location',V(103,22,27));muzzle.set_mobility(unreal.ComponentMobility.MOVABLE)
 compile_bp(npc)
 g=Graph(npc,'City_Fire');g.branch(g.math('Not_PreBool',A=g.get('bIsDead')));g.branch(g.valid(g.get('CityTarget')));g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('CityNextShot')))
 g.set('CityNextShot',g.math('Add_DoubleDouble',A=g.now(),B=g.get('CityShotInterval')));g.set('CityLastFireTime',g.now());g.count('CityShotCount')
 source=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('CityMuzzle')))
 # Each trigger emits three independently scattered hitscan rounds/pellets.
 for j in range(3):
  target=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=g.get('CityTarget')))
  spread=g.get('CitySpread');neg=g.math('Multiply_DoubleDouble',A=spread,B=-1.)
  offset=g.math('MakeVector',X=g.math('RandomFloatInRange',Min=neg,Max=spread),Y=g.math('RandomFloatInRange',Min=neg,Max=spread),Z=g.math('RandomFloatInRange',Min=-24.,Max=35.))
  aim=g.math('Add_VectorVector',A=target,B=offset);delta=g.math('Subtract_VectorVector',A=aim,B=source);direction=g.math('Normal',A=delta,Tolerance=.001);end=g.math('Add_VectorVector',A=source,B=g.math('Multiply_VectorFloat',A=direction,B=4500.))
  trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=source,End=end,TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
  hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'))
  impact=g.math('SelectVector',A=g.out(hit,'ImpactPoint'),B=end,bPickA=g.out(trace))
  mid=g.math('Multiply_VectorFloat',A=g.math('Add_VectorVector',A=source,B=impact),B=.5)
  tracer=g.spawn(B.generated_class(A.load_asset(FX+'/BP_EnemyTracer')).get_path_name(),mid,g.math('MakeRotFromZ',Z=g.math('Subtract_VectorVector',A=impact,B=source)),g.self())
  length=g.math('Divide_DoubleDouble',A=g.math('VSize',A=g.math('Subtract_VectorVector',A=impact,B=source)),B=100.)
  g.do(g.call('Engine.Actor.SetActorScale3D',target=tracer,NewScale3D=g.math('MakeVector',X=.018,Y=.018,Z=length)))
  valid=g.branch(g.valid(g.out(hit,'HitActor')));skip=valid.find_else_pin()
  g.do(g.call('Engine.GameplayStatics.ApplyDamage',DamagedActor=g.out(hit,'HitActor'),BaseDamage=g.get('CityProjectileDamage'),EventInstigator=g.out(g.call('Engine.Pawn.GetController')),DamageCauser=g.self()))
  merge=g.do(g.call('Engine.KismetSystemLibrary.DelayUntilNextTick')) if False else None
  # Merge hit and miss before the next pellet using a no-op assignment.
  n=g.set('CityShotCount',g.get('CityShotCount'));link(skip,n.find_execute_pin())
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=media['S_Carbine'].get_path_name(),Location=source,VolumeMultiplier=.6))
 compile_bp(npc)
 g=Graph(npc,'City_CombatUpdate');g.branch(g.math('Not_PreBool',A=g.get('bIsDead')));g.set('CityTarget',g.player());g.branch(g.valid(g.get('CityTarget')))
 distance=g.out(g.call('Engine.Actor.GetDistanceTo',OtherActor=g.get('CityTarget')))
 g.branch(g.math('Less_DoubleDouble',A=distance,B=g.get('CityFireRange')))
 controller=g.out(g.call('Engine.Pawn.GetController'));g.branch(g.valid(controller))
 g.branch(g.out(g.call('Engine.Controller.LineOfSightTo',target=controller,Other=g.get('CityTarget'),ViewPoint=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('CityMuzzle'))),bAlternateChecks=False)))
 close=g.branch(g.math('Less_DoubleDouble',A=distance,B=g.get('CityPreferredRange')));far=close.find_else_pin();g.do(g.call('Engine.Controller.StopMovement',target=controller))
 merge=g.set('CityTarget',g.get('CityTarget'));link(far,merge.find_execute_pin())
 rot=g.call('Engine.KismetMathLibrary.BreakRotator',InRot=g.math('FindLookAtRotation',Start=g.out(g.call('Engine.Actor.K2_GetActorLocation')),Target=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=g.get('CityTarget')))))
 g.do(g.call('Engine.Actor.K2_SetActorRotation',NewRotation=g.math('MakeRotator',Pitch=0.,Yaw=g.out(rot,'Yaw'),Roll=0.),bTeleportPhysics=False));g.do(g.own('City_Fire'))
 compile_bp(npc);event_hook(npc,'ReceiveTick','City_CombatUpdate','CityCombatTick');compile_bp(npc);save(npc)
 R['roles']=[]
 for name,kind,interval,damage,spread,rng,preferred,hp in [('Carbine',0,.55,3.,55.,1900.,900.,320.),('Shotgun',1,1.15,8.,105.,1100.,500.,400.),('Plasma',2,2.0,10.,28.,2400.,1300.,260.)]:
  p=ROOT+'/BP_Enceladus_'+name;child=A.load_asset(p) if A.does_asset_exist(p) else A.duplicate_asset(path,p)
  compile_bp(child);cd=unreal.get_default_object(B.generated_class(child))
  for key,value in dict(CityGunKind=kind,CityShotInterval=interval,CityProjectileDamage=damage,CitySpread=spread,CityFireRange=rng,CityPreferredRange=preferred,Health=hp,MaxHealth=hp).items():cd.set_editor_property(key,value)
  c=next(c for h,c,n in components(child) if n=='CityWeapon');c.set_static_mesh(media['SM_'+name])
  # Set each role's sound on its own Fire graph.
  for n in G.get_graph_editor_by_name(child,'City_Fire').list_all_nodes():
   if str(n.get_node_title())=='PlaySoundAtLocation':val(pin(n,'Sound'),media['S_'+name].get_path_name())
  compile_bp(child);save(child);R['roles'].append(p)
 R['stages'].append('three ranged AI variants')
 # Player rail-cannon: camera trace, eight-second lockout, visible beam and blast.
 player=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 for n,t,d in [('ProtocolNextFire','real','0'),('ProtocolCooldown','real','8'),('ProtocolShots','int','0'),('ProtocolCooldownRemaining','real','0')]:var(player,n,t,d)
 compile_bp(player)
 g=Graph(player,'Protocol_Fire')
 g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')));g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))));g.branch(g.math('Not_PreBool',A=g.get('bAdminFlight')));g.branch(g.math('Greater_DoubleDouble',A=g.get('VisorIntegrity'),B=0.))
 ready=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('ProtocolNextFire')));waiting=ready.find_else_pin()
 g.set('ProtocolNextFire',g.math('Add_DoubleDouble',A=g.now(),B=g.get('ProtocolCooldown')));g.count('ProtocolShots')
 cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));source=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam));fw=g.math('GetForwardVector',InRot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=cam)));end=g.math('Add_VectorVector',A=source,B=g.math('Multiply_VectorFloat',A=fw,B=12000.))
 trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=source,End=end,TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'));hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'));impact=g.math('SelectVector',A=g.out(hit,'ImpactPoint'),B=end,bPickA=g.out(trace))
 # Offset outward from the hit surface so cover tests originate outside it.
 point=g.math('Add_VectorVector',A=impact,B=g.math('Multiply_VectorFloat',A=g.out(hit,'ImpactNormal'),B=12.))
 g.spawn(B.generated_class(blast).get_path_name(),point,owner=g.self())
 muzzle=g.math('Add_VectorVector',A=g.out(g.call('Engine.Actor.K2_GetActorLocation')),B=g.math('Add_VectorVector',A=g.math('Multiply_VectorFloat',A=fw,B=70.),B=g.math('MakeVector',X=0.,Y=0.,Z=35.)))
 mid=g.math('Multiply_VectorFloat',A=g.math('Add_VectorVector',A=muzzle,B=impact),B=.5);tracer=g.spawn(B.generated_class(A.load_asset(FX+'/BP_ProtocolTracer')).get_path_name(),mid,g.math('MakeRotFromZ',Z=g.math('Subtract_VectorVector',A=impact,B=muzzle)),g.self())
 g.do(g.call('Engine.Actor.SetActorScale3D',target=tracer,NewScale3D=g.math('MakeVector',X=.07,Y=.07,Z=g.math('Divide_DoubleDouble',A=g.math('VSize',A=g.math('Subtract_VectorVector',A=impact,B=muzzle)),B=100.))))
 shake=A.load_asset('/Game/ThirdPerson/Blueprints/CS_SentinelLanding')
 if shake:g.do(g.call('Engine.PlayerCameraManager.StartCameraShake',target=cam,ShakeClass=B.generated_class(shake).get_path_name(),Scale=1.2))
 g.print('ПРОТОКОЛ: ТЯЖЁЛЫЙ ИМПУЛЬС — ПЕРЕЗАРЯДКА 8 С',duration=2.)
 g.cursor=waiting;g.print('КОНДЕНСАТОР ПЕРЕЗАРЯЖАЕТСЯ',duration=.7)
 g=Graph(player,'Protocol_Update');g.set('ProtocolCooldownRemaining',g.math('FMax',A=g.math('Subtract_DoubleDouble',A=g.get('ProtocolNextFire'),B=g.now()),B=0.))
 compile_bp(player);ev=G.get_graph_editor_by_name(player,'EventGraph')
 if not any(n.get_name()=='ProtocolFireInput' for n in ev.list_all_nodes()):
  opts=[str(m) for m in ev.list_available_nodes([]) if str(m).endswith('|MouseEvents|Леваякнопкамыши')];assert len(opts)==1,opts
  key=ev.create_node_from_name(opts[0],unreal.Vector2D(x=0,y=9400),[]);key.set_editor_property('bConsumeInput',False);key.rename('ProtocolFireInput');call=ev.add_call_function_node(B.generated_class(player).get_path_name()+'.Protocol_Fire');link(pin(key,'Pressed',True),call.find_execute_pin())
 event_hook(player,'ReceiveTick','Protocol_Update','ProtocolCooldownTick');compile_bp(player);save(player);R['stages'].append('player cannon')
 # Dedicated reactive cover: only these newly placed objects break into physics chunks.
 cover=asset(FX+'/BP_ProtocolDestructible');root=add(cover,unreal.StaticMeshComponent,'Intact');root.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cube'));root.set_material(0,A.load_asset('/Game/Surface/Materials/M_RuinConcrete'));root.set_collision_profile_name('BlockAll');root.set_editor_property('relative_scale3d',V(2.4,.55,.95));root.set_mobility(unreal.ComponentMobility.MOVABLE)
 for n,t,d in [('CoverHealth','real','160'),('bBroken','bool','false')]:var(cover,n,t,d)
 for i in range(6):
  c=add(cover,unreal.StaticMeshComponent,'Shard'+str(i),'Intact');c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,A.load_asset('/Game/Surface/Materials/M_RuinConcrete'));c.set_editor_property('relative_scale3d',V(.31,.9,.46));c.set_editor_property('relative_location',V(-33+(i%3)*33,0,-24+(i//3)*48));c.set_visibility(False);c.set_collision_profile_name('NoCollision');c.set_mobility(unreal.ComponentMobility.MOVABLE)
 compile_bp(cover);g=Graph(cover);ev=g.override('ReceiveAnyDamage');g.branch(g.math('Not_PreBool',A=g.get('bBroken')));g.set('CoverHealth',g.math('Subtract_DoubleDouble',A=g.get('CoverHealth'),B=pin(ev,'Damage',True)));g.branch(g.math('LessEqual_DoubleDouble',A=g.get('CoverHealth'),B=0.));g.set('bBroken',True)
 g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('Intact'),bNewVisibility=False,bPropagateToChildren=False));g.do(g.call('Engine.PrimitiveComponent.SetCollisionEnabled',target=g.get('Intact'),NewType='NoCollision'))
 for i in range(6):
  c=g.get('Shard'+str(i));g.do(g.call('Engine.SceneComponent.SetVisibility',target=c,bNewVisibility=True));g.do(g.call('Engine.PrimitiveComponent.SetCollisionProfileName',target=c,InCollisionProfileName='PhysicsActor',bUpdateOverlaps=True));g.do(g.call('Engine.PrimitiveComponent.SetSimulatePhysics',target=c,bSimulate=True));g.do(g.call('Engine.PrimitiveComponent.AddImpulse',target=c,Impulse=g.math('MakeVector',X=(i%3-1)*280.,Y=180. if i%2 else -180.,Z=280.+i*45),bVelChange=True))
 g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=15.));compile_bp(cover);save(cover);R['stages'].append('destructible cover')
 import runpy
 runpy.run_path(os.path.join(os.path.dirname(__file__),'Configure_CombatCollision.py'))
 runpy.run_path(os.path.join(os.path.dirname(__file__),'Patch_CityCombat.py'))
 assert json.load(open(os.path.join(S,'citycombat_pursuit_patch.json'))).get('saved')
 R.update(saved=True,player_cooldown=8.,blast_damage=900.,blast_radius=800.)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
finally:json.dump(R,open(os.path.join(S,'citycombat_build.json'),'w'),ensure_ascii=False,indent=2)
if not R['saved']:raise RuntimeError('City combat build incomplete; see Saved/citycombat_build.json')

