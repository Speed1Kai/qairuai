"""Author the playable 'Своя частота' ending on the existing mission and F input."""
from datetime import datetime
from pathlib import Path
import json, shutil
import unreal
from Install_StoryMemory import Story, A,B,G,load,compile_bp,save,var,add,pin,val,link,insert_entry,V,L,MISSION,PLAYER,GUIDE
from Present_DemoOmegaCaptions import external
from Install_StoryMemory import WIDGET

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SOURCE=PROJECT/'SourceAssets/StationSeven'
AUDIO='/Game/Story/StationSeven/Audio'
FIRST=(34488,87526,2288)
SECOND=(35417,87365,2282)
LOCK=(34803,86707,2298)
DOOR=(34794,86900,2262)
LOBBY=(34745,86902,2262)
WORKSHOP=(35311,87364,2262)
END=(34896,86793,2262)
CUT='Станция 07 · красный пеленгатор на фасаде'
HIDE='Ты засечён · скройся за стеной станции'
HAND='Мастерская · передатчик за приёмной'
RESCUE='Помоги раненым · открой ставню в приёмной'
DONE='Миссия завершена · медсклад открыт, убежище на связи'
METAL='/Game/LabTutorial/Industrial/M_DoorArmor'
RED='/Game/LabTutorial/Industrial/M_DoorStatus_Red'
GREEN='/Game/LabTutorial/Industrial/M_DoorStatus_Green'
AMBER='/Game/Surface/Materials/M_ExitAmber'

