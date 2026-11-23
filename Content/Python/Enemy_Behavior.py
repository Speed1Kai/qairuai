from Enemy_Common import *

def blackboard():
 bb=data('BB_EnemyRobot',unreal.BlackboardData,unreal.BlackboardDataFactory());keys=[]
 specs=[('SelfActor','Object'),('TargetActor','Object'),('LastKnownLocation','Vector'),('PatrolLocation','Vector'),('MovementState','Enum'),('HomeLocation','Vector'),('NeedsAlert','Bool'),('HasSearch','Bool'),('IsDead','Bool')]
 for name,type in specs:
  entry=unreal.BlackboardEntry();entry.set_editor_property('entry_name',name)
  key=unreal.new_object(cls('/Script/AIModule.BlackboardKeyType_'+type),outer=bb)
  if type=='Object':key.set_editor_property('BaseClass',unreal.Actor.static_class())
  if type=='Enum':key.set_editor_property('EnumType',obj('/Script/AIModule.EPathFollowingStatus'))
  entry.set_editor_property('key_type',key);keys.append(entry)
 bb.set_editor_property('keys',keys);save(bb);return bb

def tasks(sound):
 results={}
 def montage(g,pawn,asset,rate=1.):
  mesh=g.out(g.call('Engine.Actor.GetComponentByClass',target=pawn,ComponentClass='/Script/Engine.SkeletalMeshComponent'))
  anim=g.out(g.call('Engine.SkeletalMeshComponent.GetAnimInstance',target=mesh))
  g.do(g.call('Engine.AnimInstance.PlaySlotAnimationAsDynamicMontage',target=anim,Asset=asset,SlotNodeName='DefaultSlot',BlendInTime=.12,BlendOutTime=.2,InPlayRate=rate,LoopCount=1))
  return anim
 bp,g,ai,pawn=task('BTT_EnemyAlert');bb=g.bb(ai)
 cond=g.branch(g.bbget(bb,'NeedsAlert','Bool'));no=pin(cond,'else',True)
 g.bbset(bb,'NeedsAlert',False,'Bool');g.bbset(bb,'MovementState',1,'Enum');g.speed(pawn,0)
 g.do(g.call('Engine.Controller.StopMovement',target=ai))
 alertanim=montage(g,pawn,'/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_ChargedAttack.MM_ChargedAttack',.7)
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.85));g.do(g.call('Engine.AnimInstance.Montage_Stop',target=alertanim,InBlendOutTime=.15));g.bbset(bb,'MovementState',3,'Enum');g.speed(pawn,550);g.finish()
 g.cursor=no;g.bbset(bb,'MovementState',3,'Enum');g.speed(pawn,550);g.finish();compile_bp(bp);save(bp);results['alert']=bp
 bp,g,ai,pawn=task('BTT_EnemyPatrol');bb=g.bb(ai);g.bbset(bb,'MovementState',0,'Enum');g.speed(pawn,180)
 random=g.call('NavigationSystem.NavigationSystemV1.K2_GetRandomReachablePointInRadius',Origin=g.bbget(bb,'HomeLocation','Vector'),Radius=520)
 g.bbset(bb,'PatrolLocation',g.out(random,'RandomLocation'),'Vector');g.finish(g.out(random));compile_bp(bp);save(bp);results['patrol']=bp
 bp,g,ai,pawn=task('BTT_EnemySearch');bb=g.bb(ai);g.bbset(bb,'MovementState',2,'Enum');g.speed(pawn,180);g.finish();compile_bp(bp);save(bp);results['search']=bp
 bp,g,ai,pawn=task('BTT_EnemyFinishSearch');bb=g.bb(ai)
 var(bp,'InitialScanYaw','real','0');compile_bp(bp);g=graph(bp);ev=g.override('ReceiveExecuteAI');ai=pin(ev,'OwnerController',True);pawn=pin(ev,'ControlledPawn',True);bb=g.bb(ai)
 rot=g.call('Engine.KismetMathLibrary.BreakRotator',InRot=g.out(g.call('Engine.Actor.K2_GetActorRotation',target=pawn)));g.set('InitialScanYaw',g.out(rot,'Yaw'))
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=3.0));g.bbset(bb,'HasSearch',False,'Bool');g.bbset(bb,'MovementState',0,'Enum');g.finish();compile_bp(bp);save(bp);results['endsearch']=bp
 g.override('ReceiveTickAI');ev=g.e.find_event_node('ReceiveTickAI');scanpawn=pin(ev,'ControlledPawn',True)
 now=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))
 yaw=g.math('Add_DoubleDouble',A=g.get('InitialScanYaw'),B=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=g.math('Multiply_DoubleDouble',A=now,B=2.5)),B=28.))
 g.do(g.call('Engine.Actor.K2_SetActorRotation',target=scanpawn,NewRotation=g.math('MakeRotator',Roll=0,Pitch=0,Yaw=yaw),bTeleportPhysics=False));compile_bp(bp);save(bp)
 bp,g,ai,pawn=task('BTT_EnemyStrike');bb=g.bb(ai);target=g.bbget(bb,'TargetActor');g.speed(pawn,0)
 montage(g,pawn,'/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_03.MM_Attack_03',.9)
 # Only damage a target still within reach after the mechanical wind-up.
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.42))
 near=g.math('BooleanAND',A=g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=target)),B=g.math('Less_DoubleDouble',A=g.out(g.call('Engine.Actor.GetDistanceTo',target=pawn,OtherActor=target)),B=240))
 branch=g.branch(near);skip=pin(branch,'else',True)
 g.do(g.call('Engine.GameplayStatics.ApplyDamage',DamagedActor=target,BaseDamage=22.,EventInstigator=ai,DamageCauser=pawn))
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.65));g.speed(pawn,550);g.finish()
 g.cursor=skip;g.speed(pawn,550);g.finish();compile_bp(bp);save(bp);results['strike']=bp
 bp=asset('BTS_EnemyMemory',unreal.BTService_BlueprintBase);target_key(bp);compile_bp(bp);g=graph(bp);ev=g.override('ReceiveTickAI');ai=pin(ev,'OwnerController',True);pawn=pin(ev,'ControlledPawn',True);bb=g.bb(ai)
 state=g.bbget(bb,'MovementState','Enum')
 g.do(g.call('Engine.KismetSystemLibrary.SetIntPropertyByName',Object=pawn,PropertyName='StateIndex',Value=state))
 valid=g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.bbget(bb,'TargetActor')));g.branch(valid)
 g.bbset(bb,'LastKnownLocation',g.out(g.call('Engine.Actor.K2_GetActorLocation',target=g.bbget(bb,'TargetActor'))),'Vector')
 compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('interval',.20);cdo.set_editor_property('random_deviation',.025);save(bp);results['memory']=bp
 return results

