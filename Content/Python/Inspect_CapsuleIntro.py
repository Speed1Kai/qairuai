import unreal, os, json
actors = unreal.EditorLevelLibrary.get_all_level_actors()
rows = []
for actor in actors:
    name = actor.get_actor_label()
    if name.startswith('INTRO_') or 'Capsule' in name or 'Canopy' in name:
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        rows.append(dict(name=name, position=str(actor.get_actor_location()),
                         rotation=str(actor.get_actor_rotation()),
                         scale=str(actor.get_actor_scale3d()),
                         parent=str(actor.get_attach_parent_actor()),
                         mesh=str(comp.get_editor_property('static_mesh')) if comp else ''))
with open(os.path.join(unreal.Paths.project_saved_dir(),'capsule_inspection.json'),'w') as f:
    json.dump(rows,f,indent=2)
sequence=unreal.load_asset('/Game/LabTutorial/Intro/LS_CapsuleAwakening')
unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(106)
camera=next(a for a in actors if a.get_actor_label()=='INTRO_EmergenceCamera')
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    camera.get_actor_location(),camera.get_actor_rotation())
