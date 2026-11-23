"""Native video prologue, followed by the existing laboratory capsule intro.

The bootstrap map keeps laboratory BeginPlay, timers and Sequencer dormant until
the movie ends. No runtime Python, duplicated cinematic, or forced game pause.
"""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,Graph,pin,val,link,compile_bp,save,add,V
import Archive_AuthoringHelpers as H
ROOT='/Game/Cinematics/Prologue';LEVEL=ROOT+'/Lvl_Prologue'
LAB='/Game/Lvl_LabTutorial'
project=os.path.abspath(unreal.Paths.project_dir())
source=r'C:\Users\nuris\Downloads\gemini_generated_video_6ae385c1.mp4'
report={'saved':False,'gameplay_tested':False,'assets':[]}
backup=os.path.join(project,'Saved','Backups','VideoPrologue',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True);report['backup']=backup

def asset(name,cls,factory):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 obj=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,cls,factory)
 if not obj:raise RuntimeError('Asset creation failed '+name)
 return obj

def blueprint(name,parent):
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent)
 return asset(name,unreal.Blueprint,f)

class Flow(Graph):
 def __init__(self,bp,name=None):
  super().__init__(bp)
  if name:
   self.e=G.get_graph_editor_by_name(bp,name) if name in map(str,B.list_graph_names(bp)) else G.create_and_edit_function_graph(bp,name)
   self.e.remove_nodes([n for n in self.e.list_all_nodes() if n.get_class().get_name() not in ('K2Node_FunctionEntry','K2Node_FunctionResult')])
   self.cursor=self.e.find_graph_entry_pin()
 def event(self,name):
  n=self.e.find_event_node(name)
  if not n:
   token=name.removeprefix('Receive')
   choices=[x for x in self.e.list_available_nodes([]) if x.startswith(('Добавитьсобытие|','AddEvent|')) and x.split('|')[-1].replace(' ','') in (token,'Событие'+token,'Event'+token)]
   if len(choices)!=1:raise RuntimeError('Event choices '+name+': '+str(choices))
   n=self.node(self.e.create_node_from_name(choices[0],unreal.Vector2D(),[]))
  self.cursor=pin(n,'then',True);return n
 def pc(self):return self.out(self.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 def callself(self,name):return self.node(self.e.add_call_function_node(B.generated_class(self.bp).get_path_name()+'.'+name))
 def seq(self):
  choices=[x for x in self.e.list_available_nodes([]) if x.split('|')[-1] in ('Sequence','Последовательность')]
  if len(choices)!=1:raise RuntimeError('Sequence choices '+str(choices))
  return self.node(self.e.create_node_from_name(choices[0],unreal.Vector2D(),[]))

def member(bp,name,kind,default):
 if name not in map(str,B.list_member_variable_names(bp)):
  if not G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,kind,default):raise RuntimeError('Variable failed '+name)

def fill(canvas,widget):
 s=canvas.add_child_to_canvas(widget)
 s.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(1,1)))
 s.set_offsets(unreal.Margin(0));return s

