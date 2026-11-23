"""Finite PIE scenarios. Mode keys, HUD click, V and trigger are real UI input.
Only disposable PIE copies are positioned; movement samples use normal Pawn input.
"""
import unreal,os,json,time,traceback
S=os.path.abspath(unreal.Paths.project_saved_dir());path=os.path.join(S,'cyborg_modes_pie.json');T={'stage':'wait','passed':False,'checks':{},'start':time.monotonic()};H={}
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def prop(n):return H['p'].get_editor_property(n)
def save():
 tmp=path+'.tmp';json.dump(T,open(tmp,'w'),indent=2);os.replace(tmp,path)
def stage(n,t):T.update(stage=n,since=t);save()
def reset_position():
 p=H['p'];p.character_movement.stop_movement_immediately();p.set_actor_location(V(0,24500,128),False,True)
def aim():
 pc=H['pc'];cam=unreal.GameplayStatics.get_player_camera_manager(H['w'],0);pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam.get_camera_location(),H['n'].get_actor_location()))
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  now=unreal.SystemLibrary.get_game_time_in_seconds(w)
  if time.monotonic()-T['start']>900:raise RuntimeError('Timed out waiting for physical test input')
  if T['stage']=='wait':
   p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
   if not p or now<12:return
   enemies=[n for n in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Character) if n.get_class().get_name().startswith('BP_Enceladus_')];assert len(enemies)==6
   enemies.sort(key=lambda n:n.get_actor_location().y)
   for i,n in enumerate(enemies):
    c=n.get_controller();brain=c.get_component_by_class(unreal.BrainComponent) if c else None
    if brain:brain.stop_logic('PIE mode verification fixture')
    if c:c.stop_movement()
    n.set_actor_tick_enabled(False);n.character_movement.stop_movement_immediately();n.character_movement.set_component_tick_enabled(False)
    if i:n.set_actor_location(V(2800,27000+i*160,128),False,True)
   enemies[0].set_actor_location(V(0,25700,128),False,True)
   covers=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,'/Game/Combat/Protocol/BP_ProtocolDestructible.BP_ProtocolDestructible_C'));covers.sort(key=lambda n:n.get_actor_location().y)
   H.update(w=w,p=p,pc=pc,n=enemies[0],cover=covers[-1],cover_original=covers[-1].get_actor_transform())
   pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);pc.set_control_rotation(unreal.Rotator(pitch=-3,yaw=90,roll=0));reset_position()
   T['checks']['native_mode_hud_active']=pc.get_hud().get_class().get_name()=='BP_CyborgCombatHUD_C' and prop('ModeHUDFrames')>0
   T['checks']['hostile_tags_active']=all(n.actor_has_tag('CyborgHostile') for n in enemies)
   stage('ready_speed_key_1',now);return
  p=H['p'];pc=H['pc'];s=T['stage'];mode=prop('CyborgMode')
  for label,value,nextstage in [('speed',0,'ready_hunter_key_2'),('hunter',1,'ready_atomic_key_3'),('atomic',2,'ready_locked_key_4')]:
   if s=='ready_'+label+'_key_'+str(value+1) and mode==value:
    T.update(peak_speed=0.,movement_mode=label);stage('move_'+label,now);return
   if s=='move_'+label:
    p.add_movement_input(V(0,1,0),1.,False);T['peak_speed']=max(T['peak_speed'],p.get_velocity().length())
    if now-T['since']<1.4:return
    T[label]={'peak_speed':T['peak_speed'],'max_walk_speed':p.character_movement.max_walk_speed,'acceleration':p.character_movement.max_acceleration,'dash_cooldown':prop('PneumaticDashCooldown')};T['checks'][label+'_movement']=(T['peak_speed']>850 if value==0 else T['peak_speed']>600 if value==1 else 100<T['peak_speed']<280)
    reset_position();T['locked_before']=prop('ModeLockedAttempts');stage(nextstage,now);return
  if s=='ready_locked_key_4':
   if prop('ModeLockedAttempts')<=T['locked_before']:return
   T['checks']['reserved_mode_locked']=mode==2;stage('ready_menu_tab',now);return
  if s=='ready_menu_tab':
   if not prop('bModeMenuOpen'):return
   T['checks']['menu_cursor_enabled']=pc.get_editor_property('show_mouse_cursor') and pc.is_look_input_ignored();stage('ready_click_hunter_card',now);return
  if s=='ready_click_hunter_card':
   if mode!=1 or prop('bModeMenuOpen'):return
   T['checks']['mouse_card_selects_hunter']=True;T['checks']['selection_restores_camera']=not pc.is_look_input_ignored() and not pc.get_editor_property('show_mouse_cursor');stage('ready_first_person_v',now);return
  if s=='ready_first_person_v':
   if not prop('bFirstPerson'):return
   pc.set_ignore_look_input(True);stage('detect_visible',now);return
  if s=='detect_visible':
   aim()
   if now-T['since']<1.5:return
   T['visible_count']=prop('ModeDetectedCount');T['checks']['visible_enemy_red_ring']=T['visible_count']>=1;T['checks']['fp_weapon_visible']=prop('FP_LaserWeapon').is_visible() and not prop('TP_LaserWeapon').is_visible()
   unreal.AutomationLibrary.take_high_res_screenshot(1378,780,os.path.join(S,'CyborgModes_Detection.png'),delay=0.)
   H['cover'].set_actor_location(V(0,25100,170),False,True);H['cover'].set_actor_scale3d(V(1,1,4));stage('detect_occluded',now);return
  if s=='detect_occluded':
   aim()
   if now-T['since']<1:return
   T['occluded_count']=prop('ModeDetectedCount');T['checks']['no_ring_through_cover']=T['occluded_count']==0;H['cover'].set_actor_transform(H['cover_original'],False,True);T.update(laser_before=prop('LaserShots'),hits_before=prop('LaserHits'),enemy_health_before=H['n'].get_editor_property('Health'));stage('ready_rapid_laser_drag',now);return
  if s=='ready_rapid_laser_drag':
   aim()
   if prop('LaserShots')<=T['laser_before']:return
   stage('laser_fired',now);return
  if s=='laser_fired':
   aim()
   if prop('bLaserHeld') or now-T['since']<.5:return
   T['laser_delta']=prop('LaserShots')-T['laser_before'];T['laser_enemy_health_after']=H['n'].get_editor_property('Health');T['checks']['automatic_laser_multiple_pulses']=T['laser_delta']>=2;T['checks']['laser_hits_real_enemy']=T['laser_enemy_health_after']<T['enemy_health_before'];T['checks']['trigger_release_stops_laser']=not prop('bLaserHeld');T['checks']['hunter_acceleration_high']=T['hunter']['acceleration']>T['atomic']['acceleration'];stage('ready_speed_no_weapon_key_1',now);return
  if s=='ready_speed_no_weapon_key_1':
   if mode!=0:return
   T.update(trigger_before=prop('ModeTriggerPulls'),disabled_laser_before=prop('LaserShots'),disabled_atomic_before=prop('ProtocolShots'));stage('ready_disabled_trigger_click',now);return
  if s=='ready_disabled_trigger_click':
   if prop('ModeTriggerPulls')<=T['trigger_before']:return
   T['checks']['speed_mode_weapon_disabled']=prop('LaserShots')==T['disabled_laser_before'] and prop('ProtocolShots')==T['disabled_atomic_before'];stage('ready_atomic_weapon_key_3',now);return
  if s=='ready_atomic_weapon_key_3':
   if mode!=2:return
   H['cover'].set_actor_scale3d(V(1,1,1));H['cover'].set_actor_location(V(230,25700,75),False,True)
   T.update(atomic_before=prop('ProtocolShots'),atomic_laser_before=prop('LaserShots'));stage('ready_atomic_double_click',now);return
  if s=='ready_atomic_double_click':
   aim()
   if prop('ProtocolShots')<=T['atomic_before']:return
   stage('atomic_fired',now);return
  if s=='atomic_fired':
   if now-T['since']<1:return
   T['checks']['atomic_one_impulse']=prop('ProtocolShots')-T['atomic_before']==1;T['checks']['atomic_recharge_active']=prop('ProtocolCooldownRemaining')>5.;T['checks']['atomic_destroys_enemy']=H['n'].get_editor_property('bIsDead');T['checks']['atomic_destroys_cover']=H['cover'].get_editor_property('bBroken');T['checks']['atomic_does_not_auto_laser']=prop('LaserShots')==T['atomic_laser_before'];stage('ready_third_person_v',now);return
  if s=='ready_third_person_v':
   if prop('bFirstPerson'):return
   stage('finish',now);return
  if s=='finish':
   if now-T['since']<.5:return
   T['checks']['third_person_hides_detection']=prop('ModeDetectedCount')==0;T['checks']['third_person_weapon_visible']=prop('TP_LaserWeapon').is_visible() and not prop('FP_LaserWeapon').is_visible();pc.reset_ignore_look_input();T.update(stage='done',passed=all(T['checks'].values()));save();unreal.unregister_slate_post_tick_callback(H['handle'])
 except Exception:
  T.update(stage='failed',error=traceback.format_exc());save();unreal.log_error(T['error']);unreal.unregister_slate_post_tick_callback(H['handle'])
assert not unreal.EditorLevelLibrary.get_game_world();assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
H['handle']=unreal.register_slate_post_tick_callback(tick);save();unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
