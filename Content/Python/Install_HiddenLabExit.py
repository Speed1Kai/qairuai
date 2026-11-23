"""Replace the exposed upper lab with a buried equipment bay and concealed exit."""
from datetime import datetime
import json
import math
import shutil

import unreal

from Build_RuinedUrbanCampus import A, B, CUBE, GROUND, LEVEL, MAIN, OFFSET, V, actors, add, compile_bp, components, content, levels, save, saved, subtract
from CityCombat_Common import G, asset as blueprint, pin, var
from CityMachine_Logic import Logic
from Install_SurfaceHatch import Structure, asset
from SurfacePolish_Materials import import_file

ROOT = '/Game/Surface/HiddenExit'
BP = ROOT+'/BP_HiddenLabRoute'
SOURCE = content.parent/'SourceAssets'/'HiddenExit'
REPORT = saved/'HiddenExit'
LIFT = '/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional'
LABEL = 'LAB_HiddenExit'
FLOOR = 1150.
LANDING = 1805.
CENTER = 6375.
OPEN = (6212.,6538.,2004.,2485.)
LEVER = (6275.,1910.,1930.)
COVER = (CENTER,(OPEN[2]+OPEN[3])*.5,GROUND+.5)
SLIDE = 354.
MATS = {
    'iron':'/Game/LabTutorial/Industrial/M_DistressedMetal',
    'wall':'/Game/LabTutorial/Industrial/M_Concrete_Dirty',
    'armor':'/Game/LabTutorial/Industrial/M_DoorArmor',
    'steel':'/Game/Surface/Materials/M_RuinSteel',
    'oxide':'/Game/LabTutorial/Industrial/M_RustyIron',
    'dark':'/Game/LabTutorial/FirstFloor/M_LabGraphite',
    'amber':'/Game/Surface/Materials/M_ExitAmber',
    'ash':'/Game/Surface/RuinedCampus/Siege/M_Siege_BurnedGround',
    'chip':'/Game/Surface/RuinedCampus/Siege/M_Siege_BlastConcrete',
}
METAL = '/Game/LabTutorial/Industrial/'


def cover_mesh(world,mats):
    A.make_directory(ROOT)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    opt=unreal.FbxImportUI()
    opt.set_editor_property('automated_import_should_detect_type',False)
    opt.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
    opt.set_editor_property('import_materials',False)
    opt.set_editor_property('import_textures',False)
    opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    mesh=import_file(SOURCE/'SM_HiddenExit_ConcreteCover.fbx',ROOT,opt)
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,mats['ash' if str(slot.material_slot_name)=='Crust' else 'chip'])
    save(mesh)
    return mesh


