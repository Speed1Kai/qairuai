import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');r={'graphs':list(map(str,B.list_graph_names(bp))),'functions':{}}
for name in ['View_ApplyBodyVisibility','View_UpdateBodyCamera','View_AlignBodyToCamera','EventGraph']:
 try:
  e=G.get_graph_editor_by_name(bp,name);r['functions'][name]=[]
  for n in e.list_all_nodes():
   ps=[{'name':str(q.get_pin_name()),'value':q.get_pin_value(),'links':[x.get_owning_node().get_name()+'.'+str(x.get_pin_name()) for x in q.list_connected_pins()]} for q in n.list_all_pins()]
   if name!='EventGraph' or any(q['name'] in ['NewRotation','NewTransform'] for q in ps) or n.get_name()=='FullBodyViewSwitch':r['functions'][name].append({'node':n.get_name(),'title':str(n.get_node_title()),'pins':ps})
 except Exception as ex:r['functions'][name]=str(ex)
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'view_restore_inspect.json'),'w'),indent=2)
