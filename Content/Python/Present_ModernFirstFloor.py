"""Static environment art captures only; no PIE, no save, no actor gameplay."""
import unreal,os,time,traceback
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
folder='S:/Final_Protocol/Saved/ModernFirstFloorPreview';os.makedirs(folder,exist_ok=True)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
for command in ('t.MaxFPS 20','r.ScreenPercentage 75','r.Streaming.PoolSize 1000'):
 unreal.SystemLibrary.execute_console_command(world,command)
frames=[('ServerCore.png',(3980,-140,2335),(4670,530,2320)),('MainHall.png',(5170,-110,2335),(5830,680,2335))]
stage=0;last=time.monotonic();busy=False;positioned=False
def tick(dt):
 global stage,last,busy,positioned
 if busy:return
 busy=True
 try:
  if time.monotonic()-last<10:return
  last=time.monotonic()
  if stage>=len(frames):
   unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor();return
  name,eye,target=frames[stage]
  if not positioned:
   editor.set_level_viewport_camera_info(unreal.Vector(*eye),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye),unreal.Vector(*target)));positioned=True
  else:
   unreal.AutomationLibrary.take_high_res_screenshot(1280,720,os.path.join(folder,name),delay=1.);stage+=1;positioned=False
 except Exception:
  with open(os.path.join(folder,'error.txt'),'w') as f:f.write(traceback.format_exc())
  unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
 finally:busy=False
handle=unreal.register_slate_post_tick_callback(tick)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