def bay(s):
    # Five-sided shaft patches leave only the new upper gate aperture at Z=1150.
    for y0,y1 in ((-350,-179),(179,350)):
        s.box('iron',2960,3040,y0,y1,1136,1801)
    s.box('iron',2960,3040,-179,179,1572,2100)
    # Ground over the former lift opening. The new cabin stops well below it.
    s.box('chip',2245,3054,-384,384,2002,GROUND)
    # Buried equipment bay, then a narrower cable corridor turning north.
    s.box('iron',2996,5460,-505,521,FLOOR-32,FLOOR)
    s.box('wall',2996,5460,-505,521,1479,1535)
    s.box('wall',2996,5460,-505,-473,FLOOR,1479)
    s.box('wall',2996,5460,489,521,FLOOR,1479)
    for y0,y1 in ((-473,-179),(179,489)):
        s.box('wall',2996,3032,y0,y1,FLOOR,1479)
    for y0,y1 in ((-473,-215),(215,489)):
        s.box('wall',5420,5460,y0,y1,FLOOR,1479)
    s.box('iron',5420,6570,-215,216,FLOOR-31,FLOOR)
    s.box('wall',5420,6570,-215,216,1444,1501)
    s.box('wall',5420,6570,-215,-180,FLOOR,1444)
    s.box('wall',5420,6183,180,216,FLOOR,1444)
    s.box('wall',6537,6570,-180,462,FLOOR,1444)
    s.box('wall',6180,6212,216,462,FLOOR,1444)
    s.box('iron',6183,6570,216,466,FLOOR-28,FLOOR)
    s.box('wall',6183,6570,216,466,1444,1501)
    for x in (3220,3870,4610,5310):
        for y in (-455,450):
            s.box('steel',x-20,x+20,y-17,y+17,FLOOR,1479)
        s.box('steel',x-22,x+22,-453,450,1447,1479)
    for x in (3380,4070,4820):
        s.box('iron',x-161,x+161,-430,-258,FLOOR,FLOOR+94)
        s.box('armor',x-165,x+165,-430,-250,FLOOR+94,FLOOR+104)
        for xx in (-112,0,112):
            s.box('steel',x+xx-41,x+xx+41,-264,-251,FLOOR+26,FLOOR+82,solid=False)
        s.box('dark',x-122,x+114,-437,-368,FLOOR+106,FLOOR+164,solid=False)
        s.box('amber',x-87,x-58,-367,-364,FLOOR+134,FLOOR+139,solid=False)
    for x in (3670,4340,5050):
        s.box('armor',x-83,x+83,316,473,FLOOR,FLOOR+225)
        for z in (96,130,164,198):
            s.box('iron',x-63,x+63,310,317,FLOOR+z,FLOOR+z+5,solid=False)
    for x in (3100,3760,4410,5060,5610,6240):
        s.box('iron',x-170,x+170,-126,-116,1430,1451,solid=False)
        s.box('iron',x-170,x+170,-100,-89,1426,1448,solid=False)
    for x,y,z in ((3430,-260,1442),(4280,305,1442),(5210,-260,1442),(5960,-110,1419),(6420,330,1419)):
        s.box('steel',x-58,x+58,y-17,y+17,z,z+15,solid=False)
        s.box('amber',x-45,x+45,y-11,y+11,z-3,z,solid=False)


