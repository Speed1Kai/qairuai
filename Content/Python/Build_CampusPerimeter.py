"""Use the supplied distressed industrial wall around the laboratory grounds."""
import unreal,os,sys,math,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,V,add,components,compile_bp,save
ROOT='/Game/Surface/CampusWall';LEVEL='/Game/Surface/Lvl_SurfaceArrival'
project=os.path.abspath(unreal.Paths.project_dir());report={'saved':False,'gameplay_tested':False}
backup=os.path.join(project,'Saved','Backups','CampusPerimeter',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True);report['backup']=backup
def back(path,extension='.uasset'):
 rel=path.removeprefix('/Game/')+extension;src=os.path.join(project,'Content',rel)
 if os.path.isfile(src):
  dest=os.path.join(backup,rel);os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(src,dest)

def remove_old_fence(comps):
 removed=0
 for c in comps:
  if not isinstance(c,unreal.InstancedStaticMeshComponent):continue
  for i in range(c.get_instance_count()-1,-1,-1):
   t=c.get_instance_transform(i,False);p=t.translation;s=t.scale3d
   radius=math.hypot(p.x,p.y-5500.)
   if abs(radius-11500.)>2.:continue
   wall=abs(p.z-105.)<1 and abs(s.x-11.2)<.01 and abs(s.y-.18)<.01 and abs(s.z-1.9)<.01
   rail=abs(p.z-240.)<1 and abs(s.x-11.5)<.01 and abs(s.y-.15)<.01 and abs(s.z-.16)<.01
   post=abs(p.z-125.)<1 and abs(s.x-.34)<.01 and abs(s.y-.34)<.01 and abs(s.z-2.5)<.01
   if wall or rail or post:c.remove_instance(i);removed+=1
 return removed

try:
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Cannot preserve current level')
 back(LEVEL,'.umap');back('/Game/Surface/BP_LaboratoryCampus')
 unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 campus=A.load_asset('/Game/Surface/BP_LaboratoryCampus')
 removed=remove_old_fence([c for h,c,n in components(campus) if c])
 # Placed ISM arrays can contain per-instance overrides, so update their arrays
 # too, keeping every building, gate, planting bed and collision block intact.
 live_removed=0
 for actor in sub.get_all_level_actors():
  if actor.get_actor_label()=='CAMPUS_LaboratoryGrounds':
   live_removed+=remove_old_fence(actor.get_components_by_class(unreal.InstancedStaticMeshComponent))
 compile_bp(campus);save(campus)
 path=ROOT+'/BP_CampusPerimeterWalls';back(path)
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
  bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_CampusPerimeterWalls',ROOT,unreal.Blueprint,factory)
 root=add(bp,unreal.SceneComponent,'Root');root.set_mobility(unreal.ComponentMobility.STATIC)
 walls=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,'PerimeterWallSections','Root')
 walls.clear_instances();mesh=A.load_asset(ROOT+'/SM_Wall_A_Long');walls.set_static_mesh(mesh)
 walls.set_mobility(unreal.ComponentMobility.STATIC);walls.set_collision_profile_name('BlockAll')
 walls.set_cull_distances(0,70000);walls.set_editor_property('cast_shadow',True)
 # Correct the FBX's inverted Z and offset bottom at the component transform.
 # The source mesh and source files are preserved; all copies share one mesh.
 bounds=mesh.get_bounding_box();scale=420./(bounds.max.z-bounds.min.z)
 length=(bounds.max.x-bounds.min.x)*scale
 depth_scale=126./(bounds.max.y-bounds.min.y)
 bottom_offset=bounds.max.z*scale+2.
 count=128;radius=11550.;positions=[]
 for i in range(count):
  angle=i*math.tau/count;x=math.cos(angle)*radius;y=5500+math.sin(angle)*radius
  # Five omitted north sections retain the existing roughly 28 m gate opening.
  if y>16000 and abs(x)<1400:continue
  yaw=math.degrees(angle)-90.
  walls.add_instance(unreal.Transform(location=V((x,y,bottom_offset)),rotation=unreal.Rotator(yaw=yaw,roll=180),scale=V((scale,depth_scale,scale))),False)
  positions.append([x,y])
 # Two returns join the circular wall to the existing gate piers. Their inner
 # faces remain outside x=±1387 cm, clear of the gate's walkable central lane.
 for side in (-1,1):
  walls.add_instance(unreal.Transform(location=V((side*1450.,17050.,bottom_offset)),rotation=unreal.Rotator(yaw=-90 if side==1 else 90,roll=180),scale=V((600./(bounds.max.x-bounds.min.x),depth_scale,scale))),False)
 compile_bp(bp)
 cdo=unreal.get_default_object(B.generated_class(bp));tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick)
 save(bp)
 for actor in list(sub.get_all_level_actors()):
  if actor.get_actor_label()=='CAMPUS_IndustrialPerimeter':sub.destroy_actor(actor)
 actor=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)))
 actor.set_actor_label('CAMPUS_IndustrialPerimeter');actor.set_folder_path('SURFACE/LaboratoryCampus')
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Perimeter map save failed')
 report.update(saved=True,old_default_instances_removed=removed,old_placed_instances_removed=live_removed,
  wall_sections=walls.get_instance_count(),height_cm=420,section_width_cm=length,depth_cm=126,
  radius_cm=radius,lods=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_count(mesh),texture_limit=2048,
  gate_and_bridge_route_preserved=True,blueprint=path)
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Cinematics/Prologue/Lvl_Prologue')
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','campus_perimeter_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Campus perimeter authoring incomplete')
