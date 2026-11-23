"""Persist material support for the new instanced environment batches."""
import unreal,os,sys,json,shutil,datetime
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,components,save
bp=A.load_asset('/Game/Environment/DowntownFirstBlock/BP_FirstCityBlock')
objects={}
for h,c,n in components(bp):
 if not isinstance(c,unreal.StaticMeshComponent):continue
 for i in range(c.get_num_materials()):
  mat=c.get_material(i)
  if mat:objects[mat.get_path_name()]=mat
for path in A.list_assets('/Game/Surface/CampusWall/Materials',recursive=True):
 mat=A.load_asset(path)
 if isinstance(mat,unreal.MaterialInterface):objects[mat.get_path_name()]=mat
backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups','DowntownMaterialUsage',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True)
saved=[]
for mat in objects.values():
 path=mat.get_path_name().split('.')[0];rel=path.removeprefix('/Game/')+'.uasset'
 src=os.path.join(unreal.Paths.project_content_dir(),rel)
 if os.path.isfile(src):
  dst=os.path.join(backup,rel);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
 if isinstance(mat,unreal.Material):
  mat.set_editor_property('used_with_instanced_static_meshes',True);M.recompile_material(mat)
 elif isinstance(mat,unreal.MaterialInstanceConstant):
  M.set_material_usage_override(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True,True)
  M.update_material_instance(mat)
 save(mat);saved.append(path)
with open(os.path.join(unreal.Paths.project_saved_dir(),'downtown_material_usage.json'),'w',encoding='utf8') as f:json.dump({'saved':True,'materials':saved},f,indent=2)
