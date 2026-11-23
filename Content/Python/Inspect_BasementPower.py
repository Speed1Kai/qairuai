import unreal,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
r={'lights':[],'south':[]}
for a in sub.get_all_level_actors():
 n=a.get_actor_label()
 if isinstance(a,unreal.Light):r['lights'].append({'name':n,'class':a.get_class().get_name(),'p':str(a.get_actor_location())})
 if n=='LAB_Corridor_Wall_South':r['south'].append({'p':str(a.get_actor_location()),'scale':str(a.get_actor_scale3d())})
bp=unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
subo=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
r['player_components']=[]
for h in subo.k2_gather_subobject_data_for_blueprint(bp):
 c=lib.get_object_for_blueprint(lib.get_data(h),bp)
 if isinstance(c,unreal.SkeletalMeshComponent):r['player_components'].append({'name':str(lib.get_variable_name(lib.get_data(h))),'mesh':str(c.get_skeletal_mesh_asset())})
with open('S:/Final_Protocol/Saved/basement_power_before.json','w') as f:json.dump(r,f,indent=2)
