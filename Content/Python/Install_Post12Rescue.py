"""Continue the existing evacuation chapter through the service gate at Post 12."""
from datetime import datetime
import json
import math
from pathlib import Path
import shutil

import unreal

from CityCombat_Common import A, B, G, add, compile_bp, hook, link, save, val, var
from Install_StoryMemory import L, MISSION, PROJECT, Story, insert_entry, load
from Install_DemoCheckpoint import finish_restore
from Install_EvacuationRelay import (
    ARMOR, DARK, GREEN, LEADS, RED, STEEL, checkpoint_graphs, down, focus, guide_graphs,
    phase, sound,
)
from Install_VisorSubtitles import publish_fields

ROOT = '/Game/Story/Post12'
SOURCE_WALK = '/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd'
MANNY = '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
MAN = '/Game/Characters/ShelterResident/SK_S07_Resident'
MAN_IDLE = '/Game/Characters/ShelterResident/Animations/AN_S07_Resident_Idle'
WOMAN = '/Game/Characters/ShelterMedic/SK_S07_Medic'
WOMAN_IDLE = '/Game/Characters/ShelterMedic/Animations/AN_Medic_NaturalRest'
WOMAN_WALK = '/Game/Characters/ShelterMedic/Animations/AN_Medic_MF_Unarmed_Walk_Fwd'
AMBER = LEADS[1][-1]
CONCRETE = '/Game/LabTutorial/Industrial/M_Concrete_Dirty'
FLOOR = '/Game/Surface/Materials/CampusPaving/M_CampusConcreteSlabs'
SITE = (32480, 84690, 2169)
YAW = 0.
GATE_RISE = 246.
STAGES = {'arrive':7, 'find':9, 'mount':10, 'lift':11, 'lead':12, 'done':13}
DIALOGUE = {
    'Meet': ('ПОСТ 12 · ДЕЖУРНЫЙ', 'Нас трое. Противовес сняли при эвакуации. На табличке указан вес. В запасе у стены осталось два груза.'),
    'Mounted': ('ПОСТ 12 · ДЕЖУРНЫЙ', 'Груз сел на крюк. Теперь тяни за рукоять. Поднимешь решётку до упора — защёлка её удержит.'),
    'Open': ('ПОСТ 12 · ДЕЖУРНЫЙ', 'Проход открыт. Выйди к фонарю, мы за тобой.'),
    'Safe': ('ПОСТ 12 · ДЕЖУРНЫЙ', 'Все трое вышли. Спасибо. Вода пропала после того, как Атлас перекрыл насосную. Ниже по улице ещё есть люди.'),
    'Radio': ('[РАДИОСИГНАЛ] РАДИСТ · УБЕЖИЩЕ 07', 'Принял: трое в безопасности. Медик уже ждёт. Проверим насосную — от неё зависит не только пост двенадцать.'),
}


def location(x=0., y=0., z=0.):
    """Keep the service bay geometry and interactions in the same local frame."""
    angle = math.radians(YAW)
    return (round(SITE[0]+x*math.cos(angle)-y*math.sin(angle),3),
            round(SITE[1]+x*math.sin(angle)+y*math.cos(angle),3), SITE[2]+z)


MEET = location(0,-43,166)
MEET_REACH = 335.
MEET_AIM = 108.
LIGHT = location(136,-385,90)
RACK = location(145,-163,106)
WRONG = location(228,-163,106)
HOOK = location(154,-33,123)
CRANK = location(149,-43,174)
SAFE = location(108,-327,92)
APPROACH = location(20,-232,92)


def walkers():
    # Three separate lanes through the gate leave room for the player at the rally light.
    return (
        ('Watch', MAN, MAN_IDLE, 0., 1.0, (0,244,0), (-8,-36,0), (0,-331,0), 118.),
        ('Passenger', WOMAN, WOMAN_IDLE, 0., .97, (-93,311,0), (-83,-60,0), (-84,-364,0), 112.),
        ('Worker', MAN, MAN_IDLE, 0., 1.045, (83,381,0), (79,-58,0), (78,-397,0), 122.),
    )


def asset(name, cls, factory):
    path = ROOT+'/'+name
    if A.does_asset_exist(path):
        return load(path)
    A.make_directory(ROOT)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT, cls, factory())


