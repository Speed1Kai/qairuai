"""Place the shelter medic, animate her short ward route, and connect the existing F input."""
from pathlib import Path
from datetime import datetime
import json,math,shutil
import unreal
from Build_RuinedUrbanCampus import local
from CityCombat_Common import A,B,G,Graph,add,compile_bp,save,val,var,link
from Install_StoryMemory import CITY,MISSION,Story,bp_asset,insert_entry,load,L
from Install_VisorSubtitles import flag
import Archive_AuthoringHelpers as H
from Shelter07_Waterworks import SHELTER, light, position

PROJECT=Path(unreal.Paths.project_dir()).resolve()
OUT=PROJECT/'Saved/Shelter07/Medic'
ROOT='/Game/Characters/ShelterMedic'
NPC=ROOT+'/BP_ShelterMedic'
HUD=ROOT+'/WBP_MedicDialogue'
START=position(2.64,1.51,0.)
STOP=position(2.64,3.64,0.)
ROUTE_LENGTH=STOP[1]-START[1]
actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor_sub=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level_sub=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
U=unreal.EditorLoadingAndSavingUtils
tool=unreal.AssetToolsHelpers.get_asset_tools()

def widget():
    if A.does_asset_exist(HUD):
        bp=load(HUD)
    else:
        factory=unreal.WidgetBlueprintFactory()
        factory.set_editor_property('parent_class',unreal.UserWidget)
        bp=tool.create_asset('WBP_MedicDialogue',ROOT,unreal.WidgetBlueprint,factory)
    tree=unreal.find_object(bp,'WidgetTree')
    def make(cls,name,variable=False):
        w=unreal.find_object(tree,name) or unreal.new_object(cls,outer=tree,name=name)
        if isinstance(w,unreal.PanelWidget):w.clear_children()
        if variable:flag(w)
        return w
    def color(r,g,b,a=1.):return unreal.LinearColor(r,g,b,a)
    def label(name,text,size,rgb,bold=False,variable=False):
        w=make(unreal.TextBlock,name,variable)
        w.set_text(text)
        font=w.get_editor_property('font')
        font.set_editor_property('font_object',load('/Engine/EngineFonts/Roboto'))
        font.set_editor_property('typeface_font_name','Bold' if bold else 'Regular')
        font.set_editor_property('size',size)
        w.set_font(font)
        w.set_color_and_opacity(unreal.SlateColor(specified_color=color(*rgb)))
        w.set_shadow_color_and_opacity(color(0,0,0,.93))
        w.set_shadow_offset(unreal.Vector2D(1,1))
        return w
    canvas=make(unreal.CanvasPanel,'MedicRoot')
    H.assign_object(tree,'RootWidget',canvas)
    canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    def center(c,x,y,width,height):
        slot=canvas.add_child_to_canvas(c)
        slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(x,y),maximum=unreal.Vector2D(x,y)))
        slot.set_alignment(unreal.Vector2D(.5,.5))
        slot.set_offsets(unreal.Margin(left=0,top=0,right=width,bottom=height))
    prompt=make(unreal.Border,'MedicPromptBox',True)
    prompt.set_brush_color(color(.028,.038,.036,.88))
    prompt.set_padding(unreal.Margin(left=15,top=5,right=15,bottom=5))
    pt=label('MedicPromptLabel','[F]  Поговорить с медиком',23,(.94,.91,.77),True)
    pt.set_editor_property('justification',unreal.TextJustify.CENTER)
    prompt.add_child(pt);center(prompt,.50,.60,350,44)
    subtitle=make(unreal.Border,'MedicSubtitleBox',True)
    subtitle.set_brush_color(color(.014,.022,.025,.84))
    subtitle.set_padding(unreal.Margin(left=17,top=9,right=17,bottom=12))
    column=make(unreal.VerticalBox,'MedicLineStack');subtitle.add_child(column)
    column.add_child_to_vertical_box(label('MedicTitle','МЕДИК УБЕЖИЩА 07',15,(.86,.89,.65),True))
    body=label('MedicText','',23,(.97,.98,.95),False,True)
    body.set_auto_wrap_text(True)
    column.add_child_to_vertical_box(body).set_padding(unreal.Margin(left=0,top=5,right=0,bottom=0))
    frame=make(unreal.SizeBox,'MedicSubtitleWidth')
    frame.set_width_override(730)
    frame.add_child(subtitle)
    center(frame,.50,.85,730,0)
    subtitle_slot=frame.slot
    subtitle_slot.set_alignment(unreal.Vector2D(.5,1.))
    subtitle_slot.set_auto_size(True)
    for panel in (prompt,subtitle):panel.set_visibility(unreal.SlateVisibility.COLLAPSED)
    var(bp,'Speech','string','')
    var(bp,'Offered','bool','false')
    compile_bp(bp)
    g=Graph(bp,'RefreshMedicDialogue')
    text=g.out(g.call('Engine.KismetTextLibrary.Conv_StringToText',InString=g.get('Speech')))
    g.do(g.call('UMG.TextBlock.SetText',target=g.get('MedicText'),InText=text))
    empty=g.out(g.call('Engine.KismetStringLibrary.IsEmpty',InString=g.get('Speech')))
    for name,b in (('MedicPromptBox',g.get('Offered')),('MedicSubtitleBox',g.math('Not_PreBool',A=empty))):
        state=g.branch(b)
        g.do(g.call('UMG.Widget.SetVisibility',target=g.get(name),InVisibility='HitTestInvisible'))
        visible=g.cursor
        g.cursor=state.find_else_pin()
        node=g.do(g.call('UMG.Widget.SetVisibility',target=g.get(name),InVisibility='Collapsed'))
        # A no-op end of the widget branch joins both visibility states.
        extra=g.do(g.call('UMG.Widget.SetIsEnabled',target=g.get(name),bInIsEnabled=True))
        link(visible,extra.find_execute_pin())
    compile_bp(bp);save(bp)
    return bp

