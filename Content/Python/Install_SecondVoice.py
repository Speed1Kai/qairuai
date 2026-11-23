"""A radio call from Shelter 07 leading to a playable telephone exchange."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal
from Build_RuinedUrbanCampus import local
from CityCombat_Common import A, B, add, components, compile_bp, link, save, val, var
from Install_StoryMemory import CITY, MISSION, L, Story, bp_asset, insert_entry, load
from Install_OwnFrequency import can_use, speech
from Install_VisorSubtitles import publish_fields
from Shelter07_Waterworks import label

PROJECT = Path(unreal.Paths.project_dir()).resolve()
ROOT = '/Game/Story/SecondVoice'
ROOM = ROOT + '/BP_TelephoneExchangeMission'
LABEL = 'CITY_TelephoneExchangeMission'
DOOR = (32376, 81912, 2294)
OUT = (32632, 81950, 2263)
ENTRY = (32560, 81950, 1508)
RETURN = (32730, 81950, 1543)
TECH = (32255, 82056, 1547)
PANEL = (32030, 81755, 1554)
ISOLATOR = (32635, 82158, 1554)

CONCRETE = '/Game/LabTutorial/Industrial/M_Concrete_Dirty'
FLOOR = '/Game/Surface/Materials/CampusPaving/M_CampusConcreteSlabs'
STEEL = '/Game/Surface/Materials/M_RuinSteel'
BLACK = '/Game/Surface/Materials/M_Charcoal'
RED = '/Game/LabTutorial/Industrial/M_DoorStatus_Red'
GREEN = '/Game/LabTutorial/Industrial/M_DoorStatus_Green'
AMBER = '/Game/LabTutorial/Industrial/M_AmberIndicator'
MAT = '/Game/LabTutorial/Industrial/M_DoorArmor'
RESIDENT = '/Game/Characters/ShelterResident'
TITLE = 'ВТОРОЙ ГОЛОС В ЭФИРЕ'

def sign_material(source,name):
    folder=ROOT+'/Signs'
    target=folder+'/M_'+name
    if A.does_asset_exist(target):
        return load(target)
    task=unreal.AssetImportTask()
    for key,value in dict(filename=str(source/(name+'.png')),destination_path=folder,
                          automated=True,save=True).items():
        task.set_editor_property(key,value)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([task])
    texture=load(folder+'/'+name)
    material=tools.create_asset('M_'+name,folder,unreal.Material,unreal.MaterialFactoryNew())
    library=unreal.MaterialEditingLibrary
    sample=library.create_material_expression(material,unreal.MaterialExpressionTextureSample)
    sample.set_editor_property('texture',texture)
    assert library.connect_material_property(sample,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
    library.recompile_material(material)
    save(material)
    return material


def build_exchange(source):
    bp = bp_asset(ROOM)
    prior_labels = ('UplinkSign','UplinkSwitchSign','SwitchSign','BoardHeader','BoardRowA','BoardRowB')
    entries = components(bp)
    obsolete = [handle for handle,_,name in entries if name in prior_labels]
    if obsolete:
        subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        assert subsystem.delete_subobjects(entries[0][0],obsolete,bp)==len(obsolete)
    add(bp, unreal.SceneComponent, 'SiteRoot')

    def solid(name, loc, size, mat=STEEL, collision=False):
        c = add(bp, unreal.StaticMeshComponent, name, 'SiteRoot')
        c.set_static_mesh(load('/Engine/BasicShapes/Cube'))
        c.set_editor_property('relative_location', local(*loc))
        c.set_editor_property('relative_scale3d', unreal.Vector(*(v/100 for v in size)))
        c.set_material(0, load(mat))
        c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        return c

    def plate(component,image,position,width,height,yaw):
        mesh=add(bp,unreal.StaticMeshComponent,component,'SiteRoot')
        mesh.set_static_mesh(load('/Engine/BasicShapes/Plane'))
        mesh.set_editor_property('relative_location',local(*position))
        mesh.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw,roll=90))
        mesh.set_editor_property('relative_scale3d',unreal.Vector(width/100,height/100,1))
        mesh.set_collision_profile_name('NoCollision')
        mesh.set_material(0,sign_material(source,image))
        return mesh

    def lamp(name, loc, color, intensity, radius):
        c = add(bp, unreal.PointLightComponent, name, 'SiteRoot')
        c.set_editor_property('relative_location', local(*loc))
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_intensity(intensity)
        c.set_attenuation_radius(radius)
        c.set_light_color(unreal.LinearColor(*color,1.))
        c.set_cast_shadows(False)
        c.set_editor_property('volumetric_scattering_intensity',0.)

    # The locking panel is attached to the existing service facade.
    exterior = solid('ServiceLock',(32364,81912,2294),(18,31,54),MAT)
    exterior.set_custom_depth_stencil_value(253)
    exterior.set_render_custom_depth(True)
    solid('AccessStatus',(32374,81912,2309),(2,14,6),AMBER)
    solid('UplinkMeter',(32635,82176,1546),(85,15,115),MAT)
    solid('UplinkScreen',(32635,82166,1581),(65,5,23),BLACK)
    solid('UplinkStatus',(32635,82162,1581),(38,2,5),RED)
    shutter = solid('UplinkSwitch',ISOLATOR,(11,18,32),AMBER)
    shutter.set_custom_depth_stencil_value(253)
    shutter.set_render_custom_depth(True)
    plate('CityLineFace','CityLinePlate',(32635,82154,1614),82,20,180)
    for i,x in enumerate((32619,32630,32641)):
        solid(f'UplinkConduit{i}',(x,82179,1635),(3,7,61),STEEL)
    solid('UplinkCrossbar',(32430,82180,1661),(425,8,8),BLACK)
    # Build a walkable service room below the existing facade's solid shell.
    solid('Floor',(32358,81945,1376),(798,520,48),FLOOR,True)
    solid('Ceiling',(32358,81945,1712),(798,520,30),CONCRETE,True)
    for name,pos,size in (
        ('WestWall',(31964,81945,1548),(28,520,330)),
        ('EastWall',(32750,81945,1548),(28,520,330)),
        ('SouthWall',(32358,81690,1548),(798,28,330)),
        ('NorthWall',(32358,82200,1548),(798,28,330)),
    ):
        solid(name,pos,size,CONCRETE,True)
    for i,x in enumerate((32076,32357,32638)):
        solid(f'CeilingCrossbeam{i}',(x,81945,1678),(34,513,24),STEEL)
    for i,y in enumerate((81770,81945,82120)):
        solid(f'CableTray{i}',(32355,y,1661),(760,15,10),BLACK)
        solid(f'PulpitRaceway{i}',(31986,y,1574),(9,7,180),STEEL)
    solid('InteriorDoor',(32729,81950,1527),(12,130,246),MAT)
    solid('ExitHandle',(32720,81903,1532),(7,10,21),AMBER)
    solid('ExitHeader',(32716,81950,1663),(6,143,24),BLACK)
    label(bp,'ExitSign','ВЫХОД',(32711,81950,1670),180,11)
    solid('DeskTop',(32218,82128,1484),(183,88,9),STEEL,True)
    for i,x in enumerate((32135,32300)):
        for j,y in enumerate((82095,82161)):
            solid(f'DeskLeg{i}{j}',(x,y,1440),(6,6,86),MAT)
    solid('ReceiverCase',(32182,82138,1510),(72,37,42),BLACK)
    solid('ReceiverScreen',(32183,82117,1512),(42,4,24),GREEN)
    solid('ReceiverKnobs',(32217,82116,1509),(8,5,26),STEEL)
    solid('RadioHandset',(32265,82112,1492),(32,11,6),BLACK)
    for i,y in enumerate((81840,81943,82046)):
        solid(f'Mainframe{i}',(32005,y,1507),(58,94,205),STEEL,True)
        for j,z in enumerate((1450,1476,1502,1528,1554,1580)):
            solid(f'Patch{i}{j}',(32036,y,z),(6,83,20),BLACK)
            for k in range(3):
                solid(f'Status{i}{j}{k}',(32040,y-30+k*7,z),(2,2,3),AMBER if (j+k)%4==0 else GREEN)
    solid('PatchCase',(32002,81755,1526),(44,66,180),MAT,True)
    switch = solid('LineControl',(32027,81755,1554),(5,38,39),BLACK)
    switch.set_custom_depth_stencil_value(253)
    switch.set_render_custom_depth(True)
    solid('LineControlStatus',(32030,81755,1564),(2,17,5),RED)
    solid('SwitchLegend',(32029,81755,1593),(6,74,23),BLACK)
    plate('LocalLineFace','LocalLinePlate',(32034,81755,1595),70,17,-90)
    solid('EvacuationBoard',(32429,82183,1578),(224,10,112),BLACK)
    plate('EvacuationBoardFace','EvacuationPlate',(32429,82175,1578),216,108,180)
    for i,(p,color) in enumerate((
        ((32579,81964,1655),(.81,.88,1.)),
        ((32269,82081,1655),(1.,.77,.52)),
        ((32035,81894,1655),(.71,.91,1.)),
    )):
        lamp(f'RoomLamp{i}',p,color,1440.,280.)
        solid(f'LampTube{i}',(p[0],p[1],1670),(68,10,6),AMBER)
    exposure_box = add(bp,unreal.BoxComponent,'ExposureBounds','SiteRoot')
    exposure_box.set_editor_property('relative_location',local(32358,81945,1548))
    exposure_box.set_box_extent(unreal.Vector(381,241,150),False)
    exposure_box.set_collision_profile_name('NoCollision')
    pp = add(bp,unreal.PostProcessComponent,'ExchangeExposure','ExposureBounds')
    pp.set_editor_property('unbound',False)
    pp.set_editor_property('blend_radius',22.)
    pp.set_editor_property('priority',64.)
    settings = pp.get_editor_property('settings')
    for key,value in (('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),
                      ('auto_exposure_apply_physical_camera_exposure',False),
                      ('auto_exposure_bias',1.35)):
        settings.set_editor_property('override_'+key,True)
        settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)

    body=add(bp,unreal.SkeletalMeshComponent,'Technician','SiteRoot')
    body.set_skeletal_mesh_asset(load(RESIDENT+'/SK_S07_Resident'))
    body.set_collision_profile_name('NoCollision')
    body.set_editor_property('relative_location',local(TECH[0],TECH[1],1400))
    body.set_editor_property('relative_rotation',unreal.Rotator(yaw=-142))
    body.override_animation_data(load(RESIDENT+'/Animations/AN_S07_Resident_Idle'),True,True,0.,.93)
    space=add(bp,unreal.CapsuleComponent,'TechnicianSpace','SiteRoot')
    space.set_editor_property('relative_location',local(TECH[0],TECH[1],1490))
    space.set_capsule_size(30,90,False)
    space.set_collision_profile_name('Pawn')
    space.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    space.set_editor_property('generate_overlap_events',False)
    compile_bp(bp)
    g=Story(bp,'ShowLineInterruption')
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('AccessStatus'),ElementIndex=0,Material=RED))
    g=Story(bp,'DisconnectCityLine')
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('UplinkStatus'),ElementIndex=0,Material=BLACK))
    g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=g.get('UplinkSwitch'),bValue=False))
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('UplinkSwitch'),
                NewRotation='(Pitch=0,Yaw=0,Roll=62)',bSweep=False,bTeleport=True))
    g=Story(bp,'ReleaseLocalLine')
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('LineControlStatus'),ElementIndex=0,Material=GREEN))
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('AccessStatus'),ElementIndex=0,Material=GREEN))
    g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=g.get('LineControl'),bValue=False))
    compile_bp(bp)
    return bp

def audio(source, lines):
    assets = unreal.AssetToolsHelpers.get_asset_tools()
    sounds = {}
    for key in lines:
        name='S_SecondVoice_'+key
        path=ROOT+'/Audio/'+name
        if not A.does_asset_exist(path):
            task=unreal.AssetImportTask()
            for k,v in dict(filename=str(source/(name+'.wav')),destination_path=ROOT+'/Audio',
                            automated=True,save=True).items():
                task.set_editor_property(k,v)
            assets.import_asset_tasks([task])
        sounds[key]=load(path)
        assert sounds[key].duration>1.
    return sounds

def build_mission(room, lines, sounds):
    mission=load(MISSION)
    for name,kind,d in (('SecondVoiceStep','int','0'),('SecondVoiceInputUsed','bool','false'),
                        ('SecondVoiceIntercepted','bool','false'),('SecondVoiceIsolated','bool','false'),
                        ('SecondVoiceConfirmed','bool','false')):
        var(mission,name,kind,d)
    compile_bp(mission)

    focus_points={DOOR:'Door',RETURN:'Exit',TECH:'Technician',PANEL:'Line',ISOLATOR:'Isolator'}
    for point,name in focus_points.items():
        focus=Story(mission,'SecondVoiceFocus'+name)
        can_use(focus,point)
    compile_bp(mission)

    def focus_on(g,point):
        g.do(g.own('SecondVoiceFocus'+focus_points[point]))

    def stage(g,n):
        return g.compare('EqualEqual',g.get('SecondVoiceStep'),n)

    def available(g):
        return g.both(g.compare('GreaterEqual',g.get('SecondVoiceStep'),3),
                      g.compare('EqualEqual',g.get('ShelterStep'),5))

    room_class=B.generated_class(room).get_path_name()

    def room_action(g,name):
        found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=room_class))
        ref=g.out(found)
        g.branch(g.valid(ref))
        action=g.node(g.e.add_call_function_node(room_class+'.'+name))
        val(action.find_self_pin(),ref)
        g.do(action)

    def cue(g,key):
        row=lines[key]
        g.set('VisorRadioSource',row['caption'])
        publish_fields(g,'VisorRadio',row,float(sounds[key].duration))
        speech(g,key,lines,sounds)

    def prompt(g,point,text,fallback):
        focus_on(g,point)
        caption=g.math('SelectString',A=text,B=fallback,bPickA=g.get('FrequencyCanUse'))
        changed=g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=g.get('Objective'),B=caption))
        g.branch(changed)
        g.goal(caption,point)

    def teleport(g,point,yaw):
        target=g.do(g.call('Engine.Actor.K2_TeleportTo',target=g.get('Player'),
                           DestLocation=L(point),DestRotation=f'(Pitch=0,Yaw={yaw},Roll=0)'))
        g.branch(g.out(target))
        g.do(g.call('Engine.Controller.SetControlRotation',target=g.pc(),
                    NewRotation=g.math('MakeRotator',Roll=0.,Pitch=0.,Yaw=yaw)))
        g.set('SecondVoiceInputUsed',True)

    g=Story(mission,'SecondVoiceAdvance')
    g.branch(g.compare('GreaterEqual',g.get('ShelterStep'),4))
    g.branch(g.ready())
    for current,key,nxt in ((0,'Operator',1),(1,'Call',2),(2,'Direction',3),(4,None,5)):
        branch=g.branch(stage(g,current))
        if key:
            cue(g,key)
        g.set('SecondVoiceStep',nxt)
        g.cursor=branch.find_else_pin()
    outside=g.branch(stage(g,3))
    g.branch(g.compare('EqualEqual',g.get('ShelterStep'),5))
    g.branch(g.not_(g.get('SecondVoiceIntercepted')))
    g.branch(g.near(DOOR,880.))
    room_action(g,'ShowLineInterruption')
    g.set('SecondVoiceIntercepted',True)
    cue(g,'Interception')
    g.cursor=outside.find_else_pin()
    g.branch(stage(g,6))
    response=g.branch(g.get('SecondVoiceConfirmed'))
    g.set('SecondVoiceStep',7)
    g.cursor=response.find_else_pin()
    cue(g,'RadioCheck')
    g.set('SecondVoiceConfirmed',True)
    compile_bp(mission)

    g=Story(mission,'SecondVoiceGuide')
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('StoryHUD'),
                PropertyName='ShelterChapter',Value=TITLE))
    inside=g.branch(g.near(ENTRY,1020.))
    # The exterior route is on the same XY but 7.5 m above the apparatus room.
    on_lower_floor=g.branch(g.num('Less',g.axis(g.position(g.get('Player')),'Z'),1710.))
    internal=on_lower_floor.find_then_pin()
    g.cursor=inside.find_else_pin()
    exterior=g.branch(g.compare('Less',g.get('SecondVoiceStep'),7))
    link(on_lower_floor.find_else_pin(),exterior.find_execute_pin())
    prompt(g,DOOR,'F · открыть служебную дверь','Телефонная станция · найди служебную дверь')
    g.cursor=exterior.find_else_pin()
    g.branch(g.pget('StoryGoalActive'))
    g.set('Objective','Миссия завершена · местная линия открыта')
    g.pset('StoryGoalActive',False,'Bool')
    g.cursor=internal
    exit_control=g.branch(g.near(RETURN,139.))
    prompt(g,RETURN,'F · выйти на улицу','Выход · служебная дверь')
    g.cursor=exit_control.find_else_pin()
    meet=g.branch(stage(g,3))
    prompt(g,TECH,'F · поговорить с техником','Аппаратная · поговори с техником')
    g.cursor=meet.find_else_pin()
    working=g.branch(stage(g,5))
    isolated=g.branch(g.get('SecondVoiceIsolated'))
    prompt(g,PANEL,'F · открыть местную линию','Аппаратная · включи местную линию у стойки')
    g.cursor=isolated.find_else_pin()
    prompt(g,ISOLATOR,'F · отсоединить городскую линию','Атлас слушает линию · найди жёлтый рубильник')
    g.cursor=working.find_else_pin()
    finished=g.branch(stage(g,7))
    prompt(g,RETURN,'F · выйти на улицу','Местная линия открыта · выход на улицу')
    compile_bp(mission)

    g=Story(mission,'SecondVoiceUse')
    g.set('SecondVoiceInputUsed',False)
    g.branch(available(g))
    inside=g.branch(g.num('Less',g.axis(g.position(g.get('Player')),'Z'),1710.))
    focus_on(g,RETURN)
    exit_control=g.branch(g.get('FrequencyCanUse'))
    teleport(g,OUT,0)
    g.cursor=exit_control.find_else_pin()
    meeting=g.branch(stage(g,3))
    focus_on(g,TECH)
    g.branch(g.get('FrequencyCanUse'))
    cue(g,'Meeting')
    g.goal('Техник · выслушай рассказ об эвакуации',TECH)
    g.set('SecondVoiceStep',4)
    g.set('SecondVoiceInputUsed',True)
    g.cursor=meeting.find_else_pin()
    g.branch(stage(g,5))
    connected=g.branch(g.not_(g.get('SecondVoiceIsolated')))
    focus_on(g,ISOLATOR)
    g.branch(g.get('FrequencyCanUse'))
    room_action(g,'DisconnectCityLine')
    g.set('SecondVoiceIsolated',True)
    g.goal('Городская линия отключена · включи местную связь у стойки',PANEL)
    g.set('SecondVoiceInputUsed',True)
    g.cursor=connected.find_else_pin()
    focus_on(g,PANEL)
    g.branch(g.get('FrequencyCanUse'))
    room_action(g,'ReleaseLocalLine')
    cue(g,'StationTest')
    g.goal('Местная линия открыта · дождись ответа убежища',TECH)
    g.set('SecondVoiceStep',6)
    g.set('SecondVoiceInputUsed',True)
    g.cursor=inside.find_else_pin()
    g.branch(g.compare('Less',g.get('SecondVoiceStep'),7))
    focus_on(g,DOOR)
    g.branch(g.get('FrequencyCanUse'))
    teleport(g,ENTRY,180)
    compile_bp(mission)

    def tick(g, old, tag):
        g.do(g.own('SecondVoiceAdvance')).rename(tag)
        active=g.branch(available(g))
        g.do(g.own('SecondVoiceGuide'))
        for previous in old:
            link(active.find_else_pin(),previous)

    def use(g, old, tag):
        g.do(g.own('SecondVoiceUse')).rename(tag)
        consumed=g.branch(g.get('SecondVoiceInputUsed'))
        for previous in old:
            link(consumed.find_else_pin(),previous)

    insert_entry(mission,'ShelterTick','SecondVoiceDispatchTick',tick)
    insert_entry(mission,'ShelterUse','SecondVoiceDispatchUse',use)
    compile_bp(mission)
    return mission

def install(source, out):
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    saving=unreal.EditorLoadingAndSavingUtils
    assert not editor.get_game_world()
    backup=PROJECT/'Saved/Backups/SecondVoice'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    for ref,suffix in ((CITY,'.umap'),(MISSION,'.uasset'),(ROOM,'.uasset')):
        rel=Path('Content')/(ref.removeprefix('/Game/')+suffix)
        file=PROJECT/rel
        if file.is_file():
            dest=backup/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(file,dest)
    out.mkdir(parents=True,exist_ok=True)
    (out/'Backup.json').write_text(json.dumps({'backup':str(backup)},indent=2),encoding='utf8')
    if editor.get_editor_world().get_path_name().split('.')[0]!=CITY:
        assert not saving.get_dirty_map_packages()
        assert levels.load_level(CITY)
    assert not saving.get_dirty_map_packages()
    lines=json.loads((source/'Dialogue.json').read_text(encoding='utf-8-sig'))
    sounds=audio(source,lines)
    room=build_exchange(source)
    mission=build_mission(room,lines,sounds)
    placed=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL),None)
    if not placed:
        placed=actors.spawn_actor_from_class(B.generated_class(room),unreal.Vector())
        assert placed
        placed.set_actor_label(LABEL)
        placed.set_folder_path('CITY/TelephoneExchange')
    save(room)
    save(mission)
    assert saving.save_map(editor.get_editor_world(),CITY)
    (out/'Installed.json').write_text(json.dumps({'map':CITY,'mission':MISSION,'actor':ROOM,
        'backup':str(backup),'door':DOOR,'room':ENTRY,'sounds':{k:v.duration for k,v in sounds.items()}},indent=2),encoding='utf8')




if __name__=='__main__':
    install(PROJECT/'SourceAssets/SecondVoice',PROJECT/'Saved/SecondVoiceEvents')
