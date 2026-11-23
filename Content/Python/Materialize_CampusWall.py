"""Build the supplied wall's PBR materials and a static visual preview."""
import unreal,os,sys,json,traceback,time
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,V,save
ROOT='/Game/Surface/CampusWall';source=os.path.abspath(unreal.Paths.project_dir()+'SourceAssets/CampusWall')
report={'saved':False,'gameplay_tested':False}
try:
 tools=unreal.AssetToolsHelpers.get_asset_tools();mesh=A.load_asset(ROOT+'/SM_Wall_A_Long')
 mats={}
 for name in ['tech_panel_b','concrete_b','concrete_a','metal_c','metal_b']:
  textures={}
  for role in ['Diffuse','Normal','Glossiness']:
   label='T_Wall_'+name+'_'+role;path=ROOT+'/Textures/'+label
   if not A.does_asset_exist(path):
    task=unreal.AssetImportTask()
    for k,v in dict(filename=os.path.join(source,name+'_'+role+'.png'),destination_path=ROOT+'/Textures',destination_name=label,automated=True,save=True).items():task.set_editor_property(k,v)
    tools.import_asset_tasks([task])
   t=A.load_asset(path);t.set_editor_property('max_texture_size',2048);t.set_editor_property('never_stream',False)
   t.set_editor_property('srgb',role=='Diffuse')
   t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else unreal.TextureCompressionSettings.TC_DEFAULT if role=='Diffuse' else unreal.TextureCompressionSettings.TC_MASKS)
   save(t);textures[role]=t
  label='M_Wall_'+name;path=ROOT+'/Materials/'+label
  mat=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(label,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
  M.delete_all_material_expressions(mat)
  for role,prop in [('Diffuse',unreal.MaterialProperty.MP_BASE_COLOR),('Normal',unreal.MaterialProperty.MP_NORMAL)]:
   n=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
   n.set_editor_property('texture',textures[role]);n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
   if not M.connect_material_property(n,'RGB',prop):raise RuntimeError('Material connection failed')
  gloss=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample);gloss.set_editor_property('texture',textures['Glossiness']);gloss.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
  invert=M.create_material_expression(mat,unreal.MaterialExpressionSubtract);invert.set_editor_property('const_a',1.)
  multiply=M.create_material_expression(mat,unreal.MaterialExpressionMultiply);multiply.set_editor_property('const_b',.75)
  add_rough=M.create_material_expression(mat,unreal.MaterialExpressionAdd);add_rough.set_editor_property('const_b',.2)
  for src,out,dst,input_name in [(gloss,'R',invert,'B'),(invert,'',multiply,'A'),(multiply,'',add_rough,'A')]:
   if not M.connect_material_expressions(src,out,dst,input_name):raise RuntimeError('Glossiness conversion failed '+input_name)
  if not M.connect_material_property(add_rough,'',unreal.MaterialProperty.MP_ROUGHNESS):raise RuntimeError('Roughness connection failed')
  metal=M.create_material_expression(mat,unreal.MaterialExpressionConstant);metal.set_editor_property('r',0. if name.startswith('concrete') else .75)
  M.connect_material_property(metal,'',unreal.MaterialProperty.MP_METALLIC);M.recompile_material(mat);save(mat);mats['tenzero_tex_'+name]=mat
 for i,s in enumerate(mesh.static_materials):mesh.set_material(i,mats[str(s.material_slot_name)])
 sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
 if sms.get_lod_count(mesh)<4:
  options=unreal.StaticMeshReductionOptions();options.set_editor_property('auto_compute_lod_screen_size',False)
  reductions=[]
  for fraction,screen in [(1.,1.),(.45,.28),(.16,.12),(.055,.045)]:
   reduction=unreal.StaticMeshReductionSettings();reduction.set_editor_property('percent_triangles',fraction);reduction.set_editor_property('screen_size',screen);reductions.append(reduction)
  options.set_editor_property('reduction_settings',reductions)
  if sms.set_lods(mesh,options)<4:raise RuntimeError('Wall LOD generation failed')
 sms.remove_collisions(mesh)
 if sms.add_simple_collisions(mesh,unreal.ScriptCollisionShapeType.BOX)<0:raise RuntimeError('Wall simple collision failed')
 save(mesh)
 bounds=mesh.get_bounding_box();height=bounds.max.z-bounds.min.z;scale=500./height
 report.update(saved=True,lods=sms.get_lod_count(mesh),scale=scale,dimensions_cm=[(bounds.max.x-bounds.min.x)*scale,(bounds.max.y-bounds.min.y)*scale,500.],materials=list(mats.keys()))
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(unreal.Paths.project_saved_dir(),'campus_wall_materials.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Wall material authoring incomplete')
