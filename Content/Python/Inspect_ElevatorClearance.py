import unreal,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
rows=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 if a.get_actor_label()=='LAB_FreightElevator':continue
 p,e=a.get_actor_bounds(False)
 if p.x+e.x>=2300 and p.x-e.x<=3000 and p.y+e.y>=-360 and p.y-e.y<=360 and p.z+e.z>=0 and p.z-e.z<=2800:
  rows.append({'name':a.get_actor_label(),'class':a.get_class().get_path_name(),'location':[a.get_actor_location().x,a.get_actor_location().y,a.get_actor_location().z],'bounds_center':[p.x,p.y,p.z],'extent':[e.x,e.y,e.z],'folder':str(a.get_folder_path())})
with open('S:/Final_Protocol/Saved/elevator_clearance_before.json','w',encoding='utf8') as f:json.dump(rows,f,ensure_ascii=False,indent=2)
