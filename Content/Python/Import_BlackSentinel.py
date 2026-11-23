"""Import the supplied AccuRig character, retain its rig and create shared PBR."""
import unreal,os,sys,json,shutil,traceback
from pathlib import Path
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,save,components
ROOT='/Game/Characters/BlackSentinel';project=Path(unreal.Paths.project_dir()).resolve();src=Path('S:/Black Sentinel – Futuristic Sci-Fi Robot Soldier 3D Model');copy=project/'SourceAssets/BlackSentinel';copy.mkdir(parents=True,exist_ok=True)
tools=unreal.AssetToolsHelpers.get_asset_tools();report={'saved':False}
def imported(file,name,skeletal=False):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 dest=copy/(name+Path(file).suffix)
 if not dest.exists():shutil.copy2(file,dest)
 task=unreal.AssetImportTask()
 for k,v in dict(filename=str(dest),destination_path=ROOT,destination_name=name,automated=True,save=True).items():task.set_editor_property(k,v)
 if skeletal:
  opts=unreal.FbxImportUI()
  for k,v in dict(import_mesh=True,import_as_skeletal=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=True,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH).items():opts.set_editor_property(k,v)
  opts.skeletal_mesh_import_data.set_editor_property('import_morph_targets',False);task.set_editor_property('options',opts)
 tools.import_asset_tasks([task]);obj=A.load_asset(path)
 if not obj:
  obj=next((A.load_asset(p) for p in task.imported_object_paths if isinstance(A.load_asset(p),unreal.SkeletalMesh if skeletal else unreal.Texture2D)),None)
 if not obj:raise RuntimeError('Import failed '+name)
 return obj
try:
 A.make_directory(ROOT);textures={}
 for role,pattern in [('Color','Material_001_Diffuse.jpg'),('Normal','Material_001_Normal.jpg'),('Metal','Material_001_Metallic.png'),('Roughness','Material_001_roughness.png')]:
  file=next(src.rglob(pattern));t=imported(file,'T_Sentinel_'+role);t.set_editor_property('max_texture_size',2048);t.set_editor_property('never_stream',False);t.set_editor_property('srgb',role=='Color')
  t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else unreal.TextureCompressionSettings.TC_DEFAULT if role=='Color' else unreal.TextureCompressionSettings.TC_MASKS);save(t);textures[role]=t
 m=A.load_asset(ROOT+'/M_BlackSentinel') if A.does_asset_exist(ROOT+'/M_BlackSentinel') else tools.create_asset('M_BlackSentinel',ROOT,unreal.Material,unreal.MaterialFactoryNew());M.delete_all_material_expressions(m)
 for role,prop in [('Color',unreal.MaterialProperty.MP_BASE_COLOR),('Normal',unreal.MaterialProperty.MP_NORMAL),('Metal',unreal.MaterialProperty.MP_METALLIC),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]:
  n=M.create_material_expression(m,unreal.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[role]);n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='Color' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
  if not M.connect_material_property(n,'' if role in ('Color','Normal') else 'R',prop):raise RuntimeError('Material input rejected '+role)
 m.set_editor_property('used_with_skeletal_mesh',True)
 m.set_editor_property('used_with_morph_targets',True)
 M.recompile_material(m);save(m)
 mesh=imported(next(src.glob('*.fbx')),'SK_BlackSentinel',True)
 mats=list(mesh.materials)
 for slot in mats:slot.set_editor_property('material_interface',m)
 mesh.set_editor_property('materials',mats);save(mesh)
 # Inspect editor API once rather than guessing version-specific LOD signatures.
 report.update(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),bounds=str(mesh.get_bounds()),saved=True)
 report['lod_api']={n:getattr(unreal.SkeletalMeshEditorSubsystem,n).__doc__ for n in dir(unreal.SkeletalMeshEditorSubsystem) if any(k in n for k in ['lod','reduction'])}
 report['ikrig_api']={n:getattr(unreal.IKRigController,n).__doc__ for n in ['set_skeletal_mesh','apply_auto_generated_retarget_definition','get_retarget_chains']}
 player=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 report['player_components']=[{'name':n,'class':c.get_class().get_name(),'position':str(c.get_editor_property('relative_location')),'scale':str(c.get_editor_property('relative_scale3d'))} for h,c,n in components(player) if c and isinstance(c,unreal.SceneComponent)]
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 (project/'Saved/sentinel_import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
