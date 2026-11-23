"""Finite PIE regression via real Enhanced Input actions, never ability calls.
Reposition only between cases. Save every case atomically; unregister at finish.
"""
import unreal,os,time,json,traceback,math
S=os.path.abspath(unreal.Paths.project_saved_dir());path=os.path.join(S,'pneumatic_regression.json')
T={'stage':'wait','start':time.monotonic(),'index':0,'cases':{},'passed':False}
# name, duration, position, camera yaw, action axes, Space held intervals
CASES=[('idle',1.,(0,3000),0,(0,0),[]),
 ('right',1.3,(0,3000),0,(1,0),[(.15,.22)]),('left',1.3,(0,3000),0,(-1,0),[(.15,.22)]),
 ('forward',1.3,(0,3000),0,(0,1),[(.15,.22)]),('back',1.3,(0,3000),0,(0,-1),[(.15,.22)]),
 ('diagonal',1.3,(0,3000),0,(1,1),[(.15,.22)]),('camera_right',1.3,(0,3000),90,(1,0),[(.15,.22)]),
 ('neutral',1.3,(0,3000),0,(0,0),[(.15,.22)]),('wall',1.3,(2190,0),0,(0,1),[(.15,.22)]),
 ('cooldown',1.3,(0,3000),0,(0,0),[(.1,.17),(.28,.35)]),
 ('hold_fence',8.3,(0,0),0,(0,0),[(.1,5.5)]),('hold_release',4.5,(0,3000),0,(0,0),[(.1,1.25)]),
 ('blocked',1.3,(0,3000),0,(1,0),[(.15,.22)])]
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def get(k):return T['p'].get_editor_property(k)
def write():
    data={k:v for k,v in T.items() if k not in ('p','pc','sub','jump','move','handle')}
    tmp=path+'.tmp';json.dump(data,open(tmp,'w'),indent=2);os.replace(tmp,path)
def inject(jump=False,axis=(0,0)):
    T['sub'].inject_input_vector_for_action(T['jump'],V(1 if jump else 0),[],[])
    T['sub'].inject_input_vector_for_action(T['move'],V(axis[0],axis[1]),[],[])
def done():
    checks={};c=T['cases']
    for name,axis in [('right',(0,1)),('left',(0,-1)),('forward',(1,0)),('back',(-1,0)),('diagonal',(1,1)),('camera_right',(-1,0)),('neutral',(-1,0))]:
        ss=c[name]['samples'];d=[s for s in ss if s['dash']]
        checks[name+'_dash']=len(d)>1 and c[name]['dash_count']==1
        checks[name+'_no_lift']=max(s['z'] for s in ss)-min(s['z'] for s in ss)<1.0
        if d:
            displacement=(d[-1]['x']-d[0]['x'],d[-1]['y']-d[0]['y'])
            checks[name+'_direction']=all(displacement[i]*axis[i]>100 for i in range(2) if axis[i])
            checks[name+'_speed']=max(math.hypot(s['vx'],s['vy']) for s in d)>1200
    idle=c['idle']['samples'];checks['two_separate_helpers']=all(s['orbs']==2 and s['sphere_meshes']==2 for s in idle)
    checks['no_cylinders']=all(s['cylinder_meshes']==0 for s in idle)
    checks['orbs_float']=max(s['orbz'] for s in idle)-min(s['orbz'] for s in idle)>1.
    checks['wall_collision']=max(s['x'] for s in c['wall']['samples'])<2311
    checks['cooldown']=c['cooldown']['dash_count']==1
    checks['input_lock']=c['blocked']['dash_count']==0
    full=c['hold_fence']['samples'];active=[s for s in full if s['air']]
    checks['hold_no_dash']=c['hold_fence']['dash_count']==0
    checks['hold_launch']=bool(active) and max(s['z'] for s in full)>900
    checks['hold_crosses_7m_wall']=any(s['x']>2540 for s in full)
    checks['hold_four_seconds']=bool(active) and 3.85<active[-1]['t']-active[0]['t']<4.15
    checks['hold_timeout']=any(4.7<s['t']<5.3 and not s['air'] and s['fuel']<.001 for s in full)
    early=c['hold_release']['samples'];checks['release_stops_lift']=any(s['air'] for s in early) and not any(s['air'] for s in early if s['t']>1.4)
    checks['released_hold_does_not_dash']=c['hold_release']['dash_count']==0
    checks['restores_physics']=all(abs(c[n]['samples'][-1]['friction']-c[n]['initial_friction'])<.001 and abs(c[n]['samples'][-1]['brake']-c[n]['initial_brake'])<.1 and not c[n]['samples'][-1]['dash'] for n in c)
    checks['collision_always_enabled']=all(s['collision'] for n in c for s in c[n]['samples'])
    checks['dash_air_effects']=any(s['dash'] and s['particles']==2 and s['hiss'] and s['plumes']==2 for s in c['right']['samples'])
    checks['dash_horizontal_exhaust']=any(s['dash'] and abs(s['exhaust_z'])<.05 for s in c['right']['samples'])
    T.update(stage='done',checks=checks,passed=all(checks.values()));write();unreal.log('PNEUMATIC REGRESSION '+str(checks));unreal.unregister_slate_post_tick_callback(T['handle'])
