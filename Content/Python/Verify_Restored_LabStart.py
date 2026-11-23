"""Observe an ordinary Play start without relocating or driving the player."""
import unreal,time,os,json,traceback
assert not unreal.EditorLevelLibrary.get_game_world()
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()=='Lvl_LabTutorial'
R={'stage':'waiting','start':time.monotonic(),'samples':[]};path=os.path.join(unreal.Paths.project_saved_dir(),'lab_restored_start_check.json')
def write():json.dump({k:v for k,v in R.items() if k!='handle'},open(path,'w'),indent=2)
def tick(dt):
 try:
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  t=unreal.SystemLibrary.get_game_time_in_seconds(w);p=unreal.GameplayStatics.get_player_character(w,0)
  if not p:return
  if len(R['samples'])==0 or t-R['samples'][-1]['t']>3:
   q=p.get_actor_location();R['samples'].append(dict(t=t,world=w.get_name(),player=[q.x,q.y,q.z]));write()
  if t>25:
   q=p.get_actor_location();R['checks']={'laboratory_world':'Lvl_LabTutorial' in w.get_name(),'starts_in_laboratory':abs(q.x)<3000 and abs(q.y)<3000 and -100<q.z<1500,'capsule_present':any('CapsuleArmor' in a.get_name() or 'CapsuleArmor' in a.get_actor_label() for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.StaticMeshActor))};R['passed']=all(R['checks'].values());R['stage']='done';write();unreal.unregister_slate_post_tick_callback(R['handle'])
   unreal.AutomationLibrary.take_high_res_screenshot(1280,800,os.path.join(unreal.Paths.project_saved_dir(),'Restored_Laboratory_Start.png'),delay=0.)
 except Exception:
  R.update(stage='failed',error=traceback.format_exc());write();unreal.unregister_slate_post_tick_callback(R['handle'])
R['handle']=unreal.register_slate_post_tick_callback(tick)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
