"""Build native firearm Blueprints for the existing Final Protocol character."""
import datetime
import json
import math
from pathlib import Path
import shutil

import unreal
from CityCombat_Common import A,B,G,M,Graph,V,add,asset,compile_bp,components,link,pin,save,val,var

PLAYER='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
ROOT='/Game/Combat/Firearms'
ATOMIC='/Game/Combat/AtomicWeapon'
MODES='/Game/Combat/CyborgModes'
SAVED=Path(unreal.Paths.project_saved_dir())
CONTENT=Path(unreal.Paths.project_content_dir())
SOURCE=CONTENT.parent/'SourceAssets/Firearms'
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
BONES='CC_Base_'
CAPACITY={'Hunter':30,'Breaker':1}
SOUNDS=('Hunter_Shot_1','Hunter_Shot_2','Hunter_Shot_3','Breaker_Shot','Weapon_Magazine',
        'Weapon_Reload','Weapon_Dry','Weapon_Casing')
MESHES=('Hunter_Carbine','Hunter_Magazine','Hunter_Casing','Breaker_Railgun','Breaker_Cell')


def load(path):
    result=A.load_asset(path)
    assert result,path
    return result


def content_asset(name,cls,factory):
    path=ROOT+'/'+name
    return load(path) if A.does_asset_exist(path) else TOOLS.create_asset(name,ROOT,cls,factory)


def do_import(name,extension,options=None):
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return load(path)
    task=unreal.AssetImportTask()
    for prop,value in dict(filename=str(SOURCE/(name+extension)),destination_path=ROOT,
                           destination_name=name,automated=True,save=False).items():
        task.set_editor_property(prop,value)
    if options:
        task.set_editor_property('options',options)
    TOOLS.import_asset_tasks([task])
    return load(path)


def material(name,rgb,metal,rough,glow=False):
    m=content_asset('M_'+name,unreal.Material,unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(m)
    c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-280,0)
    c.set_editor_property('constant',unreal.LinearColor(*rgb,1.))
    if glow:
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if glow else unreal.MaterialProperty.MP_BASE_COLOR)
    if not glow:
        for v,prop in ((metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)):
            n=M.create_material_expression(m,unreal.MaterialExpressionConstant,-280,200)
            n.set_editor_property('r',v)
            M.connect_material_property(n,'',prop)
    M.recompile_material(m)
    save(m)
    return m


