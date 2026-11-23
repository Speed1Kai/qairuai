"""Render the authored enemy and observe its saved AI in disposable PIE.
The preview moves only PIE actors and never saves gameplay state.
"""
import unreal,time,os,json,traceback
ROOT='/Game/Enemies/Architect';folder='S:/Final_Protocol/Saved/EnemyPreview';os.makedirs(folder,exist_ok=True)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);edit=unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
tree=unreal.load_asset(ROOT+'/BT_EnemyRobot')
# Keep runtime nodes while the editor reconstructs its visual representation.
# The stock import path leaves ClassData empty on reconstructed graph nodes.
runtime={'Composite':[],'Task':[],'Decorator':[],'Service':[]}
snapshots=[]
root_runtime=tree.get_editor_property('root_node')
def collect(n):
 if isinstance(n,unreal.BTCompositeNode):
  snapshots.append((n,[c.copy() for c in n.get_editor_property('children')],list(n.get_editor_property('services'))))
  runtime['Composite'].append(n);runtime['Service'].extend(n.get_editor_property('services'))
  for child in n.get_editor_property('children'):
   collect(child.child_composite or child.child_task);runtime['Decorator'].extend(child.decorators)
 else:runtime['Task'].append(n)
collect(tree.get_editor_property('root_node'))
edit.open_editor_for_assets([tree])
graphnodes={k:[] for k in runtime}
for n in unreal.ObjectIterator(unreal.Object):
 if isinstance(n,type):continue
 if n.get_outer() and n.get_outer().get_class().get_name()=='BehaviorTreeGraph' and n.get_outer().get_outer()==tree:
  name=n.get_class().get_name()
  if name=='BehaviorTreeGraphNode_Root':unreal.get_default_object(unreal.SystemLibrary).call_method('SetObjectPropertyByName',(n,unreal.Name('BlackboardAsset'),unreal.load_asset(ROOT+'/BB_EnemyRobot')))
  for kind in graphnodes:
   if name=='BehaviorTreeGraphNode_'+kind:graphnodes[kind].append(n)
for kind,nodes in graphnodes.items():
 nodes.sort(key=lambda n:int(n.get_name().rsplit('_',1)[-1]))
 for n,instance in zip(nodes,runtime[kind]):unreal.get_default_object(unreal.SystemLibrary).call_method('SetObjectPropertyByName',(n,unreal.Name('NodeInstance'),instance))
edit.close_all_editors_for_asset(tree);unreal.EditorAssetLibrary.save_loaded_asset(tree,only_if_is_dirty=False)
for n,children,services in snapshots:n.set_editor_property('children',children);n.set_editor_property('services',services)
tree.set_editor_property('root_node',root_runtime);unreal.EditorAssetLibrary.save_loaded_asset(tree,only_if_is_dirty=False)
with open(folder+'/TreeGraph.json','w') as f:json.dump({'runtime':{k:len(v) for k,v in runtime.items()},'graph':{k:len(v) for k,v in graphnodes.items()},'root_children':len(root_runtime.get_editor_property('children'))},f,indent=2)
editorworld=unreal.EditorLevelLibrary.get_editor_world()
navsettings=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.LevelEditorMiscSettings'))
try:navsettings.set_editor_property('bNavigationAutoUpdate',True)
except Exception as error:unreal.log_warning(str(error))
unreal.SystemLibrary.execute_console_command(editorworld,'RebuildNavigation')
unreal.SystemLibrary.execute_console_command(editorworld,'t.MaxFPS 30')
started=time.monotonic();stage=0;play=False;busy=False;finishing=False;last=0;samples=[];cam=None
def write():
 with open(folder+'/Observations.json','w',encoding='utf8') as f:json.dump(samples,f,ensure_ascii=False,indent=2)
