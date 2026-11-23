"""Editor-only lighting/layout preview; does not save preview visibility."""
import unreal
actors=unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    if a.get_actor_label().startswith('HOLO_'):
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if c.get_name().startswith(('Projection','InteractPrompt')):
                c.set_visibility(True)
                c.set_custom_primitive_data_float(0,-100)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    unreal.Vector(130,-90,195),unreal.Rotator(pitch=2.5,yaw=90))
