"""Import and place the supplied attack drone on the connected city map."""
from datetime import datetime
import json
import shutil
import unreal

from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, V, actors, add, content, levels, local, save, saved, tools
from CityCombat_Common import asset, compile_bp
from Industrial_Common import M, xyz
from Place_CityMachines import load, mesh_component, root
from StrikeDrone_Logic import ROOT, STREAK_SPEED, animate, burst, flight, lifecycle, round_helpers, shots, state, tactics
from SurfacePolish_Materials import import_file

SOURCE=content.parent/'SourceAssets/CityMachines/StrikeDrone'
LABEL='CITY_StrikeDrone_'
TAGS=[unreal.Name(k) for k in ('CyborgHostile','CityMachine','StrikeDrone')]
LEGACY_CLASSES={'BP_Relay_C','BP_Wasp_C'}
PATROL_POINTS=('PointA','PointB','PointC','PointD')
FLIGHT_ROUTES=(
    # Fixed authored patrols along the streets. The sweeps below validate each candidate.
    (((5850,39850),(5850,43000),(5850,46100)),1220.,((260.,-980.,-50.),(-280.,1200.,260.),(300.,2660.,-30.),(-270.,390.,160.))),
    (((5850,68200),(5850,73400),(15500,68700)),1280.,((-275.,-1460.,100.),(265.,-200.,-80.),(-260.,1790.,260.),(285.,730.,-60.))),
    (((15500,90750),(15500,94700),(33400,90500)),1500.,((310.,-1290.,-90.),(-285.,300.,160.),(290.,2380.,0.),(-270.,1000.,310.))),
)


def native(name,cls,factory):
    path=ROOT+'/'+name
    return load(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT,cls,factory)


def material_node(material,cls,x,y,**props):
    node=M.create_material_expression(material,cls,x,y)
    for name,value in props.items():
        node.set_editor_property(name,value)
    return node


