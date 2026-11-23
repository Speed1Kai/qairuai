"""Import an optional user-supplied FBX/GLB; never guess rig compatibility.

Set model_file in RobotSettings.json or PROTOCOL_ROBOT_MODEL before invoking
this editor script. Unrigged files are reported rather than made playable.
"""
import unreal,os,json
content=os.path.abspath(unreal.Paths.project_content_dir())
config_path=os.path.join(content,'Characters','ProtocolRobot','Config','RobotSettings.json')
cfg=json.load(open(config_path,encoding='utf8'))
filename=os.environ.get('PROTOCOL_ROBOT_MODEL') or cfg.get('model_file','')
if not filename:raise RuntimeError('Set model_file in RobotSettings.json to the full FBX/GLB filename.')
filename=os.path.abspath(filename)
if not os.path.isfile(filename):raise FileNotFoundError(filename)
extension=os.path.splitext(filename)[1].lower()
if extension not in ('.fbx','.glb'):raise ValueError('Supported model sources: .fbx and .glb')
destination='/Game/Characters/ProtocolRobot/Imported'
task=unreal.AssetImportTask()
for key,value in {'filename':filename,'destination_path':destination,'automated':True,'save':True,'replace_existing':False}.items():task.set_editor_property(key,value)
if extension=='.fbx':
 options=unreal.FbxImportUI()
 for key,value in {'import_as_skeletal':True,'import_mesh':True,'import_animations':True,'import_materials':False,'import_textures':False,'automated_import_should_detect_type':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_SKELETAL_MESH}.items():options.set_editor_property(key,value)
 task.set_editor_property('options',options)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
meshes=[unreal.load_asset(path) for path in task.get_editor_property('imported_object_paths')]
meshes=[asset for asset in meshes if isinstance(asset,unreal.SkeletalMesh)]
if not meshes:raise RuntimeError('No skeletal mesh imported. The source must contain a skin and bones; GLB also requires the installed Unreal Interchange importer.')
model=meshes[0]
metal=unreal.load_asset('/Game/Characters/ProtocolRobot/Materials/M_RobotGunmetal');red=unreal.load_asset('/Game/Characters/ProtocolRobot/Materials/M_RobotRed')
slots=model.get_editor_property('materials')
for slot in slots:
 name=str(slot.get_editor_property('material_slot_name')).lower()
 slot.set_editor_property('material_interface',red if any(word in name for word in ('emiss','glow','eye','core','light')) else metal)
model.set_editor_property('materials',slots);unreal.EditorAssetLibrary.save_loaded_asset(model,only_if_is_dirty=False)
bounds=model.get_bounds();height=max(1.,bounds.box_extent.z*2);scale=float(cfg['target_height_cm'])/height
reference=unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
report={'asset':model.get_path_name(),'source':filename,'height_scale':scale,'mesh_offset_z':-(bounds.origin.z-bounds.box_extent.z)*scale,'manny_skeleton_match':model.get_editor_property('skeleton')==reference.get_editor_property('skeleton'),'applied_to_player':False}
# These scale/pivot values normalize the feet to z=0 and height to 200 cm.
# Preserve the existing playable model until the imported rig is retargeted.
with open(os.path.join(unreal.Paths.project_saved_dir(),'protocol_robot_import.json'),'w',encoding='utf8') as f:json.dump(report,f,indent=2)
unreal.log('Robot imported. Scale/pivot and skeleton compatibility are in Saved/protocol_robot_import.json. Retarget an incompatible skeleton before assigning it to the player.')
