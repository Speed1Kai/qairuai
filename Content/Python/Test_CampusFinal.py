"""PIE-only visual and collision check; saved player spawn is never changed."""
import unreal,time,math,json,os,traceback
check={'start':time.monotonic(),'stage':'wait'}
def write():json.dump({k:v for k,v in check.items() if k!='handle'},open(os.path.join(unreal.Paths.project_saved_dir(),'campus_readability_test.json'),'w'),ensure_ascii=False,indent=2)
def step(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  p=unreal.GameplayStatics.get_player_character(w,0)
  if not p:return
  t=time.monotonic()-check['start'];pc=unreal.GameplayStatics.get_player_controller(w,0)
  if t>23 and check['stage']=='wait':
   p.set_actor_location(unreal.Vector(5850,2500,2259.65),False,True);pc.set_control_rotation(unreal.Rotator(yaw=90));pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);check['stage']='courtyard';write()
  if t>32 and check['stage']=='courtyard':
   for actor in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
    if actor.get_class().get_name()=='BP_SurfaceArrival_C':actor.call_method('PreviewCampusNotice')
   check['stage']='notice'
  if t>100 and check['stage']=='notice':
   a=math.radians(49.08561677997487);normal=unreal.Vector(-math.sin(a),math.cos(a),0);center=unreal.Vector(10006.289955-17050*math.sin(a),6612.598659+17050*math.cos(a),2259.65)
   p.set_actor_location(center-normal*650,False,True);pc.set_control_rotation(unreal.Rotator(yaw=139.08561678));check.update(stage='gate',center=[center.x,center.y],normal=[normal.x,normal.y],gate_started=t);write()
  if check['stage']=='gate' and t-check['gate_started']>4:
   q=p.get_actor_location();n=unreal.Vector(*check['normal'],0);p.set_actor_location(q+n*3000,True,False);q=p.get_actor_location();center=unreal.Vector(*check['center'],q.z);distance=unreal.MathLibrary.dot_vector_vector(q-center,n);check.update(stage='passed',gate_blocked=distance< -50,gate_signed_distance=distance,player=str(q));write();unreal.unregister_slate_post_tick_callback(check['handle'])
 except Exception:
  check['error']=traceback.format_exc();write();unreal.unregister_slate_post_tick_callback(check['handle'])
check['handle']=unreal.register_slate_post_tick_callback(step)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()

