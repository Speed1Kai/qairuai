import unreal,time,os,json
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);p.set_actor_location(unreal.Vector(2650,0,2259.65),False,True)
probe={'t':time.monotonic()}
def collect(dt):
 if time.monotonic()-probe['t']<4:return
 ignore=[p]+[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_FreightElevatorBidirectional_C'];r={'p':str(p.get_actor_location()),'hits':[]}
 for x,y in [(2450,0),(2650,0),(2800,0),(2650,140),(2650,-140)]:
  h=unreal.SystemLibrary.line_trace_single(w,unreal.Vector(x,y,1000),unreal.Vector(x,y,2700),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,unreal.DrawDebugTrace.NONE,False)
  r['hits'].append(h.export_text() if h else 'clear')
 r['ground_transforms']=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
  if a.get_class().get_name()!='BP_ConnectedLaboratoryCampus_C':continue
  for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
   if c.get_name() not in ('Box_M_Dust_Block','Box_M_LabFloor_Block'):continue
   r['ground_transforms'].append({'name':c.get_name(),'location':str(c.get_world_location()),'rotation':str(c.get_world_rotation()),'scale':str(c.get_world_scale()),'instances':[{'local':str(c.get_instance_transform(i,False)),'world':str(c.get_instance_transform(i,True))} for i in range(c.get_instance_count())]})
 json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'upper_shaft_probe.json'),'w'),indent=2);unreal.unregister_slate_post_tick_callback(probe['handle'])
probe['handle']=unreal.register_slate_post_tick_callback(collect)
