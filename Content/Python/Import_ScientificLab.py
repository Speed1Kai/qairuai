"""Import the supplied GLB into a dedicated authoring map, preserving its layout."""
import unreal,os,json,sys,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,save
ROOT='/Game/Environment/ScientificLab';LEVEL=ROOT+'/Lvl_SourcePreview';p=os.path.abspath(unreal.Paths.project_dir())
r={'saved':False,'actors':[]};sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
try:
 unreal.SystemLibrary.execute_console_command(None,'Editor.AsyncTextureCompilation 0')
 A.make_directory(ROOT)
 if A.does_asset_exist(LEVEL):unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 else:unreal.EditorLevelLibrary.new_level(LEVEL)
 manager=unreal.InterchangeManager.get_interchange_manager_scripted()
 source=manager.create_source_data(os.path.join(p,'SourceAssets/ScientificLab/ScientificLab_UE.glb'))
 params=unreal.ImportAssetParameters();params.set_editor_property('is_automated',True);params.set_editor_property('replace_existing',False)
 if not manager.import_scene(ROOT+'/Assets',source,params):raise RuntimeError('Native GLB scene import failed')
 for path in A.list_assets(ROOT+'/Assets',recursive=True):
  asset=A.load_asset(path)
  if isinstance(asset,unreal.Texture2D):asset.set_editor_property('max_texture_size',2048);asset.set_editor_property('never_stream',False)
  save(asset)
 for actor in sub.get_all_level_actors():
  cs=[]
  for c in actor.get_components_by_class(unreal.StaticMeshComponent):
   if not c.static_mesh:continue
   t=c.get_world_transform();b,e=actor.get_actor_bounds(False)
   cs.append({'mesh':c.static_mesh.get_path_name(),'p':[t.translation.x,t.translation.y,t.translation.z],'r':[t.rotation.rotator().pitch,t.rotation.rotator().yaw,t.rotation.rotator().roll],'s':[t.scale3d.x,t.scale3d.y,t.scale3d.z],'origin':[b.x,b.y,b.z],'extent':[e.x,e.y,e.z],'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
  if cs:r['actors'].append({'label':actor.get_actor_label(),'components':cs})
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Preview map save failed')
 r['saved']=True;r['asset_count']=len(A.list_assets(ROOT+'/Assets',recursive=True))
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(p,'Saved/scientific_lab_import.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
