"""Place combatants only in the city sublevel; preserve the starting laboratory."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
R={'saved':False};S=os.path.abspath(unreal.Paths.project_saved_dir())
try:
 assert not unreal.EditorLevelLibrary.get_game_world()
 assert json.load(open(os.path.join(S,'citycombat_build.json')))['saved']
 sk=A.load_asset(ROOT+'/SK_Enceladus')
 phys=sk.physics_asset
 if not phys or not A.does_asset_exist(phys.get_path_name()):phys=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).create_physics_asset(sk,True)
 assert phys;save(phys);save(sk)
 for name in ('BP_CityEnceladus','BP_Enceladus_Carbine','BP_Enceladus_Shotgun','BP_Enceladus_Plasma'):
  bp=A.load_asset(ROOT+'/'+name)
  cd=unreal.get_default_object(B.generated_class(bp));cd.get_component_by_class(unreal.SkeletalMeshComponent).set_physics_asset(phys)
  for n in G.get_graph_editor_by_name(bp,'EventGraph').list_all_nodes():
   if n.find_input_pin('NewMesh').is_valid():val(pin(n,'NewMesh'),sk.get_path_name())
   if n.find_input_pin('NewPhysicsAsset').is_valid():val(pin(n,'NewPhysicsAsset'),phys.get_path_name())
  compile_bp(bp);save(bp)
 backup=os.path.join(S,'Backups/CityCombatPlacement',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'Surface/Lvl_SurfaceArrival.umap'),backup)
 assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 old={a.get_actor_label():a for a in sub.get_all_level_actors()}
 R['enemies']=[]
 placements=[('Carbine',-250,25800,270),('Shotgun',320,26800,270),('Plasma',-330,28250,270),('Carbine',360,29600,270),('Shotgun',-280,31500,270),('Plasma',320,33100,270)]
 for i,(role,x,y,yaw) in enumerate(placements):
  label='CITY_Enceladus_%02d_%s'%(i,role)
  a=old.get(label) or sub.spawn_actor_from_class(B.generated_class(A.load_asset(ROOT+'/BP_Enceladus_'+role)),V(x,y,132),unreal.Rotator(pitch=0,yaw=yaw,roll=0))
  a.set_actor_label(label);a.set_folder_path('SURFACE/City Combat');R['enemies'].append({'label':label,'role':role,'position':str(a.get_actor_location())})
 for i,(x,y,yaw) in enumerate([(-580,26000,0),(580,27400,0),(-590,29100,0),(580,31000,0),(-580,32700,0)]):
  label='CITY_DestructibleCover_%02d'%i;a=old.get(label) or sub.spawn_actor_from_class(B.generated_class(A.load_asset(FX+'/BP_ProtocolDestructible')),V(x,y,75),unreal.Rotator(pitch=0,yaw=yaw,roll=0));a.set_actor_label(label);a.set_folder_path('SURFACE/City Combat')
 nav=old.get('CITY_CombatNavBounds') or sub.spawn_actor_from_class(unreal.NavMeshBoundsVolume,V(0,29000,500),unreal.Rotator(pitch=0,yaw=0,roll=0))
 nav.set_actor_label('CITY_CombatNavBounds');nav.set_actor_scale3d(V(50,60,15));nav.set_folder_path('SURFACE/City Combat')
 origin,extent=nav.get_actor_bounds(False);R['nav_bounds']={'origin':str(origin),'extent':str(extent)}
 assert extent.x>1000 and extent.y>1000,'Navigation bounds have no volume'
 assert unreal.EditorLoadingAndSavingUtils.save_current_level()
 unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(V(0,24900,245),unreal.Rotator(pitch=-3,yaw=90,roll=0))
 R.update(saved=True,backup=backup,level='/Game/Surface/Lvl_SurfaceArrival',count=6,covers=5)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
finally:json.dump(R,open(os.path.join(S,'citycombat_placement.json'),'w'),indent=2)
if not R['saved']:raise RuntimeError('City combat placement incomplete')
