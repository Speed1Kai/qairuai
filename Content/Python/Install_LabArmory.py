"""Install the lab supply rack, contextual pickups and two-weapon inventory."""
from datetime import datetime
from pathlib import Path
import json
import shutil

import unreal
from Build_Firearms import A, B, G, PLAYER, GunGraph, V, add, compile_bp, components, load, pin, save, val, var
from Install_EnergyWeapons import replace_defaults

LAB='/Game/Lvl_LabTutorial'
SEQ='/Game/LabTutorial/Intro/LS_CapsuleAwakening'
ROOT='/Game/LabTutorial/Armory'
WEAPONS='/Game/Combat/ApprovedWeapons/'
READY_SOUND='/Game/Combat/Firearms/S_Weapon_Magazine'
SWAP_SOUND='/Game/Combat/CyborgModes/S_ModeSelect'
SPINE='CC_Base_Spine02'
PICKUP_RANGE=245.
AMMO_PACK=30
CAPSULE_X=-530.
RACK_CENTER=V(-620,640,0)
TAGS=('LabPickupCarbine','LabPickupDischarge','LabPickupAmmo')
MODELS={
    'Carbine':('SM_Hunter_CrimsonCarbine','SM_Hunter_CrimsonPack'),
    'Discharge':('SM_Atomic_DischargeEmitter','SM_Atomic_DischargeCell'),
}
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
utils=unreal.EditorLoadingAndSavingUtils
project=Path(unreal.Paths.project_dir()).resolve()


def arg(graph,name,kind):
    entry=graph.e.find_graph_entry_pin().get_owning_node()
    existing=entry.find_output_pin(name)
    if existing.is_valid():
        return existing
    return graph.e.add_graph_input_parameter(name,B.get_basic_type_by_name(kind) if isinstance(kind,str) else kind)

def col(r,g,b,a=1.):
    return f'(R={r},G={g},B={b},A={a})'

def rect(g,x,y,w,h,tint):
    return g.do(g.call('Engine.HUD.DrawRect',target=g.get('ModeCanvasHUD'),RectColor=tint,
                       ScreenX=x,ScreenY=y,ScreenW=w,ScreenH=h))

def text(g,caption,x,y,tint,size):
    return g.do(g.call('Engine.HUD.DrawText',target=g.get('ModeCanvasHUD'),Text=caption,TextColor=tint,
                       ScreenX=x,ScreenY=y,Font='/Engine/EngineFonts/Roboto',
                       Scale=g.mul(g.get('ModeUIScale'),size),bScalePosition=False))

def backup_packages():
    where=project/'Saved/Backups/LabArmory'/datetime.now().strftime('%Y%m%d-%H%M%S')
    files=('Content/Lvl_LabTutorial.umap',
           'Content/LabTutorial/Intro/LS_CapsuleAwakening.uasset',
           'Content/'+PLAYER.removeprefix('/Game/')+'.uasset')
    for rel in files:
        dst=where/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(project/rel,dst)
    return where

def relocate_capsule(seq,layout):
    axis=layout['LAB_Room_Floor'].get_actor_location()
    old=layout['INTRO_CircularPlinth'].get_actor_location()
    delta=V(CAPSULE_X-old.x,axis.y-old.y,0)
    moved=[]
    for label,a in layout.items():
        if (label.startswith('INTRO_') and label!='INTRO_OpeningSequence') or label=='LAB_PlayerStart':
            if not a.get_attach_parent_actor():
                a.modify()
                loc=a.get_actor_location()+delta
                a.set_actor_location(loc,False,True)
                assert (a.get_actor_location()-loc).length()<.05,label
                moved.append(label)
    assert 'INTRO_CircularPlinth' in moved and 'LAB_PlayerStart' in moved
    seq.modify()
    key_count=0
    for binding in seq.get_bindings():
        if not binding.get_name().startswith('INTRO_'):
            continue
        for track in binding.get_tracks():
            if not isinstance(track,unreal.MovieScene3DTransformTrack):
                continue
            for section in track.get_sections():
                for channel in section.get_all_channels():
                    axis=str(channel.get_editor_property('channel_name'))
                    offset={'Location.X':delta.x,'Location.Y':delta.y}.get(axis)
                    if offset is not None:
                        for key in channel.get_keys():
                            key.set_value(key.get_value()+offset)
                            key_count+=1
    assert key_count>10,key_count
    return dict(previous=[old.x,old.y],capsule=[CAPSULE_X,0],moved=len(moved),translated_keys=key_count)

