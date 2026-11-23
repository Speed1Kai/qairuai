"""Native packaged first-person camera and lightweight helmet HUD. Run in editor."""
import unreal, os, sys, json, datetime, shutil, traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,add,components,compile_bp,save,Graph,pin,val,link
import Archive_AuthoringHelpers as H
ROOT='/Game/Characters/PlayerVisor';PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
saved=os.path.abspath(unreal.Paths.project_saved_dir())
backup=os.path.join(saved,'Backups','PlayerVisor',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
r={'saved':False,'backup':backup,'gameplay_tested':False,'assets':[]}
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def sequence(self):
  opts=[x for x in self.e.list_available_nodes([]) if x.split('|')[-1] in ['Sequence','Последовательность']]
  if len(opts)!=1:raise RuntimeError('Sequence choices '+str(opts))
  return self.node(self.e.create_node_from_name(opts[0],unreal.Vector2D(),[]))
 def event(self,name):
  n=self.e.find_event_node(name)
  if not n:
   token=name.removeprefix('Receive')
   opts=[x for x in self.e.list_available_nodes([]) if x.startswith(('Добавитьсобытие|','AddEvent|')) and x.split('|')[-1].replace(' ','') in [token,'Событие'+token,'Event'+token]]
   if len(opts)!=1:raise RuntimeError('Event choices '+name+': '+str(opts))
   n=self.e.create_node_from_name(opts[0],unreal.Vector2D(),[])
  self.cursor=pin(n,'then',True);return n
 def external(self,name,cls,target):
  q=self.node(self.e.add_get_member_variable_node(name,cls));val(q.find_self_pin(),target);return pin(q,name,True)
def member(bp,n,t,d):
 if n not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(n,t,str(d))
 B.set_blueprint_variable_instance_editable(bp,n,True)
def backup_asset(path):
 rel=path.removeprefix('/Game/')+'.uasset';src=os.path.join(unreal.Paths.project_content_dir(),rel)
 if os.path.isfile(src):
  dst=os.path.join(backup,rel);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
def asset(name,cls,factory):
 p=ROOT+'/'+name;backup_asset(p)
 return A.load_asset(p) if A.does_asset_exist(p) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,cls,factory)