SCREEN='/Game/Story/StationSeven/Displays'
def prepare_displays():
    mel=unreal.MaterialEditingLibrary
    assets=unreal.AssetToolsHelpers.get_asset_tools()
    textures={}
    for key in ('Mast','Quiet','Air','OnAir','Lock','Open','Facade'):
        name='T_Station07_'+key;path=SCREEN+'/'+name
        if not A.does_asset_exist(path):
            t=unreal.AssetImportTask()
            for k,v in dict(filename=str(SOURCE/(name+'.png')),destination_path=SCREEN,automated=True,save=True).items():t.set_editor_property(k,v)
            assets.import_asset_tasks([t])
        textures[key]=load(path)
    path=SCREEN+'/M_FrequencyReadout'
    if A.does_asset_exist(path):master=load(path)
    else:
        master=assets.create_asset('M_FrequencyReadout',SCREEN,unreal.Material,unreal.MaterialFactoryNew())
        master.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        def node(cls):return mel.create_material_expression(master,cls)
        uv=node(unreal.MaterialExpressionCustom)
        uv.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        names=[]
        for name in ('Position','Centre','Extent'):
            item=unreal.CustomInput();item.set_editor_property('input_name',name);names.append(item)
        uv.set_editor_property('inputs',names)
        uv.set_editor_property('code','float3 d=(Position-Centre)/max(Extent,float3(.01,.01,.01)); return saturate(float2(.5+.5*(Extent.x>Extent.y ? -d.x : d.y),.5-.5*d.z));')
        assert mel.connect_material_expressions(node(unreal.MaterialExpressionWorldPosition),'',uv,'Position')
        assert mel.connect_material_expressions(node(unreal.MaterialExpressionObjectPositionWS),'',uv,'Centre')
        assert mel.connect_material_expressions(node(unreal.MaterialExpressionObjectBounds),'',uv,'Extent')
        tex=node(unreal.MaterialExpressionTextureSampleParameter2D)
        tex.set_editor_property('parameter_name','Display')
        tex.set_editor_property('texture',textures['Mast'])
        assert mel.connect_material_expressions(uv,'',tex,'UVs')
        assert mel.connect_material_property(tex,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        mel.recompile_material(master);save(master)
    for key,texture in textures.items():
        path=SCREEN+'/MI_'+key
        if A.does_asset_exist(path):
            mi=load(path)
            if mel.get_material_instance_texture_parameter_value(mi,'Display')==texture:
                file=PROJECT/'Content'/(path[6:]+'.uasset')
                if not file.exists():save(mi)
                continue
        else:mi=assets.create_asset('MI_'+key,SCREEN,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi,master)
        mel.set_material_instance_texture_parameter_value(mi,'Display',texture)
        assert mel.get_material_instance_texture_parameter_value(mi,'Display')==texture
        mel.update_material_instance(mi);save(mi)

def hardware(bp):
    from Industrial_Common import components
    # These components belong only to the superseded roadside booth.
    old=[h for h,_,n in components(bp) if n.startswith(('FreqBase','FreqDesk','FreqRack','FreqPlate','FreqTitle','FreqMast','FreqAerial','FreqTrack','FreqRemote','FreqLocal','FreqBeacon','FreqOnAir','RadioFloor','RadioRoof','RadioSouth','RadioNorth','RadioEnd','RadioWing','RadioBaffle','RadioEntryLight','RadioCeilingStrip','RadioStreetSign')) or n in ('TrackingDisplay','BroadcastDisplay','FrequencyRelay')]
    if old:
        sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        children=[h for h,_,n in components(bp) if h in old and n!='FrequencyRelay']
        if children:sub.delete_subobjects(components(bp)[0][0],children,bp)
        handles=[h for h,_,n in components(bp) if n=='FrequencyRelay']
        if handles:sub.delete_subobjects(components(bp)[0][0],handles,bp)
    assert not any(n.startswith(('RadioBaffle','FreqDesk','RadioFloor')) for _,_,n in components(bp))
    root='Station07Rescue'
    add(bp,unreal.SceneComponent,root,'Root')
    def part(name,pos,size,mat=METAL,parent=None,solid=False,shape='Cube'):
        c=add(bp,unreal.StaticMeshComponent,name,parent or root)
        c.set_static_mesh(load('/Engine/BasicShapes/'+shape))
        c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_scale3d',V(size))
        c.set_material(0,load(mat));c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        return c
    def plate(name,pos,size,face):
        return part(name,pos,size,SCREEN+'/MI_'+face)
    def light(name,pos,color,power,radius,on=True):
        c=add(bp,unreal.PointLightComponent,name,root)
        c.set_editor_property('relative_location',V(pos));c.set_intensity(power)
        c.set_light_color(unreal.LinearColor(*color,1));c.set_attenuation_radius(radius)
        c.set_cast_shadows(False);c.set_visibility(on)
    # West-facing equipment is bolted to the actual station facade.
    plate('StationIdentity',(34429,86900,2482),(.072,2.85,.70),'Facade')
    part('UplinkSpine',(34542,87526,2443),(.16,.31,5.50))
    part('UplinkEnclosure',(34519,87526,2281),(.37,1.15,.91),METAL,solid=True)
    plate('TrackingDisplay07',(34498,87526,2288),(.03,.98,.48),'Mast')
    for i,z in enumerate((2490,2532,2574,2616,2658)):
        part('UplinkYagi'+str(i),(34542,87526,z),(.075,1.9-i*.21,.065),METAL)
    for i,y in enumerate((87478,87574)):
        part('UplinkBolt'+str(i),(34497,y,2250),(.055,.058,.055),AMBER,shape='Sphere')
    part('UplinkBeacon',(34540,87526,2716),(.24,.24,.31),RED,shape='Sphere')
    light('UplinkGlow',(34495,87526,2450),(1,.10,.025),440,320)
    # A radio faceplate on the existing workshop bench; no extra desk.
    part('RadioReceiver',(35453,87365,2281),(.29,1.02,.64),METAL)
    plate('BroadcastDisplay07',(35436,87365,2282),(.025,.93,.47),'Air')
    part('RadioWhip',(35459,87413,2344),(.025,.025,.95),METAL,shape='Cylinder')
    # The local y=2.3 m partition has a real 1.83 m opening into the supply store.
    shutter=add(bp,unreal.SceneComponent,'MedicalRoll',root)
    shutter.set_editor_property('relative_location',V((34900,86669,2403)))
    part('ShutterLeaf',(0,0,-122), (1.83,.064,2.45),METAL,'MedicalRoll',True)
    for i in range(13):
        part('ShutterSlat'+str(i),(0,5,-8-i*18.8),(1.82,.06,.055),METAL,'MedicalRoll')
    part('ShutterRailL',(34805,86670,2278),(.065,.165,2.54))
    part('ShutterRailR',(34995,86670,2278),(.065,.165,2.54))
    part('ShutterDrum',(34900,86670,2416),(1.99,.30,.27))
    part('LockBack',(34802,86686,2296),(.50,.15,.78),METAL)
    plate('MedicalDisplay',(34804,86696,2304),(.64,.03,.35),'Lock')
    part('ManualSwitch',(34801,86696,2271),(.32,.105,.074),AMBER)
    light('ReserveLight',(34900,86577,2358),(.56,1,.78),620,340,False)
    # Physical dressings on the storage side. A white cross identifies them from the hall.
    for i,(x,y) in enumerate(((34912,86525),(34852,86527),(34912,86525))):
        z=2187 if i<2 else 2234
        part('SupplyCase'+str(i),(x,y,z),(.56,.43,.43),METAL,solid=True)
        part('SupplyBand'+str(i),(x,y+22,z),(.38,.018,.075),GREEN)
        part('SupplyCross'+str(i),(x,y+22.1,z),(.075,.019,.26),GREEN)
    for i,(x,y) in enumerate(((35147,86856),(35048,86856),(34956,86856),(34956,86762))):
        part('EscapeStripe'+str(i),(x,y,2161.8),(.42,.105,.012),GREEN).set_visibility(False)


def speech(g,key,data,sounds):
    line=data[key];sound=sounds[key]
    g.set('Speaker',line['speaker']);g.set('Dialogue',line['text'])
    g.set('DialogueUntil',g.num('Add',g.now(),sound.duration+.6))
    guide=g.branch(g.valid(g.get('Guide')));absent=guide.find_else_pin()
    g.do(g.call('Engine.AudioComponent.Stop',target=external(g,g.get('Guide'),'Voice',load(GUIDE))))
    widget=external(g,g.get('Guide'),'DemoCaptionWidget',load(GUIDE))
    check=g.branch(g.valid(widget));no_widget=check.find_else_pin()
    g.do(g.call('UMG.Widget.SetRenderOpacity',target=widget,InOpacity=0.))
    sound_node=g.do(g.call('Engine.AudioComponent.SetSound',target=g.get('Voice'),NewSound=sound.get_path_name()))
    link(absent,sound_node.find_execute_pin());link(no_widget,sound_node.find_execute_pin())
    g.do(g.call('Engine.AudioComponent.Play',target=g.get('Voice'),StartTime=0.))
    g.next(sound.duration+.85)

def when_step(g,step):
    return g.branch(g.compare('EqualEqual',g.get('FrequencyStep'),step)).find_else_pin()

def can_use(g,point):
    # This graph is used both by the HUD and the F handler. Clear the flag
    # before checking proximity so a previous frame cannot authorise a press.
    g.set('FrequencyCanUse',False)
    g.branch(g.near(point,235.))
    cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0))
    eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam))
    rot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=cam))
    facing=g.math('GetForwardVector',InRot=rot)
    toward=g.math('Normal',A=g.subv(L(point),eye))
    g.branch(g.num('Greater',g.math('Dot_VectorVector',A=facing,B=toward),.73))
    # Trace from the face of the panel. The booth walls must also block use.
    trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=L(point),End=eye,
                      TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=False,DrawDebugType='None'))
    hit=g.out(trace);parts=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'))
    pawn_hit=g.math('EqualEqual_ObjectObject',A=g.out(parts,'HitActor'),B=g.get('Player'))
    g.branch(g.math('BooleanOR',A=g.not_(hit),B=pawn_hit))
    g.set('FrequencyCanUse',True)

