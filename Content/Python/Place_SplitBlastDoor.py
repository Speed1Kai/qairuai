"""Save the revised corridor to a staging file while its source is loaded."""
import unreal,os,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
bp=unreal.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor')
for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
 if actor.get_actor_label() in ('IND_HeavyBlastDoor','IND_DoorFrontPocket','IND_DoorRearPocket'):unreal.EditorLevelLibrary.destroy_actor(actor)
door=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.BlueprintEditorLibrary.generated_class(bp),unreal.Vector(1450,0,0),unreal.Rotator())
door.set_actor_label('IND_HeavyBlastDoor');door.set_folder_path('LAB/03_Interactables')
folder=os.path.abspath(os.path.join(unreal.Paths.project_saved_dir(),'SplitDoorStaged'));os.makedirs(folder,exist_ok=True)
file=os.path.join(folder,'Lvl_LabTutorial.umap')
unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(),'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+file.replace('\\','/')+'" SILENT=true')
if not os.path.isfile(file):raise RuntimeError('Staged map not saved')
report_path=os.path.join(unreal.Paths.project_saved_dir(),'split_blast_door_report.json')
with open(report_path,encoding='utf8') as f:r=json.load(f)
r['saved']=False;r['asset_saved']=True;r['staged_map']=file
with open(report_path,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('SPLIT DOOR MAP STAGED '+file)
