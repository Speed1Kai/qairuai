"""Read-only inspection: no actor/asset/graph writes, no compilation or script execution."""
import unreal, json, os
B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
paths=['/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter','/Game/LabTutorial/Blueprints/BP_TutorialSlidingDoor','/Game/LabTutorial/Blueprints/BP_TutorialHologramTrigger','/Game/LabTutorial/Blueprints/BP_LabRecoveryLog']
report={}
for path in paths:
    bp=unreal.load_asset(path); graphs={}
    for name in B.list_graph_names(bp):
        e=G.get_graph_editor_by_name(bp,name); nodes=[]
        for n in e.list_all_nodes():
            pins=[]
            for p in n.list_all_pins():
                pins.append({'name':str(p.get_pin_name()),'value':p.get_pin_value(),'connections':[(str(c.get_owning_node().get_node_title()),str(c.get_pin_name())) for c in p.list_connected_pins()]})
            nodes.append({'name':n.get_name(),'class':n.get_class().get_name(),'title':str(n.get_node_title()),'pins':pins})
        graphs[str(name)]=nodes
    report[path]=graphs
with open(os.path.join(unreal.Paths.project_saved_dir(),'interaction_readonly_inspection.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
unreal.log('Read-only interaction inspection finished')
