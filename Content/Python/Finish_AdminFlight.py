"""Let developer noclip bypass the broken bridge's normal fall recovery."""
import unreal,sys,os,shutil,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,Graph,pin,link,compile_bp,save
report_path=os.path.join(unreal.Paths.project_saved_dir(),'admin_flight_report.json')
report=json.load(open(report_path,encoding='utf8'))
path='/Game/Surface/Bridge/BP_BridgeRecovery'
if A.does_asset_exist(path):
 bp=A.load_asset(path);g=Graph(bp)
 if 'AdminCollisionGateInstalled' not in map(str,B.list_member_variable_names(bp)):
  src=os.path.join(unreal.Paths.project_content_dir(),'Surface/Bridge/BP_BridgeRecovery.uasset')
  shutil.copy2(src,report['backup'])
  tick=g.e.find_event_node('ReceiveTick');then=pin(tick,'then',True)
  old=list(then.list_connected_pins())
  player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
  # A noclip pawn has collision disabled. Do not treat its inspection flight as
  # an accidental fall or overwrite the bridge's last safe shore.
  valid=g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=player))
  then.break_pin_links();g.cursor=then;g.branch(valid)
  g.branch(g.out(g.call('Engine.Actor.GetActorEnableCollision',target=player)))
  for p in old:link(g.cursor,p)
  g.e.add_member_variable('AdminCollisionGateInstalled',B.get_basic_type_by_name('bool'),'true')
  compile_bp(bp);save(bp)
 report['bridge_recovery_bypassed_during_noclip']=True
with open(report_path,'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
