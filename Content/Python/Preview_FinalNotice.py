import unreal
w=unreal.EditorLevelLibrary.get_game_world()
for q in unreal.ObjectIterator(unreal.UserWidget):
 if q.get_class().get_name()=='WBP_InteractionHint_C' and q.is_in_viewport():q.remove_from_parent()
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if a.get_class().get_name()=='BP_SurfaceArrival_C':a.call_method('PreviewCampusNotice')
