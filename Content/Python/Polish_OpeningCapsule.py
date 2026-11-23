"""Align the industrial capsule shell and frame the centered awakening."""
from pathlib import Path
from datetime import datetime
import shutil
import unreal
from Center_OpeningCapsule import A, LAB, SEQUENCE, U, actors, editor, project

def polish():
    assert editor.get_editor_world().get_path_name().split('.')[0] == LAB
    assert not U.get_dirty_map_packages()
    originals=project/'Saved/Backups/CenteredCapsuleCamera'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for name in ('Content/Lvl_LabTutorial.umap','Content/LabTutorial/Intro/LS_CapsuleAwakening.uasset'):
        copy=originals/name;copy.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(project/name,copy)
    layout={actor.get_actor_label():actor for actor in actors.get_all_level_actors()}
    target=layout['INTRO_CircularPlinth'].get_actor_location()
    armor=layout['IND_CapsuleArmor'].get_actor_location()
    delta=unreal.Vector(target.x-armor.x,target.y-armor.y,0)
    for name,actor in layout.items():
        if name.startswith('IND_Capsule') and not actor.get_attach_parent_actor():
            actor.modify();actor.set_actor_location(actor.get_actor_location()+delta,False,True)
    lamp=layout['INTRO_InteriorLight'].get_component_by_class(unreal.PointLightComponent)
    lamp.set_intensity(1250)
    lamp.set_source_radius(30)
    key_actor=layout.get('INTRO_CapsuleKeyLight')
    if not key_actor:
        key_actor=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(199,-160,228))
        key_actor.set_actor_label('INTRO_CapsuleKeyLight')
        key_actor.set_folder_path('LAB/00_Opening')
    key_light=key_actor.get_component_by_class(unreal.PointLightComponent)
    key_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    key_light.set_cast_shadows(False)
    key_light.set_attenuation_radius(510)
    key_light.set_intensity(3150)
    key_light.set_source_radius(32)
    key_light.set_light_color(unreal.LinearColor(.63,.83,1.,1.))
    positions=[unreal.Vector(410,-345,202),unreal.Vector(438,-373,187)]
    interests=[unreal.Vector(0,0,151),unreal.Vector(107,-99,137)]
    angles=[unreal.MathLibrary.find_look_at_rotation(eye,target) for eye,target in zip(positions,interests)]
    camera=layout['INTRO_EmergenceCamera'];camera.modify()
    camera.set_actor_location_and_rotation(positions[0],angles[0],False,True)
    seq=A.load_asset(SEQUENCE);seq.modify()
    binding=next(b for b in seq.get_bindings() if b.get_name()=='INTRO_EmergenceCamera')
    track=next(t for t in binding.get_tracks() if isinstance(t,unreal.MovieScene3DTransformTrack))
    values={'Location.X':[p.x for p in positions],
            'Location.Y':[p.y for p in positions],
            'Location.Z':[p.z for p in positions],
            'Rotation.X':[r.roll for r in angles],
            'Rotation.Y':[r.pitch for r in angles],
            'Rotation.Z':[r.yaw for r in angles]}
    for channel in track.get_sections()[0].get_all_channels():
        name=str(channel.get_editor_property('channel_name'))
        if name not in values:
            continue
        keys=channel.get_keys()
        assert len(keys)==2,(name,len(keys))
        for key,value in zip(keys,values[name]):
            key.set_value(value)
    assert U.save_map(editor.get_editor_world(),LAB)
    assert A.save_loaded_asset(seq,only_if_is_dirty=False)
    return str(originals)

