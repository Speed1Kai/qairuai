"""Install the waterworks shelter and connect its follow-up tasks to the first mission."""
from datetime import datetime
from pathlib import Path
import json
import shutil
import unreal

from CityCombat_Common import B, G, compile_bp, hook, link, save, val, var
from Install_StoryMemory import CITY, MAIN, MISSION, PLAYER, WIDGET, L, Story, insert_entry, load
from Install_OwnFrequency import can_use

from Shelter07_Waterworks import (SHELTER, HATCH, SURFACE, ENTRY, EXIT_PANEL, TRIAGE, BREAKER,
                                  ENTRY_YAW, SURFACE_YAW, build_room)
PROJECT = Path(unreal.Paths.project_dir()).resolve()
OUT = PROJECT/'Saved/Shelter07'
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
U = unreal.EditorLoadingAndSavingUtils

def build_story(shelter):
    mission = load(MISSION)
    player = load(PLAYER)
    hud=load(WIDGET)
    var(hud,'ShelterChapter','string','')
    compile_bp(hud)
    title=Story(hud,'DisplayShelterChapter')
    active=title.out(title.call('Engine.KismetStringLibrary.IsEmpty',InString=title.get('ShelterChapter')))
    title.branch(title.not_(active))
    value=title.out(title.call('Engine.KismetTextLibrary.Conv_StringToText',InString=title.get('ShelterChapter')))
    title.do(title.call('UMG.TextBlock.SetText',target=title.get('ChapterText'),InText=value))
    compile_bp(hud)
    graph=G.get_graph_editor_by_name(hud,'EventGraph')
    if not any(n.get_name()=='ShelterChapterTick' for n in graph.list_all_nodes()):
        hook(hud,graph.find_event_node('Tick').find_then_pin(),'DisplayShelterChapter','ShelterChapterTick')
    compile_bp(hud);save(hud)
    var(mission,'ShelterStep','int','0')
    var(mission,'ShelterReturnGoalAt','real','0')
    compile_bp(mission)
    shelter_class = B.generated_class(shelter).get_path_name()
    def condition(g,step):
        return g.branch(g.compare('EqualEqual',g.get('ShelterStep'),step))
    def transfer(g,point,yaw):
        node = g.do(g.call('Engine.Actor.K2_TeleportTo',target=g.get('Player'),
                          DestLocation=L(point),DestRotation=f'(Pitch=0,Yaw={yaw},Roll=0)'))
        g.branch(g.out(node))
        g.do(g.call('Engine.Controller.SetControlRotation',target=g.pc(),
                    NewRotation=g.math('MakeRotator',Roll=0.,Pitch=0.,Yaw=yaw)))
    focus = {HATCH:'ShelterFocusHatch', TRIAGE:'ShelterFocusTriage',
             BREAKER:'ShelterFocusBreaker', EXIT_PANEL:'ShelterFocusExit'}
    for point,name in focus.items():
        can_use(Story(mission,name),point)
    compile_bp(mission)
    def prompt(g,point,text,default):
        g.do(g.own(focus[point]))
        target=g.math('SelectString',A=text,B=default,bPickA=g.get('FrequencyCanUse'))
        g.branch(g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=g.get('Objective'),B=target)))
        g.goal(target,point)
    def chapter(g):
        chapter=g.math('SelectString',A='РЕЗЕРВНОЕ ПИТАНИЕ',B='УБЕЖИЩЕ 07',
                       bPickA=g.compare('GreaterEqual',g.get('ShelterStep'),3))
        g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('StoryHUD'),
                    PropertyName='ShelterChapter',Value=chapter))
    # Preserve the existing mission result long enough for it to be read.
    g=Story(mission,'ShelterTick')
    gate=g.branch(g.compare('EqualEqual',g.get('ShelterStep'),0))
    g.set('ShelterReturnGoalAt',g.num('Add',g.now(),3.5));g.set('ShelterStep',1)
    g.cursor=gate.find_else_pin()
    g.branch(g.num('GreaterEqual',g.now(),g.get('ShelterReturnGoalAt')))
    chapter(g)
    outside=g.num('Greater',g.axis(g.position(g.get('Player')),'Z'),1950.)
    progress=g.both(g.compare('GreaterEqual',g.get('ShelterStep'),2),g.compare('LessEqual',g.get('ShelterStep'),4))
    reenter=g.branch(g.both(outside,progress))
    prompt(g,HATCH,'F · вернуться в убежище','УБЕЖИЩЕ 07 · вернись к люку в насосном дворе')
    g.cursor=reenter.find_else_pin()
    for step,point,text,default in (
        (1,HATCH,'F · спуститься в убежище','УБЕЖИЩЕ 07 · люк у водонапорной башни'),
        (2,TRIAGE,'F · проверить медицинские запасы','УБЕЖИЩЕ 07 · осмотри лазарет'),
        (3,BREAKER,'F · включить резервное питание','РЕЗЕРВНОЕ ПИТАНИЕ · щиток в нижней радиорубке'),
        (4,EXIT_PANEL,'F · подняться к водонапорной башне','Питание восстановлено · выход в насосный двор'),
        (5,HATCH,'F · вернуться в убежище','УБЕЖИЩЕ 07 · питание восстановлено'),
    ):
        step_branch=condition(g,step)
        prompt(g,point,text,default)
        g.cursor=step_branch.find_else_pin()
    g=Story(mission,'ShelterUse')
    g.branch(g.num('GreaterEqual',g.now(),g.get('ShelterReturnGoalAt')))
    outside=g.num('Greater',g.axis(g.position(g.get('Player')),'Z'),1950.)
    progress=g.both(g.compare('GreaterEqual',g.get('ShelterStep'),2),g.compare('LessEqual',g.get('ShelterStep'),4))
    reenter=g.branch(g.both(outside,progress))
    can_use(g,HATCH);g.branch(g.get('FrequencyCanUse'));transfer(g,ENTRY,ENTRY_YAW)
    g.cursor=reenter.find_else_pin()
    for step,point in ((1,HATCH),(2,TRIAGE),(3,BREAKER),(4,EXIT_PANEL),(5,HATCH)):
        step_branch=condition(g,step)
        can_use(g,point);g.branch(g.get('FrequencyCanUse'))
        if step==1:
            transfer(g,ENTRY,ENTRY_YAW);g.set('ShelterStep',2);g.goal('УБЕЖИЩЕ 07 · осмотри лазарет',TRIAGE)
        elif step==2:
            g.set('ShelterStep',3);g.goal('РЕЗЕРВНОЕ ПИТАНИЕ · щиток в нижней радиорубке',BREAKER)
        elif step==3:
            placed=g.out(g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=shelter_class)))
            g.branch(g.valid(placed))
            n=g.node(g.e.add_call_function_node(shelter_class+'.EnableShelterPower'))
            val(n.find_self_pin(),placed);g.do(n)
            g.sound('/Game/Combat/CyborgModes/S_ModeSelect',L(BREAKER),.65)
            g.set('ShelterStep',4);g.goal('Питание восстановлено · выход в насосный двор',EXIT_PANEL)
        elif step==4:
            transfer(g,SURFACE,SURFACE_YAW);g.set('ShelterStep',5);g.goal('УБЕЖИЩЕ 07 · питание восстановлено',HATCH)
        else:
            transfer(g,ENTRY,ENTRY_YAW);g.set('ShelterStep',4);g.goal('Питание восстановлено · выход в насосный двор',EXIT_PANEL)
        g.cursor=step_branch.find_else_pin()
    compile_bp(mission)
    for name,action in (('FrequencyTick','ShelterTick'),('FrequencyUse','ShelterUse')):
        def prepend(g,old,tag):
            valid=g.branch(g.valid(g.get('Player')))
            done=g.branch(g.pget('FrequencyFinished'));done.rename(tag)
            g.do(g.own(action))
            for p in old:
                link(valid.find_else_pin(),p)
                link(done.find_else_pin(),p)
        insert_entry(mission,name,'ShelterAfterFrequency',prepend)
    graph=G.get_graph_editor_by_name(player,'Nav_DrawHUD')
    gate=next(n for n in graph.list_all_nodes() if n.get_name()=='OwnFrequencyEndHUD')
    g=Story(player);g.e=graph
    pin=gate.find_condition_pin()
    pin.break_pin_links()
    val(pin,g.both(g.get('FrequencyFinished'),g.both(g.not_(g.get('NavMapOpen')),g.not_(g.get('StoryGoalActive')))))
    for bp in (mission,player):
        compile_bp(bp)
        save(bp)

