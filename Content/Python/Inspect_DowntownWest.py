"""Read the downloaded demonstration scene into a renderer-independent placement manifest.
Run with UnrealEditor-Cmd -nullrhi -run=pythonscript; never saves the source map.
"""
import unreal,json,traceback
from pathlib import Path
from collections import Counter
out=Path(unreal.Paths.project_saved_dir())/'CityRealism'
out.mkdir(parents=True,exist_ok=True)
r={'complete':False}
vec=lambda v:[v.x,v.y,v.z]
def tf(t):
    rot=t.rotation.rotator()
    return {'location':vec(t.translation),'rotation':[rot.pitch,rot.yaw,rot.roll],'scale':vec(t.scale3d)}
try:
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(['/Game/Downtown_West'],force_rescan=True)
    data=registry.get_assets_by_path('/Game/Downtown_West',True)
    r['classes']=dict(Counter(str(a.asset_class_path.asset_name) for a in data))
    world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Downtown_West/Maps/Demo_Environment')
    assert world
    rows=[]
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        comps=[]
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not c.static_mesh:continue
            transforms=[tf(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())] if isinstance(c,unreal.InstancedStaticMeshComponent) else [tf(c.get_world_transform())]
            if not transforms:continue
            comps.append({'mesh':c.static_mesh.get_path_name(),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],'transforms':transforms})
        if comps:
            p,e=actor.get_actor_bounds(False)
            rows.append({'label':actor.get_actor_label(),'folder':str(actor.get_folder_path()),'origin':vec(p),'extent':vec(e),'components':comps})
    r.update(complete=True,actors=rows)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
(out/'West_SourceInventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
assert r['complete'],r.get('error')
