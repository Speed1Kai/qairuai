"""Capture the saved capsule intro and automatic door in a disposable PIE world.
Only the preview pawn is moved; no asset or map is saved.
"""
import unreal,os,time,json,traceback
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
folder='S:/Final_Protocol/Saved/IndustrialPreview';os.makedirs(folder,exist_ok=True)
unreal.log('INDUSTRIAL GAMEPLAY PREVIEW '+folder)
started=time.monotonic();play_started=False;stage=0;mark=0;finishing=False;finish_time=0;samples=[];busy=False
def write():
 with open(os.path.join(folder,'GameplayObservations.json'),'w',encoding='utf8') as f:json.dump(samples,f,ensure_ascii=False,indent=2)
def capture(world,name):
 path=os.path.join(folder,name).replace('\\','/')
 unreal.SystemLibrary.execute_console_command(world,'HighResShot 1280x720 filename="'+path+'"')
def update(dt):
 global play_started,stage,mark,finishing,finish_time,busy
 if busy:return
 busy=True
 now=time.monotonic()
 try:
  if finishing:
   if sub.is_in_play_in_editor():sub.editor_request_end_play()
   elif now-finish_time>3:
    unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
   return
  if now-started>130:raise RuntimeError('Preview time limit')
  if not play_started:
   if now-started<18:return
   play_started=True;sub.editor_request_begin_play();return
  world=unreal.EditorLevelLibrary.get_game_world()
  if not world:return
  t=unreal.GameplayStatics.get_time_seconds(world)
  pawn=unreal.GameplayStatics.get_player_pawn(world,0);pc=unreal.GameplayStatics.get_player_controller(world,0)
  if not pawn or not pc:return
  actors={a.get_actor_label():a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)}
  door=actors.get('IND_HeavyBlastDoor')
  if not door:return
  panel=next(c for c in door.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='StaticMesh_DoorPanel')
  body=next(c for c in door.get_components_by_class(unreal.BoxComponent) if c.get_name()=='DoorPanelCollision')
  def observe(name):
   samples.append({'stage':name,'time':t,'door_panel_z':panel.get_editor_property('relative_location').z,'door_collision_z':8+panel.get_editor_property('relative_location').z+body.get_editor_property('relative_location').z,'collision_parent':body.get_attach_parent().get_name(),'pawn':str(pawn.get_actor_location()),'move_locked':pc.is_move_input_ignored(),'pawn_hidden':pawn.get_editor_property('hidden')});write()
  if stage in (0,1,2):
   thresholds=(2.8,6.4,10.8)
   if t<thresholds[stage]:return
   observe('capsule_'+str(stage));capture(world,'Intro_%02d.png'%stage);stage+=1;return
  if stage==3:
   if t<12:return
   pawn.set_actor_location(unreal.Vector(1100,0,100),False,True);pc.set_control_rotation(unreal.Rotator(pitch=-5,yaw=0,roll=0));observe('door_closed');mark=t;stage=4;return
  if stage==4:
   if t-mark<1.2:return
   pawn.set_actor_location(unreal.Vector(1250,0,100),False,True);mark=t;stage=5;return
  if stage==5:
   if t-mark<.7:return
   observe('door_opening');stage=6;return
  if stage==6:
   if t-mark<1.8:return
   observe('door_open');capture(world,'Door_Open.png');mark=t;stage=7;return
  if stage==7:
   if t-mark<1.2:return
   pawn.set_actor_location(unreal.Vector(1900,0,100),False,True);mark=t;stage=8;return
  if stage==8:
   if t-mark<1.8:return
   observe('door_closed_after_exit');finishing=True;finish_time=now
 except Exception:
  samples.append({'error':traceback.format_exc()});write();finishing=True;finish_time=now
 finally:busy=False
handle=unreal.register_slate_post_tick_callback(update)
