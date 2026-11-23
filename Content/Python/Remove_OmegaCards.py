"""Retire the old Omega cards, keeping subtitles and short interaction hints."""
import json
from datetime import datetime
import shutil
from pathlib import Path

import unreal
from CityCombat_Common import A,B,G,Graph,compile_bp,save,val
from Install_StoryMemory import PLAYER,MISSION,load

PROJECT=Path(unreal.Paths.project_dir()).resolve()
HINTS=('/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt')
VISOR='/Game/Characters/PlayerVisor/WBP_PlayerVisor'
LEGACY='/Game/Story/DemoIntro/WBP_OmegaCaption'
ARCHIVE='/Game/LabTutorial/FirstFloor/BP_Floor01Archive'
NEW_SCANNER='Городская охрана. Позывной «Сентинел». Допуск подтверждён. Проход разрешён.'
OLD_SCANNER='Городская охрана. Сентинел. Допуск сотрудника подтверждён. Проход разрешён.'

def properties(bp):
    for name in B.list_graph_names(bp):
        graph=G.get_graph_editor_by_name(bp,name)
        for n in graph.list_all_nodes():
            for p in n.list_all_pins():
                yield graph,n,p

def replace_text(bp, edits):
    updated=[]
    for _,n,p in properties(bp):
        try:
            value=str(p.get_pin_value())
        except Exception:
            continue
        new=edits.get(value)
        if new is not None:
            assert p.set_pin_value(new),(n.get_name(),value)
            updated.append(value)
    return updated

def apply(out):
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    backup=PROJECT/'Saved/Backups/OmegaCards'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    paths=(*HINTS,VISOR,LEGACY,ARCHIVE,PLAYER,MISSION)
    for path in paths:
        rel=Path('Content')/(path.removeprefix('/Game/')+'.uasset')
        target=backup/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PROJECT/rel,target)

    bps={p:load(p) for p in paths}
    report={'backup':str(backup),'widgets':{},'texts':{}}
    for path in HINTS:
        bp=bps[path]
        tree=unreal.find_object(bp,'WidgetTree')
        for name in ('OmegaHologlass','SubsystemLabel','Heading','OmegaSystemLabel','OmegaNeuralLabel','OmegaSignalLabel'):
            widget=unreal.find_object(tree,name)
            assert widget,name
            widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
        body=unreal.find_object(tree,'MessageBody')
        body.set_editor_property('justification',unreal.TextJustify.CENTER)
        slot=body.get_editor_property('slot')
        if isinstance(slot,unreal.CanvasPanelSlot):
            slot.set_position(unreal.Vector2D(65,118))
            slot.set_size(unreal.Vector2D(690,40))
        filtered=[]
        graph=G.get_graph_editor_by_name(bp,'EventGraph')
        tag='OnlyPersistentDeviceHint'
        existing=any(n.get_name()==tag for n in graph.list_all_nodes())
        if not existing:
            for n in list(graph.list_all_nodes()):
                opacity=n.find_input_pin('InOpacity')
                if not opacity.is_valid() :
                    continue
                original=list(opacity.list_connected_pins())
                if not original:continue
                assert len(original)==1
                g=Graph(bp)
                g.e=graph
                opacity.break_pin_links()
                focused=g.math('Greater_DoubleDouble',A=g.get('HUDLifetime'),B=60.)
                opacity_expr=g.math('SelectFloat',A=original[0],B=0.,bPickA=focused)
                opacity_expr.get_owning_node().rename(tag)
                val(opacity,opacity_expr)
                filtered.append(n.get_name())
            assert filtered,(path,'no opacity animation pins')
        report['widgets'][path]={'plain_prompt':True,'filtered':filtered}

    tree=unreal.find_object(bps[LEGACY],'WidgetTree')
    root=unreal.find_object(tree,'CaptionCanvas')
    assert root
    root.set_visibility(unreal.SlateVisibility.COLLAPSED)
    tree=unreal.find_object(bps[VISOR],'WidgetTree')
    title=unreal.find_object(tree,'VisorDesignation')
    assert title
    title.set_text(unreal.Text('ФИНАЛЬНЫЙ ПРОТОКОЛ'))
    bp=bps[ARCHIVE]
    old='Резервный контур лаборатории активен. Лифт Л-1 ведёт на поверхность, но его питание отключено. Архитектор сохранил оборудование, уничтожив тех, кто им пользовался.'
    report['texts']['archive']=len(replace_text(bp,{old:old.replace('Архитектор','Атлас')}))
    report['texts']['navigation']=len(replace_text(bps[PLAYER],{'H — повторить сообщение Омеги':''}))
    # The existing intro cue is an interface signal. Synchronize the text in
    # both the legacy story fields and the active subtitle presenter.
    updates={OLD_SCANNER:NEW_SCANNER}
    report['texts']['scanner']=len(replace_text(bps[MISSION],updates))
    assert all(key in report['texts'] for key in ('archive','navigation','scanner')),report
    for bp in bps.values():
        compile_bp(bp)
    for bp in bps.values():
        save(bp)
    (out/'OmegaCards.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')






if __name__=='__main__':
    out=PROJECT/'Saved/SecondVoice'
    out.mkdir(exist_ok=True)
    apply(out)
