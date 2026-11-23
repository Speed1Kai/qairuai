"""Author a native, F-operated through-car freight elevator in the live map."""
import unreal,os,sys,json,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,xyz,pin,val,link,components,add,compile_bp,save,Graph
from Industrial_Materials import make_material
ROOT='/Game/LabTutorial/Elevator';METAL='/Game/LabTutorial/Industrial/'
saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
report={'asset_saved':False,'map_installed':False,'door_seconds':2.8,'ride_seconds':18.,'travel_cm':2126.,'floor_height_cm':2150.}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world()
if world.get_name()!='Lvl_LabTutorial':raise RuntimeError('Open the tutorial map before building its elevator')
backup=os.path.join(saved,'Backups','FreightElevator',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);report['backup']=backup
def package(name,file):
 os.makedirs(os.path.dirname(file),exist_ok=True)
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="'+name+'" FILE="'+file.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(file):raise RuntimeError('Package not saved: '+file)
def asset(name,parent=unreal.Actor):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent)
 return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
def member(bp,name,type,default):
 if name not in map(str,B.list_member_variable_names(bp)):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,type,str(default))
class LiftGraph(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def external(self,name,cls,target):
  n=self.node(self.e.add_get_member_variable_node(name,cls));val(n.find_self_pin(),target);return pin(n,name,True)

def import_content():
 make_material('M_ElevatorWarm','glow',(45.,32.,16.),0,.5)
 source=os.path.join(content,'LabTutorial','Elevator','Source')
 with open(os.path.join(source,'elevator_manifest.json')) as f:specs=json.load(f)
 meshes={};tools=unreal.AssetToolsHelpers.get_asset_tools()
 for spec in specs:
  name=spec['name'];path=ROOT+'/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask()
   for k,v in {'filename':os.path.join(source,name+'.obj'),'destination_path':ROOT,'destination_name':name,'automated':True,'save':True}.items():task.set_editor_property(k,v)
   opts=unreal.FbxImportUI()
   for k,v in {'import_materials':False,'import_textures':False,'import_as_skeletal':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_STATIC_MESH}.items():opts.set_editor_property(k,v)
   opts.static_mesh_import_data.set_editor_property('combine_meshes',True);opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False);task.set_editor_property('options',opts);tools.import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Missing cabin mesh '+name)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   mat=A.load_asset(METAL+str(slot.get_editor_property('material_slot_name')))
   if not mat:raise RuntimeError('Missing material slot '+str(slot))
   mesh.set_material(i,mat)
  save(mesh);meshes[name]=mesh
 sounds={}
 for name in ('S_FreightMotor','S_FreightDoor','S_FreightArrival'):
  path=ROOT+'/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask()
   for k,v in {'filename':os.path.join(source,name+'.wav'),'destination_path':ROOT,'automated':True,'save':True}.items():task.set_editor_property(k,v)
   tools.import_asset_tasks([task])
  sound=A.load_asset(path);sound.set_editor_property('looping',name=='S_FreightMotor');save(sound);sounds[name]=sound
 report['meshes']=specs
 return meshes,sounds

def prompt_asset():
 path=ROOT+'/WBP_ElevatorPrompt'
 bp=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('WBP_ElevatorPrompt',ROOT,A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint'))
 compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp))
 for k,v in {'HUDTitle':'ГРУЗОВОЙ ЛИФТ','HUDMessage':'[F]  ПОДНЯТЬСЯ НА ЭТАЖ 01','HUDLifetime':86400.}.items():cdo.set_editor_property(k,v)
 save(bp);return bp