def init_mesh(c,mesh_name,loc=V(),stencil=False):
    mesh=load(WEAPONS+mesh_name)
    c.set_static_mesh(mesh)
    c.set_collision_profile_name('NoCollision')
    c.set_editor_property('can_ever_affect_navigation',False)
    c.set_cast_shadow(False)
    c.set_editor_property('relative_location',loc)
    if stencil:
        c.set_custom_depth_stencil_value(253)
        c.set_render_custom_depth(True)
    return mesh.get_bounding_box()

def supply_blueprint(label,tag,parts):
    path=ROOT+'/BP_Lab'+label+'Pickup'
    if A.does_asset_exist(path):
        bp=load(path)
    else:
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_Lab'+label+'Pickup',ROOT,unreal.Blueprint,factory)
    add(bp,unreal.SceneComponent,'PickupRoot')
    bounds=[]
    for name,mesh,loc in parts:
        c=add(bp,unreal.StaticMeshComponent,name,'PickupRoot')
        shape=init_mesh(c,mesh,loc,True)
        bounds.append((shape.min+loc,shape.max+loc))
    start=V(*(min(getattr(b[0],axis) for b in bounds) for axis in 'xyz'))
    end=V(*(max(getattr(b[1],axis) for b in bounds) for axis in 'xyz'))
    box=add(bp,unreal.BoxComponent,'PickupTrace','PickupRoot')
    box.set_editor_property('relative_location',(start+end)*.5)
    ext=(end-start)*.5
    box.set_box_extent(V(ext.x+4,max(ext.y+4,9),ext.z+4))
    box.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    box.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
    box.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
    box.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY,unreal.CollisionResponseType.ECR_BLOCK)
    box.set_editor_property('generate_overlap_events',False)
    box.set_editor_property('can_ever_affect_navigation',False)
    compile_bp(bp)
    cls=B.generated_class(bp)
    unreal.get_default_object(cls).set_editor_property('tags',[unreal.Name(tag)])
    save(bp)
    return cls

def place_storage(layout):
    carbine,discharge=MODELS['Carbine'],MODELS['Discharge']
    configs=(
        ('Carbine',TAGS[0],(('WeaponShell',carbine[0],V()),('EmptyMagazine',carbine[1],V(17.5,0,1.3))),
         (-122,-10,116),unreal.Rotator(roll=90)),
        ('Discharge',TAGS[1],(('WeaponShell',discharge[0],V()),('PowerCell',discharge[1],V(17.5,0,1.3)),
                              ('ReadyDisplay','SM_Atomic_DisplayReady',V())),
         (11,-10,116),unreal.Rotator(roll=90)),
        ('Ammo',TAGS[2],(('SupplyMagazine',carbine[1],V(40,-5,5)),('SupplySpare',carbine[1],V(37,7,5))),
         (137,-18,124),unreal.Rotator(roll=90)),
    )
    folder='LAB/05_Armory'
    for label,tag,parts,pos,rot in configs:
        cls=supply_blueprint(label,tag,parts)
        name='ARMORY_'+label
        a=layout.get(name) or actors.spawn_actor_from_class(cls,V(*pos)+RACK_CENTER,rot)
        a.set_actor_label(name)
        a.set_folder_path(folder)
    cube=load('/Engine/BasicShapes/Cube')
    metal=load('/Game/LabTutorial/Industrial/M_DistressedMetal')
    def piece(name,position,dims,blocking=False):
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,V(*position)+RACK_CENTER)
        a.set_actor_label('ARMORY_'+name)
        a.set_folder_path(folder)
        c=a.static_mesh_component
        c.set_static_mesh(cube)
        c.set_material(0,metal)
        c.set_collision_profile_name('BlockAll' if blocking else 'NoCollision')
        a.set_actor_scale3d(V(*(v*.01 for v in dims)))
    for n,z,depth in (('Deck',103,76),('LowerShelf',33,64),('Canopy',208,61)):
        piece(n,(0,0,z),(356,depth,11),n!='Canopy')
    for x in (-175,175):
        for y in (-33,29):
            piece('Upright',(x,y,109),(9,10,224))
    piece('BackPanel',(0,35,154),(352,7,101),True)
    for x in (-61,89):
        piece('Divider',(x,17,107),(5,34,6))
    sign=actors.spawn_actor_from_class(unreal.TextRenderActor,V(0,-39,186)+RACK_CENTER,unreal.Rotator(yaw=-90))
    sign.set_actor_label('ARMORY_StorageSign')
    sign.set_folder_path(folder)
    t=sign.text_render
    t.set_text(unreal.Text('СКЛАД СНАРЯЖЕНИЯ'))
    t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    t.set_world_size(22.)
    t.set_text_render_color(unreal.Color(r=171,g=220,b=230,a=255))
    light=actors.spawn_actor_from_class(unreal.PointLight,V(0,-37,190)+RACK_CENTER)
    light.set_actor_label('ARMORY_UtilityLight')
    light.set_folder_path(folder)
    lamp=light.get_component_by_class(unreal.PointLightComponent)
    lamp.set_mobility(unreal.ComponentMobility.MOVABLE)
    lamp.set_editor_property('cast_shadows',False)
    lamp.set_intensity(420.)
    lamp.set_attenuation_radius(240.)
    lamp.set_light_color(unreal.LinearColor(.79,.90,1.,1.))
    return [pair[0] for pair in configs]

