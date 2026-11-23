import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');e=G.get_graph_editor_by_name(bp,'EventGraph')
r={'members':list(map(str,B.list_member_variable_names(bp))),'graphs':list(map(str,B.list_graph_names(bp))),'events':[x for x in e.list_available_nodes([]) if any(t in x for t in ('PointDamage','Урон в точке','ReceivePoint'))],'visibility':[],'apis':{}}
for n in e.list_all_nodes():
 p=n.find_input_pin('InVisibility')
 if p.is_valid():r['visibility'].append({'name':n.get_name(),'value':str(p.get_pin_value()),'title':str(n.get_node_title())})
for cl,names in [(unreal.RenderingLibrary,['render_target_create_static_texture2d_editor_only','create_render_target2d']),(unreal.SceneCaptureComponent2D,['show_only_actor_components','capture_scene']),(unreal.SkeletalMeshComponent,['set_leader_pose_component','set_position']),(unreal.MathLibrary,['smooth_step'])]:
 for name in names:r['apis'][cl.__name__+'.'+name]=getattr(cl,name).__doc__ if hasattr(cl,name) else None
with open(os.path.join(unreal.Paths.project_saved_dir(),'visor_upgrade_inspection.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
