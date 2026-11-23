
"""Bind the operator to the radio desk and calibrate illumination inside Shelter 07."""
from datetime import datetime
from pathlib import Path
import json
import shutil

import unreal
from Build_RuinedUrbanCampus import local
from CityCombat_Common import A, G, add, compile_bp, components, link, save, var
from Install_StoryMemory import CITY, L, Story, insert_entry, load
from Install_ShelterResident import LABEL, ROOT
from Shelter07_Waterworks import SHELTER, attach_mesh, position

PROJECT=Path(unreal.Paths.project_dir()).resolve()
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EDITOR=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
LEVELS=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
U=unreal.EditorLoadingAndSavingUtils
SEAT=(8.38,-.18,-1.55)
LAMP_SPECS={
    'S07HallFill':((-1.85,.95,2.82),(1.,.83,.67),3900.,645.),
    'S07WardTask':((2.17,2.97,2.12),(1.,.88,.74),5600.,355.),
    'S07RadioTask':((7.88,-.53,.15),(1.,.78,.57),570.,255.),
}
POST={
    'WaterworksExposure':(1.47,.135),
    'RadioExposure':(1.18,.105),
}
BP_RESIDENT=ROOT+'/BP_ShelterResident'
BACKUP_PATHS=(
    'Surface/Lvl_CampusConnected.umap',
    'Characters/ShelterResident/BP_ShelterResident.uasset',
    'Characters/ShelterResident/SK_S07_Resident.uasset',
    'Environment/Shelter07/BP_Shelter07.uasset',
)
STEEL='/Game/Surface/Materials/M_RuinSteel'
SEAT_PAD='/Game/Surface/Materials/M_Charcoal'
AMBER='/Game/Surface/Materials/M_ExitAmber'
CYAN='/Game/Surface/Materials/M_AILight'

def component_map(bp):
    return {name:obj for _,obj,name in components(bp) if obj}

def light(light_component, spec):
    at,color,intensity,radius=spec
    light_component.set_editor_property('relative_location',local(*position(*at)))
    light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light_component.set_light_color(unreal.LinearColor(*color,1.))
    light_component.set_editor_property('intensity',intensity)
    light_component.set_editor_property('attenuation_radius',radius)
    light_component.set_cast_shadows(False)
    light_component.set_editor_property('volumetric_scattering_intensity',0.)
    light_component.set_visibility(True)

