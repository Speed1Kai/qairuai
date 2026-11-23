"""Open the authored HUD in the UMG designer; do not start a game session."""
import unreal,os
A=unreal.EditorAssetLibrary
bp=A.load_asset('/Game/Characters/PlayerVisor/WBP_PlayerVisor');cdo=unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
unreal.EditorAssetLibrary.save_loaded_asset(bp,only_if_is_dirty=False)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([bp])

import json
tr=unreal.find_object(bp,'WidgetTree'); info={}
for name in ('HelmetRim','BodyDiagnostics'):
 w=unreal.find_object(tr,name)
 info[name]={k:str(w.get_editor_property(k)) for k in ('brush','color_and_opacity','render_opacity','visibility')}
open(unreal.Paths.project_saved_dir()+'visor_brushes.json','w').write(json.dumps(info,indent=2))
