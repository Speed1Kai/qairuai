import unreal,os
m=unreal.EditorAssetLibrary.load_asset('/Game/LabTutorial/UI/M_OmegaInteraction')
for expr in unreal.ObjectIterator(unreal.MaterialExpressionCustom):
 if expr.get_outer()==m:expr.set_editor_property('code',open(os.path.join(unreal.Paths.project_dir(),'SourceAssets/OmegaUI/OmegaInteraction.hlsl'),encoding='utf-8-sig').read())
unreal.MaterialEditingLibrary.recompile_material(m)
assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