def behavior(bb,tasks):
 bt=data('BT_EnemyRobot',unreal.BehaviorTree,unreal.BehaviorTreeFactory());bt.set_editor_property('blackboard_asset',bb)
 def new(type,name):
  o=unreal.new_object(cls('/Script/AIModule.'+type),outer=bt);o.set_editor_property('node_name',name);return o
 def tasknode(key):return unreal.new_object(B.generated_class(tasks[key]),outer=bt)
 def child(node,decs=[]):
  c=unreal.BTCompositeChild();c.set_editor_property('child_composite' if isinstance(node,unreal.BTCompositeNode) else 'child_task',node);c.set_editor_property('decorators',decs);return c
 def selector(key):
  s=unreal.BlackboardKeySelector();s.set_editor_property('selected_key_name',key);return s
 def move(key,radius):
  n=new('BTTask_MoveTo','Move to '+key);n.set_editor_property('blackboard_key',selector(key))
  v=n.get_editor_property('acceptable_radius');v.set_editor_property('default_value',float(radius));n.set_editor_property('acceptable_radius',v)
  return n
 def dec(key):
  n=new('BTDecorator_Blackboard',key+' is set');n.set_editor_property('blackboard_key',selector(key));n.set_editor_property('flow_abort_mode',unreal.BTFlowAbortMode.BOTH);return n
 root=new('BTComposite_Selector','ELITE GUARD / priority selector');root.set_editor_property('services',[unreal.new_object(B.generated_class(tasks['memory']),outer=bt)])
 chase=new('BTComposite_Sequence','01 / ALERT - PURSUIT - STRIKE');chase.set_editor_property('children',[child(tasknode('alert')),child(move('TargetActor',125)),child(tasknode('strike'))])
 search=new('BTComposite_Sequence','02 / LAST KNOWN POSITION - SEARCH');search.set_editor_property('children',[child(tasknode('search')),child(move('LastKnownLocation',75)),child(tasknode('endsearch'))])
 wait=new('BTTask_Wait','Mechanical scan pause');v=wait.get_editor_property('wait_time');v.set_editor_property('default_value',1.6);wait.set_editor_property('wait_time',v)
 patrol=new('BTComposite_Sequence','03 / REACHABLE NAVMESH PATROL');patrol.set_editor_property('children',[child(tasknode('patrol')),child(move('PatrolLocation',55)),child(wait)])
 root.set_editor_property('children',[child(chase,[dec('TargetActor')]),child(search,[dec('HasSearch')]),child(patrol)])
 bt.set_editor_property('root_node',root);save(bt);return bt

