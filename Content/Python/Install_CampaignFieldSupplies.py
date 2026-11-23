"""Extend the campaign with field supply sites, arrival fog and shelter reactions."""
from datetime import datetime
import json
import math
from pathlib import Path
import shutil

import unreal

from Build_RuinedUrbanCampus import local
from CityCombat_Common import A, B, G, add, compile_bp, components, hook, link, pin, save, val, var
from Install_DemoCheckpoint import JSON, SLOTS, campaign_save_enabled, file_path, file_struct, int_bool
from Install_EvacuationRelay import focus
from Install_HiddenLabExit import BP as LAB_ROUTE, CENTER, FLOOR, GROUND, LANDING
from Install_Post12Rescue import MAN, MAN_IDLE, WOMAN, WOMAN_IDLE
from Install_StoryMemory import CITY, L, MISSION, PROJECT, Story, bp_asset, insert_entry, load
from Install_VisorSubtitles import publish_fields
from Shelter07_Waterworks import ENTRY, position

V = unreal.Vector
ROOT = '/Game/Story/FieldSupplies'
GRADE = '/Game/Surface/BP_SciFi_CityGrade'
IND = '/Game/LabTutorial/Industrial/'
WRECK = '/Game/Environment/CityAftermath/SM_War_'
CACHE = (
    ('LabAnnex', 'ЛАБОРАТОРИЯ 03', (21950., 78245., 2159.7), 'Lab', 18, 1),
    ('TransitGarrison', 'ТРАНСПОРТНАЯ ЧАСТЬ', (24450., 78250., 2159.7), 'Depot', 30, 1),
    ('WaterLab', 'ЛАБОРАТОРИЯ ВОДОКАНАЛА', (29150., 90900., 2156.), 'Lab', 18, 2),
    ('MunicipalDepot', 'СЕВЕРНАЯ ВОЕННАЯ ЧАСТЬ', (32430., 90565., 2156.), 'Depot', 30, 2),
)
SITE_SIGNS = {
    'LabAnnex':'LAB 03 / RESEARCH ANNEX',
    'TransitGarrison':'TRANSIT GARRISON',
    'WaterLab':'WATER QUALITY LAB',
    'MunicipalDepot':'NORTH DEPOT',
}
RESERVES = ('HunterReserve','BreakerReserve')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ed = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

def component(bp, name):
    return next(c for _, c, n in components(bp) if n == name)

def shape(bp, name, parent, pos, dimensions, material=None, *, mesh=None, rot=None, block=False):
    part = add(bp, unreal.StaticMeshComponent, name, parent)
    part.set_static_mesh(load(mesh or '/Engine/BasicShapes/Cube'))
    part.set_editor_property('relative_location', V(*pos))
    part.set_editor_property('relative_scale3d', V(*(dimensions if mesh else (v/100. for v in dimensions))))
    part.set_editor_property('relative_rotation', rot or unreal.Rotator())
    part.set_collision_profile_name('BlockAll' if block else 'NoCollision')
    if material:
        part.set_material(0, load(material))
    return part

def title(bp, name, parent, pos, caption, size, yaw=-90.):
    part = add(bp, unreal.TextRenderComponent, name, parent)
    part.set_editor_property('relative_location', V(*pos))
    part.set_editor_property('relative_rotation', unreal.Rotator(yaw=yaw))
    part.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    part.set_text(unreal.Text(caption))
    part.set_world_size(size)
    part.set_text_render_color(unreal.Color(236,224,197,255))
    return part

