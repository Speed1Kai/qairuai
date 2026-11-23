"""Industrial art and spatial pass for the existing, playable laboratory.

All geometry, materials, Niagara, Sequence and door Blueprint are saved assets.
No Python is needed in the shipped game. Original packages are copied to Saved.
"""
import unreal,os,sys,json,math,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
from Industrial_Materials import build_materials
from Industrial_Door import import_models,build_steam,build_door

SAVED=unreal.Paths.project_saved_dir();CONTENT=unreal.Paths.project_content_dir()
REPORT=os.path.join(SAVED,'industrial_lab_report.json')
report={'saved':False,'warnings':[]}
OLD=(-550.,280.,0.);NEW=(-650.,540.,0.);YAW=-45.
def turn(p):
 x,y,z=p;x-=OLD[0];y-=OLD[1];t=math.radians(YAW)
 return (NEW[0]+x*math.cos(t)-y*math.sin(t),NEW[1]+x*math.sin(t)+y*math.cos(t),z)
def rotate(r):return unreal.Rotator(pitch=r[0],yaw=r[1]+YAW,roll=r[2])
def existing():return list(unreal.EditorLevelLibrary.get_all_level_actors())
def backup_file(rel):
 src=os.path.join(CONTENT,rel);dst=os.path.join(report['backup'],rel)
 if os.path.isfile(src) and not os.path.isfile(dst):os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)

def rotate_capsule():
 with open(os.path.join(SAVED,'industrial_lab_inspection.json'),encoding='utf8') as f:baseline=json.load(f)
 byname={a.get_actor_label():a for a in existing()}
 # Use the captured source transforms, so rerunning cannot rotate by another 45 degrees.
 for row in baseline['actors']:
  name=row['label']
  if (name.startswith('INTRO_') and name!='INTRO_OpeningSequence' and not row['parent']) or name=='LAB_PlayerStart':
   a=byname.get(name)
   if a:a.set_actor_location(V(turn(row['p'])),False,False);a.set_actor_rotation(rotate(row['r']),False)
 seq=A.load_asset('/Game/LabTutorial/Intro/LS_CapsuleAwakening')
 baseseq={b['name']:b for b in baseline['capsule_sequence']}
 changed=[]
 for binding in seq.get_bindings():
  name=str(binding.get_display_name());source=baseseq.get(name)
  if not source or not name.startswith('INTRO_'):continue
  oldtracks=[t for t in source['tracks'] if t['class']=='MovieScene3DTransformTrack']
  tracks=[t for t in binding.get_tracks() if t.get_class().get_name()=='MovieScene3DTransformTrack']
  for track,oldtrack in zip(tracks,oldtracks):
   for sec,oldsec in zip(track.get_sections(),oldtrack['sections']):
    channels=sec.get_all_channels();old=oldsec['channels']
    for i in range(len(old[0]['keys'])):
     p=[old[k]['keys'][i]['value'] for k in range(3)];q=turn(p)
     for k in range(3):channels[k].get_keys()[i].set_value(q[k])
    for key,oldkey in zip(channels[5].get_keys(),old[5]['keys']):key.set_value(oldkey['value']+YAW)
  changed.append(name)
 report['capsule']={'yaw_delta':YAW,'old_center':OLD,'center':NEW,'player_start':turn((-220,280,100)),'exit_direction':(.70710678,-.70710678,0),'sequence_bindings_transformed':changed,'vertical_axis':'upright, no pitch added','ramp_rotated_with_shell':True}
 return seq

def replace_workstations(meshes):
 for a in existing():
  if a.get_actor_label().startswith(('LAB_Workbench_01_','LAB_Workbench_02_')):unreal.EditorLevelLibrary.destroy_actor(a)
 for i,x in enumerate((-160,420),1):
  spawn('IND_CRT_Workstation_%02d'%i,meshes['SM_IndustrialWorkbench'],(x,610,0))
  proxy=spawn('IND_WorkstationCollision_%02d'%i,A.load_asset('/Engine/BasicShapes/Cube'),(x,610,96),collision=True);proxy.set_actor_scale3d(V((3.1,1.15,1.92)));proxy.static_mesh_component.set_visibility(False);proxy.set_actor_hidden_in_game(True)
 report['workstations']=2

def upgrade_projectors(meshes):
 for i in range(1,7):
  bp=A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i)
  for h,c,n in components(bp):
   if n=='Foot':
    c.set_static_mesh(meshes['SM_DockingGenerator']);c.set_editor_property('relative_location',V((0,0,0)));c.set_editor_property('relative_scale3d',V((1,1,1)))
    # Clear overrides from the old single-material primitive to use the mesh's slots.
    c.set_editor_property('override_materials',[])
   elif n in ('Housing','EmitterRim','Lens','EmitterCore') or n.startswith('CoolingRib'):c.set_visibility(False)
  compile_bp(bp);save(bp)

