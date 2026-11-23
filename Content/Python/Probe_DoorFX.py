import unreal,json,os
r={'object_helpers':[n for n in dir(unreal) if 'objects' in n.lower() or 'iterator' in n.lower()]}
for path in ('/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight','/Niagara/DefaultAssets/Templates/Systems/FountainLightweight'):
 s=unreal.load_asset(path)
 r[path]={}
 try:
  objects=unreal.get_objects_with_outer(s,include_nested_objects=True)
  r[path]['objects']=[{'name':o.get_path_name(),'class':o.get_class().get_name()} for o in objects]
 except Exception as ex:r[path]['objects_error']=str(ex)
 for name in ('EmitterHandles','EmitterHandle','StatelessEmitter','emitter_handles'):
  try:r[path][name]=str(s.get_editor_property(name))
  except Exception as ex:r[path][name]=str(ex)
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
path='/Game/LabTutorial/Industrial/BP_HeavyBlastDoor';A.make_directory('/Game/LabTutorial/Industrial')
bp=A.load_asset(path) if A.does_asset_exist(path) else None
if not bp:
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
 bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_HeavyBlastDoor','/Game/LabTutorial/Industrial',unreal.Blueprint,f)
e=G.get_graph_editor_by_name(bp,'EventGraph')
names=[x for x in e.list_available_nodes([]) if x.startswith('|') and ('Timeline' in x or 'шкалу' in x)]
n=e.create_node_from_name(names[0],unreal.Vector2D(),[])
r['timeline']={'node':n.get_name(),'pins':[str(p.get_pin_name()) for p in n.list_all_pins()]}
for k in ('TimelineName','timeline_name'):
 try:r['timeline'][k]=str(n.get_editor_property(k))
 except Exception as ex:r['timeline'][k]=str(ex)
for k in ('Timeline_Template','Timeline_0_Template','ШкалаВремени_Template','ШкалаВремени_0_Template'):
 x=unreal.find_object(bp,k)
 if x:r['template']={'path':x.get_path_name(),'length':x.get_editor_property('timeline_length')}
with open(os.path.join(unreal.Paths.project_saved_dir(),'door_fx_probe.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
