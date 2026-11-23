"""PIE traversal of each building entrance and every new staircase.
Relocates only the temporary test pawn between buildings, never saves its spawn.
"""
import unreal,time,math,json,os,traceback
P=os.path.abspath(unreal.Paths.project_dir());cfg=json.load(open(os.path.join(P,'Saved/all_campus_interiors.json'),encoding='utf-8'))
S={'start':time.monotonic(),'stage':'wait','passed':False,'results':[],'index':0,'point':0};out=os.path.join(P,'Saved/all_interiors_walk.json')
cases=[]
def flights(cx,cy,z,levels,rise=400):
    points=[]
    for floor in range(levels-1):
        base=z+floor*rise
        points.extend([(cx-300,cy-140,base+110),(cx+100,cy-140,base+rise/2+100),(cx+180,cy-140,base+rise/2+110),(cx+180,cy+140,base+rise/2+110),(cx-270,cy+140,base+rise+110),(cx-300,cy+140,base+rise+110),(cx-300,cy-140,base+rise+110)])
    return points
for b in cfg['buildings']:
    ident=b['id']
    if ident=='A_UPPER':continue
    cx,cy=b['stair_centre'] if b.get('stair_centre') else ((b['bounds'][0]+b['bounds'][1])/2,(b['bounds'][2]+b['bounds'][3])/2)
    entry=b['entry'][0] if ident=='MAIN' else b['entry'];ex,ey=entry
    if ident=='MAIN':start=(ex,ey-220,2260);pts=[(ex,ey+200,2260),(5850,cy-360,2260),(cx-300,cy-360,2260),(cx-300,cy-140,2260)]
    elif ident=='A_N':start=(ex,ey+220,2260);pts=[(ex,ey-180,2260),(ex,cy-360,2260),(cx-300,cy-360,2260),(cx-300,cy-140,2260)]
    else:
        side=1 if ident in ('G','D') else -1
        start=(ex+side*220,ey,2260);pts=[(ex-side*200,ey,2260)]
        if b.get('stair_centre'):pts.extend([(cx,ey,2260),(cx,cy-360,2260),(cx-300,cy-360,2260),(cx-300,cy-140,2260)])
        else:pts.append((cx,ey,2260))
    if b.get('stair_centre'):pts+=flights(cx,cy,2150,b['floors'])
    cases.append({'id':ident,'start':start,'points':pts})
cases.append({'id':'A_UPPER','start':(6280,600,2260),'points':[(6450,600,2260),(6700,600,2260),(6700,460,2260)]+flights(7000,600,2150,2,480)+flights(7000,600,2630,2,400)+[(6450,600,3140),(6200,600,3140)]})
def V(p):return unreal.Vector(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def write():json.dump({k:v for k,v in S.items() if k not in ('handle','pawn')},open(out,'w'),indent=2)
def step(dt):
    try:
        now=time.monotonic();w=unreal.EditorLevelLibrary.get_game_world()
        if not w:return
        p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
        if not p or not pc:return
        if S['stage']=='wait':
            if now-S['start']<24:return
            p.set_actor_location(V((5850,1070,2260)),False,True);pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0);S['stage']='stream'
        if S['stage']=='stream':
            if not any(a.get_class().get_name()=='BP_CampusInteriors_C' for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)):return
            S['stage']='next'
        if S['stage']=='next':
            if S['index']>=len(cases):S.update(stage='passed',passed=all(x['passed'] for x in S['results']));write();unreal.unregister_slate_post_tick_callback(S['handle']);return
            c=cases[S['index']];p.set_actor_location(V(c['start']),False,True);p.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately();S.update(stage='walking',point=0,since=now,case=c['id'],reached=0);write();return
        c=cases[S['index']];x,y,z=c['points'][S['point']];q=p.get_actor_location();dx=x-q.x;dy=y-q.y;d=math.hypot(dx,dy)
        if d<28:
            # Vertical sanity stops a false success after falling through a hole.
            if abs(q.z-z)>105:raise RuntimeError('Wrong floor '+str([q.x,q.y,q.z])+' expected '+str([x,y,z]))
            S['point']+=1;S['since']=now;S['reached']+=1;write()
            if S['point']>=len(c['points']):S['results'].append({'id':c['id'],'passed':True,'waypoints':S['reached'],'last_position':[q.x,q.y,q.z]});S['index']+=1;S['stage']='next';write()
            return
        if now-S['since']>40:raise RuntimeError('Blocked at '+str([q.x,q.y,q.z])+' toward '+str([x,y,z]))
        p.add_movement_input(V((dx/d,dy/d,0)),1,True);pc.set_control_rotation(unreal.Rotator(pitch=-12,yaw=math.degrees(math.atan2(dy,dx))))
        if now-S.get('last',0)>1:S.update(last=now,position=[q.x,q.y,q.z],target=[x,y,z]);write()
    except Exception:
        S['results'].append({'id':S.get('case'),'passed':False,'point':S.get('point'),'error':traceback.format_exc()});S['index']+=1;S['stage']='next';write()
S['handle']=unreal.register_slate_post_tick_callback(step)
if unreal.EditorLevelLibrary.get_game_world():S['start']-=24
else:unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
