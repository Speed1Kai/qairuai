import unreal,json,os,time
ride={'start':time.monotonic(),'samples':[]}
def observe(dt):
 w=unreal.EditorLevelLibrary.get_game_world()
 if not w:return
 p=unreal.GameplayStatics.get_player_character(w,0)
 if not p:return
 now=time.monotonic()
 if now-ride.get('last',0)<.5:return
 ride['last']=now
 lifts=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_FreightElevatorBidirectional_C']
 sample={'p':str(p.get_actor_location()),'lift':[],'hits':[]}
 for a in lifts:
  sample['lift'].append({n:str(a.get_editor_property(n)) for n in ('CurrentFloor','TargetFloor','LiftState')});sample['lift'][-1]['cabin']=str(a.get_editor_property('CabinRoot').get_world_location())
 for x,y in [(2450,0),(2650,0),(2800,0),(2650,140),(2650,-140)]:
  h=unreal.SystemLibrary.line_trace_single(w,unreal.Vector(x,y,1000),unreal.Vector(x,y,2700),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[p]+lifts,unreal.DrawDebugTrace.NONE,False)
  if h:sample['hits'].append(h.export_text())
 ride['samples'].append(sample);json.dump({k:v for k,v in ride.items() if k!='handle'},open(os.path.join(unreal.Paths.project_saved_dir(),'lift_ride_watch.json'),'w'),indent=2)
 if now-ride['start']>90:unreal.unregister_slate_post_tick_callback(ride['handle'])
ride['handle']=unreal.register_slate_post_tick_callback(observe)
