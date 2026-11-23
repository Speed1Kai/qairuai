"""Aim-based interaction targets, reticle, lift panel gates, and animated archive wall."""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,pin,val,link,components,add,compile_bp,save,Graph
import Archive_AuthoringHelpers as H
ROOT='/Game/LabTutorial/FocusedInteraction';saved=os.path.abspath(unreal.Paths.project_saved_dir())
report={'saved':False,'gameplay_tested':False,'steps':[]}
backup=os.path.join(saved,'Backups','FocusedInteraction',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);report['backup']=backup
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def event(self,name):
  q=self.e.find_event_node(name)
  if not q:
   token=name.removeprefix('Receive');opts=[x for x in self.e.list_available_nodes([]) if x.startswith('Добавитьсобытие|') and x.split('|')[-1].replace(' ','') in [token,'Событие'+token]]
   q=self.e.create_node_from_name(opts[0],unreal.Vector2D(),[])
  self.cursor=pin(q,'then',True);return q
def member(bp,n,t,d=''):
 if n not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(n,t,str(d))
 B.set_blueprint_variable_instance_editable(bp,n,True)
def backup_asset(path):
 src=os.path.join(unreal.Paths.project_content_dir(),path.removeprefix('/Game/')+'.uasset')
 if os.path.isfile(src):shutil.copy2(src,os.path.join(backup,os.path.basename(src)))
def asset(name,cls=unreal.Blueprint):
 path=ROOT+'/'+name;backup_asset(path)
 if A.does_asset_exist(path):return A.load_asset(path)
 f=unreal.BlueprintFactory() if cls==unreal.Blueprint else unreal.MaterialFactoryNew()
 if cls==unreal.Blueprint:f.set_editor_property('parent_class',unreal.Actor)
 return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,cls,f)
def simple_material(name,color,emissive=1.):
 m=asset(name,unreal.Material);M.delete_all_material_expressions(m);m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,0,0);c.set_editor_property('constant',unreal.LinearColor(*[v*emissive for v in color],1));M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(m);save(m);return m
def mesh(bp,name,p,scale,mat,parent='Root'):
 c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,mat);c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(scale));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');return c
def suppress_hints(bp,all_hints=False):
 e=G.get_graph_editor_by_name(bp,'EventGraph')
 for n in e.list_all_nodes():
  if not n.find_input_pin('ZOrder').is_valid():continue
  target=list(n.find_self_pin().list_connected_pins());suppress=all_hints
  if target:
   origin=target[0].get_owning_node();wp=origin.find_input_pin('WidgetType')
   suppress=suppress or (wp.is_valid() and any(s in wp.get_pin_value() for s in ['WBP_InteractionHint','WBP_ElevatorPrompt']))
  if suppress:
   incoming=list(n.find_execute_pin().list_connected_pins());outgoing=list(n.find_then_pin().list_connected_pins());n.find_execute_pin().break_pin_links();n.find_then_pin().break_pin_links()
   for a in incoming:
    for b in outgoing:link(a,b)
def gate_key(bp,key,fields):
 backup_asset(bp.get_path_name().split('.')[0])
 for field in fields:member(bp,field,B.get_basic_type_by_name('bool'),'false')
 compile_bp(bp);g=Flow(bp)
 for n in list(g.e.list_all_nodes()):
  if n.get_class().get_name()!='K2Node_InputKey' or str(n.get_node_title())!=key:continue
  start=pin(n,'Pressed',True);old=list(start.list_connected_pins());start.break_pin_links();g.cursor=start;condition=g.get(fields[0])
  for field in fields[1:]:condition=g.math('BooleanOR',A=condition,B=g.get(field))
  guard=g.branch(condition)
  for p in old:link(guard.find_then_pin(),p)
 suppress_hints(bp,'Freight' in bp.get_name());compile_bp(bp);save(bp)
