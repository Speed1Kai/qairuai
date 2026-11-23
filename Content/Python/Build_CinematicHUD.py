"""Replace on-screen lab debug strings with packaged, native UMG widgets.

Run in Unreal Python. No runtime Python, downloaded assets or map rebuild.
Original Blueprint packages are backed up before any graph changes.
"""
import unreal, os, json, shutil, traceback, sys, datetime

A=unreal.EditorAssetLibrary
B=unreal.BlueprintEditorLibrary
G=unreal.BlueprintGraphEditor
ROOT='/Game/LabTutorial/UI'
SAVED=unreal.Paths.project_saved_dir()
REPORT=os.path.join(SAVED,'cinematic_hud_report.json')
report={'saved':False,'widgets':[],'replacements':[],'skipped':[]}

def pin(n,name,out=False):
    if not n:raise RuntimeError('Missing node: '+name)
    p=n.find_output_pin(name) if out else n.find_input_pin(name)
    if not p.is_valid():raise RuntimeError('Missing pin '+n.get_name()+'.'+name)
    return p

def val(p,v):
    if hasattr(v,'try_create_connection'):
        if not v.try_create_connection(p):raise RuntimeError('Cannot connect '+str(p.get_pin_name()))
    elif not p.set_pin_value(str(v).lower() if isinstance(v,bool) else str(v)):
        raise RuntimeError('Cannot set '+str(p.get_pin_name())+' = '+str(v))

def link(a,b):val(b,a)

def compile_bp(bp):
    if not B.compile_blueprint(bp):raise RuntimeError('Compile failed: '+bp.get_path_name())
    for gn in B.list_graph_names(bp):
        e=G.get_graph_editor_by_name(bp,gn)
        errors=e.list_nodes_with_errors()
        if errors:raise RuntimeError('Compiler errors '+bp.get_name()+': '+str([str(n.get_node_title()) for n in errors]))

