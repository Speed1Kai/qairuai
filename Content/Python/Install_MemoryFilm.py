"""Replace the Foreign Memory hologram with the validated external MP4."""
import unreal,json,shutil,struct
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import Install_StoryMemory as ST
from CityCombat_Common import A,B,G,Graph,add,components,compile_bp,save,var,pin,val,link
ROOT='/Game/Story/ForeignMemory/Film'
PROJECT=Path(unreal.Paths.project_dir()).resolve()
SAVED=PROJECT/'Saved/MemoryFilm'
MOVIE=PROJECT/'Content/Movies/ForeignMemory_Evacuation.mp4'
MP=ROOT+'/MP_MemoryFilm';FM=ROOT+'/FM_MemoryFilm';MT=ROOT+'/MT_MemoryFilm';MAT=ROOT+'/M_MemoryFilm_UI';WBP=ROOT+'/WBP_MemoryFilm'
def load(p):
    o=A.load_asset(p);assert o,p;return o
def asset(path,cls,factory):
    if A.does_asset_exist(path):return load(path)
    folder,name=path.rsplit('/',1)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,cls,factory)
def movie_assets():
    assert MOVIE.is_file() and MOVIE.stat().st_size>100000
    raw=MOVIE.read_bytes();assert b'avc1' in raw and b'mp4a' in raw,'Expected H.264 video and AAC audio'
    player=asset(MP,unreal.MediaPlayer,unreal.MediaPlayerFactoryNew());player.close();player.set_editor_property('play_on_open',True);player.set_looping(False);save(player)
    source=asset(FM,unreal.FileMediaSource,unreal.FileMediaSourceFactoryNew());source.set_file_path(str(MOVIE));source.set_editor_property('precache_file',False);save(source)
    tex=asset(MT,unreal.MediaTexture,unreal.MediaTextureFactoryNew());tex.set_editor_property('media_player',player);tex.set_media_player(player);tex.set_editor_property('new_style_output',True);tex.set_editor_property('auto_clear',True);tex.set_editor_property('clear_color',unreal.LinearColor(0,0,0,1));tex.update_resource();save(tex)
    mat=asset(MAT,unreal.Material,unreal.MaterialFactoryNew());edit=unreal.MaterialEditingLibrary;edit.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
    node=edit.create_material_expression(mat,unreal.MaterialExpressionTextureSample);node.set_editor_property('texture',tex);node.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    assert edit.connect_material_property(node,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR);edit.recompile_material(mat);save(mat)
    f=unreal.WidgetBlueprintFactory();f.set_editor_property('parent_class',unreal.UserWidget)
    bp=asset(WBP,unreal.WidgetBlueprint,f);tree=unreal.find_object(bp,'WidgetTree')
    def w(cls,n):return unreal.find_object(tree,n) or unreal.new_object(cls,outer=tree,name=n)
    canvas=w(unreal.CanvasPanel,'FilmCanvas');canvas.clear_children();ST.H.assign_object(tree,'RootWidget',canvas);canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    def fill(widget):
        slot=canvas.add_child_to_canvas(widget);slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(1,1)));slot.set_offsets(unreal.Margin(0))
    black=w(unreal.Border,'FilmBlack');black.set_brush_color(unreal.LinearColor(0,0,0,1));fill(black)
    scale=w(unreal.ScaleBox,'FilmAspect');scale.set_stretch(unreal.Stretch.SCALE_TO_FIT);fill(scale)
    image=w(unreal.Image,'FilmImage');image.set_brush_from_material(mat)
    size=w(unreal.SizeBox,'Film1080');size.set_width_override(1920.);size.set_height_override(1080.);size.set_content(image);scale.set_content(size)
    hint=w(unreal.TextBlock,'SkipFilm');hint.set_text('ПРОБЕЛ · ПРОПУСТИТЬ')
    font=hint.get_editor_property('font');font.set_editor_property('font_object',load('/Engine/EngineFonts/Roboto'));font.set_editor_property('size',12);hint.set_font(font)
    hint.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.5,.65,.69,.7)))
    slot=canvas.add_child_to_canvas(hint);slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(1,1),maximum=unreal.Vector2D(1,1)));slot.set_alignment(unreal.Vector2D(1,1));slot.set_position(unreal.Vector2D(-26,-12));slot.set_size(unreal.Vector2D(220,24))
    compile_bp(bp);save(bp)
    return player,source

