"""Full-body first person on the existing player; preserve V, HUD and animation.
Only the head is hidden while looking through the eyes. Third person restores it.
"""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,Graph,components,pin,val,link,compile_bp,save
src=os.path.join(unreal.Paths.project_content_dir(),'Python/Upgrade_PlayerVisor.py')
exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
report={'saved':False};root=os.path.abspath(unreal.Paths.project_dir())
try:
 backup=os.path.join(root,'Saved/Backups/FirstPersonBody',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 for rel in ('ThirdPerson/Blueprints/BP_ThirdPersonCharacter','Characters/PlayerVisor/WBP_PlayerVisor'):
  source=os.path.join(root,'Content',rel+'.uasset');dest=os.path.join(backup,rel+'.uasset');os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(source,dest)
 bp=A.load_asset(PLAYER);cs={n:c for h,c,n in components(bp) if c};mesh=cs['Mesh'];camera=cs['FirstPersonCamera']
 # A stable eye-level camera avoids motion sickness from animated neck bones.
 camera.set_editor_property('relative_location',V((18,0,85)));camera.set_editor_property('use_pawn_control_rotation',True)
 mesh.set_editor_property('owner_no_see',False);mesh.set_editor_property('only_owner_see',False)
 mesh.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
 e=G.get_graph_editor_by_name(bp,'EventGraph');body_node=None;visible=[]
 for n in e.list_all_nodes():
  q=n.find_input_pin('bNewOwnerNoSee')
  if not q.is_valid():continue
  targets=[str(x.get_pin_name()) for x in n.find_self_pin().list_connected_pins()]
  # Retain head/neck glow hiding, but show the chest and limb fixtures.
  if any(x in targets for x in ('Mesh','ChestReactor','SpineReactor','ShoulderL','ShoulderR','WristL','WristR','ChestEmitter','BackEmitter','LeftArmEmitter','RightArmEmitter','LeftLegEmitter','RightLegEmitter')):
   q.break_pin_links();val(q,False);visible.extend(targets)
  if 'Mesh' in targets:body_node=n
 if not body_node:raise RuntimeError('Existing V body visibility node not found')
 g=Flow(bp,'View_ApplyBodyVisibility');g.do(g.call('Engine.PrimitiveComponent.SetOwnerNoSee',target=g.get('Mesh'),bNewOwnerNoSee=False))
 branch=g.branch(g.get('bFirstPerson'));third=branch.find_else_pin()
 g.do(g.call('Engine.SkinnedMeshComponent.HideBoneByName',target=g.get('Mesh'),BoneName='CC_Base_Head',PhysBodyOption='PBO_None'))
 g.cursor=third;g.do(g.call('Engine.SkinnedMeshComponent.UnHideBoneByName',target=g.get('Mesh'),BoneName='CC_Base_Head'))
 compile_bp(bp)
 if not any(n.get_name()=='FullBodyViewSwitch' for n in e.list_all_nodes()):
  old=list(body_node.find_then_pin().list_connected_pins());body_node.find_then_pin().break_pin_links();g=Flow(bp);g.cursor=body_node.find_then_pin();call=g.do(g.selfcall('View_ApplyBodyVisibility'));call.rename('FullBodyViewSwitch')
  for dest in old:link(g.cursor,dest)
 compile_bp(bp);save(bp)
 # GetDynamicMaterial is impure in this engine: connect its exec pins before
 # storing each MID. Previously the returned references could remain None.
 wbp=A.load_asset(ROOT+'/WBP_PlayerVisor');we=G.get_graph_editor_by_name(wbp,'EventGraph');fixed=[]
 for key in ('RimMID','BodyMID'):
  setter=next(n for n in we.list_all_nodes() if n.find_input_pin(key).is_valid() and n.find_execute_pin().is_valid())
  getmid=list(setter.find_input_pin(key).list_connected_pins())[0].get_owning_node()
  if getmid.find_execute_pin().is_valid() and not getmid.find_execute_pin().list_connected_pins():
   incoming=list(setter.find_execute_pin().list_connected_pins());setter.find_execute_pin().break_pin_links()
   for prev in incoming:link(prev,getmid.find_execute_pin())
   link(getmid.find_then_pin(),setter.find_execute_pin());fixed.append(key)
 compile_bp(wbp);save(wbp)
 report.update(saved=True,backup=backup,visible_body_parts=visible,head_bone='CC_Base_Head',camera_offset=[18,0,85],visor_mid_exec_repaired=fixed,gameplay_tested=False)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 open(os.path.join(root,'Saved/first_person_body_report.json'),'w',encoding='utf8').write(json.dumps(report,indent=2))
if not report['saved']:raise RuntimeError('Full body first person not saved')

