"""Capture same-frame movement after Enhanced Input has dispatched both actions."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,Graph,pin,val,link,compile_bp,save
assert not unreal.EditorLevelLibrary.get_game_world()
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
g=Graph(bp);g.e=G.create_and_edit_function_graph(bp,'Pneumatic_RefreshDirection');g.cursor=g.e.find_graph_entry_pin()
condition=g.math('BooleanAND',A=g.get('bPneumaticPending'),B=g.math('Greater_DoubleDouble',A=g.math('VSizeSquared',A=g.get('PneumaticMoveAxis')),B=.01))
g.branch(condition);n=g.e.add_call_function_node(B.generated_class(bp).get_path_name()+'.Pneumatic_CaptureDirection');g.do(n)
compile_bp(bp)
e=G.get_graph_editor_by_name(bp,'Pneumatic_Update');orb=next(n for n in e.list_all_nodes() if str(n.get_node_title())=='Pneumatic_Orbs')
source=orb.find_then_pin();old=list(source.list_connected_pins());source.break_pin_links();n=e.add_call_function_node(B.generated_class(bp).get_path_name()+'.Pneumatic_RefreshDirection');link(source,n.find_execute_pin())
for p in old:link(n.find_then_pin(),p)
compile_bp(bp);save(bp)
json.dump({'saved':True,'refresh_after_action_dispatch':True},open(os.path.join(unreal.Paths.project_saved_dir(),'pneumatic_simultaneous_fix.json'),'w'),indent=2)
