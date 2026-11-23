"""Preserve projector interaction while replacing every physical pedestal."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
from Industrial_Materials import make_material
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
make_material('M_CRTGlass','crt',(.025,2.4,2.8),0,.5)
make_material('M_CyanIndicator','glow',(.04,3.1,3.5),0,.5)
mesh=A.load_asset(ROOT+'/SM_DockingGenerator');rows=[]
for i in range(1,7):
 bp=A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i)
 c=add(bp,unreal.StaticMeshComponent,'IndustrialGenerator');c.set_static_mesh(mesh);c.set_editor_property('relative_location',V((0,0,0)));c.set_editor_property('relative_scale3d',V((1,1,1)));c.set_collision_profile_name('NoCollision');c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('cast_shadow',False)
 compile_bp(bp);g=Graph(bp);g.event('ReceiveBeginPlay')
 for name in ('Foot','Housing','EmitterRim','Lens','EmitterCore',*('CoolingRib%d'%j for j in range(6))):
  g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=False,bPropagateToChildren=False))
 for h,obj,n in components(bp):
  if n=='Foot' or n in ('Housing','EmitterRim','Lens','EmitterCore') or n.startswith('CoolingRib'):obj.set_editor_property('visible',False)
 compile_bp(bp);save(bp);rows.append(bp.get_name())
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 if not a.get_class().get_name().startswith('BP_ArchiveProjector_'):continue
 for c in a.get_components_by_class(unreal.StaticMeshComponent):
  n=c.get_name()
  if n=='Foot' or n in ('Housing','EmitterRim','Lens','EmitterCore') or n.startswith('CoolingRib'):c.set_editor_property('visible',False)
unreal.EditorLoadingAndSavingUtils.save_current_level()
with open('S:/Final_Protocol/Saved/industrial_props_report.json','w') as f:json.dump({'saved':True,'projectors':rows},f,indent=2)
