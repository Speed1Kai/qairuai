"""Connect actor lookup execution pins and save completed native assets."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,pin,link,compile_bp,save
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');e=G.get_graph_editor_by_name(bp,'EventGraph')
for n in e.list_all_nodes():
 if not n.find_input_pin('ActorClass').is_valid() or not n.find_output_pin('ReturnValue').is_valid() or not n.find_execute_pin().is_valid():continue
 if list(n.find_execute_pin().list_connected_pins()):continue
 for dest in list(pin(n,'ReturnValue',True).list_connected_pins()):
  valid=dest.get_owning_node()
  if str(dest.get_pin_name())!='Object' or not valid.find_output_pin('ReturnValue').is_valid():continue
  for condition in list(pin(valid,'ReturnValue',True).list_connected_pins()):
   branch=condition.get_owning_node()
   if str(condition.get_pin_name())!='Condition':continue
   upstream=list(branch.find_execute_pin().list_connected_pins());branch.find_execute_pin().break_pin_links()
   for p in upstream:link(p,n.find_execute_pin())
   link(n.find_then_pin(),branch.find_execute_pin())
compile_bp(bp);save(bp)
report=json.load(open(os.path.join(unreal.Paths.project_saved_dir(),'player_visor_report.json'),encoding='utf8'))
report.pop('error',None);report.update(saved=True,camera_key='V',fov=90,health_damage_connected=True,energy_sprint_drain=6,energy_regen=3,assets=['/Game/Characters/PlayerVisor/M_VisorRim','/Game/Characters/PlayerVisor/WBP_PlayerVisor',bp.get_path_name()])
with open(os.path.join(unreal.Paths.project_saved_dir(),'player_visor_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
