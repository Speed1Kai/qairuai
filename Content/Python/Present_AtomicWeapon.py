import unreal,os,json
S=unreal.Paths.project_saved_dir()
assert not unreal.EditorLevelLibrary.get_game_world()
reports={n:json.load(open(os.path.join(S,n))) for n in ('atomic_weapon_build.json','atomic_weapon_pie.json','atomic_switching_check.json','atomic_view_polish.json')}
assert all(reports[n].get('passed') for n in ('atomic_weapon_pie.json','atomic_switching_check.json'))
assert reports['atomic_weapon_build.json']['saved'] and reports['atomic_view_polish.json']['saved']
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(3970,-100,2335),unreal.Rotator(pitch=-4,yaw=0))
json.dump({'complete':True,'runtime_checks':reports['atomic_weapon_pie.json']['checks'],'switching_checks':reports['atomic_switching_check.json']['checks'],'observed_gpu_mib':2280,'gpu_total_mib':6141,'scope':'lab PIE sample only','controls':{'mode':'3','fire':'LMB','camera':'V'}},open(os.path.join(S,'atomic_weapon_delivery.json'),'w'),indent=2)
