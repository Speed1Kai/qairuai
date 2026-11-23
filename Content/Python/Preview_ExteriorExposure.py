import unreal
w=unreal.EditorLevelLibrary.get_game_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if isinstance(a,unreal.DirectionalLight):a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.)
 if a.get_class().get_name()=='BP_CampusReadability_C':
  for c in a.get_components_by_class(unreal.PostProcessComponent):
   s=c.settings
   for k,v in [('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),('auto_exposure_apply_physical_camera_exposure',False),('auto_exposure_bias',0.),('ambient_cubemap_intensity',.5)]:s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
   s.set_editor_property('ambient_cubemap',unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));c.set_editor_property('settings',s)
