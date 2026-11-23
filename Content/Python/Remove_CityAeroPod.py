"""Remove the placed AeroPod from the connected city and its preview."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import unreal

content = Path(unreal.Paths.project_content_dir()).resolve()
saved = Path(unreal.Paths.project_saved_dir()).resolve()
backup = saved / 'Backups/RemoveCityAeroPod' / datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True)
lab = content / 'Lvl_LabTutorial.umap'
lab_hash = hashlib.sha256(lab.read_bytes()).hexdigest()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert actors and not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
result = {}

def is_pod(actor):
    if actor.get_actor_label() == 'CITY_LunarAeroPod':
        return True
    return isinstance(actor, unreal.StaticMeshActor) and any(
        component.static_mesh and component.static_mesh.get_path_name().startswith('/Game/City/Props/LunarAeroPod/')
        for component in actor.get_components_by_class(unreal.StaticMeshComponent)
    )

for name in ('Lvl_CampusConnected', 'Lvl_SurfaceArrival'):
    path = '/Game/Surface/' + name
    shutil.copy2(content / f'Surface/{name}.umap', backup)
    assert unreal.EditorLoadingAndSavingUtils.load_map(path)
    pods = [actor for actor in actors.get_all_level_actors() if is_pod(actor)]
    assert len(pods) <= 1, (name, len(pods))
    for actor in pods:
        assert actors.destroy_actor(actor)
    if pods:
        assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    assert unreal.EditorLoadingAndSavingUtils.load_map(path)
    assert not any(is_pod(actor) for actor in actors.get_all_level_actors())
    result[name] = {'removed': len(pods), 'remaining': 0}

assert hashlib.sha256(lab.read_bytes()).hexdigest() == lab_hash
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
(saved / 'city_aeropod_removal.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