def apply_materials(mats):
 changed=0
 for a in existing():
  n=a.get_actor_label();c=a.get_component_by_class(unreal.StaticMeshComponent)
  if not c:continue
  if n.startswith(('HOLO_','IND_')):continue
  mat=None
  if n.startswith(('LAB_Wall','LAB_Ceiling','LAB_Room_Floor','LAB_Corridor_Wall','LAB_Corridor_Floor','LAB_Archive_Annex_Wall','LAB_Archive_Annex_Floor')):mat=mats['M_Concrete_Dirty']
  elif n.startswith('INTRO_') and any(s in n for s in ('RearShell','Collar','FrameRing','UprightRib','RearServicePanel','CircularPlinth','OverheadHousing','ExitRamp','RampEdge','DoorRim','DoorStile','InteriorCeiling')):mat=mats['M_DistressedMetal']
  elif n.startswith(('REF_','LAB_')):
   old=c.get_material(0);oldname=old.get_name() if old else ''
   if oldname in ('M_OxidizedPaint','M_WornPodEnamel','MI_FP_EdenSilver','MI_FP_RustedSteel'):mat=mats['M_DistressedMetal']
   elif oldname in ('M_Rust',):mat=mats['M_RustyIron']
   elif oldname=='M_AgedConcrete':mat=mats['M_Concrete_Dirty']
  if mat:c.set_material(0,mat);changed+=1
 report['material_assignments']=changed

def capsule_armor(meshes):
 for a in existing():
  if a.get_actor_label().startswith('INTRO_RearShell_'):unreal.EditorLevelLibrary.destroy_actor(a)
 armor=spawn('IND_CapsuleArmor',meshes['SM_CapsuleArmor'],NEW,unreal.Rotator(yaw=YAW))
 cube=A.load_asset('/Engine/BasicShapes/Cube')
 for i in range(23):
  a=math.radians(70+i*10);p=turn((OLD[0]+113*math.cos(a),OLD[1]+113*math.sin(a),146))
  proxy=spawn('IND_CapsuleCollision_%02d'%i,cube,p,unreal.Rotator(yaw=70+i*10+YAW),True);proxy.set_actor_scale3d(V((.12,.21,2.43)));proxy.static_mesh_component.set_visibility(False);proxy.set_actor_hidden_in_game(True)
 spawn('IND_CapsuleUmbilical',meshes['SM_CapsuleUmbilical'],NEW,unreal.Rotator(yaw=YAW))

def dress_room(meshes):
 for wall in (-1,1):
  for i,x in enumerate((-730,-360,10,380,750)):
   spawn('IND_WallBeam_%d_%d'%(wall,i),meshes['SM_WallReinforcement'],(x,wall*748,0),unreal.Rotator(yaw=90 if wall==1 else -90))
 for j,y in enumerate((-180,180)):
  for i,x in enumerate((-690,-390,-90,210,510,790)):
   spawn('IND_CeilingDuct_%d_%d'%(j,i),meshes['SM_VentDuct'],(x,y,468))
 # Service enclosure above the opening, hiding the retracted blast slab.
 cube=A.load_asset('/Engine/BasicShapes/Cube')
 for name,p,s in [('FrontPocket',(1385,0,700),(22,450,480)),('RearPocket',(1515,0,700),(22,450,480))]:
  a=spawn('IND_Door'+name,cube,p);a.set_actor_scale3d(V([v/100 for v in s]));a.static_mesh_component.set_material(0,mats['M_DistressedMetal'])

def replace_door(bp):
 for a in existing():
  n=a.get_actor_label()
  if n=='LAB_Door_Closed_Blockout' or n.startswith(('LAB_DoorFrame_','LAB_DoorLock_')) or n=='LAB_Tutorial_Sign_Hacking':unreal.EditorLevelLibrary.destroy_actor(a)
 door=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V((1450,0,8)),unreal.Rotator())
 door.set_actor_label('IND_HeavyBlastDoor');door.set_folder_path('LAB/03_Interactables')

def intro_niagara(system):
 bp=bp_asset('BP_CapsulePressureVent')
 fx=add(bp,unreal.NiagaraComponent,'SteamBurst');fx.set_asset(system);fx.set_editor_property('auto_activate',False);fx.set_editor_property('cast_shadow',False)
 compile_bp(bp);g=Graph(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay');g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=1.05));g.do(g.call('Engine.ActorComponent.Activate',target=g.get('SteamBurst'),bReset=True))
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=2.3));g.do(g.call('Engine.ActorComponent.Deactivate',target=g.get('SteamBurst')))
 compile_bp(bp);save(bp)
 for side in (-1,1):
  p=turn((-440,280+side*65,12));a=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V(p),unreal.Rotator(yaw=YAW));a.set_actor_label('IND_CapsuleVent'+str(side));a.set_folder_path('LAB/00_Opening');a.set_actor_scale3d(V((.75,.75,.75)))

