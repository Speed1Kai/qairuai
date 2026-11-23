"""Fit separate first-person grips for the two approved weapons and their reloads."""
from datetime import datetime
import json
import math
from pathlib import Path
import shutil
import sys

import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0,str(PROJECT/'Content/Python'))
from CityCombat_Common import A, B, G, compile_bp, link, pin, save, val
from Build_Firearms import GunGraph

PLAYER = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
ROOT = '/Game/Combat/ApprovedWeapons/Grips'
BASE = '/Game/Combat/AtomicWeapon/Animations/Atomic_FPGrip'
RELOAD = '/Game/Combat/Firearms/AS_Sentinel_MagazineSwap'
V = unreal.Vector
PREFIX = 'CC_Base_'
FIT = {
    'Carbine': {
        'L': ((-6.3, 3.0, 1.7), 28., (7., 13., 9.)),
        'R': ((-2.6, 3.8, -3.3), -5., (2., 6., 4.)),
    },
    'Emitter': {
        'L': ((-9.1, -2.2, -4.9), 26., (10., 13., 7.)),
        'R': ((-3.1, 0.5, -5.8), -10., (7., 11., 6.)),
    },
}


def product(a,b):
    return unreal.Quat(x=a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,
                       y=a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
                       z=a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,
                       w=a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z)


def inverse(a):
    return unreal.Quat(x=-a.x,y=-a.y,z=-a.z,w=a.w)


def unit(v):
    return v/v.length()


def between(a,b):
    a,b=unit(a),unit(b)
    cross,w=a.cross(b),1.+a.dot(b)
    scale=math.sqrt(cross.dot(cross)+w*w)
    assert scale>1e-6
    return unreal.Quat(x=cross.x/scale,y=cross.y/scale,z=cross.z/scale,w=w/scale)


def ease(t):
    t=min(1.,max(0.,t))
    return t*t*(3.-2.*t)


def around_forward(angle):
    half=math.radians(angle)*.5
    return unreal.Quat(x=0.,y=math.sin(half),z=0.,w=math.cos(half))


def evaluate(pose,side,fit,weight):
    def bone(key,world=False):
        return unreal.AnimPoseExtensions.get_bone_pose(pose,PREFIX+side+'_'+key,
            unreal.AnimPoseSpaces.WORLD if world else unreal.AnimPoseSpaces.LOCAL)

    offset, roll, curls=fit
    upper,lower,wrist=(bone(n,True) for n in ('Upperarm','Forearm','Hand'))
    s,e,h=upper.translation,lower.translation,wrist.translation
    desired=h+V(*offset)*weight
    toward=unit(desired-s)
    l1,l2=(e-s).length(),(h-e).length()
    d=max(abs(l1-l2)+.08,min((desired-s).length(),l1+l2-.08))
    pole=unit((e-s)-toward*(e-s).dot(toward))
    along=(l1*l1-l2*l2+d*d)/(2*d)
    elbow=s+toward*along+pole*math.sqrt(max(.001,l1*l1-along*along))
    wrist_goal=s+toward*d
    q1=product(between(e-s,elbow-s),upper.rotation)
    q2=product(between(h-e,wrist_goal-elbow),lower.rotation)
    wrist_rotation=product(around_forward(roll*weight),wrist.rotation)
    rotations={
        'Upperarm':product(inverse(bone('Clavicle',True).rotation),q1),
        'Forearm':product(inverse(q1),q2),
        'Hand':product(inverse(q2),wrist_rotation),
    }
    handed=1. if side=='L' else -1.
    for finger in ('Index','Mid','Ring','Pinky'):
        for index,force in enumerate(curls,1):
            key=finger+str(index)
            # Leave the trigger finger less curled than the three supporting digits.
            gain=.35 if side=='R' and finger=='Index' else 1.
            delta=unreal.Rotator(yaw=handed*force*gain*weight).quaternion()
            rotations[key]=product(bone(key).rotation,delta)
    for index,force in ((1,-8. if side=='L' else 6.),(2,9.),(3,5.)):
        key='Thumb'+str(index)
        delta=unreal.Rotator(yaw=handed*force*weight).quaternion()
        rotations[key]=product(bone(key).rotation,delta)
    return {PREFIX+side+'_'+name:(bone(name).translation,q,bone(name).scale3d)
            for name,q in rotations.items()}


