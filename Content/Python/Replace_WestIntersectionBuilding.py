"""Replace the west intersection placeholder with the rebuilt four-sided ruin."""
from datetime import datetime
import hashlib
import json
import shutil

import unreal

from Build_RuinedUrbanCampus import A, LEVEL, V, actors, content, levels, saved
from Repair_LegacyCityFacades import import_shell

ROOT = '/Game/Environment/CityExpansion'
NAME = 'SM_District_RuinedCornerWest'
LABEL = 'CITY_Detail_West_Building'
MAP_FILE = content / 'Surface' / 'Lvl_CampusConnected.umap'


def model():
    reclaim = '/Game/Environment/CityReclaim/M_Reclaim_'
    palette = {key: A.load_asset(reclaim+key) for key in
               ('Armor', 'Concrete', 'Cyan', 'Frame', 'Glass', 'Interior', 'Scorch', 'Shards')}
    palette.update(Panel=A.load_asset(ROOT+'/M_District_Panel'),
                   Mortar=A.load_asset('/Game/Surface/Materials/M_RuinConcrete'),
                   Oxide=A.load_asset('/Game/Surface/Materials/M_Oxide'))
    assert all(palette.values())
    return import_shell(NAME, ROOT, palette)


def replace(world):
    assert world.get_path_name().split('.')[0] == LEVEL
    actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == LABEL)
    c = actor.static_mesh_component
    previous = c.get_editor_property('static_mesh')
    assert previous.get_name() in ('SM_Building1', NAME), previous.get_name()
    bounds = previous.get_bounding_box()
    transform = actor.get_actor_transform()
    center = transform.transform_location((bounds.min + bounds.max) * .5)
    low = transform.transform_location(bounds.min)
    size = bounds.max - bounds.min
    size = V((size.x * transform.scale3d.x, size.y * transform.scale3d.y,
              size.z * transform.scale3d.z))
    rotation = actor.get_actor_rotation()

    backup = saved/'Backups'/'WestIntersection'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True)
    shutil.copy2(MAP_FILE, backup)
    unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
    mesh = model()
    b = mesh.get_bounding_box()
    span = b.max - b.min
    scale = V((size.x/span.x, size.y/span.y, size.z/span.z))
    midpoint = (b.max + b.min) * .5
    offset = unreal.Transform(rotation=rotation).transform_location(
        V((midpoint.x*scale.x, midpoint.y*scale.y, 0.)))
    p = center - offset
    p.z = low.z - b.min.z*scale.z
    actor.modify()
    c.modify()
    c.set_static_mesh(mesh)
    c.set_editor_property('override_materials', [])
    c.set_collision_profile_name('BlockAll')
    assert actors.set_actor_transform(actor, unreal.Transform(location=p, rotation=rotation, scale=scale))
    return actor, backup


def verify(world, actor):
    center, half = actor.get_actor_bounds(False)

    def hit(a,b,complex):
        result = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.ECC_VISIBILITY,
            complex, [], unreal.DrawDebugTrace.NONE, False)
        return bool(result and result.to_tuple()[9] == actor)

    checks = {}
    for complex in (False,True):
        checks[str(complex)] = {}
        for name,n,t,depth,span in (
                ('west',V((-1,0,0)),V((0,1,0)),half.x,half.y),
                ('east',V((1,0,0)),V((0,1,0)),half.x,half.y),
                ('south',V((0,-1,0)),V((1,0,0)),half.y,half.x),
                ('north',V((0,1,0)),V((1,0,0)),half.y,half.x)):
            good = 0
            for tier in (-.76,-.40,0.,.40,.78):
                for s in (-.72,-.37,0.,.37,.72):
                    p = center + t*(span*s) + V((0,0,half.z*tier))
                    good += hit(p+n*(depth+190.), p+n*(depth-130.), complex)
            assert good >= 10, (name, good, complex)
            checks[str(complex)][name] = good
        roof = 0
        for dx in (-.68,0.,.68):
            for dy in (-.64,0.,.64):
                p = center + V((half.x*dx,half.y*dy,half.z))
                roof += hit(p+V((0,0,220.)),p-V((0,0,115.)),complex)
        assert roof >= 5, (roof, complex)
        checks[str(complex)]['roof'] = roof
    return checks


def save_replacement(world, actor, backup):
    results = verify(world,actor)
    assert hashlib.sha256((backup/MAP_FILE.name).read_bytes()).digest() == hashlib.sha256(MAP_FILE.read_bytes()).digest()
    assert levels.save_map(world,LEVEL),LEVEL
    report = dict(actor=LABEL, asset=ROOT+'/'+NAME, verified=results, backup=str(backup), map=LEVEL)
    (saved/'WallRepair'/'Installed.json').write_text(json.dumps(report,indent=2))
