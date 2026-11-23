"""Prepare copied city textures synchronously without a graphics device."""
import unreal,os,json,traceback
A=unreal.EditorAssetLibrary;M=unreal.MaterialEditingLibrary
out=os.path.join(unreal.Paths.project_saved_dir(),'downtown_texture_preparation.json')
r={'complete':False,'prepared':[],'material_parameters':{}}
try:
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 unreal.SystemLibrary.execute_console_command(world,'Editor.AsyncTextureCompilation 0')
 registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.scan_paths_synchronous(['/Game/CityDowntown'],force_rescan=True)
 assets=registry.get_assets_by_path('/Game/CityDowntown',recursive=True)
 for data in assets:
  cls=str(data.asset_class_path.asset_name)
  if cls not in ('Texture2D','TextureCube'):continue
  texture=data.get_asset();limit=512 if cls=='TextureCube' else 2048
  if texture.get_editor_property('max_texture_size')!=limit:
   texture.set_editor_property('max_texture_size',limit)
   if cls=='Texture2D':texture.set_editor_property('never_stream',False)
   if not A.save_loaded_asset(texture,only_if_is_dirty=False):raise RuntimeError('Texture save failed '+texture.get_path_name())
  r['prepared'].append(texture.get_path_name())
  if len(r['prepared'])%20==0:
   with open(out,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
 for path in A.list_assets('/Game/CityDowntown/Materials/Windows',recursive=True):
  material=A.load_asset(path)
  if isinstance(material,unreal.MaterialInterface):
   r['material_parameters'][str(path)]={'scalar':list(map(str,M.get_scalar_parameter_names(material))),'vector':list(map(str,M.get_vector_parameter_names(material)))}
 r['complete']=True
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(out,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
