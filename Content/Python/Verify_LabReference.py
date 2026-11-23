import unreal, os
A=unreal.EditorAssetLibrary
E=unreal.MaterialEditingLibrary
path='/Game/LabTutorial/ReferenceStyle/M_HologramText'
m=A.load_asset(path)
if not m:
    m=A.duplicate_asset('/Engine/EngineMaterials/DefaultTextMaterialOpaque',path)
if m:
    color=E.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant',unreal.LinearColor(r=3,g=55,b=65,a=1))
    E.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    E.recompile_material(m);A.save_loaded_asset(m)
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(a,unreal.TextRenderActor):
            a.get_component_by_class(unreal.TextRenderComponent).set_text_material(m)
            a.set_actor_label(a.get_actor_label(),mark_dirty=True)
# Repair the pre-existing lift's unconnected component target, if its call exists.
bp=A.load_asset('/Game/LabTutorial/Blueprints/BP_LabTutorialElevator')
graph=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,unreal.Name('EventGraph'))
nodes=graph.list_all_nodes()
activate=None;getter=None
for n in nodes:
    if n.get_class().get_name()=='K2Node_CallFunction':
        if n.find_input_pin('bReset').is_valid(): activate=n
        if n.find_input_pin('ComponentClass').is_valid() and n.find_output_pin('ReturnValue').is_valid():getter=n
result='No lift change'
if activate and getter:
    target=activate.find_input_pin('self')
    if not target.is_valid(): target=activate.find_input_pin('Target')
    if target.is_valid():
        result=str(getter.find_output_pin('ReturnValue').try_create_connection(target))
compiled=unreal.BlueprintEditorLibrary.compile_blueprint(bp)
if compiled:A.save_loaded_asset(bp)
unreal.EditorLoadingAndSavingUtils.save_map(unreal.EditorLevelLibrary.get_editor_world(),'/Game/Lvl_LabTutorial')
with open(os.path.join(unreal.Paths.project_saved_dir(),'reference_final_check.txt'),'w') as f:
    f.write('Lift connection: '+result+'\nLift compile: '+str(compiled)+'\nMap saved; reference art pass complete.\n')
