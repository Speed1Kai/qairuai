"""Use the saved elite guard's visuals on the playable character, with player locomotion."""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,add,components,compile_bp,save,Graph,pin,val,link
ROOT='/Game/Characters/GuardPlayer';ENEMY='/Game/Enemies/Architect/'
content=os.path.abspath(unreal.Paths.project_content_dir());saved=os.path.abspath(unreal.Paths.project_saved_dir())
stage=os.path.join(saved,'GuardPlayerStaged');os.makedirs(stage,exist_ok=True)
backup=os.path.join(saved,'Backups','GuardPlayer',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
r={'saved':False,'installed':False,'files':[],'backup':backup,'source_mesh':ENEMY+'SK_EnemyRobot','gameplay_tested':False}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def external(self,name,cls,target):
  q=self.node(self.e.add_get_member_variable_node(name,cls));val(q.find_self_pin(),target);return pin(q,name,True)
def stage_asset(asset):
 package=asset.get_path_name().split('.')[0];rel=package.replace('/Game/','')+'.uasset';src=os.path.join(content,rel);dst=os.path.join(stage,rel);os.makedirs(os.path.dirname(dst),exist_ok=True)
 if os.path.isfile(src):
  bk=os.path.join(backup,rel);os.makedirs(os.path.dirname(bk),exist_ok=True);shutil.copy2(src,bk)
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="'+package+'" FILE="'+dst.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(dst):raise RuntimeError('Save failed '+package)
 r['files'].append({'source':dst,'destination':src})
def copy(src,name):
 p=ROOT+'/'+name;asset=A.load_asset(p) if A.does_asset_exist(p) else A.duplicate_asset(src,p)
 if not asset:raise RuntimeError('Missing source '+src)
 return asset
def member(bp,name,typ,default):
 if name not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,typ,str(default))
 B.set_blueprint_variable_instance_editable(bp,name,True)
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial');world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();A.make_directory(ROOT)
 mesh=copy(ENEMY+'SK_EnemyRobot','SK_PlayerGuard');metal=copy(ENEMY+'M_CyberBoss_Gunmetal','M_PlayerGuardMetal');glow=copy(ENEMY+'M_CyberBoss_Emissive','M_PlayerGuardEmissive')
 slots=mesh.get_editor_property('materials')
 for slot in slots:slot.set_editor_property('material_interface',metal)
 mesh.set_editor_property('materials',slots);save(mesh);save(metal);save(glow)
 # The NPC's AI animation graph forces IsFalling=false. Keep a player graph so
 # jumping/crouching continue to work, with slower, heavier locomotion playback.
 abp=copy('/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed','ABP_PlayerGuard')
 blend=copy(ENEMY+'BS_EnemyLocomotion_Manny','BS_PlayerGuard');save(blend)
 changed=0
 for graph in B.list_graph_names(abp):
  for node in G.get_graph_editor_by_name(abp,graph).list_all_nodes():
   if node.get_class().get_name()=='AnimGraphNode_BlendSpacePlayer':
    data=node.get_editor_property('node');data.set_editor_property('blend_space',blend);data.set_editor_property('play_rate',.8);node.set_editor_property('node',data);changed+=1
 if not changed:raise RuntimeError('No locomotion player found')
 compile_bp(abp);save(abp)
 playerbp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');pm=next(c for h,c,n in components(playerbp) if n=='Mesh');pm.set_skeletal_mesh_asset(mesh);pm.set_anim_instance_class(B.generated_class(abp));pm.set_editor_property('relative_scale3d',V((1.15,1.15,1.15)));pm.set_editor_property('relative_location',V((0,0,-105)))
 for i in range(pm.get_num_materials()):pm.set_material(i,metal)
 movement=next(c for h,c,n in components(playerbp) if isinstance(c,unreal.CharacterMovementComponent))
 for prop,value in [('max_walk_speed',180.),('max_acceleration',450.),('braking_deceleration_walking',650.),('jump_z_velocity',540.)]:movement.set_editor_property(prop,value)
 movement.set_editor_property('rotation_rate',unreal.Rotator(yaw=240));movement.set_editor_property('orient_rotation_to_movement',True)
 capsule=next(c for h,c,n in components(playerbp) if isinstance(c,unreal.CapsuleComponent));capsule.set_capsule_half_height(105.);capsule.set_capsule_radius(44.)
 compile_bp(playerbp);cdo=unreal.get_default_object(B.generated_class(playerbp))
 for name,value in [('RobotWalkSpeed',180.),('RobotRunSpeed',420.),('RobotJumpVelocity',540.),('RobotTurnRate',240.)]:cdo.set_editor_property(name,value)
 stage_asset(playerbp)
 body=A.load_asset('/Game/LabTutorial/Basement/BP_CyborgBodyLight');next(c for h,c,n in components(body) if n=='BodyGlowShell').set_skeletal_mesh_asset(mesh);compile_bp(body);stage_asset(body)
 # Only the guard's appearance is copied: no perception, behavior tree or AI controller.
 path=ROOT+'/BP_PlayerGuardVisual';visual=A.load_asset(path)
 if not visual:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);visual=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_PlayerGuardVisual',ROOT,unreal.Blueprint,f)
 compile_bp(visual);add(visual,unreal.SceneComponent,'GuardVisualRoot')
 refs=json.load(open(os.path.join(saved,'protocol_robot_rig.json')))
 sphere=A.load_asset('/Engine/BasicShapes/Sphere')
 anchors=[('EyeL','head',(4,11,172),(.025,.025,.025)),('EyeR','head',(-4,11,172),(.025,.025,.025)),('NeckReactor','neck_01',(0,2,155),(.13,.13,.07)),('ChestReactor','spine_05',(0,15,139),(.11,.11,.11)),('SpineReactor','spine_02',(0,-11,114),(.07,.06,.23)),('ShoulderL','upperarm_l',(23,4,145),(.13,.13,.13)),('ShoulderR','upperarm_r',(-23,4,145),(.13,.13,.13)),('WristL','hand_l',tuple(refs['hand_l']['p']),(.065,.065,.065)),('WristR','hand_r',tuple(refs['hand_r']['p']),(.065,.065,.065))]
 for name,bone,p,scale in anchors:
  c=add(visual,unreal.StaticMeshComponent,name,'GuardVisualRoot');c.set_static_mesh(sphere);c.set_material(0,glow);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_visibility(False)
  ref=refs[bone];t=unreal.Transform(location=V(ref['p']),rotation=unreal.Rotator(pitch=ref['r'][0],yaw=ref['r'][1],roll=ref['r'][2]),scale=V((1,1,1)));c.set_editor_property('relative_location',unreal.MathLibrary.inverse_transform_location(t,V(p)));c.set_editor_property('relative_scale3d',V(scale))
 audio=add(visual,unreal.AudioComponent,'MechanicalFootstep','GuardVisualRoot');audio.set_sound(A.load_asset(ENEMY+'S_EnemyFootstep'));audio.set_editor_property('auto_activate',False);audio.set_editor_property('volume_multiplier',.45)
 settings=audio.get_editor_property('attenuation_overrides');settings.set_editor_property('spatialize',True);settings.set_editor_property('attenuation_shape_extents',V((80,0,0)));settings.set_editor_property('falloff_distance',650.);audio.set_editor_property('attenuation_overrides',settings);audio.set_editor_property('override_attenuation',True)
 for name,typ,default in [('TargetMesh',B.get_object_reference_type(unreal.SkeletalMeshComponent),'None'),('Player',B.get_object_reference_type(unreal.Character),'None'),('bIntroCostume',B.get_basic_type_by_name('bool'),'false'),('GlowMID',B.get_object_reference_type(unreal.MaterialInstanceDynamic),'None'),('GlowStrength',B.get_basic_type_by_name('double'),'35'),('LastStepTime',B.get_basic_type_by_name('double'),'0'),('WalkSpeed',B.get_basic_type_by_name('double'),'180'),('RunSpeed',B.get_basic_type_by_name('double'),'420'),('bReady',B.get_basic_type_by_name('bool'),'false')]:member(visual,name,typ,default)
 compile_bp(visual);g=Flow(visual);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay');split=g.branch(g.get('bIntroCostume'));intro=split.find_then_pin();g.cursor=split.find_else_pin();g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=10.5));player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0));g.set('Player',player);g.set('TargetMesh',g.external('Mesh','/Script/Engine.Character',player))
 movement_ref=g.external('CharacterMovement','/Script/Engine.Character',g.get('Player'))
 for prop,param in [('RobotWalkSpeed','WalkSpeed'),('RobotRunSpeed','RunSpeed')]:g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('Player'),PropertyName=prop,Value=g.get(param)))
 g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=movement_ref,PropertyName='MaxWalkSpeed',Value=g.get('WalkSpeed')))
 first=g.call('Engine.KismetMaterialLibrary.CreateDynamicMaterialInstance',Parent=glow.get_path_name());g.do(first);link(intro,first.find_execute_pin());g.set('GlowMID',g.out(first))
 for name,bone,p,scale in anchors:
  target=g.get(name);g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=target,Parent=g.get('TargetMesh'),SocketName=bone,LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False));g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=target,ElementIndex=0,Material=g.get('GlowMID')));g.do(g.call('Engine.SceneComponent.SetVisibility',target=target,bNewVisibility=True,bPropagateToChildren=False))
 g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get('MechanicalFootstep'),Parent=g.get('TargetMesh'),SocketName='root',LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False));g.set('bReady',True);g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.05));g.branch(g.get('bIntroCostume'));g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=10.))
 g.event('ReceiveTick');g.branch(g.get('bReady'));time=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'));pulse=g.math('Add_DoubleDouble',A=g.get('GlowStrength'),B=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=g.math('Multiply_DoubleDouble',A=time,B=6.283185307)),B=5.))
 g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('GlowMID'),ParameterName='Glow',Value=pulse));g.branch(g.math('Not_PreBool',A=g.get('bIntroCostume')))
 g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Player'))));speed=g.math('VSizeXY',A=g.out(g.call('Engine.Actor.GetVelocity',target=g.get('Player'))));g.branch(g.math('Greater_DoubleDouble',A=speed,B=30.));g.branch(g.out(g.call('Engine.NavMovementComponent.IsMovingOnGround',target=movement_ref)))
 interval=g.math('SelectFloat',A=.36,B=.64,bPickA=g.math('Greater_DoubleDouble',A=speed,B=260.));g.branch(g.math('Greater_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=time,B=g.get('LastStepTime')),B=interval));g.set('LastStepTime',time);g.do(g.call('Engine.AudioComponent.Play',target=g.get('MechanicalFootstep'),StartTime=0))
 compile_bp(visual);save(visual)
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith(('ROBOT_','HERO_','GUARDPLAYER_')):sub.destroy_actor(a)
 intro_actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='INTRO_AwakeningCyborg');im=intro_actor.get_component_by_class(unreal.SkeletalMeshComponent);im.set_skeletal_mesh_asset(mesh);im.set_editor_property('relative_scale3d',V((1.15,1.15,1.15)))
 for i in range(im.get_num_materials()):im.set_material(i,metal)
 for intro_flag in (False,True):
  a=sub.spawn_actor_from_class(B.generated_class(visual),V((0,0,0)),unreal.Rotator());a.set_actor_label('GUARDPLAYER_IntroVisual' if intro_flag else 'GUARDPLAYER_PlayerVisual');a.set_folder_path('LAB/00_Opening');a.set_editor_property('bIntroCostume',intro_flag)
  if intro_flag:a.set_editor_property('TargetMesh',im)
 mapfile=os.path.join(stage,'Lvl_LabTutorial.umap');shutil.copy2(os.path.join(content,'Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'));unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+mapfile.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(mapfile):raise RuntimeError('Staged map missing')
 r['files'].append({'source':mapfile,'destination':os.path.join(content,'Lvl_LabTutorial.umap')});r.update(saved=True,walk_speed=180,run_speed=420,locomotion_rate=.8,turn_rate=240,guard_visual_nodes=len(anchors),npc_spawned=False)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'guard_player_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Player guard conversion failed; see report')
