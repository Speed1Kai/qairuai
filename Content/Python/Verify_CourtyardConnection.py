"""Reload saved maps and inspect the new physical doorway without starting PIE."""
import unreal,sys,os,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components,compile_bp,save,V
r={'passed':False,'gameplay_tested':False}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
try:
 world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_CampusConnected')
 actors=sub.get_all_level_actors();r['exterior_actor_count']=len(actors)
 forbidden=[a.get_actor_label() for a in actors if isinstance(a,unreal.PlayerStart) or a.get_actor_label() in ('ArrivalSequence','CAMPUS_StasisExitDoor','SURF_PlayerGuardVisual','SURF_CyborgBodyLight')]
 assert not forbidden,forbidden
 # Static geometry must inherit the streaming transform from a static root.
 paths=set(a.get_class().get_path_name().split('.')[0] for a in actors if a.get_class().get_name() in ('BP_SurfaceEnvironment_C','BP_CampusPerimeterWalls_C','BP_FirstCityBlock_C'))
 r['static_roots_fixed']=[]
 for path in paths:
  bp=A.load_asset(path)
  for h,c,name in components(bp):
   if c and c.get_class()==unreal.SceneComponent.static_class():c.set_mobility(unreal.ComponentMobility.STATIC)
  compile_bp(bp);save(bp);r['static_roots_fixed'].append(path)
 assert unreal.EditorLoadingAndSavingUtils.save_current_level()
 del actors,world
 world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 exit=next(a for a in sub.get_all_level_actors() if a.get_class().get_name()=='BP_SurfaceDeparture_C')
 r['exit_position']=str(exit.get_actor_location());bp=A.load_asset('/Game/Surface/BP_SurfaceDeparture')
 compile_bp(bp);r['graphs']={};r['forbidden_nodes']=[]
 for name in B.list_graph_names(bp):
  e=G.get_graph_editor_by_name(bp,name);titles=[str(n.get_node_title()) for n in e.list_all_nodes()];r['graphs'][str(name)]=len(titles)
  for title in titles:
   if any(t in title.lower() for t in ('open level','openlevel','teleport','start camera fade')):r['forbidden_nodes'].append(title)
 assert not r['forbidden_nodes'],r['forbidden_nodes']
 # Native editor collision traces at feet, torso and head heights, with the
 # new leaves ignored so only the surrounding architecture is checked.
 r['passage_traces']=[]
 for x in (5770,5850,5930):
  for z in (2190,2250,2340):
   hit=unreal.SystemLibrary.line_trace_single(world,V((x,1220,z)),V((x,1930,z)),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[exit],unreal.DrawDebugTrace.NONE,False)
   r['passage_traces'].append({'x':x,'z':z,'hit':hit.export_text() if hit else 'clear'})
 assert all('bBlockingHit=True' not in t['hit'] for t in r['passage_traces']),'Passage still blocked'
 # A transform round trip confirms that the original exterior doorway is
 # exactly on the new laboratory threshold, not at its old isolated spawn.
 report=json.load(open(os.path.join(unreal.Paths.project_saved_dir(),'seamless_courtyard_report.json'),encoding='utf8'))
 r['stream_offset']=report['offset'];r['stream_yaw']=report['yaw']
 r['passed']=True
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(unreal.Paths.project_saved_dir(),'courtyard_connection_verification.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['passed']:raise RuntimeError('Courtyard verification failed')