def play(g,anim,loop,rate=1.):
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get('Body'),
                NewAnimToPlay=anim,bLooping=loop))
    g.do(g.call('Engine.SkeletalMeshComponent.SetPlayRate',target=g.get('Body'),Rate=rate))

def orient(g,actor,loc,target,speed):
    toward=g.call('Engine.KismetMathLibrary.FindLookAtRotation',Start=loc,Target=target)
    angle=g.call('Engine.KismetMathLibrary.BreakRotator',InRot=g.out(toward))
    flat=g.math('MakeRotator',Pitch=0.,Roll=0.,Yaw=g.out(angle,'Yaw'))
    current=g.out(g.call('Engine.Actor.K2_GetActorRotation',target=actor))
    movement=g.math('RInterpTo',Current=current,Target=flat,DeltaTime=g.dt(),InterpSpeed=speed)
    g.do(g.call('Engine.Actor.K2_SetActorRotation',target=actor,NewRotation=movement,bTeleportPhysics=False))

def npc(assets,body_yaw,offset_z,speed):
    bp=bp_asset(NPC)
    add(bp,unreal.SceneComponent,'Root')
    body=add(bp,unreal.SkeletalMeshComponent,'Body','Root')
    body.set_skeletal_mesh_asset(load(assets['mesh']))
    body.set_mobility(unreal.ComponentMobility.MOVABLE)
    body.set_collision_profile_name('NoCollision')
    body.set_editor_property('relative_location',unreal.Vector(0,0,offset_z))
    body.set_editor_property('relative_rotation',unreal.Rotator(yaw=body_yaw))
    body.override_animation_data(load(assets['clip_paths']['Idle']),True,True,0.,1.)
    capsule=add(bp,unreal.CapsuleComponent,'MedicSpace','Root')
    capsule.set_capsule_size(28.,83.,False)
    capsule.set_editor_property('relative_location',unreal.Vector(0,0,88.))
    capsule.set_collision_profile_name('Pawn')
    capsule.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    capsule.set_editor_property('generate_overlap_events',False)
    capsule.set_editor_property('can_ever_affect_navigation',False)

    voice=add(bp,unreal.AudioComponent,'MedicVoice','Root')
    voice.set_editor_property('relative_location',unreal.Vector(3,0,151))
    voice.set_editor_property('auto_activate',False)
    voice.set_editor_property('suppress_subtitles',True)
    voice.set_editor_property('allow_spatialization',True)
    voice.set_editor_property('override_attenuation',True)
    shape=voice.get_editor_property('attenuation_overrides')
    shape.set_editor_property('attenuation_shape_extents',unreal.Vector(145,0,0))
    shape.set_editor_property('falloff_distance',560.)
    voice.set_editor_property('attenuation_overrides',shape)
    for key,typ,d in (('Mode','int',0),('SpeakUntil','real',0),('SpeechLine','string','')):
        var(bp,key,typ,d)
    var(bp,'Destination',B.get_struct_type(unreal.Vector.static_struct()),L((0,0,0)))
    compile_bp(bp)
    for row in assets['rows']:
        g=Story(bp,'Speak'+row['id'])
        g.branch(g.compare('EqualEqual',g.get('Mode'),2))
        g.set('Mode',3)
        g.set('SpeakUntil',g.num('Add',g.now(),row['duration']+.21))
        g.set('SpeechLine',row['text'])
        play(g,row['clip'],False)
        g.do(g.call('Engine.AudioComponent.SetSound',target=g.get('MedicVoice'),NewSound=row['sound']))
        g.do(g.call('Engine.AudioComponent.Play',target=g.get('MedicVoice'),StartTime=0.))

    g=Story(bp,'UpdateMedic')
    actor=g.self()
    lo=g.position(actor)
    p=g.player()
    g.branch(g.valid(p))
    there=g.position(p)
    gap=g.distance(there,lo)
    active=g.branch(g.compare('EqualEqual',g.get('Mode'),3))
    orient(g,actor,lo,there,5.0)
    g.branch(g.num('GreaterEqual',g.now(),g.get('SpeakUntil')))
    g.set('Mode',2)
    g.set('SpeechLine','')
    play(g,assets['clip_paths']['Idle'],True)
    g.cursor=active.find_else_pin()
    walk=g.branch(g.compare('EqualEqual',g.get('Mode'),1))
    d=g.get('Destination')
    near_player=g.num('Less',g.distance(there,g.addv(lo,L((0,0,106)))),70.)
    settle=g.branch(g.math('BooleanOR',A=g.num('LessEqual',g.distance(lo,d),9.),B=near_player))
    g.set('Mode',2)
    g.do(g.call('Engine.PrimitiveComponent.SetCollisionEnabled',target=g.get('MedicSpace'),NewType='QueryOnly'))
    play(g,assets['clip_paths']['Idle'],True)
    g.cursor=settle.find_else_pin()
    target=g.math('VInterpTo_Constant',Current=lo,Target=d,DeltaTime=g.dt(),InterpSpeed=speed)
    g.do(g.call('Engine.Actor.K2_SetActorLocation',target=actor,NewLocation=target,bSweep=False,bTeleport=False))
    g.cursor=walk.find_else_pin()
    idle=g.branch(g.compare('EqualEqual',g.get('Mode'),0))
    g.branch(g.num('Less',gap,460.))
    g.set('Destination',g.addv(lo,L((0,ROUTE_LENGTH,0))))
    g.set('Mode',1)
    play(g,assets['clip_paths']['Walk'],True,.43)
    g.cursor=idle.find_else_pin()
    # Look toward the player once she pauses at the medical station.
    g.branch(g.num('Less',gap,265.))
    orient(g,actor,lo,there,2.1)
    compile_bp(bp)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    if not any(n.get_name()=='MedicActorTick' for n in graph.list_all_nodes()):
        gt=Story(bp)
        ev=gt.override('ReceiveTick')
        tick=gt.do(gt.own('UpdateMedic'));tick.rename('MedicActorTick')
    compile_bp(bp);save(bp)
    return bp

