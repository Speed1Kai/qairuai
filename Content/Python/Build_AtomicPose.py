import unreal,os,sys,json,traceback,shutil,datetime
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
D='/Game/Combat/AtomicWeapon';S=unreal.Paths.project_saved_dir();R={}
try:
 src='/Game/Characters/BlackSentinel/Animations/BS_ABP_PlayerGuard';path=D+'/ABP_AtomicBody'
 bp=A.load_asset(path) if A.does_asset_exist(path) else A.duplicate_asset(src,path)
 unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([D],True)
 rifle=A.load_asset(D+'/Animations/Atomic_MF_Rifle_Idle_ADS')
 player=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 var(bp,'AtomicAimWeight','real','0');compile_bp(bp)
 e=G.get_graph_editor_by_name(bp,'AnimGraph');menus=list(map(str,e.list_available_nodes([])))
 seq=next((n for n in e.list_all_nodes() if n.get_name()=='AtomicRiflePose'),None)
 if not seq:
  seq=e.create_node_from_name(next(m for m in menus if m.endswith("Воспроизвести'Atomic_MF_Rifle_Idle_ADS'")),unreal.Vector2D(x=800,y=800),[]);seq.rename('AtomicRiflePose')
 layer=next((n for n in e.list_all_nodes() if n.get_name()=='AtomicUpperBody'),None)
 if not layer:
  layer=e.create_node_from_name('Animation|Blends|Послойноесмешиваниенакаждуюкость',unreal.Vector2D(x=1100,y=300),[]);layer.rename('AtomicUpperBody')
 filt=unreal.BranchFilter();filt.set_editor_property('bone_name','CC_Base_Spine01');filt.set_editor_property('blend_depth',1)
 config=unreal.InputBlendPose();config.set_editor_property('branch_filters',[filt])
 node=layer.get_editor_property('node');node.set_editor_property('layer_setup',[config]);node.set_editor_property('mesh_space_rotation_blend',True);node.set_editor_property('blend_weights',[0.]);layer.set_editor_property('node',node)
 R['layer_pins']=[str(p.get_pin_name()) for p in layer.list_all_pins()];R['seq_pins']=[str(p.get_pin_name()) for p in seq.list_all_pins()]
 root=next(n for n in e.list_all_nodes() if n.get_class().get_name()=='AnimGraphNode_Root');rp=pin(root,'Result')
 prev=list(rp.list_connected_pins())
 if prev and prev[0].get_owning_node()!=layer:
  rp.break_pin_links();link(prev[0],pin(layer,'BasePose'))
 link(pin(seq,'Pose',True),pin(layer,'BlendPoses_0'));link(pin(layer,'Pose',True),rp)
 # This class is installed only while the atomic weapon is equipped.
 val(pin(layer,'BlendWeights_0'),1.)
 compile_bp(bp);save(bp);R['saved']=True
except Exception:R['error']=traceback.format_exc()
json.dump(R,open(os.path.join(S,'atomic_pose_build.json'),'w'),indent=2)
