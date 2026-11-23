"""Reload saved packages and verify the actual saved UMG and message routes."""
import unreal, json, os
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
saved=unreal.Paths.project_saved_dir()
with open(os.path.join(saved,'cinematic_hud_report.json'),encoding='utf8') as f:build=json.load(f)
if not build.get('saved'):raise RuntimeError('Build has not saved all packages')
result={'passed':False,'widgets':{},'blueprints':{},'remaining_screen_messages':[]}
for name in ('WBP_InteractionHint','WBP_ArchiveLog'):
    bp=A.load_asset('/Game/LabTutorial/UI/'+name)
    if not B.compile_blueprint(bp):raise RuntimeError('Widget compile: '+name)
    cdo=unreal.get_default_object(B.generated_class(bp))
    tree=unreal.find_object(bp,'WidgetTree')
    canvas=unreal.find_object(tree,'CyberCanvas')
    if not canvas or canvas.get_name()!='CyberCanvas':raise RuntimeError('Wrong widget root: '+name)
    for child in ('Heading','MessageBody','DarkPanel','CyanRail','NeonFrame'):
        if not unreal.find_object(tree,child):raise RuntimeError('Missing widget '+child)
    if unreal.find_object(tree,'NeonFrame').get_parent()!=canvas:raise RuntimeError('Detached UI hierarchy '+name)
    e=G.get_graph_editor_by_name(bp,'EventGraph')
    for event in ('Construct','Tick'):
        n=e.find_event_node(event)
        if not n or not n.find_then_pin().list_connected_pins():raise RuntimeError('Unwired '+name+'.'+event)
    errors=e.list_nodes_with_errors()
    if errors:raise RuntimeError('Widget node errors '+name)
    result['widgets'][name]={'root':canvas.get_name(),'lifetime':cdo.get_editor_property('HUDLifetime'),'nodes':len(e.list_all_nodes()),'compiled':True,'fade_events_connected':True}
for path in build['blueprints']:
    bp=A.load_asset(path)
    if not B.compile_blueprint(bp):raise RuntimeError('Compile: '+path)
    e=G.get_graph_editor_by_name(bp,'EventGraph')
    if e.list_nodes_with_errors():raise RuntimeError('Graph compiler errors: '+path)
    calls=[];props=[]
    for node in e.list_all_nodes():
        pins={str(p.get_pin_name()):p for p in node.list_all_pins()}
        if {'InString','bPrintToScreen'}.issubset(pins) and pins['bPrintToScreen'].get_pin_value().lower()=='true':
            if node.find_execute_pin().list_connected_pins():result['remaining_screen_messages'].append(path+':'+node.get_name())
        if 'WidgetType' in pins:
            if not node.find_execute_pin().list_connected_pins():raise RuntimeError('Unwired create '+path)
            if not pins['ReturnValue'].list_connected_pins():raise RuntimeError('Unused created widget '+path)
            calls.append(pins['WidgetType'].get_pin_value())
        if 'PropertyName' in pins and 'Value' in pins:
            if pins['PropertyName'].get_pin_value() in ('HUDTitle','HUDMessage'):
                props.append({'property':pins['PropertyName'].get_pin_value(),'value':pins['Value'].get_pin_value()})
    if not calls:raise RuntimeError('No UI instantiation '+path)
    result['blueprints'][path]={'compiled':True,'widget_calls':len(calls),'messages':props}
if result['remaining_screen_messages']:raise RuntimeError('Debug messages remain: '+str(result['remaining_screen_messages']))
result['passed']=True
with open(os.path.join(saved,'cinematic_hud_verification.json'),'w',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
unreal.log('CINEMATIC HUD VERIFIED: '+str(len(result['blueprints']))+' saved Blueprint packages, no active on-screen PrintString nodes')
