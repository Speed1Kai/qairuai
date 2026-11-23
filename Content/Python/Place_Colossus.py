"""Import the supplied assault mech and add one Colossus to the streamed city."""
from datetime import datetime
import json
import math
import shutil

import unreal

from Build_CityReclaim import material, M
from Build_RuinedUrbanCampus import A, B, GROUND, LEVEL, V, actors, add, content, levels, local, save, saved
from CityCombat_Common import FX, asset, compile_bp, link
from CityMachine_Logic import Logic, events, firing, motion, patrol, plan, variables, var
from Place_CityMachines import ROOT as MACHINES, ground, load, mesh_component, root
from SurfacePolish_Materials import import_file

ROOT=MACHINES+'/Colossus'
SOURCE=content.parent/'SourceAssets/CityMachines/Colossus'
LABEL='CITY_Machine_Colossus'
HALF=705.
LIFT=-(HALF+4.)
RADIUS=500.
ROUTE=((0.,-970.,0.),(0.,-1480.,0.),(0.,1220.,0.),(0.,1530.,0.))
SITES=((5850,88200),(5850,92750),(15500,88000),(33400,85500))
TAGS=[unreal.Name(s) for s in ('CyborgHostile','CityMachine','Colossus')]


def armor():
    field='''
float2 p=float2(P.x+P.y*.31,P.z+P.y*.63);
float blotch=n.sample(p/34.0), grain=n.sample(p/2.6);
float streak=n.sample(p*float2(.074,.018));
float oxide=smoothstep(.64,.87,blotch*.62+streak*.38);
float chipping=smoothstep(.73,.94,n.sample(p/8.0)*.75+grain*.25);
float3 clean=Tint*(.67+blotch*.55+grain*.12);
return lerp(lerp(clean,float3(.17,.185,.18),chipping*.65),float3(.106,.046,.024),oxide*.74);
'''
    mats={}
    for k,tint,metal,rough in (
        ('Charcoal',(.065,.071,.075),.49,.66),('Gunmetal',(.125,.15,.16),.62,.54),
        ('Steel',(.255,.29,.295),.76,.43),('IronRed',(.30,.071,.041),.43,.62),
        ('Ochre',(.33,.226,.062),.30,.68),
    ):
        m=material('Colossus'+k,tint,metal,rough,field=field)
        world=next(n for n in unreal.ObjectIterator(unreal.MaterialExpressionWorldPosition) if n.get_outer()==m)
        code=next(n for n in unreal.ObjectIterator(unreal.MaterialExpressionCustom) if n.get_outer()==m)
        transform=next((n for n in unreal.ObjectIterator(unreal.MaterialExpressionTransformPosition) if n.get_outer()==m),None)
        if not transform:
            transform=M.create_material_expression(m,unreal.MaterialExpressionTransformPosition,-340,-185)
            transform.set_editor_property('transform_source_type',unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
            transform.set_editor_property('transform_type',unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
            assert M.connect_material_expressions(world,'',transform,M.get_material_expression_input_names(transform)[0])
            assert M.connect_material_expressions(transform,'',code,'P')
            M.recompile_material(m)
            save(m)
        mats[k]=m
    mats['Optic']=material('ColossusOptic',(5.2,.045,.011),emission=True)
    return mats


def models(spec):
    A.make_directory(ROOT)
    ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(ed.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    opt=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,
                            mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        opt.set_editor_property(key,value)
    opt.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    opt.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
    mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    reduction=unreal.EditorScriptingMeshReductionOptions()
    reduction.set_editor_property('auto_compute_lod_screen_size',False)
    lods=[]
    for fraction,screen in ((1.,1.),(.45,.28),(.14,.09)):
        lod=unreal.EditorScriptingMeshReductionSettings()
        lod.set_editor_property('percent_triangles',fraction)
        lod.set_editor_property('screen_size',screen)
        lods.append(lod)
    reduction.set_editor_property('reduction_settings',lods)
    mats=armor()
    result={}
    for name in spec:
        mesh=import_file(SOURCE/(name+'.fbx'),root=ROOT,options=opt)
        for i,slot in enumerate(mesh.static_materials):
            mesh.set_material(i,mats[str(slot.material_slot_name)])
        if mesh_editor.get_lod_count(mesh)<3:
            assert mesh_editor.set_lods(mesh,reduction)==3,name
        save(mesh)
        unreal.log(f'COLOSSUS mesh {name} {mesh.get_bounds()}')
        result[name]=mesh
    return result


def joint_position(spec,key):
    x,y,z=spec['Colossus_'+key]['pivot']
    return (x,-y,z+LIFT)


def transform(g,key,x,y,z,pitch=0.,roll=0.):
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocationAndRotation',
                target=g.get(key),NewLocation=g.vector(x,y,z),bSweep=False,bTeleport=False,
                NewRotation=g.math('MakeRotator',Roll=roll,Pitch=pitch,Yaw=0.)))


def gait(bp,spec):
    g=Logic(bp,'AnimateMachine')
    bearing=g.select(g.get('LastPoint'),g.get('Goal'),g.get('HasSight'))
    direction=g.flatten(g.subv(bearing,g.position()))
    turn=g.branch(g.num('Greater',g.math('VSize',A=direction),38.))
    facing=g.math('MakeRotFromX',X=direction)
    current=g.out(g.call('Engine.Actor.K2_GetActorRotation'))
    rotation=g.math('RInterpTo',Current=current,Target=facing,DeltaTime=g.dt(),InterpSpeed=1.65)
    g.do(g.call('Engine.Actor.K2_SetActorRotation',NewRotation=rotation,bTeleportPhysics=False))
    moving=g.num('Greater',g.distance(g.get('BeforeMove'),g.position()),.2)
    blend=g.math('FInterpTo',Current=g.get('StrideBlend'),Target=g.select(1.,0.,moving,'Float'),
                 DeltaTime=g.dt(),InterpSpeed=7.)
    update=g.set('StrideBlend',blend)
    link(turn.find_else_pin(),update.find_execute_pin())
    cycles=g.num('Divide',g.get('DistanceMoved'),455.)
    phase=g.num('Multiply',cycles,math.tau)
    stride=g.get('StrideBlend')
    sin=g.math('Sin',A=phase)
    dip=g.num('Multiply',g.math('Cos',A=g.num('Multiply',phase,2.)),g.num('Multiply',stride,4.))
    sway=g.num('Multiply',sin,g.num('Multiply',stride,1.7))
    transform(g,'Chassis',0.,0.,g.num('Add',LIFT,dip),0.,sway)

    # Two rigid links solve to a foot path that slides back only relative to the moving hull.
    for side,offset in (('L',0.),('R',.5)):
        hip,knee,ankle=[joint_position(spec,key+side) for key in ('Hip','Knee','Ankle')]
        loop=g.math('Fraction',A=g.num('Add',cycles,offset))
        planted=g.num('Less',loop,.5)
        stance=g.num('Subtract',1.,g.num('Multiply',loop,4.))
        half_swing=g.num('Multiply',g.num('Subtract',loop,.5),math.tau)
        swing=g.num('Multiply',-1.,g.math('Cos',A=half_swing))
        x_offset=g.num('Multiply',g.select(stance,swing,planted,'Float'),g.num('Multiply',112.,stride))
        rise=g.num('Multiply',g.math('Sin',A=half_swing),g.num('Multiply',57.,stride))
        z_offset=g.select(0.,rise,planted,'Float')
        ax=g.num('Add',ankle[0],x_offset)
        az=g.num('Add',ankle[2],z_offset)
        hz=g.num('Add',hip[2],dip)
        dx=g.num('Subtract',ax,hip[0])
        dz=g.num('Subtract',az,hz)
        upper=math.hypot(knee[0]-hip[0],knee[2]-hip[2])
        lower=math.hypot(ankle[0]-knee[0],ankle[2]-knee[2])
        dist=g.math('VSize',A=g.vector(dx,0.,dz))
        safe=g.math('FClamp',Value=dist,Min=25.,Max=upper+lower-.1)
        along=g.num('Divide',g.num('Add',upper*upper-lower*lower,g.num('Multiply',safe,safe)),
                    g.num('Multiply',safe,2.))
        out=g.math('Sqrt',A=g.math('FMax',A=0.,B=g.num('Subtract',upper*upper,g.num('Multiply',along,along))))
        ux=g.num('Divide',dx,dist)
        uz=g.num('Divide',dz,dist)
        kx=g.num('Add',hip[0],g.num('Subtract',g.num('Multiply',ux,along),g.num('Multiply',uz,out)))
        kz=g.num('Add',hz,g.num('Add',g.num('Multiply',uz,along),g.num('Multiply',ux,out)))
        up=g.math('DegAtan2',Y=g.num('Subtract',kx,hip[0]),X=g.num('Subtract',hz,kz))
        low=g.math('DegAtan2',Y=g.num('Subtract',ax,kx),X=g.num('Subtract',kz,az))
        rest_up=math.degrees(math.atan2(knee[0]-hip[0],hip[2]-knee[2]))
        rest_low=math.degrees(math.atan2(ankle[0]-knee[0],knee[2]-ankle[2]))
        transform(g,'Hip'+side,hip[0],hip[1],hz,g.num('Subtract',up,rest_up))
        transform(g,'Knee'+side,kx,knee[1],kz,g.num('Subtract',low,rest_low))
        transform(g,'Ankle'+side,ax,ankle[1],az)

    step=g.math('FFloor',A=g.num('Multiply',cycles,2.))
    g.branch(g.compare('Greater',step,g.get('LastStomp')))
    g.set('LastStomp',step)
    floor=g.subv(g.position(),g.vector(z=HALF))
    g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',
        Sound='/Game/LabTutorial/Industrial/S_BlastDoorThud',Location=floor,VolumeMultiplier=.72,
        PitchMultiplier=.68,AttenuationSettings=ROOT+'/SA_ColossusStep'))
    compile_bp(bp)


