"""DEMO-003A: native Blueprint local goals and GDD-aligned Russian text.

Run outside PIE. Retains the existing city mission, rejected-scene guards,
first-person settings and focused-interaction fix. Does not rebuild old installers.
"""
import unreal,json,shutil,sys,textwrap,hashlib
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(unreal.Paths.project_content_dir())/'Python'))
from CityCombat_Common import A,B,G,compile_bp,save,var,pin,val,link,components
from Install_OmegaNavigation import Nav,vector,CYAN,WHITE,AMBER,MUTED

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SOURCE=PROJECT/'SourceAssets/DemoIntro'
OUT=PROJECT/'Saved/DemoIntro/20261118';OUT.mkdir(parents=True,exist_ok=True)
PATHS={'player':'/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter','guide':'/Game/LabTutorial/OmegaGuide/BP_OmegaGuide','mission':'/Game/Story/ForeignMemory/BP_ForeignMemory','widget':'/Game/Story/ForeignMemory/WBP_StoryMission','station':'/Game/Environment/CityService/BP_ServiceStation','power':'/Game/LabTutorial/Basement/BP_BuildingPower','lift':'/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional','route':'/Game/Surface/HiddenExit/BP_HiddenLabRoute'}
report={'saved':False,'assets':[],'literal_changes':{},'numeric_changes':{}}

def ext(g,cache,field,bp):
    node=g.e.add_get_member_variable_node(field,B.generated_class(bp).get_path_name())
    val(node.find_self_pin(),g.get(cache));return pin(node,field,True)
def intro_goal(g,phase,title,point,hint):
    g.set('DemoIntroGoalActive',True);g.set('DemoIntroPhase',phase)
    g.set('NavGoal',point);g.set('NavGoalName',title);g.set('DemoIntroHint',hint)
def build_outdoor_guidance(player):
    g=Nav(player,'Demo_RefreshOutdoorGoal')
    x,y,_=g.split(g.position())
    guide=(
        (g.both(g.number('Less',y,4100.),g.number('Less',x,8200.)),
         'Обойти воронки у выхода',(6180,4280,2257),'По асфальту вдоль лаборатории'),
        (g.both(g.number('Less',y,5300.),g.number('Less',x,8380.)),
         'Выйти на служебную дорогу',(8646,4280,2257),'Дорога проходит между корпусами'),
        (g.number('Less',y,7500.),
         'Идти к воротам периметра',(8646,7670,2257),'Следуй по служебной дороге'),
        (g.both(g.number('Less',y,8190.),g.number('Greater',x,8260.)),
         'Обойти воронку на дороге',(8100,8115,2257),'Обход по краю асфальта'),
        (g.number('Less',y,9040.),
         'Пройти вдоль воронки',(8100,9130,2257),'Оставайся на ровном краю проезда'),
        (g.number('Less',y,13270.),
         'Дойти до служебного фургона',(9005,13340,2257),'Дорога к воротам идёт мимо фургона'),
        (g.both(g.number('Less',y,13950.),g.number('Greater',x,8180.)),
         'Обойти служебный фургон',(9005,14090,2257),'Пройди мимо машины по краю дороги'),
        (g.both(g.number('Less',y,15100.),g.number('Greater',x,6510.)),
         'Повернуть к выезду',(6320,14090,2257),'Держись асфальта в обход завалов'),
        (g.number('Less',y,17440.),
         'Пройти ворота периметра',(5850,17680,2257),'За воротами начинается переправа'),
        (g.number('Less',y,21700.),
         'Перейти реку по броду',(5850,21800,2257),'Дорога спускается к воде и выходит к посту 02'),
    )
    for condition,title,point,hint in guide:
        branch=g.branch(condition)
        intro_goal(g,5,title,vector(*point),hint)
        g.cursor=branch.find_else_pin()
    intro_goal(g,5,'Найти сканер городского периметра',vector(5850,25200,2310),
               'Сканер стоит за постом 02')
    compile_bp(player)


