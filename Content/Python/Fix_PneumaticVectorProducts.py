"""Repair only the newly authored scalar vector products; preserve all systems."""
import unreal,os,sys,json,shutil,datetime
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,Graph,pin,val,link,compile_bp,save
assert not unreal.EditorLevelLibrary.get_game_world()
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups/PneumaticDodge',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),backup)
R={}
for fn,constants in [('Pneumatic_CaptureDirection',[None,None,-1.]),('Pneumatic_Orbs',[-.45,-1.,-.45,-1.]),('Pneumatic_StartDash',[None])]:
 e=G.get_graph_editor_by_name(bp,fn);g=Graph(bp);g.e=e
 nodes=[n for n in e.list_all_nodes() if str(n.get_node_title())=='vector * vector']
 if not nodes:continue
 assert len(nodes)==len(constants),(fn,len(nodes))
 for n,constant in zip(nodes,constants):
  aa=list(pin(n,'A').list_connected_pins());bb=list(pin(n,'B').list_connected_pins());outs=list(pin(n,'ReturnValue',True).list_connected_pins());assert len(aa)==1
  scalar=bb[0] if bb else constant;assert scalar is not None
  br=g.call('Engine.KismetMathLibrary.BreakVector',InVec=aa[0]);xyz={}
  for k in ('X','Y','Z'):xyz[k]=g.math('Multiply_DoubleDouble',A=g.out(br,k),B=scalar)
  v=g.math('MakeVector',**xyz)
  pin(n,'ReturnValue',True).break_pin_links()
  for p in outs:link(v,p)
  e.remove_nodes([n])
 R[fn]=len(nodes)
e=G.get_graph_editor_by_name(bp,'Pneumatic_Update');g=Graph(bp);g.e=e
nodes=[n for n in e.list_all_nodes() if str(n.get_node_title())=='vector * vector'];assert len(nodes)==2
outer=next(n for n in nodes if any(str(p.get_pin_name())=='PneumaticDirection' for p in pin(n,'A').list_connected_pins()))
inner=next(n for n in nodes if n!=outer)
direction=list(pin(outer,'A').list_connected_pins())[0];speed=list(pin(inner,'A').list_connected_pins())[0];taper=list(pin(inner,'B').list_connected_pins())[0]
outs=list(pin(outer,'ReturnValue',True).list_connected_pins());pin(outer,'ReturnValue',True).break_pin_links()
br=g.call('Engine.KismetMathLibrary.BreakVector',InVec=direction)
scaled=g.math('Multiply_DoubleDouble',A=speed,B=taper)
v=g.math('MakeVector',**{k:g.math('Multiply_DoubleDouble',A=g.out(br,k),B=scaled) for k in ('X','Y','Z')})
for p in outs:link(v,p)
e.remove_nodes(nodes);R['Pneumatic_Update']=2
compile_bp(bp);save(bp)
json.dump({'saved':True,'replaced':R,'backup':backup},open(os.path.join(unreal.Paths.project_saved_dir(),'pneumatic_vector_fix.json'),'w'),indent=2)
