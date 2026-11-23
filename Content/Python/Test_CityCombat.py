"""Finite PIE integration. Observe native AI; cannon is fired by real LMB clicks.
Only disposable PIE actors are positioned to prepare the blast/cover test.
"""
import unreal,os,time,json,traceback,math
S=os.path.abspath(unreal.Paths.project_saved_dir());path=os.path.join(S,'citycombat_pie.json')
if 'T' in globals() and 'handle' in T:
 try:unreal.unregister_slate_post_tick_callback(T['handle'])
 except Exception:pass
T={'stage':'wait','start':time.monotonic(),'samples':[],'passed':False}
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def write():
 tmp=path+'.tmp';json.dump({k:v for k,v in T.items() if k not in ('p','pc','npcs','cover','handle')},open(tmp,'w'),indent=2);os.replace(tmp,path)
def val(a,n):return a.get_editor_property(n)
def aim():
 cam=unreal.GameplayStatics.get_player_camera_manager(unreal.EditorLevelLibrary.get_game_world(),0)
 target=T['npcs'][0].get_actor_location()+V(0,0,8) if T['stage'] in ('prepare_shot','ready_shot') else T['cover'].get_actor_location()
 T['pc'].set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam.get_camera_location(),target))
def step(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  now=unreal.SystemLibrary.get_game_time_in_seconds(w)
  if time.monotonic()-T['start']>240:raise RuntimeError('Combat test timed out waiting for LMB')
  if T['stage']=='wait':
   p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
   if not p or now<27:return
   npcs=[a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Character) if a.get_class().get_name().startswith('BP_Enceladus_')];assert len(npcs)==6,len(npcs)
   npcs.sort(key=lambda a:a.get_actor_location().y)
   p.set_actor_location(V(0,24400,140),False,True);pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);pc.set_control_rotation(unreal.Rotator(pitch=-3,yaw=90,roll=0))
   T.update(p=p,pc=pc,npcs=npcs,stage='observe',since=now,initial_npc_y=npcs[0].get_actor_location().y,initial_integrity=val(p,'VisorIntegrity'),initial_shots=val(p,'ProtocolShots'))
   T['roles']=[dict(cls=n.get_class().get_name(),kind=val(n,'CityGunKind'),interval=val(n,'CityShotInterval'),damage=val(n,'CityProjectileDamage'),mesh=n.get_component_by_class(unreal.SkeletalMeshComponent).get_skinned_asset().get_name()) for n in npcs];write();return
  p=T['p'];pc=T['pc'];npcs=T['npcs'];count=val(p,'ProtocolShots')-T['initial_shots']
  if T['stage']=='observe':
   q=npcs[0].get_actor_location();T['samples'].append(dict(t=now-T['since'],npc_y=q.y,npc_speed=npcs[0].get_velocity().length(),shots=val(npcs[0],'CityShotCount'),player_health=val(p,'VisorIntegrity'),state=val(npcs[0],'StateIndex')))
   if now-T['since']<3.5:return
   T['ai_checks']={'six_enemies':len(npcs)==6,'three_weapon_types':set(r['kind'] for r in T['roles'])=={0,1,2},'supplied_model_active':all(r['mesh']=='SK_Enceladus' for r in T['roles']),'ai_fired':max(s['shots'] for s in T['samples'])>0,'player_received_damage':min(s['player_health'] for s in T['samples'])<T['initial_integrity'],'pursuit_moved':T['initial_npc_y']-q.y>180}
   # Freeze only these PIE copies for reproducible blast and cooldown observation.
   for n in npcs:
    c=n.get_controller()
    if c:
     brain=c.get_component_by_class(unreal.BrainComponent)
     if brain:brain.stop_logic('Disposable combat verification fixture')
     c.stop_movement()
    n.set_actor_tick_enabled(False);n.character_movement.stop_movement_immediately()
   for i,n in enumerate(npcs):n.set_actor_location(V((i%3-1)*160,25800+(i//3)*130,128),False,True)
   p.character_movement.stop_movement_immediately();p.set_actor_location(V(0,24700,128),False,True);pc.set_control_rotation(unreal.Rotator(pitch=-3,yaw=90,roll=0))
   pc.set_ignore_look_input(True);T.update(stage='prepare_shot',since=now);write();return
  if T['stage']=='prepare_shot':
   aim()
   if now-T['since']<1:return
   T.update(stage='ready_shot',integrity_before_blast=val(p,'VisorIntegrity'));write();return
  if T['stage']=='ready_shot':
   aim()
   if count<1:return
   T.update(stage='first_shot',blast_positions=[str(a.get_actor_location()) for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor) if a.get_class().get_name()=='BP_ProtocolBlast_C'],first_shot_time=now,first_hit=[dict(health=val(n,'Health'),dead=val(n,'bIsDead')) for n in npcs]);write();return
  if T['stage']=='first_shot':
   T['post_shot_count']=count
   if now-T['first_shot_time']<2:return
   T['blast_checks']={'one_trigger_one_shot':count==1,'multiple_enemies_destroyed':sum(bool(val(n,'bIsDead')) for n in npcs)>=2,'owner_survives':val(p,'VisorIntegrity')==T['integrity_before_blast'],'cooldown_running':val(p,'ProtocolCooldownRemaining')>5.}
   coverclass=unreal.load_class(None,'/Game/Combat/Protocol/BP_ProtocolDestructible.BP_ProtocolDestructible_C');cover=unreal.GameplayStatics.get_all_actors_of_class(w,coverclass)[-1];cover.set_actor_location(V(0,25800,75),False,True);T['cover']=cover;T['stage']='cooldown_wait';write();return
  if T['stage']=='cooldown_wait':
   T['cooldown_shot_count']=count;aim()
   if now-T['first_shot_time']<8.3:return
   T.update(stage='ready_second_shot',blocked_extra_shots=count==1);write();return
  if T['stage']=='ready_second_shot':
   if count<2:return
   T.update(stage='second_shot',since=now);write();return
  if T['stage']=='second_shot':
   if now-T['since']<1:return
   cover=T['cover'];shards=[c for c in cover.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith('Shard')]
   T['cover_checks']={'second_shot_after_recharge':count==2,'cover_destroyed':bool(val(cover,'bBroken')),'physics_debris':sum(c.is_simulating_physics() for c in shards)>=4,'cooldown_prevents_spam':T['blocked_extra_shots']}
   T['checks']={**T['ai_checks'],**T['blast_checks'],**T['cover_checks']};T.update(stage='done',passed=all(T['checks'].values()));write();unreal.unregister_slate_post_tick_callback(T['handle'])
   unreal.AutomationLibrary.take_high_res_screenshot(1280,800,os.path.join(S,'CityCombat_AfterBlast.png'),delay=0.)
 except Exception:
  T.update(stage='failed',error=traceback.format_exc());write();unreal.log_error(T['error']);unreal.unregister_slate_post_tick_callback(T['handle'])
assert not unreal.EditorLevelLibrary.get_game_world()
import runpy
runpy.run_path(os.path.join(os.path.dirname(__file__),'Configure_CombatCollision.py'))
runpy.run_path(os.path.join(os.path.dirname(__file__),'Patch_CityCombat.py'))
assert json.load(open(os.path.join(S,'citycombat_pursuit_patch.json'))).get('saved')
T['handle']=unreal.register_slate_post_tick_callback(step);unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()








