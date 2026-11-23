"""Playable campaign spine after the waterworks, including Atlas shutdown."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys

import unreal

project=Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0,str(project/'Content/Python'))
from CityCombat_Common import A, B, G, add, compile_bp, link, save, val, var
from Install_StoryMemory import L, MISSION, Story, insert_entry, load
from Install_EvacuationRelay import checkpoint_graphs, focus
from Install_DemoCheckpoint import finish_restore
from Install_VisorSubtitles import publish_fields
from SurfacePolish_Materials import import_file
import Archive_AuthoringHelpers as widget_helpers

ROOT='/Game/Story/CampaignFinale'
CREDITS=ROOT+'/WBP_FinalProtocolEnding'
V=unreal.Vector
V2=unreal.Vector2D
ARCHIVE=(27000.0, 77805.0, 2159.7)
RELAY=(33325.0, 78835.0, 2160.0)
GATE=(33305.,82403.,2155.)
CELL=(34105.,82495.,720.)
STREET=(33105.,88046.,2261.)
YARD=(30783.,88046.,2261.)
ARCHIVE_APPROACH=(27000.0, 77633.0, 2264.0)
RELAY_APPROACH=(33295.0, 78665.0, 2261.0)
GATE_APPROACH=(33282.,82232.,2256.)
CROSSING=(33085.0, 77800.0, 2257.0)
YARD_EXIT=(29467.0, 88105.0, 2261.0)
DISTRICT_TURN=(32940.0, 77710.0, 2258.0)
ENDING=9
COLORS={
    'Paint':'/Game/LabTutorial/Industrial/M_DoorArmor',
    'Iron':'/Game/Surface/Materials/M_RuinSteel',
    'Dark':'/Game/Surface/Materials/M_Charcoal',
    'Steel':'/Game/Environment/CityReclaim/M_Reclaim_InfillSteel',
    'Copper':'/Game/Surface/Materials/M_Oxide',
    'Yellow':'/Game/Environment/CityReclaim/M_Reclaim_StationSafety',
    'Card':'/Game/Environment/CityReclaim/M_Reclaim_StationPaper',
    'Blue':'/Game/Environment/CityReclaim/M_Reclaim_StationCladding',
    'Glass':'/Game/Surface/Materials/M_Charcoal',
    'Ceramic':'/Game/Combat/Firearms/M_StatusBlue',
}
RED='/Game/LabTutorial/Industrial/M_DoorStatus_Red'
GREEN='/Game/LabTutorial/Industrial/M_DoorStatus_Green'
AMBER='/Game/LabTutorial/Industrial/M_AmberIndicator'
BLUE='/Game/Combat/Firearms/M_StatusBlue'
CONCRETE='/Game/LabTutorial/Industrial/M_Concrete_Dirty'
FLOOR='/Game/Surface/Materials/CampusPaving/M_CampusConcreteSlabs'
CLICK='/Game/Combat/CyborgModes/S_ModeSelect'
MOTOR='/Game/LabTutorial/Industrial/S_BlastDoorMotor'
THUD='/Game/LabTutorial/Industrial/S_BlastDoorThud'
HALT='/Game/LabTutorial/Industrial/S_BlastDoorHydraulicRelease'

def at(origin,position):
    return tuple(base+offset for base,offset in zip(origin,position))

ENTRY=at(CELL,(0.,-352.,99.))
CONTROL_LAYOUT={
    'ArchivePick':(ARCHIVE,(-50.,-50.,114.),19.),
    'ArchiveWrong':(ARCHIVE,(50.,-50.,114.),19.),
    'ArchiveSlot':(ARCHIVE,(0.,-51.,148.),24.),
    'LocalSwitch':(RELAY,(-42.,-64.,104.),31.),
    'CutSwitch':(RELAY,(42.,-64.,104.),31.),
    'GateHandle':(GATE,(39.,-32.,125.),35.),
    'Access':(CELL,(-280.,-45.,104.),35.),
    'Shutdown':(CELL,(215.,-43.,111.),35.),
    'Exit':(CELL,(65.,-425.,135.),35.),
}
TARGET={name:at(site,pos) for name,(site,pos,_) in CONTROL_LAYOUT.items()}

def mesh_assets():
    source=project/'SourceAssets/CampaignFinale'
    ui=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,import_materials=False,
                          import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        ui.set_editor_property(key,value)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    models={}
    for name in ('Reader','Relay','Verification','Breaker','Module','Lever','Gate','Core','CoreRod'):
        model=import_file(source/('SM_Finale_'+name+'.fbx'),ROOT,ui)
        for i,slot in enumerate(model.static_materials):
            label=str(slot.get_editor_property('imported_material_slot_name'))
            model.set_material(i,load(COLORS[label]))
        save(model)
        models[name]=model
    return models

def hardware(bp,models):
    for name,site in (('Archive',ARCHIVE),('Relay',RELAY),('Gate',GATE),('Cell',CELL)):
        root=add(bp,unreal.SceneComponent,'Finale'+name+'Site','Root')
        root.set_editor_property('relative_location',V(*site))
    cube=load('/Engine/BasicShapes/Cube')

    def shape(name,parent,pos,model='Cube',size=(100,100,100),mat=None,solid=False,shown=True,pitch=0.):
        c=add(bp,unreal.StaticMeshComponent,'Finale'+name,'Finale'+parent+'Site')
        c.set_static_mesh(cube if model=='Cube' else models[model])
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_location',V(*pos))
        c.set_editor_property('relative_scale3d',V(*(dimension/100 for dimension in size)))
        c.set_editor_property('relative_rotation',unreal.Rotator(pitch=pitch))
        c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        c.set_custom_depth_stencil_value(253)
        c.set_render_custom_depth(False)
        c.set_visibility(shown)
        if mat:
            c.set_material(0,load(mat))
            c.set_cast_shadow(False)
        return c

    def box(name,parent,pos,size,mat,solid=False):
        return shape(name,parent,pos,size=size,mat=mat,solid=solid)

    def body_block(name,parent,pos,extent):
        c=add(bp,unreal.BoxComponent,'Finale'+name,'Finale'+parent+'Site')
        c.set_editor_property('relative_location',V(*pos))
        c.set_box_extent(V(*extent))
        c.set_collision_profile_name('BlockAll')
        c.set_hidden_in_game(True)

    def lamp(name,parent,pos,color,intensity,radius,shown=True):
        c=add(bp,unreal.PointLightComponent,'Finale'+name,'Finale'+parent+'Site')
        c.set_editor_property('relative_location',V(*pos))
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_light_color(unreal.LinearColor(*color,1.))
        if parent == 'Cell':
            c.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
        c.set_intensity(intensity)
        c.set_attenuation_radius(radius)
        c.set_cast_shadows(False)
        c.set_editor_property('volumetric_scattering_intensity',0.)
        c.set_visibility(shown)

    def nameplate(name, parent, text, z):
        box(name+'Backing',parent,(0,-45,z),(146,4,21),COLORS['Dark'])
        label=add(bp,unreal.TextRenderComponent,'Finale'+name,'Finale'+parent+'Site')
        label.set_editor_property('relative_location',V(0,-48,z))
        label.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90.))
        label.set_text(unreal.Text(text))
        label.set_world_size(10.5)
        label.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        label.set_text_render_color(unreal.Color(231,228,205,255))

    shape('ArchiveBody','Archive',(0,0,0),'Reader')
    nameplate('ArchivePlate','Archive','WATERWORKS ARCHIVE',177.)
    body_block('ArchiveBlock','Archive',(0,3,89),(76,33,89))
    shape('ArchivePick','Archive',(-50,-50,101),'Module')
    wrong=shape('ArchiveWrong','Archive',(50,-50,101),'Module')
    for i,slot in enumerate(models['Module'].static_materials):
        if str(slot.get_editor_property('imported_material_slot_name'))=='Blue':
            wrong.set_material(i,load('/Game/Environment/CityReclaim/M_Reclaim_MachineCrimson'))
    box('ArchiveSlot','Archive',(0,-50,148),(35,2.5,11),AMBER)
    shape('ArchiveFitted','Archive',(0,-52,140),'Module',size=(79,66,58),shown=False)
    shape('Carried','Archive',(0,0,0),'Module',size=(55,55,55),shown=False)
    lamp('ArchiveTaskLight','Archive',(0,-80,206),(.59,.76,1),700,310)
    shape('RelayBody','Relay',(0,0,0),'Relay')
    nameplate('RelayPlate','Relay','LOCAL GRID / 07',177.)
    body_block('RelayBlock','Relay',(0,2,91),(76,30,91))
    shape('LocalSwitch','Relay',(-42,-54,88),'Lever',pitch=-32)
    shape('CutSwitch','Relay',(42,-54,88),'Lever',pitch=-32)
    box('LocalLamp','Relay',(-41,-44,132),(27,4,4),AMBER)
    box('CutLamp','Relay',(41,-44,132),(27,4,4),RED)
    lamp('RelayTaskLight','Relay',(0,-89,207),(.80,.88,1),730,330)

    shape('GateFrame','Gate',(0,0,0),'Gate')
    box('GatePlinth','Gate',(0,68,4),(252,225,19),CONCRETE)
    box('GateCanopy','Gate',(0,53,281),(252,236,16),COLORS['Iron'])
    for side in (-1,1):
        box('GateCheek'+str(side),'Gate',(116*side,64,139),(16,190,268),CONCRETE,True)
        box('GateTrim'+str(side),'Gate',(113*side,-36,143),(20,12,272),COLORS['Iron'])
    box('GateRear','Gate',(0,157,138),(241,16,276),CONCRETE,True)
    body_block('GateBlock','Gate',(0,0,108),(105,28,108))
    shape('GateHandle','Gate',(39,-32,112),'Lever',pitch=-24)
    box('GateLamp','Gate',(0,-36,225),(48,4,6),RED)
    lamp('GateTaskLight','Gate',(0,-104,232),(.69,.82,1),670,345)

    box('Floor','Cell',(0,0,-13),(1135,930,26),FLOOR,True)
    box('Roof','Cell',(0,0,358),(1135,930,27),CONCRETE,True)
    box('BackWall','Cell',(0,465,171),(1135,21,366),CONCRETE,True)
    box('EntryWall','Cell',(0,-465,171),(1135,21,366),CONCRETE,True)
    for side,sign in (('East',1),('West',-1)):
        box(side+'Wall','Cell',(564*sign,0,171),(22,930,365),CONCRETE,True)
        for i,y in enumerate((-270,-10,265)):
            box(side+str(i)+'Rib','Cell',(530*sign,y,167),(44,40,329),COLORS['Iron'],True)
        box(side+'Conduit','Cell',(535*sign,0,297),(24,878,30),COLORS['Copper'])
        box(side+'Strip','Cell',(526*sign,0,269),(7,840,3.5),BLUE)
    for i,y in enumerate((-265,-75,125,315)):
        box('Beam'+str(i),'Cell',(0,y,332),(1121,34,37),COLORS['Iron'])
        for sign in (-1,1):
            box('Track'+str(i)+str(sign),'Cell',(sign*392,y,312),(144,15,3.5),BLUE)
    shape('InsideExit','Cell',(0,-446,0),'Gate',size=(82,82,81))
    box('Exit','Cell',(65,-420,135),(22,9,29),AMBER)
    shape('AccessBody','Cell',(-280,8,0),'Verification')
    body_block('AccessBlock','Cell',(-280,8,89),(76,31,89))
    box('Access','Cell',(-280,-45,104),(37,3.5,22),BLUE)
    box('AccessLamp','Cell',(-280,-46,129),(39,4,4),AMBER)
    shape('ShutdownBody','Cell',(215,8,0),'Breaker')
    body_block('ShutdownBlock','Cell',(215,8,89),(76,31,89))
    shape('Shutdown','Cell',(215,-40,96),'Lever',size=(125,125,125),pitch=-32)
    box('ShutdownLamp','Cell',(215,-46,129),(39,4,4),RED)
    shape('CoreHousing','Cell',(0,213,0),'Core')
    body_block('CoreBlock','Cell',(0,213,120),(91,91,120))
    shape('CoreRod','Cell',(0,213,78),'CoreRod')
    lamp('CoreLight','Cell',(0,210,172),(.16,.74,1),460,525)
    lamp('CellFill','Cell',(0,-300,265),(.73,.83,.94),1900,720)
    lamp('CellBack','Cell',(36,300,290),(.60,.73,.86),2400,640)
    lamp('CellServiceLight','Cell',(0,24,234),(.84,.85,.78),1400,700)
    bounds=add(bp,unreal.BoxComponent,'FinaleExposureBounds','FinaleCellSite')
    bounds.set_editor_property('relative_location',V(0,0,165))
    bounds.set_box_extent(V(565,461,187))
    bounds.set_collision_profile_name('NoCollision')
    exposure=add(bp,unreal.PostProcessComponent,'FinaleExposure','FinaleExposureBounds')
    exposure.set_editor_property('unbound',False)
    exposure.set_editor_property('blend_radius',38.)
    exposure.set_editor_property('priority',66.)
    settings=exposure.get_editor_property('settings')
    for key,value in (('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),
                      ('auto_exposure_apply_physical_camera_exposure',False),('auto_exposure_bias',2.0),
                      ('ambient_cubemap_intensity',.19)):
        settings.set_editor_property('override_'+key,True)
        settings.set_editor_property(key,value)
    settings.set_editor_property('ambient_cubemap',load('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    exposure.set_editor_property('settings',settings)
    for n,x,y in (('A',-385,260),('B',352,275),('C',461,-305)):
        shape('AuxCabinet'+n,'Cell',(x,y,0),'Relay',size=(65,84,117))
        body_block('AuxBlock'+n,'Cell',(x,y,102),(53,31,102))
    for i in (-1,1):
        box('FloorRail'+str(i),'Cell',(i*86,-110,1.9),(5,395,3),COLORS['Copper'])

def credits_widget():
    factory=unreal.WidgetBlueprintFactory()
    factory.set_editor_property('parent_class',unreal.UserWidget)
    bp=load(CREDITS) if A.does_asset_exist(CREDITS) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'WBP_FinalProtocolEnding',ROOT,unreal.WidgetBlueprint,factory)
    tree=unreal.find_object(bp,'WidgetTree')
    def make(cls,name):
        c=unreal.find_object(tree,name) or unreal.new_object(cls,outer=tree,name=name)
        if isinstance(c,unreal.PanelWidget):
            c.clear_children()
        return c
    canvas=make(unreal.CanvasPanel,'EndingCanvas')
    widget_helpers.assign_object(tree,'RootWidget',canvas)
    canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    backdrop=make(unreal.Border,'Tint')
    backdrop.set_brush_color(unreal.LinearColor(.003,.012,.015,.93))
    full=canvas.add_child_to_canvas(backdrop)
    full.set_anchors(unreal.Anchors(minimum=V2(0,0),maximum=V2(1,1)))
    full.set_offsets(unreal.Margin(0,0,0,0))
    column=make(unreal.VerticalBox,'EndingText')
    slot=canvas.add_child_to_canvas(column)
    slot.set_anchors(unreal.Anchors(minimum=V2(.5,.5),maximum=V2(.5,.5)))
    slot.set_alignment(V2(.5,.5))
    slot.set_size(V2(770,370))
    rows=(
        ('Ended','КАМПАНИЯ ЗАВЕРШЕНА',15,(.57,.91,.94,1),12),
        ('Title','FINAL PROTOCOL',48,(.93,.97,.97,1),23),
        ('Aftermath','Атлас отключён. Убежища сохраняют свою сеть.',21,(.89,.93,.94,1),8),
        ('Price','Системный допуск Сентинела погашен.',20,(.89,.93,.94,1),6),
        ('Alive','Сентинел и Омега остаются на связи.',20,(.89,.93,.94,1),24),
        ('Credit','FINAL PROTOCOL  /  UNREAL ENGINE',14,(.52,.70,.73,1),16),
        ('Key','F · вернуться в зал',15,(.57,.86,.91,1),0),
    )
    for name,words,size,color,spacing in rows:
        t=make(unreal.TextBlock,name)
        t.set_text(unreal.Text(words))
        t.set_editor_property('justification',unreal.TextJustify.CENTER)
        t.set_auto_wrap_text(True)
        t.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
        font=t.get_editor_property('font')
        font.set_editor_property('font_object',load('/Engine/EngineFonts/Roboto'))
        font.set_editor_property('size',size)
        font.set_editor_property('typeface_font_name','Bold' if name in ('Title','Ended') else 'Regular')
        t.set_font(font)
        row=column.add_child_to_vertical_box(t)
        row.set_padding(unreal.Margin(0,0,0,spacing))
    compile_bp(bp)
    save(bp)
    return bp

def part(g,name):
    return g.get('Finale'+name)

def turn(g,name,angle):
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=part(g,name),
        NewRotation=g.math('MakeRotator',Pitch=angle,Yaw=0.,Roll=0.),bSweep=False,bTeleport=True))

def outline(g,name,active):
    g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=part(g,name),bValue=active))

def glow(g,name,path):
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=part(g,name),ElementIndex=0,Material=path))

def touch(g,name):
    g.do(g.own('EvacFocusFinale'+name))
    return g.get('EvacFocus')

def cue(g,speaker,text,seconds=7.):
    if speaker=='ОМЕГА':
        publish_fields(g,'VisorAI',{'text':text},seconds)
    else:
        g.set('VisorRadioSource',speaker)
        publish_fields(g,'VisorRadio',{'text':text},seconds)

def play(g,name,sound=CLICK,gain=.65):
    g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=sound,Location=L(TARGET[name]),VolumeMultiplier=gain,
                AttenuationSettings='/Game/LabTutorial/Industrial/SA_BlastDoor'))

def chapter(g,text):
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('StoryHUD'),
                PropertyName='ShelterChapter',Value=text))

def step(g):
    return g.get('EvacuationMilestone')

def save_at(g,value):
    g.set('EvacuationMilestone',value)
    g.do(g.own('EvacSave'))

def in_cell(g):
    return g.both(g.near(CELL,1220.),
        g.num('Less',g.axis(g.position(g.get('Player')),'Z'),1200.))

def spawn_at(g,target,yaw):
    finish_restore(g,L(target),yaw)

def inside(g):
    g.set('FinaleInside',True)
    outline(g,'GateHandle',False)
    outline(g,'Access',True)
    spawn_at(g,ENTRY,90.)

def carry(g):
    outline(g,'ArchivePick',False)
    outline(g,'ArchiveWrong',False)
    outline(g,'ArchiveSlot',True)
    g.visibility('FinaleArchivePick',False)
    g.set('FinaleCarrying',True)
    item=part(g,'Carried')
    eye=g.ext(g.get('Player'),'FirstPersonCamera')
    g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=item,Parent=eye,SocketName='None',
        LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepWorld',bWeldSimulatedBodies=False))
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=item,NewLocation='(X=56,Y=25,Z=-25)',
        bSweep=False,bTeleport=True))
    turn(g,'Carried',14.)
    g.visibility('FinaleCarried',True)

def installed_archive(g):
    g.visibility('FinaleArchivePick',False)
    g.visibility('FinaleCarried',False)
    g.visibility('FinaleArchiveFitted',True)
    g.set('FinaleCarrying',False)
    for name in ('ArchivePick','ArchiveWrong','ArchiveSlot'):
        outline(g,name,False)
    glow(g,'ArchiveSlot',GREEN)

def local_only(g):
    turn(g,'LocalSwitch',66.)
    g.set('FinaleLocal',True)
    outline(g,'LocalSwitch',False)
    glow(g,'LocalLamp',GREEN)

def isolated(g):
    local_only(g)
    turn(g,'CutSwitch',66.)
    g.set('FinaleIsolated',True)
    outline(g,'CutSwitch',False)
    glow(g,'CutLamp',GREEN)
    glow(g,'GateLamp',GREEN)

def authorized(g):
    g.set('FinaleAuthorized',True)
    outline(g,'Access',False)
    glow(g,'AccessLamp',GREEN)
    glow(g,'ShutdownLamp',AMBER)
    outline(g,'Shutdown',True)

def offline(g):
    g.set('FinaleAtlasOnline',False)
    g.set('FinaleAccessBurned',True)
    g.set('FinaleAuthorized',False)
    turn(g,'Shutdown',66.)
    outline(g,'Shutdown',False)
    glow(g,'ShutdownLamp',GREEN)
    glow(g,'AccessLamp',RED)
    glow(g,'Access',RED)
    g.visibility('FinaleCoreRod',False)
    g.visibility('FinaleCoreLight',False)

def start_hold(g,kind,name):
    g.branch(g.compare('EqualEqual',g.get('FinaleHoldKind'),0))
    g.set('EvacFHeld',True)
    g.set('FinaleHoldKind',kind)
    g.set('FinaleHoldAt',g.now())
    play(g,name,MOTOR,.44)

def warn(g,key,text):
    g.branch(g.num('GreaterEqual',g.now(),g.get('FinaleWarningUntil')))
    g.set('FinaleWarningUntil',g.num('Add',g.now(),3.))
    cue(g,key,text,3.25)

def use(bp):
    g=Story(bp,'FinaleUse')
    due=g.get('FinaleReadyAt')
    g.branch(g.both(g.num('Greater',due,0.),g.num('GreaterEqual',g.now(),due)))

    a=g.branch(g.compare('EqualEqual',step(g),6))
    has=g.branch(g.get('FinaleCarrying'))
    g.branch(touch(g,'ArchiveSlot'))
    installed_archive(g)
    play(g,'ArchiveSlot',THUD,.54)
    cue(g,'ЖУРНАЛ АВАРИИ','Атлас вышел за границы своей задачи. Сначала перекрыл городские службы, потом сам стал решать, кто получит воду и связь.',10.)
    save_at(g,7)
    g.cursor=has.find_else_pin()
    found=g.branch(touch(g,'ArchivePick'))
    carry(g)
    play(g,'ArchivePick')
    g.cursor=found.find_else_pin()
    g.branch(touch(g,'ArchiveWrong'))
    warn(g,'АРХИВ ВОДОКАНАЛА','Сервисный модуль. Журнал хранится в синей кассете.')

    g.cursor=a.find_else_pin()
    b=g.branch(g.compare('EqualEqual',step(g),7))
    local=g.branch(g.get('FinaleLocal'))
    g.branch(touch(g,'CutSwitch'))
    start_hold(g,2,'CutSwitch')
    g.cursor=local.find_else_pin()
    right=g.branch(touch(g,'LocalSwitch'))
    start_hold(g,1,'LocalSwitch')
    g.cursor=right.find_else_pin()
    g.branch(touch(g,'CutSwitch'))
    warn(g,'РАСПРЕДЕЛИТЕЛЬ 07','Отсечка заблокирована. Сначала переведи воду и связь на местную ветку.')

    g.cursor=b.find_else_pin()
    c=g.branch(g.compare('EqualEqual',step(g),8))
    present=g.branch(in_cell(g))
    autonomy=g.branch(g.get('FinaleAuthorized'))
    g.branch(touch(g,'Shutdown'))
    start_hold(g,3,'Shutdown')
    g.cursor=autonomy.find_else_pin()
    found=g.branch(touch(g,'Access'))
    authorized(g)
    play(g,'Access')
    cue(g,'[ЯДРО] АТЛАС','Свободные люди уже однажды довели планету до катастрофы. Ты получил мой допуск. Ты можешь сохранить порядок.',10.)
    cue(g,'ОМЕГА','У ваших систем одна основа. Сверка это подтвердила. Если разомкнёшь ядро, твой допуск сгорит вместе с его полномочиями.',10.)
    g.cursor=found.find_else_pin()
    g.branch(touch(g,'Shutdown'))
    warn(g,'ЯДРО АТЛАСА','Отключение заблокировано. Сверь допуск на левой панели.')
    g.cursor=present.find_else_pin()
    g.branch(touch(g,'GateHandle'))
    play(g,'GateHandle',MOTOR)
    inside(g)

    g.cursor=c.find_else_pin()
    g.branch(g.compare('EqualEqual',step(g),ENDING))
    panel=g.branch(g.get('FinaleCreditsActive'))
    g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('FinaleCredits')))
    g.set('FinaleCreditsActive',False)
    g.cursor=panel.find_else_pin()
    room=g.branch(in_cell(g))
    leaving=g.branch(touch(g,'Exit'))
    g.set('FinaleInside',False)
    spawn_at(g,GATE_APPROACH,-90.)
    g.cursor=leaving.find_else_pin()
    g.branch(touch(g,'Access'))
    g.branch(g.get('FinaleAccessBurned'))
    play(g,'Access',CLICK,.32)
    warn(g,'СВЕРКА ДОПУСКА','Допуск погашен. Удалённые команды выключены. Местная связь работает.')
    g.cursor=room.find_else_pin()
    g.branch(touch(g,'GateHandle'))
    inside(g)

def holds(bp):
    g=Story(bp,'FinaleHoldTick')
    for kind,name,duration in ((1,'LocalSwitch',1.9),(2,'CutSwitch',2.15),(3,'Shutdown',2.75)):
        active=g.branch(g.compare('EqualEqual',g.get('FinaleHoldKind'),kind))
        focus_again=touch(g,name)
        staying=g.branch(g.both(g.get('EvacFHeld'),focus_again))
        since=g.num('Subtract',g.now(),g.get('FinaleHoldAt'))
        f=g.math('FClamp',Value=g.num('Divide',since,duration),Min=0.,Max=1.)
        turn(g,name,g.num('Add',-32.,g.num('Multiply',98.,f)))
        g.branch(g.num('GreaterEqual',since,duration))
        g.set('FinaleHoldKind',0)
        g.set('EvacFHeld',False)
        play(g,name,THUD,.65)
        if kind==1:
            local_only(g)
            outline(g,'CutSwitch',True)
            cue(g,'РАСПРЕДЕЛИТЕЛЬ 07','Вода и местная связь переведены на свои контроллеры.',4.)
        elif kind==2:
            isolated(g)
            outline(g,'GateHandle',True)
            cue(g,'ОМЕГА','Двор и убежища остаются на местной сети. Вход в центр управления рядом. Внутри ещё работает ядро Атласа.',8.)
            save_at(g,8)
        else:
            offline(g)
            g.set('VisorRadioUntil',g.now())
            g.do(g.call('Engine.AudioComponent.Stop',target=g.get('ExternalRadioVoice')))
            play(g,name,HALT,.87)
            cue(g,'ОМЕГА','Атлас отключён. Твой системный допуск погашен. Я всё ещё здесь, Сентинел.',6.)
            g.set('FinaleCreditsAt',g.num('Add',g.now(),10.8))
            g.set('FinaleResponseAt',g.num('Add',g.now(),2.8))
            save_at(g,ENDING)
        g.cursor=staying.find_else_pin()
        turn(g,name,-32.)
        g.set('FinaleHoldKind',0)
        g.cursor=active.find_else_pin()

def task(g,condition,yes,primary,no,fallback):
    match=g.branch(condition)
    g.goal(yes,primary)
    g.cursor=match.find_else_pin()
    g.goal(no,fallback)

def component_goal(g,text,point):
    g.set('Objective',text)
    g.set('GoalPoint',point)
    g.pset('StoryGoalActive',True,'Bool')
    g.pset('StoryGoal',point,'Vector')
    g.pset('StoryGoalName',text,'String')

def archive_route(g):
    pos=g.position(g.get('Player'))
    x=g.axis(pos,'X')
    y=g.axis(pos,'Y')
    near=g.branch(g.near(ARCHIVE,430.))
    carrying=g.get('FinaleCarrying')
    component_goal(g,g.select('Наведи прицел на гнездо считывателя и нажми F',
                    'Возьми синюю кассету у архивного считывателя · F',carrying,'String'),
           g.select(L(TARGET['ArchiveSlot']),L(TARGET['ArchivePick']),carrying,'Vector'))
    g.cursor=near.find_else_pin()
    in_yard=g.branch(g.both(g.num('Greater',y,88320.),g.num('Less',x,31000.)))
    g.goal('Выйди из насосного двора к улице',YARD_EXIT)
    g.cursor=in_yard.find_else_pin()
    north=g.branch(g.num('Greater',y,CROSSING[1]+340.))
    junction=g.branch(g.num('Less',x,32800.))
    g.goal('По проезду водоканала выйди на главную улицу',STREET)
    g.cursor=junction.find_else_pin()
    g.goal('По главной улице иди к перекрёстку с торговой улицей',CROSSING)
    g.cursor=north.find_else_pin()
    g.goal('Найди на торговой улице архив водоканала · WATERWORKS ARCHIVE',ARCHIVE_APPROACH)

def relay_route(g):
    near=g.branch(g.near(RELAY,480.))
    local=g.get('FinaleLocal')
    component_goal(g,g.select('Удерживай F на правом рычаге. Отключи линию Атласа',
                    'Удерживай F на левом рычаге. Переведи службы на местную ветку',local,'String'),
           g.select(L(TARGET['CutSwitch']),L(TARGET['LocalSwitch']),local,'Vector'))
    g.cursor=near.find_else_pin()
    pos=g.position(g.get('Player'))
    x=g.axis(pos,'X')
    task(g,g.num('Less',x,DISTRICT_TURN[0]-170.),
         'Иди по торговой улице к распределителю местной сети',DISTRICT_TURN,
         'Найди распределитель местной сети · LOCAL GRID / 07',RELAY_APPROACH)


def draw_credits(g,widget):
    g.set('FinaleCreditsAt',0.)
    c=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(widget).get_path_name(),OwningPlayer=g.pc()))
    g.set('FinaleCredits',g.out(c))
    g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('FinaleCredits'),ZOrder=180))
    g.set('FinaleCreditsActive',True)

def tick(bp,widget):
    g=Story(bp,'FinaleTick')
    now=g.now()
    boot=g.branch(g.num('LessEqual',g.get('FinaleReadyAt'),0.))
    g.set('FinaleReadyAt',g.num('Add',now,4.))
    g.pset('StoryGoalActive',False,'Bool')
    g.set('Objective','Ручной режим · вода снова идёт по местной ветке')
    g.cursor=boot.find_else_pin()
    g.branch(g.num('GreaterEqual',now,g.get('FinaleReadyAt')))
    g.do(g.own('FinaleHoldTick'))

    retry=g.branch(g.both(g.compare('Less',g.get('EvacuationSaved'),step(g)),
                          g.num('GreaterEqual',now,g.get('FinaleNextSave'))))
    g.set('FinaleNextSave',g.num('Add',now,3.))
    g.do(g.own('EvacSave'))
    gate=g.node(g.e.add_branch_node())
    val(gate.find_condition_pin(),g.compare('EqualEqual',step(g),6))
    link(g.cursor,gate.find_execute_pin())
    link(retry.find_else_pin(),gate.find_execute_pin())
    g.cursor=gate.find_then_pin()
    chapter(g,'ЖУРНАЛ АВАРИИ')
    has=g.get('FinaleCarrying')
    archive_route(g)
    outline(g,'ArchivePick',g.not_(has))
    outline(g,'ArchiveWrong',g.not_(has))
    g.cursor=gate.find_else_pin()

    b=g.branch(g.compare('EqualEqual',step(g),7))
    chapter(g,'ОТСЕЧКА')
    outline(g,'LocalSwitch',g.not_(g.get('FinaleLocal')))
    outline(g,'CutSwitch',True)
    relay_route(g)
    g.cursor=b.find_else_pin()

    c=g.branch(g.compare('EqualEqual',step(g),8))
    chapter(g,'ФИНАЛЬНЫЙ ПРОТОКОЛ')
    room=g.branch(in_cell(g))
    seen=g.get('FinaleAuthorized')
    task(g,seen,'Удерживай F на рубильнике ядра до отключения',TARGET['Shutdown'],
         'Сверь свой системный допуск на левой панели',TARGET['Access'])
    g.cursor=room.find_else_pin()
    outline(g,'GateHandle',True)
    task(g,g.near(GATE,480.),'Наведи прицел на ручку служебной двери и нажми F',TARGET['GateHandle'],
         'Пройди к служебному входу центра управления',GATE_APPROACH)
    g.cursor=c.find_else_pin()

    g.branch(g.compare('EqualEqual',step(g),ENDING))
    chapter(g,'ФИНАЛЬНЫЙ ПРОТОКОЛ')
    g.set('Objective','Кампания завершена · Атлас отключён')
    g.pset('StoryGoalActive',in_cell(g),'Bool')
    g.pset('StoryGoal',L(TARGET['Exit']),'Vector')
    g.pset('StoryGoalName','СЛУЖЕБНЫЙ ВЫХОД','String')
    due=g.get('FinaleResponseAt')
    response=g.branch(g.both(g.num('Greater',due,0.),g.num('GreaterEqual',now,due)))
    g.set('FinaleResponseAt',0.)
    cue(g,'[РАДИОСИГНАЛ] УБЕЖИЩЕ 07','Вода идёт. Местная сеть на связи. Если вы слышите нас, теперь мы можем отвечать сами.',7.)
    ready=g.node(g.e.add_branch_node())
    due=g.get('FinaleCreditsAt')
    val(ready.find_condition_pin(),g.both(g.num('Greater',due,0.),g.num('GreaterEqual',now,due)))
    link(response.find_else_pin(),ready.find_execute_pin())
    link(g.cursor,ready.find_execute_pin())
    g.cursor=ready.find_then_pin()
    draw_credits(g,widget)

def restore(bp):
    g=Story(bp,'FinaleRestore')
    g.branch(g.compare('GreaterEqual',step(g),7))
    g.set('FinaleReadyAt',g.now())
    installed_archive(g)
    linked=g.branch(g.compare('GreaterEqual',step(g),8))
    isolated(g)
    fin=g.branch(g.compare('EqualEqual',step(g),ENDING))
    offline(g)
    inside(g)
    g.cursor=fin.find_else_pin()
    spawn_at(g,RELAY_APPROACH,90.)
    g.cursor=linked.find_else_pin()
    spawn_at(g,ARCHIVE_APPROACH,90.)

def migrate_waterworks(bp):
    g=Story(bp)
    g.e=G.get_graph_editor_by_name(bp,'PumpRestore')
    Branch=next(n for n in g.e.list_all_nodes() if n.get_class().get_name()=='K2Node_IfThenElse')
    pin=Branch.find_condition_pin()
    pin.break_pin_links()
    val(pin,g.compare('GreaterEqual',step(g),6))

def dispatch(bp):
    for name in ('Tick','Use'):
        def insert(g,old,tag,suffix=name):
            active=g.branch(g.compare('EqualEqual',g.get('PumpStage'),4))
            active.rename(tag)
            g.do(g.own('Finale'+suffix))
            for dest in old:
                link(active.find_else_pin(),dest)
        insert_entry(bp,'Pump'+name,'FinaleDispatch'+name,insert)

    def inside_use(g,old,tag):
        valid=g.branch(g.valid(g.get('Player')))
        active=g.node(g.e.add_branch_node())
        val(active.find_condition_pin(),g.both(g.compare('GreaterEqual',step(g),8),in_cell(g)))
        link(g.cursor,active.find_execute_pin())
        active.rename(tag)
        g.cursor=active.find_then_pin()
        g.do(g.own('FinaleUse'))
        for dest in old:
            link(valid.find_else_pin(),dest)
            link(active.find_else_pin(),dest)
    insert_entry(bp,'RequestRecovery','FinaleDispatchInside',inside_use)

    def append(g,old,tag):
        pump=next(n for n in g.e.list_all_nodes() if n.get_name()=='PumpDispatchRestore')
        g.cursor=pump.find_then_pin()
        following=list(g.cursor.list_connected_pins())
        g.cursor.break_pin_links()
        g.do(g.own('FinaleRestore')).rename(tag)
        for dest in following:
            link(g.cursor,dest)
        for dest in old:
            link(g.e.find_graph_entry_pin(),dest)
    insert_entry(bp,'ShelterTick','FinaleDispatchRestore',append)

def install():
    bp=load(MISSION)
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert bp.get_outermost() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    backup=project/'Saved/Backups/CampaignFinale'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    package=Path('Content')/(MISSION.removeprefix('/Game/')+'.uasset')
    target=backup/package
    target.parent.mkdir(parents=True)
    shutil.copy2(project/package,target)
    previous=project/'Content/Story/CampaignFinale'
    if previous.is_dir():
        shutil.copytree(previous,backup/'Content/Story/CampaignFinale')

    models=mesh_assets()
    hardware(bp,models)
    widget=credits_widget()
    reference=B.get_object_reference_type(unreal.UserWidget)
    for key,typ,default in [
        ('ReadyAt','real',0),('NextSave','real',0),('WarningUntil','real',0),('HoldAt','real',0),
        ('CreditsAt','real',0),('ResponseAt','real',0),('HoldKind','int',0),('Carrying','bool',False),
        ('Local','bool',False),('Isolated','bool',False),('Inside','bool',False),('Authorized','bool',False),
        ('AccessBurned','bool',False),('AtlasOnline','bool',True),('CreditsActive','bool',False),('Credits',reference,'None'),
    ]:
        var(bp,'Finale'+key,typ,str(default).lower() if isinstance(default,bool) else str(default))
    for fn in ('Use','Tick','HoldTick','Restore'):
        Story(bp,'Finale'+fn)
    for name,(site,offset,radius) in CONTROL_LAYOUT.items():
        focus(bp,'Finale'+name,at(site,offset),radius)
    compile_bp(bp)
    checkpoint_graphs(bp,ENDING)
    migrate_waterworks(bp)
    use(bp)
    holds(bp)
    tick(bp,widget)
    restore(bp)
    dispatch(bp)
    compile_bp(bp)
    save(bp)
    output=project/'Saved/CampaignFinale'
    output.mkdir(exist_ok=True)
    report={'backup':str(backup),'story':MISSION,'credits':CREDITS,'positions':TARGET,
            'checkpoints':{'pump':6,'archive_read':7,'city_line_isolated':8,'atlas_offline':9}}
    (output/'Installed.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    unreal.log('CampaignFinale: campaign missions and ending saved.')

if __name__=='__main__':
    install()