def import_assets():
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    palette={
        'MachinedSteel':((.15,.17,.19),.80,.39), 'Graphite':((.046,.064,.078),.76,.48),
        'Polymer':((.040,.042,.036),.10,.67), 'Brass':((.43,.255,.062),.84,.36),
        'Copper':((.36,.121,.046),.79,.40), 'StatusBlue':((.07,1.4,2.9),0.,1.),
        'StatusAmber':((3.,.49,.049),0.,1.),
    }
    mats={n:material(n,*data,glow=n.startswith('Status')) for n,data in palette.items()}
    result={}
    for name in MESHES:
        options=unreal.FbxImportUI()
        for k,v in dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                        import_materials=False,import_textures=False).items():
            options.set_editor_property(k,v)
        options.static_mesh_import_data.set_editor_property('combine_meshes',True)
        options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        m=do_import('SM_'+name,'.fbx',options)
        for i,slot in enumerate(m.static_materials):
            n=str(slot.material_slot_name)
            key=next(k for k in mats if n.lower().startswith(k.lower()))
            m.set_material(i,mats[key])
        if name in ('Hunter_Carbine','Breaker_Railgun'):
            b=m.get_bounding_box()
            assert b.min.x<-25 and b.max.x>55 and b.max.z>15,(name,str(b))
        if name=='Hunter_Casing':
            subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            subsystem.remove_collisions(m)
            assert subsystem.add_simple_collisions(m,unreal.ScriptingCollisionShapeType.BOX)>=0
        save(m)
        result[name]=m
    for n in SOUNDS:
        save(do_import('S_'+n,'.wav'))
    attenuation=content_asset('ATT_Weapon',unreal.SoundAttenuation,unreal.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents',V(250,0,0))
    settings.set_editor_property('falloff_distance',4800.)
    attenuation.set_editor_property('attenuation',settings)
    save(attenuation)
    return result


def set_mesh(c,m):
    c.set_static_mesh(m)
    for i in range(c.get_num_materials()):
        c.set_material(i,None)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name('NoCollision')


def author_props(bp,meshes):
    cs={n:c for _,c,n in components(bp)}
    for suffix in ('FP','TP'):
        gun=cs['Atomic'+suffix+'Gun']
        set_mesh(gun,meshes['Hunter_Carbine'])
        gun.set_editor_property('relative_scale3d',V(1,1,1))
        gun.set_visibility(False)
        if suffix=='FP':
            gun.set_editor_property('relative_location',V(31.,17.,-12.))
            gun.set_editor_property('relative_rotation',unreal.Rotator())
        mag=add(bp,unreal.StaticMeshComponent,'Weapon'+suffix+'Magazine','Atomic'+suffix+'Gun')
        set_mesh(mag,meshes['Hunter_Magazine'])
        mag.set_editor_property('relative_location',V(17.5,0.,-12.7))
        mag.set_editor_property('only_owner_see',suffix=='FP')
        mag.set_cast_shadow(suffix=='TP')
        port=add(bp,unreal.SceneComponent,'Weapon'+suffix+'Port','Atomic'+suffix+'Gun')
        port.set_editor_property('relative_location',V(11.,5.,10.))
        muzzle=cs['Atomic'+suffix+'Muzzle']
        muzzle.set_editor_property('relative_location',V(59.,0.,8.9) if suffix=='TP' else V(90.,17.,-3.1))
    for n in ('FP_LaserWeapon','TP_LaserWeapon'):
        cs[n].set_visibility(False)
    fp_fill=add(bp,unreal.PointLightComponent,'WeaponViewFill','FirstPersonCamera')
    fp_fill.set_mobility(unreal.ComponentMobility.MOVABLE)
    fp_fill.set_lighting_channels(False,True,False)
    fp_fill.set_editor_property('relative_location',V(9.,-26.,27.))
    fp_fill.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
    fp_fill.set_intensity(92.)
    fp_fill.set_attenuation_radius(155.)
    fp_fill.set_light_color(unreal.LinearColor(.65,.79,.96,1.))
    fp_fill.set_cast_shadows(False)
    fp_fill.set_visibility(False)
    for n in ('AtomicFPGun','AtomicFPArms','WeaponFPMagazine'):
        next(c for _,c,key in components(bp) if key==n).set_lighting_channels(True,True,False)
    casing=asset(ROOT+'/BP_HunterCasing')
    c=add(casing,unreal.StaticMeshComponent,'Brass')
    set_mesh(c,meshes['Hunter_Casing'])
    c.set_collision_profile_name('PhysicsActor')
    c.set_collision_enabled(unreal.CollisionEnabled.PHYSICS_ONLY)
    ignore=next(getattr(unreal.CollisionResponseType,n) for n in dir(unreal.CollisionResponseType) if n.lower().endswith('ignore'))
    c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,ignore)
    c.set_editor_property('generate_overlap_events',False)
    c.set_notify_rigid_body_collision(True)
    c.set_cast_shadow(False)
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    records=components(casing)
    h=next(h for h,_,n in records if n=='Brass')
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    if not lib.is_root_component(lib.get_data(h)):
        assert subsystem.make_new_scene_root(records[0][0],h,casing)
    c.set_simulate_physics(True)
    compile_bp(casing)
    var(casing,'bCasingSoundPlayed','bool','false')
    compile_bp(casing)
    g=GunGraph(casing)
    event=g.override('ReceiveHit')
    event.find_then_pin().break_pin_links()
    g.branch(g.no(g.get('bCasingSoundPlayed')))
    g.set('bCasingSoundPlayed',True)
    g.shot_sound(ROOT+'/S_Weapon_Casing',g.loc('Brass'),.32,g.math('RandomFloatInRange',Min=.91,Max=1.14))
    compile_bp(casing)
    unreal.get_default_object(B.generated_class(casing)).set_editor_property('initial_life_span',1.35)
    save(casing)
    flash=asset(ROOT+'/BP_HunterFlash')
    light=add(flash,unreal.PointLightComponent,'MuzzleLight')
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_light_color(unreal.LinearColor(1.,.52,.21,1.))
    light.set_intensity(540.)
    light.set_attenuation_radius(225.)
    light.set_cast_shadows(False)
    compile_bp(flash)
    unreal.get_default_object(B.generated_class(flash)).set_editor_property('initial_life_span',.045)
    save(flash)
    return casing,flash


class GunGraph(Graph):
    def __init__(self,bp,name=None,keep=False):
        if keep:
            super().__init__(bp)
            self.e=G.get_graph_editor_by_name(bp,name)
        else:
            super().__init__(bp,name)

    def call(self,path,target=None,**kwargs):
        if not path.startswith('/Game/'):
            return super().call(path,target=target,**kwargs)
        n=self.node(self.e.add_call_function_node(path))
        if target is not None:
            val(n.find_self_pin(),target)
        for k,v in kwargs.items():
            val(pin(n,k),v)
        return n

    def pick(self,kind,a,b,condition):
        return self.math('Select'+kind,A=a,B=b,bPickA=condition)

    def plus(self,a,b):return self.math('Add_DoubleDouble',A=a,B=b)
    def minus(self,a,b):return self.math('Subtract_DoubleDouble',A=a,B=b)
    def mul(self,a,b):return self.math('Multiply_DoubleDouble',A=a,B=b)
    def div(self,a,b):return self.math('Divide_DoubleDouble',A=a,B=b)
    def limit(self,v,lo=0.,hi=1.):return self.math('FClamp',Value=v,Min=lo,Max=hi)
    def eq(self,a,b):return self.math('EqualEqual_IntInt',A=a,B=b)
    def gt(self,a,b):return self.math('Greater_DoubleDouble',A=a,B=b)
    def yes(self,a,b):return self.math('BooleanAND',A=a,B=b)
    def no(self,v):return self.math('Not_PreBool',A=v)
    def mode(self,i):return self.eq(self.get('CyborgMode'),i)
    def vec(self,x,y,z):return self.math('MakeVector',X=x,Y=y,Z=z)
    def rot(self,p=0.,y=0.,r=0.):return self.math('MakeRotator',Pitch=p,Yaw=y,Roll=r)
    def va(self,a,b):return self.math('Add_VectorVector',A=a,B=b)
    def vs(self,a,b):return self.math('Subtract_VectorVector',A=a,B=b)
    def vm(self,a,b):return self.math('Multiply_VectorFloat',A=a,B=b)
    def loc(self,n):return self.out(self.call('Engine.SceneComponent.K2_GetComponentLocation',target=self.get(n)))
    def view(self):return self.out(self.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0))

    def visibility(self,n,v):
        return self.do(self.call('Engine.SceneComponent.SetVisibility',target=self.get(n),bNewVisibility=v,bPropagateToChildren=True))

    def relative(self,n,location=None,rotation=None):
        if location is not None:
            self.do(self.call('Engine.SceneComponent.K2_SetRelativeLocation',target=self.get(n),
                              NewLocation=location,bSweep=False,bTeleport=False))
        if rotation is not None:
            self.do(self.call('Engine.SceneComponent.K2_SetRelativeRotation',target=self.get(n),
                              NewRotation=rotation,bSweep=False,bTeleport=False))

    def shot_sound(self,sound,loc,volume=.78,pitch=1.):
        return self.do(self.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=sound,Location=loc,
                                 VolumeMultiplier=volume,PitchMultiplier=pitch,AttenuationSettings=ROOT+'/ATT_Weapon'))

    def gate(self):
        self.branch(self.no(self.get('bModeMenuOpen')))
        self.branch(self.no(self.get('bAdminFlight')))
        self.branch(self.no(self.out(self.call('Engine.Controller.IsMoveInputIgnored',target=self.pc()))))
        self.branch(self.gt(self.get('VisorIntegrity'),0.))

    def insert_before(self,node):
        incoming=list(node.find_execute_pin().list_connected_pins())
        assert len(incoming)==1,node.get_name()
        node.find_execute_pin().break_pin_links()
        self.cursor=incoming[0]

    def restore(self,node):
        link(self.cursor,node.find_execute_pin())


