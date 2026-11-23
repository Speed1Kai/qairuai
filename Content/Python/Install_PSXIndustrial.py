"""Place Bowley3D's PSX Industrial Buildings on one city block."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal

from Build_RiverForest import persist
from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, MAT, OFFSET, Site, actors, compile_bp, content, levels, local, save, saved, tools
from CityCombat_Common import asset
from Install_CityAftermath import ray
from SurfacePolish_Materials import import_file


ROOT = '/Game/Environment/PSXIndustrial'
SOURCE = content.parent / 'SourceAssets/PSXIndustrial'
WORK = saved / 'PSXIndustrial'
LABEL = 'CITY_PSX_IndustrialBlock'
# World locations and orientation. Keep the two rows separated by a service lane.
LAYOUT = (('A',8620,60570,0), ('B',10355,60680,180), ('D',12510,60680,0),
          ('C',8640,62205,180), ('E',11515,62225,90))
ROUTE = ((9435,59735),(9435,62580))


def import_pack(world):
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    texture = import_file(SOURCE/'T_Buildings_Textures.png',ROOT)
    texture.set_editor_property('max_texture_size',1024)
    texture.set_editor_property('never_stream',False)
    save(texture)
    path = ROOT+'/M_PSX_Industrial'
    if A.does_asset_exist(path):
        material = A.load_asset(path)
    else:
        material = tools.create_asset('M_PSX_Industrial',ROOT,unreal.Material,unreal.MaterialFactoryNew())
        edit = unreal.MaterialEditingLibrary
        sample = edit.create_material_expression(material,unreal.MaterialExpressionTextureSample,-300,0)
        sample.set_editor_property('texture',texture)
        assert edit.connect_material_property(sample,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        rough = edit.create_material_expression(material,unreal.MaterialExpressionConstant,-280,150)
        rough.set_editor_property('r',.89)
        assert edit.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
        persist(material)
    ui = unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,import_materials=False,
                          import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        ui.set_editor_property(key,value)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    ui.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
    meshes = {}
    for letter,_,_,_ in LAYOUT:
        mesh = import_file(SOURCE/f'SM_PSX_Building_{letter}.fbx',ROOT,ui)
        bounds = mesh.get_bounding_box()
        span = bounds.max-bounds.min
        assert min(span.x,span.y)>900 and 450<span.z<3100 and len(mesh.static_materials)==1,(letter,span)
        mesh.set_material(0,material)
        body = mesh.get_editor_property('body_setup')
        body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        body.set_editor_property('double_sided_geometry',True)
        save(mesh)
        meshes[letter] = mesh
    return meshes


def footprint(mesh, x, y, yaw):
    b = mesh.get_bounding_box()
    size = (b.max.x-b.min.x,b.max.y-b.min.y,b.max.z-b.min.z)
    width,depth = (size[1],size[0]) if yaw%180 else size[:2]
    return size,(x-width/2,y-depth/2,x+width/2,y+depth/2)


def clear_plant_overlap(scene, footprints):
    removed = 0
    for label in ('RECLAIM_City','CITY_StreetLife','CITY_Aftermath'):
        actor = scene.get(label)
        if not actor:
            continue
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.get_name().startswith(('StreetFir','Fir','SmallFir','LowShrub','Shrub','Grass','Ivy')):
                continue
            for index in reversed(range(c.get_instance_count())):
                pos = c.get_instance_transform(index,True).translation
                x,y = pos.x+OFFSET[0],pos.y+OFFSET[1]
                if any(left-95<x<right+95 and bottom-95<y<top+95 for left,bottom,right,top in footprints):
                    c.modify()
                    assert c.remove_instance(index)
                    removed += 1
    return removed


def verify(world, actor):
    components = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    groups = {c.get_name(): c for c in components}
    assert all(groups[f'Building_{letter}'].get_instance_count()==1 for letter,_,_,_ in LAYOUT)
    for letter,x,y,_ in LAYOUT:
        hit = ray(world,local(x,y,GROUND+3800),local(x,y,GROUND-45))
        assert hit and hit[9]==actor and hit[10]==groups[f'Building_{letter}'],(letter,hit[10].get_name() if hit else None)
    start,end = ROUTE
    for height in (70,125,180):
        hit = ray(world,local(*start,GROUND+height),local(*end,GROUND+height))
        assert not hit,(height,hit[9].get_actor_label() if hit else '')


def install():
    world = levels.load_map(LEVEL)
    assert world
    scene = {actor.get_actor_label():actor for actor in actors.get_all_level_actors()}
    meshes = import_pack(world)
    backup = saved/'Backups'/'PSXIndustrial'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True)
    shutil.copy2(content/'Surface/Lvl_CampusConnected.umap',backup)
    bp = asset(ROOT+'/BP_PSX_IndustrialBlock')
    site = Site(bp)
    footprints = []
    MAT['psx_yard'] = A.load_asset('/Game/Environment/SurfacePolish/M_Scan_Asphalt')
    for letter,x,y,yaw in LAYOUT:
        mesh = meshes[letter]
        size,rect = footprint(mesh,x,y,yaw)
        footprints.append(rect)
        site.box('concrete',x,y,GROUND-6,rect[2]-rect[0]+30,rect[3]-rect[1]+30,22,collide=True)
        site.fitted(f'Building_{letter}',mesh,x,y,GROUND+5,size,yaw=yaw,collide=True)
    site.box('psx_yard',9435,61160,GROUND-7,235,2850,15,collide=True)
    for c in site.batches.values():
        c.set_editor_property('can_ever_affect_navigation',False)
        c.set_cull_distances(0,65000)
    compile_bp(bp)
    save(bp)
    removed = clear_plant_overlap(scene,footprints)
    if LABEL in scene:
        assert actors.destroy_actor(scene[LABEL])
    instance = actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    assert instance
    instance.set_actor_label(LABEL)
    instance.set_folder_path('SURFACE/PSX Industrial')
    verify(world,instance)
    assert levels.save_map(world,LEVEL)
    world = levels.load_map(LEVEL)
    verify(world,next(a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL))
    (WORK/'Installed.json').write_text(json.dumps({'buildings':len(LAYOUT),'route':ROUTE,
        'removed_intersecting_plants':removed,'backup':str(backup)},indent=2),encoding='utf-8')


if __name__ == '__main__':
    install()
