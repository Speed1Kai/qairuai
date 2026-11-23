"""Build the main menu studio and the training arena."""
import json
from pathlib import Path
import shutil
from datetime import datetime
import unreal

ROOT="/Game/FrontEnd"
MENU=ROOT+"/Lvl_MainMenu"
TRAINING=ROOT+"/Lvl_Training"
MAIN="/Game/Lvl_LabTutorial"
MISSION="/Game/Story/ForeignMemory/BP_ForeignMemory"
PROJECT=Path(unreal.Paths.project_dir()).resolve()
A=unreal.EditorAssetLibrary
B=unreal.BlueprintEditorLibrary
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EDITOR=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
SAVE=unreal.EditorLoadingAndSavingUtils
V=unreal.Vector
R=unreal.Rotator

def load(path):
    asset=A.load_asset(path)
    assert asset,path
    return asset

def world():
    return EDITOR.get_editor_world()

def start_level(path):
    assert not EDITOR.get_game_world()
    assert not SAVE.get_dirty_map_packages()
    if A.does_asset_exist(path):
        assert LEVELS.load_level(path)
        for actor in ACTORS.get_all_level_actors():
            if str(actor.get_actor_label()).startswith("FP_"):
                assert ACTORS.destroy_actor(actor)
    else:
        A.make_directory(ROOT)
        assert LEVELS.new_level(path)

def spawn(kind,name,location,rotation=R()):
    actor=ACTORS.spawn_actor_from_class(kind,V(*location),rotation)
    assert actor,name
    actor.set_actor_label("FP_"+name)
    return actor

def mesh(name, location, asset, material=None, scale=(1,1,1), yaw=0, pitch=0, roll=0, block=False):
    actor=spawn(unreal.StaticMeshActor,name,location,R(yaw=yaw,pitch=pitch,roll=roll))
    shape=actor.static_mesh_component
    shape.set_mobility(unreal.ComponentMobility.MOVABLE)
    shape.set_static_mesh(load(asset))
    if material:
        shape.set_material(0,load(material) if isinstance(material,str) else material)
    actor.set_actor_scale3d(V(*scale))
    shape.set_collision_profile_name("BlockAll" if block else "NoCollision")
    return actor

def light(name, location, color, intensity, radius, size, shadows=False):
    actor=spawn(unreal.PointLight,name,location)
    c=actor.point_light_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_intensity(float(intensity))
    c.set_attenuation_radius(float(radius))
    c.set_light_color(unreal.LinearColor(*color,1.))
    c.set_editor_property("source_radius",float(size))
    c.set_cast_shadows(shadows)
    c.set_editor_property("volumetric_scattering_intensity",0.)
    return actor

def exposure(bias, camera=None):
    if camera:
        c=camera.get_component_by_class(unreal.CameraComponent)
        field="post_process_settings"
        c.set_editor_property("post_process_blend_weight",1.)
    else:
        c=spawn(unreal.PostProcessVolume,"Exposure",(0,0,0))
        c.set_editor_property("unbound",True)
        field="settings"
    settings=c.get_editor_property(field)
    for key,value in (
        ("auto_exposure_method",unreal.AutoExposureMethod.AEM_MANUAL),
        ("auto_exposure_bias",bias),
        ("auto_exposure_apply_physical_camera_exposure",False),
        ("motion_blur_amount",0.),
        ("bloom_intensity",.30),
    ):
        settings.set_editor_property("override_"+key,True)
        settings.set_editor_property(key,value)
    c.set_editor_property(field,settings)

