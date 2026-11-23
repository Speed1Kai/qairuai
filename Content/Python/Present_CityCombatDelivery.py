import unreal,os,json,hashlib
assert not unreal.EditorLevelLibrary.get_game_world()
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert e.get_editor_world().get_name()=='Lvl_LabTutorial'
e.set_level_viewport_camera_info(unreal.Vector(x=-200,y=-300,z=210),unreal.Rotator(pitch=-4,yaw=130,roll=0))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
with open(os.path.join(unreal.Paths.project_content_dir(),'Lvl_LabTutorial.umap'),'rb') as f:sha=hashlib.sha256(f.read()).hexdigest()
assert sha=='18fa88868e98ae4252e60c9d99b8fa8b85372d9695f694d850ae299fec0058ea'
s=unreal.Paths.project_saved_dir();reports={n:json.load(open(os.path.join(s,n))) for n in ('citycombat_pie.json','citycombat_final_validation.json','citycombat_main_game.json','citycombat_connected_placement.json')}
assert all(r.get('passed',r.get('saved',False)) for r in reports.values())
json.dump({'complete':True,'editor_map':'Lvl_LabTutorial','laboratory_sha256':sha,'pie_checks':reports['citycombat_pie.json']['checks'],'full_game_checks':reports['citycombat_main_game.json']['checks'],'saved_assets_valid':reports['citycombat_final_validation.json']['passed']},open(os.path.join(s,'citycombat_delivery.json'),'w'),indent=2)
