"""Dedicated repeatable physics fixture. Startup maps/configuration are untouched."""
import unreal,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A
LEVEL='/Game/Developer/Tests/Lvl_AirJetRegression'
if not A.does_asset_exist(LEVEL):
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level(LEVEL)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
    def box(name,p,size,mat):
        a=sub.spawn_actor_from_class(unreal.StaticMeshActor,V(*p));a.set_actor_label(name)
        c=a.static_mesh_component;c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,A.load_asset(mat));c.set_collision_profile_name('BlockAll');c.set_mobility(unreal.ComponentMobility.STATIC);a.set_actor_scale3d(V(*(s/100 for s in size)));return a
    box('TEST_Floor',(1000,0,-40),(16000,10000,80),'/Game/Surface/Materials/M_RuinConcrete')
    box('TEST_SevenMetreFence',(2400,0,350),(100,4000,700),'/Game/LabTutorial/FirstFloor/M_LabSteel')
    box('TEST_LowCeiling',(-3500,0,400),(2400,1600,40),'/Game/LabTutorial/FirstFloor/M_LabGraphite')
    a=sub.spawn_actor_from_class(unreal.PlayerStart,V(0,0,115),unreal.Rotator(pitch=0,yaw=0,roll=0));a.set_actor_label('TEST_PlayerStart')
    sun=sub.spawn_actor_from_class(unreal.DirectionalLight,V(0,0,4000),unreal.Rotator(pitch=-45,yaw=-40,roll=0));sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(4.)
    sky=sub.spawn_actor_from_class(unreal.SkyLight,V(0,0,3000));c=sky.get_component_by_class(unreal.SkyLightComponent);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP);c.set_editor_property('cubemap',A.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));c.set_intensity(1.2)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',A.load_blueprint_class('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode'))
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
else:
    # A failed initial lighting setup can leave the fixture loaded but unsaved.
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_name()=='Lvl_AirJetRegression':assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    else:unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors=sub.get_all_level_actors()
    if not any(isinstance(a,unreal.SkyLight) for a in actors):
        sky=sub.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(x=0,y=0,z=3000));c=sky.get_component_by_class(unreal.SkyLightComponent);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP);c.set_editor_property('cubemap',A.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));c.set_intensity(1.2)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',A.load_blueprint_class('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode'))
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
import Test_AirJetRegression

