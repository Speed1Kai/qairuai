"""Author the surface reveal and a packaged F-operated route from floor 01.

Run inside the existing editor. No PIE, external assets or rendering console hacks.
"""
import unreal,os,sys,json,math,random,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,add,components,compile_bp,save,Graph,pin,val,link
ROOT='/Game/Surface';LEVEL=ROOT+'/Lvl_SurfaceArrival';MAIN='/Game/Lvl_LabTutorial'
saved=os.path.abspath(unreal.Paths.project_saved_dir());source=os.path.abspath(unreal.Paths.project_content_dir()+'Surface/Source')
backup=os.path.join(saved,'Backups','SurfaceArrival',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools();r={'saved':False,'gameplay_tested':False,'backup':backup,'level':LEVEL,'counts':{}}
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def event(self,name):
  n=self.e.find_event_node(name)
  if not n:
   token=name.removeprefix('Receive');opts=[x for x in self.e.list_available_nodes([]) if x.startswith('Добавитьсобытие|') and x.split('|')[-1].replace(' ','') in [token,'Событие'+token]]
   if not opts:raise RuntimeError('Event unavailable '+name)
   n=self.e.create_node_from_name(opts[0],unreal.Vector2D(),[])
  self.cursor=pin(n,'then',True);return n
def blueprint(name):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);return tools.create_asset(name,ROOT,unreal.Blueprint,f)
def member(bp,n,typ,d):
 if n not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(n,typ,str(d))
 B.set_blueprint_variable_instance_editable(bp,n,True)
def pc(g):return g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
def player(g):return g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
def hud(g,title,message,lifetime=8.,store=None):
 q=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint')).get_path_name(),OwningPlayer=pc(g)));w=g.out(q)
 if store:g.set(store,w)
 for n,v in [('HUDTitle',title),('HUDMessage',message)]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=w,PropertyName=n,Value=v))
 g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=w,PropertyName='HUDLifetime',Value=lifetime));g.do(g.call('UMG.UserWidget.AddToViewport',target=w,ZOrder=60))
 return w
def freshgraph(bp):
 compile_bp(bp);g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);return g
def material(name,color,metal=0,rough=.85,glow=False,code=None,alpha=False,sky=False):
 path=ROOT+'/Materials/'+name;m=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m)
 m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT if glow or sky or alpha else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
 if alpha:m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('two_sided',True)
 if sky:m.set_editor_property('two_sided',True)
 def node(cls,**kw):
  n=M.create_material_expression(m,cls)
  for k,v in kw.items():n.set_editor_property(k,v)
  return n
 if code:
  custom=node(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4 if alpha else unreal.CustomMaterialOutputType.CMOT_FLOAT3)
  inputs=[]
  for n in ['P','UV','T']:
   p=unreal.CustomInput();p.set_editor_property('input_name',n);inputs.append(p)
  custom.set_editor_property('inputs',inputs);custom.set_editor_property('code',code)
  for cls,n in [(unreal.MaterialExpressionWorldPosition,'P'),(unreal.MaterialExpressionTextureCoordinate,'UV'),(unreal.MaterialExpressionTime,'T')]:M.connect_material_expressions(node(cls),'',custom,n)
  if alpha:
   rgb=node(unreal.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);opacity=node(unreal.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
   M.connect_material_expressions(custom,'',rgb,'');M.connect_material_expressions(custom,'',opacity,'');M.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY)
  else:rgb=custom
 else:rgb=node(unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(*color,1))
 M.connect_material_property(rgb,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if glow or sky or alpha else unreal.MaterialProperty.MP_BASE_COLOR)
 if not (glow or sky or alpha):
  for number,prop in [(metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)]:M.connect_material_property(node(unreal.MaterialExpressionConstant,r=number),'',prop)
 M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(m);save(m);return m
