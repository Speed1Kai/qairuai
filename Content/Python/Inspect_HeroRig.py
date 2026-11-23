import unreal,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
a=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,5000),unreal.Rotator())
c=a.skeletal_mesh_component;c.set_skeletal_mesh_asset(unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'));c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
r={}
for name in ('head','neck_01','spine_03','spine_05','pelvis','upperarm_l','lowerarm_l','hand_l','thigh_l','calf_l','foot_l','upperarm_r','lowerarm_r','thigh_r','calf_r'):
 t=c.get_socket_transform(name,unreal.RelativeTransformSpace.RTS_COMPONENT);p=t.translation;q=t.rotation.rotator();r[name]={'p':[p.x,p.y,p.z],'r':[q.pitch,q.yaw,q.roll]}
with open('S:/Final_Protocol/Saved/hero_rig_reference.json','w') as f:json.dump(r,f,indent=2)
