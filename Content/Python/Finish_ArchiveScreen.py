"""Place the LED surface in front of its metal backing."""
import unreal,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,V,components,compile_bp,save
film=A.load_asset('/Game/LabTutorial/FocusedInteraction/M_WorldCollapseFilm')
for expr in unreal.ObjectIterator(unreal.MaterialExpressionCustom):
 if expr.get_outer()==film:
  expr.set_editor_property('code',expr.get_editor_property('code').replace('col*(.45+Playing*.9)','col*(8+Playing*12)'))
M.recompile_material(film);save(film)
bp=A.load_asset('/Game/LabTutorial/FocusedInteraction/BP_WorldArchiveBoard')
for h,c,n in components(bp):
 if c and n=='LEDDisplay':c.set_editor_property('relative_location',V((0,-8,0)))
compile_bp(bp);save(bp)
unreal.EditorLoadingAndSavingUtils.save_current_level()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
