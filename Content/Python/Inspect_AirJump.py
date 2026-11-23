import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
r={'variables':list(map(str,B.list_member_variable_names(bp))),'graphs':{},'components':[],'particles':[]}
for name in B.list_graph_names(bp):
 if str(name) not in ('EventGraph','Move') and not any(k in str(name) for k in ('Sprint','Jump','Crouch','Move','UpdateState','ResolveSpeed','Land')):continue
 r['graphs'][str(name)]=[{'name':n.get_name(),'class':n.get_class().get_name(),'title':str(n.get_node_title()),'pins':[{'name':str(p.get_pin_name()),'value':p.get_pin_value(),'links':[str(c.get_owning_node().get_name())+'.'+str(c.get_pin_name()) for c in p.list_connected_pins()]} for p in n.list_all_pins()]} for n in G.get_graph_editor_by_name(bp,name).list_all_nodes()]
for h,c,n in components(bp):
 if not c:continue
 d={'name':n,'class':c.get_class().get_name(),'props':{}}
 for k in ('gravity_scale','jump_z_velocity','max_walk_speed','max_fly_speed','max_acceleration','air_control','braking_deceleration_falling','falling_lateral_friction','relative_location','relative_rotation','relative_scale3d','capsule_half_height','skeletal_mesh_asset','active','auto_activate'):
  try:d['props'][k]=str(c.get_editor_property(k))
  except:pass
 r['components'].append(d)
for path in ['/Game/CityDowntown/Effects/P_Steam_Lit','/Game/CityDowntown/Effects/P_Steam_Lit2']:
 p=A.load_asset(path);d={'asset':path,'class':p.get_class().get_name()}
 try:
  d['emitters']=[]
  for e in p.get_editor_property('emitters'):
   q={'name':e.get_name(),'lods':[]}
   for lod in e.get_editor_property('lod_levels'):
    mods=[]
    for m in lod.get_editor_property('modules'):
     mods.append({'class':m.get_class().get_name(),'name':m.get_name(),'text':m.export_text() if hasattr(m,'export_text') else ''})
    q['lods'].append({'modules':mods,'required':str(lod.get_editor_property('required_module'))})
   d['emitters'].append(q)
 except Exception as ex:d['error']=str(ex)
 r['particles'].append(d)
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'airjump_inspection.json'),'w'),ensure_ascii=False,indent=2)
unreal.log('AIRJUMP READONLY INSPECTION COMPLETE')
