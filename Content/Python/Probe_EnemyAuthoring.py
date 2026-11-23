import unreal,json,os
out={'classes':{},'names':[n for n in dir(unreal) if any(s in n for s in ('EnumEditor','EnumLibrary','BehaviorTree','Blackboard','AnimBlueprint','AnimationState','AnimGraph','StateMachine'))]}
for n in ('BehaviorTree','BlackboardData','BlackboardEntry','BTCompositeChild','BTComposite_Selector','BTTask_MoveTo','BTDecorator_Blackboard','BlackboardKeySelector','EnumFactory','UserDefinedEnum','AnimBlueprintFactory','AnimationBlueprintLibrary','AnimBlueprintLibrary','AnimGraphNode_StateMachine','AISenseConfig_Sight','AIPerceptionComponent'):
 cls=getattr(unreal,n,None)
 if cls:out['classes'][n]=[m for m in dir(cls) if not m.startswith('_')]
tree=unreal.new_object(unreal.BehaviorTree)
sel=unreal.new_object(unreal.BTComposite_Selector,outer=tree)
for obj,props in [(tree,('root_node','blackboard_asset','bt_graph')),(sel,('children','services','node_name'))]:
 for p in props:
  try:
   value=obj.get_editor_property(p);out[obj.get_class().get_name()+'.'+p]=str(value)
   obj.set_editor_property(p,value)
  except Exception as ex:out[obj.get_class().get_name()+'.'+p]=str(ex)
bp=unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed')
out['anim_graphs']=list(map(str,unreal.BlueprintEditorLibrary.list_graph_names(bp)))
for graph in out['anim_graphs']:
 try:
  e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,graph)
  out['graph_'+graph]=[{'class':n.get_class().get_name(),'title':str(n.get_node_title()),'pins':[str(p.get_pin_name()) for p in n.list_all_pins()]} for n in e.list_all_nodes()]
 except Exception as ex:out['graph_'+graph]=str(ex)
sk=unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
out['mesh']={'materials':[str(s.material_slot_name) for s in sk.materials],'skeleton':str(sk.skeleton),'physics':str(sk.physics_asset)}
with open('S:/Final_Protocol/Saved/enemy_authoring_probe.json','w',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
