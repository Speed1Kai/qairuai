"""Install the Police Mech encounter on the avenue in the connected city."""
from datetime import datetime
import json
import shutil

import unreal

from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, V, actors, add, content, levels, local, save, saved
from CityCombat_Common import FX, asset, compile_bp
from CityMachine_Logic import events, firing, motion, patrol, plan, variables
from Install_Catfish import animation_graphs, repair_assets
from Place_CityMachines import ROOT as MACHINES, root

STEM = 'PoliceMech'
ROOT = MACHINES + '/' + STEM
BLUEPRINT = MACHINES + '/BP_' + STEM
SOURCE = content.parent / 'SourceAssets' / 'CityMachines' / STEM
LABEL = 'CITY_Machine_PoliceMech'
SPAWN = (5850., 45100.)
ROUTE = ((-140., -1420., 0.), (160., 510., 0.), (110., 1950., 0.), (-170., -440., 0.))
HEIGHT = 540.
HULL_HEIGHT = 274.


def make_blueprint():
    manifest, mesh, walk = repair_assets(ROOT, SOURCE, STEM)
    scale = HEIGHT / (manifest['model_height'] * 100.)
    bp = asset(BLUEPRINT)
    hull = root(bp)
    hull.set_capsule_size(214., HULL_HEIGHT - 4.)
    body = add(bp, unreal.SkeletalMeshComponent, STEM + 'Body', 'Hull')
    body.set_skeletal_mesh_asset(mesh)
    body.set_mobility(unreal.ComponentMobility.MOVABLE)
    body.set_collision_profile_name('NoCollision')
    body.set_editor_property('can_ever_affect_navigation', False)
    body.set_editor_property('relative_location', V((0., 0., -HULL_HEIGHT)))
    body.set_editor_property('relative_scale3d', V((scale,) * 3))
    body.set_editor_property('visibility_based_anim_tick_option',
        unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    body.override_animation_data(walk, True, False, 0., 1.)
    for name in ('Muzzle', 'Sensor'):
        component = add(bp, unreal.SceneComponent, name, 'Hull')
        component.set_mobility(unreal.ComponentMobility.MOVABLE)

    contact = B.generated_class(A.load_asset(MACHINES + '/BP_RelayContact')).get_path_name()
    tracer = B.generated_class(A.load_asset(FX + '/BP_EnemyTracer')).get_path_name()
    variables(bp)
    patrol(bp)
    plan(bp, contact, STEM)
    motion(bp, STEM, 0, custom_gait=True)
    firing(bp, STEM, tracer, FX + '/S_Carbine')
    animation_graphs(bp, walk, STEM, manifest['stride_speed'] * scale * 100., max_rate=2.5)
    events(bp, STEM, custom_init=True)
    compile_bp(bp)

    cdo = unreal.get_default_object(B.generated_class(bp))
    for name, value in dict(HullHeight=HULL_HEIGHT, HullHealth=1120., CruiseSpeed=285.,
                            CombatSpeed=485., SensorRange=4950., FireRange=3350.,
                            KeepRange=1380., ShotDamage=15., FireCooldown=1.05, Windup=.38).items():
        cdo.set_editor_property(name, value)
    cdo.set_editor_property('tags', [unreal.Name(tag) for tag in ('CyborgHostile', 'CityMachine', STEM)])
    save(bp)
    return bp


def place(bp):
    world = levels.load_map(LEVEL)
    assert world, LEVEL
    x, y = SPAWN
    hit = unreal.SystemLibrary.line_trace_single(world, local(x, y, GROUND + 140.),
        local(x, y, GROUND - 210.), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
        unreal.DrawDebugTrace.NONE, False)
    assert hit, 'No road collision at the Police Mech spawn'
    road_z = hit.to_tuple()[5].z + GROUND
    position = local(x, y, road_z + HULL_HEIGHT)

    backup = saved / 'Backups' / STEM / datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content / (LEVEL.removeprefix('/Game/') + '.umap'), backup)

    cls = B.generated_class(bp)
    existing = [a for a in actors.get_all_level_actors() if a.get_actor_label() == LABEL]
    assert len(existing) <= 1, LABEL
    unit = existing[0] if existing else actors.spawn_actor_from_class(
        cls, position, unreal.Rotator(yaw=-90.))
    assert unit and unit.get_class() == cls, LABEL
    unit.modify()
    unit.set_actor_label(LABEL)
    unit.set_folder_path('SURFACE/City Machines')
    for name, point in zip(('PointA', 'PointB', 'PointC', 'PointD'), ROUTE):
        unit.set_editor_property(name, V(point))
    assert levels.save_map(world, LEVEL), LEVEL
    return backup


def install():
    bp = make_blueprint()
    backup = place(bp)
    (saved / STEM / 'Install.json').write_text(json.dumps(dict(
        blueprint=BLUEPRINT, map=LEVEL, label=LABEL, spawn=SPAWN, backup=str(backup)), indent=2))


if __name__ == '__main__':
    install()
