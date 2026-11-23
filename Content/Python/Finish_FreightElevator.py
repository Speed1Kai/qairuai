"""Finalize the saved elevator asset, without starting PIE."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,compile_bp,save,components
bp=A.load_asset('/Game/LabTutorial/Elevator/BP_FreightElevator');compile_bp(bp)
cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',50);save(bp)
g=G.get_graph_editor_by_name(bp,'EventGraph')
record={'compiled':True,'input_priority':50,'gameplay_playtest_run':False,'timelines':[],'F_key_connections':0,'components':[]}
for node in g.list_all_nodes():
 if node.get_class().get_name()=='K2Node_Timeline':record['timelines'].append({'name':str(node.get_node_title()),'update_connections':len(node.find_output_pin('Update').list_connected_pins()),'finished_connections':len(node.find_output_pin('Finished').list_connected_pins())})
 if node.get_class().get_name()=='K2Node_InputKey':record['F_key_connections']=len(node.find_output_pin('Pressed').list_connected_pins())
for h,c,n in components(bp):
 row={'name':n,'class':c.get_class().get_name()}
 if isinstance(c,unreal.SceneComponent):
  p=c.get_editor_property('relative_location');row['local_location_cm']=[p.x,p.y,p.z]
 if isinstance(c,unreal.PrimitiveComponent):row['collision']=str(c.get_collision_profile_name())
 record['components'].append(row)
path=os.path.join(unreal.Paths.project_saved_dir(),'freight_elevator_report.json')
with open(path,encoding='utf8') as f:r=json.load(f)
r['authoring']=record
with open(path,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('FREIGHT ELEVATOR FINAL ASSET SAVED')
