"""Offset decorative wall strips to prevent coplanar flicker; no collision changes."""
import unreal, os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from Industrial_Common import A, B, components, compile_bp, save
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before saving'
bp=A.load_asset('/Game/Surface/Interiors/BP_CampusInteriors')
def fix(c):
    count=0
    if c.get_name().removesuffix('_GEN_VARIABLE') not in ('Box_teal_Trim','Box_dark_Trim'):
        return count
    c.modify()
    for i in range(c.get_instance_count()):
        t=c.get_instance_transform(i,False)
        s=t.scale3d
        if abs(s.x-.26)<.0001:
            s.x=.28
        elif abs(s.y-.26)<.0001:
            s.y=.28
        else:
            continue
        t.scale3d=s
        c.update_instance_transform(i,t,False,True,True)
        count+=1
    return count
total=sum(fix(c) for h,c,n in components(bp) if isinstance(c,unreal.InstancedStaticMeshComponent))
compile_bp(bp)
save(bp)
w=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_CampusConnected')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
placed=0
for a in sub.get_all_level_actors():
    if a.get_class().get_name()=='BP_CampusInteriors_C':
        a.modify()
        placed+=sum(fix(c) for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent))
w.modify()
assert unreal.EditorLoadingAndSavingUtils.save_map(w,'/Game/Surface/Lvl_CampusConnected')
del w
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
json.dump({'saved':True,'template_strips':total,'placed_strips':placed},open(os.path.join(unreal.Paths.project_dir(),'Saved/campus_trim_finish.json'),'w'),indent=2)
