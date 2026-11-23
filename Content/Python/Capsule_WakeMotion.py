"""Supported reclining pose and a contact-aware, baked wake-up motion.

Only the existing Quinn skeleton and idle pose are used. IK is evaluated once
while authoring; the game plays an ordinary compressed animation sequence.
"""
import unreal
import math
import os
import json

TILT = 65.0
ORIGIN = (-550.0, 280.0, 120.0)
ACTOR_ORIGIN = (-550.0, 280.0, 0.0)
EXIT = (-550.0, -55.0, 0.0)
FRAMES = 405
FPS = 30
API = unreal.AnimPoseExtensions
SPACE = unreal.AnimPoseSpaces.WORLD


def vec(p):
    return unreal.Vector(*[float(n) for n in p])


def xyz(p):
    return (p.x, p.y, p.z)


def add(a,b): return tuple(a[i]+b[i] for i in range(3))
def sub(a,b): return tuple(a[i]-b[i] for i in range(3))
def mul(a,k): return tuple(n*k for n in a)
def dot(a,b): return sum(a[i]*b[i] for i in range(3))
def length(a): return math.sqrt(dot(a,a))
def unit(a): return mul(a,1/max(.0001,length(a)))
def lerp(a,b,t): return add(mul(a,1-t),mul(b,t))


def sample(keys, f):
    if f <= keys[0][0]: return keys[0][1]
    for (fa,a),(fb,b) in zip(keys,keys[1:]):
        if f <= fb:
            t=(f-fa)/max(1,fb-fa)
            t=t*t*(3-2*t)
            return lerp(a,b,t) if isinstance(a,tuple) else a+(b-a)*t
    return keys[-1][1]


def pod(u=0,h=0,d=0):
    a=math.radians(TILT)
    return (ORIGIN[0]-math.sin(a)*h+math.cos(a)*d,
            ORIGIN[1]+u,ORIGIN[2]+math.cos(a)*h+math.sin(a)*d)


def component(p):
    x,y,z=sub(p,ACTOR_ORIGIN)
    return (-y,x,z)


def world(p):
    return add(ACTOR_ORIGIN,(p[1],-p[0],p[2]))


def get(pose,bone):
    return API.get_bone_pose(pose,bone,SPACE)


def edit(pose,bone,rotation=None,position=None):
    transform=get(pose,bone)
    if rotation is not None: transform.rotation=rotation
    if position is not None: transform.translation=vec(position)
    # UE 5.8's WORLD setter uses skeleton indices as compact-pose indices on
    # reduced meshes. Convert explicitly and use the safe LOCAL setter.
    if bone != 'root':
        side=bone[-1]
        parent={'thigh':'pelvis','calf':'thigh_'+side,'foot':'calf_'+side,
                'upperarm':'clavicle_'+side,'lowerarm':'upperarm_'+side,
                'hand':'lowerarm_'+side}[bone.rsplit('_',1)[0]]
        transform=unreal.MathLibrary.make_relative_transform(transform,get(pose,parent))
    return API.set_bone_pose(pose,transform,bone,unreal.AnimPoseSpaces.LOCAL)


def limb(pose,upper,lower,end,target,pole,rotation=None):
    """Two-bone IK preserves segment lengths and fixes the ankle/palm target."""
    a,b,c=[xyz(get(pose,n).translation) for n in (upper,lower,end)]
    target=component(target)
    direction=unit(sub(target,a))
    l1,l2=length(sub(b,a)),length(sub(c,b))
    dist=max(abs(l1-l2)+.1,min(l1+l2-.1,length(sub(target,a))))
    pole_dir=sub(component(pole),a)
    normal=unit(sub(pole_dir,mul(direction,dot(pole_dir,direction))))
    x=(l1*l1-l2*l2+dist*dist)/(2*dist)
    elbow=add(add(a,mul(direction,x)),mul(normal,math.sqrt(max(0,l1*l1-x*x))))
    delta=unreal.MathLibrary.quat_find_between_vectors(vec(sub(b,a)),vec(sub(elbow,a)))
    pose=edit(pose,upper,rotation=delta*get(pose,upper).rotation)
    b,c=[xyz(get(pose,n).translation) for n in (lower,end)]
    wanted=add(a,mul(direction,dist))
    delta=unreal.MathLibrary.quat_find_between_vectors(vec(sub(c,b)),vec(sub(wanted,b)))
    pose=edit(pose,lower,rotation=delta*get(pose,lower).rotation)
    if rotation is not None: pose=edit(pose,end,rotation=rotation)
    return pose, length(sub(xyz(get(pose,end).translation),target))


