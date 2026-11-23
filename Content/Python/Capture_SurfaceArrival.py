"""Export one static environment artwork; does not start Play or alter gameplay."""
import unreal,os,json,shutil
# The surface loads the same visor; repair the two previously unconnected masks
# so first-person viewing does not fall back to Unreal's default material.
m=unreal.EditorAssetLibrary.load_asset('/Game/Characters/PlayerVisor/M_VisorRim')
report=json.load(open('S:/Final_Protocol/Saved/surface_arrival_report.json',encoding='utf8'))
backup=os.path.join(report['backup'],'M_VisorRim.uasset')
if not os.path.isfile(backup):shutil.copy2('S:/Final_Protocol/Content/Characters/PlayerVisor/M_VisorRim.uasset',backup)
custom=next(n for n in unreal.ObjectIterator(unreal.MaterialExpressionCustom) if n.get_outer()==m)
for mask in unreal.ObjectIterator(unreal.MaterialExpressionComponentMask):
 if mask.get_outer()==m:
  if not unreal.MaterialEditingLibrary.connect_material_expressions(custom,'',mask,''):raise RuntimeError('Visor mask connection failed')
unreal.MaterialEditingLibrary.recompile_material(m)
if not unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False):raise RuntimeError('Visor material save failed')
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
unreal.AutomationLibrary.take_high_res_screenshot(1440,900,'S:/Final_Protocol/Saved/SurfaceArrival_Overview.png',delay=1.)