def outpost(key, caption, kind):
    bp = bp_asset(ROOT+'/BP_Field'+key)
    root = 'Site'
    add(bp, unreal.SceneComponent,root)
    concrete = IND+'M_Concrete_Dirty'
    metal = IND+'M_DistressedMetal'
    dark = IND+'M_DoorArmor'
    scorched = '/Game/Surface/RuinedCampus/Siege/M_Siege_BurnedGround'
    brick = '/Game/Surface/RuinedCampus/Siege/M_Siege_BlastConcrete'

    def part(n,p,d,mat=concrete,rot=None,block=False):
        return shape(bp,n,root,p,d,mat,rot=rot,block=block)

    def detail(n,mesh,p,d,rot=None):
        return shape(bp,n,root,p,d,mesh=mesh,rot=rot)

    part('Footing',(0,95,-9),(562,474,21),brick,block=True)
    part('BackWall',(-77,305,127),(412,28,247),concrete,block=True)
    part('FrameLeft',(-258,90,128),(25,427,255),concrete,block=True)
    part('FrameRight',(254,188,130),(33,240,260),concrete,block=True)
    part('Header',(-99,-120,233),(327,33,33),dark,block=True)
    part('PortalLeft',(-258,-120,114),(32,36,234),dark,block=True)
    part('PortalRight',(87,-120,118),(29,38,237),dark,block=True)
    part('NameBacking',(-90,-140,237),(302,4,32),dark)
    title(bp,'SiteName',root,(-90,-145,238),SITE_SIGNS[key],12.)
    part('StoreDoorBacking',(-14,53,201),(172,5,26),dark)
    title(bp,'StoreSign',root,(-14,49,202),'SUPPLY ROOM',10.)
    part('Shelf',(0,91,39),(196,53,75),metal,block=True)
    part('ShelfWornTop',(0,90,79),(205,61,7),dark)
    part('RoofDeck',(-114,130,261),(279,364,19),concrete,block=True)
    part('FallenSlab',(167,197,102),(150,206,20),brick,unreal.Rotator(pitch=-28.,roll=17.))
    part('ScorchPatch',(154,217,2),(137,144,1.2),scorched)
    detail('Debris',WRECK+'RubblePile',(181,193,5),(.48,.48,.55),unreal.Rotator(yaw=41.))
    detail('BrokenSlab',WRECK+'RippedSlabA',(185,292,15),(.58,.56,.57),unreal.Rotator(yaw=38.))
    part('RibOne',(-164,87,248),(14,319,10),metal)
    part('RibTwo',(-56,107,248),(14,319,10),metal)
    if kind=='Lab':
        part('LabWingFooting',(-384,168,-8),(233,294,23),brick,block=True)
        part('LabWingBack',(-385,302,118),(248,24,236),concrete,block=True)
        part('LabWingOuter',(-507,195,103),(23,242,211),brick,block=True)
        part('LabWingSlab',(-435,251,224),(145,111,24),concrete,unreal.Rotator(pitch=7.,roll=-15.))
        detail('LabWingDebris',WRECK+'RippedSlabB',(-388,162,12),(.66,.75,.56),unreal.Rotator(yaw=102.))
        part('Bench',(-205,130,87),(76,153,12),metal,block=True)
        part('ServiceDuct',(-206,129,218),(49,232,37),metal)
        for index, z in enumerate((107,124,141)):
            part(f'LabDrawer{index}',(-190,132,z),(37,66,13),dark)
        for index, x in enumerate((106,143,185,212)):
            part(f'BrokenWindowMullion{index}',(x,-102,155),(6,12,155),metal)
        part('TestBayWall',(173,-104,55),(126,17,112),concrete,block=True)
    else:
        part('GarageFooting',(394,161,-9),(263,330,21),brick,block=True)
        part('GarageBack',(389,313,111),(265,23,223),concrete,block=True)
        part('GarageOuter',(518,177,96),(20,272,198),concrete,block=True)
        part('GaragePier',(498,23,124),(33,46,247),concrete,block=True)
        part('GarageRoofEdge',(467,54,233),(131,58,18),metal,unreal.Rotator(roll=-18.))
        detail('GarageScatteredSlab',WRECK+'RippedSlabA',(404,207,13),(.65,.55,.62))
        part('LoadingLintel',(158,230,235),(170,60,20),metal)
        for index, x in enumerate((-214,-143,149,214)):
            part(f'Baffle{index}',(x,-97,45),(58,19,91),metal,block=True)
        detail('TwistedBarrier',WRECK+'TwistedGuardrail',(212,13,12),(.48,.48,.55),unreal.Rotator(yaw=17.))
        detail('Cases',WRECK+'SpentCases',(-99,-112,2),(.6,.6,.6))
    compile_bp(bp)
    return bp