def swap_story_lines(bp,data,sounds):
    intro=json.loads((PROJECT/'SourceAssets/DemoIntro/Dialogue.json').read_text(encoding='utf8'))['lines']
    legacy=json.loads((PROJECT/'SourceAssets/OwnFrequency/Dialogue.json').read_text(encoding='utf8'))
    for fn,cue,key in [('ScanTick','Final','brief'),('ScanTick','Database','tip'),('CompleteMission','Complete','route')]:
        row=next(r for r in intro if r['id']==cue)
        texts={row['text'],row['old_text'],data[key]['text']}
        assets={row['sound']+'.'+row['sound'].rsplit('/',1)[-1],row['old_sound']}
        durations=[row['duration']]
        if key in legacy:
            texts.add(legacy[key]['text'])
            old=load('/Game/Story/OwnFrequency/Audio/S_Frequency_'+key)
            assets.add(old.get_path_name());durations.append(old.duration)
        found=False
        for node in G.get_graph_editor_by_name(bp,fn).list_all_nodes():
            for p in node.list_all_pins():
                value=p.get_pin_value()
                if value in texts:val(p,data[key]['text']);found=True
                elif value in assets:val(p,sounds[key].get_path_name())
                elif str(p.get_pin_name())=='B':
                    try:d=float(value)
                    except (TypeError,ValueError):continue
                    for duration in durations:
                        for pad in (.7,.8):
                            if abs(d-duration-pad)<.002:val(p,sounds[key].duration+pad)
        assert found,(fn,cue)
    # Repair grants navigation; keep the screen clear so the player sees the mast.
    e=G.get_graph_editor_by_name(bp,'CompleteMission')
    for n in e.list_all_nodes():
        pp=n.find_input_pin('PropertyName')
        if pp and pp.is_valid() and pp.get_pin_value()=='NavMapOpen':val(pin(n,'Value'),False)

