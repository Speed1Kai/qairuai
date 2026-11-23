"""Break the real roofs and upper facade of the laboratory's existing shells."""
from datetime import datetime
import hashlib
import json
import math
import random
import shutil

import unreal
from Build_RuinedUrbanCampus import (
    A, B, ROOT, GROUND, LEVEL, MAIN, OFFSET, Site, V, actors, add,
    compile_bp, components, content, levels, local, save, saved, subtract, tools,
)

INTERIORS = '/Game/Surface/Interiors/BP_CampusInteriors'
# Open to the courtyard at the edges. Coordinates are in the streamed world frame.
# name, wall Y, impacted X range, removed roof rectangle, roof elevation above ground.
ZONES = (
    ('A_upper', 900, (4580, 6370), (4630, 6360, -95, 900), 1280),
    ('A_wing', 60, (7330, 8615), (7330, 8615, -790, 60), 1200),
    ('Main_lab', 5352, (4750, 6650), (4750, 6650, 5352, 6125), 2000),
)


def world_pos(transform):
    p = transform.translation
    return p.x + OFFSET[0], p.y + OFFSET[1], p.z


def roof_pieces(t, hole):
    x, y, z = world_pos(t)
    sx, sy, sz = t.scale3d.x, t.scale3d.y, t.scale3d.z
    bounds = (x-50*sx, x+50*sx, y-50*sy, y+50*sy)
    patches = subtract(bounds, hole)
    if patches == [bounds]:
        return None
    return [
        unreal.Transform(location=local((x0+x1)/2, (y0+y1)/2, z+GROUND),
                         scale=V(((x1-x0)/100, (y1-y0)/100, sz)))
        for x0, x1, y0, y1 in patches
    ]


def open_shell(bp):
    count = {name: {'roof_tiles_cut': 0, 'facade_pieces_removed': 0} for name, *_ in ZONES}
    seen = set()
    for _, batch, name in components(bp):
        if name in seen or not isinstance(batch, unreal.InstancedStaticMeshComponent):
            continue
        seen.add(name)
        if not name.startswith(('Box_floor_', 'Box_white_', 'Box_glass_', 'Box_steel_', 'Box_dark_', 'Box_teal_')):
            continue
        remove, patches = [], []
        for i in range(batch.get_instance_count()):
            t = batch.get_instance_transform(i, False)
            x, y, z = world_pos(t)
            s = t.scale3d
            for zone, wall_y, (x0, x1), hole, roof_z in ZONES:
                if name == 'Box_floor_Solid' and abs(z-(roof_z-12)) < 1 and abs(t.rotation.rotator().yaw) < .1:
                    pieces = roof_pieces(t, hole)
                    if pieces is not None:
                        remove.append(i)
                        patches.extend(pieces)
                        count[zone]['roof_tiles_cut'] += 1
                        break
                front = abs(y-wall_y) < 31
                side = (zone == 'A_upper' and abs(x-6360) < 20 and 40 < y < 900)
                if not (front or side) or not x0 < x < x1 or not roof_z-665 < z < roof_z+2:
                    continue
                # Leave a broken sill and one standing mullion on the lower damaged level.
                if z < roof_z-400 and (name.startswith('Box_white_') or (x-x0) % 550 < 100):
                    continue
                if min(s.x, s.y) > .38:
                    continue
                remove.append(i)
                count[zone]['facade_pieces_removed'] += 1
                break
        if not remove:
            continue
        batch.modify()
        for i in reversed(remove):
            batch.remove_instance(i)
        for t in patches:
            batch.add_instance(t, False)
    assert all(row['roof_tiles_cut'] and row['facade_pieces_removed'] for row in count.values()), count
    compile_bp(bp)
    save(bp)
    return count


