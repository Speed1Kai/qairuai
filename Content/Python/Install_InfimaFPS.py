"""Connect the Infima first-person view model to Final Protocol's Hunter mode."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal
from Build_Firearms import GunGraph, PLAYER
from CityCombat_Common import A, V, add, compile_bp, link, pin, save, val, var

WORK = Path(unreal.Paths.project_saved_dir()).resolve() / 'InfimaImport'
SOURCE = '/Game/InfimaGames/FreeFPSTemplate'
ARMS = 'InfimaFPArms'
RIFLE = 'InfimaFPRifle'
MAGAZINE = 'InfimaFPMagazine'
PIVOT = 'InfimaFPPivot'
MUZZLE = 'InfimaFPMuzzle'
PORT = 'InfimaFPPort'
POSE = 'InfimaPose'


def load(path):
    result = A.load_asset(path)
    assert result, path
    return result


def component(bp, cls, name, parent):
    c = add(bp, cls, name, parent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    if isinstance(c, unreal.PrimitiveComponent):
        c.set_collision_profile_name('NoCollision')
        c.set_editor_property('only_owner_see', True)
        c.set_editor_property('cast_shadow', False)
        c.set_editor_property('visible', False)
    if isinstance(c, unreal.SkeletalMeshComponent):
        c.set_editor_property('visibility_based_anim_tick_option',
                              unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    return c


def add_view_model(bp, paths):
    component(bp, unreal.SceneComponent, PIVOT, 'FirstPersonCamera')
    arms = component(bp, unreal.SkeletalMeshComponent, ARMS, PIVOT)
    arms.set_skeletal_mesh_asset(load(paths['SK_FP_Manny_Simple']))
    arms.set_editor_property('relative_location', V(-.71, 0., -162.57))
    arms.set_editor_property('relative_rotation', unreal.Rotator(yaw=-90.))
    rifle = component(bp, unreal.SkeletalMeshComponent, RIFLE, ARMS)
    rifle.set_skeletal_mesh_asset(load(paths['SK_AssaultRifle']))
    magazine = component(bp, unreal.StaticMeshComponent, MAGAZINE, RIFLE)
    magazine.set_static_mesh(load(paths['SM_AssaultRifle_Magazine']))
    muzzle = component(bp, unreal.SceneComponent, MUZZLE, RIFLE)
    muzzle.set_editor_property('relative_location', V(0., 59., 3.2))
    component(bp, unreal.SceneComponent, PORT, RIFLE)
    for name, kind, default in ((POSE,'int','0'),('InfimaAttached','bool','false'),
                                ('InfimaLastShot','int','0'),('InfimaFireUntil','real','0')):
        var(bp,name,kind,default)
    compile_bp(bp)


def attach(g, name, parent, socket):
    g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(name),Parent=g.get(parent),
                SocketName=socket,LocationRule='SnapToTarget',RotationRule='SnapToTarget',
                ScaleRule='KeepRelative',bWeldSimulatedBodies=False))


def play(g, target, clip, loop, rate=1.):
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get(target),
                NewAnimToPlay=clip.get_path_name(),bLooping=loop))
    g.do(g.call('Engine.SkeletalMeshComponent.SetPlayRate',target=g.get(target),Rate=rate))


def position(g, target, value):
    g.do(g.call('Engine.SkeletalMeshComponent.SetPosition',target=g.get(target),InPos=value,bFireNotifies=False))


def active(g):
    return g.yes(g.get('bFirstPerson'),g.mode(1))


def prepare_single_node_clips(paths):
    # Single-node playback needs the authored full poses. The sample project
    # layers these three clips over its idle poses through its Anim Blueprint.
    names = ('A_FP_AssaultRifle_Reload','A_FP_AssaultRifle_Fire','A_FP_AssaultRifle_Fire_Aimed')
    for name in names:
        clip = load(paths[name])
        additive = clip.get_editor_property('additive_anim_type')
        full_pose = getattr(type(additive),'AAT_NONE')
        if additive != full_pose:
            clip.set_editor_property('additive_anim_type',full_pose)
            save(clip)


def connect_view_model(bp, paths):
    clips = {name:load(paths['A_FP_AssaultRifle_'+name]) for name in (
        'Idle_Loop','Idle_Loop_Aimed','Walk_F_Loop','Walk_F_Loop_Aimed','Run_Loop','Reload','Fire','Fire_Aimed')}
    rifle_fire = load(paths['A_FP_WEP_AssaultRifle_Fire'])
    rifle_reload = load(paths['A_FP_WEP_AssaultRifle_Reload'])
    reload_rate = clips['Reload'].get_play_length()/1.78
    fire_rate = 8.
    g = GunGraph(bp,'Weapon_InfimaTick')
    visible = active(g)
    g.visibility(ARMS,visible)
    view = g.branch(visible)
    g.cursor = view.find_else_pin()
    g.set(POSE,0)
    g.set('InfimaLastShot',g.get('LaserShots'))
    g.cursor = view.find_then_pin()
    initialized = g.branch(g.no(g.get('InfimaAttached')))
    attach(g,RIFLE,ARMS,'ik_hand_gun')
    attach(g,MAGAZINE,RIFLE,'Magazine')
    attach(g,PORT,RIFLE,'SOCKET_Ejection')
    g.set('InfimaAttached',True)
    g.visibility(ARMS,True)
    old = initialized.find_else_pin()
    ready = g.set('InfimaFireUntil',g.get('InfimaFireUntil'))
    link(old,ready.find_execute_pin())

    cam_loc = g.loc('FirstPersonCamera')
    cam_rot = g.out(g.call('Engine.SceneComponent.K2_GetComponentRotation',target=g.get('FirstPersonCamera')))
    ahead = g.va(cam_loc,g.vm(g.math('GetForwardVector',InRot=cam_rot),70.))
    blocked = g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=cam_loc,End=ahead,
                    TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
    push = g.out(g.call('Engine.KismetMathLibrary.FInterpTo',Current=g.get('InfimaWallAlpha'),
                       Target=g.pick('Float',1.,0.,g.out(blocked)),DeltaTime=g.dt(),InterpSpeed=13.))
    g.set('InfimaWallAlpha',push)
    wall = g.get('InfimaWallAlpha')
    g.relative(PIVOT,g.vec(g.mul(wall,-11.),0.,g.mul(wall,-4.)),g.rot(g.mul(wall,-16.)))

    reloading = g.branch(g.eq(g.get('WeaponReloadMode'),1))
    g.branch(g.no(g.eq(g.get(POSE),1)))
    g.set(POSE,1)
    play(g,ARMS,clips['Reload'],False,reload_rate)
    play(g,RIFLE,rifle_reload,False,reload_rate)
    progress = g.mul(g.minus(g.now(),g.get('WeaponReloadTime')),reload_rate)
    position(g,ARMS,progress)
    position(g,RIFLE,progress)

    g.cursor = reloading.find_else_pin()
    shot = g.branch(g.no(g.eq(g.get('LaserShots'),g.get('InfimaLastShot'))))
    aiming = g.gt(g.get('WeaponAimAlpha'),.55)
    g.set('InfimaLastShot',g.get('LaserShots'))
    g.set('InfimaFireUntil',g.plus(g.now(),clips['Fire'].get_play_length()/fire_rate))
    g.set(POSE,7)
    fire_aim = g.branch(aiming)
    play(g,ARMS,clips['Fire_Aimed'],False,fire_rate)
    end_aim = g.cursor
    g.cursor = fire_aim.find_else_pin()
    play(g,ARMS,clips['Fire'],False,fire_rate)
    gun_play = g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get(RIFLE),
                      NewAnimToPlay=rifle_fire.get_path_name(),bLooping=False)
    g.do(gun_play)
    link(end_aim,gun_play.find_execute_pin())
    g.do(g.call('Engine.SkeletalMeshComponent.SetPlayRate',target=g.get(RIFLE),Rate=fire_rate))

    g.cursor = shot.find_else_pin()
    g.branch(g.no(g.gt(g.get('InfimaFireUntil'),g.now())))
    speed = g.math('VSizeXY',A=g.out(g.call('Engine.Actor.GetVelocity')))
    running = g.yes(g.gt(speed,500.),g.no(aiming))
    walking = g.gt(speed,55.)
    idle_pose = g.pick('Int',3,2,aiming)
    walk_pose = g.pick('Int',5,4,aiming)
    desired = g.pick('Int',6,g.pick('Int',walk_pose,idle_pose,walking),running)
    g.branch(g.no(g.eq(g.get(POSE),desired)))
    g.set(POSE,desired)
    play(g,RIFLE,rifle_fire,False,0.)
    position(g,RIFLE,0.)
    for state, clip in ((6,'Run_Loop'),(5,'Walk_F_Loop_Aimed'),(4,'Walk_F_Loop'),(3,'Idle_Loop_Aimed')):
        branch = g.branch(g.eq(g.get(POSE),state))
        play(g,ARMS,clips[clip],True)
        g.cursor = branch.find_else_pin()
    play(g,ARMS,clips['Idle_Loop'],True)
    compile_bp(bp)


def hide_legacy_view(bp, graph, targets):
    g = GunGraph(bp,graph,keep=True)
    for name in targets:
        nodes = []
        for n in g.e.list_all_nodes():
            current = n.find_input_pin('bNewVisibility')
            owner = n.find_self_pin()
            if current.is_valid() and owner.is_valid() and any(str(p.get_pin_name())==name for p in owner.list_connected_pins()):
                nodes.append(current)
        assert len(nodes)==1,(graph,name,len(nodes))
        destination = nodes[0]
        old = list(destination.list_connected_pins())
        assert len(old)==1,(graph,name)
        destination.break_pin_links()
        link(g.yes(old[0],g.no(g.mode(1))),destination)
    compile_bp(bp)


def route_hunter_graph(bp, name, replacements):
    g = GunGraph(bp,name,keep=True)
    for old,new in replacements:
        pins = [n.find_output_pin(old) for n in g.e.list_all_nodes()]
        pins = [p for p in pins if p.is_valid() and p.list_connected_pins()]
        assert len(pins)<=1,(name,old,len(pins))
        if not pins:
            assert any(n.find_output_pin(new).is_valid() for n in g.e.list_all_nodes()),(name,old)
            continue
        previous = pins[0]
        endpoints = list(previous.list_connected_pins())
        previous.break_pin_links()
        new_source = g.get(new)
        for p in endpoints:
            link(new_source,p)
    compile_bp(bp)


def route_hunter_effects(bp):
    route_hunter_graph(bp,'Laser_Fire',(('AtomicFPMuzzle',MUZZLE),('WeaponFPPort',PORT)))
    route_hunter_graph(bp,'Lock_FireIfClear',(('AtomicFPMuzzle',MUZZLE),))


def main():
    paths = json.loads((WORK/'Probe.json').read_text(encoding='utf-8'))['paths']
    deps = json.loads((WORK/'Probe2.json').read_text(encoding='utf-8'))['packages']
    bp = load(PLAYER)
    tick = GunGraph(bp,'Atomic_Update',keep=True)
    if any(str(n.get_node_title())=='Weapon_InfimaTick' for n in tick.e.list_all_nodes()):
        return
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    backup = Path(unreal.Paths.project_saved_dir())/'Backups'/'InfimaFPS'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True,exist_ok=True)
    content = Path(unreal.Paths.project_content_dir())
    shutil.copy2(content/(PLAYER.removeprefix('/Game/')+'.uasset'),backup)
    prepare_single_node_clips(paths)
    add_view_model(bp,paths)
    var(bp,'InfimaWallAlpha','real','0')
    compile_bp(bp)
    connect_view_model(bp,paths)
    hide_legacy_view(bp,'Weapon_UpdateView',('AtomicFPArms','AtomicFPGun'))
    hide_legacy_view(bp,'Weapon_ViewMotion',('WeaponFPMagazine',))
    route_hunter_effects(bp)
    finalize(bp,deps,backup)


def finalize(bp,deps,backup):
    tick = GunGraph(bp,'Atomic_Update',keep=True)
    end = [n for n in tick.e.list_all_nodes() if str(n.get_node_title())=='Weapon_ViewMotion']
    assert len(end)==1,[str(n.get_node_title()) for n in tick.e.list_all_nodes()]
    tick.cursor = end[0].find_then_pin()
    tick.do(tick.own('Weapon_InfimaTick'))
    compile_bp(bp)
    for pkg in deps:
        if pkg.rsplit('/',1)[-1].startswith('T_'):
            texture = load(pkg)
            texture.set_editor_property('max_texture_size',1024)
            save(texture)
    save(bp)
    (WORK/'Installed.json').write_text(json.dumps(dict(player=PLAYER,backup=str(backup),
        source=SOURCE,texture_limit=1024,assets=len(deps)),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
