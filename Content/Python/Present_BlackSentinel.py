"""Editor artwork of the installed hero; no gameplay session or level modification saved."""
import unreal,os,time,json
A=unreal.EditorAssetLibrary
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
mesh=A.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel')
clip=A.load_asset('/Game/Characters/BlackSentinel/Animations/BS_MM_Idle')
if not clip:
 clip=next((A.load_asset(p) for p in A.list_assets('/Game/Characters/BlackSentinel/Animations',recursive=True) if 'Idle' in p and isinstance(A.load_asset(p),unreal.AnimSequence)),None)
actor=sub.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(-1000,1500,10),unreal.Rotator(yaw=-90));actor.set_actor_label('PREVIEW_BlackSentinel_Unsaved')
c=actor.get_component_by_class(unreal.SkeletalMeshComponent);c.set_skeletal_mesh_asset(mesh);c.set_collision_profile_name('NoCollision')
if clip:c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE);c.play_animation(clip,True);c.set_update_animation_in_editor(True)
path=os.path.abspath(unreal.Paths.project_saved_dir()+'BlackSentinel_Player.png');photo={'time':time.monotonic(),'requested':False,'old':os.path.getmtime(path) if os.path.exists(path) else 0}
def sentinel_art_tick(dt):
 if not photo['requested']:
  eye=unreal.Vector(-655,1350,155);target=unreal.Vector(-1000,1500,115)
  editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,target));unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
  if time.monotonic()-photo['time']>4:photo['requested']=True;unreal.AutomationLibrary.take_high_res_screenshot(1280,900,path,delay=0.)
 if photo['requested'] and os.path.exists(path) and os.path.getmtime(path)>photo['old']:
  unreal.unregister_slate_post_tick_callback(photo['handle']);sub.destroy_actor(actor)
  unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
photo['handle']=unreal.register_slate_post_tick_callback(sentinel_art_tick)
