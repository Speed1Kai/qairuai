"""Make the existing upper-floor exit a walkable streamed courtyard doorway.
No OpenLevel, pawn relocation, fade or respawn is used by the new exit.
"""
import unreal,os,sys,math,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,components,add,pin,val,link,compile_bp,save
src=os.path.join(unreal.Paths.project_content_dir(),'Python/Upgrade_PlayerVisor.py')
exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
MAIN='/Game/Lvl_LabTutorial';SURF='/Game/Surface/Lvl_SurfaceArrival';CONNECTED='/Game/Surface/Lvl_CampusConnected';root=os.path.abspath(unreal.Paths.project_dir())
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
r={'saved':False,'gameplay_tested':False}
def back(path):
 ext='.umap' if path in (MAIN,SURF,CONNECTED) else '.uasset';rel=path.removeprefix('/Game/')+ext;source=os.path.join(root,'Content',rel)
 if os.path.isfile(source):
  dest=os.path.join(r['backup'],rel);os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(source,dest)
def scalar(bp,name,default='0'):member(bp,name,'real',default)
def boolvar(bp,name):member(bp,name,'bool','false')
def uobject(bp,name,cls):member(bp,name,B.get_object_reference_type(cls),'None')
def pawn(g):return g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
def pc(g):return g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
def mesh(bp,name,pos,size,mat,parent='Root',asset=None,rotation=None):
 c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(asset or A.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,mat);c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_scale3d',V(size));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('BlockAll');c.set_editor_property('cast_shadow',True)
 if rotation:c.set_editor_property('relative_rotation',rotation)
 return c
