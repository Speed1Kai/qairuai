"""Register the supplied pack and inventory its assembled source city.

Only pack texture copies are adjusted. No game level or source demo is saved.
"""
import unreal,os,sys,json,traceback,collections
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,save
ROOT='/Game/CityDowntown';report={'complete':False,'gameplay_tested':False}
def vec(v):return [v.x,v.y,v.z]
def transform(t):
 r=t.rotation.rotator()
 return {'location':vec(t.translation),'rotation':[r.pitch,r.yaw,r.roll],'scale':vec(t.scale3d)}
try:
 registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.scan_paths_synchronous([ROOT],force_rescan=True)
 assets=registry.get_assets_by_path(ROOT,recursive=True)
 report['asset_classes']=dict(collections.Counter(str(a.asset_class_path.asset_name) for a in assets))
 report['texture_changes']=0
 # Bound the selected pack's streaming budget before its demonstration map can
 # request every original 4K/8K texture. Keep source copies on S:/Content intact.
 metadata_only=os.path.isfile(os.path.join(unreal.Paths.project_saved_dir(),'Downtown_MetadataOnly.flag'))
 for data in ([] if metadata_only else assets):
  cls=str(data.asset_class_path.asset_name)
  if cls not in ('Texture2D','TextureCube'):continue
  texture=data.get_asset();limit=512 if cls=='TextureCube' else 2048
  try:
   texture.set_editor_property('max_texture_size',limit)
   texture.set_editor_property('never_stream',False)
   save(texture);report['texture_changes']+=1
  except Exception as e:report.setdefault('texture_notes',[]).append(str(e))
 if not metadata_only and not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Could not preserve current map')
 unreal.EditorLoadingAndSavingUtils.load_map(ROOT+'/Scenes/Downtown_Day')
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 actors=sub.get_all_level_actors();report['actor_classes']=dict(collections.Counter(a.get_class().get_name() for a in actors))
 rows=[]
 for actor in actors:
  components=[]
  for c in actor.get_components_by_class(unreal.StaticMeshComponent):
   if not c.static_mesh:continue
   base={'mesh':c.static_mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],'collision':str(c.get_collision_profile_name())}
   if isinstance(c,unreal.InstancedStaticMeshComponent):
    transforms=[transform(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())]
   else:transforms=[transform(c.get_world_transform())]
   base['transforms']=transforms;components.append(base)
  if components:
   origin,extent=actor.get_actor_bounds(False)
   rows.append({'name':actor.get_actor_label(),'folder':str(actor.get_folder_path()),'class':actor.get_class().get_name(),'location':vec(actor.get_actor_location()),'origin':vec(origin),'extent':vec(extent),'components':components})
 report['actors']=rows;report['complete']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(unreal.Paths.project_saved_dir(),'citydowntown_source_inventory.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
