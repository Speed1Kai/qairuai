"""Readable Russian Omega subtitles above the visor, without engine duplication."""
import unreal,json,shutil
from pathlib import Path
from datetime import datetime
from CityCombat_Common import A,B,G,Graph,compile_bp,save,var,pin,val,link,components,hook
import Archive_AuthoringHelpers as H
GUIDE='/Game/LabTutorial/OmegaGuide/BP_OmegaGuide'
WIDGET='/Game/Story/DemoIntro/WBP_OmegaCaption'
MISSION='/Game/Story/ForeignMemory/BP_ForeignMemory'
def external(g,obj,field,bp):
    n=g.e.add_get_member_variable_node(field,B.generated_class(bp).get_path_name());val(n.find_self_pin(),obj);return pin(n,field,True)
def speech_priority(guide,mission):
    var(guide,'DemoStorySpeaker',B.get_object_reference_type(B.generated_class(mission)),'None');var(guide,'DemoSpeechAllowed','bool','true');compile_bp(guide)
    g=Graph(guide,'Demo_CheckSpeechPriority');g.set('DemoSpeechAllowed',True)
    missing=g.branch(g.math('Not_PreBool',A=g.valid(g.get('DemoStorySpeaker'))));existing=missing.find_else_pin()
    found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(mission).get_path_name()));g.set('DemoStorySpeaker',g.out(found))
    valid=g.branch(g.valid(g.get('DemoStorySpeaker')));link(existing,valid.find_execute_pin())
    until=external(g,g.get('DemoStorySpeaker'),'DialogueUntil',mission)
    g.set('DemoSpeechAllowed',g.math('GreaterEqual_DoubleDouble',A=g.now(),B=until));compile_bp(guide)
    for name in ['Omega_Poll','Omega_Repeat']:
        graph=G.get_graph_editor_by_name(guide,name)
        if any(n.get_name()=='DemoStorySpeechPriority' for n in graph.list_all_nodes()):continue
        entry=graph.find_graph_entry_pin();old=list(entry.list_connected_pins());assert len(old)==1;entry.break_pin_links()
        g=Graph(guide);g.e=graph;g.cursor=entry;call=g.own('Demo_CheckSpeechPriority');call.rename('DemoStorySpeechPriority');g.do(call)
        gate=g.branch(g.get('DemoSpeechAllowed'));link(gate.find_then_pin(),old[0])
    compile_bp(guide)
    for name in B.list_graph_names(mission):
        graph=G.get_graph_editor_by_name(mission,name)
        for n in list(graph.list_all_nodes()):
            sound=n.find_input_pin('NewSound')
            if not sound.is_valid() or '/S_Demo_mission_' not in sound.get_pin_value():continue
            tag='DemoStopGuide_'+n.get_name()
            if any(x.get_name()==tag for x in graph.list_all_nodes()):continue
            incoming=list(n.find_execute_pin().list_connected_pins());assert len(incoming)==1
            n.find_execute_pin().break_pin_links();g=Graph(mission);g.e=graph;g.cursor=incoming[0]
            valid=g.branch(g.valid(g.get('Guide')));valid.rename(tag);link(valid.find_else_pin(),n.find_execute_pin())
            voice=external(g,g.get('Guide'),'Voice',guide);g.do(g.call('Engine.AudioComponent.Stop',target=voice))
            widget=external(g,g.get('Guide'),'DemoCaptionWidget',guide)
            widget_valid=g.branch(g.valid(widget));link(widget_valid.find_else_pin(),n.find_execute_pin())
            g.do(g.call('UMG.Widget.SetRenderOpacity',target=widget,InOpacity=0.));link(g.cursor,n.find_execute_pin())
    compile_bp(mission);save(guide);save(mission)