try:
 r['backup']=os.path.join(root,'Saved/Backups/SeamlessCourtyard',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(r['backup'],exist_ok=True)
 for path in (MAIN,SURF,CONNECTED,'/Game/Surface/BP_SurfaceDeparture','/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor','/Game/Surface/BP_ConnectedLaboratoryCampus'):back(path)
 campus_source='/Game/Surface/BP_LaboratoryCampus';campus_copy='/Game/Surface/BP_ConnectedLaboratoryCampus'
 if not A.does_asset_exist(campus_copy):assert A.duplicate_asset(campus_source,campus_copy)
 campus=A.load_asset(campus_copy)
 # Remove only the old A-01 shell/interior; the new shell wraps the actual
 # laboratory footprint. Other campus buildings and the city are unchanged.
 removed=0
 for h,c,name in components(campus):
  if not isinstance(c,unreal.InstancedStaticMeshComponent):continue
  for idx in range(c.get_instance_count()-1,-1,-1):
   t=c.get_instance_transform(idx,False);p=t.translation
   if abs(p.x+7500)<1900 and abs(p.y+1000)<2100 and p.z>-30:
    c.remove_instance(idx);removed+=1
 for h,c,name in components(campus):
  if isinstance(c,unreal.SceneComponent):c.set_mobility(unreal.ComponentMobility.STATIC)
 compile_bp(campus);save(campus)
 # Duplicate the exterior map natively, preserving the original standalone map.
 if not A.does_asset_exist(CONNECTED):
  world=unreal.EditorLoadingAndSavingUtils.load_map(SURF)
  if not unreal.EditorLoadingAndSavingUtils.save_map(world,CONNECTED):raise RuntimeError('Could not save exterior world copy')
  del world
 else:unreal.EditorLoadingAndSavingUtils.load_map(CONNECTED)
 oldcampus=None
 for a in list(sub.get_all_level_actors()):
  label=a.get_actor_label();cls=a.get_class().get_name()
  if cls=='BP_LaboratoryCampus_C':oldcampus=a
  if isinstance(a,unreal.PlayerStart) or label in ('ArrivalSequence','CAMPUS_StasisExitDoor','SURF_PlayerGuardVisual','SURF_CyborgBodyLight') or label.startswith('CAMPUS_ExitFill_') or isinstance(a,unreal.ExponentialHeightFog) or isinstance(a,unreal.PostProcessVolume):sub.destroy_actor(a)
 if oldcampus:
  transform=oldcampus.get_actor_transform();sub.destroy_actor(oldcampus);new=sub.spawn_actor_from_class(B.generated_class(campus),transform.translation,transform.rotation.rotator());new.set_actor_label('CAMPUS_LaboratoryGrounds');new.set_actor_scale3d(transform.scale3d)
  for c in new.get_components_by_class(unreal.InstancedStaticMeshComponent):
   if 'InvisibleCollisions' in c.get_name():c.set_visibility(False);c.set_hidden_in_game(True)
 # Keep only one environment controller, avoiding duplicated player lights/HUD.
 assert unreal.EditorLoadingAndSavingUtils.save_current_level()
 # Match the original A-01 front doorway to the real upper-floor north wall.
 config=json.load(open(os.path.join(root,'Saved/lab_campus_report.json'),encoding='utf8'));source_door=config['exit']['door'];yaw=90.-config['exit']['heading'];ang=math.radians(yaw);rx=source_door[0]*math.cos(ang)-source_door[1]*math.sin(ang);ry=source_door[0]*math.sin(ang)+source_door[1]*math.cos(ang);offset=(5850-rx,1500-ry,2150.)
 unreal.EditorLoadingAndSavingUtils.load_map(MAIN)
 floor=A.load_asset('/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor')
 def clear_exit(cs):
  count=0
  for c in cs:
   if not isinstance(c,unreal.InstancedStaticMeshComponent):continue
   c.modify()
   for idx in range(c.get_instance_count()-1,-1,-1):
    p=c.get_instance_transform(idx,False).translation
    if 5540<p.x<6160 and 2149<p.z<2600 and ((1267<p.y<1320) or abs(p.y-1500)<13):c.remove_instance(idx);count+=1
  return count
 r['removed_floor_instances']=clear_exit([c for h,c,n in components(floor)]);compile_bp(floor);save(floor)
 for a in sub.get_all_level_actors():
  if a.get_class().get_name()=='BP_ModernFirstFloor_C':a.modify();clear_exit(a.get_components_by_class(unreal.InstancedStaticMeshComponent))
  if isinstance(a,unreal.TextRenderActor):
   p=a.get_actor_location()
   if abs(p.x-5850)<2 and abs(p.y-1260)<2:a.text_render.set_text(unreal.Text('A-01 / ВЫХОД ВО ДВОР'))
 bp=A.load_asset('/Game/Surface/BP_SurfaceDeparture')
 for n in ('bOpenRequested','bExitOpen','bNear'):boolvar(bp,n)
 scalar(bp,'ExitDoorAmount');uobject(bp,'CampusStreaming',unreal.LevelStreamingDynamic);uobject(bp,'Prompt',unreal.UserWidget)
 add(bp,unreal.SceneComponent,'ExitDoorRoot','Root').set_editor_property('relative_location',V((-140,420,-110)))
 steel=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabSteel');dark=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabGraphite');ceramic=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabCeramic');cyan=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabCyan');amber=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabAmber')
 # First-floor entry shell, placed around existing interiors rather than through them.
 for name,pos,size,mat in [
 ('FacadeWest',(-1742.5,420,290),(27.75,.35,8),ceramic),('FacadeEast',(292.5,420,290),(4.35,.35,8),ceramic),
 ('ExteriorWestWall',(-3110,-1730,320),(.35,8.6,8),ceramic),('ExteriorWestNorth',(-3110,-160,320),(.35,14,8),ceramic),('ExteriorWestLintel',(-3110,-1080,525),(.35,4.4,3.9),ceramic),('ExteriorEastWall',(510,-810,320),(.35,27,8),ceramic),
 ('ExteriorBackWall',(-1300,-2130,320),(36.5,.35,8),ceramic),('ExteriorRoof',(-1300,-810,740),(36.5,27,.4),dark),
 ('DoorLintel',(-140,420,330),(4.8,.8,.7),dark),('Threshold',(-140,700,-119),(6.8,9,.18),steel)]:mesh(bp,name,pos,size,mat)
 for sign,label in ((-1,'Left'),(1,'Right')):
  leaf=add(bp,unreal.SceneComponent,'Exit'+label+'Leaf','ExitDoorRoot');leaf.set_editor_property('relative_location',V((sign*102,0,0)));leaf.set_mobility(unreal.ComponentMobility.MOVABLE)
  mesh(bp,'Exit'+label+'Armor',(0,0,207),(2.02,.26,4.14),dark,'Exit'+label+'Leaf')
  mesh(bp,'Exit'+label+'Inset',(0,-15,228),(1.64,.04,2.8),steel,'Exit'+label+'Leaf')
  for j in range(5):mesh(bp,'Exit'+label+'Hazard%d'%j,(-80+j*40,-18,48),(.28,.045,.38),amber,'Exit'+label+'Leaf',rotation=unreal.Rotator(pitch=0,roll=0,yaw=-22))
  mesh(bp,'Exit'+label+'Frame',(sign*230,0,220),(.38,.80,4.4),ceramic,'ExitDoorRoot')
 compile_bp(bp)
 # Fully replace the old fade/OpenLevel path.
 g=Flow(bp,'Exit_UpdateStreaming');p=pawn(g);g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=p)));v=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=p)))
 upper=g.branch(g.math('Greater_DoubleDouble',A=pin(v,'Z',True),B=1800.));lower=upper.find_else_pin();g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('CampusStreaming')))))
 load=g.do(g.call('Engine.LevelStreamingDynamic.LoadLevelInstance',LevelName=CONNECTED,Location='(X=%f,Y=%f,Z=%f)'%offset,Rotation='(Pitch=0,Yaw=%f,Roll=0)'%yaw,OptionalLevelNameOverride='ConnectedCampus',bLoadAsTempPackage=False));g.set('CampusStreaming',g.out(load))
 g.cursor=lower;g.branch(g.math('Less_DoubleDouble',A=pin(v,'Z',True),B=1400.));g.branch(g.math('Not_PreBool',A=g.get('bExitOpen')));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('CampusStreaming'))));g.do(g.call('Engine.LevelStreaming.SetIsRequestingUnloadAndRemoval',target=g.get('CampusStreaming'),bInIsRequestingUnloadAndRemoval=True));g.set('CampusStreaming','None')
 compile_bp(bp)
 g=Flow(bp,'Exit_UpdateDoor');dt=g.arg('DeltaSeconds',B.get_basic_type_by_name('real'));target=g.math('SelectFloat',A=1.,B=0.,bPickA=g.get('bExitOpen'));g.set('ExitDoorAmount',g.math('FInterpTo_Constant',Current=g.get('ExitDoorAmount'),Target=target,DeltaTime=dt,InterpSpeed=1./1.8));alpha=g.smooth(g.get('ExitDoorAmount'))
 for sign,label in ((-1,'Left'),(1,'Right')):
  x=g.math('Multiply_DoubleDouble',A=sign,B=g.math('Add_DoubleDouble',A=102.,B=g.math('Multiply_DoubleDouble',A=alpha,B=215.)));g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('Exit'+label+'Leaf'),NewLocation=g.math('MakeVector',X=x,Y=0.,Z=0.),bSweep=False,bTeleport=False))
 g.branch(g.get('bOpenRequested'));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('CampusStreaming'))));g.branch(g.out(g.call('Engine.LevelStreaming.IsLevelVisible',target=g.get('CampusStreaming'))));g.set('bExitOpen',True)
 compile_bp(bp)
 g=Flow(bp,'Exit_UpdatePrompt');p=pawn(g);g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=p)));dist=g.out(g.call('Engine.Actor.GetDistanceTo',OtherActor=p));near=g.math('Less_DoubleDouble',A=dist,B=230.);g.branch(g.math('NotEqual_BoolBool',A=near,B=g.get('bNear')));g.set('bNear',near);br=g.branch(near);lost=br.find_else_pin();hint=A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint');created=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(hint).get_path_name(),OwningPlayer=pc(g)));g.set('Prompt',g.out(created))
 for name,value in [('HUDTitle','ВЫХОД ВО ДВОР'),('HUDMessage','[F]  ОТКРЫТЬ / ЗАКРЫТЬ ДВЕРИ')]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('Prompt'),PropertyName=name,Value=value))
 g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('Prompt'),PropertyName='HUDLifetime',Value=86400.));g.do(g.call('UMG.UserWidget.AddToViewport',target=g.get('Prompt'),ZOrder=65));g.cursor=lost;g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Prompt'))));g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('Prompt')))
 compile_bp(bp)
 g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);g.event('ReceiveBeginPlay');g.set('bExitOpen',False);g.set('bOpenRequested',False);g.set('bNear',False);g.set('ExitDoorAmount',0.);g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.2));g.do(g.call('Engine.Actor.EnableInput',PlayerController=pc(g)));g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.05))
 tick=g.event('ReceiveTick');g.do(g.selfcall('Exit_UpdateStreaming'));call=g.selfcall('Exit_UpdateDoor');val(pin(call,'DeltaSeconds'),pin(tick,'DeltaSeconds',True));g.do(call);g.do(g.selfcall('Exit_UpdatePrompt'))
 key=g.node(g.e.create_node_from_name(next(n for n in g.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|F')),unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True);g.branch(g.get('bNear'));g.set('bOpenRequested',g.math('Not_PreBool',A=g.get('bOpenRequested')));g.branch(g.math('Not_PreBool',A=g.get('bOpenRequested')));g.set('bExitOpen',False)
 compile_bp(bp);save(bp)
 for a in sub.get_all_level_actors():
  if a.get_class().get_name()=='BP_SurfaceDeparture_C':a.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);a.set_editor_property('input_priority',95)
 world=ed.get_editor_world();world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,MAIN)
 r.update(saved=True,connected_map=CONNECTED,offset=list(offset),yaw=yaw,door_world=[5850,1500,2150],door_open_seconds=1.8,no_open_level=True,no_player_teleport=True,campus_removed_instances=removed)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:open(os.path.join(root,'Saved/seamless_courtyard_report.json'),'w',encoding='utf8').write(json.dumps(r,ensure_ascii=False,indent=2))
if not r['saved']:raise RuntimeError('Courtyard connection incomplete')
