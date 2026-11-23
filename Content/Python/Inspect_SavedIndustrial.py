"""Read the authored map and packages back from disk; write a compact inventory."""
import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
r={'actors':{},'blueprints':{},'meshes':{},'niagara':[]}
actors=unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
 n=a.get_actor_label()
 if n.startswith(('IND_','INTRO_')) or n=='LAB_PlayerStart':
  q=a.get_actor_rotation();r['actors'][n]={'p':xyz(a.get_actor_location()),'r':(q.pitch,q.yaw,q.roll)}
  if n=='IND_InstancedDressing':r['instances']={c.get_name():c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)}
 if a.get_component_by_class(unreal.ExponentialHeightFogComponent):r['volumetric_fog']=a.get_component_by_class(unreal.ExponentialHeightFogComponent).get_editor_property('enable_volumetric_fog')
r['old_door_present']=any(a.get_actor_label()=='LAB_Door_Closed_Blockout' for a in actors)
for name in ('BP_HeavyBlastDoor','BP_BlastDoorImpactShake','BP_CapsulePressureVent','BP_IndustrialDressing'):
 bp=A.load_asset(ROOT+'/'+name);compile_bp(bp)
 row={'components':{},'nodes':[]}
 for h,c,n in components(bp):
  if isinstance(c,unreal.ActorComponent):
   row['components'][n]={'class':c.get_class().get_name()}
   if isinstance(c,unreal.PrimitiveComponent):row['components'][n]['collision']=str(c.get_collision_profile_name())
   if isinstance(c,unreal.SceneComponent):row['components'][n]['parent']=c.get_attach_parent().get_name() if c.get_attach_parent() else None
 for gn in B.list_graph_names(bp):
  e=G.get_graph_editor_by_name(bp,gn)
  for node in e.list_all_nodes():
   if node.get_class().get_name()=='K2Node_Timeline':
    row['timeline_pins']={str(p.get_pin_name()):len(p.list_connected_pins()) for p in node.list_all_pins()}
 for t in unreal.ObjectIterator(unreal.TimelineTemplate):
  if t.get_outer()==B.generated_class(bp):row['timeline_length']=t.get_editor_property('timeline_length')
 r['blueprints'][name]=row
for i in range(1,7):
 bp=A.load_asset('/Game/LabTutorial/Holograms/BP_ArchiveProjector_%02d'%i);compile_bp(bp)
 r['blueprints'][bp.get_name()]={'compiled':True}
for path in A.list_assets(ROOT,recursive=False,include_folder=False):
 a=A.load_asset(path)
 if isinstance(a,unreal.StaticMesh):
  b=a.get_bounds();r['meshes'][a.get_name()]={'origin':xyz(b.origin),'extent':xyz(b.box_extent),'materials':[str(m.get_editor_property('material_slot_name')) for m in a.get_editor_property('static_materials')]}
system=A.load_asset(ROOT+'/NS_PressureVent')
for o in unreal.ObjectIterator(unreal.Object):
 if isinstance(o,type):continue
 if unreal.SystemLibrary.get_path_name(o).startswith(system.get_path_name()+':') and o.get_class().get_name()=='NiagaraStatelessEmitter':
  r['niagara'].append({'spawn':[str(x.get_editor_property('Amount')) for x in o.get_editor_property('SpawnInfos')],'renderers':[str(x.get_editor_property('material')) for x in o.get_editor_property('RendererProperties') if x.get_class().get_name()=='NiagaraSpriteRendererProperties']})
r['actor_count']=len(actors);r['compiled']=True
with open(os.path.join(unreal.Paths.project_saved_dir(),'industrial_saved_inventory.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
unreal.log('SAVED INDUSTRIAL INVENTORY: '+str(len(actors))+' actors, '+str(sum(r.get('instances',{}).values()))+' decorative instances, compiled packages')
