import unreal,os,json
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pc=p.get_controller();hud=pc.get_hud();gm=unreal.GameplayStatics.get_game_mode(w)
r={'hud':str(hud),'hud_class':hud.get_class().get_name(),'game_mode_hud_class':str(gm.get_editor_property('hud_class')),'frames':p.get_editor_property('ModeHUDFrames'),'ignored':pc.is_move_input_ignored(),'pawn':str(hud.get_owning_pawn()),'show_hud':hud.get_editor_property('show_hud')}
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'cyborg_modes_runtime.json'),'w'),indent=2)
