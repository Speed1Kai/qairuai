"""Author a local developer noclip mode on the existing playable character.

Native Blueprint assets only. F6 restores the entry transform on exit, so a
review flight cannot leave the character embedded in a wall. No game test run.
"""
import unreal, os, sys, json, shutil, datetime, traceback
sys.path.insert(0, os.path.dirname(__file__))
from Industrial_Common import A, B, G, Graph, pin, val, link, compile_bp, save
import Archive_AuthoringHelpers as H

PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
ROOT='/Game/Developer/Admin'
report={'saved':False,'gameplay_tested':False}

class Flow(Graph):
 def __init__(self,bp,name=None):
  super().__init__(bp)
  if name:
   self.e=G.get_graph_editor_by_name(bp,name) if name in map(str,B.list_graph_names(bp)) else G.create_and_edit_function_graph(bp,name)
   self.e.remove_nodes([n for n in self.e.list_all_nodes() if n.get_class().get_name() not in ('K2Node_FunctionEntry','K2Node_FunctionResult')])
   self.cursor=self.e.find_graph_entry_pin()
 def pc(self):return self.out(self.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 def down(self,k):return self.out(self.call('Engine.PlayerController.IsInputKeyDown',target=self.pc(),Key='(KeyName="'+k+'")'))
 def axis(self,pos,neg):
  a=self.math('SelectFloat',A=1.,B=0.,bPickA=self.down(pos))
  b=self.math('SelectFloat',A=1.,B=0.,bPickA=self.down(neg))
  return self.math('Subtract_DoubleDouble',A=a,B=b)
 def selfcall(self,name):return self.node(self.e.add_call_function_node(B.generated_class(self.bp).get_path_name()+'.'+name))

try:
 bp=A.load_asset(PLAYER)
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups','AdminFlight',stamp)
 os.makedirs(backup,exist_ok=True)
 shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),backup)
 report['backup']=os.path.abspath(backup)
 ev=G.get_graph_editor_by_name(bp,'EventGraph')
 variables=[('bAdminFlight',B.get_basic_type_by_name('bool'),'false'),
  ('AdminFlightSpeed',B.get_basic_type_by_name('real'),'2000'),
  ('AdminBoostMultiplier',B.get_basic_type_by_name('real'),'4'),
  ('AdminEntryTransform',B.get_struct_type(unreal.load_object(None,'/Script/CoreUObject.Transform')),''),
  ('AdminEntryRotation',B.get_struct_type(unreal.load_object(None,'/Script/CoreUObject.Rotator')),''),
  ('AdminHadCollision',B.get_basic_type_by_name('bool'),'true'),
  ('AdminBoomCollision',B.get_basic_type_by_name('bool'),'true'),
  ('AdminFlightHUD',B.get_object_reference_type(unreal.UserWidget),'None')]
 for name,kind,default in variables:
  if name not in map(str,B.list_member_variable_names(bp)):
   if not ev.add_member_variable(name,kind,default):raise RuntimeError('Variable failed '+name)
 for name in ['AdminFlightSpeed','AdminBoostMultiplier']:
  B.set_blueprint_variable_instance_editable(bp,name,True)
 compile_bp(bp)

 # A small UMG banner identifies developer mode without debug PrintString spam.
 A.make_directory(ROOT)
 wp=ROOT+'/WBP_AdminFlight'
 wbp=A.load_asset(wp) if A.does_asset_exist(wp) else None
 if not wbp:
  factory=unreal.WidgetBlueprintFactory();factory.set_editor_property('parent_class',unreal.UserWidget)
  wbp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_AdminFlight',ROOT,unreal.WidgetBlueprint,factory)
 tree=unreal.find_object(wbp,'WidgetTree')
 canvas=unreal.find_object(tree,'AdminCanvas') or unreal.new_object(unreal.CanvasPanel,outer=tree,name='AdminCanvas')
 canvas.clear_children();H.assign_object(tree,'RootWidget',canvas)
 canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
 border=unreal.find_object(tree,'AdminBorder') or unreal.new_object(unreal.Border,outer=tree,name='AdminBorder')
 border.set_brush_color(unreal.LinearColor(.008,.025,.035,.88));border.set_padding(unreal.Margin(18,10,18,10))
 slot=canvas.add_child_to_canvas(border)
 slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,0),maximum=unreal.Vector2D(.5,0)))
 slot.set_alignment(unreal.Vector2D(.5,0));slot.set_position(unreal.Vector2D(0,24));slot.set_size(unreal.Vector2D(700,72))
 text=unreal.find_object(tree,'AdminText') or unreal.new_object(unreal.TextBlock,outer=tree,name='AdminText')
 text.set_text(unreal.Text('ADMIN / СВОБОДНЫЙ ПОЛЁТ\nWASD • МЫШЬ   |   SPACE ↑   CTRL ↓   SHIFT ×4   |   F6 — ВЕРНУТЬСЯ'))
 text.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.2,.95,1,1)))
 font=text.get_editor_property('font');font.set_editor_property('font_object',A.load_asset('/Engine/EngineFonts/Roboto'));font.set_editor_property('size',15);text.set_font(font)
 text.set_editor_property('justification',unreal.TextJustify.CENTER);border.set_content(text)
 compile_bp(wbp);save(wbp)

 # Toggle is a character function; no console cheats or CheatManager required.
 g=Flow(bp,'Admin_ToggleFlight')
 g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
 split=g.branch(g.get('bAdminFlight'));enable=split.find_else_pin()
 # Disable: restore the exact entry point before re-enabling capsule collision.
 g.set('bAdminFlight',False)
 g.do(g.call('Engine.MovementComponent.StopMovementImmediately',target=g.get('CharacterMovement')))
 g.do(g.call('Engine.Actor.K2_SetActorTransform',NewTransform=g.get('AdminEntryTransform'),bSweep=False,bTeleport=True))
 g.do(g.call('Engine.Controller.SetControlRotation',target=g.pc(),NewRotation=g.get('AdminEntryRotation')))
 g.do(g.call('Engine.Actor.SetActorEnableCollision',bNewActorEnableCollision=g.get('AdminHadCollision')))
 g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=g.get('CameraBoom'),PropertyName='bDoCollisionTest',Value=g.get('AdminBoomCollision')))
 g.do(g.call('Engine.CharacterMovementComponent.SetMovementMode',target=g.get('CharacterMovement'),NewMovementMode='MOVE_Falling',NewCustomMode=0))
 g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=False))
 g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('AdminFlightHUD')))
 # Enable only once the intro has handed control to the player.
 g.cursor=enable
 g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
 g.set('AdminEntryTransform',g.out(g.call('Engine.Actor.GetTransform')))
 g.set('AdminEntryRotation',g.out(g.call('Engine.Controller.GetControlRotation',target=g.pc())))
 g.set('AdminHadCollision',g.out(g.call('Engine.Actor.GetActorEnableCollision')))
 boom=g.node(g.e.add_get_member_variable_node('bDoCollisionTest','/Script/Engine.SpringArmComponent'));val(boom.find_self_pin(),g.get('CameraBoom'))
 g.set('AdminBoomCollision',pin(boom,'bDoCollisionTest',True))
 g.set('bAdminFlight',True)
 g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=True))
 g.do(g.call('Engine.MovementComponent.StopMovementImmediately',target=g.get('CharacterMovement')))
 g.do(g.call('Engine.CharacterMovementComponent.SetMovementMode',target=g.get('CharacterMovement'),NewMovementMode='MOVE_None',NewCustomMode=0))
 g.do(g.call('Engine.Actor.SetActorEnableCollision',bNewActorEnableCollision=True))
 g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=g.get('CameraBoom'),PropertyName='bDoCollisionTest',Value=False))
 create=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(wbp).get_path_name(),OwningPlayer=g.pc()))
 g.set('AdminFlightHUD',g.out(create));g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('AdminFlightHUD'),ZOrder=100))
 compile_bp(bp)

 g=Flow(bp,'Admin_UpdateFlight')
 g.branch(g.get('bAdminFlight'))
 # Use full camera pitch for forward flight, a normalized vector for diagonals,
 # and frame delta for identical speed at different display frame rates.
 rotation=g.out(g.call('Engine.Controller.GetControlRotation',target=g.pc()))
 forward=g.math('Multiply_VectorFloat',A=g.math('GetForwardVector',InRot=rotation),B=g.axis('W','S'))
 right=g.math('Multiply_VectorFloat',A=g.math('GetRightVector',InRot=rotation),B=g.axis('D','A'))
 vertical=g.math('MakeVector',X=0,Y=0,Z=g.axis('SpaceBar','LeftControl'))
 direction=g.math('Normal',A=g.math('Add_VectorVector',A=g.math('Add_VectorVector',A=forward,B=right),B=vertical),Tolerance=.0001)
 multiplier=g.math('SelectFloat',A=g.get('AdminBoostMultiplier'),B=1.,bPickA=g.down('LeftShift'))
 dt=g.math('FClamp',Value=g.out(g.call('Engine.GameplayStatics.GetWorldDeltaSeconds')),Min=0.,Max=.05)
 distance=g.math('Multiply_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=g.get('AdminFlightSpeed'),B=multiplier),B=dt)
 g.do(g.call('Engine.Actor.K2_AddActorWorldOffset',DeltaLocation=g.math('Multiply_VectorFloat',A=direction,B=distance),bSweep=True,bTeleport=False))
 compile_bp(bp)

 # Preserve every existing input and Tick branch. Insert an independent Sequence
 # output once; subsequent runs update the functions without duplicating hooks.
 g=Flow(bp)
 existing=g.e.list_all_nodes()
 if not any('Admin_ToggleFlight' in n.get_node_title() for n in existing):
  options=[x for x in g.e.list_available_nodes([]) if x.endswith('|KeyboardEvents|F6')]
  if len(options)!=1:raise RuntimeError('F6 event choices '+str(options))
  key=g.node(g.e.create_node_from_name(options[0],unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',True)
  g.cursor=pin(key,'Pressed',True);g.do(g.selfcall('Admin_ToggleFlight'))
 if not any('Admin_UpdateFlight' in n.get_node_title() for n in existing):
  tick=g.e.find_event_node('ReceiveTick')
  if not tick:raise RuntimeError('Existing player Tick is missing')
  then=pin(tick,'then',True);old=list(then.list_connected_pins())
  options=[x for x in g.e.list_available_nodes([]) if x.split('|')[-1] in ('Sequence','Последовательность')]
  if len(options)!=1:raise RuntimeError('Sequence choices '+str(options))
  seq=g.node(g.e.create_node_from_name(options[0],unreal.Vector2D(),[]))
  then.break_pin_links();link(then,seq.find_execute_pin())
  for p in old:link(pin(seq,'then_0',True),p)
  g.cursor=pin(seq,'then_1',True);g.do(g.selfcall('Admin_UpdateFlight'))
 compile_bp(bp);save(bp)
 report.update(saved=True,player=PLAYER,widget=wp,toggle='F6',speed=2000,boost=4,return_to_entry=True)
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(unreal.Paths.project_saved_dir(),'admin_flight_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Admin flight authoring incomplete; see Saved/admin_flight_report.json')
