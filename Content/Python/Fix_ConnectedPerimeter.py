"""Make the streamed perimeter inherit the exterior level rotation correctly."""
import unreal,os,sys,shutil,datetime,json,math
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,components,compile_bp,save,V
root=os.path.abspath(unreal.Paths.project_dir());directory='/Game/Surface/CampusWall';source=directory+'/BP_CampusPerimeterWalls';target=directory+'/BP_ConnectedPerimeterWalls';level='/Game/Surface/Lvl_CampusConnected'
backup=os.path.join(root,'Saved/Backups/ConnectedPerimeter',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
for path,ext in [(level,'.umap'),(target,'.uasset')]:
 file=os.path.join(root,'Content',path.removeprefix('/Game/')+ext)
 if os.path.isfile(file):shutil.copy2(file,os.path.join(backup,os.path.basename(file)))
if not A.does_asset_exist(target):assert A.duplicate_asset(source,target)
bp=A.load_asset(target)
# Bake the campus alignment into this connected-level-only copy. The streamed
# component currently receives translation only; keep the original surface asset
# intact and rebuild from it every run so the correction never accumulates.
source_bp=A.load_asset(source)
original=next(c for h,c,n in components(source_bp) if n=='PerimeterWallSections')
transforms=[original.get_instance_transform(i,False) for i in range(original.get_instance_count())]
angle=49.08561677997487;rad=math.radians(angle)
for h,c,n in components(bp):
 if n!='PerimeterWallSections':continue
 c.modify();c.clear_instances()
 c.set_editor_property('relative_rotation',unreal.Rotator())
 for t in transforms:
  p=t.translation;r=t.rotation.rotator()
  c.add_instance(unreal.Transform(location=V((p.x*math.cos(rad)-p.y*math.sin(rad),p.x*math.sin(rad)+p.y*math.cos(rad),p.z)),rotation=unreal.Rotator(pitch=r.pitch,yaw=r.yaw+angle,roll=r.roll),scale=t.scale3d),False)
# Movable scene hierarchy is required for a transformed dynamic level instance.
# These shared HISM meshes do not tick or move after loading.
for h,c,n in components(bp):
 if isinstance(c,unreal.SceneComponent):c.modify();c.set_mobility(unreal.ComponentMobility.MOVABLE)
compile_bp(bp);save(bp)
world=unreal.EditorLoadingAndSavingUtils.load_map(level);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in list(sub.get_all_level_actors()):
 if a.get_class().get_name() in ('BP_CampusPerimeterWalls_C','BP_ConnectedPerimeterWalls_C'):sub.destroy_actor(a)
a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label('CAMPUS_IndustrialPerimeter');a.set_folder_path('SURFACE/LaboratoryCampus')
world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,level);del world
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
json.dump({'saved':True,'blueprint':target,'backup':backup,'sections':next(c.get_instance_count() for h,c,n in components(bp) if n=='PerimeterWallSections')},open(os.path.join(root,'Saved/connected_perimeter_fix.json'),'w'),indent=2)
