"""Author the bounded first story mission using the existing city, pawn and drone."""
import unreal,json,shutil,hashlib
from pathlib import Path
from datetime import datetime
from CityCombat_Common import A,B,G,Graph,add,components,compile_bp,save,var,pin,val,link
from CityMachine_Logic import Logic
import Archive_AuthoringHelpers as H

ROOT='/Game/Story/ForeignMemory'
MISSION=ROOT+'/BP_ForeignMemory'
WIDGET=ROOT+'/WBP_StoryMission'
DRONE=ROOT+'/BP_StoryPatrol'
PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
GUIDE='/Game/LabTutorial/OmegaGuide/BP_OmegaGuide'
MAIN='/Game/Lvl_LabTutorial';CITY='/Game/Surface/Lvl_CampusConnected'
PROJECT=Path(unreal.Paths.project_dir()).resolve()
WORK=PROJECT/'Saved/ForeignMemory'
SOURCE=PROJECT/'SourceAssets/ForeignMemory'
SAVED=PROJECT/'Saved/ForeignMemory'
SCAN=(5850.,25200.,2310.);PATROL=(5850.,39850.,2770.)
TERMINAL=(34837.,87293.,2255.)
ENTRANCE=(34240.,86900.,2260.)
RELAY=(33400.,95600.,2257.)
MEMORYCAM=(5850.,37800.,2320.)
V=lambda p:unreal.Vector(*map(float,p))
L=lambda p:'(X=%s,Y=%s,Z=%s)'%tuple(p)

def load(p):
    o=A.load_asset(p);assert o,p;return o
def bp_asset(p):
    if A.does_asset_exist(p):return load(p)
    folder,name=p.rsplit('/',1);factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Blueprint,factory)
def defaults(bp):return unreal.get_default_object(B.generated_class(bp))
def setprop(g,obj,name,value,kind='Double'):
    return g.do(g.call('Engine.KismetSystemLibrary.Set'+kind+'PropertyByName',Object=obj,PropertyName=name,Value=value))
class Story(Logic):
    def self(self,component='Root'):return super().self(component)
    def ext(self,obj,name,path=PLAYER):
        cls='/Script/Engine.Actor' if name=='bCanBeDamaged' else B.generated_class(load(path)).get_path_name()
        n=self.e.add_get_member_variable_node(name,cls)
        val(n.find_self_pin(),obj);return pin(n,name,True)
    def pget(self,name):return self.ext(self.get('Player'),name)
    def pset(self,name,value,kind='Double'):return setprop(self,self.get('Player'),name,value,kind)
    def pcall(self,name):
        node=self.e.add_call_function_node(B.generated_class(load(PLAYER)).get_path_name()+'.'+name)
        val(node.find_self_pin(),self.get('Player'));return self.do(node)
    def isstage(self,n):return self.compare('EqualEqual',self.get('Stage'),n)
    def both(self,a,b):return self.math('BooleanAND',A=a,B=b)
    def not_(self,a):return self.math('Not_PreBool',A=a)
    def ready(self):return self.num('GreaterEqual',self.now(),self.get('NextAt'))
    def next(self,delay):self.set('NextAt',self.num('Add',self.now(),delay))
    def near(self,point,r):return self.num('Less',self.distance(self.position(self.get('Player')),L(point)),r)
    def goal(self,text,point):
        self.set('Objective',text);self.set('GoalPoint',L(point))
        self.pset('StoryGoalActive',True,'Bool');self.pset('StoryGoal',L(point),'Vector');self.pset('StoryGoalName',text,'String')
    def say(self,cue):
        row=LINES[cue]
        self.set('Speaker',row['speaker']);self.set('Dialogue',row['text'])
        self.set('DialogueUntil',self.num('Add',self.now(),row['duration']+.7))
        self.do(self.call('Engine.AudioComponent.SetSound',target=self.get('Voice'),NewSound=ROOT+'/S_Memory_'+cue))
        self.do(self.call('Engine.AudioComponent.Play',target=self.get('Voice'),StartTime=0.))
        self.next(row['duration']+.8)
    def checkpoint(self,stage,point):
        self.set('CheckpointStage',stage);self.set('CheckpointPosition',L(point));self.set('CheckpointReady',True)
        self.set('CheckpointMax',self.pget('VisorMaxIntegrity'));self.set('CheckpointNoticeUntil',self.num('Add',self.now(),5.))
    def visibility(self,name,show):
        self.do(self.call('Engine.SceneComponent.SetVisibility',target=self.get(name),bNewVisibility=show,bPropagateToChildren=True))
    def clear_enemy(self,name):
        valid=self.branch(self.valid(self.get(name)));skip=valid.find_else_pin()
        n=self.do(self.call('Engine.Actor.K2_DestroyActor',target=self.get(name)))
        reset=self.set(name,'None');link(skip,reset.find_execute_pin())

