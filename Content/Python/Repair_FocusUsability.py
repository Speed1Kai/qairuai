"""Replace brittle proxy-hit gating with proximity, view cone and native line of sight."""
import unreal,os,sys,json
src=os.path.join(os.path.dirname(__file__),'Upgrade_FocusedInteraction.py')
exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
focus=A.load_asset(ROOT+'/BP_InteractionFocus');backup_asset(focus.get_path_name().split('.')[0])
for h,c,n in components(focus):
 if c and n=='FocusCollider':c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
for name,scale in [('M_FocusCyan',50.),('M_StandbyCyan',100.)]:
 mat=A.load_asset(ROOT+'/'+name)
 for expr in unreal.ObjectIterator(unreal.MaterialExpressionConstant3Vector):
  if expr.get_outer()==mat:expr.set_editor_property('constant',unreal.LinearColor(.03*scale,.7*scale,.86*scale,1))
 M.recompile_material(mat);save(mat)
g=Flow(focus);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
g.event('ReceiveBeginPlay');g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.08))
g.branch(g.math('EqualEqual_NameName',A=g.get('FocusField'),B='FocusCabButton'));g.do(g.call('Engine.Actor.K2_SetActorRelativeLocation',NewRelativeLocation='(X=80,Y=165,Z=185)',bSweep=False,bTeleport=True))
g.event('ReceiveTick');g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=player(g))))
pos=g.out(g.call('Engine.Actor.K2_GetActorLocation'));dist=g.math('Vector_Distance',V1=pos,V2=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=player(g))))
near=g.math('LessEqual_DoubleDouble',A=dist,B=260.)
g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('BrightFrame'),bNewVisibility=near,bPropagateToChildren=True))
camera=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));camera_pos=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=camera));rot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=camera))
direction=g.math('GetDirectionUnitVector',From=camera_pos,To=pos);dot=g.math('Dot_VectorVector',A=g.math('GetForwardVector',InRot=rot),B=direction)
# Trace toward the actual device rather than its invisible marker actor.
# Device casing may stop the trace just before the marker; that is a valid hit.
trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=camera_pos,End=pos,TraceChannel='TraceTypeQuery1',bTraceComplex=False,DrawDebugType='None',bIgnoreSelf=True))
hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'))
clear=g.math('Not_PreBool',A=g.out(trace))
on_device=g.math('EqualEqual_ObjectObject',A=g.out(hit,'HitActor'),B=g.get('Device'))
at_endpoint=g.math('LessEqual_DoubleDouble',A=g.math('Vector_Distance',V1=g.out(hit,'ImpactPoint'),V2=pos),B=90.)
los=g.math('BooleanOR',A=clear,B=g.math('BooleanOR',A=on_device,B=at_endpoint))
aimed=g.math('BooleanAND',A=near,B=g.math('BooleanAND',A=g.math('Greater_DoubleDouble',A=dot,B=.4),B=los))
g.branch(g.math('NotEqual_BoolBool',A=aimed,B=g.get('bFocused')));g.set('bFocused',aimed);g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Device'))));g.do(g.call('Engine.KismetSystemLibrary.SetBoolPropertyByName',Object=g.get('Device'),PropertyName=g.get('FocusField'),Value=g.get('bFocused')))
split=g.branch(g.get('bFocused'));lost=split.find_else_pin();hint=A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint');q=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(hint).get_path_name(),OwningPlayer=pc(g)));widget=g.out(q);g.set('Prompt',widget)
for prop,value in [('HUDTitle','ВЗАИМОДЕЙСТВИЕ'),('HUDMessage',g.get('InteractionText'))]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=prop,Value=value))
g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=widget,PropertyName='HUDLifetime',Value=86400.));g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=65))
g.cursor=lost;g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Prompt'))));g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('Prompt')))
compile_bp(focus);save(focus)
for a in sub.get_all_level_actors():
 name=a.get_actor_label()
 if name.startswith('HOLO_ArchiveProjector_') or name in ['BASE_MainPowerSwitch','LAB_FreightElevator','ARCHIVE_WorldCollapseBoard']:
  a.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
  a.set_editor_property('input_priority',90 if name=='BASE_MainPowerSwitch' else 70)
 if name.startswith('FOCUS_') and str(a.get_editor_property('FocusField'))=='FocusCabButton':
  lift=a.get_editor_property('Device');cabin=lift.get_editor_property('CabinRoot');a.set_actor_location(cabin.get_world_location()+V((80,165,185)),False,True)
for i in range(1,7):
 bp=A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i);e=G.get_graph_editor_by_name(bp,'EventGraph')
 for n in e.list_all_nodes():
  if 'B' not in {str(p.get_pin_name()) for p in n.list_all_pins()}:continue
  p=n.find_input_pin('B')
  if p.is_valid() and p.get_pin_value() in ['350','350.0','350.000000']:p.set_pin_value('225.0')
 compile_bp(bp);save(bp)
# Deleted CRT lights must not break the remaining power restoration chain.
power=A.load_asset('/Game/LabTutorial/Basement/BP_BuildingPower');backup_asset(power.get_path_name().split('.')[0]);e=G.get_graph_editor_by_name(power,'EventGraph')
for n in list(e.list_all_nodes()):
 target=n.find_self_pin()
 if not target.is_valid() or not n.find_execute_pin().is_valid():continue
 source=list(target.list_connected_pins())
 if not source:continue
 if not any(x in str(source[0].get_owning_node().get_node_title()) for x in ['CircuitLight_000','CircuitLight_001']):continue
 incoming=list(n.find_execute_pin().list_connected_pins());outgoing=list(n.find_then_pin().list_connected_pins());n.find_execute_pin().break_pin_links()
 valid=e.add_call_function_node('/Script/Engine.KismetSystemLibrary.IsValid');val(pin(valid,'Object'),source[0]);guard=e.add_branch_node();val(pin(guard,'Condition'),pin(valid,'ReturnValue',True))
 for p in incoming:link(p,guard.find_execute_pin())
 link(guard.find_then_pin(),n.find_execute_pin())
 for p in outgoing:link(guard.find_else_pin(),p)
compile_bp(power);save(power)
# Keep one device's key binding from consuming input intended for another.
paths=['/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional','/Game/LabTutorial/Basement/BP_BuildingPower',ROOT+'/BP_WorldArchiveBoard']+['/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i for i in range(1,7)]
for path in paths:
 bp=A.load_asset(path);e=G.get_graph_editor_by_name(bp,'EventGraph')
 for n in e.list_all_nodes():
  if n.get_class().get_name()=='K2Node_InputKey':n.set_editor_property('bConsumeInput',False)
 compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('block_input',False);save(bp)
unreal.EditorLoadingAndSavingUtils.save_current_level()
with open(os.path.join(saved,'focus_repair_report.json'),'w',encoding='utf8') as f:json.dump({'saved':True,'method':'distance + view cone + native line of sight','cab_button_relative':[80,165,185],'input_enabled':True,'gameplay_verified':False},f,indent=2)
