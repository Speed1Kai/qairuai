import os,unreal
src=os.path.join(unreal.Paths.project_content_dir(),'Python/Upgrade_PlayerVisor.py')
exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
r['backup']=os.path.join(p,'Saved/Backups/VisorDiagnostics/MaterialConnectionRepair');os.makedirs(r['backup'],exist_ok=True)
material('M_VisorRim',open(os.path.join(p,'SourceAssets/Visor/VisorFrame.hlsl'),encoding='utf8').read(),{'Boot':1.,'T':0.})
material('M_VisorBodyDiagnostics',open(os.path.join(p,'SourceAssets/Visor/VisorBody.hlsl'),encoding='utf8').read(),{**{n:1. for n,_ in parts},'T':0.},A.load_asset(ROOT+'/T_BlackSentinelDiagram'))
unreal.log('VISOR_MATERIAL_CONNECTIONS_SAVED')