def import_audio():
    SOURCE.mkdir(parents=True,exist_ok=True)
    audio_source=Path(__file__).resolve().parent/'story_audio'
    if not audio_source.exists():audio_source=SOURCE
    rows=json.loads((audio_source/'Lines.json').read_text(encoding='utf8'))
    tasks=[]
    for row in rows:
        src=audio_source/row['file']
        if src.resolve()!=(SOURCE/src.name).resolve():shutil.copy2(src,SOURCE/src.name)
        task=unreal.AssetImportTask()
        for k,v in dict(filename=str(SOURCE/src.name),destination_path=ROOT,destination_name=src.stem,automated=True,replace_existing=True,save=False).items():task.set_editor_property(k,v)
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for row in rows:
        snd=load(ROOT+'/S_Memory_'+row['id']);assert abs(snd.duration-row['duration'])<.05
        subtitle=unreal.SubtitleCue();subtitle.set_editor_property('time',.05);subtitle.set_editor_property('text',unreal.Text(row['speaker']+' · '+row['text']))
        snd.set_editor_property('subtitles',[subtitle]);save(snd)
    (SOURCE/'Lines.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    for filename in ('Amy_MODEL_CARD','MODEL_CARD'):
        shutil.copy2(PROJECT/'Saved/OmegaVoiceTool'/filename,SOURCE/filename)
    return {x['id']:x for x in rows}

def widget():
    if A.does_asset_exist(WIDGET):bp=load(WIDGET)
    else:
        f=unreal.WidgetBlueprintFactory();f.set_editor_property('parent_class',unreal.UserWidget)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_StoryMission',ROOT,unreal.WidgetBlueprint,f)
    tree=unreal.find_object(bp,'WidgetTree')
    def w(cls,n):return unreal.find_object(tree,n) or unreal.new_object(cls,outer=tree,name=n)
    canvas=w(unreal.CanvasPanel,'StoryCanvas');canvas.clear_children();H.assign_object(tree,'RootWidget',canvas)
    canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    def flag(obj):defaults(H.helper).call_method('AssignFlag',args=(obj,unreal.Name('bIsVariable'),True))
    def text(name,initial,pos,size,width,anchor=(0,0),align=(0,0),color=(.78,.92,.96,1)):
        obj=w(unreal.TextBlock,name);flag(obj);obj.set_text(initial)
        obj.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
        font=obj.get_editor_property('font');font.set_editor_property('font_object',load('/Engine/EngineFonts/Roboto'));font.set_editor_property('size',size);obj.set_font(font)
        obj.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,.96));obj.set_shadow_offset(unreal.Vector2D(1,2))
        obj.set_auto_wrap_text(True)
        slot=canvas.add_child_to_canvas(obj);slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor),maximum=unreal.Vector2D(*anchor)));slot.set_alignment(unreal.Vector2D(*align));slot.set_position(unreal.Vector2D(*pos));slot.set_size(unreal.Vector2D(width,82))
        return obj
    text('ChapterText','ЧУЖАЯ ПАМЯТЬ',(48,96),16,550,color=(.29,.85,.94,1))
    text('ObjectiveText','',(48,126),21,550)
    text('CheckpointText','',(48,204),14,550,color=(1,.74,.35,1))
    text('SpeakerText','',(0,-220),15,980,anchor=(.5,1),align=(.5,1),color=(.32,.91,1,1))
    text('DialogueText','',(0,-164),23,980,anchor=(.5,1),align=(.5,1),color=(.94,.97,1,1))
    text('MemoryText','',(0,80),18,1000,anchor=(.5,0),align=(.5,0),color=(.42,.96,1,1))
    for n in ('MissionObjective','MissionSpeaker','MissionDialogue','MissionCheckpoint','MissionMemory'):var(bp,n,'string','')
    var(bp,'Age','real','0');compile_bp(bp)
    g=Graph(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
    g.override('Tick');g.set('Age',g.math('Add_DoubleDouble',A=g.get('Age'),B=g.dt()))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.get('Age'),B=.12));g.set('Age',0.)
    for field,name in [('MissionObjective','ObjectiveText'),('MissionSpeaker','SpeakerText'),('MissionDialogue','DialogueText'),('MissionCheckpoint','CheckpointText'),('MissionMemory','MemoryText')]:
        value=g.out(g.call('Engine.KismetTextLibrary.Conv_StringToText',InString=g.get(field)))
        g.do(g.call('UMG.TextBlock.SetText',target=g.get(name),InText=value))
    compile_bp(bp);save(bp);return bp

