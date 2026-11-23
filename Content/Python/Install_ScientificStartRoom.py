"""Replace the opening room's art with the supplied scientific-lab GLB scene.

Keeps the existing capsule sequence, player start, projectors, power controller,
interactions, corridor and lift. Changes are native saved actors and materials.
"""
import unreal,os,sys,json,math,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,V,save
p=os.path.abspath(unreal.Paths.project_dir());LEVEL='/Game/Lvl_LabTutorial'
ROOT='/Game/Environment/ScientificLab';S=.09;OFFSET=(124.,-286.,9.)
r={'saved':False,'gameplay_tested':False,'scale':S,'offset':OFFSET,'imported':0,'omitted':[],'old_art_hidden':[],'clearance_omitted':[]}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def inside(v):return -1350<v.x<950 and -1150<v.y<1200 and -100<v.z<1050
def clearance(o,e):
 # Existing cinematic capsule, player release, and the eastbound exit path.
 for x0,x1,y0,y1 in [(-950,-220,170,930),(-430,1000,-220,200)]:
  if o[0]+e[0]>x0 and o[0]-e[0]<x1 and o[1]+e[1]>y0 and o[1]-e[1]<y1:return True
 return False
def cube(name,center,size,mat,visible=True):
 a=sub.spawn_actor_from_class(unreal.StaticMeshActor,V(center));a.set_actor_label(name);a.set_folder_path('LAB/ScientificRoom/Architecture')
 c=a.static_mesh_component;c.set_mobility(unreal.ComponentMobility.STATIC);c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,mat)
 a.set_actor_scale3d(V([v/100 for v in size]));c.set_collision_profile_name('BlockAll');c.set_visibility(visible);c.set_hidden_in_game(not visible);return a