def build_local_goals(player,bps):
    for name,kind,default in [('DemoIntroGoalActive','bool','false'),('DemoIntroPhase','int','0'),('DemoIntroHint','string',''),('DemoReachedSurface','bool','false')]:var(player,name,kind,default)
    caches=[('DemoIntroMission','mission'),('DemoIntroPower','power'),('DemoIntroLift','lift'),('DemoIntroExit','route')]
    for name,role in caches:var(player,name,B.get_object_reference_type(B.generated_class(bps[role])),'None')
    compile_bp(player)
    build_outdoor_guidance(player)
    g=Nav(player,'Demo_RefreshIntroGoal');g.set('DemoIntroGoalActive',False);g.set('DemoIntroPhase',0)
    g.branch(g.inverse(g.get('NavMemoryReady')))
    for name,role in caches:
        missing=g.branch(g.inverse(g.valid(g.get(name))));valid=missing.find_else_pin()
        found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(bps[role]).get_path_name()))
        g.set(name,g.out(found));merge=g.set(name,g.get(name));link(valid,merge.find_execute_pin())
        g.branch(g.valid(g.get(name)))
    stage=ext(g,'DemoIntroMission','Stage',bps['mission'])
    g.branch(g.math('EqualEqual_IntInt',A=stage,B=0))
    pos=g.position();x,y,z=g.split(pos)
    moving=g.both(g.number('Greater',ext(g,'DemoIntroLift','LiftState',bps['lift']),0.),g.number('Less',z,2100.))
    gate=g.branch(moving);rest=gate.find_else_pin()
    cabin=ext(g,'DemoIntroLift','CabinRoot',bps['lift'])
    cabin_pos=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=cabin))
    intro_goal(g,2,'Дождаться остановки лифта',g.math('Add_VectorVector',A=cabin_pos,B=vector(80,165,185)),'Оставайся в кабине')
    g.cursor=rest
    basement=g.branch(g.number('Less',z,865.));upper=basement.find_else_pin()
    powered=ext(g,'DemoIntroPower','bBuildingPowered',bps['power'])
    power=g.branch(g.inverse(powered));lift=power.find_else_pin()
    intro_goal(g,1,'Найти главный рубильник',vector(3460,-1700,150),'Наведись на панель и нажми E · K — подсветка')
    g.cursor=lift
    called=g.branch(g.math('EqualEqual_IntInt',A=ext(g,'DemoIntroLift','CurrentFloor',bps['lift']),B=1));board=called.find_else_pin()
    intro_goal(g,2,'Вызвать грузовой лифт',vector(2295,-215,165),'Наведись на кнопку вызова и нажми F')
    g.cursor=board
    intro_goal(g,2,'Подняться на грузовом лифте',vector(2730,165,185),'Войди в кабину · F — кнопка лифта')
    g.cursor=upper
    emerged=g.both(g.number('Greater',z,2100.),g.number('Greater',y,3040.))
    surface=g.branch(g.math('BooleanOR',A=g.get('DemoReachedSurface'),B=emerged));inside=surface.find_else_pin()
    g.set('DemoReachedSurface',True)
    g.do(g.own('Demo_RefreshOutdoorGoal'))
    g.cursor=inside
    opened=g.branch(ext(g,'DemoIntroExit','CoverReleased',bps['route']));stairs=opened.find_else_pin()
    intro_goal(g,4,'Выйти на поверхность',vector(6375,3350,2257),'Поднимись по лестнице через открытый люк')
    g.cursor=stairs
    near=g.number('Less',g.math('Vector_Distance',V1=pos,V2=vector(6275,1910,1930)),180.)
    lever=g.branch(near);approach=lever.find_else_pin()
    intro_goal(g,3,'Открыть наружный люк',vector(6275,1910,1930),'F — рычаг люка · дождись открытия')
    g.cursor=approach
    intro_goal(g,3,'Подняться к наружному люку',vector(6275,1910,1930),'Ищи техническую лестницу на первом этаже')
    compile_bp(player)
    graph=G.get_graph_editor_by_name(player,'Nav_RefreshTarget')
    if not any(n.get_name()=='DemoIntroGoalBeforeCity' for n in graph.list_all_nodes()):
        entry=graph.find_graph_entry_pin();old=list(entry.list_connected_pins());assert len(old)==1
        entry.break_pin_links();g=Nav(player);g.e=graph;g.cursor=entry
        call=g.own('Demo_RefreshIntroGoal');call.rename('DemoIntroGoalBeforeCity');g.do(call)
        gate=g.branch(g.get('DemoIntroGoalActive'));link(gate.find_else_pin(),old[0])
    compile_bp(player)

