"""Cut a permanent shaft opening in exterior ground slabs, preserving the yard."""
import unreal,os,sys,json,math,datetime,shutil
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,components,compile_bp,save,V
root=os.path.abspath(unreal.Paths.project_dir());report=json.load(open(os.path.join(root,'Saved/seamless_courtyard_report.json')));yaw=0.;off=report['offset'];corners=[]
# The existing detached ground batches translate with the streaming instance,
# but retain world yaw zero (measured in Probe_UpperShaft.py). Cut their actual
# coordinate frame, not the actor's nominal 49-degree rotation.
for x in (2250,3050):
 for y in (-380,380):
  dx=x-off[0];dy=y-off[1];corners.append((dx*math.cos(yaw)-dy*math.sin(yaw),dx*math.sin(yaw)+dy*math.cos(yaw)))
hole=(min(p[0] for p in corners),max(p[0] for p in corners),min(p[1] for p in corners),max(p[1] for p in corners))
backup=os.path.join(root,'Saved/Backups/LiftShaft',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
for file in ('Surface/BP_ConnectedLaboratoryCampus.uasset','Surface/Lvl_CampusConnected.umap'):shutil.copy2(os.path.join(root,'Content',file),os.path.join(backup,os.path.basename(file)))
def cut(cs):
 count=0
 for c in cs:
  if not isinstance(c,unreal.InstancedStaticMeshComponent) or c.get_name().split('_GEN')[0] not in ('Box_M_Dust_Block','Box_M_LabFloor_Block'):continue
  c.modify()
  # Rebuild only these two broad ground slabs to avoid accumulating old cuts.
  is_dust=c.get_name().startswith('Box_M_Dust_Block');c.clear_instances()
  c.add_instance(unreal.Transform(location=V((0,6500,-80) if is_dust else (0,5700,-10)),scale=V((420,500,1.5) if is_dust else (235,250,.25))),False)
  for i in range(c.get_instance_count()-1,-1,-1):
   t=c.get_instance_transform(i,False);p=t.translation;s=t.scale3d
   if abs(t.rotation.rotator().yaw)>.01:continue
   x0=p.x-s.x*50;x1=p.x+s.x*50;y0=p.y-s.y*50;y1=p.y+s.y*50
   a=max(x0,hole[0]);b=min(x1,hole[1]);d=max(y0,hole[2]);e=min(y1,hole[3])
   if b-a<.01 or e-d<.01:continue
   c.remove_instance(i);count+=1
   for lx,rx,by,ty in ((x0,a,y0,y1),(b,x1,y0,y1),(a,b,y0,d),(a,b,e,y1)):
    if rx-lx<.01 or ty-by<.01:continue
    c.add_instance(unreal.Transform(location=V(((lx+rx)/2,(by+ty)/2,p.z)),rotation=t.rotation.rotator(),scale=V(((rx-lx)/100,(ty-by)/100,s.z))),False)
 return count
bp=A.load_asset('/Game/Surface/BP_ConnectedLaboratoryCampus');template_count=cut([c for h,c,n in components(bp)]);compile_bp(bp);save(bp)
world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_CampusConnected');sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);placed=0
for a in sub.get_all_level_actors():
 if a.get_class().get_name()=='BP_ConnectedLaboratoryCampus_C':a.modify();placed+=cut(a.get_components_by_class(unreal.InstancedStaticMeshComponent))
world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Surface/Lvl_CampusConnected');del world
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
json.dump({'saved':True,'backup':backup,'hole_local':hole,'template_slabs_cut':template_count,'placed_slabs_cut':placed},open(os.path.join(root,'Saved/lift_shaft_cut.json'),'w'),indent=2)
