"""Author the capsule opening in the existing laboratory, without rebuilding gameplay.

Run in Unreal Editor Python or with -run=pythonscript -script=... -nullrhi.
The cinematic uses shared engine meshes, one existing character, six procedural
steam cards and a short mono sound. No Niagara, render targets or volumetric fog.
"""
import unreal
import os
import math
import shutil
import traceback
import wave
import random
import struct

A = unreal.EditorAssetLibrary
E = unreal.MaterialEditingLibrary
ROOT = '/Game/LabTutorial/Intro'
LEVEL = '/Game/Lvl_LabTutorial'
FPS = 30
END = 300
saved = unreal.Paths.project_saved_dir()
report_path = os.path.join(saved, 'capsule_intro_report.txt')
CENTER = (-550, 280, 0)
EXIT = (-220, 280, 0)


def v(p):
    return unreal.Vector(*[float(n) for n in p])


def frame(n):
    return unreal.FrameNumber(int(n))


def label(actor, name):
    actor.set_actor_label('INTRO_' + name, mark_dirty=True)
    actor.set_folder_path(unreal.Name('LAB/00_Opening'))
    return actor


def material(name, color, opacity=None, roughness=.5, steam=False):
    path = ROOT + '/' + name
    mat = A.load_asset(path) if A.does_asset_exist(path) else None
    if not mat:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    E.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', True)
    if opacity is not None:
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    if steam:
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)

    def node(cls, **props):
        result = E.create_material_expression(mat, cls)
        for key, value in props.items():
            result.set_editor_property(key, value)
        return result

    def connect(a, b, pin):
        linked = E.connect_material_expressions(a, '', b, pin)
        if not linked and pin == 'Input':
            linked = E.connect_material_expressions(a, '', b, '')
        if not linked:
            raise RuntimeError('Could not connect material pin ' + b.get_class().get_name() + '.' + pin)

    color_node = node(unreal.MaterialExpressionConstant3Vector,
                      constant=unreal.LinearColor(r=color[0], g=color[1], b=color[2], a=1))
    E.connect_material_property(color_node, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR
                                if steam else unreal.MaterialProperty.MP_BASE_COLOR)
    rough = node(unreal.MaterialExpressionConstant, r=roughness)
    E.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    if opacity is not None:
        amount = node(unreal.MaterialExpressionScalarParameter,
                      parameter_name='SteamOpacity' if steam else 'GlassOpacity',
                      default_value=0.0 if steam else opacity)
        if not steam:
            # Sphere UV seams must not erase the front of the glass shell.
            E.connect_material_property(amount, '', unreal.MaterialProperty.MP_OPACITY)
        else:
            # Soft procedural ellipse: zero at card edges, no texture allocation.
            uv = node(unreal.MaterialExpressionTextureCoordinate)
            center = node(unreal.MaterialExpressionSubtract, const_b=.5)
            connect(uv, center, 'A')
            radius = node(unreal.MaterialExpressionDotProduct)
            connect(center, radius, 'A')
            connect(center, radius, 'B')
            width = node(unreal.MaterialExpressionMultiply, const_b=4.0)
            connect(radius, width, 'A')
            soft = node(unreal.MaterialExpressionOneMinus)
            connect(width, soft, 'Input')
            clamp = node(unreal.MaterialExpressionSaturate)
            connect(soft, clamp, 'Input')
            feather = node(unreal.MaterialExpressionMultiply)
            connect(clamp, feather, 'A')
            connect(clamp, feather, 'B')
            mask = node(unreal.MaterialExpressionMultiply)
            connect(feather, mask, 'A')
            connect(amount, mask, 'B')
            E.connect_material_property(mask, '', unreal.MaterialProperty.MP_OPACITY)
    E.recompile_material(mat)
    A.save_loaded_asset(mat)
    return mat


def mesh(name, position, size, mat, shape='Cube', rotation=None, parent=None):
    actor = label(unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, v(position), rotation or unreal.Rotator()), name)
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(A.load_asset('/Engine/BasicShapes/' + shape))
    comp.set_material(0, mat)
    comp.set_collision_profile_name('NoCollision')
    comp.set_editor_property('cast_shadow', False)
    actor.set_actor_scale3d(v(tuple(n / 100 for n in size)))
    if parent:
        keep = unreal.AttachmentRule.KEEP_WORLD
        actor.attach_to_actor(parent, unreal.Name('None'), keep, keep, keep, False)
    return actor


