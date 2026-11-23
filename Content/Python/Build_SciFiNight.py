"""Author the night lighting and reusable neon assets for the city."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

import unreal
from Industrial_Common import A, B, G, M, V, Graph, add, compile_bp, pin, save

ROOT = '/Game/Surface/Materials'
MAPS = ('Lvl_CampusConnected', 'Lvl_SurfaceArrival')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.EditorLoadingAndSavingUtils
tools = unreal.AssetToolsHelpers.get_asset_tools()
content = Path(unreal.Paths.project_content_dir())
saved = Path(unreal.Paths.project_saved_dir())
color = unreal.LinearColor


def asset(name, folder, kind, factory):
    path = folder + '/' + name
    return A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name, folder, kind, factory())


def node(material, kind, x, y, **properties):
    expression = M.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind), x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def wire(source, dest, pin):
    assert M.connect_material_expressions(source, '', dest, pin), pin


def output(source, pin):
    assert M.connect_material_property(source, '', getattr(unreal.MaterialProperty, 'MP_' + pin))


def neon_material():
    material = asset('M_SciFi_Neon_Master', ROOT, unreal.Material, unreal.MaterialFactoryNew)
    M.delete_all_material_expressions(material)

    def n(kind, x, y, **props):
        return node(material, kind, x, y, **props)

    def scalar(name, value, x, y):
        return n('ScalarParameter', x, y, parameter_name=name, default_value=value)

    def binary(kind, a, b, x, y, **props):
        result = n(kind, x, y, **props)
        wire(a, result, 'A')
        if b is not None:
            wire(b, result, 'B')
        return result

    def wave(phase, x, y, power):
        sine = n('Sine', x, y, period=1.0)
        wire(phase, sine, '')
        half = binary('Multiply', sine, None, x + 200, y, const_b=0.5)
        normalized = binary('Add', half, None, x + 400, y, const_b=0.5)
        shaped = n('Power', x + 600, y, const_exponent=power)
        wire(normalized, shaped, 'Base')
        return shaped

    uv = n('TextureCoordinate', -2200, -450)
    vertical = n('ComponentMask', -2000, -450, r=False, g=True, b=False, a=False)
    wire(uv, vertical, '')
    time = n('Time', -2200, 200)
    frequency = binary('Multiply', vertical, scalar('ScanlineFrequency', 16, -2000, -250), -1750, -450)
    travel = binary('Multiply', time, scalar('ScanlineSpeed', 0.8, -2000, -30), -1750, -80)
    phase = binary('Add', frequency, travel, -1530, -450)
    bands = wave(phase, -1300, -450, 4)
    scan = n('LinearInterpolate', -420, -450, const_a=1.0)
    wire(bands, scan, 'B')
    wire(scalar('ScanlineAmount', 0.25, -710, -250), scan, 'Alpha')

    tempo = binary('Multiply', time, scalar('FlickerSpeed', 2.4, -2000, 410), -1750, 210)
    pulse = wave(tempo, -1300, 210, 8)
    dip = n('OneMinus', -500, 210)
    wire(pulse, dip, '')
    flicker = n('LinearInterpolate', -270, 210, const_a=1.0)
    wire(dip, flicker, 'B')
    wire(scalar('FlickerAmount', 0.18, -500, 430), flicker, 'Alpha')

    tint = n('VectorParameter', -700, -900, parameter_name='EmissiveColor', default_value=color(0.05, 0.7, 1.0, 1))
    hdr = binary('Multiply', tint, scalar('EmissiveIntensity', 50, -700, -720), -420, -860)
    striped = binary('Multiply', hdr, scan, -180, -510)
    output(binary('Multiply', striped, flicker, 45, -360), 'EMISSIVE_COLOR')
    output(n('VectorParameter', 0, -800, parameter_name='BaseColor', default_value=color(0.018, 0.025, 0.037, 1)), 'BASE_COLOR')
    output(n('Constant', 50, -630, r=0.55), 'ROUGHNESS')
    M.recompile_material(material)
    save(material)
    return material


def sky_material():
    material = asset('M_SciFi_OvercastNight', ROOT, unreal.Material, unreal.MaterialFactoryNew)
    M.delete_all_material_expressions(material)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('is_sky', True)
    direction = node(material, 'CameraVectorWS', -430, 0)
    direction_input = unreal.CustomInput()
    direction_input.set_editor_property('input_name', 'ViewDirection')
    cloud = node(material, 'Custom', -190, 0,
                 output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, inputs=[direction_input],
                 code="""float3 d = normalize(-ViewDirection);