class Graph:
    def __init__(self,bp):self.e=G.get_graph_editor_by_name(bp,'EventGraph');self.cursor=None;self.i=0
    def node(self,n):
        if not n:raise RuntimeError('Could not create Blueprint node')
        n.set_node_pos(unreal.IntPoint(x=(self.i%7)*290,y=250+(self.i//7)*310));self.i+=1
        return n
    def call(self,path,target=None,**args):
        n=self.node(self.e.add_call_function_node('/Script/'+path))
        if target is not None:val(n.find_self_pin(),target)
        # Promotable math nodes infer their real type from connected pins first.
        for k,v in args.items():
            if hasattr(v,'try_create_connection'):val(pin(n,k),v)
        for k,v in args.items():
            if not hasattr(v,'try_create_connection'):val(pin(n,k),v)
        return n
    def get(self,name):return pin(self.node(self.e.add_get_member_variable_node(name)),name,True)
    def out(self,n,name='ReturnValue'):return pin(n,name,True)
    def do(self,n):link(self.cursor,n.find_execute_pin());self.cursor=n.find_then_pin();return n
    def set(self,name,v):
        n=self.node(self.e.add_set_member_variable_node(name));val(pin(n,name),v);return self.do(n)
    def math(self,name,**args):return self.out(self.call('Engine.KismetMathLibrary.'+name,**args))
    def branch(self,condition):
        n=self.node(self.e.add_branch_node());val(pin(n,'Condition'),condition);self.do(n);return n
    def event(self,name):
        n=self.e.find_event_node(name)
        if not n:
            choices=[x for x in self.e.list_available_nodes([]) if x.split('|')[-1].replace(' ','').lower() in (name.lower(),'event'+name.lower())]
            if len(choices)!=1:raise RuntimeError('Event missing '+name+': '+str(choices))
            n=self.e.create_node_from_name(choices[0],unreal.Vector2D(x=0,y=0),[])
        self.cursor=pin(n,'then',True);return n

def backup(path):
    rel=path.removeprefix('/Game/')+'.uasset'
    src=os.path.join(unreal.Paths.project_content_dir(),rel)
    dest=os.path.join(report['backup'],rel)
    if os.path.isfile(src) and not os.path.isfile(dest):
        os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(src,dest)

def color(r,g,b,a=1):return unreal.LinearColor(r=r,g=g,b=b,a=a)

def build_widget(name,hint=False):
    path=ROOT+'/'+name;backup(path)
    bp=A.load_asset(path) if A.does_asset_exist(path) else None
    if not bp:
        factory=unreal.WidgetBlueprintFactory();factory.set_editor_property('parent_class',unreal.UserWidget)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.WidgetBlueprint,factory)
    tree=unreal.find_object(bp,'WidgetTree')
    if not tree:raise RuntimeError('WidgetTree missing '+path)
    def w(cls,n):return unreal.find_object(tree,n) or unreal.new_object(cls,outer=tree,name=n)
    canvas=w(unreal.CanvasPanel,'CyberCanvas');canvas.clear_children()
    assign_object(tree,'RootWidget',canvas)
    width=640 if hint else 920;height=104 if hint else 224
    frame=w(unreal.Border,'NeonFrame');frame.clear_children()
    frame.set_brush_color(color(.02,.65,.7,.8));frame.set_padding(unreal.Margin(1))
    slot=canvas.add_child_to_canvas(frame)
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,1),maximum=unreal.Vector2D(.5,1)))
    slot.set_alignment(unreal.Vector2D(.5,1))
    slot.set_position(unreal.Vector2D(0,-64 if hint else -184));slot.set_size(unreal.Vector2D(width,height))
    panel=w(unreal.Border,'DarkPanel');panel.clear_children()
    panel.set_brush_color(color(.004,.009,.018,.94));panel.set_padding(unreal.Margin(0));frame.add_child(panel)
    content=w(unreal.CanvasPanel,'ContentCanvas');content.clear_children();panel.add_child(content)
    def box(cls,n,x,y,sx,sy):
        obj=w(cls,n)
        if isinstance(obj,unreal.PanelWidget):obj.clear_children()
        sl=content.add_child_to_canvas(obj);sl.set_position(unreal.Vector2D(x,y));sl.set_size(unreal.Vector2D(sx,sy))
        return obj
    stripe=box(unreal.Border,'CyanRail',0,0,4,height-2);stripe.set_brush_color(color(.02,.9,.95))
    marker=box(unreal.Border,'AmberMarker',width-30,18,9,9);marker.set_brush_color(color(1,.32,.06))
    progress=box(unreal.Border,'BottomLine',22,height-12,width-44,1);progress.set_brush_color(color(.02,.5,.6,.55))
    def text(n,txt,x,y,sx,sy,size,tint,bold=False):
        t=box(unreal.TextBlock,n,x,y,sx,sy);t.set_text(unreal.Text(txt))
        t.set_color_and_opacity(unreal.SlateColor(specified_color=tint))
        f=t.get_editor_property('font');f.set_editor_property('size',size)
        font=A.load_asset('/Engine/EngineFonts/Roboto')
        if font:f.set_editor_property('font_object',font)
        f.set_editor_property('typeface_font_name','Bold' if bold else 'Regular');t.set_font(f)
        t.set_auto_wrap_text(True);t.set_editor_property('wrap_text_at',float(sx))
        t.set_shadow_color_and_opacity(color(0,0,0,.8));t.set_shadow_offset(unreal.Vector2D(0,1))
        return t
    text('SubsystemLabel','OMEGA  /  НЕЙРОИНТЕРФЕЙС' if hint else 'FINAL PROTOCOL  /  АРХИВ ЛАБОРАТОРИИ',22,10,width-75,19,10,color(.28,.63,.7),True)
    heading=text('Heading','ВЗАИМОДЕЙСТВИЕ' if hint else 'АРХИВ 02 | ЯДРО ATLAS',22,31,width-55,32,16 if hint else 21,color(.2,.96,1),True)
    body=text('MessageBody','[E]  ЧИТАТЬ ЗАПИСЬ' if hint else 'Система уничтожила человечество и называет стерильный порядок лекарством. Её главный дата-центр находится наверху.',22,59 if hint else 78,width-52,33 if hint else 100,17 if hint else 20,color(.84,.94,1))
    # These named TextBlocks become generated Blueprint component variables.
    assign_flag(heading,'bIsVariable',True);assign_flag(body,'bIsVariable',True)
    canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    e=G.get_graph_editor_by_name(bp,'EventGraph')
    e.remove_nodes([n for n in e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
    members=[str(x) for x in B.list_member_variable_names(bp)]
    for n,t,d in [('HUDTitle','string',''),('HUDMessage','string',''),('HUDAge','real','0.0'),('HUDLifetime','real','3.5' if hint else '8.0')]:
        if n not in members:
            if not e.add_member_variable(n,B.get_basic_type_by_name(t),d):raise RuntimeError('Member creation '+n)
    compile_bp(bp);g=Graph(bp)
    g.event('Construct');g.set('HUDAge',0)
    g.do(g.call('UMG.Widget.SetRenderOpacity',InOpacity=0))
    for widget,member in [('Heading','HUDTitle'),('MessageBody','HUDMessage')]:
        converted=g.out(g.call('Engine.KismetTextLibrary.Conv_StringToText',InString=g.get(member)))
        g.do(g.call('UMG.TextBlock.SetText',target=g.get(widget),InText=converted))
    tick=g.event('Tick')
    age=g.math('Add_DoubleDouble',A=g.get('HUDAge'),B=pin(tick,'InDeltaTime',True))
    g.set('HUDAge',age)
    enter=g.math('Divide_DoubleDouble',A=g.get('HUDAge'),B=.45)
    remain=g.math('Subtract_DoubleDouble',A=g.get('HUDLifetime'),B=g.get('HUDAge'))
    leave=g.math('Divide_DoubleDouble',A=remain,B=.35)
    alpha=g.math('FClamp',Value=g.math('FMin',A=enter,B=leave),Min=0,Max=1)
    g.do(g.call('UMG.Widget.SetRenderOpacity',InOpacity=alpha))
    y=g.math('Multiply_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=1,B=g.math('FClamp',Value=enter,Min=0,Max=1)),B=12)
    translation=g.math('MakeVector2D',X=0,Y=y)
    g.do(g.call('UMG.Widget.SetRenderTranslation',Translation=translation))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.get('HUDAge'),B=g.get('HUDLifetime')))
    g.do(g.call('UMG.Widget.RemoveFromParent'))
    compile_bp(bp)
    if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Could not save '+path)
    report['widgets'].append(path);return bp

def assign_flag(target,name,value):
    unreal.get_default_object(B.generated_class(helper)).call_method('AssignFlag',args=(target,unreal.Name(name),value))

def classify(message):
    low=message.lower()
    if 'тепловизор' in low and '\n' not in message:
        return True,'ОПТИЧЕСКАЯ ПОДСИСТЕМА',message.replace(' | ',' / ')
    if 'лифт запущен' in low:
        return True,'ГРУЗОВАЯ ПЛАТФОРМА','ПОДЪЁМ  /  ЭТАЖ 01'
    if message.startswith('PROTOCOL OMEGA ACTIVATED'):
        return False,'ПРОТОКОЛ OMEGA / ПРОБУЖДЕНИЕ','STATUS: AWAKE  /  MISSION: NEUTRALIZE CORE\nHUMANITY STATUS: TERMINATED\nWASD — движение    SPACE — прыжок'
    hint=any(k in low for k in ('нажмите','нажми ','подойдите','подойди ','press ')) and '\n' not in message and len(message)<200
    if hint:
        if 'прочит' in low:return True,'ЛОКАЛЬНЫЙ ТЕРМИНАЛ','[E]  ЧИТАТЬ ЗАПИСЬ'
        if 'голограф' in low or 'прослуш' in low:return True,'ГОЛОГРАФИЧЕСКИЙ АРХИВ','[E]  ВОСПРОИЗВЕСТИ ЗАПИСЬ'
        if 'взлом' in low or 'панел' in low:return True,'ЭЛЕКТРОННЫЙ ЗАМОК','[E]  ПОДКЛЮЧИТЬСЯ'
        return True,'СИСТЕМНАЯ ПОДСКАЗКА',message
    lines=message.split('\n',1)
    if len(lines)==2:return False,lines[0],lines[1]
    if message.startswith('АРХИВ 02') or message.startswith('АРХИВ 02 | ATLAS.'):
        return False,'АРХИВ 02 | ЯДРО ATLAS','Система уничтожила человечество и называет стерильный порядок лекарством. Её главный дата-центр находится наверху.'
    if 'ЗАТВОР' in message:return True,'ДОСТУП РАЗРЕШЁН','ЗАТВОР РАЗБЛОКИРОВАН'
    return False,'OMEGA  /  ПОЛУЧЕНЫ ДАННЫЕ',message

def replace_message(bp,node,widgets):
    e=G.get_graph_editor_by_name(bp,'EventGraph');g=Graph(bp)
    msg=pin(node,'InString').get_pin_value();dynamic=list(pin(node,'InString').list_connected_pins())
    hint,title,body=classify(msg)
    incoming=list(node.find_execute_pin().list_connected_pins());outgoing=list(node.find_then_pin().list_connected_pins())
    if not incoming:return False
    ref='CyberHUD_'+node.get_name().replace('K2Node_','')
    members=[str(x) for x in B.list_member_variable_names(bp)]
    if ref not in members:
        if not e.add_member_variable(ref,B.get_object_reference_type(unreal.UserWidget)):raise RuntimeError('Cannot add '+ref)
        compile_bp(bp);e=G.get_graph_editor_by_name(bp,'EventGraph');g=Graph(bp)
    # A live widget blocks repeated inputs; removed widgets allow reading again.
    valid=g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get(ref)))
    branch=g.node(e.add_branch_node());val(pin(branch,'Condition'),valid)
    visible=g.out(g.call('UMG.Widget.IsInViewport',target=g.get(ref)))
    active=g.node(e.add_branch_node());val(pin(active,'Condition'),visible)
    link(branch.find_then_pin(),active.find_execute_pin())
    pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
    wbp=widgets[0 if hint else 1]
    create=g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(wbp).get_path_name(),OwningPlayer=pc)
    link(branch.find_else_pin(),create.find_execute_pin());link(active.find_else_pin(),create.find_execute_pin())
    g.cursor=create.find_then_pin();widget=g.out(create);g.set(ref,widget)
    for prop,content in [('HUDTitle',title),('HUDMessage',dynamic[0] if dynamic else body)]:
        g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=prop,Value=content))
    # The widget owns its fade and lifetime, so no actor delay can remove a newer UI.
    g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=40 if hint else 50))
    sound=A.load_asset('/Game/LabTutorial/Holograms/S_ProjectorStartup')
    if sound and not hint:g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound=sound.get_path_name(),VolumeMultiplier=.18))
    for p in outgoing:
        link(g.cursor,p);link(active.find_then_pin(),p)
    node.find_execute_pin().break_pin_links();node.find_then_pin().break_pin_links()
    for p in incoming:link(p,branch.find_execute_pin())
    e.remove_nodes([node])
    report['replacements'].append({'blueprint':bp.get_path_name(),'text':msg,'type':'hint' if hint else 'archive','title':title,'body':body})
    return True

