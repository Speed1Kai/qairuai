"""Import the supplied AeroPod with its PBR textures, then place in both city maps."""
import unreal, os, json, shutil, datetime, traceback, hashlib
A=unreal.EditorAssetLibrary; M=unreal.MaterialEditingLibrary
ROOT='/Game/City/Props/LunarAeroPod'
SRC='S:/Meshy_AI_Lunar_AeroPod_20261102_texture_fbx'
BASE='Meshy_AI_Lunar_AeroPod_20261102_texture'
S=os.path.abspath(unreal.Paths.project_saved_dir())
R={'complete':False}
def v(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def save(a):assert A.save_loaded_asset(a,only_if_is_dirty=False),a
def sha(p):return hashlib.sha256(open(p,'rb').read()).hexdigest()
try:
 assert not unreal.EditorLevelLibrary.get_game_world()
 lab=os.path.join(unreal.Paths.project_content_dir(),'Lvl_LabTutorial.umap');before=sha(lab)
 backup=os.path.join(S,'Backups/CityAeroPod',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 tools=unreal.AssetToolsHelpers.get_asset_tools();A.make_directory(ROOT)
 mesh=A.load_asset(ROOT+'/SM_LunarAeroPod') if A.does_asset_exist(ROOT+'/SM_LunarAeroPod') else None
 if not mesh:
  opt=unreal.FbxImportUI()
  for k,val in dict(import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opt.set_editor_property(k,val)
  opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
  opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
  task=unreal.AssetImportTask()
  for k,val in dict(filename=SRC+'/'+BASE+'.fbx',destination_path=ROOT,destination_name='SM_LunarAeroPod',options=opt,automated=True,save=True).items():task.set_editor_property(k,val)
  tools.import_asset_tasks([task]);mesh=A.load_asset(ROOT+'/SM_LunarAeroPod')
 assert isinstance(mesh,unreal.StaticMesh)
 tex={}
 for role,suffix in [('BaseColor',''),('Normal','_normal'),('Metallic','_metallic'),('Roughness','_roughness')]:
  name='T_AeroPod_'+role;path=ROOT+'/'+name
  t=A.load_asset(path) if A.does_asset_exist(path) else None
  if not t:
   task=unreal.AssetImportTask()
   for k,val in dict(filename=SRC+'/'+BASE+suffix+'.png',destination_path=ROOT,destination_name=name,automated=True,save=True).items():task.set_editor_property(k,val)
   tools.import_asset_tasks([task]);t=A.load_asset(path)
  assert t
  t.set_editor_property('srgb',role=='BaseColor')
  t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else unreal.TextureCompressionSettings.TC_DEFAULT if role=='BaseColor' else unreal.TextureCompressionSettings.TC_MASKS)
  t.set_editor_property('max_texture_size',2048);save(t);tex[role]=t
 mat=A.load_asset(ROOT+'/M_LunarAeroPod') if A.does_asset_exist(ROOT+'/M_LunarAeroPod') else tools.create_asset('M_LunarAeroPod',ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(mat)
 for role,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Normal',unreal.MaterialProperty.MP_NORMAL),('Metallic',unreal.MaterialProperty.MP_METALLIC),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]:
  n=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample);n.set_editor_property('texture',tex[role])
  n.set_editor_property('sampler_type',getattr(unreal.MaterialSamplerType,('SAMPLERTYPE_VIRTUAL_' if tex[role].virtual_texture_streaming else 'SAMPLERTYPE_')+('NORMAL' if role=='Normal' else 'COLOR' if role=='BaseColor' else 'MASKS')))
  assert M.connect_material_property(n,'RGB' if role in ('BaseColor','Normal') else 'R',prop)
 M.recompile_material(mat);save(mat)
 for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
 sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
 nanite=sms.get_nanite_settings(mesh)
 nanite.set_editor_property('enabled',True)
 sms.set_nanite_settings(mesh,nanite,True)
 sms.remove_collisions(mesh)
 sms.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.NDOP26)
 save(mesh)
 b=mesh.get_bounding_box();dims=b.max-b.min;scale=550/max(dims.x,dims.y)
 R.update(mesh=mesh.get_path_name(),bounds=str(b),scale=scale,material=mat.get_path_name(),textures={k:t.get_path_name() for k,t in tex.items()})
 R['maps']=[]
 for name in ('Lvl_SurfaceArrival','Lvl_CampusConnected'):
  path='/Game/Surface/'+name
  shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'Surface',name+'.umap'),backup)
  assert unreal.EditorLoadingAndSavingUtils.load_map(path)
  sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
  frame=actors['CITY_FirstDowntownBlock'].get_actor_transform()
  # Park beside the first city street; leave the street centre and combat route clear.
  local=v(520,24850,18-b.min.z*scale)
  pos=unreal.MathLibrary.transform_location(frame,local)
  actor=actors.get('CITY_LunarAeroPod') or sub.spawn_actor_from_class(unreal.StaticMeshActor,pos,unreal.Rotator(pitch=0,yaw=90,roll=0))
  actor.set_actor_label('CITY_LunarAeroPod');actor.set_folder_path('SURFACE/City Props')
  actor.set_actor_location(pos,False,False);actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0),False);actor.set_actor_scale3d(v(scale,scale,scale))
  c=actor.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll');c.set_cast_shadow(True)
  assert unreal.EditorLoadingAndSavingUtils.save_current_level()
  origin,ext=actor.get_actor_bounds(False)
  R['maps'].append(dict(map=path,actor=actor.get_path_name(),position=str(pos),origin=str(origin),extent=str(ext)))
 assert before==sha(lab),'Starting laboratory changed'
 R.update(complete=True,lab_unchanged=True,lab_sha256=before,backup=backup)
except Exception:
 R['error']=traceback.format_exc();unreal.log_error(R['error'])
finally:
 json.dump(R,open(os.path.join(S,'city_aeropod.json'),'w'),indent=2)
assert R['complete'],R
