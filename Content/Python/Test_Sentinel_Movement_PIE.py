"""Finite, fixed PIE-only movement integration test. No asset editing/saving.
Creates a disposable floor and ceiling in PIE, observes physics and real key counters.
Stops after ten minutes or the PIE world closes. All spawned objects belong to PIE.
"""
import unreal,os,json,time,math
if '_mhandle' in globals():
    unreal.unregister_slate_post_tick_callback(_mhandle)
_msaved=unreal.Paths.project_saved_dir()
_mreport=json.load(open(os.path.join(_msaved,'sentinel_movement_authoring.json')))
_mclass=unreal.load_class(None,_mreport['asset']+'.'+_mreport['asset'].split('/')[-1]+'_C')
_mdeadline=time.monotonic()+600
_mpawn=None;_mworld=None;_mstage=None;_mstart=0;_mdata={};_mceiling=None;_msamples=[];_mlastsave=0
_mcases=[('settle',.7),('jog',2.0),('brake',.8),('walk',2.0),('sprint',2.0),('jump',1.6),('crouch',.7),('blocked_stand',.7),('stand',.7),('input',450)]
_mindex=0

def _mspawn(cls,x,y,z):
    t=unreal.Transform(location=unreal.Vector(x=x,y=y,z=z),rotation=unreal.Rotator(pitch=0,yaw=0,roll=0),scale=unreal.Vector(x=1,y=1,z=1))
    a=unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(_mworld,cls,t,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN)
    return unreal.GameplayStatics.finish_spawning_actor(a,t)
def _mbox(x,y,z,sx,sy,sz):
    a=_mspawn(unreal.StaticMeshActor,x,y,z)
    c=a.static_mesh_component;c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'))
    c.set_collision_profile_name('BlockAll')
    a.set_actor_scale3d(unreal.Vector(x=sx,y=sy,z=sz));return a
def _mget(k):return _mpawn.get_editor_property(k)
def _mset(k,v):_mpawn.set_editor_property(k,v)
def _mtick(delta):
    global _mpawn,_mworld,_mstart,_mstage,_mindex,_mceiling,_mlastsave
    if time.monotonic()>_mdeadline:
        unreal.unregister_slate_post_tick_callback(_mhandle);return
    world=unreal.EditorLevelLibrary.get_game_world()
    if not world:
        if _mpawn is not None:unreal.unregister_slate_post_tick_callback(_mhandle)
        return
    _mworld=world
    pc=unreal.GameplayStatics.get_player_controller(world,0)
    if not pc:return
    now=unreal.SystemLibrary.get_game_time_in_seconds(world)
    if _mpawn is None:
        _mbox(-50000,0,-20,100,100,.4)
        # Test the actual default pawn when LIVE; otherwise possess an isolated preview.
        if _mreport['mode']=='LIVE':_mpawn=unreal.GameplayStatics.get_player_character(world,0)
        else:_mpawn=_mspawn(_mclass,-50000,0,95);pc.possess(_mpawn)
        _mpawn.set_actor_location(unreal.Vector(x=-50000,y=0,z=95),False,True)
        pc.set_control_rotation(unreal.Rotator(pitch=-12,yaw=0,roll=0))
        _mstart=now
    name,duration=_mcases[_mindex]
    cm=_mpawn.character_movement
    if name!=_mstage:
        _mstage=name;_mstart=now
        _mdata[name]={'samples':[]}
        _mset('WantsSprint',name=='sprint');_mset('WalkingGait',name=='walk')
        if name=='jump':_mpawn.jump()
        if name=='crouch':_mset('WantsCrouch',True)
        if name=='blocked_stand':
            p=_mpawn.get_actor_location();_mceiling=_mbox(p.x,p.y,140,3,3,.4);_mset('WantsCrouch',False)
        if name=='stand':_mceiling.destroy_actor();_mceiling=None
        unreal.log('SENTINEL PIE TEST '+name)
    elapsed=now-_mstart
    if name in ('jog','walk','sprint'):
        _mpawn.add_movement_input(unreal.Vector(x=1,y=0,z=0),1,False)
    p=_mpawn.get_actor_location();v=_mpawn.get_velocity()
    s={'t':round(elapsed,4),'speed':round(math.hypot(v.x,v.y),3),'z':round(p.z,3),'vz':round(v.z,3),'cap':_mpawn.capsule_component.get_unscaled_capsule_half_height(),'max':cm.max_walk_speed}
    for k in ['isSprinting','isGrounded','Falling','GripSlide','isCrouching','LandingActive','CrouchBlocked','FootstepCount','LandingCount','CrouchInputCount','SprintInputCount','WalkInputCount']:
        s[k]=_mget(k)
    # Sampling on every Slate tick retains short key presses and the landing window.
    if len(_mdata[name]['samples'])<1600:_mdata[name]['samples'].append(s)
    else:_mdata[name]['samples'][-1]=s
    if name=='input':
        _mdata[name]['latest']=s
        for k in ('CrouchInputCount','SprintInputCount','WalkInputCount'):
            _mdata[name][k]=max(_mdata[name].get(k,0),s[k])
    if time.monotonic()-_mlastsave>.5:
        _mlastsave=time.monotonic()
        with open(os.path.join(_msaved,'sentinel_movement_pie.json'),'w') as f:json.dump({'asset':_mreport['asset'],'cases':_mdata},f,indent=2)
    if elapsed>=duration and _mindex<len(_mcases)-1:_mindex+=1
def _mguard(delta):
    try:_mtick(delta)
    except Exception as exc:
        unreal.log_error('SENTINEL TEST STOPPED: '+str(exc))
        unreal.unregister_slate_post_tick_callback(_mhandle)
_mhandle=unreal.register_slate_post_tick_callback(_mguard)
unreal.log('SENTINEL fixed PIE movement test armed; waiting for Play')


