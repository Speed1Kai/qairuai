"""Return editor preview components to their saved, player-activated state."""
import unreal
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if not actor.get_actor_label().startswith('HOLO_ArchiveProjector_'):continue
    actor.modify()
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name().startswith('Projection'):
            c.modify();c.set_visibility(False)
            c.set_custom_primitive_data_float(0,0.)
if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Save failed')
unreal.log('HOLOGRAM PREVIEW CLOSED; F ACTIVATION RESTORED')
