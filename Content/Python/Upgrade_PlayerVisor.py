"""Native blue helmet HUD, actual-player schematic and per-module damage.

Preserves movement, energy balance, interaction focus and camera key V. Runtime
uses only Blueprint, UMG and two UI materials; Python is authoring-only.
"""
import unreal,os,sys,json,datetime,shutil,traceback,ast
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,Graph,pin,val,link,compile_bp,save
import Archive_AuthoringHelpers as H
ROOT='/Game/Characters/PlayerVisor';PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
p=os.path.abspath(unreal.Paths.project_dir());r={'saved':False,'gameplay_tested':False}
parts=[('Head','ГОЛОВА'),('Core','ЯДРО'),('ArmL','Л. РУКА'),('ArmR','П. РУКА'),('LegL','Л. НОГА'),('LegR','П. НОГА')]
class Flow(Graph):
 def __init__(self,bp,fn=None):
  super().__init__(bp)
  if fn:
   self.e=G.get_graph_editor_by_name(bp,fn) if fn in map(str,B.list_graph_names(bp)) else G.create_and_edit_function_graph(bp,fn)
   self.e.remove_nodes([n for n in self.e.list_all_nodes() if n.get_class().get_name() not in ('K2Node_FunctionEntry','K2Node_FunctionResult')]);self.cursor=self.e.find_graph_entry_pin()
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def event(self,name):
  n=self.e.find_event_node(name)
  if not n:
   token=name.removeprefix('Receive');choices=[x for x in self.e.list_available_nodes([]) if x.startswith(('Добавитьсобытие|','AddEvent|')) and x.split('|')[-1].replace(' ','') in [token,'Событие'+token,'Event'+token]]
   if len(choices)!=1:raise RuntimeError('Event not unique '+name+': '+str(choices))
   n=self.e.create_node_from_name(choices[0],unreal.Vector2D(),[])
  self.cursor=pin(n,'then',True);return n
 def sequence(self):
  choices=[x for x in self.e.list_available_nodes([]) if x.split('|')[-1] in ('Sequence','Последовательность')]
  if len(choices)!=1:raise RuntimeError('Sequence not unique')
  return self.node(self.e.create_node_from_name(choices[0],unreal.Vector2D(),[]))
 def selfcall(self,name,target=None):
  n=self.node(self.e.add_call_function_node(B.generated_class(self.bp).get_path_name()+'.'+name))
  if target is not None:val(n.find_self_pin(),target)
  return n
 def arg(self,name,kind):
  entry=self.e.find_graph_entry_pin().get_owning_node();out=entry.find_output_pin(name)
  return out if out.is_valid() else self.e.add_graph_input_parameter(name,kind)
 def smooth(self,t):return self.math('Multiply_DoubleDouble',A=self.math('Multiply_DoubleDouble',A=t,B=t),B=self.math('Subtract_DoubleDouble',A=3.,B=self.math('Multiply_DoubleDouble',A=2.,B=t)))
def member(bp,n,kind='real',default='0'):
 if n not in map(str,B.list_member_variable_names(bp)):
  typ=B.get_basic_type_by_name(kind) if isinstance(kind,str) else kind
  if not G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(n,typ,default):raise RuntimeError('Variable failed '+n)
 B.set_blueprint_variable_instance_editable(bp,n,True)
def back(path):
 src=os.path.join(p,'Content',path.removeprefix('/Game/')+'.uasset')
 if os.path.isfile(src):
  dst=os.path.join(r['backup'],path.removeprefix('/Game/')+'.uasset');os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