def build_navigation_hud(player):
    g=Nav(player,'Nav_DrawHUD');entry=g.e.find_graph_entry_pin().get_owning_node()
    g.branch(g.inverse(g.get('StoryBusy')));g.input_enabled()
    for field,parameter in [('NavCanvas','Canvas'),('NavWidth','Width'),('NavHeight','Height')]:g.set(field,pin(entry,parameter,True))
    scale=g.math('FMin',A=g.number('Divide',g.get('NavHeight'),780.),B=g.number('Divide',g.get('NavWidth'),800.))
    g.set('NavScale',g.math('FClamp',Value=scale,Min=.48,Max=1.));g.do(g.own('Nav_RefreshTarget'))
    left=g.offset(g.number('Multiply',g.get('NavWidth'),.5),-215.);top=g.scaled(48.)
    x=g.offset(left,12.);row=lambda v:g.offset(top,v)
    distance=g.metres(g.math('Vector_Distance',V1=g.position(),V2=g.get('NavGoal')))
    distance_label=g.concat('До цели: ',distance,' м')
    full=g.math('BooleanOR',A=g.get('DemoIntroGoalActive'),B=g.inverse(g.get('StoryGoalActive')))
    height=g.math('SelectFloat',A=84.,B=60.,bPickA=full)
    g.rectangle(left,top,g.scaled(430.),g.scaled(height),'(R=.013,G=.036,B=.05,A=.80)')
    g.rectangle(left,top,g.scaled(2.),g.scaled(height),CYAN)
    title=g.math('SelectString',A=g.get('NavGoalName'),B=distance_label,bPickA=full)
    g.text(title,x,row(8.),WHITE,1.)
    xcoord,ycoord,zcoord=g.split(g.position())
    close=g.both(g.near_console(xcoord,ycoord,zcoord),g.inverse(g.get('NavMemoryReady')))
    normal=g.math('SelectString',A='F — подключиться к сервисному терминалу',B='',bPickA=close)
    normal=g.math('SelectString',A='M — карта города · N — выбор точки',B=normal,bPickA=g.get('NavMemoryReady'))
    hint=g.math('SelectString',A=g.get('DemoIntroHint'),B=normal,bPickA=g.get('DemoIntroGoalActive'))
    second=g.math('SelectString',A=distance_label,B=hint,bPickA=full)
    g.text(second,x,row(31.),CYAN,.91)
    detail=g.branch(full);no_detail=detail.find_else_pin()
    g.text(hint,x,row(55.),AMBER,.78)
    draw_map=g.do(g.own('Nav_DrawCityMap'));link(no_detail,draw_map.find_execute_pin())
    compile_bp(player)

