"""Populate surveyed frontage strips and close service yards on the first city route."""
from pathlib import Path
from datetime import datetime
from functools import lru_cache
import json
import math
import shutil
import unreal
from Industrial_Common import A,B,compile_bp,save
from Build_RuinedUrbanCampus import LEVEL,OFFSET,Site,actors,levels,local
from Build_KlenStreet import asset,WEST,FINISH,FLOOR
from SurfacePolish_Materials import import_file,sample,DX,MASKS
from Build_RiverForest import expr,output,persist

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SRC=PROJECT/'SourceAssets/CityFrontages'
ROOT='/Game/Environment/CityFrontages'
BP=ROOT+'/BP_StreetBlocks'
LABEL='CITY_StreetBlocks'
OUT=PROJECT/'Saved/CityFrontage20'
DIMS={'CourtFlats':(1740,1060),'Dressmakers':(1240,880),'PictureHouse':(2120,1240),
      'PrintHouse':(1240,880),'CornerDispensary':(1240,880),'TelephoneExchange':(1700,1010),'TramWorks':(2180,1120),'VerandaHouse':(1540,920)}
SIGNS=('Cinema','Exchange','Sewing','Tram','Gate','Books','Bread','Ceramics','Tickets','Playbill','Printer','Clinic')
# axis, frontage coordinate, intervals between cross streets and entrances, street-to-lot normal.
STREETS=[
 ('Klen','y',5850,1435,[(30300,35130),(40570,45160),(47015,48300)]),
 ('MarketRoad','y',15500,1150,[(55970,57880),(60020,67000),(69170,77020)]),
 ('MarketLink','x',46100,1100,[(7410,13020)]),
 ('MarketEntry','y',14700,1030,[(47300,48400)]),
 ('StationCross','x',78300,1160,[(16770,32120)]),
 ('StationLane','y',33400,1100,[(79600,83450)])]
REGULAR=('CourtFlats','VerandaHouse','Dressmakers')
PRIORITY=[('StationCross',1,22400,'PictureHouse'),('StationCross',-1,24670,'TramWorks'),
          ('MarketRoad',-1,61950,'Dressmakers'),('StationLane',-1,81950,'TelephoneExchange'),
          ('Klen',-1,44150,'VerandaHouse'),('Klen',1,42900,'CourtFlats')]
