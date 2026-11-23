"""Render bounded preview frames of the saved opening; never saves editor state."""
import unreal, os, time

sequence = unreal.load_asset('/Game/LabTutorial/Intro/LS_CapsuleAwakening')
unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
frames = [(15, 'InsidePodCamera', 'Capsule_01_Inside.png'),
          (106, 'EmergenceCamera', 'Capsule_02_Opening.png'),
          (185, 'EmergenceCamera', 'Capsule_03_Exit.png')]
actors = {a.get_actor_label(): a for a in unreal.EditorLevelLibrary.get_all_level_actors()}
folder = os.path.join(unreal.Paths.project_saved_dir(), 'CapsulePreview')
os.makedirs(folder, exist_ok=True)
started = time.monotonic()
stage = 0
last = started


def update(dt):
    global stage, last
    now = time.monotonic()
    if stage >= len(frames):
        if now-last > 3:
            unreal.unregister_slate_post_tick_callback(handle)
            unreal.SystemLibrary.quit_editor()
        return
    if now-started < 14 or now-last < 5:
        return
    position, camera, filename = frames[stage]
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(position)
    unreal.AutomationLibrary.take_high_res_screenshot(
        960, 640, os.path.join(folder, filename), actors['INTRO_' + camera],
        delay=1.0)
    stage += 1
    last = now


handle = unreal.register_slate_post_tick_callback(update)
