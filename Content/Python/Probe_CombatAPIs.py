import unreal,os,json
R={}
classes={'asset':unreal.GeometryScript_AssetUtils,'new':unreal.GeometryScript_NewAssetUtils,'skin':unreal.GeometryScript_BoneWeights,'transform':unreal.GeometryScript_MeshTransforms,'query':unreal.GeometryScript_MeshQueries,'simplify':unreal.GeometryScript_MeshSimplification}
for label,cls in classes.items():
 R[label]={n:getattr(cls,n).__doc__ for n in dir(cls) if any(k in n for k in ('copy_mesh_from','create_new_skeletal','compute_smooth','transfer_bone','translate_mesh','scale_mesh','transform_mesh','bounding_box','simplify_to_triangle'))}
R['options']={n:getattr(unreal,n).__doc__ for n in ('GeometryScriptSmoothBoneWeightsOptions','GeometryScriptCreateNewSkeletalMeshAssetOptions','GeometryScriptCopyMeshFromAssetOptions')}
mesh=unreal.load_asset('/Game/Enemies/Architect/SK_EnemyRobot');R['manny_bounds']=str(mesh.get_bounds());R['skeleton']=mesh.skeleton.get_path_name()
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'combat_api.json'),'w'),indent=2)