def recline_existing_shell(actors):
    """Move only the capsule assembly, preserving the rest of the laboratory."""
    for actor in actors:
        for tag in actor.get_editor_property('tags'):
            if str(tag).startswith('CapsuleRailHome='):
                home=tuple(float(n) for n in str(tag).split('=',1)[1].split(';'))
                actor.set_actor_location(vec(home),False,False)
    back=next(a for a in actors if a.get_actor_label()=='REF_PodBack')
    old=math.radians(back.get_actor_rotation().pitch)
    bp=back.get_actor_location()
    old_origin=(bp.x+39*math.cos(old),bp.y,bp.z+39*math.sin(old))
    delta=unreal.Rotator(pitch=TILT-math.degrees(old)).quaternion()
    for actor in actors:
        name=actor.get_actor_label()
        if not name.startswith('REF_Pod') or name.startswith(('REF_PodPedestal','REF_PodUmbilical','REF_PodInterior')):
            continue
        p=sub(xyz(actor.get_actor_location()),old_origin)
        h=-math.sin(old)*p[0]+math.cos(old)*p[2]
        d=math.cos(old)*p[0]+math.sin(old)*p[2]
        actor.modify()
        actor.set_actor_location(vec(pod(p[1],h,d)),False,False)
        actor.set_actor_rotation((delta*actor.get_actor_rotation().quaternion()).rotator(),False)
        comp=actor.get_component_by_class(unreal.StaticMeshComponent)
        if comp and name in ('REF_PodBack','REF_PodMattress','REF_PodFootCowl'):
            comp.set_collision_profile_name('BlockAll')
    for actor in actors:
        if actor.get_actor_label()=='REF_PodHeadrest':
            actor.set_actor_location(vec(pod(0,90,-12)),False,False)


