"""Finite PIE integration: input is injected into IA_Jump through Enhanced Input,
including Started/Completed. Ability functions are never called by the fixture.
Only the running pawn is repositioned between cases, never during a flight.
"""
import unreal,os,time,json,traceback,math
T={'start':time.monotonic(),'stage':'wait','passed':False,'cases':{},'index':0}
cases=[('tap',2.6,(0,0),[(.0,.06)]),('fence_and_timeout',8.3,(0,0),[(.0,5.4)]),('release_early',5.5,(0,3000),[(.0,1.3)]),('pulse_budget',6.5,(0,3000),[(.0,1.0),(1.3,2.3)]),('ceiling',4.5,(-3600,0),[(.0,1.0)]),('input_lock',5.5,(0,3000),[(.0,2.2)])]
path=os.path.join(unreal.Paths.project_saved_dir(),'airjet_regression.json')
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def write():json.dump({k:v for k,v in T.items() if k not in ('handle','pawn','pc','subsystem','action')},open(path,'w'),indent=2)
def get(k):return T['pawn'].get_editor_property(k)
def finish():
    checks={}
    c=T['cases'];tap=c['tap']['samples'];full=c['fence_and_timeout']['samples'];early=c['release_early']['samples'];pulse=c['pulse_budget']['samples'];ceil=c['ceiling']['samples'];locked=c['input_lock']['samples']
    checks['tap_ordinary_jump']=max(s['z'] for s in tap)>150 and not any(s['active'] for s in tap)
    active=[s for s in full if s['active']]
    checks['boost_activated']=bool(active)
    checks['crossed_7m_fence']=any(s['x']>2540 for s in full)
    crossing=[s for s in full if 2300<s['x']<2500]
    checks['capsule_cleared_fence']=bool(crossing) and min(s['z']-105 for s in crossing)>698
    checks['thrust_limit']=bool(active) and 3.88<active[-1]['t']-active[0]['t']<4.12
    checks['exhausted_while_still_held']=any(s['t']>4.35 and s['t']<5.2 and not s['active'] and s['fuel']<.001 for s in full)
    checks['release_stops_thrust']=any(s['active'] for s in early) and not any(s['active'] for s in early if 1.4<s['t']<2)
    checks['release_keeps_unused_fuel']=any(1.4<s['t']<1.6 and 2.7<s['fuel']<3.2 for s in early)
    checks['pulse_does_not_refill_midair']=any(2.0<s['t']<2.2 and 2<s['fuel']<2.7 for s in pulse)
    checks['ceiling_collision']=max(s['z']+105 for s in ceil)<382
    checks['input_lock_stops_thrust']=any(s['active'] for s in locked) and not any(s['active'] for s in locked if 1.15<s['t']<2)
    checks['physics_restored']=all(abs(c[n]['samples'][-1]['brake']-1500)<.1 and abs(c[n]['samples'][-1]['air']-.35)<.001 for n in c)
    checks['landing_refills']=all(abs(c[n]['samples'][-1]['fuel']-4)<.001 for n in c)
    checks['collision_never_disabled']=all(s['collision'] for n in c for s in c[n]['samples'])
    checks['steam_and_hiss_active']=any(s['active'] and s['particles']==2 and s['hiss'] for s in full)
    T.update(checks=checks,passed=all(checks.values()),stage='keyboard_ready')
    T['keyboard_initial_presses']=get('AirJetInputPresses');T['keyboard_press_count']=0;write()
    unreal.log('AIRJET REGRESSION FINISHED: '+str(checks))
def tick(dt):
    try:
        world=unreal.EditorLevelLibrary.get_game_world()
        if not world:return
        if time.monotonic()-T['start']>190:
            unreal.unregister_slate_post_tick_callback(T['handle']);return
        now=unreal.SystemLibrary.get_game_time_in_seconds(world)
        if T['stage']=='wait':
            p=unreal.GameplayStatics.get_player_character(world,0);pc=unreal.GameplayStatics.get_player_controller(world,0)
            if not p or not pc or now<1:return
            assert p.get_class().get_name()=='BP_ThirdPersonCharacter_C'
            # Only a live local-player subsystem is eligible, never a default object.
            subs=[s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if not s.get_name().startswith('Default__') and unreal.GameplayStatics.get_player_controller(s,0)==pc]
            assert len(subs)==1,[s.get_path_name() for s in subs]
            T.update(pawn=p,pc=pc,subsystem=subs[0],action=unreal.load_asset('/Game/Input/Actions/IA_Jump'),stage='prepare')
            pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0)
        if T['stage']=='keyboard_ready':
            new_count=get('AirJetInputPresses')-T['keyboard_initial_presses']
            if new_count!=T['keyboard_press_count']:T['keyboard_press_count']=new_count;write()
            return
        if T['stage']=='prepare':
            name,duration,pos,windows=cases[T['index']]
            T['pc'].reset_ignore_move_input();T['subsystem'].inject_input_vector_for_action(T['action'],V(),[],[])
            T['pawn'].character_movement.stop_movement_immediately()
            T['pawn'].set_actor_location(V(pos[0],pos[1],108),False,True)
            T['pawn'].set_actor_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0),True)
            T['pc'].set_control_rotation(unreal.Rotator(pitch=-8,yaw=0,roll=0))
            T.update(stage='settle',settle_until=now+.4)
            T['cases'][name]={'samples':[]};write();return
        if T['stage']=='settle':
            if now<T['settle_until']:return
            T.update(stage='run',case_start=now)
        name,duration,pos,windows=cases[T['index']];elapsed=now-T['case_start']
        held=any(a<=elapsed<b for a,b in windows)
        T['subsystem'].inject_input_vector_for_action(T['action'],V(1 if held else 0),[],[])
        if name=='input_lock':
            if elapsed>=1 and not T.get('locked'):
                T['pc'].set_ignore_move_input(True);T['locked']=True
            if elapsed>=2.4 and T.get('locked'):T['pc'].reset_ignore_move_input();T['locked']=False
        p=T['pawn'];q=p.get_actor_location();cm=p.character_movement
        particles=[s for s in p.get_components_by_class(unreal.ParticleSystemComponent) if s.get_name().startswith(('AirJetLeft','AirJetRight'))]
        audio=next(s for s in p.get_components_by_class(unreal.AudioComponent) if s.get_name().startswith('AirJetHiss'))
        T['cases'][name]['samples'].append({'t':round(elapsed,4),'x':round(q.x,2),'z':round(q.z,2),'vz':round(p.get_velocity().z,2),'fuel':round(get('AirJetRemaining'),4),'active':bool(get('bAirJetActive')),'held':bool(get('bAirJetHeld')),'collision':p.get_actor_enable_collision(),'brake':cm.braking_deceleration_falling,'air':cm.air_control,'particles':sum(1 for s in particles if s.is_active()),'hiss':audio.is_playing()})
        if name=='fence_and_timeout' and elapsed>2.8 and not T.get('captured'):
            T['captured']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,os.path.join(unreal.Paths.project_saved_dir(),'AirJet_FenceFlight.png'),delay=0.)
        if elapsed>=duration:
            T['subsystem'].inject_input_vector_for_action(T['action'],V(),[],[])
            T['pc'].reset_ignore_move_input();T['index']+=1
            if T['index']==len(cases):finish()
            else:T['stage']='prepare';write()
    except Exception:
        T['error']=traceback.format_exc();T['stage']='failed';write();unreal.log_error(T['error']);unreal.unregister_slate_post_tick_callback(T['handle'])
T['handle']=unreal.register_slate_post_tick_callback(tick)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()