def patch_before(bp,graph,tag,operation,match):
    g=GunGraph(bp,graph,keep=True)
    if any(n.get_name()==tag for n in g.e.list_all_nodes()):
        return
    nodes=[n for n in g.e.list_all_nodes() if match(n)]
    assert len(nodes)==1,(graph,[(n.get_name(),str(n.get_node_title())) for n in nodes])
    node=nodes[0]
    g.insert_before(node)
    operation(g).rename(tag)
    g.restore(node)
    compile_bp(bp)


def add_members(bp):
    members={
        'HunterMagazine':('int',30),'HunterReserve':('int',150),
        'BreakerMagazine':('int',1),'BreakerReserve':('int',5),
        'WeaponEquippedMode':('int',0),'WeaponReloadMode':('int',0),
        'WeaponReloadTime':('real',0),'WeaponReloadEnd':('real',0),
        'WeaponAimAlpha':('real',0),'WeaponKick':('real',0),
        'WeaponNextDry':('real',0),'WeaponDryClicks':('int',0),'WeaponReloads':('int',0),
        'WeaponHUDFrames':('int',0),'WeaponCoverStops':('int',0),
    }
    for n,(t,d) in members.items():
        var(bp,n,t,str(d))
    for n in ('WeaponMuzzle','WeaponAimPoint','WeaponRayDirection'):
        var(bp,n,B.get_struct_type(unreal.Vector.static_struct()),'(X=0,Y=0,Z=0)')
    compile_bp(bp)
    cd=unreal.get_default_object(B.generated_class(bp))
    cd.set_editor_property('LaserInterval',.105)
    cd.set_editor_property('LaserDamage',22.)


def reload_transfer(bp,key):

    g=GunGraph(bp,'Weapon_Seat'+key)
    miss=g.math('Subtract_IntInt',A=CAPACITY[key],B=g.get(key+'Magazine'))
    g.set('WeaponReloadAmount',g.math('Min',A=miss,B=g.get(key+'Reserve')))
    g.set(key+'Magazine',g.math('Add_IntInt',A=g.get(key+'Magazine'),B=g.get('WeaponReloadAmount')))
    g.set(key+'Reserve',g.math('Subtract_IntInt',A=g.get(key+'Reserve'),B=g.get('WeaponReloadAmount')))
    compile_bp(bp)