def resident_walk():
    existing = ROOT+'/Post12_MF_Unarmed_Walk_Fwd'
    if A.does_asset_exist(existing):
        return load(existing)
    source, target = load(MANNY), load(MAN)
    rigs = {}
    for key, mesh in (('Source',source),('Resident',target)):
        rig = asset('IK_Post12'+key, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory)
        controller = unreal.IKRigController.get_controller(rig)
        assert controller.set_skeletal_mesh(mesh)
        if not controller.get_retarget_chains():
            assert controller.apply_auto_generated_retarget_definition(), key
        save(rig)
        rigs[key] = rig
    retarget = asset('RTG_Post12Resident', unreal.IKRetargeter, unreal.IKRetargetFactory)
    ctrl = unreal.IKRetargeterController.get_controller(retarget)
    ctrl.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, rigs['Source'])
    ctrl.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, rigs['Resident'])
    ctrl.add_default_ops()
    ctrl.auto_map_chains(unreal.AutoMapChainType.EXACT, True)
    ctrl.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET, unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)
    save(retarget)
    request = unreal.IKRetargetBatchOperationInputs()
    for name,value in dict(assets_to_retarget=[A.find_asset_data(load(SOURCE_WALK).get_path_name())],
                           source_mesh=source,target_mesh=target,ik_retarget_asset=retarget,prefix='Post12_',
                           target_path=ROOT,include_referenced_assets=False,overwrite_existing_files=False).items():
        request.set_editor_property(name,value)
    result = [entry.get_asset() for entry in unreal.IKRetargetBatchOperation.run_batch_retarget(request)]
    walk = next((anim for anim in result if isinstance(anim,unreal.AnimSequence)),None)
    assert walk and walk.get_editor_property('skeleton') == target.skeleton, result
    save(walk)
    return walk