def exposure(component, values):
    ev,ambient=values
    s=component.get_editor_property('settings')
    s.set_editor_property('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL)
    s.set_editor_property('override_auto_exposure_method',True)
    s.set_editor_property('override_auto_exposure_apply_physical_camera_exposure',True)
    s.set_editor_property('auto_exposure_apply_physical_camera_exposure',False)
    s.set_editor_property('override_auto_exposure_bias',True)
    s.set_editor_property('auto_exposure_bias',ev)
    s.set_editor_property('override_ambient_cubemap_intensity',True)
    s.set_editor_property('ambient_cubemap_intensity',ambient)
    s.set_editor_property('ambient_cubemap',load('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    component.set_editor_property('settings',s)

def room_curve(r):
    # Using the existing fixture positions keeps the power switch and its lights together.
    for name, settings in POST.items():
        exposure(r[name],settings)
    r['RadioExposureBox'].set_box_extent(unreal.Vector(227,268,122),False)
    r['RadioExposure'].set_editor_property('blend_radius',74.)
    r['ShelterLight7'].set_editor_property('intensity',725.)
    r['ShelterLight6'].set_editor_property('intensity',1770.)
    r['MedicWardPendant'].set_editor_property('intensity',2150.)

def room(bp):
    def mesh(name,shape,p,size,material):
        component=attach_mesh(bp,name,load('/Engine/BasicShapes/'+shape),position(*p),size)
        component.set_material(0,load(material))
        return component

    # Chair is centered on the main CRT, leaving the two station stools available on both sides.
    x,y,z=SEAT
    mesh('S07RadioSeatFrame','Cylinder',(x,y,z+.423),(.46,.43,.052),STEEL)
    mesh('S07RadioSeatPad','Cylinder',(x,y,z+.476),(.45,.42,.087),SEAT_PAD)
    mesh('S07RadioSeatStem','Cylinder',(x,y,z+.25),(.047,.047,.46),STEEL)
    mesh('S07RadioSeatBase','Cylinder',(x,y,z+.036),(.38,.37,.058),STEEL)
    mesh('S07RadioSeatFootRest','Cylinder',(x,y,z+.18),(.30,.27,.018),STEEL)
    mesh('S07RadioPilotHousing','Cube',(8.67,.445,-.605),(.137,.028,.055),STEEL)
    mesh('S07RadioBatteryPilot','Cube',(8.67,.427,-.605),(.092,.010,.024),AMBER)
    mesh('S07RadioReservePilot','Cube',(8.67,.424,-.605),(.092,.010,.024),CYAN).set_visibility(False)
    for name,spec in LAMP_SPECS.items():
        light(add(bp,unreal.PointLightComponent,name,'SiteRoot'),spec)
    room_curve(component_map(bp))
    compile_bp(bp)
    def connect_pilot(g,existing,tag):
        off=g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('S07RadioBatteryPilot'),bNewVisibility=False,bPropagateToChildren=False))
        off.rename(tag)
        g.visibility('S07RadioReservePilot',True)
        for pin in existing:
            link(g.cursor,pin)
    insert_entry(bp,'EnableShelterPower','RadioPilotPower',connect_pilot)
    g=Story(bp,'CalibrateShelterLights')
    for name,power in [(k,v[2]) for k,v in LAMP_SPECS.items()]+[
            ('ShelterLight6',1770.),('ShelterLight7',725.),('MedicWardPendant',2150.)]:
        g.do(g.call('Engine.LightComponent.SetIntensity',target=g.get(name),NewIntensity=power))
    compile_bp(bp)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    if not any(n.get_name()=='S07CalibrateLights' for n in graph.list_all_nodes()):
        g=Story(bp)
        g.override('ReceiveBeginPlay')
        previous=list(g.cursor.list_connected_pins())
        g.cursor.break_pin_links()
        g.do(g.own('CalibrateShelterLights')).rename('S07CalibrateLights')
        for pin in previous:
            link(g.cursor,pin)
    configure_interior_exposure(bp)
    compile_bp(bp)
    save(bp)

def configure_interior_exposure(bp):
    # Stabilize the view only for the player in the shelter. Restore the previous
    # setting on exit, map unload and the end of a Play In Editor session.
    var(bp,'S07ExposureActive','bool','false')
    var(bp,'S07PreviousExposureQuality','int','2')
    compile_bp(bp)
    cvar='r.EyeAdaptationQuality'
    restore=Story(bp,'RestoreShelterExposure')
    restore.branch(restore.get('S07ExposureActive'))
    value=restore.out(restore.call('Engine.KismetStringLibrary.Conv_IntToString',InInt=restore.get('S07PreviousExposureQuality')))
    cmd=restore.out(restore.call('Engine.KismetStringLibrary.Concat_StrStr',A=cvar+' ',B=value))
    restore.do(restore.call('Engine.KismetSystemLibrary.ExecuteConsoleCommand',Command=cmd,SpecificPlayer=restore.pc()))
    restore.set('S07ExposureActive',False)
    compile_bp(bp)
    g=Story(bp,'UpdateShelterExposure')
    pawn=g.player()
    inside=g.both(g.valid(pawn),g.math('IsPointInBox',Point=g.position(pawn),
             BoxOrigin=L(position(.16,0.,.16)),BoxExtent=L((1115.,640.,232.))))
    g.branch(g.math('NotEqual_BoolBool',A=inside,B=g.get('S07ExposureActive')))
    entering=g.branch(inside)
    quality=g.out(g.do(g.call('Engine.KismetSystemLibrary.GetConsoleVariableIntValue',VariableName=cvar)))
    g.set('S07PreviousExposureQuality',quality)
    g.do(g.call('Engine.KismetSystemLibrary.ExecuteConsoleCommand',Command=cvar+' 0',SpecificPlayer=g.pc()))
    g.set('S07ExposureActive',True)
    g.cursor=entering.find_else_pin()
    g.do(g.own('RestoreShelterExposure'))
    compile_bp(bp)

    for event,func,tag in (('ReceiveTick','UpdateShelterExposure','S07ExposureTick'),
                           ('ReceiveEndPlay','RestoreShelterExposure','S07ExposureExit')):
        graph=G.get_graph_editor_by_name(bp,'EventGraph')
        if any(n.get_name()==tag for n in graph.list_all_nodes()):
            continue
        g=Story(bp)
        g.override(event)
        previous=list(g.cursor.list_connected_pins())
        g.cursor.break_pin_links()
        g.do(g.own(func)).rename(tag)
        for pin in previous:
            link(g.cursor,pin)

def radio_loop(source,skeleton):
    opts=unreal.FbxImportUI()
    for key,value in dict(import_mesh=False,import_as_skeletal=True,import_animations=True,import_materials=False,
                          import_textures=False,skeleton=skeleton,automated_import_should_detect_type=False,
                          mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION).items():
        opts.set_editor_property(key,value)
    opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',True)
    if A.does_asset_exist(ROOT+'/Animations/AN_S07_RadioWatch'):
        current=load(ROOT+'/Animations/AN_S07_RadioWatch')
        if current.get_editor_property('skeleton')==skeleton:
            return current
    task=unreal.AssetImportTask()
    fields=dict(filename=str(source/'AN_S07_RadioWatch.fbx'),destination_path=ROOT+'/Animations',
                destination_name='AN_S07_RadioWatch',automated=True,replace_existing=True,
                replace_existing_settings=True,save=False,options=opts)
    for key,value in fields.items():
        task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    assert task.get_editor_property('imported_object_paths'), 'Radio animation did not import'
    an=load(ROOT+'/Animations/AN_S07_RadioWatch')
    assert an and 11.9<an.sequence_length<12.1 and an.get_editor_property('skeleton')==skeleton,an
    save(an)
    return an

def restore_skeleton(mesh):
    if mesh.skeleton:
        return mesh.skeleton
    name=mesh.get_name()+'_Skeleton'
    full=ROOT+'/'+name
    if A.does_asset_exist(full):
        skeleton=load(full)
        mesh.set_editor_property('skeleton',skeleton)
    else:
        factory=unreal.SkeletonFactory()
        props=unreal.get_default_object(unreal.SystemLibrary)
        props.call_method('SetObjectPropertyByName',args=(factory,unreal.Name('TargetSkeletalMesh'),mesh))
        skeleton=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Skeleton,factory)
    assert skeleton and mesh.skeleton==skeleton
    save(skeleton)
    save(mesh)
    return skeleton

