import unreal,json,traceback
r={}
try:
 w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);m=p.mesh;c=p.get_editor_property('FirstPersonCamera')
 r.update(actor_rotation=str(p.get_actor_rotation()),control_rotation=str(p.get_control_rotation()),mesh_relative_rotation=str(m.get_editor_property('relative_rotation')),mesh_relative_location=str(m.get_editor_property('relative_location')),camera_location=str(c.get_world_location()),camera_rotation=str(c.get_world_rotation()),camera_relative=str(c.get_editor_property('relative_location')),yaw_enabled=p.get_editor_property('use_controller_rotation_yaw'))
 t=p.get_actor_transform();r['bones']={}
 for n in ('CC_Base_Hip','CC_Base_Head','CC_Base_L_Foot','CC_Base_R_Foot','CC_Base_L_Hand','CC_Base_R_Hand','CC_Base_L_Upperarm','CC_Base_R_Upperarm'):
  pos=m.get_socket_location(n);r['bones'][n]={'world':str(pos),'actor_local':str(unreal.MathLibrary.inverse_transform_location(t,pos))}
except Exception:r['error']=traceback.format_exc()
open(unreal.Paths.project_saved_dir()+'body_camera_center_inspection.json','w').write(json.dumps(r,indent=2))
