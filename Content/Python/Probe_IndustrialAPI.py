import unreal,json,os
r={}
for n in ('NiagaraSystem','NiagaraEmitter','NiagaraSystemFactoryNew','NiagaraEditorScriptingUtilities','NiagaraSpriteRendererProperties','NiagaraStatelessEmitter','TimelineTemplate','LegacyCameraShake','MatineeCameraShake','CurveFloat','RichCurve','TTFloatTrack'):
 c=getattr(unreal,n,None);r[n]={'doc':str(getattr(c,'__doc__','')),'methods':dir(c)} if c else None
for path in ('/Niagara/DefaultAssets/Templates/Systems/FountainLightweight','/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight','/Niagara/DefaultAssets/Templates/Systems/MinimalLightweight','/Niagara/DefaultAssets/Templates/Emitters/Fountain'):
 x=unreal.load_asset(path);r[path]={'class':x.get_class().get_name(),'doc':str(x.__doc__)} if x else None
bp=unreal.load_asset('/Game/LabTutorial/Blueprints/BP_TutorialSlidingDoor');e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
r['timelines']=[x for x in e.list_available_nodes([]) if any(t in x.lower() for t in ('времен','timeline','шкала'))]
with open(os.path.join(unreal.Paths.project_saved_dir(),'industrial_api.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
