import unreal,json,os
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
r={'compiled':[],'gameplay_tested':False}
for path in ('/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt','/Game/Characters/PlayerVisor/WBP_PlayerVisor'):
 bp=A.load_asset(path)
 assert B.compile_blueprint(bp),path
 for name in B.list_graph_names(bp):assert not G.get_graph_editor_by_name(bp,name).list_nodes_with_errors(),path
 r['compiled'].append(path)
open(os.path.join(unreal.Paths.project_saved_dir(),'memory_widget_reload_verification.json'),'w').write(json.dumps(r,indent=2))