GATES=[('MarketRoad',58950,-1),('MarketRoad',58950,1),('MarketRoad',68100,1),('MarketRoad',68100,-1)]
def material(name):
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
def prepare(world,reimport=False):
    brick=ROOT+'/M_SalvagedBrick'
    if not A.does_asset_exist(brick):
        mat=material('M_SalvagedBrick')
        uv=expr(mat,'TextureCoordinate',u_tiling=8/3,v_tiling=8/3)
        for role,channel,sampler in [('Diffuse','BASE_COLOR',None),('nor_dx','NORMAL',DX),('Rough','ROUGHNESS',MASKS)]:
            tex=import_file(SRC/('brick_wall_001_'+role+'_1k.jpg'),ROOT)
            tex.set_editor_property('srgb',role=='Diffuse')
            if sampler:tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='nor_dx' else unreal.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property('max_texture_size',1024);save(tex)
            node=sample(mat,tex,sampler,uv)
            output(node,channel,'R' if role=='Rough' else 'RGB')
        unreal.MaterialEditingLibrary.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        persist(mat)
    fab='/Game/Downtown_West/Materials/Buildings_Shared/MI_Building_'
    slots={'Brick':brick,'Ochre':fab+'SandstoneRed_WS','Limestone':fab+'SandstoneWhite_WS','Plaster':fab+'Stucco',
           'Paint':fab+'Wood_Trim_darkerGreen','Wood':fab+'Wood_Trim_Brown','Bronze':FINISH+'ColossusOchre',
           'Iron':FINISH+'Frame','Steel':FINISH+'InfillSteel','Pane':'/Game/CityDowntown/Materials/Windows/MI_windowsFakeInterior03',
           'Presswork':'/Game/CityDowntown/Materials/Windows/MI_windowsFakeInteriorNoCurtain3',
           'Shop':'/Game/CityDowntown/Materials/Windows/MI_ShopWindowsFakeInterior3',
           'WarmPane':'/Game/CityDowntown/Materials/Windows/MI_windowsFakeInterior04','Lamp':FINISH+'StationWarm','Blind':FINISH+'StationPaper',
           'RoofTile':fab+'Wood_Trim_DarkGrey','TileBand':fab+'Wood_Trim_Blue','Tar':FLOOR+'Asphalt'}
    opts=unreal.FbxImportUI()
    for k,v in dict(automated_import_should_detect_type=False,import_materials=False,import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():opts.set_editor_property(k,v)
    opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
    opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    for kind in (*DIMS,'YardGate'):
        name='SM_'+kind
        existed=A.does_asset_exist(ROOT+'/'+name)
        if existed and not reimport:continue
        if reimport and existed(ROOT+'/'+name):
            task=unreal.AssetImportTask()
            for key,value in dict(filename=str(SRC/(name+'.fbx')),destination_path=ROOT,automated=True,replace_existing=True,options=opts,save=False).items():task.set_editor_property(key,value)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=import_file(SRC/(name+'.fbx'),ROOT,opts)
        for i,slot in enumerate(mesh.static_materials):
            key=str(slot.get_editor_property('imported_material_slot_name'))
            choice=slots[key]
            if key=='Shop' and kind in ('PictureHouse','TelephoneExchange','CourtFlats','CornerDispensary','PrintHouse'):
                choice='/Game/CityDowntown/Materials/Windows/MI_windowsFakeInteriorNoCurtain2'
            mesh.set_material(i,asset(choice))
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        save(mesh)
    for name in SIGNS:
        if A.does_asset_exist(ROOT+'/M_'+name):continue
        tex=import_file(SRC/(name+'.png'),ROOT);save(tex)
        mat=material('M_'+name);output(sample(mat,tex),'BASE_COLOR','RGB')
        unreal.MaterialEditingLibrary.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        persist(mat)
def plan(world,ignore):
    parcels=[];boundaries=[];entrances=[]
    @lru_cache(None)
    def roof(x,y):
        h=unreal.SystemLibrary.line_trace_single(world,local(x,y,18000),local(x,y,1760),unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignore,unreal.DrawDebugTrace.NONE,False)
        return h.to_tuple()[5].z+OFFSET[2] if h and h.to_tuple()[0] else 0
    for district,axis,center,offset,spans in STREETS:
        for side in (-1,1):
            face=center+side*offset
            yaw=(90 if side<0 else -90) if axis=='y' else (180 if side<0 else 0)
            def xy(t,r):return (face+side*r,t) if axis=='y' else (t,face+side*r)
            runs=list(spans)
            if district=='MarketRoad' and side<0:runs=runs[:-1]+[(69170,73300),(73300,77020)]
            for a,b in runs:
                face=center+side*(offset+(735 if district=='MarketRoad' and side<0 and a==73300 else 0))
                choices=[]
                def accept(kind,mid,width,depth):
                    start,end=mid-width/2,mid+width/2
                    if start<a or end>b or any(start<v+15 and end>u-15 for u,v in choices):return False
                    for j in range(math.ceil(width/165)+1):
                        t=start+18+(width-36)*j/math.ceil(width/165)
                        for k in range(math.ceil(depth/170)+1):
                            x,y=xy(t,15+(depth-30)*k/math.ceil(depth/170))
                            if roof(round(x/25)*25,round(y/25)*25)>2395:return False
                    base=max(2152,min(2202,max(roof(*map(round,xy(mid,r))) for r in (0,depth*.5,depth))+.5))
                    x,y=xy(mid,depth/2)
                    parcels.append(dict(district=district,axis=axis,side=side,kind=kind,t=mid,x=x,y=y,z=base,
                                        width=width,depth=depth,face=face,yaw=yaw))
                    choices.append((start,end))
                    return True
                for dis,s,t,kind in PRIORITY:
                    if dis==district and side==s and a<t<b:
                        width,depth=DIMS[kind]
                        for shift in (0,-180,180,-360,360):
                            if accept(kind,t+shift,width,depth):break
                cursor=a+13;idx=0
                while cursor+980<b:
                    kinds=list(REGULAR)
                    if district=='StationCross' and side<0:kinds=['TramWorks','Dressmakers','CourtFlats']
                    if district=='StationLane':kinds=['VerandaHouse','CourtFlats','Dressmakers']
                    sequence=kinds[(idx+int(side>0))%3:]+kinds[:(idx+int(side>0))%3]
                    placed=False
                    for kind in sequence:
                        w,d=DIMS[kind]
                        for scale in (1.0,.86):
                            width=round(w*scale);depth=round(d*(1 if scale==1 else .82))
                            if accept(kind,cursor+width/2,width,depth):
                                cursor+=width+(424 if idx%3==0 else 23);idx+=1;placed=True;break
                        if placed:break
                    if not placed:cursor+=112
                # Close all gaps between the actual buildings and visible boundaries.
                # Existing masonry is sampled at the new frontage. Longer gaps get a
                # brick wall with a recessed working yard gate in its middle.
                edges=sorted(choices)+[(b,b)]
                last=a
                for u,v in edges:
                    if u-last>39:
                        start=None
                        n=math.ceil((u-last)/95)
                        for j in range(n+1):
                            t=last+(j+.5)*(u-last)/n
                            free=j<n and roof(*map(round,xy(t,0)))<2430
                            if free and start is None:start=last+j*(u-last)/n
                            if not free and start is not None:
                                end=last+j*(u-last)/n
                                if end-start>36:boundaries.append(dict(axis=axis,face=face,side=side,a=start,b=end,yaw=yaw,district=district))
                                start=None
                    last=max(last,v)
    return dict(parcels=parcels,boundaries=boundaries)
def layout(site,data):
    cube=asset('/Engine/BasicShapes/Cube');plane=asset('/Engine/BasicShapes/Plane')
    paver=asset(WEST+'ground_walkways/SM_ground_mod_walk_tile_a_4m')
    def box(key,mat,x,y,z,w,d,h,yaw=0,solid=False):
        site.mesh(key,cube,x,y,z+h/2,(w/100,d/100,h/100),yaw=yaw,collide=solid)
        site.batches[key].set_material(0,asset(mat))
    def board(tag,x,y,z,w,h,yaw):
        # A plane facing -Y at yaw 180 follows the same normal as the front wall.
        site.mesh('Sign_'+tag,plane,x,y,z,(w/100,h/100,1),yaw=yaw+180,roll=90)
        site.batches['Sign_'+tag].set_material(0,asset(ROOT+'/M_'+tag))
    def orient(angle,u,v,x,y):
        a=math.radians(angle)
        return x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a)
    def masonry(x,y,yaw,width):
        if width<=1:return
        box('YardBrick','/Game/Downtown_West/Materials/Buildings_Shared/MI_Building_Bricks_A_red_WS',x,y,2138,width,31,276,yaw,True)
        box('Coping','/Game/Downtown_West/Materials/Buildings_Shared/MI_Building_SandstoneWhite_WS',x,y,2414,width+1,40,11,yaw)
        n=max(1,math.ceil(width/340))
        for j in range(n):
            xx,yy=orient(yaw,-width/2+18+j*width/n,0,x,y)
            box('Piers',FINISH+'StationPlaster',xx,yy,2145,39,44,290,yaw,True)
    def gate(x,y,yaw,width):
        site.mesh('YardGate',asset(ROOT+'/SM_YardGate'),x,y,2149,(width/622,1,1),yaw=yaw,collide=True)
        xx,yy=orient(yaw,0,-14,x,y);board('Gate',xx,yy,2250,min(width*.4,145),30,yaw)
    seen={}
    for lot in data['parcels']:
        kind=lot['kind'];w=lot['width'];d=lot['depth'];z=lot['z'];yaw=lot['yaw']
        x,y=lot['x'],lot['y'];sx=w/DIMS[kind][0];sy=d/DIMS[kind][1]
        site.mesh(kind,asset(ROOT+'/SM_'+kind),x,y,z,(sx,sy,1),yaw=yaw,collide=True)
        if kind=='PictureHouse':tag='Cinema'
        elif kind=='TelephoneExchange':tag='Exchange'
        elif kind=='TramWorks':tag='Tram' if not seen.get('Tram') else None
        elif kind=='PrintHouse' and lot['district']=='StationCross' and not seen.get('Printer'):tag='Printer'
        elif kind=='CornerDispensary' and lot['district']=='MarketRoad' and not seen.get('Clinic'):tag='Clinic'
        elif kind=='Dressmakers':tag=next((s for s in ('Sewing','Books','Bread','Ceramics') if not seen.get(s)),None)
        else:tag=None
        if tag:
            seen[tag]=True
            distance=(218 if kind=='PictureHouse' else 30)*sy
            xx,yy=orient(yaw,0,-d/2-distance,x,y)
            board(tag,xx,yy,z+(322 if kind=='PictureHouse' else 318),785 if kind=='PictureHouse' else min(w*.61,475),76 if kind=='PictureHouse' else 70,yaw)
        if kind=='PictureHouse':
            xx,yy=orient(yaw,0,-d/2+263*sy,x,y)
            board('Tickets',xx,yy,z+265,249,46,yaw)
            for delta in (-732,745):
                xx,yy=orient(yaw,delta*sx,-d/2-150*sy,x,y)
                site.fitted('CinemaBenches',asset(WEST+'props/prop_bench_wood/SM_bench_wood_a'),xx,yy,z,(148,51,79),yaw=yaw,collide=True)
            xx,yy=orient(yaw,-889*sx,-d/2-184*sy,x,y)
            site.fitted('LitterBin',asset(WEST+'props/prop_recycle_bin/SM_prop_recycle_bin'),xx,yy,z,(47,44,82),yaw=yaw,collide=True)
            for delta in (-645,645):
                xx,yy=orient(yaw,delta*sx,-d/2+300*sy,x,y)
                box('PlaybillFrame',FINISH+'Frame',xx,yy,z+62,90,12,130,yaw,True)
                xx,yy=orient(yaw,delta*sx,-d/2+292*sy,x,y)
                board('Playbill',xx,yy,z+127,84,124,yaw)
            for delta in (-860,860):
                xx,yy=orient(yaw,delta*sx,-d/2-76*sy,x,y)
                site.fitted('TicketPosters',asset(WEST+'props/prop_store_signs/SM_signs_poster_travel'),xx,yy,z+91,(88,8,124),yaw=yaw)
        width=285 if lot['district']=='Klen' else 305
        n=math.ceil(w/376)
        for j in range(n):
            xx,yy=orient(yaw,(j+.5)*w/n-w/2,-d/2-width/2,x,y)
            site.fitted('Pavement',paver,xx,yy,z-5,(w/n-.2,width,5),yaw=yaw,collide=True)
        if kind in ('PictureHouse','TelephoneExchange') or (kind=='Dressmakers' and tag):
            xx,yy=orient(yaw,-w*.37,-d/2-width+49,x,y)
            site.fitted('Hydrants',asset(WEST+'props/prop_fire_hydrant/SM_fire_hydrant'),xx,yy,z,(48,39,74),yaw=yaw,collide=True)
    for e in data['boundaries']:
        a,b=e['a'],e['b'];width=b-a;side=e['side'];face=e['face'];yaw=e['yaw']
        def at(t,r):return (face+side*r,t) if e['axis']=='y' else (t,face+side*r)
        if width<277:
            masonry(*at((a+b)/2,0),yaw,width+8);continue
        opening=min(568,width)
        for lo,hi in ((a,(a+b-opening)/2),((a+b+opening)/2,b)):
            if hi>lo:masonry(*at((lo+hi)/2,0),yaw,hi-lo+5)
        # Short return walls stop players slipping around a recessed gate.
        for t in ((a+b-opening)/2,(a+b+opening)/2):masonry(*at(t,80),yaw+90,170)
        gx,gy=at((a+b)/2,166)
        gate(gx,gy,yaw,opening+10)
        if opening>360:
            xx,yy=at((a+b)/2,12)
            box('DeliveryAprons',FLOOR+'Asphalt',xx,yy,2151,opening,304,5,yaw,True)
    # Close the far end of minor roads with a delivery entrance and its masonry returns.
    masonry(13982,73300,0,752)
    # The roof survey detected projecting ruins here. Capsule sweeps found openings underneath.
    # Masonry and steel leaves close the openings at street level below the surviving roofs.
    for start,end in ((62665,62885),(62990,63445),(63470,63685),(64910,65605),
                      (73420,73795),(73740,74275),(76060,76435),(76380,77080)):
        wall_width=end-start
        if wall_width>385:gate(16697,(start+end)/2,-90,wall_width)
        else:masonry(16697,(start+end)/2,-90,wall_width)
    gate(10410,47233,0,538)
    portals=[]
    for _,y,side in GATES:
        x=15500+side*1990;yaw=90 if side<0 else -90
        gate(x,y,yaw,600)
        for s in (-1,1):
            masonry(x,y+s*705,yaw,813)
            masonry(x-side*418,y+s*1100,0,854)
        portals.append((x,y,yaw))
    for x,y,yaw in ((13460,78300,90),(15500,85325,180)):
        gate(x,y,yaw,630)
        for sign in (-1,1):
            xx,yy=orient(yaw,sign*730,0,x,y);masonry(xx,yy,yaw,839)
            xx,yy=orient(yaw,sign*1138,-433,x,y);masonry(xx,yy,yaw+90,892)
        portals.append((x,y,yaw))
    # The old tram layover remains long enough for the existing Lynx patrol to turn.
    for x in (14362,16638):
        masonry(x,82082,90,5007)
    # Connect the old tram fence at the two stub mouths to the line of properties.
    masonry(14366,79533,90,205)
    masonry(14301,79432,0,143)
    data['service_gates']=portals
