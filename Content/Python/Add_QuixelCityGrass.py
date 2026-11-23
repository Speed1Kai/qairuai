"""Import the supplied Quixel grass and place it only on the two city maps."""
import datetime
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from Industrial_Common import A, B, M, add, compile_bp, components, save

content = Path(unreal.Paths.project_content_dir()).resolve()
source = content.parent / 'SourceAssets/Quixel/DryGrass_tbbqejqr'
saved = Path(unreal.Paths.project_saved_dir()).resolve()
root = '/Game/City/Vegetation/QuixelDryGrass'
prefix = 'Dry_Grass_tbbqejqr_Mid'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
assert not editor.get_game_world()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save current level edits before switching maps.'
lab = content / 'Lvl_LabTutorial.umap'
lab_hash = hashlib.sha256(lab.read_bytes()).hexdigest()

def vector(x=0, y=0, z=0):
    return unreal.Vector(x=x, y=y, z=z)

def import_asset(filename, name, options=None):
    path = root + '/' + name
    if A.does_asset_exist(path):
        return A.load_asset(path)
    task = unreal.AssetImportTask()
    properties = dict(filename=str(source / filename), destination_path=root,
                      destination_name=name, automated=True, save=True)
    if options is not None:
        properties['options'] = options
    for key, value in properties.items():
        task.set_editor_property(key, value)
    tools.import_asset_tasks([task])
    asset = A.load_asset(path)
    assert asset, path
    return asset

A.make_directory(root)
material_path = root + '/M_QuixelDryGrass'
material = A.load_asset(material_path) if A.does_asset_exist(material_path) else tools.create_asset(
    'M_QuixelDryGrass', root, unreal.Material, unreal.MaterialFactoryNew())
M.delete_all_material_expressions(material)
material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
material.set_editor_property('opacity_mask_clip_value', .20)
material.set_editor_property('two_sided', True)
material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
for index, (name, target) in enumerate((
        ('BaseColor', unreal.MaterialProperty.MP_BASE_COLOR),
        ('Normal', unreal.MaterialProperty.MP_NORMAL),
        ('Opacity', unreal.MaterialProperty.MP_OPACITY_MASK),
        ('Roughness', unreal.MaterialProperty.MP_ROUGHNESS),
        ('AO', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION))):
    texture = import_asset(f'{prefix}_2K_{name}.jpg', 'T_DryGrass_' + name)
    texture.set_editor_property('srgb', name == 'BaseColor')
    texture.set_editor_property('compression_settings', {
        'BaseColor': unreal.TextureCompressionSettings.TC_DEFAULT,
        'Normal': unreal.TextureCompressionSettings.TC_NORMALMAP,
    }.get(name, unreal.TextureCompressionSettings.TC_MASKS))
    texture.set_editor_property('max_texture_size', 2048)
    save(texture)
    sample = M.create_material_expression(material, unreal.MaterialExpressionTextureSample, -420, index * 180)
    sample.set_editor_property('texture', texture)
    sampler = 'SAMPLERTYPE_VIRTUAL_' if texture.virtual_texture_streaming else 'SAMPLERTYPE_'
    sampler += {'BaseColor': 'COLOR', 'Normal': 'NORMAL'}.get(name, 'MASKS')
    sample.set_editor_property('sampler_type', getattr(unreal.MaterialSamplerType, sampler))
    if name == 'BaseColor':
        tint = M.create_material_expression(material, unreal.MaterialExpressionMultiply, -200, index * 180)
        tint.set_editor_property('const_b', .55)
        assert M.connect_material_expressions(sample, 'RGB', tint, 'A')
        assert M.connect_material_property(tint, '', target)
        assert M.connect_material_property(tint, '', unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    else:
        assert M.connect_material_property(sample, 'RGB' if name == 'Normal' else 'R', target)
M.recompile_material(material)
save(material)

blueprint_path = root + '/BP_CityQuixelDryGrass'
if A.does_asset_exist(blueprint_path):
    blueprint = A.load_asset(blueprint_path)
else:
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.Actor)
    blueprint = tools.create_asset('BP_CityQuixelDryGrass', root, unreal.Blueprint, factory)
add(blueprint, unreal.SceneComponent, 'GrassRoot').set_mobility(unreal.ComponentMobility.STATIC)
for _, component, name in components(blueprint):
    if name == 'DefaultSceneRoot' and isinstance(component, unreal.SceneComponent):
        component.set_mobility(unreal.ComponentMobility.STATIC)

