import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');hud=A.load_asset('/Game/Combat/CyborgModes/BP_CyborgCombatHUD')
var(bp,'bModeHUDInstalled','bool','false');var(bp,'ModeHUDInstallAt','real','0');compile_bp(bp)
g=Graph(bp,'Modes_EnsureHUD');g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')));g.branch(g.math('Not_PreBool',A=g.get('bModeHUDInstalled')));g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('ModeHUDInstallAt')));g.set('bModeHUDInstalled',True);g.do(g.call('Engine.PlayerController.ClientSetHUD',target=g.pc(),NewHUDClass=B.generated_class(hud).get_path_name()));compile_bp(bp)
# Add one isolated call after the existing mode update's entry.
e=G.get_graph_editor_by_name(bp,'Modes_Update');entry=e.find_graph_entry_pin();old=list(entry.list_connected_pins());entry.break_pin_links();n=e.add_call_function_node(B.generated_class(bp).get_path_name()+'.Modes_EnsureHUD');link(entry,n.find_execute_pin())
for p in old:link(n.find_then_pin(),p)
e=G.get_graph_editor_by_name(bp,'Modes_Init');entry=e.find_graph_entry_pin();old=list(entry.list_connected_pins());entry.break_pin_links();g=Graph.__new__(Graph);g.bp=bp;g.e=e;g.i=100;g.cursor=entry;n=g.set('ModeHUDInstallAt',g.math('Add_DoubleDouble',A=g.now(),B=.5))
for p in old:link(n.find_then_pin(),p)
mesh=next(c for h,c,n in components(bp) if n=='Mesh');names=[str(mesh.get_bone_name(i)) for i in range(mesh.get_num_bones())];hands=[n for n in names if 'hand' in n.lower() and any(t in n.lower() for t in ('right','_r','.r'))];socket=min(hands,key=len) if hands else None
for n in e.list_all_nodes():
 if 'AttachToComponent' in str(n.get_node_title()):
  p=n.find_input_pin('SocketName')
  if p.is_valid() and str(p.get_pin_value())=='hand_r' and socket:val(p,socket)
compile_bp(bp);save(bp);json.dump({'socket':socket,'bones':names,'saved':True},open(os.path.join(unreal.Paths.project_saved_dir(),'cyborg_modes_hud_install.json'),'w'),indent=2)
