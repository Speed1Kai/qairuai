"""Capture the authored gate approach; no gameplay session is started."""
import unreal,os,time
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
path=os.path.abspath(unreal.Paths.project_saved_dir()+'CampusPerimeter_Wall.png')
photo={'since':time.monotonic(),'requested':False,'old':os.path.getmtime(path) if os.path.exists(path) else 0}
def perimeter_art_tick(dt):
 if not photo['requested']:
  eye=unreal.Vector(-6500,13600,350);target=unreal.Vector(-6100,15300,250)
  editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,target))
  unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
  if time.monotonic()-photo['since']>5:
   photo['requested']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,path,delay=0.)
 if photo['requested'] and os.path.exists(path) and os.path.getmtime(path)>photo['old']:
  unreal.unregister_slate_post_tick_callback(photo['handle'])
  unreal.EditorLoadingAndSavingUtils.load_map('/Game/Cinematics/Prologue/Lvl_Prologue')
photo['handle']=unreal.register_slate_post_tick_callback(perimeter_art_tick)