def build(meshes,sounds,prompt):
 bp=asset('BP_FreightElevator');compile_bp(bp)
 root=add(bp,unreal.SceneComponent,'ElevatorRoot');root.set_mobility(unreal.ComponentMobility.MOVABLE)
 cabin=add(bp,unreal.SceneComponent,'CabinRoot','ElevatorRoot');cabin.set_mobility(unreal.ComponentMobility.MOVABLE)
 cabin.set_editor_property('relative_location',V((0,0,0)))
 def mesh(name,model,p=(0,0,0),scale=(1,1,1),parent='CabinRoot',yaw=0):
  c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(model);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(scale));c.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw));return c
 def box(name,p,extent,parent='CabinRoot',profile='BlockAll'):
  c=add(bp,unreal.BoxComponent,name,parent);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('relative_location',V(p));c.set_box_extent(V(extent));c.set_collision_profile_name(profile);c.set_editor_property('generate_overlap_events',profile=='Trigger');return c
 mesh('CabinShell',meshes['SM_FreightCabin']);mesh('RoofMachinery',meshes['SM_FreightRoofDrive'])
 mesh('ControlPanel',meshes['SM_FreightControlPanel'],(80,212,0))
 box('CabinFloor',(0,0,12),(260,255,12))
 box('CabinCeiling',(0,0,449),(260,255,10))
 for sign in (-1,1):box('CabinSideWall'+str(sign),(0,sign*252,231),(225,9,207))
 box('ControlPanelCollision',(80,212,180),(55,25,83))
 boarding=box('BoardingZone',(0,0,142),(140,175,118),profile='Trigger')
 cube=A.load_asset('/Engine/BasicShapes/Cube')
 # Four pairs: moving cabin front/rear, fixed shaft gates at both landings.
 pairs=[('CabFront',-248,24,'CabinRoot',True),('CabRear',248,24,'CabinRoot',False),('LowerGate',-310,24,'ElevatorRoot',True),('UpperGate',350,2150,'ElevatorRoot',False)]
 for group,x,z,parent,opened in pairs:
  for sign,label in [(-1,'Left'),(1,'Right')]:
   mesh(group+label,A.load_asset(METAL+'SM_BlastDoor_'+label),(x,sign*(246 if opened else 80),z),(.65,.92,.95),parent)
   box(group+label+'Collision',(0,0,205),(20,87,201),group+label)
  if group.endswith('Gate'):
   mesh(group+'Frame',A.load_asset(METAL+'SM_BlastDoor_SplitFrame'),(x,0,z),(.45,.92,.96),'ElevatorRoot')
   for side in (-1,1):box(group+'Jamb'+str(side),(x,side*186,z+203),(28,24,203),'ElevatorRoot')
   lens=mesh(group+'Indicator',cube,(x-34 if x<0 else x+34,0,z+405),(.06,.88,.17),'ElevatorRoot');lens.set_material(0,A.load_asset(METAL+('M_DoorStatus_Green' if opened else 'M_DoorStatus_Red')));lens.set_editor_property('cast_shadow',False)
 box('LowerThreshold',(-286,0,12),(40,175,12),'ElevatorRoot')
 box('UpperThreshold',(308,0,2138),(65,175,12),'ElevatorRoot')
 mesh('OutsideCallPanel',meshes['SM_FreightControlPanel'],(-345,-215,35),(.45,.45,.65),'ElevatorRoot',-90)
 for x in (-210,210):
  for y in (-285,285):mesh('GuideCable_%d_%d'%(x,y),A.load_asset('/Engine/BasicShapes/Cylinder'),(x,y,1400),(.045,.045,27.5),'ElevatorRoot')
 light=add(bp,unreal.PointLightComponent,'CabinWarmLight','CabinRoot');light.set_editor_property('relative_location',V((0,0,402)));light.set_intensity(520);light.set_attenuation_radius(490);light.set_light_color(unreal.LinearColor(r=1,g=.74,b=.46,a=1));light.set_cast_shadows(False);light.set_editor_property('source_radius',48.)
 for name,sound,p in [('RideAudio',sounds['S_FreightMotor'],(0,0,380)),('DoorAudio',sounds['S_FreightDoor'],(-245,0,210))]:
  c=add(bp,unreal.AudioComponent,name,'CabinRoot');c.set_sound(sound);c.set_editor_property('auto_activate',False);c.set_editor_property('relative_location',V(p));c.set_editor_property('volume_multiplier',.6)
  settings=c.get_editor_property('attenuation_overrides');settings.set_editor_property('attenuation_shape_extents',V((120,0,0)));settings.set_editor_property('falloff_distance',950.);settings.set_editor_property('spatialize',True);c.set_editor_property('attenuation_overrides',settings);c.set_editor_property('override_attenuation',True)
 text=add(bp,unreal.TextRenderComponent,'ButtonCaption','CabinRoot');text.set_text(unreal.Text('F  /  01'));text.set_world_size(11.);text.set_text_render_color(unreal.Color(r=100,g=240,b=255,a=255));text.set_editor_property('relative_location',V((61,173,260)));text.set_editor_property('relative_rotation',unreal.Rotator(yaw=0,roll=90))
 for n,t,d in [('LiftState',B.get_basic_type_by_name('int'),'0'),('PromptWidget',B.get_object_reference_type(unreal.UserWidget),'None'),('Passenger',B.get_object_reference_type(unreal.Character),'None')]:member(bp,n,t,d)
 compile_bp(bp);g=LiftGraph(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 native=unreal.get_default_object(unreal.SystemLibrary)
 def timeline(name,duration):
  before={o.get_path_name() for o in unreal.ObjectIterator(unreal.TimelineTemplate) if o.get_outer()==B.generated_class(bp)}
  actions=[n for n in g.e.list_available_nodes([]) if n.startswith('|') and ('шкалу' in n or 'Timeline' in n)]
  node=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(),[]))
  template=next(o for o in unreal.ObjectIterator(unreal.TimelineTemplate) if o.get_outer()==B.generated_class(bp) and o.get_path_name() not in before)
  native.call_method('SetNamePropertyByName',(node,unreal.Name('TimelineName'),unreal.Name(name)));template.rename(name+'_Template');template.set_editor_property('timeline_length',duration);template.set_editor_property('length_mode',unreal.TimelineLengthMode.TL_TIMELINE_LENGTH)
  return node
 close=timeline('TL_CloseEntry',2.8);ride=timeline('TL_Ride',18.);exit=timeline('TL_OpenExit',2.8)
 compile_bp(bp);g=LiftGraph(bp)
 def alpha(name,duration):
  position=g.out(g.call('Engine.TimelineComponent.GetPlaybackPosition',target=g.get(name)))
  t=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=position,B=duration),Min=0,Max=1)
  return g.math('Multiply_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=t,B=t),B=g.math('Subtract_DoubleDouble',A=3,B=g.math('Multiply_DoubleDouble',A=2,B=t)))
 for node,name,groups,opening in [(close,'TL_CloseEntry',[('CabFront',-248,24),('LowerGate',-310,24)],False),(exit,'TL_OpenExit',[('CabRear',248,24),('UpperGate',350,2150)],True)]:
  a=alpha(name,2.8);g.cursor=pin(node,'Update',True)
  for group,x,z in groups:
   for sign,label in [(-1,'Left'),(1,'Right')]:
    pos=g.math('VLerp',A=g.math('MakeVector',X=x,Y=sign*(80 if opening else 246),Z=z),B=g.math('MakeVector',X=x,Y=sign*(246 if opening else 80),Z=z),Alpha=a)
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get(group+label),NewLocation=pos,bSweep=False,bTeleport=False))
 a=alpha('TL_Ride',18.);g.cursor=pin(ride,'Update',True)
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('CabinRoot'),NewLocation=g.math('MakeVector',X=0,Y=0,Z=g.math('Multiply_DoubleDouble',A=a,B=2126.)),bSweep=False,bTeleport=False))
 def pc():return g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 def player():return g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
 def movement():return g.external('CharacterMovement','/Script/Engine.Character',g.get('Passenger'))
 def clear_prompt():
  check=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('PromptWidget'))));otherwise=check.find_else_pin()
  g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('PromptWidget')))
  reset=g.set('PromptWidget','None');link(otherwise,reset.find_execute_pin())
 def shake():
  g.do(g.call('Engine.GameplayStatics.PlayWorldCameraShake',Shake=METAL+'BP_BlastDoorImpactShake.BP_BlastDoorImpactShake_C',Epicenter=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('CabinRoot'))),InnerRadius=100,OuterRadius=650,Falloff=1.5,bOrientShakeTowardsEpicenter=False))
 def one_shot(sound):g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=sound,Location=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('CabinRoot'))),AttenuationSettings=METAL+'SA_BlastDoor',VolumeMultiplier=.65))
 begin=g.e.add_component_bound_event_node(boarding,'OnComponentBeginOverlap');g.cursor=pin(begin,'then',True)
 g.branch(g.math('EqualEqual_ObjectObject',A=pin(begin,'OtherActor',True),B=player()));g.branch(g.math('EqualEqual_IntInt',A=g.get('LiftState'),B=0))
 valid=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('PromptWidget'))));g.cursor=valid.find_else_pin()
 create=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(prompt).get_path_name(),OwningPlayer=pc()));widget=g.out(create);g.set('PromptWidget',widget);g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=45))
 end=g.e.add_component_bound_event_node(boarding,'OnComponentEndOverlap');g.cursor=pin(end,'then',True)
 g.branch(g.math('EqualEqual_ObjectObject',A=pin(end,'OtherActor',True),B=player()))
 remains=g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('BoardingZone'),Other=player()));g.branch(g.math('Not_PreBool',A=remains));clear_prompt()
 choices=[n for n in g.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|F')]
 if len(choices)!=1:raise RuntimeError('Cannot find F key event')
 key=g.node(g.e.create_node_from_name(choices[0],unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True)
 g.branch(g.math('EqualEqual_IntInt',A=g.get('LiftState'),B=0));g.branch(g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('BoardingZone'),Other=player())))
 g.set('Passenger',player());g.set('LiftState',1);clear_prompt()
 g.do(g.call('Engine.Actor.DisableInput',target=g.get('Passenger'),PlayerController=pc()));g.do(g.call('Engine.CharacterMovementComponent.DisableMovement',target=movement()))
 g.do(g.call('Engine.Actor.K2_AttachToComponent',target=g.get('Passenger'),Parent=g.get('CabinRoot'),SocketName='None',LocationRule='KeepWorld',RotationRule='KeepWorld',ScaleRule='KeepWorld',bWeldSimulatedBodies=False))
 g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('LowerGateIndicator'),ElementIndex=0,Material=METAL+'M_DoorStatus_Red'))
 one_shot(METAL+'S_BlastDoorHydraulicRelease');g.do(g.call('Engine.AudioComponent.Play',target=g.get('DoorAudio'),StartTime=0));link(g.cursor,pin(close,'PlayFromStart'))
 g.cursor=pin(close,'Finished',True);g.do(g.call('Engine.AudioComponent.Stop',target=g.get('DoorAudio')));one_shot(METAL+'S_BlastDoorThud');shake();g.set('LiftState',2)
 g.do(g.call('Engine.AudioComponent.FadeIn',target=g.get('RideAudio'),FadeInDuration=.7,FadeVolumeLevel=.6,StartTime=0));link(g.cursor,pin(ride,'PlayFromStart'))
 g.cursor=pin(ride,'Finished',True);g.set('LiftState',3);g.do(g.call('Engine.AudioComponent.FadeOut',target=g.get('RideAudio'),FadeOutDuration=.65,FadeVolumeLevel=0));shake();one_shot(sounds['S_FreightArrival'].get_path_name())
 g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('UpperGateIndicator'),ElementIndex=0,Material=METAL+'M_DoorStatus_Green'))
 g.do(g.call('Engine.AudioComponent.Play',target=g.get('DoorAudio'),StartTime=0));link(g.cursor,pin(exit,'PlayFromStart'))
 g.cursor=pin(exit,'Finished',True);g.do(g.call('Engine.AudioComponent.Stop',target=g.get('DoorAudio')))
 g.do(g.call('Engine.Actor.K2_DetachFromActor',target=g.get('Passenger'),LocationRule='KeepWorld',RotationRule='KeepWorld',ScaleRule='KeepWorld'))
 g.do(g.call('Engine.CharacterMovementComponent.SetMovementMode',target=movement(),NewMovementMode='MOVE_Walking',NewCustomMode=0));g.do(g.call('Engine.Actor.EnableInput',target=g.get('Passenger'),PlayerController=pc()));g.set('LiftState',4)
 compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',50);save(bp)
 report['blueprint']=bp.get_path_name();report['asset_saved']=True;return bp

