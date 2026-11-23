"""Observe real V key switches and move forward after each return to third person."""
import unreal,time,json,os,traceback,math
state={'start':time.monotonic(),'stage':'waiting','last_mode':None,'switches':[],'movement':[],'sample':0,'tested_returns':0};out=os.path.join(unreal.Paths.project_saved_dir(),'view_switch_regression.json')
def record():json.dump({k:v for k,v in state.items() if k!='handle'},open(out,'w'),indent=2)
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  p=unreal.GameplayStatics.get_player_character(w,0)
  if not p:return
  pc=unreal.GameplayStatics.get_player_controller(w,0);now=time.monotonic();elapsed=now-state['start']
  if state['stage']=='waiting':
   if elapsed<23:return
   p.set_actor_location(unreal.Vector(4400,0,2259.65),False,True);p.set_actor_rotation(unreal.Rotator(yaw=90),True);pc.set_control_rotation(unreal.Rotator(yaw=90));pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);state['stage']='ready'
  mode=bool(p.get_editor_property('bFirstPerson'));cm=p.get_component_by_class(unreal.CharacterMovementComponent);yaw=p.mesh.get_relative_transform().rotation.rotator().yaw
  if mode!=state['last_mode']:
   state['switches'].append({'first_person':mode,'mesh_yaw':yaw,'correction':p.get_editor_property('FirstPersonBodyYawCorrection'),'orient_to_movement':cm.get_editor_property('orient_rotation_to_movement'),'controller_yaw':p.get_editor_property('use_controller_rotation_yaw')});prev=state['last_mode'];state['last_mode']=mode
   if mode:pc.set_control_rotation(unreal.Rotator(pitch=-35,yaw=pc.get_control_rotation().yaw+55))
   elif prev is True:state['move_until']=now+1.3;state['move_start']=now;state['tested_returns']+=1
   record()
  if not mode and now<state.get('move_until',0):
   p.add_movement_input(unreal.Vector(0,1,0),1.,True)
   if now-state['move_start']>.6 and now-state['sample']>.15:
    state['sample']=now;v=p.get_velocity();a=p.get_actor_rotation().yaw;vy=math.degrees(math.atan2(v.y,v.x));state['movement'].append({'mesh_yaw':yaw,'yaw_error':abs((a-vy+180)%360-180),'speed':math.hypot(v.x,v.y)});record()
  if state['tested_returns']>=3 and now>state.get('move_until',0):
   state['stage']='passed' if all(abs(s['mesh_yaw']+90)<.01 and s['orient_to_movement'] and not s['controller_yaw'] for s in state['switches'] if not s['first_person']) else 'failed';record();unreal.unregister_slate_post_tick_callback(state['handle'])
 except:
  state['error']=traceback.format_exc();record();unreal.unregister_slate_post_tick_callback(state['handle'])
state['handle']=unreal.register_slate_post_tick_callback(tick)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