def stairs(s):
    def ramp(y0,y1,z0,z1):
        run,rise=y1-y0,z1-z0
        pitch=math.degrees(math.atan2(rise,run))
        length=math.hypot(run,rise)
        z=(z0+z1)*.5-6./math.cos(math.radians(pitch))
        s.place('WalkableStairRamps',CUBE,(CENTER,(y0+y1)*.5,z),
                (length/100.,3.25,.12),solid=True,yaw=90.,pitch=pitch)
        collision=s.batches['WalkableStairRamps']
        collision.set_visibility(False)
        collision.set_hidden_in_game(True)

    rise=(LANDING-FLOOR)/40.
    for i in range(40):
        y=460.+35.*i
        top=FLOOR+(i+1)*rise
        s.box('iron',6212,6538,y,y+35.15,top-25.,top,solid=False)
        if i%6==0:
            s.box('oxide',6222,6528,y+.5,y+3.,top,top+1.,solid=False)
    ramp(460.,1860.,FLOOR,LANDING)
    # Roof follows the lower stairs without reaching the yard.
    for i in range(0,40,5):
        y=460.+i*35.
        z=FLOOR+(i+5)*rise
        s.box('wall',6175,6575,y,y+175.3,z+272,z+302)
        if i:
            s.box('wall',6175,6575,y-1.,y+1.,z+272-5*rise,z+302)
        for a,b in ((6175,6212),(6538,6575)):
            s.box('wall',a,b,y,y+175.3,z-118,z+272)
    s.box('iron',6212,6538,1860,2020,LANDING-25,LANDING)
    s.box('wall',6175,6575,1860,2004,2077,2148)
    for i in range(17):
        y=2020.+25.*i
        z=LANDING+(i+1)*(GROUND-LANDING)/17.
        s.box('iron',6212,6538,y,y+25.15,z-25.,z,solid=False)
    ramp(2020.,2445.,LANDING,GROUND)
    s.box('chip',6212,6538,2445,2490,GROUND-34,GROUND)
    for a,b in ((6175,6212),(6538,6575)):
        s.box('wall',a,b,1860,2490,LANDING-70,2149)
    # Flush runners for the hidden slab. Hardware sits underneath the rubble line.
    s.box('iron',5850,6210,OPEN[2],OPEN[3],2136,2147)
    for y in (2016.,2473.):
        s.box('oxide',5845,6542,y-4,y+4,2145,2149,solid=False)
    s.box('armor',6216,6259,1870,1960,1841,2003,solid=False)
    s.box('oxide',6254,6291,1902,1920,1903,1971,solid=False)
    s.box('iron',6283,6311,1897,1925,1947,1969,solid=False)
    for y,z in ((650,1495),(1030,1690),(1415,1875),(1800,2080)):
        s.box('amber',6223,6231,y-15,y+15,z-6,z+6,solid=False)
    ruin='/Game/Surface/ServiceHatch/'
    s.place('BrokenCorner',asset(ruin+'SM_Hatch_WallLow'),(6590,2200,GROUND),
            (.91,1.15,.82),yaw=90.,solid=True)
    s.place('BrokenReturn',asset(ruin+'SM_Hatch_WallTall'),(6010,2010,GROUND),
            (.88,1.12,.57),yaw=180.,solid=True)
    debris='/Game/Environment/CityAftermath/SM_War_'
    for i,(x,y,yaw,k,q) in enumerate((
            (6005,2112,-22,'RippedSlabA',.64),(5910,2365,41,'RubblePile',1.04),
            (6020,2490,-74,'RippedSlabB',.77),(6670,2440,22,'RubblePile',1.02),
            (6535,1960,-9,'RippedSlabB',.62),(5900,1984,21,'RubblePile',.71))):
        s.place('BrokenYard'+str(i),asset(debris+k),(x,y,GROUND+2),(q,)*3,yaw=yaw)


def lid(bp,mesh,mats):
    pivot=add(bp,unreal.SceneComponent,'CoverSlide','SiteRoot')
    pivot.set_mobility(unreal.ComponentMobility.MOVABLE)
    pivot.set_editor_property('relative_location',V(COVER))
    length = OPEN[3]-OPEN[2]
    for name,model,p,scale,solid in (
            ('ConcreteSkin',mesh,(0,0,0),(1.,length/422.,1.),False),
            ('CoverCollision',CUBE,(0,0,-4.4),(3.27,length/100.,.089),True)):
        c=add(bp,unreal.StaticMeshComponent,name,'CoverSlide')
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(model)
        c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        c.set_editor_property('relative_location',V(p))
        c.set_editor_property('relative_scale3d',V(scale))
        if solid:
            c.set_visibility(False)
            c.set_hidden_in_game(True)


