import unreal
assert not unreal.EditorLevelLibrary.get_game_world()
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert editor.get_editor_world().get_name()=='Lvl_LabTutorial'
editor.set_level_viewport_camera_info(unreal.Vector(x=-200,y=-300,z=210),unreal.Rotator(pitch=-4,yaw=130,roll=0))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