try:
    report['backup']=os.path.join(SAVED,'Backups','CinematicHUD',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(report['backup'],exist_ok=True)
    A.make_directory(ROOT)
    sys.path.insert(0,os.path.join(unreal.Paths.project_content_dir(),'Python'))
    import Archive_AuthoringHelpers
    helper=Archive_AuthoringHelpers.helper
    assign_object=Archive_AuthoringHelpers.assign_object
    if 'AssignFlag' not in [str(n) for n in B.list_graph_names(helper)]:
        e=G.create_and_edit_function_graph(helper,'AssignFlag')
        obj=e.add_graph_input_parameter('TargetObject',B.get_object_reference_type(unreal.Object))
        name=e.add_graph_input_parameter('PropertyName',B.get_basic_type_by_name('name'))
        v=e.add_graph_input_parameter('Value',B.get_basic_type_by_name('bool'))
        n=e.add_call_function_node('/Script/Engine.KismetSystemLibrary.SetBoolPropertyByName')
        link(e.find_graph_entry_pin(),n.find_execute_pin())
        for p,k in [(obj,'Object'),(name,'PropertyName'),(v,'Value')]:link(p,pin(n,k))
        compile_bp(helper)
    hint=build_widget('WBP_InteractionHint',True)
    archive=build_widget('WBP_ArchiveLog',False)
    modified=[]
    paths=[]
    for root in ('/Game/LabTutorial/Blueprints','/Game/ThirdPerson/Blueprints'):
        paths.extend(A.list_assets(root,recursive=True,include_folder=False))
    for path in paths:
        bp=A.load_asset(path)
        if not isinstance(bp,unreal.Blueprint):continue
        if 'EventGraph' not in [str(x) for x in B.list_graph_names(bp)]:continue
        e=G.get_graph_editor_by_name(bp,'EventGraph')
        nodes=[]
        for n in e.list_all_nodes():
            names={str(p.get_pin_name()) for p in n.list_all_pins()}
            if not {'bPrintToScreen','InString'}.issubset(names):continue
            p=n.find_input_pin('bPrintToScreen');s=n.find_input_pin('InString')
            if p.is_valid() and s.is_valid() and p.get_pin_value().lower()=='true':nodes.append(n)
        if not nodes:continue
        backup(bp.get_path_name().split('.')[0])
        changed=False
        for n in nodes:changed=replace_message(bp,n,(hint,archive)) or changed
        if changed:compile_bp(bp);modified.append(bp)
    # No gameplay Blueprint is saved unless every modified graph compiles first.
    for bp in modified:
        if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Save failed '+bp.get_path_name())
    report['blueprints']=[bp.get_path_name() for bp in modified]
    report['saved']=True
    report['note']='Native UMG; opacity/slide 0.45s, fade-out 0.35s; hints 3.5s, archive 8s; repeat input guarded per message; original gameplay continuations preserved.'
    unreal.log('CINEMATIC HUD SAVED: '+str(len(report['replacements']))+' messages')
except Exception:
    report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
    with open(REPORT,'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Cinematic HUD not applied; see '+REPORT)
