"""Read-only scene/resource inventory. No game session is started."""
import unreal,os,json,collections,traceback
r={}
try:
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);actors=sub.get_all_level_actors();r['actors']=len(actors);r['actor_classes']=collections.Counter(a.get_class().get_name() for a in actors)
 meshes={};lights=[];captures=[]
 for a in actors:
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   m=c.static_mesh
   if m:
    p=m.get_path_name();meshes[p]=meshes.get(p,0)+1
  for c in a.get_components_by_class(unreal.LightComponent):
   lights.append({'actor':a.get_actor_label(),'component':c.get_name(),'class':c.get_class().get_name(),'shadow':c.get_editor_property('cast_shadows'),'intensity':c.get_editor_property('intensity')})
  captures.extend(a.get_actor_label() for c in a.get_components_by_class(unreal.SceneCaptureComponent2D))
 r['static_mesh_components']=sum(meshes.values());r['unique_static_meshes']=len(meshes);r['lights']=lights;r['scene_captures']=captures
 tex=[]
 for t in unreal.ObjectIterator(unreal.Texture2D):
  if not t.get_path_name().startswith('/Game/'):continue
  d={'path':t.get_path_name(),'max_size':t.get_editor_property('max_texture_size'),'never_stream':t.get_editor_property('never_stream'),'group':str(t.get_editor_property('lod_group'))}
  try:d['x']=t.blueprint_get_size_x();d['y']=t.blueprint_get_size_y()
  except Exception:pass
  tex.append(d)
 r['loaded_textures']=tex
 m=unreal.EditorAssetLibrary.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel');r['sentinel_lods']=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(m)
 r['widget_guid_property_api']={}
 for p in ('/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt'):
  bp=unreal.EditorAssetLibrary.load_asset(p)
  try:r['widget_guid_property_api'][p]=len(bp.get_editor_property('widget_variable_name_to_guid_map'))
  except Exception as ex:r['widget_guid_property_api'][p]=str(ex)
except Exception:r['error']=traceback.format_exc()
open(os.path.join(unreal.Paths.project_saved_dir(),'memory_scene_audit.json'),'w',encoding='utf8').write(json.dumps(r,ensure_ascii=False,indent=2))
