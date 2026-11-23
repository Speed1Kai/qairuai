"""Repair placed lift input overrides, preserving all geometry and ride logic."""
import unreal, os, json, shutil, datetime
path='/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional'
saved=os.path.abspath(unreal.Paths.project_saved_dir())
backup=os.path.join(saved,'Backups','LiftInput',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True)
for rel in ['Lvl_LabTutorial.umap','LabTutorial/Elevator/BP_FreightElevatorBidirectional.uasset']:
 src=os.path.join(unreal.Paths.project_content_dir(),rel)
 if os.path.isfile(src):shutil.copy2(src,os.path.join(backup,os.path.basename(src)))
bp=unreal.EditorAssetLibrary.load_asset(path)
cls=unreal.BlueprintEditorLibrary.generated_class(bp)
cdo=unreal.get_default_object(cls)
cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
cdo.set_editor_property('input_priority',70)
r={'backup':backup,'editor_actors':[],'live_actors':[]}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in sub.get_all_level_actors():
 if a.get_class()!=cls:continue
 a.modify()
 a.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
 a.set_editor_property('input_priority',70)
 r['editor_actors'].append(a.get_path_name())
w=unreal.EditorLevelLibrary.get_game_world()
if w:
 pc=unreal.GameplayStatics.get_player_controller(w,0)
 for a in unreal.GameplayStatics.get_all_actors_of_class(w,cls):
  a.set_editor_property('input_priority',70)
  a.enable_input(pc)
  r['live_actors'].append(a.get_path_name())
r['blueprint_saved']=unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
r['map_saved']=unreal.EditorLoadingAndSavingUtils.save_current_level()
with open(os.path.join(saved,'lift_input_fix_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('Lift keyboard input repaired: '+str(r))