def material(name,code,parameters,texture=None):
 path=ROOT+'/'+name;back(path)
 mat=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
 custom=M.create_material_expression(mat,unreal.MaterialExpressionCustom,100,0);inputs=[];nodes=[]
 for i,(n,d) in enumerate([('UV',None)]+list(parameters.items())):
  ci=unreal.CustomInput();ci.set_editor_property('input_name',n);inputs.append(ci)
  if n=='UV':node=M.create_material_expression(mat,unreal.MaterialExpressionTextureCoordinate,-450,0)
  elif n=='T':node=M.create_material_expression(mat,unreal.MaterialExpressionTime,-450,100*i)
  else:
   node=M.create_material_expression(mat,unreal.MaterialExpressionScalarParameter,-450,100*i);node.set_editor_property('parameter_name',n);node.set_editor_property('default_value',d)
  nodes.append((node,n))
 if texture:
  ci=unreal.CustomInput();ci.set_editor_property('input_name','Diagram');inputs.append(ci)
  node=M.create_material_expression(mat,unreal.MaterialExpressionTextureObjectParameter,-450,900);node.set_editor_property('parameter_name','Diagram');node.set_editor_property('texture',texture);node.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);nodes.append((node,'Diagram'))
 custom.set_editor_property('inputs',inputs);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4);custom.set_editor_property('code',code)
 for node,name in nodes:M.connect_material_expressions(node,'',custom,name)
 for name,channels,prop in [('Color',('r','g','b'),unreal.MaterialProperty.MP_EMISSIVE_COLOR),('Alpha',('a',),unreal.MaterialProperty.MP_OPACITY)]:
  mask=M.create_material_expression(mat,unreal.MaterialExpressionComponentMask,450,0 if name=='Color' else 200)
  for ch in ('r','g','b','a'):mask.set_editor_property(ch,ch in channels)
  assert M.connect_material_expressions(custom,'',mask,'');assert M.connect_material_property(mask,'',prop)
 M.recompile_material(mat);save(mat);return mat
def splice_event(bp,event,function,tag,setup=None):
 g=Flow(bp)
 if any(n.get_name()==tag for n in g.e.list_all_nodes()):return
 ev=g.event(event);old=list(pin(ev,'then',True).list_connected_pins());pin(ev,'then',True).break_pin_links();seq=g.sequence();link(pin(ev,'then',True),seq.find_execute_pin())
 for oldpin in old:link(pin(seq,'then_0',True),oldpin)
 g.cursor=pin(seq,'then_1',True)
 if setup:setup(g,ev)
 n=g.selfcall(function);n.rename(tag)
 if event=='ReceivePointDamage':
  for name in ('Damage','BoneName','HitLocation'):val(pin(n,name),pin(ev,name,True))
 elif event=='ReceiveAnyDamage':val(pin(n,'Damage'),pin(ev,'Damage',True))
 g.do(n)
