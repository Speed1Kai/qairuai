"""Increase the existing sprint speed and reduce its energy consumption.

Keep the existing input/camera/locomotion graphs and update both the player
defaults and legacy visual helpers which initialize those defaults at runtime.
"""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,compile_bp,save
project=os.path.abspath(unreal.Paths.project_dir())
report={'saved':False,'gameplay_tested':False,'assets':[],'maps':[]}
settings={'sprint_speed_cm_s':700,'sprint_energy_per_second':2.0}
backup=os.path.join(project,'Saved','Backups','RunBalance',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True);report['backup']=backup

def backup_asset(path,extension='.uasset'):
 rel=path.removeprefix('/Game/')+extension
 src=os.path.join(project,'Content',rel)
 if os.path.isfile(src):
  dst=os.path.join(backup,rel);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)

def update(obj,changes):
 result={}
 for name,value in changes.items():
  try:
   old=obj.get_editor_property(name)
  except Exception:continue
  if isinstance(old,int):value=int(value)
  elif isinstance(old,float):value=float(value)
  obj.set_editor_property(name,value);result[name]={'before':str(old),'after':str(value)}
 return result

try:
 playerpath='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
 bp=A.load_asset(playerpath);backup_asset(playerpath)
 changes={'RobotRunSpeed':700,'SprintEnergyDrain':2.,'VisorSprintEnergyDrain':2.}
 # This project currently uses Shift Pressed/Released to select RobotRunSpeed /
 # RobotWalkSpeed. Update the real defaults rather than unused prototype graphs.
 defaults=unreal.get_default_object(B.generated_class(bp))
 report['player_changes']=update(defaults,changes)
 if len(report['player_changes'])!=3:raise RuntimeError('Expected player speed/energy settings missing')
 compile_bp(bp)
 # Compilation may reconstruct the CDO. Apply again to the final generated class.
 update(unreal.get_default_object(B.generated_class(bp)),changes);save(bp)
 report['assets'].append(playerpath)
 helper_paths=['/Game/Characters/GuardPlayer/BP_PlayerGuardVisual','/Game/Characters/ProtocolRobot/BP_ProtocolRobotVisual']
 helper_changes={}
 for path in helper_paths:
  if not A.does_asset_exist(path):continue
  helper=A.load_asset(path);backup_asset(path)
  values={'RunSpeed':700}
  applied=update(unreal.get_default_object(B.generated_class(helper)),values)
  if applied:
   compile_bp(helper);update(unreal.get_default_object(B.generated_class(helper)),values);save(helper)
   helper_changes[B.generated_class(helper).get_name()]=values;report['assets'].append(path)
 # A placed visual helper can override RunSpeed. Persist the same value in both
 # levels so its BeginPlay cannot restore an old sprint speed.
 levelsub=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
 actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 start_world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 start_map=start_world.get_path_name().split('.')[0]
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Could not preserve current level')
 for level in ['/Game/Lvl_LabTutorial','/Game/Surface/Lvl_SurfaceArrival']:
  backup_asset(level,'.umap')
  unreal.EditorLoadingAndSavingUtils.load_map(level)
  affected=[]
  for actor in actor_sub.get_all_level_actors():
   cls=actor.get_class().get_name()
   if cls in helper_changes:
    update(actor,helper_changes[cls]);affected.append(actor.get_actor_label())
   elif cls=='BP_ThirdPersonCharacter_C':
    update(actor,changes);affected.append(actor.get_actor_label())
  if affected:
   if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Level save failed '+level)
  report['maps'].append({'path':level,'updated_instances':affected})
 unreal.EditorLoadingAndSavingUtils.load_map(start_map)
 report.update(saved=True,settings=settings,sprint_seconds_at_full_charge=50)
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','run_balance_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Run balance incomplete; see Saved/run_balance_report.json')
