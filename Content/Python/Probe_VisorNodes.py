import unreal,json
bp=unreal.EditorAssetLibrary.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
n=e.list_all_nodes()[0]
open(unreal.Paths.project_saved_dir()+'visor_node_api.json','w').write(json.dumps([x for x in dir(n) if not x.startswith('_')]))
