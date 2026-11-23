"""Bake the actual player mesh into a lightweight holographic HUD texture.

This scene capture is editor-only. The shipped HUD uses a saved texture, not a
live camera or render target. Temporary preview actors are removed afterwards.
"""
import unreal,os,sys,time,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,V,save
ROOT='/Game/Characters/PlayerVisor';sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();tools=unreal.AssetToolsHelpers.get_asset_tools()
actors=[];state={'start':time.monotonic(),'captured':False};report={'saved':False}
def make_mat(name,value,wire=False):
 path=ROOT+'/'+name;m=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m);m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);m.set_editor_property('used_with_skeletal_mesh',True)
 m.set_editor_property('wireframe',wire)
 n=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);n.constant=unreal.LinearColor(value,value,value,1);M.connect_material_property(n,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(m);save(m);return m
base_mat=make_mat('M_DiagramCaptureFill',.07);wire_mat=make_mat('M_DiagramCaptureWire',.82,True)
mesh=A.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel');idle=A.load_asset('/Game/Characters/BlackSentinel/Animations/BS_MM_Idle')
body=sub.spawn_actor_from_class(unreal.SkeletalMeshActor,V((0,0,-40000)),unreal.Rotator(yaw=-90));actors.append(body)
c=body.get_component_by_class(unreal.SkeletalMeshComponent);c.set_skeletal_mesh_asset(mesh);c.set_material(0,base_mat);c.set_collision_profile_name('NoCollision')
c.set_editor_property('forced_lod_model',3);c.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
if idle:c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE);c.play_animation(idle,True);c.set_update_animation_in_editor(True)
wire=sub.spawn_actor_from_class(unreal.SkeletalMeshActor,V((0,0,-40000)),unreal.Rotator(yaw=-90));actors.append(wire)
wc=wire.get_component_by_class(unreal.SkeletalMeshComponent);wc.set_skeletal_mesh_asset(mesh);wc.set_material(0,wire_mat);wc.set_collision_profile_name('NoCollision');wc.set_editor_property('forced_lod_model',3);wc.set_leader_pose_component(c,True,False)
rt=unreal.RenderingLibrary.create_render_target2d(world,512,1024,unreal.TextureRenderTargetFormat.RTF_RGBA16F,unreal.LinearColor(0,0,0,0),False,False)
capture=sub.spawn_actor_from_class(unreal.SceneCapture2D,V((350,0,-39898)),unreal.Rotator(yaw=180));actors.append(capture)
cc=capture.get_component_by_class(unreal.SceneCaptureComponent2D)
cc.set_editor_property('projection_type',unreal.CameraProjectionMode.ORTHOGRAPHIC);cc.set_editor_property('ortho_width',132.)
cc.set_editor_property('texture_target',rt);cc.set_editor_property('capture_every_frame',False);cc.set_editor_property('capture_on_movement',False)
cc.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
cc.set_editor_property('primitive_render_mode',unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
cc.show_only_actor_components(body);cc.show_only_actor_components(wire)
def diagram_capture_tick(dt):
 try:
  age=time.monotonic()-state['start']
  if age<7:return
  if not state['captured']:
   cc.capture_scene();state['captured']=True;state['capture_time']=time.monotonic();return
  if time.monotonic()-state['capture_time']<2:return
  tex=unreal.RenderingLibrary.render_target_create_static_texture2d_editor_only(rt,ROOT+'/T_BlackSentinelDiagram',unreal.TextureCompressionSettings.TC_HDR,unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
  if not tex:raise RuntimeError('Could not bake the actual cyborg diagram')
  tex.set_editor_property('srgb',False);tex.set_editor_property('never_stream',True);save(tex)
  report.update(saved=True,texture=tex.get_path_name(),actual_player_mesh=mesh.get_path_name(),resolution=[512,1024],runtime_scene_capture=False)
 except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
 else:
  if not report['saved']:return
 unreal.unregister_slate_post_tick_callback(state['handle'])
 for a in actors:sub.destroy_actor(a)
 with open(os.path.join(unreal.Paths.project_saved_dir(),'visor_hero_diagram.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
state['handle']=unreal.register_slate_post_tick_callback(diagram_capture_tick)