def author_reload_pose():
    path=ROOT+'/AS_Sentinel_MagazineSwap'
    idle=load(ATOMIC+'/Animations/Atomic_FPGrip')
    clip=load(path) if A.does_asset_exist(path) else A.duplicate_asset(idle.get_path_name(),path)
    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(idle,0.,unreal.AnimPoseEvaluationOptions())

    def bone(n,world=False):
        space=unreal.AnimPoseSpaces.WORLD if world else unreal.AnimPoseSpaces.LOCAL
        return unreal.AnimPoseExtensions.get_bone_pose(pose,BONES+n,space)

    def unit(v):return v/v.length()

    def product(a,b):
        return unreal.Quat(x=a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,
            y=a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
            z=a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,
            w=a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z)

    def inverse(q):return unreal.Quat(x=-q.x,y=-q.y,z=-q.z,w=q.w)

    def rotate_between(a,b):
        a,b=unit(a),unit(b)
        cross,w=a.cross(b),1.+a.dot(b)
        length=math.sqrt(cross.dot(cross)+w*w)
        return unreal.Quat(x=cross.x/length,y=cross.y/length,z=cross.z/length,w=w/length)

    def ease(t):
        t=max(0.,min(1.,t))
        return t*t*(3.-2.*t)

    names=('L_Upperarm','L_Forearm','L_Hand')
    shoulder,elbow,hand=[bone(n,True) for n in names]
    parent=bone('L_Clavicle',True)
    s,e,h=shoulder.translation,elbow.translation,hand.translation
    upper,lower=(e-s).length(),(h-e).length()
    tracks=[[],[],[]]
    for i in range(55):
        t=i/54.
        reach=ease(t/.21)*(1.-ease((t-.72)/.25))
        pull=math.sin(math.pi*max(0.,min(1.,(t-.20)/.52)))
        desired=h+(V(-15.5,24.5,148.)-h)*reach+V(-4.,0.,-16.)*pull
        if reach<.0001 and pull<.0001:
            rotations=[bone(n).rotation for n in names]
        else:
            direction=unit(desired-s)
            d=min((desired-s).length(),upper+lower-.07)
            pole=(e-s)-direction*(e-s).dot(direction)
            x=(upper*upper-lower*lower+d*d)/(2*d)
            new_e=s+direction*x+unit(pole)*math.sqrt(max(.01,upper*upper-x*x))
            q1=product(rotate_between(e-s,new_e-s),shoulder.rotation)
            q2=product(rotate_between(h-e,s+direction*d-new_e),elbow.rotation)
            rotations=[product(inverse(parent.rotation),q1),product(inverse(q1),q2),
                       product(inverse(q2),hand.rotation)]
        for track,q in zip(tracks,rotations):
            track.append(q)
    ctrl=clip.controller
    ctrl.open_bracket('Author support-hand reload',False)
    try:
        ctrl.set_frame_rate(unreal.FrameRate(numerator=30,denominator=1),False)
        ctrl.set_number_of_frames(unreal.FrameNumber(54),False)
        for name,track in zip(names,tracks):
            t=bone(name)
            assert ctrl.set_bone_track_keys(BONES+name,[t.translation]*55,track,[t.scale3d]*55,False),name
    finally:
        ctrl.close_bracket(False)
    save(clip)
    return clip


def play_grip(g,clip=ATOMIC+'/Animations/Atomic_FPGrip',loop=True):
    return g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get('AtomicFPArms'),
                       NewAnimToPlay=clip,bLooping=loop))


def reload_graphs(bp):
    clip=author_reload_pose()
    var(bp,'WeaponReloadAmount','int','0')
    compile_bp(bp)
    for k in CAPACITY:
        reload_transfer(bp,k)
    g=GunGraph(bp,'Weapon_Reload')
    g.gate()
    g.branch(g.no(g.mode(0)))
    g.branch(g.eq(g.get('WeaponReloadMode'),0))
    breaker=g.mode(2)
    loaded=g.pick('Int',g.get('BreakerMagazine'),g.get('HunterMagazine'),breaker)
    reserve=g.pick('Int',g.get('BreakerReserve'),g.get('HunterReserve'),breaker)
    cap=g.pick('Int',1,30,breaker)
    g.branch(g.math('Less_IntInt',A=loaded,B=cap))
    g.branch(g.math('Greater_IntInt',A=reserve,B=0))
    g.set('bLaserHeld',False)
    g.set('WeaponReloadMode',g.get('CyborgMode'))
    g.set('WeaponReloadTime',g.now())
    g.set('WeaponReloadEnd',g.plus(g.get('WeaponReloadTime'),g.pick('Float',2.30,1.78,breaker)))
    play_grip(g,clip.get_path_name(),False)
    g.do(g.call('Engine.SkeletalMeshComponent.SetPlayRate',target=g.get('AtomicFPArms'),
                Rate=g.pick('Float',.783,1.011,breaker)))
    g.shot_sound(ROOT+'/S_Weapon_Reload',g.loc('FirstPersonCamera'),.75,g.pick('Float',.83,1.,breaker))
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_ReloadTick')
    g.branch(g.no(g.eq(g.get('WeaponReloadMode'),0)))
    valid=g.yes(g.eq(g.get('WeaponReloadMode'),g.get('CyborgMode')),
                g.yes(g.no(g.get('bModeMenuOpen')),g.gt(g.get('VisorIntegrity'),0.)))
    active=g.branch(valid)
    g.cursor=active.find_else_pin()
    g.set('WeaponReloadMode',0)
    play_grip(g)
    g.cursor=active.find_then_pin()
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('WeaponReloadEnd')))
    heavy=g.branch(g.eq(g.get('WeaponReloadMode'),2))
    g.do(g.own('Weapon_SeatBreaker'))
    path=g.cursor
    g.cursor=heavy.find_else_pin()
    g.do(g.own('Weapon_SeatHunter'))
    merge=g.set('WeaponReloadMode',0)
    link(path,merge.find_execute_pin())
    play_grip(g)
    g.count('WeaponReloads')
    g.shot_sound(ROOT+'/S_Weapon_Magazine',g.loc('FirstPersonCamera'),.40)
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_DryClick')
    g.gate()
    g.branch(g.no(g.mode(0)))
    g.branch(g.eq(g.get('WeaponReloadMode'),0))
    loaded=g.pick('Int',g.get('BreakerMagazine'),g.get('HunterMagazine'),g.mode(2))
    g.branch(g.eq(loaded,0))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('WeaponNextDry')))
    g.set('WeaponNextDry',g.plus(g.now(),.24))
    g.count('WeaponDryClicks')
    g.shot_sound(ROOT+'/S_Weapon_Dry',g.loc('FirstPersonCamera'),.78)
    compile_bp(bp)


