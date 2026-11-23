import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components
r={'actors':[],'blueprints':{}}
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 n=a.get_actor_label();p=a.get_actor_location()
 if p.z<600 and (any(x in n.lower() for x in ['computer','terminal','desk','bench','monitor','screen','holo','power','lift','freight']) or (abs(p.y)<900 and abs(p.x)<1100)):
  r['actors'].append({'name':n,'class':a.get_class().get_path_name(),'p':[p.x,p.y,p.z],'r':str(a.get_actor_rotation())})
paths=['/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional','/Game/LabTutorial/Basement/BP_BuildingPower','/Game/LabTutorial/Holograms/BP_ArchiveProjector_01']
for path in paths:
 bp=A.load_asset(path);e=G.get_graph_editor_by_name(bp,'EventGraph');ns=[]
 for n in e.list_all_nodes():
  if n.get_class().get_name()=='K2Node_InputKey' or n.find_input_pin('WidgetType').is_valid() or n.find_input_pin('ZOrder').is_valid():ns.append({'name':n.get_name(),'title':str(n.get_node_title()),'pins':[{'n':str(p.get_pin_name()),'value':p.get_pin_value()} for p in n.list_all_pins()]})
 r['blueprints'][path]={'nodes':ns,'components':[{'name':n,'class':c.get_class().get_name(),'p':str(c.get_editor_property('relative_location')) if isinstance(c,unreal.SceneComponent) else ''} for h,c,n in components(bp) if c]}
with open(os.path.join(unreal.Paths.project_saved_dir(),'interaction_upgrade_inspect.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
