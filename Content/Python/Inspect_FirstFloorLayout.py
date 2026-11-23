import unreal,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows=[]
for a in sub.get_all_level_actors():
 p=a.get_actor_location()
 rows.append({'name':a.get_actor_label(),'class':a.get_class().get_path_name(),'folder':str(a.get_folder_path()),'p':[p.x,p.y,p.z]})
with open('S:/Final_Protocol/Saved/first_floor_before.json','w',encoding='utf8') as f:json.dump(rows,f,ensure_ascii=False,indent=2)
