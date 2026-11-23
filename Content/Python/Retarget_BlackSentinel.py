"""Bake the existing player locomotion and capsule clips onto AccuRig."""
import unreal,os,sys,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,save,compile_bp
ROOT='/Game/Characters/BlackSentinel';tools=unreal.AssetToolsHelpers.get_asset_tools();out=os.path.join(unreal.Paths.project_saved_dir(),'sentinel_retarget.json');r={'saved':False}
def asset(name,cls,factory):
 path=ROOT+'/'+name
 return A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,cls,factory)
try:
 target=A.load_asset(ROOT+'/SK_BlackSentinel');source=A.load_asset('/Game/Characters/GuardPlayer/SK_PlayerGuard')
 rigs={}
 for label,mesh in [('Source',source),('Target',target)]:
  rig=asset('IK_Sentinel'+label,unreal.IKRigDefinition,unreal.IKRigDefinitionFactory());controller=unreal.IKRigController.get_controller(rig)
  if not controller.set_skeletal_mesh(mesh):raise RuntimeError('IK Rig mesh assignment failed '+label)
  auto=controller.apply_auto_generated_retarget_definition();r[label]={'automatic':auto,'chains':[str(c.chain_name) for c in controller.get_retarget_chains()]}
  if not auto and label=='Target':
   for existing in list(controller.get_retarget_chains()):controller.remove_retarget_chain(existing.chain_name)
   if not controller.set_retarget_root('CC_Base_Hip'):raise RuntimeError('AccuRig pelvis bone not found')
   chains=[('Spine','CC_Base_Waist','CC_Base_Spine02'),('Neck','CC_Base_NeckTwist01','CC_Base_NeckTwist02'),('Head','CC_Base_Head','CC_Base_Head')]
   for side,short in [('Left','L'),('Right','R')]:
    pre='CC_Base_'+short+'_'
    chains.extend([(side+'Leg',pre+'Thigh',pre+'Foot'),(side+'Foot',pre+'ToeBase',pre+'ToeBase'),(side+'Clavicle',pre+'Clavicle',pre+'Clavicle'),(side+'Arm',pre+'Upperarm',pre+'Hand')])
    for chain,bone in [('Thumb','Thumb'),('Index','Index'),('Middle','Mid'),('Ring','Ring'),('Pinky','Pinky')]:chains.append((side+chain,pre+bone+'1',pre+bone+'3'))
   for chain,start,end in chains:controller.add_retarget_chain(chain,start,end,'None')
   r[label]['chains']=[str(c.chain_name) for c in controller.get_retarget_chains()];r[label]['manual_accu_rig']=True
  elif not auto:raise RuntimeError('Automatic rig definition unavailable '+label)
  save(rig);rigs[label]=rig
 rt=asset('RTG_MannyToSentinel',unreal.IKRetargeter,unreal.IKRetargetFactory());controller=unreal.IKRetargeterController.get_controller(rt)
 controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE,rigs['Source']);controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET,rigs['Target']);controller.add_default_ops();controller.auto_map_chains(unreal.AutoMapChainType.EXACT,True)
 controller.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET,unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN);save(rt)
 inputs=unreal.IKRetargetBatchOperationInputs();abp=A.load_asset('/Game/Characters/GuardPlayer/ABP_PlayerGuard');assets=[abp];sequences=[]
 for path in A.list_assets('/Game/LabTutorial',recursive=True):
  if '/LS_CapsuleAwakening.' in path or path.endswith('/LS_CapsuleAwakening'):
   seq=A.load_asset(path);sequences.append(seq)
   for binding in seq.get_bindings():
    for track in binding.get_tracks():
     if isinstance(track,unreal.MovieSceneSkeletalAnimationTrack):
      for section in track.get_sections():
       clip=section.get_editor_property('params').get_editor_property('animation')
       if clip and clip not in assets:assets.append(clip)
 for k,v in dict(assets_to_retarget=[A.find_asset_data(a.get_path_name()) for a in assets],source_mesh=source,target_mesh=target,ik_retarget_asset=rt,prefix='BS_',target_path=ROOT+'/Animations',include_referenced_assets=True,overwrite_existing_files=True).items():inputs.set_editor_property(k,v)
 if A.does_asset_exist(ROOT+'/Animations/BS_ABP_PlayerGuard'):
  outputs=[A.find_asset_data(p) for p in A.list_assets(ROOT+'/Animations',recursive=True)]
 else:outputs=unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
 r['assets']=[a.get_asset().get_path_name() for a in outputs];r['input_animations']=[a.get_path_name() for a in assets];r['sequences']=[s.get_path_name() for s in sequences]
 converted=[]
 for data in outputs:
  obj=data.get_asset()
  if isinstance(obj,unreal.AnimBlueprint):compile_bp(obj);converted.append(obj.get_path_name())
  save(obj)
 r['animation_blueprints']=converted
 if not converted:raise RuntimeError('Retarget produced no animation blueprint')
 r['lod_count']=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(target);r['saved']=True
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(out,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
