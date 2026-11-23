"""Install the river continuation, scanned ground surfaces and grounded debris."""
from datetime import datetime
import json
import math
import random
import shutil

import unreal

from Build_CityReclaim import ROOT as RECLAIM, ROADS
from Build_LabSiege import ASSETS as SIEGE_ASSETS
from Build_RiverForest import ROOT as RIVER
from Build_RuinedUrbanCampus import (
    A, B, GROUND, LEVEL, OFFSET, V, actors, add, compile_bp, components, content,
    levels, local, save, saved,
)
from RiverContinuation_Geometry import MIN_X, MAX_X, bed_height, channel, city_edge, city_height, generate, south_height
from SurfacePolish_Materials import ROOT, ground_material, import_file, prepare, sets

MAPS={
    'RECLAIM_City':RECLAIM+'/BP_ReclaimedCity',
    'RIVER_ForestBasin':RIVER+'/BP_RiverForest',
    'SURF_Environment':'/Game/Surface/BP_SurfaceEnvironment',
    'SIEGE_Battlefield':SIEGE_ASSETS+'/BP_LabSiege',
    'CITY_FirstDowntownBlock':'/Game/Environment/DowntownFirstBlock/BP_FirstCityBlock_Repaired',
}
ASPHALT=SIEGE_ASSETS+'/M_Siege_FracturedAsphalt'
BURNED=SIEGE_ASSETS+'/M_Siege_BurnedGround'
PAVEMENT=RIVER+'/M_CampusWeatheredPavement'


def asset(path):
    obj=A.load_asset(path)
    assert obj,path
    return obj


def prepare_assets():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    materials=prepare()
    directory=saved/'SurfacePolishSource'
    names=generate(directory)
    options=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False, import_materials=False,
                    import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(k,v)
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    map_material={'water':asset(RIVER+'/M_FlowingRiver'),'rock':materials['bank'],
                  'forest':materials['forest'],'paving':materials['concrete']}
    for name in names:
        mesh=import_file(directory/(name+'.obj'),options=options)
        material=materials['mixed'] if name=='SM_CityBasin_Reshaped' else map_material[str(mesh.static_materials[0].material_slot_name)]
        mesh.set_material(0,material)
        if name!='SM_RiverWater_Continued':
            body=mesh.get_editor_property('body_setup')
            body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(mesh)
    rocks=import_file(content.parent/'SourceAssets/SurfacePolish/SM_CoastRockScan.fbx',options=options)
    rocks.set_material(0,materials['coast'])
    save(rocks)
    (saved/'surface_polish_assets.json').write_text(json.dumps(dict(meshes=[*names,rocks.get_name()],
                        rock_bounds=str(rocks.get_bounding_box())),indent=2),encoding='utf-8')


def entries(bp):
    return {name:c for _,c,name in components(bp) if isinstance(c,unreal.StaticMeshComponent)}


