"""Finish the verified change and restore the user's main level."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,compile_bp,save
assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE first'
S=os.path.abspath(unreal.Paths.project_saved_dir())
reports={n:json.load(open(os.path.join(S,n))) for n in ('pneumatic_regression.json','pneumatic_physical_keys.json','pneumatic_saved_verified.json')}
assert all(r['passed'] for r in reports.values()),'Verification must pass'
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');compile_bp(bp);save(bp)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(x=-200,y=-300,z=210),unreal.Rotator(pitch=-4,yaw=130,roll=0))
r=json.load(open(os.path.join(S,'pneumatic_authoring.json')));r.update(gameplay_tested=True,physical_keys_tested=True,saved_verified=True,main_map_restored=True,checks={n:len(v['checks']) for n,v in reports.items()})
json.dump(r,open(os.path.join(S,'pneumatic_authoring.json'),'w'),indent=2)
unreal.log('PNEUMATIC COMPLETE: '+str(r))
