import unreal,json,os
w=unreal.EditorLevelLibrary.get_game_world();r=[]
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if isinstance(a,unreal.DirectionalLight):a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(300.)
 if a.get_class().get_name()=='BP_CampusReadability_C':
  for c in a.get_components_by_class(unreal.SkyLightComponent):c.set_intensity(3.);c.recapture_sky();r.append(str(c.cubemap))
  for c in a.get_components_by_class(unreal.PostProcessComponent):
   s=c.settings;s.set_editor_property('auto_exposure_bias',1.5);c.set_editor_property('settings',s)
 if a.get_class().get_name()=='BP_SurfaceArrival_C':
  try:a.call_method('ReceiveBeginPlay')
  except:pass
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'sky_recapture.json'),'w'))