def connect_bp(bp,ui):
    mission=load(MISSION)
    medic=B.generated_class(bp)
    widget_class=B.generated_class(ui)
    for name,cls in (('MedicRef',medic),('MedicWidget',widget_class)):
        var(mission,name,B.get_object_reference_type(cls),'None')
    var(mission,'MedicOffered','bool','false')
    compile_bp(mission)
    g=Story(mission,'MedicFocus')
    g.set('MedicOffered',False)
    m=g.get('MedicRef')
    g.branch(g.valid(m))
    actor=g.get('Player')
    g.branch(g.valid(actor))
    g.branch(g.both(g.pget('FrequencyFinished'),
                    g.compare('GreaterEqual',g.get('ShelterStep'),2)))
    g.branch(g.not_(g.pget('NavMapOpen')))
    g.branch(g.compare('EqualEqual',g.ext(m,'Mode',NPC),2))
    anchor=g.addv(g.position(m),L((0,0,139)))
    g.branch(g.num('Less',g.distance(g.position(actor),anchor),235.))
    camera=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0))
    pos=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=camera))
    rotation=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=camera))
    forward=g.math('GetForwardVector',InRot=rotation)
    toward=g.math('Normal',A=g.subv(anchor,pos))
    g.branch(g.num('Greater',g.math('Dot_VectorVector',A=forward,B=toward),.87))
    hit,parts=g.trace(anchor,pos)
    pawnhit=g.math('EqualEqual_ObjectObject',A=g.out(parts,'HitActor'),B=actor)
    g.branch(g.math('BooleanOR',A=g.not_(hit),B=pawnhit))
    # An aimed hardware control keeps F while it has the explicit mission prompt.
    for existing in ('F · проверить медицинские запасы','F · включить резервное питание','F · подняться к водонапорной башне'):
        same=g.out(g.call('Engine.KismetStringLibrary.EqualEqual_StrStr',A=g.get('Objective'),B=existing))
        g.branch(g.not_(same))
    g.set('MedicOffered',True)
    compile_bp(mission)

    g=Story(mission,'MedicRefresh')
    actor=g.get('Player')
    g.branch(g.valid(actor))
    missing=g.branch(g.not_(g.valid(g.get('MedicRef'))))
    found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=medic.get_path_name()))
    g.do(g.call('Engine.KismetSystemLibrary.SetObjectPropertyByName',Object=g.self('Voice'),
                PropertyName='MedicRef',Value=g.out(found)))
    follow=g.do(g.own('MedicFocus'));link(missing.find_else_pin(),follow.find_execute_pin())
    m=g.get('MedicRef')
    g.branch(g.valid(m))
    close=g.num('Less',g.distance(g.position(actor),g.position(m)),640.)
    no_ui=g.branch(g.not_(g.valid(g.get('MedicWidget'))))
    g.branch(close)
    made=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=widget_class.get_path_name(),OwningPlayer=g.pc()))
    g.do(g.call('Engine.KismetSystemLibrary.SetObjectPropertyByName',Object=g.self('Voice'),
                PropertyName='MedicWidget',Value=g.out(made)))
    added=g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('MedicWidget'),ZOrder=79))
    can_set=g.branch(g.valid(g.get('MedicWidget')))
    link(no_ui.find_else_pin(),can_set.find_execute_pin())
    text=g.math('SelectString',A=g.ext(m,'SpeechLine',NPC),B='',bPickA=g.both(close,g.not_(g.pget('NavMapOpen'))))
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('MedicWidget'),
                PropertyName='Speech',Value=text))
    g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=g.get('MedicWidget'),
                PropertyName='Offered',Value=g.get('MedicOffered')))
    cmd=g.e.add_call_function_node(widget_class.get_path_name()+'.RefreshMedicDialogue')
    val(cmd.find_self_pin(),g.get('MedicWidget'));g.do(cmd)

    g=Story(mission,'MedicSpeak')
    for step,key in ((2,'Arrival'),(3,'Reserve'),(4,'Restored')):
        # Step five is exterior, and re-entry returns the mission to four.
        selected=g.branch(g.compare('EqualEqual',g.get('ShelterStep'),step))
        cmd=g.e.add_call_function_node(medic.get_path_name()+'.Speak'+key)
        val(cmd.find_self_pin(),g.get('MedicRef'));g.do(cmd)
        g.cursor=selected.find_else_pin()
    compile_bp(mission)

    def tick(g,old,tag):
        node=g.do(g.own('MedicRefresh'))
        node.rename(tag)
        for item in old:link(g.cursor,item)
    def use(g,old,tag):
        g.do(g.own('MedicFocus'))
        makes=g.branch(g.get('MedicOffered'));makes.rename(tag)
        g.do(g.own('MedicSpeak'))
        for item in old:link(makes.find_else_pin(),item)
    insert_entry(mission,'ShelterTick','MedicConversationTick',tick)
    insert_entry(mission,'ShelterUse','MedicConversationUse',use)
    compile_bp(mission);save(mission)

