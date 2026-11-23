"""Export an editor artwork frame and restore the laboratory startup map."""
import unreal,time,os,traceback
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor.set_level_viewport_camera_info(unreal.Vector(0,28300,210),unreal.Rotator(pitch=12,yaw=90))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
residential_photo={'since':time.monotonic(),'captured':False}
def residential_photo_tick(dt):
 try:
  elapsed=time.monotonic()-residential_photo['since']
  if elapsed>4 and not residential_photo['captured']:
   residential_photo['captured']=True
   unreal.AutomationLibrary.take_high_res_screenshot(1440,900,'S:/Final_Protocol/Saved/ResidentialDistrict.png',delay=1.)
  if elapsed>10:
   unreal.unregister_slate_post_tick_callback(residential_photo['handle'])
   unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
   eye=unreal.Vector(-200,-300,210)
   editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,unreal.Vector(-416,306,160)))
 except Exception:
  unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(residential_photo['handle'])
  unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
residential_photo['handle']=unreal.register_slate_post_tick_callback(residential_photo_tick)
