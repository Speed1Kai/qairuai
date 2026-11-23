import unreal,json,os,traceback
r={}
def prop(o,n):
 try:return str(o.get_editor_property(n))
 except:return None
try:
 w=unreal.EditorLevelLibrary.get_game_world();r['world']=str(w)
 p=unreal.GameplayStatics.get_player_character(w,0);cam=unreal.GameplayStatics.get_player_camera_manager(w,0)
 r.update(player=str(p.get_actor_location()),camera=str(cam.get_camera_location()),rotation=str(cam.get_camera_rotation()))
 start=cam.get_camera_location();end=start+unreal.MathLibrary.get_forward_vector(cam.get_camera_rotation())*3000
 r['traces']=[]
 for channel in (unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,unreal.TraceTypeQuery.TRACE_TYPE_QUERY2):
  hit=unreal.SystemLibrary.line_trace_single(w,start,end,channel,True,[p],unreal.DrawDebugTrace.NONE,False)
  r['traces'].append(hit.export_text() if hit else 'clear')
 r['exits']=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
  if a.get_class().get_name()=='BP_SurfaceDeparture_C':
   d={'actor':str(a),'loc':str(a.get_actor_location()),'vars':{n:prop(a,n) for n in ('bNear','bOpenRequested','bExitOpen','ExitDoorAmount','CampusStreaming')},'components':[]}
   for c in a.get_components_by_class(unreal.SceneComponent):d['components'].append({'name':c.get_name(),'loc':str(c.get_world_location()),'scale':str(c.get_world_scale()),'mobility':prop(c,'mobility')})
   r['exits'].append(d)
except:r['error']=traceback.format_exc()
with open(os.path.join(unreal.Paths.project_saved_dir(),'exit_obstruction.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