def pc(g):return g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
def player(g):return g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
try:
 A.make_directory(ROOT)
 # Preserve a native copy of the current scene before replacing the workstations.
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+(backup+'/Lvl_LabTutorial.umap').replace('\\','/')+'" SILENT=true')
 cyan=simple_material('M_FocusCyan',(.03,.7,.86),2.);dim=simple_material('M_StandbyCyan',(.01,.13,.17),1.)
 # The reticle belongs to the existing visor, so V automatically shows/hides it.
 visor=A.load_asset('/Game/Characters/PlayerVisor/WBP_PlayerVisor');backup_asset(visor.get_path_name().split('.')[0]);tree=unreal.find_object(visor,'WidgetTree');canvas=unreal.find_object(tree,'VisorCanvas')
 for name,x,y,sx,sy in [('ReticleLeft',-7,0,4,1),('ReticleRight',7,0,4,1),('ReticleTop',0,-7,1,4),('ReticleBottom',0,7,1,4),('ReticleDot',0,0,2,2)]:
  o=unreal.find_object(tree,name) or unreal.new_object(unreal.Border,outer=tree,name=name)
  unreal.get_default_object(B.generated_class(H.helper)).call_method('AssignFlag',args=(o,unreal.Name('bIsVariable'),False))
  o.set_brush_color(unreal.LinearColor(.4,.95,1,.85));sl=canvas.add_child_to_canvas(o);sl.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,.5),maximum=unreal.Vector2D(.5,.5)));sl.set_alignment(unreal.Vector2D(.5,.5));sl.set_position(unreal.Vector2D(x,y));sl.set_size(unreal.Vector2D(sx,sy))
 compile_bp(visor);save(visor);report['steps'].append('reticle')
 # One reusable world-space affordance actor, traced on Camera at 10 Hz.
 focus=asset('BP_InteractionFocus');add(focus,unreal.SceneComponent,'Root')
 box=add(focus,unreal.BoxComponent,'FocusCollider','Root');box.set_box_extent(V((42,12,42)));box.set_collision_profile_name('Custom');box.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY);box.set_collision_response_to_all_channels(next(getattr(unreal.CollisionResponseType,n) for n in dir(unreal.CollisionResponseType) if n.lower().endswith('ignore')));box.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA,next(getattr(unreal.CollisionResponseType,n) for n in dir(unreal.CollisionResponseType) if n.lower().endswith('block')));box.set_editor_property('generate_overlap_events',False)
 bright=add(focus,unreal.SceneComponent,'BrightFrame','Root');bright.set_visibility(False,True)
 for signx in (-1,1):
  for signz in (-1,1):
   for k,(p,s) in enumerate([((signx*37,-14,signz*41),(.15,.025,.02)),((signx*44,-14,signz*34),(.02,.025,.16))]):
    mesh(focus,'Idle%d%d%d'%(signx,signz,k),p,s,dim);mesh(focus,'Aim%d%d%d'%(signx,signz,k),p,s,cyan,'BrightFrame')
 for n,t,d in [('Device',B.get_object_reference_type(unreal.Actor),'None'),('FocusField',B.get_basic_type_by_name('name'),'bFocusedInteraction'),('InteractionText',B.get_basic_type_by_name('string'),'[F]  ВКЛЮЧИТЬ'),('bFocused',B.get_basic_type_by_name('bool'),'false'),('Prompt',B.get_object_reference_type(unreal.UserWidget),'None')]:member(focus,n,t,d)
 compile_bp(focus);g=Flow(focus);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay');g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.1));g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('BrightFrame'),bNewVisibility=False,bPropagateToChildren=True))
 g.event('ReceiveTick');g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=player(g))))
 camera=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));start=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=camera));rot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=camera));direction=g.math('GetForwardVector',InRot=rot);end=g.math('Add_VectorVector',A=start,B=g.math('Multiply_VectorFloat',A=direction,B=1000.))
 trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=start,End=end,TraceChannel='TraceTypeQuery2',bTraceComplex=False,DrawDebugType='None',bIgnoreSelf=False))
 hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'))
 distance=g.math('Vector_Distance',V1=g.out(g.call('Engine.Actor.K2_GetActorLocation')),V2=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=player(g))))
 aimed=g.math('BooleanAND',A=g.math('EqualEqual_ObjectObject',A=g.out(hit,'HitComponent'),B=g.get('FocusCollider')),B=g.math('LessEqual_DoubleDouble',A=distance,B=320.))
 g.branch(g.math('NotEqual_BoolBool',A=aimed,B=g.get('bFocused')));g.set('bFocused',aimed);g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('BrightFrame'),bNewVisibility=g.get('bFocused'),bPropagateToChildren=True));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Device'))));g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=g.get('Device'),PropertyName=g.get('FocusField'),Value=g.get('bFocused')))
 branch=g.branch(g.get('bFocused'));lost=branch.find_else_pin();hint=A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint');created=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(hint).get_path_name(),OwningPlayer=pc(g)));widget=g.out(created);g.set('Prompt',widget)
 for prop,text in [('HUDTitle','ОБЪЕКТ ДОСТУПЕН'),('HUDMessage',g.get('InteractionText'))]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=prop,Value=text))
 g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=widget,PropertyName='HUDLifetime',Value=86400.));g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=65))
 g.cursor=lost;g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Prompt'))));g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('Prompt')))
 compile_bp(focus);save(focus);report['steps'].append('focus_actor')
 # Modify the existing actions, keeping the complete ride, power and story graphs.
 lift=A.load_asset('/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional');gate_key(lift,'F',['FocusCabButton','FocusLowerButton','FocusUpperButton'])
 power=A.load_asset('/Game/LabTutorial/Basement/BP_BuildingPower');gate_key(power,'E',['bFocusedInteraction'])
 for i in range(1,7):gate_key(A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i),'F',['bFocusedInteraction'])
 report['steps'].append('input_gates')
 # A looping archive film synthesized by one unlit shader: skyline, blast, collapse, dust.
 film=asset('M_WorldCollapseFilm',unreal.Material);M.delete_all_material_expressions(film);film.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);film.set_editor_property('two_sided',True)
 uv=M.create_material_expression(film,unreal.MaterialExpressionTextureCoordinate,0,0);time=M.create_material_expression(film,unreal.MaterialExpressionTime,0,120)
 inputs=[]
 for name in ['UV','Clock','Start','Playing']:
  ci=unreal.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
 custom=M.create_material_expression(film,unreal.MaterialExpressionCustom,260,0);custom.set_editor_property('inputs',inputs);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
 custom.set_editor_property('code','''
float t=fmod(max(Clock-Start,0),26)*Playing;
float2 p=float2(UV.x,1-UV.y);float shake=sin(t*61)*sin(t*37)*smoothstep(7,10,t)*.003;
p.x+=shake;float3 col=lerp(float3(.02,.045,.065),float3(.14,.23,.25),p.y);
float haze=sin(p.x*21+p.y*8+t*.15)*sin(p.x*7-p.y*17+t*.11)*.025;col+=haze;
float blast=exp(-abs(t-8.4)*7);col+=float3(3,1.8,.8)*blast;
for(int i=0;i<26;i++){
 float seed=frac(sin(i*73.173+3)*43758.54);float cx=(i+.5)/26;
 float height=.12+seed*.48;float fall=smoothstep(10+seed*5,19+seed*3,t);
 float x=cx+(p.y-.13)*fall*(seed-.5)*.9;float top=.13+height*(1-fall*.85);
 float body=step(abs(p.x-x),.012+seed*.006)*step(.13,p.y)*step(p.y,top);
 float win=step(.72,frac(p.x*370))*step(.48,frac(p.y*170))*step(.22,seed)*step(t,11+seed*3);
 col=lerp(col,float3(.018,.025,.028)+win*float3(.38,.44,.31),body);
 float fire=exp(-pow((p.x-cx)*75,2))*exp(-pow((p.y-.15)*18,2))*smoothstep(9,13,t)*(1+.4*sin(t*18+i));col+=fire*float3(.8,.17,.025);
}
float cloud=smoothstep(12,19,t)*smoothstep(.65,.05,p.y)*( .5+.2*sin(p.x*14+t*.5)+.15*sin(p.x*37-t*.7));col=lerp(col,float3(.19,.12,.085),saturate(cloud));
col*=.88+.12*sin(UV.y*1100);col+=step(.998,frac(sin(dot(UV,float2(114,71))+floor(t*15))*43758.5))*.13;
col*=1-smoothstep(23,25.5,t);return col*(8+Playing*12);
''')
 M.connect_material_expressions(uv,'',custom,'UV');M.connect_material_expressions(time,'',custom,'Clock')
 for n,d in [('Start',0.),('Playing',0.)]:
  q=M.create_material_expression(film,unreal.MaterialExpressionScalarParameter,0,240 if n=='Start' else 360);q.set_editor_property('parameter_name',n);q.set_editor_property('default_value',d);M.connect_material_expressions(q,'',custom,n)
 M.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(film);save(film)
 board=asset('BP_WorldArchiveBoard');add(board,unreal.SceneComponent,'Root');metal=A.load_asset('/Game/LabTutorial/Industrial/M_DoorArmor')
 mesh(board,'BackHousing',(0,10,0),(9.7,.25,3.85),metal)
 panel=add(board,unreal.StaticMeshComponent,'LEDDisplay','Root');panel.set_static_mesh(A.load_asset('/Engine/BasicShapes/Plane'));panel.set_material(0,film);panel.set_editor_property('relative_rotation',unreal.Rotator(roll=90));panel.set_editor_property('relative_scale3d',V((9.2,3.45,1)));panel.set_collision_profile_name('NoCollision')
 for x in [-478,478]:mesh(board,'Side'+str(x),(x,-5,0),(.06,.07,3.65),cyan)
 for z in [-180,180]:mesh(board,'Rail'+str(z),(0,-5,z),(9.5,.07,.045),cyan)
 for n,text,z,size in [('Header','АРХИВ 00  /  ПАДЕНИЕ ЦИВИЛИЗАЦИИ',201,12),('Control','[F]  ВОСПРОИЗВЕСТИ / ОСТАНОВИТЬ',-207,10)]:
  tx=add(board,unreal.TextRenderComponent,n,'Root');tx.set_text(unreal.Text(text));tx.set_world_size(size);tx.set_text_render_color(unreal.Color(90,225,240,255));tx.set_editor_property('relative_location',V((-450,-12,z)));tx.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90));tx.set_collision_profile_name('NoCollision')
 for n,t,d in [('bFocusedInteraction',B.get_basic_type_by_name('bool'),'false'),('bPlaying',B.get_basic_type_by_name('bool'),'false'),('FilmMID',B.get_object_reference_type(unreal.MaterialInstanceDynamic),'None')]:member(board,n,t,d)
 compile_bp(board);g=Flow(board);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);g.event('ReceiveBeginPlay');q=g.do(g.call('Engine.PrimitiveComponent.CreateDynamicMaterialInstance',target=g.get('LEDDisplay'),ElementIndex=0,SourceMaterial=film.get_path_name()));g.set('FilmMID',g.out(q))
 key=g.node(g.e.create_node_from_name(next(x for x in g.e.list_available_nodes([]) if x.endswith('|KeyboardEvents|F')),unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True);g.branch(g.get('bFocusedInteraction'));g.set('bPlaying',g.math('Not_PreBool',A=g.get('bPlaying')));g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('FilmMID'),ParameterName='Start',Value=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))));g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('FilmMID'),ParameterName='Playing',Value=g.math('SelectFloat',A=1.,B=0.,bPickA=g.get('bPlaying'))));g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound='/Game/LabTutorial/Holograms/S_ProjectorStartup',VolumeMultiplier=.3));compile_bp(board);cdo=unreal.get_default_object(B.generated_class(board));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',65);save(board)
 report['steps'].append('archive_board')
 # Remove only the two superseded CRTs, their blockers and dedicated glow lamps.
 removed=[]
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith(('IND_CRT_Workstation_','IND_WorkstationCollision_','IND_CRTGlow')):removed.append(a.get_actor_label());sub.destroy_actor(a)
 archive=sub.spawn_actor_from_class(B.generated_class(board),V((120,670,220)),unreal.Rotator());archive.set_actor_label('ARCHIVE_WorldCollapseBoard');archive.set_folder_path('LAB/05_Story');archive.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
 def place(device,p,scale,text,field='bFocusedInteraction',yaw=0,parent=None,show_corners=True):
  a=sub.spawn_actor_from_class(B.generated_class(focus),V(p),unreal.Rotator(yaw=yaw));a.set_actor_label('FOCUS_'+device.get_actor_label()+'_'+field);a.set_folder_path('LAB/InteractableMarkers');a.set_actor_scale3d(V(scale));a.set_editor_property('Device',device);a.set_editor_property('FocusField',field);a.set_editor_property('InteractionText',text)
  if not show_corners:
   for component in a.get_components_by_class(unreal.StaticMeshComponent):
    if component.get_name().startswith(('Idle','Aim')):
     component.set_hidden_in_game(True,False)
  if parent:a.attach_to_component(parent,'None',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
 for a in list(sub.get_all_level_actors()):
  name=a.get_actor_label()
  if name.startswith('HOLO_ArchiveProjector_'):
   p=a.get_actor_location();place(a,(p.x,p.y,65),(1.4,3.,.7),'[F]  ГОЛОГРАММА',yaw=a.get_actor_rotation().yaw)
  elif name=='BASE_MainPowerSwitch':place(a,(3460,-1700,150),(1.,1.,1.8),'[E]  ВКЛЮЧИТЬ ПИТАНИЕ',yaw=-90,show_corners=False)
  elif name=='LAB_FreightElevator':
   cabin=a.get_editor_property('CabinRoot');place(a,(2730,165,185),(.9,1.,1.6),'[F]  ПОЕХАТЬ НА ДРУГОЙ ЭТАЖ','FocusCabButton',parent=cabin)
   place(a,(2295,-215,165),(.6,1.,1.),'[F]  ВЫЗВАТЬ ЛИФТ','FocusLowerButton',yaw=90)
   place(a,(3060,180,2300),(.6,1.,1.),'[F]  ВЫЗВАТЬ ЛИФТ','FocusUpperButton',yaw=90)
 place(archive,(120,650,220),(10.,1.,4.),'[F]  АРХИВ: ПАДЕНИЕ МИРА')
 report.update(removed_workstations=removed)
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Map save failed')
 report['saved']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(saved,'focused_interaction_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Interaction authoring failed; see focused_interaction_report.json')




