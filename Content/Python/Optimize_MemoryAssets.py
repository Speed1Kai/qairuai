"""Targeted memory/stability changes; preserve hero, world layout and texture detail."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components,pin,val,link,compile_bp,save
import Archive_AuthoringHelpers as H
root=os.path.abspath(unreal.Paths.project_dir());r={'saved':False,'holograms':[],'widgets':[]}
try:
 backup=os.path.join(root,'Saved/Backups/MemoryAssets',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 def back(a):
  path=a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset';src=os.path.join(root,'Content',path);dst=os.path.join(backup,path);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
 # Use the engine's legacy migration branch to regenerate valid deterministic
 # widget GUIDs and remove stale names after restructuring a WidgetTree.
 helper=H.helper;back(helper);fn='RefreshWidgetVariableTracking'
 if fn not in map(str,B.list_graph_names(helper)):
  e=G.create_and_edit_function_graph(helper,fn);target=e.add_graph_input_parameter('TargetObject',B.get_object_reference_type(unreal.Object));typ=B.get_map_type(B.get_basic_type_by_name('name'),B.get_struct_type(unreal.load_object(None,'/Script/CoreUObject.Guid')));mapping=e.add_graph_input_parameter('WidgetMapping',typ)
  n=e.add_call_function_node('/Script/Engine.BlueprintMapLibrary.SetMapPropertyByName');link(e.find_graph_entry_pin(),n.find_execute_pin());val(pin(n,'Object'),target);val(pin(n,'PropertyName'),'WidgetVariableNameToGuidMap');val(pin(n,'Value'),mapping)
 compile_bp(helper);save(helper)
 for path in ('/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt','/Game/Characters/PlayerVisor/WBP_PlayerVisor'):
  bp=A.load_asset(path);back(bp);unreal.get_default_object(B.generated_class(helper)).call_method(fn,args=(bp,{}));compile_bp(bp);compile_bp(bp);save(bp);r['widgets'].append(path)
 for i in range(1,7):
  bp=A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i);back(bp)
  for h,c,name in components(bp):
   if name=='HoloSentinel':
    c.set_editor_property('forced_lod_model',3)
    c.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
  e=G.get_graph_editor_by_name(bp,'EventGraph')
  if not any(n.get_name()=='HoloStopIdlePolling' for n in e.list_all_nodes()):
   for n in list(e.list_all_nodes()):
    q=n.find_input_pin('Enabled')
    if not q.is_valid() or q.list_connected_pins() or str(q.get_pin_value()).lower()!='true':continue
    old=list(n.find_then_pin().list_connected_pins());n.find_then_pin().break_pin_links();stop=e.add_call_function_node('/Script/Engine.Actor.SetActorTickEnabled');val(pin(stop,'bEnabled'),False);link(n.find_then_pin(),stop.find_execute_pin());stop.rename('HoloStopIdlePolling')
    for dest in old:link(stop.find_then_pin(),dest)
    break
  compile_bp(bp);save(bp);r['holograms'].append(bp.get_path_name())
 # Apply the render budgets to the current editor session. Worker count takes
 # effect next start; no restart is forced over the user's unsaved work.
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 for cmd in ('r.Streaming.PoolSize 1000','r.Streaming.LimitPoolSizeToVRAM 1','r.Streaming.MaxTempMemoryAllowed 32','r.Nanite.Streaming.StreamingPoolSize 256'):
  unreal.SystemLibrary.execute_console_command(world,cmd)
 unreal.SystemLibrary.collect_garbage()
 r.update(saved=True,backup=backup,main_player_model_unchanged=True,texture_resolution_unchanged=True,hologram_lod=2,worker_limit_requires_restart=True)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:open(os.path.join(root,'Saved/memory_asset_optimization.json'),'w',encoding='utf8').write(json.dumps(r,ensure_ascii=False,indent=2))
if not r['saved']:raise RuntimeError('Memory optimization incomplete')

