"""PIE-only actual lift travel test; only the initial boarding position is set."""
import unreal,time,json,os,traceback
try:unreal.unregister_slate_post_tick_callback(liftcheck['handle'])
except:pass
liftcheck={'start':time.monotonic(),'stage':'waiting','samples':[],'passed_up':False,'passed_down':False}
def write():json.dump({k:v for k,v in liftcheck.items() if k not in ('handle','pawn')},open(os.path.join(unreal.Paths.project_saved_dir(),'full_lift_ride_test.json'),'w'),indent=2)
def check(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  p=unreal.GameplayStatics.get_player_character(w,0)
  if not p:return
  now=time.monotonic()
  if liftcheck['stage']=='waiting':
   if now-liftcheck['start']<23:return
   p.set_actor_location(unreal.Vector(2650,0,107.15),False,True);pc=unreal.GameplayStatics.get_player_controller(w,0);pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);pc.set_control_rotation(unreal.Rotator(yaw=0));liftcheck.update(stage='ready',pawn=p)
  if now-liftcheck.get('last',0)<.5:return
  liftcheck['last']=now
  a=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_FreightElevatorBidirectional_C');pos=p.get_actor_location();floor=a.get_editor_property('CurrentFloor');state=a.get_editor_property('LiftState')
  sample={'z':pos.z,'x':pos.x,'floor':floor,'state':state,'cabin_z':a.get_editor_property('CabinRoot').get_world_location().z,'obstructions':[]}
  for x,y in [(2450,0),(2650,0),(2800,0),(2650,140),(2650,-140)]:
   h=unreal.SystemLibrary.line_trace_single(w,unreal.Vector(x,y,1000),unreal.Vector(x,y,2700),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[p,a],unreal.DrawDebugTrace.NONE,False)
   if h:sample['obstructions'].append(h.export_text())
  liftcheck['samples'].append(sample)
  if floor==1 and state==0 and pos.z>2200:
   liftcheck.update(passed_up=True,stage='upper_ready')
  if liftcheck['passed_up'] and floor==0 and state==0 and pos.z<160:
   liftcheck.update(passed_down=True,stage='passed');write();unreal.unregister_slate_post_tick_callback(liftcheck['handle']);return
  write()
 except Exception:liftcheck['error']=traceback.format_exc();write();unreal.unregister_slate_post_tick_callback(liftcheck['handle'])
liftcheck['handle']=unreal.register_slate_post_tick_callback(check)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
