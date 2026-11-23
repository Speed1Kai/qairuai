"""Finish native surface material wiring and save the authored environment."""
import unreal,os,sys,json,textwrap
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,V,save
for name in ['M_RisingSmoke','M_SmallFire']:
 m=A.load_asset('/Game/Surface/Materials/'+name)
 custom=next(x for x in unreal.ObjectIterator(unreal.MaterialExpressionCustom) if x.get_outer()==m)
 for mask in unreal.ObjectIterator(unreal.MaterialExpressionComponentMask):
  if mask.get_outer()==m:
   if not M.connect_material_expressions(custom,'',mask,''):raise RuntimeError('Mask connection failed '+name)
 M.recompile_material(m);save(m)
path=os.path.join(os.path.dirname(__file__),'Build_SurfaceArrival.py');src=open(path,encoding='utf8').read();ctx={'__file__':path}
exec(compile(src.split('\ntry:\n')[0],path,'exec'),ctx)
def spawn(cls,name,p,rot=None):
 a=ctx['sub'].spawn_actor_from_class(cls,V(p),rot or unreal.Rotator());a.set_actor_label('SURF_'+name);a.set_folder_path('SURFACE/Arrival');return a
ctx.update(spawn=spawn,wind=A.load_asset('/Game/Surface/S_SurfaceWind'),mats={},count=0,batches={},buildings=[None]*20,specs=json.load(open('S:/Final_Protocol/Content/Surface/Source/surface_kit.json')))
ctx['r']=json.load(open('S:/Final_Protocol/Saved/surface_arrival_report.json',encoding='utf8'));ctx['r'].pop('error',None)
tail=src[src.index(' pp=spawn(unreal.PostProcessVolume'):src.index('\nexcept Exception:r[')]
exec(compile(textwrap.dedent(tail),path,'exec'),ctx)
env=A.load_asset('/Game/Surface/BP_SurfaceEnvironment');cdo=unreal.get_default_object(B.generated_class(env));cs=cdo.get_components_by_class(unreal.InstancedStaticMeshComponent)
ctx['r']['counts']['instances']=sum(c.get_instance_count() for c in cs);ctx['r']['counts']['batches']=len(cs)
with open('S:/Final_Protocol/Saved/surface_arrival_report.json','w',encoding='utf8') as f:json.dump(ctx['r'],f,ensure_ascii=False,indent=2)