class Film(ST.Story):
    def finish(self):self.do(self.own('FinishMemoryFilm'))
    def restore_input(self):
        self.branch(self.valid(self.get('Player')))
        self.pcall('Story_RestoreDamage')
        locked=self.branch(self.get('InputLocked'));skip=locked.find_else_pin()
        self.do(self.call('Engine.Controller.SetIgnoreMoveInput',target=self.pc(),bNewMoveInput=False));self.do(self.call('Engine.Controller.SetIgnoreLookInput',target=self.pc(),bNewLookInput=False))
        done=self.set('InputLocked',False);link(skip,done.find_execute_pin())

def install():
    SAVED.mkdir(parents=True,exist_ok=True)
    report_path=SAVED/'Install.json'
    if report_path.exists() and json.loads(report_path.read_text(encoding='utf8')).get('enabled') is False:
        import Remove_MemoryFilm
        return Remove_MemoryFilm.install()
    if not report_path.exists():
        backup=PROJECT/'Saved/Backups/MemoryFilm'/datetime.now().strftime('%Y%m%d_%H%M%S')
        for path,ext in [(ST.MISSION,'.uasset')]:
            rel=Path(path.removeprefix('/Game/')+ext);dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content'/rel,dst)
        report_path.write_text(json.dumps({'backup':str(backup),'complete':False}),encoding='utf8')
    else:backup=Path(json.loads(report_path.read_text(encoding='utf8'))['backup'])
    ST.LINES={r['id']:r for r in json.loads((PROJECT/'SourceAssets/ForeignMemory/Lines.json').read_text(encoding='utf8'))}
    A.make_directory(ROOT);player,source=movie_assets();bp=load(ST.MISSION)
    for n,t,d in [('FilmActive','bool','false'),('FilmStarted','bool','false'),('FilmFailed','bool','false'),('ArchiveUnlocked','bool','false'),('FilmWorldWasEnabled','bool','true'),('FilmStartAt','real','0'),('FilmAge','real','0'),('FilmLastPosition','real','0')]:var(bp,n,t,d)
    var(bp,'FilmPlayer',B.get_object_reference_type(unreal.MediaPlayer),player.get_path_name())
    var(bp,'FilmTexture',B.get_object_reference_type(unreal.MediaTexture),load(MT).get_path_name())
    var(bp,'FilmWidget',B.get_object_reference_type(unreal.UserWidget),'None')
    sound=add(bp,unreal.MediaSoundComponent,'FilmAudio','Root')
    # SetMediaPlayer changes a transient pointer; persist the template binding too.
    # Start the synth only after binding it, so its generator keeps a valid queue.
    sound.set_editor_property('media_player',player);sound.set_media_player(player)
    sound.set_editor_property('is_ui_sound',True);sound.set_editor_property('allow_spatialization',False);sound.set_editor_property('auto_activate',False)
    for name in ('CloseMemoryFilm','FinishMemoryFilm','FailMemoryFilm'):
        if name not in map(str,B.list_graph_names(bp)):G.create_and_edit_function_graph(bp,name)
    compile_bp(bp)
    g=Film(bp,'CloseMemoryFilm')
    g.do(g.call('AudioMixer.SynthComponent.Stop',target=g.get('FilmAudio')))
    active=g.branch(g.get('FilmActive'));skip=active.find_else_pin()
    g.do(g.call('Engine.GameplayStatics.SetEnableWorldRendering',bEnable=g.get('FilmWorldWasEnabled')))
    close=g.do(g.call('MediaAssets.MediaPlayer.Close',target=g.get('FilmPlayer')));link(skip,close.find_execute_pin())
    check=g.branch(g.valid(g.get('FilmWidget')));skip=check.find_else_pin()
    g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('FilmWidget')))
    reset=g.set('FilmWidget','None');link(skip,reset.find_execute_pin());g.set('FilmActive',False)
    g.branch(g.valid(g.get('StoryHUD')));g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('StoryHUD'),InOpacity=1.))
    g=Film(bp,'FinishMemoryFilm');g.branch(g.get('FilmActive'));g.do(g.own('CloseMemoryFilm'));g.set('Beat',2);g.next(0.)
    g=Film(bp,'FailMemoryFilm');g.set('FilmFailed',True);g.do(g.own('CloseMemoryFilm'));g.restore_input();g.set('Stage',3);g.set('Beat',0)
    g.pset('StoryBusy',False,'Bool');g.goal('Лаборатория № 2 · F — повторить чтение записи',ST.TERMINAL)
    g.set('Speaker','ОМЕГА');g.set('Dialogue','Не удалось прочитать запись. Переподключись к терминалу.');g.set('DialogueUntil',g.num('Add',g.now(),8.))
    compile_bp(bp)

    g=Film(bp,'BeginMemory');g.set('Stage',5);g.set('Beat',0);g.set('MemoryStarted',True);g.set('ArchiveUnlocked',True)
    g.set('Objective','Восстановление архива эвакуации');g.set('MemoryCaption','');g.set('Dialogue','');g.set('Speaker','')
    g.visibility('MemoryRoot',False);g.pcall('Story_ProtectMemory')
    g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=True));g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=True));g.set('InputLocked',True)
    g.do(g.call('Engine.AudioComponent.Stop',target=g.get('Voice')))
    g.do(g.call('AudioMixer.SynthComponent.Stop',target=g.get('FilmAudio')))
    g.do(g.call('MediaAssets.MediaPlayer.Close',target=g.get('FilmPlayer')))
    g.set('FilmStarted',False);g.set('FilmFailed',False);g.set('FilmStartAt',g.now());g.set('FilmAge',0.);g.set('FilmLastPosition',0.)
    prior=g.do(g.call('Engine.GameplayStatics.GetEnableWorldRendering'));g.set('FilmWorldWasEnabled',g.out(prior));g.set('FilmActive',True)
    made=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(load(WBP)).get_path_name(),OwningPlayer=g.pc()));g.set('FilmWidget',g.out(made))
    g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('FilmWidget'),ZOrder=1000))
    g.do(g.call('MediaAssets.MediaSoundComponent.SetMediaPlayer',target=g.get('FilmAudio'),NewMediaPlayer=g.get('FilmPlayer')))
    g.do(g.call('AudioMixer.SynthComponent.Start',target=g.get('FilmAudio')))
    g.do(g.call('MediaAssets.MediaTexture.SetMediaPlayer',target=g.get('FilmTexture'),NewMediaPlayer=g.get('FilmPlayer')))
    g.do(g.call('MediaAssets.MediaTexture.UpdateResource',target=g.get('FilmTexture')))
    opened=g.do(g.call('MediaAssets.MediaPlayer.OpenSource',target=g.get('FilmPlayer'),MediaSource=source.get_path_name()))
    ok=g.branch(g.out(opened));g.cursor=ok.find_else_pin();g.do(g.own('FailMemoryFilm'))

    g=Film(bp,'MemoryTick')
    aftermath=g.branch(g.compare('EqualEqual',g.get('Beat'),3));more=aftermath.find_else_pin()
    g.branch(g.ready());g.do(g.own('CompleteMission'))
    g.cursor=more;restore=g.branch(g.compare('EqualEqual',g.get('Beat'),2));movie=restore.find_else_pin()
    g.restore_input();g.pset('StoryBusy',False,'Bool');g.say('After');g.set('Beat',3)
    g.cursor=movie;g.branch(g.get('FilmActive'));g.set('FilmAge',g.num('Subtract',g.now(),g.get('FilmStartAt')))
    expired=g.branch(g.num('Greater',g.get('FilmAge'),28.));keep=expired.find_else_pin();g.do(g.own('FailMemoryFilm'))
    g.cursor=keep;bad=g.branch(g.out(g.call('MediaAssets.MediaPlayer.HasError',target=g.get('FilmPlayer'))));keep=bad.find_else_pin();g.do(g.own('FailMemoryFilm'))
    g.cursor=keep;playing=g.branch(g.out(g.call('MediaAssets.MediaPlayer.IsPlaying',target=g.get('FilmPlayer'))));stopped=playing.find_else_pin()
    g.set('FilmStarted',True)
    position=g.out(g.call('MediaAssets.MediaPlayer.GetTime',target=g.get('FilmPlayer')))
    g.set('FilmLastPosition',g.out(g.call('Engine.KismetMathLibrary.GetTotalSeconds',A=position)))
    g.cursor=stopped;started=g.branch(g.get('FilmStarted'));waiting=started.find_else_pin()
    busy=g.math('BooleanOR',A=g.out(g.call('MediaAssets.MediaPlayer.IsBuffering',target=g.get('FilmPlayer'))),B=g.out(g.call('MediaAssets.MediaPlayer.IsPreparing',target=g.get('FilmPlayer'))))
    g.branch(g.not_(busy));ended=g.branch(g.num('Greater',g.get('FilmLastPosition'),13.5));early=ended.find_else_pin();g.finish()
    g.cursor=early;g.do(g.own('FailMemoryFilm'))
    g.cursor=waiting;g.branch(g.num('Greater',g.get('FilmAge'),8.));g.do(g.own('FailMemoryFilm'))
    compile_bp(bp)
    # Keep the story overlay out of the burned-in movie subtitles.
    e=G.get_graph_editor_by_name(bp,'RefreshHUD');g=Film(bp);g.e=e
    for node in list(e.list_all_nodes()):
        if node.get_node_title()!='Set Render Opacity':continue
        target=list(node.find_self_pin().list_connected_pins())
        if not target or target[0].get_owning_node().get_node_title()!='Get StoryHUD':continue
        opacity=pin(node,'InOpacity');opacity.break_pin_links();val(opacity,g.math('SelectFloat',A=0.,B=1.,bPickA=g.get('FilmActive')))
    def marked(node,tag):
        return node.get_name().startswith(tag)
    e=G.get_graph_editor_by_name(bp,'RetryCheckpoint')
    if not any(marked(n,'MemoryFilmRetryCleanup') for n in e.list_all_nodes()):
        entry=e.find_graph_entry_pin();old=list(entry.list_connected_pins());assert old
        entry.break_pin_links();g=Film(bp);g.e=e;g.cursor=entry
        n=g.own('CloseMemoryFilm');n.rename('MemoryFilmRetryCleanup_'+uuid4().hex[:12]);g.do(n);g.set('ArchiveUnlocked',False)
        for p in old:link(g.cursor,p)
    # A decode failure leaves the unlocked archive retryable without another fight.
    e=G.get_graph_editor_by_name(bp,'RequestRecovery')
    if not any(marked(n,'MemoryFilmArchiveRetry') for n in e.list_all_nodes()):
        target=next(n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_VariableSet' and n.find_input_pin('Stage').is_valid() and n.find_input_pin('Stage').get_pin_value()=='4')
        incoming=list(target.find_execute_pin().list_connected_pins());target.find_execute_pin().break_pin_links()
        g=Film(bp);g.e=e;gate=g.e.add_branch_node();gate.rename('MemoryFilmArchiveRetry_'+uuid4().hex[:12]);val(pin(gate,'Condition'),g.get('ArchiveUnlocked'))
        for p in incoming:link(p,gate.find_execute_pin())
        link(gate.find_else_pin(),target.find_execute_pin());g.cursor=gate.find_then_pin();g.do(g.own('BeginMemory'))
    compile_bp(bp)
    g=Film(bp);end=g.override('ReceiveEndPlay');g.do(g.own('CloseMemoryFilm'))
    existing=[n for n in g.e.list_all_nodes() if n.get_class().get_name()=='K2Node_InputKey' and str(n.get_editor_property('input_key').get_editor_property('key_name'))=='SpaceBar']
    if not existing:
        menu=next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|F9'))
        event=g.e.create_node_from_name(menu,unreal.Vector2D(),[]);key=unreal.Key();key.set_editor_property('key_name','SpaceBar');event.set_editor_property('input_key',key);event.set_editor_property('bConsumeInput',False)
        g.cursor=pin(event,'Pressed',True);g.branch(g.get('FilmActive'));g.do(g.own('FinishMemoryFilm'))
    compile_bp(bp);save(bp)
    data={'complete':True,'backup':str(backup),'movie':str(MOVIE),'media_path':source.get_editor_property('file_path'),'assets':[MP,FM,MT,MAT,WBP],'bp':ST.MISSION,'duration':15,'skip':'Space','retry':'F9','render_world_during_film':True}
    report_path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    return data
if __name__=='__main__':install()
