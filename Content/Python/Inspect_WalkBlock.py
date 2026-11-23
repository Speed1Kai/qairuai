import unreal,json,os
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pos=p.get_actor_location();r={'pos':str(pos),'near':[]}
hit=unreal.SystemLibrary.line_trace_single(w,pos,pos+unreal.Vector(1200,0,0),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[p],unreal.DrawDebugTrace.NONE,False);r['hit']=hit.export_text() if hit else 'clear'
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if a.get_distance_to(p)>600:continue
 cls=a.get_class().get_path_name();d={'name':a.get_name(),'cls':cls,'pos':str(a.get_actor_location()),'vars':{}}
 if cls.startswith('/Game/'):
  bp=unreal.EditorAssetLibrary.load_asset(cls.split('.')[0])
  for n in unreal.BlueprintEditorLibrary.list_member_variable_names(bp):
   try:d['vars'][str(n)]=str(a.get_editor_property(str(n)))
   except:pass
 r['near'].append(d)
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'walk_block.json'),'w'),indent=2)