try:
 data=json.load(open(os.path.join(p,'Saved/scientific_lab_import.json'),encoding='utf8'))
 if not data['saved']:raise RuntimeError('Scene import incomplete')
 backup=os.path.join(p,'Saved/Backups/ScientificStartRoom',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 shutil.copy2(os.path.join(p,'Content/Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'));r['backup']=backup
 unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 # Preserve old geometry as hidden native actors, so reversing this art pass
 # does not rely on reconstructing the former room from names or scripts.
 for a in list(sub.get_all_level_actors()):
  name=a.get_actor_label()
  if name.startswith('SCI_'):
   sub.destroy_actor(a);continue
  if name.startswith(('INTRO_','HOLO_','BASE_')) or name=='LAB_PlayerStart':continue
  if isinstance(a,unreal.StaticMeshActor) and inside(a.get_actor_location()):
   a.modify();c=a.static_mesh_component;c.modify();c.set_visibility(False);c.set_hidden_in_game(True);a.set_actor_enable_collision(False);r['old_art_hidden'].append(name)
  elif name.startswith(('IND_','REF_')):
   for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
    for i in reversed(range(c.get_instance_count())):
     if inside(c.get_instance_transform(i,True).translation):a.modify();c.modify();c.remove_instance(i)
 # Imported PBR instances can require explicit instancing/Nanite usage saves.
 fallback=A.load_asset('/Game/LabTutorial/Industrial/M_DistressedMetal')
 if not fallback:fallback=A.load_asset('/Game/Surface/Materials/M_RuinSteel')
 if not fallback:raise RuntimeError('Fallback metal unavailable')
 mats={};meshes={}
 for row in data['actors']:
  for j,q in enumerate(row['components']):
   name=row['label'];origin=[q['origin'][i]*S+OFFSET[i] for i in range(3)];extent=[q['extent'][i]*S for i in range(3)]
   is_shell=name=='Cube_339' or any(m and '/Material_057.' in m for m in q['materials'])
   if is_shell or origin[0]+extent[0]<-1300 or origin[0]-extent[0]>910 or origin[1]+extent[1]<-1120 or origin[1]-extent[1]>1170:
    r['omitted'].append(name);continue
   # Keep floor plates and upper galleries. Remove entire obstructing detail
   # objects from the reserved capsule and level-zero release/exit corridor.
   ground_detail=origin[2]-extent[2]<280 and origin[2]+extent[2]>35 and max(extent[:2])<350
   if ground_detail and clearance(origin,extent):r['clearance_omitted'].append(name);continue
   mesh=meshes.setdefault(q['mesh'],A.load_asset(q['mesh']))
   if not mesh:raise RuntimeError('Missing imported mesh '+q['mesh'])
   a=sub.spawn_actor_from_class(unreal.StaticMeshActor,V([q['p'][i]*S+OFFSET[i] for i in range(3)]),unreal.Rotator(pitch=q['r'][0],yaw=q['r'][1],roll=q['r'][2]))
   a.set_actor_label('SCI_'+name+('_%d'%j if j else ''));a.set_folder_path('LAB/ScientificRoom/Imported')
   c=a.static_mesh_component;c.set_mobility(unreal.ComponentMobility.STATIC);c.set_static_mesh(mesh);a.set_actor_scale3d(V([v*S for v in q['s']]))
   for i,mp in enumerate(q['materials']):
    mat=mats.setdefault(mp,A.load_asset(mp)) if mp and 'DefaultMaterial' not in mp and 'WorldGrid' not in mp else fallback
    c.set_material(i,mat or fallback)
   c.set_editor_property('can_ever_affect_navigation',False)
   collision=origin[2]-extent[2]<90 and origin[2]+extent[2]>80 and max(extent[:2])>35
   if clearance(origin,extent):collision=False
   c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
   r['imported']+=1
 # A reliable planar walk surface and a fitted enclosure with the existing
 # east doorway. Source outer walls are intentionally omitted to leave it open.
 wall=A.load_asset('/Game/LabTutorial/Industrial/M_Concrete_Dirty') or fallback
 floor=A.load_asset('/Game/LabTutorial/Industrial/M_DistressedMetal') or fallback
 cube('SCI_WalkableFloor',(-165,15,-18),(2200,2300,36),floor,False)
 for n,pos,size in [('West',(-1270,15,475),(34,2300,950)),('North',(-165,1165,475),(2200,34,950)),('South',(-165,-1135,475),(2200,34,950)),('EastNorth',(935,690,475),(34,950,950)),('EastSouth',(935,-690,475),(34,950,950)),('DoorLintel',(935,0,690),(34,430,520)),('Ceiling',(-165,15,965),(2234,2334,30))]:cube('SCI_Room_'+n,pos,size,wall)
 # Wall ribs and low service panels continue the model's industrial language.
 for y in (-1000,-500,0,500,1000):cube('SCI_WestSupport_'+str(y),(-1245,y,475),(35,30,950),fallback)
 # Keep the existing circuit's actor references: redistribute its actual room
 # lights instead of adding lamps which would bypass the power-restoration task.
 lights=[a for a in sub.get_all_level_actors() if isinstance(a,unreal.PointLight) and inside(a.get_actor_location()) and not any(t in a.get_actor_label().lower() for t in ('holo','projector','capsule','backup'))]
 slots=[(-800,-650,350),(500,-650,350),(-800,750,350),(500,750,350),(-300,100,650),(250,650,720)]
 for i,a in enumerate(lights):
  a.modify();a.set_actor_location(V(slots[i%len(slots)]),False,False);c=a.point_light_component;c.modify();c.set_attenuation_radius(1500);c.set_intensity(max(c.get_editor_property('intensity'),2400));c.set_light_color(unreal.LinearColor(.40,.68,1,1));c.set_cast_shadows(i<3)
 r['existing_circuit_lights_repositioned']=len(lights)
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.modify()
 if not unreal.EditorLoadingAndSavingUtils.save_map(world,LEVEL):raise RuntimeError('Room map save failed')
 r['saved']=True;r['map']=LEVEL
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(p,'Saved/scientific_start_room_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
