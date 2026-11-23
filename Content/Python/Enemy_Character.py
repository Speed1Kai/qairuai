from Enemy_Common import *
import math,wave,struct,random
M=unreal.MaterialEditingLibrary

def materials():
 mats={}
 for name,glow in [('M_CyberBoss_Gunmetal',False),('M_CyberBoss_Emissive',True)]:
  m=data(name,unreal.Material,unreal.MaterialFactoryNew());M.delete_all_material_expressions(m)
  def node(type,**kwargs):
   n=M.create_material_expression(m,type)
   for k,v in kwargs.items():n.set_editor_property(k,v)
   return n
  def color(rgb):return node(unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(*rgb,1.))
  if glow:
   m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
   amount=node(unreal.MaterialExpressionScalarParameter,parameter_name='Glow',default_value=35.)
   mul=node(unreal.MaterialExpressionMultiply);M.connect_material_expressions(color((1,.018,.003)),'',mul,'A');M.connect_material_expressions(amount,'',mul,'B');M.connect_material_property(mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
  else:
   M.connect_material_property(color((.16,.19,.23)),'',unreal.MaterialProperty.MP_BASE_COLOR)
   M.connect_material_property(color((.008,.011,.016)),'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
   for value,prop in [(.8,unreal.MaterialProperty.MP_METALLIC),(.32,unreal.MaterialProperty.MP_ROUGHNESS)]:
    n=node(unreal.MaterialExpressionConstant,r=value);M.connect_material_property(n,'',prop)
   texture=A.load_asset('/Game/Characters/Mannequins/Textures/Manny/T_Manny_01_BN')
   n=node(unreal.MaterialExpressionTextureSample,texture=texture,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL);M.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_NORMAL)
  for usage in (unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH,):M.set_material_usage(m,usage)
  M.recompile_material(m);save(m);mats[name]=m
 return mats

def sound():
 folder='S:/Final_Protocol/Content/Enemies/Architect/Source';os.makedirs(folder,exist_ok=True);assets={}
 for name,duration in [('S_EnemyAlert',1.25),('S_EnemyFootstep',.22),('S_EnemyImpact',.65)]:
  if A.does_asset_exist(ROOT+'/'+name):assets[name]=A.load_asset(ROOT+'/'+name);continue
  sr=22050;buf=bytearray();rng=random.Random(27);smooth=0
  for i in range(int(sr*duration)):
   t=i/sr;noise=rng.uniform(-1,1);smooth=smooth*.8+noise*.2
   if name=='S_EnemyAlert':
    env=min(1,t*12)*min(1,(duration-t)*4);v=env*(.13*math.sin(math.tau*(96*t+130*t*t))+.09*math.sin(math.tau*47*t)+.03*smooth)
   else:v=(.2*math.sin(math.tau*(65-22*t)*t)+.13*smooth+.07*noise)*math.exp(-t*(24 if name=='S_EnemyFootstep' else 8))
   buf.extend(struct.pack('<h',int(max(-.8,min(.8,v))*32767)))
  path=folder+'/'+name+'.wav'
  with wave.open(path,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(buf)
  task=unreal.AssetImportTask()
  for k,v in {'filename':path,'destination_path':ROOT,'destination_name':name,'automated':True,'save':True}.items():task.set_editor_property(k,v)
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);assets[name]=A.load_asset(ROOT+'/'+name)
 return assets

def animation():
 source='/Game/Characters/Mannequins/Anims/Unarmed'
 abp=A.load_asset(ROOT+'/ABP_EnemyRobot') or A.duplicate_asset(source+'/ABP_Unarmed',ROOT+'/ABP_EnemyRobot')
 # Keep Epic's validated triangulation and sample topology intact. Raw edits
 # to sample positions leave the runtime blend-space acceleration data stale.
 blend=A.load_asset(ROOT+'/BS_EnemyLocomotion_Manny') or A.duplicate_asset(source+'/BS_Idle_Walk_Run',ROOT+'/BS_EnemyLocomotion_Manny')
 save(blend)
 for name in B.list_graph_names(abp):
  e=G.get_graph_editor_by_name(abp,name)
  for n in e.list_all_nodes():
   if n.get_class().get_name()=='AnimGraphNode_BlendSpacePlayer':
    value=n.get_editor_property('node');value.set_editor_property('blend_space',blend);n.set_editor_property('node',value)
 for name,kind in [('AIState','int'),('bAlerting','bool'),('bSearching','bool'),('bChasing','bool')]:var(abp,name,kind,'0' if kind=='int' else 'false')
 compile_bp(abp);g=graph(abp);g.override('BlueprintUpdateAnimation')
 pawn=g.out(g.call('Engine.AnimInstance.TryGetPawnOwner'));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=pawn)))
 velocity=g.out(g.call('Engine.Actor.GetVelocity',target=pawn));g.set('Velocity',velocity)
 speed=g.math('VSizeXY',A=velocity);g.set('GroundSpeed',speed);g.set('ShouldMove',g.math('Greater_DoubleDouble',A=speed,B=3));g.set('IsFalling',False);g.set('Direction',0.)
 bb=g.bb(pawn);g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=bb)));state=g.bbget(bb,'MovementState','Enum');g.set('AIState',state)
 for name,index in [('bAlerting',1),('bSearching',2),('bChasing',3)]:g.set(name,g.math('EqualEqual_IntInt',A=state,B=index))
 compile_bp(abp);save(abp);return abp

