import unreal
w=unreal.EditorLevelLibrary.get_game_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if isinstance(a,unreal.DirectionalLight):a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.)
 if a.get_class().get_name()=='BP_CampusReadability_C':
  for c in a.get_components_by_class(unreal.PostProcessComponent):
   c.set_editor_property('unbound',True);s=c.settings;s.set_editor_property('ambient_cubemap_intensity',.5);s.set_editor_property('auto_exposure_bias',0.);c.set_editor_property('settings',s)

