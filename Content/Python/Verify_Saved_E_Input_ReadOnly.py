"""Verify saved packages in a separate process, without editing or compiling."""
import unreal, json, os
A=unreal.EditorAssetLibrary;G=unreal.BlueprintGraphEditor
names=['BP_TutorialHologramTrigger','BP_LabRecoveryLog','BP_LabAtlasLog','BP_LabMobilityLog','BP_LabPurposeLog','BP_LabArchiveFragmentLog','BP_LabStealthHint','BP_TutorialSlidingDoor']
results={}
for name in names:
    bp=A.load_asset('/Game/LabTutorial/Blueprints/'+name)
    e=G.get_graph_editor_by_name(bp,'EventGraph')
    keys=[n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_InputKey' and str(n.get_editor_property('input_key').get_editor_property('key_name'))=='E']
    assert len(keys)==1,name+': expected one E event'
    assert not keys[0].get_editor_property('bConsumeInput'),name+': E consumed by inactive objects'
    links=keys[0].find_output_pin('Pressed').list_connected_pins()
    assert len(links)==1,name+': disconnected E'
    branch=links[0].get_owning_node()
    assert branch.get_class().get_name()=='K2Node_IfThenElse',name+': no proximity guard'
    assert branch.find_then_pin().list_connected_pins(),name+': disconnected action'
    assert branch.find_input_pin('Condition').list_connected_pins(),name+': disconnected condition'
    results[name]='PASS: saved E binding, proximity guard, action connection, non-consuming input'
with open(os.path.join(unreal.Paths.project_saved_dir(),'saved_e_input_verified.json'),'w',encoding='utf8') as f:json.dump(results,f,ensure_ascii=False,indent=2)
unreal.log('SAVED E INPUT VERIFICATION: 8/8 PASS')
