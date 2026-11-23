"""Read-only snapshot for aligning the laboratory with the selected drawing."""
import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,components
bp=A.load_asset('/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor')
r={'components':[],'actors':[]}
if bp:
    seen=set()
    for h,c,name in components(bp):
        if name in seen or not isinstance(c,unreal.InstancedStaticMeshComponent):continue
        seen.add(name);row={'name':name,'count':c.get_instance_count(),'mesh':c.static_mesh.get_path_name() if c.static_mesh else None,'instances':[]}
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,False);p=t.translation;s=t.scale3d
            row['instances'].append({'p':[p.x,p.y,p.z],'s':[s.x,s.y,s.z],'yaw':t.rotation.rotator().yaw})
        r['components'].append(row)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    p=a.get_actor_location();name=a.get_actor_label()
    if name.startswith('F01_') or a.get_class().get_name() in ('BP_SurfaceDeparture_C','BP_FreightElevatorBidirectional_C'):
        row={'name':name,'class':a.get_class().get_name(),'p':[p.x,p.y,p.z],'yaw':a.get_actor_rotation().yaw}
        if isinstance(a,unreal.TextRenderActor):row['text']=str(a.text_render.text)
        r['actors'].append(row)
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'current_lab_plan.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
