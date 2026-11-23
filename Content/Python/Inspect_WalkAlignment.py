import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components
r={};w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0)
if p:
 m=p.mesh;pc=unreal.GameplayStatics.get_player_controller(w,0);cm=p.get_component_by_class(unreal.CharacterMovementComponent)
 r.update(actor=str(p.get_actor_transform()),velocity=str(p.get_velocity()),control=str(pc.get_control_rotation()),mesh_relative=str(m.get_relative_transform()),anim=str(m.get_anim_instance()))
 r['bones']={str(n):str(m.get_socket_location(n)) for n in ['CC_Base_Hip','CC_Base_Head','CC_Base_L_Upperarm','CC_Base_R_Upperarm','CC_Base_L_Foot','CC_Base_R_Foot','CC_Base_L_ToeBase','CC_Base_R_ToeBase']}
 r['movement']={n:str(cm.get_editor_property(n)) for n in ['orient_rotation_to_movement','use_controller_desired_rotation','rotation_rate']}
 r['flags']={}
 for n in ['bFirstPerson','FirstPersonBodyYawCorrection','use_controller_rotation_yaw','use_controller_rotation_pitch','use_controller_rotation_roll']:
  try:r['flags'][n]=str(p.get_editor_property(n))
  except:pass
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');r['rotations']=[]
for gn in B.list_graph_names(bp):
 for n in G.get_graph_editor_by_name(bp,gn).list_all_nodes():
  if any(s in str(n.get_node_title()).replace(' ','').lower() for s in ['rotation','rotator','поворот']):
   r['rotations'].append({'graph':str(gn),'node':str(n.get_node_title()),'pins':[{ 'name':str(q.get_pin_name()),'value':q.get_pin_value(),'links':[str(x.get_owning_node().get_node_title())+'.'+str(x.get_pin_name()) for x in q.list_connected_pins()]} for q in n.list_input_pins()]})
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'walk_alignment_inspect.json'),'w'),indent=2)