def graphs(bp):
    var(bp,'CoverReleased','bool','false')
    var(bp,'CoverAlpha','real','0')
    var(bp,'CampusStreaming',B.get_object_reference_type(unreal.LevelStreamingDynamic),'None')
    compile_bp(bp)

    g=Logic(bp,'PreloadYard')
    p=g.player()
    g.branch(g.valid(p))
    pos=g.position(p)
    check=g.branch(g.num('Greater',g.axis(pos,'Z'),865.))
    unload=check.find_else_pin()
    g.branch(g.math('Not_PreBool',A=g.valid(g.get('CampusStreaming'))))
    stream=g.do(g.call('Engine.LevelStreamingDynamic.LoadLevelInstance',LevelName=LEVEL,
        Location='(X=%f,Y=%f,Z=%f)'%OFFSET,Rotation='(Pitch=0,Yaw=0,Roll=0)',
        OptionalLevelNameOverride='ConnectedCampus',bLoadAsTempPackage=False))
    g.set('CampusStreaming',g.out(stream))
    g.cursor=unload
    g.branch(g.num('Less',g.axis(pos,'Z'),625.))
    g.branch(g.num('Less',g.axis(pos,'Y'),900.))
    g.branch(g.valid(g.get('CampusStreaming')))
    g.do(g.call('Engine.LevelStreaming.SetIsRequestingUnloadAndRemoval',
        target=g.get('CampusStreaming'),bInIsRequestingUnloadAndRemoval=True))
    g.set('CampusStreaming','None')
    compile_bp(bp)

    g=Logic(bp,'ReleaseCover')
    p=g.player()
    g.branch(g.valid(p))
    g.branch(g.math('Not_PreBool',A=g.get('CoverReleased')))
    g.branch(g.num('Less',g.distance(g.position(p),g.vector(*LEVER)),158.))
    g.branch(g.valid(g.get('CampusStreaming')))
    g.branch(g.out(g.call('Engine.LevelStreaming.IsLevelVisible',target=g.get('CampusStreaming'))))
    g.set('CoverReleased',True)
    g.sound(METAL+'S_BlastDoorHydraulicRelease',g.vector(*LEVER),.29)
    compile_bp(bp)

    g=Logic(bp,'UpdateCover')
    target=g.select(1.,0.,g.get('CoverReleased'),'Float')
    amount=g.get('CoverAlpha')
    update=g.branch(g.num('Greater',g.math('Abs',A=g.num('Subtract',amount,target)),.002))
    g.set('CoverAlpha',g.math('FInterpTo_Constant',Current=amount,Target=target,DeltaTime=g.dt(),InterpSpeed=.9))
    x=g.num('Subtract',COVER[0],g.num('Multiply',g.get('CoverAlpha'),SLIDE))
    z=g.num('Subtract',COVER[2],g.num('Multiply',g.get('CoverAlpha'),4.))
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('CoverSlide'),
        NewLocation=g.vector(x,COVER[1],z),bSweep=False,bTeleport=False))
    g.cursor=update.find_else_pin()
    g.branch(g.get('CoverReleased'))
    p=g.player()
    g.branch(g.valid(p))
    pos=g.position(p)
    g.branch(g.num('Greater',g.axis(pos,'Z'),2130.))
    g.branch(g.num('Greater',g.axis(pos,'Y'),3220.))
    g.set('CoverReleased',False)
    compile_bp(bp)

    g=Logic(bp)
    g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
    g.event_call('ReceiveTick','PreloadYard')
    g.do(g.own('UpdateCover'))
    key=g.node(g.e.create_node_from_name(next(n for n in g.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|F')),
                 unreal.Vector2D(),[]))
    key.set_editor_property('bConsumeInput',False)
    g.cursor=pin(key,'Pressed',True)
    g.do(g.own('ReleaseCover'))
    compile_bp(bp)
    cdo=unreal.get_default_object(B.generated_class(bp))
    cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)


def prepare(world):
    mats={k:asset(v) for k,v in MATS.items()}
    bp=blueprint(BP)
    s=Structure(bp,mats)
    bay(s)
    stairs(s)
    lid(bp,cover_mesh(world,mats),mats)
    graphs(bp)
    save(bp)
    return B.generated_class(bp)

def retire_exposed_campus_int(world):
    assert world.get_path_name().split('.')[0]==LEVEL
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    retired=0
    interior=scene['INT_AllCampusBuildings']
    interior.modify()

    def former_a(p):
        return p.z>=2110. and ((2920.<p.x<6470. and -390.<p.y<980.)
                              or (6490.<p.x<7490. and 205.<p.y<990.))

    for c in interior.get_components_by_class(unreal.InstancedStaticMeshComponent):
        remove=[]
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,True)
            if t and former_a(t.translation+V(OFFSET)):
                remove.append(i)
        if remove:
            c.modify()
            for i in reversed(remove):
                assert c.remove_instance(i)
                retired+=1
    for label,a in scene.items():
        if label=='REF_Sign_00' or (label.startswith(('INT_Light_','INT_Sign_')) and former_a(a.get_actor_location()+V(OFFSET))):
            assert actors.destroy_actor(a)
    return retired