def seat_operator(bp,an):
    nodes=component_map(bp)
    body=nodes['Body']
    body.override_animation_data(an,True,True,0.,1.)
    space=nodes['PersonalSpace']
    space.set_capsule_size(27.,66.,False)
    space.set_editor_property('relative_location',unreal.Vector(0,3.,66.))
    compile_bp(bp)
    save(bp)
    npc=next(a for a in ACTORS.get_all_level_actors() if a.get_actor_label()==LABEL)
    npc.modify()
    npc.set_actor_location(local(*position(*SEAT)),False,True)
    npc.set_actor_rotation(unreal.Rotator(),True)
    skin=npc.get_editor_property('Body')
    yaw=0.  # The imported component's local forward is +Y.
    npc.set_actor_rotation(unreal.Rotator(yaw=yaw),True)
    skin.modify()
    skin.override_animation_data(an,True,True,0.,1.)
    capsule=npc.get_editor_property('PersonalSpace')
    capsule.modify()
    capsule.set_capsule_size(27.,66.,False)
    capsule.set_editor_property('relative_location',unreal.Vector(0,3.,66.))
    return an,yaw

def install(source, output_dir):
    assert not EDITOR.get_game_world()
    world=EDITOR.get_editor_world()
    if world.get_path_name().split('.')[0]!=CITY:
        assert not U.get_dirty_map_packages()
        assert LEVELS.load_level(CITY)
        world=EDITOR.get_editor_world()
    output_dir.mkdir(parents=True,exist_ok=True)
    recovery=output_dir/'OriginalBackup.txt'
    assert not U.get_dirty_map_packages() or recovery.exists()
    if recovery.exists():
        backup=Path(recovery.read_text(encoding='utf8').strip())
        assert backup.resolve().is_relative_to((PROJECT/'Saved/Backups/ShelterRadio').resolve())
    else:
        backup=PROJECT/'Saved/Backups/ShelterRadio'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        recovery.write_text(str(backup),encoding='utf8')
    for rel in BACKUP_PATHS:
        dest=backup/'Content'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            shutil.copy2(PROJECT/'Content'/rel,dest)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    mesh=load(ROOT+'/SK_S07_Resident')
    skeleton=restore_skeleton(mesh)
    clip=radio_loop(source,skeleton)
    room(load(SHELTER))
    placed=next(a for a in ACTORS.get_all_level_actors() if a.get_actor_label()=='CITY_Shelter07')
    placed.modify()
    old_names=(*POST,'RadioExposureBox','ShelterLight6','ShelterLight7','MedicWardPendant')
    instance={name:placed.get_editor_property(name) for name in (*old_names,*LAMP_SPECS)}
    for component in instance.values():
        component.modify()
    room_curve(instance)
    for name,spec in LAMP_SPECS.items():
        light(instance[name],spec)
    _,yaw=seat_operator(load(BP_RESIDENT),clip)
    assert U.save_map(world,CITY)
    (output_dir/'Installed.json').write_text(json.dumps({
        'passed':True,'map':CITY,'backup':str(backup),'operator':BP_RESIDENT,
        'position_world_cm':position(*SEAT),'animation':clip.get_path_name(),
        'animation_seconds':clip.sequence_length,'yaw':yaw,'lamp_specs':LAMP_SPECS,
        'exposure':POST,
    },ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    install(PROJECT/'SourceAssets/Shelter07/Resident',PROJECT/'Saved/Shelter07/RadioWatch')
