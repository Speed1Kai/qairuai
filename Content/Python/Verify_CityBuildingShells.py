"""Reload both saved maps and check the same capsule profile used in flight."""
import json
from pathlib import Path
import traceback
import unreal

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
saved = Path(unreal.Paths.project_saved_dir())
result = {'maps': {}}

def vector(x=0, y=0, z=0):
    return unreal.Vector(x=x, y=y, z=z)

def sweep(world, start, end):
    hit = unreal.SystemLibrary.capsule_trace_single_by_profile(
        world, start, end, 42, 96, 'Pawn', False, [], unreal.DrawDebugTrace.NONE, False)
    return hit is not None

try:
    for name in ('Lvl_CampusConnected', 'Lvl_SurfaceArrival'):
        assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/' + name)
        scene = actors.get_all_level_actors()
        world = editor.get_editor_world()
        shells = [a for a in scene if a.get_actor_label().startswith('CITY_Shell_')]
        assert len(shells) == 4
        wall_checks = {}
        for shell in shells:
            center, extent = shell.get_actor_bounds(False)
            starts = [center + vector(x=sign*(extent.x + 330)) for sign in (-1, 1)]
            starts += [center + vector(y=sign*(extent.y + 330)) for sign in (-1, 1)]
            starts.append(center + vector(z=extent.z + 200))
            wall_checks[shell.get_actor_label()] = [sweep(world, start, center) for start in starts]
        assert all(all(checks) for checks in wall_checks.values()), wall_checks
        city = next(a for a in scene if a.get_actor_label() == 'CITY_FirstDowntownBlock')
        frame = city.get_actor_transform()
        a, b = [unreal.MathLibrary.transform_location(frame, vector(y=y, z=400)) for y in (24500, 33500)]
        assert not sweep(world, a, b), 'Main street blocked'
        landscape = next(a for a in scene if a.get_actor_label() == 'SURF_Environment')
        ruins = [c for c in landscape.get_components_by_class(unreal.StaticMeshComponent)
                 if c.static_mesh and c.static_mesh.get_name().startswith(('SM_Ruin_', 'SM_ArchitectTower'))]
        assert len(ruins) == 5 and all(str(c.get_collision_profile_name()) == 'BlockAll' for c in ruins)
        assert sum(a.get_actor_label().startswith('CITY_Enceladus_') for a in scene) == 6
        assert sum(a.get_actor_label() == 'CITY_LunarAeroPod' for a in scene) == 1
        result['maps'][name] = dict(walls_and_roofs=wall_checks, main_street_clear=True, skyline_profiles=True)
    result['passed'] = True
except Exception:
    result['passed'] = False
    result['error'] = traceback.format_exc()
    unreal.log_error(result['error'])
finally:
    (saved / 'city_building_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    editor.set_level_viewport_camera_info(vector(-6500, 23200, 4300), unreal.Rotator(pitch=-17, yaw=35, roll=0))
    levels.editor_set_game_view(True)
assert result['passed']