def tick(dt):
    try:
        w=unreal.EditorLevelLibrary.get_game_world()
        if not w:return
        if time.monotonic()-T['start']>150:raise RuntimeError('Test timeout')
        now=unreal.SystemLibrary.get_game_time_in_seconds(w)
        if T['stage']=='wait':
            p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
            if not p or not pc or now<1:return
            assert p.get_class().get_name()=='BP_ThirdPersonCharacter_C'
            subs=[s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if not s.get_name().startswith('Default__') and unreal.GameplayStatics.get_player_controller(s,0)==pc];assert len(subs)==1
            T.update(p=p,pc=pc,sub=subs[0],jump=unreal.load_asset('/Game/Input/Actions/IA_Jump'),move=unreal.load_asset('/Game/Input/Actions/IA_Move'),stage='prepare')
            pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0)
        p=T['p'];pc=T['pc'];cm=p.character_movement
        name,duration,pos,yaw,axis,windows=CASES[T['index']]
        if T['stage']=='prepare':
            inject();pc.reset_ignore_move_input();cm.stop_movement_immediately();p.set_actor_location(V(pos[0],pos[1],108),False,True);p.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),True);pc.set_control_rotation(unreal.Rotator(pitch=-8,yaw=yaw,roll=0))
            T.update(stage='settle',settle=now+.65)
            T['cases'][name]={'samples':[],'initial_count':get('PneumaticDashCount'),'initial_friction':cm.ground_friction,'initial_brake':cm.braking_deceleration_walking};write();return
        if T['stage']=='settle':
            if now<T['settle']:return
            T.update(stage='run',case_start=now)
            if name=='blocked':pc.set_ignore_move_input(True)
        elapsed=now-T['case_start'];held=any(a<=elapsed<b for a,b in windows)
        # Movement input establishes direction before the tap, then goes neutral
        # immediately so tests measure the dodge rather than walking afterward.
        inject(held,axis if elapsed<.3 else (0,0))
        q=p.get_actor_location();v=p.get_velocity();child=p.get_components_by_class(unreal.ChildActorComponent)
        orbs=[c for c in child if c.get_name().startswith('AssistOrb')]
        sm=p.get_components_by_class(unreal.StaticMeshComponent)
        actors=p.get_all_child_actors(True)
        spheres=[c for a in actors if a.get_class().get_name()=='BP_PneumaticOrb_C' for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='Sphere']
        parts=[c for c in p.get_components_by_class(unreal.ParticleSystemComponent) if c.get_name().startswith(('AirJetLeft','AirJetRight'))]
        audio=next(c for c in p.get_components_by_class(unreal.AudioComponent) if c.get_name().startswith('AirJetHiss'))
        plumes=[c for c in sm if c.get_name().startswith('AirJetPlume')]
        sample=dict(t=round(elapsed,4),x=q.x,y=q.y,z=q.z,vx=v.x,vy=v.y,vz=v.z,direction=str(get('PneumaticDirection')),hold=get('AirJetHoldTime'),pending=bool(get('bPneumaticPending')),dash=bool(get('bPneumaticDash')),air=bool(get('bAirJetActive')),fuel=get('AirJetRemaining'),collision=p.get_actor_enable_collision(),friction=cm.ground_friction,brake=cm.braking_deceleration_walking,orbs=len(orbs),sphere_meshes=len(spheres),cylinder_meshes=sum(1 for c in sm if c.get_name().startswith('AirJetNozzle') and c.static_mesh),orbz=orbs[0].get_world_location().z if orbs else 0,particles=sum(1 for c in parts if c.is_active()),hiss=audio.is_playing(),plumes=sum(1 for c in plumes if c.is_visible()),exhaust_z=plumes[0].get_up_vector().z)
        T['cases'][name]['samples'].append(sample)
        if False and name=='right' and sample['dash'] and elapsed>.27 and not T.get('dash_capture'):
            T['dash_capture']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,os.path.join(S,'Pneumatic_RightDash.png'),delay=0.)
        if False and name=='idle' and elapsed>.7 and not T.get('idle_capture'):
            T['idle_capture']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,os.path.join(S,'Pneumatic_TwoOrbs.png'),delay=0.)
        if elapsed>=duration:
            inject();pc.reset_ignore_move_input();T['cases'][name]['dash_count']=get('PneumaticDashCount')-T['cases'][name]['initial_count'];T['index']+=1
            if T['index']==len(CASES):done()
            else:T['stage']='prepare';write()
    except Exception:
        T.update(stage='failed',error=traceback.format_exc());write();unreal.log_error(T['error']);unreal.unregister_slate_post_tick_callback(T['handle'])
assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE first'
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Developer/Tests/Lvl_AirJetRegression')
T['handle']=unreal.register_slate_post_tick_callback(tick)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
