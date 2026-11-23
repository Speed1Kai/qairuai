"""Read the currently open editor world without reloading the player's map."""
import unreal,os,json
r={'actors':[],'level_api':{}}
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 p=a.get_actor_location();n=a.get_actor_label()
 if 780<p.x<2350 and p.z<700:
  origin,extent=a.get_actor_bounds(False)
  r['actors'].append({'name':n,'class':a.get_class().get_path_name(),'p':[p.x,p.y,p.z],'bounds':[extent.x,extent.y,extent.z],'folder':str(a.get_folder_path())})
for name in ('create_new_streaming_level','create_new_streaming_level_for_world','move_actors_to_level','remove_level_from_world','set_current_level_by_name'):
 f=getattr(unreal.EditorLevelUtils,name,None);r['level_api'][name]=str(getattr(f,'__doc__','missing'))
with open(os.path.join(unreal.Paths.project_saved_dir(),'corridor_live_inventory.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('CORRIDOR INVENTORY SAVED')
