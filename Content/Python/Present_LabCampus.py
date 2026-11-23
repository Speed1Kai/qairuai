"""Static campus artwork export; always return editor to the awakening map."""
import unreal,os,time,traceback
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
editor.set_level_viewport_camera_info(unreal.Vector(-21000,-18000,17500),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(-21000,-18000,17500),unreal.Vector(0,6000,400)))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
campus_photo={'since':time.monotonic(),'captured':False}
def campus_photo_tick(dt):
 try:
  elapsed=time.monotonic()-campus_photo['since']
  if elapsed>5 and not campus_photo['captured']:
   campus_photo['captured']=True;unreal.AutomationLibrary.take_high_res_screenshot(1280,800,'S:/Final_Protocol/Saved/LaboratoryCampus_Overview.png',delay=1.)
  if elapsed>10:
   unreal.unregister_slate_post_tick_callback(campus_photo['handle'])
   unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
   editor.set_level_viewport_camera_info(unreal.Vector(-200,-300,210),unreal.Rotator(pitch=-4,yaw=130))
 except Exception:
  unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(campus_photo['handle'])
  unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
campus_photo['handle']=unreal.register_slate_post_tick_callback(campus_photo_tick)
