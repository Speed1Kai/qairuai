"""Close the downtown shells and make normal and F6 flight respect city geometry."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from Industrial_Common import A, G, M, compile_bp, components, save, val

content = Path(unreal.Paths.project_content_dir())
saved = Path(unreal.Paths.project_saved_dir())
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not editor.get_game_world()
lab = content / 'Lvl_LabTutorial.umap'
lab_hash = hashlib.sha256(lab.read_bytes()).hexdigest()
backup = saved / 'Backups' / 'CityBuildingShells' / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
map_names = ('Lvl_CampusConnected', 'Lvl_SurfaceArrival')
player_path = 'ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
ruin_names = ('SM_Ruin_A', 'SM_Ruin_B', 'SM_Ruin_C', 'SM_Ruin_D', 'SM_ArchitectTower')
for relative in [player_path + '.uasset', 'Surface/BP_SurfaceEnvironment.uasset', *(f'Surface/{name}.umap' for name in map_names),
                 *(f'Surface/Meshes/{name}.uasset' for name in ruin_names)]:
    destination = backup / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(content / relative, destination)

player = A.load_asset('/Game/' + player_path)
toggle = G.get_graph_editor_by_name(player, 'Admin_ToggleFlight')
disable_collision = [n.find_input_pin('bNewActorEnableCollision') for n in toggle.list_all_nodes()]
unbound = [p for p in disable_collision if p.is_valid() and not p.list_connected_pins()]
assert len(unbound) == 1
val(unbound[0], True)
update = G.get_graph_editor_by_name(player, 'Admin_UpdateFlight')
offset = [n for n in update.list_all_nodes() if n.find_input_pin('DeltaLocation').is_valid()]
assert len(offset) == 1
val(offset[0].find_input_pin('bSweep'), True)
val(offset[0].find_input_pin('bTeleport'), False)
compile_bp(player)
save(player)

for name in ruin_names:
    mesh = A.load_asset('/Game/Surface/Meshes/' + name)
    body = mesh.get_editor_property('body_setup')
    assert body, name
    body.modify()
    body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    body.set_editor_property('double_sided_geometry', True)
    save(mesh)

environment = A.load_asset('/Game/Surface/BP_SurfaceEnvironment')
ruin_templates = {component.static_mesh.get_name(): component for _, component, _ in components(environment)
                  if isinstance(component, unreal.InstancedStaticMeshComponent)
                  and component.static_mesh and component.static_mesh.get_name() in ruin_names}
assert set(ruin_templates) == set(ruin_names)
for component in ruin_templates.values():
    component.set_collision_profile_name('BlockAll')
compile_bp(environment)
save(environment)

root = '/Game/Environment/DowntownFirstBlock'
path = root + '/M_DowntownBrickInfill'
brick = A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    'M_DowntownBrickInfill', root, unreal.Material, unreal.MaterialFactoryNew())
M.delete_all_material_expressions(brick)
world_position = M.create_material_expression(brick, unreal.MaterialExpressionWorldPosition, -620, -100)
normal = M.create_material_expression(brick, unreal.MaterialExpressionPixelNormalWS, -620, 60)
uv = M.create_material_expression(brick, unreal.MaterialExpressionCustom, -380, -80)
uv.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
inputs = []
for name in ('WorldPos', 'NormalWS'):
    entry = unreal.CustomInput()
    entry.set_editor_property('input_name', name)
    inputs.append(entry)
uv.set_editor_property('inputs', inputs)
uv.set_editor_property('code', 'float3 N = abs(NormalWS);\nreturn (N.z > 0.5 ? WorldPos.xy : float2(N.x > N.y ? WorldPos.y : WorldPos.x, -WorldPos.z)) / 320.0;')
assert M.connect_material_expressions(world_position, '', uv, 'WorldPos')
assert M.connect_material_expressions(normal, '', uv, 'NormalWS')
sample = M.create_material_expression(brick, unreal.MaterialExpressionTextureSample, -100, -80)
sample.set_editor_property('texture', A.load_asset('/Game/CityDowntown/Textures/Bricks/T_Bricks_BC'))
assert M.connect_material_expressions(uv, '', sample, 'UVs')
assert M.connect_material_property(sample, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
roughness = M.create_material_expression(brick, unreal.MaterialExpressionConstant, -90, 190)
roughness.set_editor_property('r', .87)
assert M.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
M.recompile_material(brick)
save(brick)

plan = json.loads((content.parent / 'SourceAssets/DowntownFirstBlock/selection.json').read_text(encoding='utf-8'))
cube = A.load_asset('/Engine/BasicShapes/Cube')
office = A.load_asset('/Game/Surface/Materials/M_RuinConcrete')
report = {'backup': str(backup), 'maps': {}}

for name in map_names:
    assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/' + name)
    scene = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
    city = scene['CITY_FirstDowntownBlock']
    frame = city.get_actor_transform()
    ruin_components = [c for c in scene['SURF_Environment'].get_components_by_class(unreal.StaticMeshComponent)
                       if c.static_mesh and c.static_mesh.get_name() in ruin_names]
    assert len(ruin_components) == len(ruin_names)

    filled = []
    for building in plan['buildings']:
        x, y, base = building['target_center']
        width, depth, height = building['size']
        code = building['source'].split('/')[-1]
        label = 'CITY_Shell_' + code
        # Keep the modular window facades and roof caps. Fill behind their faces.
        center = unreal.Vector(x=x, y=y, z=(22 + base + height - 12) / 2)
        position = unreal.MathLibrary.transform_location(frame, center)
        actor = scene.get(label) or actors.spawn_actor_from_class(unreal.StaticMeshActor, position, city.get_actor_rotation())
        actor.set_actor_label(label)
        actor.set_folder_path('SURFACE/First City Block/Shells')
        actor.set_actor_location(position, False, False)
        actor.set_actor_rotation(city.get_actor_rotation(), False)
        # Window modules sit well inside bounds that include cornices and signs.
        component = actor.static_mesh_component
        actor.modify()
        component.modify()
        component.set_editor_property('relative_scale3d', unreal.Vector(x=(width - 360) / 100, y=(depth - 350) / 100, z=(base + height - 34) / 100))
        component.set_static_mesh(cube)
        component.set_material(0, office if code == 'Building39' else brick)
        component.set_mobility(unreal.ComponentMobility.STATIC)
        # The existing aligned hull handles physics; this mesh closes the visible shell.
        component.set_collision_profile_name('NoCollision')
        component.set_editor_property('can_ever_affect_navigation', False)
        filled.append(label)
    report['maps'][name] = {'shells': filled, 'collidable_skyline_instances': sum(c.get_instance_count() for c in ruin_components)}
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()

assert lab_hash == hashlib.sha256(lab.read_bytes()).hexdigest()
(saved / 'city_building_repairs.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
editor.set_level_viewport_camera_info(unreal.Vector(x=-6500,y=23200,z=4300),unreal.Rotator(pitch=-17,yaw=35,roll=0))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
