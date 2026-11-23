import unreal,os,json
r={}
for n in ('CubeBuilder','NavMeshBoundsVolume','NavigationSystemV1','AnimBlueprint','BlendSpace','BlueprintGraphEditor','AnimationLibrary'):
 c=getattr(unreal,n,None)
 if c:r[n]=[x for x in dir(c) if not x.startswith('_')]
for path in ('/Engine/ArtTools/RenderToTexture/Enums/RenderToTexture_Enum','/Engine/ArtTools/RenderToTexture/Enums/EFloatTypes'):
 e=unreal.load_asset(path)
 if e:
  try:r[path]={'map':{str(k):str(v) for k,v in e.get_editor_property('DisplayNameMap').items()},'class':e.get_class().get_name()}
  except Exception as ex:r[path]=str(ex)
bp=unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed');e=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'AnimGraph')
r['anim_actions']=[n for n in e.list_available_nodes([]) if any(s in n.lower() for s in ('modify bone','изменить кость','transform (modify)','blend poses','слот'))][:55]
r['anim_functions']=[x for x in dir(unreal.AnimGraphNode_ModifyBone) if not x.startswith('_')]
bs=unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run')
for p in ('sample_data','blend_parameters'):
 try:r['blend_'+p]=str(bs.get_editor_property(p))
 except Exception as ex:r[p]=str(ex)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
a=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.NavMeshBoundsVolume,unreal.Vector(0,0,0))
r['nav_bounds_before']=str(a.get_actor_bounds(False))
try:
 builder=unreal.new_object(unreal.load_class(None,'/Script/UnrealEd.CubeBuilder'))
 builder.set_editor_property('x',600.);builder.set_editor_property('y',600.);builder.set_editor_property('z',400.)
 r['cube_build']=str(builder.build(unreal.EditorLevelLibrary.get_editor_world(),a));r['nav_bounds_after']=str(a.get_actor_bounds(False))
except Exception as ex:r['cube_build_error']=str(ex)
with open('S:/Final_Protocol/Saved/enemy_details_probe.json','w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
