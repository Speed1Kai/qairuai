"""Apply the repair steps and current-context speech on top of the existing mission."""
from datetime import datetime
from pathlib import Path
import json
import shutil

import unreal
from CityCombat_Common import A, B, G, Graph, add, components, compile_bp, link, save, val
from Install_StoryMemory import GUIDE, L, MISSION, Story, load
from Install_OwnFrequency import SECOND, METAL
from Install_SecondVoice import PANEL
from Install_VisorSubtitles import sound_input

PROJECT=Path(unreal.Paths.project_dir()).resolve()
NATIVE='Final_Protocol.FinalProtocolRepairPass'
RADIO='/Game/Story/SecondVoice/Audio/'

def editable(bp, name):
    graph=Graph(bp)
    graph.e=G.get_graph_editor_by_name(bp,name)
    return graph

def before(g, target, tag, insert):
    if any(node.get_name()==tag for node in g.e.list_all_nodes()):
        return
    sources=list(target.list_connected_pins())
    assert len(sources)==1,(tag,len(sources))
    target.break_pin_links()
    g.cursor=sources[0]
    insert(g,tag)
    link(g.cursor,target)

def setup_tuning(mission, first=True, second=True):
    def guard(g,tag,circuit,point):
        if circuit==1:
            g.set('SecondVoiceInputUsed',True)
        begin=g.do(g.call(NATIVE+'.BeginOrConsumeSignalTuning',Mission=g.self('Voice'),Player=g.get('Player'),
                          Circuit=circuit,Panel=L(point)))
        begin.rename(tag)
        allowed=g.branch(g.out(begin))
        g.cursor=allowed.find_then_pin()
    if first:
        g=editable(mission,'FrequencyUse')
        target=next(node for node in g.e.list_all_nodes()
                    if node.get_class().get_name()=='K2Node_VariableSet'
                    and any(str(p.get_pin_name())=='FrequencyStep' and str(p.get_pin_value())=='2' for p in node.list_all_pins()))
        before(g,target.find_execute_pin(),'TuneStation07',lambda graph,tag:guard(graph,tag,0,SECOND))
    if second:
        g=editable(mission,'SecondVoiceUse')
        target=next(node for node in g.e.list_all_nodes() if str(node.get_node_title())=='Release Local Line'
                    or str(node.get_node_title())=='ReleaseLocalLine')
        before(g,target.find_execute_pin(),'TuneTelephone',lambda graph,tag:guard(graph,tag,1,PANEL))
    for method,changes in (
        ('FrequencyTick',{'F · передать местную частоту убежищу':'F · настроить передатчик'}),
        ('SecondVoiceGuide',{'F · открыть местную линию':'F · настроить местную линию',
                             'Аппаратная · включи местную линию у стойки':'Аппаратная · настрой связь у стойки'}),
    ):
        if method not in map(str,B.list_graph_names(mission)):
            continue
        for node in G.get_graph_editor_by_name(mission,method).list_all_nodes():
            for p in node.list_all_pins():
                prior=p.get_pin_value()
                if prior in changes:
                    val(p,changes[prior])

def guide_context(guide):
    def insert(g,tag):
        call=g.do(g.call(NATIVE+'.RefreshGuideContext',Guide=g.self('Voice'),Player=g.player()))
        call.rename(tag)
    for fn in ('Omega_Poll','Omega_Repeat'):
        g=editable(guide,fn)
        entry=g.e.find_graph_entry_pin()
        [previous]=entry.list_connected_pins()
        before(g,previous,'RefreshRelevantOmegaCue',insert)