def equip_graphs(bp,meshes):
    g=GunGraph(bp,'Atomic_Equip')
    heavy=g.mode(2)
    # Mesh and magazine are assigned only when changing protocol.
    br=g.branch(heavy)
    ends=[]
    for branch,keys in ((br.find_then_pin(),('Breaker_Railgun','Breaker_Cell')),
                        (br.find_else_pin(),('Hunter_Carbine','Hunter_Magazine'))):
        g.cursor=branch
        for view in ('FP','TP'):
            for comp,key in (('Atomic'+view+'Gun',keys[0]),('Weapon'+view+'Magazine',keys[1])):
                g.do(g.call('Engine.StaticMeshComponent.SetStaticMesh',target=g.get(comp),NewMesh=meshes[key].get_path_name()))
        ends.append(g.cursor)
    merge=g.set('WeaponEquippedMode',g.get('CyborgMode'))
    link(ends[0],merge.find_execute_pin())
    g.do(g.call('Engine.SkeletalMeshComponent.SetAnimInstanceClass',target=g.get('Mesh'),
                NewClass=B.generated_class(load(ATOMIC+'/ABP_AtomicBody')).get_path_name()))
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get('AtomicFPArms'),
                NewAnimToPlay=ATOMIC+'/Animations/Atomic_FPGrip',bLooping=True))
    g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get('AtomicTPGun'),Parent=g.get('Mesh'),
                SocketName=BONES+'R_Hand',LocationRule='KeepRelative',RotationRule='KeepRelative',
                ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
    seq=load(ATOMIC+'/Animations/Atomic_MF_Rifle_Idle_ADS')
    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,unreal.AnimPoseEvaluationOptions())
    hand=unreal.AnimPoseExtensions.get_bone_pose(pose,BONES+'R_Hand',unreal.AnimPoseSpaces.WORLD)
    offset=unreal.MathLibrary.inverse_transform_location(hand,V(-22.3,12.7,161.))
    rot=unreal.MathLibrary.inverse_transform_rotation(hand,unreal.Rotator(yaw=90.))
    g.relative('AtomicTPGun',str(offset.export_text()),g.rot(rot.pitch,rot.yaw,rot.roll))
    g.relative('AtomicFPMuzzle',g.vec(g.pick('Float',98.5,90.,heavy),17.,-3.1))
    g.relative('AtomicTPMuzzle',g.vec(g.pick('Float',67.5,59.,heavy),0.,8.9))
    g.set('bAtomicWasEquipped',True)
    compile_bp(bp)
    g=GunGraph(bp,'Modes_ApplyVisuals')
    for name in ('FP_LaserWeapon','TP_LaserWeapon'):
        g.visibility(name,False)
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_Sync')
    g.branch(g.no(g.eq(g.get('WeaponEquippedMode'),g.get('CyborgMode'))))
    g.set('WeaponReloadMode',0)
    active=g.branch(g.no(g.mode(0)))
    g.do(g.own('Atomic_Equip'))
    g.cursor=active.find_else_pin()
    g.do(g.own('Atomic_Unequip'))
    g.set('WeaponEquippedMode',0)
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_UpdateView')
    armed=g.no(g.mode(0))
    fp=g.get('bFirstPerson')
    first=g.yes(armed,fp)
    for name,flag in (('AtomicFPArms',first),('AtomicFPGun',first),('WeaponViewFill',first),
                      ('AtomicTPGun',g.yes(armed,g.no(fp)))):
        g.visibility(name,flag)
    changed=g.branch(g.math('NotEqual_BoolBool',A=first,B=g.get('bAtomicFPArmsHidden')))
    hide=g.branch(first)
    for side in ('L','R'):
        g.do(g.call('Engine.SkinnedMeshComponent.HideBoneByName',target=g.get('Mesh'),
                    BoneName=BONES+side+'_Upperarm',PhysBodyOption='PBO_None'))
    hidden=g.cursor
    g.cursor=hide.find_else_pin()
    for side in ('L','R'):
        g.do(g.call('Engine.SkinnedMeshComponent.UnHideBoneByName',target=g.get('Mesh'),
                    BoneName=BONES+side+'_Upperarm'))
    commit=g.set('bAtomicFPArmsHidden',first)
    link(hidden,commit.find_execute_pin())
    link(changed.find_else_pin(),commit.find_execute_pin())
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_ViewMotion')
    dt=g.dt()
    first=g.yes(g.get('bFirstPerson'),g.no(g.mode(0)))
    reload=g.no(g.eq(g.get('WeaponReloadMode'),0))
    aiming=g.out(g.call('Engine.PlayerController.IsInputKeyDown',target=g.pc(),Key='(KeyName="RightMouseButton")'))
    aiming=g.yes(aiming,g.yes(first,g.yes(g.no(reload),g.no(g.get('bModeMenuOpen')))))
    g.set('WeaponAimAlpha',g.math('FInterpTo',Current=g.get('WeaponAimAlpha'),
                                 Target=g.pick('Float',1.,0.,aiming),DeltaTime=dt,InterpSpeed=12.))
    aim=g.get('WeaponAimAlpha')
    # Recover smoothly after each shot and let repeated shots accumulate modestly.
    g.set('WeaponKick',g.math('FInterpTo',Current=g.get('WeaponKick'),Target=0.,DeltaTime=dt,
                             InterpSpeed=g.pick('Float',8.,16.,g.mode(2))))
    kick=g.get('WeaponKick')
    vel=g.out(g.call('Engine.Actor.GetVelocity'))
    planar=g.math('VSizeXY',A=vel)
    amount=g.limit(g.div(planar,700.))
    stride=g.math('Sin',A=g.mul(g.now(),10.3))
    sway=g.mul(g.mul(stride,amount),g.minus(1.3,g.mul(1.1,aim)))
    airborne=g.pick('Float',5.,0.,g.get('bAirJetActive'))
    age=g.minus(g.now(),g.get('WeaponReloadTime'))
    duration=g.math('FMax',A=g.minus(g.get('WeaponReloadEnd'),g.get('WeaponReloadTime')),B=.1)
    progress=g.limit(g.div(age,duration))
    lean=g.pick('Float',g.math('Sin',A=g.mul(progress,math.pi)),0.,reload)
    lowered=g.plus(airborne,g.mul(lean,10.))
    g.relative('AtomicFPRig',g.vec(g.minus(g.plus(7.8,g.mul(aim,3.8)),g.mul(kick,2.3)),
                                   g.plus(g.mul(aim,-17.),sway),
                                   g.minus(g.plus(g.minus(g.mul(aim,-2.4),4.3),g.mul(kick,.6)),lowered)),
               g.rot(g.minus(g.mul(kick,2.4),g.mul(lean,11.)),g.mul(sway,.36),g.mul(lean,13.)))
    pull=g.pick('Float',g.math('Sin',A=g.mul(g.limit(g.div(g.minus(progress,.20),.52)),math.pi)),0.,reload)
    mag=g.vec(17.5,g.mul(pull,4.),g.minus(-12.7,g.mul(pull,16.)))
    for n in ('WeaponFPMagazine','WeaponTPMagazine'):
        g.relative(n,mag,g.rot(g.mul(pull,10.)))
    # Hide the spent atomic cell until a new one is visibly inserted.
    show_cell=g.yes(g.mode(2),g.yes(g.eq(g.get('BreakerMagazine'),0),g.no(reload)))
    armed=g.no(g.mode(0))
    g.visibility('WeaponFPMagazine',g.yes(first,g.no(show_cell)))
    g.visibility('WeaponTPMagazine',g.yes(g.yes(armed,g.no(g.get('bFirstPerson'))),g.no(show_cell)))
    g.do(g.call('Engine.CameraComponent.SetFieldOfView',target=g.get('FirstPersonCamera'),
                InFieldOfView=g.minus(90.,g.mul(22.,aim))))
    compile_bp(bp)

    g=GunGraph(bp,'Atomic_Update')
    for fn in ('Weapon_Sync','Weapon_ReloadTick','Weapon_UpdateView','Weapon_ViewMotion'):
        g.do(g.own(fn))
    compile_bp(bp)