def build_motion():
    asset='/Game/LabTutorial/Intro/A_CapsuleWakeAndExit'
    idle=unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle')
    mesh=unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')
    options=unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh',mesh)
    base=API.get_anim_pose_at_time(idle,0.0,options)
    names=API.get_bone_names(base)
    pelvis=xyz(get(base,'pelvis').translation)
    rest_pelvis=pod(0,25,0)
    qrest=unreal.Rotator(roll=-TILT).quaternion()
    rest_translation=sub(component(rest_pelvis),xyz(qrest.rotate_vector(vec(pelvis))))
    rest_feet={'l':pod(-13,-60,10),'r':pod(13,-60,10)}
    qexit=unreal.Rotator(yaw=-90).quaternion()
    exit_base=component(EXIT)
    exit_pelvis=world(add(exit_base,xyz(qexit.rotate_vector(vec(pelvis)))))
    exit_feet={s:world(add(exit_base,xyz(qexit.rotate_vector(get(base,'foot_'+s).translation)))) for s in ('l','r')}
    pelvis_keys=[(0,rest_pelvis),(132,rest_pelvis),(170,(-565,240,139)),
        (198,(-550,195,127)),(225,(-550,195,127)),(248,(-550,160,141)),
        (270,(-550,145,151.526)),(296,(-550,122,124)),(315,(-550,105,112)),
        (335,(-550,65,122.5)),(355,(-550,20,92)),(375,(-550,-35,90)),(390,exit_pelvis)]
    headings=[(0,0),(132,0),(170,-30),(198,-90),(390,-90)]
    tilts=[(0,TILT),(132,TILT),(170,35),(198,0),(225,-5),(248,-12),
           (270,0),(296,-8),(315,-5),(335,0),(355,-7),(375,-2),(390,0)]
    feet={
      'l':[(0,rest_feet['l']),(132,rest_feet['l']),(160,(-520,245,170)),
           (180,(-550,180,155)),(198,(-565,155,63)),(270,(-565,155,63)),
           (288,(-565,125,91)),(315,(-565,65,36)),(335,(-565,65,36)),
           (348,(-565,20,62)),(365,(-565,-25,8)),(375,(-565,-25,8)),(390,exit_feet['l'])],
      'r':[(0,rest_feet['r']),(140,rest_feet['r']),(168,(-500,245,170)),
           (190,(-535,180,155)),(210,(-535,155,63)),(305,(-535,155,63)),
           (316,(-535,135,85)),(335,(-535,45,36)),(352,(-535,45,36)),
           (365,(-535,15,62)),(385,exit_feet['r']),(390,exit_feet['r'])]}
    tracks={str(n):[[],[],[]] for n in names}
    reach=[]
    contacts=[]
    for f in range(FRAMES+1):
        pose=API.get_anim_pose_at_time(idle,0.0,options)
        heading,tilt=sample(headings,f),sample(tilts,f)
        rootq=unreal.Rotator(yaw=heading,roll=-tilt).quaternion()
        rootp=sub(component(sample(pelvis_keys,f)),xyz(rootq.rotate_vector(vec(pelvis))))
        pose=edit(pose,'root',rootq,rootp)
        if f>=0:
            blend=min(1,max(0,(f-132)/78))
            blend=blend*blend*(3-2*blend)
            for side in ('l','r'):
                flat=unreal.Rotator(yaw=heading).quaternion()*get(base,'foot_'+side).rotation
                reclined=rootq*get(base,'foot_'+side).rotation
                ankleq=unreal.MathLibrary.quat_slerp(reclined,flat,blend)
                hip=world(xyz(get(pose,'thigh_'+side).translation))
                forward=(math.cos(math.radians(heading)),math.sin(math.radians(heading)),0)
                bed_normal=(math.cos(math.radians(TILT)),0,math.sin(math.radians(TILT)))
                knee_direction=lerp(bed_normal,forward,blend)
                pole=add(hip,add(mul(knee_direction,95),(0,0,10)))
                pose,error=limb(pose,'thigh_'+side,'calf_'+side,'foot_'+side,
                               sample(feet[side],f),pole,ankleq)
                if error>1: reach.append((f,side,round(error,2)))
            # Brace the palms on the edge while the pelvis leaves the mattress.
            weight=sample([(0,0),(150,0),(190,1),(230,1),(270,0),(390,0)],f)
            resting=sample([(0,1),(132,1),(175,0),(390,0)],f)
            if weight>0 or resting>0:
                for side,dx in (('l',-24),('r',24)):
                    current=world(xyz(get(pose,'hand_'+side).translation))
                    target=lerp(current,pod(-26 if side=='l' else 26,20,3),resting)
                    target=lerp(target,(-550+dx,215,124),weight)
                    shoulder=world(xyz(get(pose,'upperarm_'+side).translation))
                    pole=add(shoulder,(-30 if side=='l' else 30,10,-20))
                    pose,_=limb(pose,'upperarm_'+side,'lowerarm_'+side,'hand_'+side,target,pole)
        for bone in names:
            t=API.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.LOCAL)
            p,q,s=tracks[str(bone)]
            p.append(t.translation);q.append(t.rotation);s.append(t.scale3d)
        if f%15==0:
            contacts.append(dict(frame=f, pelvis=world(xyz(get(pose,'pelvis').translation)),
                left=world(xyz(get(pose,'foot_l').translation)),right=world(xyz(get(pose,'foot_r').translation)),
                head=world(xyz(get(pose,'head').translation))))
    sequence=unreal.EditorAssetLibrary.load_asset(asset) if unreal.EditorAssetLibrary.does_asset_exist(asset) else unreal.EditorAssetLibrary.duplicate_asset(idle.get_path_name().split('.')[0],asset)
    sequence.modify()
    controller=sequence.get_editor_property('controller')
    controller.open_bracket(unreal.Text('Supported capsule wake-up and steps'),False)
    try:
        controller.set_frame_rate(unreal.FrameRate(FPS,1),False)
        controller.set_number_of_frames(unreal.FrameNumber(FRAMES),False)
        controller.remove_all_bone_tracks(False)
        for bone,(positions,rotations,scales) in tracks.items():
            if not controller.add_bone_curve(bone,False):
                raise RuntimeError('Could not author bone '+bone)
            if not controller.set_bone_track_keys(bone,positions,rotations,scales,False):
                raise RuntimeError('Could not write motion for '+bone)
    finally:
        controller.close_bracket(False)
    sequence.set_editor_property('enable_root_motion',False)
    sequence.set_editor_property('force_root_lock',False)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence,only_if_is_dirty=False):
        raise RuntimeError('Could not save the capsule wake-up animation')
    with open(os.path.join(unreal.Paths.project_saved_dir(),'capsule_motion_contacts.json'),'w') as f:
        json.dump(dict(reach_errors=reach,contacts=contacts,rest_feet=rest_feet,exit_feet=exit_feet),f,indent=2)
    return sequence