def lighting(mats):
 for a in existing():
  n=a.get_actor_label();p=a.get_actor_location()
  fog=a.get_component_by_class(unreal.ExponentialHeightFogComponent)
  if fog:
   fog.set_editor_property('enable_volumetric_fog',False);fog.set_editor_property('fog_density',.008);fog.set_editor_property('fog_max_opacity',.28);fog.set_editor_property('start_distance',160.)
  light=a.get_component_by_class(unreal.LightComponent)
  if light and p.x<950:
   if n.startswith(('REF_AlarmGlow','LAB_RedEmergency')):
    light.set_intensity(850.);light.set_light_color(unreal.LinearColor(r=1.,g=.065,b=.022,a=1));light.set_cast_shadows(False)
   elif n.startswith('REF_CeilingPool'):
    light.set_intensity(950.);light.set_light_color(unreal.LinearColor(r=.34,g=.48,b=.51,a=1));light.set_cast_shadows(False)
   elif n=='INTRO_InteriorLight':light.set_intensity(650.)
 # Two local shadowless pools let emissive CRTs touch the nearby geometry.
 for i,x in enumerate((-160,420)):
  a=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight,V((x,510,158)),unreal.Rotator());a.set_actor_label('IND_CRTGlow%d'%i);a.set_folder_path('LAB/02_Lighting')
  c=a.point_light_component;c.set_intensity(90.);c.set_light_color(unreal.LinearColor(r=.02,g=.6,b=.66,a=1));c.set_editor_property('attenuation_radius',190.);c.set_cast_shadows(False)
 report['atmosphere']={'height_fog_density':.008,'volumetric_fog':False,'new_shadowless_lights':2,'CRT_and_indicators':'subtle material flicker'}

def batch_decorations():
 prefixes=('REF_CeilingBundle','REF_CorridorCable','REF_Crack_','REF_WaterStain_','REF_Rubble','REF_WallJoint_','REF_ServerVent_','REF_ServerDrawer_','REF_ServerLED_')
 group={};sources=[]
 for a in existing():
  if not a.get_actor_label().startswith(prefixes):continue
  c=a.get_component_by_class(unreal.StaticMeshComponent)
  if not c or a.get_attach_parent_actor():continue
  mesh=c.get_editor_property('static_mesh');mat=c.get_material(0)
  if not mesh or not mat:continue
  key=(mesh.get_path_name(),mat.get_path_name());group.setdefault(key,[]).append(a.get_actor_transform());sources.append(a)
 bp=bp_asset('BP_IndustrialDressing');compile_bp(bp)
 if not sources:
  # The previous successful pass already consolidated the source actors.
  # Reuse its saved template instances when rebuilding other room details.
  a=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)),unreal.Rotator());a.set_actor_label('IND_InstancedDressing');a.set_folder_path('LAB/07_Industrial')
  cs=a.get_components_by_class(unreal.InstancedStaticMeshComponent)
  report['batching']={'reused_saved_instances':sum(c.get_instance_count() for c in cs),'mesh_material_batches':len(cs)}
  return
 for i,((mesh,mat),transforms) in enumerate(sorted(group.items())):
  c=add(bp,unreal.InstancedStaticMeshComponent,'Batch%02d'%i);c.set_static_mesh(A.load_asset(mesh));c.set_material(0,A.load_asset(mat));c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.clear_instances()
  for transform in transforms:c.add_instance(transform,world_space=False)
 compile_bp(bp);save(bp)
 a=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)),unreal.Rotator());a.set_actor_label('IND_InstancedDressing');a.set_folder_path('LAB/07_Industrial')
 count=sum(c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent))
 if count!=len(sources):raise RuntimeError('Instanced dressing lost transforms '+str((count,len(sources))))
 for a in sources:unreal.EditorLevelLibrary.destroy_actor(a)
 report['batching']={'replaced_actors':len(sources),'instances':count,'mesh_material_batches':len(group)}

try:
 report['backup']=os.path.join(SAVED,'Backups','IndustrialLab',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(report['backup'],exist_ok=True)
 backup_file('Lvl_LabTutorial.umap');backup_file('LabTutorial/Intro/LS_CapsuleAwakening.uasset')
 for i in range(1,7):backup_file('LabTutorial/Holograms/BP_ArchiveProjector_%02d.uasset'%i)
 A.make_directory(ROOT)
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 # Rerunnable additions use a dedicated actor prefix.
 for a in existing():
  if a.get_actor_label().startswith('IND_'):unreal.EditorLevelLibrary.destroy_actor(a)
 seq=rotate_capsule()
 mats=build_materials();report['materials']=list(mats)
 meshes=import_models(mats);report['meshes']={n:m.get_path_name() for n,m in meshes.items()}
 steam=build_steam(mats,report);doorbp=build_door(meshes,steam,report)
 apply_materials(mats);replace_workstations(meshes);upgrade_projectors(meshes);capsule_armor(meshes);dress_room(meshes);replace_door(doorbp);intro_niagara(steam);lighting(mats);batch_decorations()
 report['actor_count']=len(existing())
 report['map']='/Game/Lvl_LabTutorial';save(seq)
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Map save failed; close the open Unreal Editor to release files')
 report['saved']=True
 unreal.log('INDUSTRIAL LAB SAVED')
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(REPORT,'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Industrial laboratory pass incomplete; see '+REPORT)
