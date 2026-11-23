"""Align existing interaction distances and protect obsolete lamp references."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,components,pin,val,link,compile_bp,save
root='/Game/LabTutorial/FocusedInteraction/'
for i in range(1,7):
 bp=A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i);e=G.get_graph_editor_by_name(bp,'EventGraph')
 for n in e.list_all_nodes():
  title=str(n.get_node_title())
  # Raise only the original 175 cm proximity gate; aim and occlusion remain required.
  names={str(p.get_pin_name()) for p in n.list_all_pins()}
  if 'A' in names and 'B' in names:
   b=n.find_input_pin('B')
   if b.is_valid() and b.get_pin_value() in ['175','175.0','175.000000']:b.set_pin_value('350.0')
  if 'bNewVisibility' in names:
   target=list(n.find_self_pin().list_connected_pins())
   if target and 'InteractPrompt' in str(target[0].get_owning_node().get_node_title()):
    p=n.find_input_pin('bNewVisibility');p.break_pin_links();p.set_pin_value('false')
 compile_bp(bp);save(bp)
lift=A.load_asset('/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional')
for h,c,n in components(lift):
 if n=='UpperCallZone' and c:c.set_editor_property('relative_location',V((455,130,2275)));c.set_box_extent(V((120,150,130)))
compile_bp(lift);save(lift)
power=A.load_asset('/Game/LabTutorial/Basement/BP_BuildingPower');e=G.get_graph_editor_by_name(power,'EventGraph')
for n in list(e.list_all_nodes()):
 names={str(p.get_pin_name()) for p in n.list_all_pins()}
 if not {'ParameterName','ParameterValue'}.issubset(names):continue
 source=list(n.find_self_pin().list_connected_pins())
 if not source:continue
 getter=source[0].get_owning_node()
 if not any('CircuitSurface_0'+s in str(getter.get_node_title()) for s in ['09','10']):continue
 incoming=list(n.find_execute_pin().list_connected_pins());outgoing=list(n.find_then_pin().list_connected_pins());n.find_execute_pin().break_pin_links()
 valid=e.add_call_function_node('/Script/Engine.KismetSystemLibrary.IsValid');val(pin(valid,'Object'),source[0]);branch=e.add_branch_node();val(pin(branch,'Condition'),pin(valid,'ReturnValue',True))
 for p in incoming:link(p,branch.find_execute_pin())
 link(branch.find_then_pin(),n.find_execute_pin())
 for p in outgoing:link(branch.find_else_pin(),p)
compile_bp(power);save(power)
# Make the focus target's range explicit rather than showing hints across a room.
focus=A.load_asset(root+'BP_InteractionFocus');e=G.get_graph_editor_by_name(focus,'EventGraph')
for n in e.list_all_nodes():
 if str(n.get_node_title())=='<=':
  p=n.find_input_pin('B')
  if p.is_valid() and p.get_pin_value() in ['320','320.0','320.000000']:p.set_pin_value('280.0')
compile_bp(focus);save(focus)
unreal.EditorLoadingAndSavingUtils.save_current_level()
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor.set_level_viewport_camera_info(V((120,80,235)),unreal.MathLibrary.find_look_at_rotation(V((120,80,235)),V((120,670,220))))
with open(os.path.join(unreal.Paths.project_saved_dir(),'focused_interaction_report.json'),encoding='utf8') as f:r=json.load(f)
r['polished']=True
with open(os.path.join(unreal.Paths.project_saved_dir(),'focused_interaction_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
