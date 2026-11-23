"""Bind supplied geometry to the existing humanoid rig using native Geometry Script.
Keep all eight material groups and the supplied UDIM PBR textures.
"""
import unreal,os,sys,json,glob,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,save
ROOT='/Game/Enemies/Enceladus';S=os.path.abspath(unreal.Paths.project_saved_dir());R={'saved':False,'stages':[]}
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
try:
 tools=unreal.AssetToolsHelpers.get_asset_tools();A.make_directory(ROOT+'/Textures')
 source=A.load_asset(ROOT+'/SM_EnceladusSource');assert source
 mats={};R['textures']={}
 for slot in source.static_materials:
  part=str(slot.material_slot_name);tex={}
  for role in ('BaseColor','Normal','Metallic','Roughness'):
   name='T_Enceladus_'+part+'_'+role;path=ROOT+'/Textures/'+name
   t=A.load_asset(path) if A.does_asset_exist(path) else None
   if not t:
    files=sorted(glob.glob(os.path.join(unreal.Paths.project_dir(),'SourceAssets/Enceladus/Textures','Enceladus_'+part+'_'+role+'.*.png')));assert files,(part,role)
    task=unreal.AssetImportTask()
    for k,v in dict(filename=files[0],destination_path=ROOT+'/Textures',destination_name=name,automated=True,save=True).items():task.set_editor_property(k,v)
    tools.import_asset_tasks([task]);t=A.load_asset(path)
    if not t:t=next((A.load_asset(p) for p in task.imported_object_paths if isinstance(A.load_asset(p),unreal.Texture2D)),None)
   assert t,(part,role)
   t.set_editor_property('srgb',role=='BaseColor');t.set_editor_property('never_stream',False)
   t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else unreal.TextureCompressionSettings.TC_DEFAULT if role=='BaseColor' else unreal.TextureCompressionSettings.TC_MASKS)
   save(t);tex[role]=t;R['textures'][part+'_'+role]={'asset':t.get_path_name(),'virtual':t.virtual_texture_streaming,'width':t.blueprint_get_size_x(),'height':t.blueprint_get_size_y()}
  name='M_Enceladus_'+part;path=ROOT+'/'+name;mat=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
  M.delete_all_material_expressions(mat)
  for role,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Normal',unreal.MaterialProperty.MP_NORMAL),('Metallic',unreal.MaterialProperty.MP_METALLIC),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]:
   n=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample);n.set_editor_property('texture',tex[role]);virtual=tex[role].virtual_texture_streaming
   sampler=('SAMPLERTYPE_VIRTUAL_' if virtual else 'SAMPLERTYPE_')+('NORMAL' if role=='Normal' else 'COLOR' if role=='BaseColor' else 'MASKS')
   n.set_editor_property('sampler_type',getattr(unreal.MaterialSamplerType,sampler));assert M.connect_material_property(n,'RGB' if role in ('BaseColor','Normal') else 'R',prop)
  mat.set_editor_property('used_with_skeletal_mesh',True);M.recompile_material(mat);save(mat);mats[part]=mat
 R['stages'].append('PBR materials and UDIM textures')
 meshpath=ROOT+'/SK_Enceladus'
 if A.does_asset_exist(meshpath):sk=A.load_asset(meshpath)
 else:
  dm=unreal.DynamicMesh();_,outcome=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(source,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD());R['copy']=str(outcome)
  b=source.get_bounding_box();scale=180.54/(b.max.z-b.min.z)
  unreal.GeometryScript_MeshTransforms.scale_mesh(dm,V(scale,scale,scale))
  unreal.GeometryScript_MeshTransforms.translate_mesh(dm,V(0,6.85-(b.min.y+b.max.y)*.5*scale,-b.min.z*scale))
  R['original_triangles']=dm.get_triangle_count()
  if dm.get_triangle_count()>30000:unreal.GeometryScript_MeshSimplification.apply_editor_simplify_to_triangle_count(dm,30000)
  skeleton=A.load_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin')
  weights=unreal.GeometryScriptSmoothBoneWeightsOptions();weights.set_editor_property('max_influences',2);weights.set_editor_property('stiffness',.75)
  unreal.GeometryScript_BoneWeights.compute_smooth_bone_weights(dm,skeleton,weights)
  opts=unreal.GeometryScriptCreateNewSkeletalMeshAssetOptions();opts.set_editor_property('materials',{unreal.Name(k):v for k,v in mats.items()});opts.set_editor_property('enable_recompute_tangents',True)
  sk,outcome=unreal.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,skeleton,meshpath,opts);assert sk,str(outcome)
  R['triangles']=dm.get_triangle_count();R['stages'].append('native skin binding')
 # Explicit material-slot assignment makes order-independent material creation safe.
 slots=list(sk.materials)
 for slot in slots:
  part=str(slot.material_slot_name)
  if part in mats:slot.set_editor_property('material_interface',mats[part])
 sk.set_editor_property('materials',slots)
 if not sk.physics_asset:unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).create_physics_asset(sk,True)
 if sk.physics_asset:save(sk.physics_asset)
 save(sk);R.update(saved=True,mesh=sk.get_path_name(),skeleton=sk.skeleton.get_path_name(),physics=str(sk.physics_asset),material_slots=[str(x.material_slot_name) for x in sk.materials])
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
finally:json.dump(R,open(os.path.join(S,'enceladus_assets.json'),'w'),indent=2)
if not R['saved']:raise RuntimeError('Enceladus asset preparation incomplete')
