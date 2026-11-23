"""Install the two independent caption channels used by the first mission."""
from pathlib import Path
from datetime import datetime
import json
import re
import shutil
import unreal
from CityCombat_Common import A,B,G,Graph,add,compile_bp,save,var,pin,val,link,hook
from Present_DemoOmegaCaptions import external
import Archive_AuthoringHelpers as H

PROJECT=Path(unreal.Paths.project_dir()).resolve()
ROOT='/Game/Story/Subtitles'
HUD=ROOT+'/WBP_VisorSubtitles'
GUIDE='/Game/LabTutorial/OmegaGuide/BP_OmegaGuide'
MISSION='/Game/Story/ForeignMemory/BP_ForeignMemory'
LEGACY_GUIDE='/Game/Story/DemoIntro/WBP_OmegaCaption'
LEGACY_STORY='/Game/Story/ForeignMemory/WBP_StoryMission'
OUT=PROJECT/'Saved/VisorSubtitles20'
BLUE=(.13,.79,.98,1)
AMBER=(1,.44,.10,1)
V=unreal.Vector2D
SV=unreal.SlateVisibility
ALIGN=unreal.HorizontalAlignment
VERT=unreal.VerticalAlignment
def load(p):
    o=A.load_asset(p);assert o,p;return o
def clr(values):return unreal.LinearColor(*values)
def margin(l,t,r,b):return unreal.Margin(left=l,top=t,right=r,bottom=b)
def klass(bp):return B.generated_class(bp)
def flag(obj):
    unreal.get_default_object(klass(H.helper)).call_method('AssignFlag',args=(obj,unreal.Name('bIsVariable'),True))
def radio_art():
    path=ROOT+'/T_SubtitleRadio'
    if not A.does_asset_exist(path):
        t=unreal.AssetImportTask()
        for key,value in dict(filename=str(PROJECT/'SourceAssets/VisorSubtitles/T_SubtitleRadio.png'),destination_path=ROOT,automated=True,save=False).items():t.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        icon=load(path);icon.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        icon.set_editor_property('lod_group',unreal.TextureGroup.TEXTUREGROUP_UI);save(icon)
    return load(path)
