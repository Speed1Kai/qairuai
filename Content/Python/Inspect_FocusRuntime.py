import unreal,os,json
r={};w=unreal.EditorLevelLibrary.get_game_world();r['world']=str(w)
def prop(o,n):
 try:return str(o.get_editor_property(n))
 except Exception as e:return str(e)
if w:
 p=unreal.GameplayStatics.get_player_character(w,0);c=unreal.GameplayStatics.get_player_camera_manager(w,0)
 r.update(player=str(p.get_actor_location()),camera=str(c.get_camera_location()),rotation=str(c.get_camera_rotation()))
 try:
  start=c.get_camera_location();end=start+unreal.MathLibrary.get_forward_vector(c.get_camera_rotation())*1000
  hit=unreal.SystemLibrary.line_trace_single(w,start,end,unreal.TraceTypeQuery.TRACE_TYPE_QUERY2,False,[p],unreal.DrawDebugTrace.NONE,False)
  r['hit_doc']=unreal.HitResult.__doc__;r['hit_methods']=dir(hit)
  r['hit_export']=hit.export_text()
  hit2=unreal.SystemLibrary.line_trace_single(w,start,end,unreal.TraceTypeQuery.ECC_CAMERA,False,[],unreal.DrawDebugTrace.NONE,False)
  r['without_player_ignore']=hit2.export_text()
  r['trace']={}
  for field in ['blocking_hit','actor','hit_actor','component','hit_component','distance','impact_point','location']:
   r['trace'][field]=prop(hit,field)
 except Exception as e:r['trace_error']=str(e)
 r['focus']=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
  if a.get_class().get_name()!='BP_InteractionFocus_C':continue
  d={'name':a.get_name(),'p':str(a.get_actor_location()),'tick':a.is_actor_tick_enabled(),'bFocused':prop(a,'bFocused'),'Device':prop(a,'Device'),'field':prop(a,'FocusField')}
  for comp in a.get_components_by_class(unreal.BoxComponent):d.update(box=str(comp.get_world_location()),extent=str(comp.get_scaled_box_extent()),collision=str(comp.get_collision_enabled()),camera_response=str(comp.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA)))
  r['focus'].append(d)
with open(os.path.join(unreal.Paths.project_saved_dir(),'focus_runtime.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