def cut_yard_slot(world):
    assert world.get_path_name().split('.')[0]==LEVEL
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    cut={}
    for label in ('REF_LaboratoryComplex','RUIN_Exterior','SIEGE_Battlefield'):
        actor=scene[label]
        actor.modify()
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if not mesh:
                continue
            altered=[]
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True)
                if not t:
                    continue
                p=t.translation+V(OFFSET)
                if not 2020.<p.z<2300.:
                    continue
                if mesh.get_name()!='Cube':
                    if label=='SIEGE_Battlefield' and c.get_name() in ('CollapsedConcrete','ScatteredMasonry','HangingConcrete'):
                        if OPEN[0]-30<p.x<OPEN[1]+30 and OPEN[2]-20<p.y<OPEN[3]+55:
                            altered.append((i,[],t))
                    continue
                r=t.rotation.rotator()
                if abs(r.pitch)>.1 or abs(r.roll)>.1 or abs(math.sin(math.radians(2*r.yaw)))>.02:
                    continue
                dims=(abs(t.scale3d.x)*50.,abs(t.scale3d.y)*50.)
                if abs(round(r.yaw/90.))%2:
                    dims=dims[::-1]
                hx,hy=dims
                if min(hx,hy)<10.:
                    continue
                rect=(p.x-hx,p.x+hx,p.y-hy,p.y+hy)
                blocks=subtract(rect,OPEN)
                if blocks!=[rect]:
                    altered.append((i,blocks,t))
            if not altered:
                continue
            c.modify()
            for i,_,_ in reversed(altered):
                assert c.remove_instance(i)
            for _,pieces,t in altered:
                for x0,x1,y0,y1 in pieces:
                    p=V(((x0+x1)*.5,(y0+y1)*.5,t.translation.z+OFFSET[2]))-V(OFFSET)
                    c.add_instance(unreal.Transform(location=p,scale=V(((x1-x0)/100.,(y1-y0)/100.,t.scale3d.z))),True)
            cut[label+'/'+c.get_name()]=len(altered)
    return cut


def adapt_lift(lift_actor):
    bp=asset(LIFT)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    constants=0
    for n in graph.list_all_nodes():
        title=str(n.get_node_title())
        for name,old,new,expected in (('Z',2150.,FLOOR,'MakeVector'),('B',2126.,FLOOR-24.,'SelectFloat')):
            if title!=expected:
                continue
            p=n.find_input_pin(name)
            if p.is_valid() and str(p.get_pin_value()) in (str(old),str(int(old))):
                assert p.set_pin_value(str(int(new)))
                constants+=1
    moved={}
    for _,c,name in components(bp):
        if not c or not name.startswith('Upper') or not isinstance(c,unreal.SceneComponent):
            continue
        p=c.get_editor_property('relative_location')
        if p.z>1900.:
            c.modify()
            p.z-=2150.-FLOOR
            c.set_editor_property('relative_location',p)
            moved[name]=p
    assert constants in (0,10) and (len(moved)>=9 or constants==0),(constants,list(moved))
    compile_bp(bp)
    save(bp)
    lift_actor.modify()
    for c in lift_actor.get_components_by_class(unreal.SceneComponent):
        if c.get_name() in moved:
            c.modify()
            c.set_relative_location(moved[c.get_name()],False,False)
    return constants,len(moved)


def move_upper_focus(scene):
    marker=scene.get('FOCUS_LAB_FreightElevator_FocusUpperButton')
    assert marker
    p=marker.get_actor_location()
    marker.modify()
    p.z=FLOOR+150.
    assert marker.set_actor_location(p,False,True)


