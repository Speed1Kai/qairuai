"""Check the game graph against Dijkstra and exercise routing between street positions."""
from collections import defaultdict
from pathlib import Path
from math import dist, hypot, inf, isclose
import heapq
import json

ROOT = Path(__file__).resolve().parent

def adjacency(nodes, edges):
    paths = defaultdict(dict)
    for a,b in edges:
        assert a!=b and b not in paths[a]
        w=dist(nodes[a],nodes[b])
        paths[a][b]=paths[b][a]=w
    return paths

def search(nodes, graph, start, goal, astar=True, excluded=()):
    """Shortest metres are calibrated from Unreal's centimetres. No straight-line fallback."""
    def h(n):
        return dist(nodes[n],nodes[goal]) if astar else 0.
    visited={}
    best={start:0.}
    fringe=[(h(start),0.,start)]
    prev={}
    blocked=set(excluded)
    while fringe:
        _,g,u=heapq.heappop(fringe)
        if g!=best[u] or u in visited:continue
        visited[u]=g
        if u==goal:
            path=[goal]
            while path[-1]!=start:path.append(prev[path[-1]])
            return path[::-1],g
        for v,w in graph[u].items():
            if tuple(sorted((u,v))) in blocked:continue
            ng=g+w
            if ng<best.get(v,inf):
                best[v]=ng
                prev[v]=u
                heapq.heappush(fringe,(ng+h(v),ng,v))
    return [],inf

def closest_segment(nodes,edges,point,max_planar=450,max_vertical=130):
    """Return a projected street position. Tracing the player connector belongs in Unreal."""
    nearest=None
    for a,b in edges:
        x0,y0,z0=nodes[a];x1,y1,z1=nodes[b]
        dx,dy=x1-x0,y1-y0
        t=max(0,min(1,((point[0]-x0)*dx+(point[1]-y0)*dy)/(dx*dx+dy*dy or 1)))
        p=(x0+t*dx,y0+t*dy,z0+t*(z1-z0))
        gap=hypot(point[0]-p[0],point[1]-p[1])
        if gap>max_planar or abs(point[2]-p[2])>max_vertical:continue
        record=(gap,a,b,t,p)
        if nearest is None or record<nearest:nearest=record
    return nearest

def route_from_position(nodes, edges, position, target, max_planar=450, max_vertical=130):
    snap=closest_segment(nodes,edges,position,max_planar,max_vertical)
    if snap is None:return [],inf
    gap,a,b,t,p=snap
    n=len(nodes)
    ns=[*nodes,p]
    ed=[tuple(e) for e in edges if tuple(e)!=(a,b)]+[(a,n),(n,b)]
    path,cost=search(ns,adjacency(ns,ed),n,target)
    return [position]+[ns[i] for i in path],cost+dist(position,p) if path else inf

def run():
    data=json.loads((ROOT/'CityWalkGraph.json').read_text(encoding='utf-8'))
    nodes=data['nodes'];edges=data['edges'];poi=data['pois']
    g=adjacency(nodes,edges)
    assert len(g)==len(nodes)
    for i in range(len(nodes)):
        for j in range(i,len(nodes)):
            pa,da=search(nodes,g,i,j)
            pd,dd=search(nodes,g,i,j,False)
            assert pa and pd and isclose(da,dd,abs_tol=1e-5),(i,j)
    def near(x,y):
        return min(range(len(nodes)),key=lambda i:hypot(nodes[i][0]-x,nodes[i][1]-y))
    a,b=near(13014,46100),near(14538,50420)
    easier,normal=search(nodes,g,a,b)
    detours=[]
    for u,v in zip(easier,easier[1:]):
        alternative,length=search(nodes,g,a,b,True,[(min(u,v),max(u,v))])
        if alternative and length>normal+200:detours.append((length,(u,v),alternative))
    assert detours,(a,b,easier)
    alt,blocked,alt_path=min(detours)
    straight_pair=(poi['Передатчик станции 07'],poi['Вход в убежище 07'])
    route,length=search(nodes,g,*straight_pair)
    disconnected=route_from_position(nodes,edges,(0,0,-100),b)
    assert disconnected==([],inf)
    for edge in [(a,easier[1]),(route[0],route[1])]:
        midpoint=tuple((q+r)*.5 for q,r in zip(nodes[edge[0]],nodes[edge[1]]))
        selected,cost=route_from_position(nodes,edges,midpoint,edge[1])
        assert isclose(cost,dist(midpoint,nodes[edge[1]]),abs_tol=.01)
    report={'passed':True,'pairs_checked':len(nodes)*(len(nodes)+1)//2,'cycle_rank':len(edges)-len(nodes)+1,
            'metric':'3D Euclidean lengths along traversed wired walking segments, cm; divide by 100 for metres',
            'market':{'start':a,'start_xyz':nodes[a],'end':b,'end_xyz':nodes[b],'short_m':round(normal/100,2),'alternate_m':round(alt/100,2),
                      'short_path':easier,'alternate_path':alt_path,'block_edge_for_test':blocked},
            'station_to_hatch':{'start':route[0],'end':route[-1],'start_xyz':nodes[route[0]],'end_xyz':nodes[route[-1]],'m':round(length/100,2),'path':route},
            'offgraph_player_rejected':True,'segment_midpoints_checked':True,'pois':poi}
    (ROOT/'CityWalkReferenceCheck.json').write_text(json.dumps(report,indent=1,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='pois'},ensure_ascii=False))
if __name__=='__main__':run()