def setup_members(bp):
    for name,kind,default in (
        ('OwnsCarbine','bool','false'),('OwnsDischarge','bool','false'),
        ('ArmoryAmmoCollected','bool','false'),('ArmorySpeedBoost','bool','false'),('ArmorySwapKeyDown','bool','false'),
        ('ArmoryFocusKind','int','0'),('ArmoryFocusActor',B.get_object_reference_type(unreal.Actor),'None')):
        var(bp,name,kind,default)
    for kind in MODELS:
        name='Holstered'+kind
        c=add(bp,unreal.StaticMeshComponent,name,'Mesh')
        init_mesh(c,MODELS[kind][0])
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_visibility(False)
        mag=add(bp,unreal.StaticMeshComponent,name+'Cell',name)
        init_mesh(mag,MODELS[kind][1],V(17.5,0,1.3))
        mag.set_mobility(unreal.ComponentMobility.MOVABLE)
        mag.set_visibility(False)
    compile_bp(bp)

def armory_focus(bp):
    g=GunGraph(bp,'Armory_UpdateFocus')
    g.set('ArmoryFocusKind',0)
    g.branch(g.no(g.yes(g.get('OwnsCarbine'),g.yes(g.get('OwnsDischarge'),g.get('ArmoryAmmoCollected')))))
    g.gate()
    # The rendered eye determines aim, while pawn distance keeps third-person pickup local.
    view=g.view()
    eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=view))
    direction=g.math('GetForwardVector',InRot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=view)))
    distance=g.pick('Float',PICKUP_RANGE,PICKUP_RANGE+410.,g.get('bFirstPerson'))
    trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=eye,End=g.va(eye,g.vm(direction,distance)),
                      TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
    g.branch(g.out(trace))
    hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'))
    actor=g.out(hit,'HitActor')
    g.branch(g.valid(actor))
    pawn_pos=g.out(g.call('Engine.Actor.K2_GetActorLocation'))
    reach=g.math('VSize',A=g.vs(g.out(hit,'ImpactPoint'),pawn_pos))
    g.branch(g.gt(PICKUP_RANGE,reach))
    for k,tag in enumerate(TAGS,1):
        matched=g.branch(g.out(g.call('Engine.Actor.ActorHasTag',target=actor,Tag=tag)))
        g.cursor=matched.find_then_pin()
        g.set('ArmoryFocusActor',actor)
        g.set('ArmoryFocusKind',k)
        g.cursor=matched.find_else_pin()
    compile_bp(bp)