def make_hardware(bp):
    V = unreal.Vector
    def spatial(name,cls,xy,rotation=0,parent='PostSite'):
        c=add(bp,cls,'Post'+name,parent)
        c.set_editor_property('relative_location',V(*xy))
        c.set_editor_property('relative_rotation',unreal.Rotator(yaw=rotation))
        return c

    site=spatial('Site',unreal.SceneComponent,SITE,YAW,'Root')
    site.set_mobility(unreal.ComponentMobility.MOVABLE)
    cube=load('/Engine/BasicShapes/Cube')
    cylinder=load('/Engine/BasicShapes/Cylinder')
    def solid(name,xy,size,mat,mesh=cube,parent='PostSite',rotation=0):
        c=spatial(name,unreal.StaticMeshComponent,xy,rotation,parent)
        c.set_static_mesh(mesh)
        c.set_material(0,load(mat))
        c.set_editor_property('relative_scale3d',V(*(d/100. for d in size)))
        c.set_collision_profile_name('NoCollision')
        c.set_custom_depth_stencil_value(253)
        return c
    def box(name,xy,size,parent='PostSite'):
        c=spatial(name,unreal.BoxComponent,xy,parent=parent)
        c.set_box_extent(V(*(d/2 for d in size)),False)
        c.set_collision_profile_name('BlockAll')
        c.set_editor_property('generate_overlap_events',False)
        c.set_editor_property('can_ever_affect_navigation',False)
        return c
    def sign(name,text,xy,size):
        t=spatial(name,unreal.TextRenderComponent,xy,-90.)
        t.set_text(unreal.Text(text))
        t.set_world_size(size)
        t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        t.set_text_render_color(unreal.Color(232,228,195,255))
        return t
    def lamp(name,xy,rgb,intensity,radius):
        p=spatial(name,unreal.PointLightComponent,xy)
        p.set_mobility(unreal.ComponentMobility.MOVABLE)
        p.set_cast_shadows(False)
        p.set_intensity(intensity)
        p.set_attenuation_radius(radius)
        p.set_light_color(unreal.LinearColor(*rgb,1.))
        p.set_editor_property('volumetric_scattering_intensity',0.)
        return p

    spatial('Gate',unreal.SceneComponent,(0,0,0))
    box('GateBlock',(0,0,124),(272,12,248),'PostGate')
    for y in (0,-8):
        for z in (9,129,242):
            solid(f'GateRail{y+8}_{z}',(0,y,z),(267,6,9),STEEL,parent='PostGate')
    for i,x in enumerate(range(-125,126,25)):
        solid(f'GateBar{i}',(x,0,123),(5,7,238),ARMOR,parent='PostGate')
    for x in (-142.,142.):
        solid('Column'+str(int(x)),(x,0,138),(19,28,276),STEEL)
        box('ColumnBox'+str(int(x)),(x,0,130),(18,32,260))
        solid('Track'+str(int(x)),(x,9,230),(9,7,457),DARK)
    solid('Header',(0,-10,270),(315,31,23),STEEL)
    solid('HeaderBacking',(0,-28,270),(131,4,21),DARK)
    solid('IntercomPlate',(0,-29,170),(118,7,26),DARK)
    sign('IntercomLabel','INTERCOM',(0,-35,170),11.)
    solid('IntercomLamp',(-52,-35,170),(4,3,6),AMBER)
    sign('HeaderLabel','TRANSIT  /  POST 12',(0,-31,270),12.)
    for side in (-1,1):
        x=side*169.
        solid('Wing'+str(side),(x,109,105),(12,230,210),CONCRETE)
        box('WingBox'+str(side),(x,109,105),(12,230,210))
        solid('RearWing'+str(side),(x,340,116),(12,238,232),CONCRETE)
        box('RearWingBox'+str(side),(x,340,116),(12,238,232))
    solid('RearFacade',(0,462,136),(346,18,272),CONCRETE)
    box('RearBox',(0,462,136),(346,18,272))
    for x in (-155,155):
        solid('RearColumn'+str(x),(x,448,127),(15,14,254),STEEL)
    solid('CounterweightRack',(186,-159,81),(125,29,91),STEEL)
    solid('RackShelf',(186,-162,82),(120,46,11),DARK)
    solid('Weight',(145,-163,106),(35,27,40),STEEL,cylinder)
    solid('LightWeight',(228,-163,106),(26,24,31),ARMOR,cylinder)
    sign('WeightLabel','40',(145,-183,97),9.)
    sign('LightWeightLabel','20',(228,-181,97),9.)
    solid('FittedWeight',(154,-28,100),(35,27,40),STEEL,cylinder).set_visibility(False,False)
    solid('WeightCable',(154,-21,178),(3,3,159),STEEL,cylinder).set_visibility(False,False)
    solid('Hook',(154,-23,123),(18,15,14),AMBER)
    solid('DriveHousing',(153,-17,170),(31,17,103),ARMOR)
    solid('DrivePlate',(155,-31,206),(50,4,14),DARK)
    sign('DriveLabel','40 KG',(155,-34,206),8.)
    solid('CrankHub',(149,-36,174),(24,20,24),STEEL)
    spatial('Crank',unreal.SceneComponent,(149,-43,174))
    solid('CrankArm',(0,0,8),(5,7,22),AMBER,parent='PostCrank')
    solid('CrankGrip',(0,-7,20),(10,17,10),DARK,parent='PostCrank')
    solid('GateStatus',(117,-18,257),(16,5,6),RED)
    solid('PickupPole',(136,-385,107),(11,11,211),STEEL)
    solid('PickupShade',(136,-385,222),(44,35,8),DARK)
    solid('PickupGlass',(136,-385,216),(37,27,3),AMBER)
    lamp('PickupLight',(136,-385,208),(1.,.79,.51),820.,260.)
    lamp('GateLight',(0,-52,254),(.82,.89,1.),650.,325.)
    lamp('InteriorLight',(15,265,273),(1.,.78,.54),740.,355.)
    lamp('ShelterFill',(5,145,195),(1.,.84,.70),360.,345.)
    solid('Cover',(0,261,292),(337,236,16),ARMOR)
    for i, (x,y,z) in enumerate(((-132,337,23),(115,423,23),(-131,388,23))):
        solid(f'Supply{i}',(x,y,z),(52,54,44),STEEL)
        solid(f'SupplyHandle{i}',(x,y-28,z+9),(19,6,4),DARK)

    carried=solid('Carry',(0,0,0),(21,17,25),STEEL,cylinder)
    carried.set_visibility(False,False)
    for i,(role,mesh,idle,rotation,scale,start,_,_,_) in enumerate(walkers()):
        person=spatial('Walker'+str(i),unreal.SkeletalMeshComponent,start,rotation)
        person.set_skeletal_mesh_asset(load(mesh))
        person.set_collision_profile_name('NoCollision')
        person.set_editor_property('relative_scale3d',V(scale,scale,scale))
        person.override_animation_data(load(idle),True,True,float(i)*.7,.91+i*.06)
        if i==2:
            # The other male model has a different jacket material and silhouette.
            jacket=person.get_material_index('Jacket_Mat')
            if jacket<0:
                jacket=person.get_material_index('Jacket')
            if jacket>=0:
                person.set_material(jacket,load('/Game/Characters/ShelterResident/Materials/M_S07_Backpack'))
    compile_bp(bp)


