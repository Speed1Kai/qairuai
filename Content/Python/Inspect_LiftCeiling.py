import unreal,json,os
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pos=p.get_actor_location();r={'player':str(pos),'traces':[]}
ignore=[p]+[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_FreightElevatorBidirectional_C']
for x,y in [(pos.x,pos.y),(2650,0),(2450,0),(2800,0),(2650,150),(2650,-150)]:
 hit=unreal.SystemLibrary.line_trace_single(w,unreal.Vector(x,y,1600),unreal.Vector(x,y,3000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,unreal.DrawDebugTrace.NONE,False)
 r['traces'].append({'x':x,'y':y,'hit':hit.export_text() if hit else 'clear'})
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'lift_ceiling.json'),'w'),indent=2)
