import unreal,json,os
w=unreal.EditorLevelLibrary.get_game_world();pc=unreal.GameplayStatics.get_player_controller(w,0);cam=unreal.GameplayStatics.get_player_camera_manager(w,0);r=[]
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if a.get_class().get_name()=='BP_InteractionFocus_C' and str(a.get_editor_property('FocusField'))=='FocusCabButton':
  target=a.get_actor_location();pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam.get_camera_location(),target));r.append({'target':str(target),'camera':str(cam.get_camera_location()),'focused':a.get_editor_property('bFocused')})
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'lift_panel_aim.json'),'w'),indent=2)