def actor_component(g,name):
    return g.get('Post'+name)


def visibility(g,name,show):
    g.visibility('Post'+name,show)


def depth(g,name,show):
    g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=actor_component(g,name),bValue=show))


def status(g,mat):
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=actor_component(g,'GateStatus'),ElementIndex=0,Material=mat))


def say(g,name,duration):
    speaker,message=DIALOGUE[name]
    g.set('VisorRadioSource',speaker)
    publish_fields(g,'VisorRadio',{'text':message},duration)
    sound(g,MEET)


def world(g,name):
    return g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=actor_component(g,name)))


def set_world(g,name,pos):
    g.do(g.call('Engine.SceneComponent.K2_SetWorldLocation',target=actor_component(g,name),
                NewLocation=pos,bSweep=False,bTeleport=True))


def set_local(g,name,pos):
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=actor_component(g,name),
                NewLocation=pos,bSweep=False,bTeleport=True))


def rotate(g,name,rot,local=False):
    direction='Relative' if local else 'World'
    g.do(g.call('Engine.SceneComponent.K2_Set'+direction+'Rotation',target=actor_component(g,name),
                NewRotation=rot,bSweep=False,bTeleport=True))


def animation(g,i,asset_path,rate=1.):
    body=actor_component(g,'Walker'+str(i))
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=body,NewAnimToPlay=asset_path,bLooping=True))
    g.do(g.call('Engine.SkeletalMeshComponent.SetPlayRate',target=body,Rate=rate))


def on_phase(g,k):
    return phase(g,STAGES[k])


def mounting(g):
    visibility(g,'Carry',False)
    visibility(g,'Weight',False)
    visibility(g,'WeightLabel',False)
    visibility(g,'FittedWeight',True)
    visibility(g,'WeightCable',True)
    depth(g,'Hook',False)


def height(g,fraction):
    lift=g.math('Multiply_DoubleDouble',A=fraction,B=GATE_RISE)
    set_local(g,'Gate',g.vector(0.,0.,lift))
    rotor=g.math('Multiply_DoubleDouble',A=fraction,B=560.)
    rotate(g,'Crank',g.math('MakeRotator',Pitch=rotor,Yaw=0.,Roll=0.),True)
    weight=g.math('Subtract_DoubleDouble',A=100.,B=g.math('Multiply_DoubleDouble',A=fraction,B=48.))
    set_local(g,'FittedWeight',g.vector(154.,-28.,weight))
    attachment=g.math('Add_DoubleDouble',A=weight,B=20.)
    center=g.math('Lerp',A=attachment,B=256.,Alpha=.5)
    set_local(g,'WeightCable',g.vector(154.,-28.,center))
    length=g.math('Subtract_DoubleDouble',A=256.,B=attachment)
    g.do(g.call('Engine.SceneComponent.SetRelativeScale3D',target=actor_component(g,'WeightCable'),
                NewScale3D=g.vector(.03,.03,g.math('Divide_DoubleDouble',A=length,B=100.))))


