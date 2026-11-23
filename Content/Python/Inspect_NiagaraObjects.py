import unreal,os,json
s=unreal.load_asset('/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight')
r=[]
for o in unreal.ObjectIterator(unreal.Object):
 if isinstance(o,type):continue
 if unreal.SystemLibrary.get_path_name(o).startswith(s.get_path_name()+':'):
  d={'path':unreal.SystemLibrary.get_path_name(o),'class':o.get_class().get_name(),'doc':str(o.__doc__)}
  for prop in ('SpawnInfos','Modules','RendererProperties','EmitterState'):
   try:d[prop]=str(o.get_editor_property(prop))
   except:pass
  r.append(d)
with open(os.path.join(unreal.Paths.project_saved_dir(),'niagara_objects.json'),'w') as f:json.dump(r,f,indent=2)