def hunter_graph(bp,casing,flash):
    g=GunGraph(bp,'Laser_Fire')
    g.branch(g.mode(1))
    g.gate()
    g.branch(g.eq(g.get('WeaponReloadMode'),0))
    g.branch(g.math('Greater_IntInt',A=g.get('HunterMagazine'),B=0))
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('LaserNextFire')))
    g.set('LaserNextFire',g.plus(g.now(),g.get('LaserInterval')))
    g.set('HunterMagazine',g.math('Subtract_IntInt',A=g.get('HunterMagazine'),B=1))
    g.count('LaserShots')
    camera=g.view()
    eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=camera))
    rotation=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=camera))
    forward=g.math('GetForwardVector',InRot=rotation)
    speed=g.math('VSizeXY',A=g.out(g.call('Engine.Actor.GetVelocity')))
    spread=g.plus(g.minus(.72,g.mul(g.get('WeaponAimAlpha'),.53)),g.mul(g.limit(g.div(speed,900.)),.62))
    g.set('WeaponRayDirection',g.math('RandomUnitVectorInConeInDegrees',ConeDir=forward,ConeHalfAngleInDegrees=spread))
    aim_end=g.va(eye,g.vm(g.get('WeaponRayDirection'),14500.))
    first=g.get('bFirstPerson')
    muzzle=g.pick('Vector',g.loc('AtomicFPMuzzle'),g.loc('AtomicTPMuzzle'),first)

    def trace(start,end):
        return g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=start,End=end,
                           TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
    def hit(t):
        return g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(t,'OutHit'))
    look=trace(eye,aim_end)
    h=hit(look)
    g.set('WeaponAimPoint',g.pick('Vector',g.out(h,'ImpactPoint'),aim_end,g.out(look)))
    near=trace(eye,muzzle)
    hn=hit(near)
    corrected=g.va(g.out(hn,'ImpactPoint'),g.vm(g.out(hn,'ImpactNormal'),2.))
    g.set('WeaponMuzzle',g.pick('Vector',corrected,muzzle,g.out(near)))
    g.set('WeaponCoverStops',g.math('Add_IntInt',A=g.get('WeaponCoverStops'),B=g.pick('Int',1,0,g.out(near))))
    origin=g.get('WeaponMuzzle')
    result=trace(origin,g.va(g.get('WeaponAimPoint'),g.vm(g.get('WeaponRayDirection'),7.)))
    h=hit(result)
    g.set('LaserLastPoint',g.pick('Vector',g.out(h,'ImpactPoint'),g.get('WeaponAimPoint'),g.out(result)))
    g.set('LaserLastHit',g.out(h,'HitActor'))

    g.set('WeaponKick',g.limit(g.plus(g.get('WeaponKick'),.56),0.,1.20))
    g.do(g.call('Engine.Pawn.AddControllerPitchInput',Val=g.minus(-.30,g.mul(g.get('WeaponAimAlpha'),-.12))))
    pitch=g.math('RandomFloatInRange',Min=.96,Max=1.045)
    shot1=g.eq(g.math('Percent_IntInt',A=g.get('LaserShots'),B=3),1)
    shot2=g.eq(g.math('Percent_IntInt',A=g.get('LaserShots'),B=3),2)
    # One sound plays per shot; the branching avoids stacked transients.
    br=g.branch(shot1)
    g.shot_sound(ROOT+'/S_Hunter_Shot_1',origin,.83,pitch)
    one=g.cursor
    g.cursor=br.find_else_pin()
    br=g.branch(shot2)
    g.shot_sound(ROOT+'/S_Hunter_Shot_2',origin,.83,pitch)
    two=g.cursor
    g.cursor=br.find_else_pin()
    g.shot_sound(ROOT+'/S_Hunter_Shot_3',origin,.83,pitch)
    merge=g.set('WeaponKick',g.get('WeaponKick'))
    for path in (one,two):
        link(path,merge.find_execute_pin())
    g.spawn(B.generated_class(flash).get_path_name(),origin,owner=g.self())
    port=g.pick('Vector',g.loc('WeaponFPPort'),g.loc('WeaponTPPort'),first)
    brass=g.spawn(B.generated_class(casing).get_path_name(),port,g.rot(20.,42.,24.),g.self())
    mesh=g.out(g.call('Engine.Actor.GetComponentByClass',target=brass,
                      ComponentClass='/Script/Engine.StaticMeshComponent'))
    side=g.math('GetRightVector',InRot=rotation)
    g.do(g.call('Engine.PrimitiveComponent.AddImpulse',target=mesh,Impulse=g.va(g.vm(side,200.),g.vec(0.,0.,145.)),bVelChange=True))

    delta=g.vs(g.get('LaserLastPoint'),origin)
    mid=g.vm(g.va(origin,g.get('LaserLastPoint')),.5)
    beam=load(MODES+'/BP_HunterLaserBeam')
    ray=g.spawn(B.generated_class(beam).get_path_name(),mid,g.math('MakeRotFromZ',Z=delta),g.self())
    length=g.math('VSize',A=delta)
    g.do(g.call('Engine.Actor.SetActorScale3D',target=ray,NewScale3D=g.vec(.013,.013,g.div(length,100.))))
    g.branch(g.valid(g.get('LaserLastHit')))
    g.count('LaserHits')
    g.do(g.call('Engine.GameplayStatics.ApplyPointDamage',DamagedActor=g.get('LaserLastHit'),BaseDamage=g.get('LaserDamage'),
                HitFromDirection=g.get('WeaponRayDirection'),HitInfo=g.out(result,'OutHit'),EventInstigator=g.pc(),DamageCauser=g.self()))
    spark=load(MODES+'/BP_HunterLaserImpact')
    g.spawn(B.generated_class(spark).get_path_name(),g.va(g.get('LaserLastPoint'),g.vm(g.out(h,'ImpactNormal'),1.2)),
            owner=g.self())
    compile_bp(bp)


