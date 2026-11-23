"""Build pedestrian navigation in the campaign HUD. Geometry is in Unreal centimetres."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal
from Install_OmegaNavigation import Nav, PLAYER, WHITE, CYAN, MUTED, AMBER, vector
from Install_OmegaDiagnostics import after_branch
from Install_StoryMemory import A, B, compile_bp, defaults, link, load, save, var

BASE = Path(__file__).resolve().parent
PROJECT = Path(unreal.Paths.project_dir()).resolve()
INF = 100000000.
ZERO = vector(0., 0., 0.)
PREFIX = "CityWalk"


class Street(Nav):
    def read(self, name):
        return self.get(PREFIX + name)

    def put(self, name, value):
        return self.set(PREFIX + name, value)

    def item(self, key, index):
        return self.out(self.call("Engine.KismetArrayLibrary.Array_Get",
                                  TargetArray=self.read(key), Index=index), "Item")

    def arr(self, method, key, **kw):
        return self.do(self.call("Engine.KismetArrayLibrary.Array_" + method,
                                 TargetArray=self.read(key), **kw))

    def assign(self, key, index, item):
        self.arr("Set", key, Index=index, Item=item, bSizeToFit=False)

    def length(self, key):
        return self.out(self.arr("Length", key))

    def point(self, index):
        return self.item("Nodes", index)

    def dist(self, a, b):
        return self.math("Vector_Distance", V1=a, V2=b)

    def inc(self, key):
        return self.put(key, self.math("Add_IntInt", A=self.read(key), B=1))

    def ilt(self, a, b):
        return self.math("Less_IntInt", A=a, B=b)

    def eq(self, a, b):
        return self.math("EqualEqual_IntInt", A=a, B=b)

    def either(self, a, b):
        return self.math("BooleanOR", A=a, B=b)

    def repeat(self, condition, body):
        loop = self.branch(condition)
        body()
        link(self.cursor, loop.find_execute_pin())
        self.cursor = loop.find_else_pin()

    def each(self, counter, begin, end, body):
        self.put(counter, begin)
        def iteration():
            body(self.read(counter))
            self.inc(counter)
        self.repeat(self.ilt(self.read(counter), end), iteration)

    def run(self, name):
        self.do(self.own(PREFIX + name))

    def stroke(self, a, b, tint, weight):
        x1, y1 = self.project(a)
        x2, y2 = self.project(b)
        self.do(self.call("Engine.HUD.DrawLine", target=self.get("NavCanvas"), StartScreenX=x1,
                          StartScreenY=y1, EndScreenX=x2, EndScreenY=y2,
                          LineColor=tint, LineThickness=self.scaled(weight)))

    def project(self, point):
        x,y,_ = self.split(point)
        dx=self.number("Multiply",self.number("Subtract",x,self.read("MidX")),self.read("Zoom"))
        dy=self.number("Multiply",self.number("Subtract",self.read("MidY"),y),self.read("Zoom"))
        return self.offset(self.read("PanelX"),self.number("Add",280.,dx)), self.offset(self.read("PanelY"),self.number("Add",183.,dy))

    def bounded(self, point):
        x,y,_=self.split(point)
        return self.both(self.range_test(x,self.read("Left"),self.read("Right")),self.range_test(y,self.read("Bottom"),self.read("Top")))


def install_snap(bp):
    g = Street(bp, PREFIX + "Snap")
    g.put("Near", INF)
    def edge(i):
        a, b = g.item("EdgeA", i), g.item("EdgeB", i)
        closest = g.math("FindClosestPointOnSegment", Point=g.read("Query"),
                         SegmentStart=g.point(a), SegmentEnd=g.point(b))
        d = g.dist(g.read("Query"), closest)
        def take():
            g.put("Near", d)
            g.put("SnapA", a)
            g.put("SnapB", b)
            g.put("Snapped", closest)
        after_branch(g, g.number("Less", d, g.read("Near")), take)
    g.each("I", 0, g.length("EdgeA"), edge)


def install_search(bp):
    g = Street(bp, PREFIX + "Search")
    g.put("Valid", False)
    g.arr("Clear", "Trail")
    g.arr("Clear", "Open")
    g.put("Best", INF)
    g.put("EndNode", -1)
    g.put("Query", g.read("Origin"))
    g.run("Snap")
    g.branch(g.number("LessEqual", g.read("Near"), 1500.))
    for dest, source in (("StartA","SnapA"),("StartB","SnapB"),("From","Snapped")):
        g.put(dest, g.read(source))
    g.put("Query", g.read("Target"))
    g.run("Snap")
    g.branch(g.number("LessEqual", g.read("Near"), 1500.))
    g.put("To", g.read("Snapped"))
    g.put("Cost", g.read("EmptyCost"))
    g.put("Parent", g.read("EmptyParent"))
    for key in ("StartA","StartB"):
        index=g.read(key)
        g.assign("Cost",index,g.dist(g.point(index),g.read("From")))
        g.arr("AddUnique","Open",NewItem=index)
    same=g.both(g.eq(g.read("StartA"),g.read("SnapA")),g.eq(g.read("StartB"),g.read("SnapB")))
    after_branch(g,same,lambda: g.put("Best",g.dist(g.read("From"),g.read("To"))))
    g.put("Expanded", 0)
    def step():
        g.put("BestScore", INF)
        def consider(i):
            node=g.item("Open",i)
            score=g.number("Add",g.item("Cost",node),g.dist(g.point(node),g.read("To")))
            def take():
                g.put("BestScore",score)
                g.put("OpenIndex",i)
                g.put("Current",node)
            after_branch(g,g.number("Less",score,g.read("BestScore")),take)
        g.each("Scan",0,g.length("Open"),consider)
        def expand():
            g.arr("Remove","Open",IndexToRemove=g.read("OpenIndex"))
            g.inc("Expanded")
            node=g.read("Current")
            goal=g.either(g.eq(node,g.read("SnapA")),g.eq(node,g.read("SnapB")))
            def finish():
                g.put("Best",g.read("BestScore"))
                g.put("EndNode",node)
            after_branch(g,goal,finish)
            def relax(i):
                n=g.item("Adj",i)
                candidate=g.number("Add",g.item("Cost",node),g.dist(g.point(node),g.point(n)))
                def improve():
                    g.assign("Cost",n,candidate)
                    g.assign("Parent",n,node)
                    g.arr("AddUnique","Open",NewItem=n)
                after_branch(g,g.number("Less",candidate,g.item("Cost",n)),improve)
            g.each("Neighbor",g.item("Offsets",node),g.item("Offsets",g.math("Add_IntInt",A=node,B=1)),relax)
        choose=g.branch(g.number("Less",g.read("BestScore"),g.read("Best")))
        expand()
        join=g.node(g.e.add_branch_node())
        from Industrial_Common import pin, val
        val(pin(join,"Condition"),True)
        link(g.cursor,join.find_execute_pin())
        g.cursor=choose.find_else_pin()
        g.arr("Clear","Open")
        link(g.cursor,join.find_execute_pin())
        g.cursor=join.find_then_pin()
    g.repeat(g.ilt(0,g.length("Open")),step)
    g.branch(g.number("Less",g.read("Best"),INF))
    g.arr("Add","Trail",NewItem=g.read("To"))
    g.put("Current",g.read("EndNode"))
    def backtrack():
        g.arr("Add","Trail",NewItem=g.point(g.read("Current")))
        g.put("Current",g.item("Parent",g.read("Current")))
    g.repeat(g.ilt(-1,g.read("Current")),backtrack)
    g.arr("Add","Trail",NewItem=g.read("From"))
    g.put("Valid",True)


def bounds(bp):
    g=Street(bp,PREFIX+"Bounds")
    x,y,_=g.split(g.read("Origin"))
    for field,value in (("MinX",x),("MaxX",x),("MinY",y),("MaxY",y)):
        g.put(field,value)
    def include(i):
        x,y,_=g.split(g.item("Trail",i))
        for axis,point in (("X",x),("Y",y)):
            for kind in ("Min","Max"):
                key=kind+axis
                g.put(key,g.math("F"+kind,A=g.read(key),B=point))
    g.each("I",0,g.length("Trail"),include)
    for axis in "XY":
        g.put("Mid"+axis,g.number("Multiply",.5,g.number("Add",g.read("Min"+axis),g.read("Max"+axis))))
    def fit(axis,screen):
        span=g.math("FMax",A=2300.,B=g.number("Subtract",g.read("Max"+axis),g.read("Min"+axis)))
        return g.number("Divide",screen,span)
    g.put("Zoom",g.math("FMin",A=fit("X",450.),B=fit("Y",212.)))
    for low,high,axis,extent in (("Left","Right","X",256.),("Bottom","Top","Y",116.)):
        half=g.number("Divide",extent,g.read("Zoom"))
        g.put(low,g.number("Subtract",g.read("Mid"+axis),half))
        g.put(high,g.number("Add",g.read("Mid"+axis),half))


def controls(bp, pois):
    count=len(pois)+1
    g=Street(bp,"Nav_ToggleMap")
    g.branch(g.inverse(g.get("NavMDown")))
    g.set("NavMDown",True)
    g.input_enabled()
    g.branch(g.either(g.get("NavMemoryReady"),g.get("DemoReachedSurface")))
    g.set("NavMapOpen",g.inverse(g.get("NavMapOpen")))
    g=Street(bp,"Nav_SelectNext")
    g.branch(g.inverse(g.get("NavNDown")))
    g.set("NavNDown",True)
    g.input_enabled()
    g.branch(g.get("NavMapOpen"))
    g.put("Choice",g.math("Percent_IntInt",A=g.math("Add_IntInt",A=g.read("Choice"),B=1),B=count))
    g=Street(bp,PREFIX+"Choose")
    for i,(name,node) in enumerate(pois,1):
        branch=g.branch(g.eq(g.read("Choice"),i))
        g.put("Target",g.point(node))
        g.put("Caption",name)
        g.cursor=branch.find_else_pin()
    g.put("Target",g.get("NavGoal"))
    g.put("Caption","Цель задания")


def render(bp):
    g=Street(bp,"Nav_DrawCityMap")
    accessible=g.either(g.get("DemoReachedSurface"),g.get("NavMemoryReady"))
    g.branch(accessible)
    opened=g.branch(g.get("NavMapOpen"))
    # Before the memory repair, the existing HUD only shows the tutorial objective.
    g.cursor=opened.find_else_pin()
    g.branch(g.inverse(g.get("NavMemoryReady")))
    g.text("M   Карта улиц",g.scaled(32.),g.scaled(23.),CYAN,.83)
    g.cursor=opened.find_then_pin()
    g.run("Choose")
    changed=g.either(g.inverse(g.read("Cached")),g.either(
        g.number("Greater",g.dist(g.read("Target"),g.read("LastTarget")),1.),
        g.number("Greater",g.dist(g.position(),g.read("Origin")),110.)))
    def refresh():
        g.put("Cached",True)
        g.put("Origin",g.position())
        g.put("LastTarget",g.read("Target"))
        g.run("Search")
        g.run("Bounds")
    after_branch(g,changed,refresh)
    g.put("PanelX",g.offset(g.number("Multiply",g.get("NavWidth"),.5),-280.))
    g.put("PanelY",g.offset(g.number("Multiply",g.get("NavHeight"),.5),-195.))
    px=lambda x:g.offset(g.read("PanelX"),x)
    py=lambda y:g.offset(g.read("PanelY"),y)
    g.rectangle(px(0.),py(0.),g.scaled(560.),g.scaled(390.),"(R=.009,G=.022,B=.030,A=.98)")
    g.rectangle(px(0.),py(0.),g.scaled(560.),g.scaled(2.),CYAN)
    g.text("КАРТА ПЕШИХ МАРШРУТОВ",px(18.),py(12.),WHITE,1.03)
    g.text("M   закрыть       N   сменить цель",px(18.),py(38.),MUTED,.86)
    g.rectangle(px(12.),py(66.),g.scaled(536.),g.scaled(240.),"(R=.02,G=.05,B=.06,A=1)")
    g.text("С ↑",px(502.),py(73.),MUTED,.78)
    g.text(g.concat("Куда:  ",g.read("Caption")),px(18.),py(319.),AMBER,1.)
    valid=g.branch(g.read("Valid"))
    def street(i):
        a=g.point(g.item("EdgeA",i))
        b=g.point(g.item("EdgeB",i))
        after_branch(g,g.both(g.bounded(a),g.bounded(b)),lambda:g.stroke(a,b,"(R=.21,G=.33,B=.37,A=1)",1.7))
    g.each("I",0,g.length("EdgeA"),street)
    def leg(i):
        previous=g.math("Subtract_IntInt",A=i,B=1)
        g.stroke(g.item("Trail",previous),g.item("Trail",i),"(R=.17,G=.86,B=.93,A=1)",3.)
    g.each("I",1,g.length("Trail"),leg)
    for key,col,size in (("To",AMBER,11.),("From",WHITE,7.)):
        x,y=g.project(g.read(key))
        g.rectangle(g.offset(x,-size/2),g.offset(y,-size/2),g.scaled(size),g.scaled(size),col)
    g.text(g.concat("По улицам:  ",g.metres(g.read("Best"))," м"),px(18.),py(353.),CYAN,.94)
    g.text("Белая точка — вы     Жёлтая — цель",px(257.),py(355.),MUTED,.79)
    g.cursor=valid.find_else_pin()
    g.text("Пеший маршрут недоступен",px(55.),py(144.),WHITE,1.10)
    g.text("Вы или цель вне сети разведанных улиц.",px(55.),py(182.),MUTED,.96)
    g.text("N   выбрать другую цель",px(18.),py(353.),CYAN,.90)


def install(data_path=None):
    data=json.loads(Path(data_path or PROJECT/"Saved/CityStreetGuide/CityWalkGraph.json").read_text(encoding="utf-8-sig"))
    nodes=data["nodes"]; edges=data["edges"]
    stops=("Вход в убежище 07","Станция 07 · вход","Телефонная станция","Рынок 04","Выход из лаборатории")
    pois=[(name,data["pois"][name]) for name in stops]
    assert len(nodes)>2 and all(0<=i<len(nodes) for edge in edges for i in edge)
    assert all(0<=idx<len(nodes) for _,idx in pois)
    dirty={pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert PLAYER not in dirty, dirty
    name=Path("Content")/(PLAYER[6:]+".uasset")
    backup=PROJECT/"Saved/Backups/CityStreetGuide"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")/name
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(PROJECT/name,backup)
    bp=load(PLAYER)
    vtype=B.get_struct_type(unreal.Vector.static_struct())
    for kind,names,initial in (
        ("bool","Valid Cached","false"),("string","Caption",""),
        ("int","Choice I Scan Neighbor StartA StartB SnapA SnapB OpenIndex Current EndNode Expanded","0"),
        ("real","Near Best BestScore PanelX PanelY MinX MinY MaxX MaxY MidX MidY Zoom Left Right Top Bottom","0"),
        (vtype,"Query Snapped From To Origin Target LastTarget",ZERO)):
        for n in names.split():
            var(bp,PREFIX+n,kind,initial)
    arrays=((vtype,"Nodes Trail"),("int","EdgeA EdgeB Offsets Adj EmptyParent Parent Open"),("real","Cost EmptyCost"))
    for kind,names in arrays:
        typ=B.get_basic_type_by_name(kind) if isinstance(kind,str) else kind
        for n in names.split():
            var(bp,PREFIX+n,B.get_array_type(typ),"()")
    for fn in ("Search","Snap","Bounds","Choose"):
        Street(bp,PREFIX+fn)
    compile_bp(bp)
    install_snap(bp); install_search(bp); bounds(bp); controls(bp,pois); render(bp)
    compile_bp(bp)
    adjacency=[[] for _ in nodes]
    for a,b in edges:
        adjacency[a].append(b); adjacency[b].append(a)
    offsets=[0]
    for neighbours in adjacency:
        offsets.append(offsets[-1]+len(neighbours))
    values={"Nodes":[unreal.Vector(*p) for p in nodes],"EdgeA":[a for a,b in edges],"EdgeB":[b for a,b in edges],
            "Offsets":offsets,"Adj":[v for row in adjacency for v in row],"EmptyParent":[-1]*len(nodes),"EmptyCost":[INF]*len(nodes)}
    cdo=defaults(bp)
    for key,value in values.items():
        cdo.set_editor_property(PREFIX+key,value)
        assert len(cdo.get_editor_property(PREFIX+key))==len(value),key
    bp.modify()
    save(bp)
    return {"passed":True,"backup":str(backup),"nodes":len(nodes),"edges":len(edges),"pois":dict(pois)}


