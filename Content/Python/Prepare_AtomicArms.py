"""Author lightweight robot arms using existing skin weights and rifle pose."""
import unreal,os,sys,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
P=os.path.abspath(unreal.Paths.project_dir());D='/Game/Combat/AtomicWeapon';R={}
try:
 target=A.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel');source=A.load_asset('/Game/Characters/GuardPlayer/SK_PlayerGuard')
 clips=[A.load_asset('/Game/Characters/Mannequins/Anims/Rifle/'+n) for n in ('MF_Rifle_Idle_ADS','MM_Rifle_Fire','MM_Rifle_Equip')]
 inputs=unreal.IKRetargetBatchOperationInputs()
 for k,v in dict(assets_to_retarget=[A.find_asset_data(a.get_path_name()) for a in clips],source_mesh=source,target_mesh=target,ik_retarget_asset=A.load_asset('/Game/Characters/BlackSentinel/RTG_MannyToSentinel'),prefix='Atomic_',target_path=D+'/Animations',include_referenced_assets=False,overwrite_existing_files=True).items():inputs.set_editor_property(k,v)
 outputs=unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
 for a in outputs:save(a.get_asset())
 R['animations']=[a.get_asset().get_path_name() for a in outputs]
 dm=unreal.DynamicMesh();unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(target,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
 # Remove torso, head and legs in reference space; retain original arm skinning/UVs.
 _,sel=unreal.GeometryScript_MeshSelection.select_mesh_elements_in_box(dm,unreal.Box(min=V(-21,-100,-10),max=V(21,100,250)),min_num_triangle_points=1)
 unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dm,sel)
 _,sel=unreal.GeometryScript_MeshSelection.select_mesh_elements_with_plane(dm,V(0,0,115),V(0,0,-1),min_num_triangle_points=1)
 unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dm,sel)
 opt=unreal.GeometryScriptCreateNewSkeletalMeshAssetOptions();R['options']=str(opt)
 if not A.does_asset_exist(D+'/SK_SentinelArms'):
  sk,out=unreal.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,target.skeleton,D+'/SK_SentinelArms',opt);R['arms_outcome']=str(out)
 else:sk=A.load_asset(D+'/SK_SentinelArms')
 sk.set_editor_property('materials',target.materials);save(sk);R['arms']=sk.get_path_name();R['bounds']=str(sk.get_bounds())
 seq=A.load_asset(D+'/Animations/Atomic_MF_Rifle_Idle_ADS');pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,unreal.AnimPoseEvaluationOptions())
 R['bones']={n:str(unreal.AnimPoseExtensions.get_bone_pose(pose,n,unreal.AnimPoseSpaces.WORLD)) for n in ('CC_Base_R_Hand','CC_Base_L_Hand','CC_Base_R_Upperarm','CC_Base_L_Upperarm','CC_Base_Head')}
 bp=A.load_asset('/Game/Characters/BlackSentinel/Animations/BS_ABP_PlayerGuard');e=G.get_graph_editor_by_name(bp,'AnimGraph')
 R['menus']=[str(x) for x in e.list_available_nodes([]) if any(w in str(x).lower() for w in ('layered','sequenceplayer','последоват','слоям','смешиван'))]
 R['animnode_docs']={n:getattr(unreal,n).__doc__ for n in ('AnimNode_LayeredBoneBlend','AnimNode_SequencePlayer','InputScaleBias','BranchFilter','InputBlendPose')}
except Exception:R['error']=traceback.format_exc()
json.dump(R,open(P+'/Saved/atomic_arms_prepare.json','w'),indent=2,default=str)
