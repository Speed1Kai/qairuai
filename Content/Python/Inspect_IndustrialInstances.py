import unreal,os,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
r={}
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 n=a.get_actor_label()
 if a.get_class().get_name().startswith('BP_ArchiveProjector_') or n.startswith('IND_'):
  row=[]
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   row.append({'name':c.get_name(),'visible':c.is_visible(),'mesh':c.get_editor_property('static_mesh').get_name() if c.get_editor_property('static_mesh') else None,'materials':[m.get_name() if m else None for m in c.get_materials()],'parent':c.get_attach_parent().get_name() if c.get_attach_parent() else None})
  r[n]=row
with open('S:/Final_Protocol/Saved/industrial_instances.json','w') as f:json.dump(r,f,indent=2)
