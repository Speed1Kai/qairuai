"""Public Blueprint authoring helpers for UMG's editor-only UObject fields."""
import unreal
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
HELPER_PATH='/Game/LabTutorial/UI/BP_ArchiveAuthoring'
helper=A.load_asset(HELPER_PATH) if A.does_asset_exist(HELPER_PATH) else None
if not helper:
    f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
    helper=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ArchiveAuthoring','/Game/LabTutorial/UI',unreal.Blueprint,f)
if 'AssignObject' not in [str(n) for n in B.list_graph_names(helper)]:
    e=G.create_and_edit_function_graph(helper,'AssignObject')
    obj=e.add_graph_input_parameter('TargetObject',B.get_object_reference_type(unreal.Object))
    name=e.add_graph_input_parameter('PropertyName',B.get_basic_type_by_name('name'))
    val=e.add_graph_input_parameter('Value',B.get_object_reference_type(unreal.Object))
    n=e.add_call_function_node('/Script/Engine.KismetSystemLibrary.SetObjectPropertyByName')
    assert e.find_graph_entry_pin().try_create_connection(n.find_execute_pin())
    for p,k in ((obj,'Object'),(name,'PropertyName'),(val,'Value')):assert p.try_create_connection(n.find_input_pin(k))
    assert B.compile_blueprint(helper)
def assign_object(target,name,value):
    unreal.get_default_object(B.generated_class(helper)).call_method('AssignObject',args=(target,unreal.Name(name),value))
def assign_array(target,property_name,member_name,pin_type,default):
    e=G.get_graph_editor_by_name(helper,'EventGraph')
    names=[str(n) for n in B.list_member_variable_names(helper)]
    if member_name not in names:
        assert e.add_member_variable(member_name,B.get_array_type(pin_type),default)
    fname='Assign'+member_name
    if fname not in [str(n) for n in B.list_graph_names(helper)]:
        e=G.create_and_edit_function_graph(helper,fname)
        obj=e.add_graph_input_parameter('TargetObject',B.get_object_reference_type(unreal.Object))
        get=e.add_get_member_variable_node(member_name)
        call=e.add_call_function_node('/Script/Engine.KismetArrayLibrary.SetArrayPropertyByName')
        assert e.find_graph_entry_pin().try_create_connection(call.find_execute_pin())
        assert obj.try_create_connection(call.find_input_pin('Object'))
        assert call.find_input_pin('PropertyName').set_pin_value(property_name)
        assert get.find_output_pin(member_name).try_create_connection(call.find_input_pin('Value'))
    assert B.compile_blueprint(helper)
    unreal.get_default_object(B.generated_class(helper)).call_method(fname,args=(target,))
