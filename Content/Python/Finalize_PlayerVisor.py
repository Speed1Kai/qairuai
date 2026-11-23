"""Persist final helmet alpha channel and authoring helper."""
import unreal,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,save
mat=A.load_asset('/Game/Characters/PlayerVisor/M_VisorRim')
for obj in unreal.ObjectIterator(unreal.MaterialExpressionComponentMask):
 if obj.get_outer()!=mat or not obj.get_editor_property('a'):continue
 for ch in ['r','g','b']:obj.set_editor_property(ch,False)
M.recompile_material(mat);save(mat)
save(A.load_asset('/Game/LabTutorial/UI/BP_ArchiveAuthoring'))
