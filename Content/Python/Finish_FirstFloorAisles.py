"""Keep the twelve drawn racks while clearing the rear aisle to security."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,components,compile_bp,save
bp=A.load_asset('/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor');shift={180:140,380:320,580:500,780:680};n=0
for h,c,name in components(bp):
    if not isinstance(c,unreal.InstancedStaticMeshComponent) or name not in ('SM_LabUtilityBench','HiddenFurnitureCollisions'):continue
    c.modify()
    for i in range(c.get_instance_count()):
        t=c.get_instance_transform(i,False);p=t.translation
        if abs(p.x-3330)<1 and abs(p.y-245)<1:
            p.x=3535;p.y=60;t.translation=p;t.rotation=unreal.Rotator(yaw=90).quaternion();c.update_instance_transform(i,t,False,True,True)
for h,c,name in components(bp):
    if not isinstance(c,unreal.InstancedStaticMeshComponent) or name not in ('SM_ModernServerRack','HiddenFurnitureCollisions'):continue
    c.modify()
    for i in range(c.get_instance_count()):
        t=c.get_instance_transform(i,False);p=t.translation
        if min(abs(p.x-x) for x in (4150,4530,4900))<1 and round(p.y) in shift:
            p.y=shift[round(p.y)];t.translation=p;c.update_instance_transform(i,t,False,True,True);n+=1
compile_bp(bp)
stage=os.path.join(unreal.Paths.project_saved_dir(),'FirstFloorPlanStaged')
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(w,'OBJ SAVEPACKAGE PACKAGE="/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor" FILE="'+os.path.join(stage,'LabTutorial/FirstFloor/BP_ModernFirstFloor.uasset').replace('\\','/')+'" SILENT=true')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in list(sub.get_all_level_actors()):
    if a.get_class().get_name()=='BP_ModernFirstFloor_C':
        p=a.get_actor_location();rot=a.get_actor_rotation();label=a.get_actor_label();sub.destroy_actor(a);a=sub.spawn_actor_from_class(B.generated_class(bp),p,rot);a.set_actor_label(label);a.set_folder_path('LAB/Floor01/Architecture')
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();w.modify()
unreal.SystemLibrary.execute_console_command(w,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+os.path.join(stage,'Lvl_LabTutorial.umap').replace('\\','/')+'" SILENT=true')
json.dump({'saved':True,'shifted_mesh_and_collision_instances':n,'rack_rows':[140,320,500,680]},open(os.path.join(unreal.Paths.project_saved_dir(),'first_floor_aisles.json'),'w'),indent=2)