def integrate_controls(bp):
    # Keep the existing primary input and heavy projectile implementation.
    g=GunGraph(bp,'Modes_StartFire')
    g.gate()
    g.count('ModeTriggerPulls')
    g.do(g.own('Weapon_DryClick'))
    hunter=g.branch(g.mode(1))
    g.set('bLaserHeld',True)
    g.do(g.own('Laser_Fire'))
    g.cursor=hunter.find_else_pin()
    g.set('bLaserHeld',False)
    g.branch(g.mode(2))
    g.do(g.own('Protocol_Fire'))
    compile_bp(bp)

    g=GunGraph(bp,'EventGraph',keep=True)
    if not any(n.get_name()=='WeaponReloadKey' for n in g.e.list_all_nodes()):
        menu=next(n for n in g.e.list_available_nodes([]) if str(n).endswith('|KeyboardEvents|R'))
        key=g.e.create_node_from_name(menu,unreal.Vector2D(x=0,y=16500),[])
        key.rename('WeaponReloadKey')
        key.set_editor_property('bConsumeInput',True)
        input_key=unreal.Key()
        input_key.set_editor_property('key_name','R')
        key.set_editor_property('input_key',input_key)
        g.cursor=pin(key,'Pressed',True)
        g.do(g.own('Weapon_Reload'))
    compile_bp(bp)

    g=GunGraph(bp,'Protocol_Fire',keep=True)
    if not any(n.get_name()=='WeaponConsumeBreaker' for n in g.e.list_all_nodes()):
        set_next=next(n for n in g.e.list_all_nodes() if n.get_class().get_name()=='K2Node_VariableSet'
                      and n.find_input_pin('ProtocolNextFire').is_valid())
        g.insert_before(set_next)
        g.branch(g.eq(g.get('WeaponReloadMode'),0))
        g.branch(g.math('Greater_IntInt',A=g.get('BreakerMagazine'),B=0))
        g.set('BreakerMagazine',g.math('Subtract_IntInt',A=g.get('BreakerMagazine'),B=1)).rename('WeaponConsumeBreaker')
        g.set('WeaponKick',1.85)
        g.restore(set_next)
    sound=next(n for n in g.e.list_all_nodes() if n.find_input_pin('Sound').is_valid()
               and n.find_input_pin('AttenuationSettings').is_valid())
    val(pin(sound,'Sound'),ROOT+'/S_Breaker_Shot')
    val(pin(sound,'VolumeMultiplier'),.94)
    val(pin(sound,'AttenuationSettings'),ROOT+'/ATT_Weapon')
    compile_bp(bp)


