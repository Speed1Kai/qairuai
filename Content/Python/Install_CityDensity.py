"""Install the surveyed blocks and planted public spaces into the connected city."""
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import json,math,random,shutil
from collections import Counter

import unreal
from Build_RuinedUrbanCampus import A,B,CUBE,GROUND,LEVEL,MAT,OFFSET,Site,actors,add,compile_bp,local,save,levels
from SurfacePolish_Materials import import_file
from Build_RiverForest import persist

PROJECT=Path(unreal.Paths.project_dir()).resolve()
ROOT='/Game/Environment/CityDensity'
OUT=PROJECT/'Saved/CityDensity20'
SOURCE=PROJECT/'SourceAssets/CityDensity'
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
MODEL_KEYS=('BrickCourt','Residential','Civic','SlabTower','Workshop','Shattered','RuinShell','Memorial')
RUINS={'Shattered','RuinShell'}
E='/Game/Environment/'
DW='/Game/Downtown_West/'
W='/Game/Surface/'
FIN=E+'CityReclaim/M_Reclaim_'
MT=DW+'Materials/Buildings_Shared/MI_Building_'
MATERIALS={
  'Concrete':E+'SurfacePolish/M_Scan_Concrete',
  'Brick':E+'CityFrontages/M_SalvagedBrick','Stone':MT+'SandstoneWhite_WS',
  'Plaster':MT+'Stucco','Frame':FIN+'Frame','Dark':W+'Materials/M_Charcoal',
  'Roof':E+'SurfacePolish/M_Scan_Asphalt','Pane':'/Game/CityDowntown/Materials/Windows/MI_windowsFakeInteriorNoCurtain3',
  'Blind':FIN+'StationPaper','Shop':'/Game/CityDowntown/Materials/Windows/MI_ShopWindowsFakeInterior3',
  'Iron':FIN+'InfillSteel','Rust':E+'Vehicles/M_Wreck_Oxide','Copper':FIN+'ColossusOchre',
  'Timber':FIN+'StationTimber','Stripe':FIN+'InfillPaint','Moss':FIN+'Moss',
}
SCENERY={
    'Planter':E+'CityInfill/SM_Infill_PlanterBench',
    'Pergola':E+'CityInfill/SM_Infill_CourtyardPergola',
    'Bench':DW+'Assets/props/prop_bench_wood/SM_bench_wood_a',
    'BenchB':DW+'Assets/props/prop_bench_wood/SM_bench_wood_b',
    'Railing':DW+'Assets/props/prop_park_railing/SM_prop_park_railing_rail_a',
    'Fir':W+'RiverForest/SM_Fir_A','FirB':W+'RiverForest/SM_Fir_B',
    'NarrowLeafA':DW+'Assets/foliage/tree_narrowleaf/SM_tree_narrowleaf_a',
    'NarrowLeafB':DW+'Assets/foliage/tree_narrowleaf/SM_tree_narrowleaf_b',
    'NarrowLeafC':DW+'Assets/foliage/tree_narrowleaf/SM_tree_narrowleaf_c',
    'Shrub':DW+'Assets/foliage/shrub_evergreen/SM_evergreen_plant_shrub_evergreen_a',
    'ShrubLow':DW+'Assets/foliage/bush/SM_bush_low',
    'Flowers':DW+'Assets/foliage/flowers/SM_flowers_flowers_b',
    'GrassA':'/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_A',
    'GrassC':'/Game/City/Vegetation/QuixelDryGrass/SM_DryGrass_C',
    'Ivy':E+'CityAftermath/SM_War_RootedIvy','Rubble':E+'CityAftermath/SM_War_RubblePile',
    'Slab':E+'CityAftermath/SM_War_RippedSlabA',
    'StainlessBin':'/Game/CityDowntown/Geometry/Props/SM_streetBin',
    'Lamp':E+'CityInfill/SM_Infill_StreetLight',
    'Pallet':E+'QuixelWarehouse/Meshes/SM_QW_Pallet',
    'Crate':E+'QuixelWarehouse/Meshes/SM_QW_WrappedCrate',
    'Van':E+'Vehicles/SM_FP_BurnedServiceVan',
    'Basins':E+'CityReclaim/SM_Reclaim_Basin',
}
TREES=('NarrowLeafA','NarrowLeafB','NarrowLeafC','Fir','FirB')
LARGE_PROPS={'Memorial','Pergola','Railing','Van'}
ZONES={}

def load(path):
    a=A.load_asset(path)
    assert a,path
    return a

