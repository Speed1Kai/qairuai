"""Keep the cabin button focus volume on the moving control panel."""
import unreal,os,sys,json,datetime,shutil
sys.path.insert(0,os.path.dirname(__file__))
src=os.path.join(os.path.dirname(__file__),'Upgrade_PlayerVisor.py');exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups','MovingLiftFocus',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
for file in ('Lvl_LabTutorial.umap','LabTutorial/FocusedInteraction/BP_InteractionFocus.uasset'):shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),file),os.path.join(backup,os.path.basename(file)))
bp=A.load_asset('/Game/LabTutorial/FocusedInteraction/BP_InteractionFocus');member(bp,'FollowComponent',B.get_object_reference_type(unreal.SceneComponent),'None')
g=Flow(bp);tick=g.e.find_event_node('ReceiveTick');then=pin(tick,'then',True);old=list(then.list_connected_pins());then.break_pin_links();g.cursor=then;seq=g.do(g.sequence());g.cursor=pin(seq,'then_0',True)
g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('FollowComponent'))));loc=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('FollowComponent')));newloc=g.math('Add_VectorVector',A=loc,B='(X=80,Y=165,Z=185)');g.do(g.call('Engine.Actor.K2_SetActorLocation',NewLocation=newloc,bSweep=False,bTeleport=True))
for p in old:link(pin(seq,'then_1',True),p)
compile_bp(bp);save(bp)
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);count=0
for a in sub.get_all_level_actors():
 if a.get_class().get_name()=='BP_InteractionFocus_C' and str(a.get_editor_property('FocusField'))=='FocusCabButton':
  a.modify();lift=a.get_editor_property('Device');a.set_editor_property('FollowComponent',lift.get_editor_property('CabinRoot'));count+=1
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Lvl_LabTutorial')
json.dump({'saved':True,'markers':count,'backup':backup},open(os.path.join(unreal.Paths.project_saved_dir(),'moving_lift_focus_fix.json'),'w'),indent=2)
