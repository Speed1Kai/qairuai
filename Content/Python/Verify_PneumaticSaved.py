"""Independent read-only validation of the saved production Blueprint."""
import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');ev=G.get_graph_editor_by_name(bp,'EventGraph')
cs={n:c for h,c,n in components(bp)};names=set(map(str,B.list_graph_names(bp)))
checks={}
checks['production_player']=bp.get_name()=='BP_ThirdPersonCharacter'
checks['no_graph_errors']=not any(G.get_graph_editor_by_name(bp,n).list_nodes_with_errors() for n in names)
checks['new_functions_saved']=all(n in names for n in ('Pneumatic_Update','Pneumatic_Orbs','Pneumatic_StartDash','Pneumatic_StopDash','Pneumatic_InputPressed','Pneumatic_InputReleased','Pneumatic_InputCanceled'))
checks['existing_systems_preserved']=all(n in names for n in ('AirJet_Update','AirJet_Landed','AirJet_Stop'))
checks['exactly_two_helpers']=len([n for n in cs if n.startswith('AssistOrb')])==2
checks['separate_actor_class']=all(cs['AssistOrb'+side].get_editor_property('child_actor_class').get_name()=='BP_PneumaticOrb_C' for side in ('Left','Right'))
checks['cylinder_meshes_removed']=all(cs['AirJetNozzle'+side].static_mesh is None for side in ('Left','Right'))
checks['tap_hold_event_routes']=all(len(n.find_execute_pin().list_connected_pins())==1 for n in ev.list_all_nodes() if n.get_name() in ('PneumaticStarted','PneumaticCompleted','PneumaticCanceled'))
checks['tick_precedes_air']=any(p.get_owning_node().get_name()=='AirJetRuntimeTick' for n in ev.list_all_nodes() if n.get_name()=='PneumaticRuntimeTick' for p in n.find_then_pin().list_connected_pins())
cdo=unreal.get_default_object(B.generated_class(bp))
checks['four_second_air_budget']=abs(cdo.get_editor_property('AirJetCapacity')-4)<.001
checks['dash_config']=abs(cdo.get_editor_property('PneumaticDashDuration')-.24)<.001 and abs(cdo.get_editor_property('PneumaticDashSpeed')-1600)<.01
orb=A.load_asset('/Game/Characters/AirJet/BP_PneumaticOrb');oc={n:c for h,c,n in components(orb)};sphere=oc['MetallicSphere']
checks['metal_spheres']=sphere.static_mesh.get_name()=='Sphere' and sphere.get_material(0).get_name()=='M_PneumaticOrb'
checks['helpers_no_collision']=sphere.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION
R={'passed':all(checks.values()),'checks':checks}
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'pneumatic_saved_verified.json'),'w'),indent=2)
unreal.log('PNEUMATIC SAVED VERIFICATION '+str(R))
assert R['passed']