def materials():
    textures={}
    for suffix,srgb,compression in (
        ('Base',True,unreal.TextureCompressionSettings.TC_DEFAULT),
        ('Normal',False,unreal.TextureCompressionSettings.TC_NORMALMAP),
        ('Masks',False,unreal.TextureCompressionSettings.TC_MASKS),
    ):
        t=import_file(SOURCE/f'T_Strike_{suffix}.png',ROOT)
        t.set_editor_property('srgb',srgb)
        t.set_editor_property('compression_settings',compression)
        t.set_editor_property('max_texture_size',1024)
        if suffix=='Normal':
            t.set_editor_property('flip_green_channel',True)
        save(t)
        textures[suffix]=t
    m=native('M_StrikeBody',unreal.Material,unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(m)
    color=material_node(m,unreal.MaterialExpressionTextureSample,-450,-180,texture=textures['Base'])
    normal=material_node(m,unreal.MaterialExpressionTextureSample,-450,10,texture=textures['Normal'],
                         sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    masks=material_node(m,unreal.MaterialExpressionTextureSample,-450,240,texture=textures['Masks'],
                        sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    for node,channel,prop in ((color,'RGB',unreal.MaterialProperty.MP_BASE_COLOR),
                             (normal,'RGB',unreal.MaterialProperty.MP_NORMAL),
                             (masks,'G',unreal.MaterialProperty.MP_ROUGHNESS),
                             (masks,'B',unreal.MaterialProperty.MP_METALLIC)):
        assert M.connect_material_property(node,channel,prop)
    M.recompile_material(m)
    save(m)
    result={'StrikeDrone':m}
    for key,tint in (
        ('SensorGlass',(3.1,.084,.019,1.)),('FlashCore',(35.,17.,7.,1.)),
        ('FlashEdge',(10.,2.05,.36,1.)),('Streak',(11.,5.6,1.55,1.)),
    ):
        m=native('M_'+key,unreal.Material,unreal.MaterialFactoryNew())
        M.delete_all_material_expressions(m)
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        m.set_editor_property('two_sided',key.startswith('Flash'))
        c=material_node(m,unreal.MaterialExpressionConstant3Vector,-240,0,constant=unreal.LinearColor(*tint))
        assert M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        M.recompile_material(m)
        save(m)
        result[key]=m
    return result


def meshes(spec,mats):
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    options=unreal.FbxImportUI()
    for name,value in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                           mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(name,value)
    data=options.static_mesh_import_data
    data.set_editor_property('auto_generate_collision',False)
    data.set_editor_property('generate_lightmap_u_vs',False)
    reduction=unreal.StaticMeshReductionOptions()
    reduction.set_editor_property('auto_compute_lod_screen_size',False)
    lods=[]
    for percent,screen in ((1.,1.),(.48,.25),(.18,.08)):
        lod=unreal.StaticMeshReductionSettings()
        lod.set_editor_property('percent_triangles',percent)
        lod.set_editor_property('screen_size',screen)
        lods.append(lod)
    reduction.set_editor_property('reduction_settings',lods)
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    result={}
    for key in spec:
        m=import_file(SOURCE/f'Strike_{key}.fbx',ROOT,options)
        for index,slot in enumerate(m.static_materials):
            m.set_material(index,mats[str(slot.material_slot_name)])
        if key!='Flash' and editor.get_lod_count(m)<3:
            assert editor.set_lods(m,reduction)==3,key
        save(m)
        result[key]=m
    return result


def attenuation(name,inner,falloff):
    obj=native(name,unreal.SoundAttenuation,unreal.SoundAttenuationFactory())
    cfg=obj.get_editor_property('attenuation')
    for key,value in (('attenuation_shape_extents',V((inner,0,0))),('falloff_distance',falloff),
                      ('spatialize',True),('attenuate',True),('enable_occlusion',True),
                      ('occlusion_low_pass_filter_frequency',1600.),('occlusion_volume_attenuation',.37)):
        cfg.set_editor_property(key,value)
    obj.set_editor_property('attenuation',cfg)
    save(obj)
    return obj


def audio():
    sound=import_file(SOURCE/'S_Strike_Rotors.wav',ROOT)
    sound.set_editor_property('looping',True)
    sound.set_editor_property('virtualization_mode',unreal.VirtualizationMode.PLAY_WHEN_SILENT)
    save(sound)
    attenuation('ATT_StrikeGun',380.,6800.)
    return sound,attenuation('ATT_StrikeRotor',290.,3800.)


def fx(name,mesh,scale,life,material=None):
    bp=asset(ROOT+'/BP_Strike'+name)
    c=add(bp,unreal.StaticMeshComponent,'Effect')
    c.set_static_mesh(mesh)
    c.set_collision_profile_name('NoCollision')
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_cast_shadow(False)
    c.set_editor_property('relative_scale3d',V(scale))
    if material:
        c.set_material(0,material)
    if name=='Flash':
        light=add(bp,unreal.PointLightComponent,'Light')
        light.set_mobility(unreal.ComponentMobility.MOVABLE)
        light.set_light_color(unreal.LinearColor(1.,.57,.24,1.))
        light.set_intensity(360.)
        light.set_attenuation_radius(238.)
        light.set_cast_shadows(False)
        light.set_editor_property('volumetric_scattering_intensity',.06)
    if name=='Streak':
        c.set_editor_property('relative_rotation',unreal.Rotator(pitch=90.))
        move=add(bp,unreal.ProjectileMovementComponent,'ForwardFlight')
        move.set_editor_property('velocity',V((1,0,0)))
        move.set_editor_property('initial_speed',STREAK_SPEED)
        move.set_editor_property('max_speed',STREAK_SPEED)
        move.set_editor_property('projectile_gravity_scale',0.)
        move.set_editor_property('initial_velocity_in_local_space',True)
    compile_bp(bp)
    cls=B.generated_class(bp)
    unreal.get_default_object(cls).set_editor_property('initial_life_span',life)
    save(bp)
    return cls.get_path_name()


def prepare():
    A.make_directory(ROOT)
    spec=json.loads((SOURCE/'Parts.json').read_text())
    mats=materials()
    models=meshes(spec,mats)
    rotor,rotor_attenuation=audio()
    flash=fx('Flash',models['Flash'],(1.,1.,1.),.041)
    spark=fx('Spark',models['Flash'],(.29,.41,.41),.087)
    streak=fx('Streak',load('/Engine/BasicShapes/Cylinder'),(.018,.018,2.35),.24,mats['Streak'])
    bp=asset(ROOT+'/BP_StrikeDrone')
    hull=root(bp)
    hull.set_capsule_size(119.,119.)
    hull.set_editor_property('generate_overlap_events',False)
    mesh_component(bp,'Chassis',models['Chassis'],(0,0,0),1.)
    for key in ('RotorL','RotorR','GunL','GunR'):
        part=add(bp,unreal.StaticMeshComponent,key,'Chassis')
        part.set_static_mesh(models[key])
        part.set_collision_profile_name('NoCollision')
        part.set_mobility(unreal.ComponentMobility.MOVABLE)
        part.set_editor_property('can_ever_affect_navigation',False)
        part.set_editor_property('relative_location',V(spec[key]['pivot']))
    for side in ('L','R'):
        socket=add(bp,unreal.SceneComponent,'Muzzle'+side,'Gun'+side)
        socket.set_mobility(unreal.ComponentMobility.MOVABLE)
        socket.set_editor_property('relative_location',V(spec['Gun'+side]['muzzle']))
    eye=add(bp,unreal.SceneComponent,'Sensor','Chassis')
    eye.set_mobility(unreal.ComponentMobility.MOVABLE)
    eye.set_editor_property('relative_location',V((54.,0.,0.)))
    player=add(bp,unreal.AudioComponent,'RotorAudio','Hull')
    player.set_sound(rotor)
    player.set_editor_property('attenuation_settings',rotor_attenuation)
    player.set_editor_property('auto_activate',True)
    player.set_volume_multiplier(.63)
    state(bp)
    tactics(bp)
    flight(bp)
    animate(bp,spec)
    round_helpers(bp,streak)
    shots(bp,flash,streak,spark)
    burst(bp)
    lifecycle(bp)
    cdo=unreal.get_default_object(B.generated_class(bp))
    for name,value in dict(CruiseSpeed=1220.,CombatSpeed=2060.,SensorRange=6300.,
                           FireRange=4750.,ShotDamage=3.6,HullHealth=315.,Flying=True,tags=TAGS).items():
        cdo.set_editor_property(name,value)
    save(bp)
    return bp


def find_route(world,options,altitude,route):
    for x,y in options:
        start=(x,y,GROUND+altitude)
        if route_is_clear(world,start,route):
            return start
    raise RuntimeError(f'No clear route at {options}')


def route_is_clear(world,start,route,ignored=()):
    x,y,z=start
    points=[start]+[(x+dx,y+dy,z+dz) for dx,dy,dz in route]
    points.append(points[1])
    return not any(unreal.SystemLibrary.sphere_trace_single(
        world,local(*a),local(*b),175.,unreal.TraceTypeQuery.ECC_VISIBILITY,False,
        list(ignored),unreal.DrawDebugTrace.NONE,False) for a,b in zip(points,points[1:]))


def replacement_route(world,drone,ignored):
    p=drone.get_actor_location()-local(0,0,0)
    original=tuple(xyz(drone.get_editor_property(name)) for name in PATROL_POINTS)
    street=5850. if p.x<10000. else 15500.
    compact=((-260.,-980.,80.),(275.,200.,-40.),(-245.,1640.,180.),(220.,690.,0.))
    for x,route in ((p.x,original),(street,original),(street,compact)):
        for lift in (0.,220.,440.,660.):
            start=(x,p.y,p.z+lift)
            if route_is_clear(world,start,route,ignored):
                return start,route
    raise RuntimeError('No clear replacement patrol for '+drone.get_actor_label())


def configure_patrol(drone,route):
    drone.modify()
    drone.set_editor_property('tags',TAGS+[unreal.Name('CityStrikePatrol')])
    for name,point in zip(PATROL_POINTS,route):
        drone.set_editor_property(name,V(point))


def spawn_patrol(cls,label,position,route,yaw):
    drone=actors.spawn_actor_from_class(cls,local(*position),unreal.Rotator(yaw=yaw))
    assert drone,label
    drone.set_actor_label(label)
    drone.set_folder_path('SURFACE/City Machines')
    configure_patrol(drone,route)
    return drone


def main():
    path=ROOT+'/BP_StrikeDrone'
    bp=load(path) if A.does_asset_exist(path) else prepare()
    cls=B.generated_class(bp)
    world=levels.load_map(LEVEL)
    assert world
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    legacy=sorted((a for a in scene.values() if a.get_class().get_name() in LEGACY_CLASSES),
                  key=lambda actor:actor.get_actor_label())
    planned=[(a,*replacement_route(world,a,legacy)) for a in legacy]
    backup=saved/'Backups/StrikeDrone'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    records={label:xyz(a.get_actor_location()-local(0,0,0)) for label,a in scene.items()
             if label.startswith(LABEL) and a.get_class()==cls}
    expected_routes={}
    for index,(candidates,altitude,route) in enumerate(FLIGHT_ROUTES,1):
        label=LABEL+f'{index:02d}'
        if label not in records:
            position=find_route(world,candidates,altitude,route)
            spawn_patrol(cls,label,position,route,90.)
            records[label]=position
            expected_routes[label]=route
    replaced={}
    number=max(int(label.removeprefix(LABEL)) for label in records)
    for old,position,route in planned:
        number+=1
        label=LABEL+f'{number:02d}'
        spawn_patrol(cls,label,position,route,old.get_actor_rotation().yaw)
        records[label]=position
        expected_routes[label]=route
        replaced[old.get_actor_label()]=label
    for old in legacy:
        assert actors.destroy_actor(old),old.get_actor_label()
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    restored={a.get_actor_label():a for a in actors.get_all_level_actors()}
    assert not any(a.get_class().get_name() in LEGACY_CLASSES for a in restored.values())
    for label in records:
        a=restored[label]
        assert a.get_class()==cls,label
        if label in expected_routes:
            for name,point in zip(PATROL_POINTS,expected_routes[label]):
                assert xyz(a.get_editor_property(name))==point,label
        assert 'cyborghostile' in {str(tag).lower() for tag in a.tags},(label,list(a.tags))
    (saved/'Drone002/Placement.json').write_text(json.dumps(dict(
        actors=records,replaced=replaced,backup=str(backup)),indent=2))


if __name__=='__main__':
    main()
