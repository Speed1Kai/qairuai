"""Dress the playable city with grounded battle debris and attached vegetation."""
from collections import Counter
from datetime import datetime
import json
import math
import random
import shutil

import unreal

from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, OFFSET, Site, V, actors, compile_bp, content, levels, local, save, saved
from CityCombat_Common import asset as blueprint
from SurfacePolish_Materials import import_file

ROOT = '/Game/Environment/CityAftermath'
SOURCE = content.parent/'SourceAssets'/'CityAftermath'
REPORT = saved/'CityAftermath'
BP = ROOT+'/BP_CityAftermath'
LABEL = 'CITY_Aftermath'
OLD_IVY = ('IvyCurtain','IvyFall','Lichen')
PANEL_LABELS = {f'CITY_Night_{i:02d}_{part}' for i in (1,2,4,5) for part in ('Housing','Neon','FogLight')}
MAJOR = ('RippedSlabA','RippedSlabB','RubblePile','TwistedGuardrail')
MESHES = (*MAJOR,'SpentCases','Scorch','RootedIvy','ClimbingIvy')
CORRIDORS = (
    ('FirstBlock', 'Y', 5850, 23800, 34900, 720, 720),
    ('Civic', 'Y', 5850, 35600, 57200, 820, 995),
    ('North', 'Y', 5850, 57800, 100700, 890, 1470),
    ('East', 'Y', 15500, 59600, 96300, 750, 1850),
    ('West', 'Y', -12600, 60100, 96800, 750, 1860),
    ('OuterEast', 'Y', 33400, 61000, 95900, 680, 2190),
    ('CrossSouth', 'X', 58950, -15500, 29200, 710, 1820),
    ('CrossNorth', 'X', 78300, -14900, 30200, 740, 1890),
)
TRACE = unreal.TraceTypeQuery.ECC_VISIBILITY
DEBUG = unreal.DrawDebugTrace.NONE
OXIDE = '/Game/Environment/Vehicles/M_Wreck_Oxide'
RECLAIM = '/Game/Environment/CityReclaim/'
PROPS = '/Game/CityDowntown/Geometry/Props/'


def load(path):
    asset = A.load_asset(path)
    assert asset, path
    return asset


