"""Check persisted campus bridge removal and collision across both gate leaves."""
import unreal,os,json,traceback
O=(10006.289955343997,6612.598659341473,2150.)
def V(p):return unreal.Vector(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def L(p):return V(tuple(p[i]-O[i] for i in range(3)))
r={'passed':False}
try:
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors=sub.get_all_level_actors()
    a=next(a for a in actors if a.get_class().get_name()=='BP_ReferenceCampus_C')
    bridge={c.get_name():c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent) if any(k in c.get_name() for k in ('SM_BridgeCampusHalf','SM_BridgeCityHalf','FallenSpan'))}
    assert bridge and all(n==0 for n in bridge.values()),str(bridge)
    r['bridge_instances']=bridge
    gates=[a for a in actors if a.get_class().get_name()=='BP_ReferenceSteelGate_C'];assert len(gates)==1
    r['gate_traces']=[]
    for x in (5400,5850,6300):
        hit=unreal.SystemLibrary.line_trace_single(w,L((x,17000,2450)),L((x,17800,2450)),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,False)
        s=hit.export_text();r['gate_traces'].append(s);assert 'bBlockingHit=True' in s,s
    hit=unreal.SystemLibrary.line_trace_single(w,L((5850,20000,2500)),L((5850,20000,2000)),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,False)
    r['restored_ground_trace']=hit.export_text();assert 'bBlockingHit=True' in r['restored_ground_trace']
    r['passed']=True
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
    json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'steel_checkpoint_checks.json'),'w'),indent=2)
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(V((5650,1200,2390)),unreal.Rotator(pitch=-6,yaw=90))
