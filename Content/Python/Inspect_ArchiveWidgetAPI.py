import unreal, os, json
result={}
for name in ('WidgetBlueprint','WidgetBlueprintFactory','WidgetTree','WidgetAnimation','WidgetAnimationBinding','MovieScene','MovieSceneFloatTrack','WidgetBlueprintEditorLibrary'):
    cls=getattr(unreal,name,None)
    result[name]=dict(doc=str(getattr(cls,'__doc__',''))[:1500],methods=[k for k in dir(cls) if any(s in k for s in ('widget','animation','possess','track','binding','root'))]) if cls else None
bp=unreal.load_asset('/Game/LabTutorial/Blueprints/BP_LabAtlasLog')
e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
result['terminal']=[dict(name=n.get_name(),cls=n.get_class().get_name(),title=str(n.get_node_title()),pins=[dict(name=str(p.get_pin_name()),value=p.get_pin_value(),links=[(q.get_owning_node().get_name(),str(q.get_pin_name())) for q in p.list_connected_pins()]) for p in n.list_all_pins()]) for n in e.list_all_nodes()]
with open(os.path.join(unreal.Paths.project_saved_dir(),'archive_widget_api.json'),'w',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