def author_assets(src,world):
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    palette={name:load(path) for name,path in MATERIALS.items()}
    results={}
    ses=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for name in MODEL_KEYS:
        path=ROOT+'/SM_Density_'+name
        if A.does_asset_exist(path):
            m=load(path)
        else:
            opt=unreal.FbxImportUI()
            for prop,val in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                       mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
                opt.set_editor_property(prop,val)
            opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
            opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
            opt.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
            m=import_file(src/('SM_Density_'+name+'.fbx'),ROOT,opt)
            b=m.get_bounding_box();s=b.max-b.min
            assert s.x>600 and s.y>600 and s.z>700, (name,s)
            for i,mat in enumerate(m.static_materials):
                key=str(mat.get_editor_property('imported_material_slot_name'))
                m.set_material(i,palette[key])
            if name in RUINS:
                body=m.get_editor_property('body_setup')
                body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                body.set_editor_property('double_sided_geometry',True)
            elif name!='Memorial':
                ses.add_simple_collisions(m,unreal.ScriptingCollisionShapeType.BOX)
            if name not in RUINS and name!='Memorial':
                opts=unreal.EditorScriptingMeshReductionOptions()
                opts.set_editor_property('auto_compute_lod_screen_size',False)
                parts=[]
                for percent,size in ((1.,1.),(.43,.29),(.15,.116),(.052,.042)):
                    item=unreal.EditorScriptingMeshReductionSettings()
                    item.set_editor_property('percent_triangles',percent)
                    item.set_editor_property('screen_size',size)
                    parts.append(item)
                opts.set_editor_property('reduction_settings',parts)
                assert ses.set_lods(m,opts)>=3,name
            save(m)
        results[name]=m
    results.update({key:load(path) for key,path in SCENERY.items()})
    MAT.update({
        'DensityMasonry':palette['Stone'],'DensityPaving':palette['Concrete'],
        'DensityRoad':palette['Roof'],'DensitySoil':load(E+'SurfacePolish/M_Scan_Forest'),
        'DensityKerb':palette['Concrete'],'DensityMark':palette['Stripe'],
        'DensityDark':palette['Dark'],'DensityRust':palette['Rust'],'DensityWood':palette['Timber'],
        'DensityIvy':palette['Moss'],'DensityPillar':palette['Brick'],
    })
    return results

def zone(x,y):
    i=int((y-27000)//18300)
    return ('West' if x<7900 else 'East')+str(i+1)

def site_for(x,y):
    name=zone(x,y)
    if name not in ZONES:
        path=ROOT+'/BP_CityDensity_'+name
        assert not A.does_asset_exist(path),path
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_CityDensity_'+name,ROOT,unreal.Blueprint,factory)
        ZONES[name]=Site(bp)
    return ZONES[name]

def dimensions(mesh):
    return mesh.get_bounding_box().max-mesh.get_bounding_box().min

def fitting(site,key,mesh,x,y,z,w,d,h,yaw=0,collide=False):
    site.fitted(key,mesh,x,y,z,(w,d,h),yaw=yaw,collide=collide)
    cull=85000 if key in MODEL_KEYS[:-1] else 43000 if key in TREES else 29000 if key in LARGE_PROPS else 17400
    site.batches[key].set_cull_distances(0,cull)

def meshprop(site,key,models,x,y,z,scale,yaw=0,solid=False):
    mesh=models[key]
    size=dimensions(mesh)
    if isinstance(scale,(tuple,list)):
        height=size.z*scale[2]
        w,d=size.x*scale[0],size.y*scale[1]
    else:
        w,d,height=size.x*scale,size.y*scale,size.z*scale
    fitting(site,key,mesh,x,y,z,w,d,height,yaw,solid)

def layout_sign(site,name,title,x,y,z,yaw,size=38.):
    c=add(site.bp,unreal.TextRenderComponent,name,'SiteRoot')
    c.set_mobility(unreal.ComponentMobility.STATIC)
    c.set_text(unreal.Text(title.upper()))
    c.set_world_size(size)
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    c.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    c.set_text_render_color(unreal.Color(179,204,199,255))
    c.set_editor_property('relative_location',local(x,y,z))
    c.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw))
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