def equip_and_pickup(bp):
    g=GunGraph(bp,'Modes_Select')
    wanted=arg(g,'RequestedMode','int')
    ok=g.math('BooleanOR',A=g.yes(g.eq(wanted,1),g.get('OwnsCarbine')),
              B=g.yes(g.eq(wanted,2),g.get('OwnsDischarge')))
    g.branch(ok)
    g.branch(g.no(g.eq(wanted,g.get('CyborgMode'))))
    g.set('CyborgMode',wanted)
    g.set('HunterBurstLeft',0)
    g.set('WeaponReloadMode',0)
    g.set('WeaponKick',0.)
    # The next frame applies the already-authored grip animation and equipped mesh.
    g.do(g.own('Weapon_Sync'))
    compile_bp(bp)

    g=GunGraph(bp,'Armory_Pickup')
    g.gate()
    g.do(g.own('Armory_UpdateFocus'))
    g.branch(g.gt(g.get('ArmoryFocusKind'),0))
    g.branch(g.valid(g.get('ArmoryFocusActor')))
    for idx,(member,condition) in enumerate((('OwnsCarbine',1),('OwnsDischarge',2),('ArmoryAmmoCollected',3))):
        choice=g.branch(g.eq(g.get('ArmoryFocusKind'),condition))
        g.cursor=choice.find_then_pin()
        g.branch(g.no(g.get(member)))
        g.set(member,True)
        if idx==1:
            g.set('BreakerMagazine',1)
            g.set('BreakerReserve',5)
        if idx==2:
            g.set('HunterReserve',g.math('Add_IntInt',A=g.get('HunterReserve'),B=AMMO_PACK))
        g.do(g.call('Engine.Actor.K2_DestroyActor',target=g.get('ArmoryFocusActor')))
        g.set('ArmoryFocusKind',0)
        g.set('ArmoryFocusActor','None')
        g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound=READY_SOUND,VolumeMultiplier=.68))
        if idx<2:
            g.branch(g.mode(0))
            g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_Select',RequestedMode=condition))
        g.cursor=choice.find_else_pin()
    compile_bp(bp)

def wire_swap(bp):
    g=GunGraph(bp,'Armory_Swap')
    g.gate()
    g.branch(g.yes(g.get('OwnsCarbine'),g.get('OwnsDischarge')))
    current=g.branch(g.mode(1))
    for route,mode in ((current.find_then_pin(),2),(current.find_else_pin(),1)):
        g.cursor=route
        g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_Select',RequestedMode=mode))
        g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound=SWAP_SOUND,VolumeMultiplier=.34))
    compile_bp(bp)

    g=GunGraph(bp,'Armory_ReadSwapKey')
    down=g.out(g.call('Engine.PlayerController.IsInputKeyDown',target=g.pc(),Key='Q'))
    held=g.branch(down)
    g.cursor=held.find_else_pin()
    g.set('ArmorySwapKeyDown',False)
    g.cursor=held.find_then_pin()
    g.branch(g.no(g.get('ArmorySwapKeyDown')))
    g.set('ArmorySwapKeyDown',True)
    g.do(g.own('Armory_Swap'))
    compile_bp(bp)

def set_holster(bp):
    g=GunGraph(bp,'Armory_AttachHolsters')
    anim=load('/Game/Combat/AtomicWeapon/Animations/Atomic_MF_Rifle_Idle_ADS')
    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(anim,0.,unreal.AnimPoseEvaluationOptions())
    spine=unreal.AnimPoseExtensions.get_bone_pose(pose,SPINE,unreal.AnimPoseSpaces.WORLD)
    loc=unreal.MathLibrary.inverse_transform_location(spine,V(-17.,-19.,140.))
    rot=unreal.MathLibrary.inverse_transform_rotation(spine,unreal.Rotator(pitch=55.,yaw=188.,roll=-12.))
    for kind in MODELS:
        n='Holstered'+kind
        g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(n),Parent=g.get('Mesh'),
             SocketName=SPINE,LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
        g.relative(n,loc.export_text(),g.rot(rot.pitch,rot.yaw,rot.roll))
    compile_bp(bp)

    g=GunGraph(bp,'Armory_Update')
    g.do(g.own('Armory_ReadSwapKey'))
    g.do(g.own('Armory_UpdateFocus'))
    for kind,mode in (('Carbine',1),('Discharge',2)):
        n='Holstered'+kind
        show=g.yes(g.no(g.get('bFirstPerson')),g.yes(g.get('Owns'+kind),g.no(g.mode(mode))))
        g.visibility(n,show)
        cell=show if mode==1 else g.yes(show,g.gt(g.get('BreakerMagazine'),0))
        g.visibility(n+'Cell',cell)
    compile_bp(bp)

