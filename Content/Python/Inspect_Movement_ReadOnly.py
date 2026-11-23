import unreal,json,os
B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
bp=unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');e=G.get_graph_editor_by_name(bp,'EventGraph')
r={'graphs':{},'components':[],'menus':[str(x) for x in e.list_available_nodes([]) if any(k in str(x).lower() for k in ['tick','landed','keyboardevents|c','keyboardevents|leftshift','keyboardevents|capslock'])]}
for name in B.list_graph_names(bp):
 ed=G.get_graph_editor_by_name(bp,name)
 r['graphs'][str(name)]=[{'title':str(n.get_node_title()),'class':n.get_class().get_name(),'pins':[(str(p.get_pin_name()),p.get_pin_value()) for p in n.list_all_pins()]} for n in ed.list_all_nodes()]
s=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
props=['max_walk_speed','max_acceleration','ground_friction','braking_deceleration_walking','gravity_scale','jump_z_velocity','air_control','falling_lateral_friction','braking_deceleration_falling','max_walk_speed_crouched','rotation_rate','orient_rotation_to_movement','capsule_half_height','capsule_radius','relative_location','target_arm_length','socket_offset','nav_agent_props']
for h in s.k2_gather_subobject_data_for_blueprint(bp):
 o=lib.get_object_for_blueprint(lib.get_data(h),bp)
 if not o:continue
 d={'name':o.get_name(),'class':o.get_class().get_name(),'values':{}}
 for p in props:
  try:d['values'][p]=str(o.get_editor_property(p))
  except:pass
 r['components'].append(d)
with open(os.path.join(unreal.Paths.project_saved_dir(),'movement_inspection.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('MOVEMENT INSPECTION COMPLETE')
