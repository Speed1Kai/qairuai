import unreal,os,json
r={}
for cls in ['MediaPlayer','MediaTexture','FileMediaSource','MediaSoundComponent','GameMapsSettings','ProjectPackagingSettings','WidgetBlueprintLibrary','ScaleBox','EditorLoadingAndSavingUtils']:
 c=getattr(unreal,cls,None)
 r[cls]={n:str(getattr(c,n).__doc__) for n in dir(c or []) if any(k in n for k in ['media_player','file_path','new_level','default_map','open_source','duration','time','stretch','sound','looping'])}
with open(os.path.join(unreal.Paths.project_saved_dir(),'prologue_api.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