try:
 if not os.path.isfile(source):raise RuntimeError('Source video is missing')
 for name in ('DefaultEngine.ini','DefaultGame.ini'):
  shutil.copy2(os.path.join(project,'Config',name),os.path.join(backup,name))
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Could not preserve current level')
 movie_dir=os.path.join(project,'Content','Movies');os.makedirs(movie_dir,exist_ok=True)
 destination=os.path.join(movie_dir,'FinalProtocol_Prologue.mp4')
 if os.path.isfile(destination):shutil.copy2(destination,os.path.join(backup,'FinalProtocol_Prologue.mp4'))
 shutil.copy2(source,destination)
 A.make_directory(ROOT)
 media=asset('MP_Prologue',unreal.MediaPlayer,unreal.MediaPlayerFactoryNew())
 media.set_editor_property('play_on_open',True);media.set_looping(False);media.close();save(media)
 file=asset('FM_Prologue',unreal.FileMediaSource,unreal.FileMediaSourceFactoryNew())
 file.set_file_path(destination);file.set_editor_property('precache_file',False);save(file)
 texture=asset('MT_Prologue',unreal.MediaTexture,unreal.MediaTextureFactoryNew())
 texture.set_media_player(media);texture.set_editor_property('new_style_output',True);texture.set_editor_property('auto_clear',True)
 texture.set_editor_property('clear_color',unreal.LinearColor(0,0,0,1));save(texture)
 mat=asset('M_PrologueScreen',unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI)
 mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
 tex=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
 tex.set_editor_property('texture',texture);tex.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
 if not M.connect_material_property(tex,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Media material connection failed')
 M.recompile_material(mat);save(mat)

 f=unreal.WidgetBlueprintFactory();f.set_editor_property('parent_class',unreal.UserWidget)
 wbp=asset('WBP_Prologue',unreal.WidgetBlueprint,f)
 tree=unreal.find_object(wbp,'WidgetTree')
 def w(cls,name):return unreal.find_object(tree,name) or unreal.new_object(cls,outer=tree,name=name)
 canvas=w(unreal.CanvasPanel,'MovieCanvas');canvas.clear_children();H.assign_object(tree,'RootWidget',canvas)
 canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
 bg=w(unreal.Border,'BlackBackground');bg.set_brush_color(unreal.LinearColor(0,0,0,1));fill(canvas,bg)
 scale=w(unreal.ScaleBox,'MovieAspect');scale.set_stretch(unreal.Stretch.SCALE_TO_FIT);fill(canvas,scale)
 image=w(unreal.Image,'MovieImage');image.set_brush_from_material(mat)
 size=w(unreal.SizeBox,'MovieSize');size.set_width_override(1920.);size.set_height_override(1080.)
 size.set_content(image);scale.set_content(size)
 hint=w(unreal.TextBlock,'SkipHint');hint.set_text(unreal.Text('SPACE  /  ПРОПУСТИТЬ'))
 font=hint.get_editor_property('font');font.set_editor_property('font_object',A.load_asset('/Engine/EngineFonts/Roboto'));font.set_editor_property('size',13);hint.set_font(font)
 hint.set_editor_property('justification',unreal.TextJustify.RIGHT)
 hint.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.65,.83,.87,.75)))
 hint.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,1));hint.set_shadow_offset(unreal.Vector2D(1,1))
 slot=canvas.add_child_to_canvas(hint);slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(1,1),maximum=unreal.Vector2D(1,1)))
 slot.set_alignment(unreal.Vector2D(1,1));slot.set_position(unreal.Vector2D(-36,-28));slot.set_size(unreal.Vector2D(360,32))
 compile_bp(wbp);save(wbp)

 bp=blueprint('BP_ProloguePlayer',unreal.Actor)
 audio=add(bp,unreal.MediaSoundComponent,'MovieAudio')
 audio.set_media_player(media);audio.set_editor_property('is_ui_sound',True)
 audio.set_editor_property('allow_spatialization',False);audio.set_editor_property('auto_activate',True)
 for name,kind,default in [
  ('MoviePlayer',B.get_object_reference_type(unreal.MediaPlayer),media.get_path_name()),
  ('MovieWidget',B.get_object_reference_type(unreal.UserWidget),'None'),
  ('MovieAge',B.get_basic_type_by_name('real'),'0'),
  ('ExitAge',B.get_basic_type_by_name('real'),'0'),
  ('bStarted',B.get_basic_type_by_name('bool'),'false'),
  ('bEnding',B.get_basic_type_by_name('bool'),'false'),
  ('bLeaving',B.get_basic_type_by_name('bool'),'false')]:member(bp,name,kind,default)
 compile_bp(bp)
 g=Flow(bp,'BeginLaboratoryTransition')
 g.branch(g.math('Not_PreBool',A=g.get('bEnding')));g.set('bEnding',True);g.set('ExitAge',0.)
 compile_bp(bp)
 g=Flow(bp)
 g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay')
 g.set('MovieAge',0.);g.set('bStarted',False);g.set('bEnding',False);g.set('bLeaving',False)
 g.do(g.call('UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly',PlayerController=g.pc(),bFlushInput=True))
 create=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(wbp).get_path_name(),OwningPlayer=g.pc()))
 g.set('MovieWidget',g.out(create));g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('MovieWidget'),ZOrder=1000))
 g.do(g.call('MediaAssets.MediaSoundComponent.SetMediaPlayer',target=g.get('MovieAudio'),NewMediaPlayer=g.get('MoviePlayer')))
 opened=g.do(g.call('MediaAssets.MediaPlayer.OpenSource',target=g.get('MoviePlayer'),MediaSource=file.get_path_name()))
 failed=g.branch(g.out(opened));g.cursor=failed.find_else_pin();g.do(g.callself('BeginLaboratoryTransition'))
 tick=g.event('ReceiveTick');dt=pin(tick,'DeltaSeconds',True)
 g.branch(g.math('Not_PreBool',A=g.get('bLeaving')))
 g.set('MovieAge',g.math('Add_DoubleDouble',A=g.get('MovieAge'),B=dt))
 ending=g.branch(g.get('bEnding'));normal=ending.find_else_pin()
 # Fade to black before opening the laboratory. Its own Sequencer fade takes
 # over after level travel; the capsule animation starts only at that point.
 g.set('ExitAge',g.math('Add_DoubleDouble',A=g.get('ExitAge'),B=dt))
 opacity=g.math('FClamp',Value=g.math('Subtract_DoubleDouble',A=1.,B=g.math('Divide_DoubleDouble',A=g.get('ExitAge'),B=.3)),Min=0.,Max=1.)
 g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('MovieWidget'),InOpacity=opacity))
 g.branch(g.math('GreaterEqual_DoubleDouble',A=g.get('ExitAge'),B=.3));g.set('bLeaving',True)
 g.do(g.call('MediaAssets.MediaPlayer.Close',target=g.get('MoviePlayer')))
 g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('MovieWidget')))
 g.do(g.call('Engine.GameplayStatics.OpenLevel',LevelName=LAB,bAbsolute=True,Options=''))
 g.cursor=normal;seq=g.seq();g.do(seq)
 # First branch handles skip immediately, independently of codec readiness.
 g.cursor=pin(seq,'then_0',True)
 skip=g.out(g.call('Engine.PlayerController.WasInputKeyJustPressed',target=g.pc(),Key='(KeyName="SpaceBar")'))
 skipbranch=g.branch(skip);g.do(g.callself('BeginLaboratoryTransition'))
 g.cursor=pin(seq,'then_1',True)
 playing=g.branch(g.out(g.call('MediaAssets.MediaPlayer.IsPlaying',target=g.get('MoviePlayer'))));stopped=playing.find_else_pin()
 g.set('bStarted',True)
 g.cursor=stopped
 started=g.branch(g.get('bStarted'));waiting=started.find_else_pin()
 busy=g.math('BooleanOR',A=g.out(g.call('MediaAssets.MediaPlayer.IsBuffering',target=g.get('MoviePlayer'))),B=g.out(g.call('MediaAssets.MediaPlayer.IsPreparing',target=g.get('MoviePlayer'))))
 g.branch(g.math('Not_PreBool',A=busy));g.do(g.callself('BeginLaboratoryTransition'))
 g.cursor=waiting;g.branch(g.math('Greater_DoubleDouble',A=g.get('MovieAge'),B=12.));g.do(g.callself('BeginLaboratoryTransition'))
 # Last-resort watchdog also covers a decoder which stalls after playback starts.
 # Ten-second source + generous twenty-second allowance for local decoding.
 g.cursor=pin(seq,'then_0',True)
 # Keep skip intact: add watchdog to a second Sequence output by chaining its
 # pure condition into the existing skip Branch as OR, avoiding extra timers.
 condition=pin(skipbranch,'Condition');condition.break_pin_links()
 val(condition,g.math('BooleanOR',A=skip,B=g.math('Greater_DoubleDouble',A=g.get('MovieAge'),B=30.)))
 compile_bp(bp);save(bp)

 gm=blueprint('BP_PrologueGameMode',unreal.GameModeBase);compile_bp(gm)
 cdo=unreal.get_default_object(B.generated_class(gm));cdo.set_editor_property('default_pawn_class',None);cdo.set_editor_property('start_players_as_spectators',True);save(gm)
 # Create only a new empty map, never replace the laboratory or its level script.
 levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
 if A.does_asset_exist(LEVEL):
  unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
  actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
  for actor in actors.get_all_level_actors():
   if actor.get_actor_label()=='PROLOGUE_VideoPlayer':actors.destroy_actor(actor)
 else:
  if not levels.new_level(LEVEL):raise RuntimeError('Could not create prologue map')
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 world.get_world_settings().set_editor_property('default_game_mode',B.generated_class(gm))
 actor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(B.generated_class(bp),V((0,0,0)))
 actor.set_actor_label('PROLOGUE_VideoPlayer')
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Prologue map save failed')
 report.update(saved=True,map=LEVEL,laboratory=LAB,file=destination,relative_media_path=file.get_editor_property('file_path'),duration_seconds=10.006,skip_key='Space',audio=True)
 report['assets']=list(map(str,A.list_assets(ROOT,recursive=True)))
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','video_prologue_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Prologue authoring incomplete; see Saved/video_prologue_report.json')