def hud_graph(bp):
    g=GunGraph(bp,'Weapon_DrawHUD')
    g.branch(g.no(g.mode(0)))
    g.count('WeaponHUDFrames')
    heavy=g.mode(2)
    ammo=g.pick('Int',g.get('BreakerMagazine'),g.get('HunterMagazine'),heavy)
    reserve=g.pick('Int',g.get('BreakerReserve'),g.get('HunterReserve'),heavy)
    reloading=g.no(g.eq(g.get('WeaponReloadMode'),0))
    scale=g.limit(g.div(g.get('ModeScreenH'),900.),.72,1.45)
    width=g.mul(214.,scale)
    left=g.minus(g.get('ModeScreenW'),g.plus(width,g.mul(scale,26.)))
    top=g.minus(g.get('ModeScreenH'),g.mul(105.,scale))
    def box(x,y,w,h,c):
        g.do(g.call('Engine.HUD.DrawRect',target=g.get('ModeCanvasHUD'),RectColor=c,
                    ScreenX=x,ScreenY=y,ScreenW=w,ScreenH=h))
    def label(s,x,y,tint,size):
        g.do(g.call('Engine.HUD.DrawText',target=g.get('ModeCanvasHUD'),Text=s,TextColor=tint,
                    ScreenX=g.plus(left,g.mul(x,scale)),ScreenY=g.plus(top,g.mul(y,scale)),
                    Font='/Engine/EngineFonts/Roboto',Scale=g.mul(size,scale),bScalePosition=False))
    white='(R=.78,G=.91,B=.96,A=1)'
    gray='(R=.39,G=.55,B=.61,A=1)'
    aqua='(R=.14,G=.83,B=1,A=1)'
    orange='(R=1,G=.46,B=.16,A=1)'
    box(left,top,width,g.mul(73.,scale),'(R=.008,G=.020,B=.032,A=.56)')
    title=g.pick('String','BREAKER  /  ИМПУЛЬС','HUNTER  /  АВТО',heavy)
    label(title,10.,5.,gray,.62)
    mag_string=g.out(g.call('Engine.KismetStringLibrary.Conv_IntToString',InInt=ammo))
    reserve_string=g.out(g.call('Engine.KismetStringLibrary.Conv_IntToString',InInt=reserve))
    numbers=g.out(g.call('Engine.KismetStringLibrary.Concat_StrStr',A=mag_string,
                        B=g.out(g.call('Engine.KismetStringLibrary.Concat_StrStr',A='  /  ',B=reserve_string))))
    tint=g.pick('Color',orange,white,g.eq(ammo,0))
    label(numbers,9.,20.,tint,1.40)
    state=g.pick('String','ПАТРОНЫ / РЕЗЕРВ','R  ПЕРЕЗАРЯДИТЬ',g.no(g.eq(ammo,0)))
    state=g.pick('String','ПЕРЕЗАРЯДКА',state,reloading)
    label(state,10.,52.,gray,.56)
    elapsed=g.minus(g.now(),g.get('WeaponReloadTime'))
    duration=g.math('FMax',A=g.minus(g.get('WeaponReloadEnd'),g.get('WeaponReloadTime')),B=.1)
    p=g.pick('Float',g.limit(g.div(elapsed,duration)),1.,reloading)
    box(left,g.plus(top,g.mul(72.,scale)),g.mul(width,p),1.,aqua)
    compile_bp(bp)

    patch_before(bp,'Modes_DrawHUD','WeaponAmmoHUD',lambda g:g.do(g.own('Weapon_DrawHUD')),
                 lambda n:n.get_class().get_name()=='K2Node_VariableSet' and n.find_input_pin('ModeDetectedCount').is_valid())


def main():
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    backup=SAVED/'Backups/Firearms'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(CONTENT/(PLAYER.removeprefix('/Game/')+'.uasset'),backup)
    meshes=import_assets()
    bp=load(PLAYER)
    casing,flash=author_props(bp,meshes)
    add_members(bp)
    reload_graphs(bp)
    equip_graphs(bp,meshes)
    hunter_graph(bp,casing,flash)
    integrate_controls(bp)
    hud_graph(bp)
    compile_bp(bp)
    save(bp)
    (SAVED/'firearms_author.json').write_text(json.dumps(dict(saved=True,backup=str(backup),
        capacity=CAPACITY,models=list(meshes),audio=len(SOUNDS),player=PLAYER),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
