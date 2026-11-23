import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import components,B,G
bp=unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
e=G.get_graph_editor_by_name(bp,'EventGraph')
r={'members':list(map(str,B.list_member_variable_names(bp))),'components':[],'events':[],'methods':{}}
for h,c,n in components(bp):
 if not c:continue
 d={'name':n,'class':c.get_class().get_name()}
 if isinstance(c,unreal.CameraComponent):d.update(location=str(c.get_editor_property('relative_location')),active=c.get_editor_property('auto_activate'))
 r['components'].append(d)
for n in e.list_all_nodes():
 if n.get_class().get_name() in ['K2Node_Event','K2Node_InputKey']:r['events'].append({'name':n.get_name(),'title':str(n.get_node_title()),'outputs':str(n)})
for cl in [unreal.WidgetTree,unreal.MaterialExpressionCustom,unreal.CameraComponent,unreal.CanvasPanelSlot]:r['methods'][cl.__name__]=cl.__doc__
r['nodes']=[x for x in e.list_available_nodes([]) if any(k in x for k in ['|KeyboardEvents|V','AnyDamage','GetFloatProperty','GetDoubleProperty','SetOwnerNoSee','SetActive'])]
with open(os.path.join(unreal.Paths.project_saved_dir(),'visor_api.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
