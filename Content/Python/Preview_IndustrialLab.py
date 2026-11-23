"""Bounded rendered preview of saved assets. Does not save editor changes."""
import unreal,os,time,json,traceback
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
sub.editor_set_game_view(True)
folder='S:/Final_Protocol/Saved/IndustrialPreview';os.makedirs(folder,exist_ok=True)
unreal.log('INDUSTRIAL PREVIEW FOLDER '+folder+' CWD '+os.getcwd())
world=unreal.EditorLevelLibrary.get_editor_world()
for command in ('t.MaxFPS 30','r.ScreenPercentage 100','r.TextureStreaming 1','r.Streaming.PoolSize 1200'):
 unreal.SystemLibrary.execute_console_command(world,command)
frames=[('Laboratory.png',(360,-560,225),(-330,480,145)),('Capsule45.png',(-230,-40,190),(-650,540,155)),('BlastDoor.png',(1100,-100,205),(1450,0,220)),('Workbench.png',(-125,240,175),(-150,610,140))]
stage=0;started=time.monotonic();last=started;positioned=False;busy=False
def update(dt):
 global stage,last,positioned,busy
 if busy:return
 busy=True
 now=time.monotonic()
 try:
  if now-started<12 or now-last<4:return
  if stage>=len(frames):
   unreal.unregister_slate_post_tick_callback(handle)
   next_script='S:/Final_Protocol/Content/Python/Preview_IndustrialGameplay.py'
   exec(compile(open(next_script,encoding='utf8').read(),next_script,'exec'),{'__name__':'__main__'})
   return
  filename,p,t=frames[stage]
  if not positioned:
   positioned=True;last=now
   editor.set_level_viewport_camera_info(unreal.Vector(*p),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*p),unreal.Vector(*t)))
   return
  stage+=1;positioned=False;last=now
  result=unreal.AutomationLibrary.take_high_res_screenshot(1280,720,os.path.join(folder,filename),delay=1.)
  unreal.log('INDUSTRIAL CAPTURE '+filename+' '+str(result))
 except Exception:
  unreal.log_error(traceback.format_exc())
  with open(os.path.join(folder,'error.txt'),'w') as f:f.write(traceback.format_exc())
  unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
 finally:busy=False
handle=unreal.register_slate_post_tick_callback(update)
