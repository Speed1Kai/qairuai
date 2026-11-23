import unreal,os,sys,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,save
ROOT='/Game/Surface/CampusWall';r={'saved':False}
try:
 A.make_directory(ROOT)
 path=ROOT+'/SM_Wall_A_Long'
 if not A.does_asset_exist(path):
  opts=unreal.FbxImportUI()
  for k,v in dict(import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opts.set_editor_property(k,v)
  data=opts.static_mesh_import_data
  for k,v in dict(combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True).items():data.set_editor_property(k,v)
  task=unreal.AssetImportTask()
  for k,v in dict(filename=os.path.abspath(unreal.Paths.project_dir()+'SourceAssets/CampusWall/Wall_A_Long.fbx'),destination_path=ROOT,destination_name='SM_Wall_A_Long',options=opts,automated=True,save=True).items():task.set_editor_property(k,v)
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 mesh=A.load_asset(path)
 if not mesh:raise RuntimeError('Wall mesh import failed')
 bounds=mesh.get_bounding_box()
 r.update(saved=True,mesh=mesh.get_path_name(),bounds_min=str(bounds.min),bounds_max=str(bounds.max),slots=[str(s.material_slot_name) for s in mesh.static_materials],vertices=mesh.get_num_vertices(0))
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(unreal.Paths.project_saved_dir(),'campus_wall_import.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
