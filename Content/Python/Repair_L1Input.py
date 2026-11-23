"""Persist explicit input registration for the surface departure console."""
import unreal,sys,os,json,shutil,datetime
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,Graph,pin,link,compile_bp,save
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups','L1Input',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
for rel in ['Surface/BP_SurfaceDeparture.uasset','Lvl_LabTutorial.umap']:
 src=os.path.join(unreal.Paths.project_content_dir(),rel);shutil.copy2(src,os.path.join(backup,os.path.basename(src)))
bp=A.load_asset('/Game/Surface/BP_SurfaceDeparture');g=Graph(bp)
# AutoReceiveInput on the placed instance had reverted to Disabled. Register at
# BeginPlay explicitly, after PlayerController creation, including packaged play.
if not any(n.find_input_pin('PlayerController').is_valid() and n.find_execute_pin().is_valid() for n in g.e.list_all_nodes()):
 begin=g.e.find_event_node('ReceiveBeginPlay');then=pin(begin,'then',True);old=list(then.list_connected_pins());then.break_pin_links();g.cursor=then
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.2))
 pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 g.do(g.call('Engine.Actor.EnableInput',PlayerController=pc))
 for p in old:link(g.cursor,p)
compile_bp(bp)
cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',95);cdo.set_editor_property('block_input',False);save(bp)
fixed=[]
for a in sub.get_all_level_actors():
 if a.get_class().get_name()=='BP_SurfaceDeparture_C':
  a.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);a.set_editor_property('input_priority',95);fixed.append({'actor':a.get_actor_label(),'input':str(a.get_editor_property('auto_receive_input')),'position':str(a.get_actor_location())})
if not fixed:raise RuntimeError('No surface departure console in awakening map')
if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('L1 map save failed')
with open(os.path.join(unreal.Paths.project_saved_dir(),'l1_input_repair.json'),'w',encoding='utf8') as f:json.dump({'saved':True,'explicit_begin_play_enable_input':True,'instances':fixed,'backup':backup,'gameplay_tested':False},f,ensure_ascii=False,indent=2)
