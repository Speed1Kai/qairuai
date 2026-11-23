"""Restore the laboratory and verify the city enemies inside the actual streamed game."""
import unreal,os,json,time,traceback,hashlib
S=os.path.abspath(unreal.Paths.project_saved_dir());R={'stage':'starting','passed':False};H={};started=time.monotonic()
assert not unreal.EditorLevelLibrary.get_game_world()
import runpy
runpy.run_path(os.path.join(os.path.dirname(__file__),'Place_ConnectedCityCombat.py'))
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor.set_level_viewport_camera_info(unreal.Vector(x=-200,y=-300,z=210),unreal.Rotator(pitch=-4,yaw=130,roll=0));levels.editor_set_game_view(True)
def write():json.dump(R,open(os.path.join(S,'citycombat_main_game.json'),'w'),indent=2)
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  t=unreal.SystemLibrary.get_game_time_in_seconds(w);p=unreal.GameplayStatics.get_player_character(w,0)
  if time.monotonic()-started>100:raise RuntimeError('Main game verification timeout')
  if not p:return
  if R['stage']=='starting':
   R.update(stage='intro',initial_player=str(p.get_actor_location()));write();return
  if R['stage']=='intro':
   if t<29:return
   enemies=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Character) if a.get_class().get_name().startswith('BP_Enceladus_')]
   if len(enemies)!=6:
    if not R.get('stream_triggered'):
     p.set_actor_location(unreal.Vector(x=-140,y=0,z=2300),False,True);R['stream_triggered']=True;write()
    return
   enemies.sort(key=lambda n:n.get_actor_location().y);n=enemies[0];q=n.get_actor_location();pc=p.get_controller();pc.reset_ignore_move_input();pc.reset_ignore_look_input()
   p.set_actor_location(q+unreal.Vector(x=0,y=-1400,z=5),False,True);pc.set_control_rotation(unreal.Rotator(pitch=-3,yaw=90,roll=0))
   H.update(player=p,enemy=n);R.update(stage='observe',since=t,npc_start=[q.x,q.y,q.z],health_before=p.get_editor_property('VisorIntegrity'),shots_before=n.get_editor_property('CityShotCount'));write();return
  if R['stage']=='observe':
   if t-R['since']<3.5:return
   n=H['enemy'];q=n.get_actor_location();path=unreal.NavigationSystemV1.find_path_to_actor_synchronously(w,q,p,pathfinding_context=n)
   R['checks']={'normal_lab_start':True,'six_npcs_in_streamed_city':True,'navigation_valid_in_full_game':bool(path and path.is_valid()),'pursuit_in_full_game':R['npc_start'][1]-q.y>100,'fired_in_full_game':n.get_editor_property('CityShotCount')>R['shots_before'],'player_damaged_in_full_game':p.get_editor_property('VisorIntegrity')<R['health_before']}
   R.update(stage='done',passed=all(R['checks'].values()),npc_end=[q.x,q.y,q.z],health_after=p.get_editor_property('VisorIntegrity'));write();unreal.unregister_slate_post_tick_callback(H['handle']);levels.editor_request_end_play()
 except Exception:
  R.update(stage='failed',error=traceback.format_exc());write();unreal.unregister_slate_post_tick_callback(H['handle']);levels.editor_request_end_play()
H['handle']=unreal.register_slate_post_tick_callback(tick);write();levels.editor_request_begin_play()