def install(assets,work_dir):
    world=editor_sub.get_editor_world()
    if world.get_path_name().split('.')[0]!=CITY:
        assert not U.get_dirty_map_packages()
        assert level_sub.load_level(CITY)
        world=editor_sub.get_editor_world()
    backup_file=work_dir/'Backup.json'
    assert not editor_sub.get_game_world() and (not U.get_dirty_map_packages() or backup_file.exists())
    if backup_file.exists():
        backup=Path(json.loads(backup_file.read_text())['backup'])
    else:
        backup=PROJECT/'Saved/Backups/ShelterMedic'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        for suffix,path in (('.umap',CITY),('.uasset',MISSION)):
            rel=Path('Content')/(path.removeprefix('/Game/')+suffix)
            to=backup/rel;to.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PROJECT/rel,to)
        backup_file.write_text(json.dumps({'backup':str(backup)}))
    rel=Path('Content')/(SHELTER.removeprefix('/Game/')+'.uasset')
    dst=backup/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(PROJECT/rel,dst)
    shelter=load(SHELTER)
    # The emergency pendant already sits beside the ward. Its light stays local.
    pendant_position=(2.10,2.20,2.70)
    pendant_intensity=4400.
    light(shelter,'MedicWardPendant',pendant_position,(1.,.84,.69),pendant_intensity,410,True,False)
    compile_bp(shelter);save(shelter)
    preview=actor_sub.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
    sk=preview.skeletal_mesh_component;sk.set_skeletal_mesh_asset(load(assets['mesh']))
    front=sk.get_socket_location('ball_l')-sk.get_socket_location('foot_l')
    actor_sub.destroy_actor(preview)
    assert math.hypot(front.x,front.y)>2.5,front
    yaw=round(-math.degrees(math.atan2(front.y,front.x)),2)
    if abs(yaw)<4:yaw=0.
    elif abs(yaw-90.)<9:yaw=90.
    elif abs(yaw+90.)<9:yaw=-90.
    elif abs(abs(yaw)-180.)<9:yaw=180.
    bp=npc(assets,yaw,0.,132.)
    ui=widget()
    connect_bp(bp,ui)
    resident=next((a for a in actor_sub.get_all_level_actors() if a.get_actor_label()=='CITY_S07_Medic'),None)
    if not resident:
        resident=actor_sub.spawn_actor_from_class(B.generated_class(bp),local(*START),unreal.Rotator(yaw=90))
        resident.set_actor_label('CITY_S07_Medic');resident.set_folder_path('CITY/Waterworks/Residents')
    room=next(a for a in actor_sub.get_all_level_actors() if a.get_actor_label()=='CITY_Shelter07')
    pendant=room.get_editor_property('MedicWardPendant')
    pendant.modify()
    pendant.set_editor_property('relative_location',local(*position(*pendant_position)))
    pendant.set_intensity(pendant_intensity)
    pendant.set_attenuation_radius(410.)
    pendant.set_visibility(True)
    assert U.save_map(world,CITY)
    (work_dir/'Installed.json').write_text(json.dumps(dict(passed=True,backup=str(backup),model_yaw=yaw,
           start=START,stop=STOP,blueprint=NPC,mission=MISSION),indent=2))

if __name__ == '__main__':
    manifest=PROJECT/'SourceAssets/Shelter07/Medic/MedicAssets.json'
    run_dir=OUT/'InstallRuns'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run_dir.mkdir(parents=True)
    install(json.loads(manifest.read_text(encoding='utf8')),run_dir)
