"""Unload unused assets from the cancelled grass attempt before archiving files."""
import unreal,os,json
A=unreal.EditorAssetLibrary
assert not unreal.EditorLevelLibrary.get_game_world()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();assert world.get_name()=='Lvl_LabTutorial'
assets=A.list_assets('/Game/Environment/CityGrass',True,False)
packages=[]
for path in assets:
 refs=[str(p) for p in A.find_package_referencers_for_asset(path,False) if not str(p).startswith('/Game/Environment/CityGrass/')]
 assert not refs,(path,refs)
 asset=A.load_asset(path)
 if asset and asset.get_name()=='BP_CityGrassPatches':
  assert unreal.BlueprintEditorLibrary.compile_blueprint(asset)
  assert A.save_loaded_asset(asset,only_if_is_dirty=False)
 if asset and asset.get_outermost() not in packages:packages.append(asset.get_outermost())
result=unreal.EditorLoadingAndSavingUtils.unload_packages(packages)
json.dump({'result':str(result),'assets':list(map(str,assets))},open(os.path.join(unreal.Paths.project_saved_dir(),'grass_rollback_unload.json'),'w'),indent=2)