def install():
    OUT.mkdir(exist_ok=True)
    assert not EDITOR.get_game_world() and not U.get_dirty_map_packages()
    backup=PROJECT/'Saved/Backups/Shelter07'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for package in (CITY,MISSION,PLAYER,WIDGET,SHELTER):
        relative=Path('Content')/(package[6:]+('.umap' if package==CITY else '.uasset'))
        source=PROJECT/relative
        if source.exists():
            dest=backup/relative
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)
    assert LEVELS.load_level(CITY)
    shelter=build_room()
    placed=next((a for a in ACTORS.get_all_level_actors() if a.get_actor_label()=='CITY_Shelter07'),None)
    if placed is None:
        placed=ACTORS.spawn_actor_from_class(B.generated_class(shelter),unreal.Vector(),unreal.Rotator())
        placed.set_actor_label('CITY_Shelter07');placed.set_folder_path('CITY/Waterworks')
    placed.set_folder_path('CITY/Waterworks')
    build_story(shelter)
    assert U.save_map(EDITOR.get_editor_world(),CITY)
    (OUT/'Installed.json').write_text(json.dumps({'backup':str(backup),'mission':MISSION,'map':CITY,
          'blueprint':SHELTER,'hatch':HATCH,'triage':TRIAGE,'breaker':BREAKER},indent=2),encoding='utf8')

if __name__=='__main__':
    install()

