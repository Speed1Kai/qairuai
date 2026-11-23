import unreal,time,os,json,traceback
try:unreal.unregister_slate_post_tick_callback(check['handle'])
except:pass
visual={'start':time.monotonic(),'ready':False}
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
  if time.monotonic()-visual['start']<23:return
  if not p:return
  if not visual['ready']:
   p.set_actor_location(unreal.Vector(5850,1080,2259.65),False,True);p.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately();pc.set_control_rotation(unreal.Rotator(yaw=90));pc.set_view_target_with_blend(p,0)
   exits=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_SurfaceDeparture_C']
   if exits:
    stream=exits[0].get_editor_property('CampusStreaming')
    if stream and stream.is_level_visible():
     visual['ready']=True
     p.set_actor_location(unreal.Vector(5850,3500,2259.65),False,True)
     for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
      if a.get_class().get_name()=='BP_SurfaceArrival_C':a.call_method('PreviewCampusNotice')
  visual['player']=str(p.get_actor_location())
  for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
   if a.get_class().get_name()=='BP_CampusReadability_C':visual['blend']=a.get_component_by_class(unreal.PostProcessComponent).get_editor_property('blend_weight')
  json.dump({k:v for k,v in visual.items() if k!='handle'},open(os.path.join(unreal.Paths.project_saved_dir(),'campus_final_visual.json'),'w'),indent=2)
  if visual['ready']:unreal.unregister_slate_post_tick_callback(visual['handle'])
 except:
  unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(visual['handle'])
visual['handle']=unreal.register_slate_post_tick_callback(tick)

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()

