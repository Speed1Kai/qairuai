import unreal,json,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
r={'defaults':{},'nodes':[]};cdo=unreal.get_default_object(B.generated_class(bp))
for name in B.list_member_variable_names(bp):
 if any(x in str(name).lower() for x in ('speed','sprint','energy','walk')):
  try:r['defaults'][str(name)]=str(cdo.get_editor_property(str(name)))
  except:pass
for gn in B.list_graph_names(bp):
 for n in G.get_graph_editor_by_name(bp,gn).list_all_nodes():
  title=str(n.get_node_title())
  pins=[]
  for p in n.list_all_pins():
   try:pins.append({'name':str(p.get_pin_name()),'value':str(p.get_pin_value()),'links':[str(q.get_pin_name()) for q in p.list_connected_pins()]})
   except:pass
  if any(x in title.lower() for x in ('speed','sprint','energy','select float','выбрать float')) or any(p['name'] in ('MaxWalkSpeed','VisorSprintEnergyDrain','VisorEnergyRegen') or p['value']=='MaxWalkSpeed' for p in pins):
   r['nodes'].append({'graph':str(gn),'node':n.get_name(),'title':title,'pins':pins})
with open(os.path.join(unreal.Paths.project_saved_dir(),'run_balance_inspect.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
