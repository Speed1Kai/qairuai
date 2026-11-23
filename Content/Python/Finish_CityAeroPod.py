import unreal,runpy,os
assert not unreal.EditorLevelLibrary.get_game_world()
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
runpy.run_path(os.path.join(os.path.dirname(__file__),'Present_RestoredLab.py'),run_name='__main__')