def stomp_attenuation():
    if A.does_asset_exist(ROOT+'/SA_ColossusStep'):
        return
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    factory=unreal.SoundAttenuationFactory()
    attenuation=tools.create_asset('SA_ColossusStep',ROOT,unreal.SoundAttenuation,factory)
    settings=attenuation.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents',V((320.,0.,0.)))
    settings.set_editor_property('falloff_distance',3800.)
    attenuation.set_editor_property('attenuation',settings)
    save(attenuation)


def prepare():
    spec=json.loads((SOURCE/'Parts.json').read_text(encoding='utf-8'))
    muzzles=spec.pop('muzzles')
    meshes=models(spec)
    stomp_attenuation()
    bp=asset(ROOT+'/BP_Colossus')
    hull=root(bp)
    hull.set_capsule_size(RADIUS,HALF)
    for name in spec:
        key=name.removeprefix('Colossus_')
        mesh_component(bp,key,meshes[name],joint_position(spec,key),1.)
    # The FBX import mirrors Y when mapping Blender's right-handed geometry to Unreal.
    sockets=(('Sensor',(200.,0.,1125.)),('Muzzle',muzzles[0]),('MuzzleRight',muzzles[1]))
    for key,(x,y,z) in sockets:
        c=add(bp,unreal.SceneComponent,key,'Chassis')
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_location',V((x,-y,z)))
    variables(bp)
    var(bp,'StrideBlend','real','0.0')
    var(bp,'LastStomp','int','0')
    compile_bp(bp)
    contact=B.generated_class(load(MACHINES+'/BP_RelayContact')).get_path_name()
    tracer=B.generated_class(load(FX+'/BP_EnemyTracer')).get_path_name()
    patrol(bp)
    plan(bp,contact,'Colossus')
    motion(bp,'Colossus',0,custom_gait=True)
    gait(bp,spec)
    firing(bp,'Colossus',tracer,FX+'/S_Plasma')
    events(bp,'Colossus')
    cdo=unreal.get_default_object(B.generated_class(bp))
    for key,value in dict(HullHeight=HALF+4.,CruiseSpeed=240.,CombatSpeed=385.,
                            SensorRange=6200.,FireRange=5100.,KeepRange=2150.,ShotDamage=37.,
                            FireCooldown=1.65,Windup=1.03,HullHealth=3650.).items():
        cdo.set_editor_property(key,value)
    cdo.set_editor_property('tags',TAGS)
    save(bp)
    return bp


