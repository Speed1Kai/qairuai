"""Mount animated LED cabinets on intact sections of the playable city facades."""
from datetime import datetime
import json
import math
import shutil

import unreal

from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, V, actors, add, content, levels, local, make_static_root, save, saved
from Build_SciFiNight import asset, node, output, wire
from CityCombat_Common import asset as blueprint, compile_bp
from SurfacePolish_Materials import import_file

ROOT = '/Game/Environment/CityLED'
SOURCE = content.parent / 'SourceAssets' / 'CityLED'
REPORT = saved / 'CityLED'
LABEL = 'CITY_LED_'
M = unreal.MaterialEditingLibrary
CITY_ROWS = (
    ('Arrival', 5850, (25150, 28550, 31600, 33700), 8),
    ('Business', 5850, (37450, 39700, 42050, 44300, 47900, 52400, 55350), 10),
    ('Skyline', 5850, (62400, 65200, 70900, 73800, 78000, 83100, 88200, 94100, 98400), 8),
    ('East', 15500, (64600, 73150, 84400, 89000, 95500), 4),
    ('West', -12600, (66500, 73150, 82500, 90200, 94900), 4),
)
ART = {'System': 4.7, 'Overwatch': 4.5, 'Connecting': 3.9, 'Neural': 4.3, 'Regime': 4.5}


def build_materials():
    A.make_directory(ROOT)
    master = asset('M_City_LED_Master', ROOT, unreal.Material, unreal.MaterialFactoryNew)
    M.delete_all_material_expressions(master)
    master.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    textures = {}
    for key in ART:
        texture = import_file(SOURCE / f'T_LED_{key}.png', ROOT)
        texture.set_editor_property('srgb', True)
        texture.set_editor_property('never_stream', False)
        texture.set_editor_property('max_texture_size', 1024)
        save(texture)
        textures[key] = texture

    art = node(master, 'TextureSampleParameter2D', -620, -300,
               parameter_name='Artwork', texture=textures['System'])
    uv = node(master, 'TextureCoordinate', -900, -300)
    wire(uv, art, 'UVs')
    time = node(master, 'Time', -900, 80)
    position = node(master, 'ObjectPositionWS', -900, 250)
    inputs = []
    for name in ('UV', 'Seconds', 'PanelPosition'):
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    scan = node(master, 'Custom', -620, 45, description='LED scan and dropout',
                inputs=inputs, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1, code="""
float phase = frac(dot(PanelPosition.xy, float2(0.001713, 0.002139)));
float scan = 0.94 + 0.06 * sin(6.283185 * (UV.y * 94.0 - Seconds * 2.0 + phase));
float drift = frac(UV.y - Seconds * 0.29 + phase);
float sweep = 1.0 + 0.16 * (1.0 - smoothstep(0.0, 0.065, drift));
float interval = frac(Seconds * 0.28 + phase);
float dropout = smoothstep(0.972, 0.992, interval) * step(0.5, frac(UV.y * 8.0 + phase));
return scan * sweep * (1.0 - 0.26 * dropout);
""")
    wire(uv, scan, 'UV')
    wire(time, scan, 'Seconds')
    wire(position, scan, 'PanelPosition')
    intensity = node(master, 'ScalarParameter', -400, 245,
                     parameter_name='Brightness', default_value=4.5)
    modulation = node(master, 'Multiply', -175, 50)
    wire(scan, modulation, 'A')
    wire(intensity, modulation, 'B')
    glow = node(master, 'Multiply', 75, -180)
    wire(art, glow, 'A')
    wire(modulation, glow, 'B')
    output(glow, 'EMISSIVE_COLOR')
    M.recompile_material(master)
    save(master)

    result = {}
    for key, brightness in ART.items():
        instance = asset('MI_LED_' + key, ROOT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew)
        M.set_material_instance_parent(instance, master)
        M.set_material_instance_texture_parameter_value(instance, 'Artwork', textures[key])
        M.set_material_instance_scalar_parameter_value(instance, 'Brightness', brightness)
        M.update_material_instance(instance)
        actual = M.get_material_instance_texture_parameter_value(instance, 'Artwork')
        assert actual == textures[key], (key, actual, M.get_texture_parameter_names(master))
        save(instance)
        result[key] = instance
    return result


def make_screen(materials):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
    options = unreal.FbxImportUI()
    options.set_editor_property('automated_import_should_detect_type', False)
    options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property('import_materials', False)
    options.set_editor_property('import_textures', False)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision', False)

    bp = blueprint(ROOT + '/BP_CityLED')
    root = add(bp, unreal.SceneComponent, 'SiteRoot')
    make_static_root(bp, root)
    for key in ('Cabinet', 'Display'):
        mesh = import_file(SOURCE / ('SM_LED_' + key + '.fbx'), ROOT, options)
        box = mesh.get_bounding_box()
        assert box.max.x - box.min.x < 35. and box.max.y - box.min.y > 90. and box.max.z - box.min.z > 90., str(box)
        save(mesh)
        part = add(bp, unreal.StaticMeshComponent, key, 'SiteRoot')
        part.set_static_mesh(mesh)
        part.set_mobility(unreal.ComponentMobility.STATIC)
        part.set_collision_profile_name('NoCollision')
        part.set_editor_property('can_ever_affect_navigation', False)
        if key == 'Cabinet':
            part.set_material(0, A.load_asset('/Game/Surface/Materials/M_Charcoal'))
        else:
            part.set_material(0, materials['System'])
            part.set_editor_property('cast_shadow', False)
    compile_bp(bp)
    save(bp)
    return B.generated_class(bp)


