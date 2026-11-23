"""Connect the drone's mesh to its two thermal material operations."""
import unreal, os, shutil, json, traceback
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
saved=unreal.Paths.project_saved_dir()
report=os.path.join(saved,'drone_material_repair.json')
try:
    backup=os.path.join(saved,'Backups','DroneMaterialTargets');os.makedirs(backup,exist_ok=True)
    source=os.path.join(unreal.Paths.project_content_dir(),'LabTutorial','Blueprints','BP_TutorialPatrolDrone.uasset')
    dest=os.path.join(backup,os.path.basename(source))
    if not os.path.exists(dest):shutil.copy2(source,dest)
    bp=A.load_asset('/Game/LabTutorial/Blueprints/BP_TutorialPatrolDrone')
    e=G.get_graph_editor_by_name(bp,'EventGraph')
    repaired=[]
    for node in e.list_all_nodes():
        if node.get_class().get_name()!='K2Node_CallFunction':continue
        # Both targets must point at the native inherited StaticMeshComponent.
        mat=node.find_input_pin('Material');slot=node.find_input_pin('ElementIndex')
        if not mat.is_valid() or not slot.is_valid():continue
        target=node.find_self_pin()
        if not target.is_valid():raise RuntimeError('Missing material operation target')
        if target.list_connected_pins():continue
        getter=e.add_get_member_variable_node('StaticMeshComponent','/Script/Engine.StaticMeshActor')
        out=getter.find_output_pin('StaticMeshComponent')
        if not out.is_valid() or not out.try_create_connection(target):raise RuntimeError('Could not connect mesh target')
        pos=node.get_node_pos();getter.set_node_pos(unreal.IntPoint(x=pos.x-240,y=pos.y+130))
        repaired.append(node.get_name())
    if not B.compile_blueprint(bp):raise RuntimeError('Drone compilation failed')
    errors=[]
    for name in B.list_graph_names(bp):
        ed=G.get_graph_editor_by_name(bp,name)
        errors.extend(str(n.get_node_title()) for n in ed.list_nodes_with_errors())
    if errors:raise RuntimeError('Remaining graph errors: '+str(errors))
    if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Could not save drone')
    with open(report,'w',encoding='utf8') as f:json.dump(dict(saved=True,repaired_nodes=repaired,compile_errors=errors),f,indent=2)
    unreal.log('DRONE MATERIAL TARGETS REPAIRED AND SAVED')
except Exception:
    with open(report,'w',encoding='utf8') as f:json.dump(dict(error=traceback.format_exc()),f,indent=2)
    raise
