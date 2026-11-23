"""Keep chest plating out of the lens without changing the cyborg proportions.
Eye camera leans forward gently as the player looks down; the same animated
body stays visible and V continues to restore the complete third-person mesh.
"""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,components,pin,val,link,compile_bp,save
source=os.path.join(unreal.Paths.project_content_dir(),'Python/Upgrade_PlayerVisor.py')
exec(compile(open(source,encoding='utf-8-sig').read().split('\ntry:\n')[0],source,'exec'))
report={'saved':False,'gameplay_tested':False}
try:
 bp=A.load_asset(PLAYER);backup=os.path.join(p,'Saved/Backups/FirstPersonCamera',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 shutil.copy2(os.path.join(p,'Content/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),os.path.join(backup,'BP_ThirdPersonCharacter.uasset'))
 member(bp,'FirstPersonLookDownLean','real','0')
 member(bp,'FirstPersonEyeForward','real','18')
 member(bp,'FirstPersonDownForward','real','18')
 member(bp,'FirstPersonEyeHeight','real','85')
 member(bp,'FirstPersonLeanSpeed','real','9')
 cs={n:c for h,c,n in components(bp) if c};cs['FirstPersonCamera'].set_editor_property('relative_location',V((18,0,85)))
 compile_bp(bp)
 g=Flow(bp,'View_UpdateBodyCamera');dt=g.arg('DeltaSeconds',B.get_basic_type_by_name('real'));g.branch(g.get('bFirstPerson'))
 rot=g.out(g.call('Engine.Pawn.GetControlRotation'))
 forward=g.math('GetForwardVector',InRot=rot);vec=g.call('Engine.KismetMathLibrary.BreakVector',InVec=forward)
 down=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=pin(vec,'Z',True),B=-1.),B=.90),Min=0.,Max=1.)
 eased=g.smooth(down)
 g.set('FirstPersonLookDownLean',g.math('FInterpTo',Current=g.get('FirstPersonLookDownLean'),Target=eased,DeltaTime=dt,InterpSpeed=g.get('FirstPersonLeanSpeed')))
 x=g.math('Add_DoubleDouble',A=g.get('FirstPersonEyeForward'),B=g.math('Multiply_DoubleDouble',A=g.get('FirstPersonDownForward'),B=g.get('FirstPersonLookDownLean')))
 pos=g.math('MakeVector',X=x,Y=0.,Z=g.get('FirstPersonEyeHeight'))
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('FirstPersonCamera'),NewLocation=pos,bSweep=False,bTeleport=False))
 compile_bp(bp)
 e=G.get_graph_editor_by_name(bp,'EventGraph')
 if not any(n.get_name()=='FullBodyCameraLeanTick' for n in e.list_all_nodes()):
  g=Flow(bp);ev=g.event('ReceiveTick');old=list(pin(ev,'then',True).list_connected_pins());pin(ev,'then',True).break_pin_links();seq=g.sequence();link(pin(ev,'then',True),seq.find_execute_pin())
  for dest in old:link(pin(seq,'then_0',True),dest)
  g.cursor=pin(seq,'then_1',True);call=g.selfcall('View_UpdateBodyCamera');val(pin(call,'DeltaSeconds'),pin(ev,'DeltaSeconds',True));g.do(call);call.rename('FullBodyCameraLeanTick')
 compile_bp(bp);save(bp)
 report.update(saved=True,backup=backup,eye_offset=[18,0,85],look_down_offset=[36,0,85],smooth_speed=9,body_proportions_unchanged=True)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:open(os.path.join(p,'Saved/first_person_camera_refinement.json'),'w').write(json.dumps(report,indent=2))
if not report['saved']:raise RuntimeError('First-person camera refinement incomplete')