def route_external(mission):
    count=0
    for name in B.list_graph_names(mission):
        g=editable(mission,name)
        for sound in list(g.e.list_all_nodes()):
            input_pin=sound_input(sound)
            if not input_pin or not str(input_pin.get_pin_value()).startswith(RADIO):
                continue
            tag='RouteRadio_'+sound.get_name()
            if any(node.get_name()==tag for node in g.e.list_all_nodes()):
                continue
            current=sound
            stack=[current]
            visited=set()
            deadline=None
            while stack and deadline is None:
                node=stack.pop()
                if node.get_name() in visited:
                    continue
                visited.add(node.get_name())
                if node.get_class().get_name()=='K2Node_VariableSet' and node.find_input_pin('DialogueUntil').is_valid():
                    deadline=node
                    break
                entry=node.find_execute_pin()
                if entry.is_valid():
                    stack.extend(p.get_owning_node() for p in entry.list_connected_pins())
            assert deadline,(name,sound.get_name())
            p=deadline.find_then_pin()
            following=list(p.list_connected_pins())
            # Terminate the obsolete pre-emption path and play on the radio component.
            for target in following:
                target.break_pin_links()
            input_exec=sound.find_execute_pin()
            input_exec.break_pin_links()
            link(p,input_exec)
            [next_pin]=sound.find_then_pin().list_connected_pins()
            play=next_pin.get_owning_node()
            assert play.find_input_pin('StartTime').is_valid()
            radio=g.get('ExternalRadioVoice')
            radio.get_owning_node().rename(tag)
            for node in (sound,play):
                self_pin=node.find_self_pin()
                self_pin.break_pin_links()
                val(self_pin,radio)
            count+=1
    return count

def setup_audio(guide,mission):
    guide_context(guide)
    g=editable(mission,'Visor_RefreshCaptions')
    [next_pin]=g.e.find_graph_entry_pin().list_connected_pins()
    def insert(graph,tag):
        node=graph.do(graph.call(NATIVE+'.BalanceStoryVoices',Mission=graph.self('Voice'),DeltaSeconds=graph.dt()))
        node.rename(tag)
    before(g,next_pin,'MixIndependentVoices',insert)
    for _,component,name in components(mission):
        if name=='ExternalRadioVoice':
            component.set_low_pass_filter_enabled(True)
            component.set_low_pass_filter_frequency(3900.)
            component.set_volume_multiplier(.94)
    return route_external(mission)

def hardware(mission):
    cylinder=load('/Engine/BasicShapes/Cylinder')
    cube=load('/Engine/BasicShapes/Cube')
    steel=load(METAL)
    indicator=load('/Game/LabTutorial/Industrial/M_AmberIndicator')
    for bank,points,yaw in (
        ('Tune07',((35428,87347,2267),(35428,87384,2267)),0.),
        ('TunePhone',((32012,81751,1540),(32043,81751,1540)),90.),
    ):
        for index,point in enumerate(points):
            knob=add(mission,unreal.StaticMeshComponent,bank+str(index),'Root')
            knob.set_static_mesh(cylinder)
            knob.set_material(0,steel)
            knob.set_collision_profile_name('NoCollision')
            knob.set_editor_property('relative_location',unreal.Vector(*point))
            knob.set_editor_property('relative_scale3d',unreal.Vector(.15,.15,.10))
            knob.set_editor_property('relative_rotation',unreal.Rotator(pitch=90,yaw=yaw))
            tick=add(mission,unreal.StaticMeshComponent,bank+'Mark'+str(index),bank+str(index))
            tick.set_static_mesh(cube)
            tick.set_material(0,indicator)
            tick.set_collision_profile_name('NoCollision')
            tick.set_editor_property('relative_location',unreal.Vector(0,20,51))
            tick.set_editor_property('relative_scale3d',unreal.Vector(.18,.45,.06))

def install():
    assert unreal.load_class(None,'/Script/'+NATIVE)
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    paths=(MISSION,GUIDE,'/Game/FrontEnd/Lvl_MainMenu')
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert not dirty.intersection(paths),dirty.intersection(paths)
    backup=PROJECT/'Saved/Backups/RepairPass'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    for path in paths:
        rel=Path('Content')/(path[6:]+('.umap' if '/Lvl_' in path else '.uasset'))
        dst=backup/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PROJECT/rel,dst)
    mission,guide=load(MISSION),load(GUIDE)
    hardware(mission)
    compile_bp(mission)
    setup_tuning(mission)
    routes=setup_audio(guide,mission)
    for bp in (mission,guide):
        compile_bp(bp)
        save(bp)
    from Install_FrontEnd import install_menu
    install_menu(PROJECT/'SourceAssets/FrontEnd')
    result=PROJECT/'Saved/RepairPass/Applied.json'
    result.parent.mkdir(exist_ok=True)
    result.write_text(json.dumps({'backup':str(backup),'saved':list(paths),'radio_routes':routes},indent=2),encoding='utf-8')

if __name__=='__main__':
    install()



