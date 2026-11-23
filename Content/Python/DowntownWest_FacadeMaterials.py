"""Local opaque facade variants for panels visible from either side of a street."""
import hashlib
import unreal
ROOT='/Game/Environment/CityRealism/Materials'
A=unreal.EditorAssetLibrary
M=unreal.MaterialEditingLibrary

def facade_panel(mesh_path):
    path=str(mesh_path).lower()
    return path.startswith('/game/downtown_west/assets/building_') and any(s in path for s in ('mod_wall','mod_lvl','mod_door','_brick_','_pillar'))

def facade_material(material):
    if not material or material.get_path_name().startswith(ROOT+'/MI_FacadeTwoSided_'):return material
    base=material.get_base_material()
    if base.get_editor_property('blend_mode') not in (unreal.BlendMode.BLEND_OPAQUE,unreal.BlendMode.BLEND_MASKED):return material
    key=hashlib.sha1(material.get_path_name().encode('utf8')).hexdigest()[:12]
    path=ROOT+'/MI_FacadeTwoSided_'+key
    if A.does_asset_exist(path):return A.load_asset(path)
    A.make_directory(ROOT)
    mi=unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[-1],ROOT,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    M.set_material_instance_parent(mi,material)
    overrides=mi.get_editor_property('base_property_overrides')
    overrides.set_editor_property('override_two_sided',True)
    overrides.set_editor_property('two_sided',True)
    mi.set_editor_property('base_property_overrides',overrides)
    M.update_material_instance(mi)
    assert A.save_loaded_asset(mi,only_if_is_dirty=False)
    return mi

def facade_materials(mesh_path,paths):
    if not facade_panel(mesh_path):return paths
    return [facade_material(A.load_asset(p)).get_path_name() if p else p for p in paths]