def stage_city():
    assert levels.load_level(CITY)
    for key, caption, site, kind, _, _ in CACHE:
        bp = outpost(key,caption,kind)
        save(bp)
        label = 'CITY_Field'+key
        placed = next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
        if not placed:
            placed = actors.spawn_actor_from_class(B.generated_class(bp),local(*site))
            assert placed, label
            placed.set_actor_label(label)
            placed.set_folder_path('CITY/Field Supply')
        elif (placed.get_actor_location()-local(*site)).length() > 1.:
            assert placed.set_actor_location(local(*site),False,True)
    scars=bp_asset(ROOT+'/BP_FieldStreetDamage')
    root='DebrisRoot'
    add(scars,unreal.SceneComponent,root)
    shape(scars,'Scorch',root,(40.,10.,1.2),(.75,.69,1.),mesh=WRECK+'Scorch')
    shape(scars,'Guardrail',root,(0.,36.,5.),(.7,.69,.7),mesh=WRECK+'TwistedGuardrail',
          rot=unreal.Rotator(yaw=8.,pitch=15.))
    shape(scars,'SpalledConcrete',root,(-138.,70.,6.),(.64,.56,.59),mesh=WRECK+'RubblePile')
    compile_bp(scars)
    save(scars)
    for index,(x,y,z,yaw) in enumerate(((25800.,77400.,2159.7,14.),(31000.,77500.,2154.4,131.),
                                      (33550.,80070.,2160.2,78.),(32020.,87835.,2156.,69.))):
        label=f'CITY_FieldStreetDamage{index}'
        if not any(a.get_actor_label()==label for a in actors.get_all_level_actors()):
            actor=actors.spawn_actor_from_class(B.generated_class(scars),local(x,y,z),unreal.Rotator(yaw=yaw))
            assert actor,label
            actor.set_actor_label(label)
            actor.set_folder_path('CITY/War damage')
    assert levels.save_current_level()

def site_ammo(site):
    return (site[0],site[1]+72.,site[2]+88.)

def field_components(bp):
    for key, _, site, _, _, _ in CACHE:
        center=site_ammo(site)
        root='FieldAmmo'+key
        add(bp,unreal.SceneComponent,root,'Root').set_editor_property('relative_location',V(*center))
        for index,x in enumerate((-15.,4.,22.)):
            item=shape(bp,root+str(index),root,(x,0.,5.),(.39,.42,.46),
                       mesh='/Game/Combat/Firearms/SM_Hunter_Magazine')
            item.set_custom_depth_stencil_value(253)
            item.set_render_custom_depth(True)
        title(bp,root+'Prompt',root,(0.,-12.,39.),'F / AMMO',9.5).set_visibility(True)

def assign(g, player, name, value, tag):
    g.do(g.call('Engine.KismetSystemLibrary.Set'+tag+'PropertyByName',Object=player,PropertyName=name,Value=value))

