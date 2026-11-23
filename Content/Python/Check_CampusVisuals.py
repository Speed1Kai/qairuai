import unreal,os,json,traceback
r={};w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
p.set_actor_location(unreal.Vector(5850,3500,2259.65),False,True);pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=90));p.set_actor_rotation(unreal.Rotator(yaw=90),True)
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if a.get_class().get_name()=='BP_CampusReadability_C':
  r['lighting']=[{'name':c.get_name(),'pos':str(c.get_world_location()),'rot':str(c.get_world_rotation())} for c in a.get_components_by_class(unreal.SceneComponent)]
try:
 bp=unreal.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint');wid=unreal.WidgetBlueprintLibrary.create(w,unreal.BlueprintEditorLibrary.generated_class(bp),pc);wid.set_editor_property('HUDTitle','ЦЕЛЬ / ПЕРИМЕТР КОМПЛЕКСА');wid.set_editor_property('HUDMessage','Найдите северные ворота. Они заблокированы — потребуется способ преодолеть периметр.');wid.set_editor_property('HUDLifetime',120.);wid.add_to_viewport(70)
except:r['error']=traceback.format_exc()
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'campus_visual_check.json'),'w'),indent=2)
