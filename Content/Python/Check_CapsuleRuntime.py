"""One bounded PIE check of startup, hinge motion, and control handoff. Saves no assets."""
import unreal, time, os, json

unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
play_settings = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
previous_compile = play_settings.get_editor_property('AutoRecompileBlueprints')
play_settings.set_editor_property('AutoRecompileBlueprints', False)
started = time.monotonic()
samples = []
thresholds = [.8, 3.5, 6.5, 8.8, 11.7, 14.3]
out = os.path.join(unreal.Paths.project_saved_dir(), 'capsule_runtime_check.json')
folder = os.path.join(unreal.Paths.project_saved_dir(), 'CapsulePreview')
os.makedirs(folder, exist_ok=True)
finishing = False
finish_time = 0


def update(dt):
    global finishing, finish_time
    try:
        if finishing:
            if subsystem.is_in_play_in_editor() and time.monotonic()>finish_time:
                subsystem.editor_request_end_play()
            if not subsystem.is_in_play_in_editor():
                play_settings.set_editor_property('AutoRecompileBlueprints', previous_compile)
                unreal.unregister_slate_post_tick_callback(handle)
            return
        world = unreal.EditorLevelLibrary.get_game_world()
        if not world:
            if time.monotonic() - started > 35:
                raise RuntimeError('PIE did not start within the bounded check')
            return
        clock = unreal.GameplayStatics.get_time_seconds(world)
        if len(samples) >= len(thresholds) or clock < thresholds[len(samples)]:
            return
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        actors = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)}
        hinge = actors['INTRO_CapsuleHinge']
        body = actors['INTRO_AwakeningCyborg']
        skeleton=body.get_component_by_class(unreal.SkeletalMeshComponent)
        camera_manager=unreal.GameplayStatics.get_player_camera_manager(world,0)
        row = dict(time=clock, pawn_hidden=pawn.get_editor_property('hidden'),
                   move_locked=pc.is_move_input_ignored(), look_locked=pc.is_look_input_ignored(),
                   camera=pc.get_view_target().get_name(), hinge_position=str(hinge.get_actor_location()),
                   hinge_rotation=str(hinge.get_actor_rotation()), ghost_hidden=body.get_editor_property('hidden'),
                   pawn_position=str(pawn.get_actor_location()),
                   head=str(skeleton.get_socket_location('head')),
                   camera_position=str(camera_manager.get_camera_location()),
                   camera_rotation=str(camera_manager.get_camera_rotation()),
                   control_rotation=str(pc.get_control_rotation()),
                   left_foot=str(skeleton.get_socket_location('foot_l')),
                   right_foot=str(skeleton.get_socket_location('foot_r')))
        samples.append(row)
        with open(out, 'w') as f:
            json.dump(samples, f, indent=2)
        if len(samples) in (1,2,3,4,5,6):
            filename = os.path.join(folder,'Runtime_%02d.png' % len(samples)).replace('\\','/')
            unreal.SystemLibrary.execute_console_command(world, 'HighResShot 960x640 filename="'+filename+'"')
        if len(samples) == len(thresholds):
            assert samples[0]['pawn_hidden'] and samples[0]['move_locked'], 'Intro did not lock and hide the player'
            assert not row['pawn_hidden'] and not row['move_locked'] and not row['look_locked'], 'Player control did not return'
            assert row['ghost_hidden'], 'Cinematic stand-in remained visible'
            finishing = True
            finish_time=time.monotonic()+.8
            unreal.log('CAPSULE RUNTIME HANDOFF PASSED')
    except Exception as error:
        with open(out, 'w') as f:
            json.dump(dict(error=str(error),samples=samples),f,indent=2)
        play_settings.set_editor_property('AutoRecompileBlueprints', previous_compile)
        unreal.unregister_slate_post_tick_callback(handle)
        if subsystem.is_in_play_in_editor():
            subsystem.editor_request_end_play()
        unreal.log_error('Capsule check: '+str(error))


handle = unreal.register_slate_post_tick_callback(update)
subsystem.editor_request_begin_play()
