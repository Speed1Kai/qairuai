import unreal,os,json,time,traceback
S=unreal.Paths.project_saved_dir();w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);R={'checks':{}};stage=0;start=time.monotonic()
p.call_method('Modes_Select',(2,))
def tick(dt):
 global stage,start
 try:
  if time.monotonic()-start<.8:return
  if stage==0:
   R['checks']['third_person_weapon_visible']=p.get_editor_property('AtomicTPGun').is_visible()
   R['checks']['first_person_arms_hidden_in_third_person']=not p.get_editor_property('AtomicFPArms').is_visible()
   R['checks']['rifle_upper_body_active']=p.mesh.get_anim_instance().get_class().get_name()=='ABP_AtomicBody_C'
   before=p.get_editor_property('ProtocolShots');p.call_method('Protocol_Fire',());p.call_method('Protocol_Fire',());R['checks']['spam_blocked']=p.get_editor_property('ProtocolShots')-before<=1
   p.call_method('Modes_Select',(0,));stage=1;start=time.monotonic();return
  R['checks']['weapon_hidden_after_mode_exit']=not p.get_editor_property('AtomicTPGun').is_visible()
  R['checks']['locomotion_restored']=p.mesh.get_anim_instance().get_class().get_name()=='BS_ABP_PlayerGuard_C'
  R['passed']=all(R['checks'].values());json.dump(R,open(os.path.join(S,'atomic_switching_check.json'),'w'),indent=2);unreal.unregister_slate_post_tick_callback(handle)
 except Exception:
  R['error']=traceback.format_exc();json.dump(R,open(os.path.join(S,'atomic_switching_check.json'),'w'),indent=2);unreal.unregister_slate_post_tick_callback(handle)
handle=unreal.register_slate_post_tick_callback(tick)
