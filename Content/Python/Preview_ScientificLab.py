"""Static source-art preview; never starts gameplay."""
import unreal,time,os
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Environment/ScientificLab/Lvl_SourcePreview')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not any(a.get_actor_label()=='ART_PreviewLight' for a in sub.get_all_level_actors()):
 a=sub.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,10000),unreal.Rotator(pitch=-50,yaw=-35));a.set_actor_label('ART_PreviewLight');a.light_component.set_intensity(3)
 for x,y in [(-5000,-3000),(5000,6000)]:
  a=sub.spawn_actor_from_class(unreal.PointLight,unreal.Vector(x,y,4500));a.set_actor_label('ART_PreviewFill');c=a.point_light_component;c.set_intensity(180000);c.set_attenuation_radius(25000);c.set_cast_shadows(False)
ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ed.set_level_viewport_camera_info(unreal.Vector(6000,-7000,1900),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(6000,-7000,1900),unreal.Vector(-3000,5500,2000)))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
start=time.monotonic()
def scientific_photo(dt):
 if time.monotonic()-start<12:return
 unreal.unregister_slate_post_tick_callback(scientific_handle)
 unreal.AutomationLibrary.take_high_res_screenshot(1440,900,os.path.abspath(unreal.Paths.project_saved_dir()+'ScientificLab_Source.png'),delay=0.)
scientific_handle=unreal.register_slate_post_tick_callback(scientific_photo)