def assets(world):
    A.make_directory(ROOT)
    unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
    opts = unreal.FbxImportUI()
    opts.set_editor_property('automated_import_should_detect_type', False)
    opts.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    opts.set_editor_property('import_materials', False)
    opts.set_editor_property('import_textures', False)
    opts.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
    mat_paths = {
        'Concrete': '/Game/Environment/SurfacePolish/M_Scan_Concrete',
        'Rubble': '/Game/Surface/RuinedCampus/Siege/M_Siege_BlastConcrete',
        'Char': '/Game/Surface/RuinedCampus/Siege/M_Siege_BurnedGround',
        'Tar': '/Game/Surface/RuinedCampus/Siege/M_Siege_FracturedAsphalt',
        'Steel': '/Game/Environment/Vehicles/M_Wreck_Steel',
        'Oxide': OXIDE, 'Brass': '/Game/Environment/Vehicles/M_Wreck_Trim',
        'Paint': '/Game/Surface/Materials/M_LanePaint',
        **{name: RECLAIM+'M_Reclaim_'+name for name in ('Stem','Leaf','LeafPale')},
    }
    materials = {k:load(v) for k,v in mat_paths.items()}
    result = {}
    for key in MESHES:
        mesh = import_file(SOURCE/('SM_War_'+key+'.fbx'),ROOT,opts)
        for i,slot in enumerate(mesh.static_materials):
            mesh.set_material(i,materials[str(slot.material_slot_name)])
        if key in MAJOR:
            mesh.get_editor_property('body_setup').set_editor_property(
                'collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(mesh)
        result[key] = mesh
    for key, name in (('Bag','SM_trashBag02'),('Can','SM_sodaCan'),('Bottle','SM_beerBottle')):
        result[key] = load(PROPS+name)
    return result


def dirty_bag_material(mesh):
    path = ROOT+'/MI_War_WeatheredBag'
    original = mesh.get_material(0)
    instance = A.load_asset(path) if A.does_asset_exist(path) else A.duplicate_asset(
        original.get_path_name(),path)
    materials = unreal.MaterialEditingLibrary
    materials.set_material_instance_vector_parameter_value(
        instance,'Tint',unreal.LinearColor(.39,.24,.092,1.))
    materials.update_material_instance(instance)
    save(instance)
    return instance


def ray(world,start,end,ignored=()):
    hit = unreal.SystemLibrary.line_trace_single(world,start,end,TRACE,True,list(ignored),DEBUG,False)
    return hit.to_tuple() if hit else None


def facade(world,point,normal):
    hit = ray(world,point+normal*195.,point-normal*190.)
    if not hit:
        return None
    surface, facing, actor, component = hit[5],hit[7],hit[9],hit[10]
    if not actor or not component or abs(facing.z) > .26 or unreal.MathLibrary.dot_vector_vector(facing,normal) < .72:
        return None
    label = actor.get_actor_label()
    if label == 'RECLAIM_City':
        if not component.get_name().startswith('Skyline_'):
            return None
    elif label in ('CITY_FirstDowntownBlock','DISTRICT_Expansion'):
        if not component.get_name().startswith(('Repaired_','Building_')):
            return None
    elif not label.startswith(('CITY_Detail_West_Building','CITY_Residential_','CITY_Shell_')):
        return None
    material, _ = component.get_material_from_collision_face_index(hit[15])
    if not material or any(word in material.get_name().lower() for word in ('glass','shards','interior','neon')):
        return None
    return surface,facing,actor,component


def transforms(component):
    return [component.get_instance_transform(i,True) for i in range(component.get_instance_count())]


def vector_key(point, step):
    return tuple(round(v/step) for v in (point.x,point.y,point.z))


def put(site,key,mesh,point,scale,*,yaw=0.,collide=False):
    p = point+V(OFFSET)
    site.mesh(key,mesh,p.x,p.y,p.z,scale,collide=collide,yaw=yaw)


def horizontal_unit(vector):
    length = math.hypot(vector.x,vector.y)
    return V((vector.x/length,vector.y/length,0.))


def grow_ivy(world,site,models,candidates,rng,ignored):
    points = set()
    anchors = []
    for idx,t in enumerate(candidates):
        if not t or idx%3 == 1:
            continue
        n = t.transform_location(V((0.,1.,0.))) - t.translation
        normal = horizontal_unit(n)
        anchor = t.translation
        climb = idx%9 == 0 and anchor.z < 780.
        if climb:
            anchor.z = 63.
        key = 'ClimbingIvy' if climb else 'RootedIvy'
        direction = 1. if climb else -1.
        hit = facade(world,anchor,normal)
        if not hit:
            continue
        point,facing,actor,component = hit
        if climb:
            floor = ground(world,point.x+facing.x*27.,point.y+facing.y*27.,ignored)
            if not floor:
                continue
            hit = facade(world,V((point.x,point.y,floor.z+9.)),normal)
            if not hit or hit[2:] != (actor,component):
                continue
            point,facing,_,_ = hit
        if point.z < (-48. if climb else 240.) or point.z > 1400.:
            continue
        cell = vector_key(point,154.)
        if cell in points:
            continue
        facing = horizontal_unit(facing)
        tangent = V((-facing.y,facing.x,0.))
        scale = rng.uniform(.62,1.13)

        def contact(offset, height, tolerance=23.):
            sample = point+tangent*offset+V((0,0,height))
            check = facade(world,sample,facing)
            return (check and check[2:] == (actor,component)
                    and abs(unreal.MathLibrary.dot_vector_vector(check[0]-sample,facing)) <= tolerance)

        if not all(contact(u*scale,0.) for u in (-29.,29.)):
            continue
        if not any(contact(u*scale,direction*64.*scale) for u in (-28.,0.,28.)):
            continue
        if not any(contact(u*scale,direction*125.*scale) for u in (-21.,0.,21.)):
            scale *= .73
            if not contact(0.,direction*105.*scale):
                continue
        pos = point+facing*3.5
        yaw = math.degrees(math.atan2(facing.y,facing.x))-90.
        put(site,key,models[key],pos,(scale,scale,scale),yaw=yaw)
        points.add(cell)
        anchors.append((key,actor.get_actor_label(),[pos.x,pos.y,pos.z]))
    return anchors


def ground(world,x,y,ignored=()):
    hit = ray(world,V((x,y,370)),V((x,y,-195)),ignored)
    if not hit or hit[7].z < .78 or not (-62. < hit[5].z < 105.):
        return None
    actor = hit[9]
    if not actor:
        return None
    label = actor.get_actor_label()
    if label not in ('RECLAIM_City','SURF_Environment','CITY_FirstDowntownBlock','DISTRICT_Expansion'):
        if not label.startswith(('CITY_Detail_','RIVER_')):
            return None
    return hit[5]


def place_grounded(world,site,models,key,x,y,scale,yaw,*,large=False,ignored=()):
    center = ground(world,x,y,ignored)
    if center is None:
        return False
    if large:
        around = [ground(world,x+dx*scale,y+dy*scale,ignored) for dx,dy in ((51,0),(-51,0),(0,51),(0,-51))]
        if any(p is None or abs(p.z-center.z)>31. for p in around):
            return False
        if ray(world,center+V((0,0,55)),center+V((0,0,220)),ignored):
            return False
    mesh = models[key]
    z = center.z - mesh.get_bounding_box().min.z*scale + (1.5 if key == 'Scorch' else -1.5 if large else .7)
    put(site,key,mesh,V((x,y,z)),(scale,)*3,yaw=yaw,collide=large)
    return True


def dress_streets(world,site,models,old_blocks,rng,ignored):
    groups = Counter()
    for section,axis,line,first,last,half,spacing in CORRIDORS:
        for marker, distance in enumerate(range(first,last,spacing)):
            for side in (-1,1):
                if marker%3 == 1 and side == -1:
                    continue
                shoulder = side*(half+rng.uniform(90.,375.))
                along = distance+rng.uniform(-180.,180.)
                x,y = (line+shoulder,along) if axis=='Y' else (along,line+shoulder)
                x,y = x-OFFSET[0],y-OFFSET[1]
                key = rng.choice(MAJOR)
                placed = place_grounded(world,site,models,key,x,y,rng.uniform(.58,1.26),rng.randrange(360),
                                         large=True,ignored=ignored)
                if placed:
                    groups[section] += 1
                for key in ('Scorch',rng.choice(('Bag','Bottle','Can')),'SpentCases',rng.choice(('Can','Bottle'))):
                    place_grounded(world,site,models,key,x+rng.uniform(-143.,143.),y+rng.uniform(-255.,255.),
                                   rng.uniform(.71,1.27),rng.randrange(360),ignored=ignored)
    for t in old_blocks:
        if t:
            p=t.translation
            if place_grounded(world,site,models,'TwistedGuardrail',p.x,p.y,.92,rng.randrange(360),
                              large=True,ignored=ignored):
                groups['Old barriers'] += 1
    return groups


def prepare(world):
    assert world.get_path_name().split('.')[0] == LEVEL
    scene = {a.get_actor_label():a for a in actors.get_all_level_actors()}
    reclaim = scene['RECLAIM_City']
    components = {c.get_name():c for c in reclaim.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    old_ivy = [components[name] for name in OLD_IVY]
    old_blocks = components['RustedTrafficBlock']
    ignored = (scene[LABEL],) if LABEL in scene else ()
    models = assets(world)

    backup = saved/'Backups'/'CityAftermath'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    bp = blueprint(BP)
    site = Site(bp)
    anchors = grow_ivy(world,site,models,transforms(old_ivy[0])+transforms(old_ivy[1]),
                       random.Random(59217),ignored)
    groups = dress_streets(world,site,models,transforms(old_blocks),random.Random(1539),ignored)
    counts = {key:c.get_instance_count() for key,c in site.batches.items()}
    assert len(anchors)>=24 and sum(groups.values())>=50,(len(anchors),groups)
    if 'Bag' in site.batches:
        site.batches['Bag'].set_material(0,dirty_bag_material(models['Bag']))
    for key,c in site.batches.items():
        c.set_editor_property('can_ever_affect_navigation', False)
        c.set_cull_distances(0,33000 if key in MAJOR else 20500 if 'Ivy' in key else 12500)
        if key not in MAJOR:
            c.set_editor_property('cast_shadow',False)
    compile_bp(bp)
    save(bp)

    reclaim.modify()
    for component in (*old_ivy,old_blocks):
        component.modify()
        component.set_visibility(False)
        component.set_hidden_in_game(True)
    removed = []
    for label in sorted(PANEL_LABELS):
        actor = scene.get(label)
        if actor:
            assert actors.destroy_actor(actor),label
            removed.append(label)
    if LABEL in scene:
        assert actors.destroy_actor(scene[LABEL])
    actor = actors.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)))
    assert actor
    actor.set_actor_label(LABEL)
    actor.set_folder_path('SURFACE/City Aftermath')
    report = dict(map=LEVEL, backup=str(backup), removed=removed, ivy=len(anchors),
                  clusters=groups, counts=counts, anchors=anchors)
    return report


def commit(world,report):
    assert levels.save_map(world,LEVEL),LEVEL
    (REPORT/'Install.json').write_text(json.dumps(report,indent=2))