def projection_material():
    path=ROOT+'/M_MemoryProjection'
    if A.does_asset_exist(path):return load(path)
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_MemoryProjection',ROOT,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('two_sided',True)
    edit=unreal.MaterialEditingLibrary
    color=edit.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-300,0);color.set_editor_property('constant',unreal.LinearColor(.02,.35,.42,1.))
    opacity=edit.create_material_expression(mat,unreal.MaterialExpressionConstant,-300,160);opacity.set_editor_property('r',.6)
    assert edit.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert edit.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
    edit.recompile_material(mat);save(mat);return mat

def geometry(bp):
    add(bp,unreal.SceneComponent,'Root')
    scanner=add(bp,unreal.SceneComponent,'ScannerRoot','Root')
    memory=add(bp,unreal.SceneComponent,'MemoryRoot','Root');memory.set_visibility(False,True)
    cube=load('/Engine/BasicShapes/Cube')
    metal=load('/Game/LabTutorial/Industrial/M_DoorArmor')
    glow=load('/Game/LabTutorial/Industrial/M_DoorStatus_Green')
    red=load('/Game/LabTutorial/Industrial/M_DoorStatus_Red')
    def mesh(name,pos,scale,mat,parent='ScannerRoot'):
        c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(cube);c.set_material(0,mat)
        c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_scale3d',V(scale));c.set_collision_profile_name('NoCollision');c.set_cast_shadow(False)
        return c
    mesh('ScannerPost',(6600,25200,2280),(.42,.56,2.6),metal)
    mesh('ScannerHead',(6600,25200,2430),(1.15,.75,.48),metal)
    mesh('ScannerLens',(6538,25200,2430),(.07,.49,.14),glow)
    mesh('ScannerBase',(6600,25200,2162),(1.1,1.1,.18),metal)
    def text(name,value,pos,yaw,size,parent='ScannerRoot'):
        c=add(bp,unreal.TextRenderComponent,name,parent);c.set_text(value);c.set_world_size(size);c.set_text_render_color(unreal.Color(105,220,231,255))
        c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw));c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_collision_profile_name('NoCollision')
    text('ScannerLabel','ГОРОДСКАЯ ОХРАНА\nАРХИВ ДОПУСКОВ',(6528,25200,2400),180,13)
    # An incomplete optical reconstruction on the same street, with no collision or render target.
    for side,x in (('L',5490),('R',6210)):
        mesh('MemoryPost'+side,(x,39000,2400),(.55,.7,5),glow,'MemoryRoot')
    mesh('MemoryLintel',(5850,39000,2660),(7.8,.7,.45),glow,'MemoryRoot')
    for i in range(11):mesh('MemoryGateBar'+str(i),(5520+i*66,39000,2380),(.07,.1,4.2),glow,'MemoryRoot')
    holo=projection_material()
    for _,component,name in components(bp):
        if name.startswith('Memory') and isinstance(component,unreal.StaticMeshComponent):component.set_material(0,holo)
        if name in ('MemoryPostL','MemoryPostR'):component.set_editor_property('relative_scale3d',V((.14,.14,4.5)))
        if name=='MemoryLintel':
            component.set_editor_property('relative_scale3d',V((7.8,.14,.14)));component.set_editor_property('relative_location',V((5850,39000,2620)))
    mesh('MemoryRedSignal',(5480,38945,2570),(.20,.15,.20),red,'MemoryRoot')
    text('MemoryEvacuation','ЭВАКУАЦИОННЫЙ ПРОХОД / СЕКТОР 07\nЗАКРЫТО ПО ПРИКАЗУ ОХРАНЫ',(5850,38930,2710),-90,21,'MemoryRoot')
    camera=add(bp,unreal.CameraComponent,'MemoryCamera','Root');camera.set_editor_property('relative_location',V(MEMORYCAM));camera.set_editor_property('relative_rotation',unreal.Rotator(yaw=90));camera.set_field_of_view(78.)
    memory.set_visibility(False,True)
    voice=add(bp,unreal.AudioComponent,'Voice','Root');voice.set_editor_property('auto_activate',False);voice.set_editor_property('allow_spatialization',False);voice.set_editor_property('suppress_subtitles',True)
    voice.set_editor_property('volume_multiplier',.9)

FUNCTIONS=['FindActors','RefreshHUD','BeginChapter','ScanTick','BeginPatrol','PatrolTick','LabTick','RequestRecovery','AlarmTick','BeginMemory','MemoryTick','CompleteMission','RetryCheckpoint','CheckFailure','MissionTick']
def vars_and_stubs(bp):
    for n,kind,d in [('Stage','int','0'),('Beat','int','0'),('NextAt','real','0'),('DialogueUntil','real','0'),('CheckpointNoticeUntil','real','0'),('CheckpointMax','real','100'),('CheckpointStage','int','0'),('CheckpointReady','bool','false'),('Failed','bool','false'),('InputLocked','bool','false'),('InputBound','bool','false'),('Objective','string',''),('Dialogue','string',''),('Speaker','string',''),('MemoryCaption','string',''),('SavedCanBeDamaged','bool','true'),('MemoryStarted','bool','false'),('ScanDetected','bool','false'),('RecoveryGranted','bool','false'),('PatrolPassedPeacefully','bool','false')]:var(bp,n,kind,d)
    for n,cls in [('Player',B.generated_class(load(PLAYER))),('Guide',B.generated_class(load(GUIDE))),('Patrol',unreal.Actor),('AlarmGuard',unreal.Actor),('StoryHUD',unreal.UserWidget)]:var(bp,n,B.get_object_reference_type(cls),'None')
    for n in ('GoalPoint','CheckpointPosition'):var(bp,n,B.get_struct_type(unreal.Vector.static_struct()),'(X=0,Y=0,Z=0)')
    for name in FUNCTIONS:
        if name not in map(str,B.list_graph_names(bp)):G.create_and_edit_function_graph(bp,name)
    compile_bp(bp)

