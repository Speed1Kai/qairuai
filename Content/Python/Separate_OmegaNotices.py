import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,pin,val,compile_bp,save
src=os.path.join(os.path.dirname(__file__),'Upgrade_PlayerVisor.py');exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
for path in ['/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt']:
 bp=A.load_asset(path);g=Flow(bp)
 if not any(n.get_name()=='NoticeVerticalSeparation' for n in g.e.list_all_nodes()):
  target=next(n for n in g.e.list_all_nodes() if n.find_input_pin('Translation').is_valid());make=target.find_input_pin('Translation').list_connected_pins()[0].get_owning_node();yp=pin(make,'Y');original=list(yp.list_connected_pins());old=original[0] if original else yp.get_pin_value();yp.break_pin_links()
  transient=g.math('Less_DoubleDouble',A=g.get('HUDLifetime'),B=60.);offset=g.math('SelectFloat',A=-265.,B=0.,bPickA=transient);output=g.math('Add_DoubleDouble',A=old,B=offset);output.get_owning_node().rename('NoticeVerticalSeparation');val(yp,output)
 compile_bp(bp);save(bp)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(5850,800,2380),unreal.Rotator(yaw=90))
json.dump({'saved':True,'notification_offset':-265,'interaction_offset':0},open(os.path.join(unreal.Paths.project_saved_dir(),'notice_separation.json'),'w'),indent=2)