def backdrop(source):
    path=ROOT+"/T_MenuCity"
    if not A.does_asset_exist(path):
        task=unreal.AssetImportTask()
        for key,value in dict(filename=str(source/"T_MenuCity.png"),destination_path=ROOT,
                              destination_name="T_MenuCity",automated=True,save=True).items():
            task.set_editor_property(key,value)
        tools=unreal.AssetToolsHelpers.get_asset_tools()
        tools.import_asset_tasks([task])
    texture=load(path)
    texture.set_editor_property("max_texture_size",2048)
    assert A.save_loaded_asset(texture)
    path=ROOT+"/M_MenuCity"
    library=unreal.MaterialEditingLibrary
    if A.does_asset_exist(path):
        return load(path)
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_MenuCity",ROOT,unreal.Material,unreal.MaterialFactoryNew())
    material.set_editor_property("shading_model",unreal.MaterialShadingModel.MSM_UNLIT)
    sample=library.create_material_expression(material,unreal.MaterialExpressionTextureSample,-430,0)
    sample.set_editor_property("texture",texture)
    gain=library.create_material_expression(material,unreal.MaterialExpressionMultiply,-150,0)
    gain.set_editor_property("const_b",4.)
    assert library.connect_material_expressions(sample,"RGB",gain,"A")
    assert library.connect_material_property(gain,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    library.recompile_material(material)
    assert A.save_loaded_asset(material)
    return material

def install_menu(source):
    backdrop_material=backdrop(source)
    start_level(MENU)
    camera=spawn(unreal.CameraActor,"MenuCamera",(0,680,111),R(yaw=-90))
    camera.tags=[unreal.Name("FrontEndCamera")]
    c=camera.get_component_by_class(unreal.CameraComponent)
    c.set_editor_property("projection_mode",unreal.CameraProjectionMode.ORTHOGRAPHIC)
    c.set_editor_property("ortho_width",445.)
    c.set_editor_property("aspect_ratio",16./9.)
    c.set_editor_property("constrain_aspect_ratio",True)
    exposure(-1.5,camera)

    plane=mesh("CityBackdrop",(0,-390,111),"/Engine/BasicShapes/Plane",backdrop_material,(4.47,2.53,1),yaw=0,roll=90)
    plane.static_mesh_component.set_cast_shadow(False)

    origin=(57,0,0)
    body=spawn(unreal.SkeletalMeshActor,"Sentinel",origin)
    body.tags=[unreal.Name("FrontEndSentinel")]
    sk=body.skeletal_mesh_component
    sk.set_mobility(unreal.ComponentMobility.MOVABLE)
    sk.set_skeletal_mesh_asset(load("/Game/Characters/BlackSentinel/SK_BlackSentinel"))
    sk.set_editor_property("forced_lod_model",1)
    sk.set_collision_profile_name("NoCollision")
    idle=load("/Game/Characters/BlackSentinel/Animations/BS_MM_Idle")
    sk.override_animation_data(idle,True,True,.20,.55)
    sk.set_update_animation_in_editor(True)
    sk.play_animation(idle,True)

    def attach(actor,parent):
        actor.attach_to_actor(parent,"",unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    def add_weapon(name, primary, magazine, position, rotation, scale):
        base="/Game/Combat/ApprovedWeapons/"
        weapon=mesh(name,position,base+primary,scale=(scale,)*3,**rotation)
        attach(weapon,body)
        part=mesh(name+"Magazine",position,base+magazine)
        part.attach_to_actor(weapon,"",unreal.AttachmentRule.SNAP_TO_TARGET,
                             unreal.AttachmentRule.SNAP_TO_TARGET,unreal.AttachmentRule.KEEP_RELATIVE,False)
        part.root_component.set_relative_location(V(17.5,0,1.3),False,True)
        return weapon

    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(idle,.20,unreal.AnimPoseEvaluationOptions())
    hand=unreal.AnimPoseExtensions.get_bone_pose(pose,"CC_Base_R_Hand",unreal.AnimPoseSpaces.WORLD).translation
    add_weapon("MenuCarbine","SM_Hunter_CrimsonCarbine","SM_Hunter_CrimsonPack",
               (origin[0]+hand.x,hand.y+2,hand.z-13),{"pitch":-68.,"yaw":84.,"roll":10.},.74)
    add_weapon("MenuEmitter","SM_Atomic_DischargeEmitter","SM_Atomic_DischargeCell",
               (origin[0]-15,-22,132),{"pitch":52.,"yaw":178.,"roll":-11.},.75)
    body.set_actor_rotation(R(yaw=118),True)

    from Animate_FrontEnd import add_scenery
    add_scenery(mesh,light,body)
    EDITOR.set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
    assert SAVE.save_current_level()

def install_training():
    start_level(TRAINING)
    concrete="/Game/Surface/Materials/M_RuinConcrete"
    dark="/Game/LabTutorial/FirstFloor/M_LabGraphite"
    steel="/Game/LabTutorial/FirstFloor/M_LabSteel"
    marker="/Game/LabTutorial/Industrial/M_AmberIndicator"
    cube="/Engine/BasicShapes/Cube"
    def box(name,pos,size,material,collision=True):
        return mesh(name,pos,cube,material,tuple(axis/100 for axis in size),block=collision)
    box("RangeFloor",(540,0,-36),(1710,960,72),concrete)
    box("RangeCeiling",(540,0,459),(1710,960,48),dark)
    for y,side in ((-466,"Left"),(466,"Right")):
        box("Wall"+side,(540,y,229),(1710,28,460),concrete)
        for index,x in enumerate((-205,130,445,760,1075,1370)):
            box(side+"Pillar"+str(index),(x,y*.97,225),(32,42,450),steel)
        for x in (70,510,950):
            box(side+"Practical"+str(x),(x,y*.925,320),(115,4,8),marker,False)
    for x,side in ((-302,"Entry"),(1375,"Backstop")):
        box(side+"Wall",(x,0,230),(32,930,460),concrete)
    for index,y in enumerate((-293,0,293)):
        box("BackstopPanel"+str(index),(1340,y,193),(21,282,265),dark)
        box("LaneStripe"+str(index),(540,y,1),(1340,5,2),marker,False)
    for index,x in enumerate((40,450,850,1210)):
        box("Lamp"+str(index),(x,0,415),(245,14,9),steel,False)
        light("RangeLight"+str(index),(x,0,374),(.63,.79,1.),1780,680,50)
    light("RangeBounce",(175,130,185),(1.,.72,.46),320,620,55)
    spawn(unreal.PlayerStart,"RangeStart",(0,0,108),R())
    exposure(-.8)
    EDITOR.set_level_viewport_camera_info(V(90,390,259),R(pitch=-12,yaw=-47))
    assert SAVE.save_current_level()

def install(source):
    backup=PROJECT/"Saved/Backups/FrontEnd"/datetime.now().strftime("%Y%m%d_%H%M%S")
    for path in (MENU,TRAINING,ROOT+"/T_MenuCity",ROOT+"/M_MenuCity"):
        suffix=".umap" if path in (MENU,TRAINING) else ".uasset"
        rel=Path("Content")/(path.removeprefix("/Game/")+suffix)
        original=PROJECT/rel
        if original.is_file():
            destination=backup/rel
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(original,destination)
    install_menu(source)
    install_training()
    (source/"Maps.json").write_text(json.dumps({"menu":MENU,"training":TRAINING,"backup":str(backup)},indent=2))