NOISE='''struct Noise {float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}}; Noise n;
'''
try:
 if editor.get_editor_world().get_name()!='Lvl_LabTutorial':unreal.EditorLoadingAndSavingUtils.load_map(MAIN)
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Cannot save current laboratory')
 shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'))
 A.make_directory(ROOT);A.make_directory(ROOT+'/Materials')
 mats={}
 for name,col,metal,rough in [('M_RuinConcrete',(.24,.23,.205),0,.93),('M_RuinSteel',(.055,.065,.066),.68,.7),('M_Charcoal',(.015,.018,.019),0,.97),('M_DeadGlass',(.035,.066,.075),.5,.35),('M_Oxide',(.17,.058,.02),.3,.88),('M_AIWhite',(.64,.72,.74),.45,.28),('M_Asphalt',(.044,.048,.047),0,.95),('M_Dust',(.17,.15,.115),0,.97)]:
  code=NOISE+'float grime=n.n(P.xy*.008+P.z*.003);float grain=n.n(P.xy*.22+P.z*.12);float cracks=1-smoothstep(.008,.025,abs(n.n(P.xy*.035)-.5));return float3(%s,%s,%s)*(.62+.38*grime+.1*grain)*(1-cracks*.13);'%col
  mats[name]=material(name,col,metal,rough,code=code)
 for name,col in [('M_AILight',(.08,2.3,3.2)),('M_ExitAmber',(2.8,.85,.08)),('M_ColdLight',(.5,1.5,1.8)),('M_LanePaint',(.24,.20,.12))]:mats[name]=material(name,col,glow=True)
 skycode=NOISE+'''float3 d=normalize(P-float3(0,0,400));float h=saturate(d.z*1.6);float3 c=lerp(float3(.44,.385,.31),float3(.095,.145,.18),h);float cloud=n.n(d.xy*6/(abs(d.z)+.35)+float2(T*.001,0));cloud=cloud*.7+n.n(d.xy*19)*.3;c*=lerp(.5,1.07,smoothstep(.25,.76,cloud));float sun=pow(saturate(dot(d,normalize(float3(-.7,.9,.3)))),90);return c+float3(.7,.39,.13)*sun*.5;'''
 mats['M_AshSky']=material('M_AshSky',(0,0,0),sky=True,code=skycode)
 smoke=NOISE+'''float2 uv=UV;float rise=T*.035;float shape=sin(saturate(uv.y)*3.14159);float width=.13+.33*(1-uv.y);float edge=1-smoothstep(width*.65,width,abs(uv.x-.5+.06*sin(uv.y*12+T*.19)));float noise=n.n(float2(uv.x*7,uv.y*9+rise))*0.7+n.n(float2(uv.x*15,uv.y*21+rise*1.7))*.3;float a=edge*shape*smoothstep(.2,.75,noise)*.68;return float4(lerp(float3(.075,.083,.085),float3(.17,.16,.135),uv.y),a);'''
 mats['M_RisingSmoke']=material('M_RisingSmoke',(0,0,0),alpha=True,code=smoke)
 fire=NOISE+'''float2 uv=UV;float v=1-uv.y;float f=n.n(float2(uv.x*11,uv.y*9+T*2));float shape=saturate(1-abs(uv.x-.5)*2.4-v*.55);float a=smoothstep(.18,.7,shape+f*.45-v*.7)*sin(uv.y*3.14159);return float4(lerp(float3(3,.12,.005),float3(8,2,.08),uv.y)*(.8+.2*sin(T*8)),a);'''
 mats['M_SmallFire']=material('M_SmallFire',(0,0,0),alpha=True,code=fire)
 meshes={};specs=json.load(open(os.path.join(source,'surface_kit.json')))
 for spec in specs:
  name=spec['name'];path=ROOT+'/Meshes/'+name
  if not A.does_asset_exist(path):
   task=unreal.AssetImportTask();opts=unreal.FbxImportUI()
   for k,v in [('import_mesh',True),('import_materials',False),('import_textures',False),('automated_import_should_detect_type',False),('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)]:opts.set_editor_property(k,v)
   opts.static_mesh_import_data.set_editor_property('combine_meshes',True)
   for k,v in {'filename':os.path.join(source,name+'.obj'),'destination_path':ROOT+'/Meshes','automated':True,'save':True,'options':opts}.items():task.set_editor_property(k,v)
   tools.import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Import failed '+name)
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,mats[str(s.get_editor_property('material_slot_name'))])
  save(mesh);meshes[name]=mesh
 soundpath=ROOT+'/S_SurfaceWind'
 if not A.does_asset_exist(soundpath):
  task=unreal.AssetImportTask()
  for k,v in {'filename':os.path.join(source,'S_SurfaceWind.wav'),'destination_path':ROOT,'automated':True,'save':True}.items():task.set_editor_property(k,v)
  tools.import_asset_tasks([task])
 wind=A.load_asset(soundpath);wind.set_editor_property('looping',True);save(wind)
 # A real native Actor handles F without relying on editor Python during play.
 route=blueprint('BP_SurfaceDeparture');add(route,unreal.SceneComponent,'Root')
 for n,t,d in [('bNear','bool','false'),('bTravelling','bool','false')]:member(route,n,B.get_basic_type_by_name(t),d)
 member(route,'Prompt',B.get_object_reference_type(unreal.UserWidget),'None');g=freshgraph(route)
 g.event('ReceiveBeginPlay');g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.2));g.do(g.call('Engine.Actor.EnableInput',PlayerController=pc(g)));g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.15))
 g.event('ReceiveTick');g.branch(g.math('Not_PreBool',A=g.get('bTravelling')));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=player(g))))
 dist=g.math('Vector_Distance',V1=g.out(g.call('Engine.Actor.K2_GetActorLocation')),V2=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=player(g))))
 near=g.math('LessEqual_DoubleDouble',A=dist,B=190.);g.branch(g.math('NotEqual_BoolBool',A=near,B=g.get('bNear')));g.set('bNear',near);split=g.branch(near);out=split.find_else_pin();hud(g,'ЛИФТ Л-1','[F]  НА ПОВЕРХНОСТЬ',86400,'Prompt');g.cursor=out;g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Prompt'))));g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('Prompt')))
 key=g.node(g.e.create_node_from_name(next(x for x in g.e.list_available_nodes([]) if x.endswith('|KeyboardEvents|F')),unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True)
 g.branch(g.get('bNear'));g.branch(g.math('Not_PreBool',A=g.get('bTravelling')));g.set('bTravelling',True)
 g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('Prompt'))));g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('Prompt')))
 g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound='/Game/LabTutorial/Industrial/S_BlastDoorThud',VolumeMultiplier=.35))
 hud(g,'ЛИФТ Л-1 / ПОДЪЁМ','СИГНАЛ ПОВЕРХНОСТИ ВОССТАНОВЛЕН',4.)
 cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));g.do(g.call('Engine.PlayerCameraManager.StartCameraFade',target=cam,FromAlpha=0.,ToAlpha=1.,Duration=2.5,Color='(R=0,G=0,B=0,A=1)',bShouldFadeAudio=True,bHoldWhenFinished=True))
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=3.));g.do(g.call('Engine.GameplayStatics.OpenLevel',LevelName=LEVEL,bAbsolute=True,Options=''))
 compile_bp(route);cdo=unreal.get_default_object(B.generated_class(route));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',60);save(route)
 # Replace the dormant lift notice with an active route. Keep its existing cabin.
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label()=='SURFACE_Departure':sub.destroy_actor(a)
  if isinstance(a,unreal.TextRenderActor):
   p=a.get_actor_location()
   if abs(p.x-5850)<10 and abs(p.y-1260)<10 and abs(p.z-2444)<10:a.text_render.set_text(unreal.Text('Л-1 / ГОТОВ К ПОДЪЁМУ'))
 depart=sub.spawn_actor_from_class(B.generated_class(route),V((5990,1080,2260)),unreal.Rotator());depart.set_actor_label('SURFACE_Departure');depart.set_folder_path('LAB/Floor01/Interactables');depart.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
 # Give the existing console a bright physical indicator, independent of focus gating.
 light=sub.spawn_actor_from_class(unreal.PointLight,V((6060,1060,2345)),unreal.Rotator());light.set_actor_label('SURFACE_DepartureIndicator');light.set_folder_path('LAB/Floor01/Interactables');light.point_light_component.set_intensity(100);light.point_light_component.set_attenuation_radius(180);light.point_light_component.set_light_color(unreal.LinearColor(.05,1,.7,1));light.point_light_component.set_cast_shadows(False)
 unreal.EditorLoadingAndSavingUtils.save_current_level()
 if A.does_asset_exist(LEVEL):unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 else:
  if not unreal.EditorLevelLibrary.new_level(LEVEL):raise RuntimeError('New surface map failed')
 # Idempotent re-authoring only touches this dedicated surface map.
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith('SURF_'):sub.destroy_actor(a)
 env=blueprint('BP_SurfaceEnvironment');add(env,unreal.SceneComponent,'Root').set_mobility(unreal.ComponentMobility.STATIC);batches={};count=0
 cube=A.load_asset('/Engine/BasicShapes/Cube');plane=A.load_asset('/Engine/BasicShapes/Plane')
 def instance(key,mesh,p,scale=(1,1,1),rot=None,mat=None,block=False):
  global count
  if key not in batches:
   c=add(env,unreal.InstancedStaticMeshComponent,key,'Root');c.clear_instances();c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if block else 'NoCollision')
   if mat:c.set_material(0,mat)
   batches[key]=c
  batches[key].add_instance(unreal.Transform(location=V(p),rotation=rot or unreal.Rotator(),scale=V(scale)),False);count+=1
 def box(p,size,mat='M_RuinConcrete',block=False,rot=None):instance('Boxes_'+mat+('_Block' if block else ''),cube,p,tuple(v/100 for v in size),rot,mats[mat],block)
 def prop(name,p,scale=(1,1,1),yaw=0,roll=0,pitch=0):instance(name,meshes[name],p,scale,unreal.Rotator(pitch=pitch,yaw=yaw,roll=roll))
 def block(p,size):box(p,size,'M_Charcoal',True)
 # The lift opens into a short narrow shelter framing the first panorama.
 box((0,-900,370),(720,1500,60),'M_RuinConcrete',True)
 for x in (-350,350):box((x,-900,630),(70,1500,520),'M_RuinConcrete',True)
 box((0,-900,900),(770,1500,70),'M_RuinConcrete',True);box((0,-1620,650),(720,50,560),'M_RuinSteel',True)
 for y in (-1400,-950,-500):
  box((0,y,865),(470,80,12),'M_ColdLight');box((-305,y,625),(18,38,410),'M_RuinSteel');box((305,y,625),(18,38,410),'M_RuinSteel')
 # Four-metre-high ruined loading terrace; physical staircase leads to the street.
 box((0,550,350),(3600,1600,100),'M_RuinConcrete',True)
 for x in (-1800,1800):
  box((x,550,470),(45,1650,140),'M_RuinConcrete',True)
  for y in range(-150,1301,220):box((x,y,565),(22,22,70),'M_RuinSteel')
  box((x,550,605),(20,1650,16),'M_RuinSteel')
 for sign in (-1,1):box((sign*1220,1330,470),(1150,50,140),'M_RuinConcrete',True)
 for i in range(20):
  height=400-i*20;box((0,1360+i*55,height/2),(1100,60,height),'M_RuinConcrete',True)
 # Terrain is intentionally modest: one visible block, with inaccessible skyline dressing.
 box((0,18000,-80),(78000,68000,150),'M_Dust',True)
 box((0,11400,-10),(2280,18400,28),'M_Asphalt',True)
 for sign in (-1,1):
  box((sign*1430,10900,20),(560,17400,60),'M_RuinConcrete',True)
  for y in range(2650,19200,300):
   box((sign*1155,y,35),(22,270,50),'M_RuinConcrete')
  for y in range(2900,18000,900):box((sign*490,y,7),(12,410,1),'M_LanePaint')
 for y in range(3000,17400,600):box((0,y,7),(12,280,1),'M_LanePaint')
 rng=random.Random(2701)
 # Near architecture: irregular silhouettes and readable open floor slabs.
 buildings=[]
 for sign in (-1,1):
  for j,y in enumerate((2900,5700,9300,12800,16600,20500)):
   x=sign*(3000+rng.randint(0,750));variant='ABCD'[(j+(0 if sign<0 else 2))%4];scale=rng.uniform(1.15,1.8)
   buildings.append((variant,(x,y,0),(scale,scale,rng.uniform(1.1,2.1)),90 if sign<0 else -90))
  for j,y in enumerate((4500,10000,15700,22000)):
   buildings.append(('ABCD'[j],(sign*rng.uniform(6600,10400),y,0),(rng.uniform(1.9,2.6),rng.uniform(1.3,2),rng.uniform(1.5,3.2)),rng.choice((0,90))))
 for variant,p,s,yaw in buildings:
  prop('SM_Ruin_'+variant,p,s,yaw)
  if abs(p[0])<4500:block((p[0],p[1],500),(1500*s[0],1100*s[1],1000))
 # Far city is repeated instanced geometry, with no local lights or collision.
 for sign in (-1,1):
  for j in range(24):
   x=sign*rng.uniform(10000,35000);y=rng.uniform(18000,58000)
   prop('SM_Ruin_'+'ABCD'[j%4],(x,y,-80),(rng.uniform(1.5,3.1),rng.uniform(1.4,2.5),rng.uniform(1.8,4.2)),rng.choice((0,90,180)))
 prop('SM_ArchitectTower',(5400,53000,0));r['tower_world_cm']=[5400,53000,0]
 # The torn elevated highway cuts across the first view without hiding the Tower.
 for sign in (-1,1):
  for i in range(4):
   x=sign*(2700+i*1560);prop('SM_FallenOverpass',(x,7900,1800),yaw=0,roll=sign*(3 if i==0 else 0))
   box((x,7900,850),(190,500,1700),'M_RuinConcrete')
 prop('SM_FallenOverpass',(-1050,7500,280),yaw=-17,roll=-18,pitch=16)
 prop('SM_FallenOverpass',(1450,8200,390),yaw=12,roll=24,pitch=-9)
 # Wrecks and broken services communicate abandonment at human scale.
 for x,y,yaw in [(-550,3300,18),(710,4250,-24),(-260,5650,94),(690,9200,47),(-650,11800,-20),(380,14500,15),(-1300,2500,28)]:
  prop('SM_WreckedSedan',(x,y,12),yaw=yaw);block((x,y,55),(410,160,100))
 for sign in (-1,1):
  for j,y in enumerate(range(2800,18800,2900)):
   prop('SM_DeadStreetlight',(sign*1370,y,45),yaw=0 if sign<0 else 180,roll=sign*(16 if j%3==0 else 4))
   prop('SM_DeadTree',(sign*1750,y+500,30),yaw=rng.uniform(0,360),roll=rng.uniform(-8,8))
 for i in range(105):
  y=rng.uniform(2300,19000);x=rng.choice((-1,1))*rng.uniform(950,3000)
  prop('SM_RubbleCluster',(x,y,30),(rng.uniform(.7,2),rng.uniform(.7,1.7),rng.uniform(.6,1.8)),rng.uniform(0,360))
 for x,y in [(-1450,900),(1200,1100),(-2200,7500),(1850,8450),(-600,16200)]:prop('SM_RubbleCluster',(x,y,400 if y<1500 else 50),(2,2,2),35)
 for x in (-850,-510,510,850):prop('SM_ConcreteBarrier',(x,17800,8),yaw=0)
 # Limited translucent surface area: six two-plane distant plumes, no volumetric grids.
 for index,(x,y,height) in enumerate([(-3200,3700,3400),(4100,10000,6200),(-6700,17500,7600),(9300,25000,11500),(-14000,34000,15000),(1900,36500,14500)]):
  width=height*.38
  for angle in (0,75):
   instance('SmokePlumes',plane,(x,y,height*.5),(width/100,height/100,1),unreal.Rotator(pitch=0,yaw=angle,roll=90),mats['M_RisingSmoke'])
  if index<3:
   instance('SmallFires',plane,(x,y,160),(4,3.2,1),unreal.Rotator(roll=90),mats['M_SmallFire'])
 # Local loose panels on the terrace provide foreground texture and scale.
 for i in range(42):
  x=rng.uniform(-1600,1600);y=rng.uniform(-150,1200)
  if abs(x)<650 and y>800:continue
  box((x,y,403+rng.uniform(0,8)),(rng.uniform(20,90),rng.uniform(15,55),rng.uniform(2,12)),'M_RuinSteel' if i%4==0 else 'M_RuinConcrete',False,unreal.Rotator(yaw=rng.uniform(0,360)))
 compile_bp(env);save(env)
 def spawn(cls,name,p,rot=None):
  a=sub.spawn_actor_from_class(cls,V(p),rot or unreal.Rotator());a.set_actor_label('SURF_'+name);a.set_folder_path('SURFACE/Arrival');return a
 spawn(B.generated_class(env),'Environment',(0,0,0))
 # Sky is a cheap opaque sphere with an analytic cloud field.
 a=spawn(unreal.StaticMeshActor,'AshSky',(0,0,0));c=a.static_mesh_component;c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Sphere'));c.set_material(0,mats['M_AshSky']);c.set_world_scale3d(V((5000,5000,5000)));c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
 sun=spawn(unreal.DirectionalLight,'LateSun',(0,0,15000),unreal.Rotator(pitch=-24,yaw=-45));lc=sun.get_component_by_class(unreal.DirectionalLightComponent);lc.set_intensity(3.2);lc.set_light_color(unreal.LinearColor(1,.76,.52,1));lc.set_mobility(unreal.ComponentMobility.MOVABLE)
 sky=spawn(unreal.SkyLight,'SkyFill',(0,0,12000));lc=sky.get_component_by_class(unreal.SkyLightComponent);lc.set_mobility(unreal.ComponentMobility.MOVABLE);lc.set_intensity(.9);lc.set_editor_property('lower_hemisphere_is_black',False);lc.recapture_sky()
 fog=spawn(unreal.ExponentialHeightFog,'AshHaze',(0,0,0)).get_component_by_class(unreal.ExponentialHeightFogComponent)
 for k,v in [('fog_density',.004),('fog_height_falloff',.09),('fog_max_opacity',.72),('start_distance',2400.),('enable_volumetric_fog',False)]:fog.set_editor_property(k,v)
 pp=spawn(unreal.PostProcessVolume,'SurfaceGrade',(0,0,0));pp.set_editor_property('unbound',True);s=pp.get_editor_property('settings')
 for k,v in [('auto_exposure_min_brightness',2.),('auto_exposure_max_brightness',2.),('auto_exposure_bias',0.),('bloom_intensity',.22),('vignette_intensity',.23),('motion_blur_amount',0.)]:s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
 pp.set_editor_property('settings',s)
 # A local fill makes the shelter readable without lighting the ruined city cyan.
 for y in (-1300,-600):
  a=spawn(unreal.PointLight,'ShelterLight'+str(y),(0,y,740));lc=a.point_light_component;lc.set_intensity(800);lc.set_attenuation_radius(600);lc.set_light_color(unreal.LinearColor(.46,.65,.74,1));lc.set_cast_shadows(False)
 spawn(unreal.PlayerStart,'PlayerStart',(0,-850,508),unreal.Rotator(yaw=90))
 # Reuse the working automatic split door; its trigger is reached on walking out.
 door=A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor')
 spawn(B.generated_class(door),'ExitDoor',(0,-185,400),unreal.Rotator(yaw=90))
 # Existing appearance helper is visual only: no NPC or AI is placed here.
 spawn(B.generated_class(A.load_asset('/Game/Characters/GuardPlayer/BP_PlayerGuardVisual')),'PlayerGuardVisual',(0,0,0))
 spawn(B.generated_class(A.load_asset('/Game/LabTutorial/Basement/BP_CyborgBodyLight')),'CyborgBodyLight',(0,0,0))
 arrival=blueprint('BP_SurfaceArrival');add(arrival,unreal.SceneComponent,'Root');audio=add(arrival,unreal.AudioComponent,'Wind','Root');audio.set_sound(wind);audio.set_editor_property('auto_activate',False);audio.set_editor_property('is_ui_sound',True)
 g=freshgraph(arrival);g.event('ReceiveBeginPlay');camera=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));g.do(g.call('Engine.PlayerCameraManager.StartCameraFade',target=camera,FromAlpha=1.,ToAlpha=0.,Duration=2.8,Color='(R=0,G=0,B=0,A=1)',bShouldFadeAudio=False,bHoldWhenFinished=False));g.do(g.call('Engine.AudioComponent.FadeIn',target=g.get('Wind'),FadeInDuration=3.,FadeVolumeLevel=.55,StartTime=0.));g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=7.));hud(g,'ПОВЕРХНОСТЬ / СЕКТОР 07','СВЯЗЬ С ГОРОДОМ ОТСУТСТВУЕТ',5.);g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=9.));hud(g,'НОВАЯ ЦЕЛЬ / БАШНЯ АРХИТЕКТОРА','Найдите путь через разрушенную магистраль.\nБелая Башня — единственный действующий узел.',10.);compile_bp(arrival);save(arrival);spawn(B.generated_class(arrival),'ArrivalSequence',(0,0,0))
 editor.set_level_viewport_camera_info(V((0,-140,585)),unreal.Rotator(pitch=4,yaw=90))
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Surface map save failed')
 r.update(saved=True,counts={'instances':count,'batches':len(batches),'buildings':len(buildings)+48,'smoke_plumes':6,'original_meshes':len(specs)},departure_cm=[5990,1080,2260],preview_eye_cm=[0,-140,585],note='Native assets compiled and saved. No gameplay test or VRAM measurement.')
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'surface_arrival_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Surface authoring failed; see Saved/surface_arrival_report.json')