def new_batch(bp, name, root, mesh_name, collision=False):
    c=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,name,root)
    c.clear_instances()
    c.set_static_mesh(asset(ROOT+'/'+mesh_name))
    c.set_mobility(unreal.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    c.set_editor_property('can_ever_affect_navigation',False)
    c.set_cull_distances(0,0)
    return c


def use_mesh(component, name):
    component.modify()
    component.set_static_mesh(asset(ROOT+'/'+name))
    component.set_editor_property('override_materials',[])


def install_river(bp):
    cs=entries(bp)
    use_mesh(cs['RiverCurrent'],'SM_RiverWater_Continued')
    use_mesh(cs['RiverGorge'],'SM_Riverbed_Continued')
    for name in ('ForestSlope_West','ForestSlope_East','ForestSlope_South'):
        cs[name].set_material(0,asset(ROOT+'/M_Scan_Forest'))
    if 'NearBankApron' in cs:
        cs['NearBankApron'].set_material(0,asset(ROOT+'/M_Scan_Bank'))
    for name,mesh in (('ContinuationSouth','SM_RiverSouthWings'),('ContinuationNorth','SM_RiverNorthBank')):
        c=new_batch(bp,name,'SiteRoot',mesh,True)
        c.add_instance(unreal.Transform(location=local(0,0,GROUND)),False)
    # The original landing apron had a straight edge over the natural bank.
    soil=cs['Box_soil_Solid']
    for i in range(soil.get_instance_count()-1,-1,-1):
        t=soil.get_instance_transform(i,False)
        if t.scale3d.x>200 or t.scale3d.x<=14:
            assert soil.remove_instance(i)
    return fit_rock_clusters(bp)


def fit_rock_clusters(bp):
    # Remove the old faceted ledge props along the channel. Keep the cliff
    # stones that are already grounded in the surrounding forest.
    cs=entries(bp)
    for name in ('CliffTalus','CliffBroken'):
        c=cs[name]
        for i in range(c.get_instance_count()-1,-1,-1):
            p=c.get_instance_transform(i,False).translation
            x,y=p.x+OFFSET[0],p.y+OFFSET[1]
            if p.z<0 and min(abs(y-bank) for bank in channel(x))<620:
                assert c.remove_instance(i)
    rng=random.Random(7329)
    rock=new_batch(bp,'RiverScannedRocks','SiteRoot','SM_CoastRockScan')
    b=rock.get_editor_property('static_mesh').get_bounding_box()
    width=max(b.max.x-b.min.x,b.max.y-b.min.y)
    center=(b.max+b.min)*.5
    assert width>120,str(b)
    spots=[x+rng.randrange(-410,410) for x in range(-99000,109000,1960) if abs(x-5850)>3300]
    for i,x in enumerate(spots):
        lo,hi=channel(x)
        side=i%2
        y=lo+rng.uniform(190,410) if not side else hi-rng.uniform(230,420)
        span=rng.uniform(580,1270) if MIN_X<x<MAX_X else rng.uniform(800,1780)
        s=span/width
        yaw=rng.uniform(-40,40)+side*180
        a=math.radians(yaw)
        dx=(center.x*math.cos(a)-center.y*math.sin(a))*s
        dy=(center.x*math.sin(a)+center.y*math.cos(a))*s
        height=(b.max.z-b.min.z)*s*.81
        z=GROUND+bed_height(x,y)-b.min.z*s*.81-height*.47
        rock.add_instance(unreal.Transform(location=local(x-dx,y-dy,z),
             rotation=unreal.Rotator(yaw=yaw),scale=V((s,s,s*.81))),False)
    rock.set_cull_distances(42000,78000)
    return rock.get_instance_count()


def install_city(bp):
    cs=entries(bp)
    use_mesh(cs['CityBasin'],'SM_CityBasin_Reshaped')
    cs['Box_reclaim_asphalt_Solid'].set_material(0,asset(ROOT+'/M_Scan_Asphalt'))
    ground=cs['HorizonFir']
    removed,moved=0,0
    for i in range(ground.get_instance_count()-1,-1,-1):
        t=ground.get_instance_transform(i,False)
        p=t.translation
        x,y=p.x+OFFSET[0],p.y+OFFSET[1]
        if y>=city_edge(x)+16:
            z=city_height(x,y)-24
        elif (x<MIN_X-60 or x>MAX_X+60) and y<channel(x)[0]-100:
            z=south_height(x,y)-24
        else:
            assert ground.remove_instance(i)
            removed+=1
            continue
        if abs(p.z-z)>4:
            t.translation=V((p.x,p.y,z))
            assert ground.update_instance_transform(i,t,False,False,True)
            moved+=1
    path=cs.get('WeatheredSidewalks') or new_batch(bp,'WeatheredSidewalks','SiteRoot','SM_WeatheredSidewalk')
    squares=cs['Box_concrete']
    crossings=[(x,y,w,d) for x,y,w,d in ROADS if w>d]
    for i in range(squares.get_instance_count()-1,-1,-1):
        t=squares.get_instance_transform(i,False)
        if abs(t.scale3d.x-3.35)>.015 or t.scale3d.y<10:
            continue
        p=t.translation
        x,y=p.x+OFFSET[0],p.y+OFFSET[1]
        road=min((r for r in ROADS if r[3]>r[2]),key=lambda r:abs(abs(r[0]-x)-(r[2]/2+170))+abs(r[1]-y)*.02)
        length=t.scale3d.y*100
        count=round(length/600)
        length/=count
        for j in range(count):
            yy=y+(j+.5-count*.5)*length
            if any(abs(x-a)<w*.5 and abs(yy-b)<d*.5+length*.42 for a,b,w,d in crossings):
                continue
            path.add_instance(unreal.Transform(location=local(x,yy,GROUND+1.2),
                rotation=unreal.Rotator(yaw=0 if x>road[0] else 180),
                scale=V((1.,length/600,1.))),False)
        assert squares.remove_instance(i)
    return dict(relocated_firs=moved,removed_from_channel=removed,sidewalk_segments=path.get_instance_count())


def install_surface(bp):
    cs=entries(bp)
    ground=cs['Boxes_M_Dust_Block']
    ground.set_material(0,asset(ROOT+'/M_Scan_Mixed'))
    cs['Boxes_M_Asphalt_Block'].set_material(0,asset(ROOT+'/M_Scan_Asphalt'))
    for i in range(ground.get_instance_count()):
        t=ground.get_instance_transform(i,False)
        p=t.translation
        if t.scale3d.x<700 or p.y+23500<30000:
            # Environment component positions are relative to (5850,23500).
            continue
        end=p.y+23500+t.scale3d.y*50
        start=p.y+23500-t.scale3d.y*50
        if start>=22740:
            continue
        assert 21300<start<21650,(start,end)
        t.translation=V((p.x,(end+22800)*.5-23500,p.z))
        t.scale3d=V((t.scale3d.x,(end-22800)/100,t.scale3d.z))
        assert ground.update_instance_transform(i,t,False,True,True)


def lower_debris(world, bp, siege):
    cs=entries(bp)
    suspended=cs['HangingConcrete']
    hanging=[suspended.get_instance_transform(i,False).translation for i in range(suspended.get_instance_count())]
    suspended.clear_instances()
    rods=cs['Box_rust']
    rods_removed=0
    for i in range(rods.get_instance_count()-1,-1,-1):
        t=rods.get_instance_transform(i,False)
        p=t.translation
        if abs(t.scale3d.y-.038)<.002 and any(abs(p.x-q.x)<59 and 24<p.y-q.y<96 and -120<p.z-q.z<-37 for q in hanging):
            assert rods.remove_instance(i)
            rods_removed+=1
    rubble=cs['CollapsedConcrete']
    b=rubble.get_editor_property('static_mesh').get_bounding_box()
    corners=[V((x,y,z)) for x in (b.min.x,b.max.x) for y in (b.min.y,b.max.y) for z in (b.min.z,b.max.z)]
    for i in range(rubble.get_instance_count()):
        t=rubble.get_instance_transform(i,False)
        p=t.translation
        position=unreal.MathLibrary.transform_location(siege.get_actor_transform(),p)
        floor=unreal.SystemLibrary.line_trace_single_by_profile(world,position+V((0,0,24)),position-V((0,0,520)),
              'Pawn',False,[siege],unreal.DrawDebugTrace.NONE,False)
        top=floor.to_tuple()[5].z if floor else 0.
        z=[unreal.MathLibrary.transform_location(t,c).z-p.z for c in corners]
        desired=p.z+top-position.z-min(z)-min(22,(max(z)-min(z))*.22)
        t.translation=V((p.x,p.y,min(p.z,desired)))
        assert rubble.update_instance_transform(i,t,False,False,True)
    return dict(airborne_slabs_removed=len(hanging),airborne_rods_removed=rods_removed,
                rubble_grounded=rubble.get_instance_count())


def refresh_instances(labels=None):
    world=levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    for label,path in MAPS.items():
        if labels is not None and label not in labels:
            continue
        original=scene[label]
        transform=original.get_actor_transform()
        folder,tags=original.get_folder_path(),list(original.tags)
        replacement=actors.spawn_actor_from_class(B.generated_class(asset(path)),transform.translation,
                                                  transform.rotation.rotator())
        assert replacement and actors.destroy_actor(original),label
        replacement.set_actor_label(label)
        replacement.set_folder_path(folder)
        replacement.set_editor_property('tags',tags)
        replacement.set_actor_scale3d(transform.scale3d)
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)


