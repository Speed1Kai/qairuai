import unreal,os,json
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0)
p.get_editor_property('AtomicFPArms').set_relative_location(unreal.Vector(18,-5,-174),False,False)
p.get_editor_property('AtomicFPGun').set_relative_location(unreal.Vector(50,17,-14),False,False)
p.get_editor_property('AtomicFPGun').set_relative_scale3d(unreal.Vector(.56,.56,.56))
p.get_editor_property('AtomicFPMuzzle').set_relative_location(unreal.Vector(88,17,-12),False,False)
seq=unreal.load_asset('/Game/Combat/AtomicWeapon/Animations/Atomic_MF_Rifle_Idle_ADS');R={'controller':seq.controller.set_bone_track_keys.__doc__}
pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,unreal.AnimPoseEvaluationOptions())
R['fingers']={n:str(unreal.AnimPoseExtensions.get_bone_pose(pose,n,unreal.AnimPoseSpaces.LOCAL)) for n in ('CC_Base_L_Index1','CC_Base_L_Index2','CC_Base_L_Index3','CC_Base_R_Index1','CC_Base_R_Index2','CC_Base_L_Mid2','CC_Base_R_Mid2')}
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'atomic_grip_api.json'),'w'),indent=2)
