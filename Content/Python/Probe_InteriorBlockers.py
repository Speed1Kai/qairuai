import unreal,os,json,re,math
P=os.path.abspath(unreal.Paths.project_dir());test=json.load(open(os.path.join(P,'Saved/all_interiors_walk.json')))
w=unreal.EditorLevelLibrary.get_game_world();r={}
p=unreal.GameplayStatics.get_player_character(w,0)
cap=p.get_component_by_class(unreal.CapsuleComponent);r['capsule']=[cap.get_scaled_capsule_radius(),cap.get_scaled_capsule_half_height()]
def V(p):return unreal.Vector(x=p[0],y=p[1],z=p[2])
for row in test['results']:
    if row['passed']:continue
    m=re.search(r'Blocked at (\[.*?\]) toward (\[.*?\])',row['error'])
    if not m:continue
    a=json.loads(m[1]);b=json.loads(m[2]);d=math.hypot(b[0]-a[0],b[1]-a[1]);dx=(b[0]-a[0])/d;dy=(b[1]-a[1])/d
    rays=[]
    for h in (-90,-50,0,50,90):
        hit=unreal.SystemLibrary.line_trace_single(w,V((a[0]-dx*60,a[1]-dy*60,a[2]+h)),V((a[0]+dx*220,a[1]+dy*220,a[2]+h)),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[p],unreal.DrawDebugTrace.NONE,False);rays.append(hit.export_text() if hit else "clear")
    r[row['id']]=rays
    hit=unreal.SystemLibrary.capsule_trace_single(w,V((a[0]-dx*60,a[1]-dy*60,a[2])),V((a[0]+dx*150,a[1]+dy*150,a[2]+25)),44.,105.,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[p],unreal.DrawDebugTrace.NONE,False)
    r[row['id']+'_capsule']=hit.export_text() if hit else 'clear'
json.dump(r,open(os.path.join(P,'Saved/interior_blockers.json'),'w'),indent=2)