def setup_graphs(bp,male_walk):
    g=Story(bp,'Post12Restore')
    milestone=g.get('EvacuationMilestone')
    g.branch(g.compare('GreaterEqual',milestone,4))
    mounting(g)
    g.set('Post12Lift',1.)
    height(g,g.get('Post12Lift'))
    status(g,GREEN)
    done=g.branch(g.compare('EqualEqual',milestone,5))
    for i,(_,_,idle,_,_,_,_,end,_) in enumerate(walkers()):
        set_world(g,'Walker'+str(i),L(location(*end)))
        animation(g,i,idle)
        g.set('Post12Walk'+str(i),3)
    g.set('Post12Escorting',True)
    g.set('EvacuationStage',STAGES['done'])
    finish_restore(g,L(location(37,-286,92)),YAW-90.)
    g.cursor=done.find_else_pin()
    g.set('EvacuationStage',STAGES['lead'])
    finish_restore(g,L(APPROACH),YAW+90.)

    for i,(_,_,idle,_,_,_,way,end,speed) in enumerate(walkers()):
        g=Story(bp,'Post12Move'+str(i))
        name='Walker'+str(i)
        state='Post12Walk'+str(i)
        begun=g.branch(g.compare('EqualEqual',g.get(state),0))
        g.branch(g.num('GreaterEqual',g.now(),g.math('Add_DoubleDouble',A=g.get('Post12EscortAt'),B=i*.56)))
        animation(g,i,WOMAN_WALK if i==1 else male_walk,.77+i*.04)
        g.set(state,1)
        g.cursor=begun.find_else_pin()
        g.branch(g.compare('Less',g.get(state),3))
        first=g.compare('EqualEqual',g.get(state),1)
        goal=g.select(L(location(*way)),L(location(*end)),first)
        current=world(g,name)
        distance=g.distance(current,goal)
        reached=g.branch(g.num('Less',distance,9.))
        set_world(g,name,goal)
        g.set(state,g.math('Add_IntInt',A=g.get(state),B=1))
        g.branch(g.compare('EqualEqual',g.get(state),3))
        animation(g,i,idle)
        g.cursor=reached.find_else_pin()
        facing=g.math('FindLookAtRotation',Start=current,Target=goal)
        yaw=g.out(g.call('Engine.KismetMathLibrary.BreakRotator',InRot=facing),'Yaw')
        rotate(g,name,g.math('MakeRotator',Pitch=0.,Yaw=yaw,Roll=0.))
        moved=g.math('VInterpTo_Constant',Current=current,Target=goal,DeltaTime=g.get('Post12WalkDelta'),InterpSpeed=speed)
        set_world(g,name,moved)

    g=Story(bp,'Post12LiftTick')
    g.branch(g.get('Post12Cranking'))
    g.do(g.own('EvacFocusPostCrank'))
    holds=g.branch(g.both(down(g),g.get('EvacFocus')))
    elapsed=g.num('Subtract',g.now(),g.get('Post12LastCrank'))
    value=g.num('Add',g.get('Post12LiftStart'),g.num('Divide',elapsed,2.7))
    g.set('Post12Lift',g.math('FClamp',Value=value,Min=0.,Max=1.))
    height(g,g.get('Post12Lift'))
    g.branch(g.num('GreaterEqual',g.get('Post12Lift'),1.))
    g.set('Post12Cranking',False)
    g.set('EvacFHeld',False)
    g.set('EvacuationStage',STAGES['lead'])
    depth(g,'CrankGrip',False)
    status(g,GREEN)
    say(g,'Open',5.5)
    g.set('EvacuationMilestone',4)
    g.do(g.own('EvacSave'))
    g.cursor=holds.find_else_pin()
    g.set('Post12Cranking',False)

    g=Story(bp,'Post12EscortTick')
    ready=g.branch(g.get('Post12Escorting'))
    g.cursor=ready.find_else_pin()
    check=g.branch(g.near(SAFE,200.))
    g.set('Post12Escorting',True)
    g.set('Post12EscortAt',g.now())
    g.set('Post12LastWalk',g.now())
    g.cursor=ready.find_then_pin()
    g.set('Post12WalkDelta',g.math('FClamp',Value=g.num('Subtract',g.now(),g.get('Post12LastWalk')),Min=0.,Max=.65))
    g.set('Post12LastWalk',g.now())
    for i in range(3):
        g.do(g.own('Post12Move'+str(i)))
    all_here=g.both(g.compare('EqualEqual',g.get('Post12Walk0'),3),
                     g.both(g.compare('EqualEqual',g.get('Post12Walk1'),3),g.compare('EqualEqual',g.get('Post12Walk2'),3)))
    g.branch(all_here)
    g.set('EvacuationStage',STAGES['done'])
    say(g,'Safe',10.)
    g.set('Post12RadioAt',g.math('Add_DoubleDouble',A=g.now(),B=10.25))
    g.set('EvacuationMilestone',5)
    g.do(g.own('EvacSave'))


