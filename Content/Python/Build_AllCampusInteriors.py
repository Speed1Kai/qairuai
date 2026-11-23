"""Native modular interiors for every laboratory-campus building.
Uses the measured campus footprints, shared meshes and real stair geometry.
No travel teleport, no new enemy or player-controller changes.
"""
import unreal,os,sys,json,math,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,G,add,components,compile_bp,save
P=os.path.abspath(unreal.Paths.project_dir());ROOT='/Game/Surface/Interiors';MAP='/Game/Surface/Lvl_CampusConnected';Z=2150.
O=(10006.289955343997,6612.598659341473,2150.)
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
R={'saved':False,'buildings':[],'doors':[],'stairs':[],'lights':0,'signs':0,'reference':'Gemini_Generated_Image_giy9nqgiy9nqgiy9.jpg'}
back=os.path.join(P,'Saved/Backups/AllCampusInteriors',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(back,exist_ok=True)
def V(p):return unreal.Vector(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def L(p):return V(tuple(p[i]-O[i] for i in range(3)))
def W(px,py,z=0):return (5850+(786-py)*12,1500+(px-708)*12,Z+z)
def rect(px):
    a=W(px[0],px[1]);b=W(px[2],px[3]);return (min(a[0],b[0]),max(a[0],b[0]),min(a[1],b[1]),max(a[1],b[1]))
def backup(path,ext='.uasset'):
    src=os.path.join(P,'Content',path.removeprefix('/Game/')+ext)
    if os.path.isfile(src):
        dst=os.path.join(back,path.removeprefix('/Game/')+ext);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
specs=[
 {'id':'A_N','name':'А / ИССЛЕДОВАТЕЛЬСКОЕ КРЫЛО','px':[458,545,588,721],'floors':3,'type':'research','side':('y',1)},
 {'id':'B','name':'Б / ОБОРУДОВАНИЕ','px':[937,347,1193,473],'floors':4,'type':'workshop','side':('x',-1)},
 {'id':'V','name':'В / ЭНЕРГОБЛОК','px':[1325,351,1552,468],'floors':3,'type':'power','side':('x',-1)},
 {'id':'HANGAR','name':'СКЛАДСКОЙ АНГАР','px':[1660,347,1895,473],'floors':1,'type':'warehouse','side':('x',-1)},
 {'id':'G','name':'Г / БИОЛАБОРАТОРИЯ','px':[942,1128,1229,1243],'floors':3,'type':'bio','side':('x',1)},
 {'id':'D','name':'Д / ЖИЛОЙ БЛОК','px':[1394,1128,1725,1243],'floors':4,'type':'living','side':('x',1)}]
Hpx=[(1072,720,1454,855),(1029,661,1100,917),(1234,645,1290,931),(1426,661,1496,917),(1100,687,1234,711),(1290,687,1426,711),(1100,866,1234,890),(1290,866,1426,890)]
for s in specs:s['bounds']=rect(s['px'])
H=[rect(x) for x in Hpx]
try:
    assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE'
    for path,ext in [(MAP,'.umap'),('/Game/Lvl_LabTutorial','.umap'),('/Game/Surface/ReferencePlan/BP_ReferenceCampus','.uasset'),('/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor','.uasset'),(ROOT+'/BP_CampusInteriors','.uasset')]:backup(path,ext)
    # Shared opaque palette. One lightweight two-sided glass material, no RTs.
    A.make_directory(ROOT)
    def glass():
        path=ROOT+'/M_InteriorGlass'
        if A.does_asset_exist(path):return A.load_asset(path)
        m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_InteriorGlass',ROOT,unreal.Material,unreal.MaterialFactoryNew())
        m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('two_sided',True)
        for val,prop in [(.19,unreal.MaterialProperty.MP_OPACITY),(.23,unreal.MaterialProperty.MP_ROUGHNESS),(.35,unreal.MaterialProperty.MP_SPECULAR)]:
            n=M.create_material_expression(m,unreal.MaterialExpressionConstant);n.set_editor_property('r',val);M.connect_material_property(n,'',prop)
        c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(r=.035,g=.11,b=.13,a=1));M.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
        M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(m);save(m);return m
    mats={n:A.load_asset('/Game/LabTutorial/FirstFloor/'+p) for n,p in {'white':'M_LabCeramic','dark':'M_LabGraphite','steel':'M_LabSteel','teal':'M_LabTeal','cyan':'M_LabCyan','screen':'M_LabDisplay','floor':'M_LabFloor','rubber':'M_LabRubber'}.items()};mats['glass']=glass()
    path=ROOT+'/BP_CampusInteriors'
    if A.does_asset_exist(path):bp=A.load_asset(path)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_CampusInteriors',ROOT,unreal.Blueprint,f)
    root=add(bp,unreal.SceneComponent,'InteriorRoot');root.set_mobility(unreal.ComponentMobility.MOVABLE)
    batches={};cube=A.load_asset('/Engine/BasicShapes/Cube');cylinder=A.load_asset('/Engine/BasicShapes/Cylinder');signs=[];lights=[];doors=[]
    def item(key,mesh,p,scale=(1,1,1),yaw=0,mat=None,block=False,pitch=0):
        if key not in batches:
            c=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,key,'InteriorRoot');c.modify();c.clear_instances();c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('BlockAll' if block else 'NoCollision')
            if mat:c.set_material(0,mats[mat])
            batches[key]=c
        batches[key].add_instance(unreal.Transform(location=L(p),rotation=unreal.Rotator(pitch=pitch,yaw=yaw),scale=V(scale)),False)
    def box(p,size,mat='white',block=True,yaw=0):item('Box_'+mat+('_Solid' if block else '_Trim'),cube,p,tuple(x/100 for x in size),yaw,mat,block)
    def cyl(p,r,h,mat='steel',block=False):item('Cylinder_'+mat+str(block),cylinder,p,(r/50,r/50,h/100),mat=mat,block=block)
    def sign(text,p,yaw=180,size=18):signs.append((text,p,yaw,size))
    def prop(name,p,yaw=90,size=None):
        mesh=A.load_asset('/Game/LabTutorial/FirstFloor/'+name);assert mesh,name
        item('Prop_'+name,mesh,p,yaw=yaw)
        if size:box((p[0],p[1],p[2]+size[2]/2),(size[0],size[1],size[2]),'dark',True)
        # The visual meshes need simple collision, not solid boxes rendered over them.
        if size:
            key='Box_dark_Solid';c=batches[key];c.remove_instance(c.get_instance_count()-1)
            item('Collision_'+name,cube,(p[0],p[1],p[2]+size[2]/2),tuple(x/100 for x in size),mat='dark',block=True)
            batches['Collision_'+name].set_visibility(False);batches['Collision_'+name].set_hidden_in_game(True)
    def lamp(p):
        prop('SM_CleanroomLight',(p[0],p[1],p[2]+372),0)
        lights.append((p[0],p[1],p[2]+290))
    # Axis-aligned shell; doors and glass occupy real openings, no mass behind.
    def wall(axis,c,a,b,z,height=400,opening=None,windows=True):
        if b-a<2:return
        if opening and a<opening[0]<b:
            center,width=opening;left=max(a,center-width/2);right=min(b,center+width/2)
            wall(axis,c,a,left,z,height,None,windows);wall(axis,c,right,b,z,height,None,windows)
            p=(c,(left+right)/2,z+(height+290)/2) if axis=='x' else ((left+right)/2,c,z+(height+290)/2)
            box(p,(26,right-left,height-290) if axis=='x' else (right-left,26,height-290),'white')
            return
        count=max(1,math.ceil((b-a)/360));step=(b-a)/count
        for i in range(count):
            mid=a+(i+.5)*step
            def band(h,thick,mat,collision=True):
                p=(c,mid,z+h) if axis=='x' else (mid,c,z+h)
                depth=26 if collision else 28  # Keep trim clear of the wall surface.
                box(p,(depth,step,thick) if axis=='x' else (step,depth,thick),mat,collision)
            if windows and step>170:
                band(65,130,'white');band(377,46,'white');band(242,224,'glass')
                for v in (a+i*step+9,a+(i+1)*step-9):
                    p=(c,v,z+242) if axis=='x' else (v,c,z+242);box(p,(36,18,224) if axis=='x' else (18,36,224),'steel')
            else:band(height/2,height,'white')
            band(22,24,'dark',False);band(122,12,'teal',False)
    def solidwall(axis,c,a,b,z,opening=None):wall(axis,c,a,b,z,340,opening,False)
    def splitrect(q,hole):
        x0,x1,y0,y1=q
        if not hole:return [q]
        a,b,c,d=hole;ax=max(x0,a);bx=min(x1,b);cy=max(y0,c);dy=min(y1,d)
        if ax>=bx or cy>=dy:return[q]
        return [r for r in [(x0,ax,y0,y1),(bx,x1,y0,y1),(ax,bx,y0,cy),(ax,bx,dy,y1)] if r[1]-r[0]>1 and r[3]-r[2]>1]
    def slab(q,z,hole=None):
        for x0,x1,y0,y1 in splitrect(q,hole):box(((x0+x1)/2,(y0+y1)/2,z-12),(x1-x0,y1-y0,24),'floor')
    def stair(cx,cy,base,levels,stepheight=400,ident=''):
        # Two flights, each 12 risers, with continuous full-width landings.
        R['stairs'].append({'id':ident,'centre':[cx,cy],'base':base,'levels':levels,'rise':stepheight,'hole':[cx-240,cx+240,cy-280,cy+280]})
        for level in range(levels-1):
            z=base+level*stepheight;rise=stepheight/24
            for i in range(12):
                h=(i+1)*rise;v=-240+(i+.5)*30
                box((cx+v,cy-140,z+h-8),(30,120,16),'steel')
                h=stepheight/2+(i+1)*rise;v=120-(i+.5)*30
                box((cx+v,cy+140,z+h-8),(30,120,16),'steel')
            box((cx+180,cy,z+stepheight/2-8),(120,420,16),'steel')
            box((cx-300,cy,z+stepheight-8),(120,420,16),'steel')
            # Rails outside the walking lanes; no crossbar at stair entry.
            for side in (-1,1):
                for v in (-220,-100,20,200):box((cx+v,cy+side*225,z+stepheight/2+50),(8,8,100),'steel')
                box((cx,cy+side*225,z+stepheight/2+100),(480,7,7),'steel')
        for level in range(1,levels):
            z=base+level*stepheight
            for side in (-1,1):
                box((cx,cy+side*285,z+108),(480,8,8),'steel')
                for v in (-230,0,230):box((cx+v,cy+side*285,z+54),(8,8,108),'steel')
    def furnishing(kind,x,y,z,roomw=700,side=1):
        # x/y are world room centre. All furniture leaves the corridor clear.
        if kind in ('workshop','research','control'):
            prop('SM_ModernConsole',(x+side*130,y,z),90 if side<0 else -90,(76,180,84))
            prop('SM_ModernChair',(x-side*30,y,z),90 if side<0 else -90)
            prop('SM_LabEquipmentCabinet',(x+side*110,y+min(260,roomw*.33),z),90,(48,90,216))
            if kind=='workshop':prop('SM_LabUtilityBench',(x+side*80,y-min(240,roomw*.32),z),90,(65,190,93))
        elif kind=='power':
            for yy in (-150,150):
                prop('SM_ModernServerRack',(x+side*80,y+yy,z),90,(100,86,236))
                cyl((x-side*100,y+yy,z+95),48,190,'steel',True);cyl((x-side*100,y+yy,z+195),36,7,'cyan')
            box((x,y,z+1),(280,490,2),'dark',False)
        elif kind=='bio':
            prop('SM_LabUtilityBench',(x+side*150,y,z),90,(65,190,93))
            for yy in (-180,180):
                cyl((x-side*100,y+yy,z+14),62,28,'dark',True);cyl((x-side*100,y+yy,z+114),49,172,'glass',True)
                cyl((x-side*100,y+yy,z+114),15,142,'screen');cyl((x-side*100,y+yy,z+210),60,18,'steel',True)
        elif kind=='living':
            for yy in (-160,160):
                box((x+side*60,y+yy,z+24),(210,100,48),'dark');box((x+side*60,y+yy,z+54),(200,94,16),'rubber')
                box((x+side*130,y+yy,z+66),(42,82,12),'white',False);box((x-side*49,y+yy,z+39),(5,96,5),'teal',False)
            prop('SM_LabEquipmentCabinet',(x-side*100,y+roomw*.36,z),90,(48,90,216))
        else:
            for yy in (-160,160):
                prop('SM_LabEquipmentCabinet',(x+side*50,y+yy,z),90,(48,90,216))
                for zz in (40,100,160):box((x-side*100,y+yy,z+zz),(100,100,65),'steel')
    # Strip the old filled solids and decorative facades from these footprints.
    campus=A.load_asset('/Game/Surface/ReferencePlan/BP_ReferenceCampus');assert campus
    bounds=[s['bounds'] for s in specs]+H
    removed={}
    for h,c,n in components(campus):
        if not isinstance(c,unreal.InstancedStaticMeshComponent) or n not in ('Box_dark_Collision','Box_dark_Detail','Box_wall_Detail','Box_glass_Detail','Box_steel_Detail','Box_steel_Collision','Box_cyan_Detail'):continue
        c.modify();count=0
        for i in range(c.get_instance_count()-1,-1,-1):
            p=c.get_instance_transform(i,False).translation;x,y,z=p.x+O[0],p.y+O[1],p.z+O[2]
            inside=any(a-130<x<b+130 and d-130<y<e+130 for a,b,d,e in bounds)
            # A's broad old roof would cut through the new upper interior.
            oldroof=abs(x-5874)<5 and abs(y+288)<5 and 3300<z<3450
            if (inside and z>Z+80) or oldroof:c.remove_instance(i);count+=1
        if count:removed[n]=count
    compile_bp(campus);save(campus);R['old_solid_instances_removed']=removed
    # Rectangular site buildings: continuous central corridor, rooms on each
    # side and a dedicated stair lobby at the end (no furniture in stair wells).
    for s in specs:
        x0,x1,y0,y1=s['bounds'];cx=(x0+x1)/2;cy=(y0+y1)/2;width=y1-y0;depth=x1-x0;floors=s['floors'];kind=s['type']
        scx=cx;scy=y1-350;hole=(scx-240,scx+240,scy-280,scy+280) if floors>1 else None
        axis,side=s['side'];entry=((x0 if side<0 else x1),cy) if axis=='x' else (cx+400,(y0 if side<0 else y1))
        doors.append((s['id'],(entry[0],entry[1],Z),0 if axis=='x' else 90))
        for f in range(floors):
            z=Z+f*400;slab(s['bounds'],z,hole if f else None)
            for axis,c,a,b,side in [('x',x0,y0,y1,-1),('x',x1,y0,y1,1),('y',y0,x0,x1,-1),('y',y1,x0,x1,1)]:
                op=(entry[1] if axis=='x' else entry[0],366) if f==0 and axis==s['side'][0] and side==s['side'][1] else None
                wall(axis,c,a,b,z,opening=op)
            for yy in (y0+500,cy,y1-500):lamp((cx,yy,z))
            sign(s['name']+' / %02d'%(f+1),(cx-175,y1-760,z+270),180,18)
            if kind=='warehouse':
                for yy in range(int(y0+350),int(y1-250),420):
                    if abs(yy-cy)<450:continue
                    for side in (-1,1):furnishing('warehouse',cx+side*(depth/2-230),yy,z,500,side)
                prop('SM_LabSupplyCart',(cx-320,cy,z),0)
            else:
                usable=width-800;cells=1 if usable<1400 else 2 if kind=='power' else 3;step=usable/cells
                names={'workshop':['МЕХАНИКА','МОДУЛИ','ДИАГНОСТИКА'],'power':['ГЕНЕРАТОРЫ','РАСПРЕДЕЛЕНИЕ'],'bio':['АНАЛИЗ','КРИОБАНК','КУЛЬТУРЫ'],'living':['КАЮТЫ','ОТДЫХ','МЕДИЦИНА'],'research':['АНАЛИТИКА','ИССЛЕДОВАНИЯ','АРХИВ']}[kind]
                for j in range(cells):
                    a=y0+25+j*step;b=y0+25+(j+1)*step;mid=(a+b)/2
                    for side in (-1,1):
                        entrybay=f==0 and s['side'][0]=='x' and side==s['side'][1] and a<cy<b
                        solidwall('x',cx+side*180,a,b,z,opening=(cy if entrybay else mid,190 if entrybay else 150))
                        if j and not (f==0 and s['side'][0]=='x' and side==s['side'][1] and abs(a-cy)<240):
                            if side<0:solidwall('y',a,x0+25,cx-180,z)
                            else:solidwall('y',a,cx+180,x1-25,z)
                        roomkind=kind
                        if kind=='living' and f==0:roomkind='control' if j==0 else 'research'
                        if not entrybay:furnishing(roomkind,cx+side*(180+(depth/2-200)/2),mid,z,step,side)
                        sign(names[j],(cx+side*170,mid,z+275),180 if side>0 else 0,14)
        slab(s['bounds'],Z+floors*400)
        if floors>1:stair(scx,scy,Z,floors,400,s['id'])
        R['buildings'].append({'id':s['id'],'name':s['name'],'bounds':s['bounds'],'floors':floors,'entry':entry,'stair_centre':[scx,scy] if floors>1 else None,'type':kind})
    # Main building: exact union of its H-shaped footprint, with no overlapped
    # slabs. The cross-spine remains a clear route between both entrances.
    xs=sorted({q for r in H for q in r[:2]});ys=sorted({q for r in H for q in r[2:]})
    cells=[]
    for i in range(len(xs)-1):
        for j in range(len(ys)-1):
            x=(xs[i]+xs[i+1])/2;y=(ys[j]+ys[j+1])/2
            if any(a<=x<=b and c<=y<=d for a,b,c,d in H):cells.append((i,j))
    occupied=set(cells);scx=6400;scy=10536;hole=(scx-240,scx+240,scy-280,scy+280)
    mainnames=['ПРИЁМ И НАБЛЮДЕНИЕ','ИССЛЕДОВАТЕЛЬСКИЕ ЗАЛЫ','ВЫЧИСЛИТЕЛЬНОЕ ЯДРО','СИМУЛЯЦИИ И ПРОТОТИПЫ','НАУЧНОЕ УПРАВЛЕНИЕ']
    for f in range(5):
        z=Z+400*f
        for i,j in cells:
            slab((xs[i],xs[i+1],ys[j],ys[j+1]),z,hole if f else None)
            for di,dj,axis,c,a,b in [(-1,0,'x',xs[i],ys[j],ys[j+1]),(1,0,'x',xs[i+1],ys[j],ys[j+1]),(0,-1,'y',ys[j],xs[i],xs[i+1]),(0,1,'y',ys[j+1],xs[i],xs[i+1])]:
                if (i+di,j+dj) not in occupied:
                    op=(5850,366) if f==0 and axis=='y' and c in (min(ys),max(ys)) and a<5850<b else None
                    wall(axis,c,a,b,z,opening=op)
        for yy in (6400,7700,9000):
            lamp((5850,yy,z))
            for side in (-1,1):
                solidwall('x',5850+side*190,yy-490,yy+490,z,opening=(yy,180))
                furnishing('bio' if f==1 else 'power' if f==2 else 'workshop' if f==3 else 'research',5850+side*470,yy,z,900,side)
        for xx,yy in ((4650,5700),(7100,5700),(4500,8150),(7350,8150)):
            furnishing('research',xx,yy,z,600,-1);lamp((xx,yy,z))
        sign('%02d / '%(f+1)+mainnames[f],(5850,5600,z+295),90,22)
    for i,j in cells:slab((xs[i],xs[i+1],ys[j],ys[j+1]),Z+2000)
    stair(scx,scy,Z,5,400,'MAIN')
    for yy in (min(ys),max(ys)):doors.append(('MAIN',(5850,yy,Z),90))
    R['buildings'].append({'id':'MAIN','name':'ГЛАВНЫЙ НАУЧНЫЙ КОРПУС','floors':5,'rectangles':H,'entry':[[5850,min(ys)],[5850,max(ys)]],'stair_centre':[scx,scy],'type':'research'})
    # A's existing first floor is preserved. Two upper floors and an external
    # stair core attach at the previously blank east wall, without touching L1.
    upper=(3000,6360,-300,900)
    for f in range(2):
        z=Z+480+400*f;slab(upper,z)
        for axis,c,a,b in [('x',3000,-300,900),('x',6360,-300,900),('y',-300,3000,6360),('y',900,3000,6360)]:wall(axis,c,a,b,z,opening=(600,300) if axis=='x' and c==6360 else None)
        for xx in (3500,4400,5400):
            for yy in (0,650):furnishing('research',xx,yy,z,350,-1 if yy==0 else 1)
            lamp((xx,300,z))
        slab((6360,6760,400,800),z);sign('А / ЭТАЖ %d'%(f+2),(6290,600,z+300),180,20)
    slab(upper,Z+1280)
    tower=(6550,7450,250,950)
    for z in (Z,Z+480,Z+880):
        slab(tower,z,(6760,7240,320,880) if z>Z else None);slab((6360,6760,400,800),z)
        wall('y',250,6550,7450,z,480 if z==Z else 400);wall('y',950,6550,7450,z,480 if z==Z else 400);wall('x',7450,250,950,z,480 if z==Z else 400)
    slab(tower,Z+1280)
    stair(7000,600,Z,2,480,'A_01_02');stair(7000,600,Z+480,2,400,'A_02_03')
    R['buildings'].append({'id':'A_UPPER','name':'А / ВЕРХНИЕ ЭТАЖИ','floors':3,'bounds':upper,'stair_centre':[7000,600],'type':'research'})
    # Cut only the A first-floor wall needed for the real stair connection.
    floor=A.load_asset('/Game/LabTutorial/FirstFloor/BP_ModernFirstFloor')
    for h,c,n in components(floor):
        if not isinstance(c,unreal.InstancedStaticMeshComponent) or n not in ('Boxes_M_LabCeramic','Boxes_M_LabGraphite','Boxes_M_LabTeal','Boxes_M_LabSteel'):continue
        c.modify()
        for i in range(c.get_instance_count()-1,-1,-1):
            p=c.get_instance_transform(i,False).translation
            if abs(p.x-6360)<12 and -300<=p.y<=900 and Z<p.z<Z+440:c.remove_instance(i)
    compile_bp(floor);save(floor)
    wall('x',6360,-300,900,Z,440,(600,300),False)
    compile_bp(bp);save(bp)
    # Install all new actors in the streamed exterior; original campus origin
    # is zero. Root geometry uses L(world) to share the existing stream frame.
    w=unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    for a in list(sub.get_all_level_actors()):
        if a.get_actor_label().startswith('INT_'):sub.destroy_actor(a)
        elif a.get_class().get_name()=='BP_ReferenceCampus_C':
            p=a.get_actor_location();rot=a.get_actor_rotation();label=a.get_actor_label();sub.destroy_actor(a);a=sub.spawn_actor_from_class(B.generated_class(campus),p,rot);a.set_actor_label(label);a.set_folder_path('SURFACE/ReferencePlan')
    a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label('INT_AllCampusBuildings');a.set_folder_path('SURFACE/Interiors')
    doorclass=B.generated_class(A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor'))
    for idx,(ident,p,yaw) in enumerate(doors):
        a=sub.spawn_actor_from_class(doorclass,L(p),unreal.Rotator(yaw=yaw));a.set_actor_label('INT_Door_'+ident+'_'+str(idx));a.set_folder_path('SURFACE/Interiors/Doors');R['doors'].append({'id':ident,'world':p,'yaw':yaw})
    for i,p in enumerate(lights):
        a=sub.spawn_actor_from_class(unreal.PointLight,L(p));a.set_actor_label('INT_Light_'+str(i));a.set_folder_path('SURFACE/Interiors/Lights');c=a.point_light_component;c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_intensity(650);c.set_attenuation_radius(700);c.set_cast_shadows(False);c.set_light_color(unreal.LinearColor(r=.65,g=.83,b=1,a=1));c.set_editor_property('source_radius',90.)
    for i,(text,p,yaw,size) in enumerate(signs):
        a=sub.spawn_actor_from_class(unreal.TextRenderActor,L(p),unreal.Rotator(yaw=yaw));a.set_actor_label('INT_Sign_'+str(i));a.set_folder_path('SURFACE/Interiors/Wayfinding');c=a.text_render;c.set_text(unreal.Text(text));c.set_world_size(size);c.set_text_render_color(unreal.Color(r=130,g=230,b=240,a=255));c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    w.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(w,MAP);del w
    # Refresh the placed A first-floor actor after its small doorway cut.
    w=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
    departure=A.load_asset('/Game/Surface/BP_SurfaceDeparture');backup('/Game/Surface/BP_SurfaceDeparture')
    cs={n:c for h,c,n in components(departure)};east=cs['ExteriorEastWall'];east.modify()
    east.set_editor_property('relative_location',V((510,-1420,320)));east.set_editor_property('relative_scale3d',V((.35,14.8,8)))
    north=add(departure,unreal.StaticMeshComponent,'ExteriorEastNorth','Root');north.set_static_mesh(east.static_mesh);north.set_material(0,east.get_material(0));north.set_mobility(unreal.ComponentMobility.MOVABLE);north.set_collision_profile_name('BlockAll');north.set_editor_property('relative_location',V((510,130,320)));north.set_editor_property('relative_scale3d',V((.35,8.2,8)))
    compile_bp(departure);save(departure)
    for a in list(sub.get_all_level_actors()):
        if a.get_class().get_name()=='BP_ModernFirstFloor_C':
            p=a.get_actor_location();rot=a.get_actor_rotation();label=a.get_actor_label();sub.destroy_actor(a);a=sub.spawn_actor_from_class(B.generated_class(floor),p,rot);a.set_actor_label(label);a.set_folder_path('LAB/Floor01/Architecture')
        elif a.get_class().get_name()=='BP_SurfaceDeparture_C':
            a.modify()
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                if c.get_name()=='ExteriorEastWall':c.set_relative_location(V((510,-1420,320)),False,False);c.set_relative_scale3d(V((.35,14.8,8)))
    w.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(w,'/Game/Lvl_LabTutorial')
    R.update(saved=True,backup=back,lights=len(lights),signs=len(signs),batches={k:c.get_instance_count() for k,c in batches.items()},total_instances=sum(c.get_instance_count() for c in batches.values()))
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
finally:json.dump(R,open(os.path.join(P,'Saved/all_campus_interiors.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not R['saved']:raise RuntimeError('Campus interiors incomplete; see report')
