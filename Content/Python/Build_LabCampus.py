"""Connect the existing laboratory route to an exterior research campus.

Native authoring only. Keep the awakening map open when work is complete.
"""
import unreal,os,sys,json,math,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,add,components,compile_bp,save
ROOT='/Game/Surface';MAIN='/Game/Lvl_LabTutorial';SURFACE=ROOT+'/Lvl_SurfaceArrival'
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir());source=os.path.join(content,'Surface','CampusSource')
backup=os.path.join(saved,'Backups','LabCampus',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
r={'saved':False,'gameplay_tested':False,'backup':backup,'start_map':MAIN,'campus_map':SURFACE}
def backup_asset(rel):
 src=os.path.join(content,rel)
 if os.path.isfile(src):
  dst=os.path.join(backup,rel);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
def spawn(cls,name,p,rot=None):
 a=sub.spawn_actor_from_class(cls,V(p),rot or unreal.Rotator());a.set_actor_label(name);a.set_folder_path('SURFACE/LaboratoryCampus');return a
try:
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 for rel in ['Lvl_LabTutorial.umap','Surface/Lvl_SurfaceArrival.umap','Surface/BP_SurfaceEnvironment.uasset','Surface/BP_SurfaceArrival.uasset']:backup_asset(rel)
 if editor.get_editor_world().get_name()!='Lvl_SurfaceArrival':unreal.EditorLoadingAndSavingUtils.load_map(SURFACE)
 mats={n:A.load_asset('/Game/LabTutorial/FirstFloor/'+n) for n in ['M_LabCeramic','M_LabGraphite','M_LabSteel','M_LabCyan','M_LabAmber','M_LabFloor','M_LabTeal']}
 for n in ['M_DeadGlass','M_RuinConcrete','M_Asphalt','M_Dust','M_Charcoal','M_Oxide']:mats[n]=A.load_asset(ROOT+'/Materials/'+n)
 meshes={}
 for spec in json.load(open(os.path.join(source,'campus_meshes.json'))):
  name=spec['name'];path=ROOT+'/Meshes/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask();opts=unreal.FbxImportUI()
   for k,v in [('import_materials',False),('import_textures',False),('automated_import_should_detect_type',False),('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)]:opts.set_editor_property(k,v)
   opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
   for k,v in {'filename':os.path.join(source,name+'.obj'),'destination_path':ROOT+'/Meshes','automated':True,'save':True,'options':opts}.items():task.set_editor_property(k,v)
   tools.import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Campus mesh missing '+name)
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,mats[str(s.get_editor_property('material_slot_name'))])
  save(mesh);meshes[name]=mesh
 # Shift the city away to make actual space for the research grounds.
 # Strip the old isolated shelter from the reusable city geometry as well.
 city=A.load_asset(ROOT+'/BP_SurfaceEnvironment')
 def trim_city(c):
  for i in range(c.get_instance_count()-1,-1,-1):
   p=c.get_instance_transform(i,False).translation
   if p.y<2500:c.remove_instance(i)
 for h,c,n in components(city):
  if c and isinstance(c,unreal.InstancedStaticMeshComponent):trim_city(c)
 compile_bp(city);save(city)
 for a in list(sub.get_all_level_actors()):
  name=a.get_actor_label()
  if name=='SURF_Environment':
   for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):trim_city(c)
   sub.set_actor_transform(a,unreal.Transform(location=V((0,26000,0))))
  if name.startswith('CAMPUS_') or name=='SURF_ExitDoor' or name.startswith('SURF_ShelterLight'):sub.destroy_actor(a)
 path=ROOT+'/BP_LaboratoryCampus'
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);bp=tools.create_asset('BP_LaboratoryCampus',ROOT,unreal.Blueprint,f)
 add(bp,unreal.SceneComponent,'Root').set_mobility(unreal.ComponentMobility.STATIC);batches={};cube=A.load_asset('/Engine/BasicShapes/Cube');cylinder=A.load_asset('/Engine/BasicShapes/Cylinder');count=0
 def item(key,mesh,p,scale=(1,1,1),yaw=0,mat=None,block=False,hidden=False):
  global count
  if key not in batches:
   c=add(bp,unreal.InstancedStaticMeshComponent,key,'Root');c.clear_instances();c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if block else 'NoCollision')
   if mat:c.set_material(0,mat)
   if hidden:c.set_visibility(False);c.set_hidden_in_game(True);c.set_editor_property('cast_shadow',False)
   batches[key]=c
  batches[key].add_instance(unreal.Transform(location=V(p),rotation=unreal.Rotator(yaw=yaw),scale=V(scale)),False);count+=1
 def box(p,s,mat='M_LabCeramic',block=False,yaw=0):item('Box_'+mat+('_Block' if block else ''),cube,p,tuple(v/100 for v in s),yaw,mats[mat],block)
 def collision(p,s,yaw=0):item('InvisibleCollisions',cube,p,tuple(v/100 for v in s),yaw,None,True,True)
 def local(p,origin,yaw):
  angle=math.radians(yaw);x,y,z=p;return (origin[0]+x*math.cos(angle)-y*math.sin(angle),origin[1]+x*math.sin(angle)+y*math.cos(angle),origin[2]+z)
 def localbox(p,s,origin,yaw,mat='M_LabCeramic',block=False):box(local(p,origin,yaw),s,mat,block,yaw)
 def sign(text,p,yaw,size=40,color=(133,225,232)):
  a=spawn(unreal.TextRenderActor,'CAMPUS_Sign_'+str(len(signs)),p,unreal.Rotator(yaw=yaw));c=a.text_render;c.set_text(unreal.Text(text));c.set_world_size(size);c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_text_render_color(unreal.Color(*color,255));c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);signs.append(text)
 signs=[]
 box((0,6500,-80),(42000,50000,150),'M_Dust',True)
 box((0,5700,-10),(23500,25000,25),'M_LabFloor',True)
 # Ring road, connected pedestrian terraces, and an unobstructed north exit.
 for i in range(48):
  angle=i*math.tau/48;x=math.cos(angle)*6800;y=5500+math.sin(angle)*6800
  box((x,y,7),(910,850,12),'M_Asphalt',False,math.degrees(angle)+90)
  if i%2==0:box((x,y,14),(190,12,1),'M_LabAmber',False,math.degrees(angle)+90)
 box((0,20500,1),(1800,16500,24),'M_Asphalt',True)
 for y in range(13300,27600,500):box((0,y,15),(14,220,1),'M_LabAmber')
 for y in range(13000,27400,300):
  for sx in (-1,1):box((sx*1040,y,20),(280,290,40),'M_RuinConcrete')
 # Main building occupies the centre; six separate research blocks surround it.
 centre=(0,5500,0);item('Headquarters',meshes['SM_CampusHeadquarters'],centre)
 collision((0,5500,1250),(4400,3200,2500))
 box((0,3150,0),(4900,1500,35),'M_RuinConcrete',True)
 sign('ATLAS  /  CENTRAL RESEARCH',(0,3860,1730),-90,105)
 sign('MAIN ADMINISTRATION',(0,3820,690),-90,50)
 wings=[('A-01  /  STASIS',(-7500,-1000,0)),('B-02  /  BIOENGINEERING',(7400,-800,0)),('C-03  /  COMPUTING',(-8000,9500,0)),('D-04  /  ROBOTICS',(8000,10400,0)),('E-05  /  ENERGY',(-3000,14500,0)),('F-06  /  ARCHIVES',(4000,14500,0))]
 exits=None
 for index,(title,p) in enumerate(wings):
  inward=math.degrees(math.atan2(5500-p[1],-p[0]));yaw=inward+90
  item('ResearchWings',meshes['SM_CampusResearchWing'],p,yaw=yaw)
  sign(title,local((0,-1260,690),p,yaw),inward,48)
  localbox((0,-1510,-6),(1300,620,20),p,yaw,'M_RuinConcrete',True)
  if index:
   collision(local((0,0,750),p,yaw),(3200,2400,1500),yaw)
   # Sealed secondary entries are exterior scenery for later room expansion.
   localbox((0,-1210,205),(400,30,410),p,yaw,'M_LabGraphite',True)
  else:
   exits={'origin':p,'yaw':yaw,'heading':inward,'spawn':local((0,-750,110),p,yaw),'door':local((0,-1210,0),p,yaw)}
   # This exit corridor is visibly inside the complete stasis building.
   localbox((0,-750,-12),(720,1000,24),p,yaw,'M_LabFloor',True)
   localbox((0,-750,520),(760,1040,40),p,yaw,'M_LabGraphite',True)
   for sx in (-1,1):
    localbox((sx*360,-750,250),(30,1000,500),p,yaw,'M_LabGraphite',True)
    localbox((sx*343,-750,235),(4,960,35),p,yaw,'M_LabTeal')
    for yy in (-1050,-850,-650,-450):localbox((sx*339,yy,245),(5,9,420),p,yaw,'M_LabSteel')
   localbox((0,-260,250),(720,35,500),p,yaw,'M_LabGraphite',True)
   for yy in (-1050,-650):
    localbox((0,yy,490),(420,55,8),p,yaw,'M_LabCyan')
    lamp=spawn(unreal.PointLight,'CAMPUS_ExitFill_'+str(yy),local((0,yy,360),p,yaw));lc=lamp.point_light_component;lc.set_intensity(450);lc.set_attenuation_radius(430);lc.set_cast_shadows(False);lc.set_light_color(unreal.LinearColor(.45,.64,.75,1))
   for sx in (-1,1):localbox((sx*290,-1210,250),(145,100,500),p,yaw,'M_LabCeramic',True)
   localbox((0,-1210,470),(720,100,70),p,yaw,'M_LabGraphite',True)
  # Broad spokes and emergency service ducts relate the blocks to the campus.
  front=local((0,-1900,0),p,yaw);toward=(0,5500,0);length=math.dist(front[:2],toward[:2]);mid=((front[0]+toward[0])/2,(front[1]+toward[1])/2,5)
  box(mid,(length,420,10),'M_RuinConcrete',False,inward)
 # Damaged courtyard planting, benches and equipment tell a quieter part of the story.
 tree=A.load_asset(ROOT+'/Meshes/SM_DeadTree');rubble=A.load_asset(ROOT+'/Meshes/SM_RubbleCluster');barrier=A.load_asset(ROOT+'/Meshes/SM_ConcreteBarrier')
 for i in range(12):
  a=i*math.tau/12;x=math.cos(a)*4100;y=5500+math.sin(a)*4100
  box((x,y,55),(680,340,110),'M_RuinConcrete',True,math.degrees(a))
  box((x,y,112),(620,280,8),'M_Dust',False,math.degrees(a));item('DeadCourtyardTrees',tree,(x,y,112),(.7,.7,.7),math.degrees(a))
 for i in range(18):
  a=i*math.tau/18;item('CampusRubble',rubble,(math.cos(a)*9300,5500+math.sin(a)*9300,10),(.8,.8,.7),math.degrees(a))
 # Perimeter fence has one clear gate toward the ruined city.
 for i in range(64):
  a=i*math.tau/64;x=math.cos(a)*11500;y=5500+math.sin(a)*11500
  if y>16400 and abs(x)<1850:continue
  yaw=math.degrees(a)+90
  box((x,y,105),(1120,18,190),'M_LabSteel',True,yaw)
  box((x,y,240),(1150,15,16),'M_LabGraphite',False,yaw)
  box((x,y,125),(34,34,250),'M_LabGraphite',True)
 for sx in (-1,1):
  box((sx*1300,17200,270),(160,270,540),'M_RuinConcrete',True)
  box((sx*1300,17200,570),(180,300,45),'M_LabGraphite')
  for yy in range(17800,19301,500):item('GateBarriers',barrier,(sx*1330,yy,25),yaw=90)
 box((0,17200,620),(2780,160,120),'M_LabGraphite',True)
 sign('ATLAS  /  RESEARCH COMPLEX',(0,17105,627),-90,58)
 sign('CITY ACCESS  /  SECTOR 07',(0,16990,440),-90,35,(244,189,94))
 # Simple laboratory transport cars remain behind the service perimeter.
 car=A.load_asset(ROOT+'/Meshes/SM_WreckedSedan')
 for x,y,yaw in [(-11100,2000,90),(11000,6200,90),(9500,13200,0)]:item('AbandonedServiceCars',car,(x,y,10),yaw=yaw)
 compile_bp(bp);save(bp);campus=spawn(B.generated_class(bp),'CAMPUS_LaboratoryGrounds',(0,0,0))
 for c in campus.get_components_by_class(unreal.InstancedStaticMeshComponent):
  if 'InvisibleCollisions' in c.get_name():c.set_visibility(False);c.set_hidden_in_game(True);c.set_editor_property('cast_shadow',False)
 start=next(a for a in sub.get_all_level_actors() if isinstance(a,unreal.PlayerStart));start.set_actor_location(V(exits['spawn']),False,True);start.set_actor_rotation(unreal.Rotator(yaw=exits['heading']),True)
 door=A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor');spawn(B.generated_class(door),'CAMPUS_StasisExitDoor',exits['door'],unreal.Rotator(yaw=exits['heading']))
 arrival=A.load_asset(ROOT+'/BP_SurfaceArrival');e=G.get_graph_editor_by_name(arrival,'EventGraph')
 replacements={'ПОВЕРХНОСТЬ / СЕКТОР 07':'ATLAS / ЛАБОРАТОРНЫЙ КОМПЛЕКС','СВЯЗЬ С ГОРОДОМ ОТСУТСТВУЕТ':'КОРПУС А-01 / ВЫХОД ИЗ СТАЗИС-БЛОКА','Найдите путь через разрушенную магистраль.\nБелая Башня — единственный действующий узел.':'Пройдите через двор комплекса к северным воротам.\nЗа ними — разрушенный город и путь к Башне.'}
 for n in e.list_all_nodes():
  for p in n.list_all_pins():
   value=p.get_pin_value()
   if value in replacements:p.set_pin_value(replacements[value])
 compile_bp(arrival);save(arrival)
 editor.set_level_viewport_camera_info(V(local((0,-2050,205),exits['origin'],exits['yaw'])),unreal.Rotator(pitch=2,yaw=exits['heading']))
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 r.update(saved=True,campus_buildings=7,instances=count,exit=exits,city_offset_cm=[0,26000,0],signs=signs)
 # Leave Play pointing to the actual awakening level, never the surface preview.
 unreal.EditorLoadingAndSavingUtils.load_map(MAIN)
 starts=[a for a in sub.get_all_level_actors() if isinstance(a,unreal.PlayerStart)];r['laboratory_player_starts']=[{'name':a.get_actor_label(),'location':str(a.get_actor_location())} for a in starts]
 if not starts:raise RuntimeError('Laboratory PlayerStart missing')
 try:
  settings=unreal.get_default_object(unreal.LevelEditorPlaySettings);enum=unreal.PlayModeLocations;default=next(getattr(enum,n) for n in dir(enum) if n.endswith('DEFAULT_PLAYER_START'));settings.set_editor_property('last_executed_play_mode_location',default)
 except Exception as ex:r['play_location_setting_note']=str(ex)
 editor.set_level_viewport_camera_info(V((-200,-300,210)),unreal.Rotator(pitch=-4,yaw=130));unreal.EditorLoadingAndSavingUtils.save_current_level()
except Exception:r['saved']=False;r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'lab_campus_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Campus authoring incomplete; see Saved/lab_campus_report.json')
