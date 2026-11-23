"""Static character art preview; never starts gameplay or saves the map."""
import unreal,os,json,time,traceback
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);world=editor.get_editor_world();root='/Game/Characters/FinalSentinel/'
folder='S:/Final_Protocol/Saved/HeroCyborgPreview';os.makedirs(folder,exist_ok=True)
origin=unreal.Vector(0,0,5000)
a=sub.spawn_actor_from_class(unreal.SkeletalMeshActor,origin,unreal.Rotator());mesh=a.skeletal_mesh_component;mesh.set_skeletal_mesh_asset(unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'));mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
for i in range(mesh.get_num_materials()):mesh.set_material(i,unreal.load_asset(root+('M_HeroBaseMetal' if i==0 else 'M_HeroGraphite')))
costume=sub.spawn_actor_from_class(unreal.BlueprintEditorLibrary.generated_class(unreal.load_asset(root+'BP_FinalSentinelArmour')),origin,unreal.Rotator())
specs=json.load(open('S:/Final_Protocol/Content/Characters/FinalSentinel/Source/hero_armour_manifest.json'))
for spec in specs:
 c=next(c for c in costume.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()==spec['name'])
 c.call_method('K2_AttachToComponent',(mesh,unreal.Name(spec['bone']),unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False));c.set_visibility(True)
cube=unreal.load_asset('/Engine/BasicShapes/Cube')
for p,scale in [((0,0,4997),(8,8,.05)),((0,-160,5150),(8,.05,5))]:
 a=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*p),unreal.Rotator());a.static_mesh_component.set_static_mesh(cube);a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_material(0,unreal.load_asset('/Game/LabTutorial/FirstFloor/M_LabGraphite'))
for p,power,col in [((130,170,5260),5000,(.75,.88,1)),((-180,100,5180),3000,(1,.8,.55)),((0,-90,5240),4000,(.3,.65,1))]:
 a=sub.spawn_actor_from_class(unreal.PointLight,unreal.Vector(*p),unreal.Rotator());c=a.point_light_component;c.set_intensity(power);c.set_attenuation_radius(750);c.set_cast_shadows(False);c.set_light_color(unreal.LinearColor(r=col[0],g=col[1],b=col[2],a=1));c.set_editor_property('source_radius',40.)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
for cmd in ('t.MaxFPS 20','r.Streaming.PoolSize 1000'):unreal.SystemLibrary.execute_console_command(world,cmd)
editor.set_level_viewport_camera_info(unreal.Vector(60,140,5110),unreal.MathLibrary.find_look_at_rotation(unreal.Vector(60,140,5110),unreal.Vector(0,0,5095)))
started=time.monotonic();done=False;busy=False
def tick(dt):
 global done,busy
 if busy:return
 busy=True
 try:
  elapsed=time.monotonic()-started
  if elapsed>14 and not done:
   done=True;unreal.AutomationLibrary.take_high_res_screenshot(1000,1000,folder+'/FinalSentinel.png',delay=1.)
  if elapsed>25:
   unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
 except Exception:
  with open(folder+'/error.txt','w') as f:f.write(traceback.format_exc())
  unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
 finally:busy=False
handle=unreal.register_slate_post_tick_callback(tick);unreal.EditorPythonScripting.set_keep_python_script_alive(True)
