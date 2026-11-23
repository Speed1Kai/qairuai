"""Minimal demo fixes: first-person startup and self-occlusion-free interactions.

Run in the editor outside PIE. Backs up only the two changed assets. Reapply this
postprocess after rebuilding either Blueprint with an older authoring script.
"""
import unreal,json,shutil,sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(unreal.Paths.project_content_dir())/'Python'))
from Industrial_Common import A,B,G,components,compile_bp,pin,val

project=Path(unreal.Paths.project_dir()).resolve()
out=project/'Saved/DemoAudit/20261118'
out.mkdir(parents=True,exist_ok=True)
report={'saved':False,'changed_assets':[]}
def repair_demo_start():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(),'End PIE first'
    paths={'player':'/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter','focus':'/Game/LabTutorial/FocusedInteraction/BP_InteractionFocus'}
    backup=project/'Saved/Backups/DemoFirstPersonInteraction'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for path in paths.values():
        rel=Path('Content')/(path.removeprefix('/Game/')+'.uasset')
        dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(project/rel,dest)
    report['backup']=str(backup)
    focus=A.load_asset(paths['focus']);player=A.load_asset(paths['player'])
    graph=G.get_graph_editor_by_name(focus,'EventGraph')
    traces=[n for n in graph.list_all_nodes() if n.find_input_pin('ActorsToIgnore').is_valid()]
    assert len(traces)==1,'Unexpected focus trace layout'
    trace=traces[0];ignore=trace.find_input_pin('ActorsToIgnore')
    if not ignore.list_connected_pins():
        action=next(s for s in graph.list_available_nodes([]) if s.split('|')[-1] in ['Сделатьмассив','MakeArray','Make Array'])
        array=graph.create_node_from_name(action,unreal.Vector2D(-650,400),[])
        array.rename('Demo_IgnoreLocalPlayerArray')
        val(ignore,pin(array,'Array',True))
        getter=graph.add_call_function_node('/Script/Engine.GameplayStatics.GetPlayerCharacter')
        getter.rename('Demo_GetLocalPlayerForInteraction')
        val(pin(getter,'PlayerIndex'),0)
        val(pin(array,'[0]'),pin(getter,'ReturnValue',True))
    else:
        assert any(p.get_owning_node().get_name()=='Demo_IgnoreLocalPlayerArray' for p in ignore.list_connected_pins()),'Existing ignore logic needs review'
    compile_bp(focus)
    player.modify()
    camera_components={name:c for _,c,name in components(player) if c}
    camera_components['FirstPersonCamera'].set_editor_property('auto_activate',True)
    camera_components['FollowCamera'].set_editor_property('auto_activate',False)
    # The visor is created after the intro. Its initial visibility must match
    # the default view; the existing V switch still controls it afterwards.
    visor_changes=0
    for name in B.list_graph_names(player):
        eg=G.get_graph_editor_by_name(player,name)
        for n in eg.list_all_nodes():
            visibility=n.find_input_pin('InVisibility')
            if not visibility.is_valid() or visibility.get_pin_value()!='Collapsed':continue
            execute=n.find_execute_pin()
            if not execute.is_valid():continue
            previous=[p.get_owning_node() for p in execute.list_connected_pins()]
            if not any(p.find_input_pin('ZOrder').is_valid() for p in previous):continue
            target=n.find_self_pin()
            if not target.is_valid():continue
            if not any('VisorHUD' in str(p.get_owning_node().get_node_title()) for p in target.list_connected_pins()):continue
            val(visibility,'HitTestInvisible');visor_changes+=1
    compile_bp(player)
    cdo=unreal.get_default_object(B.generated_class(player))
    cdo.set_editor_property('bFirstPerson',True)
    cdo.set_editor_property('use_controller_rotation_yaw',True)
    cdo.character_movement.set_editor_property('orient_rotation_to_movement',False)
    for name,bp in [('focus',focus),('player',player)]:
        assert A.save_loaded_asset(bp,only_if_is_dirty=False),'Could not save '+name
        report['changed_assets'].append(paths[name])
    report.update(saved=True,first_person_default=cdo.get_editor_property('bFirstPerson'),visor_initial_visibility_nodes_changed=visor_changes,ignore_array_connected=True,blueprint_graph_errors={name:{str(gn):str(G.get_graph_editor_by_name(bp,gn).list_nodes_with_errors()) for gn in B.list_graph_names(bp) if G.get_graph_editor_by_name(bp,gn).list_nodes_with_errors()} for name,bp in [('focus',focus),('player',player)]})
try:
    repair_demo_start()
finally:
    (out/'StartInteractionFix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
