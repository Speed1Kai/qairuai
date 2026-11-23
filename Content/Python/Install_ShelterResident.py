
"""Import the supplied shelter resident and place him beside the bunks."""
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
import unreal

from Build_RiverForest import constant, output, persist
from Build_RuinedUrbanCampus import local
from CityCombat_Common import A, B, add, compile_bp, save
from Install_StoryMemory import CITY, load
from Shelter07_Waterworks import position
from SurfacePolish_Materials import sample

PROJECT = Path(unreal.Paths.project_dir()).resolve()
ROOT = '/Game/Characters/ShelterResident'
LABEL = 'CITY_S07_Resident'
STAND = (0.56, 3.57, 0.)
ASSETS = unreal.AssetToolsHelpers.get_asset_tools()
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
SAVING = unreal.EditorLoadingAndSavingUtils

def import_file(path, destination, opts=None):
    asset_path = destination+'/'+path.stem
    if A.does_asset_exist(asset_path):
        return load(asset_path)
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=destination, destination_name=path.stem,
                           automated=True, replace_existing=False, save=False).items():
        task.set_editor_property(key,value)
    if opts:
        task.set_editor_property('options',opts)
    ASSETS.import_asset_tasks([task])
    asset=load(asset_path)
    assert asset, asset_path
    return asset

def setup_texture(path, role):
    t=import_file(path,ROOT+'/Textures')
    t.set_editor_property('srgb',role=='Color')
    if role=='Normal':
        t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif role in ('ORM','Mask'):
        t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    save(t)
    return t

