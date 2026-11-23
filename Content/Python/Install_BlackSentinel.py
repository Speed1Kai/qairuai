"""Install Black Sentinel on the existing player and capsule cinematic."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,components,compile_bp,save
ROOT='/Game/Characters/BlackSentinel';project=os.path.abspath(unreal.Paths.project_dir());content=os.path.abspath(unreal.Paths.project_content_dir());sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
r={'saved':False,'gameplay_tested':False,'modified':[]}
def backup(path):
 rel=path.removeprefix('/Game/')+('.umap' if path.endswith(('Lvl_LabTutorial','Lvl_SurfaceArrival')) else '.uasset');src=os.path.join(content,rel)
 if os.path.isfile(src):
  dst=os.path.join(r['backup'],rel);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
def patch_sockets(bp):
 mapping={'root':'RL_BoneRoot','pelvis':'CC_Base_Hip','head':'CC_Base_Head','neck_01':'CC_Base_NeckTwist01','spine_02':'CC_Base_Waist','spine_03':'CC_Base_Spine01','spine_05':'CC_Base_Spine02','upperarm_l':'CC_Base_L_Upperarm','upperarm_r':'CC_Base_R_Upperarm','lowerarm_l':'CC_Base_L_Forearm','lowerarm_r':'CC_Base_R_Forearm','hand_l':'CC_Base_L_Hand','hand_r':'CC_Base_R_Hand','calf_l':'CC_Base_L_Calf','calf_r':'CC_Base_R_Calf'}
 for gn in B.list_graph_names(bp):
  for n in G.get_graph_editor_by_name(bp,gn).list_all_nodes():
   p=n.find_input_pin('SocketName')
   if p.is_valid():
    old=str(p.get_pin_value())
    if old in mapping:p.set_pin_value(mapping[old])
try:
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 r['backup']=os.path.join(project,'Saved','Backups','BlackSentinel',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(r['backup'],exist_ok=True)
 for path in ['/Game/Lvl_LabTutorial','/Game/Surface/Lvl_SurfaceArrival','/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter','/Game/LabTutorial/Basement/BP_CyborgBodyLight','/Game/Characters/GuardPlayer/BP_PlayerGuardVisual','/Game/LabTutorial/Intro/LS_CapsuleAwakening']:backup(path)
 mesh=A.load_asset(ROOT+'/SK_BlackSentinel');material=A.load_asset(ROOT+'/M_BlackSentinel');abp=A.load_asset(ROOT+'/Animations/BS_ABP_PlayerGuard')
 if not mesh or not abp:raise RuntimeError('Retargeted player assets are missing')
 # Finish native assets made by the batch retarget, including referenced clips.
 for path in A.list_assets(ROOT+'/Animations',recursive=True):
  asset=A.load_asset(path)
  if isinstance(asset,unreal.AnimBlueprint):compile_bp(asset)
  save(asset)
 r['animation_assets']=len(A.list_assets(ROOT+'/Animations',recursive=True))
 sms=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
 if sms.get_lod_count(mesh)<4:
  if not sms.regenerate_lod(mesh,4):raise RuntimeError('Could not generate skeletal LODs')
 save(mesh);r['lod_count']=sms.get_lod_count(mesh)
 player=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 seen=set()
 for h,c,n in components(player):
  if not c or c.get_path_name() in seen:continue
  seen.add(c.get_path_name())
  if n=='Mesh':
   c.set_skeletal_mesh_asset(mesh);c.set_anim_instance_class(B.generated_class(abp));c.set_editor_property('relative_scale3d',V((1,1,1)));c.set_editor_property('relative_location',V((0,0,-105)))
   for i in range(c.get_num_materials()):c.set_material(i,material)
 compile_bp(player);save(player);r['modified'].append(player.get_path_name())
 # Keep K's real illumination. Hide old mannequin glow shells and fake spheres,
 # which would obscure the supplied robot and no longer match its anatomy.
 for path in ['/Game/Characters/GuardPlayer/BP_PlayerGuardVisual','/Game/LabTutorial/Basement/BP_CyborgBodyLight']:
  bp=A.load_asset(path);patch_sockets(bp)
  for h,c,n in components(bp):
   if not c:continue
   if isinstance(c,unreal.StaticMeshComponent) or n=='BodyGlowShell':c.set_editor_property('hidden_in_game',True);c.set_editor_property('cast_shadow',False)
   if n=='BodyGlowShell':c.set_skeletal_mesh_asset(mesh)
   if n=='BodyFill':c.set_editor_property('relative_location',V((0,0,0)))
  compile_bp(bp);save(bp);r['modified'].append(path)
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 intro=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='INTRO_AwakeningCyborg')
 im=intro.get_component_by_class(unreal.SkeletalMeshComponent);im.set_skeletal_mesh_asset(mesh);im.set_editor_property('relative_scale3d',V((1,1,1)))
 for i in range(im.get_num_materials()):im.set_material(i,material)
 sequence=A.load_asset('/Game/LabTutorial/Intro/LS_CapsuleAwakening');count=0
 for binding in sequence.get_bindings():
  for track in binding.get_tracks():
   if isinstance(track,unreal.MovieSceneSkeletalAnimationTrack):
    for section in track.get_sections():
     params=section.get_editor_property('params');clip=params.get_editor_property('animation')
     if not clip or clip.get_path_name().startswith(ROOT):continue
     replacement=A.load_asset(ROOT+'/Animations/BS_'+clip.get_name())
     if not replacement:raise RuntimeError('Missing retargeted intro animation '+clip.get_name())
     params.set_editor_property('animation',replacement);section.set_editor_property('params',params);count+=1
 save(sequence);r['cinematic_sections']=count
 # Instances sometimes store explicit visibility overrides; align both maps.
 for level in ['/Game/Lvl_LabTutorial','/Game/Surface/Lvl_SurfaceArrival']:
  if level.endswith('Lvl_SurfaceArrival'):unreal.EditorLoadingAndSavingUtils.load_map(level)
  for actor in sub.get_all_level_actors():
   if 'BP_PlayerGuardVisual' in actor.get_class().get_name() or 'BP_CyborgBodyLight' in actor.get_class().get_name():
    for c in actor.get_components_by_class(unreal.PrimitiveComponent):
     if isinstance(c,unreal.StaticMeshComponent) or c.get_name().startswith('BodyGlowShell'):c.set_hidden_in_game(True)
  if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Level save failed '+level)
 r['saved']=True
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(project,'Saved','sentinel_install.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