def field_logic(bp):
    for key, *_ in CACHE:
        var(bp,'FieldTaken'+key,'bool','false')
    var(bp,'FieldAmmoUsed','bool','false')
    for fn in ('FieldAmmoUse','FieldRestoreSupplies'):
        Story(bp,fn)
    compile_bp(bp)
    for key, _, site, *_ in CACHE:
        focus(bp,'Field'+key,site_ammo(site),48.,205.)
    compile_bp(bp)
    g=Story(bp,'FieldAmmoUse')
    g.set('FieldAmmoUsed',False)
    player=g.get('Player')
    g.branch(g.valid(player))
    g.branch(g.isstage(6))
    g.branch(g.not_(g.pget('NavMapOpen')))
    for key, _, site, _, rounds, cells in CACHE:
        g.do(g.own('EvacFocusField'+key))
        aimed=g.branch(g.both(g.get('EvacFocus'),g.not_(g.get('FieldTaken'+key))))
        g.set('FieldAmmoUsed',True)
        g.set('FieldTaken'+key,True)
        for name, increment in (('HunterReserve',rounds),('BreakerReserve',cells)):
            assign(g,player,name,g.math('Add_IntInt',A=g.pget(name),B=increment),'Int')
        g.visibility('FieldAmmo'+key,False)
        g.sound('/Game/Combat/Firearms/S_Weapon_Magazine',L(site_ammo(site)),.62)
        g.do(g.own('EvacSave'))
        # Continue checking the next cache only when this one didn't consume the key.
        g.cursor=aimed.find_else_pin()

    g=Story(bp,'FieldRestoreSupplies')
    g.branch(campaign_save_enabled(g))
    path=file_path(g,SLOTS[0])
    g.branch(g.out(g.call('Engine.BlueprintPathsLibrary.FileExists',InPath=path)))
    read=g.do(g.call(JSON+'FromFile',File=file_struct(g,path)))
    g.branch(g.out(read))
    data=g.out(read,'OutJsonObject')
    for key, *_ in CACHE:
        field='FieldTaken'+key
        exists=g.do(g.call(JSON+'HasField',JsonObject=data,FieldName=field))
        branch=g.branch(g.out(exists))
        number=g.do(g.call(JSON+'GetField',JsonObject=data,FieldName=field))
        # A legacy checkpoint has no field. Its supply crate remains available.
        local_name='Read'+field
        if local_name not in map(str,g.e.list_local_variable_names()):
            assert g.e.add_local_variable(local_name,B.get_basic_type_by_name('int'),'0')
        typed=g.node(g.e.add_set_local_variable_node(local_name))
        val(pin(typed,local_name),g.out(number,'OutValue'))
        g.do(typed)
        value=pin(g.node(g.e.add_get_local_variable_node(local_name)),local_name,True)
        node=g.node(g.e.add_set_member_variable_node(field))
        val(pin(node,field),g.compare('EqualEqual',value,1))
        g.do(node)
        visible=g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('FieldAmmo'+key),
                          bNewVisibility=g.not_(g.get(field)),bPropagateToChildren=True))
        link(branch.find_else_pin(),visible.find_execute_pin())

    def use(g, old, tag):
        g.do(g.own('FieldAmmoUse')).rename(tag)
        used=g.branch(g.get('FieldAmmoUsed'))
        for previous in old:
            link(used.find_else_pin(),previous)
    def restore(g, old, tag):
        g.do(g.own('FieldRestoreSupplies')).rename(tag)
        for previous in old:
            link(g.cursor,previous)
    compile_bp(bp)
    insert_entry(bp,'RequestRecovery','FieldSupplyUse',use)
    insert_entry(bp,'EvacLoad','FieldSupplyLoad',restore)

    g=Story(bp)
    g.e=G.get_graph_editor_by_name(bp,'EvacSave')
    if not any(n.get_name()=='FieldSupplySave' for n in g.e.list_all_nodes()):
        writer=next(n for n in g.e.list_all_nodes()
            if n.find_input_pin('File').is_valid() and n.find_input_pin('JsonObject').is_valid())
        data=pin(writer,'JsonObject').list_connected_pins()[0]
        start=writer.find_execute_pin()
        g.cursor=start.list_connected_pins()[0]
        start.break_pin_links()
        for key, *_ in CACHE:
            name='FieldTaken'+key
            g.do(g.call(JSON+'SetField',JsonObject=data,FieldName=name,Value=int_bool(g,g.get(name))))
        player=g.get('Player')
        reserves=g.branch(g.valid(player))
        for name in RESERVES:
            g.do(g.call(JSON+'SetField',JsonObject=data,FieldName=name,Value=g.pget(name)))
        reserves.rename('FieldSupplySave')
        link(reserves.find_else_pin(),start)
        link(g.cursor,start)