def material(source, name, roles):
    path=ROOT+'/Materials/M_S07_'+name
    if A.does_asset_exist(path):
        return load(path)
    mat=ASSETS.create_asset('M_S07_'+name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('used_with_skeletal_mesh',True)
    srgb=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
    normal=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
    masks=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
    for role in roles:
        texture=setup_texture(source/'Textures'/f'T_S07_{name}_{role}.png',role)
        node=sample(mat,texture,{'Color':srgb,'Normal':normal,'ORM':masks,'Mask':masks}[role])
        if role=='Color':
            output(node,'BASE_COLOR','RGB')
        elif role=='Normal':
            output(node,'NORMAL','RGB')
        elif role=='ORM':
            output(node,'AMBIENT_OCCLUSION','R')
            output(node,'ROUGHNESS','G')
            output(node,'METALLIC','B')
        elif role=='Mask':
            mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
            mat.set_editor_property('two_sided',True)
            mat.set_editor_property('opacity_mask_clip_value',.34 if name=='Hair' else .47)
            output(node,'OPACITY_MASK','R')
    if 'ORM' not in roles:
        constant(mat,'ROUGHNESS',.31 if name=='Eye' else .58)
    return persist(mat,False)

def import_character(source):
    world=EDITOR.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    options=unreal.FbxImportUI()
    for key,value in dict(import_mesh=True,import_as_skeletal=True,import_animations=False,import_materials=False,
                          import_textures=False,create_physics_asset=False,automated_import_should_detect_type=False,
                          mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH).items():
        options.set_editor_property(key,value)
    options.skeletal_mesh_import_data.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    mesh=import_file(source/'SK_S07_Resident.fbx',ROOT,options)
    assert mesh and mesh.skeleton
    save(mesh.skeleton)
    material_info=json.loads((source/'Materials.json').read_text())
    slots=list(mesh.materials)
    names=[]
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name')).removesuffix('_Mat')
        assert name in material_info,(name,[str(s.material_slot_name) for s in slots])
        slot.set_editor_property('material_interface',material(source,name,material_info[name]))
        names.append(name)
    assert set(names)==set(material_info),(names,list(material_info))
    mesh.set_editor_property('materials',slots)
    save(mesh)
    opts=unreal.FbxImportUI()
    for key,value in dict(import_mesh=False,import_as_skeletal=True,import_animations=True,import_materials=False,
                          import_textures=False,skeleton=mesh.skeleton,automated_import_should_detect_type=False,
                          mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION).items():
        opts.set_editor_property(key,value)
    opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',True)
    idle=import_file(source/'AN_S07_Resident_Idle.fbx',ROOT+'/Animations',opts)
    assert idle.get_editor_property('skeleton')==mesh.skeleton and 7.98<=idle.sequence_length<=8.06
    save(idle)
    return mesh,idle,names

def build_npc(mesh, idle):
    name='BP_ShelterResident'
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        bp=load(path)
    else:
        f=unreal.BlueprintFactory()
        f.set_editor_property('parent_class',unreal.Actor)
        bp=ASSETS.create_asset(name,ROOT,unreal.Blueprint,f)
    add(bp,unreal.SceneComponent,'Root')
    skin=add(bp,unreal.SkeletalMeshComponent,'Body','Root')
    skin.set_skeletal_mesh_asset(mesh)
    skin.set_collision_profile_name('NoCollision')
    skin.override_animation_data(idle,True,True,0.,1.)
    capsule=add(bp,unreal.CapsuleComponent,'PersonalSpace','Root')
    capsule.set_capsule_size(27.,89.,False)
    capsule.set_editor_property('relative_location',unreal.Vector(0,0,91))
    capsule.set_collision_profile_name('Pawn')
    capsule.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    capsule.set_editor_property('generate_overlap_events',False)
    capsule.set_editor_property('can_ever_affect_navigation',False)
    compile_bp(bp)
    save(bp)
    return bp

def place(bp):
    point=local(*position(*STAND))
    resident=next((a for a in ACTORS.get_all_level_actors() if a.get_actor_label()==LABEL),None)
    if not resident:
        resident=ACTORS.spawn_actor_from_class(B.generated_class(bp),point)
        resident.set_actor_label(LABEL)
        resident.set_folder_path('CITY/Waterworks/Residents')
    else:
        resident.set_actor_location(point,False,True)
        resident.set_actor_rotation(unreal.Rotator(),True)
    skin=resident.get_editor_property('Body')
    foot=skin.get_socket_location('ball_l')-skin.get_socket_location('foot_l')
    assert foot.length()>5
    yaw=180-math.degrees(math.atan2(foot.y,foot.x))
    resident.set_actor_rotation(unreal.Rotator(yaw=yaw),True)
    return resident,yaw

def install(source, output_dir):
    assert not EDITOR.get_game_world()
    world=EDITOR.get_editor_world()
    if world.get_path_name().split('.')[0]!=CITY:
        assert not SAVING.get_dirty_map_packages()
        assert LEVELS.load_level(CITY)
        world=EDITOR.get_editor_world()
    assert not SAVING.get_dirty_map_packages()
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=PROJECT/'Saved/Backups/ShelterResident'/stamp
    content=PROJECT/'Content'
    for rel in (Path('Surface/Lvl_CampusConnected.umap'),Path('Characters/ShelterResident/BP_ShelterResident.uasset'),
                 Path('Characters/ShelterResident/SK_S07_Resident.uasset'),Path('Characters/ShelterResident/Animations/AN_S07_Resident_Idle.uasset')):
        if (content/rel).is_file():
            dest=backup/'Content'/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(content/rel,dest)
    mesh,idle,slots=import_character(source)
    bp=build_npc(mesh,idle)
    resident,yaw=place(bp)
    assert SAVING.save_map(world,CITY)
    output_dir.mkdir(parents=True,exist_ok=True)
    world_point=position(*STAND)
    (output_dir/'Installed.json').write_text(json.dumps({
        'passed':True, 'map':CITY, 'label':LABEL, 'blueprint':bp.get_path_name(), 'world_cm':world_point,
        'mesh':mesh.get_path_name(),'slots':slots,'idle':idle.get_path_name(),'idle_seconds':idle.sequence_length,
        'backup':str(backup),'yaw':yaw,
    },ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    install(PROJECT/'SourceAssets/Shelter07/Resident',PROJECT/'Saved/Shelter07/Resident')
