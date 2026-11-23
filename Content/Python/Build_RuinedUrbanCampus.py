"""Rebuild the playable laboratory exterior as a bombed urban district."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math
import random
import shutil

import unreal
from Industrial_Common import A, B, V, add, components, compile_bp, save

LEVEL = '/Game/Surface/Lvl_CampusConnected'
MAIN = '/Game/Lvl_LabTutorial'
PLAN = '/Game/Surface/ReferencePlan/BP_ReferenceCampus'
ROOT = '/Game/Surface/RuinedCampus'
OFFSET = (10006.289955343997, 6612.598659341473, 2150.)
# World-space X, Y, half-width and depth. All three cuts are off the lab exit lane.
CRATERS = ((4340, 2550, 715, 165), (7440, 2790, 790, 210), (2710, 5060, 635, 145))
GROUND = 2150.
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.EditorLoadingAndSavingUtils
tools = unreal.AssetToolsHelpers.get_asset_tools()
saved = Path(unreal.Paths.project_saved_dir()).resolve()
content = Path(unreal.Paths.project_content_dir()).resolve()
rng = random.Random(117)

MAT = {key: A.load_asset('/Game/Surface/Materials/' + name) for key, name in (
    ('concrete', 'M_RuinConcrete'), ('steel', 'M_RuinSteel'), ('black', 'M_Charcoal'),
    ('rust', 'M_Oxide'), ('asphalt', 'M_Asphalt'), ('soil', 'M_Dust'),
    ('stripe', 'M_LanePaint'), ('amber', 'M_ExitAmber'),
)}
CUBE = A.load_asset('/Engine/BasicShapes/Cube')
CYLINDER = A.load_asset('/Engine/BasicShapes/Cylinder')


def local(x, y, z):
    return V((x - OFFSET[0], y - OFFSET[1], z - OFFSET[2]))


def crater_mesh(index, half, depth):
    name = f'SM_ImpactCrater_{index}'
    path = ROOT + '/' + name
    if not A.does_asset_exist(path):
        source = saved / 'RuinedCampusSource'
        source.mkdir(exist_ok=True)
        file = source / (name + '.obj')
        mats = ['concrete', 'soil', 'black']
        rows = [(0.14, -1.), (.37, -.92), (.57, -.65), (.76, .13), (.92, .045), (1., 0.)]
        vertices = [(0, 0, -depth)]
        steps = 40
        for radius, height in rows:
            for k in range(steps):
                angle = math.tau * k / steps
                x, y = math.cos(angle), math.sin(angle)
                rough = .94 + .056 * math.sin(angle * 5 + index) + .028 * math.cos(angle * 9)
                distance = half / max(abs(x), abs(y)) if radius == 1. else half * radius * rough
                z = 0. if radius == 1. else depth * (height + .035 * math.sin(angle * 7 + radius * 8))
                vertices.append((x * distance, y * distance, z))
        with file.open('w', encoding='ascii') as obj:
            obj.write(f'mtllib {name}.mtl\no {name}\n')
            for x, y, z in vertices:
                obj.write(f'v {x:.4f} {-y:.4f} {z:.4f}\nvt {x / 110:.4f} {y / 110:.4f}\n')
            def face(a, b, c):
                obj.write(f'f {c}/{c} {b}/{b} {a}/{a}\n')
            obj.write('usemtl black\n')
            for k in range(steps):
                face(1, 2 + k, 2 + (k + 1) % steps)
            for ring in range(len(rows) - 1):
                inner = 2 + steps * ring
                outer = inner + steps
                obj.write('usemtl ' + ('soil' if ring < 3 else 'concrete') + '\n')
                for k in range(steps):
                    k1 = (k + 1) % steps
                    face(inner + k, outer + k, outer + k1)
                    face(inner + k, outer + k1, inner + k1)
        file.with_suffix('.mtl').write_text(''.join(f'newmtl {m}\nKd .2 .2 .2\n' for m in mats))
        opts = unreal.FbxImportUI()
        for key, value in dict(import_mesh=True, import_materials=False, import_textures=False,
                               automated_import_should_detect_type=False,
                               mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
            opts.set_editor_property(key, value)
        opts.static_mesh_import_data.set_editor_property('combine_meshes', True)
        task = unreal.AssetImportTask()
        for key, value in dict(filename=str(file), destination_path=ROOT,
                               automated=True, options=opts, save=False).items():
            task.set_editor_property(key, value)
        tools.import_asset_tasks([task])
    mesh = A.load_asset(path)
    assert mesh, path
    extent = mesh.get_bounding_box()
    assert abs((extent.max.x - extent.min.x) - 2 * half) < 3 and abs(extent.min.z + depth) < depth * .05, str(extent)
    for i, slot in enumerate(mesh.static_materials):
        material = MAT.get(str(slot.material_slot_name))
        if material:
            mesh.set_material(i, material)
    mesh.get_editor_property('body_setup').set_editor_property(
        'collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh)
    return mesh


def subtract(rect, hole):
    x0, x1, y0, y1 = rect
    hx0, hx1 = max(x0, hole[0]), min(x1, hole[1])
    hy0, hy1 = max(y0, hole[2]), min(y1, hole[3])
    if hx0 >= hx1 or hy0 >= hy1:
        return [rect]
    return [r for r in ((x0, hx0, y0, y1), (hx1, x1, y0, y1),
                        (hx0, hx1, y0, hy0), (hx0, hx1, hy1, y1))
            if r[1] - r[0] > .01 and r[3] - r[2] > .01]


def damage_plan(bp):
    changes = {}
    holes = [(x - r, x + r, y - r, y + r) for x, y, r, _ in CRATERS]
    seen = set()
    for _, c, name in components(bp):
        if not isinstance(c, unreal.InstancedStaticMeshComponent) or name in seen:
            continue
        seen.add(name)
        remove, insert = [], []
        for i in range(c.get_instance_count()):
            t = c.get_instance_transform(i, False)
            p, s, rot = t.translation, t.scale3d, t.rotation.rotator()
            x, y, z = (p.x + OFFSET[0], p.y + OFFSET[1], p.z)
            breach = ((x < 1700 and 3900 < y < 7350) or
                      (x > 10450 and 4700 < y < 7700) or
                      (x < 3950 and 11900 < y < 14200))
            # The original fence beams are high and their mesh thickness is 3 cm.
            wire = name == 'Box_steel_Detail' and 609 < z < 681 and s.z < .05 and s.y < .05
            cut_long_wire = wire and s.x > 10 and (x < 1600 or x > 10900)
            if (name == 'ImportedConcretePerimeter' and breach) or cut_long_wire:
                remove.append(i)
                continue
            if name == 'Box_amber_Detail' and z < 15 and any(h[0] < x < h[1] and h[2] < y < h[3] for h in holes):
                remove.append(i)
                continue
            if name not in ('Box_floor_Collision', 'ExteriorWalkwayPaving', 'Box_asphalt_Detail') or not -45 < z < 15:
                continue
            cardinal = round(rot.yaw / 90)
            if abs(rot.yaw - cardinal * 90) > .1:
                continue
            swapped = cardinal % 2
            sx, sy = (s.y, s.x) if swapped else (s.x, s.y)
            rect = (x - 50 * sx, x + 50 * sx, y - 50 * sy, y + 50 * sy)
            pieces = [rect]
            for hole in holes:
                pieces = [piece for part in pieces for piece in subtract(part, hole)]
            if pieces == [rect]:
                continue
            remove.append(i)
            for x0, x1, y0, y1 in pieces:
                dx, dy = (x1-x0)/100, (y1-y0)/100
                scale = (dy, dx, s.z) if swapped else (dx, dy, s.z)
                insert.append(unreal.Transform(location=local((x0+x1)/2, (y0+y1)/2, z+GROUND),
                                               rotation=rot, scale=V(scale)))
        if remove:
            c.modify()
            for i in reversed(remove):
                c.remove_instance(i)
            for transform in insert:
                c.add_instance(transform, False)
            changes[name] = (len(remove), len(insert))
    compile_bp(bp)
    save(bp)
    return changes


def make_static_root(bp, root):
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    records = components(bp)
    root_handle = next(handle for handle, _, name in records if name == 'SiteRoot')
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    if not library.is_root_component(library.get_data(root_handle)):
        assert subsystem.make_new_scene_root(records[0][0], root_handle, bp)
    root.set_mobility(unreal.ComponentMobility.STATIC)


class Site:
    def __init__(self, bp):
        self.bp = bp
        self.root = add(bp, unreal.SceneComponent, 'SiteRoot')
        make_static_root(bp, self.root)
        self.batches = {}
        for _, c, _ in components(bp):
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                c.clear_instances()

    def mesh(self, key, mesh, x, y, z, scale=(1., 1., 1.), *, material=None,
             collide=False, yaw=0., pitch=0., roll=0.):
        if key not in self.batches:
            c = add(self.bp, unreal.HierarchicalInstancedStaticMeshComponent, key, 'SiteRoot')
            c.set_static_mesh(mesh)
            c.set_mobility(unreal.ComponentMobility.STATIC)
            c.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
            if material:
                c.set_material(0, MAT[material])
            c.set_cull_distances(0, 55000)
            self.batches[key] = c
        self.batches[key].add_instance(unreal.Transform(
            location=local(x, y, z), scale=V(scale), rotation=unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll)), False)

    def box(self, mat, x, y, z, sx, sy, sz, *, collide=False, yaw=0, pitch=0, roll=0):
        self.mesh('Box_' + mat + ('_Solid' if collide else ''), CUBE, x, y, z,
                  (sx/100, sy/100, sz/100), material=mat, collide=collide, yaw=yaw, pitch=pitch, roll=roll)

    def beam(self, mat, start, end, width):
        a, b = V(start), V(end)
        p = (a + b) * .5
        rot = unreal.MathLibrary.find_look_at_rotation(a, b)
        self.box(mat, p.x, p.y, p.z, (b-a).length(), width, width, yaw=rot.yaw, pitch=rot.pitch)

    def fitted(self, key, mesh, x, y, bottom, size, yaw=0, collide=False):
        bounds = mesh.get_bounding_box()
        spans = bounds.max - bounds.min
        center = (bounds.min + bounds.max) * .5
        sx, sy, sz = (size[0] / spans.x, size[1] / spans.y, size[2] / spans.z)
        angle = math.radians(yaw)
        dx, dy = center.x * sx, center.y * sy
        self.mesh(key, mesh, x - math.cos(angle)*dx + math.sin(angle)*dy,
                  y - math.sin(angle)*dx - math.cos(angle)*dy, bottom - bounds.min.z * sz,
                  (sx, sy, sz), yaw=yaw, collide=collide)

    def road(self, x, y, sx, sy, *, stripes=True):
        self.box('asphalt', x, y, GROUND+3, sx, sy, 6)
        if stripes:
            along_y = sy > sx
            length = sy if along_y else sx
            for n in range(-int(length/850), int(length/850)+1):
                self.box('stripe', x if along_y else x+n*420, y+n*420 if along_y else y,
                         GROUND+7, 12 if along_y else 155, 155 if along_y else 12, 2)


def build_gardens(site, craters):
    tree = A.load_asset('/Game/Surface/Meshes/SM_DeadTree')
    rubble = A.load_asset('/Game/Surface/Meshes/SM_RubbleCluster')
    for i, ((x, y, radius, depth), mesh) in enumerate(zip(CRATERS, craters)):
        site.mesh(f'Crater_{i}', mesh, x, y, GROUND + 0.35, collide=True)
        for j in range(11):
            angle = j * math.tau / 11 + rng.uniform(-.13, .13)
            px = x + math.cos(angle) * radius * rng.uniform(.72, 1.12)
            py = y + math.sin(angle) * radius * rng.uniform(.72, 1.09)
            scale = rng.uniform(.22, .53)
            site.mesh('ImpactRubble', rubble, px, py, GROUND + 4, (scale, scale, scale),
                      yaw=rng.randrange(360))
            if j % 2 == 0:
                end = (x + math.cos(angle) * radius * 1.26, y + math.sin(angle) * radius * 1.24, GROUND+4)
                site.beam('black', (px, py, GROUND+5), end, rng.uniform(3, 11))
    for x, y, size in (
        (3940, 1630, .80), (3370, 2070, .93), (3400, 3150, 1.15), (4090, 3530, .92),
        (4860, 3340, 1.05), (5140, 1870, .72), (6700, 1990, .83), (7560, 1710, 1.10),
        (8240, 2020, .81), (8060, 3560, 1.14), (7070, 3700, .81), (7670, 3940, .76),
        (1320, 7770, 1.02), (1900, 8140, .85), (2120, 5410, .89), (3210, 4580, .71),
    ):
        site.mesh('DeadGardenTrees', tree, x, y, GROUND+2, (size, size, size),
                  yaw=rng.randrange(360), pitch=rng.uniform(-9, 9))
    for x, y, yaw in ((3480, 2490, 20), (6890, 3480, -38), (3270, 5510, 70)):
        site.mesh('FallenGardenTrees', tree, x, y, GROUND+40, (.7, .7, .7), yaw=yaw, pitch=82)
    for x, y in ((3350, 1850), (4920, 3500), (7630, 3890), (8350, 1780)):
        site.box('soil', x, y, GROUND+4, 440, 280, 8)
        for dx, dy, sx, sy in ((-217, 0, 22, 280), (217, 0, 22, 190), (0, 140, 440, 22)):
            site.box('concrete', x+dx, y+dy, GROUND+18, sx, sy, 36)
    # Dislodged cladding along the lab entrance, clear of the central route.
    for side in (-1, 1):
        for j in range(5):
            x, y = 5850 + side * (410 + j * 92), 1760 + j * 94
            site.box('concrete', x, y, GROUND + rng.uniform(38, 78), 150+j*12, 100, 24,
                     yaw=rng.uniform(-45, 50), pitch=rng.uniform(-23, 24))
            site.beam('rust', (x-40, y+12, GROUND+26), (x+105, y-46, GROUND+112), 4)
    for x, y in ((-1010, 3920), (-1040, 7320), (-1030, 11900), (-1040, 14260),
                 (12200, 4400), (12200, 7770)):
        for i in range(3):
            site.box('concrete', x + i*118, y + rng.uniform(-100, 120), GROUND+65, 240, 200, 48,
                     yaw=rng.randrange(360), pitch=rng.uniform(-30, 30), roll=rng.uniform(-12, 35))
        site.mesh('ImpactRubble', rubble, x+85, y+55, GROUND, (.65, .65, .65), yaw=rng.randrange(360))


def annex(site, x, y, w, d, loading_bay):
    site.box('asphalt', x, y, GROUND+5, w+140, d+620, 10)
    front, back = y+d/2, y-d/2
    for ix in (-1, 1):
        for iy in (-1, 1):
            site.box('steel', x+ix*(w/2-50), y+iy*(d/2-50), GROUND+275, 60, 60, 550, collide=True)
    for j in range(7):
        px = x-w/2+(j+.5)*w/7
        height = 505 if j in (0, 1, 5, 6) else (250, 125, 355)[j-2]
        site.box('concrete', px, back, GROUND+height/2, w/7-5, 55, height, collide=True)
    for side in (-1, 1):
        for j in range(5):
            height = 490 if (j + side) % 4 else 220
            site.box('steel' if j % 2 else 'concrete', x+side*w/2, y-d/2+(j+.5)*d/5,
                     GROUND+height/2, 55, d/5-6, height, collide=True)
    for px in (x-w*.37, x+w*.37):
        site.box('concrete', px, front, GROUND+224, w*.24, 54, 448, collide=True)
    site.box('steel', x, front, GROUND+488, w, 74, 83, collide=True)
    if loading_bay:
        for i in range(9):
            site.box('rust', x, front-31, GROUND+155+i*32, w*.51, 37, 31, collide=True)
    for j in range(5):
        py = y-d/2+(j+.5)*d/5
        site.beam('steel', (x-w/2, py, GROUND+510), (x, py, GROUND+690), 28)
        site.beam('steel', (x, py, GROUND+690), (x+w/2, py, GROUND+510), 28)
        if j not in (1, 2) or not loading_bay:
            site.box('steel', x-w/4, py, GROUND+600, w*.52, d/5-8, 26, pitch=11)
        if j in (0, 3, 4):
            site.box('rust', x+w/4, py, GROUND+600, w*.52, d/5-8, 24, pitch=-11)
    site.box('steel', x+w*.31, front+35, GROUND+350, 164, 10, 39)
    site.box('amber', x+w*.31, front+41, GROUND+350, 135, 3, 9)


def parking(site):
    x, y = 5720, 12600
    site.road(x, y, 2490, 2240, stripes=False)
    for row in (-1, 1):
        for i in range(8):
            site.box('stripe', x-1050+i*300, y+row*750, GROUND+8, 9, 520, 2)
        site.box('stripe', x, y+row*1010, GROUND+8, 2110, 10, 2)
    wreck = A.load_asset('/Game/Surface/Meshes/SM_WreckedSedan')
    van = A.load_asset('/Game/City/Props/DeliveryVan/SM_CityDeliveryVan/StaticMeshes/SM_CityDeliveryVan')
    for i, (xx, yy, yaw) in enumerate(((5020, 11850, 90), (5670, 13350, 95), (6280, 11850, 70),
                                       (6620, 13350, -90))):
        site.fitted('ParkingWrecks', wreck, xx, yy, GROUND+7, (450, 184, 135), yaw, True)
    site.fitted('ParkingUtilityVan', van, 4970, 13350, GROUND+7, (195, 490, 210), 0, True)
    stop = A.load_asset('/Game/Surface/Meshes/SM_ConcreteBarrier')
    for xx in (4580, 6860):
        site.mesh('ParkingBarriers', stop, xx, y+1090, GROUND+7, (.72, .72, .72), yaw=10)


def urban_edges(site):
    # The new streets are joined to the old city north of the sealed gate.
    for x in (-3750, 15250):
        site.box('soil', x, 7000, GROUND-40, 4500, 25600, 80, collide=True)
    site.box('soil', 5800, 20200, GROUND-40, 22700, 4400, 80, collide=True)
    site.box('soil', 5800, -5610, GROUND-40, 15000, 2230, 80, collide=True)
    for x in (-2530, 14300):
        site.road(x, 6870, 1250, 25800)
        for side in (-1, 1):
            site.box('concrete', x+side*703, 6870, GROUND+7, 150, 25700, 14)
    site.road(5850, 19350, 17500, 1330)
    site.road(5850, 20900, 1380, 3100)
    # Cross-streets align with the damaged campus wall openings.
    site.road(330, 5900, 5500, 830, stripes=False)
    site.road(12000, 6100, 5050, 880, stripes=False)
    site.road(410, 13100, 5850, 760, stripes=False)
    plots = (
        (-4700, -1400, 2650, 2650, 3400), (-4700, 2400, 2700, 2850, 4350),
        (-4630, 7490, 2640, 2950, 3950), (-4650, 12030, 2700, 3200, 4800),
        (16000, -1800, 2400, 2680, 3400), (16100, 2340, 2600, 2900, 4350),
        (16050, 7150, 2500, 3050, 5000), (16100, 12300, 2500, 2900, 3800),
        (1850, -5620, 2360, 1670, 3850), (10050, -5680, 2900, 1670, 4200),
    )
    for i, (x, y, sx, sy, sz) in enumerate(plots, 1):
        asset = A.load_asset(f'/Game/Environment/Residential/Meshes/SM_Residential_{i:03d}')
        site.fitted(f'UrbanBlock_{i:02d}', asset, x, y, GROUND, (sx, sy, sz), 0 if i % 2 else 180, True)


def sign(label, text, x, y, z, yaw=90):
    actor = actors.spawn_actor_from_class(unreal.TextRenderActor, local(x, y, z),
                                         unreal.Rotator(yaw=yaw))
    actor.set_actor_label('RUIN_' + label)
    actor.set_folder_path('SURFACE/Ruined Urban Campus')
    widget = actor.text_render
    widget.set_text(unreal.Text(text))
    widget.set_world_size(43)
    widget.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    widget.set_text_render_color(unreal.Color(r=181, g=193, b=185, a=255))


def main():
    assert not levels.get_dirty_map_packages()
    lab = content / 'Lvl_LabTutorial.umap'
    lab_before = hashlib.sha256(lab.read_bytes()).hexdigest()
    backup = saved / 'Backups/RuinedUrbanCampus' / datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for file in (content / 'Surface/Lvl_CampusConnected.umap',
                 content / 'Surface/ReferencePlan/BP_ReferenceCampus.uasset'):
        shutil.copy2(file, backup)
    craters = [crater_mesh(i, half, depth) for i, (_, _, half, depth) in enumerate(CRATERS, 1)]
    path = ROOT + '/BP_RuinedUrbanCampus'
    bp = A.load_asset(path)
    if not bp:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset('BP_RuinedUrbanCampus', ROOT, unreal.Blueprint, factory)
    site = Site(bp)
    build_gardens(site, craters)
    annex(site, 1720, 2650, 1830, 1610, True)
    annex(site, 10430, 2760, 2200, 1770, False)
    parking(site)
    urban_edges(site)
    compile_bp(bp)
    save(bp)

    plan = A.load_asset(PLAN)
    changes = damage_plan(plan)
    world = levels.load_map(LEVEL)
    existing = None
    for actor in list(actors.get_all_level_actors()):
        label = actor.get_actor_label()
        if label.startswith('RUIN_'):
            assert actors.destroy_actor(actor)
        if label == 'REF_LaboratoryComplex':
            existing = actor
    assert existing
    origin = existing.get_actor_location()
    rotation = existing.get_actor_rotation()
    assert actors.destroy_actor(existing)
    rebuilt = actors.spawn_actor_from_class(B.generated_class(plan), origin, rotation)
    rebuilt.set_actor_label('REF_LaboratoryComplex')
    rebuilt.set_folder_path('SURFACE/ReferencePlan')
    exterior = actors.spawn_actor_from_class(B.generated_class(bp), unreal.Vector())
    exterior.set_actor_label('RUIN_Exterior')
    exterior.set_folder_path('SURFACE/Ruined Urban Campus')
    sign('Warehouse', 'СКЛАД / С-02', 1720, 3475, 2520)
    sign('Hangar', 'РЕМОНТНЫЙ АНГАР / А-03', 10430, 3665, 2575)
    sign('Parking', 'СТОЯНКА / АТЛАС', 4610, 11465, 2360, -90)
    world.modify()
    assert levels.save_map(world, LEVEL)
    del world
    assert levels.load_map(LEVEL)
    scene = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    exterior = scene['RUIN_Exterior']
    counts = {c.get_name(): c.get_instance_count()
              for c in exterior.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert all(counts.get(f'Crater_{i}') == 1 for i in range(3)), counts
    assert sum(n.startswith('UrbanBlock_') for n in counts) == 10
    assert counts.get('DeadGardenTrees') == 16
    assert hashlib.sha256(lab.read_bytes()).hexdigest() == lab_before
    assert levels.load_map(MAIN)
    (saved / 'ruined_urban_campus.json').write_text(json.dumps({
        'level': LEVEL, 'backup': str(backup), 'craters': CRATERS, 'edits': changes,
        'trees': 19, 'urban_buildings': 10, 'annexes': 2, 'parking_slots': 14,
        'instanced_mesh_batches': len(counts),
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
