"""Clean the live tutorial corridor; preserve the annex as a separate level."""
import unreal,os,json,datetime,time,traceback
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world();A=unreal.EditorAssetLibrary
if world.get_name()!='Lvl_LabTutorial':raise RuntimeError('Open Lvl_LabTutorial before corridor cleanup')
saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
folder=os.path.join(saved,'Backups','CorridorCleanup',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(folder,exist_ok=True)
report={'saved':False,'backup':folder,'removed':[],'archived':[],'instances_archived':0}
def v(x,y,z):return unreal.Vector(float(x),float(y),float(z))
def annex(p):return 1050<=p.x<=1750 and 240<=p.y<=910 and -100<=p.z<650
def save_package(name,file):
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="'+name+'" FILE="'+file.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(file):raise RuntimeError('Package not written: '+file)
def actors():return list(sub.get_all_level_actors())

try:
 # Includes the user's unsaved edits in the open editor, not just the disk map.
 save_package('/Game/Lvl_LabTutorial',os.path.join(folder,'Lvl_LabTutorial.umap'))
 archive_actors=[a for a in actors() if annex(a.get_actor_location()) or a.get_actor_label()=='LAB_Archive_Entry_Lintel']
 archive_path='/Game/LabTutorial/Archive/Lvl_ArchiveRoom_Preserved'
 if archive_actors:
  if A.does_asset_exist(archive_path):archive_path+='_'+datetime.datetime.now().strftime('%H%M%S')
  report['archived']=[a.get_actor_label() for a in archive_actors]
  # Transfer shared-batch details by instance; other room/corridor instances stay.
  details=[]
  for actor in actors():
   for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
    indices=[]
    for i in range(c.get_instance_count()):
     t=c.get_instance_transform(i,world_space=True)
     if annex(t.translation):details.append((c.get_editor_property('static_mesh'),list(c.get_materials()),t));indices.append(i)
    if indices:
     c.modify()
     for i in reversed(indices):c.remove_instance(i)
  stream=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,archive_path,False)
  if not stream:raise RuntimeError('Cannot create preserved archive level')
  moved=unreal.EditorLevelUtils.move_actors_to_level(archive_actors,stream,False,False)
  if moved!=len(archive_actors):raise RuntimeError('Not all archive actors moved: '+str((moved,len(archive_actors))))
  unreal.EditorLevelUtils.make_level_current(stream)
  for i,(mesh,materials,t) in enumerate(details):
   a=sub.spawn_actor_from_class(unreal.StaticMeshActor,t.translation,t.rotation.rotator())
   a.set_actor_label('ARCHIVE_PreservedDetail_%03d'%i);a.set_actor_transform(t,False,True)
   c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('NoCollision')
   for j,mat in enumerate(materials):
    if mat:c.set_material(j,mat)
  report['instances_archived']=len(details);report['archive_level']=archive_path
  dest=os.path.join(content,archive_path.removeprefix('/Game/')+'.umap');os.makedirs(os.path.dirname(dest),exist_ok=True)
  save_package(archive_path,dest)
  unreal.EditorLevelLibrary.set_current_level_by_name('Lvl_LabTutorial')
  if not unreal.EditorLevelUtils.remove_level_from_world(stream.get_loaded_level(),True,False):raise RuntimeError('Could not detach preserved archive')

 with unreal.ScopedEditorTransaction('Clear tutorial corridor and close archive entrance'):
  for a in actors():
   n=a.get_actor_label()
   remove=n.startswith(('LAB_Wall_ServicePanel_830_','LAB_Wall_PanelStatus_830_','LAB_Tutorial_JumpWreck_','LAB_Tutorial_StealthCover_'))
   remove=remove or n in ('LAB_Tutorial_Sign_Movement','LAB_Tutorial_Sign_Crouch','LAB_Tutorial_Sign_Stealth','LAB_Tutorial_Sign_Archive','LAB_Tutorial_Sign_Door')
   if remove:report['removed'].append(n);sub.destroy_actor(a)
  existing={a.get_actor_label() for a in actors()}
  cube=A.load_asset('/Engine/BasicShapes/Cube')
  def box(name,p,size,material,blocking=True):
   if name in existing:return
   a=sub.spawn_actor_from_class(unreal.StaticMeshActor,v(*p));a.set_actor_label(name);a.set_folder_path('LAB/08_CorridorRefit')
   c=a.static_mesh_component;c.set_static_mesh(cube);c.set_material(0,A.load_asset(material));c.set_collision_profile_name('BlockAll' if blocking else 'NoCollision')
   a.set_actor_scale3d(v(*(s/100. for s in size)))
  root='/Game/LabTutorial/Industrial/'
  box('LAB_Corridor_Wall_North_ClosedArchive',(1400,230,250),(400,60,500),root+'M_Concrete_Dirty')
  # Flush service panels and floor-edge guides detail the wall without obstacles.
  for x in (1260,1575):box('LAB_Corridor_ServicePanel_'+str(x),(x,197,238),(94,5,170),root+'M_DistressedMetal',False)
  for y in (-190,190):box('LAB_Corridor_EdgeGuide_'+str(y),(1600,y,2),(1290,3,2),root+'M_CyanIndicator',False)
  for a in actors():
   if a.get_actor_label().startswith('LAB_Corridor_Conduit_'):
    a.modify();p=a.get_actor_location();p.z=419.;a.set_actor_location(p,False,True)

 sub.set_selected_level_actors([])
 mainfile=os.path.join(content,'Lvl_LabTutorial.umap');start=time.time()
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 report['saved']=os.path.getmtime(mainfile)>=start-1
 if not report['saved']:
  report['staged_map']=os.path.join(folder,'Lvl_LabTutorial_Cleaned.umap')
  save_package('/Game/Lvl_LabTutorial',report['staged_map'])
  unreal.log_warning('CORRIDOR CLEANED IN EDITOR; SOURCE MAP STILL LOCKED')
 else:unreal.log('CORRIDOR CLEANUP SAVED')
 # Show the now-open lab entrance from the corridor in the user's editor.
 eye=v(1320,-30,215);target=v(650,0,200)
 editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,target))
 unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error']);raise
finally:
 with open(os.path.join(saved,'corridor_cleanup_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
