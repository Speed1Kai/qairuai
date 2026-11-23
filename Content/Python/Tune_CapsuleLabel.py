"""Apply the compact inner-glass service label to an already built intro."""
import unreal
actor = next(a for a in unreal.EditorLevelLibrary.get_all_level_actors()
             if a.get_actor_label() == 'INTRO_InnerGlassStatus')
text = actor.get_component_by_class(unreal.TextRenderComponent)
actor.modify()
text.modify()
text.set_world_size(1.4)
text.set_text(unreal.Text('OMEGA // 01\nSEAL RELEASE'))
text.set_text_render_color(unreal.Color(r=100,g=190,b=195,a=255))
actor.set_actor_label('INTRO_InnerGlassStatus', mark_dirty=True)
if not unreal.EditorLoadingAndSavingUtils.save_map(
        unreal.EditorLevelLibrary.get_editor_world(), '/Game/Lvl_LabTutorial'):
    raise RuntimeError('Could not save the compact capsule label')
