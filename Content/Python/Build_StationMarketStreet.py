"""Build the Station 07 market street on the connected city map."""
from pathlib import Path
from datetime import datetime
import json,math,shutil,unreal
from Industrial_Common import A,B,add,compile_bp,save
from Build_RuinedUrbanCampus import Site,local,LEVEL,levels,actors,V,OFFSET

def install():
    root=Path(unreal.Paths.project_dir()).resolve()
    saved=root/'Saved/StationDistrict'
    saved.mkdir(exist_ok=True)
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    path='/Game/Environment/StationDistrict/BP_StationDistrict'
    assert not any(p.get_name()==path for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    world=levels.load_map(LEVEL);assert world and LEVEL=='/Game/Surface/Lvl_CampusConnected'
    backup=root/'Saved/Backups/StationDistrict'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    for asset,ext in ((LEVEL,'.umap'),(path,'.uasset')):
        src=root/'Content'/(asset[6:]+ext)
        if src.exists():shutil.copy2(src,backup/src.name)
    bp=A.load_asset(path) if A.does_asset_exist(path) else None
    if not bp:
        factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_StationDistrict',path.rsplit('/',1)[0],unreal.Blueprint,factory)
    site=Site(bp)
    inf='/Game/Environment/CityInfill/SM_Infill_';exp='/Game/Environment/CityExpansion/SM_District_'
    west='/Game/Downtown_West/Assets/';props=west+'props/'
    floor='/Game/Environment/SurfacePolish/M_Scan_'
    cache={}
    def get(path):
        if path not in cache:
            cache[path]=unreal.load_asset(path);assert cache[path],path
        return cache[path]
    def mesh(path,x,y,z,yaw=0,scale=1,solid=False):
        m=get(path);bb=m.get_bounding_box();c=(bb.max+bb.min)*.5
        sn=math.sin(math.radians(yaw));cs=math.cos(math.radians(yaw))
        site.mesh(m.get_name(),m,x-scale*(c.x*cs-c.y*sn),y-scale*(c.x*sn+c.y*cs),z-scale*bb.min.z,(scale,)*3,yaw=yaw,collide=solid)
    def slab(key,mat,x,y,top,sx,sy,thick,solid=False,yaw=0):
        site.mesh(key,get('/Engine/BasicShapes/Cube'),x,y,top-thick*.5,(sx/100,sy/100,thick/100),yaw=yaw,collide=solid)
        site.batches[key].set_material(0,get(mat))
    def paint(x,y,sx,sy,yaw=0,z=2156.3):
        slab('TrafficPaint','/Game/Surface/Materials/M_LanePaint',x,y,z,sx,sy,.3,False,yaw)
    def tile(key,path,x,y,top,w,d,h):
        m=get(path);bb=m.get_bounding_box()
        site.fitted(key,m,x,y,top-h,(w,d,h),collide=True)
    slab('MainCarriageway',floor+'Asphalt',33400,87000,2156,1328,6150,3)
    slab('RearServiceLane',floor+'Mixed',31180,86960,2152,350,5500,10,True)
    slab('DeliveryCourt',floor+'Concrete',32140,87935,2156,2080,420,13,True)
    slab('MarketCourt',floor+'Burned',31890,88840,2154,2530,1560,11,True)
    # Flush curb breaks lead through the loading cut and across to the station.
    paving=west+'ground_walkways/SM_ground_mod_walk_tile_a_4m'
    for x,width in [(32494,472),(34261,372)]:
        for i in range(15):
            y=84100+400*i;top=2163 if abs(y-86900)<280 or abs(y-87900)<290 else 2169
            tile('Paving',paving,x,y,top,width,399.5,top-2149)
    for y in range(84150,90000,500):
        if abs(y-86900)>280:paint(33400,y,10,195)
    for x in range(32830,34025,101):paint(x,86900,48,230)
    paint(33104,87120,540,14);paint(33740,86680,550,14)
    for y in (84800,86050,87600,89100):
        mesh(props+'prop_sewer_caps/SM_sewer_cap_c',33885,y,2156.6,11,.92)
    mesh(exp+'BrickWalkup',31690,84990,2153,-90,.88,True)
    mesh(inf+'ShopRow',31858,86470,2154,-90,1,True)
    mesh(inf+'ShopRow',31858,87570,2154,-90,.89,True)
    mesh(inf+'MarketHall',31685,89085,2154,-90,.97,True)
    mesh(inf+'ServiceGarage',34975,84865,2152,90,1,True)
    mesh(exp+'CivicResidence',35265,88970,2150,90,.78,True)
    mesh(inf+'TransitShelter',32565,85830,2170,-90,.82,True)
    mesh(inf+'CourtyardPergola',32264,89220,2156,-90,.78)
    for y in (87080,):
        mesh(props+'props_streetlight/SM_light_streetlight_complete',32688,y,2169,-90,.86)
    for x,y,angle in [(32632,86475,90),(32468,88740,90),(34266,88310,-90)]:
        mesh(props+'prop_bench_wood/SM_bench_wood_a',x,y,2169,angle,.96,True)
    for x,y in ((32583,86305),(34215,88105),(32540,88576)):
        mesh(props+'prop_recycle_bin/SM_prop_recycle_bin',x,y,2169,22,.94,True)
    mesh(props+'prop_poster_stands/SM_prop_poster_pillar_with_posters',32470,87080,2163,12,.86,True)
    mesh(props+'prop_fire_hydrant/SM_fire_hydrant',34170,86550,2169,33,.94)
    mesh(props+'prop_hotdog_cart/SM_food_cart',32332,88540,2169,-83,.94,True)
    mesh('/Game/Environment/Vehicles/SM_FP_BurnedServiceVan',30370,88730,2151,8,.94,True)
    mesh('/Game/Environment/Vehicles/SM_FP_AbandonedSedan',33910,85320,2156,92,.95,True)
    for i,(x,y) in enumerate(((32070,89310),(31290,88230),(34900,88080))):
        slab('PlantingSoil',floor+'Forest',x,y,2159,270,330,11,True)
        mesh(west+'ground/SM_ground_mod_garden_planter_tall_b',x,y,2157,90,.74)
    for y in (84875,89360):
        mesh(inf+'StreetLight',32672,y,2169,90,.95)
    # Repaired utility cuts are flush with the street. Preserve clear zebra markings.
    slab('RoadRepairs','/Game/Surface/Materials/M_Asphalt',33708,86240,2156.65,229,1040,.45)
    slab('RoadRepairs','/Game/Surface/Materials/M_Asphalt',33049,88361,2156.65,308,680,.45)
    for i in range(4):
        tile('BrickForecourt',west+'ground_walkways/SM_ground_mod_brick_walkway_a_curve',32358,88460+i*290,2161,172,283,7)
    def shop_sign(key,x,y,z,width,height):
        folder='/Game/Environment/StationDistrict/Signs'
        texture=folder+'/'+key;material=folder+'/M_'+key
        if not A.does_asset_exist(texture):
            task=unreal.AssetImportTask()
            for k,v in dict(filename=str(root/'SourceAssets/StationDistrict'/(key+'.png')),destination_path=folder,automated=True,save=True).items():task.set_editor_property(k,v)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not A.does_asset_exist(material):
            m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+key,folder,unreal.Material,unreal.MaterialFactoryNew())
            lib=unreal.MaterialEditingLibrary
            tex=lib.create_material_expression(m,unreal.MaterialExpressionTextureSample)
            tex.set_editor_property('texture',get(texture))
            lib.connect_material_property(tex,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
            lib.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
            lib.recompile_material(m);save(m)
        # A plane's U axis runs along local X. Rotate it up to face east.
        site.mesh('Sign'+key,get('/Engine/BasicShapes/Plane'),x,y,z,(width/100,height/100,1),yaw=-90,roll=90)
        site.batches['Sign'+key].set_material(0,get(material))
    shop_sign('Bakery',32210,86470,2456,420,96)
    shop_sign('Repairs',32177,87570,2421,369,84)
    shop_sign('Market',32190,89085,2500,562,118)
    # The freight gate runs west from the shops into the municipal water yard.
    utility=root/'SourceAssets/StationDistrict'
    from SurfacePolish_Materials import import_file
    ui=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():ui.set_editor_property(k,v)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    utility_root='/Game/Environment/StationDistrict'
    matroot='/Game/Environment/CityReclaim/M_Reclaim_'
    finishes={'Concrete':floor+'Concrete','Paint':matroot+'StationCladding','Rust':'/Game/Surface/Materials/M_Oxide',
              'Ivory':matroot+'StationPaper','Steel':matroot+'InfillSteel','Safety':matroot+'StationSafety','Wood':matroot+'StationTimber'}
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for name in ('SM_PumpCourt_Tower','SM_PumpCourt_Dock','SM_PumpCourt_Fence'):
        if A.does_asset_exist(utility_root+'/'+name):continue
        model=import_file(utility/(name+'.fbx'),utility_root,ui)
        for i,slot in enumerate(model.static_materials):
            model.set_material(i,get(finishes[str(slot.get_editor_property('imported_material_slot_name'))]))
        model.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(model)
    slab('PumpApron',floor+'Concrete',29330,89180,2151,1590,1650,11,True)
    slab('FreightApron',floor+'Mixed',30330,88920,2151,1480,2260,11,True)
    slab('PassageBelts',floor+'Asphalt',30530,88040,2154,2120,328,12,True)
    slab('PumpFootway',floor+'Concrete',29250,88065,2152,1030,235,9,True)
    mesh(utility_root+'/SM_PumpCourt_Tower',28840,89340,2151,0,1,True)
    # The hatch and maintenance ladder face the loading court.
    mesh(inf+'ServiceGarage',27895,89075,2146,-90,.88,True)
    mesh(utility_root+'/SM_PumpCourt_Dock',30175,89485,2151,0,1,True)
    mesh(exp+'CivicResidence',26540,88955,2148,90,.76,True)
    crate='/Game/Environment/QuixelWarehouse/Meshes/SM_QW_'
    for kind,x,y,z,angle in (
        ('Pallet',30020,89485,2234,2),('WrappedCrate',30020,89485,2247,2),('ToolCase',30258,89450,2234,-15),
        ('Crate',30354,89515,2234,3),('HandTruck',30580,89342,2152,-21),('DamagedPallet',30600,89140,2151,12),
        ('CableSpool',28210,88870,2150,14),('RustyDrum',28195,89020,2150,9),('MetalCabinet',28208,88725,2150,-90)):
        mesh(crate+kind,x,y,z,angle,1,kind not in ('ToolCase','DamagedPallet'))
    for i in range(5):
        slab('FreightHatch',matroot+'StationSafety',29740+i*179,89271,2152.5,17,84,1,False,-32)
    # Pipe trench, four bolted grilles, and a warm working light above the dock.
    for i in range(4):
        y=88450+i*141
        slab('DrainWell',matroot+'Frame',29855,y,2152.4,34,139,2)
        for j in range(9):
            slab('DrainBars',matroot+'InfillSteel',29855,y-58+j*14.5,2153.4,32,4,1.5)
    for x in (29870,30480):
        slab('DockLampCase',matroot+'Frame',x,89525,2524,95,15,10)
        slab('DockLampGlass',matroot+'StationWarm',x,89525,2518,80,11,4)
        light=add(bp,unreal.PointLightComponent,'LoadingLight'+str(x),'SiteRoot')
        light.set_editor_property('relative_location',local(x,89480,2490));light.set_light_color(unreal.LinearColor(1,.64,.31,1))
        light.set_intensity(580);light.set_attenuation_radius(405);light.set_cast_shadows(False)
    mesh('/Game/Environment/CityAftermath/SM_War_RootedIvy',28250,88660,2148,-90,.82)
    for x,y,angle in [(29332,89850,12),(29180,89845,-20),(28425,88560,45),(28710,88440,19)]:
        mesh('/Game/Environment/CityReclaim/SM_Reclaim_Shrub',x,y,2146,angle,.39)


    # Contain the working yard on the residential side; leave the freight throat open.
    for i in range(10):
        mesh(utility_root+'/SM_PumpCourt_Fence',28180+i*300,90200,2149,0,1,True)
    for i in range(6):
        mesh(utility_root+'/SM_PumpCourt_Fence',31030,90050-i*300,2149,90,1,True)
    mesh(props+'prop_sewer_caps/SM_sewer_cap_c',29520,88820,2152,17,.78)
    for y in (87901,88203):
        slab('GateBase',floor+'Concrete',30752,y,2185,59,59,39,True)
        slab('GateUpright',matroot+'InfillSteel',30752,y,2574,15,15,393,True)
    slab('GateLintel',matroot+'Frame',30752,88052,2573,20,352,83,True)
    shop_sign('Waterworks',30763,88052,2531,330,76)
    compile_bp(bp);save(bp)
    label='CITY_Station07_MarketStreet'
    matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==label];assert len(matches)<=1
    if not matches:
        placed=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector());placed.set_actor_label(label);placed.set_folder_path('SURFACE/Station 07')
    else:
        placed=matches[0]
    # UE can retain serialized per-instance transforms on a previously placed HISM.
    # Reconcile this generated actor while preserving its identity and references.
    expected={}
    for key,template in site.batches.items():
        transforms=[template.get_instance_transform(i,False) for i in range(template.get_instance_count())]
        expected[key]=transforms
    for component in placed.get_components_by_class(unreal.InstancedStaticMeshComponent):
        key=component.get_name()
        if key in expected:
            component.modify()
            component.clear_instances()
            component.add_instances(expected[key],False,False)
    placed.modify()
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0]==LEVEL
    world.modify();assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    aa=[a for a in actors.get_all_level_actors() if a.get_actor_label()==label];assert len(aa)==1
    batches=aa[0].get_components_by_class(unreal.InstancedStaticMeshComponent)
    for c in batches:
        if c.get_name() not in expected:continue
        transforms=expected[c.get_name()]
        assert c.get_instance_count()==len(transforms),c.get_name()
        for i,t in enumerate(transforms):
            assert (c.get_instance_transform(i,False).translation-t.translation).length()<.1,(c.get_name(),i)
    (saved/'District.json').write_text(json.dumps(dict(map=LEVEL,backup=str(backup),instances={c.get_name():c.get_instance_count() for c in batches},reloaded=True),indent=2))
if __name__=='__main__':install()

