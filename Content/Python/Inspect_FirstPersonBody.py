import unreal,sys,os,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');r={'components':[],'nodes':[]}
for h,c,n in components(bp):
 if not c or not isinstance(c,unreal.SceneComponent):continue
 d={'name':n,'class':c.get_class().get_name(),'location':str(c.get_editor_property('relative_location')),'rotation':str(c.get_editor_property('relative_rotation')),'scale':str(c.get_editor_property('relative_scale3d'))}
 if isinstance(c,unreal.SkeletalMeshComponent):
  d.update(mesh=str(c.get_skinned_asset()),owner_no_see=c.get_editor_property('owner_no_see'),bones=[str(c.get_bone_name(i)) for i in range(c.get_num_bones())])
 r['components'].append(d)
e=G.get_graph_editor_by_name(bp,'EventGraph')
for n in e.list_all_nodes():
 q=n.find_input_pin('bNewOwnerNoSee')
 if q.is_valid():r['nodes'].append({'name':n.get_name(),'inputs':[{ 'name':str(p.get_pin_name()),'value':str(p.get_pin_value()),'links':[str(x.get_owning_node().get_name())+'.'+str(x.get_pin_name()) for x in p.list_connected_pins()]} for p in n.list_input_pins()]})
open(unreal.Paths.project_saved_dir()+'first_person_body_inspection.json','w').write(json.dumps(r,indent=2))
