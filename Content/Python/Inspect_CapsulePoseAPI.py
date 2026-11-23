import unreal, os, json
idle=unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle')
mesh=unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')
options=unreal.AnimPoseEvaluationOptions()
options.set_editor_property('optional_skeletal_mesh',mesh)
pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(idle,0.0,options)
names=unreal.AnimPoseExtensions.get_bone_names(pose)
result={'bones':{},'skeleton':str(mesh.get_editor_property('skeleton')),
        'set_pose_doc':unreal.AnimPoseExtensions.set_bone_pose.__doc__}
for name in names:
    if str(name) in ('root','pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','head',
        'thigh_l','calf_l','foot_l','ball_l','thigh_r','calf_r','foot_r','ball_r',
        'upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r'):
        t=unreal.AnimPoseExtensions.get_bone_pose(pose,name,unreal.AnimPoseSpaces.WORLD)
        p=t.translation
        result['bones'][str(name)]=dict(position=[p.x,p.y,p.z],rotation=str(t.rotation))
controller=idle.get_editor_property('controller')
result['controller']=str(controller)
result['set_keys_doc']=controller.set_bone_track_keys.__doc__
result['names']=[str(n) for n in names]
with open(os.path.join(unreal.Paths.project_saved_dir(),'capsule_pose_api.json'),'w') as f:json.dump(result,f,indent=2)