def update(dt):
 global stage,play,busy,finishing,last,cam
 if busy:return
 busy=True
 try:
  now=time.monotonic()
  if finishing:
   if sub.is_in_play_in_editor():sub.editor_request_end_play();last=now
   elif now-last>3:unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
   return
  if now-started>170:raise RuntimeError('Preview timeout')
  if not play:
   if now-started<18:return
   unreal.SystemLibrary.execute_console_command(editorworld,'RebuildNavigation')
   unreal.EditorLoadingAndSavingUtils.save_current_level();play=True;sub.editor_request_begin_play();return
  w=unreal.EditorLevelLibrary.get_game_world()
  if not w:return
  t=unreal.GameplayStatics.get_time_seconds(w)
  robots=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.load_class(None,ROOT+'/BP_EnemyRobot.BP_EnemyRobot_C'))
  if not robots:return
  robot=robots[0];ai=robot.get_controller();pawn=unreal.GameplayStatics.get_player_pawn(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
  if not ai or not pawn or not pc:return
  bb=unreal.AIHelperLibrary.get_blackboard(ai);mesh=robot.get_component_by_class(unreal.SkeletalMeshComponent)
  def observe(name):
   p=robot.get_actor_location();v=robot.get_velocity()
   row={'stage':name,'time':t,'location':(p.x,p.y,p.z),'speed':(v.x*v.x+v.y*v.y)**.5,'max_speed':robot.character_movement.max_walk_speed,'state':bb.get_value_as_enum('MovementState') if bb else None,'target':str(bb.get_value_as_object('TargetActor')) if bb else None,'last_known':str(bb.get_value_as_vector('LastKnownLocation')) if bb else None,'health':robot.get_editor_property('Health'),'dead':robot.get_editor_property('bIsDead'),'ragdoll':mesh.is_simulating_physics(),'pelvis_simulating':mesh.is_simulating_physics('pelvis'),'pelvis':str(mesh.get_socket_location('pelvis')),'death_stage':robot.get_editor_property('DeathStage'),'movement_mode':str(robot.character_movement.movement_mode)}
   if name=='patrol':row['glow_nodes']={c.get_name():{'p':str(c.get_world_location()),'bone':str(c.get_attach_socket_name())} for c in robot.get_components_by_class(unreal.StaticMeshComponent)};row['head']=str(mesh.get_socket_transform('head',unreal.RelativeTransformSpace.RTS_COMPONENT));row['chest']=str(mesh.get_socket_transform('spine_03',unreal.RelativeTransformSpace.RTS_COMPONENT))
   samples.append(row);write()
  def capture(name):
   unreal.SystemLibrary.execute_console_command(w,'HighResShot 1280x720 filename="'+folder+'/'+name+'"')
  if stage==0 and t>.8:observe('patrol_start');stage=1
  elif stage==1 and t>12:
   transform=unreal.Transform(location=unreal.Vector(3510,-370,2360))
   helper=unreal.get_default_object(unreal.GameplayStatics)
   cam=helper.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.CameraActor.static_class(),transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   cam=helper.call_method('FinishSpawningActor',(cam,transform,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   p=robot.get_actor_location();cam.set_actor_location(unreal.Vector(p.x-340,p.y-210,p.z+25),False,True);cam.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(cam.get_actor_location(),unreal.Vector(p.x,p.y,p.z+5)),False);cam.camera_component.set_field_of_view(60.)
   pc.set_view_target_with_blend(cam,0.);unreal.GameplayStatics.get_player_camera_manager(w,0).set_manual_camera_fade(0.,unreal.LinearColor(0,0,0,1),False);observe('patrol');stage=2
  elif stage==2 and t>13:stage=3;capture('Robot_Patrol.png')
  elif stage==3 and t>14:
   robot.set_actor_location(unreal.Vector(3900,-160,2255),False,True);ai.stop_movement();robot.set_actor_rotation(unreal.Rotator(yaw=180),False)
   pawn.set_actor_location(unreal.Vector(3330,-160,2245),False,True);stage=4
  elif stage==4 and t>14.5:observe('alert');stage=5;capture('Robot_Alert.png')
  elif stage==5 and t>15.3:observe('chase');pawn.set_actor_location(unreal.Vector(3060,-160,2245),False,True);stage=6
  elif stage==6 and t>18:
   observe('chase_repath');pawn.set_actor_location(unreal.Vector(-416,306,100),False,True);stage=7
  elif stage==7 and t>19:observe('lost_sight_search');stage=8
  elif stage==8 and t>25:
   observe('after_search');unreal.GameplayStatics.apply_damage(robot,35.,pc,pawn,None);stage=9
  elif stage==9 and t>25.2:observe('hit_reaction');stage=10
  elif stage==10 and t>27:unreal.GameplayStatics.apply_damage(robot,400.,pc,pawn,None);stage=11
  elif stage==11 and t>29:
   observe('destroyed');p=mesh.get_socket_location('pelvis');cam.set_actor_location(unreal.Vector(p.x-270,p.y-220,p.z+150),False,True);cam.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(cam.get_actor_location(),p),False);stage=12;capture('Robot_Destroyed.png')
  elif stage==12 and t>30:finishing=True;last=now
 except Exception:
  samples.append({'error':traceback.format_exc()});write();unreal.log_error(traceback.format_exc());finishing=True;last=time.monotonic()
 finally:busy=False
handle=unreal.register_slate_post_tick_callback(update)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