def shelter_people(bp):
    for name, mesh, idle, point, yaw in (
            ('ShelterDoorWatch',MAN,MAN_IDLE,position(-7.22,1.57,.85),-65.),
            ('ShelterStockKeeper',WOMAN,WOMAN_IDLE,position(7.15,4.56,1.08),-92.),
            ('NorthDepotSurvivor',MAN,MAN_IDLE,(32270.,90675.,2156.),-95.)):
        part=add(bp,unreal.SkeletalMeshComponent,name,'Root')
        part.set_skeletal_mesh_asset(load(mesh))
        part.set_editor_property('relative_location',V(*point))
        part.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw))
        part.set_collision_profile_name('NoCollision')
        part.override_animation_data(load(idle),True,True,0.,.94 if mesh==MAN else 1.)
    for name in ('ShelterGreetingPlayed','ShelterHopePlayed'):
        var(bp,name,'bool','false')
    Story(bp,'ShelterLivingTick')
    compile_bp(bp)
    g=Story(bp,'ShelterLivingTick')
    g.branch(g.valid(g.get('Player')))
    player=g.position(g.get('Player'))
    where=g.axis(player,'Z')
    g.branch(g.both(g.near(ENTRY,2280.),g.num('Less',where,1785.)))
    watch=g.get('ShelterDoorWatch')
    watch_pos=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=watch))
    close=g.branch(g.num('Less',g.distance(player,watch_pos),420.))
    delta=g.subv(player,watch_pos)
    flat=g.vector(g.axis(delta,'X'),g.axis(delta,'Y'),0.)
    rot=g.math('MakeRotFromX',X=flat)
    current=g.out(g.call('Engine.SceneComponent.K2_GetComponentRotation',target=watch))
    turn=g.math('RInterpTo',Current=current,Target=rot,DeltaTime=.06,InterpSpeed=4.2)
    moved=g.do(g.call('Engine.SceneComponent.K2_SetWorldRotation',target=watch,NewRotation=turn,
                     bSweep=False,bTeleport=False))
    quiet=g.branch(g.num('GreaterEqual',g.now(),g.get('VisorRadioUntil')))
    link(close.find_else_pin(),quiet.find_execute_pin())
    entering=g.branch(g.both(g.near(ENTRY,465.),
                      g.both(g.compare('GreaterEqual',g.get('ShelterStep'),2),
                             g.not_(g.get('ShelterGreetingPlayed')))))
    g.set('ShelterGreetingPlayed',True)
    g.set('VisorRadioSource','ДЕЖУРНЫЙ · УБЕЖИЩЕ 07')
    publish_fields(g,'VisorRadio',{'text':'Сентинел? Проходи. Медик ждёт у дальней стены. Здесь ты в безопасности.'},6.3)
    g.cursor=entering.find_else_pin()
    g.branch(g.both(g.compare('GreaterEqual',g.get('SecondVoiceStep'),7),g.not_(g.get('ShelterHopePlayed'))))
    desk=g.get('ShelterStockKeeper')
    desk_point=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=desk))
    g.branch(g.num('Less',g.distance(player,desk_point),675.))
    g.set('ShelterHopePlayed',True)
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=desk,NewAnimToPlay='/Game/Characters/ShelterMedic/Animations/AN_Medic_NaturalRestored',bLooping=True))
    g.set('VisorRadioSource','КЛАДОВЩИЦА · УБЕЖИЩЕ 07')
    publish_fields(g,'VisorRadio',{'text':'Слышишь? Это другой район. Теперь сможем делиться запасами и искать тех, кто ещё жив.'},7.4)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    if not any(n.get_name()=='ShelterLivingUpdate' for n in graph.list_all_nodes()):
        hook(bp,graph.find_event_node('ReceiveTick').find_then_pin(),'ShelterLivingTick','ShelterLivingUpdate')

def arrival_fog(bp):
    g=Story(bp)
    original=next(n for n in g.e.list_all_nodes() if n.find_input_pin('BoxOrigin').is_valid() and n.find_input_pin('BoxExtent').is_valid())
    inside=original.find_output_pin('ReturnValue')
    position=original.find_input_pin('Point').list_connected_pins()[0]
    following=list(inside.list_connected_pins())
    if any(n.get_name()=='FogAtLabExit' for n in g.e.list_all_nodes()):
        return
    assert following
    x,y,z=(g.axis(position,axis) for axis in 'XYZ')
    courtyard=g.both(g.both(g.num('GreaterEqual',z,2195.),g.num('GreaterEqual',y,2448.)),
                     g.both(g.num('Less',y,23900.),
                            g.both(g.num('Greater',x,3100.),g.num('Less',x,9050.))))
    node=g.call('Engine.KismetMathLibrary.BooleanOR',A=inside,B=courtyard)
    node.rename('FogAtLabExit')
    for dest in following:
        old=list(dest.list_connected_pins())
        assert len(old)==1
        dest.break_pin_links()
        link(g.out(node),dest)
    fog=component(bp,'CityFog')
    fog.set_start_distance(370.)
    compile_bp(bp)