def reconnect_bunker_lights(scene):
    power=scene['BASE_MainPowerSwitch']
    bp=asset('/Game/LabTutorial/Basement/BP_BuildingPower')
    lamps=[a for label,a in sorted(scene.items()) if label.startswith(LABEL+'_Lamp_')]
    missing=[str(n) for n in B.list_member_variable_names(bp)
             if str(n).startswith('CircuitLight_') and not power.get_editor_property(str(n))]
    assert lamps
    power.modify()
    for i,name in enumerate(missing):
        power.set_editor_property(name,lamps[i%len(lamps)])
    return len(missing)


def place_route(cls):
    prior=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL),None)
    if prior:
        assert actors.destroy_actor(prior)
    route=actors.spawn_actor_from_class(cls,V((0,0,0)))
    assert route
    route.set_actor_label(LABEL)
    route.set_folder_path('LAB/Hidden Service Exit')
    return route


def rebuild_main(world,cls):
    assert world.get_path_name().split('.')[0]==MAIN
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    lift=scene['LAB_FreightElevator']
    constants,moved=adapt_lift(lift)
    move_upper_focus(scene)
    wall=scene['LAB_Shaft_Wall_East_Lower']
    wall.modify()
    assert actors.set_actor_transform(wall,unreal.Transform(location=V((3000,0,568)),scale=V((.80,7.,11.36))))
    removed=[]
    for label,a in scene.items():
        if label.startswith(('F01_','LAB_SurfaceHatch',LABEL)) or label in ('SURFACE_Departure','SURFACE_DepartureIndicator'):
            assert actors.destroy_actor(a),label
            removed.append(label)
    for c in scene['PLAN01_Layout'].get_components_by_class(unreal.InstancedStaticMeshComponent):
        for i in range(c.get_instance_count()-1,-1,-1):
            t=c.get_instance_transform(i,True)
            if t and 2890.<t.translation.x<6400. and -900.<t.translation.y<1500. and t.translation.z>=2150.:
                c.modify()
                c.remove_instance(i)
    place_route(cls)
    for i,p in enumerate(((3440,-245,1418),(4320,258,1418),(5160,-250,1420),
                        (5860,40,1380),(6390,610,1400),(6420,1225,1655),(6275,1840,2088))):
        lamp=actors.spawn_actor_from_class(unreal.PointLight,V(p))
        lamp.set_actor_label(LABEL+'_Lamp_'+str(i))
        lamp.set_folder_path('LAB/Hidden Service Exit')
        c=lamp.point_light_component
        c.set_intensity(570. if i<4 else 310.)
        c.set_light_color(unreal.LinearColor(1.,.73,.48,1.))
        c.set_attenuation_radius(470. if i<4 else 270.)
        c.set_cast_shadows(False)
    for i,(text,p,yaw,size) in enumerate((
            ('ТЕХОТСЕК / 02',(3043.,136.,1371.),0.,20.),
            ('СЛУЖЕБНЫЙ ХОД',(5430.,245.,1378.),180.,20.),
            ('[F]  СНЯТЬ ЗАСОВ',(6230.,1918.,1967.),0.,15.))):
        sign=actors.spawn_actor_from_class(unreal.TextRenderActor,V(p),unreal.Rotator(yaw=yaw))
        sign.set_actor_label(LABEL+'_Plate_'+str(i))
        sign.set_folder_path('LAB/Hidden Service Exit')
        t=sign.text_render
        t.set_text(unreal.Text(text))
        t.set_world_size(size)
        t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        t.set_text_render_color(unreal.Color(191,166,125,255))
        t.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    power=reconnect_bunker_lights({a.get_actor_label():a for a in actors.get_all_level_actors()})
    return dict(constants=constants,upper_components=moved,retired_actors=removed,light_bindings=power)


def backup():
    folder=saved/'Backups'/'HiddenLabExit'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder.mkdir(parents=True)
    for p,ext in ((MAIN,'.umap'),(LEVEL,'.umap'),(LIFT,'.uasset')):
        rel=p.removeprefix('/Game/')+ext
        dest=folder/rel
        dest.parent.mkdir(exist_ok=True,parents=True)
        shutil.copy2(content/rel,dest)
    return folder
