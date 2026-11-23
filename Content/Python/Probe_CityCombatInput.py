import unreal,os,json
bp=unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
opts=[str(m) for m in e.list_available_nodes([]) if any(k in str(m).lower() for k in ('mouse','мыш','лкм'))]
json.dump({'mouse_menus':opts,'key_doc':unreal.Key.__doc__},open(os.path.join(unreal.Paths.project_saved_dir(),'citycombat_input_probe.json'),'w'),ensure_ascii=False,indent=2)
