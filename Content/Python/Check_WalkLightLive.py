"""Real movement-input regression test, never modifies saved spawn or collision."""
import unreal,time,math,os,json,traceback
check={'start':time.monotonic(),'stage':'button','samples':[]};out=os.path.join(unreal.Paths.project_saved_dir(),'walk_light_regression.json')
def record():json.dump({k:v for k,v in check.items() if k not in ('handle','exit')},open(out,'w'),indent=2)
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  p=unreal.GameplayStatics.get_player_character(w,0)
  if not p:return
  t=time.monotonic()-check['start'];pc=unreal.GameplayStatics.get_player_controller(w,0)
  if t>150:raise RuntimeError('test timeout '+check['stage'])
  actors=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor);ex=next((a for a in actors if a.get_class().get_name()=='BP_SurfaceDeparture_C'),None);grade=next((a for a in actors if a.get_class().get_name()=='BP_CampusReadability_C'),None)
  if check['stage']=='wait' and t>23:
   p.set_actor_location(unreal.Vector(5850,1080,2259.65),False,True);p.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately();pc.set_control_rotation(unreal.Rotator(yaw=90));pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0)
   if grade and ex.get_editor_property('CampusStreaming').is_level_visible():check.update(stage='settle',settled=t)
  if check['stage']=='settle' and t-check['settled']>3:
   check.update(stage='button',mesh_yaw=p.mesh.get_relative_transform().rotation.rotator().yaw,inside_blend=grade.get_editor_property('ExteriorBlend'));record()
  if check['stage']=='button' and ex.get_editor_property('ExitDoorAmount')>.99:
   check.update(stage='walk',index=0,targets=[(5850,2700),(6250,2700),(6250,3200),(5850,3200),(5850,2700)],segment=t)
  if check['stage']=='walk':
   q=p.get_actor_location();x,y=check['targets'][check['index']];dx=x-q.x;dy=y-q.y;dist=math.hypot(dx,dy)
   if dist<45:
    check['index']+=1;check['segment']=t
    if check['index']==len(check['targets']):
     check.update(stage='passed',outside_blend=grade.get_editor_property('ExteriorBlend'),same_mesh_yaw=p.mesh.get_relative_transform().rotation.rotator().yaw,position=str(q));record();unreal.unregister_slate_post_tick_callback(check['handle']);return
   else:p.add_movement_input(unreal.Vector(dx/dist,dy/dist,0),1.,True)
   if int(t*5)!=check.get('last_sample'):
    check['last_sample']=int(t*5);v=p.get_velocity();ar=p.get_actor_rotation();yaw=p.mesh.get_relative_transform().rotation.rotator().yaw
    check['samples'].append({'y':q.y,'blend':grade.get_editor_property('ExteriorBlend'),'mesh_yaw':yaw,'actor_yaw':ar.yaw,'velocity_yaw':math.degrees(math.atan2(v.y,v.x)),'speed':math.hypot(v.x,v.y),'turning':t-check['segment']<.6});record()
 except:
  check['error']=traceback.format_exc();record();unreal.unregister_slate_post_tick_callback(check['handle'])
check['handle']=unreal.register_slate_post_tick_callback(tick)