def build(bp,player,data,sounds):
    focus={0:('FrequencyFocusMonitor',FIRST),1:('FrequencyFocusRadio',SECOND),2:('StationFocusLock',LOCK)}
    methods=[f for f,p in focus.values()]+['FrequencyUse','FrequencyTick','FrequencyResident','FrequencyReply']
    for fn in methods:Story(bp,fn)
    hardware(bp)
    for name,kind,d in [('FrequencyStep','int','0'),('FrequencyReplay','bool','false'),('FrequencyCanUse','bool','false'),('StationHiddenSince','real','-1'),('StationGateAt','real','0'),('StationScanUntil','real','0'),('StationDetected','bool','false')]:
        var(bp,name,kind,d)
    var(bp,'FrequencyLastContact',B.get_struct_type(unreal.Vector.static_struct()),L((0,0,0)))
    var(player,'FrequencyFinished','bool','false');compile_bp(player);compile_bp(bp)
    swap_story_lines(bp,data,sounds)
    for name,point in focus.values():can_use(Story(bp,name),point)
    for fn,key in [('FrequencyResident','resident'),('FrequencyReply','reply')]:speech(Story(bp,fn),key,data,sounds)
    def screen(g,component,key):
        g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get(component),ElementIndex=0,Material=SCREEN+'/MI_'+key))
    def advance(g,step):
        g.set('FrequencyStep',step)
    def alive(g):
        g.branch(g.isstage(6));g.branch(g.valid(g.get('Player')));g.branch(g.get('RecoveryGranted'))
        g.branch(g.not_(g.get('Failed')));g.branch(g.num('Greater',g.pget('VisorIntegrity'),0.))
    g=Story(bp,'FrequencyUse');alive(g);g.branch(g.not_(g.pget('NavMapOpen')))
    for step,(fn,point) in focus.items():
        other=when_step(g,step);g.do(g.own(fn));g.branch(g.get('FrequencyCanUse'))
        if step==0:
            advance(g,5);g.set('StationDetected',False);g.set('StationScanUntil',g.num('Add',g.now(),10.));g.set('StationHiddenSince',-1.);g.set('FrequencyLastContact',g.position(g.get('Player')))
            g.goal(HIDE,DOOR);speech(g,'decoy',data,sounds)
        elif step==1:
            advance(g,2);screen(g,'BroadcastDisplay07','OnAir')
            for i in range(4):g.visibility('EscapeStripe'+str(i),True)
            g.goal(RESCUE,LOCK);g.checkpoint(6,WORKSHOP);g.do(g.own('FrequencyResident'))
        else:
            advance(g,3);g.set('StationGateAt',g.now());g.set('FrequencyReplay',False)
            screen(g,'MedicalDisplay','Open');g.visibility('ReserveLight',True)
            g.sound('/Game/Combat/CyborgModes/S_ModeSelect',L(LOCK),.7)
            g.goal('Ставня поднимается',LOCK)
        g.cursor=other
    g=Story(bp,'FrequencyTick');alive(g)
    for step,(fn,point) in focus.items():
        other=when_step(g,step)
        if step==2:
            retry=g.branch(g.get('FrequencyReplay'));skip=retry.find_else_pin()
            g.set('FrequencyReplay',False);g.do(g.own('FrequencyResident'))
            n=g.do(g.own(fn));link(skip,n.find_execute_pin())
        else:
            if step==0:
                wave=g.math('Sin',A=g.num('Multiply',g.now(),4.5))
                g.do(g.call('Engine.LightComponent.SetIntensity',target=g.get('UplinkGlow'),NewIntensity=g.num('Add',390.,g.num('Multiply',wave,300.))))
            g.do(g.own(fn))
        label=[CUT,HAND,RESCUE][step];prompt=['F · подменить сигнал убежища своим','F · передать местную частоту убежищу','F · снять блокировку медсклада'][step]
        if step==0:label=g.math('SelectString',A='Подмена раскрыта · повтори у антенны',B=label,bPickA=g.get('StationDetected'))
        goal=g.math('SelectString',A=prompt,B=label,bPickA=g.get('FrequencyCanUse'))
        g.branch(g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=g.get('Objective'),B=goal)))
        g.goal(goal,point);g.cursor=other
    # Loss of contact requires actual solid geometry between the mast and the player.
    other=when_step(g,5)
    eye=g.addv(g.position(g.get('Player')),L((0,0,48)))
    hit,parts=g.trace(L((34470,87526,2480)),eye)
    hit_pawn=g.math('EqualEqual_ObjectObject',A=g.out(parts,'HitActor'),B=g.get('Player'))
    hidden=g.branch(g.both(hit,g.not_(hit_pawn)));exposed=hidden.find_else_pin()
    start=g.branch(g.num('Less',g.get('StationHiddenSince'),0.));progress=start.find_else_pin()
    g.set('StationHiddenSince',g.now());g.goal('Держись за стеной · пеленг ослабевает',DOOR)
    g.cursor=progress;g.branch(g.num('GreaterEqual',g.num('Subtract',g.now(),g.get('StationHiddenSince')),1.4))
    advance(g,1);g.set('FrequencyLastContact',L((0,0,0)));g.visibility('UplinkBeacon',False);g.visibility('UplinkGlow',False)
    screen(g,'TrackingDisplay07','Quiet');g.goal(HAND,SECOND);g.checkpoint(6,LOBBY);speech(g,'cut',data,sounds)
    g.cursor=exposed;g.set('StationHiddenSince',-1.);g.set('FrequencyLastContact',g.position(g.get('Player')))
    deadline=g.branch(g.num('GreaterEqual',g.now(),g.get('StationScanUntil')));counting=deadline.find_else_pin()
    advance(g,0);g.set('StationDetected',True);g.goal('Подмена раскрыта · повтори у антенны',FIRST)
    g.sound('/Game/Combat/CyborgModes/S_ModeSelect',L(FIRST),.6)
    g.cursor=counting
    urgent=g.num('Less',g.num('Subtract',g.get('StationScanUntil'),g.now()),4.)
    warning=g.math('SelectString',A='Пеленг усилился · срочно за стену!',B=HIDE,bPickA=urgent)
    g.branch(g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=g.get('Objective'),B=warning)));g.goal(warning,DOOR)
    g.cursor=other;other=when_step(g,3)
    elapsed=g.num('Subtract',g.now(),g.get('StationGateAt'))
    motion=g.branch(g.num('Less',elapsed,1.3));opened=motion.find_else_pin()
    scale_z=g.num('Subtract',1.,g.num('Multiply',elapsed,.73))
    def roll(z):
        g.do(g.call('Engine.SceneComponent.SetRelativeScale3D',target=g.get('MedicalRoll'),NewScale3D=g.vector(1,1,z)))
    roll(scale_z)
    g.cursor=opened;roll(.05);g.branch(g.num('GreaterEqual',g.now(),g.get('DialogueUntil')));advance(g,6);g.set('FrequencyReplay',False)
    g.goal('Медсклад открыт · ответ из подвала',LOCK);g.checkpoint(6,END);g.do(g.own('FrequencyReply'))
    g.cursor=other;other=when_step(g,6)
    replay=g.branch(g.get('FrequencyReplay'));normal=replay.find_else_pin()
    g.set('FrequencyReplay',False);g.do(g.own('FrequencyReply'))
    g.cursor=normal;g.branch(g.ready());advance(g,4);g.pset('FrequencyFinished',True,'Bool')
    g.set('Objective',DONE);g.pset('StoryGoalActive',False,'Bool');g.checkpoint(6,END)
    g.cursor=other;when_step(g,4)
    g.branch(g.out(g.call('Engine.KismetStringLibrary.NotEqual_StrStr',A=g.get('Objective'),B=DONE)));g.set('Objective',DONE);g.pset('StoryGoalActive',False,'Bool')
    compile_bp(bp)
    def prepend(name,method):
        def insert(g,old,tag):
            n=g.do(g.own(method));n.rename(tag)
            for p in old:link(g.cursor,p)
        insert_entry(bp,name,'Own'+method,insert)
    prepend('MissionTick','FrequencyTick');prepend('RequestRecovery','FrequencyUse')
    # Existing retry hook recognizes steps 2 and 3. Add reply replay for step 6
    # after the old hook; the normal mission retry clears the current caption.
    e=G.get_graph_editor_by_name(bp,'RetryCheckpoint')
    hook=next((n for n in e.list_all_nodes() if n.get_name()=='OwnFrequencyRetry'),None)
    if hook:
        flag=pin(hook,'FrequencyReplay')
        flag.break_pin_links()
        graph=Story(bp);graph.e=e
        val(flag,graph.both(graph.isstage(6),graph.math('BooleanOR',A=graph.compare('EqualEqual',graph.get('FrequencyStep'),2),B=graph.compare('EqualEqual',graph.get('FrequencyStep'),6))))
    else:
        def retry(g,old,tag):
            n=g.set('FrequencyReplay',g.math('BooleanOR',A=g.compare('EqualEqual',g.get('FrequencyStep'),2),B=g.compare('EqualEqual',g.get('FrequencyStep'),6)));n.rename(tag)
            for p in old:link(g.cursor,p)
        insert_entry(bp,'RetryCheckpoint','OwnFrequencyRetry',retry)
    def nav(g,old,tag):
        gate=g.branch(g.both(g.get('FrequencyFinished'),g.not_(g.get('NavMapOpen'))));gate.rename(tag)
        for p in old:link(gate.find_else_pin(),p)
    insert_entry(player,'Nav_DrawHUD','OwnFrequencyEndHUD',nav)
    from Install_OmegaNavigation import city_map, POINTS
    assert POINTS[3][0]=='РАДИО / СТ. 07'
    city_map(player)
    # Navigation is already integrated with the story. Change only the old POI.
    for node in G.get_graph_editor_by_name(player,'Nav_RefreshTarget').list_all_nodes():
        for p in node.list_all_pins():
            value=p.get_pin_value()
            if value=='УЗЕЛ СВЯЗИ':val(p,'РАДИО / СТ. 07')
            elif value and '33400' in value and '95600' in value:val(p,L((34526,87526,2150)))
    for fn,replacements in {
        'BeginPatrol':{'Пройти патруль: укрытия или бой':'Станция 07 · минуй патруль по флангу или вступи в бой'},
        'PatrolTick':{'Лаборатория № 2 · найти терминал':'Станция 07 · найди терминал в приёмной'},
        'LabTick':{'Лаборатория № 2 · F — подключить терминал':'Приёмная станции · F у сервисного терминала'},
    }.items():
        for n in G.get_graph_editor_by_name(bp,fn).list_all_nodes():
            for p in n.list_all_pins():
                v=p.get_pin_value()
                if v in replacements:val(p,replacements[v])
    compile_bp(bp);compile_bp(player);save(bp);save(player)