def separate_movement_and_keyboard(bp):
    g=GunGraph(bp,'Modes_UpdateSpeed',keep=True)
    getters=[n for n in g.e.list_all_nodes() if n.find_output_pin('CyborgMode').is_valid()]
    assert getters
    speed=g.pick('Int',0,1,g.get('ArmorySpeedBoost'))
    for old in getters:
        for dest in list(old.find_output_pin('CyborgMode').list_connected_pins()):
            dest.break_pin_links()
            val(dest,speed)
    compile_bp(bp)
    g=GunGraph(bp,'Armory_ToggleSpeed')
    g.gate()
    g.set('ArmorySpeedBoost',g.no(g.get('ArmorySpeedBoost')))
    g.do(g.own('Modes_UpdateSpeed'))
    compile_bp(bp)
    event=G.get_graph_editor_by_name(bp,'EventGraph')
    legacy=[n for n in event.list_all_nodes() if n.get_name().startswith('CyborgModeKey_')]
    assert len(legacy)==5
    event.remove_nodes(legacy)
    for key,func in (('E','Armory_Pickup'),('1','Armory_ToggleSpeed')):
        entry=next(n for n in event.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|'+key))
        k=event.create_node_from_name(entry,unreal.Vector2D(0,16000),[])
        k.rename('ArmoryKey_'+key)
        k.set_editor_property('bConsumeInput',False)
        if key=='1':
            binding=unreal.Key()
            binding.set_editor_property('key_name','One')
            k.set_editor_property('input_key',binding)
        action=event.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+func)
        val(action.find_execute_pin(),pin(k,'Pressed',True))
    start=GunGraph(bp,'Modes_Init',keep=True)
    ending=next(n for n in start.e.list_all_nodes() if n.find_then_pin().is_valid() and n.get_class().get_name()!='K2Node_FunctionEntry'
                and not n.find_then_pin().list_connected_pins() and n.find_execute_pin().is_valid()
                and n.find_execute_pin().list_connected_pins())
    start.cursor=ending.find_then_pin()
    start.do(start.own('Armory_AttachHolsters'))
    tick=GunGraph(bp,'Atomic_Update',keep=True)
    arc=next(n for n in tick.e.list_all_nodes() if str(n.get_node_title())=='Weapon_ArcTick')
    assert not arc.find_then_pin().list_connected_pins()
    tick.cursor=arc.find_then_pin()
    tick.do(tick.own('Armory_Update'))
    compile_bp(bp)

