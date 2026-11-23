"""Finite PIE regression. Uses the real pawn, physical movement, streamed map.
No package or player-spawn changes. F is pressed separately in the viewport.
"""
import unreal,time,math,json,os,traceback
S={'start':time.monotonic(),'stage':'wait','passed':False,'route':[],'checks':{}}
out=os.path.join(unreal.Paths.project_saved_dir(),'reference_campus_pie.json')
def V(p):return unreal.Vector(x=p[0],y=p[1],z=p[2])
def W(px,py):return (5850+(786-py)*12,1500+(px-708)*12)
def write():json.dump({k:v for k,v in S.items() if k not in ('handle','pawn','exit','campus','camera')},open(out,'w'),ensure_ascii=False,indent=2)
def step(dt):
    try:
        world=unreal.EditorLevelLibrary.get_game_world()
        if not world:return
        t=time.monotonic()-S['start']
        if t>520:raise RuntimeError('Finite campus regression timeout: '+S['stage'])
        p=unreal.GameplayStatics.get_player_character(world,0)
        pc=unreal.GameplayStatics.get_player_controller(world,0)
        if not p or not pc:return
        if t>7 and S['stage']=='wait':
            p.set_actor_location(V((5850,1070,2270)),False,True)
            pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0)
            pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0))
            S.update(stage='stream',identity=p.get_path_name());write()
        if S['stage']=='stream':
            campus=next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_class().get_name()=='BP_ReferenceCampus_C'),None)
            if not campus:return
            S['campus']=campus
            S['exit']=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_class().get_name()=='BP_SurfaceDeparture_C')
            cs=campus.get_components_by_class(unreal.InstancedStaticMeshComponent)
            S['checks']['instance_count']=sum(c.get_instance_count() for c in cs)
            # One exact global position proves the new streaming frame has been inherited.
            ground=next(c for c in cs if c.get_name().startswith('Box_floor_Collision'))
            q=ground.get_instance_transform(0,True).translation
            S['checks']['first_ground_world']=[q.x,q.y,q.z]
            S['checks']['stream_aligned']=abs(q.x-225)<2 and abs(q.y-6650)<2 and abs(q.z-2115)<2
            assert S['checks']['stream_aligned'],str(q)
            S.update(stage='at_button',ready=time.monotonic());write()
        if S['stage']=='at_button':
            S['door_open']=S['exit'].get_editor_property('ExitDoorAmount');write()
            if S['door_open']<.99:return
            # Walk the north road to B, energy, hangar and the eastern checkpoint.
            points=[(5850,2300),W(820,786),W(870,786),W(870,615),W(930,553),W(1065,553),W(1065,510),W(1065,553),W(1438,553),W(1438,510),W(1438,553),W(1740,553),W(1800,615),W(1800,786),W(1960,786),W(2050,786),(5850,18850)]
            S.update(stage='walking_north',targets=points,index=0,waypoint_start=time.monotonic(),last_record=0);write()
        if S['stage'] in ('walking_north','walking_south'):
            target=S['targets'][S['index']];q=p.get_actor_location();dx=target[0]-q.x;dy=target[1]-q.y;d=math.hypot(dx,dy)
            if d<60:
                S['route'].append({'target':target,'position':[q.x,q.y,q.z],'seconds':time.monotonic()-S['waypoint_start']});S['index']+=1;S['waypoint_start']=time.monotonic();write()
                if S['index']==len(S['targets']):
                    if S['stage']=='walking_north':
                        # The bridge gap must stay open; a road route returns along the south.
                        S['checks']['bridge_gap_trace']=unreal.SystemLibrary.line_trace_single(world,V((5850,20000,2400)),V((5850,20000,1500)),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[p],unreal.DrawDebugTrace.NONE,True).export_text()
                        S.update(stage='walking_south',index=0,targets=[W(2050,786),W(1800,786),W(1800,974),W(1740,1036),W(1558,1036),W(1558,1080),W(1558,1036),W(1080,1036),W(1080,1080),W(1080,1036),W(930,1036),W(870,974),W(870,786),W(708,786),(5850,1070)]);write()
                    else:
                        S.update(stage='passed',passed=p.get_path_name()==S['identity']);write();unreal.unregister_slate_post_tick_callback(S['handle'])
                return
            if time.monotonic()-S['waypoint_start']>38:raise RuntimeError('Blocked waypoint '+str(target)+' at '+str(q))
            p.add_movement_input(V((dx/d,dy/d,0)),1,False)
            pc.set_control_rotation(unreal.Rotator(pitch=-6,yaw=math.degrees(math.atan2(dy,dx)),roll=0))
            if time.monotonic()-S['last_record']>1:
                S['last_record']=time.monotonic();S['position']=[q.x,q.y,q.z];S['speed']=p.get_velocity().length();write()
    except Exception:
        S['error']=traceback.format_exc();write();unreal.log_error(S['error']);unreal.unregister_slate_post_tick_callback(S['handle'])
S['handle']=unreal.register_slate_post_tick_callback(step)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
