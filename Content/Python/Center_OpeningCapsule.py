"""Center the existing opening assembly and offset its authored camera/actor keys."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import unreal

LAB = '/Game/Lvl_LabTutorial'
SEQUENCE = '/Game/LabTutorial/Intro/LS_CapsuleAwakening'
A = unreal.EditorAssetLibrary
U = unreal.EditorLoadingAndSavingUtils
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
project = Path(unreal.Paths.project_dir()).resolve()

def center_capsule(backup):
    assert editor.get_editor_world().get_path_name().split('.')[0] == LAB
    assert not U.get_dirty_map_packages()
    layout = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    floor = layout['LAB_Room_Floor'].get_actor_location()
    capsule = layout['INTRO_CircularPlinth'].get_actor_location()
    delta = unreal.Vector(floor.x-capsule.x, floor.y-capsule.y, 0)
    if delta.length() < .01:
        return {'center': [floor.x, floor.y], 'already_centered': True}
    affected = ['Content/Lvl_LabTutorial.umap', 'Content/LabTutorial/Intro/LS_CapsuleAwakening.uasset']
    for relative in affected:
        destination = backup/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project/relative,destination)
    seq = A.load_asset(SEQUENCE)
    plan = []
    for binding in seq.get_bindings():
        if not binding.get_name().startswith('INTRO_'):
            continue
        for track in binding.get_tracks():
            if not isinstance(track,unreal.MovieScene3DTransformTrack):
                continue
            for section in track.get_sections():
                for channel in section.get_all_channels():
                    axis = str(channel.get_editor_property('channel_name'))
                    shift = {'Location.X':delta.x,'Location.Y':delta.y}.get(axis)
                    if shift is not None:
                        for key in channel.get_keys():
                            plan.append((key,key.get_value()+shift))
    assert plan
    moved = []
    for name,actor in layout.items():
        if (name.startswith('INTRO_') and name!='INTRO_OpeningSequence') or name=='LAB_PlayerStart':
            if actor.get_attach_parent_actor():
                continue
            actor.modify()
            before = actor.get_actor_location()
            actor.set_actor_location(before+delta,False,True)
            assert (actor.get_actor_location()-(before+delta)).length()<.01,name
            moved.append(name)
    assert 'INTRO_CircularPlinth' in moved and 'LAB_PlayerStart' in moved
    seq.modify()
    for key,value in plan:
        key.set_value(value)
    assert A.save_loaded_asset(seq,only_if_is_dirty=False)
    assert U.save_map(editor.get_editor_world(),LAB)
    return {'center':[floor.x,floor.y], 'previous':[capsule.x,capsule.y], 'moved':moved,
            'translated_keys':len(plan), 'backup':str(backup)}

if __name__=='__main__':
    backup = project/'Saved/Backups/CenteredCapsule'/datetime.now().strftime('%Y%m%d_%H%M%S')
    result = center_capsule(backup)
    (project/'Saved/CapsuleCenter.json').write_text(json.dumps(result,indent=2),encoding='utf8')

