"""Make real weapon rays hit living capsules; preserve movement/camera channels."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
R={}
for path in ['/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter']+[ROOT+'/'+n for n in ('BP_CityEnceladus','BP_Enceladus_Carbine','BP_Enceladus_Shotgun','BP_Enceladus_Plasma')]:
 bp=A.load_asset(path);cd=unreal.get_default_object(B.generated_class(bp));cap=next(c for h,c,n in components(bp) if n=='CapsuleComponent');cap.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY,cap.get_collision_response_to_channel(unreal.CollisionChannel.ECC_WORLD_STATIC));g=Graph(bp,'Combat_InitCollision');g.do(g.call('Engine.PrimitiveComponent.SetCollisionResponseToChannel',target=g.get('CapsuleComponent'),Channel='ECC_Visibility',NewResponse='ECR_Block'));compile_bp(bp)
 e=G.get_graph_editor_by_name(bp,'EventGraph')
 if not any(n.get_name()=='CombatInitCollision' for n in e.list_all_nodes()):hook(bp,e.find_event_node('ReceiveBeginPlay').find_then_pin(),'Combat_InitCollision','CombatInitCollision')
 compile_bp(bp);save(bp)
 R[path]=str(cap.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'combat_collision.json'),'w'),indent=2)





