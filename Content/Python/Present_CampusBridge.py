"""Capture the authored bridge only after its viewport has rendered."""
import unreal,os,time,json
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
path=os.path.abspath(unreal.Paths.project_saved_dir()+'CampusBrokenBridge_Overview.png')
photo={'since':time.monotonic(),'requested':False,'old_mtime':os.path.getmtime(path) if os.path.exists(path) else 0}
def bridge_art_tick(dt):
 elapsed=time.monotonic()-photo['since']
 if not photo['requested']:
  eye=unreal.Vector(1450,20700,650)
  editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,unreal.Vector(0,22700,-150)))
  unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
  if elapsed>4:
   photo['requested']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,path,delay=0.)
 if photo['requested'] and os.path.exists(path) and os.path.getmtime(path)>photo['old_mtime']:
  unreal.unregister_slate_post_tick_callback(photo['handle'])
  unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
photo['handle']=unreal.register_slate_post_tick_callback(bridge_art_tick)