def add_park(site,models,p,ground,rng,index):
    x,y,w,d,kind=p['x'],p['y'],p['w'],p['d'],p['kind']
    h=ground(x,y)
    assert h is not None,(kind,x,y)
    deck=h+8
    site.box('DensityPaving',x,y,deck-4,w,d,8,collide=True)
    # Existing streets meet the park with shallow paving. Paths run between planted beds.
    for dx in (-1,1):
        for dy in (-1,1):
            bw=w*.5-545;bd=d*.5-495
            bx=x+dx*(w*.23+162);by=y+dy*(d*.21+145)
            if bw<555 or bd<470:continue
            site.box('DensitySoil',bx,by,deck+9,bw,bd,18)
            for t in (-1,1):
                site.box('DensityKerb',bx+t*bw*.5,by,deck+14,24,bd+12,30,collide=True)
                site.box('DensityKerb',bx,by+t*bd*.5,deck+14,bw+12,24,30,collide=True)
            for j in range(max(2,int(bw/480))):
                xx=bx+(.15+(j+.5)/max(2,int(bw/480))*.70-.50)*bw
                meshprop(site,TREES[(j+index+int(dx>0)+int(dy>0))%len(TREES)],models,
                         xx,by+rng.uniform(-bd*.28,bd*.28),deck+15,rng.uniform(.56,.92),rng.randrange(360))
            for k in range(18):
                xx,yy=bx+rng.uniform(-.44,.44)*bw,by+rng.uniform(-.43,.43)*bd
                item=('Shrub','ShrubLow','GrassA','GrassC','Flowers')[k%5]
                meshprop(site,item,models,xx,yy,deck+17,rng.uniform(.60,1.12),rng.randrange(360))
            meshprop(site,'Bench' if dx==dy else 'BenchB',models,
                     bx,by-dy*(bd*.5+105),deck,1.,0 if dy<0 else 180)
            meshprop(site,'Lamp',models,bx+dx*min(320,bw*.23),by-dy*(bd*.5+155),deck,.90,180)
            if dx==dy:meshprop(site,'StainlessBin',models,bx-170,by-dy*(bd*.5+128),deck,1.,0)
    if kind in ('North','Station'):
        mesh=models['Memorial']
        scl=.85 if kind=='Station' else 1.04
        meshprop(site,'Memorial',models,x,y,deck+.5,scl,25 if kind=='North' else 0)
        site.box('DensityMasonry',x,y,deck+7,760*scl,760*scl,14,collide=True)
    elif kind in ('Court','Market','Tram'):
        mesh=models['Basins']
        fitting(site,'Basins',mesh,x,y,deck,620 if kind=='Court' else 510,620 if kind=='Court' else 510,92,0,False)
    else:
        meshprop(site,'Pergola',models,x,y+95,deck,.52 if kind=='Gateway' else .63,0,False)
        meshprop(site,'Planter',models,x,y+280,deck,.87,0,False)
    # Entry plaques are readable by approaching pedestrians. Fence lengths leave both crossing axes open.
    path=p.get('path',[])
    sign_path=p.get('sign_path',path)
    ax,ay=(sign_path[1][0]-sign_path[0][0],sign_path[1][1]-sign_path[0][1]) if len(sign_path)>1 else (0,-400)
    along_x=abs(ax)>abs(ay)
    positive=(ax if along_x else ay)>0
    side=1 if positive else -1
    if along_x:
        sign_x,sign_y=x+side*(w*.5-125),y+410
        yaw=0 if positive else 180
    else:
        sign_x,sign_y=x+580,y+side*(d*.5-125)
        yaw=90 if positive else -90
    site.box('DensityMasonry',sign_x,sign_y,deck+43,55,345,87,collide=True,yaw=yaw)
    offset=68.
    layout_sign(site,'ParkTitle'+str(index),p['title'],sign_x+math.cos(math.radians(yaw))*offset,
               sign_y+math.sin(math.radians(yaw))*offset,deck+88.,yaw,22)
    for a,b in zip(path,path[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        px,py=(a[0]+b[0])*.5,(a[1]+b[1])*.5
        height=p.get('path_z')
        if height is None:
            gz=ground(px,py)
            if gz is None:continue
            height=gz+3
        width=p.get('path_width',360)
        site.box('DensityPaving',px,py,height,abs(dx)+width,abs(dy)+width,6,collide=True)
    return deck

def place_lots(data,world,models):
    rng=random.Random(7591)
    @lru_cache(maxsize=23000)
    def ground(x,y):
        line=unreal.SystemLibrary.line_trace_single(world,local(x,y,12200),local(x,y,1870),
            unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,False)
        if not line or not line.to_tuple()[0]:return None
        z=line.to_tuple()[5].z+OFFSET[2]
        return z if 2075<z<2410 else None
    selected=[]
    for lot in data['lots']:
        x,y,w,d,h,yaw,kind=[lot[k] for k in ('x','y','w','d','h','yaw','model')]
        a=math.radians(yaw)
        c,s=math.cos(a),math.sin(a)
        sample=[ground(x+c*dx-s*dy,y+s*dx+c*dy) for dx,dy in
            ((0,0),(-w*.44,-d*.43),(w*.44,-d*.43),(-w*.44,d*.43),(w*.44,d*.43),
             (-w*.42,0),(w*.42,0),(0,-d*.43),(0,d*.43))]
        if any(z is None for z in sample) or max(sample)-min(sample)>80:
            continue
        gz=sum(sample)/len(sample)
        site=site_for(x,y)
        base=min(gz+8,max(sample)+5)
        if not lot.get('apron_only'):
            fitting(site,kind,models[kind],x,y,base,w,d,h,yaw,True)
        front=d*.5-12
        xx,yy=x+s*front,y-c*front
        # Entrance apron, curb and meter box anchor the facade to the street.
        site.box('DensityPaving',xx+s*151,yy-c*151,base-2,w*.91,321,6,yaw=yaw)
        if lot.get('apron_only'):
            continue
        if kind in RUINS:
            for i in range(3):
                t=(i-1)*w*.239
                k=front+rng.uniform(-18,50)
                meshprop(site,'Rubble',models,x+c*t+s*k,y+s*t-c*k,base+.4,rng.uniform(.80,1.39),rng.randrange(360))
        if kind=='Workshop' and rng.random()<.64:
            for i,key in enumerate(('Pallet','Crate')):
                t=w*.37
                k=front+105+i*68
                meshprop(site,key,models,x+c*t+s*k,y+s*t-c*k,base+.4,.83,yaw)
        selected.append(dict(lot,actual_ground=round(base,2)))
    names=Counter()
    for x,y,w,d,yaw in data['alleys']:
        z=ground(x,y)
        if z is None:continue
        site=site_for(x,y)
        site.box('DensityRoad',x,y,z+2,w,d,4,yaw=yaw,collide=True)
        a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
        for side in (-1,1):
            j=side*(d*.5+85)
            xx,yy=x-s*j,y+c*j
            site.box('DensityPaving',xx,yy,z+3,w,166,6,yaw=yaw,collide=True)
        names['alleys']+=1
    parks=[]
    for i,p in enumerate(data['parks']):
        if ground(p['x'],p['y']) is None:continue
        site=site_for(p['x'],p['y'])
        height=add_park(site,models,p,ground,rng,i)
        parks.append(dict(p,height=height))
    for item in data['greens']:
        x,y=item['x'],item['y'];gz=ground(x,y)
        if gz is None:continue
        site=site_for(x,y)
        nature=item['kind']
        if nature in ('birch','fir'):
            meshprop(site,rng.choice(TREES[:3] if nature=='birch' else TREES[3:]),models,x,y,gz,rng.uniform(.60,.99),rng.randrange(360))
        for k in range(4 if nature=='grass' else 3):
            x1,y1=x+rng.uniform(-241,241),y+rng.uniform(-217,217)
            z=ground(round(x1),round(y1))
            if z is None or abs(z-gz)>45:continue
            key=('Shrub','Ivy','ShrubLow')[k] if nature=='hedge' else ('Rubble','Slab','GrassC')[k] if nature=='debris' else ('GrassA','GrassC','ShrubLow','Ivy')[k]
            meshprop(site,key,models,x1,y1,z+.8,rng.uniform(.76,1.4),rng.randrange(360))
        names['green_clusters']+=1
    assert len(selected)>270 and len(parks)>=7,(len(selected),len(parks))
    return selected,parks,names

def install(src):
    ZONES.clear()
    assert not levels.get_dirty_map_packages()
    world=editor.get_editor_world()
    assert world.get_path_name().split('.')[0]==LEVEL
    data=json.loads((src/'CityLayout.json').read_text(encoding='utf-8'))
    backup=PROJECT/'Saved/Backups/CityDensity20'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True,exist_ok=False)
    shutil.copy2(PROJECT/'Content/Surface/Lvl_CampusConnected.umap',backup/'Lvl_CampusConnected.umap')
    models=author_assets(src,world)
    lots,parks,names=place_lots(data,world,models)
    area_parts={}
    for name,site in ZONES.items():
        compile_bp(site.bp)
        save(site.bp)
        a=actors.spawn_actor_from_class(B.generated_class(site.bp),unreal.Vector())
        a.set_actor_label('CITY_Density_'+name)
        a.set_folder_path('CITY/Density20')
        cs=a.get_components_by_class(unreal.InstancedStaticMeshComponent)
        count=sum(c.get_instance_count() for c in cs)
        assert count>=20,(name,count)
        area_parts[name]=count
    assert len(area_parts)>=7
    OUT.mkdir(exist_ok=True)
    report=dict(lots=lots,parks=parks,features=dict(names),sectors=area_parts,
                footprint_m2=round(sum(l['w']*l['d'] for l in lots)/10000),
                built=dict(Counter(l['model'] for l in lots)),before_sample=data['sample_stats'],
                backup=str(backup))
    (OUT/'Build.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return report

if __name__=='__main__':
    install(SOURCE)
    assert levels.save_map(editor.get_editor_world(),LEVEL)

