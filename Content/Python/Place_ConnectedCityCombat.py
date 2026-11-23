"""Place combat in the actual connected campus using its city actor transform."""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
R={'saved':False};S=os.path.abspath(unreal.Paths.project_saved_dir())
try:
 assert not unreal.EditorLevelLibrary.get_game_world()
 path='/Game/Surface/Lvl_CampusConnected';src=os.path.join(unreal.Paths.project_content_dir(),'Surface/Lvl_CampusConnected.umap')
 backup=os.path.join(S,'Backups/ConnectedCityCombat',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);shutil.copy2(src,backup)
 assert unreal.EditorLoadingAndSavingUtils.load_map(path)
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);old={a.get_actor_label():a for a in sub.get_all_level_actors()}
 city=old['CITY_FirstDowntownBlock'];frame=city.get_actor_transform();R['city_frame']=str(frame)
 def loc(x,y,z):return unreal.MathLibrary.transform_location(frame,V(x,y,z))
 R['positions']=[]
 for i,(role,x,y) in enumerate([('Carbine',-250,25800),('Shotgun',320,26800),('Plasma',-330,28250),('Carbine',360,29600),('Shotgun',-280,31500),('Plasma',320,33100)]):
  label='CITY_Enceladus_%02d_%s'%(i,role);a=old.get(label) or sub.spawn_actor_from_class(B.generated_class(A.load_asset(ROOT+'/BP_Enceladus_'+role)),loc(x,y,132),unreal.Rotator(pitch=0,yaw=270,roll=0));a.set_actor_label(label);a.set_folder_path('SURFACE/City Combat');R['positions'].append(str(a.get_actor_location()))
 for i,(x,y) in enumerate([(-580,26000),(580,27400),(-590,29100),(580,31000),(-580,32700)]):
  label='CITY_DestructibleCover_%02d'%i;a=old.get(label) or sub.spawn_actor_from_class(B.generated_class(A.load_asset(FX+'/BP_ProtocolDestructible')),loc(x,y,75),unreal.Rotator());a.set_actor_label(label);a.set_folder_path('SURFACE/City Combat')
 nav=old.get('CITY_CombatNavBounds') or sub.spawn_actor_from_class(unreal.NavMeshBoundsVolume,loc(0,29000,500),unreal.Rotator());nav.set_actor_label('CITY_CombatNavBounds');nav.set_actor_scale3d(V(50,60,15));nav.set_folder_path('SURFACE/City Combat')
 unreal.SystemLibrary.execute_console_command(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),'RebuildNavigation')
 assert unreal.EditorLoadingAndSavingUtils.save_current_level();R.update(saved=True,backup=backup,map=path)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
json.dump(R,open(os.path.join(S,'citycombat_connected_placement.json'),'w'),indent=2)
assert R['saved'],R