def add_collapse():
    path = ROOT + '/BP_CollapsedLabShell'
    bp = A.load_asset(path) if A.does_asset_exist(path) else None
    if not bp:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset('BP_CollapsedLabShell', ROOT, unreal.Blueprint, factory)
    site = Site(bp)
    rubble = A.load_asset('/Game/Surface/Meshes/SM_RubbleCluster')
    rng = random.Random(453)
    for zone, y, (x0, x1), hole, roof_z in ZONES:
        direction = -1 if zone == 'Main_lab' else 1
        left, right, near, far = hole
        z = GROUND+roof_z
        for j in range(7):
            x = left + (j+.5)*(right-left)/7
            depth = rng.uniform(75, 220)
            py = (near if direction == 1 else far) + direction * depth * .35
            site.box('concrete', x, py, z-rng.uniform(8, 36), rng.uniform(133, 233), depth, 27,
                     yaw=rng.uniform(-21, 21), roll=rng.uniform(-35, 29))
            site.beam('rust', (x-20, py, z-28), (x+rng.uniform(-50, 60), py+direction*205, z-rng.uniform(65, 195)), 5)
            site.beam('steel', (x, y-direction*45, z-60), (x+rng.uniform(-75, 80), y+direction*rng.uniform(38, 170), z-rng.uniform(265, 430)), 14)
        for fraction in (.08, .91):
            x = x0 + (x1-x0)*fraction
            site.box('concrete', x, y, z-255, 72, 56, 300, pitch=rng.uniform(-20, 19))
        for j in range(12):
            x = x0 + (x1-x0)*rng.random()
            py = y + direction*rng.uniform(165, 480)
            # Keep the doorway and walk straight out of the laboratory clear.
            if 5425 < x < 6265 and 850 < py < 3500:
                continue
            d = rng.uniform(.22, .56)
            site.mesh('FallenLabDebris', rubble, x, py, GROUND+2, (d, d, d), yaw=rng.randrange(360))
        for j in range(3):
            x = left + (j+.4)*(right-left)/3
            site.box('concrete', x, (near+far)*.5+rng.uniform(-60, 60), z-392,
                     rng.uniform(115, 235), rng.uniform(105, 210), 36, yaw=rng.uniform(-35, 35), pitch=rng.uniform(-25, 22))
    compile_bp(bp)
    save(bp)
    return bp


def main():
    assert not levels.get_dirty_map_packages()
    start = content/'Lvl_LabTutorial.umap'
    old_hash = hashlib.sha256(start.read_bytes()).hexdigest()
    backup = saved/'Backups/LabShellCollapse'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for file in (content/'Surface/Lvl_CampusConnected.umap', content/'Surface/Interiors/BP_CampusInteriors.uasset'):
        shutil.copy2(file, backup)
    bp = A.load_asset(INTERIORS)
    collapse = add_collapse()
    count = open_shell(bp)
    world = levels.load_map(LEVEL)
    existing = None
    lights = []
    for actor in list(actors.get_all_level_actors()):
        label = actor.get_actor_label()
        if label == 'INT_AllCampusBuildings':
            existing = actor
        elif label == 'RUIN_LaboratoryShell':
            assert actors.destroy_actor(actor)
        elif isinstance(actor, unreal.PointLight) and label.startswith('INT_Light_'):
            p = actor.get_actor_location()
            x, y, z = p.x+OFFSET[0], p.y+OFFSET[1], p.z
            if any(a-100<x<b+100 and c-220<y<d+220 and height-620<z<height
                   for _, _, _, (a,b,c,d), height in ZONES):
                actor.modify()
                actor.point_light_component.set_visibility(False)
                lights.append(label)
    assert existing
    origin, rotation = existing.get_actor_location(), existing.get_actor_rotation()
    assert actors.destroy_actor(existing)
    fresh = actors.spawn_actor_from_class(B.generated_class(bp), origin, rotation)
    fresh.set_actor_label('INT_AllCampusBuildings')
    fresh.set_folder_path('SURFACE/Interiors')
    damaged = actors.spawn_actor_from_class(B.generated_class(collapse), unreal.Vector())
    damaged.set_actor_label('RUIN_LaboratoryShell')
    damaged.set_folder_path('SURFACE/Ruined Urban Campus')
    world.modify()
    assert levels.save_map(world, LEVEL)
    del world
    assert levels.load_map(LEVEL)
    assert any(a.get_actor_label() == 'RUIN_LaboratoryShell' for a in actors.get_all_level_actors())
    assert hashlib.sha256(start.read_bytes()).hexdigest() == old_hash
    (saved/'lab_shell_collapse.json').write_text(json.dumps(
        dict(saved=True, damage=count, lights_disabled=lights, backup=str(backup)), indent=2))
    assert levels.load_map(MAIN)


if __name__ == '__main__':
    main()