def tint(v):return unreal.LinearColor(*v)
try:
 A.make_directory(ROOT);backup_asset(PLAYER);player=A.load_asset(PLAYER)
 if 'AssignFlag' not in list(map(str,B.list_graph_names(H.helper))):
  he=G.create_and_edit_function_graph(H.helper,'AssignFlag')
  ho=he.add_graph_input_parameter('TargetObject',B.get_object_reference_type(unreal.Object));hn=he.add_graph_input_parameter('PropertyName',B.get_basic_type_by_name('name'));hv=he.add_graph_input_parameter('Value',B.get_basic_type_by_name('bool'))
  hc=he.add_call_function_node('/Script/Engine.KismetSystemLibrary.SetBoolPropertyByName');link(he.find_graph_entry_pin(),hc.find_execute_pin())
  for p,k in [(ho,'Object'),(hn,'PropertyName'),(hv,'Value')]:link(p,pin(hc,k))
  compile_bp(H.helper)
 params=[('bFirstPerson','bool','false'),('bVisorReady','bool','false'),('VisorIntegrity','double','100'),('VisorMaxIntegrity','double','100'),('VisorEnergy','double','100'),('VisorMaxEnergy','double','100'),('VisorSprintEnergyDrain','double','6'),('VisorEnergyRegen','double','3'),('VisorHUD',None,'None')]
 for n,t,d in params:
  member(player,n,B.get_basic_type_by_name('real' if t=='double' else t) if t else B.get_object_reference_type(unreal.UserWidget),d)
 camera=add(player,unreal.CameraComponent,'FirstPersonCamera','CapsuleComponent')
 camera.set_editor_property('relative_location',V((25,0,80)));camera.set_editor_property('use_pawn_control_rotation',True);camera.set_editor_property('field_of_view',90.);camera.set_editor_property('auto_activate',False)
 compile_bp(player)
 # Analytic rounded helmet rim: one UI material, no render targets or bitmap masks.
 mat=asset('M_VisorRim',unreal.Material,unreal.MaterialFactoryNew());M.delete_all_material_expressions(mat)
 mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
 uv=M.create_material_expression(mat,unreal.MaterialExpressionTextureCoordinate,0,0)
 custom=M.create_material_expression(mat,unreal.MaterialExpressionCustom,220,0)
 ci=unreal.CustomInput();ci.set_editor_property('input_name','UV');custom.set_editor_property('inputs',[ci]);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4)
 custom.set_editor_property('code','''
float2 p=abs(UV*2-1);
float2 q=p-float2(.78,.72);
float d=length(max(q,0))+min(max(q.x,q.y),0)-.19;
float rim=smoothstep(-.008,.012,d);
float lip=exp(-abs(d+.012)*180)*.35;
float haze=pow(saturate(max(p.x,p.y)),12)*.10;
float3 col=lerp(float3(.004,.009,.014),float3(.12,.55,.66),lip);
return float4(col,max(rim*.98,lip+haze));''')
 M.connect_material_expressions(uv,'',custom,'UV')
 # RGBA is split by component masks for final color and transparency.
 rgb=M.create_material_expression(mat,unreal.MaterialExpressionComponentMask,460,0);rgb.set_editor_property('r',True);rgb.set_editor_property('g',True);rgb.set_editor_property('b',True)
 alpha=M.create_material_expression(mat,unreal.MaterialExpressionComponentMask,460,150)
 for ch in ['r','g','b']:alpha.set_editor_property(ch,False)
 alpha.set_editor_property('a',True)
 M.connect_material_expressions(custom,'',rgb,'Input');M.connect_material_expressions(custom,'',alpha,'Input');M.connect_material_property(rgb,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.connect_material_property(alpha,'',unreal.MaterialProperty.MP_OPACITY);M.recompile_material(mat);save(mat)
 factory=unreal.WidgetBlueprintFactory();factory.set_editor_property('parent_class',unreal.UserWidget)
 wbp=asset('WBP_PlayerVisor',unreal.WidgetBlueprint,factory);tree=unreal.find_object(wbp,'WidgetTree')
 def w(cls,n):return unreal.find_object(tree,n) or unreal.new_object(cls,outer=tree,name=n)
 canvas=w(unreal.CanvasPanel,'VisorCanvas');canvas.clear_children();H.assign_object(tree,'RootWidget',canvas);canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
 def flag(obj):unreal.get_default_object(B.generated_class(H.helper)).call_method('AssignFlag',args=(obj,unreal.Name('bIsVariable'),True))
 def slot(obj,x,y,width,height,anchor=(0,0),align=(0,0)):
  s=canvas.add_child_to_canvas(obj);s.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor),maximum=unreal.Vector2D(*anchor)));s.set_alignment(unreal.Vector2D(*align));s.set_position(unreal.Vector2D(x,y));s.set_size(unreal.Vector2D(width,height));return s
 rim=w(unreal.Image,'HelmetRim');rim.set_brush_from_material(mat);s=canvas.add_child_to_canvas(rim);s.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(1,1)));s.set_offsets(unreal.Margin(0))
 def text(n,txt,x,y,width,size,color,anchor=(0,1),align=(0,1),right=False):
  t=w(unreal.TextBlock,n);t.set_text(unreal.Text(txt));t.set_color_and_opacity(unreal.SlateColor(specified_color=tint(color)));f=t.get_editor_property('font');f.set_editor_property('font_object',A.load_asset('/Engine/EngineFonts/Roboto'));f.set_editor_property('size',size);f.set_editor_property('typeface_font_name','Regular');t.set_font(f);t.set_shadow_color_and_opacity(tint((0,0,0,.8)));t.set_shadow_offset(unreal.Vector2D(0,1));t.set_editor_property('justification',unreal.TextJustify.RIGHT if right else unreal.TextJustify.LEFT);slot(t,x,y,width,32,anchor,align);return t
 cyan=(.24,.94,1,1);amber=(1,.72,.25,1)
 text('IntegrityLabel','СОСТОЯНИЕ',125,-153,310,12,cyan)
 text('EnergyLabel','ЭНЕРГИЯ',-125,-153,310,12,amber,(1,1),(1,1),True)
 hp=text('IntegrityValue','100%',125,-113,310,24,cyan);en=text('EnergyValue','100%',-125,-113,310,24,amber,(1,1),(1,1),True)
 bars=[]
 for n,col,x,anchor,align in [('IntegrityBar',cyan,125,(0,1),(0,1)),('EnergyBar',amber,-125,(1,1),(1,1))]:
  bar=w(unreal.ProgressBar,n);style=bar.get_editor_property('widget_style');bg=style.get_editor_property('background_image');bg.set_editor_property('tint_color',unreal.SlateColor(specified_color=tint((.015,.035,.045,.7))));style.set_editor_property('background_image',bg);bar.set_editor_property('widget_style',style);bar.set_fill_color_and_opacity(tint(col));bar.set_percent(1);slot(bar,x,-94,310,5,anchor,align);bars.append(bar)
 text('VisorDesignation','OMEGA  /  ОПТИЧЕСКАЯ СИСТЕМА',0,42,500,11,(.35,.7,.75,.65),(.5,0),(.5,0))
 text('ViewHint','V  /  ВНЕШНЯЯ КАМЕРА',0,-45,300,10,(.45,.7,.74,.65),(.5,1),(.5,1))
 for o in [hp,en]+bars:flag(o)
 for n,t,d in [('VisorIntegrityRatio',B.get_basic_type_by_name('real'),'1'),('VisorEnergyRatio',B.get_basic_type_by_name('real'),'1'),('RefreshAge',B.get_basic_type_by_name('real'),'0')]:member(wbp,n,t,d)
 compile_bp(wbp);g=Flow(wbp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('Construct');g.set('RefreshAge',0)
 tick=g.event('Tick');g.set('RefreshAge',g.math('Add_DoubleDouble',A=g.get('RefreshAge'),B=pin(tick,'InDeltaTime',True)));g.branch(g.math('GreaterEqual_DoubleDouble',A=g.get('RefreshAge'),B=.1));g.set('RefreshAge',0)
 for value,maximum,bar,txt in [('VisorIntegrity','VisorMaxIntegrity','IntegrityBar','IntegrityValue'),('VisorEnergy','VisorMaxEnergy','EnergyBar','EnergyValue')]:
  ratio=g.math('FClamp',Value=g.get(value+'Ratio'),Min=0,Max=1)
  g.do(g.call('UMG.ProgressBar.SetPercent',target=g.get(bar),InPercent=ratio))
  formatted=g.out(g.call('Engine.KismetTextLibrary.AsPercent_Float',Value=ratio,MinimumIntegralDigits=1,MaximumIntegralDigits=3,MinimumFractionalDigits=0,MaximumFractionalDigits=0))
  g.do(g.call('UMG.TextBlock.SetText',target=g.get(txt),InText=formatted))
 compile_bp(wbp);save(wbp)
 # Add isolated camera/status graph, preserving all existing movement and interaction nodes.
 g=Flow(player);before={n.get_name() for n in g.e.list_all_nodes()}
 pc=lambda:g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 selfref=lambda:g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
 begin=g.event('ReceiveBeginPlay');old=list(pin(begin,'then',True).list_connected_pins());pin(begin,'then',True).break_pin_links()
 # A sequence preserves any existing BeginPlay branch independently of the intro delay.
 seq=g.sequence();link(pin(begin,'then',True),seq.find_execute_pin())
 for p in old:link(pin(seq,'then_0',True),p)
 g.cursor=pin(seq,'then_1',True);g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=10.6));create=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(wbp).get_path_name(),OwningPlayer=pc()));g.set('VisorHUD',g.out(create));g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('VisorHUD'),ZOrder=5));g.do(g.call('UMG.Widget.SetVisibility',target=g.get('VisorHUD'),InVisibility='Collapsed'));g.set('bVisorReady',True)
 opts=[x for x in g.e.list_available_nodes([]) if x.endswith('|KeyboardEvents|V')];key=g.node(g.e.create_node_from_name(opts[0],unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True);g.branch(g.get('bVisorReady'));g.set('bFirstPerson',g.math('Not_PreBool',A=g.get('bFirstPerson')))
 g.do(g.call('Engine.ActorComponent.SetActive',target=g.get('FollowCamera'),bNewActive=g.math('Not_PreBool',A=g.get('bFirstPerson')),bReset=False));g.do(g.call('Engine.ActorComponent.SetActive',target=g.get('FirstPersonCamera'),bNewActive=g.get('bFirstPerson'),bReset=False))
 g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=selfref(),PropertyName='bUseControllerRotationYaw',Value=g.get('bFirstPerson')));g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=g.get('CharacterMovement'),PropertyName='bOrientRotationToMovement',Value=g.math('Not_PreBool',A=g.get('bFirstPerson'))));g.do(g.call('Engine.PrimitiveComponent.SetOwnerNoSee',target=g.get('Mesh'),bNewOwnerNoSee=g.get('bFirstPerson')))
 # Hide attached emissive body pieces only from the local camera; keep their lamps.
 for path,names in [('/Game/Characters/GuardPlayer/BP_PlayerGuardVisual',['EyeL','EyeR','NeckReactor','ChestReactor','SpineReactor','ShoulderL','ShoulderR','WristL','WristR']),('/Game/LabTutorial/Basement/BP_CyborgBodyLight',['BodyGlowShell','ChestEmitter','BackEmitter','LeftArmEmitter','RightArmEmitter','LeftLegEmitter','RightLegEmitter'])]:
  cls=B.generated_class(A.load_asset(path)).get_path_name();actor=g.out(g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=cls)));check=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=actor)));skip=check.find_else_pin();g.do(g.call('Engine.Actor.SetOwner',target=actor,NewOwner=selfref()))
  for n in names:g.do(g.call('Engine.PrimitiveComponent.SetOwnerNoSee',target=g.external(n,cls,actor),bNewOwnerNoSee=g.get('bFirstPerson')))
  merge=g.set('bFirstPerson',g.get('bFirstPerson'));link(skip,merge.find_execute_pin())
 split=g.branch(g.get('bFirstPerson'));third=split.find_else_pin();g.do(g.call('UMG.Widget.SetVisibility',target=g.get('VisorHUD'),InVisibility='HitTestInvisible'));g.cursor=third;g.do(g.call('UMG.Widget.SetVisibility',target=g.get('VisorHUD'),InVisibility='Collapsed'))
 # Status values are gameplay variables, not fixed decorative percentages.
 tick=g.event('ReceiveTick');old=list(pin(tick,'then',True).list_connected_pins());pin(tick,'then',True).break_pin_links();seq=g.sequence();link(pin(tick,'then',True),seq.find_execute_pin())
 for p in old:link(pin(seq,'then_0',True),p)
 g.cursor=pin(seq,'then_1',True);g.branch(g.get('bVisorReady'));speed=g.math('VSizeXY',A=g.out(g.call('Engine.Actor.GetVelocity')));rate=g.math('SelectFloat',A=g.math('Subtract_DoubleDouble',A=0.,B=g.get('VisorSprintEnergyDrain')),B=g.get('VisorEnergyRegen'),bPickA=g.math('Greater_DoubleDouble',A=speed,B=260.))
 g.set('VisorEnergy',g.math('FClamp',Value=g.math('Add_DoubleDouble',A=g.get('VisorEnergy'),B=g.math('Multiply_DoubleDouble',A=rate,B=pin(tick,'DeltaSeconds',True))),Min=0,Max=g.get('VisorMaxEnergy')))
 for value,maximum in [('VisorIntegrity','VisorMaxIntegrity'),('VisorEnergy','VisorMaxEnergy')]:
  ratio=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get(value),B=g.math('FMax',A=g.get(maximum),B=1.)),Min=0,Max=1)
  g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('VisorHUD'),PropertyName=value+'Ratio',Value=ratio))
 damage=g.event('ReceiveAnyDamage');g.set('VisorIntegrity',g.math('FClamp',Value=g.math('Subtract_DoubleDouble',A=g.get('VisorIntegrity'),B=g.math('FMax',A=pin(damage,'Damage',True),B=0.)),Min=0,Max=g.get('VisorMaxIntegrity')))
 compile_bp(player);save(player)
 r.update(saved=True,assets=[mat.get_path_name(),wbp.get_path_name(),player.get_path_name()],camera_key='V',fov=90,helmet_texture_memory=0,health_damage_connected=True,energy_sprint_drain=6,energy_regen=3)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'player_visor_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Visor authoring failed, see player_visor_report.json')