def laboratory(bp):
    metal=IND+'M_DistressedMetal'
    concrete=IND+'M_Concrete_Dirty'
    armor=IND+'M_DoorArmor'
    exit_amber='/Game/Surface/Materials/M_ExitAmber'
    def part(n,p,d,mat=metal,rot=None):
        return shape(bp,n,'SiteRoot',p,d,mat,rot=rot)
    treads=add(bp,unreal.InstancedStaticMeshComponent,'LabExitAntislipTreads','SiteRoot')
    treads.set_static_mesh(load('/Engine/BasicShapes/Cube'))
    treads.set_material(0,load('/Game/Surface/Materials/M_RuinSteel'))
    treads.set_collision_profile_name('NoCollision')
    treads.clear_instances()
    # Existing invisible collision ramps are authoritative.
    for index,(start,end,low,high) in enumerate(((460.,1860.,FLOOR,LANDING),(2020.,2445.,LANDING,GROUND))):
        slope=math.degrees(math.atan2(high-low,end-start))
        for side in (-1,1):
            part(f'StairRail{index}_{side}',(CENTER+side*145.,(start+end)*.5,(low+high)*.5+96.),
                 (math.hypot(end-start,high-low),4.6,5.2),metal,unreal.Rotator(pitch=slope,yaw=90.))
            for step in range(1,5 if index==0 else 3):
                fraction=step/(5 if index==0 else 3)
                y=start+fraction*(end-start)
                z=low+fraction*(high-low)
                part(f'StairPost{index}_{side}_{step}',(CENTER+side*145.,y,z+50.),(4.3,4.3,94.))
        count=40 if index==0 else 17
        for step in range(count):
            y=start+step*(end-start)/count
            z=low+(step+1)*(high-low)/count
            depth=(end-start)/count
            treads.add_instance(unreal.Transform(location=V(CENTER,y+depth*.5,z+.35),
                                scale=V(3.04,(depth-2.2)/100.,.008)),False)
            part(f'StairNosing{index}_{step}',(CENTER,y+1.9,z+.55),(291.,3.8,1.1),
                 armor if step%5 else exit_amber)
    part('ExitWestSill',(6173.,2472.,2173.),(64.,128.,46.),concrete)
    part('ExitEastSill',(6572.,2472.,2173.),(63.,125.,46.),concrete)
    part('ExitPier',(6642.,2341.,2240.),(82.,270.,191.),concrete,unreal.Rotator(pitch=-7.,roll=-9.))
    part('ExitHeaderRemainder',(6702.,2350.,2338.),(221.,40.,24.),concrete,unreal.Rotator(roll=-20.))
    compile_bp(bp)

def run():
    assert not ed.get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    mission,lab,grade=map(load,(MISSION,LAB_ROUTE,GRADE))
    for bp in (mission,lab,grade):
        assert bp.get_outermost() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    backup=PROJECT/'Saved/Backups/FieldSupplies'/datetime.now().strftime('%Y%m%d_%H%M%S')
    existing=tuple((path,'.uasset') for path in (*[ROOT+'/BP_Field'+row[0] for row in CACHE],ROOT+'/BP_FieldStreetDamage') if A.does_asset_exist(path))
    for asset,ext in ((MISSION,'.uasset'),(LAB_ROUTE,'.uasset'),(GRADE,'.uasset'),(CITY,'.umap'),*existing):
        path=Path('Content')/(asset[6:]+ext)
        target=backup/path
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PROJECT/path,target)
    component(mission,'PostIntercomLabel').set_text(unreal.Text('INTERCOM'))
    field_components(mission)
    field_logic(mission)
    shelter_people(mission)
    compile_bp(mission)
    arrival_fog(grade)
    laboratory(lab)
    stage_city()
    for bp in (mission, grade, lab):
        save(bp)
    report=PROJECT/'Saved/FieldSupplies'
    report.mkdir(exist_ok=True)
    (report/'Installed.json').write_text(json.dumps({'sites':CACHE,'backup':str(backup),
        'compiled':[MISSION,LAB_ROUTE,GRADE]},ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':
    run()
