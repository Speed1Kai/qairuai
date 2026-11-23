import unreal
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0)
p.mesh.set_relative_rotation(unreal.Rotator(yaw=247.5),False,False)
p.set_editor_property('FirstPersonDownForward',24.)
p.get_editor_property('FirstPersonCamera').set_field_of_view(100.)

