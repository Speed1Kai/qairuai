"""Build a static, instanced street from selected native Downtown West assemblies.
Selection is recorded in SourceAssets/CityRealism/Selection.json after source inspection.
"""
import unreal,json,math,shutil,hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter
from Industrial_Common import A,B,G,add,components,compile_bp,save
from DowntownWest_FacadeMaterials import facade_materials

PROJECT=Path(unreal.Paths.project_dir()).resolve()
ROOT='/Game/Environment/CityRealism'
CITY='/Game/Surface/Lvl_CampusConnected'
MAIN=PROJECT/'Content/Lvl_LabTutorial.umap'
WORK=PROJECT/'Saved/CityRealism'
SOURCE=PROJECT/'SourceAssets/CityRealism'
BPNAME=ROOT+'/BP_DowntownWestStreet'
OFFSET=unreal.Vector(10006.289955343997,6612.598659341473,2150.)
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS=unreal.EditorLoadingAndSavingUtils
vec=lambda v:[v.x,v.y,v.z]

def load(path):
    o=A.load_asset(path);assert o,path
    return o

def transform(row):
    return unreal.Transform(location=unreal.Vector(*row['location']),rotation=unreal.Rotator(pitch=row['rotation'][0],yaw=row['rotation'][1],roll=row['rotation'][2]),scale=unreal.Vector(*row['scale']))