def controller(bb,bt,sound):
 bp=asset('AIC_EnemyRobot',unreal.AIController);compile_bp(bp)
 perception=add(bp,unreal.AIPerceptionComponent,'RobotPerception')
 sight=unreal.new_object(unreal.AISenseConfig_Sight,outer=perception)
 for k,v in {'sight_radius':1800.,'lose_sight_radius':2200.,'peripheral_vision_angle_degrees':60.,'max_age':4.}.items():sight.set_editor_property(k,v)
 affiliation=sight.get_editor_property('detection_by_affiliation')
 for k in ('detect_enemies','detect_neutrals','detect_friendlies'):affiliation.set_editor_property(k,True)
 sight.set_editor_property('detection_by_affiliation',affiliation);perception.set_editor_property('senses_config',[sight]);perception.set_editor_property('dominant_sense',unreal.AISense_Sight.static_class())
 var(bp,'HasVisualContact','bool','false');compile_bp(bp);g=graph(bp)
 ev=g.override('ReceivePossess');pawn=pin(ev,'PossessedPawn',True)
 use=g.call('AIModule.AIController.UseBlackboard',BlackboardAsset=bb.get_path_name());g.do(use);board=g.out(use,'BlackboardComponent')
 g.bbset(board,'SelfActor',pawn);g.bbset(board,'HomeLocation',g.out(g.call('Engine.Actor.K2_GetActorLocation',target=pawn)),'Vector');g.bbset(board,'MovementState',0,'Enum')
 g.do(g.call('AIModule.AIController.RunBehaviorTree',BTAsset=bt.get_path_name()))
 event=g.e.add_component_bound_event_node(perception,'OnTargetPerceptionUpdated');g.cursor=pin(event,'then',True);actor=pin(event,'Actor',True)
 player=g.out(g.call('Engine.GameplayStatics.GetPlayerPawn',PlayerIndex=0));g.branch(g.math('EqualEqual_ObjectObject',A=actor,B=player))
 seen=g.call('AIModule.AIPerceptionComponent.GetCurrentlyPerceivedActors',target=g.get('RobotPerception'),SenseToUse=unreal.AISense_Sight.static_class().get_path_name());g.do(seen)
 contains=g.out(g.call('Engine.KismetArrayLibrary.Array_Contains',TargetArray=g.out(seen,'OutActors'),ItemToFind=actor))
 b=g.branch(contains);lost=pin(b,'else',True);board=g.bb()
 first=g.branch(g.math('Not_PreBool',A=g.get('HasVisualContact')));already=pin(first,'else',True)
 g.set('HasVisualContact',True);g.bbset(board,'NeedsAlert',True,'Bool')
 owner=g.out(g.call('Engine.Controller.K2_GetPawn'))
 audio=g.out(g.call('Engine.Actor.GetComponentByClass',target=owner,ComponentClass='/Script/Engine.AudioComponent'))
 g.do(g.call('Engine.AudioComponent.Play',target=audio,StartTime=0.))
 g.bbset(board,'LastKnownLocation',g.out(g.call('Engine.Actor.K2_GetActorLocation',target=actor)),'Vector');g.bbset(board,'TargetActor',actor);g.bbset(board,'HasSearch',False,'Bool')
 g.cursor=already;g.bbset(board,'TargetActor',actor)
 g.cursor=lost;g.set('HasVisualContact',False);g.bbset(board,'HasSearch',True,'Bool');g.bbset(board,'MovementState',2,'Enum');g.do(g.call('AIModule.BlackboardComponent.ClearValue',target=board,KeyName='TargetActor'))
 compile_bp(bp);save(bp);return bp
