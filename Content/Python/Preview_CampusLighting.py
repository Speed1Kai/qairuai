import unreal
w=unreal.EditorLevelLibrary.get_game_world()
sky=unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w,unreal.SkyLight,unreal.Transform())
sky=unreal.GameplayStatics.finish_spawning_actor(sky,unreal.Transform());c=sky.get_component_by_class(unreal.SkyLightComponent);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP);c.set_editor_property('cubemap',unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));c.set_intensity(1.6);c.set_editor_property('lower_hemisphere_is_black',False);c.recapture_sky()
pp=unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w,unreal.PostProcessVolume,unreal.Transform());pp=unreal.GameplayStatics.finish_spawning_actor(pp,unreal.Transform());pp.set_editor_property('unbound',True);pp.set_editor_property('priority',100.)
s=pp.settings
for k,v in [('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.),('auto_exposure_bias',.5),('vignette_intensity',.15)]:s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
pp.set_editor_property('settings',s)