def select_site(world):
    for x,y in SITES:
        base=ground(world,x,y)
        if any(abs(ground(world,x,y+dy)-base)>80 for _,dy,_ in ROUTE):
            continue
        if any(unreal.SystemLibrary.line_trace_single(world,
            local(x+dx,y-1700,base+z),local(x+dx,y+1740,base+z),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[],unreal.DrawDebugTrace.NONE,False)
            for dx in (-420,0,420) for z in (110,450,1040)):
            continue
        return x,y,base
    raise RuntimeError('No clear patrol lane found')


def main():
    bp=prepare()
    world=levels.load_map(LEVEL)
    assert world
    existing=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL),None)
    if existing:
        unreal.log('COLOSSUS already placed')
        return
    x,y,base=select_site(world)
    backup=saved/'Backups/Colossus'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    actor=actors.spawn_actor_from_class(B.generated_class(bp),local(x,y,base-LIFT),unreal.Rotator(yaw=-90.))
    assert actor
    actor.set_actor_label(LABEL)
    actor.set_folder_path('SURFACE/City Machines')
    actor.modify()
    actor.set_editor_property('tags',TAGS)
    for key,point in zip(('PointA','PointB','PointC','PointD'),ROUTE):
        actor.set_editor_property(key,V(point))
    bounds=actor.get_actor_bounds(False)
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    reloaded=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL)
    assert reloaded.get_editor_property('PointB').y==ROUTE[1][1]
    (saved/'Import122/Placement.json').write_text(json.dumps(dict(position=(x,y,base),
        bounds=[(v.x,v.y,v.z) for v in bounds],backup=str(backup)),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
