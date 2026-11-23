"""Author the playable red/gunmetal robot. Runtime is native Blueprint/UMG only."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,components,add,compile_bp,save,Graph,pin,val,link
ROOT='/Game/Characters/ProtocolRobot';content=os.path.abspath(unreal.Paths.project_content_dir());saved=os.path.abspath(unreal.Paths.project_saved_dir())
cfg=json.load(open(os.path.join(content,'Characters','ProtocolRobot','Config','RobotSettings.json')))
stage=os.path.join(saved,'ProtocolRobotStaged');os.makedirs(stage,exist_ok=True)
backup=os.path.join(saved,'Backups','ProtocolRobot',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
r={'saved':False,'installed':False,'files':[],'backup':backup,'placeholder':True,'gameplay_tested':False}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def external(self,name,cls,target):
  n=self.node(self.e.add_get_member_variable_node(name,cls));val(n.find_self_pin(),target);return pin(n,name,True)
def stage_asset(asset):
 package=asset.get_path_name().split('.')[0];rel=package.replace('/Game/','')+'.uasset';src=os.path.join(content,rel);dst=os.path.join(stage,rel);os.makedirs(os.path.dirname(dst),exist_ok=True)
 if os.path.isfile(src):
  bk=os.path.join(backup,rel);os.makedirs(os.path.dirname(bk),exist_ok=True);shutil.copy2(src,bk)
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="'+package+'" FILE="'+dst.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(dst):raise RuntimeError('Staged save failed '+package)
 r['files'].append({'source':dst,'destination':src})
def member(bp,name,typ,default):
 if name not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,typ,str(default))
 B.set_blueprint_variable_instance_editable(bp,name,True)
def colour(rgb):return unreal.LinearColor(r=rgb[0],g=rgb[1],b=rgb[2],a=rgb[3] if len(rgb)>3 else 1.)
def material(name,rgb,metal,rough,emissive=False):
 path=ROOT+'/Materials/'+name
 m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew());M.delete_all_material_expressions(m)
 if emissive:
  m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
  col=M.create_material_expression(m,unreal.MaterialExpressionVectorParameter);col.set_editor_property('parameter_name','GlowColor');col.set_editor_property('default_value',colour(cfg['glow_color_linear']))
  strength=M.create_material_expression(m,unreal.MaterialExpressionScalarParameter);strength.set_editor_property('parameter_name','GlowStrength');strength.set_editor_property('default_value',cfg['glow_strength'])
  frequency=M.create_material_expression(m,unreal.MaterialExpressionScalarParameter);frequency.set_editor_property('parameter_name','PulseHz');frequency.set_editor_property('default_value',cfg['pulse_hz'])
  time=M.create_material_expression(m,unreal.MaterialExpressionTime)
  pulse=M.create_material_expression(m,unreal.MaterialExpressionCustom);pulse.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
  inputs=[]
  for name in ('T','F'):
   v=unreal.CustomInput();v.set_editor_property('input_name',name);inputs.append(v)
  pulse.set_editor_property('inputs',inputs);pulse.set_editor_property('code','return 1.0 + 0.15*sin(T*6.283185307*F);');M.connect_material_expressions(time,'',pulse,'T');M.connect_material_expressions(frequency,'',pulse,'F')
  q=M.create_material_expression(m,unreal.MaterialExpressionMultiply);M.connect_material_expressions(strength,'',q,'A');M.connect_material_expressions(pulse,'',q,'B')
  out=M.create_material_expression(m,unreal.MaterialExpressionMultiply);M.connect_material_expressions(col,'',out,'A');M.connect_material_expressions(q,'',out,'B');M.connect_material_property(out,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 else:
  col=M.create_material_expression(m,unreal.MaterialExpressionVectorParameter);col.set_editor_property('parameter_name','BaseColor');col.set_editor_property('default_value',colour(rgb));M.connect_material_property(col,'',unreal.MaterialProperty.MP_BASE_COLOR)
  for name,value,prop in [('Metallic',metal,unreal.MaterialProperty.MP_METALLIC),('Roughness',rough,unreal.MaterialProperty.MP_ROUGHNESS)]:
   n=M.create_material_expression(m,unreal.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);M.connect_material_property(n,'',prop)
 M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH);M.recompile_material(m);save(m);return m
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial');world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 for folder in ('Models','Materials','Blueprints','Animations'):A.make_directory(ROOT+'/'+folder)
 mats={}
 for name,rgb,metal,rough,glow in [('M_RobotGunmetal',(.065,.075,.09),cfg['metallic'],cfg['roughness'],False),('M_RobotChrome',(.3,.34,.4),.96,.23,False),('M_RobotJoint',(.012,.016,.022),.6,.4,False),('M_RobotRed',(1,.01033,.01033),0,.3,True)]:mats[name]=material(name,rgb,metal,rough,glow)
 specs=json.load(open(os.path.join(content,'Characters','ProtocolRobot','Models','Source','robot_parts.json')));refs=json.load(open(os.path.join(saved,'protocol_robot_rig.json')))
 meshes={}
 for spec in specs:
  name=spec['name'];path=ROOT+'/Models/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask();opts=unreal.FbxImportUI()
   for k,v in {'import_mesh':True,'import_materials':False,'import_textures':False,'automated_import_should_detect_type':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_STATIC_MESH}.items():opts.set_editor_property(k,v)
   opts.static_mesh_import_data.set_editor_property('combine_meshes',True);opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
   for k,v in {'filename':os.path.join(content,'Characters','ProtocolRobot','Models','Source',name+'.obj'),'destination_path':ROOT+'/Models','automated':True,'save':True,'options':opts}.items():task.set_editor_property(k,v)
   unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Missing robot part '+name)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,mats[str(slot.get_editor_property('material_slot_name'))])
  save(mesh);meshes[name]=mesh
 # Reuse a validated skinned mannequin core and existing locomotion assets.
 sk=A.load_asset(ROOT+'/Models/SK_ProtocolRobot') or A.duplicate_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple',ROOT+'/Models/SK_ProtocolRobot')
 slots=sk.get_editor_property('materials')
 for i,slot in enumerate(slots):slot.set_editor_property('material_interface',mats['M_RobotGunmetal' if i==0 else 'M_RobotJoint'])
 sk.set_editor_property('materials',slots);save(sk)
 anim=ROOT+'/Animations/'
 copies={'ABP_ProtocolRobot':'/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed','BS_ProtocolRobot':'/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run','AN_RobotIdle':'/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle','AN_RobotWalk':'/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd','AN_RobotRun':'/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd','AN_RobotJump':'/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Jump'}
 assets={name:(A.load_asset(anim+name) or A.duplicate_asset(src,anim+name)) for name,src in copies.items()}
 abp=assets['ABP_ProtocolRobot'];rates=[]
 for graph in B.list_graph_names(abp):
  for node in G.get_graph_editor_by_name(abp,graph).list_all_nodes():
   if node.get_class().get_name()=='AnimGraphNode_BlendSpacePlayer':
    data=node.get_editor_property('node');data.set_editor_property('blend_space',assets['BS_ProtocolRobot'])
    try:data.set_editor_property('play_rate',.9);rates.append(.9)
    except Exception:pass
    node.set_editor_property('node',data)
 compile_bp(abp)
 for asset in assets.values():save(asset)
 # The visual actor exposes material, pulse and light settings in Details.
 path=ROOT+'/Blueprints/BP_ProtocolRobotVisual'
 visual=A.load_asset(path)
 if not visual:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);visual=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ProtocolRobotVisual',ROOT+'/Blueprints',unreal.Blueprint,f)
 compile_bp(visual);add(visual,unreal.SceneComponent,'RobotRoot')
 for spec in specs:
  c=add(visual,unreal.StaticMeshComponent,spec['name'],'RobotRoot');c.set_static_mesh(meshes[spec['name']]);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_visibility(False)
  ref=refs[spec['bone']];transform=unreal.Transform(location=V(ref['p']),rotation=unreal.Rotator(pitch=ref['r'][0],yaw=ref['r'][1],roll=ref['r'][2]),scale=V((1,1,1)));inv=unreal.MathLibrary.invert_transform(transform)
  c.set_editor_property('relative_location',inv.translation);c.set_editor_property('relative_rotation',inv.rotation.rotator())
 light_specs=[('EyeGlow','head',(0,14,172),12.,100.),('ChestGlow','spine_05',(0,19,135),40.,175.)]
 for name,bone,p,intensity,radius in light_specs:
  c=add(visual,unreal.PointLightComponent,name,'RobotRoot');c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('intensity_units',unreal.LightUnits.LUMENS);c.set_intensity(intensity);c.set_attenuation_radius(radius);c.set_cast_shadows(False);c.set_light_color(colour(cfg['glow_color_linear']));c.set_visibility(False)
  ref=refs[bone];t=unreal.Transform(location=V(ref['p']),rotation=unreal.Rotator(pitch=ref['r'][0],yaw=ref['r'][1],roll=ref['r'][2]),scale=V((1,1,1)));c.set_editor_property('relative_location',unreal.MathLibrary.inverse_transform_location(t,V(p)))
 for name,typ,default in [('TargetMesh',B.get_object_reference_type(unreal.SkeletalMeshComponent),'None'),('bIntroCostume',B.get_basic_type_by_name('bool'),'false'),('GlowStrength',B.get_basic_type_by_name('double'),cfg['glow_strength']),('PulseHz',B.get_basic_type_by_name('double'),cfg['pulse_hz']),('GlowColor',B.get_struct_type(unreal.load_object(None,'/Script/CoreUObject.LinearColor')),'(R=1.0,G=0.01033,B=0.01033,A=1.0)'),('GlowMID',B.get_object_reference_type(unreal.MaterialInstanceDynamic),'None'),('bReady',B.get_basic_type_by_name('bool'),'false')]:member(visual,name,typ,default)
 for name,key in [('WalkSpeed','walk_speed'),('RunSpeed','run_speed'),('JumpVelocity','jump_velocity'),('TurnRate','turn_rate')]:member(visual,name,B.get_basic_type_by_name('double'),cfg[key])
 compile_bp(visual);g=Flow(visual);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay');split=g.branch(g.get('bIntroCostume'));intro=split.find_then_pin();g.cursor=split.find_else_pin();g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=10.5))
 player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0));g.set('TargetMesh',g.external('Mesh','/Script/Engine.Character',player))
 movement_ref=g.external('CharacterMovement','/Script/Engine.Character',player)
 for prop,param in [('MaxWalkSpeed','WalkSpeed'),('JumpZVelocity','JumpVelocity')]:g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=movement_ref,PropertyName=prop,Value=g.get(param)))
 for prop,param in [('RobotWalkSpeed','WalkSpeed'),('RobotRunSpeed','RunSpeed')]:g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=player,PropertyName=prop,Value=g.get(param)))
 g.do(g.call('Engine.KismetSystemLibrary.SetRotatorPropertyByName',Object=movement_ref,PropertyName='RotationRate',Value=g.math('MakeRotator',Roll=0,Pitch=0,Yaw=g.get('TurnRate'))))
 create=g.call('Engine.KismetMaterialLibrary.CreateDynamicMaterialInstance',Parent=mats['M_RobotRed'].get_path_name());g.do(create);link(intro,create.find_execute_pin());g.set('GlowMID',g.out(create))
 for param in ('GlowStrength','PulseHz'):g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('GlowMID'),ParameterName=param,Value=g.get(param)))
 g.do(g.call('Engine.MaterialInstanceDynamic.SetVectorParameterValue',target=g.get('GlowMID'),ParameterName='GlowColor',Value=g.get('GlowColor')))
 for spec in specs:
  target=g.get(spec['name']);g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=target,Parent=g.get('TargetMesh'),SocketName=spec['bone'],LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False));g.do(g.call('Engine.SceneComponent.SetVisibility',target=target,bNewVisibility=True,bPropagateToChildren=False))
  for i,slot in enumerate(meshes[spec['name']].get_editor_property('static_materials')):
   if str(slot.get_editor_property('material_slot_name'))=='M_RobotRed':g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=target,ElementIndex=i,Material=g.get('GlowMID')))
 for name,bone,p,intensity,radius in light_specs:
  g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(name),Parent=g.get('TargetMesh'),SocketName=bone,LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False));g.do(g.call('Engine.LightComponent.SetLightColor',target=g.get(name),NewLightColor=g.get('GlowColor'),bSRGB=False));g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=True,bPropagateToChildren=False))
 g.set('bReady',True);g.branch(g.get('bIntroCostume'));g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=10.))
 g.event('ReceiveTick');g.branch(g.get('bReady'));time=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'));phase=g.math('Multiply_DoubleDouble',A=time,B=g.math('Multiply_DoubleDouble',A=g.get('PulseHz'),B=6.283185307));pulse=g.math('Add_DoubleDouble',A=1.,B=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=phase),B=.15))
 for name,bone,p,intensity,radius in light_specs:g.do(g.call('Engine.LightComponent.SetIntensity',target=g.get(name),NewIntensity=g.math('Multiply_DoubleDouble',A=pulse,B=g.math('Multiply_DoubleDouble',A=g.get('GlowStrength'),B=intensity/3.))))
 compile_bp(visual);save(visual)
 # Preserve WASD/Enhanced Input, camera, jump and crouch logic. Only rebind sprint.
 playerbp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');pm=next(c for h,c,n in components(playerbp) if n=='Mesh');pm.set_skeletal_mesh_asset(sk);pm.set_anim_instance_class(B.generated_class(abp));pm.set_editor_property('relative_scale3d',V((cfg['height_scale'],)*3));pm.set_editor_property('relative_location',V((0,0,-99)))
 for i in range(pm.get_num_materials()):pm.set_material(i,mats['M_RobotGunmetal' if i==0 else 'M_RobotJoint'])
 movement=next(c for h,c,n in components(playerbp) if isinstance(c,unreal.CharacterMovementComponent));movement.set_editor_property('max_walk_speed',cfg['walk_speed']);movement.set_editor_property('jump_z_velocity',cfg['jump_velocity']);movement.set_editor_property('max_acceleration',cfg['acceleration']);movement.set_editor_property('braking_deceleration_walking',cfg['braking']);movement.set_editor_property('orient_rotation_to_movement',True);movement.set_editor_property('rotation_rate',unreal.Rotator(yaw=cfg['turn_rate']))
 capsule=next(c for h,c,n in components(playerbp) if isinstance(c,unreal.CapsuleComponent));capsule.set_capsule_half_height(99.)
 for name,key in [('RobotWalkSpeed','walk_speed'),('RobotRunSpeed','run_speed'),('RobotJumpVelocity','jump_velocity'),('RobotTurnRate','turn_rate')]:member(playerbp,name,B.get_basic_type_by_name('double'),cfg[key])
 compile_bp(playerbp);g=Flow(playerbp)
 for node in list(g.e.list_all_nodes()):
  if node.get_class().get_name()=='K2Node_InputKey' and str(node.get_editor_property('input_key').get_editor_property('key_name'))=='LeftShift':g.e.remove_nodes([node])
 actions=[n for n in g.e.list_available_nodes([]) if '|KeyboardEvents|' in n and 'Shift' in n.rsplit('|',1)[-1] and 'Debug' not in n and 'Right' not in n and 'Правая' not in n]
 if not actions:raise RuntimeError('No registered LeftShift event')
 key=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(),[]))
 for edge,param in [('Pressed','RobotRunSpeed'),('Released','RobotWalkSpeed')]:
  g.cursor=pin(key,edge,True);g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('CharacterMovement'),PropertyName='MaxWalkSpeed',Value=g.get(param)))
 cdo=unreal.get_default_object(B.generated_class(playerbp));cdo.set_editor_property('use_controller_rotation_yaw',False)
 # Use editable defaults at runtime, including jump and smooth facing settings.
 for name,value in [('RobotWalkSpeed',cfg['walk_speed']),('RobotRunSpeed',cfg['run_speed']),('RobotJumpVelocity',cfg['jump_velocity']),('RobotTurnRate',cfg['turn_rate'])]:cdo.set_editor_property(name,float(value))
 compile_bp(playerbp);stage_asset(playerbp)
 body=A.load_asset('/Game/LabTutorial/Basement/BP_CyborgBodyLight');shell=next(c for h,c,n in components(body) if n=='BodyGlowShell');shell.set_skeletal_mesh_asset(sk);compile_bp(body);stage_asset(body)
 # Replace both old costume instances, retaining the existing capsule animation.
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith(('HERO_','ROBOT_')):sub.destroy_actor(a)
 intro_actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='INTRO_AwakeningCyborg');im=intro_actor.get_component_by_class(unreal.SkeletalMeshComponent);im.set_skeletal_mesh_asset(sk);im.set_editor_property('relative_scale3d',V((cfg['height_scale'],)*3))
 for i in range(im.get_num_materials()):im.set_material(i,mats['M_RobotGunmetal' if i==0 else 'M_RobotJoint'])
 for intro_flag in (False,True):
  a=sub.spawn_actor_from_class(B.generated_class(visual),V((0,0,0)),unreal.Rotator());a.set_actor_label('ROBOT_IntroVisual' if intro_flag else 'ROBOT_PlayerVisual');a.set_folder_path('LAB/00_Opening');a.set_editor_property('bIntroCostume',intro_flag)
  if intro_flag:a.set_editor_property('TargetMesh',im)
 # A modest bloom amount keeps the emissive red readable rather than blown out.
 for a in sub.get_all_level_actors():
  if isinstance(a,unreal.PostProcessVolume):
   settings=a.get_editor_property('settings');settings.set_editor_property('override_bloom_intensity',True);settings.set_editor_property('bloom_intensity',.3);a.set_editor_property('settings',settings)
 stagedmap=os.path.join(stage,'Lvl_LabTutorial.umap');shutil.copy2(os.path.join(content,'Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'));unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+stagedmap.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(stagedmap):raise RuntimeError('Map not staged')
 r['files'].append({'source':stagedmap,'destination':os.path.join(content,'Lvl_LabTutorial.umap')});r.update(saved=True,parts=len(specs),height_cm=200,pulse_hz=cfg['pulse_hz'],settings=cfg,animation_rate_overrides=rates)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'protocol_robot_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Protocol robot authoring failed; see report')