try:
 package('/Game/Lvl_LabTutorial',os.path.join(backup,'Lvl_LabTutorial.umap'))
 meshes,sounds=import_content();prompt=prompt_asset();bp=build(meshes,sounds,prompt)
 report['removed']=[]
 for a in list(sub.get_all_level_actors()):
  n=a.get_actor_label()
  if n.startswith(('LAB_Elevator_','LAB_LiftCallPanel_','LAB_Shaft_LadderRung_')) or n in ('LAB_FreightElevator','LAB_LiftThreshold_Amber','LAB_Tutorial_Sign_Lift'):
   report['removed'].append(n);sub.destroy_actor(a)
  elif n=='LAB_Shaft_Wall_East_Upper':
   a.modify();p=a.get_actor_location();p.z=2700;a.set_actor_location(p,False,True);s=a.get_actor_scale3d();s.z=2.;a.set_actor_scale3d(s)
 lift=sub.spawn_actor_from_class(B.generated_class(bp),V((2650,0,0)),unreal.Rotator());lift.set_actor_label('LAB_FreightElevator');lift.set_folder_path('LAB/03_Interactables');lift.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);lift.set_editor_property('input_priority',50)
 staged=os.path.join(saved,'FreightElevatorStaged','Lvl_LabTutorial.umap');package('/Game/Lvl_LabTutorial',staged);report['staged_map']=staged
 eye=V((2130,-50,226));target=V((2630,0,225));editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,target));unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
 unreal.log('FREIGHT ELEVATOR ASSETS AND LIVE MAP READY')
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error']);raise
finally:
 with open(os.path.join(saved,'freight_elevator_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
