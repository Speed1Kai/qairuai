import unreal,os,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
r={'actors':[],'api':{}}
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 p=a.get_actor_location()
 if 850<p.x<1700:
  o,e=a.get_actor_bounds(False)
  c=a.get_component_by_class(unreal.StaticMeshComponent)
  r['actors'].append({'label':a.get_actor_label(),'class':a.get_class().get_path_name(),'p':[p.x,p.y,p.z],'bounds':[[o.x,o.y,o.z],[e.x,e.y,e.z]],'mesh':str(c.get_editor_property('static_mesh')) if c else ''})
for name in ('BlueprintGraphEditor','BlueprintEditorLibrary','TimelineTemplate','CurveFloat','RichCurve','RichCurveKey','TTFloatTrack','SubobjectDataSubsystem'):
 cls=getattr(unreal,name,None)
 r['api'][name]={'doc':str(getattr(cls,'__doc__','')),'methods':dir(cls)} if cls else None
bp=unreal.load_asset('/Game/LabTutorial/Industrial/BP_HeavyBlastDoor')
r['nodes']=[]
for node in unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph').list_all_nodes():
 if node.get_class().get_name()=='K2Node_Timeline':
  r['nodes'].append({'name':node.get_name(),'doc':str(node.__doc__),'methods':dir(node)})
with open(os.path.join(unreal.Paths.project_saved_dir(),'splitdoor_inspection.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2,default=str)
