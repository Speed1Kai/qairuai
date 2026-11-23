"""Correct OBJ UV orientation, additive luminance and unobstructed placement."""
import unreal, os, json
filename=os.path.join(unreal.Paths.project_content_dir(),'Python','Build_InteractiveHolograms.py')
scope={}
exec(compile(open(filename,encoding='utf8').read().split('\ntry:')[0],filename,'exec'),scope)
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary
root=scope['ROOT']
scope['textures']=[A.load_asset(root+'/T_HoloArchive_01')]
scope['material']()
for i in range(1,7):
    bp=A.load_asset(root+'/BP_ArchiveProjector_%02d'%i)
    scope['setup_backing'](bp,A.load_asset(root+'/SM_ArchivePanel'))
    for h,c,name in scope['components'](bp):
        if name=='Projection':
            c.modify();c.set_editor_property('relative_location',unreal.Vector(0,-20,224))
    if not B.compile_blueprint(bp):raise RuntimeError('Compile failed '+bp.get_name())
    A.save_loaded_asset(bp,only_if_is_dirty=False)
placements=[(-210,405),(130,405),(470,405),(-420,-340),(-70,-340),(280,-340)]
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if not a.get_actor_label().startswith('HOLO_ArchiveProjector_'):continue
    i=int(a.get_actor_label().rsplit('_',1)[-1])-1
    a.modify();x,y=placements[i]
    a.set_actor_location(unreal.Vector(x,y,0),False,False)
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if c.get_name().startswith('Projection'):
            c.modify();c.set_visibility(False)
            if c.get_name().startswith('ProjectionBacking'):
                c.set_editor_property('relative_location',unreal.Vector(0,2,0))
            elif not c.get_name().startswith('ProjectionBeam'):
                c.set_editor_property('relative_location',unreal.Vector(0,-20,224))
unreal.EditorLoadingAndSavingUtils.save_current_level()
with open(os.path.join(unreal.Paths.project_saved_dir(),'hologram_readability_repair.json'),'w') as f:
    json.dump(dict(saved=True,emission=48,blend='additive with translucent backing',uv='180 degree correction',positions=placements),f,indent=2)
unreal.log('HOLOGRAM READABILITY REPAIR SAVED')
