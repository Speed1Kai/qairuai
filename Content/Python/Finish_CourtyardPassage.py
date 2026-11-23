import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,components,compile_bp,save
world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor=A.load_asset('/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor')
for h,c,name in components(floor):
 if c and c.get_class()==unreal.SceneComponent.static_class():c.modify();c.set_mobility(unreal.ComponentMobility.STATIC)
compile_bp(floor);save(floor)
count=0
for a in sub.get_all_level_actors():
 if a.get_class().get_name()!='BP_ModernFirstFloor_C':continue
 a.modify()
 for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
  c.modify()
  for i in range(c.get_instance_count()-1,-1,-1):
   p=c.get_instance_transform(i,False).translation
   if 5540<p.x<6160 and 2149<p.z<2600 and ((1267<p.y<1320) or abs(p.y-1500)<13):c.remove_instance(i);count+=1
world.modify()
assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Lvl_LabTutorial')
unreal.log('COURTYARD: removed persisted blockers %d'%count)