def trim_plants(data):
    count=0
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label()==LABEL:continue
        for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.static_mesh:continue
            name=c.static_mesh.get_name().lower()
            litter='trashbag' in name
            if not litter and not any(s in name for s in ('deadtree','_tree','_shrub','_grass','_fir','_reed','_ivy','_weed','_bush')):continue
            remove=[]
            for i in range(c.get_instance_count()):
                p=c.get_instance_transform(i,True).translation
                x,y=p.x+OFFSET[0],p.y+OFFSET[1]
                if litter:
                    if 21000<x<23800 and 78960<y<79505:remove.append(i)
                    continue
                for lot in data['parcels']:
                    t,r=(y,x) if lot['axis']=='y' else (x,y)
                    if abs(t-lot['t'])<lot['width']/2+24 and -292<(r-lot['face'])*lot['side']<lot['depth']+25:
                        remove.append(i);break
            if remove:
                actor.modify();c.modify()
                for i in reversed(remove):c.remove_instance(i)
                count+=len(remove)
    return count
def install(reimport=False):
    assert not levels.get_dirty_map_packages()
    backup=PROJECT/'Saved/Backups/StreetBlocks'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');backup.mkdir(parents=True)
    for path,ext in [(LEVEL,'.umap'),(BP,'.uasset')]+[(ROOT+'/SM_'+name,'.uasset') for name in (*DIMS,'YardGate')]:
        original=PROJECT/'Content'/(path[6:]+ext)
        if original.exists():shutil.copy2(original,backup/original.name)
    world=levels.load_map(LEVEL);assert world
    existing=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(existing)<=1
    OUT.mkdir(exist_ok=True);report=OUT/'Build.json'
    data=json.loads(report.read_text()) if existing and report.exists() else plan(world,existing)
    # Narrow plots share a party-wall footprint. Alternate their actual architecture along each street.
    narrow=[p for p in data['parcels'] if p['kind'] in ('Dressmakers','CornerDispensary','PrintHouse')]
    for i,lot in enumerate(narrow):
        lot['kind']=('Dressmakers','PrintHouse','CornerDispensary')[i%3]
    assert len(data['parcels'])>=12 and {p['kind'] for p in data['parcels']}==set(DIMS),(len(data['parcels']),{p['kind'] for p in data['parcels']})
    prepare(world,reimport)
    if A.does_asset_exist(BP):bp=asset(BP)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_StreetBlocks',ROOT,unreal.Blueprint,f)
    site=Site(bp);layout(site,data);compile_bp(bp);save(bp)
    if existing:
        for c in existing[0].get_components_by_class(unreal.InstancedStaticMeshComponent):
            t=site.batches.get(c.get_name())
            if t:
                c.modify();c.clear_instances();c.add_instances([t.get_instance_transform(i,False) for i in range(t.get_instance_count())],False,False)
    else:
        actor=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector());actor.set_actor_label(LABEL);actor.set_folder_path('CITY/StreetBlocks')
    data['removed_obstructing_instances']=data.get('removed_obstructing_instances',data.get('removed_plants',0))+trim_plants(data)
    world.modify();assert levels.save_map(world,LEVEL) and levels.load_map(LEVEL)
    found=[a for a in actors.get_all_level_actors() if a.get_actor_label()==LABEL]
    assert len(found)==1
    counts={c.get_name():c.get_instance_count() for c in found[0].get_components_by_class(unreal.InstancedStaticMeshComponent)}
    assert counts.get('Hydrants',0)>0 and counts.get('TicketPosters',0)==2
    assert sum(counts[n] for n in DIMS)==len(data['parcels'])
    data.update(instances=counts,backup=data.get('backup',str(backup)))
    report.write_text(json.dumps(data,indent=2))
    unreal.SystemLibrary.execute_console_command(levels.get_editor_world() if hasattr(levels,'get_editor_world') else unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),'MAP CHECK')
if __name__=='__main__':install()




