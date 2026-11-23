"""Disposable PIE fixture: visible grip, travelling bolt, damage and cleanup."""
import unreal,os,json,time,traceback
S=unreal.Paths.project_saved_dir();T={'stage':'wait','checks':{},'start':time.monotonic()};H={}
def write():json.dump(T,open(os.path.join(S,'atomic_weapon_pie.json'),'w'),indent=2)
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  now=unreal.SystemLibrary.get_game_time_in_seconds(w)
  if T['stage']=='wait':
   if now<25:return
   p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
   if not p:return
   pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0.)
   p.character_movement.stop_movement_immediately();p.set_actor_location(V(3970,-100,2258),False,True);p.set_actor_rotation(unreal.Rotator(yaw=0),True);pc.set_control_rotation(unreal.Rotator(pitch=-2,yaw=0))
   p.set_editor_property('bFirstPerson',True);p.get_editor_property('FirstPersonCamera').set_active(True,False);p.get_editor_property('FollowCamera').set_active(False,False);p.call_method('View_ApplyBodyVisibility',())
   p.call_method('Modes_Select',(2,))
   cls=unreal.load_class(None,'/Game/Combat/Protocol/BP_ProtocolDestructible.BP_ProtocolDestructible_C')
   lib=unreal.get_default_object(unreal.GameplayStatics);tf=unreal.Transform(location=V(4900,-100,2270))
   cover=lib.call_method('BeginDeferredActorSpawnFromClass',(w,cls,tf,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,p,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   lib.call_method('FinishSpawningActor',(cover,tf,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   H.update(p=p,pc=pc,cover=cover,w=w);T.update(stage='ready',since=now,before=p.get_editor_property('ProtocolShots'));write();return
  p=H['p'];s=T['stage']
  if s=='ready':
   if now-T['since']<2:return
   T['checks']['atomic_equipped']=p.get_editor_property('bAtomicWasEquipped')
   T['checks']['fp_hands_visible']=p.get_editor_property('AtomicFPArms').is_visible()
   T['checks']['fp_gun_visible']=p.get_editor_property('AtomicFPGun').is_visible()
   T['checks']['old_weapon_hidden']=not p.get_editor_property('FP_LaserWeapon').is_visible()
   T['right_hand']=str(p.get_editor_property('AtomicFPArms').get_socket_location('CC_Base_R_Hand'));T['left_hand']=str(p.get_editor_property('AtomicFPArms').get_socket_location('CC_Base_L_Hand'))
   T['stage']='await_fire';write()
  elif s=='await_fire':
   if p.get_editor_property('ProtocolShots')<=T['before']:return
   T.update(stage='shot',since=now);write()
  elif s=='shot':
   if now-T['since']<3:return
   T['checks']['one_shot']=p.get_editor_property('ProtocolShots')==T['before']+1
   T['checks']['cooldown_active']=p.get_editor_property('ProtocolCooldownRemaining')>3
   T['checks']['target_destroyed']=H['cover'].get_editor_property('bBroken')
   for name in ('BP_AtomicBolt','BP_AtomicImpact','BP_AtomicMuzzle'):
    cls=unreal.load_class(None,'/Game/Combat/AtomicWeapon/'+name+'.'+name+'_C');T['checks'][name+'_cleaned']=len(unreal.GameplayStatics.get_all_actors_of_class(w,cls))==0
   T['checks']['recoil_recovered']=abs(p.get_editor_property('AtomicFPRig').get_editor_property('relative_location').x)<.1
   T.update(stage='complete',passed=all(T['checks'].values()));write();unreal.unregister_slate_post_tick_callback(H['handle'])
 except Exception:
  T.update(stage='error',error=traceback.format_exc());write();unreal.unregister_slate_post_tick_callback(H['handle'])
H['handle']=unreal.register_slate_post_tick_callback(tick)
if not unreal.EditorLevelLibrary.get_game_world():unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
write()
