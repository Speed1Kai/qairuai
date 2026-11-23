"""Apply city offset to static instance data and leave the awakening level open."""
import unreal,sys,os,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,V,components,compile_bp,save
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
city=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='SURF_Environment')
data={'actor_location':str(city.get_actor_location()),'components':[]}
for c in city.get_components_by_class(unreal.InstancedStaticMeshComponent):
 if c.static_mesh and c.static_mesh.get_name().startswith('SM_Ruin_') and c.get_instance_count():data['components'].append({'mesh':c.static_mesh.get_name(),'local':str(c.get_instance_transform(0,False).translation),'world':str(c.get_instance_transform(0,True).translation)})
path='S:/Final_Protocol/Saved/campus_city_offset.json'
with open(path,'w') as f:json.dump(data,f,indent=2)
for path,label,offset in [('/Game/Surface/BP_SurfaceEnvironment','SURF_Environment',(0,26000,0)),('/Game/Surface/BP_LaboratoryCampus','CAMPUS_LaboratoryGrounds',(0,0,0))]:
 bp=A.load_asset(path)
 for h,c,n in components(bp):
  if c and isinstance(c,unreal.SceneComponent):c.set_mobility(unreal.ComponentMobility.STATIC)
 compile_bp(bp);save(bp)
 actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()==label)
 root=actor.root_component;root.set_mobility(unreal.ComponentMobility.STATIC)
 if not sub.set_actor_transform(actor,unreal.Transform(location=V(offset))):raise RuntimeError('Editor actor transform failed '+label)
 for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
  c.set_mobility(unreal.ComponentMobility.STATIC)
  c.call_method('K2_AttachToComponent',(root,unreal.Name('None'),unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False))
 if label=='SURF_Environment':
  sample=next(c for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Ruin_A')
  data['corrected_actor_location']=str(actor.get_actor_location());data['corrected_first_building_world']=str(sample.get_instance_transform(0,True).translation)
  with open('S:/Final_Protocol/Saved/campus_city_offset.json','w') as f:json.dump(data,f,indent=2)
unreal.EditorLoadingAndSavingUtils.save_current_level()
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
editor.set_level_viewport_camera_info(V((-200,-300,210)),unreal.Rotator(pitch=-4,yaw=130))
