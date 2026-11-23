"""Static editor photographs of the authored street, without starting gameplay."""
import unreal,os,time,json
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_editor_world().get_name()!='Lvl_SurfaceArrival':unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
shots=[('DowntownFirstBlock_Street.png',(0,25200,235),(80,29600,1150)),
       ('DowntownFirstBlock_Overview.png',(8500,22400,7000),(0,29300,1300))]
photo={'index':0,'requested':False,'since':time.monotonic(),'old':0}
def block_art_tick(dt):
 name,eye,target=shots[photo['index']];path=os.path.abspath(unreal.Paths.project_saved_dir()+name)
 if not photo['requested']:
  editor.set_level_viewport_camera_info(unreal.Vector(*eye),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye),unreal.Vector(*target)))
  unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
  if time.monotonic()-photo['since']>7:
   photo['old']=os.path.getmtime(path) if os.path.exists(path) else 0
   photo['requested']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,path,delay=0.)
 if photo['requested'] and os.path.exists(path) and os.path.getmtime(path)>photo['old']:
  photo['index']+=1
  if photo['index']==len(shots):
   unreal.unregister_slate_post_tick_callback(photo['handle'])
   unreal.EditorLoadingAndSavingUtils.load_map('/Game/Cinematics/Prologue/Lvl_Prologue')
  else:photo.update(requested=False,since=time.monotonic())
photo['handle']=unreal.register_slate_post_tick_callback(block_art_tick)
