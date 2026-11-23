"""Disable the rejected memory film without restoring the older hologram."""
import json,shutil
from datetime import datetime
from pathlib import Path
import unreal
import Install_StoryMemory as ST
from CityCombat_Common import A,B,G,compile_bp,save,link

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SAVED=PROJECT/'Saved/MemoryFilm'

def install():
    SAVED.mkdir(parents=True,exist_ok=True)
    backup=PROJECT/'Saved/Backups/MemoryFilmRemoval'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True,exist_ok=True)
    source=PROJECT/'Content/Story/ForeignMemory/BP_ForeignMemory.uasset'
    shutil.copy2(source,backup/source.name)
    bp=A.load_asset(ST.MISSION);assert bp
    # Both entry points advance safely, with no cutscene or playback request.
    for name in ('BeginMemory','MemoryTick'):
        g=ST.Story(bp,name)
        if 'CloseMemoryFilm' in map(str,B.list_graph_names(bp)):
            g.do(g.own('CloseMemoryFilm'))
        g.visibility('MemoryRoot',False)
        g.set('MemoryStarted',False);g.set('MemoryCaption','')
        g.do(g.call('Engine.AudioComponent.Stop',target=g.get('Voice')))
        g.pcall('Story_RestoreDamage')
        locked=g.branch(g.get('InputLocked'));skip=locked.find_else_pin()
        g.do(g.call('Engine.Controller.SetIgnoreMoveInput',target=g.pc(),bNewMoveInput=False))
        g.do(g.call('Engine.Controller.SetIgnoreLookInput',target=g.pc(),bNewLookInput=False))
        reset=g.set('InputLocked',False);link(skip,reset.find_execute_pin())
        g.pset('StoryBusy',False,'Bool')
        g.do(g.own('CompleteMission'))
    compile_bp(bp);save(bp)
    manifest=SAVED/'Install.json'
    data=json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else {}
    data.update(enabled=False,removed_from_game=True,removal_backup=str(backup))
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    report={'disabled':True,'old_hologram_restored':False,'mission_flow':'terminal fight -> repair, Omega and relay objective','backup':str(backup)}
    (SAVED/'Removal.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

if __name__=='__main__':install()
