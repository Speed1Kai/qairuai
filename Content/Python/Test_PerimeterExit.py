"""Editor-only swept-capsule regression check; never changes saved player spawn."""
import unreal,time,json,os,traceback,math
walk={'t':time.monotonic(),'stage':'waiting','passed':False,'positions':[],'last_record':0}
out=os.path.join(unreal.Paths.project_saved_dir(),'perimeter_exit_regression.json')
def record():json.dump({k:v for k,v in walk.items() if k not in ('handle','pawn','exit')},open(out,'w'),indent=2)
def step(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  p=unreal.GameplayStatics.get_player_character(w,0)
  if not p:return
  elapsed=time.monotonic()-walk['t']
  if elapsed>145:raise RuntimeError('Walk timed out at '+str(p.get_actor_location()))
  if walk['stage']=='waiting':
   if elapsed<23:return
   p.set_actor_location(unreal.Vector(5850,1050,2259.65),False,True)
   walk.update(pawn=p,identity=p.get_path_name(),stage='walking',index=0,targets=[(5850,1080)],start=time.monotonic())
   pc=unreal.GameplayStatics.get_player_controller(w,0);pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0)
  pos=p.get_actor_location()
  if elapsed-walk['last_record']>1:walk['last_record']=elapsed;walk['positions'].append([round(pos.x,1),round(pos.y,1),round(pos.z,1)]);record()
  if walk['stage']=='walking':
   target=walk['targets'][walk['index']];dx=target[0]-pos.x;dy=target[1]-pos.y;d=math.hypot(dx,dy)
   if d<12:
    walk['index']+=1
    if walk['index']==len(walk['targets']):
     a=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_SurfaceDeparture_C');walk.update(stage='at_button',exit=a,arrived=time.monotonic());pc=unreal.GameplayStatics.get_player_controller(w,0);pc.set_control_rotation(unreal.Rotator(yaw=90));record()
    return
   amount=min(d,240*min(dt,.05));p.set_actor_location(unreal.Vector(pos.x+dx/d*amount,pos.y+dy/d*amount,2259.65),True,False)
  elif walk['stage']=='at_button':
   a=walk['exit'];walk['door_requested']=bool(a.get_editor_property('bOpenRequested'));walk['door_amount']=a.get_editor_property('ExitDoorAmount');record()
   if walk['door_amount']>.99:walk.update(stage='outward',index=0,targets=[(5850,2000),(5850,2300)])
  elif walk['stage'] in ('outward','returning'):
   target=walk['targets'][walk['index']];dx=target[0]-pos.x;dy=target[1]-pos.y;d=math.hypot(dx,dy)
   if d<12:
    walk['index']+=1
    if walk['index']==len(walk['targets']):
     if walk['stage']=='outward':walk.update(stage='returning',index=0,targets=[(5850,1080)],outdoor_reached=True)
     else:
      walk.update(stage='passed',passed=p.get_path_name()==walk['identity']);record();unreal.unregister_slate_post_tick_callback(walk['handle'])
    return
   amount=min(d,240*min(dt,.05));p.set_actor_location(unreal.Vector(pos.x+dx/d*amount,pos.y+dy/d*amount,2259.65),True,False)
 except Exception:
  walk['error']=traceback.format_exc();record();unreal.unregister_slate_post_tick_callback(walk['handle'])
walk['handle']=unreal.register_slate_post_tick_callback(step)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()

