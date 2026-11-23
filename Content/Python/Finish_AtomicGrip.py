"""Trim hidden shoulder geometry and author a closed, two-hand mechanical grip."""
import unreal,os,sys,json,math
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
assert not unreal.EditorLevelLibrary.get_game_world()
D='/Game/Combat/AtomicWeapon';seq=A.load_asset(D+'/Animations/Atomic_MF_Rifle_Idle_ADS');ctrl=seq.controller
pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,unreal.AnimPoseEvaluationOptions())
def bone(n,world=False):return unreal.AnimPoseExtensions.get_bone_pose(pose,n,unreal.AnimPoseSpaces.WORLD if world else unreal.AnimPoseSpaces.LOCAL)
def mul(a,b):return unreal.Quat(x=a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,y=a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,z=a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,w=a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z)
def inv(a):return unreal.Quat(x=-a.x,y=-a.y,z=-a.z,w=a.w)
def norm(v):return v/v.length()
def between(a,b):
 a=norm(a);b=norm(b);c=a.cross(b);w=1+a.dot(b);l=math.sqrt(c.dot(c)+w*w);return unreal.Quat(x=c.x/l,y=c.y/l,z=c.z/l,w=w/l)
def put(n,q):
 t=bone(n);assert ctrl.set_bone_track_keys(n,[t.translation],[q],[t.scale3d],False),n
# A small analytic IK adjustment brings the support hand under the fore-end.
sn='CC_Base_L_Upperarm';en='CC_Base_L_Forearm';hn='CC_Base_L_Hand';s=bone(sn,True);e=bone(en,True);h=bone(hn,True);target=h.translation+V(-12,0,-6)
u=norm(target-s.translation);d=(target-s.translation).length();l1=(e.translation-s.translation).length();l2=(h.translation-e.translation).length();d=min(d,l1+l2-.1)
bend=norm((e.translation-s.translation)-u*(e.translation-s.translation).dot(u));a=(l1*l1-l2*l2+d*d)/(2*d);new_e=s.translation+u*a+bend*math.sqrt(max(.1,l1*l1-a*a))
q1=mul(between(e.translation-s.translation,new_e-s.translation),s.rotation);q2=mul(between(h.translation-e.translation,target-new_e),e.rotation)
parent=A.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel');parentname='CC_Base_L_Clavicle';put(sn,mul(inv(bone(parentname,True).rotation),q1));put(en,mul(inv(q1),q2));put(hn,mul(inv(q2),h.rotation))
for side,sign in [('L',1),('R',-1)]:
 for finger in ('Index','Mid','Ring','Pinky'):
  for joint,angle in [(1,22),(2,32),(3,23)]:
   name='CC_Base_'+side+'_'+finger+str(joint);put(name,mul(bone(name).rotation,unreal.Rotator(yaw=angle*sign).quaternion()))
 for joint,angle in [(1,25),(2,30),(3,20)]:
  name='CC_Base_'+side+'_Thumb'+str(joint);put(name,mul(bone(name).rotation,unreal.Rotator(yaw=angle*sign).quaternion()))
save(seq)
dm=unreal.DynamicMesh();unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(parent,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
for box in [unreal.Box(min=V(-38,-100,-10),max=V(38,100,250)),unreal.Box(min=V(-200,-100,-20),max=V(200,100,115))]:
 _,sel=unreal.GeometryScript_MeshSelection.select_mesh_elements_in_box(dm,box,min_num_triangle_points=1);unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dm,sel)
arms=A.load_asset(D+'/SK_SentinelArms');unreal.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dm,arms,unreal.GeometryScriptCopyMeshToAssetOptions(),unreal.GeometryScriptMeshWriteLOD());save(arms)
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
for h,c,n in components(bp):
 if n=='AtomicFPArms':c.set_editor_property('relative_location',V(18,-5,-174))
 elif n=='AtomicFPGun':c.set_editor_property('relative_location',V(50,17,-14));c.set_editor_property('relative_scale3d',V(.56,.56,.56))
 elif n=='AtomicFPMuzzle':c.set_editor_property('relative_location',V(88,17,-12))
compile_bp(bp);save(bp)
json.dump({'saved':True,'grip':'robot fingers closed; support-arm IK','fp_mesh':'forearms only'},open(os.path.join(unreal.Paths.project_saved_dir(),'atomic_grip_finish.json'),'w'),indent=2)