def functions(bp):
    g=Story(bp,'FindActors')
    b=g.branch(g.not_(g.valid(g.get('Player'))));skip=b.find_else_pin()
    find=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(load(PLAYER)).get_path_name()));n=g.set('Player',g.out(find))
    check=g.branch(g.not_(g.valid(g.get('Guide'))));link(skip,check.find_execute_pin())
    find=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(load(GUIDE)).get_path_name()));g.set('Guide',g.out(find))

    g=Story(bp,'RefreshHUD');g.branch(g.valid(g.get('StoryHUD')))
    g.branch(g.num('Greater',g.get('Stage'),0.))
    g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('StoryHUD'),InOpacity=1.))
    for name,field in [('MissionObjective','Objective'),('MissionSpeaker','Speaker'),('MissionDialogue','Dialogue'),('MissionMemory','MemoryCaption')]:setprop(g,g.get('StoryHUD'),name,g.get(field),'String')
    note=g.math('SelectString',A='КОНТРОЛЬНАЯ ТОЧКА СОХРАНЕНА',B='',bPickA=g.num('Less',g.now(),g.get('CheckpointNoticeUntil')))
    note=g.math('SelectString',A='КОРПУС РАЗРУШЕН · F9 — повторить от контрольной точки',B=note,bPickA=g.get('Failed'))
    setprop(g,g.get('StoryHUD'),'MissionCheckpoint',note,'String')

    g=Story(bp,'BeginChapter')
    g.set('Stage',1);g.set('Beat',-1);g.set('ScanDetected',False);g.goal('Подойти к городскому сканеру',SCAN)
    g.next(0.);g.checkpoint(1,(5850,23900,2257))

    g=Story(bp,'ScanTick')
    latch=g.branch(g.near(SCAN,1600.));skip=latch.find_else_pin();g.set('ScanDetected',True)
    ready=g.branch(g.ready());link(skip,ready.find_execute_pin())
    initial=g.branch(g.compare('EqualEqual',g.get('Beat'),-1));nextbeat=initial.find_else_pin()
    g.branch(g.valid(g.get('Guide')));g.branch(g.num('Greater',g.now(),g.ext(g.get('Guide'),'BusyUntil',GUIDE)))
    g.say('Final');g.set('Beat',0)
    g.cursor=nextbeat
    b=g.branch(g.compare('EqualEqual',g.get('Beat'),0));otherwise=b.find_else_pin()
    g.branch(g.get('ScanDetected'));g.say('Scanner');g.set('Beat',1)
    g.cursor=otherwise;b=g.branch(g.compare('EqualEqual',g.get('Beat'),1));otherwise=b.find_else_pin()
    g.say('Database');g.set('Beat',2)
    g.cursor=otherwise;g.do(g.own('BeginPatrol'))

    g=Story(bp,'BeginPatrol');g.set('Stage',2);g.set('Beat',0)
    find=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(load(DRONE)).get_path_name()));g.set('Patrol',g.out(find))
    missing=g.branch(g.not_(g.valid(g.get('Patrol'))));skip=missing.find_else_pin()
    g.set('Patrol',g.spawn(B.generated_class(load(DRONE)).get_path_name(),L(PATROL)))
    goal=g.set('Objective','Пройти патруль: укрытия или бой');link(skip,goal.find_execute_pin())
    g.goal('Пройти патруль: укрытия или бой',(5850,44500,2257));g.say('Patrol');g.checkpoint(2,(5850,36500,2257))

    g=Story(bp,'PatrolTick')
    pos=g.position(g.get('Player'));g.branch(g.num('Greater',g.axis(pos,'Y'),44500.))
    g.set('PatrolPassedPeacefully',g.valid(g.get('Patrol')))
    g.set('Stage',3);g.set('Beat',0);g.goal('Лаборатория № 2 · найти терминал',ENTRANCE)

    g=Story(bp,'LabTick')
    g.branch(g.near(ENTRANCE,1300.))
    g.branch(g.compare('NotEqual',g.get('CheckpointStage'),3))
    g.checkpoint(3,ENTRANCE)
    g.goal('Лаборатория № 2 · F — подключить терминал',TERMINAL)

    g=Story(bp,'RequestRecovery')
    g.branch(g.valid(g.get('Player')));g.branch(g.not_(g.get('Failed')));g.branch(g.isstage(3))
    g.branch(g.not_(g.pget('NavMemoryReady')))
    pos=g.position(g.get('Player'));z=g.axis(pos,'Z')
    planar=g.vector(g.axis(pos,'X'),g.axis(pos,'Y'),0.)
    g.branch(g.num('Less',g.distance(planar,L((*TERMINAL[:2],0))),165.))
    g.branch(g.both(g.num('Greater',z,2160.),g.num('Less',z,2460.)))
    g.branch(g.not_(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
    g.checkpoint(3,ENTRANCE);g.set('Stage',4);g.set('Beat',0);g.pset('StoryBusy',True,'Bool')
    g.goal('Тревога · отойти от терминала и найти укрытие',ENTRANCE);g.say('Terminal')
    g.sound('/Game/Combat/CyborgModes/S_ModeSelect',L(TERMINAL),.6)

    g=Story(bp,'AlarmTick');g.branch(g.ready())
    b=g.branch(g.compare('EqualEqual',g.get('Beat'),0));otherwise=b.find_else_pin()
    g.say('Alarm');g.next(5.);g.set('Beat',1)
    g.cursor=otherwise;b=g.branch(g.compare('EqualEqual',g.get('Beat'),1));otherwise=b.find_else_pin()
    g.set('AlarmGuard',g.spawn(B.generated_class(load(DRONE)).get_path_name(),L((33480,86900,2740))))
    g.set('Beat',2);g.next(1.);g.goal('Нейтрализовать охранный дрон у входа',ENTRANCE)
    g.cursor=otherwise;g.branch(g.not_(g.valid(g.get('AlarmGuard'))));g.do(g.own('BeginMemory'))

    g=Story(bp,'BeginMemory');g.set('Stage',5);g.set('Beat',0);g.set('MemoryStarted',True)
    g.set('Objective','Восстановление · повреждённый фрагмент')
    g.set('MemoryCaption','АРХИВ ЭВАКУАЦИИ / СЕКТОР 07 · ЗРИТЕЛЬНАЯ РЕКОНСТРУКЦИЯ')
    g.visibility('MemoryRoot',True)
    g.pcall('Story_ProtectMemory')
    g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=True))
    g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=True))
    g.set('InputLocked',True)
    g.do(g.call('Engine.PlayerController.SetViewTargetWithBlend',target=g.pc(),NewViewTarget=g.self(),BlendTime=.45))
    g.set('Dialogue','');g.set('Speaker','');g.next(1.)

    g=Story(bp,'MemoryTick');g.branch(g.ready())
    b=g.branch(g.compare('EqualEqual',g.get('Beat'),0));otherwise=b.find_else_pin()
    g.say('Memory');g.set('Beat',1)
    g.cursor=otherwise;b=g.branch(g.compare('EqualEqual',g.get('Beat'),1));otherwise=b.find_else_pin()
    g.say('Civilian');g.set('Beat',2)
    g.cursor=otherwise;b=g.branch(g.compare('EqualEqual',g.get('Beat'),2));otherwise=b.find_else_pin()
    g.visibility('MemoryRoot',False);g.set('MemoryCaption','ФРАГМЕНТ ОБОРВАН · ИСТОЧНИК ПРИКАЗА НЕИЗВЕСТЕН')
    g.do(g.call('Engine.PlayerController.SetViewTargetWithBlend',target=g.pc(),NewViewTarget=g.get('Player'),BlendTime=.25))
    g.pcall('Story_RestoreDamage')
    g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=False))
    g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=False))
    g.set('InputLocked',False)
    g.say('After');g.set('Beat',3)
    g.cursor=otherwise;g.do(g.own('CompleteMission'))

    g=Story(bp,'CompleteMission');g.branch(g.not_(g.get('RecoveryGranted')))
    # Award the existing repair once, independently of where the player took cover.
    g.pset('NavMemoryReady',True,'Bool');g.pset('NavMapOpen',True,'Bool');g.pset('NavTargetIndex',3,'Int')
    g.pset('VisorMaxIntegrity',g.num('Add',g.pget('VisorMaxIntegrity'),25.))
    g.pset('VisorIntegrity',g.pget('VisorMaxIntegrity'));g.pset('VisorEnergy',g.pget('VisorMaxEnergy'))
    for name in ('ModuleHeadHP','ModuleCoreHP','ModuleArmLHP','ModuleArmRHP','ModuleLegLHP','ModuleLegRHP'):g.pset(name,100.)
    g.pcall('Story_TagMemory')
    g.pset('StoryBusy',False,'Bool');g.pset('StoryGoalActive',False,'Bool')
    g.set('RecoveryGranted',True);g.set('Stage',6);g.set('MemoryCaption','')
    g.set('Objective','ЧУЖАЯ ПАМЯТЬ ЗАВЕРШЕНА · Узел связи: найти исходный приказ')
    g.set('GoalPoint',L(RELAY));g.say('Complete');g.checkpoint(6,ENTRANCE)

    g=Story(bp,'CheckFailure')
    g.branch(g.get('CheckpointReady'));g.branch(g.not_(g.get('Failed')))
    g.branch(g.num('LessEqual',g.pget('VisorIntegrity'),0.))
    g.set('Failed',True);g.set('Dialogue','');g.set('Speaker','')
    g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=True))
    g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=True))
    g.set('InputLocked',True)

    g=Story(bp,'RetryCheckpoint');g.branch(g.get('CheckpointReady'));g.branch(g.valid(g.get('Player')))
    g.do(g.call('Engine.AudioComponent.Stop',target=g.get('Voice')))
    g.clear_enemy('AlarmGuard');g.visibility('MemoryRoot',False)
    memory=g.branch(g.isstage(5));other=memory.find_else_pin()
    g.pcall('Story_RestoreDamage')
    failed=g.branch(g.get('InputLocked'));link(other,failed.find_execute_pin());skip=failed.find_else_pin()
    g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=False))
    n=g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=False))
    merge=g.set('Failed',False);link(skip,merge.find_execute_pin())
    g.set('InputLocked',False)
    g.pset('StoryBusy',False,'Bool');g.set('MemoryCaption','');g.set('Dialogue','');g.set('Speaker','')
    g.do(g.call('Engine.PlayerController.SetViewTargetWithBlend',target=g.pc(),NewViewTarget=g.get('Player'),BlendTime=0.))
    g.do(g.call('Engine.Actor.K2_SetActorLocation',target=g.get('Player'),NewLocation=g.get('CheckpointPosition'),bSweep=False,bTeleport=True))
    g.pset('VisorMaxIntegrity',g.get('CheckpointMax'));g.pset('VisorIntegrity',g.get('CheckpointMax'));g.pset('VisorEnergy',g.pget('VisorMaxEnergy'))
    for name in ('ModuleHeadHP','ModuleCoreHP','ModuleArmLHP','ModuleArmRHP','ModuleLegLHP','ModuleLegRHP'):g.pset(name,100.)
    g.set('Stage',g.get('CheckpointStage'));g.set('Beat',0)
    complete=g.branch(g.isstage(6));other=complete.find_else_pin()
    g.set('Objective','Узел связи · найти исходный приказ');g.pset('StoryGoalActive',False,'Bool')
    g.cursor=other;g.pset('NavMemoryReady',False,'Bool');g.pset('NavMapOpen',False,'Bool')
    street=g.branch(g.isstage(2));other=street.find_else_pin()
    g.clear_enemy('Patrol');g.do(g.own('BeginPatrol'))
    g.cursor=other;lab=g.branch(g.isstage(3));other=lab.find_else_pin()
    g.goal('Лаборатория № 2 · F — подключить терминал',TERMINAL)
    g.cursor=other;g.do(g.own('BeginChapter'))

    g=Story(bp,'MissionTick');g.do(g.own('FindActors'));g.branch(g.valid(g.get('Player')))
    bind=g.branch(g.not_(g.get('InputBound')));bound=bind.find_else_pin()
    g.do(g.call('Engine.Actor.EnableInput',PlayerController=g.pc()));g.set('InputBound',True)
    expired=g.branch(g.num('Greater',g.now(),g.get('DialogueUntil')));skip=expired.find_else_pin()
    link(bound,expired.find_execute_pin())
    g.set('Dialogue','');g.set('Speaker','')
    hud=g.do(g.own('RefreshHUD'));link(skip,hud.find_execute_pin())
    g.do(g.own('CheckFailure'));g.branch(g.not_(g.get('Failed')))
    # Disjoint stages make transitions deterministic and one-shot.
    for stage,fn in [(0,'BeginChapter'),(1,'ScanTick'),(2,'PatrolTick'),(3,'LabTick'),(4,'AlarmTick'),(5,'MemoryTick')]:
        gate=g.branch(g.isstage(stage));otherwise=gate.find_else_pin()
        if stage==0:
            p=g.position(g.get('Player'));g.branch(g.num('Greater',g.axis(p,'Y'),21950.));g.branch(g.num('Greater',g.axis(p,'Z'),2100.))
            g.branch(g.num('Greater',g.now(),26.))
            g.branch(g.valid(g.get('Guide')))
        g.do(g.own(fn));g.cursor=otherwise

    compile_bp(bp)
    g=Story(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
    g.override('ReceiveBeginPlay');g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.12));g.visibility('MemoryRoot',False)
    widget_bp=load(WIDGET)
    create=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(widget_bp).get_path_name(),OwningPlayer=g.pc()))
    g.set('StoryHUD',g.out(create));g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('StoryHUD'),ZOrder=72))
    g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('StoryHUD'),InOpacity=0.))
    g.override('ReceiveTick');g.do(g.own('MissionTick'))
    event=g.e.create_node_from_name(next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|F9')),unreal.Vector2D(),[])
    event.set_editor_property('bConsumeInput',False);g.cursor=pin(event,'Pressed',True);g.do(g.own('RetryCheckpoint'))
    compile_bp(bp);defaults(bp).set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
    defaults(bp).set_editor_property('input_priority',35);save(bp)

def insert_entry(bp,name,tag,build):
    e=G.get_graph_editor_by_name(bp,name)
    if any(n.get_name()==tag for n in e.list_all_nodes()):return
    entry=e.find_graph_entry_pin();old=list(entry.list_connected_pins());assert old,name
    entry.break_pin_links();g=Story(bp);g.e=e;g.cursor=entry
    build(g,old,tag)

def integrate_player(bp):
    for n,k,d in [('StoryGoalActive','bool','false'),('StoryGoalName','string',''),('StoryBusy','bool','false')]:var(bp,n,k,d)
    var(bp,'StoryGoal',B.get_struct_type(unreal.Vector.static_struct()),'(X=0,Y=0,Z=0)');compile_bp(bp)
    def target(g,old,tag):
        gate=g.branch(g.get('StoryGoalActive'));gate.rename(tag)
        g.set('NavGoal',g.get('StoryGoal'));g.set('NavGoalName',g.get('StoryGoalName'))
        for p in old:link(gate.find_else_pin(),p)
    insert_entry(bp,'Nav_RefreshTarget','ForeignMemoryGoal',target)
    def recovery(g,old,tag):
        find=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(load(MISSION)).get_path_name()));actor=g.out(find)
        gate=g.branch(g.valid(actor));gate.rename(tag)
        node=g.e.add_call_function_node(B.generated_class(load(MISSION)).get_path_name()+'.RequestRecovery');val(node.find_self_pin(),actor);g.do(node)
        for p in old:link(gate.find_else_pin(),p)
    insert_entry(bp,'Nav_RecoverMemory','ForeignMemoryTerminal',recovery)
    def hud(g,old,tag):
        gate=g.branch(g.get('StoryBusy'));gate.rename(tag)
        for p in old:link(gate.find_else_pin(),p)
    insert_entry(bp,'Nav_DrawHUD','ForeignMemoryBusy',hud)
    compile_bp(bp);save(bp)