def pavement_height(world,x,y,ignore):
    start=unreal.Vector(x,y,2250)-OFFSET;end=unreal.Vector(x,y,2100)-OFFSET
    hit=unreal.SystemLibrary.line_trace_single(world,start,end,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
    if hit:
        values=hit.to_tuple()
        if values[0]:return values[5].z+OFFSET.z
    return 2172.

class Street:
    def __init__(self,bp):
        self.bp=bp;self.groups={};self.count=0;self.mirrored=[]
        root=add(bp,unreal.SceneComponent,'Root')
        records=components(bp);sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
        rh=next(h for h,c,n in records if n=='Root')
        if not lib.is_root_component(lib.get_data(rh)):assert sub.make_new_scene_root(records[0][0],rh,bp)
        root.set_mobility(unreal.ComponentMobility.STATIC)
        for _,c,_ in components(bp):
            if isinstance(c,unreal.InstancedStaticMeshComponent):c.clear_instances()
            elif isinstance(c,unreal.StaticMeshComponent) and n.startswith('WestMirror_'):c.set_static_mesh(None)
    def item(self,mesh,t,materials=(),collision=False,hidden=False,cull=45000):
        materials=facade_materials(mesh,materials)
        # Instanced draws share culling orientation. Give mirrored transforms a
        # regular primitive so Unreal handles their determinant correctly.
        s=t.scale3d
        if s.x*s.y*s.z<0:
            c=add(self.bp,unreal.StaticMeshComponent,'WestMirror_%03d'%len(self.mirrored),'Root')
            c.set_mobility(unreal.ComponentMobility.STATIC);c.set_static_mesh(load(mesh))
            c.set_relative_transform(t,False,False)
            c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
            c.set_editor_property('can_ever_affect_navigation',collision);c.set_cull_distance(float(cull))
            c.set_visibility(not hidden);c.set_hidden_in_game(hidden);c.set_cast_shadow(not hidden)
            for i,m in enumerate(materials):
                if m:c.set_material(i,load(m))
            self.mirrored.append(c);self.count+=1
            return
        key=(mesh,tuple(materials),collision,hidden,cull)
        if key not in self.groups:
            c=add(self.bp,unreal.HierarchicalInstancedStaticMeshComponent,'West_%03d'%len(self.groups),'Root')
            c.clear_instances();c.set_static_mesh(load(mesh));c.set_mobility(unreal.ComponentMobility.STATIC)
            c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
            c.set_editor_property('can_ever_affect_navigation',collision);c.set_cull_distances(0,cull)
            c.set_visibility(not hidden);c.set_hidden_in_game(hidden)
            if hidden:c.set_cast_shadow(False)
            for i,m in enumerate(materials):
                if m:c.set_material(i,load(m))
            self.groups[key]=c
        self.groups[key].add_instance(t,False);self.count+=1
    def box(self,center,size,material,hidden=False,collision=True):
        self.item('/Engine/BasicShapes/Cube.Cube',unreal.Transform(location=unreal.Vector(*center),scale=unreal.Vector(*(v/100 for v in size))),[material],collision,hidden,60000)


def dependency_budget(paths):
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    visited=set();pending=list(paths)
    opts=unreal.AssetRegistryDependencyOptions(include_soft_package_references=False,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
    while pending:
        p=pending.pop().split('.')[0]
        if p in visited or not p.startswith('/Game/Downtown_West'):continue
        visited.add(p)
        pending.extend(str(x) for x in registry.get_dependencies(p,opts))
    prepared=[]
    for p in sorted(visited):
        d=registry.get_asset_by_object_path(p+'.'+p.rsplit('/',1)[-1])
        if str(d.asset_class_path.asset_name)=='Material':
            m=d.get_asset()
            if unreal.MaterialEditingLibrary.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES):save(m)
    for p in sorted(visited):
        d=registry.get_asset_by_object_path(p+'.'+p.rsplit('/',1)[-1])
        cls=str(d.asset_class_path.asset_name)
        if cls not in ('Texture2D','TextureCube'):continue
        t=d.get_asset();limit=512 if cls=='TextureCube' else 2048
        changed=t.get_editor_property('max_texture_size')!=limit or (cls=='Texture2D' and t.get_editor_property('never_stream'))
        if changed:
            t.set_editor_property('max_texture_size',limit)
            if cls=='Texture2D':t.set_editor_property('never_stream',False)
            save(t)
        prepared.append(p)
        if len(prepared)%3==0:
            t=None
            unreal.SystemLibrary.collect_garbage()
        if len(prepared)%10==0:(WORK/'TextureBudget_Progress.json').write_text(json.dumps({'prepared':len(prepared),'last':p}),encoding='utf8')
    return prepared


def preserve_street(old,street):
    snapshot=SOURCE/'BaseStreet.json'
    if snapshot.exists():
        rows=json.loads(snapshot.read_text(encoding='utf8'))
        for row in rows:
            for t in row['transforms']:street.item(row['mesh'],transform(t),row['materials'],row['collision'],row['hidden'],55000)
        return [{'mesh':r['mesh'],'instances':len(r['transforms'])} for r in rows]
    records=[]
    rows=[]
    for c in old.get_components_by_class(unreal.StaticMeshComponent):
        mesh=c.static_mesh
        if not mesh or c.get_name().startswith('Repaired_'):continue
        mats=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
        collision=str(c.get_collision_profile_name()) not in ('NoCollision','OverlapAll')
        hidden=c.get_editor_property('hidden_in_game')
        ts=[c.get_instance_transform(i,True) for i in range(c.get_instance_count())] if isinstance(c,unreal.InstancedStaticMeshComponent) else [c.get_world_transform()]
        for t in ts:
            street.item(mesh.get_path_name(),t,mats,collision,hidden,55000)
        if ts:
            records.append({'mesh':mesh.get_path_name(),'instances':len(ts)})
            values=[]
            for t in ts:
                rot=t.rotation.rotator();values.append({'location':vec(t.translation),'rotation':[rot.pitch,rot.yaw,rot.roll],'scale':vec(t.scale3d)})
            rows.append({'mesh':mesh.get_path_name(),'materials':mats,'collision':collision,'hidden':hidden,'transforms':values})
    assert sum(r['instances'] for r in records)>70
    SOURCE.mkdir(parents=True,exist_ok=True);snapshot.write_text(json.dumps(rows,indent=2),encoding='utf8')
    return records


def prune_tree_screen(scene,buildings):
    changed=[]
    for actor in scene:
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.static_mesh or '/SM_Fir_' not in c.static_mesh.get_path_name():continue
            remove=[]
            for i in range(c.get_instance_count()):
                p=c.get_instance_transform(i,True).translation+OFFSET
                frontage=3800<p.x<7900 and 23500<p.y<30800
                inside=any(b['bounds'][0][0]-150<p.x<b['bounds'][1][0]+150 and b['bounds'][0][1]-150<p.y<b['bounds'][1][1]+150 for b in buildings)
                if frontage or inside:remove.append(i)
            if not remove:continue
            actor.modify();c.modify();before=c.get_instance_count()
            for i in reversed(remove):assert c.remove_instance(i)
            changed.append({'actor':actor.get_actor_label(),'component':c.get_name(),'before':before,'after':c.get_instance_count(),'removed':len(remove)})
    return changed


def install():
    assert not unreal.EditorLevelLibrary.get_game_world(),'End PIE before installing'
    selection=json.loads((SOURCE/'Selection.json').read_text(encoding='utf8'))
    source=json.loads((WORK/'West_SourceInventory.json').read_text(encoding='utf8'))
    assert source['complete']
    main_hash=hashlib.sha256(MAIN.read_bytes()).hexdigest()
    backup=PROJECT/'Saved/Backups/DowntownWest'/datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
    shutil.copy2(PROJECT/'Content/Surface/Lvl_CampusConnected.umap',backup/'Lvl_CampusConnected.umap')
    world=LEVELS.load_map(CITY);assert world
    scene=ACTORS.get_all_level_actors();old=next(a for a in scene if a.get_actor_label()=='CITY_FirstDowntownBlock')
    required=set()
    for building in selection['buildings']:
        for index in building['actors']:
            for c in source['actors'][index]['components']:
                required.add(c['mesh'].split('.')[0]);required.update(p.split('.')[0] for p in c['materials'] if p)
    for prop in selection.get('props',[]):required.add(prop['mesh'].split('.')[0])
    budget_file=WORK/'TextureBudget.json'
    cached=json.loads(budget_file.read_text(encoding='utf8')) if budget_file.exists() and budget_file.stat().st_mtime>=(SOURCE/'Selection.json').stat().st_mtime else {}
    textures=cached['textures'] if cached.get('complete') else dependency_budget(required)
    A.make_directory(ROOT)
    if A.does_asset_exist(BPNAME):
        bp=load(BPNAME);shutil.copy2(PROJECT/'Content/Environment/CityRealism/BP_DowntownWestStreet.uasset',backup/'BP_DowntownWestStreet.uasset')
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_DowntownWestStreet',ROOT,unreal.Blueprint,f)
    street=Street(bp);retained=preserve_street(old,street)
    building_counts=[]
    merged_manifest=WORK/'MergedBuildings.json'
    merged_data=json.loads(merged_manifest.read_text(encoding='utf8')) if merged_manifest.exists() else {}
    # Reject merges made without render-ready source materials. Keep the exact
    # modular meshes and original material overrides if a merge used a fallback.
    merged_by_name={r['name']:r for r in merged_data.get('buildings',[]) if all('WorldGridMaterial' not in m and 'DefaultMaterial' not in m for m in r.get('materials',[]))} if merged_data.get('complete') else {}
    for b in selection['buildings']:
        angle=math.radians(b['yaw']);cos,sin=math.cos(angle),math.sin(angle);scale=b.get('scale',1.)
        origin=b['source_origin'];dest=b['location'];count=0
        if b['name'] in merged_by_name:
            record=merged_by_name[b['name']];assert record['pivot']==origin
            street.item(record['mesh'],unreal.Transform(location=unreal.Vector(*dest)-OFFSET,rotation=unreal.Rotator(yaw=b['yaw']),scale=unreal.Vector(scale,scale,scale)),(),False,False,48000)
            count=record['actors']
        else:
            for index in b['actors']:
                for c in source['actors'][index]['components']:
                    for row in c['transforms']:
                        p=row['location'];x,y=(p[0]-origin[0])*scale,(p[1]-origin[1])*scale
                        target=[dest[0]+x*cos-y*sin,dest[1]+x*sin+y*cos,dest[2]+(p[2]-origin[2])*scale]
                        t=transform(row)
                        t.translation=unreal.Vector(*target)-OFFSET
                        rot=t.rotation.rotator();rot.yaw+=b['yaw'];t.rotation=rot.quaternion();t.scale3d=t.scale3d*scale
                        street.item(c['mesh'],t,c['materials'],False,False,48000);count+=1
        assert count>10,b['name']
        # Closed shells have one coarse collision envelope; entrances face the sidewalk.
        lo,hi=b['bounds'];center=[(lo[i]+hi[i])/2 for i in range(3)];size=[hi[i]-lo[i] for i in range(3)]
        street.box([center[0]-OFFSET.x,center[1]-OFFSET.y,center[2]-OFFSET.z],size,'/Game/Surface/Materials/M_RuinConcrete',True,True)
        building_counts.append({'name':b['name'],'instances':count,'bounds':b['bounds']})
    ignore=[a for a in scene if a.get_actor_label().startswith(('FLEET_','CITY_StreetLife','RECLAIM_'))]
    for prop in selection.get('props',[]):
        p=list(prop['location']);rotation=prop.get('rotation',[0,0,0]);scale=prop.get('scale',[1,1,1])
        if prop.get('grounded'):
            box=load(prop['mesh']).get_bounding_box();angle=math.radians(rotation[1]);ox=(box.min.x+box.max.x)*.5*scale[0];oy=(box.min.y+box.max.y)*.5*scale[1]
            p[2]=pavement_height(world,p[0],p[1],ignore)+prop.get('raise',.5)-box.min.z*scale[2]
            p[0]-=ox*math.cos(angle)-oy*math.sin(angle);p[1]-=ox*math.sin(angle)+oy*math.cos(angle)
        street.item(prop['mesh'],transform({'location':vec(unreal.Vector(*p)-OFFSET),'rotation':rotation,'scale':scale}),prop.get('materials',[]),prop.get('collision',False),False,prop.get('cull',16000))
    for crossing in selection.get('crossings',[]):
        x=crossing['x0']+crossing['stripe']/2
        while x<crossing['x1']:
            y=crossing['y'];z=pavement_height(world,x,y,ignore)+.8
            street.box([x-OFFSET.x,y-OFFSET.y,z-OFFSET.z],[crossing['stripe'],crossing['length'],1.],'/Game/Surface/Materials/M_LanePaint',False,False)
            x+=crossing['stripe']+crossing['gap']
    compile_bp(bp);save(bp)
    placement=ACTORS.spawn_actor_from_class(B.generated_class(bp),unreal.Vector());assert placement
    label,folder,tags=old.get_actor_label(),old.get_folder_path(),list(old.tags)
    assert ACTORS.destroy_actor(old)
    placement.set_actor_label(label);placement.set_folder_path(folder);placement.tags=tags
    pruned=prune_tree_screen([a for a in scene if a!=old],selection['buildings'])
    counts={c.get_name():c.get_instance_count() if isinstance(c,unreal.InstancedStaticMeshComponent) else 1 for c in placement.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh}
    assert LEVELS.save_map(world,CITY)
    assert LEVELS.load_map(CITY)
    actual=ACTORS.get_all_level_actors();placed=next(a for a in actual if a.get_actor_label()==label)
    assert {c.get_name():c.get_instance_count() if isinstance(c,unreal.InstancedStaticMeshComponent) else 1 for c in placed.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh}==counts
    for item in pruned:
        a=next(a for a in actual if a.get_actor_label()==item['actor']);c=next(c for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent) if c.get_name()==item['component']);assert c.get_instance_count()==item['after'],item
    assert hashlib.sha256(MAIN.read_bytes()).hexdigest()==main_hash,'Unrelated lab map changed'
    report={'saved':True,'backup':str(backup),'buildings':building_counts,'instances':street.count,'batches':len(street.groups)+len(street.mirrored),'hism_batches':len(street.groups),'mirrored_static_components':len(street.mirrored),'retained_street':retained,'textures_capped_2k':textures,'pruned_trees':pruned,'lab_map_unchanged':True,'pack':'Downtown West Modular Pack','source_version':'5.6','engine_version':unreal.SystemLibrary.get_engine_version()}
    (WORK/'Installed.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

if __name__=='__main__':install()
