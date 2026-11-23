"""Canvas HUD with clickable mode cards and occlusion-tested first-person threat rings."""
import unreal,os,sys,json,traceback,shutil
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
_BaseGraph=Graph
class Graph(_BaseGraph):
 def call(self,path,target=None,**kw):
  if not path.startswith('/Game/'):return super().call(path,target=target,**kw)
  n=self.node(self.e.add_call_function_node(path))
  if target is not None:val(n.find_self_pin(),target)
  for k,v in kw.items():
   if hasattr(v,'try_create_connection'):val(pin(n,k),v)
  for k,v in kw.items():
   if not hasattr(v,'try_create_connection'):val(pin(n,k),v)
  return n
P='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter';MOD='/Game/Combat/CyborgModes';S=os.path.abspath(unreal.Paths.project_saved_dir());R={'saved':False}
def arg(g,n,t):
 entry=g.e.find_graph_entry_pin().get_owning_node()
 if n in [str(p.get_pin_name()) for p in entry.list_all_pins()]:return pin(entry,n,True)
 return g.e.add_graph_input_parameter(n,B.get_basic_type_by_name(t) if isinstance(t,str) else t)
def plus(g,a,b):return g.math('Add_DoubleDouble',A=a,B=b)
def minus(g,a,b):return g.math('Subtract_DoubleDouble',A=a,B=b)
def mul(g,a,b):return g.math('Multiply_DoubleDouble',A=a,B=b)
def col(r,g,b,a=1):return '(R=%f,G=%f,B=%f,A=%f)'%(r,g,b,a)
CYAN=col(.18,.85,1);WHITE=col(.78,.91,.94);MUTED=col(.32,.46,.5);RED=col(1,.035,.055);DARK=col(.008,.018,.028,.86)
def rect(g,x,y,w,h,c):return g.do(g.call('Engine.HUD.DrawRect',target=g.get('ModeCanvasHUD'),RectColor=c,ScreenX=x,ScreenY=y,ScreenW=w,ScreenH=h))
def text(g,s,x,y,c=WHITE,size=1):return g.do(g.call('Engine.HUD.DrawText',target=g.get('ModeCanvasHUD'),Text=s,TextColor=c,ScreenX=x,ScreenY=y,Font='/Engine/EngineFonts/Roboto',Scale=mul(g,g.get('ModeUIScale'),size),bScalePosition=False))
def custom(bp,fn,target,g,**kw):return g.do(g.call(B.generated_class(bp).get_path_name().removeprefix('/Script/')+'.'+fn,target=target,**kw))
try:
 assert json.load(open(os.path.join(S,'cyborg_modes_gameplay.json')))['saved'];assert not unreal.EditorLevelLibrary.get_game_world()
 bp=A.load_asset(P)
 for n,k,d in [('ModeScreenW','real','1920'),('ModeScreenH','real','1080'),('ModeUIScale','real','1'),('ModeDetectedCount','int','0'),('ModeHUDFrames','int','0')]:var(bp,n,k,d)
 var(bp,'ModeCanvasHUD',B.get_object_reference_type(unreal.HUD),'None');var(bp,'ModeTargets',B.get_array_type(actorref()),'()');compile_bp(bp)
 # A thin screen-space circle: no mesh custom-depth changes, no through-wall outline.
 path=MOD+'/M_ThreatRing';ring=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_ThreatRing',MOD,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(ring);ring.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);ring.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);ring.set_editor_property('two_sided',True)
 uv=M.create_material_expression(ring,unreal.MaterialExpressionTextureCoordinate);mask=M.create_material_expression(ring,unreal.MaterialExpressionCustom);i=unreal.CustomInput();i.set_editor_property('input_name','UV');mask.set_editor_property('inputs',[i]);mask.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1);mask.set_editor_property('code','float2 p=UV*2-1;float d=abs(length(p)-.88);return (1-smoothstep(.012,.034,d))*.92;');M.connect_material_expressions(uv,'',mask,'UV');M.connect_material_property(mask,'',unreal.MaterialProperty.MP_OPACITY)
 c=M.create_material_expression(ring,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(r=1.,g=.025,b=.045,a=1));M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(ring);save(ring)
 g=Graph(bp,'Modes_DrawOneThreat');target=arg(g,'Enemy',actorref());g.branch(g.valid(target));g.branch(g.math('LessEqual_DoubleDouble',A=g.out(g.call('Engine.Actor.GetLifeSpan',target=target)),B=0.))
 dist=g.out(g.call('Engine.Actor.GetDistanceTo',OtherActor=target));g.branch(g.math('Less_DoubleDouble',A=dist,B=4000.))
 cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam));g.branch(g.out(g.call('Engine.Controller.LineOfSightTo',target=g.pc(),Other=target,ViewPoint=eye,bAlternateChecks=False)))
 pos=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=target));q=g.do(g.call('Engine.PlayerController.ProjectWorldLocationToScreen',target=g.pc(),WorldLocation=pos,bPlayerViewportRelative=True));g.branch(g.out(q))
 xy=g.call('Engine.KismetMathLibrary.BreakVector2D',InVec=g.out(q,'ScreenLocation'));x=g.out(xy,'X');y=g.out(xy,'Y')
 for v,maximum in [(x,g.get('ModeScreenW')),(y,g.get('ModeScreenH'))]:g.branch(g.math('BooleanAND',A=g.math('Greater_DoubleDouble',A=v,B=0.),B=g.math('Less_DoubleDouble',A=v,B=maximum)))
 radius=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=mul(g,g.get('ModeScreenW'),65.),B=g.math('FMax',A=dist,B=100.)),Min=25.,Max=145.)
 g.do(g.call('Engine.HUD.DrawMaterial',target=g.get('ModeCanvasHUD'),Material=ring.get_path_name(),ScreenX=minus(g,x,radius),ScreenY=minus(g,y,radius),ScreenW=mul(g,radius,2.),ScreenH=mul(g,radius,2.),MaterialU=0.,MaterialV=0.,MaterialUWidth=1.,MaterialVHeight=1.,Scale=1.,bScalePosition=False))
 text(g,'УГРОЗА',minus(g,x,mul(g,g.get('ModeUIScale'),27.)),minus(g,minus(g,y,radius),mul(g,g.get('ModeUIScale'),18.)),RED,.56);g.count('ModeDetectedCount');compile_bp(bp)
 g=Graph(bp,'Modes_DrawThreats');index=arg(g,'Index','int');length=g.out(g.call('Engine.KismetArrayLibrary.Array_Length',TargetArray=g.get('ModeTargets')))
 g.branch(g.math('BooleanAND',A=g.math('Less_IntInt',A=index,B=length),B=g.math('Less_IntInt',A=index,B=32)))
 n=g.call('Engine.KismetArrayLibrary.Array_Get',TargetArray=g.get('ModeTargets'),Index=index);g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_DrawOneThreat',Enemy=g.out(n,'Item')));compile_bp(bp)
 # Bounded recursion traverses the small current target list without latent actions.
 q=g.e.add_call_function_node(B.generated_class(bp).get_path_name()+'.Modes_DrawThreats');val(pin(q,'Index'),g.math('Add_IntInt',A=index,B=1));g.do(q);compile_bp(bp)
 g=Graph(bp,'Modes_DrawHUD');canvas=arg(g,'HUD',B.get_object_reference_type(unreal.HUD));width=arg(g,'Width','int');height=arg(g,'Height','int')
 g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))));g.set('ModeCanvasHUD',canvas);g.set('ModeScreenW',width);g.set('ModeScreenH',height);g.set('ModeUIScale',g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get('ModeScreenH'),B=900.),Min=.8,Max=1.4));g.count('ModeHUDFrames');g.set('ModeDetectedCount',0)
 u=g.get('ModeUIScale');x=mul(g,u,24.);top=mul(g,g.get('ModeScreenH'),.22);w=mul(g,u,294.)
 text(g,'БОЕВЫЕ ПРОТОКОЛЫ',x,minus(g,top,mul(g,u,30.)),CYAN,.85)
 cards=[('СКОРОСТЬ','Усиленный бег / манёвренность'),('ОХОТНИК','Автолазер / быстрая реакция'),('АТОМНОЕ КРУШЕНИЕ','Тяжёлый импульс / мощь'),('НЕЙРОКОНТРОЛЬ','Дроны / роботы · НЕДОСТУПНО')]
 for i,(title,desc) in enumerate(cards):
  y=plus(g,top,mul(g,u,i*79.));h=mul(g,u,69.);selected=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=i);accent=g.math('SelectColor',A=col(1.,.43,.16) if i==2 else CYAN,B=MUTED,bPickA=selected)
  rect(g,x,y,w,h,DARK);rect(g,x,y,mul(g,u,3.),h,accent);rect(g,plus(g,x,mul(g,u,12.)),plus(g,y,mul(g,u,13.)),mul(g,u,31.),mul(g,u,31.),col(.035,.07,.085,.95))
  text(g,str(i+1),plus(g,x,mul(g,u,21.)),plus(g,y,mul(g,u,16.)),accent,.85)
  text(g,title,plus(g,x,mul(g,u,54.)),plus(g,y,mul(g,u,11.)),MUTED if i==3 else WHITE,.87)
  text(g,desc,plus(g,x,mul(g,u,54.)),plus(g,y,mul(g,u,37.)),MUTED,.53)
  g.do(g.call('Engine.HUD.AddHitBox',target=canvas,Position=g.math('MakeVector2D',X=x,Y=y),Size=g.math('MakeVector2D',X=w,Y=h),InName='Mode'+str(i),bConsumesInput=True,Priority=10))
 text(g,'1–3  ВЫБОР    TAB  КУРСОР',x,plus(g,top,mul(g,u,329.)),CYAN,.65)
 # Low horizontal charge rail remains visible in both camera modes.
 charge=g.math('Subtract_DoubleDouble',A=1.,B=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get('ProtocolCooldownRemaining'),B=8.),Min=0.,Max=1.))
 yy=plus(g,top,mul(g,u,358.));atomic=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=2)
 label=g.out(g.call('Engine.KismetMathLibrary.SelectString',A='ИМПУЛЬС / ПЕРЕЗАРЯДКА 8 С',B='ЛАЗЕР / УДЕРЖИВАЙТЕ ЛКМ',bPickA=atomic));label=g.out(g.call('Engine.KismetMathLibrary.SelectString',A='СКОРОСТЬ / ОРУЖИЕ ОТКЛЮЧЕНО',B=label,bPickA=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=0)));text(g,label,x,yy,CYAN,.6)
 rect(g,x,plus(g,yy,mul(g,u,22.)),w,mul(g,u,3.),col(.07,.14,.18,.85));rect(g,x,plus(g,yy,mul(g,u,22.)),mul(g,w,g.math('SelectFloat',A=charge,B=1.,bPickA=atomic)),mul(g,u,3.),CYAN)
 # Crosshair and an unobtrusive third-person health rail.
 cx=mul(g,g.get('ModeScreenW'),.5);cy=mul(g,g.get('ModeScreenH'),.5)
 for dx,dy,ww,hh in [(-11,-1,6,2),(5,-1,6,2),(-1,-11,2,6),(-1,5,2,6)]:rect(g,plus(g,cx,dx),plus(g,cy,dy),ww,hh,CYAN)
 hp=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get('VisorIntegrity'),B=g.math('FMax',A=g.get('VisorMaxIntegrity'),B=1.)),Min=0.,Max=1.)
 text(g,'КОРПУС',x,minus(g,g.get('ModeScreenH'),mul(g,u,49.)),MUTED,.56);rect(g,x,minus(g,g.get('ModeScreenH'),mul(g,u,26.)),w,mul(g,u,3.),col(.1,.1,.12,.8));rect(g,x,minus(g,g.get('ModeScreenH'),mul(g,u,26.)),mul(g,w,hp),mul(g,u,3.),g.math('SelectColor',A=RED,B=CYAN,bPickA=g.math('Less_DoubleDouble',A=hp,B=.25)))
 g.branch(g.get('bFirstPerson'));targets=g.do(g.call('Engine.GameplayStatics.GetAllActorsWithTag',Tag='CyborgHostile'));g.set('ModeTargets',g.out(targets,'OutActors'));g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_DrawThreats',Index=0));compile_bp(bp);save(bp)
 # The HUD is a native saved Blueprint so it also works in packaged gameplay.
 hud=asset(MOD+'/BP_CyborgCombatHUD',unreal.HUD);compile_bp(hud);g=Graph(hud);g.e.remove_nodes(g.e.list_all_nodes())
 menu=next(s for s in json.load(open(os.path.join(S,'cyborg_modes_api.json')))['cast_menus'] if s.endswith('|CastToBP_ThirdPersonCharacter'))
 def cast_player(g):
  n=g.e.create_node_from_name(menu,unreal.Vector2D(x=400,y=0),[]);val(pin(n,'Object'),g.out(g.call('Engine.HUD.GetOwningPawn')));g.do(n)
  return next(p for p in n.list_all_pins() if str(p.get_pin_name()).startswith('AsBP'))
 ev=g.override('ReceiveDrawHUD');player=cast_player(g);ownerpc=g.out(g.call('Engine.HUD.GetOwningPlayerController'));selfhud=g.out(g.call('Engine.PlayerController.GetHUD',target=ownerpc));g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_DrawHUD',target=player,HUD=selfhud,Width=pin(ev,'SizeX',True),Height=pin(ev,'SizeY',True)))
 ev=g.override('ReceiveHitBoxClick');player=cast_player(g)
 for i in range(4):
  eq=g.math('EqualEqual_NameName',A=pin(ev,'BoxName',True),B='Mode'+str(i));q=g.branch(eq);skip=q.find_else_pin();g.do(g.call(B.generated_class(bp).get_path_name()+'.Modes_Select',target=player,RequestedMode=i));g.cursor=skip
 compile_bp(hud);save(hud)
 mode=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode');unreal.get_default_object(B.generated_class(mode)).set_editor_property('hud_class',B.generated_class(hud));save(mode)
 # Shift existing visor body diagnostics to the right, leaving the requested selector clear.
 visor=A.load_asset('/Game/Characters/PlayerVisor/WBP_PlayerVisor');tree=unreal.find_object(visor,'WidgetTree');root=unreal.find_object(tree,'VisorCanvas')
 shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'Characters/PlayerVisor/WBP_PlayerVisor.uasset'),json.load(open(os.path.join(S,'cyborg_modes_gameplay.json')))['backup'])
 moved=[]
 for i in range(root.get_children_count()):
  child=root.get_child_at(i);slot=child.slot
  if not isinstance(slot,unreal.CanvasPanelSlot):continue
  anchors=slot.get_anchors()
  if anchors.minimum.x==0 and abs(anchors.minimum.y-.5)<.01:
   pos=slot.get_position();slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(x=1,y=.5),maximum=unreal.Vector2D(x=1,y=.5)));slot.set_position(unreal.Vector2D(x=pos.x-320,y=pos.y));moved.append(child.get_name())
 compile_bp(visor);save(visor);R.update(saved=True,hud=hud.get_path_name(),diagnostics_moved=moved)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
json.dump(R,open(os.path.join(S,'cyborg_modes_hud.json'),'w'),indent=2)
assert R['saved'],R