float horizon = pow(1.0 - saturate(d.z), 4.0);
float2 p = d.xy / (0.38 + abs(d.z));
float broad = sin(p.x * 4.1 + sin(p.y * 3.7)) * sin(p.y * 5.3 - p.x * 2.1);
float fine = sin(dot(p, float2(13.0, 9.0))) * sin(dot(p, float2(-7.0, 16.0)));
float clouds = smoothstep(-0.65, 0.65, broad + 0.19 * fine);
float3 night = lerp(float3(0.009, 0.017, 0.040), float3(0.055, 0.074, 0.104), horizon);
return night * lerp(0.55, 1.12, clouds);""")
    wire(direction, cloud, 'ViewDirection')
    output(cloud, 'EMISSIVE_COLOR')
    M.recompile_material(material)
    save(material)
    return material


def instance(master, suffix, tint, intensity):
    material = asset('MI_SciFi_Neon_' + suffix, ROOT, unreal.MaterialInstanceConstant,
                     unreal.MaterialInstanceConstantFactoryNew)
    M.set_material_instance_parent(material, master)
    M.set_material_instance_vector_parameter_value(material, 'EmissiveColor', tint)
    M.set_material_instance_scalar_parameter_value(material, 'EmissiveIntensity', intensity)
    assert M.get_material_instance_scalar_parameter_value(material, 'EmissiveIntensity') == intensity
    save(material)
    return material


def grade(settings):
    for name, value in (
        ('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL),
        ('auto_exposure_apply_physical_camera_exposure', False),
        ('auto_exposure_bias', 0.0),
        ('bloom_intensity', 0.9),
        ('bloom_threshold', 0.75),
    ):
        settings.set_editor_property('override_' + name, True)
        settings.set_editor_property(name, value)
    return settings


def configure_fog(fog):
    for name, value in (
        ('fog_density', 0.021),
        ('fog_height_falloff', 0.13),
        ('fog_max_opacity', 0.62),
        ('start_distance', 300.0),
        ('enable_volumetric_fog', True),
        ('volumetric_fog_albedo', unreal.Color(r=86, g=96, b=115, a=255)),
        ('volumetric_fog_scattering_distribution', 0.25),
        ('volumetric_fog_extinction_scale', 1.1),
        ('volumetric_fog_distance', 15500.0),
        ('volumetric_fog_start_distance', 300.0),
    ):
        if name == 'enable_volumetric_fog':
            fog.set_editor_property(name, value)
        else:
            getattr(fog, 'set_' + name)(value)
    fog.set_fog_inscattering_color(color(0.028, 0.037, 0.060, 1))


def city_grade_blueprint():
    bp = asset('BP_SciFi_CityGrade', '/Game/Surface', unreal.Blueprint, unreal.BlueprintFactory)
    bounds = add(bp, unreal.BoxComponent, 'CityBounds')
    bounds.set_box_extent(V((65000, 43000, 20000)))
    bounds.set_collision_profile_name('NoCollision')
    post = add(bp, unreal.PostProcessComponent, 'NightGrade', 'CityBounds')
    post.set_editor_property('unbound', False)
    post.set_editor_property('blend_radius', 2000.0)
    post.set_editor_property('priority', 20.0)
    post.set_editor_property('settings', grade(post.get_editor_property('settings')))
    fog = add(bp, unreal.ExponentialHeightFogComponent, 'CityFog', 'CityBounds')
    fog.set_editor_property('relative_location', V((0, 0, -20000)))
    fog.set_visibility(False)
    configure_fog(fog)

    graph = G.get_graph_editor_by_name(bp, 'EventGraph')
    variables = (
        ('PreviousFog', B.get_object_reference_type(unreal.ExponentialHeightFogComponent), 'None'),
        ('bPreviousFogVisible', B.get_basic_type_by_name('bool'), 'false'),
        ('bCityFogActive', B.get_basic_type_by_name('bool'), 'false'),
    )
    for name, kind, default in variables:
        if name not in map(str, B.list_member_variable_names(bp)):
            assert graph.add_member_variable(name, kind, default), name
    compile_bp(bp)

    g = Graph(bp)
    g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name() != 'K2Node_Event'])

    def event(name):
        if not g.e.find_event_node(name):
            token = name.removeprefix('Receive')
            choices = [n for n in g.e.list_available_nodes([])
                       if n.startswith(('Добавитьсобытие|', 'AddEvent|'))
                       and n.split('|')[-1].replace(' ', '') in (token, 'Событие' + token, 'Event' + token)]
            assert len(choices) == 1, (name, choices)
            g.e.create_node_from_name(choices[0], unreal.Vector2D(), [])
        g.event(name)

    def valid(obj):
        return g.out(g.call('Engine.KismetSystemLibrary.IsValid', Object=obj))

    def visibility(obj, visible):
        g.do(g.call('Engine.SceneComponent.SetVisibility', target=obj,
                    bNewVisibility=visible, bPropagateToChildren=False))

    event('ReceiveBeginPlay')
    g.do(g.call('Engine.Actor.SetActorTickInterval', TickInterval=0.2))
    previous = g.out(g.do(g.call('Engine.GameplayStatics.GetActorOfClass',
                                 ActorClass='/Script/Engine.ExponentialHeightFog')))
    g.branch(valid(previous))
    previous_fog = g.out(g.call('Engine.Actor.GetComponentByClass', target=previous,
                                ComponentClass='/Script/Engine.ExponentialHeightFogComponent'))
    g.set('PreviousFog', previous_fog)
    g.branch(valid(g.get('PreviousFog')))
    g.set('bPreviousFogVisible', g.out(g.call('Engine.SceneComponent.IsVisible', target=g.get('PreviousFog'))))

    event('ReceiveTick')
    camera = g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager', PlayerIndex=0))
    g.branch(valid(camera))
    position = g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation', target=camera))
    bounds_info = g.call('Engine.KismetSystemLibrary.GetComponentBounds', Component=g.get('CityBounds'))
    inside = g.math('IsPointInBox', Point=position, BoxOrigin=pin(bounds_info, 'Origin', True),
                    BoxExtent=pin(bounds_info, 'BoxExtent', True))
    g.branch(g.math('NotEqual_BoolBool', A=inside, B=g.get('bCityFogActive')))
    g.set('bCityFogActive', inside)
    enter = g.branch(g.get('bCityFogActive'))
    visibility(g.get('CityFog'), True)
    g.branch(valid(g.get('PreviousFog')))
    visibility(g.get('PreviousFog'), False)
    g.cursor = enter.find_else_pin()
    visibility(g.get('CityFog'), False)
    g.branch(valid(g.get('PreviousFog')))
    visibility(g.get('PreviousFog'), g.get('bPreviousFogVisible'))

    event('ReceiveEndPlay')
    g.branch(g.get('bCityFogActive'))
    g.branch(valid(g.get('PreviousFog')))
    visibility(g.get('PreviousFog'), g.get('bPreviousFogVisible'))
    compile_bp(bp)
    save(bp)
    return B.generated_class(bp)


def spawn(cls, label, location):
    actor = actors.spawn_actor_from_class(cls, location)
    assert actor, label
    actor.set_actor_label(label)
    actor.set_folder_path('CITY/NightLighting')
    return actor


def component(scene, label, actor_type, component_type, location):
    actor = scene.get(label) or spawn(actor_type, label, location)
    result = actor.get_component_by_class(component_type)
    assert result, label
    actor.modify()
    result.modify()
    return result


def configure(name, dome, variants, grade_class):
    path = '/Game/Surface/' + name
    world = levels.load_map(path)
    assert world, path
    scene = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
    city = scene['CITY_FirstDowntownBlock']

    def point(x, y, z):
        return unreal.MathLibrary.transform_location(city.get_actor_transform(), V((x, y, z)))

    for actor in scene.values():
        if actor.get_actor_label().startswith('CITY_Night_'):
            assert actors.destroy_actor(actor)
    sky_dome = scene['SURF_AshSky'].static_mesh_component
    sky_dome.modify()
    sky_dome.set_material(0, dome)

    moon = component(scene, 'SURF_LateSun', unreal.DirectionalLight, unreal.DirectionalLightComponent, point(0, 0, 15000))
    moon.set_intensity(0.30)
    moon.set_light_color(color(0.25, 0.40, 0.75, 1))
    moon.set_editor_property('volumetric_scattering_intensity', 0.35)

    sky = component(scene, 'SURF_SkyFill', unreal.SkyLight, unreal.SkyLightComponent, point(0, 0, 12000))
    sky.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    sky.set_editor_property('real_time_capture', False)
    sky.set_editor_property('lower_hemisphere_is_black', True)
    sky.set_intensity(0.65)
    sky.recapture_sky()
    readability = scene.get('CAMPUS_ExteriorReadability')
    if readability:
        old_sky = readability.get_component_by_class(unreal.SkyLightComponent)
        if old_sky:
            old_sky.modify()
            old_sky.set_visibility(False)

    if name == 'Lvl_SurfaceArrival':
        preview_grade = scene.get('SURF_SurfaceGrade') or spawn(
            unreal.PostProcessVolume, 'SURF_SurfaceGrade', point(0, 0, 0))
        preview_grade.set_editor_property('unbound', True)
        fog = component(scene, 'SURF_AshHaze', unreal.ExponentialHeightFog, unreal.ExponentialHeightFogComponent, point(0, 0, 0))
        configure_fog(fog)
        preview_grade.modify()
        preview_grade.set_editor_property('settings', grade(preview_grade.get_editor_property('settings')))
    else:
        if 'SURF_AshHaze' in scene:
            assert actors.destroy_actor(scene['SURF_AshHaze'])
        spawn(grade_class, 'CITY_Night_Grade', point(0, 63500, 20000))

    cube = A.load_asset('/Engine/BasicShapes/Cube')
    steel = A.load_asset(ROOT + '/M_RuinSteel')
    palette = ('Cyan', 'Magenta', 'Amber')
    for index, (x, y) in enumerate(((-1180, 24980), (1180, 26900), (-1180, 29100),
                                     (1180, 31400), (-1180, 33300), (1180, 34500)), 1):
        tint, material = variants[palette[(index - 1) % len(palette)]]
        label = f'CITY_Night_{index:02d}'
        housing = spawn(unreal.StaticMeshActor, label + '_Housing', point(x, y, 192))
        housing.static_mesh_component.set_static_mesh(cube)
        housing.static_mesh_component.set_material(0, steel)
        housing.static_mesh_component.set_collision_profile_name('NoCollision')
        housing.set_actor_scale3d(V((0.28, 0.92, 3.84)))
        panel = spawn(unreal.StaticMeshActor, label + '_Neon', point(x * 0.985, y, 245))
        mesh = panel.static_mesh_component
        mesh.set_static_mesh(cube)
        mesh.set_material(0, material)
        mesh.set_collision_profile_name('NoCollision')
        mesh.set_editor_property('cast_shadow', False)
        panel.set_actor_scale3d(V((0.10, 0.72, 2.45)))
        lamp = spawn(unreal.PointLight, label + '_FogLight', point(x * 0.91, y, 225))
        light = lamp.get_component_by_class(unreal.PointLightComponent)
        light.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
        light.set_intensity(1150)
        light.set_attenuation_radius(1150)
        light.set_light_color(tint)
        light.set_editor_property('cast_shadows', False)
        light.set_editor_property('cast_volumetric_shadow', False)
        light.set_editor_property('volumetric_scattering_intensity', 8.0)

    world.modify()
    assert levels.save_map(world, path), path
    del world
    world = levels.load_map(path)
    assert world, path
    scene = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
    fog_owner = scene.get('SURF_AshHaze') or scene['CITY_Night_Grade']
    fog = fog_owner.get_component_by_class(unreal.ExponentialHeightFogComponent)
    assert fog.get_editor_property('enable_volumetric_fog')
    assert sum(label.endswith('_Neon') and label.startswith('CITY_Night_') for label in scene) == 6
    assert sum(label.endswith('_FogLight') and label.startswith('CITY_Night_') for label in scene) == 6
    assert scene['SURF_AshSky'].static_mesh_component.get_material(0) == dome
    return {'volumetric_fog': True, 'neon_panels': 6, 'neon_lights': 6}


def main():
    assert not levels.get_dirty_map_packages()
    backup = saved / 'Backups/SciFiNight' / datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for name in MAPS:
        shutil.copy2(content / f'Surface/{name}.umap', backup)
    lab = content / 'Lvl_LabTutorial.umap'
    original_lab = hashlib.sha256(lab.read_bytes()).hexdigest()
    master = neon_material()
    dome = sky_material()
    grade_class = city_grade_blueprint()
    variants = {}
    for suffix, tint, intensity in (
        ('Cyan', color(0.035, 0.62, 1, 1), 12),
        ('Magenta', color(1, 0.035, 0.30, 1), 10),
        ('Amber', color(1, 0.29, 0.045, 1), 9),
    ):
        variants[suffix] = (tint, instance(master, suffix, tint, intensity))
    results = {name: configure(name, dome, variants, grade_class) for name in MAPS}
    assert hashlib.sha256(lab.read_bytes()).hexdigest() == original_lab
    assert levels.load_map('/Game/Lvl_LabTutorial')
    assert unreal.SystemLibrary.get_console_variable_int_value('r.VirtualTextures') == 1
    assert unreal.SystemLibrary.get_console_variable_int_value('r.Streaming.PoolSize') == 2000
    (saved / 'scifi_night.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
