"""Walk the real player through the first-floor zones and new automatic doors."""
import unreal,time,os,json,math,traceback
S={'start':time.monotonic(),'stage':'waiting','passed':False,'waypoints':[]};out=os.path.join(unreal.Paths.project_saved_dir(),'first_floor_walk_check.json')
points=[(3300,200),(3300,550),(3450,600),(3750,600),(4030,600),(4030,820),(4510,820),(4510,1050),(4510,820),(4030,820),(4030,-100),(4800,-100),(4800,-550),(4800,-100),(5350,-100),(5850,0),(5850,1050)]
def V(p):return unreal.Vector(x=p[0],y=p[1],z=p[2])
def write():json.dump({k:v for k,v in S.items() if k!='handle'},open(out,'w'),indent=2)
def step(dt):
    try:
        now=time.monotonic();w=unreal.EditorLevelLibrary.get_game_world()
        if not w:return
        p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
        if not p or not pc:return
        if S['stage']=='waiting':
            if now-S['start']<24:return
            p.set_actor_location(V((3300,0,2260)),False,True);pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0)
            S.update(stage='walking',index=0,since=now);write()
        x,y=points[S['index']];q=p.get_actor_location();dx=x-q.x;dy=y-q.y;d=math.hypot(dx,dy)
        if d<45:
            S['waypoints'].append({'target':[x,y],'actual':[q.x,q.y,q.z]});S['index']+=1;S['since']=now;write()
            if S['index']==len(points):S.update(stage='passed',passed=True);write();unreal.unregister_slate_post_tick_callback(S['handle'])
            return
        if now-S['since']>18:raise RuntimeError('Blocked at '+str([q.x,q.y,q.z])+' heading to '+str([x,y]))
        p.add_movement_input(V((dx/d,dy/d,0)),1,True);pc.set_control_rotation(unreal.Rotator(pitch=-8,yaw=math.degrees(math.atan2(dy,dx))))
        if now-S.get('last',0)>1:S.update(last=now,position=[q.x,q.y,q.z]);write()
    except Exception:S.update(stage='failed',error=traceback.format_exc());write();unreal.unregister_slate_post_tick_callback(S['handle'])
S['handle']=unreal.register_slate_post_tick_callback(step)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