def transform(sequence, actor, keys, keep=True):
    binding = sequence.add_possessable(actor)
    section = binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
    section.set_range(0, END)
    section.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE if keep
                                else unreal.MovieSceneCompletionMode.RESTORE_STATE)
    channels = section.get_all_channels()
    for time, position, rotation, scale in keys:
        values = (*position, rotation.roll, rotation.pitch, rotation.yaw, *scale)
        for channel, value in zip(channels[:9], values):
            channel.add_key(frame(time), float(value),
                            interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
    return binding


def visibility(binding, keys):
    track = binding.add_track(unreal.MovieSceneVisibilityTrack)
    track.set_property_name_and_path('bHidden', 'bHidden')
    section = track.add_section()
    section.set_range(0, END)
    section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    channel = section.get_all_channels()[0]
    for time, visible in keys:
        channel.add_key(frame(time), visible)


def animation(binding, clip, start, end, rate=1.0):
    section = binding.add_track(unreal.MovieSceneSkeletalAnimationTrack).add_section()
    section.set_range(start, end)
    section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    params = section.get_editor_property('params')
    params.set_editor_property('animation', clip)
    params.set_editor_property('play_rate', unreal.MovieSceneTimeWarpExtensions.make_time_warp(rate))
    section.set_editor_property('params', params)


def audio():
    directory = os.path.join(unreal.Paths.project_content_dir(), 'LabTutorial', 'Intro')
    os.makedirs(directory, exist_ok=True)
    filename = os.path.join(directory, 'CapsulePressureRelease.wav')
    rng = random.Random(47)
    sample_rate = 22050
    samples = bytearray()
    smooth_noise = 0.0
    for n in range(int(sample_rate * 6.4)):
        t = n / sample_rate
        noise = rng.uniform(-1, 1)
        smooth_noise = .8 * smooth_noise + .2 * noise
        hiss = .15 * noise * math.exp(-max(0, t - .25) * .9) if t > .25 else 0
        motor = (.07 * math.sin(t * 2 * math.pi * 64) + .03 * smooth_noise)
        motor *= min(1, max(0, t - .7) * 2) * max(0, min(1, (4.5 - t) * 2))
        latch = 0
        for hit in (.18, .58, 4.25):
            dt = t - hit
            if 0 < dt < .18:
                latch += .3 * math.exp(-dt * 35) * (noise + math.sin(dt * 640))
        sample = max(-.8, min(.8, hiss + motor + latch))
        samples.extend(struct.pack('<h', int(sample * 32767)))
    with wave.open(filename, 'wb') as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(sample_rate)
        sound.writeframes(samples)
    task = unreal.AssetImportTask()
    for name, value in dict(filename=filename, destination_path=ROOT,
                            automated=True, replace_existing=True, save=True).items():
        task.set_editor_property(name, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return A.load_asset(ROOT + '/CapsulePressureRelease')


try:
    # Release any editor-only preview before rebuilding its bindings.
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    # Preserve the user's existing map and gameplay before changing only the intro.
    backup = os.path.join(saved, 'Backups', 'CapsuleIntro')
    os.makedirs(backup, exist_ok=True)
    source = os.path.join(unreal.Paths.project_content_dir(), 'Lvl_LabTutorial.umap')
    target = os.path.join(backup, 'Lvl_LabTutorial_before_intro.umap')
    if not os.path.exists(target):
        shutil.copy2(source, target)
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not world or not world.get_path_name().startswith(LEVEL + '.'):
        if not unreal.EditorLoadingAndSavingUtils.load_map(LEVEL):
            raise RuntimeError('Could not load the existing laboratory')
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        name = actor.get_actor_label()
        if name.startswith(('INTRO_', 'REF_Pod')) or name in (
                'LAB_Capsule_AutoOpeningHatch', 'LAB_Capsule_Hatch_CyanSeam',
                'REF_OpenGlassCanopy', 'LAB_WakeUp_LowColdMist'):
            unreal.EditorLevelLibrary.destroy_actor(actor)
    A.make_directory(ROOT)
    glass = material('M_FrostedCapsuleGlass', (.12, .23, .25), opacity=.22, roughness=.3)
    steam = material('M_CapsuleSteam', (.5, .65, .67), opacity=.18, steam=True)
    steel = A.load_asset('/Game/LabTutorial/ReferenceStyle/M_OxidizedPaint')
    if not steel:
        steel = A.load_asset('/Game/FinalProtocol/Materials/MI_FP_EdenSilver')
    cyan = A.load_asset('/Game/FinalProtocol/Materials/MI_FP_ProtocolCyan')
    seq_path = ROOT + '/LS_CapsuleAwakening'
    sequence = A.load_asset(seq_path) if A.does_asset_exist(seq_path) else None
    if sequence:
        for binding in sequence.get_bindings():
            binding.remove()
        for track in sequence.get_tracks():
            sequence.remove_track(track)
    else:
        sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'LS_CapsuleAwakening', ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    sequence.set_display_rate(unreal.FrameRate(FPS, 1))
    sequence.set_tick_resolution_directly(unreal.FrameRate(FPS, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(END)

    # Upright cylinder. Both door leaves rotate around the cylinder centre,
    # retracting onto its sides rather than floating away from the enclosure.
    def radial(angle, radius=112, z=150):
        t=math.radians(angle)
        return (-550+radius*math.cos(t),280+radius*math.sin(t),z)

    def arc(name, start, end, radius, z, height, thickness, mat, parent=None):
        count=max(1,round(abs(end-start)/10))
        for i in range(count):
            angle=start+(end-start)*(i+.5)/count
            length=2*radius*math.sin(math.radians(abs(end-start)/count)/2)+.6
            mesh(name+'_%02d'%i,radial(angle,radius,z),(thickness,length,height),mat,
                 rotation=unreal.Rotator(yaw=angle),parent=parent)

    base=mesh('CircularPlinth',(-550,280,5),(244,244,10),steel,'Cylinder')
    base.get_component_by_class(unreal.StaticMeshComponent).set_collision_profile_name('BlockAll')
    mesh('OverheadHousing',(-550,280,284),(245,245,24),steel,'Cylinder')
    mesh('InteriorCeiling',(-550,280,270),(202,202,4),steel,'Cylinder')
    arc('RearShell',65,295,112,143,260,10,steel)
    arc('LowerCollar',65,295,116,18,14,9,steel)
    # Front threshold remains below the ankles and has no obstructing cowl.
    for z in (32,264):
        arc('FrameRing%d'%z,65 if z==32 else 0,295 if z==32 else 360,114,z,7,6,steel)
    for angle in (65,115,180,245,295):
        mesh('UprightRib%d'%angle,radial(angle,103,148),(8,8,230),steel,'Cylinder')
    for angle in (125,235):
        mesh('ColdStrip%d'%angle,radial(angle,99,155),(3,3,202),cyan,'Cylinder')
    for z in (73,127,181,235):
        mesh('RearServicePanel%d'%z,(-651,280,z),(7,86,38),steel)
    # Low ramp: twelve centimetres of rise across 150 cm of travel.
    ramp=mesh('ExitRamp',(-375,280,5),(150,152,8),steel,
              rotation=unreal.Rotator(pitch=-4.6))
    ramp.get_component_by_class(unreal.StaticMeshComponent).set_collision_profile_name('BlockAll')
    for side in (-1,1):
        mesh('RampEdge%d'%side,(-375,280+side*73,10),(150,3,4),steel,
             rotation=unreal.Rotator(pitch=-4.6))
    for index, (start,end,sign) in enumerate(((-60,0,-1),(0,60,1))):
        hinge=label(unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor,v((-550,280,0)),unreal.Rotator()),
            'CapsuleHinge' if index==0 else 'CapsuleHingeRight')
        hinge.get_component_by_class(unreal.StaticMeshComponent).set_mobility(unreal.ComponentMobility.MOVABLE)
        arc('DoorGlass%d'%index,start,end,114,148,224,1.4,glass,hinge)
        for z in (35,261):
            arc('DoorRim%d_%d'%(index,z),start,end,116,z,5,5,steel,hinge)
        for angle in (start,end):
            mesh('DoorStile%d_%d'%(index,angle),radial(angle,116,148),(6,5,230),steel,
                 rotation=unreal.Rotator(yaw=angle),parent=hinge)
        keys=[]
        for t in list(range(0,109,3))+[END-1]:
            progress=max(0,min(1,(t-24)/78))
            eased=progress*progress*(3-2*progress)
            keys.append((t,(-550,280,0),unreal.Rotator(yaw=sign*103*eased),(1,1,1)))
        transform(sequence,hinge,keys)
    lamp=label(unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PointLight,v((-520,280,243)),unreal.Rotator()),'InteriorLight')
    light=lamp.get_component_by_class(unreal.PointLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_editor_property('intensity',850.0)
    light.set_editor_property('attenuation_radius',310.0)
    light.set_editor_property('cast_shadows',False)
    light.set_light_color(unreal.LinearColor(r=.65,g=.85,b=1,a=1))

    for i in range(6):
        side = -1 if i % 2 else 1
        start = (-450 + i * 3,280 + side * (40+i*4),28 + i*6)
        finish = (start[0] + 70 + i * 8, start[1] + side * 42, start[2] + 55 + i * 6)
        card = mesh('PressureMist%02d' % i, start, (1, 1, 1), steam, 'Plane',
                    unreal.Rotator(pitch=75, yaw=-35 + i * 13))
        card.set_actor_hidden_in_game(True)
        start_time = 31 + i * 4
        binding = transform(sequence, card, [
            (0, start, card.get_actor_rotation(), (.15, .15, .15)),
            (start_time, start, card.get_actor_rotation(), (.15, .15, .15)),
            (start_time + 55, finish, card.get_actor_rotation(), (.9, 1.15, 1)),
            (start_time + 95, (finish[0]+22, finish[1], finish[2]+15),
             card.get_actor_rotation(), (1.2, 1.4, 1))])
        visibility(binding, [(0, False), (start_time, True), (start_time + 96, False)])
        comp_binding = sequence.add_possessable(card.get_component_by_class(unreal.StaticMeshComponent))
        comp_binding.set_parent(binding)
        track = comp_binding.add_track(unreal.MovieSceneComponentMaterialTrack)
        info = unreal.ComponentMaterialInfo()
        info.set_editor_property('material_slot_index', 0)
        info.set_editor_property('material_type', unreal.ComponentMaterialType.INDEXED_MATERIAL)
        track.set_material_info(info)
        section = track.add_section()
        section.set_range(0, END)
        section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
        param = unreal.MaterialParameterInfo(name='SteamOpacity')
        for time, amount in [(0,0), (start_time,0), (start_time+10,.18),
                             (start_time+45,.10), (start_time+95,0)]:
            section.add_scalar_parameter_key(param, frame(time), amount, '', '')

    # Stand upright, wait for the doorway to clear, then take slow steps forward.
    body = label(unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.SkeletalMeshActor,v((-550,280,12)),unreal.Rotator(yaw=-90)), 'AwakeningCyborg')
    skeletal = body.get_component_by_class(unreal.SkeletalMeshComponent)
    skeletal.set_skeletal_mesh_asset(A.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple'))
    skeletal.set_collision_profile_name('NoCollision')
    skeletal.set_editor_property('cast_shadow', False)
    body.set_actor_hidden_in_game(True)
    body_binding = transform(sequence, body, [
        (0,(-550,280,12),unreal.Rotator(yaw=-90),(1,1,1)),
        (111,(-550,280,12),unreal.Rotator(yaw=-90),(1,1,1)),
        (150,(-450,280,12),unreal.Rotator(yaw=-90),(1,1,1)),
        (210,(-300,280,0),unreal.Rotator(yaw=-90),(1,1,1)),
        (242,EXIT,unreal.Rotator(yaw=-90),(1,1,1)),
        (END-1,EXIT,unreal.Rotator(yaw=-90),(1,1,1))],keep=False)
    visibility(body_binding, [(0, True), (END-1, False)])
    idle=A.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle')
    if not idle:
        idle=A.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/Idle/MF_Unarmed_Idle')
    walk=A.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd')
    if not idle or not walk:
        raise RuntimeError('Missing upright idle/walk animation')
    animation(body_binding,idle,0,111)
    animation(body_binding,walk,111,242,.5)
    animation(body_binding,idle,242,END)

    camera_track = sequence.add_track(unreal.MovieSceneCameraCutTrack)
    # Keep the exhibition hologram from filling the foreground of the opening.
    # Its normal visibility is restored when the player takes control.
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label().startswith('LAB_Hologram_Text_'):
            visibility(sequence.add_possessable(actor), [(0, False)])
    position=(-110,-120,185)
    target=(-510,280,145)
    rotation=unreal.MathLibrary.find_look_at_rotation(v(position),v(target))
    camera=label(unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.CameraActor,v(position),rotation),'EmergenceCamera')
    camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view',55.0)
    end_position=(-40,-85,165)
    end_rotation=unreal.MathLibrary.find_look_at_rotation(v(end_position),v((-390,280,130)))
    binding=transform(sequence,camera,[(0,position,rotation,(1,1,1)),
        (END-1,end_position,end_rotation,(1,1,1))],False)
    cut=camera_track.add_section()
    cut.set_range(0,END)
    binding_id=unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property('guid',binding.get_id())
    cut.set_editor_property('camera_binding_id',binding_id)

    fade = sequence.add_track(unreal.MovieSceneFadeTrack).add_section()
    fade.set_range(0, END)
    # End explicitly clear. Restoring a captured opaque fade can leave the
    # gameplay camera black after the cinematic changes the view target.
    fade.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    for time, amount in [(0,1.0),(20,0.0),(END-1,0.0)]:
        fade.get_all_channels()[0].add_key(frame(time), amount)
    sound = audio()
    if sound:
        section = sequence.add_track(unreal.MovieSceneAudioTrack).add_section()
        section.set_sound(sound)
        section.set_range(24, 216)

    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_actor_label() == 'LAB_PlayerStart':
            ex=EXIT
            actor.set_actor_location(v((ex[0],ex[1],100)), False, False)
            # Face the room when control returns; the third-person camera then
            # sits in the clear aisle rather than backing into the capsule.
            actor.set_actor_rotation(unreal.Rotator(yaw=0), False)
        fog = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
        if fog:
            fog.set_editor_property('enable_volumetric_fog', False)
            fog.set_editor_property('fog_density', .006)
    player = label(unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.LevelSequenceActor, unreal.Vector()), 'OpeningSequence')
    settings = unreal.MovieSceneSequencePlaybackSettings()
    for key in ('auto_play', 'disable_movement_input', 'disable_look_at_input', 'hide_player', 'hide_hud'):
        settings.set_editor_property(key, True)
    player.set_editor_property('playback_settings', settings)
    player.set_sequence(sequence)
    if not A.save_loaded_asset(sequence):
        raise RuntimeError('Could not save the opening sequence')
    A.save_directory(ROOT, only_if_is_dirty=True, recursive=True)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError('Could not save the laboratory with its opening sequence')
    with open(report_path, 'w', encoding='utf-8') as report:
        report.write('SAVED: Lvl_LabTutorial + LS_CapsuleAwakening.\n'
                     '10-second upright cylindrical capsule intro, two curved sliding door leaves.\n'
                     'Standing cyborg waits for clearance, then slowly walks down a low ramp.\n'
                     'Six texture-free steam cards, mono mechanical release, shadowless interior light.\n'
                     'No Niagara, volumetric fog, scene captures or new texture allocations.\n')
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(v((-110,-120,185)),unreal.MathLibrary.find_look_at_rotation(v((-110,-120,185)),v((-510,280,145))))
    unreal.log('CAPSULE INTRO SAVED')
except Exception:
    with open(report_path, 'w', encoding='utf-8') as report:
        report.write('FAILED\n' + traceback.format_exc())
    raise

