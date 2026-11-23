"""Keep source detail and painted vertex data while batching each chosen building."""
import unreal,json,traceback
from pathlib import Path
P=Path('S:/Final_Protocol');OUT=P/'Saved/CityRealism'
r={'complete':False,'buildings':[]}
try:
    source=json.loads((OUT/'West_SourceInventory.json').read_text(encoding='utf8'))['actors']
    selection=json.loads((P/'SourceAssets/CityRealism/Selection.json').read_text(encoding='utf8'))
    assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Downtown_West/Maps/Demo_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label={a.get_actor_label():a for a in actors.get_all_level_actors()}
    # Commandlets omit some editor subsystem instances. These utility methods
    # carry no per-instance state and can run on their class default object.
    sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
    for b in selection['buildings']:
        chosen=[by_label[source[i]['label']] for i in b['actors']]
        flattened=[]
        for a in chosen:
            if isinstance(a,unreal.StaticMeshActor):flattened.append(a);continue
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                if not c.static_mesh:continue
                proxy=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
                proxy.static_mesh_component.set_static_mesh(c.static_mesh)
                proxy.static_mesh_component.set_world_transform(c.get_world_transform(),False,True)
                for i in range(c.get_num_materials()):proxy.static_mesh_component.set_material(i,c.get_material(i))
                flattened.append(proxy)
        chosen=flattened
        path='/Game/Environment/CityRealism/SM_DW_'+b['name']
        options=unreal.MergeStaticMeshActorsOptions()
        options.set_editor_property('destroy_source_actors',False)
        options.set_editor_property('spawn_merged_actor',True)
        options.set_editor_property('new_actor_label','EXPORT_'+b['name'])
        options.set_editor_property('base_package_name',path)
        settings=unreal.MeshMergingSettings()
        for name,value in [('merge_materials',False),('merge_physics_data',False),('generate_light_map_uv',False),('bake_vertex_data_to_mesh',True),('support_ray_tracing',False),('allow_distance_field',False)]:settings.set_editor_property(name,value)
        settings.set_editor_property('pivot_type',unreal.MeshMergePivotType.CUSTOM)
        settings.set_editor_property('custom_pivot_location',unreal.Vector(*b['source_origin']))
        options.set_editor_property('mesh_merging_settings',settings)
        merged=sms.merge_static_mesh_actors(chosen,options)
        actor=merged[-1] if isinstance(merged,tuple) else merged
        mesh=actor.static_mesh_component.static_mesh if actor else None
        assert mesh,(path,str(merged))
        path=mesh.get_path_name().split('.')[0]
        reduction=unreal.StaticMeshReductionOptions();reduction.set_editor_property('auto_compute_lod_screen_size',False)
        values=[]
        for fraction,size in [(1.,1.),(.55,.32),(.25,.14),(.10,.055)]:
            v=unreal.StaticMeshReductionSettings();v.set_editor_property('percent_triangles',fraction);v.set_editor_property('screen_size',size);values.append(v)
        reduction.set_editor_property('reduction_settings',values)
        assert sms.set_lods(mesh,reduction)==4
        sms.remove_collisions(mesh)
        assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
        materials=[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials]
        assert all(materials),materials
        box=mesh.get_bounding_box()
        record={'name':b['name'],'mesh':path,'actors':len(chosen),'materials':materials,'triangles':[mesh.get_num_triangles(i) for i in range(4)],'pivot':b['source_origin'],'bounds':[list((box.min.x,box.min.y,box.min.z)),list((box.max.x,box.max.y,box.max.z))]}
        r['buildings'].append(record)
        (OUT/'MergedBuildings.json').write_text(json.dumps(r,indent=2),encoding='utf8')
    r['complete']=True
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
(OUT/'MergedBuildings.json').write_text(json.dumps(r,indent=2),encoding='utf8')
assert r['complete'],r.get('error')