def build_clip(label,reload):
    src=A.load_asset(RELOAD if reload else BASE)
    target=ROOT+'/AS_FP_'+label+('Reload' if reload else 'Hold')
    clip=A.load_asset(target) if A.does_asset_exist(target) else A.duplicate_asset(src.get_path_name(),target)
    assert clip and src
    size=55 if reload else 1
    tracks={}
    for frame in range(size):
        t=frame/54. if reload else 0.
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(src,t*src.sequence_length,unreal.AnimPoseEvaluationOptions())
        for side,fit in FIT[label].items():
            # The support hand leaves its grip during the existing magazine motion.
            weight=1. if not reload or side=='R' else max(1.-ease(t/.19),ease((t-.73)/.27))
            for name,row in evaluate(pose,side,fit,weight).items():
                tracks.setdefault(name,[]).append(row)

    controller=clip.controller
    controller.open_bracket('Set separate weapon grip keys',False)
    try:
        if not reload:
            controller.set_frame_rate(unreal.FrameRate(numerator=30,denominator=1),False)
            controller.set_number_of_frames(unreal.FrameNumber(1),False)
        for name,rows in tracks.items():
            positions,rotations,scales=map(list,zip(*rows))
            if not reload:
                positions*=2
                rotations*=2
                scales*=2
            assert controller.set_bone_track_keys(name,positions,rotations,scales,False),name
    finally:
        controller.close_bracket(False)
    save(clip)
    return clip


def fit_graph(bp,method,clips,reload=False):
    graph=GunGraph(bp)
    graph.e=G.get_graph_editor_by_name(bp,method)
    targets=[node for node in graph.e.list_all_nodes() if node.find_input_pin('NewAnimToPlay').is_valid()
             and str(node.find_input_pin('NewAnimToPlay').get_pin_value()).startswith(RELOAD if reload else BASE)]
    expected=2 if method=='Weapon_ReloadTick' else 1
    completed=[node for node in graph.e.list_all_nodes() if node.get_name().startswith('PlaySeparateEmitterGrip_')]
    if completed:
        assert len(completed)==expected,method
        return expected
    assert len(targets)==expected,(method,len(targets))
    for i,node in enumerate(targets):
        entry=node.find_execute_pin()
        [previous]=entry.list_connected_pins()
        entry.break_pin_links()
        after=list(node.find_then_pin().list_connected_pins())
        graph.cursor=previous
        split=graph.branch(graph.mode(2))
        val(pin(node,'NewAnimToPlay'),clips['Carbine'].get_path_name())
        link(split.find_else_pin(),entry)
        call=graph.do(graph.call('Engine.SkeletalMeshComponent.PlayAnimation',target=graph.get('AtomicFPArms'),
                                 NewAnimToPlay=clips['Emitter'].get_path_name(),bLooping=not reload))
        call.rename('PlaySeparateEmitterGrip_'+str(i))
        for target in after:
            link(graph.cursor,target)
    return len(targets)


def install():
    bp=A.load_asset(PLAYER)
    assert bp and not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    out=PROJECT/'Saved/WeaponGrip'
    out.mkdir(exist_ok=True)
    backup=PROJECT/'Saved/Backups/WeaponGrip'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    for path in (PLAYER,*(ROOT+'/AS_FP_'+label+kind for label in FIT for kind in ('Hold','Reload'))):
        rel=Path('Content')/(path.removeprefix('/Game/')+'.uasset')
        existing=PROJECT/rel
        if existing.is_file():
            preserve=backup/rel
            preserve.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(existing,preserve)
    A.make_directory(ROOT)
    holds={label:build_clip(label,False) for label in FIT}
    reloads={label:build_clip(label,True) for label in FIT}
    patched={}
    for fn in ('Atomic_Equip','Weapon_ReloadTick'):
        patched[fn]=fit_graph(bp,fn,holds)
    patched['Weapon_Reload']=fit_graph(bp,'Weapon_Reload',reloads,True)
    compile_bp(bp)
    save(bp)
    (out/'Installed.json').write_text(json.dumps({'backup':str(backup),'fits':FIT,'graphs':patched,
        'animations':[a.get_path_name() for a in (*holds.values(),*reloads.values())]},indent=2),encoding='utf8')


if __name__=='__main__':
    install()
