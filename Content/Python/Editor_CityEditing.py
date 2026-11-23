"""Return from laboratory play to the saved city at the player's last city view."""
import json
import time
from pathlib import Path

import unreal

LAB = '/Game/Lvl_LabTutorial'
CITY = '/Game/Surface/Lvl_CampusConnected'
ROUTE = '/Game/Surface/HiddenExit/BP_HiddenLabRoute.BP_HiddenLabRoute_C'
_installed = False
_tick_handle = None
_next_sample = 0
_was_playing = False
_last_view = None

def _level_path():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return world.get_path_name().split('.')[0] if world else ''

def _record(result):
    directory = Path(unreal.Paths.project_saved_dir()) / 'CityEditor20'
    directory.mkdir(exist_ok=True)
    (directory / 'LastReturn.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')

def _city_view(game):
    route_class = unreal.load_class(None, ROUTE)
    route = unreal.GameplayStatics.get_actor_of_class(game, route_class)
    if not route:
        return None
    stream = route.get_editor_property('CampusStreaming')
    player = unreal.GameplayStatics.get_player_character(game, 0)
    if not stream or not stream.is_level_visible() or not player:
        return None
    transform = stream.get_editor_property('level_transform')
    # Preloading the exterior while still in the lift does not count as entering it.
    if player.get_actor_location().z < transform.translation.z - 50:
        return None
    camera = unreal.GameplayStatics.get_player_camera_manager(game, 0)
    if not camera:
        return None
    return (
        transform.inverse_transform_location(camera.get_camera_location()),
        transform.inverse_transform_rotation(camera.get_camera_rotation())
    )

def _open_city(view):
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:
        _record({'status': 'unsaved_maps', 'maps': [p.get_name() for p in dirty]})
        unreal.log_warning('Город для редактирования: сначала сохраните изменённую карту. '
                           'Затем откройте /Game/Surface/Lvl_CampusConnected.')
        return
    try:
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not levels.load_level(CITY):
            raise RuntimeError('Could not open the city for editing')
        position, rotation = view
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
            position, rotation)
        _record({
            'status': 'opened',
            'level': _level_path(),
            'camera': [position.x, position.y, position.z],
            'rotation': [rotation.pitch, rotation.yaw, rotation.roll],
            'streamed_transform_used': True
        })
        unreal.log('Город открыт для редактирования на месте завершения игрового теста.')
    except Exception as error:
        _record({'status': 'error', 'error': str(error)})
        unreal.log_error('Город для редактирования: ' + str(error))

def _watch_game(delta_seconds):
    global _next_sample, _was_playing, _last_view
    now = time.monotonic()
    if now < _next_sample:
        return
    _next_sample = now + .25
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    game = editor.get_game_world()
    if game:
        _was_playing = True
        _last_view = _city_view(game) if unreal.GameplayStatics.get_current_level_name(game, True) == 'Lvl_LabTutorial' else None
        return
    if _was_playing:
        _was_playing = False
        view = _last_view
        _last_view = None
        if view and _level_path() == LAB:
            _open_city(view)

def install():
    global _installed, _tick_handle
    if not _installed and unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem):
        _tick_handle = unreal.register_slate_post_tick_callback(_watch_game)
        _installed = True