def use_graph(bp):
    g=Story(bp,'Post12Use')
    for key,focus_key in (('arrive','Meet'),('find','Weight'),('mount','Hook'),('lift','Crank')):
        gate=g.branch(on_phase(g,key))
        g.do(g.own('EvacFocusPost'+focus_key))
        active=g.branch(g.get('EvacFocus'))
        if key=='arrive':
            say(g,'Meet',10.)
            depth(g,'Weight',True)
            g.set('EvacuationStage',STAGES['find'])
        elif key=='find':
            visibility(g,'Weight',False)
            visibility(g,'WeightLabel',False)
            depth(g,'Weight',False)
            depth(g,'Hook',True)
            carry=actor_component(g,'Carry')
            # Use the first-person camera, as the weapon mounting code does.
            camera=g.ext(g.get('Player'),'FirstPersonCamera')
            g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=carry,Parent=camera,
                        SocketName='None',LocationRule='KeepRelative',RotationRule='KeepRelative',
                        ScaleRule='KeepWorld',bWeldSimulatedBodies=False))
            set_local(g,'Carry',L((75,32,-24)))
            visibility(g,'Carry',True)
            sound(g,RACK)
            g.set('EvacuationStage',STAGES['mount'])
            g.cursor=active.find_else_pin()
            g.do(g.own('EvacFocusPostWrong'))
            g.branch(g.get('EvacFocus'))
            g.set('Post12WrongAt',g.math('Add_DoubleDouble',A=g.now(),B=3.4))
        elif key=='mount':
            mounting(g)
            depth(g,'CrankGrip',True)
            sound(g,HOOK)
            say(g,'Mounted',7.)
            g.set('EvacuationStage',STAGES['lift'])
        else:
            # The shared F handler may run repeatedly while the key is held.
            g.branch(g.not_(g.get('Post12Cranking')))
            g.set('EvacFHeld',True)
            g.set('Post12LiftStart',g.get('Post12Lift'))
            g.set('Post12LastCrank',g.now())
            g.set('Post12Cranking',True)
        g.cursor=gate.find_else_pin()


def objectives(bp):
    g=Story(bp,'Post12Tick')
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('StoryHUD'),
                PropertyName='ShelterChapter',Value='СПИСОК ОСТАВШИХСЯ'))
    guide=(
        ('arrive',MEET,'Пост 12 · подойди к решётке под вывеской TRANSIT / POST 12'),
        ('find',RACK,'Проверь табличку у рукояти и возьми нужный противовес'),
        ('mount',HOOK,'F · повесить противовес на крюк привода'),
        ('lift',CRANK,'Удерживай F у рукояти, пока решётка не поднимется до упора'),
        ('lead',SAFE,'Дойди до фонаря у выхода и дождись всех троих'),
    )
    for key, point, prompt in guide:
        state=g.branch(on_phase(g,key))
        if key=='arrive':
            g.do(g.own('EvacFocusPostMeet'))
            prompt=g.select('Наведи прицел на табличку INTERCOM посреди решётки',
                            prompt,g.near(MEET,410.),'String')
            prompt=g.select('F · поговорить с дежурным через решётку',
                            prompt,g.get('EvacFocus'),'String')
        if key=='find':
            wrong=g.num('Greater',g.get('Post12WrongAt'),g.now())
            prompt=g.math('SelectString',A='Груз 20 кг слишком лёгкий. Для привода нужен груз 40 кг.',B=prompt,bPickA=wrong)
        if key=='lift':
            g.do(g.own('Post12LiftTick'))
        if key=='lead':
            g.do(g.own('Post12EscortTick'))
        g.goal(prompt,point)
        g.cursor=state.find_else_pin()
    g.branch(on_phase(g,'done'))
    g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.12))
    g.set('Objective','Список оставшихся · трое выведены')
    g.pset('StoryGoalActive',False,'Bool')
    g.branch(g.num('Greater',g.get('Post12RadioAt'),0.))
    g.branch(g.num('GreaterEqual',g.now(),g.get('Post12RadioAt')))
    g.set('Post12RadioAt',0.)
    say(g,'Radio',10.)