def player_helpers(bp):
    var(bp,'StoryDamageWasEnabled','bool','true');compile_bp(bp)
    g=Graph(bp,'Story_ProtectMemory');g.set('StoryDamageWasEnabled',g.get('bCanBeDamaged'))
    setprop(g,g.self(),'bCanBeDamaged',False,'Bool')
    g=Graph(bp,'Story_RestoreDamage');setprop(g,g.self(),'bCanBeDamaged',g.get('StoryDamageWasEnabled'),'Bool')
    g=Graph(bp,'Story_TagMemory');tags=g.e.add_get_member_variable_node('Tags','/Script/Engine.Actor')
    g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=pin(tags,'Tags',True),NewItem='OmegaCityMemoryRestored'))
    compile_bp(bp)

def integrate_guide(bp):
    # Mission owns its aftermath line; retain all other existing voice functions.
    e=G.get_graph_editor_by_name(bp,'Nav_CheckRecovery')
    if not any(n.get_name()=='ForeignMemoryRecoveryVoice' for n in e.list_all_nodes()):
        entry=e.find_graph_entry_pin();old=list(entry.list_connected_pins());entry.break_pin_links()
        g=Story(bp);g.e=e;g.cursor=entry
        found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(load(MISSION)).get_path_name()))
        gate=g.branch(g.not_(g.valid(g.out(found))));gate.rename('ForeignMemoryRecoveryVoice')
        for p in old:link(gate.find_then_pin(),p)
    compile_bp(bp);save(bp)

