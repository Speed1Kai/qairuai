import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,save
assert not unreal.EditorLevelLibrary.get_game_world()
ROOT='/Game/Enemies/Enceladus';A.make_directory(ROOT)
path=ROOT+'/SM_EnceladusSource'
if not A.does_asset_exist(path):
 opt=unreal.FbxImportUI()
 for k,v in dict(import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opt.set_editor_property(k,v)
 opt.static_mesh_import_data.set_editor_property('combine_meshes',True);opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
 task=unreal.AssetImportTask()
 for k,v in dict(filename='C:/Users/nuris/Downloads/Enceladus(1).fbx',destination_path=ROOT,destination_name='SM_EnceladusSource',options=opt,automated=True,save=True).items():task.set_editor_property(k,v)
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=A.load_asset(path);b=mesh.get_bounding_box()
R={'bounds':str(b),'materials':[str(s.material_slot_name) for s in mesh.static_materials]}
R['skeletal_subsystem']={n:getattr(unreal.SkeletalMeshEditorSubsystem,n).__doc__ for n in dir(unreal.SkeletalMeshEditorSubsystem) if 'create' in n.lower() or 'static' in n.lower()}
R['geometry_classes']=[n for n in dir(unreal) if 'GeometryScript' in n and any(k in n for k in ('Bone','Skin','Asset','Skeletal'))]
R['player_input_nodes']=[]
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
for n in unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph').list_all_nodes():
 if any(s in str(n.get_node_title()) for s in ('Mouse','Attack','Fire','IA_')):R['player_input_nodes'].append(str(n.get_node_title()))
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'enceladus_ue_inspect.json'),'w'),indent=2)
