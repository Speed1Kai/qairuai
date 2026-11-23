"""Apply the abandoned recovery-laboratory art pass without rebuilding gameplay."""
import unreal, math, random, os, traceback

ROOT = '/Game/LabTutorial/ReferenceStyle'
random.seed(41)
V = lambda p: unreal.Vector(*[float(n) for n in p])
E = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

def material(name, color, metal=0, rough=.85, glow=0, weather=False):
    path = ROOT + '/' + name
    m = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    E.delete_all_material_expressions(m)
    def expr(cls, **props):
        n = E.create_material_expression(m, cls)
        for k,v in props.items(): n.set_editor_property(k,v)
        return n
    c = expr(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1))
    if weather:
        pos = expr(unreal.MaterialExpressionWorldPosition)
        noise = expr(unreal.MaterialExpressionNoise, scale=.06, quality=1, levels=2, output_min=.65, output_max=1.)
        E.connect_material_expressions(pos,'',noise,'Position')
        dark = expr(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(r=color[0]*.6,g=color[1]*.6,b=color[2]*.6,a=1))
        lerp = expr(unreal.MaterialExpressionLinearInterpolate)
        for src, pin in ((dark,'A'),(c,'B'),(noise,'Alpha')): E.connect_material_expressions(src,'',lerp,pin)
        E.connect_material_property(lerp,'',unreal.MaterialProperty.MP_BASE_COLOR)
    else: E.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for val,prop in ((metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)):
        n = expr(unreal.MaterialExpressionConstant,r=float(val)); E.connect_material_property(n,'',prop)
    if glow:
        g=expr(unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(r=color[0]*glow,g=color[1]*glow,b=color[2]*glow,a=1))
        E.connect_material_property(g,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    E.recompile_material(m); assets.save_loaded_asset(m)
    return m

def mesh(name,p,s,mat,shape='Cube',rot=(0,0,0),block=False):
    rotation=unreal.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2])
    a=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor,V(p),rotation)
    a.set_actor_label('REF_'+name); a.set_folder_path('LAB/06_ReferenceStyle')
    c=a.static_mesh_component; c.set_static_mesh(assets.load_asset('/Engine/BasicShapes/'+shape)); c.set_material(0,mat)
    c.set_collision_profile_name('BlockAll' if block else 'NoCollision')
    a.set_actor_scale3d(V([n/100 for n in s])); a.set_actor_rotation(rotation,False); return a

def line(name,a,b,r,mat):
    d=V(b)-V(a); center=(V(a)+V(b))*.5
    rot=unreal.MathLibrary.make_rot_from_z(d)
    return mesh(name,(center.x,center.y,center.z),(r*2,r*2,d.length()),mat,'Cylinder',(rot.pitch,rot.yaw,rot.roll))

def cable(name,points,r=2):
    for j in range(len(points)-1): line(name+'_'+str(j),points[j],points[j+1],r,rubber)

def light(name,p,color,power,radius):
    a=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight,V(p),unreal.Rotator())
    a.set_actor_label('REF_'+name); a.set_folder_path('LAB/02_Lighting')
    c=a.point_light_component; c.set_light_color(unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1)); c.set_intensity(power)
    c.set_editor_property('attenuation_radius',float(radius)); c.set_cast_shadows(False)
    return a

