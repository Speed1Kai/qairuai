"""Reusable lift: walking passenger, bidirectional travel, landing calls and safe shaft."""
import unreal,os,sys,ast,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,pin,val,link,components,add,compile_bp,save,Graph
ROOT='/Game/LabTutorial/Elevator';METAL='/Game/LabTutorial/Industrial/'
saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir());TRAVEL=2126.;DOOR=2.8;RIDE=18.
stage=os.path.join(saved,'BidirectionalElevatorStaged');os.makedirs(stage,exist_ok=True)
backup=os.path.join(saved,'Backups','BidirectionalElevator',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
r={'saved':False,'installed':False,'files':[],'backup':backup,'gameplay_tested':False,'moved_shaft_objects':[]}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
def member(bp,name,typ,default):
 if name not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,typ,str(default))
def asset(name,parent=unreal.Actor):
 path=ROOT+'/BP_FreightElevatorBidirectional'
 if A.does_asset_exist(path):return A.load_asset(path)
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent);return unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_FreightElevatorBidirectional',ROOT,unreal.Blueprint,f)
def save_map(world):
 dst=os.path.join(stage,'Lvl_LabTutorial.umap');src=os.path.join(content,'Lvl_LabTutorial.umap');shutil.copy2(src,os.path.join(backup,'Lvl_LabTutorial.umap'))
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+dst.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(dst):raise RuntimeError('Map staging failed')
 r['files'].append({'source':dst,'destination':src})
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial');world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 meshes={name:A.load_asset(ROOT+'/'+name) for name in ('SM_FreightCabin','SM_FreightControlPanel','SM_FreightRoofDrive')}
 sounds={name:A.load_asset(ROOT+'/'+name) for name in ('S_FreightMotor','S_FreightDoor','S_FreightArrival')}
 # Reuse only the original component-construction prefix, without its old graph,
 # asset imports or one-way placement/save code.
 source=os.path.join(os.path.dirname(__file__),'Build_FreightElevator.py');tree=ast.parse(open(source,encoding='utf8').read())
 build=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build');prefix=[]
 for stmt in build.body:
  if isinstance(stmt,ast.For) and any(isinstance(x,ast.Constant) and x.value=='LiftState' for x in ast.walk(stmt)):break
  prefix.append(stmt)
 build.body=prefix+[ast.Return(value=ast.Name(id='bp',ctx=ast.Load()))];module=ast.fix_missing_locations(ast.Module(body=[build],type_ignores=[]));exec(compile(module,source,'exec'),globals())
 bp=globals()['build'](meshes,sounds,None)
 def box(name,p,extent,parent='ElevatorRoot',trigger=False):
  c=add(bp,unreal.BoxComponent,name,parent);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('relative_location',V(p));c.set_box_extent(V(extent));c.set_collision_profile_name('Trigger' if trigger else 'BlockAll');c.set_editor_property('generate_overlap_events',trigger);return c
 def mesh(name,model,p,scale,parent='ElevatorRoot',mat=None):
  c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(model);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(scale))
  if mat:c.set_material(0,mat)
  return c
 cs={n:c for h,c,n in components(bp)};cube=A.load_asset('/Engine/BasicShapes/Cube');metal=A.load_asset(METAL+'M_DoorArmor')
 cs['UpperThreshold'].set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
 mesh('LowerBridgeMesh',cube,(-286,0,11.9),(.8,3.5,.238),mat=metal)
 upper_bridge=mesh('UpperBridgeMesh',cube,(308,0,2137.9),(1.3,3.5,.238),mat=metal);upper_bridge.set_visibility(False)
 box('UpperApproachFloor',(335,0,2138),(35,175,12));mesh('UpperApproachMesh',cube,(335,0,2138),(.7,3.5,.24),mat=metal)
 # A shallow ramp replaces the original 24 cm abrupt boarding step.
 ramp=mesh('LowerBoardingRamp',cube,(-356,0,6),(1.,3.4,.12),mat=metal);ramp.set_editor_property('relative_rotation',unreal.Rotator(pitch=14));ramp.set_collision_profile_name('BlockAll')
 box('FrontDoorSafety',(-248,0,220),(65,162,190),'CabinRoot',True)
 box('RearDoorSafety',(248,0,220),(65,162,190),'CabinRoot',True)
 lower=box('LowerCallZone',(-410,-95,135),(100,115,130),trigger=True)
 upper=box('UpperCallZone',(455,-95,2275),(110,115,130),trigger=True)
 mesh('UpperCallPanel',meshes['SM_FreightControlPanel'],(410,225,2150),(.45,.45,.65))
 cs['ButtonCaption'].set_text(unreal.Text('[F]'));cs['ButtonCaption'].set_editor_property('relative_location',V((80,170,275)));cs['ButtonCaption'].set_editor_property('relative_rotation',unreal.Rotator(yaw=-90))
 for name,typ,default in [('LiftState',B.get_basic_type_by_name('int'),'0'),('CurrentFloor',B.get_basic_type_by_name('int'),'0'),('TargetFloor',B.get_basic_type_by_name('int'),'1'),('bCloseAborted',B.get_basic_type_by_name('bool'),'false'),('RideStartZ',B.get_basic_type_by_name('double'),'0'),('RideTargetZ',B.get_basic_type_by_name('double'),str(TRAVEL)),('PromptWidget',B.get_object_reference_type(unreal.UserWidget),'None')]:member(bp,name,typ,default)
 compile_bp(bp);g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 native=unreal.get_default_object(unreal.SystemLibrary)
 def timeline(name,duration):
  before={o.get_path_name() for o in unreal.ObjectIterator(unreal.TimelineTemplate) if o.get_outer()==B.generated_class(bp)}
  actions=[n for n in g.e.list_available_nodes([]) if n.startswith('|') and ('шкалу' in n or 'Timeline' in n)]
  node=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(),[]));template=next(o for o in unreal.ObjectIterator(unreal.TimelineTemplate) if o.get_outer()==B.generated_class(bp) and o.get_path_name() not in before)
  native.call_method('SetNamePropertyByName',(node,unreal.Name('TimelineName'),unreal.Name(name)));template.rename(name+'_Template');template.set_editor_property('timeline_length',duration);template.set_editor_property('length_mode',unreal.TimelineLengthMode.TL_TIMELINE_LENGTH);return node
 close=timeline('TL_CloseDoors',DOOR);ride=timeline('TL_Travel',RIDE);opened=timeline('TL_OpenDoors',DOOR)
 compile_bp(bp);g=Flow(bp)
 def pc():return g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 def player():return g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
 def overlaps(name):return g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get(name),Other=player()))
 def eqfloor(floor):return g.math('EqualEqual_IntInt',A=g.get('CurrentFloor'),B=floor)
 def clear_prompt():
  check=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('PromptWidget'))));otherwise=check.find_else_pin();g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('PromptWidget')));reset=g.set('PromptWidget','None');link(otherwise,reset.find_execute_pin());return check
 def show_prompt(message):
  wbp=A.load_asset(ROOT+'/WBP_ElevatorPrompt');q=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(wbp).get_path_name(),OwningPlayer=pc()));widget=g.out(q);g.set('PromptWidget',widget)
  for prop,text in [('HUDTitle','ГРУЗОВОЙ ЛИФТ'),('HUDMessage',message)]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=prop,Value=text))
  g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=45))
 def refresh_prompt():
  clear_prompt();g.branch(g.math('EqualEqual_IntInt',A=g.get('LiftState'),B=0));inside=g.branch(overlaps('BoardingZone'));outside=inside.find_else_pin();floor=g.branch(eqfloor(0));otherfloor=floor.find_else_pin();show_prompt('[F]  ПОДНЯТЬСЯ НА ЭТАЖ 01');g.cursor=otherfloor;show_prompt('[F]  СПУСТИТЬСЯ В ПОДВАЛ')
  g.cursor=outside;low=g.branch(g.math('BooleanAND',A=overlaps('LowerCallZone'),B=g.math('Not_PreBool',A=eqfloor(0))));high=low.find_else_pin();show_prompt('[F]  ВЫЗВАТЬ ЛИФТ');g.cursor=high;g.branch(g.math('BooleanAND',A=overlaps('UpperCallZone'),B=g.math('Not_PreBool',A=eqfloor(1))));show_prompt('[F]  ВЫЗВАТЬ ЛИФТ')
 def alpha(name,duration):
  p=g.out(g.call('Engine.TimelineComponent.GetPlaybackPosition',target=g.get(name)));t=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=p,B=duration),Min=0,Max=1)
  return g.math('Multiply_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=t,B=t),B=g.math('Subtract_DoubleDouble',A=3,B=g.math('Multiply_DoubleDouble',A=2,B=t)))
 pairs=[('CabFront',-248,24,0),('CabRear',248,24,1),('LowerGate',-310,24,0),('UpperGate',350,2150,1)]
 for node,clock,opening in [(close,'TL_CloseDoors',False),(opened,'TL_OpenDoors',True)]:
  a=alpha(clock,DOOR);g.cursor=pin(node,'Update',True)
  for group,x,z,floor in pairs:
   endpoint=g.math('SelectFloat',A=246,B=80,bPickA=eqfloor(floor))
   for sign,label in [(-1,'Left'),(1,'Right')]:
    variable_y=g.math('Multiply_DoubleDouble',A=endpoint,B=sign)
    start=g.math('MakeVector',X=x,Y=(80.*sign if opening else variable_y),Z=z);end=g.math('MakeVector',X=x,Y=(variable_y if opening else 80.*sign),Z=z)
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get(group+label),NewLocation=g.math('VLerp',A=start,B=end,Alpha=a),bSweep=False,bTeleport=False))
 a=alpha('TL_Travel',RIDE);g.cursor=pin(ride,'Update',True)
 z=g.math('Lerp',A=g.get('RideStartZ'),B=g.get('RideTargetZ'),Alpha=a)
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('CabinRoot'),NewLocation=g.math('MakeVector',X=0,Y=0,Z=z),bSweep=False,bTeleport=False))
 def bridge(floor,enabled):
  group='Lower' if floor==0 else 'Upper'
  g.do(g.call('Engine.PrimitiveComponent.SetCollisionEnabled',target=g.get(group+'Threshold'),NewType='QueryAndPhysics' if enabled else 'NoCollision'))
  g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(group+'BridgeMesh'),bNewVisibility=enabled,bPropagateToChildren=False))
 def restore_bridges():
  check=g.branch(eqfloor(0));otherwise=check.find_else_pin();bridge(0,True);bridge(1,False);first=g.cursor;g.cursor=otherwise;bridge(0,False);bridge(1,True);return first
 def door_sound():g.do(g.call('Engine.AudioComponent.Play',target=g.get('DoorAudio'),StartTime=0))
 def sound(path):g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=path,Location=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('CabinRoot'))),AttenuationSettings=METAL+'SA_BlastDoor',VolumeMultiplier=.6))
 def set_lenses():
  check=g.branch(eqfloor(0));otherwise=check.find_else_pin()
  for group,green in [('Lower',True),('Upper',False)]:g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get(group+'GateIndicator'),ElementIndex=0,Material=METAL+('M_DoorStatus_Green' if green else 'M_DoorStatus_Red')))
  first=g.cursor;g.cursor=otherwise
  for group,green in [('Lower',False),('Upper',True)]:g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get(group+'GateIndicator'),ElementIndex=0,Material=METAL+('M_DoorStatus_Green' if green else 'M_DoorStatus_Red')))
  return first
 # Existing and new overlaps refresh context without a per-frame widget rebuild.
 for name,c in [('BoardingZone',cs['BoardingZone']),('LowerCallZone',lower),('UpperCallZone',upper)]:
  for event_name in ('OnComponentBeginOverlap','OnComponentEndOverlap'):
   event=g.e.add_component_bound_event_node(c,event_name);g.cursor=pin(event,'then',True);g.branch(g.math('EqualEqual_ObjectObject',A=pin(event,'OtherActor',True),B=player()));refresh_prompt()
 actions=[n for n in g.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|F')]
 key=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True);g.branch(g.math('EqualEqual_IntInt',A=g.get('LiftState'),B=0))
 inside=g.branch(overlaps('BoardingZone'));outside=inside.find_else_pin();g.set('TargetFloor',g.math('Subtract_IntInt',A=1,B=g.get('CurrentFloor')));starts=[g.cursor]
 g.cursor=outside;low=g.branch(g.math('BooleanAND',A=overlaps('LowerCallZone'),B=g.math('Not_PreBool',A=eqfloor(0))));high=low.find_else_pin();g.set('TargetFloor',0);starts.append(g.cursor)
 g.cursor=high;g.branch(g.math('BooleanAND',A=overlaps('UpperCallZone'),B=g.math('Not_PreBool',A=eqfloor(1))));g.set('TargetFloor',1);starts.append(g.cursor)
 state=g.set('LiftState',1)
 for tail in starts[:-1]:link(tail,state.find_execute_pin())
 g.set('bCloseAborted',False);g.set('RideStartZ',g.math('SelectFloat',A=0,B=TRAVEL,bPickA=eqfloor(0)));g.set('RideTargetZ',g.math('SelectFloat',A=0,B=TRAVEL,bPickA=g.math('EqualEqual_IntInt',A=g.get('TargetFloor'),B=0)))
 clear_prompt();bridge(0,False);bridge(1,False)
 for group in ('Lower','Upper'):g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get(group+'GateIndicator'),ElementIndex=0,Material=METAL+'M_DoorStatus_Red'))
 door_sound();sound(METAL+'S_BlastDoorHydraulicRelease');link(g.cursor,pin(close,'PlayFromStart'))
 # If a player walks into a closing doorway, reverse to open and stay at this floor.
 g.event('ReceiveTick');g.branch(g.math('EqualEqual_IntInt',A=g.get('LiftState'),B=1));g.branch(g.math('Not_PreBool',A=g.get('bCloseAborted')))
 obstructed=g.math('BooleanOR',A=g.math('BooleanAND',A=eqfloor(0),B=overlaps('FrontDoorSafety')),B=g.math('BooleanAND',A=eqfloor(1),B=overlaps('RearDoorSafety')));g.branch(obstructed);g.set('bCloseAborted',True);door_sound();link(g.cursor,pin(close,'Reverse'))
 g.cursor=pin(close,'Finished',True);g.do(g.call('Engine.AudioComponent.Stop',target=g.get('DoorAudio')));aborted=g.branch(g.get('bCloseAborted'));depart=aborted.find_else_pin();tail=restore_bridges();idle=g.set('LiftState',0);link(tail,idle.find_execute_pin());g.set('bCloseAborted',False);tail=set_lenses();dummy=g.set('LiftState',0);link(tail,dummy.find_execute_pin());refresh_prompt()
 g.cursor=depart;g.set('LiftState',2);sound(METAL+'S_BlastDoorThud');g.do(g.call('Engine.AudioComponent.FadeIn',target=g.get('RideAudio'),FadeInDuration=.7,FadeVolumeLevel=.6,StartTime=0));link(g.cursor,pin(ride,'PlayFromStart'))
 g.cursor=pin(ride,'Finished',True);g.set('CurrentFloor',g.get('TargetFloor'));g.set('LiftState',3);g.do(g.call('Engine.AudioComponent.FadeOut',target=g.get('RideAudio'),FadeOutDuration=.65,FadeVolumeLevel=0));sound(sounds['S_FreightArrival'].get_path_name());tail=restore_bridges();nextnode=g.set('LiftState',3);link(tail,nextnode.find_execute_pin());tail=set_lenses();nextnode=g.set('LiftState',3);link(tail,nextnode.find_execute_pin());door_sound();link(g.cursor,pin(opened,'PlayFromStart'))
 g.cursor=pin(opened,'Finished',True);g.do(g.call('Engine.AudioComponent.Stop',target=g.get('DoorAudio')));g.set('LiftState',0);refresh_prompt()
 compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',70);save(bp)
 # Keep existing light actors/components: the building-power controller references
 # them. Move the fixtures to the wall rather than deleting their references.
 for a in sub.get_all_level_actors():
  name=a.get_actor_label()
  if name.startswith('LAB_Shaft_LightStrip_'):
   z=a.get_actor_location().z;a.set_actor_location(V((2650,303,z)),False,True);a.set_actor_rotation(unreal.Rotator(),False);a.set_actor_scale3d(V((1.6,.025,.12)));r['moved_shaft_objects'].append(name)
  for idx,z,side in [(5,745,1),(6,1485,-1),(7,2085,1)]:
   if name=='LAB_RouteLamp_Fixture_%02d'%idx:
    a.set_actor_location(V((2650,side*304,z)),False,True);a.set_actor_rotation(unreal.Rotator(),False);a.set_actor_scale3d(V((1.4,.12,.26)));r['moved_shaft_objects'].append(name)
   elif name=='LAB_RouteLamp_Lens_%02d'%idx:
    a.set_actor_location(V((2650,side*296,z)),False,True);a.set_actor_rotation(unreal.Rotator(),False);a.set_actor_scale3d(V((1.1,.03,.16)));r['moved_shaft_objects'].append(name)
   elif name=='LAB_RouteMaintenanceLight_%02d'%idx:
    a.set_actor_location(V((2650,side*285,z)),False,True);a.point_light_component.set_attenuation_radius(340);r['moved_shaft_objects'].append(name)
 # Seal the previously open west shaft above the ground-floor doorway.
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label() in ('LAB_FreightElevator','LIFT_ShaftWestClosure'):sub.destroy_actor(a)
 wall=sub.spawn_actor_from_class(unreal.StaticMeshActor,V((2300,0,1615)),unreal.Rotator());wall.set_actor_label('LIFT_ShaftWestClosure');wall.set_folder_path('LAB/02_Shaft');wall.static_mesh_component.set_static_mesh(cube);wall.set_actor_scale3d(V((.8,4,23.7)));wall.static_mesh_component.set_material(0,A.load_asset(METAL+'M_DistressedMetal'));wall.static_mesh_component.set_collision_profile_name('BlockAll')
 lift=sub.spawn_actor_from_class(B.generated_class(bp),V((2650,0,0)),unreal.Rotator());lift.set_actor_label('LAB_FreightElevator');lift.set_folder_path('LAB/03_Interactables')
 # Placed actors can retain disabled input even when the CDO has Player 0.
 lift.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
 lift.set_editor_property('input_priority',70)
 save_map(world)
 r.update(saved=True,blueprint=bp.get_path_name(),bidirectional=True,free_passenger_movement=True,landing_calls=True,door_safety=True,travel_cm=TRAVEL,ride_seconds=RIDE,door_seconds=DOOR)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'bidirectional_elevator_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Bidirectional elevator authoring failed; see report')