options = unreal.FbxImportUI()
for key, value in dict(import_mesh=True, import_as_skeletal=False, import_materials=False,
                       import_textures=False, automated_import_should_detect_type=False,
                       mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
    options.set_editor_property(key, value)
options.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
options.static_mesh_import_data.set_editor_property('combine_meshes', True)

variants = []
for letter in 'ABCDE':
    stem = f'{prefix}_tbbqejqr_Var{letter}_LOD'
    mesh = import_asset(stem + '0.fbx', 'SM_DryGrass_' + letter, options)
    if mesh_editor.get_lod_count(mesh) < 2:
        assert mesh_editor.import_lod(mesh, 1, str(source / (stem + '1.fbx'))) == 1, letter
    for slot in range(len(mesh.static_materials)):
        mesh.set_material(slot, material)
    save(mesh)
    box = mesh.get_bounding_box()
    height = box.max.z - box.min.z
    assert height > 0, letter
    group = add(blueprint, unreal.HierarchicalInstancedStaticMeshComponent, 'Grass_' + letter, 'GrassRoot')
    group.clear_instances()
    group.set_static_mesh(mesh)
    group.set_mobility(unreal.ComponentMobility.STATIC)
    group.set_collision_profile_name('NoCollision')
    group.set_editor_property('can_ever_affect_navigation', False)
    group.set_cull_distances(5500, 8500)
    variants.append((group, box, mesh_editor.get_lod_count(mesh)))

rng = random.Random(5132)
weighted_variants = variants[:3] * 3 + variants[3:]
for side in (-1, 1):
    for y in (24770, 25370, 26080, 27060, 27920, 28900, 29870, 30790, 31650, 32550, 33220):
        for index in range(rng.randint(10, 14)):
            group, box, _ = rng.choice(weighted_variants)
            # Keep the natural difference between upright tufts and fallen blades.
            scale = rng.uniform(.62, .95)
            location = vector(side * rng.choice((rng.uniform(730, 805), rng.uniform(1165, 1235))),
                              y + rng.uniform(-145, 145), 41 - box.min.z * scale)
            rotation = unreal.Rotator(yaw=rng.uniform(0, 360))
            group.add_instance(unreal.Transform(location=location, rotation=rotation, scale=vector(scale, scale, scale)), False)

counts = [group.get_instance_count() for group, _, _ in variants]
lods = [lod for _, _, lod in variants]
placements = {group.static_mesh.get_name(): [group.get_instance_transform(i, False) for i in range(group.get_instance_count())]
              for group, _, _ in variants}
assert all(counts) and all(lod >= 2 for lod in lods)
compile_bp(blueprint)
save(blueprint)
backup = saved / 'Backups/QuixelCityGrass' / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True, exist_ok=True)
report = {'lods': lods, 'tufts': sum(counts), 'maps': {}}
for name in ('Lvl_CampusConnected', 'Lvl_SurfaceArrival'):
    shutil.copy2(content / f'Surface/{name}.umap', backup)
    path = '/Game/Surface/' + name
    assert unreal.EditorLoadingAndSavingUtils.load_map(path)
    scene = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
    city = scene['CITY_FirstDowntownBlock']
    grass = scene.get('CITY_QuixelDryGrass')
    if grass is None:
        grass = actors.spawn_actor_from_class(B.generated_class(blueprint), city.get_actor_location(), city.get_actor_rotation())
    grass.set_actor_label('CITY_QuixelDryGrass')
    grass.set_folder_path('SURFACE/City Vegetation')
    grass.modify()
    grass.root_component.set_mobility(unreal.ComponentMobility.STATIC)
    assert actors.set_actor_transform(grass, city.get_actor_transform())
    assert (grass.get_actor_location() - city.get_actor_location()).length() < 1
    for group in grass.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
        group.modify()
        group.clear_instances()
        for transform in placements[group.static_mesh.get_name()]:
            group.add_instance(transform, False)
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    assert unreal.EditorLoadingAndSavingUtils.load_map(path)
    groups = [actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == 'CITY_QuixelDryGrass']
    assert len(groups) == 1
    city = next(actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == 'CITY_FirstDowntownBlock')
    assert (groups[0].get_actor_location() - city.get_actor_location()).length() < 1
    instances = groups[0].get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent)
    assert sum(group.get_instance_count() for group in instances) == sum(counts)
    assert all(str(group.get_collision_profile_name()) == 'NoCollision' for group in instances)
    assert all(.60 <= group.get_instance_transform(0, False).scale3d.x <= .96 for group in instances)
    report['maps'][name] = sum(counts)

assert hashlib.sha256(lab.read_bytes()).hexdigest() == lab_hash
report['passed'] = True
(saved / 'quixel_city_grass.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
editor.set_level_viewport_camera_info(vector(1030, 24570, 140), unreal.Rotator(pitch=-15, yaw=52, roll=0))
levels.editor_set_game_view(True)
