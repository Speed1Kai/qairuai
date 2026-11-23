"""Discard unsaved grass placement and reopen the original awakening laboratory.
Never replace a map file or modify existing actors, player, lighting or materials.
"""
import unreal,os,json,hashlib
A=unreal.EditorAssetLibrary
assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE first'
S=os.path.abspath(unreal.Paths.project_saved_dir());C=os.path.abspath(unreal.Paths.project_content_dir())
def digest(p):
 with open(p,'rb') as f:return hashlib.sha256(f.read()).hexdigest()
city=os.path.join(C,'Surface/Lvl_SurfaceArrival.umap');before=os.path.join(S,'Backups/CityGrass/20261027_161145/Lvl_SurfaceArrival.umap')
report={'city_map_unchanged_since_grass_request':digest(city)==digest(before),'lab_hash':digest(os.path.join(C,'Lvl_LabTutorial.umap'))}
# Native map load discards the failed attempt's transient probe actors; no save.
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert editor.get_editor_world().get_name()=='Lvl_LabTutorial'
editor.set_level_viewport_camera_info(unreal.Vector(x=-200,y=-300,z=210),unreal.Rotator(pitch=-4,yaw=130,roll=0))
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report['map']='Lvl_LabTutorial';report['player_starts']=[str(a.get_actor_location()) for a in actors if isinstance(a,unreal.PlayerStart)]
report['grass_actors']=[a.get_actor_label() for a in actors if 'Grass' in a.get_class().get_name()]
report['direct_city_block_actors']=[a.get_actor_label() for a in actors if a.get_class().get_name()=='BP_FirstCityBlock_C']
report['capsule_actors']=[dict(label=a.get_actor_label(),cls=a.get_class().get_name()) for a in actors if any(t in (a.get_actor_label()+' '+a.get_class().get_name()).lower() for t in ('capsule','awak','cryopod','stasis'))]
assets=A.list_assets('/Game/Environment/CityGrass',recursive=True,include_folder=False)
report['external_grass_references']={}
for asset in assets:
 refs=[str(p) for p in A.find_package_referencers_for_asset(asset,False) if not str(p).startswith('/Game/Environment/CityGrass/')]
 if refs:report['external_grass_references'][str(asset)]=refs
report['restored']=not report['grass_actors'] and not report['direct_city_block_actors']
json.dump(report,open(os.path.join(S,'lab_restored_after_grass.json'),'w'),indent=2)
assert report['restored']
unreal.log('LABORATORY RESTORED '+str(report))
