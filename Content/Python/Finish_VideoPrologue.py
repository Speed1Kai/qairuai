"""Finalize metadata and in-memory startup settings, without playing the movie."""
import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,compile_bp,save
ROOT='/Game/Cinematics/Prologue';LEVEL=ROOT+'/Lvl_Prologue'
for name in ['WBP_Prologue','BP_ProloguePlayer','BP_PrologueGameMode']:
 bp=A.load_asset(ROOT+'/'+name);compile_bp(bp);save(bp)
settings=unreal.get_default_object(unreal.GameMapsSettings)
for key in ('editor_startup_map','game_default_map'):
 settings.set_editor_property(key,unreal.SoftObjectPath(LEVEL+'.Lvl_Prologue'))
file=A.load_asset(ROOT+'/FM_Prologue')
report={'saved':True,'gameplay_tested':False,'map':LEVEL,'laboratory':'/Game/Lvl_LabTutorial',
 'relative_media_path':file.get_editor_property('file_path'),'duration_seconds':10.006,
 'file_bytes':os.path.getsize(os.path.join(unreal.Paths.project_content_dir(),'Movies/FinalProtocol_Prologue.mp4')),
 'skip_key':'Space','audio':True,'startup_configured':True,
 'assets':list(map(str,A.list_assets(ROOT,recursive=True)))}
with open(os.path.join(unreal.Paths.project_saved_dir(),'video_prologue_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
