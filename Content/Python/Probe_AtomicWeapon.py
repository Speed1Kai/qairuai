import unreal, os, sys, json, traceback, shutil
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
P=os.path.abspath(unreal.Paths.project_dir()); R={}; D='/Game/Combat/AtomicWeapon'
try:
 A.make_directory(D);os.makedirs(P+'/SourceAssets/AtomicWeapon',exist_ok=True)
 shutil.copy2('C:/Users/nuris/Downloads/gun4.fbx',P+'/SourceAssets/AtomicWeapon/gun4.fbx')
 t=unreal.AssetImportTask();o=unreal.FbxImportUI()
 for k,v in dict(import_mesh=True,import_as_skeletal=False,import_animations=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():o.set_editor_property(k,v)
 o.static_mesh_import_data.set_editor_property('combine_meshes',True);o.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
 for k,v in dict(filename=P+'/SourceAssets/AtomicWeapon/gun4.fbx',destination_path=D,destination_name='SM_AtomicGun',automated=True,save=True,options=o).items():t.set_editor_property(k,v)
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);R['imported']=list(t.imported_object_paths)
 m=A.load_asset(D+'/SM_AtomicGun');R['gun_bounds']=str(m.get_bounds());R['gun_materials']=[str(x.material_slot_name) for x in m.static_materials]
 bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 R['components']=[{'name':n,'class':c.get_class().get_name(),'mesh':str(c.get_skinned_asset()) if isinstance(c,unreal.SkinnedMeshComponent) else '', 'loc':str(c.get_editor_property('relative_location')) if isinstance(c,unreal.SceneComponent) else ''} for h,c,n in components(bp) if c]
 R['graphs']=list(map(str,B.list_graph_names(bp)))
 for gn in ('AnimGraph',):
  ab=A.load_asset('/Game/Characters/BlackSentinel/Animations/BS_ABP_PlayerGuard');e=G.get_graph_editor_by_name(ab,gn)
  R['anim_nodes']=[{'name':n.get_name(),'class':n.get_class().get_name(),'title':str(n.get_node_title()),'pins':[str(p.get_pin_name()) for p in n.list_all_pins()]} for n in e.list_all_nodes()]
 R['geometry_classes']=[x for x in dir(unreal) if 'GeometryScript' in x and any(y in x for y in ('Asset','MeshSelection','MeshEdit','Scene','MeshQuery'))]
 for cl in R['geometry_classes']:
  cls=getattr(unreal,cl);R[cl]={n:getattr(cls,n).__doc__ for n in dir(cls) if any(x in n for x in ('copy_mesh','select_mesh','delete_selected','get_vertex','create_new','triangle')) and callable(getattr(cls,n))}
 R['pose_api']={n:getattr(unreal.AnimPoseExtensions,n).__doc__ for n in dir(unreal.AnimPoseExtensions) if not n.startswith('_')}
 R['anim_api']={n:getattr(unreal.AnimSequence,n).__doc__ for n in dir(unreal.AnimSequence) if 'pose' in n}
except Exception:R['error']=traceback.format_exc()
json.dump(R,open(P+'/Saved/atomic_probe.json','w'),indent=2,default=str)
