"""City-only pursuit and combat diagnostics. Existing laboratory elite is untouched."""
import unreal,sys,os,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
R={}
try:
 for name in ('BP_CityEnceladus','BP_Enceladus_Carbine','BP_Enceladus_Shotgun','BP_Enceladus_Plasma'):
  bp=A.load_asset(ROOT+'/'+name)
  for n,k,d in [('CityNextPath','real','0'),('CityLastSeen','real','-100'),('CityOwnAI','bool','false'),('CityMoveResult','int','0')]:var(bp,n,k,d)
  compile_bp(bp)
  for h,c,n in components(bp):
   if isinstance(c,unreal.SceneComponent):c.set_mobility(unreal.ComponentMobility.MOVABLE)
  g=Graph(bp,'City_Pursuit');g.branch(g.math('Not_PreBool',A=g.get('bIsDead')))
  ai=g.out(g.call('AIModule.AIBlueprintHelperLibrary.GetAIController',ControlledActor=g.self()));g.branch(g.valid(ai));player=g.player();g.branch(g.valid(player))
  init=g.branch(g.math('Not_PreBool',A=g.get('CityOwnAI')));already=init.find_else_pin()
  # Stop the legacy melee behavior once; ranged units use their own stand-off distance.
  brain=g.out(g.call('Engine.Actor.GetComponentByClass',target=ai,ComponentClass='/Script/AIModule.BrainComponent'))
  ok=g.branch(g.valid(brain));skip=ok.find_else_pin();g.do(g.call('AIModule.BrainComponent.StopLogic',target=brain,Reason='City ranged combat'))
  merge=g.set('CityOwnAI',True);link(skip,merge.find_execute_pin())
  gate=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('CityNextPath')));link(already,gate.find_execute_pin());g.set('CityNextPath',g.math('Add_DoubleDouble',A=g.now(),B=.6))
  dist=g.out(g.call('Engine.Actor.GetDistanceTo',OtherActor=player));g.branch(g.math('Less_DoubleDouble',A=dist,B=2600.))
  seen=g.branch(g.out(g.call('Engine.Controller.LineOfSightTo',target=ai,Other=player,bAlternateChecks=False)));lost=seen.find_else_pin();g.set('CityLastSeen',g.now())
  memory=g.branch(g.math('Less_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=g.now(),B=g.get('CityLastSeen')),B=5.));link(lost,memory.find_execute_pin())
  g.set('StateIndex',1);g.cmset('MaxWalkSpeed',400.)
  far=g.branch(g.math('Greater_DoubleDouble',A=dist,B=g.math('Add_DoubleDouble',A=g.get('CityPreferredRange'),B=70.)));close=far.find_else_pin()
  move=g.do(g.call('AIModule.AIController.MoveToActor',target=ai,Goal=player,AcceptanceRadius=g.get('CityPreferredRange'),bStopOnOverlap=False,bUsePathfinding=True,bCanStrafe=True,bAllowPartialPath=True))
  # Store the returned request state for finite integration diagnostics.
  g.cursor=close;g.do(g.call('Engine.Controller.StopMovement',target=ai))
  compile_bp(bp)
  e=G.get_graph_editor_by_name(bp,'EventGraph')
  if not any(n.get_name()=='CityPursuitTick' for n in e.list_all_nodes()):hook(bp,e.find_event_node('ReceiveTick').find_then_pin(),'City_Pursuit','CityPursuitTick')
  compile_bp(bp);save(bp)
  R[name]=True
 # More reliable direct-hit lethality while retaining the 8 metre falloff envelope.
 blast=A.load_asset(FX+'/BP_ProtocolBlast');g=G.get_graph_editor_by_name(blast,'EventGraph')
 for n in g.list_all_nodes():
  if 'ApplyRadialDamageWithFalloff' in str(n.get_node_title()):val(pin(n,'DamageInnerRadius'),350.);val(pin(n,'MinimumDamage'),180.);val(pin(n,'DamagePreventionChannel'),'ECC_Camera')
 compile_bp(blast);save(blast)
 cover=A.load_asset(FX+'/BP_ProtocolDestructible')
 intact=next(c for h,c,n in components(cover) if n=='Intact');intact.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
 g=Graph(cover,'Cover_Init');g.do(g.call('Engine.PrimitiveComponent.SetCollisionObjectType',target=g.get('Intact'),Channel='ECC_WorldDynamic'));compile_bp(cover)
 e=G.get_graph_editor_by_name(cover,'EventGraph');event=e.find_event_node('ReceiveBeginPlay')
 if not event:event=B.add_event_override(cover,'ReceiveBeginPlay',unreal.IntPoint(x=0,y=7000))
 if not any(n.get_name()=='CoverInit' for n in e.list_all_nodes()):hook(cover,event.find_then_pin(),'Cover_Init','CoverInit')
 compile_bp(cover);save(cover)
 city=A.load_asset('/Game/Environment/DowntownFirstBlock/BP_FirstCityBlock')
 for h,c,n in components(city):
  if isinstance(c,unreal.PrimitiveComponent) and str(c.get_collision_profile_name())=='BlockAll':c.set_editor_property('can_ever_affect_navigation',True)
 compile_bp(city);save(city)
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 if world.get_name()=='Lvl_SurfaceArrival':
  unreal.SystemLibrary.execute_console_command(world,'RebuildNavigation')
  unreal.EditorLoadingAndSavingUtils.save_current_level()
 R['saved']=True
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'citycombat_pursuit_patch.json'),'w'),indent=2)





