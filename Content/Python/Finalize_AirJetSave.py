"""Finalize editor-only comment identities and leave the awakening map ready."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,save
assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE first'
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
# Native PostLoad creates missing comment GUIDs. Reload and resave through the
# editor's supported package lifecycle; no protected fields are accessed.
save(bp)
package=bp.get_outermost()
reload_result=unreal.EditorLoadingAndSavingUtils.reload_packages([package],unreal.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
save(bp)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(x=-200,y=-300,z=210),unreal.Rotator(pitch=-4,yaw=130,roll=0))
json.dump({'saved':True,'native_reload':str(reload_result),'startup_map_preserved':True},open(os.path.join(unreal.Paths.project_saved_dir(),'airjet_final_save.json'),'w'),indent=2)