def make_widget():
    if A.does_asset_exist(HUD):bp=load(HUD)
    else:
        factory=unreal.WidgetBlueprintFactory();factory.set_editor_property('parent_class',unreal.UserWidget)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_VisorSubtitles',ROOT,unreal.WidgetBlueprint,factory)
    tree=unreal.find_object(bp,'WidgetTree')
    def make(cls,name,variable=False):
        w=unreal.find_object(tree,name) or unreal.new_object(cls,outer=tree,name=name)
        if isinstance(w,unreal.PanelWidget):w.clear_children()
        if variable:flag(w)
        return w
    def label(name,words,size,color,bold=False,variable=False):
        w=make(unreal.TextBlock,name,variable);w.set_text(words)
        font=w.get_editor_property('font');font.set_editor_property('font_object',load('/Engine/EngineFonts/Roboto'))
        font.set_editor_property('typeface_font_name','Bold' if bold else 'Regular');font.set_editor_property('size',size)
        w.set_font(font);w.set_color_and_opacity(unreal.SlateColor(specified_color=clr(color)))
        w.set_shadow_color_and_opacity(clr((0,0,0,.93)));w.set_shadow_offset(V(1,1))
        w.set_editor_property('justification',unreal.TextJustify.LEFT);return w
    canvas=make(unreal.CanvasPanel,'VisorCanvas');H.assign_object(tree,'RootWidget',canvas)
    canvas.set_visibility(SV.HIT_TEST_INVISIBLE)
    row=make(unreal.HorizontalBox,'Channels')
    slot=canvas.add_child_to_canvas(row)
    slot.set_anchors(unreal.Anchors(minimum=V(.07,1),maximum=V(.93,1)))
    slot.set_offsets(margin(0,-282,0,176))
    for channel,color in (('AI',BLUE),('Radio',AMBER)):
        group=make(unreal.Overlay,channel+'Group',True);group.set_visibility(SV.COLLAPSED)
        col=row.add_child_to_horizontal_box(group)
        col.set_size(unreal.SlateChildSize(size_rule=unreal.SlateSizeRule.FILL,value=1))
        col.set_padding(margin(9,0,9,0))
        sized=make(unreal.SizeBox,channel+'Width');sized.set_width_override(694)
        anch=group.add_child_to_overlay(sized);anch.set_horizontal_alignment(ALIGN.H_ALIGN_CENTER);anch.set_vertical_alignment(VERT.V_ALIGN_BOTTOM)
        border=make(unreal.Border,channel+'Backdrop');sized.add_child(border)
        border.set_brush_color(clr((.010,.018,.023,.74)));border.set_padding(margin(14,8,16,10))
        content=make(unreal.HorizontalBox,channel+'Content');border.add_child(content)
        iconbox=make(unreal.SizeBox,channel+'IconSize');iconbox.set_width_override(43);iconbox.set_height_override(36)
        iconslot=content.add_child_to_horizontal_box(iconbox);iconslot.set_vertical_alignment(VERT.V_ALIGN_TOP);iconslot.set_padding(margin(0,1,11,0))
        if channel=='AI':
            iconbox.add_child(label('AIGlyph','AI',24,color,True))
        else:
            image=make(unreal.Image,'RadioAntenna');image.set_brush_from_texture(radio_art(),False)
            image.set_color_and_opacity(clr(color));iconbox.add_child(image)
        stack=make(unreal.VerticalBox,channel+'Stack');sl=content.add_child_to_horizontal_box(stack)
        sl.set_size(unreal.SlateChildSize(size_rule=unreal.SlateSizeRule.FILL,value=1))
        head=label(channel+'Source','[ОМЕГА]' if channel=='AI' else '[РАДИОСИГНАЛ]',17,color,True,True)
        head.set_auto_wrap_text(True);stack.add_child_to_vertical_box(head)
        body=label(channel+'Body','',25,(.98,.98,.97,1),False,True);body.set_auto_wrap_text(True)
        stack.add_child_to_vertical_box(body).set_padding(margin(0,2,0,0))
    for field in ('AIText','RadioText','SourceName','LastAI','LastRadio','LastSource'):var(bp,field,'string','')
    compile_bp(bp)
    for channel,last in (('AI','LastAI'),('Radio','LastRadio')):
        g=Graph(bp,'Display'+channel);current=g.get(channel+'Text')
        changed=g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=current,B=g.get(last)))
        if channel=='Radio':
            new_source=g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=g.get('SourceName'),B=g.get('LastSource')))
            changed=g.math('BooleanOR',A=changed,B=new_source)
        g.branch(changed);g.set(last,current)
        def settext(name,string):
            text=g.out(g.call('Engine.KismetTextLibrary.Conv_StringToText',InString=string))
            g.do(g.call('UMG.TextBlock.SetText',target=g.get(name),InText=text))
        if channel=='Radio':
            g.set('LastSource',g.get('SourceName'));settext('RadioSource',g.get('SourceName'))
        settext(channel+'Body',current)
        branch=g.branch(g.out(g.call('Engine.KismetStringLibrary.IsEmpty',InString=current)))
        g.do(g.call('UMG.Widget.SetVisibility',target=g.get(channel+'Group'),InVisibility='Collapsed'))
        g.cursor=branch.find_else_pin()
        g.do(g.call('UMG.Widget.SetVisibility',target=g.get(channel+'Group'),InVisibility='HitTestInvisible'))
    compile_bp(bp);save(bp);return bp

def read_lines():
    src=PROJECT/'SourceAssets'
    intro=json.loads((src/'DemoIntro/Dialogue.json').read_text(encoding='utf8'))['lines']
    stations=json.loads((src/'StationSeven/Dialogue.json').read_text(encoding='utf8'))
    rows={r['sound']:r for r in intro}
    for k,row in stations.items():rows['/Game/Story/StationSeven/Audio/S_Station07_'+k]=row
    return rows