def trace_wall(world, x, y, z, side):
    start = local(x, y, z)
    end = local(x + side * 6200., y, z)
    hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.ECC_VISIBILITY,
        True, [], unreal.DrawDebugTrace.NONE, False)
    if not hit:
        return None
    data = hit.to_tuple()
    actor, component = data[9:11]
    if not actor or not isinstance(component, unreal.StaticMeshComponent):
        return None
    label = actor.get_actor_label()
    if label == 'RECLAIM_City':
        if not component.get_name().startswith('Skyline_'):
            return None
    elif not label.startswith(('CITY_Shell_', 'CITY_Residential_', 'CITY_FirstDowntownBlock', 'DISTRICT_Expansion')):
        return None
    mesh = component.get_static_mesh_asset() if hasattr(component, 'get_static_mesh_asset') else component.static_mesh
    if not mesh:
        return None
    if label in ('DISTRICT_Expansion', 'CITY_FirstDowntownBlock'):
        if not any(word in mesh.get_name() for word in ('District_', 'Shell', 'Building', 'Tower', 'Block')):
            return None
    point, normal = data[5], data[7]
    if normal.x * -side < .76 or abs(normal.z) > .22:
        return None
    if (point - start).length() < 870.:
        return None
    return point, normal, actor, component


def mount(world, x, y, side, width, height, altitude):
    for shift in (0, -180, 180, -370, 370, -610, 610):
        for dz in (0, -125, 145, 295, -260, 455):
            yy, zz = y + shift, GROUND + altitude + dz
            hit = trace_wall(world, x, yy, zz, side)
            if not hit:
                continue
            point, normal, actor, component = hit
            tangent = V((-normal.y, normal.x, 0.))
            support = []
            for sy, sz in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                edge = trace_wall(world, x, yy + sy * width * .38 * abs(tangent.y),
                                  zz + sz * height * .38, side)
                if edge and edge[2:4] == (actor, component):
                    delta = edge[0] - point
                    depth = unreal.MathLibrary.dot_vector_vector(delta, normal)
                    if -64. <= depth <= 27.:
                        support.append((sy, sz, depth))
            if len(support) >= 3:
                depth = max(0., max(row[2] for row in support))
                horizontal_normal = V((normal.x, normal.y, 0.))
                center = point + horizontal_normal * (depth + 4.)
                yaw = math.degrees(math.atan2(normal.y, normal.x))
                return center, yaw, actor.get_actor_label()
    return None


def positions(world):
    result = []
    for sector, x, rows, target in CITY_ROWS:
        found = []
        for row, y in enumerate(rows):
            for side in (1, -1):
                if len(found) == target:
                    break
                index = (row * 2 + (side < 0)) % len(ART)
                key = tuple(ART)[index]
                if sector == 'Arrival' and row == 0:
                    key = 'System' if side < 0 else 'Overwatch'
                width = 1250. if row % 3 == 0 else 940.
                if sector in ('Skyline', 'East', 'West'):
                    width *= 1.25
                height = width * .5
                altitude = 800. if row % 2 == 0 else 1080.
                if sector == 'Arrival' and row < 2:
                    altitude = 1580.
                if key == 'Regime':
                    width, height = 215., 860.
                location = mount(world, x, y, side, width, height, altitude)
                if location is None:
                    width *= .74
                    height *= .74
                    location = mount(world, x, y, side, width, height, altitude - 205.)
                if location is None:
                    continue
                point, yaw, facade = location
                if any((point - other['point']).length() < (width + other['width']) * .52 for other in result + found):
                    continue
                found.append(dict(sector=sector, key=key, point=point, yaw=yaw,
                                  facade=facade, width=width, height=height))
        result.extend(found)
    return result


def add_screens():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    assert world.get_path_name().split('.')[0] == LEVEL, LEVEL
    materials = build_materials()
    cls = make_screen(materials)
    selected = positions(world)
    REPORT.mkdir(exist_ok=True)
    data = [{**row, 'point': [row['point'].x, row['point'].y, row['point'].z]} for row in selected]
    (REPORT / 'Mounts.json').write_text(json.dumps(data, indent=2))
    assert len(selected) >= 12, f'Only {len(selected)} supported facade mounts'

    backup = saved / 'Backups' / 'CityLED' / datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content / (LEVEL.removeprefix('/Game/') + '.umap'), backup)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith(LABEL) and actor.get_class() == cls:
            assert actors.destroy_actor(actor)
    for i, row in enumerate(selected, 1):
        actor = actors.spawn_actor_from_class(cls, row['point'], unreal.Rotator(yaw=row['yaw']))
        assert actor
        actor.modify()
        actor.set_actor_label(f"{LABEL}{row['sector']}_{i:02d}_{row['key']}")
        actor.set_folder_path('SURFACE/City LED')
        actor.set_actor_scale3d(V((1., row['width'] / 100., row['height'] / 100.)))
        display = next(c for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Display')
        display.set_material(0, materials[row['key']])
    return world, len(selected), backup


def save_city(world, count, backup):
    assert levels.save_map(world, LEVEL), LEVEL
    (REPORT / 'Install.json').write_text(json.dumps(dict(count=count, level=LEVEL, backup=str(backup)), indent=2))


if __name__ == '__main__':
    import time

    assert levels.load_map(LEVEL)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    ready = time.monotonic() + 2.

    def install_after_load(_delta):
        if time.monotonic() < ready:
            return
        unreal.unregister_slate_post_tick_callback(handle)
        try:
            save_city(*add_screens())
        finally:
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    handle = unreal.register_slate_post_tick_callback(install_after_load)