def hud(bp):
    for name,old,new in (('A','BREAKER  /  РАЗРЯД','ДУГОВОЙ ИЗЛУЧАТЕЛЬ'),
                         ('B','HUNTER  /  ОЧЕРЕДЬ x3','ИМПУЛЬСНЫЙ КАРАБИН')):
        nodes=G.get_graph_editor_by_name(bp,'Weapon_DrawHUD').list_all_nodes()
        if any(n.find_input_pin(name).is_valid() and str(n.find_input_pin(name).get_pin_value())==old for n in nodes):
            replace_defaults(bp,'Weapon_DrawHUD',name,{old:new},1)
    g=GunGraph(bp,'Modes_DrawHUD')
    canvas=arg(g,'HUD',B.get_object_reference_type(unreal.HUD))
    width=arg(g,'Width','int')
    height=arg(g,'Height','int')
    prefix=B.generated_class(bp).get_path_name()
    g.do(g.call(prefix+'.Nav_DrawHUD',Canvas=canvas,Width=width,Height=height))
    g.do(g.call(prefix+'.Cloak_DrawStatus',Canvas=canvas,Width=width))
    g.branch(g.no(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
    g.set('ModeCanvasHUD',canvas)
    g.set('ModeScreenW',width)
    g.set('ModeScreenH',height)
    g.set('ModeUIScale',g.limit(g.div(g.get('ModeScreenH'),900.),.80,1.4))
    g.count('ModeHUDFrames')
    g.set('ModeDetectedCount',0)
    for fn in ('Weapon_DrawHUD','Lock_DrawStatus'):
        g.do(g.own(fn))
    w,h,u=g.get('ModeScreenW'),g.get('ModeScreenH'),g.get('ModeUIScale')
    cx,cy=g.mul(w,.5),g.mul(h,.5)
    white,col_cyan=col(.91,.96,.98),col(.18,.85,1.)
    for x,y,a,b in [(-10,-1,5,2),(5,-1,5,2),(-1,-10,2,5),(-1,5,2,5)]:
        rect(g,g.plus(cx,x),g.plus(cy,y),a,b,col_cyan)
    hp=g.limit(g.div(g.get('VisorIntegrity'),g.math('FMax',A=g.get('VisorMaxIntegrity'),B=1.)))
    bar_x=g.mul(24.,u)
    bar_y=g.minus(h,g.mul(26.,u))
    bar_w=g.mul(210.,u)
    text(g,'КОРПУС',bar_x,g.minus(h,g.mul(49.,u)),col(.32,.46,.50),.56)
    rect(g,bar_x,bar_y,bar_w,3.,col(.10,.10,.12,.8))
    rect(g,bar_x,bar_y,g.mul(bar_w,hp),3.,g.pick('Color',col(1.,.035,.055),col_cyan,g.gt(.25,hp)))
    owned=g.branch(g.yes(g.get('OwnsCarbine'),g.get('OwnsDischarge')))
    g.cursor=owned.find_then_pin()
    text(g,'Q  СМЕНИТЬ ОРУЖИЕ',g.minus(w,g.mul(230.,u)),g.minus(h,g.mul(128.,u)),
         col(.65,.77,.82),.74)
    after_q=g.cursor
    g.cursor=owned.find_else_pin()
    outlined=g.branch(g.gt(g.get('ArmoryFocusKind'),0))
    val(outlined.find_execute_pin(),after_q)
    g.cursor=outlined.find_then_pin()
    kind=g.get('ArmoryFocusKind')
    pickup=g.pick('String','E  ВЗЯТЬ КАРАБИН',g.pick('String','E  ВЗЯТЬ ИЗЛУЧАТЕЛЬ','E  ВЗЯТЬ ПАТРОНЫ',g.eq(kind,2)),g.eq(kind,1))
    left=g.minus(cx,g.mul(118.,u))
    y=g.plus(cy,g.mul(52.,u))
    rect(g,left,y,g.mul(236.,u),g.mul(25.,u),col(.016,.028,.036,.84))
    text(g,pickup,g.plus(left,g.mul(13.,u)),g.plus(y,g.mul(4.,u)),white,.88)
    after_prompt=g.cursor
    g.cursor=outlined.find_else_pin()
    detect=g.branch(g.get('bFirstPerson'))
    val(detect.find_execute_pin(),after_prompt)
    targets=g.do(g.call('Engine.GameplayStatics.GetAllActorsWithTag',Tag='CyborgHostile'))
    g.set('ModeTargets',g.out(targets,'OutActors'))
    g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_DrawThreats',Index=0))
    compile_bp(bp)

def install():
    assert not editor.get_game_world()
    world=editor.get_editor_world()
    assert world.get_path_name().split('.')[0]==LAB
    assert not utils.get_dirty_map_packages()
    bp=load(PLAYER)
    assert 'Armory_Pickup' not in list(map(str,B.list_graph_names(bp)))
    backup=backup_packages()
    layout={a.get_actor_label():a for a in actors.get_all_level_actors()}
    assert 'ARMORY_Carbine' not in layout
    setup_members(bp)
    armory_focus(bp)
    equip_and_pickup(bp)
    wire_swap(bp)
    set_holster(bp)
    separate_movement_and_keyboard(bp)
    hud(bp)
    cdo=unreal.get_default_object(B.generated_class(bp))
    for k,n in dict(CyborgMode=0,WeaponEquippedMode=0,HunterMagazine=0,HunterReserve=0,
                    BreakerMagazine=0,BreakerReserve=0).items():
        cdo.set_editor_property(k,n)
    compile_bp(bp)
    seq=load(SEQ)
    data=relocate_capsule(seq,layout)
    data.update(pickups=place_storage(layout),backup=str(backup))
    out=project/'Saved/LabArmory'
    out.mkdir(parents=True,exist_ok=True)
    (out/'Install.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    return bp,seq







if __name__=='__main__':
    player,sequence=install()
    save(player)
    save(sequence)
    assert utils.save_map(editor.get_editor_world(),LAB)
