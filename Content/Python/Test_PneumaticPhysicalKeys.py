"""Observe a real native D+Space chord; no synthetic action or ability calls."""
import unreal,os,time,json,traceback
w=unreal.EditorLevelLibrary.get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_control_rotation(unreal.Rotator(pitch=-8,yaw=0,roll=0));p.set_actor_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0),True);p.character_movement.stop_movement_immediately()
q=p.get_actor_location();P={'start':time.monotonic(),'initial':[q.x,q.y,q.z],'initial_count':p.get_editor_property('PneumaticDashCount'),'initial_presses':p.get_editor_property('AirJetInputPresses'),'samples':[],'stage':'waiting_for_physical_keys'}
path=os.path.join(unreal.Paths.project_saved_dir(),'pneumatic_physical_keys.json')
def write():json.dump({k:v for k,v in P.items() if k!='handle'},open(path,'w'),indent=2)
def tick(dt):
 try:
  if not unreal.EditorLevelLibrary.get_game_world():unreal.unregister_slate_post_tick_callback(P['handle']);return
  if time.monotonic()-P['start']>80:
   P['stage']='timeout';write();unreal.unregister_slate_post_tick_callback(P['handle']);return
  count=p.get_editor_property('PneumaticDashCount')-P['initial_count'];q=p.get_actor_location();active=bool(p.get_editor_property('bPneumaticDash'))
  if count:
   P['stage']='recording';P['samples'].append(dict(t=time.monotonic()-P['start'],x=q.x,y=q.y,z=q.z,active=active,direction=str(p.get_editor_property('PneumaticDirection'))))
   if False and active and not P.get('captured'):
    P['captured']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,os.path.join(unreal.Paths.project_saved_dir(),'Pneumatic_RightDash.png'),delay=0.)
   if not active and len(P['samples'])>3:
    P['stage']='done';P['dash_count']=count;P['physical_press_count']=p.get_editor_property('AirJetInputPresses')-P['initial_presses'];P['displacement']=[q.x-P['initial'][0],q.y-P['initial'][1],q.z-P['initial'][2]]
    P['checks']={'physical_action_received':P['physical_press_count']>=1,'one_dodge':count==1,'moved_right':P['displacement'][1]>200,'no_lift':abs(P['displacement'][2])<1};P['passed']=all(P['checks'].values());write();unreal.unregister_slate_post_tick_callback(P['handle']);return
  if P['stage']!='waiting_for_physical_keys':write()
 except Exception:
  P['stage']='failed';P['error']=traceback.format_exc();write();unreal.unregister_slate_post_tick_callback(P['handle'])
P['handle']=unreal.register_slate_post_tick_callback(tick);write()
