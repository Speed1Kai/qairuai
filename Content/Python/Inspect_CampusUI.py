import unreal,os,json
w=unreal.EditorLevelLibrary.get_game_world();r={'world':str(w),'actors':[],'widgets':[]}
if not w:w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if isinstance(a,(unreal.Light,unreal.PostProcessVolume)) or 'Arrival' in a.get_class().get_name():
  d={'name':a.get_name(),'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':str(a.get_actor_location()),'components':[]}
  for c in a.get_components_by_class(unreal.ActorComponent):
   x={'name':c.get_name(),'class':c.get_class().get_name()}
   for k in ('intensity','visible','source_type','cubemap','light_color','cast_shadows'):
    try:x[k]=str(c.get_editor_property(k))
    except:pass
   d['components'].append(x)
  if isinstance(a,unreal.PostProcessVolume):
   s=a.settings;d['settings']={}
   for k in ('auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','auto_exposure_method','override_auto_exposure_bias'):d['settings'][k]=str(s.get_editor_property(k))
   d['unbound']=str(a.get_editor_property('unbound'))
  r['actors'].append(d)
for q in unreal.ObjectIterator(unreal.UserWidget):
 try:
  if q.is_in_viewport():r['widgets'].append({'class':q.get_class().get_name(),'title':str(q.get_editor_property('HUDTitle')),'body':str(q.get_editor_property('HUDMessage'))})
 except:pass
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'campus_ui_light_inspect.json'),'w'),indent=2,ensure_ascii=False)
