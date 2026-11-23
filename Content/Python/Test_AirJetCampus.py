"""Finite live-campus fence jump through the same IA_Jump input pipeline.
Pawn is positioned once before takeoff. No position overrides occur in flight.
"""
import unreal,os,json,time,math,traceback
C={'start':time.monotonic(),'stage':'wait','passed':False,'samples':[],'hold':True}
path=os.path.join(unreal.Paths.project_saved_dir(),'airjet_campus_test.json')
def write():
    dest=path+'.tmp'
    json.dump({k:v for k,v in C.items() if k not in ('handle','pawn','subsystem','action','pc')},open(dest,'w'),indent=2);os.replace(dest,path)
def step(dt):
    try:
        w=unreal.EditorLevelLibrary.get_game_world()
        if not w:return
        now=unreal.SystemLibrary.get_game_time_in_seconds(w)
        if time.monotonic()-C['start']>100:raise RuntimeError('Campus jet test timed out')
        if C['stage']=='wait':
            p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
            if not p or now<24:return
            p.set_actor_location(unreal.Vector(x=10200,y=8100,z=2270),False,True);p.set_actor_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0),True)
            pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);pc.set_control_rotation(unreal.Rotator(pitch=-8,yaw=0,roll=0))
            subs=[s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if not s.get_name().startswith('Default__') and unreal.GameplayStatics.get_player_controller(s,0)==pc];assert len(subs)==1
            C.update(pawn=p,pc=pc,subsystem=subs[0],action=unreal.load_asset('/Game/Input/Actions/IA_Jump'),stage='stream',since=now);write();return
        if C['stage']=='stream':
            if now-C['since']<4:return
            p=C['pawn'];q=p.get_actor_location();assert 2230<q.z<2300,str(q)
            C.update(stage='flight',since=now,start_position=[q.x,q.y,q.z],identity=p.get_path_name());write()
        elapsed=now-C['since'];p=C['pawn'];q=p.get_actor_location()
        # Release just after crossing the actual north perimeter, retaining a
        # safe external landing apron. Four-second exhaustion is tested separately.
        if q.x>12400 or elapsed>3.35:C['hold']=False
        C['subsystem'].inject_input_vector_for_action(C['action'],unreal.Vector(x=1 if C['hold'] else 0,y=0,z=0),[],[])
        left=next(s for s in p.get_components_by_class(unreal.StaticMeshComponent) if s.get_name().startswith('AirJetPlumeLeft'))
        C['samples'].append({'t':round(elapsed,4),'x':round(q.x,2),'y':round(q.y,2),'z':round(q.z,2),'active':bool(p.get_editor_property('bAirJetActive')),'fuel':p.get_editor_property('AirJetRemaining'),'collision':p.get_actor_enable_collision(),'plume_visible':left.is_visible()})
        if elapsed>2.7 and not C.get('captured'):
            C['captured']=True;unreal.AutomationLibrary.take_high_res_screenshot(1440,900,os.path.join(unreal.Paths.project_saved_dir(),'AirJet_CampusFence.png'),delay=0.)
        if elapsed>8:
            C['subsystem'].inject_input_vector_for_action(C['action'],unreal.Vector(),[],[])
            crossing=[s for s in C['samples'] if 12100<s['x']<12330]
            C['checks']={'crossed_actual_perimeter':q.x>12330,'cleared_barbed_wire':bool(crossing) and min(s['z']-105 for s in crossing)>2824,'landed_outside':q.x>12330 and 2230<q.z<2300,'refilled':abs(p.get_editor_property('AirJetRemaining')-4)<.001,'same_pawn':p.get_path_name()==C['identity'],'collision_kept':all(s['collision'] for s in C['samples']),'directed_plumes_visible':any(s['active'] and s['plume_visible'] for s in C['samples'])}
            C.update(stage='passed',passed=all(C['checks'].values()),final=[q.x,q.y,q.z]);write();unreal.unregister_slate_post_tick_callback(C['handle']);return
        if int(elapsed*4)!=C.get('last_saved'):C['last_saved']=int(elapsed*4);write()
    except Exception:
        C.update(stage='failed',error=traceback.format_exc());write();unreal.log_error(C['error']);unreal.unregister_slate_post_tick_callback(C['handle'])
C['handle']=unreal.register_slate_post_tick_callback(step)
if not unreal.EditorLevelLibrary.get_game_world():unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()