try:
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
    assets.make_directory(ROOT)
    concrete=material('M_AgedConcrete',(.28,.31,.29),weather=True)
    steel=material('M_OxidizedPaint',(.20,.26,.25),.55,.72,weather=True)
    ivory=material('M_WornPodEnamel',(.49,.55,.50),.48,.58,weather=True)
    rust=material('M_Rust',(.19,.065,.028),.35,.94,weather=True)
    rubber=material('M_CableRubber',(.009,.014,.015),.15,.8)
    cyan=material('M_CyanPhosphor',(.04,.63,.68),.15,.3,3)
    red=material('M_RedEmergency',(.8,.018,.009),0,.4,5)
    white=material('M_ColdTube',(.65,.8,.78),0,.5,3)
    # Retain all Blueprint actors, collision, terminals, and player controls.
    for a in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        n=a.get_actor_label()
        if n.startswith('REF_') or n.startswith('LAB_Cradle_') or n.startswith('LAB_Hologram_Frame') or n.startswith('LAB_Hologram_Figure'):
            unreal.EditorLevelLibrary.destroy_actor(a); continue
        c=a.get_component_by_class(unreal.StaticMeshComponent)
        if c and n.startswith('LAB_'):
            old=c.get_material(0); oldname=old.get_name() if old else ''
            if any(t in n for t in ('Wall','Ceiling','Floor')) and 'Light' not in n and 'Marker' not in n:
                c.set_material(0,concrete if 'Plate' not in n and 'Beam' not in n else steel)
            elif oldname in ('MI_FP_RustedSteel','MI_FP_EdenSilver'): c.set_material(0,steel)
            elif oldname=='MI_FP_EdenCeramic': c.set_material(0,ivory)
            elif oldname=='MI_FP_ProtocolCyan': c.set_material(0,cyan)
            elif oldname=='MI_FP_LaserRed': c.set_material(0,red)
        lc=a.get_component_by_class(unreal.PointLightComponent)
        if lc and n.startswith('LAB_RedEmergency'): lc.set_intensity(2500); lc.set_editor_property('attenuation_radius',1000.)
        if lc and n.startswith('LAB_RouteMaintenance'): lc.set_intensity(2400)
        if n=='LAB_PlayerStart':
            # Keep the first-person spawn inside the recovery cradle, behind
            # the animated hatch, so the opening beat starts from the pod.
            a.set_actor_location(V((-430,280,198)),False,False)
    # Inclined capsule: a rounded rectangular perimeter in a tilted local plane.
    # It opens toward +X; the player spawns beside its open foot end.
    origin=(-550,280,205); tilt=math.radians(22)
    def pod(u,v,depth=0):
        return (origin[0]-math.sin(tilt)*v+math.cos(tilt)*depth, origin[1]+u,
                origin[2]+math.cos(tilt)*v+math.sin(tilt)*depth)
    perimeter=[]
    for cx,cy,start in ((48,125,0),(-48,125,90),(-48,-125,180),(48,-125,270)):
        for j in range(7):
            t=math.radians(start+j*15)
            perimeter.append((cx+47*math.cos(t),cy+47*math.sin(t)))
    for depth,r,mat in ((-34,15,steel),(-13,12,ivory),(8,5,rubber),(14,2,cyan)):
        for j,(u,v) in enumerate(perimeter):
            un,vn=perimeter[(j+1)%len(perimeter)]
            line('PodRim_%s_%s'%(depth,j),pod(u,v,depth),pod(un,vn,depth),r,mat)
    mesh('PodBack',pod(0,0,-39),(20,154,300),steel,rot=(22,0,0),block=True)
    mesh('PodMattress',pod(0,-10,-20),(18,128,254),ivory,rot=(22,0,0))
    mesh('PodHeadrest',pod(0,106,-1),(22,70,48),rubber,rot=(22,0,0))
    for side in (-1,1):
        for j in range(5):
            mesh('PodArmor_%s_%s'%(side,j),pod(side*103,-115+j*58,-25),(66,22,48),ivory,rot=(22,0,0))
        cable('PodInternalLead'+str(side),[pod(side*(53+7*math.sin(j)),125-j*25,-2) for j in range(11)],1.5)
    mesh('PodPedestal',(-520,280,20),(265,250,40),steel,'Cylinder',block=True)
    mesh('PodFootCowl',pod(0,-141,10),(83,172,65),ivory,rot=(22,0,0),block=True)
    for i in range(4): mesh('PodFootVent'+str(i),pod(-45+i*30,-144,53),(2,17,23),rubber,rot=(22,0,0))
    light('PodInterior',(-385,280,220),(.16,.65,.68),950,430)
    # Bundled, sagging cables across the room and along the complete tutorial route.
    for i in range(12):
        y=-640+i*112
        points=[(-840+j*140,y+22*math.sin(j*.5+i),420-(45+i%4*18)*math.sin(math.pi*j/12)) for j in range(13)]
        cable('CeilingBundle'+str(i),points,2+i%3)
    for i in range(5):
        cable('PodUmbilical'+str(i),[(-775+i*10,280+i*13,425),(-800+i*12,280+i*13,335),(-735+i*10,290+i*13,205),(-635,290+i*12,95)],3)
    for i in range(4):
        cable('CorridorCable'+str(i),[(920+j*100,150+i*10,400-45*abs(math.sin(j*.4))) for j in range(14)],2)
    # Tall obsolete server banks along the rear wall, with vent slats and sparse LEDs.
    for i in range(7):
        x=-730+i*225
        mesh('ServerCabinet'+str(i),(x,-700,177),(175,102,350),steel,block=True)
        mesh('ServerInset'+str(i),(x,-644,180),(148,8,310),rubber)
        for j in range(11):
            z=47+j*26
            mesh('ServerDrawer_%s_%s'%(i,j),(x,-636,z),(136,8,20),steel)
            for k in range(3): mesh('ServerVent_%s_%s_%s'%(i,j,k),(x+12,-630,z-5+k*5),(84,3,2),rubber)
            if j%3==0: mesh('ServerLED_%s_%s'%(i,j),(x-54,-629,z),(5,3,4),cyan if i%3 else red)
    # Concrete seams, spalling, and branching cracks are geometry, visible at grazing angles.
    for wall in (-1,1):
        y=wall*762
        for x in range(-800,851,210):
            line('WallJoint_%s_%s'%(wall,x),(x,y,15),(x,y,428),.7,rubber)
        for i in range(18):
            x=random.uniform(-830,830); z=random.uniform(210,415)
            pts=[(x,y,z)]
            for j in range(4):
                x+=random.uniform(-24,24);z-=random.uniform(12,32);pts.append((x,y,z))
            for j in range(4): line('Crack_%s_%s_%s'%(wall,i,j),pts[j],pts[j+1],.6,rubber)
        for i in range(24):
            x=random.uniform(-840,840);z=random.uniform(260,420)
            mesh('WaterStain_%s_%s'%(wall,i),(x,y,z),(random.uniform(3,15),1,random.uniform(30,130)),rust)
    # Broken concrete stays at the perimeter and leaves the playable route clear.
    for i in range(65):
        x=random.uniform(-820,820);y=random.choice((-1,1))*random.uniform(590,735)
        mesh('Rubble'+str(i),(x,y,random.uniform(2,8)),(random.uniform(6,30),random.uniform(5,24),random.uniform(4,14)),concrete,rot=(random.randrange(25),random.randrange(180),random.randrange(20)))
    for i,(x,y,z) in enumerate(((-630,730,365),(570,730,365),(-650,-745,375),(760,-500,380),(1180,-180,355),(2150,175,360),(1400,820,380),(4050,395,2510))):
        mesh('AlarmHousing'+str(i),(x,y,z),(55,24,26),rubber)
        mesh('AlarmLens'+str(i),(x,y-15,z),(35,8,14),red)
        light('AlarmGlow'+str(i),(x,y-55,z-10),(1,.025,.012),1700,650)
    # Grated ceiling luminaires repeat on both laboratory floors.
    for i,(x,y,z) in enumerate(((50,40,425),(500,400,425),(1400,520,425),(3800,0,2680))):
        mesh('CeilingLampFrame'+str(i),(x,y,z),(210,100,12),rubber)
        mesh('CeilingLampDiffuser'+str(i),(x,y,z-8),(187,78,3),white)
        for j in range(9): mesh('LampGrille_%s_%s'%(i,j),(x-88+j*22,y,z-12),(4,86,5),steel)
        light('CeilingPool'+str(i),(x,y,z-30),(.53,.72,.71),2600,850)
    # Upper lab also receives hardware and cable runs.
    for i in range(3):
        mesh('UpperRack'+str(i),(3500+i*225,-350,2325),(160,100,350),steel,block=True)
        for j in range(8): mesh('UpperRackSlot_%s_%s'%(i,j),(3500+i*225,-294,2200+j*32),(136,7,22),rubber)
        cable('UpperCable'+str(i),[(3450+j*65,-240+i*30,2665-55*math.sin(math.pi*j/10)) for j in range(11)],3)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(V((610,550,260)),unreal.Rotator(-5,-150,0))
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        n=a.get_actor_label()
        if n.startswith('LAB_Hologram_Text_'):
            i=int(n.rsplit('_',1)[-1])-1
            a.set_actor_location(V((-60,-30,330-i*45)),False,False)
            a.set_actor_rotation(unreal.Rotator(pitch=0,yaw=126,roll=0),False)
        elif isinstance(a,unreal.TextRenderActor):
            p=a.get_actor_location()
            viewer=(-280,280) if p.x<900 else (p.x,0)
            a.set_actor_rotation(unreal.Rotator(pitch=0,yaw=math.degrees(math.atan2(viewer[1]-p.y,viewer[0]-p.x)),roll=0),False)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level(): raise RuntimeError('Map save failed')
    assets.save_directory(ROOT)
    with open(os.path.join(unreal.Paths.project_saved_dir(),'reference_style_report.txt'),'w') as f:
        f.write('SUCCESS: reference style applied; gameplay Blueprints retained.\nActors: '+str(len(unreal.EditorLevelLibrary.get_all_level_actors())))
    exec(compile(open(os.path.join(unreal.Paths.project_content_dir(),'Python/Finish_LabReference.py'),encoding='utf8').read(),'Finish_LabReference.py','exec'))
except Exception:
    with open(os.path.join(unreal.Paths.project_saved_dir(),'reference_style_report.txt'),'w') as f: f.write(traceback.format_exc())
    raise
