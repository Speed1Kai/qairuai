"""Static editor photographs of the fitted room, without running gameplay."""
import unreal,time,os
ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if ed.get_editor_world().get_name()!='Lvl_LabTutorial':unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
frames=[('ScientificLab_Installed.png',(620,-720,210),(-400,530,240)),('ScientificLab_Exit.png',(-260,400,190),(850,0,190))]
s={'i':0,'requested':False,'since':time.monotonic(),'old':0}
def sci_installed_photo(dt):
 name,eye,target=frames[s['i']];path=os.path.abspath(unreal.Paths.project_saved_dir()+name)
 if not s['requested']:
  ed.set_level_viewport_camera_info(unreal.Vector(*eye),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye),unreal.Vector(*target)))
  unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
  if time.monotonic()-s['since']>8:
   s['old']=os.path.getmtime(path) if os.path.exists(path) else 0;s['requested']=True
   unreal.AutomationLibrary.take_high_res_screenshot(1440,900,path,delay=0.)
 if s['requested'] and os.path.exists(path) and os.path.getmtime(path)>s['old']:
  s['i']+=1
  if s['i']==len(frames):unreal.unregister_slate_post_tick_callback(s['handle'])
  else:s.update(requested=False,since=time.monotonic())
s['handle']=unreal.register_slate_post_tick_callback(sci_installed_photo)
