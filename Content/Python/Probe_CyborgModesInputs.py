import unreal,os,json
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
r={}
w=unreal.EditorLevelLibrary.get_game_world();c=unreal.GameplayStatics.get_player_character(w,0)
r['player']={k:str(c.get_editor_property(k)) for k in ('ModeSwitches','ModeTriggerPulls','bModeMenuOpen','CyborgMode')}
m=c.get_component_by_class(unreal.SkeletalMeshComponent);r['mesh']={'asset':str(m.get_skinned_asset()),'hand':str(m.get_socket_location('CC_Base_R_Hand')),'hand_exists':m.does_socket_exist('CC_Base_R_Hand')}
t=c.get_editor_property('TP_LaserWeapon');r['tp']={'socket':str(t.get_attach_socket_name()),'parent':str(t.get_attach_parent()),'pos':str(t.get_world_location())}
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'cyborg_modes_inputs_debug.json'),'w'),indent=2)