def install_captions():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    project=Path(unreal.Paths.project_dir()).resolve();out=project/'Saved/DemoIntro/20261118'
    backup=project/'Saved/Backups/DemoOmegaCaptions'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for path in [GUIDE,WIDGET,MISSION]:
        rel=Path('Content')/(path.removeprefix('/Game/')+'.uasset');src=project/rel
        if src.exists():
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    if A.does_asset_exist(WIDGET):bp=A.load_asset(WIDGET)
    else:
        factory=unreal.WidgetBlueprintFactory();factory.set_editor_property('parent_class',unreal.UserWidget)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(WIDGET.rsplit('/',1)[-1],WIDGET.rsplit('/',1)[0],unreal.WidgetBlueprint,factory)
    tree=unreal.find_object(bp,'WidgetTree')
    canvas=unreal.find_object(tree,'CaptionCanvas') or unreal.new_object(unreal.CanvasPanel,outer=tree,name='CaptionCanvas')
    canvas.clear_children();H.assign_object(tree,'RootWidget',canvas);canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    for name,text,y,size,height,color in [('SpeakerText','ОМЕГА',-184,14,22,(.42,.88,.96,1)),('CaptionText','',-104,20,76,(.94,.97,1,1))]:
        obj=unreal.find_object(tree,name) or unreal.new_object(unreal.TextBlock,outer=tree,name=name)
        unreal.get_default_object(B.generated_class(H.helper)).call_method('AssignFlag',args=(obj,unreal.Name('bIsVariable'),True))
        obj.set_text(unreal.Text(text));obj.set_editor_property('justification',unreal.TextJustify.CENTER);obj.set_auto_wrap_text(True)
        font=obj.get_editor_property('font');font.set_editor_property('font_object',A.load_asset('/Engine/EngineFonts/Roboto'));font.set_editor_property('size',size);obj.set_font(font)
        obj.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
        obj.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,1));obj.set_shadow_offset(unreal.Vector2D(1,2))
        slot=canvas.add_child_to_canvas(obj);slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,1),maximum=unreal.Vector2D(.5,1)));slot.set_alignment(unreal.Vector2D(.5,1));slot.set_position(unreal.Vector2D(0,y));slot.set_size(unreal.Vector2D(900,height))
    var(bp,'Caption','string','');compile_bp(bp)
    g=Graph(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
    g.override('Tick');value=g.out(g.call('Engine.KismetTextLibrary.Conv_StringToText',InString=g.get('Caption')))
    g.do(g.call('UMG.TextBlock.SetText',target=g.get('CaptionText'),InText=value));compile_bp(bp);save(bp)
    guide=A.load_asset(GUIDE);var(guide,'DemoCaption','string','');var(guide,'DemoCaptionWidget',B.get_object_reference_type(unreal.UserWidget),'None');compile_bp(guide)
    data=json.loads((project/'SourceAssets/DemoIntro/Dialogue.json').read_text(encoding='utf8'))
    for row in [r for r in data['lines'] if r['role']=='guide']:
        graph=G.get_graph_editor_by_name(guide,'Speak_'+row['id']);tag='DemoCaption_'+row['id']
        if any(n.get_name()==tag for n in graph.list_all_nodes()):continue
        sound=next(n for n in graph.list_all_nodes() if n.find_input_pin('NewSound').is_valid())
        start=sound.find_then_pin();old=list(start.list_connected_pins());assert len(old)==1
        start.break_pin_links();g=Graph(guide);g.e=graph;g.cursor=start
        setter=g.set('DemoCaption',row['text']);setter.rename(tag);link(g.cursor,old[0])
    g=Graph(guide,'Demo_UpdateCaption');g.branch(g.valid(g.pc()))
    missing=g.branch(g.math('Not_PreBool',A=g.valid(g.get('DemoCaptionWidget'))));existing=missing.find_else_pin()
    created=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(bp).get_path_name(),OwningPlayer=g.pc()))
    g.set('DemoCaptionWidget',g.out(created));g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('DemoCaptionWidget'),InOpacity=0.))
    g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('DemoCaptionWidget'),ZOrder=60))
    ready=g.branch(g.valid(g.get('DemoCaptionWidget')));link(existing,ready.find_execute_pin())
    playing=g.out(g.do(g.call('Engine.AudioComponent.IsPlaying',target=g.get('Voice'))))
    input_ok=g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc())))
    shown=g.math('BooleanAND',A=playing,B=input_ok)
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('DemoCaptionWidget'),PropertyName='Caption',Value=g.get('DemoCaption')))
    g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('DemoCaptionWidget'),InOpacity=g.math('SelectFloat',A=1.,B=0.,bPickA=shown)))
    compile_bp(guide)
    graph=G.get_graph_editor_by_name(guide,'EventGraph')
    if not any(n.get_name()=='DemoCaptionAfterPoll' for n in graph.list_all_nodes()):hook(guide,graph.find_event_node('ReceiveTick').find_then_pin(),'Demo_UpdateCaption','DemoCaptionAfterPoll')
    for _,c,name in components(guide):
        if isinstance(c,unreal.AudioComponent) and name=='Voice':c.set_editor_property('suppress_subtitles',True)
    compile_bp(guide);save(guide)
    speech_priority(guide,A.load_asset(MISSION))
    (out/'Captions.json').write_text(json.dumps({'saved':True,'widget':WIDGET,'guide':GUIDE,'backup':str(backup),'engine_subtitles_suppressed':True,'body_bottom_offset':104,'speaker_bottom_offset':184,'story_blocks_repeat':True,'story_preempts_guide':True},ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':install_captions()
