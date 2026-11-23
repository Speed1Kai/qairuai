"""Static editor artwork: inspect the imported module before perimeter use."""
import unreal,os,time
ROOT='/Game/Surface/CampusWall'
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh=unreal.EditorAssetLibrary.load_asset(ROOT+'/SM_Wall_A_Long')
b=mesh.get_bounding_box();s=500./(b.max.z-b.min.z)
actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(15000,10000,b.max.z*s+3),unreal.Rotator(roll=180))
actor.set_actor_label('TEMP_WallAssetArtwork');actor.static_mesh_component.set_static_mesh(mesh)
actor.set_actor_scale3d(unreal.Vector(s,s*.3,s));actor.static_mesh_component.set_collision_profile_name('NoCollision')
path=os.path.abspath(unreal.Paths.project_saved_dir()+'CampusWall_Asset.png')
photo={'requested':False,'since':time.monotonic(),'old_mtime':os.path.getmtime(path) if os.path.exists(path) else 0}
def wall_art_tick(dt):
 elapsed=time.monotonic()-photo['since']
 if not photo['requested']:
  eye=unreal.Vector(15850,9100,490);target=unreal.Vector(15000,10000,220)
  editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,target))
  unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
  if elapsed>5:
   photo['requested']=True;unreal.AutomationLibrary.take_high_res_screenshot(1280,800,path,delay=0.)
 if photo['requested'] and os.path.exists(path) and os.path.getmtime(path)>photo['old_mtime']:
  unreal.unregister_slate_post_tick_callback(photo['handle']);sub.destroy_actor(actor)
  unreal.EditorLoadingAndSavingUtils.load_map('/Game/Cinematics/Prologue/Lvl_Prologue')
photo['handle']=unreal.register_slate_post_tick_callback(wall_art_tick)
