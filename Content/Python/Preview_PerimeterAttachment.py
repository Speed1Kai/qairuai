import unreal,json,os
w=unreal.EditorLevelLibrary.get_game_world();r=[]
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if a.get_class().get_name()!='BP_CampusPerimeterWalls_C':continue
 cs={c.get_name():c for c in a.get_components_by_class(unreal.SceneComponent)}
 for c in cs.values():c.set_mobility(unreal.ComponentMobility.MOVABLE)
 base=a.root_component;scene=cs['Root'];mesh=cs['PerimeterWallSections']
 scene.attach_to_component(base,'None',unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False);scene.set_relative_location(unreal.Vector(),False,False);scene.set_relative_rotation(unreal.Rotator(yaw=49.08561677997487),False,False)
 mesh.attach_to_component(scene,'None',unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False);mesh.set_relative_location(unreal.Vector(),False,False);mesh.set_relative_rotation(unreal.Rotator(),False,False)
 r.append({'rotation':str(mesh.get_world_rotation()),'position':str(mesh.get_world_location())})
json.dump(r,open(os.path.join(unreal.Paths.project_saved_dir(),'perimeter_attachment_preview.json'),'w'),indent=2)