def character(abp,mats,sounds):
 bp=asset('BP_EnemyRobot',unreal.Character);compile_bp(bp)
 sk=A.load_asset(ROOT+'/SK_EnemyRobot') or A.duplicate_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple',ROOT+'/SK_EnemyRobot')
 phys=A.load_asset(ROOT+'/PA_EnemyRobot') or A.duplicate_asset('/Game/Characters/Mannequins/Rigs/PA_Mannequin',ROOT+'/PA_EnemyRobot')
 for name,type,default in [('Health','real','320'),('MaxHealth','real','320'),('bIsDead','bool','false'),('StateIndex','int','0'),('LastStepTime','real','0'),('DeathStage','int','0')]:var(bp,name,type,default)
 if 'GlowMID' not in map(str,B.list_member_variable_names(bp)):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable('GlowMID',B.get_object_reference_type(unreal.MaterialInstanceDynamic))
 # Physical red nodes are attached to bones, so animation and ragdoll carry them.
 compile_bp(bp)
 sphere=A.load_asset('/Engine/BasicShapes/Sphere');cylinder=A.load_asset('/Engine/BasicShapes/Cylinder');cube=A.load_asset('/Engine/BasicShapes/Cube')
 specs=[('EyeL','head',(0,0,0),(.025,.025,.025),sphere),('EyeR','head',(0,0,0),(.025,.025,.025),sphere),('NeckReactor','neck_01',(0,0,0),(.13,.13,.07),sphere),('ChestReactor','spine_05',(0,0,0),(.11,.11,.11),sphere),('SpineReactor','spine_02',(0,-11,0),(.07,.06,.23),sphere),('ShoulderL','upperarm_l',(0,0,0),(.13,.13,.13),sphere),('ShoulderR','upperarm_r',(0,0,0),(.13,.13,.13),sphere),('WristL','hand_l',(0,0,0),(.065,.065,.065),sphere),('WristR','hand_r',(0,0,0),(.065,.065,.065),sphere)]
 glow_names=[]
 for name,bone,p,s,shape in specs:
  c=add(bp,unreal.StaticMeshComponent,name,parent='Mesh');c.set_static_mesh(shape);c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(s));c.set_material(0,mats['M_CyberBoss_Emissive']);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);glow_names.append(name)
 audio=add(bp,unreal.AudioComponent,'AlertAudio');audio.set_sound(sounds['S_EnemyAlert']);audio.set_editor_property('auto_activate',False);audio.set_editor_property('volume_multiplier',.75)
 compile_bp(bp);g=graph(bp);g.event('ReceiveBeginPlay');g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.08))
 g.do(g.call('Engine.SkeletalMeshComponent.SetSkeletalMeshAsset',target=g.get('Mesh'),NewMesh=sk.get_path_name()))
 g.do(g.call('Engine.SkinnedMeshComponent.SetPhysicsAsset',target=g.get('Mesh'),NewPhysicsAsset=phys.get_path_name(),bForceReInit=True))
 g.do(g.call('Engine.SkeletalMeshComponent.SetAnimInstanceClass',target=g.get('Mesh'),NewClass=B.generated_class(abp).get_path_name()))
 transform=g.math('MakeTransform',Location=g.math('MakeVector',X=0,Y=0,Z=-105),Rotation=g.math('MakeRotator',Roll=0,Pitch=0,Yaw=-90),Scale=g.math('MakeVector',X=1.15,Y=1.15,Z=1.15))
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeTransform',target=g.get('Mesh'),NewTransform=transform,bSweep=False,bTeleport=True))
 for i in range(2):g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('Mesh'),ElementIndex=i,Material=mats['M_CyberBoss_Gunmetal'].get_path_name()))
 for name,bone,p,s,shape in specs:
  g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(name),Parent=g.get('Mesh'),SocketName=bone,LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
  if name in ('EyeL','EyeR','ChestReactor'):
   origin=g.out(g.call('Engine.SceneComponent.GetSocketLocation',target=g.get('Mesh'),InSocketName=bone))
   forward=g.out(g.call('Engine.Actor.GetActorForwardVector'));right=g.out(g.call('Engine.Actor.GetActorRightVector'))
   desired=g.math('Add_VectorVector',A=origin,B=g.math('Multiply_VectorFloat',A=forward,B=10.4 if name.startswith('Eye') else 14.5))
   desired=g.math('Add_VectorVector',A=desired,B=g.math('MakeVector',X=0,Y=0,Z=10. if name.startswith('Eye') else -2.))
   if name.startswith('Eye'):desired=g.math('Add_VectorVector',A=desired,B=g.math('Multiply_VectorFloat',A=right,B=4.0 if name=='EyeL' else -4.0))
   local=g.math('InverseTransformLocation',T=g.out(g.call('Engine.SceneComponent.GetSocketTransform',target=g.get('Mesh'),InSocketName=bone,TransformSpace='RTS_World')),Location=desired)
   g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get(name),NewLocation=local,bSweep=False,bTeleport=True))
 mid=g.call('Engine.KismetMaterialLibrary.CreateDynamicMaterialInstance',Parent=mats['M_CyberBoss_Emissive'].get_path_name());g.do(mid);g.set('GlowMID',g.out(mid))
 for name in glow_names:g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get(name),ElementIndex=0,Material=g.get('GlowMID')))
 g.event('ReceiveTick')
 t=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))
 aggressive=g.math('BooleanOR',A=g.math('EqualEqual_IntInt',A=g.get('StateIndex'),B=1),B=g.math('EqualEqual_IntInt',A=g.get('StateIndex'),B=3))
 base=g.math('SelectFloat',A=95.,B=35.,bPickA=aggressive)
 pulse=g.math('Add_DoubleDouble',A=base,B=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=g.math('Multiply_DoubleDouble',A=t,B=9.)),B=10.))
 alive=g.branch(g.math('Not_PreBool',A=g.get('bIsDead')))
 g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('GlowMID'),ParameterName='Glow',Value=pulse))
 speed=g.math('VSizeXY',A=g.out(g.call('Engine.Actor.GetVelocity')));g.branch(g.math('Greater_DoubleDouble',A=speed,B=20))
 interval=g.math('SelectFloat',A=.34,B=.72,bPickA=aggressive);g.branch(g.math('Greater_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=t,B=g.get('LastStepTime')),B=interval));g.set('LastStepTime',t)
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=sounds['S_EnemyFootstep'].get_path_name(),Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=.30))
 event=g.override('ReceiveAnyDamage');g.branch(g.math('BooleanAND',A=g.math('Not_PreBool',A=g.get('bIsDead')),B=g.math('Greater_DoubleDouble',A=pin(event,'Damage',True),B=0)))
 g.set('Health',g.math('FMax',A=0,B=g.math('Subtract_DoubleDouble',A=g.get('Health'),B=pin(event,'Damage',True))))
 condition=g.branch(g.math('LessEqual_DoubleDouble',A=g.get('Health'),B=0));hit=pin(condition,'else',True)
 g.set('bIsDead',True);g.set('StateIndex',5);g.set('DeathStage',1)
 g.do(g.call('Engine.CharacterMovementComponent.DisableMovement',target=g.get('CharacterMovement')))
 g.set('DeathStage',2)
 g.do(g.call('Engine.PrimitiveComponent.SetCollisionEnabled',target=g.get('CapsuleComponent'),NewType='NoCollision'))
 g.do(g.call('Engine.PrimitiveComponent.SetCollisionProfileName',target=g.get('Mesh'),InCollisionProfileName='Ragdoll',bUpdateOverlaps=True))
 g.set('DeathStage',3)
 g.do(g.call('Engine.SkeletalMeshComponent.SetAllBodiesSimulatePhysics',target=g.get('Mesh'),bNewSimulate=True));g.do(g.call('Engine.SkeletalMeshComponent.SetAllBodiesPhysicsBlendWeight',target=g.get('Mesh'),PhysicsBlendWeight=1.,bSkipCustomPhysicsType=False));g.do(g.call('Engine.PrimitiveComponent.SetSimulatePhysics',target=g.get('Mesh'),bSimulate=True));g.set('DeathStage',4)
 g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('GlowMID'),ParameterName='Glow',Value=.25))
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=sounds['S_EnemyImpact'].get_path_name(),Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=.7));g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=35.))
 controller=g.out(g.call('Engine.Pawn.GetController'));bb=g.bb(controller);g.bbset(bb,'IsDead',True,'Bool');g.set('DeathStage',5)
 brain=g.out(g.call('Engine.Actor.GetComponentByClass',target=controller,ComponentClass='/Script/AIModule.BehaviorTreeComponent'))
 g.do(g.call('AIModule.BrainComponent.StopLogic',target=brain,Reason='Elite robot destroyed'));g.do(g.call('Engine.Controller.StopMovement',target=controller));g.set('DeathStage',6)
 g.cursor=hit;g.set('StateIndex',4)
 anim=g.out(g.call('Engine.SkeletalMeshComponent.GetAnimInstance',target=g.get('Mesh')))
 g.do(g.call('Engine.AnimInstance.PlaySlotAnimationAsDynamicMontage',target=anim,Asset='/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Hvy_01.MM_HitReact_Front_Hvy_01',SlotNodeName='DefaultSlot',BlendInTime=.08,BlendOutTime=.15,InPlayRate=1.,LoopCount=1))
 g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('CharacterMovement'),PropertyName='MaxWalkSpeed',Value=0.))
 g.do(g.call('Engine.KismetSystemLibrary.RetriggerableDelay',Duration=.45));g.branch(g.math('Not_PreBool',A=g.get('bIsDead')))
 board=g.bb(g.out(g.call('Engine.Pawn.GetController')));speed=g.math('SelectFloat',A=550.,B=180.,bPickA=g.math('EqualEqual_IntInt',A=g.bbget(board,'MovementState','Enum'),B=3))
 g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('CharacterMovement'),PropertyName='MaxWalkSpeed',Value=speed))
 compile_bp(bp)
 # Configure inherited native components after graph compilation.
 cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED);cdo.set_editor_property('use_controller_rotation_yaw',False)
 cap=cdo.get_component_by_class(unreal.CapsuleComponent);cap.set_capsule_size(44.,105.)
 sk=A.load_asset(ROOT+'/SK_EnemyRobot') or A.duplicate_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple',ROOT+'/SK_EnemyRobot')
 phys=A.load_asset(ROOT+'/PA_EnemyRobot') or A.duplicate_asset('/Game/Characters/Mannequins/Rigs/PA_Mannequin',ROOT+'/PA_EnemyRobot');sk.set_editor_property('physics_asset',phys);save(sk)
 mesh=cdo.get_component_by_class(unreal.SkeletalMeshComponent);mesh.set_skeletal_mesh_asset(sk);mesh.set_editor_property('relative_location',V((0,0,-105)));mesh.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90));mesh.set_editor_property('relative_scale3d',V((1.15,1.15,1.15)));mesh.set_anim_instance_class(B.generated_class(abp))
 for i in range(2):mesh.set_material(i,mats['M_CyberBoss_Gunmetal'])
 move=cdo.get_component_by_class(unreal.CharacterMovementComponent);move.set_editor_property('max_walk_speed',180.);move.set_editor_property('orient_rotation_to_movement',True);move.set_editor_property('rotation_rate',unreal.Rotator(yaw=240.));move.set_editor_property('max_acceleration',1200.);move.set_editor_property('braking_deceleration_walking',1200.)
 save(bp);return bp
