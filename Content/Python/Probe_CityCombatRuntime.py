import unreal,json,os
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0)
R={'cameras':[],'npc':[],'control':str(p.get_controller().get_control_rotation()),'camera':str(unreal.GameplayStatics.get_player_camera_manager(w,0).get_camera_location())}
for c in p.get_components_by_class(unreal.SceneComponent):
 if isinstance(c,(unreal.CameraComponent,unreal.SpringArmComponent)):
  R['cameras'].append(dict(name=c.get_name(),rot=str(c.get_world_rotation()),active=c.is_active(),usecontrol=c.get_editor_property('use_pawn_control_rotation'),parent=str(c.get_attach_parent()),relative=str(c.get_relative_transform()),absolute=c.get_editor_property('absolute_rotation')))
for n in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Character):
 if not n.get_class().get_name().startswith('BP_Enceladus_'):continue
 c=n.get_controller();path=unreal.NavigationSystemV1.find_path_to_actor_synchronously(w,n.get_actor_location(),p,pathfinding_context=n)
 R['npc'].append(dict(name=n.get_name(),pos=str(n.get_actor_location()),cmc=str(n.character_movement.movement_mode),speed=n.character_movement.max_walk_speed,path_valid=path.is_valid() if path else None,path_partial=path.is_partial() if path else None,points=[str(v) for v in path.path_points] if path else [],controller=str(c),visibility=str(n.get_component_by_class(unreal.CapsuleComponent).get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))))
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'citycombat_diagnostic.json'),'w'),indent=2)

