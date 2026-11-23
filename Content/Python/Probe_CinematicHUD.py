import unreal, json, os
result = {'engine': unreal.SystemLibrary.get_engine_version()}
for name in ('WidgetBlueprint','WidgetTree','CanvasPanel','Border','TextBlock','UserWidget'):
    cls=getattr(unreal,name)
    result[name]={'doc':cls.__doc__, 'methods':dir(cls)}
bp=unreal.load_asset('/Game/LabTutorial/Blueprints/BP_LabAtlasLog')
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
result['actions']=[x for x in e.list_available_nodes([]) if any(k in x.lower() for k in ('createwidget','create widget','viewport','setrenderopacity'))]
with open(os.path.join(unreal.Paths.project_saved_dir(),'cinematic_hud_probe.json'),'w',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