def hooks(bp):
    start=Story(bp,'Post12MaybeStart')
    start.branch(phase(start,6))
    start.branch(start.num('LessEqual',start.get('EvacReplyAt'),0.))
    start.set('EvacuationStage',STAGES['arrive'])
    start.do(start.call('Engine.Actor.SetActorTickInterval',TickInterval=.055))

    tick=Story(bp,'Post12WorldTick')
    tick.branch(tick.valid(tick.get('Player')))
    tick.branch(tick.isstage(6))
    tick.branch(tick.not_(tick.get('Failed')))
    tick.do(tick.own('Post12MaybeStart'))
    tick.branch(tick.compare('GreaterEqual',tick.get('EvacuationStage'),STAGES['arrive']))
    tick.do(tick.own('Post12Tick'))

    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    if not any(n.get_name()=='Post12WorldUpdate' for n in graph.list_all_nodes()):
        event=graph.find_event_node('ReceiveTick')
        assert event, 'Missing mission tick event'
        hook(bp,event.find_then_pin(),'Post12WorldTick','Post12WorldUpdate')
    def use(g,old,tag):
        active=g.branch(g.compare('GreaterEqual',g.get('EvacuationStage'),STAGES['arrive']))
        active.rename(tag)
        g.do(g.own('Post12Use'))
        for previous in old:
            link(active.find_else_pin(),previous)
    def restore_after(g,old,tag):
        # Handle new milestones after the relay restores its original hardware.
        original=next(n for n in g.e.list_all_nodes() if str(n.get_node_title()).replace(' ','')=='EvacRestoreVisuals')
        output=original.find_then_pin()
        next_pins=list(output.list_connected_pins())
        assert len(next_pins)==1
        input_pin=next_pins[0]
        output.break_pin_links()
        g.cursor=output
        g.do(g.own('Post12Restore')).rename(tag)
        link(g.cursor,input_pin)
        for previous in old:
            link(g.e.find_graph_entry_pin(),previous)
    insert_entry(bp,'EvacUse','Post12UseDispatch',use)
    insert_entry(bp,'ShelterTick','Post12RestoreDispatch',restore_after)


def install():
    bp=load(MISSION)
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert bp.get_outermost() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    rel=Path('Content')/(MISSION.removeprefix('/Game/')+'.uasset')
    backup=PROJECT/'Saved/Backups/Post12'/datetime.now().strftime('%Y%m%d_%H%M%S')/rel
    backup.parent.mkdir(parents=True,exist_ok=False)
    shutil.copy2(PROJECT/rel,backup)
    walk=resident_walk()
    make_hardware(bp)
    for name,data,initial in (
        ('Post12Lift','real','0'),('Post12Cranking','bool','false'),
        ('Post12Escorting','bool','false'),('Post12EscortAt','real','0'),('Post12WrongAt','real','0'),
        ('Post12RadioAt','real','0'), ('Post12LastCrank','real','0'), ('Post12LiftStart','real','0'),
        ('Post12LastWalk','real','0'), ('Post12WalkDelta','real','0'),*((f'Post12Walk{i}','int','0') for i in range(3)),
    ):
        var(bp,name,data,initial)
    for name in ('Post12Restore','Post12LiftTick','Post12EscortTick','Post12Use','Post12Tick','Post12MaybeStart','Post12WorldTick',
                 *(f'Post12Move{i}' for i in range(3)) ):
        Story(bp,name)
    focus(bp,'PostMeet',MEET,MEET_AIM,MEET_REACH)
    for name,point,radius in (('Weight',RACK,19.),('Wrong',WRONG,18.),('Hook',HOOK,20.),('Crank',CRANK,19.)):
        focus(bp,'Post'+name,point,radius)
    compile_bp(bp)
    checkpoint_graphs(bp,5)
    setup_graphs(bp,walk.get_path_name())
    use_graph(bp)
    objectives(bp)
    # Graph deletion leaves the old UObject name occupied until garbage collection.
    evac_tick=G.get_graph_editor_by_name(bp,'EvacTick')
    for node in evac_tick.list_all_nodes():
        if node.get_name()=='Post12TickDispatch':
            node.rename('RetiredPost12Dispatch'+datetime.now().strftime('%H%M%S%f'))
    guide_graphs(bp)
    hooks(bp)
    compile_bp(bp)
    save(bp)
    out=PROJECT/'Saved/Post12'
    out.mkdir(exist_ok=True)
    (out/'Installed.json').write_text(json.dumps({'backup':str(backup),'asset':MISSION,'site':SITE,'yaw':YAW,
        'approach':APPROACH,'gate':location(),'safe':SAFE,'milestones':[4,5],
        'resident_walk':walk.get_path_name()},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
    install()
