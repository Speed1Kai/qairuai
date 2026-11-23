"""Author a detailed first city street from four coherent CityDowntown buildings.

Uses a captured native inventory of the supplied demonstration map. Hundreds of
source Blueprint actors are flattened into shared static HISM batches; no source
construction scripts, lights, or demonstration gameplay run in the game level.
"""
import unreal,os,sys,json,math,shutil,datetime,traceback,collections,random
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,V,add,components,compile_bp,save
ROOT='/Game/Environment/DowntownFirstBlock';LEVEL='/Game/Surface/Lvl_SurfaceArrival'
project=os.path.abspath(unreal.Paths.project_dir());tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'saved':False,'gameplay_tested':False,'buildings':[],'removed_old_actors':[]}
backup=os.path.join(project,'Saved','Backups','DowntownFirstBlock',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True);report['backup']=backup

def back(path,ext='.uasset'):
 rel=path.removeprefix('/Game/')+ext;src=os.path.join(project,'Content',rel)
 if os.path.isfile(src):
  dest=os.path.join(backup,rel);os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(src,dest)

def material(path):
 if not path or 'WorldGridMaterial' in path:return A.load_asset('/Game/Surface/Materials/M_RuinConcrete')
 if '/Windows/' not in path:return A.load_asset(path)
 if path in dark_windows:return dark_windows[path]
 name=path.rsplit('/',1)[-1].split('.')[0]+'_Abandoned';dest=ROOT+'/Materials/'+name
 result=A.load_asset(dest) if A.does_asset_exist(dest) else A.duplicate_asset(path,dest)
 names=list(map(str,M.get_scalar_parameter_names(result)))
 for key in ('Emissive','Power Emissive'):
  if key in names:M.set_material_instance_scalar_parameter_value(result,key,0.)
 # Retain the original frame textures, roughness and parallax-window structure.
 if 'Brightness' in names:M.set_material_instance_scalar_parameter_value(result,'Brightness',.55)
 M.update_material_instance(result);save(result);dark_windows[path]=result;return result

def transform(data,offset=(0,0,0)):
 p=data['location'];r=data['rotation']
 return unreal.Transform(location=V(tuple(p[i]+offset[i] for i in range(3))),rotation=unreal.Rotator(pitch=r[0],yaw=r[1],roll=r[2]),scale=V(data['scale']))

