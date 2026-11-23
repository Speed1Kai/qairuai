"""Rebuild the connected exterior from the user's October 26 site plan.
Public native authoring only. Copies affected packages before edits; preserves
the real laboratory, lift and doorway. All new coordinates use one zero-yaw
streaming frame to avoid the former detached-component rotation discrepancies.
"""
import unreal,os,sys,math,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,add,components,compile_bp,save,pin,val,link,Graph
ROOT='/Game/Surface/ReferencePlan';LEVEL='/Game/Surface/Lvl_CampusConnected';MAIN='/Game/Lvl_LabTutorial'
project=os.path.abspath(unreal.Paths.project_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
offset=(10006.289955343997,6612.598659341473,2150.)
backup=os.path.join(project,'Saved/Backups/ReferenceCampus',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True)
r={'saved':False,'backup':backup,'reference':'Gemini_Generated_Image_giy9nqgiy9nqgiy9.jpg','stream_offset':offset,'stream_yaw':0,'plan_scale_cm_per_pixel':12,'buildings':[],'removed_actors':[]}
def V(p):return unreal.Vector(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def W(px,py,z=0):return (5850+(786-py)*12,1500+(px-708)*12,2150+z)
def L(p):return V(tuple(p[i]-offset[i] for i in range(3)))
def back(path,ext='.uasset'):
    src=os.path.join(content,path.removeprefix('/Game/')+ext)
    if os.path.isfile(src):
        dest=os.path.join(backup,path.removeprefix('/Game/')+ext);os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(src,dest)
def asset(name):
    p=ROOT+'/'+name;back(p)
    if A.does_asset_exist(p):return A.load_asset(p)
    f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
def spawn(cls,label,p,yaw=0):
    a=sub.spawn_actor_from_class(cls,L(p),unreal.Rotator(pitch=0,yaw=yaw,roll=0));a.set_actor_label(label);a.set_folder_path('SURFACE/ReferencePlan');return a
try:
    assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE before authoring'
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    for p,ext in [(LEVEL,'.umap'),(MAIN,'.umap'),('/Game/Surface/BP_SurfaceDeparture','.uasset'),('/Game/Surface/BP_SurfaceArrival','.uasset')]:back(p,ext)
    bp=asset('BP_ReferenceCampus')
    root=add(bp,unreal.SceneComponent,'PlanRoot');root.set_mobility(unreal.ComponentMobility.MOVABLE)
    mats={}
    for key,path in {'concrete':'/Game/Surface/Materials/M_RuinConcrete','asphalt':'/Game/Surface/Materials/M_Asphalt','dust':'/Game/Surface/Materials/M_Dust','glass':'/Game/Surface/Materials/M_DeadGlass','wall':'/Game/LabTutorial/FirstFloor/M_LabCeramic','dark':'/Game/LabTutorial/FirstFloor/M_LabGraphite','steel':'/Game/LabTutorial/FirstFloor/M_LabSteel','cyan':'/Game/LabTutorial/FirstFloor/M_LabCyan','amber':'/Game/LabTutorial/FirstFloor/M_LabAmber','floor':'/Game/LabTutorial/FirstFloor/M_LabFloor'}.items():
        mats[key]=A.load_asset(path);assert mats[key],path
    cube=A.load_asset('/Engine/BasicShapes/Cube');cyl=A.load_asset('/Engine/BasicShapes/Cylinder')
    batches={};counts={};signs=[]
    def item(key,mesh,p,scale=(1,1,1),yaw=0,material=None,block=False,roll=0,pitch=0):
        if key not in batches:
            c=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,key,'PlanRoot');c.modify();c.clear_instances();c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.MOVABLE)
            c.set_collision_profile_name('BlockAll' if block else 'NoCollision');c.set_editor_property('cast_shadow',True)
            if material:c.set_material(0,mats[material])
            batches[key]=c;counts[key]=0
        batches[key].add_instance(unreal.Transform(location=L(p),rotation=unreal.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=V(scale)),False);counts[key]+=1
    def box(p,size,mat='concrete',block=False,yaw=0):
        item('Box_'+mat+('_Collision' if block else '_Detail'),cube,p,tuple(v/100. for v in size),yaw,mat,block)
    def pbox(px,py,z,sx,sy,sz,mat='concrete',block=False):
        # sx/sy are dimensions measured along image axes, not engine axes.
        box(W(px,py,z),(sy*12,sx*12,sz),mat,block)
    def rect(x1,y1,x2,y2,z,thick,mat,block=False):pbox((x1+x2)/2,(y1+y2)/2,z,x2-x1,y2-y1,thick,mat,block)
    def segment(a,b,z,width,height,mat='steel',block=False):
        p=W(a[0],a[1],z);q=W(b[0],b[1],z);d=math.hypot(q[0]-p[0],q[1]-p[1]);yaw=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))
        box(tuple((p[i]+q[i])/2 for i in range(3)),(d,width,height),mat,block,yaw)
    def road(points,width=700,mark=True):
        for a,b in zip(points,points[1:]):
            segment(a,b,3,width,6,'asphalt')
            dx=b[0]-a[0];dy=b[1]-a[1];d=math.hypot(dx,dy)*12
            for k in range(1,int(d/420)):
                t=k*420/d;mx=a[0]+dx*t;my=a[1]+dy*t;ll=100/d
                if mark:segment((mx-dx*ll/2,my-dy*ll/2),(mx+dx*ll/2,my+dy*ll/2),7,10,1,'amber')
    def sign(text,px,py,z,yaw=90,size=44):signs.append((text,W(px,py,z),yaw,size))
    def building(label,rects,floors,mat='wall',door=None,existing=False):
        height=floors*400
        r['buildings'].append({'name':label,'floors':floors,'rectangles_px':rects,'height_cm':height})
        for x1,y1,x2,y2 in rects:
            cx=(x1+x2)/2;cy=(y1+y2)/2;w=(x2-x1)*12;d=(y2-y1)*12
            if not existing:pbox(cx,cy,height/2,x2-x1,y2-y1,height,'dark',True)
            pbox(cx,cy,-4,x2-x1+12,y2-y1+12,8,'concrete')
            pbox(cx,cy,height+20,x2-x1+5,y2-y1+5,40,'dark')
            # Four panelled facades, 4m story rhythm and dark recessed glazing.
            center=W(cx,cy)
            for axis,length,depth in [(0,d,w),(1,w,d)]:
                for side in (-1,1):
                    n=max(1,round(length/400));step=length/n
                    for floor in range(2 if existing else 0,floors):
                        for j in range(n):
                            along=-length/2+(j+.5)*step
                            pos=list(center);pos[axis]+=along;pos[1-axis]+=side*(depth/2+3);pos[2]+=floor*400+70
                            dims=[step-4,32,140] if axis==0 else [32,step-4,140]
                            box(pos,dims,mat)
                            pos[2]=2150+floor*400+260;dims=[step-56,18,225] if axis==0 else [18,step-56,225]
                            box(pos,dims,'glass')
                            pos[axis]-=step/2-12;pos[2]=2150+floor*400+212;dims=[24,56,375] if axis==0 else [56,24,375]
                            box(pos,dims,mat)
                    pos=list(center);pos[1-axis]+=side*(depth/2+30);pos[2]+=height-18
                    box(pos,[length+40,65,48] if axis==0 else [65,length+40,48],'steel')
            for k in (-1,1):
                pbox(cx+k*(x2-x1)*.25,cy,height+105,30,36,170,'steel')
                pbox(cx+k*(x2-x1)*.25,cy,height+196,27,33,10,'dark')
        if door:
            px,py,yaw=door
            pbox(px,py,210,30,5,420,'steel')
            pbox(px,py-10,480,82,45,55,'dark')
            pbox(px,py-10,449,74,37,7,'cyan')
            sign(label,px,py-5,650,yaw,48)

    # Ground has a genuine lift aperture. It never bridges over the real shaft.
    x0,x1=-1800,13200;y0,y1=-4500,17800;hx0,hx1=2250,3050;hy0,hy1=-380,380
    for xa,xb,ya,yb in [(x0,hx0,y0,y1),(hx1,x1,y0,y1),(hx0,hx1,y0,hy0),(hx0,hx1,hy1,y1)]:
        box(((xa+xb)/2,(ya+yb)/2,2115),(xb-xa,yb-ya,70),'floor',True)
    # The measured ring road follows the rounded/octagonal central block.
    ring=[(870,786),(870,615),(930,553),(1740,553),(1800,615),(1800,974),(1740,1036),(930,1036),(870,974),(870,786)]
    road(ring,720)
    road([(708,786),(870,786)],650,False)
    road([(1800,786),(2035,786)],1180)
    for pts in [[(1065,553),(1065,473)],[(1438,553),(1438,468)],[(1778,553),(1778,473)],[(1080,1036),(1080,1128)],[(1558,1036),(1558,1128)]]:road(pts,500,False)
    # Clean sidewalks, central open court, and unbroken pedestrian approaches.
    rect(1458,608,1758,1000,6,12,'concrete')
    for a,b in zip(ring,ring[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];d=math.hypot(dx,dy)
        for side in (-1,1):
            nx=-dy/d*side*35;ny=dx/d*side*35
            segment((a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),7,95,14,'concrete')
    # Building A wraps the real interior; upper/south wings supply the T profile.
    # No new collision is placed in the existing shell or across its doorway.
    r['buildings'].append({'name':'КОРПУС А / НАЧАЛЬНАЯ ЛАБОРАТОРИЯ','floors':3,'existing_interior_preserved':True})
    building('А / СЕВЕРНОЕ КРЫЛО',[(458,545,588,721)],3,door=None)
    # This shorter southern wing avoids the working elevator shaft (X2250..3050).
    building('А / ЮЖНОЕ КРЫЛО',[(458,847,588,987)],3,door=None,existing=True)
    # Roof and parapet over the actual first-floor exit, with no extra wall.
    rect(410,721,708,847,1200,45,'dark')
    sign('КОРПУС А / НАЧАЛЬНАЯ ЛАБОРАТОРИЯ',700,786,930,90,50)
    # Seven site buildings exactly follow the plan's identities and story counts.
    building('КОРПУС Б / ОБОРУДОВАНИЕ',[(937,347,1193,473)],4,door=(1065,475,180))
    building('КОРПУС В / ЭНЕРГОБЛОК',[(1325,351,1552,468)],3,door=(1438,470,180))
    building('СКЛАДСКОЙ АНГАР',[(1660,347,1895,473)],1,mat='steel',door=(1778,475,180))
    # Hangar scale and roof vents distinguish it from the research offices.
    rect(1657,344,1898,476,650,40,'steel')
    for py in range(352,473,12):rect(1661,py,1894,py+1,674,5,'dark')
    h=[(1072,720,1454,855),(1029,661,1100,917),(1234,645,1290,931),(1426,661,1496,917),(1100,687,1234,711),(1290,687,1426,711),(1100,866,1234,890),(1290,866,1426,890)]
    building('ГЛАВНЫЙ НАУЧНЫЙ КОРПУС / 5 ЭТАЖЕЙ',h,5,door=None)
    # Eastern entry faces the open court; western entry faces A's arrival route.
    for px,yaw in [(1070,-90),(1498,90)]:
        sign('ГЛАВНЫЙ НАУЧНЫЙ КОРПУС',px,786,1100,yaw,48)
        pbox(px,786,212,5,34,424,'steel')
    building('КОРПУС Г / БИОЛАБОРАТОРИЯ',[(942,1128,1229,1243)],3,door=(1080,1126,0))
    building('КОРПУС Д / ЖИЛОЙ БЛОК',[(1394,1128,1725,1243)],4,door=(1558,1126,0))
    # Services and court furniture stay outside the clear circulation lanes.
    for px in (1540,1670):
        for py in (650,930):
            pbox(px,py,35,52,35,70,'concrete',True)
            pbox(px,py,72,46,29,8,'dust')
    for py in range(630,990,90):
        pbox(1727,py,30,34,7,60,'dark',True)
        pbox(1727,py,65,38,10,10,'steel')
    for px,py in [(905,540),(1770,540),(905,1060),(1770,1060),(770,730),(770,840)]:
        pbox(px,py,225,4,4,450,'steel',True);pbox(px,py,452,25,5,9,'dark');pbox(px,py,447,21,4,3,'cyan')
    # Polygon perimeter and four guard towers. East gate is physically open.
    polygon=[(270,520),(834,255),(1908,255),(2035,380),(2035,1130),(1830,1360),(878,1360),(270,1090),(270,520)]
    wallmesh=A.load_asset('/Game/Surface/CampusWall/SM_Wall_A_Long');bounds=wallmesh.get_bounding_box()
    dz=bounds.max.z-bounds.min.z;dx=bounds.max.x-bounds.min.x;dy=bounds.max.y-bounds.min.y
    def wall_segment(a,b):
        p=W(*a);q=W(*b);length=math.hypot(q[0]-p[0],q[1]-p[1]);count=math.ceil(length/650);yaw=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))
        for i in range(count):
            t=(i+.5)/count;pos=(p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t,2150+bounds.max.z*600/dz)
            item('ImportedConcretePerimeter',wallmesh,pos,((length/count+5)/dx,100/dy,600/dz),yaw,block=True,roll=180)
        # Three stretched barbed strands with periodic diagonal razor clusters.
        for z in (615,644,674):segment(a,b,z,3,3,'steel')
        for i in range(count+1):
            t=i/count;px=a[0]+(b[0]-a[0])*t;py=a[1]+(b[1]-a[1])*t
            pbox(px,py,635,2.5,2.5,130,'steel')
            for z in (630,660):
                box(W(px,py,z),(22,3,3),'steel',False,yaw+40)
                box(W(px,py,z),(22,3,3),'steel',False,yaw-40)
    for a,b in zip(polygon,polygon[1:]):
        if a==(2035,380):wall_segment(a,(2035,725));wall_segment((2035,847),b)
        else:wall_segment(a,b)
    for idx,(px,py) in enumerate([(282,532),(2015,390),(2015,1115),(282,1075)],1):
        pbox(px,py,490,95,95,28,'dark',True)
        pbox(px,py,705,101,101,25,'steel')
        for sx in (-33,33):
            for sy in (-33,33):pbox(px+sx,py+sy,250,5,5,500,'steel',True)
        for sy in (-40,40):pbox(px,py+sy,583,88,4,160,'glass')
        for sx in (-40,40):pbox(px+sx,py,583,4,88,160,'glass')
        sign('ОХРАНА / %02d'%idx,px,py+43,540,-90,26)
    # Side booths, gate piers and sign bridge leave a 12 m clear throat.
    for py in (704,869):
        pbox(1960,py,150,78,47,300,'dark',True)
        pbox(1960,py-25,210,66,2,90,'glass')
        pbox(1960,py,315,86,54,30,'steel')
        pbox(2028,py,335,12,12,670,'concrete',True)
    pbox(2028,786,685,20,178,100,'dark',True)
    sign('ГЛАВНЫЙ КПП / ВЫХОД В ГОРОД',2016,786,690,-90,46)
    road([(2035,786),(2080,786)],1300)
    # Existing detailed fractured bridge kit, now on the plan's eastern axis.
    bridgecenter=(5850,20000,2150)
    for name in ('SM_BridgeCampusHalf','SM_BridgeCityHalf'):
        mesh=A.load_asset('/Game/Surface/Bridge/'+name);assert mesh
        item(name,mesh,bridgecenter,block=True)
    fallen=A.load_asset('/Game/Surface/Bridge/SM_BridgeFallenSpan')
    item('FallenSpan',fallen,(5930,20000,600),block=True)
    # Real channel void: neither campus nor city ground crosses the gap.
    box((5850,20050,-125),(3200,2850,150),'dark',True)
    for y in (18625,21475):box((5850,y,1040),(4200,80,2220),'concrete',True)
    box((5850,23400,2115),(4200,3800,70),'floor',True)
    road([(2230,786),(2360,786)],1600)
    sign('ОПАСНО / РАЗРУШЕННЫЙ МОСТ',2152,786,260,-90,42)
    sign('ДЛЯ ПЕРЕЛЁТА НУЖЕН ИМПУЛЬСНЫЙ МОДУЛЬ',2155,786,190,-90,25)
    # Connect the far bank to the preserved city district, keeping the gap open.
    box((5850,38000,2080),(18000,29000,140),'dust',True)
    box((5850,38000,2151),(1800,29000,10),'asphalt')
    compile_bp(bp)
    cdo=unreal.get_default_object(B.generated_class(bp));tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick);save(bp)

    # Preserve environmental lighting and city art, replace only site geometry.
    world=unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
    for a in list(sub.get_all_level_actors()):
        label=a.get_actor_label();cls=a.get_class().get_name()
        if label.startswith(('CAMPUS_Sign_','BRIDGE_','REF_')) or cls in ('BP_ConnectedLaboratoryCampus_C','BP_ConnectedPerimeterWalls_C','BP_CampusSealedGate_C'):
            r['removed_actors'].append(label);sub.destroy_actor(a)
        elif label.startswith('CITY_Residential_') or label in ('SURF_Environment','CITY_FirstDowntownBlock'):
            p=a.get_actor_location();a.modify()
            # Translate their original source-space layout to the eastern city.
            a.set_actor_location(L((p.x+5850,p.y-2500,2150+p.z)),False,True)
        elif label=='SURF_ArrivalSequence':
            # The existing one-shot notice is retained; only its route text changes below.
            pass
    actor=spawn(B.generated_class(bp),'REF_LaboratoryComplex',(offset[0],offset[1],offset[2]))
    # Geometry already carries local-frame coordinates, so its actor stays at zero.
    assert abs(actor.get_actor_location().x)+abs(actor.get_actor_location().y)+abs(actor.get_actor_location().z)<.1
    for i,(text,p,yaw,size) in enumerate(signs):
        a=spawn(unreal.TextRenderActor,'REF_Sign_%02d'%i,p,yaw)
        c=a.text_render;c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_text(unreal.Text(text));c.set_world_size(size);c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        c.set_text_render_color(unreal.Color(r=165,g=222,b=222,a=255));c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
    # Change only the streaming frame's yaw, preserving its location and lifecycle.
    departure=A.load_asset('/Game/Surface/BP_SurfaceDeparture');changed=0
    for name in B.list_graph_names(departure):
        for n in G.get_graph_editor_by_name(departure,name).list_all_nodes():
            if 'LoadLevelInstance' in str(n.get_node_title()).replace(' ',''):
                p=n.find_input_pin('Rotation')
                if p.is_valid():assert p.set_pin_value('(Pitch=0,Yaw=0,Roll=0)');changed+=1
    assert changed==1,('Expected one campus streaming call',changed)
    compile_bp(departure);save(departure)
    notice=A.load_asset('/Game/Surface/BP_SurfaceArrival')
    for name in B.list_graph_names(notice):
        for n in G.get_graph_editor_by_name(notice,name).list_all_nodes():
            for p in n.list_all_pins():
                text=p.get_pin_value()
                if 'северные ворота' in text or 'северным воротам' in text:
                    p.set_pin_value('Выйдите из корпуса А. Обойдите научный корпус по внутренней дороге к восточному КПП. Мост в город разрушен — найдите импульсный модуль.')
    compile_bp(notice);save(notice)
    unreal.EditorLoadingAndSavingUtils.load_map(MAIN)
    ed.set_level_viewport_camera_info(V((5650,1200,2390)),unreal.Rotator(pitch=-6,yaw=90,roll=0))
    r.update(saved=True,instances=sum(counts.values()),batches=counts,ring_px=ring,perimeter_px=polygon,wall_height_cm=600,bridge_world=bridgecenter,door_world=[5850,1500,2150],map=LEVEL)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
    json.dump(r,open(os.path.join(project,'Saved/reference_campus_authoring.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Reference site-plan authoring incomplete')

