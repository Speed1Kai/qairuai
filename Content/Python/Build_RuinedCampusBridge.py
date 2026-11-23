"""Native bridge placement and real terrain opening; preserve laboratory startup."""
import unreal,os,sys,json,math,datetime,shutil,traceback,time
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,add,components,compile_bp,save,Graph,pin,val,link
ROOT='/Game/Surface/Bridge';LEVEL='/Game/Surface/Lvl_SurfaceArrival';MAIN='/Game/Lvl_LabTutorial'
project=os.path.abspath(unreal.Paths.project_dir());content=os.path.abspath(unreal.Paths.project_content_dir());source=os.path.join(project,'SourceAssets','CampusBridge')
tools=unreal.AssetToolsHelpers.get_asset_tools();sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report={'saved':False,'gameplay_tested':False,'terrain_edits':0,'bridge_centre':[0,22500,0],'gap_cm':[940,1200]}
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
def spawn(cls,label,p,rot=None):
 a=sub.spawn_actor_from_class(cls,V(p),rot or unreal.Rotator());a.set_actor_label(label);a.set_folder_path('SURFACE/Collapsed Bridge');return a
def static(label,mesh,p,rot=None,collision=True):
 a=spawn(unreal.StaticMeshActor,label,p,rot);c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision');return a
def box(label,p,size,material,collision=True):
 a=static(label,A.load_asset('/Engine/BasicShapes/Cube'),p,collision=collision);a.set_actor_scale3d(V(tuple(v/100 for v in size)));a.static_mesh_component.set_material(0,material);return a
def cut(cs,offset):
 seen=set()
 for c in cs:
  if not c or not isinstance(c,unreal.InstancedStaticMeshComponent) or not c.static_mesh or c.static_mesh.get_name()!='Cube' or c.get_path_name() in seen:continue
  seen.add(c.get_path_name());remove=[];pieces=[]
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,False);p=t.translation;s=t.scale3d;wy=p.y+offset[1];wx=p.x+offset[0]
   if abs(t.rotation.rotator().yaw)>1 or p.z+offset[2]>100:continue
   low=wy-abs(s.y)*50;high=wy+abs(s.y)*50
   if high<=21100.01 or low>=23999.99:continue
   if abs(s.x)*100>=1200 and high-low>500:
    remove.append(i)
    for lo,hi in [(low,min(high,21100)),(max(low,24000),high)]:
     if hi-lo>1:pieces.append(unreal.Transform(location=V((p.x,(lo+hi)/2-offset[1],p.z)),rotation=t.rotation.rotator(),scale=V((s.x,(hi-lo)/100,s.z))))
   elif abs(wx)<1450 and 21100<wy<24000:remove.append(i)
  for i in reversed(remove):c.remove_instance(i)
  for t in pieces:c.add_instance(t,False)
  report['terrain_edits']+=len(remove)
