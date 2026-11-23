"""Heroic player redesign with reference-space rigid armour on Manny's rig."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,components,add,compile_bp,save,Graph,pin,val,link
ROOT='/Game/Characters/FinalSentinel';saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
backup=os.path.join(saved,'Backups','HeroCyborg',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
stage=os.path.join(saved,'HeroCyborgStaged');os.makedirs(stage,exist_ok=True)
r={'saved':False,'installed':False,'files':[],'backup':backup,'visual':'Original segmented armour on the existing Epic Manny skeleton; adapted from the image, not a reconstructed scan.'}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def external(self,name,cls,target):
  n=self.node(self.e.add_get_member_variable_node(name,cls));val(n.find_self_pin(),target);return pin(n,name,True)
def stage_asset(asset):
 package=asset.get_path_name().split('.')[0];relative=package.replace('/Game/','')+'.uasset';src=os.path.join(content,relative);dst=os.path.join(stage,relative);os.makedirs(os.path.dirname(dst),exist_ok=True)
 if os.path.isfile(src):
  bk=os.path.join(backup,relative);os.makedirs(os.path.dirname(bk),exist_ok=True);shutil.copy2(src,bk)
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="'+package+'" FILE="'+dst.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(dst):raise RuntimeError('Asset staging failed '+package)
 r['files'].append({'source':dst,'destination':src})
def mat(name,color,metal=.8,rough=.3,glow=False,normal=False):
 path=ROOT+'/'+name;m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew());M.delete_all_material_expressions(m)
 c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1))
 if glow:m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if glow else unreal.MaterialProperty.MP_BASE_COLOR)
 if not glow:
  for value,prop in [(metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)]:
   q=M.create_material_expression(m,unreal.MaterialExpressionConstant);q.set_editor_property('r',value);M.connect_material_property(q,'',prop)
  if normal:
   q=M.create_material_expression(m,unreal.MaterialExpressionTextureSample);q.set_editor_property('texture',A.load_asset('/Game/Characters/Mannequins/Textures/Manny/T_Manny_01_BN'));q.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL);M.connect_material_property(q,'RGB',unreal.MaterialProperty.MP_NORMAL)
 M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH);M.recompile_material(m);save(m);return m
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial');world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();A.make_directory(ROOT)
 mats={}
 for name,color,metal,rough,glow in [('M_HeroSilver',(.48,.56,.61),.8,.3,False),('M_HeroGraphite',(.028,.045,.065),.65,.43,False),('M_HeroGold',(.56,.32,.075),.8,.3,False),('M_HeroCore',(.16,4.8,7.5),0,.3,True),('M_HeroVisor',(.005,.018,.028),.7,.17,False)]:mats[name]=mat(name,color,metal,rough,glow)
 base=mat('M_HeroBaseMetal',(.19,.25,.3),.85,.37,False,True)
 specs=json.load(open(os.path.join(content,'Characters','FinalSentinel','Source','hero_armour_manifest.json')))
 refs=json.load(open(os.path.join(saved,'hero_rig_reference.json')));meshes={}
 for spec in specs:
  name=spec['name'];path=ROOT+'/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask();opts=unreal.FbxImportUI()
   for k,v in {'import_materials':False,'import_textures':False,'import_mesh':True,'automated_import_should_detect_type':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_STATIC_MESH}.items():opts.set_editor_property(k,v)
   opts.static_mesh_import_data.set_editor_property('combine_meshes',True);opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
   for k,v in {'filename':os.path.join(content,'Characters','FinalSentinel','Source',name+'.obj'),'destination_path':ROOT,'automated':True,'save':True,'options':opts}.items():task.set_editor_property(k,v)
   unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Import failed '+name)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,mats[str(slot.get_editor_property('material_slot_name'))])
  save(mesh);meshes[name]=mesh
 path=ROOT+'/BP_FinalSentinelArmour'
 if A.does_asset_exist(path):armour=A.load_asset(path)
 else:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);armour=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_FinalSentinelArmour',ROOT,unreal.Blueprint,f)
 compile_bp(armour);add(armour,unreal.SceneComponent,'ArmourRoot')
 for spec in specs:
  c=add(armour,unreal.StaticMeshComponent,spec['name'],'ArmourRoot');c.set_static_mesh(meshes[spec['name']]);c.set_collision_profile_name('NoCollision');c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_visibility(False)
  ref=refs[spec['bone']];t=unreal.Transform(location=V(ref['p']),rotation=unreal.Rotator(pitch=ref['r'][0],yaw=ref['r'][1],roll=ref['r'][2]),scale=V((1,1,1)));inverse=unreal.MathLibrary.invert_transform(t)
  c.set_editor_property('relative_location',inverse.translation);c.set_editor_property('relative_rotation',inverse.rotation.rotator());c.set_editor_property('relative_scale3d',V((1,1,1)))
 names=list(map(str,B.list_member_variable_names(armour)))
 for name,typ,default in [('TargetMesh',B.get_object_reference_type(unreal.SkeletalMeshComponent),'None'),('bIntroCostume',B.get_basic_type_by_name('bool'),'false')]:
  if name not in names:G.get_graph_editor_by_name(armour,'EventGraph').add_member_variable(name,typ,default)
  B.set_blueprint_variable_instance_editable(armour,name,True)
 compile_bp(armour);g=Flow(armour);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay');split=g.branch(g.get('bIntroCostume'));intro=split.find_then_pin();g.cursor=split.find_else_pin()
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=10.5));player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0));target=g.external('Mesh','/Script/Engine.Character',player);g.set('TargetMesh',target)
 first=None
 for spec in specs:
  q=g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(spec['name']),Parent=g.get('TargetMesh'),SocketName=spec['bone'],LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False)
  if first is None:first=q
  g.do(q);g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(spec['name']),bNewVisibility=True,bPropagateToChildren=False))
 link(intro,first.find_execute_pin())
 g.branch(g.get('bIntroCostume'));g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=10.))
 compile_bp(armour);save(armour)
 # Same skeleton and animation class: change only the playable mesh/materials.
 manny=A.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
 playerbp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 player_mesh=next(c for h,c,n in components(playerbp) if n=='Mesh');player_mesh.set_skeletal_mesh_asset(manny)
 for i in range(player_mesh.get_num_materials()):player_mesh.set_material(i,base if i==0 else mats['M_HeroGraphite'])
 compile_bp(playerbp);stage_asset(playerbp)
 # Maintain the K light's current intensity/radius and align its follower mesh.
 body=A.load_asset('/Game/LabTutorial/Basement/BP_CyborgBodyLight')
 shell=next(c for h,c,n in components(body) if n=='BodyGlowShell');shell.set_skeletal_mesh_asset(manny);compile_bp(body);stage_asset(body)
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith('HERO_'):sub.destroy_actor(a)
 intro_actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='INTRO_AwakeningCyborg')
 intro_mesh=intro_actor.get_component_by_class(unreal.SkeletalMeshComponent);intro_mesh.set_skeletal_mesh_asset(manny)
 for i in range(intro_mesh.get_num_materials()):intro_mesh.set_material(i,base if i==0 else mats['M_HeroGraphite'])
 for intro_flag in (False,True):
  a=sub.spawn_actor_from_class(B.generated_class(armour),V((0,0,0)),unreal.Rotator());a.set_actor_label('HERO_IntroArmour' if intro_flag else 'HERO_PlayerArmour');a.set_folder_path('LAB/00_Opening');a.set_editor_property('bIntroCostume',intro_flag)
  if intro_flag:a.set_editor_property('TargetMesh',intro_mesh)
 stagedmap=os.path.join(stage,'Lvl_LabTutorial.umap');shutil.copy2(os.path.join(content,'Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'))
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+stagedmap.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(stagedmap):raise RuntimeError('Map stage failed')
 r['files'].append({'source':stagedmap,'destination':os.path.join(content,'Lvl_LabTutorial.umap')});r.update(saved=True,armour_parts=len(specs),skeletal_base=manny.get_path_name(),controls_unchanged=True,gameplay_tested=False)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'hero_cyborg_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Hero cyborg authoring failed; see report')
