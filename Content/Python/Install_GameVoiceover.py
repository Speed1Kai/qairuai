"""Install the ElevenLabs voice tracks and connect the new Relay/Post 12 cues."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys

import unreal

project=Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0,str(project/'Content/Python'))
from CityCombat_Common import B, G, compile_bp, link, save
from Install_StoryMemory import GUIDE, MISSION, Story, load
from Install_VisorSubtitles import phrases
from Install_Post12Rescue import MEET, SAFE, L
from Install_ShelterMedic import NPC

source=project/'SourceAssets/GameVoiceover'
rows=json.loads((source/'Manifest.json').read_text(encoding='utf-8'))
backup=project/'Saved/Backups/GameVoiceover'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
output=project/'Saved/GameVoiceover'
output.mkdir(parents=True,exist_ok=True)

def package_path(package):
    return project/'Content'/(package.removeprefix('/Game/').split('.')[0]+'.uasset')

def import_rows():
    paths={}
    factory=unreal.SoundFactory()
    importer=unreal.AssetToolsHelpers.get_asset_tools()
    jobs=[]
    for row in rows:
        package=row['sound'].split('.')[0]
        folder, name=package.rsplit('/',1)
        task=unreal.AssetImportTask()
        task.set_editor_property('filename',str(source/row['file']))
        task.set_editor_property('destination_path',folder)
        task.set_editor_property('destination_name',name)
        task.set_editor_property('automated',True)
        task.set_editor_property('replace_existing',True)
        task.set_editor_property('save',False)
        task.set_editor_property('factory',factory)
        jobs.append(task)
        paths[row['key']]=package
    importer.import_asset_tasks(jobs)
    sounds={}
    for row, task in zip(rows,jobs):
        key=row['key']
        sound=load(paths[key])
        assert isinstance(sound,unreal.SoundWave) and abs(sound.duration-row['duration'])<.025,(key,sound.duration,row['duration'])
        assert len(task.imported_object_paths)==1,(key,task.imported_object_paths)
        sounds[key]=sound
    return sounds

def input_pin(node, name):
    return next((p for p in node.list_all_pins() if str(p.get_pin_name())==name),None)

def set_variable(node, name):
    return node.get_class().get_name()=='K2Node_VariableSet' and input_pin(node,name) is not None

def next_node(node):
    downstream=list(node.find_then_pin().list_connected_pins())
    assert len(downstream)==1,(node.get_name(),len(downstream))
    return downstream[0].get_owning_node()

def locate(mission):
    pending={phrases(r['text'])[0]:r for r in rows if r['key'].split('.')[0] in ('Relay','Post')}
    matches=[]
    for name in B.list_graph_names(mission):
        editor=G.get_graph_editor_by_name(mission,name)
        for node in editor.list_all_nodes():
            if not set_variable(node,'VisorRadioFirst'):
                continue
            text=str(node.find_input_pin('VisorRadioFirst').get_pin_value())
            if text not in pending:
                continue
            current=next_node(next_node(next_node(node)))
            assert set_variable(current,'VisorRadioUntil'),(name,node.get_name(),current.get_name())
            row=pending.pop(text)
            following=list(current.find_then_pin().list_connected_pins())
            assert len(following)==1,(name,row['key'])
            tag='RecordedVoice_'+row['key'].replace('.','_')
            if following[0].get_owning_node().get_name()!=tag:
                matches.append((editor,current,following,row))
    assert not pending,[r['key'] for r in pending.values()]
    return matches

def wire(mission,matches,sounds):
    for editor,current,following,row in matches:
        key=row['key']
        graph=Story(mission)
        graph.e=editor
        graph.i=len(editor.list_all_nodes())+8
        graph.cursor=current.find_then_pin()
        existing=list(current.find_then_pin().list_connected_pins())
        assert len(existing)==len(following)
        graph.cursor.break_pin_links()
        # Keep the original cue beep. Radio shares the existing subtitle/audio channel.
        path=sounds[key].get_path_name()
        if row['channel']=='radio':
            radio=graph.get('ExternalRadioVoice')
            first=graph.do(graph.call('Engine.AudioComponent.SetSound',target=radio,NewSound=path))
            graph.do(graph.call('Engine.AudioComponent.Play',target=radio,StartTime=0.))
        else:
            position=SAFE if key=='Post.Safe' else MEET
            first=graph.sound(path,L(position),.86)
        first.rename('RecordedVoice_'+key.replace('.','_'))
        for destination in following:
            link(graph.cursor,destination)

def verify(mission, sounds):
    packages={s.get_path_name().split('.')[0]:k for k,s in sounds.items()}
    users={key:[] for key in sounds}
    for bp in [mission,load(GUIDE),load(NPC)]:
        compile_bp(bp)
        for name in B.list_graph_names(bp):
            editor=G.get_graph_editor_by_name(bp,name)
            for node in editor.list_all_nodes():
                if node.get_class().get_name()!='K2Node_CallFunction':
                    continue
                for pin_name in ('NewSound','Sound'):
                    p=input_pin(node,pin_name)
                    if p is None:continue
                    key=packages.get(str(p.get_pin_value()).split('.')[0])
                    if key is not None:
                        users[key].append(bp.get_name()+'.'+str(name))
    unused={'Intro.Final','Intro.Database','Intro.Complete','Phone.Reply'}
    assert all(users[key] for key in users.keys()-unused),[key for key,targets in users.items() if not targets]
    return users

def main():
    mission=load(MISSION)
    matches=locate(mission)
    paths=[package_path(r['sound']) for r in rows]+[package_path(MISSION)]
    for p in paths:
        if p.is_file():
            dst=backup/p.relative_to(project)
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,dst)
    sounds=import_rows()
    wire(mission,matches,sounds)
    users=verify(mission,sounds)
    for sound in sounds.values():
        save(sound)
    save(mission)
    report={
        'backup':str(backup),'replaced':34,'connected':8,'new_connections':len(matches),
        'clips':[{**row,'engine_seconds':sounds[row['key']].duration,'graphs':users[row['key']]} for row in rows],
    }
    (output/'Installed.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    unreal.log('GameVoiceover: verified '+str(len(sounds))+' SoundWave assets and compiled the story and guide Blueprints.')

if __name__=='__main__':
    main()
