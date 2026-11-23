"""Build the modern first-floor plan, retaining the functioning basement lift."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,V,add,compile_bp,save
ROOT='/Game/LabTutorial/FirstFloor'
saved=os.path.abspath(unreal.Paths.project_saved_dir())
content=os.path.abspath(unreal.Paths.project_content_dir())
backup=os.path.join(saved,'Backups','ModernFirstFloor',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True)
shutil.copy2(os.path.join(content,'Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'))
r={'saved':False,'backup':backup,'floor_z':2150,'removed':[],'rooms':[],'note':'Authored and saved only; no gameplay test performed.'}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 A.make_directory(ROOT)
 # Remove the previous first-floor blockout and every placed enemy, including the drone.
 for a in list(sub.get_all_level_actors()):
  n=a.get_actor_label();p=a.get_actor_location();cls=a.get_class().get_path_name()
  enemy=n.startswith(('ENEMY_','LAB_Drone_')) or 'BP_EnemyRobot' in cls or 'BP_TutorialPatrolDrone' in cls
  obsolete=n.startswith(('LAB_FirstFloor_','F01_')) or (n.startswith('REF_') and p.x>3000 and p.z>2100)
  obsolete=obsolete or n=='LAB_StoryTrigger_StealthHint'
  if enemy or obsolete:r['removed'].append(n);sub.destroy_actor(a)
 # Industrial dressing contains batched props from the old upstairs room.
 trimmed=0
 for a in sub.get_all_level_actors():
  if a.get_actor_label()!='IND_InstancedDressing':continue
  for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
   for i in range(c.get_instance_count()-1,-1,-1):
    p=c.get_instance_transform(i,world_space=True).translation
    if p.x>3000 and p.z>2100:c.remove_instance(i);trimmed+=1
 r['old_upstairs_instances_removed']=trimmed
 # Small shared, texture-free PBR palette. The basement materials are untouched.
 mats={}
 def material(name,color,metal=0,rough=.5,glow=False):
  path=ROOT+'/'+name
  m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
  M.delete_all_material_expressions(m)
  col=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);col.set_editor_property('constant',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1))
  if glow:
   m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);M.connect_material_property(col,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
  else:
   M.connect_material_property(col,'',unreal.MaterialProperty.MP_BASE_COLOR)
   for val,prop in [(metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)]:
    q=M.create_material_expression(m,unreal.MaterialExpressionConstant);q.set_editor_property('r',val);M.connect_material_property(q,'',prop)
  M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(m);save(m);mats[name]=m
 for name,col,metal,rough,glow in [
  ('M_LabCeramic',(.56,.65,.67),.1,.43,False),('M_LabGraphite',(.025,.042,.055),.45,.36,False),
  ('M_LabSteel',(.22,.29,.31),.82,.32,False),('M_LabRubber',(.012,.019,.025),0,.82,False),
  ('M_LabFloor',(.16,.22,.25),.16,.47,False),('M_LabTeal',(.018,.19,.22),.35,.4,False),
  ('M_LabCyan',(.03,4.5,5.3),0,.4,True),('M_LabDisplay',(.015,.32,.43),0,.4,True),
  ('M_LabWhiteLight',(4.5,5.2,5.5),0,.4,True),('M_LabAmber',(4,1.25,.05),0,.4,True)]:material(name,col,metal,rough,glow)
 specs=json.load(open(os.path.join(content,'LabTutorial','FirstFloor','Source','first_floor_meshes.json')))
 meshes={};tools=unreal.AssetToolsHelpers.get_asset_tools()
 for spec in specs:
  name=spec['name'];path=ROOT+'/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask()
   opts=unreal.FbxImportUI();opts.set_editor_property('import_mesh',True);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False)
   opts.set_editor_property('automated_import_should_detect_type',False);opts.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
   opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
   for k,v in {'filename':os.path.join(content,'LabTutorial','FirstFloor','Source',name+'.obj'),'destination_path':ROOT,'automated':True,'save':True,'options':opts}.items():task.set_editor_property(k,v)
   tools.import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Mesh import failed '+name)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   key=str(slot.get_editor_property('material_slot_name'))
   if key not in mats:raise RuntimeError('Missing modern material '+key)
   mesh.set_material(i,mats[key])
  save(mesh);meshes[name]=mesh
 # One Blueprint with shared instancing for architecture and all repeated equipment.
 path=ROOT+'/BP_ModernFirstFloor'
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);bp=tools.create_asset('BP_ModernFirstFloor',ROOT,unreal.Blueprint,f)
 compile_bp(bp);add(bp,unreal.SceneComponent,'FloorRoot')
 batches={};cube=A.load_asset('/Engine/BasicShapes/Cube')
 counts={'instances':0,'lights':0,'signs':0,'doors':0}
 def instance(key,mesh,p,scale=(1,1,1),yaw=0,mat=None,block=False,hidden=False):
  if key not in batches:
   c=add(bp,unreal.InstancedStaticMeshComponent,key,'FloorRoot');c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC)
   c.clear_instances();c.set_collision_profile_name('BlockAll' if block else 'NoCollision')
   if mat:c.set_material(0,mat)
   c.set_editor_property('cast_shadow',not hidden)
   if hidden:c.set_visibility(False);c.set_hidden_in_game(True)
   batches[key]=c
  transform=unreal.Transform(location=V(p),rotation=unreal.Rotator(yaw=yaw),scale=V(scale))
  batches[key].add_instance(transform,world_space=False);counts['instances']+=1
 def box(p,size,mat='M_LabCeramic',block=True,yaw=0):instance('Boxes_'+mat,cube,p,tuple(v/100 for v in size),yaw,mats[mat],block)
 def blocker(p,size,yaw=0):instance('HiddenFurnitureCollisions',cube,p,tuple(v/100 for v in size),yaw,None,True,True)
 def prop(name,p,yaw=0,scale=(1,1,1),collision=None):
  instance(name,meshes[name],p,scale,yaw)
  if collision:
   cx,cy,cz=collision;blocker((p[0],p[1],p[2]+cz*scale[2]/2),(cx*scale[0],cy*scale[1],cz*scale[2]),yaw)
 Z=2150;H=440
 def floor_rect(x0,x1,y0,y1):
  box(((x0+x1)/2,(y0+y1)/2,Z-15),(x1-x0,y1-y0,30),'M_LabGraphite')
  # Panel seams are real shallow joints; the foundation keeps every seam walkable.
  for x in range(int(x0),int(x1),100):
   for y in range(int(y0),int(y1),100):
    dx=min(100,x1-x);dy=min(100,y1-y)
    box((x+dx/2,y+dy/2,Z+.35),(dx-1.2,dy-1.2,.7),'M_LabFloor',False)
  box(((x0+x1)/2,(y0+y1)/2,Z+H+10),(x1-x0,y1-y0,20),'M_LabGraphite')
 def wall_x(x,y0,y1):
  if y1<=y0:return
  box((x,(y0+y1)/2,Z+H/2),(20,y1-y0,H))
  for side in (-1,1):
   xx=x+side*10.5
   for z,h,mat in [(12,24,'M_LabGraphite'),(122,16,'M_LabTeal'),(414,32,'M_LabSteel')]:box((xx,(y0+y1)/2,Z+z),(1.5,y1-y0,h),mat,False)
   for y in range(int(y0)+110,int(y1),120):box((xx,y,Z+238),(1.7,1.2,340),'M_LabGraphite',False)
 def wall_y(y,x0,x1):
  if x1<=x0:return
  box(((x0+x1)/2,y,Z+H/2),(x1-x0,20,H))
  for side in (-1,1):
   yy=y+side*10.5
   for z,h,mat in [(12,24,'M_LabGraphite'),(122,16,'M_LabTeal'),(414,32,'M_LabSteel')]:box(((x0+x1)/2,yy,Z+z),(x1-x0,1.5,h),mat,False)
   for x in range(int(x0)+110,int(x1),120):box((x,yy,Z+238),(1.2,1.7,340),'M_LabGraphite',False)
 def opening_x(x,y0,y1,center=0):
  wall_x(x,y0,center-183);wall_x(x,center+183,y1)
  box((x,center,Z+424),(20,366,32))
 def opening_y(y,x0,x1,center):
  wall_y(y,x0,center-183);wall_y(y,center+183,x1)
  box((center,y,Z+424),(366,20,32))
 def sign(text,p,yaw=180,size=18,color=(128,232,245)):
  a=sub.spawn_actor_from_class(unreal.TextRenderActor,V(p),unreal.Rotator(yaw=yaw));a.set_actor_label('F01_Sign_%02d'%counts['signs']);a.set_folder_path('LAB/Floor01/Wayfinding')
  c=a.text_render;c.set_text(unreal.Text(text));c.set_world_size(size);c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_text_render_color(unreal.Color(r=color[0],g=color[1],b=color[2],a=255));c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);counts['signs']+=1
 def lamp(x,y,power=1100):
  prop('SM_CleanroomLight',(x,y,Z+H-13))
  # Broad local fill replaces unavailable GI, while keeping the source far enough
  # below the ceiling to avoid the former concentrated inverse-square hotspots.
  a=sub.spawn_actor_from_class(unreal.PointLight,V((x,y,Z+H-120)),unreal.Rotator());a.set_actor_label('F01_Light_%02d'%counts['lights']);a.set_folder_path('LAB/Floor01/Lighting')
  c=a.point_light_component;c.set_intensity(power*.7);c.set_attenuation_radius(720);c.set_light_color(unreal.LinearColor(r=.72,g=.87,b=1,a=1));c.set_cast_shadows(False);c.set_editor_property('source_radius',70.);counts['lights']+=1
 def door(p,yaw=0):
  asset=A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor');a=sub.spawn_actor_from_class(B.generated_class(asset),V(p),unreal.Rotator(yaw=yaw));a.set_actor_label('F01_AutoDoor_%02d'%counts['doors']);a.set_folder_path('LAB/Floor01/Doors')
  mapping={'M_DistressedMetal':'M_LabGraphite','M_DoorArmor':'M_LabCeramic','M_RustyIron':'M_LabSteel','M_Rubber':'M_LabRubber','M_Chrome':'M_LabSteel'}
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   mesh=c.static_mesh
   if not mesh:continue
   for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=str(slot.get_editor_property('material_slot_name'))
    if key in mapping:c.set_material(i,mats[mapping[key]])
  counts['doors']+=1
 # Plan, in metres: 6x6 receiving bay; 6x6 showers; 3x6 airlock;
 # 12x12 server core; engineer bay; 8x3.5 security; 12.6x12 hall.
 rooms=[('01 / ПРИЁМНАЯ',3000,3600,-300,300),('01B / САНОБРАБОТКА',3000,3600,300,900),('02 / ШЛЮЗ',3600,3900,-300,300),('03 / СЕРВЕРНОЕ ЯДРО',3900,5100,-300,900),('03B / ИНЖЕНЕРНАЯ',4500,5100,-900,-300),('04 / ПОСТ ДИАГНОСТИКИ',3900,4700,900,1250),('04B / ТЕХНИЧЕСКАЯ',4700,5100,900,1250),('05 / ГЛАВНЫЙ ХОЛЛ',5100,6360,-300,900),('05B / ВЫХОД НА ПОВЕРХНОСТЬ',5550,6150,900,1500)]
 for name,x0,x1,y0,y1 in rooms:floor_rect(x0,x1,y0,y1);r['rooms'].append({'name':name,'bounds':[x0,x1,y0,y1]})
 # Receiving bay west wall has the existing elevator exit, exactly aligned at y=0.
 opening_x(3000,-300,300);wall_y(-300,3000,3900);opening_y(300,3000,3600,3300)
 wall_x(3000,300,900);wall_y(900,3000,3600);wall_x(3600,300,900)
 opening_x(3600,-300,300);opening_x(3900,-300,300);wall_y(300,3600,3900)
 wall_y(-300,3900,4500);opening_y(-300,4500,5100,4800)
 wall_x(4500,-900,-300);wall_y(-900,4500,5100);wall_x(5100,-900,-300)
 opening_x(5100,-300,900);wall_y(-300,5100,6360);wall_x(6360,-300,900)
 opening_y(900,3900,4700,4510);wall_y(1250,3900,5100);wall_x(3900,300,1250)
 opening_x(4700,900,1250,1075);wall_x(5100,900,1250)
 wall_y(900,5100,5550);wall_y(900,6150,6360);wall_y(1500,5550,6150);wall_x(5550,900,1500);wall_x(6150,900,1500)
 # Modern automatic partitions reuse the existing working split-door logic.
 for p,yaw in [((3600,0,Z),0),((3900,0,Z),0),((5100,0,Z),0),((4510,900,Z),90)]:door(p,yaw)
 # Clean entry furnishings: lockers and technical workbench.
 for x in (3120,3240,3360):prop('SM_LabEquipmentCabinet',(x,-255,Z),0,collision=(90,48,216))
 prop('SM_LabUtilityBench',(3330,245,Z),180,collision=(190,65,93))
 prop('SM_LabSupplyCart',(3485,-170,Z),0,collision=(66,42,94))
 for x in (3090,3210,3330,3450):
  prop('SM_DeconShowerColumn',(x,850,Z),0,collision=(26,28,286))
  box((x,755,Z+1),(75,80,2),'M_LabSteel',False)
  for yy in range(722,790,8):box((x,yy,Z+2.2),(63,2,1),'M_LabGraphite',False)
 for x in (3650,3850):
  prop('SM_DeconShowerColumn',(x,260,Z),0,scale=(.65,.65,1),collision=(26,28,286))
 # Twelve racks in three rows with wide end and cross aisles, no hidden blockers in routes.
 for row,x in enumerate((4150,4530,4900)):
  for j,y in enumerate((180,380,580,780)):
   prop('SM_ModernServerRack',(x,y,Z),-90,collision=(86,100,240))
  sign('C-%02d  /  DATA NODE'%(10+row),(x-58,180,Z+265),180,13)
  for y in (140,820):box((x,y,Z+2),(118,5,1),'M_LabCyan',False)
 # Floor-edge navigation lines keep the path readable under emergency conditions.
 for x0,x1,y in [(3030,3570,-80),(3930,5070,-105),(5140,5810,-105)]:
  box(((x0+x1)/2,y,Z+1.1),(x1-x0,4,1),'M_LabCyan',False)
 box((5810,340,Z+1.1),(4,890,1),'M_LabCyan',False)
 # Engineer room: modern flat panels, sample bench, rolling chairs, archive dock.
 for x in (4630,4940):
  prop('SM_ModernConsole',(x,-835,Z),180,collision=(180,76,84));prop('SM_ModernChair',(x,-720,Z),180,collision=(50,48,70))
 prop('SM_LabUtilityBench',(4555,-505,Z),90,collision=(190,65,93))
 prop('SM_LabEquipmentCabinet',(5055,-505,Z),-90,collision=(90,48,216))
 # Security / diagnostics workstation and unoccupied equipment safe.
 for x in (4075,4290):
  prop('SM_ModernConsole',(x,1190,Z),0,collision=(180,76,84));prop('SM_ModernChair',(x,1060,Z),0,collision=(50,48,70))
 prop('SM_LabEquipmentCabinet',(4615,1195,Z),0,collision=(90,48,216))
 for y in (1000,1160):prop('SM_LabEquipmentCabinet',(5050,y,Z),-90,collision=(90,48,216))
 # Main hall: structural columns, quiet waiting area and equipment carts.
 for x in (5310,6190):
  for y in (150,620):
   box((x,y,Z+220),(65,65,440),'M_LabCeramic');box((x,y,Z+26),(77,77,52),'M_LabGraphite')
   for dx in (-34,34):box((x+dx,y,Z+207),(2,38,200),'M_LabTeal',False)
 for y in (100,410,710):
  prop('SM_LabEquipmentCabinet',(6300,y,Z),-90,collision=(90,48,216))
 for x in (5420,5570,5720):prop('SM_ModernChair',(x,-225,Z),0,collision=(50,48,70))
 for x,y in [(5430,470),(6060,620)]:prop('SM_LabSupplyCart',(x,y,Z),35,collision=(66,42,94))
 # The surface freight lift is deliberately a sealed future destination, not another ride.
 box((5850,1315,Z+210),(510,36,420),'M_LabSteel')
 for x in (5723,5977):
  box((x,1288,Z+207),(247,16,402),'M_LabGraphite')
  for z in (70,195,320):box((x,1278,Z+z),(217,3,92),'M_LabSteel',False)
  box((x,1275,Z+48),(217,2,24),'M_LabAmber',False)
 box((5850,1273,Z+210),(3,2,390),'M_LabCyan',False)
 for x in (5575,6125):box((x,1290,Z+216),(35,90,432),'M_LabCeramic')
 box((5850,1290,Z+426),(585,90,35),'M_LabGraphite')
 prop('SM_ModernConsole',(6085,1060,Z),-90,scale=(.65,.65,.85),collision=(180,76,84))
 # Repeated ceiling services and cold-white working illumination, without volumetric fog.
 for x,y,power in [(3290,0,1200),(3290,620,1300),(3750,0,850),(4100,-70,1200),(4490,-70,1200),(4880,-70,1200),(4100,470,1200),(4490,470,1200),(4880,470,1200),(4120,1080,1000),(4510,1080,1000),(4910,1080,900),(4790,-620,1350),(5380,0,1300),(5850,0,1300),(6230,0,1000),(5390,590,1300),(5850,590,1300),(6230,590,1000),(5850,1100,1300)]:lamp(x,y,power)
 for x in range(3100,6301,200):
  prop('SM_LabCeilingService',(x,-220,Z+H-32))
 for x in (4100,4490,4880):
  for y in (160,560):prop('SM_LabCeilingService',(x,y,Z+H-30),90)
 sign('01  /  ТЕХНИЧЕСКАЯ ПРИЁМНАЯ',(3575,0,Z+407),180,14)
 sign('02  /  ДЕКОНТАМИНАЦИЯ',(3874,0,Z+407),180,13)
 sign('03  /  СЕРВЕРНОЕ ЯДРО ATLAS',(5075,0,Z+407),180,14)
 sign('04  /  ОХРАНА И ДИАГНОСТИКА',(4510,875,Z+407),-90,13)
 sign('05  /  ГЛАВНЫЙ ХОЛЛ',(5130,0,Z+405),0,17)
 sign('Л-1  /  НА ПОВЕРХНОСТЬ',(5850,1260,Z+383),-90,21)
 sign('ПИТАНИЕ ОТКЛЮЧЕНО',(5850,1260,Z+294),-90,13,(255,190,70))
 sign('ИНЖЕНЕРНЫЙ ПОСТ  /  АРХИВ 02',(4800,-875,Z+300),90,15)
 sign('САНИТАРНАЯ ОБРАБОТКА',(3300,875,Z+340),-90,16)
 # Archive terminal uses the existing cinematic widget, with its own new instance only.
 src=A.load_asset('/Game/LabTutorial/UI/WBP_ArchiveLog')
 if src:
  from Industrial_Common import G,Graph,pin,link
  path=ROOT+'/BP_Floor01Archive'
  if A.does_asset_exist(path):terminal=A.load_asset(path)
  else:
   f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);terminal=tools.create_asset('BP_Floor01Archive',ROOT,unreal.Blueprint,f)
  compile_bp(terminal);root=add(terminal,unreal.SceneComponent,'ArchiveRoot');zone=add(terminal,unreal.BoxComponent,'ReadZone','ArchiveRoot');zone.set_box_extent(V((130,130,150)));zone.set_editor_property('relative_location',V((0,0,130)));zone.set_collision_profile_name('Trigger');zone.set_editor_property('generate_overlap_events',True)
  g=Graph(terminal);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
  names=list(map(str,B.list_member_variable_names(terminal)))
  for name,typ,default in [('bIsReading',B.get_basic_type_by_name('bool'),'false'),('CurrentLog',B.get_object_reference_type(unreal.UserWidget),'None')]:
   if name not in names:g.e.add_member_variable(name,typ,default)
  compile_bp(terminal);g=Graph(terminal)
  class SafeGraph(Graph):
   def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
  g=SafeGraph(terminal)
  actions=[n for n in g.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|E')]
  key=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True)
  player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0));pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
  g.branch(g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('ReadZone'),Other=player)));g.branch(g.math('Not_PreBool',A=g.get('bIsReading')));g.set('bIsReading',True)
  q=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(src).get_path_name(),OwningPlayer=pc));widget=g.out(q);g.set('CurrentLog',widget)
  for propname,text in [('HUDTitle','АРХИВ 02 | СЕРВЕРНОЕ ЯДРО ATLAS'),('HUDMessage','Резервный контур лаборатории активен. Лифт Л-1 ведёт на поверхность, но его питание отключено. Атлас сохранил оборудование, уничтожив тех, кто им пользовался.')]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=propname,Value=text))
  g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=45));g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=8.));g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('CurrentLog')));g.set('bIsReading',False)
  compile_bp(terminal);cdo=unreal.get_default_object(B.generated_class(terminal));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',60);save(terminal)
  a=sub.spawn_actor_from_class(B.generated_class(terminal),V((4790,-680,Z)),unreal.Rotator());a.set_actor_label('F01_ArchiveInteraction');a.set_folder_path('LAB/Floor01/Interactables')
  sign('[E]  АРХИВ 02',(4790,-780,Z+169),90,11)
 compile_bp(bp);save(bp)
 a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)),unreal.Rotator());a.set_actor_label('F01_ModernLaboratory');a.set_folder_path('LAB/Floor01/Architecture')
 # Viewing position for the next editor opening. Gameplay still starts in the capsule.
 unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(V((3970,-100,Z+185)),unreal.Rotator(pitch=-4,yaw=40))
 staged=os.path.join(saved,'ModernFirstFloorStaged','Lvl_LabTutorial.umap');os.makedirs(os.path.dirname(staged),exist_ok=True)
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+staged.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(staged):raise RuntimeError('Staged map save failed')
 r.update(saved=True,staged_map=staged,counts=counts,instance_batches=len(batches),meshes=specs)
except Exception:
 r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'modern_first_floor_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Modern first floor authoring failed; see report')
