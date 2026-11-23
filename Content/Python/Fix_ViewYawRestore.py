"""Restore the player mesh with a typed Rotator after exiting first person."""
import unreal,os,sys,json,datetime,shutil
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,pin,val,compile_bp,save
src=os.path.join(os.path.dirname(__file__),'Upgrade_PlayerVisor.py');exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
project=os.path.abspath(unreal.Paths.project_dir());path='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter';backup=os.path.join(project,'Saved/Backups/ViewRestore',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);shutil.copy2(os.path.join(project,'Content/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),os.path.join(backup,'BP_ThirdPersonCharacter.uasset'))
bp=A.load_asset(path);g=Flow(bp);g.e=G.get_graph_editor_by_name(bp,'View_ApplyBodyVisibility');restore=next(n for n in g.e.list_all_nodes() if n.get_name()=='FullBodyRestoreYaw');rp=pin(restore,'NewRotation');old=rp.get_pin_value();rp.break_pin_links()
# A named FRotator string was silently parsed as (0,0,0). A typed MakeRotator
# connection is locale-independent and matches the mesh's authored orientation.
rotation=g.math('MakeRotator',Roll=0.,Pitch=0.,Yaw=-90.);val(rp,rotation);compile_bp(bp);save(bp)
json.dump({'saved':True,'backup':backup,'previous_literal':old,'restored_yaw':-90,'typed_rotator':True},open(os.path.join(project,'Saved/view_restore_fix.json'),'w'),indent=2)