def verify_saved():
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    siege={c.get_name():c for c in scene['SIEGE_Battlefield'].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert not siege['HangingConcrete'].get_instance_count()
    river={c.get_name():c for c in scene['RIVER_ForestBasin'].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert river['RiverCurrent'].get_editor_property('static_mesh').get_name()=='SM_RiverWater_Continued'
    assert river['RiverGorge'].get_editor_property('static_mesh').get_name()=='SM_Riverbed_Continued'
    city={c.get_name():c for c in scene['RECLAIM_City'].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert city['WeatheredSidewalks'].get_instance_count()>100
    return dict(slabs_in_air=siege['HangingConcrete'].get_instance_count(),
                sidewalk_segments=city['WeatheredSidewalks'].get_instance_count(),
                river_rock_clusters=river['RiverScannedRocks'].get_instance_count())


def main():
    world=levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    backup=saved/'Backups/SurfacePolish'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for path in (*MAPS.values(),ASPHALT,BURNED,PAVEMENT,LEVEL):
        ext='.umap' if path==LEVEL else '.uasset'
        file=content/(path.removeprefix('/Game/')+ext)
        shutil.copy2(file,backup/file.name)
    bps={label:asset(path) for label,path in MAPS.items()}
    result=lower_debris(world,bps['SIEGE_Battlefield'],scene['SIEGE_Battlefield'])
    result.update(install_city(bps['RECLAIM_City']))
    result['river_rock_clusters']=install_river(bps['RIVER_ForestBasin'])
    install_surface(bps['SURF_Environment'])
    entries(bps['CITY_FirstDowntownBlock'])['Batch_287'].set_material(0,asset(ROOT+'/M_Scan_Asphalt'))
    materials=sets()
    for path,kind in ((ASPHALT,'asphalt'),(BURNED,'burned'),(PAVEMENT,'concrete')):
        ground_material(asset(path),kind,*materials)
    for bp in bps.values():
        compile_bp(bp)
        save(bp)
    refresh_instances()
    result.update(verify_saved())
    (saved/'surface_polish_applied.json').write_text(json.dumps(dict(backup=str(backup),**result),indent=2))
