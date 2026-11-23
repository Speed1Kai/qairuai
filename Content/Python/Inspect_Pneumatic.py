import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G
R={};w=unreal.EditorLevelLibrary.get_game_world()
if w:
 p=unreal.GameplayStatics.get_player_character(w,0)
 for n in ('PneumaticDirection','PneumaticMoveAxis','bPneumaticDash','PneumaticDashCount','bPneumaticPending','AirJetInputPresses','AirJetInputReleases','AirJetHoldTime'):
  R[n]=str(p.get_editor_property(n))
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
for fn in ('Pneumatic_CaptureDirection','Pneumatic_Update','Pneumatic_StartDash'):
 e=G.get_graph_editor_by_name(bp,fn)
 R[fn]=[dict(name=n.get_name(),title=str(n.get_node_title()),pins=[dict(name=str(p.get_pin_name()),value=str(p.get_pin_value()),links=[str(q.get_owning_node().get_name())+'.'+str(q.get_pin_name()) for q in p.list_connected_pins()]) for p in n.list_all_pins()]) for n in e.list_all_nodes()]
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'pneumatic_inspect.json'),'w'),indent=2)