def install():
    global LINES
    SAVED.mkdir(parents=True,exist_ok=True)
    manifest=SAVED/'Install.json'
    if manifest.exists():backup=Path(json.loads(manifest.read_text(encoding='utf8'))['backup'])
    else:
        backup=PROJECT/'Saved/Backups/ForeignMemory'/datetime.now().strftime('%Y%m%d_%H%M%S')
        for p,ext in [(PLAYER,'.uasset'),(GUIDE,'.uasset'),(MAIN,'.umap'),(CITY,'.umap')]:
            rel=Path(p.removeprefix('/Game/')+ext);dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content'/rel,dst)
        manifest.write_text(json.dumps({'backup':str(backup),'complete':False}),encoding='utf8')
    A.make_directory(ROOT)
    LINES=import_audio()
    if A.does_asset_exist(DRONE):drone=load(DRONE)
    else:drone=A.duplicate_asset('/Game/Enemies/CityMachines/StrikeDrone/BP_StrikeDrone',DRONE)
    c=defaults(drone)
    for n,v in [('HullHealth',110.),('CruiseSpeed',180.),('CombatSpeed',290.),('SensorRange',1650.),('FireRange',1450.),('ShotDamage',3.),('KeepRange',650.),('Windup',1.2)]:c.set_editor_property(n,v)
    for n,p in [('PointA',(-350,-800,20)),('PointB',(300,850,60)),('PointC',(-300,650,-30)),('PointD',(330,-550,30))]:c.set_editor_property(n,V(p))
    compile_bp(drone);save(drone)
    tune=Graph(drone,'Story_Tune')
    for n,v in [('HullHealth',110.),('CruiseSpeed',180.),('CombatSpeed',290.),('SensorRange',900.),('FireRange',1450.),('ShotDamage',3.),('KeepRange',650.),('Windup',1.2)]:tune.set(n,v)
    compile_bp(drone)
    def init_tuning(g,old,tag):
        n=g.own('Story_Tune');n.rename(tag);g.do(n)
        for p in old:link(g.cursor,p)
    insert_entry(drone,'MachineInit','ForeignMemoryPatrolTuning',init_tuning)
    compile_bp(drone);save(drone)
    widget()
    player_helpers(load(PLAYER))
    bp=bp_asset(MISSION);geometry(bp);vars_and_stubs(bp);functions(bp)
    integrate_player(load(PLAYER));integrate_guide(load(GUIDE))
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world=unreal.EditorLoadingAndSavingUtils.load_map(CITY)
    old=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='CITY_StrikeDrone_01'),None)
    if old:
        t=old.get_actor_transform();t.translation.z=620.;assert actors.destroy_actor(old)
        a=actors.spawn_actor_from_class(B.generated_class(drone),t.translation,t.rotation.rotator());a.set_actor_label('CITY_StoryPatrol_01');a.set_folder_path('CITY/Story/ForeignMemory')
    # Keep exposition at the entry scanner outside the old scout's immediate fire zone.
    scout=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='CITY_StrikeDrone_04'),None)
    if scout:
        pos=scout.get_actor_location();pos.x=5493.710044656003;pos.y=45387.40134065853;scout.set_actor_location(pos,False,True)
        for n,p in [('PointA',(-100,-450,20)),('PointB',(180,650,60)),('PointC',(-180,1000,-30)),('PointD',(200,500,30))]:scout.set_editor_property(n,V(p))
        scout.tags=list(dict.fromkeys(list(scout.tags)+[unreal.Name('ForeignMemoryScannerSafe')]))
    marauder=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='CITY_Machine_00_Marauder'),None)
    if marauder:
        pos=marauder.get_actor_location();pos.x=5493.710044656003;pos.y=52987.40134065853;marauder.set_actor_location(pos,False,True)
    police=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='CITY_Machine_PoliceMech'),None)
    if police:
        pos=police.get_actor_location();pos.x=5493.710044656003;pos.y=58387.40134065853;police.set_actor_location(pos,False,True)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,CITY)
    world=unreal.EditorLoadingAndSavingUtils.load_map(MAIN)
    if not any(a.get_class()==B.generated_class(bp) for a in actors.get_all_level_actors()):
        a=actors.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label('STORY_ForeignMemory');a.set_folder_path('STORY/ForeignMemory')
        assert unreal.EditorLoadingAndSavingUtils.save_map(world,MAIN)
    compile_report={}
    for item in (bp,drone,load(WIDGET),load(PLAYER),load(GUIDE)):
        compile_bp(item);compile_report[item.get_path_name()]={str(n):len(G.get_graph_editor_by_name(item,n).list_nodes_with_errors()) for n in B.list_graph_names(item)}
    data=dict(backup=str(backup),complete=True,assets=[MISSION,WIDGET,DRONE],compile=compile_report,scanner=SCAN,patrol=PATROL,terminal=TERMINAL,entrance=ENTRANCE,relay=RELAY,checkpoints='session only, F9; failure detected from VisorIntegrity',screen_capture=False)
    # Preserve the installed external film when rebuilding the mission graphs.
    film_manifest=PROJECT/'Saved/MemoryFilm/Install.json'
    if film_manifest.exists() and json.loads(film_manifest.read_text(encoding='utf8')).get('complete'):
        import importlib,Install_MemoryFilm
        importlib.reload(Install_MemoryFilm)
        data['memory_video']=Install_MemoryFilm.install().get('movie','disabled by user')
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'mission_install_result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    return data

if __name__=='__main__':install()



