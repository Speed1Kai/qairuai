import unreal,os,sys,json,math,runpy
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
assert not unreal.EditorLevelLibrary.get_game_world()
D='/Game/Combat/AtomicWeapon';path=D+'/Animations/Atomic_FPGrip'
seq=A.load_asset(path) if A.does_asset_exist(path) else A.duplicate_asset(D+'/Animations/Atomic_MF_Rifle_Idle_ADS',path)
pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,unreal.AnimPoseEvaluationOptions());ctrl=seq.controller
def bone(n,w=False):return unreal.AnimPoseExtensions.get_bone_pose(pose,n,unreal.AnimPoseSpaces.WORLD if w else unreal.AnimPoseSpaces.LOCAL)
def norm(v):return v/v.length()
def mul(a,b):return unreal.Quat(x=a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,y=a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,z=a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,w=a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z)
def inv(a):return unreal.Quat(x=-a.x,y=-a.y,z=-a.z,w=a.w)
def between(a,b):
 a=norm(a);b=norm(b);c=a.cross(b);w=1+a.dot(b);l=math.sqrt(c.dot(c)+w*w);return unreal.Quat(x=c.x/l,y=c.y/l,z=c.z/l,w=w/l)
if A.get_metadata_tag(seq,'AtomicViewPose')!='2':
 for side,sign in [('L',1),('R',-1)]:
  sn='CC_Base_'+side+'_Upperarm';en='CC_Base_'+side+'_Forearm';hn='CC_Base_'+side+'_Hand';parent=bone('CC_Base_'+side+'_Clavicle',True);s=bone(sn,True);e=bone(en,True);h=bone(hn,True)
  new_s=s.translation+V(0,-22,-22);target=h.translation;u=norm(target-new_s);d=(target-new_s).length();l1=(e.translation-s.translation).length();l2=(h.translation-e.translation).length();d=min(d,l1+l2-.1)
  pole=V(sign*35,-15,-65);bend=norm(pole-u*pole.dot(u));a=(l1*l1-l2*l2+d*d)/(2*d);new_e=new_s+u*a+bend*math.sqrt(max(.1,l1*l1-a*a))
  q1=mul(between(e.translation-s.translation,new_e-new_s),s.rotation);q2=mul(between(h.translation-e.translation,target-new_e),e.rotation)
  for name,q,pos in [(sn,mul(inv(parent.rotation),q1),unreal.MathLibrary.inverse_transform_location(parent,new_s)),(en,mul(inv(q1),q2),bone(en).translation),(hn,mul(inv(q2),h.rotation),bone(hn).translation)]:
   t=bone(name);assert ctrl.set_bone_track_keys(name,[pos],[q],[t.scale3d],False)
 A.set_metadata_tag(seq,'AtomicViewPose','2');save(seq)
target=A.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel');dm=unreal.DynamicMesh();unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(target,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
for box in [unreal.Box(min=V(-21,-100,-10),max=V(21,100,250)),unreal.Box(min=V(-200,-100,-20),max=V(200,100,115))]:
 _,sel=unreal.GeometryScript_MeshSelection.select_mesh_elements_in_box(dm,box,min_num_triangle_points=1);unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dm,sel)
arms=A.load_asset(D+'/SK_SentinelArms');unreal.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dm,arms,unreal.GeometryScriptCopyMeshToAssetOptions(),unreal.GeometryScriptMeshWriteLOD());save(arms)
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
for n in G.get_graph_editor_by_name(bp,'Atomic_Equip').list_all_nodes():
 p=n.find_input_pin('NewAnimToPlay')
 if p.is_valid():val(p,path)
compile_bp(bp);save(bp)
json.dump({'saved':True,'fp_pose':path},open(os.path.join(unreal.Paths.project_saved_dir(),'atomic_view_polish.json'),'w'),indent=2)
