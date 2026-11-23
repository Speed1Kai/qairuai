"""Read current PIE lift state without changing gameplay."""
import unreal, json, os
r={}
def read(o,n):
 try:return str(o.get_editor_property(n))
 except Exception as e:return str(e)
w=unreal.EditorLevelLibrary.get_game_world()
r['world']=str(w)
if w:
 p=unreal.GameplayStatics.get_player_character(w,0)
 r['player']=str(p);r['player_location']=str(p.get_actor_location()) if p else None
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
  if 'FreightElevator' not in a.get_class().get_name():continue
  q={'actor':str(a),'class':a.get_class().get_path_name()}
  for n in ['LiftState','CurrentFloor','TargetFloor','bCloseAborted','RideStartZ','RideTargetZ','auto_receive_input','input_priority','input_component']:q[n]=read(a,n)
  q['components']=[]
  for c in a.get_components_by_class(unreal.ActorComponent):
   d={'name':c.get_name(),'class':c.get_class().get_name()}
   if isinstance(c,unreal.SceneComponent):d['relative_location']=read(c,'relative_location')
   if isinstance(c,unreal.PrimitiveComponent):d['overlap_player']=c.is_overlapping_actor(p) if p else False
   if isinstance(c,unreal.TimelineComponent):d.update(position=c.get_playback_position(),playing=c.is_playing())
   q['components'].append(d)
  r.setdefault('lifts',[]).append(q)
with open(os.path.join(unreal.Paths.project_saved_dir(),'lift_live_diagnostic.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('Lift live diagnostic saved')
