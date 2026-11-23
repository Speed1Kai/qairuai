"""Replace shared chair/monitor meshes using native asset imports, preserving actors."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,save,V
project=os.path.abspath(unreal.Paths.project_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
root='/Game/Environment/LabWorkstations';first='/Game/LabTutorial/FirstFloor'
tools=unreal.AssetToolsHelpers.get_asset_tools();sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
report={'saved':False,'assets':[],'gameplay_tested':False}
def imported(filename,path,mesh=False,replace=False):
 if A.does_asset_exist(path) and not replace:return A.load_asset(path)
 task=unreal.AssetImportTask()
 for k,v in dict(filename=filename,destination_path=path.rsplit('/',1)[0],destination_name=path.rsplit('/',1)[1],automated=True,save=True,replace_existing=replace).items():task.set_editor_property(k,v)
 if mesh:
  opt=unreal.FbxImportUI()
  for k,v in dict(import_mesh=True,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opt.set_editor_property(k,v)
  opt.static_mesh_import_data.set_editor_property('combine_meshes',True);opt.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
  task.set_editor_property('options',opt)
 tools.import_asset_tasks([task]);obj=A.load_asset(path)
 if not obj:raise RuntimeError('Import failed '+path)
 return obj
def material(name):
 path=root+'/'+name
 m=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,root,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m);return m
def node(m,cls,**kw):
 n=M.create_material_expression(m,cls)
 for k,v in kw.items():n.set_editor_property(k,v)
 return n
try:
 A.make_directory(root)
 backup=os.path.join(project,'Saved','Backups','Workstations',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);report['backup']=backup
 paths=[first+'/SM_ModernChair',first+'/SM_ModernConsole','/Game/LabTutorial/Industrial/SM_IndustrialWorkbench']
 for path in paths:
  filename=os.path.join(content,path.removeprefix('/Game/')+'.uasset')
  if os.path.exists(filename):shutil.copy2(filename,os.path.join(backup,os.path.basename(filename)))
 # A shared photographed PBR chair, using 1K maps and DirectX normal convention.
 source=os.path.join(project,'SourceAssets','PolyHaven','SchoolChair_01','1k')
 manifest=json.load(open(os.path.join(source,'asset_manifest.json'),encoding='utf8'));textures={}
 for row in manifest['files']:
  relative=row['path'];lower=relative.lower()
  role=next((role for token,role in [('diff','Color'),('nor_gl','Normal'),('metal','Metal'),('rough','Roughness')] if token in lower),None)
  if not role or lower.endswith('.fbx'):continue
  tex=imported(os.path.join(source,relative),root+'/T_Chair_'+role)
  tex.set_editor_property('max_texture_size',1024);tex.set_editor_property('never_stream',False)
  tex.set_editor_property('srgb',role=='Color')
  tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else unreal.TextureCompressionSettings.TC_DEFAULT if role=='Color' else unreal.TextureCompressionSettings.TC_MASKS)
  if role=='Normal':tex.set_editor_property('flip_green_channel',True)
  save(tex);textures[role]=tex
 chairmat=material('M_LabChair_PBR')
 for role,prop in [('Color',unreal.MaterialProperty.MP_BASE_COLOR),('Normal',unreal.MaterialProperty.MP_NORMAL),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS),('Metal',unreal.MaterialProperty.MP_METALLIC)]:
  if role not in textures:continue
  n=node(chairmat,unreal.MaterialExpressionTextureSample,texture=textures[role],sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='Color' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
  M.connect_material_property(n,'' if role in ('Color','Normal') else 'R',prop)
 M.set_material_usage(chairmat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(chairmat);save(chairmat)
 display=material('M_WorkstationDisplay');display.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 base=node(display,unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(.006,.045,.065,1))
 M.connect_material_property(base,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.set_material_usage(display,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(display);save(display)
 chair=imported(os.path.join(source,'SchoolChair_01_1k.fbx'),paths[0],True,True)
 for i in range(len(chair.static_materials)):chair.set_material(i,chairmat)
 sms.remove_collisions(chair);sms.add_simple_collisions(chair,unreal.ScriptingCollisionShapeType.BOX);save(chair)
 bounds=chair.get_bounds();report['assets'].append({'path':chair.get_path_name(),'height_cm':bounds.box_extent.z*2,'source':manifest['source']})
 specs=json.load(open(os.path.join(project,'SourceAssets','LabWorkstations','workstations.json')))
 for spec in specs:
  name=spec['name'];path=first+'/'+name if name=='SM_ModernConsole' else '/Game/LabTutorial/Industrial/'+name
  mesh=imported(os.path.join(project,'SourceAssets','LabWorkstations',name+'.obj'),path,True,True)
  for i,slot in enumerate(mesh.static_materials):
   n=str(slot.material_slot_name)
   mat=display if n=='M_WorkstationDisplay' else A.load_asset(first+'/'+n) if A.does_asset_exist(first+'/'+n) else A.load_asset('/Game/LabTutorial/Industrial/'+n)
   if not mat:raise RuntimeError('Missing material '+n)
   mesh.set_material(i,mat)
  save(mesh);report['assets'].append({'path':path,'vertices':spec['vertices']})
 # Existing component material overrides must not retain the old shared palette.
 actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 counts={}
 for a in actors.get_all_level_actors():
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   mesh=c.static_mesh
   if mesh and mesh.get_path_name().split('.')[0] in paths:
    for i,slot in enumerate(mesh.static_materials):c.set_material(i,slot.material_interface)
    counts[mesh.get_name()]=counts.get(mesh.get_name(),0)+(c.get_instance_count() if isinstance(c,unreal.InstancedStaticMeshComponent) else 1)
 report['placed_counts']=counts
 report['saved']=bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','workstations_update.json'),'w',encoding='utf8') as f:json.dump(report,f,indent=2,ensure_ascii=False)
