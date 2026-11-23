"""Printed, UV-mapped warning boards replace floating TextRender glyphs."""
import unreal,os,sys,shutil,datetime,json,time,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,V,save
project=os.path.abspath(unreal.Paths.project_dir());source=os.path.join(project,'SourceAssets','CampusBridge');ROOT='/Game/Surface/Bridge'
tools=unreal.AssetToolsHelpers.get_asset_tools();sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report={'saved':False,'removed_text':0,'faces':0,'gameplay_tested':False}
def imported(file,name,mesh=False):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 task=unreal.AssetImportTask()
 for k,v in dict(filename=file,destination_path=ROOT,destination_name=name,automated=True,save=True).items():task.set_editor_property(k,v)
 if mesh:
  opts=unreal.FbxImportUI()
  for k,v in dict(import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opts.set_editor_property(k,v)
  opts.static_mesh_import_data.set_editor_property('combine_meshes',True);task.set_editor_property('options',opts)
 tools.import_asset_tasks([task]);obj=A.load_asset(path)
 if not obj:raise RuntimeError('Import failed '+name)
 return obj
try:
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 backup=os.path.join(project,'Saved','Backups','BridgeSigns',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 shutil.copy2(os.path.join(project,'Content','Surface','Lvl_SurfaceArrival.umap'),os.path.join(backup,'Lvl_SurfaceArrival.umap'));report['backup']=backup
 texture=imported(os.path.join(source,'T_BridgeWarning.png'),'T_BridgeWarning')
 texture.set_editor_property('max_texture_size',1024);texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',False);save(texture)
 mat=tools.create_asset('M_BridgeWarningPrinted',ROOT,unreal.Material,unreal.MaterialFactoryNew()) if not A.does_asset_exist(ROOT+'/M_BridgeWarningPrinted') else A.load_asset(ROOT+'/M_BridgeWarningPrinted')
 M.delete_all_material_expressions(mat)
 sample=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample);sample.set_editor_property('texture',texture)
 # OBJ front-face import reverses the horizontal axis; compensate in UV space.
 uv=M.create_material_expression(mat,unreal.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',-1.)
 if not M.connect_material_expressions(uv,'',sample,'UVs'):raise RuntimeError('Warning texture UV connection rejected')
 M.connect_material_property(sample,'',unreal.MaterialProperty.MP_BASE_COLOR)
 emission=M.create_material_expression(mat,unreal.MaterialExpressionMultiply);emission.set_editor_property('const_b',.16);M.connect_material_expressions(sample,'',emission,'A');M.connect_material_property(emission,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 rough=M.create_material_expression(mat,unreal.MaterialExpressionConstant);rough.set_editor_property('r',.8);M.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
 M.recompile_material(mat);save(mat)
 # Matching OBJ handedness and V convention to the existing mesh authoring tools.
 obj='mtllib SM_WarningSignFace.mtl\no SM_WarningSignFace\n'
 for x,z in [(-80,50),(80,50),(80,-50),(-80,-50)]:obj+='v %s 0 %s\nvt %s %s\n'%(x,z,(x+80)/160,(z+50)/100)
 obj+='usemtl Warning\nf 1/1 2/2 3/3\nf 1/1 3/3 4/4\n'
 open(os.path.join(source,'SM_WarningSignFace.obj'),'w').write(obj);open(os.path.join(source,'SM_WarningSignFace.mtl'),'w').write('newmtl Warning\nKd 1 1 1\n')
 mesh=imported(os.path.join(source,'SM_WarningSignFace.obj'),'SM_WarningSignFace',True);mesh.set_material(0,mat);save(mesh)
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_SurfaceArrival')
 for actor in list(sub.get_all_level_actors()):
  label=actor.get_actor_label()
  if label.startswith(('BRIDGE_WarningText_','BRIDGE_PrintedSign_')):
   sub.destroy_actor(actor);report['removed_text']+=1
  elif label.startswith('BRIDGE_WarningPlate_'):
   c=actor.get_component_by_class(unreal.StaticMeshComponent);c.set_material(0,A.load_asset('/Game/Surface/Materials/M_RuinSteel'))
 for x in (-820,820):
  for y in (20800,24200):
   # Each side gets its own outward-facing front; text is never viewed backwards.
   for side in (-1,1):
    actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,V((x,y-8+side*4,135)),unreal.Rotator(yaw=0 if side==-1 else 180))
    actor.set_actor_label('BRIDGE_PrintedSign_%s_%s_%s'%(x,y,side));actor.set_folder_path('SURFACE/Collapsed Bridge')
    c=actor.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('NoCollision');report['faces']+=1
 report['saved']=bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
 # Export a near view after rendering, then restore the laboratory editor map.
 photo={'since':time.monotonic(),'requested':False};path=os.path.join(project,'Saved','BridgeWarningPrinted.png');old=os.path.getmtime(path) if os.path.exists(path) else 0
 def sign_photo(dt):
  if not photo['requested']:
   eye=V((-720,20440,170));editor.set_level_viewport_camera_info(eye,unreal.MathLibrary.find_look_at_rotation(eye,V((-820,20800,135))));unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
   if time.monotonic()-photo['since']>4:photo['requested']=True;unreal.AutomationLibrary.take_high_res_screenshot(1280,800,path,delay=0.)
  if photo['requested'] and os.path.exists(path) and os.path.getmtime(path)>old:
   unreal.unregister_slate_post_tick_callback(photo['handle']);unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 photo['handle']=unreal.register_slate_post_tick_callback(sign_photo)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(project,'Saved','bridge_sign_repair.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