try:
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 backup=os.path.join(project,'Saved','Backups','CampusBridge',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);report['backup']=backup
 for rel in ['Surface/Lvl_SurfaceArrival.umap','Surface/BP_LaboratoryCampus.uasset','Surface/BP_SurfaceEnvironment.uasset']:
  shutil.copy2(os.path.join(content,rel),os.path.join(backup,os.path.basename(rel)))
 A.make_directory(ROOT);meshes={}
 for spec in json.load(open(os.path.join(source,'bridge_meshes.json'))):
  name=spec['name'];path=ROOT+'/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask();opt=unreal.FbxImportUI()
   for k,v in dict(import_mesh=True,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opt.set_editor_property(k,v)
   opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
   for k,v in dict(filename=os.path.join(source,name+'.obj'),destination_path=ROOT,destination_name=name,options=opt,automated=True,save=True).items():task.set_editor_property(k,v)
   tools.import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Bridge import failed '+name)
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,A.load_asset('/Game/Surface/Materials/'+str(slot.material_slot_name)))
  # Per-triangle static collision preserves jagged edges and the open span.
  # A convex collision hull here would incorrectly fill empty space below railings.
  sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem);sms.remove_collisions(mesh)
  mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);save(mesh);meshes[name]=mesh
 unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 for path,label,offset in [('/Game/Surface/BP_LaboratoryCampus','CAMPUS_LaboratoryGrounds',(0,0,0)),('/Game/Surface/BP_SurfaceEnvironment','SURF_Environment',(0,26000,0))]:
  bp=A.load_asset(path);cut([c for h,c,n in components(bp)],offset);compile_bp(bp);save(bp)
  actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()==label);cut(actor.get_components_by_class(unreal.InstancedStaticMeshComponent),offset)
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith('BRIDGE_'):sub.destroy_actor(a)
 for name in ('SM_BridgeCampusHalf','SM_BridgeCityHalf'):static('BRIDGE_'+name,meshes[name],(0,22500,0))
 static('BRIDGE_FallenSpan',meshes['SM_BridgeFallenSpan'],(80,22500,-1550),unreal.Rotator(pitch=19,yaw=12,roll=28))
 concrete=A.load_asset('/Game/Surface/Materials/M_RuinConcrete');dust=A.load_asset('/Game/Surface/Materials/M_Dust');steel=A.load_asset('/Game/Surface/Materials/M_RuinSteel')
 box('BRIDGE_ChannelBed',(0,22550,-2275),(78000,2900,150),dust)
 for y in (21125,23975):box('BRIDGE_ChannelRetainingWall_'+str(y),(0,y,-1110),(78000,50,2200),concrete)
 rubble=A.load_asset('/Game/Surface/Meshes/SM_RubbleCluster')
 for i,(x,y,z,s) in enumerate([(-900,22250,-2185,2.6),(900,22650,-2180,3),(0,23000,-2140,2),(-1100,21850,3,.5),(1080,23200,3,.6)]):
  a=static('BRIDGE_Rubble_%02d'%i,rubble,(x,y,z),unreal.Rotator(yaw=i*39),False);a.set_actor_scale3d(V((s,s,s)))
 # Physical warning structures leave the centre approachable for inspection.
 for x in (-820,820):
  for yy in (20800,24200):
   box('BRIDGE_WarningPost_%s_%s'%(x,yy),(x,yy,95),(12,12,190),steel)
   box('BRIDGE_WarningPlate_%s_%s'%(x,yy),(x,yy-8,135),(160,6,95),concrete,False)
   if A.does_asset_exist(ROOT+'/SM_WarningSignFace'):
    for side in (-1,1):static('BRIDGE_PrintedSign_%s_%s_%s'%(x,yy,side),A.load_asset(ROOT+'/SM_WarningSignFace'),(x,yy-8+side*4,135),unreal.Rotator(yaw=0 if side==-1 else 180),False)
 # A fall returns the player to the last side of the crossing rather than trapping
 # them in the channel. Only this recovery sensor ticks, at 5 Hz.
 path=ROOT+'/BP_BridgeRecovery'
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);bp=tools.create_asset('BP_BridgeRecovery',ROOT,unreal.Blueprint,f)
 compile_bp(bp);g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 for name,default in [('LastSafeY','21400.0')]:
  if name not in list(map(str,B.list_member_variable_names(bp))):g.e.add_member_variable(name,B.get_basic_type_by_name('double'),default)
 event=g.e.find_event_node('ReceiveTick')
 if not event:
  name=next(n for n in g.e.list_available_nodes([]) if n.startswith('Добавитьсобытие|') and n.split('|')[-1].replace(' ','') in ('Tick','СобытиеTick'))
  event=g.e.create_node_from_name(name,unreal.Vector2D(),[])
 g.cursor=pin(event,'then',True)
 player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=player)))
 pos=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=player));v=g.call('Engine.KismetMathLibrary.BreakVector',InVec=pos);y=g.out(v,'Y');z=g.out(v,'Z')
 nearby=g.math('BooleanAND',A=g.math('Greater_DoubleDouble',A=y,B=20000.),B=g.math('Less_DoubleDouble',A=y,B=25000.));g.branch(nearby)
 below=g.branch(g.math('Less_DoubleDouble',A=z,B=-450.));safe=below.find_else_pin()
 destination=g.math('MakeVector',X=0.,Y=g.get('LastSafeY'),Z=125.)
 g.do(g.call('Engine.Actor.K2_SetActorLocation',target=player,NewLocation=destination,bSweep=False,bTeleport=True))
 g.cursor=safe;g.branch(g.math('Greater_DoubleDouble',A=z,B=50.))
 side=g.branch(g.math('Less_DoubleDouble',A=y,B=22000.));far=side.find_else_pin();g.set('LastSafeY',21400.)
 g.cursor=far;g.branch(g.math('Greater_DoubleDouble',A=y,B=23100.));g.set('LastSafeY',23600.)
 compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('tick_interval',.2);cdo.set_editor_property('primary_actor_tick',tick);save(bp)
 spawn(B.generated_class(bp),'BRIDGE_FallRecovery',(0,22500,0))
 report['saved']=bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
 if not report['saved']:raise RuntimeError('Bridge level save failed')
 eye=V((1700,20500,750));editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,V((0,22800,-200))))
 unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
 # Keep the level loaded until screenshot I/O has completed. Background editor
 # throttling can postpone capture by several frames, beyond a fixed timeout.
 capture_path=os.path.join(project,'Saved','CampusBrokenBridge_Overview.png')
 bridge_capture={'since':time.monotonic(),'captured':False,'old_mtime':os.path.getmtime(capture_path) if os.path.exists(capture_path) else 0}
 def bridge_capture_tick(dt):
  if time.monotonic()-bridge_capture['since']>5 and not bridge_capture['captured']:
   bridge_capture['captured']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,capture_path,delay=0.)
  if bridge_capture['captured'] and os.path.exists(capture_path) and os.path.getmtime(capture_path)>bridge_capture['old_mtime']:
   unreal.unregister_slate_post_tick_callback(bridge_capture['handle']);unreal.EditorLoadingAndSavingUtils.load_map(MAIN)
 bridge_capture['handle']=unreal.register_slate_post_tick_callback(bridge_capture_tick)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','campus_bridge_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
