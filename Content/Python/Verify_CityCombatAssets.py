"""Read saved packages in a fresh editor process; never save or modify the level."""
import unreal,sys,os,json,hashlib,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
R={'passed':False,'blueprints':{},'checks':{}}
try:
 for path in [ROOT+'/'+n for n in ('BP_CityEnceladus','BP_Enceladus_Carbine','BP_Enceladus_Shotgun','BP_Enceladus_Plasma')]+[FX+'/'+n for n in ('BP_EnemyTracer','BP_ProtocolTracer','BP_ProtocolBlast','BP_ProtocolDestructible')]+['/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter']:
  bp=A.load_asset(path);assert bp,path;compile_bp(bp);R['blueprints'][path]=True
 player=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');names=list(map(str,B.list_graph_names(player)));R['player_functions']=names
 R['checks']['cannon_present']='Protocol_Fire' in names and 'Protocol_Update' in names
 R['checks']['pneumatic_movement_preserved']=any('Pneumatic' in n or 'AirJet' in n for n in names)
 sk=A.load_asset(ROOT+'/SK_Enceladus');R['checks']['rigged_mesh_and_physics']=bool(sk and sk.physics_asset and sk.skeleton)
 R['checks']['eight_pbr_slots']=len(sk.materials)==8
 with open(os.path.join(unreal.Paths.project_content_dir(),'Lvl_LabTutorial.umap'),'rb') as f:R['lab_sha256']=hashlib.sha256(f.read()).hexdigest()
 R['checks']['original_laboratory_unchanged']=R['lab_sha256']=='18fa88868e98ae4252e60c9d99b8fa8b85372d9695f694d850ae299fec0058ea'
 live=json.load(open(os.path.join(unreal.Paths.project_saved_dir(),'citycombat_pie.json')));R['runtime_checks']=live['checks'];R['checks']['real_pie_combat_passed']=live['passed']
 assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
 actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
 R['checks']['six_persistent_city_npcs']=sum(a.get_class().get_name().startswith('BP_Enceladus_') for a in actors)==6
 R['checks']['five_reactive_covers']=sum(a.get_class().get_name()=='BP_ProtocolDestructible_C' for a in actors)==5
 R['passed']=all(R['checks'].values())
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'citycombat_final_validation.json'),'w'),indent=2)
assert R['passed'],R
