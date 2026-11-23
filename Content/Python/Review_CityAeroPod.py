import unreal,os,json
assert not unreal.EditorLevelLibrary.get_game_world()
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
pod=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='CITY_LunarAeroPod')
p,e=pod.get_actor_bounds(False)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(x=p.x-750,y=p.y-650,z=p.z+330),unreal.Rotator(pitch=-15,yaw=42,roll=0))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