def phrases(text):
    if len(text)<76:return text,''
    options=[m.start() for m in re.finditer(r'(?<=[.!?])\s+(?=[А-ЯЁA-Z])',text)]
    if not options:return text,''
    index=min(options,key=lambda i:abs(i-len(text)*.5))
    return text[:index],text[index:].lstrip()
def publish_fields(g,prefix,row,duration):
    first,second=phrases(row['text'])
    g.set(prefix+'First',first);g.set(prefix+'Second',second or first)
    delta=duration*len(first)/len(row['text'])
    g.set(prefix+'Change',g.math('Add_DoubleDouble',A=g.now(),B=delta))
    g.set(prefix+'Until',g.math('Add_DoubleDouble',A=g.now(),B=duration+.22))
def fields(bp,prefix):
    for f in ('First','Second'):var(bp,prefix+f,'string','')
    for f in ('Change','Until'):var(bp,prefix+f,'real','0')
def label_for(raw):
    return {'УБЕЖИЩЕ 07 · МЕДИК':'[РАДИОСИГНАЛ]   МЕДИК · УБЕЖИЩЕ 07',
            'АТЛАС · ПЕЛЕНГАТОР 07':'[ПЕЛЕНГАТОР 07]   АТЛАС',
            'ГОРОДСКОЙ СКАНЕР':'[ГОРОДСКОЙ СКАНЕР]',
            'ТЕРМИНАЛ ЛАБОРАТОРИИ № 2':'[ТЕРМИНАЛ]   ЛАБОРАТОРИЯ № 2'}.get(raw,'[РАДИОСИГНАЛ]   '+raw)
def sound_input(node):
    if node.get_class().get_name()!='K2Node_CallFunction':return None
    return next((p for p in node.list_all_pins() if str(p.get_pin_name())=='NewSound'),None)

def writers(guide,mission,rows):
    fields(guide,'VisorGuide');fields(mission,'VisorAI');fields(mission,'VisorRadio')
    var(mission,'VisorRadioSource','string','')
    radio=add(mission,unreal.AudioComponent,'ExternalRadioVoice','Root')
    radio.set_editor_property('auto_activate',False);radio.set_editor_property('allow_spatialization',False)
    radio.set_editor_property('suppress_subtitles',True)
    compile_bp(guide);compile_bp(mission)
    patched=[]
    for bp in (guide,mission):
        for name in B.list_graph_names(bp):
            e=G.get_graph_editor_by_name(bp,name)
            for sound in list(e.list_all_nodes()):
                q=sound_input(sound)
                if q is None:continue
                path=str(q.get_pin_value()).split('.')[0]
                if path not in rows:continue
                row=rows[path];tag='VisorCue_'+sound.get_name()
                if any(n.get_name()==tag for n in e.list_all_nodes()):continue
                duration=float(load(path).duration)
                g=Graph(bp);g.e=e
                inbound=sound.find_execute_pin()
                if bp==mission and row['speaker']!='ОМЕГА':
                    # The original story writer stopped Omega immediately before SetSound.
                    # Bypass only that pre-emption for an external source.
                    queue=[sound];seen=set();until=None
                    while queue and until is None:
                        n=queue.pop(0)
                        if n.get_name() in seen:continue
                        seen.add(n.get_name())
                        if n.get_class().get_name()=='K2Node_VariableSet' and n.find_input_pin('DialogueUntil').is_valid():until=n;break
                        p=n.find_execute_pin()
                        if p.is_valid():queue.extend(t.get_owning_node() for t in p.list_connected_pins())
                    assert until is not None,(name,path)
                    start=until.find_then_pin();start.break_pin_links();inbound.break_pin_links()
                    g.cursor=start;first=g.set('VisorRadioSource',label_for(row['speaker']));first.rename(tag)
                    publish_fields(g,'VisorRadio',row,duration)
                    [playpin]=sound.find_then_pin().list_connected_pins();play=playpin.get_owning_node()
                    assert play.find_input_pin('StartTime').is_valid(),name
                    for node in (sound,play):
                        target=node.find_self_pin();target.break_pin_links();val(target,g.get('ExternalRadioVoice'))
                else:
                    # Multiple exec paths may converge here when a guide is not present.
                    incoming=list(inbound.list_connected_pins());assert incoming,(name,path)
                    inbound.break_pin_links();g.cursor=incoming[0]
                    prefix='VisorGuide' if bp==guide else 'VisorAI'
                    marker=g.set(prefix+'Until',0.);marker.rename(tag)
                    for other in incoming[1:]:link(other,marker.find_execute_pin())
                    publish_fields(g,prefix,row,duration)
                link(g.cursor,inbound);patched.append([str(name),path])
    # Permit guide speech during external radio. Story Omega alone has priority over guide Omega.
    g=Graph(guide,'Demo_CheckSpeechPriority');g.set('DemoSpeechAllowed',True)
    missing=g.branch(g.math('Not_PreBool',A=g.valid(g.get('DemoStorySpeaker'))));old=missing.find_else_pin()
    found=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=klass(mission).get_path_name()));g.set('DemoStorySpeaker',g.out(found))
    ok=g.branch(g.valid(g.get('DemoStorySpeaker')));link(old,ok.find_execute_pin())
    until=external(g,g.get('DemoStorySpeaker'),'VisorAIUntil',mission)
    g.set('DemoSpeechAllowed',g.math('GreaterEqual_DoubleDouble',A=g.now(),B=until))
    return patched

