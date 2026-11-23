import unreal,os,json
A=unreal.EditorAssetLibrary;G=unreal.BlueprintGraphEditor;B=unreal.BlueprintEditorLibrary
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
def xyz(v):return [v.x,v.y,v.z]
r={'actors':[],'capsule_sequence':[],'niagara':[],'timeline_api':{}}
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 c=a.get_component_by_class(unreal.StaticMeshComponent)
 rot=a.get_actor_rotation()
 d={'label':a.get_actor_label(),'path':a.get_path_name(),'class':a.get_class().get_path_name(),'p':xyz(a.get_actor_location()),'r':[rot.pitch,rot.yaw,rot.roll],'s':xyz(a.get_actor_scale3d()),'parent':a.get_attach_parent_actor().get_actor_label() if a.get_attach_parent_actor() else None}
 if c:d.update(mesh=c.get_editor_property('static_mesh').get_path_name() if c.get_editor_property('static_mesh') else '',materials=[m.get_path_name() if m else '' for m in c.get_materials()])
 r['actors'].append(d)
seq=A.load_asset('/Game/LabTutorial/Intro/LS_CapsuleAwakening')
for b in seq.get_bindings():
 r['capsule_sequence'].append({'name':str(b.get_display_name()),'id':str(b.get_id()),'tracks':[{'class':t.get_class().get_name(),'sections':[{'channels':[{'name':str(c.get_name()),'keys':[{'time':str(k.get_time()),'value':k.get_value()} for k in c.get_keys()]} for c in s.get_all_channels()]} for s in t.get_sections()]} for t in b.get_tracks()]})
bp=A.load_asset('/Game/LabTutorial/Blueprints/BP_TutorialSlidingDoor');e=G.get_graph_editor_by_name(bp,'EventGraph')
r['timeline_api']={'methods':dir(e),'nodes':[x for x in e.list_available_nodes([]) if any(k in x.lower() for k in ('timeline','camera shake','camerashake'))]}
r['niagara']=[x for x in A.list_assets('/Niagara',recursive=True,include_folder=False) if any(k in x.lower() for k in ('smoke','steam','fountain','empty','minimal','dust','sprite'))][:80]
with open(os.path.join(unreal.Paths.project_saved_dir(),'industrial_lab_inspection.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2,default=str)