try:
 r['backup']=os.path.join(p,'Saved/Backups/VisorDiagnostics',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(r['backup'],exist_ok=True)
 for path in (PLAYER,ROOT+'/WBP_PlayerVisor',ROOT+'/M_VisorRim','/Game/LabTutorial/UI/BP_ArchiveAuthoring'):back(path)
 texture=A.load_asset(ROOT+'/T_BlackSentinelDiagram')
 if not texture:raise RuntimeError('Bake the actual hero diagram first')
 frame=material('M_VisorRim',open(os.path.join(p,'SourceAssets/Visor/VisorFrame.hlsl'),encoding='utf8').read(),{'Boot':1.,'T':0.})
 diagram=material('M_VisorBodyDiagnostics',open(os.path.join(p,'SourceAssets/Visor/VisorBody.hlsl'),encoding='utf8').read(),{**{n:1. for n,_ in parts},'T':0.},texture)
 player=A.load_asset(PLAYER);wbp=A.load_asset(ROOT+'/WBP_PlayerVisor')
 for n,_ in parts:member(player,'Module'+n+'HP','real','100');member(wbp,'Module'+n+'Ratio','real','1')
 member(player,'bVisorPointHandled','bool','false');member(player,'ModuleMaxHP','real','100')
 member(wbp,'BootAge','real','0');member(wbp,'BootDuration','real','.85');member(wbp,'RefreshAge','real','0');member(wbp,'VisorSpeedMPS','real','0');member(wbp,'VisorEnergyUnits','real','100')
 for n in ('RimMID','BodyMID'):member(wbp,n,B.get_object_reference_type(unreal.MaterialInstanceDynamic),'None')
 tree=unreal.find_object(wbp,'WidgetTree')
 def w(cls,n):return unreal.find_object(tree,n) or unreal.new_object(cls,outer=tree,name=n)
 canvas=w(unreal.CanvasPanel,'VisorCanvas');canvas.clear_children();H.assign_object(tree,'RootWidget',canvas);canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
 def flag(o):unreal.get_default_object(B.generated_class(H.helper)).call_method('AssignFlag',args=(o,unreal.Name('bIsVariable'),True))
 def slot(o,x,y,sx,sy,anchor=(0,0),align=(0,0)):
  q=canvas.add_child_to_canvas(o);q.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor),maximum=unreal.Vector2D(*anchor)));q.set_alignment(unreal.Vector2D(*align));q.set_position(unreal.Vector2D(x,y));q.set_size(unreal.Vector2D(sx,sy));return q
 def image(n,x,y,sx,sy,color=(.35,.7,1,.8),anchor=(0,0),align=(0,0),mat=None):
  o=w(unreal.Image,n)
  if mat:o.set_brush_from_material(mat)
  else:o.set_color_and_opacity(unreal.LinearColor(*color))
  slot(o,x,y,sx,sy,anchor,align);flag(o);return o
 def text(n,label,x,y,sx,size=11,color=(.40,.72,1,.9),anchor=(0,0),align=(0,0),justify=unreal.TextJustify.LEFT):
  o=w(unreal.TextBlock,n);o.set_text(unreal.Text(label));o.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
  font=o.get_editor_property('font');font.set_editor_property('font_object',A.load_asset('/Engine/EngineFonts/Roboto'));font.set_editor_property('size',size);font.set_editor_property('typeface_font_name','Regular');o.set_font(font);o.set_editor_property('justification',justify)
  o.set_shadow_color_and_opacity(unreal.LinearColor(0,.01,.03,.65));o.set_shadow_offset(unreal.Vector2D(0,1));slot(o,x,y,sx,24,anchor,align);flag(o);return o
 rim=image('HelmetRim',0,0,1,1,mat=frame);q=rim.slot;q.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(1,1)));q.set_offsets(unreal.Margin(0))
 text('VisorDesignation','ФИНАЛЬНЫЙ ПРОТОКОЛ',0,31,360,13,anchor=(.5,0),align=(.5,0),justify=unreal.TextJustify.CENTER)
 image('BodyDiagnostics',22,67,240,480,anchor=(0,.5),align=(0,.5),mat=diagram)
 text('DiagnosticsTitle','BLACK SENTINEL / ДИАГНОСТИКА',29,-164,280,9,anchor=(0,.5))
 for i,(name,label) in enumerate(parts):
  col=i%2;row=i//2;x=30+col*130;y=307+row*23
  text('Module'+name+'Label',label,x,y,76,9,anchor=(0,.5))
  text('Module'+name+'Value','100%',x+77,y,48,10,anchor=(0,.5))
  image('Module'+name+'LED',x-7,y+4,2,10,anchor=(0,.5))
 text('DamageAlert','ПОВРЕЖДЕНИЕ МОДУЛЕЙ',0,69,400,11,(1,.12,.15,1),(.5,0),(.5,0),unreal.TextJustify.CENTER)
 # Paired thin status rails and the segmented energy meter from the reference.
 for n,col,y,h in [('EnergyBar',(.27,.63,1,1),-61,8),('IntegrityBar',(.45,.78,1,.95),-43,3)]:
  o=w(unreal.ProgressBar,n);o.set_fill_color_and_opacity(unreal.LinearColor(*col));o.set_percent(1)
  style=o.get_editor_property('widget_style');bg=style.get_editor_property('background_image');bg.set_editor_property('tint_color',unreal.SlateColor(specified_color=unreal.LinearColor(.01,.035,.08,.65)));style.set_editor_property('background_image',bg);o.set_editor_property('widget_style',style);slot(o,-190,y,380,h,(.5,1),(0,1));flag(o)
 for i in range(1,10):image('EnergyGap_%02d'%i,-190+i*38,-61,3,8,(.01,.035,.08,.95),(.5,1),(0,1))
 for n,x,y,sx,sy in [('MeterTop',-255,-86,510,1),('MeterBottom',-255,-50,510,1),('MeterLeft',-255,-86,1,36),('MeterRight',255,-86,1,36)]:image(n,x,y,sx,sy,(.22,.62,1,.7),(.5,1),(0,0))
 text('EnergyValue','100%',-247,-78,54,11,anchor=(.5,1));text('EnergyUnits','100',204,-78,50,11,anchor=(.5,1))
 text('IntegrityLabel','КОРПУС',-190,-34,95,9,anchor=(.5,1));text('IntegrityValue','100%',145,-34,55,9,anchor=(.5,1))
 text('SpeedLabel','СКОРОСТЬ / М·С',-90,-106,150,10,anchor=(.5,1));text('SpeedValue','0.0',67,-106,70,10,anchor=(.5,1))
 text('ViewHint','V  /  ВНЕШНИЙ ВИД     K  /  ПОДСВЕТКА',0,-14,430,9,(.35,.66,.91,.65),(.5,1),(.5,1),unreal.TextJustify.CENTER)
 for name,x,y,sx,sy in [('ReticleLeft',-7,0,4,1),('ReticleRight',7,0,4,1),('ReticleTop',0,-7,1,4),('ReticleBottom',0,7,1,4),('ReticleDot',0,0,2,2)]:image(name,x,y,sx,sy,(.72,.9,1,.75),(.5,.5),(.5,.5))
 compile_bp(wbp);g=Flow(wbp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('Construct');g.set('BootAge',0.);g.set('RefreshAge',1.)
 for widget,key in [('HelmetRim','RimMID'),('BodyDiagnostics','BodyMID')]:g.set(key,g.out(g.do(g.call('UMG.Image.GetDynamicMaterial',target=g.get(widget)))))
 g.do(g.call('UMG.Widget.SetRenderOpacity',InOpacity=0.))
 tick=g.event('Tick');g.set('BootAge',g.math('FMin',A=2.,B=g.math('Add_DoubleDouble',A=g.get('BootAge'),B=pin(tick,'InDeltaTime',True))))
 t=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get('BootAge'),B=g.math('FMax',A=g.get('BootDuration'),B=.1)),Min=0,Max=1);smooth=g.smooth(t)
 g.do(g.call('UMG.Widget.SetRenderOpacity',InOpacity=smooth));g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('RimMID'),ParameterName='Boot',Value=t))
 g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('BodyDiagnostics'),InOpacity=g.smooth(g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=t,B=.20),B=.8),Min=0,Max=1))))
 g.set('RefreshAge',g.math('Add_DoubleDouble',A=g.get('RefreshAge'),B=pin(tick,'InDeltaTime',True)));g.branch(g.math('GreaterEqual_DoubleDouble',A=g.get('RefreshAge'),B=.1));g.set('RefreshAge',0.)
 for ratio,widget in [('VisorIntegrityRatio','IntegrityValue'),('VisorEnergyRatio','EnergyValue')]+[('Module'+n+'Ratio','Module'+n+'Value') for n,_ in parts]:
  percent=g.out(g.call('Engine.KismetTextLibrary.AsPercent_Float',Value=g.math('FClamp',Value=g.get(ratio),Min=0,Max=1),MinimumIntegralDigits=1,MaximumIntegralDigits=3,MinimumFractionalDigits=0,MaximumFractionalDigits=0));g.do(g.call('UMG.TextBlock.SetText',target=g.get(widget),InText=percent))
 for ratio,widget in [('VisorIntegrityRatio','IntegrityBar'),('VisorEnergyRatio','EnergyBar')]:g.do(g.call('UMG.ProgressBar.SetPercent',target=g.get(widget),InPercent=g.get(ratio)))
 for value,widget,digits in [('VisorSpeedMPS','SpeedValue',1),('VisorEnergyUnits','EnergyUnits',0)]:
  number=g.out(g.call('Engine.KismetTextLibrary.Conv_DoubleToText',Value=g.get(value),MinimumIntegralDigits=1,MaximumIntegralDigits=4,MinimumFractionalDigits=digits,MaximumFractionalDigits=digits));g.do(g.call('UMG.TextBlock.SetText',target=g.get(widget),InText=number))
 minimum=None
 for name,_ in parts:
  ratio=g.get('Module'+name+'Ratio');minimum=ratio if minimum is None else g.math('FMin',A=minimum,B=ratio)
  g.do(g.call('Engine.MaterialInstanceDynamic.SetScalarParameterValue',target=g.get('BodyMID'),ParameterName=name,Value=ratio))
  hurt=g.math('Less_DoubleDouble',A=ratio,B=.999)
  color=g.math('LinearColorLerp',A='(R=0.25,G=0.65,B=1,A=0.8)',B='(R=1,G=0.025,B=0.035,A=1)',Alpha=g.math('SelectFloat',A=1.,B=0.,bPickA=hurt))
  g.do(g.call('UMG.Image.SetColorAndOpacity',target=g.get('Module'+name+'LED'),InColorAndOpacity=color))
 g.do(g.call('UMG.Widget.SetRenderOpacity',target=g.get('DamageAlert'),InOpacity=g.math('SelectFloat',A=1.,B=0.,bPickA=g.math('Less_DoubleDouble',A=minimum,B=.999))))
 compile_bp(wbp);save(wbp);compile_bp(player)
 # Independent module health lives on the pawn, so it persists through V toggles.
 g=Flow(player,'Visor_UpdateDiagnostics');g.branch(g.get('bVisorReady'));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('VisorHUD'))))
 for name,_ in parts:
  ratio=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get('Module'+name+'HP'),B=g.math('FMax',A=g.get('ModuleMaxHP'),B=1.)),Min=0,Max=1)
  g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('VisorHUD'),PropertyName='Module'+name+'Ratio',Value=ratio))
 for key,value in [('VisorSpeedMPS',g.math('Divide_DoubleDouble',A=g.math('VSize',A=g.out(g.call('Engine.Actor.GetVelocity'))),B=100.)),('VisorEnergyUnits',g.get('VisorEnergy'))]:g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('VisorHUD'),PropertyName=key,Value=value))
 def hurt(g,module,damage):g.set('Module'+module+'HP',g.math('FClamp',Value=g.math('Subtract_DoubleDouble',A=g.get('Module'+module+'HP'),B=g.math('FMax',A=damage,B=0.)),Min=0,Max=g.get('ModuleMaxHP')))
 g=Flow(player,'Visor_GenericModuleDamage');damage=g.arg('Damage',B.get_basic_type_by_name('real'));b=g.branch(g.get('bVisorPointHandled'));generic=b.find_else_pin();g.set('bVisorPointHandled',False);g.cursor=generic;hurt(g,'Core',damage)
 g=Flow(player,'Visor_PointModuleDamage');damage=g.arg('Damage',B.get_basic_type_by_name('real'));bone=g.arg('BoneName',B.get_basic_type_by_name('name'));hit=g.arg('HitLocation',B.get_struct_type(unreal.load_object(None,'/Script/CoreUObject.Vector')))
 g.branch(g.math('Greater_DoubleDouble',A=damage,B=0.));g.set('bVisorPointHandled',True)
 bone_string=g.out(g.call('Engine.KismetStringLibrary.Conv_NameToString',InName=bone))
 def has(s):return g.out(g.call('Engine.KismetStringLibrary.Contains',SearchIn=bone_string,Substring=s,bUseCase=False,bSearchFromEnd=False))
 def either(tokens):
  out=has(tokens[0])
  for token in tokens[1:]:out=g.math('BooleanOR',A=out,B=has(token))
  return out
 left=either(['_l_','_l','left'])
 head=g.branch(either(['head','neck']));next_head=head.find_else_pin();hurt(g,'Head',damage);g.cursor=next_head
 leg=g.branch(either(['thigh','calf','foot','toe','leg']));next_leg=leg.find_else_pin();side=g.branch(left);right=side.find_else_pin();hurt(g,'LegL',damage);g.cursor=right;hurt(g,'LegR',damage);g.cursor=next_leg
 arm=g.branch(either(['arm','hand','shoulder','clavicle','finger','wrist']));next_arm=arm.find_else_pin();side=g.branch(left);right=side.find_else_pin();hurt(g,'ArmL',damage);g.cursor=right;hurt(g,'ArmR',damage);g.cursor=next_arm
 # Capsule hits may not return a bone: use the contact point in pawn space.
 transform=g.out(g.do(g.call('Engine.Actor.GetTransform')))
 local=g.math('InverseTransformLocation',T=transform,Location=hit);v=g.call('Engine.KismetMathLibrary.BreakVector',InVec=local)
 head=g.branch(g.math('Greater_DoubleDouble',A=pin(v,'Z',True),B=60.));next_head=head.find_else_pin();hurt(g,'Head',damage);g.cursor=next_head
 leg=g.branch(g.math('Less_DoubleDouble',A=pin(v,'Z',True),B=-35.));next_leg=leg.find_else_pin();side=g.branch(g.math('Less_DoubleDouble',A=pin(v,'Y',True),B=0.));right=side.find_else_pin();hurt(g,'LegL',damage);g.cursor=right;hurt(g,'LegR',damage);g.cursor=next_leg
 arm=g.branch(g.math('Greater_DoubleDouble',A=g.math('Abs',A=pin(v,'Y',True)),B=24.));core=arm.find_else_pin();side=g.branch(g.math('Less_DoubleDouble',A=pin(v,'Y',True),B=0.));right=side.find_else_pin();hurt(g,'ArmL',damage);g.cursor=right;hurt(g,'ArmR',damage);g.cursor=core;hurt(g,'Core',damage)
 compile_bp(player)
 splice_event(player,'ReceiveTick','Visor_UpdateDiagnostics','VisorV2Tick')
 splice_event(player,'ReceivePointDamage','Visor_PointModuleDamage','VisorV2PointDamage')
 splice_event(player,'ReceiveAnyDamage','Visor_GenericModuleDamage','VisorV2GenericDamage')
 # The widget already exists when V shows it; reset its boot clock on each show.
 e=G.get_graph_editor_by_name(player,'EventGraph');resets=0
 for n in list(e.list_all_nodes()):
  if n.get_name()=='VisorV2BootReset':continue
  q=n.find_input_pin('InVisibility')
  if not q.is_valid() or str(q.get_pin_value())!='HitTestInvisible':continue
  targets=list(n.find_self_pin().list_connected_pins())
  if not any(str(x.get_pin_name())=='VisorHUD' for x in targets):continue
  old=list(n.find_then_pin().list_connected_pins());n.find_then_pin().break_pin_links();g=Flow(player);g.cursor=n.find_then_pin()
  reset=g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('VisorHUD'),PropertyName='BootAge',Value=0.))
  reset.rename('VisorV2BootResetCall');n.rename('VisorV2BootReset')
  for dest in old:link(g.cursor,dest)
  resets+=1
 if not resets and not any(n.get_name()=='VisorV2BootReset' for n in e.list_all_nodes()):raise RuntimeError('First-person visor activation was not connected')
 compile_bp(player);save(player)
 r.update(saved=True,widget=wbp.get_path_name(),player=player.get_path_name(),modules=[n for n,_ in parts],boot_seconds=.85,activation_key='V',actual_player_diagram=texture.get_path_name(),runtime_render_targets=0,point_damage_bone_routing=True,generic_damage_module='Core')
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(p,'Saved/visor_diagnostics_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Visor diagnostics authoring incomplete')



