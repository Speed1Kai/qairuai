import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');R={'keys':[]}
for n in G.get_graph_editor_by_name(bp,'EventGraph').list_all_nodes():
 if n.get_name().startswith('CyborgModeKey_'):
  key=n.get_name().split('_')[-1];before=str(n.get_editor_property('input_key'));k=unreal.Key();k.set_editor_property('key_name',{'1':'One','2':'Two','3':'Three','4':'Four','Tab':'Tab'}[key]);n.set_editor_property('input_key',k);R['keys'].append({'key':key,'before':before,'after':str(n.get_editor_property('input_key'))})
for n in G.get_graph_editor_by_name(bp,'Modes_Init').list_all_nodes():
 if 'SocketName' in [str(p.get_pin_name()) for p in n.list_all_pins()]:R['old_socket']=pin(n,'SocketName').get_pin_value();val(pin(n,'SocketName'),'CC_Base_R_Hand')
# Each text call owns its scale multiplication, so this doesn't resize hit areas.
for graph in ('Modes_DrawHUD','Modes_DrawOneThreat'):
 for n in G.get_graph_editor_by_name(bp,graph).list_all_nodes():
  if str(n.get_node_title()).replace(' ','')=='DrawText':
   scale=pin(n,'Scale');connections=list(scale.list_connected_pins())
   if connections:
    calc=connections[0].get_owning_node();p=calc.find_input_pin('B')
    if p.is_valid() and not p.list_connected_pins() and not calc.get_name().startswith('TextScaleFixed_'):
     val(p,float(p.get_pin_value())*2.3);calc.rename('TextScaleFixed_'+calc.get_name())
compile_bp(bp);save(bp);R['saved']=True;json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'cyborg_modes_input_fix.json'),'w'),indent=2)

