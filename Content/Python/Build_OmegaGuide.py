"""Install OMEGA's voiced tutorial in the existing laboratory map."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import wave

import unreal
from CityCombat_Common import A, B, G, Graph, V, add, asset, compile_bp, link, pin, save, val, var

ROOT='/Game/LabTutorial/OmegaGuide'
MAP='/Game/Lvl_LabTutorial'
POWER='/Game/LabTutorial/Basement/BP_BuildingPower'
ARCHIVE='/Game/LabTutorial/FirstFloor/BP_Floor01Archive'
LEGACY='/Game/LabTutorial/Blueprints/BP_TutorialHologramTrigger'
CONTENT=Path(unreal.Paths.project_content_dir()).resolve()
SAVED=Path(unreal.Paths.project_saved_dir()).resolve()
SOURCE=CONTENT.parent/'SourceAssets/OmegaVoice'
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
LEVELS=unreal.EditorLoadingAndSavingUtils
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def load(path):
    value=A.load_asset(path)
    assert value,path
    return value


def prepare_lines(reimport=False):
    result={}
    for index,row in enumerate(json.loads((SOURCE/'Lines.json').read_text(encoding='utf-8-sig'))):
        cue=row['id']
        filename=SOURCE/('S_Omega_'+cue+'.wav')
        with wave.open(str(filename),'rb') as wav:
            seconds=wav.getnframes()/wav.getframerate()
            assert wav.getnchannels()==1 and 3.<seconds<12., (cue,seconds)
        path=ROOT+'/'+filename.stem
        if reimport or not A.does_asset_exist(path):
            task=unreal.AssetImportTask()
            for k,v in dict(filename=str(filename),destination_path=ROOT,destination_name=filename.stem,
                            automated=True,replace_existing=reimport,save=False).items():
                task.set_editor_property(k,v)
            TOOLS.import_asset_tasks([task])
            assert task.get_objects(),filename
        sound=load(path)
        assert abs(sound.get_editor_property('duration')-seconds)<.05,(cue,seconds)
        subtitle=unreal.SubtitleCue()
        subtitle.set_editor_property('text',unreal.Text('OMEGA  ·  '+row['text']))
        subtitle.set_editor_property('time',.12)
        sound.set_editor_property('subtitles',[subtitle])
        save(sound)
        result[cue]=(index,sound,row['text'],seconds)
    return result


class GuideGraph(Graph):
    def player_loc(self):
        return self.out(self.call('Engine.Actor.K2_GetActorLocation',target=self.player()))

    def no(self,condition):
        return self.math('Not_PreBool',A=condition)

    def both(self,a,b):
        return self.math('BooleanAND',A=a,B=b)

    def either(self,a,b):
        return self.math('BooleanOR',A=a,B=b)

    def gt(self,a,b):
        return self.math('Greater_DoubleDouble',A=a,B=b)

    def lt(self,a,b):
        return self.math('Less_DoubleDouble',A=a,B=b)

    def add(self,a,b):
        return self.math('Add_DoubleDouble',A=a,B=b)

    def elapsed(self,var):
        return self.math('Subtract_DoubleDouble',A=self.now(),B=self.get(var))

    def external(self,var,field,blueprint):
        n=self.node(self.e.add_get_member_variable_node(field,B.generated_class(blueprint).get_path_name()))
        val(n.find_self_pin(),self.get(var))
        return pin(n,field,True)

    def idle(self):
        playing=self.out(self.do(self.call('Engine.AudioComponent.IsPlaying',target=self.get('Voice'))))
        self.branch(self.no(playing))
        self.branch(self.gt(self.now(),self.get('BusyUntil')))
        self.branch(self.gt(self.elapsed('LastFire'),1.1))

    def launch(self,cue,condition):
        allowed=self.both(self.no(self.get('Heard'+cue)),condition)
        b=self.branch(allowed)
        self.do(self.own('Speak_'+cue))
        self.cursor=b.find_else_pin()


def line_graph(bp,cue,entry):
    index,sound,_,seconds=entry
    g=GuideGraph(bp,'Speak_'+cue)
    g.idle()
    g.set('Heard'+cue,True)
    g.set('LastLine',index)
    g.set('BusyUntil',g.add(g.now(),seconds+.30))
    g.count('VoiceStarts')
    voice=g.get('Voice')
    g.do(g.call('Engine.AudioComponent.SetSound',target=voice,NewSound=sound.get_path_name()))
    g.do(g.call('Engine.AudioComponent.Play',target=voice,StartTime=0.))
    compile_bp(bp)


def author_guide(lines):
    bp=asset(ROOT+'/BP_OmegaGuide')
    c=add(bp,unreal.AudioComponent,'Voice')
    c.set_editor_property('auto_activate',False)
    c.set_editor_property('allow_spatialization',False)
    c.set_editor_property('volume_multiplier',.95)
    c.set_editor_property('suppress_subtitles',False)
    power,archive=load(POWER),load(ARCHIVE)
    for n,typ,d in (('LastLine','int','-1'),('VoiceStarts','int','0'),('BusyUntil','real','0'),
                    ('LastFire','real','-10'),('WakeTime','real','0'),('ArchiveOpened','bool','false')):
        var(bp,n,typ,d)
    var(bp,'PowerSource',B.get_object_reference_type(B.generated_class(power)),'None')
    var(bp,'ArchiveSource',B.get_object_reference_type(B.generated_class(archive)),'None')
    for cue in lines:
        var(bp,'Heard'+cue,'bool','false')
    compile_bp(bp)
    for cue,entry in lines.items():
        line_graph(bp,cue,entry)

    g=GuideGraph(bp,'Omega_ObserveArchive')
    g.branch(g.valid(g.get('ArchiveSource')))
    g.branch(g.external('ArchiveSource','bIsReading',archive))
    g.set('ArchiveOpened',True)
    compile_bp(bp)

    g=GuideGraph(bp,'Omega_Poll')
    g.branch(g.valid(g.player()))
    g.branch(g.valid(g.pc()))
    g.do(g.own('Omega_ObserveArchive'))
    g.branch(g.no(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
    fire=g.branch(g.out(g.call('Engine.PlayerController.IsInputKeyDown',target=g.pc(),Key='(KeyName="LeftMouseButton")')))
    g.set('LastFire',g.now())
    g.cursor=fire.find_else_pin()
    g.idle()
    coords=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.player_loc())
    x,y,z=(g.out(coords,k) for k in 'XYZ')
    g.branch(g.gt(g.now(),3.))
    wake=g.branch(g.no(g.get('HeardWake')))
    g.set('WakeTime',g.now())
    g.do(g.own('Speak_Wake'))
    g.cursor=wake.find_else_pin()
    g.launch('Mission',g.gt(g.elapsed('WakeTime'),4.))
    g.launch('City',g.both(g.gt(y,21950.),g.gt(z,2100.)))
    court=g.both(g.gt(y,1640.),g.both(g.gt(z,1800.),g.both(g.lt(y,21950.),g.gt(x,2400.))))
    g.launch('Courtyard',court)
    g.launch('Archive',g.get('ArchiveOpened'))
    g.launch('Upper',g.both(g.gt(z,2180.),g.both(g.gt(x,2770.),g.lt(y,1550.))))
    g.branch(g.lt(z,950.))
    g.branch(g.valid(g.get('PowerSource')))
    powered=g.external('PowerSource','bBuildingPowered',power)
    g.launch('PowerReady',powered)
    close=g.both(g.gt(x,1650.),g.both(g.lt(x,3050.),g.both(g.gt(y,-710.),g.lt(y,650.))))
    g.launch('Power',g.both(g.no(powered),g.either(close,g.gt(g.elapsed('WakeTime'),21.))))
    compile_bp(bp)

    g=GuideGraph(bp,'Omega_Repeat')
    g.branch(g.valid(g.pc()))
    g.branch(g.no(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))))
    g.idle()
    for cue,(index,*_) in lines.items():
        b=g.branch(g.math('EqualEqual_IntInt',A=g.get('LastLine'),B=index))
        g.do(g.own('Speak_'+cue))
        g.cursor=b.find_else_pin()
    compile_bp(bp)

    g=GuideGraph(bp)
    g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
    g.override('ReceiveBeginPlay')
    for varname,source in (('PowerSource',power),('ArchiveSource',archive)):
        find=g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=B.generated_class(source).get_path_name()))
        actor=g.out(find)
        g.set(varname,actor)
    g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.16))
    g.override('ReceiveTick')
    g.do(g.own('Omega_Poll'))
    menu=next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|H'))
    key=g.e.create_node_from_name(menu,unreal.Vector2D(x=0,y=1600),[])
    h=unreal.Key()
    h.set_editor_property('key_name','H')
    key.set_editor_property('input_key',h)
    key.set_editor_property('bConsumeInput',False)
    g.cursor=pin(key,'Pressed',True)
    g.do(g.own('Omega_Repeat'))
    compile_bp(bp)
    cd=unreal.get_default_object(B.generated_class(bp))
    cd.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
    save(bp)
    return bp


def suppress_cards(path,titles):
    bp=load(path)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    edits=0
    nodes=graph.list_all_nodes()
    def bypass(node):
        before=list(node.find_execute_pin().list_connected_pins())
        if not before:
            return 0
        assert len(before)==1,node.get_name()
        after=list(node.find_then_pin().list_connected_pins())
        node.find_execute_pin().break_pin_links()
        node.find_then_pin().break_pin_links()
        for p in after:
            link(before[0],p)
        return 1
    if path==POWER:
        for name in ('K2Node_CallFunction_67','K2Node_CallFunction_169'):
            node=next(n for n in nodes if n.get_name()==name)
            assert str(node.get_node_title())=='AddToViewport'
            edits+=bypass(node)
    for n in nodes:
        if str(n.get_node_title())!='SetStringPropertyByName':
            continue
        prop=pin(n,'PropertyName').get_pin_value()
        title=pin(n,'Value').get_pin_value()
        if prop!='HUDTitle' or title not in titles:
            continue
        cursor=n
        for _ in range(5):
            out=list(cursor.find_then_pin().list_connected_pins())
            if len(out)!=1:
                break
            node=out[0].get_owning_node()
            if str(node.get_node_title())=='AddToViewport':
                edits+=bypass(node)
                break
            cursor=node
    if edits:
        compile_bp(bp)
        save(bp)
    return edits


def main():
    assert not LEVELS.get_dirty_map_packages()
    backup=SAVED/'Backups/OmegaGuide'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path,ext in ((MAP,'.umap'),(POWER,'.uasset'),(LEGACY,'.uasset')):
        shutil.copy2(CONTENT/(path.removeprefix('/Game/')+ext),backup)
    lines=prepare_lines()
    bp=author_guide(lines)
    hidden=suppress_cards(POWER,{'РЕЗЕРВНОЕ ПИТАНИЕ','ЭЛЕКТРОПИТАНИЕ ВОССТАНОВЛЕНО'})
    hidden+=suppress_cards(LEGACY,{'ПРОТОКОЛ OMEGA / ПРОБУЖДЕНИЕ'})
    world=LEVELS.load_map(MAP)
    assert world
    for old in ACTORS.get_all_level_actors():
        if old.get_actor_label()=='OMEGA_VoiceGuide':
            assert ACTORS.destroy_actor(old)
    guide=ACTORS.spawn_actor_from_class(B.generated_class(bp),V(0,0,0))
    guide.set_actor_label('OMEGA_VoiceGuide')
    guide.set_folder_path('LAB/Guidance')
    world.modify()
    assert LEVELS.save_map(world,MAP)
    (SAVED/'omega_guide.json').write_text(json.dumps(dict(saved=True,backup=str(backup),lines=list(lines),
               narration_cards_replaced_on_this_run=hidden,level=MAP),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
