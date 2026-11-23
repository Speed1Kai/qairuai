"""Bounded repair of missing E events in existing lab actors.

Uses public graph APIs only. No interface/property reflection, function graph
deletions, generic task runner, or modification of the player movement graph.
Copies every affected asset and the map before changes, checks every pin/link,
and compiles every graph before saving any asset.
"""
import unreal, os, shutil, json
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
directory='/Game/LabTutorial/Blueprints/'
specs={
 'BP_TutorialHologramTrigger':'ПРОТОКОЛ OMEGA АКТИВИРОВАН. ЦЕЛЬ: ОТКЛЮЧИТЬ ЯДРО ATLAS.',
 'BP_LabRecoveryLog':'ЖУРНАЛ 01 | OMEGA. Ты был создан до падения. Собери фрагменты протокола отключения ATLAS.',
 'BP_LabAtlasLog':'АРХИВ 02 | ATLAS. Система уничтожила человечество. Главный дата-центр находится наверху.',
 'BP_LabMobilityLog':'МОДУЛЬ ПЕРЕМЕЩЕНИЯ повреждён. Его фрагмент ищи у шахты лифта.',
 'BP_LabPurposeLog':'СЕКРЕТНЫЙ ПРОТОКОЛ. Тебя создали, чтобы отключить ATLAS. Найди главный дата-центр.',
 'BP_LabArchiveFragmentLog':'АРХИВ КООРДИНАТ. Карта города повреждена. Найди фрагменты протокола в старых узлах связи.',
 'BP_LabStealthHint':'СЕКТОР ПОИСКА. Прячься от дрона за серверными стойками.',
 'BP_TutorialSlidingDoor':None,
}
backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups','Interaction','MissingERepair')
os.makedirs(backup,exist_ok=True)
for name in specs:
    source=os.path.join(unreal.Paths.project_content_dir(),'LabTutorial','Blueprints',name+'.uasset')
    dest=os.path.join(backup,name+'.uasset')
    if not os.path.exists(dest):shutil.copy2(source,dest)
map_source=os.path.join(unreal.Paths.project_content_dir(),'Lvl_LabTutorial.umap')
if not os.path.exists(os.path.join(backup,'Lvl_LabTutorial.umap')):shutil.copy2(map_source,os.path.join(backup,'Lvl_LabTutorial.umap'))

def pin(node,name,output=False):
    value=node.find_output_pin(name) if output else node.find_input_pin(name)
    if not value.is_valid():raise RuntimeError('Missing pin '+node.get_name()+'.'+name)
    return value
def link(a,b):
    if not a.is_valid() or not b.is_valid() or not a.try_create_connection(b):raise RuntimeError('Could not connect graph pins')

modified=[];report={}
with unreal.ScopedEditorTransaction('Repair missing laboratory E input'):
    for name,message in specs.items():
        bp=A.load_asset(directory+name);e=G.get_graph_editor_by_name(bp,'EventGraph')
        existing=[n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_InputKey' and str(n.get_editor_property('input_key').get_editor_property('key_name'))=='E']
        existing_links=pin(existing[0],'Pressed',True).list_connected_pins() if existing else []
        if existing_links and existing_links[0].get_owning_node().find_then_pin().list_connected_pins():
            report[name]='E binding already exists; unchanged';continue
        choices=[n for n in e.list_available_nodes([]) if n.endswith('|KeyboardEvents|E')]
        if len(choices)!=1:raise RuntimeError('Expected one localized E event action: '+str(choices))
        event=existing[0] if existing else e.create_node_from_name(choices[0],unreal.Vector2D(x=0,y=650),[])
        if not event:raise RuntimeError('Could not create E event')
        event.set_editor_property('bConsumeInput',False)
        event.set_editor_property('bExecuteWhenPaused',False)
        pin(event,'Pressed',True).break_pin_links()
        near=e.add_get_member_variable_node('bPlayerNear')
        branch=e.add_branch_node()
        link(pin(event,'Pressed',True),branch.find_execute_pin())
        link(pin(near,'bPlayerNear',True),pin(branch,'Condition'))
        if message is None:
            action=e.add_call_function_node('/Script/Engine.Actor.K2_SetActorLocation')
            assert pin(action,'NewLocation').set_pin_value('(X=1450.0,Y=0.0,Z=750.0)')
            link(branch.find_then_pin(),action.find_execute_pin())
            feedback=e.add_call_function_node('/Script/Engine.KismetSystemLibrary.PrintString')
            assert pin(feedback,'InString').set_pin_value('ЗАТВОР OMEGA ОТКРЫТ')
            link(pin(action,'then',True),feedback.find_execute_pin())
        else:
            feedback=e.add_call_function_node('/Script/Engine.KismetSystemLibrary.PrintString')
            assert pin(feedback,'InString').set_pin_value(message)
            link(branch.find_then_pin(),feedback.find_execute_pin())
        assert pin(feedback,'Duration').set_pin_value('10.0')
        assert pin(feedback,'bPrintToScreen').set_pin_value('true')
        assert pin(feedback,'bPrintToLog').set_pin_value('true')
        for i,n in enumerate((near,branch,feedback)):
            n.set_node_pos(unreal.IntPoint(x=250+i*300,y=650))
        unreal.get_default_object(B.generated_class(bp)).set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
        if not B.compile_blueprint(bp):raise RuntimeError('Compile failed: '+name)
        modified.append(bp);report[name]='E Pressed -> proximity check -> interaction; compiled'
    # Save only after all eight Blueprints have passed compilation.
    for bp in modified:
        if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Could not save '+bp.get_name())
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if actor.get_class().get_name().removesuffix('_C') in specs:
            actor.modify()
            actor.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
# The map is saved outside the graph-editing transaction.
if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Map save failed; Blueprint packages are already saved')
with open(os.path.join(unreal.Paths.project_saved_dir(),'missing_e_repair_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
unreal.log('Missing E repair finished: '+str(len(modified))+' compiled Blueprints')
