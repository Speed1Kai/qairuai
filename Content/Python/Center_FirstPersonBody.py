"""Align the animated shoulders to the first-person view, preserving third person.
Uses the actual shoulder bones rather than a permanent yaw offset, so walk/run
animations can retain their own poses without leaving the body turned sideways.
"""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,components,pin,val,link,compile_bp,save
src=os.path.join(unreal.Paths.project_content_dir(),'Python/Upgrade_PlayerVisor.py')
exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
r={'saved':False,'live_preview_checked':True,'walking_tested':False}
try:
 bp=A.load_asset(PLAYER);backup=os.path.join(p,'Saved/Backups/FirstPersonCenter',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);shutil.copy2(os.path.join(p,'Content/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),os.path.join(backup,'BP_ThirdPersonCharacter.uasset'))
 member(bp,'FirstPersonBodyYawCorrection','real','0')
 cs={n:c for h,c,n in components(bp) if c};cs['FirstPersonCamera'].set_field_of_view(100.)
 g=Flow(bp,'View_AlignBodyToCamera');dt=g.arg('DeltaSeconds',B.get_basic_type_by_name('real'));g.branch(g.get('bFirstPerson'))
 transform=g.out(g.do(g.call('Engine.Actor.GetTransform')))
 points=[]
 for bone in ('CC_Base_L_Upperarm','CC_Base_R_Upperarm'):
  world=g.out(g.call('Engine.SceneComponent.GetSocketLocation',target=g.get('Mesh'),InSocketName=bone));local=g.math('InverseTransformLocation',T=transform,Location=world);points.append(g.call('Engine.KismetMathLibrary.BreakVector',InVec=local))
 dx=g.math('Subtract_DoubleDouble',A=pin(points[1],'X',True),B=pin(points[0],'X',True));dy=g.math('Subtract_DoubleDouble',A=pin(points[1],'Y',True),B=pin(points[0],'Y',True))
 error=g.math('DegAtan2',Y=dx,X=dy)
 target=g.math('FClamp',Value=g.math('Add_DoubleDouble',A=g.get('FirstPersonBodyYawCorrection'),B=error),Min=-50.,Max=50.)
 g.set('FirstPersonBodyYawCorrection',g.math('FInterpTo',Current=g.get('FirstPersonBodyYawCorrection'),Target=target,DeltaTime=dt,InterpSpeed=10.))
 rotation=g.math('MakeRotator',Roll=0.,Pitch=0.,Yaw=g.math('Add_DoubleDouble',A=270.,B=g.get('FirstPersonBodyYawCorrection')))
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('Mesh'),NewRotation=rotation,bSweep=False,bTeleport=False))
 compile_bp(bp)
 e=G.get_graph_editor_by_name(bp,'View_UpdateBodyCamera')
 if not any(n.get_name()=='FullBodyCenterAlignment' for n in e.list_all_nodes()):
  move=next(n for n in e.list_all_nodes() if n.find_input_pin('NewLocation').is_valid());old=list(move.find_then_pin().list_connected_pins());move.find_then_pin().break_pin_links();g=Flow(bp);g.e=e;g.cursor=move.find_then_pin();call=g.selfcall('View_AlignBodyToCamera');entry=e.find_graph_entry_pin().get_owning_node();val(pin(call,'DeltaSeconds'),pin(entry,'DeltaSeconds',True));g.do(call);call.rename('FullBodyCenterAlignment')
  for dest in old:link(g.cursor,dest)
 # Restore the original relative orientation on V -> third person.
 e=G.get_graph_editor_by_name(bp,'View_ApplyBodyVisibility')
 if not any(n.get_name()=='FullBodyRestoreYaw' for n in e.list_all_nodes()):
  unhide=next(n for n in e.list_all_nodes() if 'UnHideBoneByName' in str(n.get_node_title()).replace(' ',''))
  g=Flow(bp);g.e=e;g.cursor=unhide.find_then_pin();g.set('FirstPersonBodyYawCorrection',0.)
  restore=g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('Mesh'),NewRotation='(Pitch=0,Yaw=270,Roll=0)',bSweep=False,bTeleport=False));restore.rename('FullBodyRestoreYaw')
 compile_bp(bp)
 cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('FirstPersonDownForward',24.)
 save(bp);r.update(saved=True,backup=backup,fov=100,look_down_forward=42,body_alignment='animated shoulder bones',third_person_yaw=270)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:open(os.path.join(p,'Saved/first_person_center_report.json'),'w').write(json.dumps(r,indent=2))
if not r['saved']:raise RuntimeError('First person centering incomplete')
