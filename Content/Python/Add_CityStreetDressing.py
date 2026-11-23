"""Extend the city street with a small intersection, service lots and parked vehicles."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from Industrial_Common import A, save

content = Path(unreal.Paths.project_content_dir()).resolve()
saved = Path(unreal.Paths.project_saved_dir()).resolve()
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
assert not editor.get_game_world()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
lab = content / 'Lvl_LabTutorial.umap'
lab_hash = hashlib.sha256(lab.read_bytes()).hexdigest()
backup = saved / 'Backups/CityStreetDressing' / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True)

def v(x=0, y=0, z=0):
    return unreal.Vector(x=x, y=y, z=z)

folder = '/Game/City/Props/DeliveryVan'
van_path = folder + '/SM_CityDeliveryVan/StaticMeshes/SM_CityDeliveryVan'
if not A.does_asset_exist(van_path):
    task = unreal.AssetImportTask()
    task.filename = str(content.parent / 'SourceAssets/CityDressing/SM_CityDeliveryVan.glb')
    task.destination_path = folder
    task.destination_name = 'SM_CityDeliveryVan'
    task.automated = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
van = A.load_asset(van_path)
if not van:
    candidates = [A.load_asset(path) for path in A.list_assets(folder, recursive=True)]
    van = next(mesh for mesh in candidates if isinstance(mesh, unreal.StaticMesh))
assert len(van.static_materials) >= 5

geometry = '/Game/CityDowntown/Geometry/'
materials = '/Game/CityDowntown/Materials/'
assets = {}
def asset(path):
    if path not in assets:
        assets[path] = A.load_asset(path)
        assert assets[path], path
    return assets[path]

building_meshes = [asset(geometry + 'LowPolyBuilding/SM_Building' + n) for n in ('1', '2')]
roadworks = asset(geometry + 'Props/SM_RoadConstruction_small')
if any(slot.material_interface is None for slot in roadworks.static_materials):
    for index, slot in enumerate(roadworks.static_materials):
        if slot.material_interface is None:
            roadworks.set_material(index, asset(materials + 'MI_RoadConstruction01'))
    save(roadworks)
for mesh in (van, *building_meshes):
    if mesh_editor.get_simple_collision_count(mesh) == 0:
        assert mesh_editor.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX) >= 0
        save(mesh)

maps = {}
for name in ('Lvl_CampusConnected', 'Lvl_SurfaceArrival'):
    path = '/Game/Surface/' + name
    shutil.copy2(content / f'Surface/{name}.umap', backup)
    assert unreal.EditorLoadingAndSavingUtils.load_map(path)
    scene = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
    city = scene['CITY_FirstDowntownBlock']
    frame = city.get_actor_transform()
    labels = []

    def place(code, mesh, x, y, floor, yaw=0, dimensions=None, block=False, material=None):
        label = 'CITY_Detail_' + code
        model_bounds = mesh.get_bounding_box()
        source_size = model_bounds.max - model_bounds.min
        scale = v(1, 1, 1)
        if dimensions is not None:
            scale = v(*(target / max(.001, actual) if target else 1
                        for target, actual in zip(dimensions, (source_size.x, source_size.y, source_size.z))))
        midpoint = (model_bounds.max + model_bounds.min) * .5
        angle = math.radians(yaw)
        mx, my = midpoint.x * scale.x, midpoint.y * scale.y
        local_position = v(x - mx * math.cos(angle) + my * math.sin(angle),
                           y - mx * math.sin(angle) - my * math.cos(angle),
                           floor - model_bounds.min.z * scale.z)
        position = unreal.MathLibrary.transform_location(frame, local_position)
        rotation = unreal.Rotator(yaw=city.get_actor_rotation().yaw + yaw)
        actor = scene.get(label) or actors.spawn_actor_from_class(unreal.StaticMeshActor, position, rotation)
        actor.modify()
        component = actor.static_mesh_component
        component.modify()
        component.set_static_mesh(mesh)
        component.set_collision_profile_name('BlockAll' if block else 'NoCollision')
        if material:
            component.set_material(0, material)
        component.set_mobility(unreal.ComponentMobility.STATIC)
        assert actors.set_actor_transform(actor, unreal.Transform(location=position, rotation=rotation, scale=scale))
        actor.set_actor_label(label)
        actor.set_folder_path('SURFACE/City Street Details')
        labels.append(label)
        return actor

    cube = asset('/Engine/BasicShapes/Cube')
    asphalt = asset(materials + 'MI_Asphalt')
    dirt = asset('/Game/Surface/Materials/M_Dust')
    concrete = asset('/Game/Surface/Materials/M_RuinConcrete')
    road = asset(geometry + 'RoadDecalsAndProps/SM_roadPiece3lanes')
    walk = asset(geometry + 'RoadDecalsAndProps/walkside_6x6_simple')
    cross = asset(geometry + 'RoadDecalsAndProps/SM_roadCrossPiece3x3')
    place('IntersectionBase', cube, 0, 34500, -10, dimensions=(6900, 1400, 30), block=True, material=asphalt)
    place('Intersection', cross, 0, 34500, 22, dimensions=(1400, 1400, 0), material=asphalt)
    place('StreetExtensionBase', cube, 0, 36150, -10, dimensions=(1400, 1900, 30), block=True, material=asphalt)
    place('StreetExtension', road, 0, 36150, 22, dimensions=(1400, 1900, 0), material=asphalt)
    for index, side in enumerate((-1, 1)):
        key = 'West' if side < 0 else 'East'
        place(key + '_SideRoad', road, side*2075, 34500, 22, yaw=90, dimensions=(1400, 2750, 0), material=asphalt)
        place(key + '_ServiceYard', cube, side*2190, 36610, -12, dimensions=(2100, 2300, 35), block=True, material=dirt)
        place(key + '_WalkBase', cube, side*1000, 36200, 12, dimensions=(600, 2000, 26), block=True, material=concrete)
        for tile in range(3):
            place(key + '_Paving_' + str(tile), walk, side*1000, 35525+tile*650, 37, dimensions=(600, 650, 0))
        building = building_meshes[index]
        repaired = '/Game/Environment/CityExpansion/SM_District_RuinedCornerWest'
        if side < 0 and name == 'Lvl_CampusConnected' and A.does_asset_exist(repaired):
            building = asset(repaired)
        place(key + '_Building', building, side*2250, 37010, 23,
              yaw=0 if side < 0 else 180, dimensions=(1740, 1150, 1500 if side < 0 else 1890), block=True)
        props = (
            ('Signal', 'SM_trafficLightPole01', 1070, 33700, 40, 90),
            ('JunctionBarrier', 'SM_metallicBarrier', 2910, 35270, 22, 90),
            ('Dumpster', 'SM_Bin', 1640, 35970, 23, 90),
            ('Box', 'SM_box02', 1520, 36075, 23, 30),
            ('Trash', 'SM_trashBag02', 1600, 36125, 23, 40),
            ('RoadWorks', 'SM_RoadConstruction_small', 2980, 34640, 24, 90),
        )
        for code, model, x, y, floor, yaw in props:
            place(key + '_' + code, asset(geometry + 'Props/' + model), side*x, y, floor, yaw=side*yaw)
        for index, y in enumerate((25570, 28330, 31980, 34970)):
            place(key + '_Drain_' + str(index), asset(geometry + 'RoadDecalsAndProps/SM_sewer2'), side*520, y, 27)

    van_bounds = van.get_bounding_box()
    van_size = van_bounds.max - van_bounds.min
    along_street = 0 if van_size.y > van_size.x else 90
    place('ServiceVan', van, -510, 28650, 26, yaw=along_street+7, block=True)
    place('EvacuationVan', van, 485, 34720, 26, yaw=along_street-18, block=True)
    wreck = asset('/Game/Surface/Meshes/SM_WreckedSedan')
    place('AbandonedSedan', wreck, 2350, 34770, 26, yaw=90, block=True)
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    assert unreal.EditorLoadingAndSavingUtils.load_map(path)
    labels_after = {actor.get_actor_label() for actor in actors.get_all_level_actors()}
    assert set(labels) <= labels_after and 'CITY_QuixelDryGrass' in labels_after
    maps[name] = len(labels)

assert hashlib.sha256(lab.read_bytes()).hexdigest() == lab_hash
(saved / 'city_street_dressing.json').write_text(json.dumps(dict(passed=True, maps=maps, van=str(van.get_path_name()),
    van_bounds=str(van_bounds), van_material_slots=len(van.static_materials)), indent=2), encoding='utf-8')
editor.set_level_viewport_camera_info(v(100, 33450, 480), unreal.Rotator(pitch=-10, yaw=90, roll=0))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