try:
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 unreal.SystemLibrary.execute_console_command(world,'Editor.AsyncTextureCompilation 0')
 plan=json.load(open(os.path.join(project,'SourceAssets/DowntownFirstBlock/selection.json'),encoding='utf8'))
 A.make_directory(ROOT);A.make_directory(ROOT+'/Materials')
 path=ROOT+'/BP_FirstCityBlock';back(path);back(LEVEL,'.umap')
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
  bp=tools.create_asset('BP_FirstCityBlock',ROOT,unreal.Blueprint,f)
 root=add(bp,unreal.SceneComponent,'Root');root.set_mobility(unreal.ComponentMobility.STATIC)
 # A run can be safely continued after a native save failure.
 for h,c,n in components(bp):
  if isinstance(c,unreal.InstancedStaticMeshComponent):c.clear_instances()
 batches={};dark_windows={};meshes={};instance_count=0
 def mesh(path):
  if path not in meshes:
   meshes[path]=A.load_asset(path)
   if not isinstance(meshes[path],unreal.StaticMesh):raise RuntimeError('Missing mesh '+path)
  return meshes[path]
 def item(path,t,materials=None,collision=False,hidden=False):
  global instance_count
  obj=mesh(path);mats=tuple(materials or [])
  key=(path,mats,collision,hidden)
  if key not in batches:
   name='Batch_%03d'%len(batches)
   c=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,name,'Root');c.clear_instances();c.set_static_mesh(obj)
   c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
   c.set_editor_property('can_ever_affect_navigation',False);c.set_cull_distances(0,55000)
   for i,m in enumerate(mats):c.set_material(i,material(m))
   if hidden:c.set_visibility(False);c.set_hidden_in_game(True);c.set_editor_property('cast_shadow',False)
   batches[key]=c
  batches[key].add_instance(t,False);instance_count+=1
 def fitted(path,center,size,yaw=0,materials=None,collision=False,hidden=False):
  obj=mesh(path);b=obj.get_bounding_box()
  lo=(b.min.x,b.min.y,b.min.z);hi=(b.max.x,b.max.y,b.max.z)
  scale=[size[i]/max(hi[i]-lo[i],.001) if size[i] else 1. for i in range(3)]
  ox=(lo[0]+hi[0])*.5*scale[0];oy=(lo[1]+hi[1])*.5*scale[1];a=math.radians(yaw)
  pos=(center[0]-ox*math.cos(a)+oy*math.sin(a),center[1]-ox*math.sin(a)-oy*math.cos(a),center[2]-lo[2]*scale[2])
  item(path,unreal.Transform(location=V(pos),rotation=unreal.Rotator(yaw=yaw),scale=V(scale)),materials,collision,hidden)
 def prop(name,p,yaw=0,scale=1.,collision=False,pitch=0,materials=None):
  path='/Game/CityDowntown/Geometry/Props/'+name;obj=mesh(path);b=obj.get_bounding_box()
  if pitch:
   t=unreal.Transform(location=V(p),rotation=unreal.Rotator(pitch=pitch,yaw=yaw),scale=V((scale,)*3))
  else:
   ox=(b.min.x+b.max.x)*.5*scale;oy=(b.min.y+b.max.y)*.5*scale;a=math.radians(yaw)
   t=unreal.Transform(location=V((p[0]-ox*math.cos(a)+oy*math.sin(a),p[1]-ox*math.sin(a)-oy*math.cos(a),p[2]-b.min.z*scale)),rotation=unreal.Rotator(yaw=yaw),scale=V((scale,)*3))
  item(path,t,materials,collision)
 cube='/Engine/BasicShapes/Cube';concrete='/Game/Surface/Materials/M_RuinConcrete';asphalt='/Game/CityDowntown/Materials/MI_Asphalt'
 for building in plan['buildings']:
  for actor in building['actors']:
   for c in actor['components']:
    for t in c['transforms']:item(c['mesh'],transform(t,building['offset']),c['materials'])
  x,y,z=building['target_center'];sx,sy,sz=building['size']
  # Closed facades use one inexpensive body collision, rather than thousands of
  # per-polygon collision triangles. Roof caps close procedural demo roofs.
  fitted(cube,(x,y,22),(sx-60,sy-60,sz+20),materials=[concrete],collision=True,hidden=True)
  fitted(cube,(x,y,z+sz-14),(sx-45,sy-45,22),materials=[concrete])
  for dx,dy in [(-sx*.2,-sy*.15),(sx*.15,sy*.2)]:
   prop('SM_ac2',(x+dx,y+dy,z+sz+10),90,1.,materials=['/Game/CityDowntown/MasterMaterials/M_ac'])
  report['buildings'].append({'source':building['source'],'position':[x,y,z],'size_cm':[sx,sy,sz],'source_actors':len(building['actors'])})
 # A continuous walkable connection begins after the bridge's far bank. The
 # channel and broken bridge remain completely outside this authored region.
 fitted(cube,(0,29000,-10),(1400,9600,30),materials=[asphalt],collision=True)
 road='/Game/CityDowntown/Geometry/RoadDecalsAndProps/SM_roadPiece4lanes'
 walk='/Game/CityDowntown/Geometry/RoadDecalsAndProps/walkside_6x6_simple'
 road_mats=['/Game/CityDowntown/Materials/MI_Asphalt'];walk_mats=['/Game/CityDowntown/Materials/MI_walkside01','/Game/CityDowntown/Materials/MI_walkside02']
 for y in range(24500,34100,600):
  fitted(road,(0,y,21),(1400,600,0),materials=road_mats)
  for side in (-1,1):
   fitted(walk,(side*1000,y,23),(600,600,0),yaw=0 if side<0 else 180,materials=walk_mats)
   fitted(cube,(side*1000,y,13),(600,600,27),materials=[concrete],collision=True)
 # Lane markings, patches and drains are native textured meshes from the pack.
 marking='/Game/CityDowntown/Geometry/RoadDecalsAndProps/SM_roadSmallMarking'
 for y in range(24900,33600,600):
  fitted(marking,(0,y,25),(12,260,0),materials=['/Game/CityDowntown/Materials/MI_decalRoad'])
 for side in (-1,1):
  for y in (25800,28100,30600,32900):prop('SM_streetLight',(side*1220,y,40),90 if side<0 else -90)
  for y in (27200,31700):prop('SM_hydrant',(side*850,y,40),side*90)
  for y in (26600,32200):prop('SM_streetBin',(side*1150,y,40),-side*90)
  prop('SM_mailbox',(side*1130,29250,40),-side*90)
  prop('SM_NewspaperBox',(side*1130,26200,40),-side*90)
 for i,(x,y) in enumerate([(-560,25250),(510,28700),(-490,30500),(560,33200)]):
  prop('SM_RoadConstruction_cone',(x,y,25),i*37)
  prop('SM_trashBag01',(x*1.8,y+120,40),i*23)
 prop('SM_streetLight',(530,31100,70),23,1.,pitch=-83)
 # Blend the detailed street with the existing ruined world using its debris and
 # three wrecked vehicles. Keep a clear route through the middle and sidewalks.
 rubble='/Game/Surface/Meshes/SM_RubbleCluster';car='/Game/Surface/Meshes/SM_WreckedSedan'
 for i,(x,y,s) in enumerate([(-560,25400,.45),(580,27000,.5),(-1100,29400,.38),(590,30700,.5),(-570,32450,.45),(1200,33000,.4)]):
  item(rubble,unreal.Transform(location=V((x,y,24)),rotation=unreal.Rotator(yaw=i*61),scale=V((s,s,s))))
 for x,y,yaw in [(-430,26700,18),(460,30100,-14),(-450,33100,33)]:
  item(car,unreal.Transform(location=V((x,y,27)),rotation=unreal.Rotator(yaw=yaw),scale=V((1,1,1))),collision=True)
 compile_bp(bp)
 cdo=unreal.get_default_object(B.generated_class(bp));tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick);save(bp)
 # Replace only the four original nearest residential placeholders; the skyline,
 # campus perimeter, bridge, recovery sensor and progression remain in place.
 unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 for actor in list(sub.get_all_level_actors()):
  label=actor.get_actor_label()
  if label in ('CITY_Residential_001','CITY_Residential_002','CITY_Residential_003','CITY_Residential_004','CITY_FirstDowntownBlock'):
   report['removed_old_actors'].append(label);sub.destroy_actor(actor)
 actor=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));actor.set_actor_label('CITY_FirstDowntownBlock');actor.set_folder_path('SURFACE/First City Block')
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('City block map save failed')
 report.update(saved=True,blueprint=path,instances=instance_count,shared_batches=len(batches),dark_window_materials=len(dark_windows),new_dynamic_lights=0,street_length_m=96,connection_start_y=24200,texture_limit=2048)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','downtown_first_block_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('First city block authoring incomplete')
