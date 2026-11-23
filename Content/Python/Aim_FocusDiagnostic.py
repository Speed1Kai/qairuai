"""Reproduce aim in the already-running PIE; preserve the player's original pose."""
import unreal,os,json
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
statefile=os.path.join(unreal.Paths.project_saved_dir(),'focus_original_pose.json')
if not os.path.isfile(statefile):
 v=p.get_actor_location();r=pc.get_control_rotation()
 with open(statefile,'w') as f:json.dump({'p':[v.x,v.y,v.z],'r':[r.pitch,r.yaw,r.roll]},f)
p.set_actor_location(unreal.Vector(130,210,107.15),False,True);pc.set_control_rotation(unreal.Rotator(pitch=-35.6,yaw=90))
started=unreal.SystemLibrary.get_game_time_in_seconds(w)
def collect(_):
 if unreal.SystemLibrary.get_game_time_in_seconds(w)-started<.6:return
 unreal.unregister_slate_post_tick_callback(handle)
 exec(compile(open(os.path.join(unreal.Paths.project_content_dir(),'Python/Inspect_FocusRuntime.py'),encoding='utf8').read(),'Inspect_FocusRuntime.py','exec'))
handle=unreal.register_slate_post_tick_callback(collect)
