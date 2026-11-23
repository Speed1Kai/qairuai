"""Surface lighting/composition pass; editor authoring, no gameplay execution."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,V,components,compile_bp,save
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
bp=A.load_asset('/Game/Surface/BP_SurfaceEnvironment')
for h,c,n in components(bp):
 if not c:continue
 if n=='Boxes_M_Charcoal_Block':c.set_visibility(False);c.set_hidden_in_game(True);c.set_editor_property('cast_shadow',False)
 if n=='SM_ArchitectTower':c.update_instance_transform(0,unreal.Transform(location=V((5400,90000,0)),scale=V((1,1,.86))),False,True,True)
compile_bp(bp);save(bp)
def composition(c):
 mesh=c.static_mesh
 if not mesh:return
 if mesh.get_name()=='SM_Ruin_B' and c.get_instance_count()>0:
  t=c.get_instance_transform(0,False);t.rotation=unreal.Quat() if False else unreal.Rotator(pitch=4,yaw=t.rotation.rotator().yaw,roll=-10).quaternion();c.update_instance_transform(0,t,False,True,True)
 if c.get_material(0) and c.get_material(0).get_name()=='M_RisingSmoke':
  positions=[(-1750,6800,4700,2600,9400),(1900,10500,6500,3400,13000),(-7000,17500,10000,4400,20000),(9300,25000,9000,4300,18000),(-14000,34000,11000,5000,22000),(1900,36500,10000,4200,20000)]
  for i,(x,y,z,w,h) in enumerate(positions):
   for j,angle in enumerate((0,75)):c.update_instance_transform(i*2+j,unreal.Transform(location=V((x,y,z)),rotation=unreal.Rotator(yaw=angle,roll=90),scale=V((w/100,h/100,1))),False,True,True)
for handle,c,n in components(bp):
 if c and isinstance(c,unreal.InstancedStaticMeshComponent):composition(c)
compile_bp(bp);save(bp)
for a in sub.get_all_level_actors():
 label=a.get_actor_label()
 if label=='SURF_Environment':
  for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
   mesh=c.static_mesh;mat=c.get_material(0)
   if mesh and mesh.get_name()=='Cube' and mat and mat.get_name()=='M_Charcoal':c.set_visibility(False);c.set_hidden_in_game(True);c.set_editor_property('cast_shadow',False)
   if mesh and mesh.get_name()=='SM_ArchitectTower':c.update_instance_transform(0,unreal.Transform(location=V((5400,90000,0)),scale=V((1,1,.86))),False,True,True)
   composition(c)
 if label=='SURF_LateSun':a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(6.)
 if label=='SURF_SkyFill':a.get_component_by_class(unreal.SkyLightComponent).set_intensity(2.)
 if label=='SURF_AshHaze':
  c=a.get_component_by_class(unreal.ExponentialHeightFogComponent)
  for k,v in [('fog_density',.002),('fog_max_opacity',.6),('start_distance',3500.)]:c.set_editor_property(k,v)
 if label=='SURF_SurfaceGrade':
  s=a.get_editor_property('settings')
  for k,v in [('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.),('auto_exposure_bias',1.)]:s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
  a.set_editor_property('settings',s)
# Deep soot staining and vertical streaks share the existing procedural noise.
m=A.load_asset('/Game/Surface/Materials/M_RuinConcrete')
for q in unreal.ObjectIterator(unreal.MaterialExpressionCustom):
 if q.get_outer()==m:
  code=q.get_editor_property('code')
  if 'SURFACE_SCORCH' not in code:
   code=code.replace('return float3(', '/* SURFACE_SCORCH */ float soot=smoothstep(.33,.7,n.n(float2(P.x+P.y*.73,P.z)*.0014));float streak=n.n(float2((P.x+P.y)*.028,P.z*.0012));return lerp(.18,1.,soot)*(.68+.32*streak)*float3(');q.set_editor_property('code',code)
M.recompile_material(m);save(m)
editor.set_level_viewport_camera_info(V((0,300,590)),unreal.Rotator(pitch=6,yaw=90))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
unreal.EditorLoadingAndSavingUtils.save_current_level()
path=os.path.join(unreal.Paths.project_saved_dir(),'surface_arrival_report.json')
with open(path,encoding='utf8') as f:r=json.load(f)
envactor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='SURF_Environment');cs=envactor.get_components_by_class(unreal.InstancedStaticMeshComponent)
r['counts']['instances']=sum(c.get_instance_count() for c in cs);r['counts']['batches']=len(cs)
r.update(polished=True,tower_world_cm=[5400,90000,0])
with open(path,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