def install():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    config=json.loads((SOURCE/'Dialogue.json').read_text(encoding='utf8'))
    backup=PROJECT/'Saved/Backups/DemoIntro'/datetime.now().strftime('%Y%m%d_%H%M%S');report['backup']=str(backup)
    mutable=[PATHS[n] for n in ['player','guide','mission','widget','station']]+[row['sound'] for row in config['lines']]
    for path in mutable:
        rel=Path('Content')/(path.removeprefix('/Game/')+'.uasset');src=PROJECT/rel
        if src.exists():
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    protected=['Content/Lvl_LabTutorial.umap','Content/Surface/Lvl_CampusConnected.umap','Content/LabTutorial/Basement/BP_BuildingPower.uasset','Content/LabTutorial/FocusedInteraction/BP_InteractionFocus.uasset','Content/LabTutorial/Elevator/BP_FreightElevatorBidirectional.uasset','Content/Environment/CityRealism/BP_DowntownWestStreet.uasset','Config/DefaultEngine.ini','Config/DefaultGame.ini']
    report['protected_hashes_before']={p:hashlib.sha256((PROJECT/p).read_bytes()).hexdigest() for p in protected}
    bps={name:unreal.load_asset(path) for name,path in PATHS.items()};assert all(bps.values())
    tasks=[]
    for row in config['lines']:
        task=unreal.AssetImportTask()
        for key,value in dict(filename=str(SOURCE/row['file']),destination_path=row['sound'].rsplit('/',1)[0],destination_name=row['sound'].rsplit('/',1)[-1],automated=True,replace_existing=True,save=False).items():task.set_editor_property(key,value)
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    report['audio']=[];replacements=dict(config['literal_replacements'])
    for row in config['lines']:
        sound=unreal.load_asset(row['sound']);assert sound
        assert abs(sound.get_editor_property('duration')-row['duration'])<.01
        cue=unreal.SubtitleCue();cue.set_editor_property('time',.12)
        cue.set_editor_property('text',unreal.Text(textwrap.fill(row['speaker']+' · '+row['text'],width=86)))
        sound.set_editor_property('subtitles',[cue]);report['audio'].append(row['sound'])
        replacements[row['old_sound']]=sound.get_path_name();replacements[row['old_text']]=row['text']
    for role in ['player','guide','mission']:
        changed=0
        for gn in B.list_graph_names(bps[role]):
            graph=G.get_graph_editor_by_name(bps[role],gn)
            for n in graph.list_all_nodes():
                for p in n.list_all_pins():
                    try:value=p.get_pin_value()
                    except Exception:continue
                    if value in replacements:
                        assert p.set_pin_value(replacements[value]),(role,gn,value)
                        changed+=1
        report['literal_changes'][role]=changed
    poll=G.get_graph_editor_by_name(bps['guide'],'Omega_Poll')
    for old,new in [(2180.,1180.),(1640.,3220.),(1800.,2100.)]:
        count=0
        for n in poll.list_all_nodes():
            p=n.find_input_pin('B')
            if not p.is_valid() or p.list_connected_pins():continue
            try:matches=float(p.get_pin_value())==old
            except Exception:matches=False
            if matches:val(p,new);count+=1
        if count==0:
            # Already-applied thresholds are valid on repeated postprocessing.
            already=[]
            for n in poll.list_all_nodes():
                p=n.find_input_pin('B')
                if not p.is_valid() or p.list_connected_pins():continue
                try:already.append(float(p.get_pin_value())==new)
                except Exception:pass
            assert any(already),(old,count)
        else:assert count==1,(old,count)
        report['numeric_changes'][str(old)]=new
    tree=unreal.find_object(bps['widget'],'WidgetTree');chapter=unreal.find_object(tree,'ChapterText');assert chapter
    chapter.set_text(unreal.Text(config['chapter']))
    for _,c,name in components(bps['station']):
        if isinstance(c,unreal.TextRenderComponent):
            if name=='ReceptionSign':c.set_text(unreal.Text('СЕРВИС НАВИГАЦИИ'))
            if name=='FacadeSign':c.set_text(unreal.Text('ЛАБОРАТОРИЯ 02 / СЕРВИСНЫЙ УЗЕЛ'))
    build_local_goals(bps['player'],bps);build_navigation_hud(bps['player'])
    report['compile']={}
    for role in ['widget','station','guide','mission','player']:
        bp=bps[role];compile_bp(bp);report['compile'][role]='passed'
    assert unreal.get_default_object(B.generated_class(bps['player'])).get_editor_property('bFirstPerson')
    for role in ['widget','station','guide','mission','player']:save(bps[role]);report['assets'].append(PATHS[role])
    for row in config['lines']:save(unreal.load_asset(row['sound']))
    from Present_DemoOmegaCaptions import install_captions
    install_captions()
    report['caption_widget']='/Game/Story/DemoIntro/WBP_OmegaCaption'
    report['protected_hashes_after']={p:hashlib.sha256((PROJECT/p).read_bytes()).hexdigest() for p in protected}
    assert report['protected_hashes_before']==report['protected_hashes_after']
    report['saved']=True
try:install()
finally:(OUT/'Install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
