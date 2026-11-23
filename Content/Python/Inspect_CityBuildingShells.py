import json
import os
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not editor.get_game_world()
report = {}

def xyz(value):
    return [value.x, value.y, value.z]

for name in ('Lvl_CampusConnected', 'Lvl_SurfaceArrival'):
    assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/' + name)
    entries = []
    for actor in actors.get_all_level_actors():
        label = actor.get_actor_label()
        if not (label.startswith('CITY_Residential_') or label in ('CITY_FirstDowntownBlock', 'SURF_Environment')):
            continue
        origin, extent = actor.get_actor_bounds(False)
        row = dict(label=label, origin=xyz(origin), extent=xyz(extent), location=xyz(actor.get_actor_location()), components=[])
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.static_mesh
            if not mesh:
                continue
            count = component.get_instance_count() if isinstance(component, unreal.InstancedStaticMeshComponent) else 1
            box = mesh.get_bounding_box()
            row['components'].append(dict(name=component.get_name(), mesh=mesh.get_path_name(), count=count,
                profile=str(component.get_collision_profile_name()), size=xyz(box.max-box.min)))
        entries.append(row)
    report[name] = entries

with open(os.path.join(unreal.Paths.project_saved_dir(), 'city_building_shells.json'), 'w') as output:
    json.dump(report, output, indent=2)
editor.set_level_viewport_camera_info(unreal.Vector(x=-6500,y=23200,z=4300),unreal.Rotator(pitch=-17,yaw=35,roll=0))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
