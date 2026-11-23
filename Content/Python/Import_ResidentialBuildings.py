"""Import supplied residential exteriors through native Unreal asset APIs.

Original files remain untouched. Run from the existing editor, outside PIE.
"""
import unreal, os, sys, shutil, json, datetime, traceback
sys.path.insert(0, os.path.dirname(__file__))
from Industrial_Common import A, M, save
ROOT='/Game/Environment/Residential'
project=os.path.abspath(unreal.Paths.project_dir())
source=os.path.join(project,'SourceAssets','Residential')
os.makedirs(source,exist_ok=True)
tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'meshes':[],'textures':[],'complete':False}
out=os.path.join(project,'Saved','residential_import.json')
def write():
 with open(out,'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
def imported(filename,name,folder,options=None):
 path=ROOT+'/'+folder+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 dest=os.path.join(source,os.path.basename(filename))
 if not os.path.exists(dest):shutil.copy2(filename,dest)
 task=unreal.AssetImportTask()
 for k,v in dict(filename=dest,destination_path=ROOT+'/'+folder,destination_name=name,automated=True,save=True,replace_existing=False).items():task.set_editor_property(k,v)
 if options:task.set_editor_property('options',options)
 tools.import_asset_tasks([task])
 paths=list(task.get_editor_property('imported_object_paths'))
 obj=A.load_asset(path) if A.does_asset_exist(path) else next((A.load_asset(p) for p in paths if A.load_asset(p)),None)
 if not obj:raise RuntimeError('Import produced no asset: '+filename)
 return obj
try:
 for folder in ['Meshes','Textures','Materials']:A.make_directory(ROOT+'/'+folder)
 tex={}
 for filename,name,normal,linear,limit in [('Steel_C.jpg','T_Facade_Color',False,False,2048),('Steel_N.jpg','T_Facade_Normal',True,True,2048),('Steel_S.jpg','T_Facade_Specular',False,True,1024),('Hotel_Hous_AO.png','T_Building_AO',False,True,2048)]:
  t=imported('S:/textures/'+filename,name,'Textures')
  t.set_editor_property('max_texture_size',limit)
  t.set_editor_property('srgb',not linear)
  t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT)
  t.set_editor_property('never_stream',False);save(t);tex[name]=t
  report['textures'].append({'path':t.get_path_name(),'max_size':limit});write()
 for i in range(1,11):
  opts=unreal.FbxImportUI()
  for k,v in dict(import_mesh=True,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opts.set_editor_property(k,v)
  opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
  opts.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
  mesh=imported('S:/fbx/Residential Buildings %03d.fbx'%i,'SM_Residential_%03d'%i,'Meshes',opts)
  bounds=mesh.get_bounds()
  report['meshes'].append({'index':i,'path':mesh.get_path_name(),'origin':[bounds.origin.x,bounds.origin.y,bounds.origin.z],'extent':[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],'slots':[str(s.material_slot_name) for s in mesh.static_materials]})
  write()
 report['complete']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:write()
