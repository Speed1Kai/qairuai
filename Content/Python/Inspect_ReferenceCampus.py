import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import components
s=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
r={}
for path in ['/Game/Surface/Lvl_CampusConnected']:
 unreal.EditorLoadingAndSavingUtils.load_map(path)
 r[path]=[]
 for a in s.get_all_level_actors():
  d={'label':a.get_actor_label(),'class':a.get_class().get_name(),'location':str(a.get_actor_location()),'rotation':str(a.get_actor_rotation())}
  if isinstance(a,unreal.TextRenderActor):d['text']=str(a.text_render.text)
  r[path].append(d)
bp=unreal.load_asset('/Game/Surface/CampusWall/BP_CampusPerimeterWalls')
r['wall']=[{'name':n,'mesh':c.static_mesh.get_path_name(),'instance0':c.get_instance_transform(0,False).export_text(),'bounds':c.static_mesh.get_bounding_box().export_text()} for h,c,n in components(bp) if isinstance(c,unreal.InstancedStaticMeshComponent)]
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'reference_plan_inspection.json'),'w'),ensure_ascii=False,indent=2)
unreal.log('REFERENCE PLAN INSPECTION FINISHED')
