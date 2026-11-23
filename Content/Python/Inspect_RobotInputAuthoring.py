import unreal,json
bp=unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
r={'actions':[n for n in e.list_available_nodes([]) if 'hift' in n.lower() or n.endswith('|K')],'keys':[]}
for node in e.list_all_nodes():
 if node.get_class().get_name()!='K2Node_InputKey':continue
 r['keys'].append({'key':str(node.get_editor_property('input_key')),'pins':[str(p.get_pin_name()) for p in node.list_all_pins()]})
 p=node.find_output_pin('Pressed');r['pin_methods']=[s for s in dir(p) if not s.startswith('_')]
with open('S:/Final_Protocol/Saved/robot_input_authoring.json','w') as f:json.dump(r,f,indent=2)