def wire_presenter(mission,guide,bp):
    var(mission,'VisorCaptions',B.get_object_reference_type(klass(bp)),'None')
    compile_bp(mission)
    g=Graph(mission,'Visor_RefreshCaptions');g.branch(g.valid(g.pc()))
    missing=g.branch(g.math('Not_PreBool',A=g.valid(g.get('VisorCaptions'))));existing=missing.find_else_pin()
    made=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=klass(bp).get_path_name(),OwningPlayer=g.pc()))
    g.do(g.call('Engine.KismetSystemLibrary.SetObjectPropertyByName',Object=g.self('Voice'),PropertyName='VisorCaptions',Value=g.out(made)));g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('VisorCaptions'),ZOrder=78))
    ready=g.branch(g.valid(g.get('VisorCaptions')));link(existing,ready.find_execute_pin())
    def setstr(field,value):
        g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('VisorCaptions'),PropertyName=field,Value=value))
    def current(prefix,get):
        second=g.math('GreaterEqual_DoubleDouble',A=g.now(),B=get(prefix+'Change'))
        line=g.math('SelectString',A=get(prefix+'Second'),B=get(prefix+'First'),bPickA=second)
        active=g.math('Less_DoubleDouble',A=g.now(),B=get(prefix+'Until'))
        return g.math('SelectString',A=line,B='',bPickA=active)
    setstr('RadioText',current('VisorRadio',g.get));setstr('SourceName',g.get('VisorRadioSource'))
    has_ai=g.branch(g.math('Less_DoubleDouble',A=g.now(),B=g.get('VisorAIUntil')))
    setstr('AIText',current('VisorAI',g.get));ai_written=g.cursor
    g.cursor=has_ai.find_else_pin()
    has_guide=g.branch(g.valid(g.get('Guide')));no_guide=has_guide.find_else_pin()
    enabled=g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))));disabled=enabled.find_else_pin()
    setstr('AIText',current('VisorGuide',lambda f:external(g,g.get('Guide'),f,guide)));guide_written=g.cursor
    g.cursor=no_guide;clear=g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('VisorCaptions'),PropertyName='AIText',Value='')
    g.do(clear);link(disabled,clear.find_execute_pin())
    call=g.node(g.e.add_call_function_node(klass(bp).get_path_name()+'.DisplayAI'))
    val(call.find_self_pin(),g.get('VisorCaptions'));g.do(call)
    link(ai_written,call.find_execute_pin());link(guide_written,call.find_execute_pin())
    call=g.node(g.e.add_call_function_node(klass(bp).get_path_name()+'.DisplayRadio'));val(call.find_self_pin(),g.get('VisorCaptions'));g.do(call)
    # Sequence after the existing mission tick, even at stage zero in the capsule.
    compile_bp(mission)
    eg=G.get_graph_editor_by_name(mission,'EventGraph')
    if not any(n.get_name()=='VisorCaptionTick' for n in eg.list_all_nodes()):
        hook(mission,eg.find_event_node('ReceiveTick').find_then_pin(),'Visor_RefreshCaptions','VisorCaptionTick')
    # Clear the interrupted AI line as well as its audio to prevent a stale page
    # returning after a shorter story cue. A radio transmission remains independent.
    g=Graph(mission,'Visor_StopGuide')
    g.branch(g.valid(g.get('Guide')))
    g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('Guide'),PropertyName='VisorGuideUntil',Value=0.))
    g.do(g.call('Engine.AudioComponent.Stop',target=external(g,g.get('Guide'),'Voice',guide)))
    compile_bp(mission)
    rows=read_lines()
    for name in B.list_graph_names(mission):
        e=G.get_graph_editor_by_name(mission,name)
        for sound in list(e.list_all_nodes()):
            q=sound_input(sound)
            if q is None or rows.get(str(q.get_pin_value()).split('.')[0],{}).get('speaker')!='ОМЕГА':continue
            tag='VisorStopGuide_'+sound.get_name()
            if any(n.get_name()==tag for n in e.list_all_nodes()):continue
            source=sound.find_then_pin();after=list(source.list_connected_pins())
            source.break_pin_links();g=Graph(mission);g.e=e;g.cursor=source
            stop=g.own('Visor_StopGuide');stop.rename(tag);g.do(stop)
            for out_pin in after:link(g.cursor,out_pin)
    g=Graph(mission,'Visor_ClearCaptions')
    g.set('VisorAIUntil',0.);g.set('VisorRadioUntil',0.)
    g.do(g.call('Engine.AudioComponent.Stop',target=g.get('ExternalRadioVoice')))
    g.do(g.call('Engine.AudioComponent.Stop',target=g.get('Voice')))
    g.do(g.own('Visor_StopGuide'))
    compile_bp(mission)
    for name,field in [('RetryCheckpoint','Failed'),('CheckFailure','Failed')]:
        if name not in map(str,B.list_graph_names(mission)):continue
        e=G.get_graph_editor_by_name(mission,name)
        if any(n.get_name()=='VisorClearOnReset' for n in e.list_all_nodes()):continue
        target=next((n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_VariableSet' and n.find_input_pin(field).is_valid()),None)
        if target:
            source=target.find_then_pin();after=list(source.list_connected_pins());source.break_pin_links()
            g=Graph(mission);g.e=e;g.cursor=source;n=g.own('Visor_ClearCaptions');n.rename('VisorClearOnReset');g.do(n)
            for p in after:link(g.cursor,p)

def install():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    OUT.mkdir(exist_ok=True);back=PROJECT/'Saved/Backups/VisorSubtitles'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    targets=[GUIDE,MISSION,LEGACY_GUIDE,LEGACY_STORY,HUD]
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert not dirty.intersection(targets),dirty.intersection(targets)
    for pkg in targets:
        rel=Path('Content')/(pkg[6:]+'.uasset');src=PROJECT/rel
        if src.exists():
            dest=back/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    bp=make_widget();guide=load(GUIDE);mission=load(MISSION)
    patched=writers(guide,mission,read_lines());compile_bp(guide);compile_bp(mission)
    wire_presenter(mission,guide,bp)
    for path,names in ((LEGACY_GUIDE,('SpeakerText','CaptionText')),(LEGACY_STORY,('SpeakerText','DialogueText'))):
        old=load(path);tree=unreal.find_object(old,'WidgetTree')
        for name in names:unreal.find_object(tree,name).set_visibility(SV.COLLAPSED)
        compile_bp(old);save(old)
    for obj in (guide,mission):compile_bp(obj);save(obj)
    (OUT/'Install.json').write_text(json.dumps(dict(backup=str(back),paths=targets,patched=patched),ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':install()