def install():
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    data=json.loads((SOURCE/'Dialogue.json').read_text(encoding='utf8'))
    out=PROJECT/'Saved/StationSeven';out.mkdir(exist_ok=True)
    backup=PROJECT/'Saved/Backups/StationSeven'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    paths=[MISSION,PLAYER,WIDGET]+[AUDIO+'/S_Station07_'+key for key in data]
    assert not dirty.intersection(paths),dirty.intersection(paths)
    for path in paths:
        rel=Path('Content')/(path[6:]+'.uasset');src=PROJECT/rel
        if src.exists():
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    sounds={}
    for key in data:
        path=AUDIO+'/S_Station07_'+key
        if not A.does_asset_exist(path):
            t=unreal.AssetImportTask()
            for k,v in dict(filename=str(SOURCE/(path.rsplit('/',1)[-1]+'.wav')),destination_path=AUDIO,automated=True,save=True).items():t.set_editor_property(k,v)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        sounds[key]=load(path)
    prepare_displays()
    build(load(MISSION),load(PLAYER),data,sounds)
    chapter=load(WIDGET)
    title=unreal.find_object(unreal.find_object(chapter,'WidgetTree'),'ChapterText')
    title.set_text('ПЕРВАЯ МИССИЯ · СВОЯ ЧАСТОТА')
    # Space the short checkpoint hint above the left-side combat visor.
    check=unreal.find_object(unreal.find_object(chapter,'WidgetTree'),'CheckpointText')
    check.slot.set_position(unreal.Vector2D(48,189))
    compile_bp(chapter);save(chapter)
    (out/'Installed.json').write_text(json.dumps({'backup':str(backup),'sounds':{k:v.duration for k,v in sounds.items()},'compiled':[MISSION,PLAYER,WIDGET]},indent=2))
    # Reconnect freshly rebuilt station cues to their visor channels.
    from Install_VisorSubtitles import install as install_visor_subtitles
    install_visor_subtitles()
    # Reconnect the follow-up if the shelter is already part of this project.
    from Install_Shelter07 import SHELTER, build_story as connect_shelter
    if A.does_asset_exist(SHELTER):
        connect_shelter(load(SHELTER))

if __name__=='__main__':install()



