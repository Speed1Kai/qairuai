"""Install the repaired city shells without changing the gameplay map layout."""
import hashlib
import json

import unreal

from Build_CityReclaim import build_materials
from Build_RuinedUrbanCampus import LEVEL, V, actors, compile_bp, components, content, levels, save, saved, tools
from Industrial_Common import A, B, add
from Place_CityExpansion import DISTRICTS, ROOT as DISTRICT_ROOT

SOURCE = content.parent/'SourceAssets/CityExpansion'
DOWNTOWN = '/Game/Environment/DowntownFirstBlock'
PLAN = json.loads((SOURCE.parent/'DowntownFirstBlock/selection.json').read_text(encoding='utf-8'))
RUINS = ('SM_Ruin_A','SM_Ruin_B','SM_Ruin_C','SM_Ruin_D')
DISTRICT_MODELS = tuple('SM_District_'+kind for kind in sorted({row[1] for row in DISTRICTS}))
DOWNTOWN_MODELS = tuple('SM_Repaired_'+row['source'].split('/')[-1] for row in PLAN['buildings'])


def shell_materials():
    materials = build_materials()
    materials.update({key:A.load_asset(DISTRICT_ROOT+'/M_District_'+key) for key in ('Brick','Panel','Stone')})
    materials['Mortar'] = A.load_asset('/Game/Surface/Materials/M_RuinConcrete')
    materials['Oxide'] = A.load_asset('/Game/Surface/Materials/M_Oxide')
    return materials


def apply_section_materials(mesh, materials):
    slots = {str(slot.get_editor_property('imported_material_slot_name')):i
             for i,slot in enumerate(mesh.static_materials)}
    assert {'Mortar','Scorch','Shards','Interior'}.issubset(slots),(mesh.get_name(),slots)
    # Blender writes the new FBX sections in material name order. Unreal retains
    # the old section overrides on reimport, including the original window slots.
    keys = sorted(slots.keys() & materials.keys())
    assert len(keys)==mesh.get_num_sections(0),(mesh.get_name(),keys,slots)
    sm = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for section,key in enumerate(keys):
        slot = slots[key]
        mesh.set_material(slot,materials[key])
        if sm.get_lod_material_slot(mesh,0,section)!=slot:
            sm.set_lod_material_slot(mesh,slot,0,section)


def import_shell(name, root, materials):
    options = unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                    mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(k,v)
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    task = unreal.AssetImportTask()
    for k,v in dict(filename=str(SOURCE/(name+'.fbx')),destination_path=root,destination_name=name,
                    automated=True,replace_existing=True,save=False,options=options).items():
        task.set_editor_property(k,v)
    tools.import_asset_tasks([task])
    result = A.load_asset(root+'/'+name)
    assert result and task.get_objects(),name
    apply_section_materials(result,materials)
    body = result.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    body.set_editor_property('double_sided_geometry',True)
    save(result)
    return result


def fix_downtown(meshes):
    # Only the active city uses this block. Leave the template block for the alternate level.
    old_path = DOWNTOWN+'/BP_FirstCityBlock'
    path = DOWNTOWN+'/BP_FirstCityBlock_Repaired'
    bp = A.load_asset(path) if A.does_asset_exist(path) else A.duplicate_asset(old_path,path)
    assert bp
    modules = {c['mesh'].split('.')[0] for b in PLAN['buildings'] for a in b['actors'] for c in a['components']}
    modules.add('/Game/CityDowntown/Geometry/Props/SM_ac2')
    kept, removed = 0, 0
    for _,c,name in components(bp):
        if not isinstance(c,unreal.InstancedStaticMeshComponent):
            continue
        mesh = c.get_editor_property('static_mesh')
        if not mesh:
            continue
        package = mesh.get_path_name().split('.')[0]
        if package in modules or name in ('Batch_073','Batch_074') or name.startswith('Repaired_'):
            removed += c.get_instance_count()
            c.clear_instances()
        else:
            kept += c.get_instance_count()
    assert kept>70,kept
    for b,name in zip(PLAN['buildings'],DOWNTOWN_MODELS):
        c = add(bp,unreal.HierarchicalInstancedStaticMeshComponent,name.removeprefix('SM_'),'Root')
        c.set_static_mesh(meshes[name])
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_collision_profile_name('BlockAll')
        c.set_cull_distances(0,0)
        c.set_editor_property('can_ever_affect_navigation',True)
        c.add_instance(unreal.Transform(location=V(b['target_center'])),False)
    compile_bp(bp)
    save(bp)
    return bp, kept, removed


def main():
    tutorial = content/'Lvl_LabTutorial.umap'
    initial = hashlib.sha256(tutorial.read_bytes()).digest()
    world = levels.load_map(LEVEL)
    assert world
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    materials = shell_materials()
    meshes = {}
    for root,names in (('/Game/Surface/Meshes',RUINS),(DISTRICT_ROOT,DISTRICT_MODELS),(DOWNTOWN,DOWNTOWN_MODELS)):
        for name in names:
            meshes[name] = import_shell(name,root,materials)
    bp,kept,removed = fix_downtown(meshes)
    scene = {a.get_actor_label():a for a in actors.get_all_level_actors()}
    label = 'CITY_FirstDowntownBlock'
    old = scene[label]
    folder, location, rotation = old.get_folder_path(),old.get_actor_location(),old.get_actor_rotation()
    tags = list(old.tags)
    replacement = actors.spawn_actor_from_class(B.generated_class(bp),location,rotation)
    assert replacement
    assert actors.destroy_actor(old)
    replacement.set_actor_label(label)
    replacement.set_folder_path(folder)
    replacement.set_editor_property('tags',tags)
    for name in DOWNTOWN_MODELS:
        infill = scene.get('CITY_Shell_'+name.removeprefix('SM_Repaired_'))
        if infill:
            assert actors.destroy_actor(infill)
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    scene = {a.get_actor_label():a for a in actors.get_all_level_actors()}
    assert not any(name.startswith('CITY_Shell_Building') for name in scene)
    checked = {}
    for name in (label,'DISTRICT_Expansion','SURF_Environment'):
        groups = scene[name].get_components_by_class(unreal.InstancedStaticMeshComponent)
        chosen = [(c,c.get_editor_property('static_mesh')) for c in groups]
        for c,mesh in chosen:
            if mesh not in meshes.values():
                continue
            assert str(c.get_collision_profile_name())=='BlockAll',(name,c.get_name())
            checked[mesh.get_name()] = c.get_instance_count()
    assert set(checked)==set(meshes) and min(checked.values())>0,checked
    assert hashlib.sha256(tutorial.read_bytes()).digest()==initial
    (saved/'legacy_city_repair.json').write_text(json.dumps({
        'buildings':checked,'kept_street_objects':kept,'retired_modules':removed,
        'models':len(meshes),'map':LEVEL},indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
