"""Basement expansion, physical electrical switch and K-operated cyborg light."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,add,components,compile_bp,save,Graph,pin,val,link
ROOT='/Game/LabTutorial/Basement';IND='/Game/LabTutorial/Industrial/';MOD='/Game/LabTutorial/FirstFloor/'
saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
backup=os.path.join(saved,'Backups','BasementPower',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
shutil.copy2(os.path.join(content,'Lvl_LabTutorial.umap'),os.path.join(backup,'Lvl_LabTutorial.umap'))
r={'saved':False,'installed':False,'backup':backup,'rooms':[],'note':'Blueprint authoring and compilation only; no gameplay test.'}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
class Flow(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n
 def external(self,name,cls,target):
  q=self.node(self.e.add_get_member_variable_node(name,cls));val(q.find_self_pin(),target);return pin(q,name,True)
 def key(self,key):
  opts=[n for n in self.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|'+key)]
  if len(opts)!=1:raise RuntimeError('Key action missing: '+key)
  q=self.node(self.e.create_node_from_name(opts[0],unreal.Vector2D(),[]));q.set_editor_property('bConsumeInput',False);self.cursor=pin(q,'Pressed',True);return q
def blueprint(name):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor);bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
 compile_bp(bp);add(bp,unreal.SceneComponent,'Root')
 g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);return bp
def member(bp,name,typ,default='None'):
 if name not in list(map(str,B.list_member_variable_names(bp))):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,typ,default)
 B.set_blueprint_variable_instance_editable(bp,name,True)
def material(name,color,glow=False,powered=False):
 path=ROOT+'/'+name
 m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m)
 q=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);q.set_editor_property('constant',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1))
 if glow:
  m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
  if powered:
   s=M.create_material_expression(m,unreal.MaterialExpressionScalarParameter);s.set_editor_property('parameter_name','BuildingPower');s.set_editor_property('default_value',1.)
   mul=M.create_material_expression(m,unreal.MaterialExpressionMultiply);M.connect_material_expressions(q,'',mul,'A');M.connect_material_expressions(s,'',mul,'B');q=mul
  M.connect_material_property(q,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 else:
  M.connect_material_property(q,'',unreal.MaterialProperty.MP_BASE_COLOR)
  for value,prop in [(.6,unreal.MaterialProperty.MP_ROUGHNESS),(.45,unreal.MaterialProperty.MP_METALLIC)]:
   s=M.create_material_expression(m,unreal.MaterialExpressionConstant);s.set_editor_property('r',value);M.connect_material_property(s,'',prop)
 M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(m);save(m);return m
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial');world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();A.make_directory(ROOT)
 removed=[]
 for a in list(sub.get_all_level_actors()):
  if a.get_actor_label().startswith('BASE_') or a.get_actor_label()=='LAB_Corridor_Wall_South':removed.append(a.get_actor_label());sub.destroy_actor(a)
 r['removed']=removed
 cube=A.load_asset('/Engine/BasicShapes/Cube');cylinder=A.load_asset('/Engine/BasicShapes/Cylinder');sphere=A.load_asset('/Engine/BasicShapes/Sphere')
 wall=A.load_asset(IND+'M_Concrete_Dirty');metal=A.load_asset(IND+'M_DistressedMetal');rubber=A.load_asset(IND+'M_Rubber');steel=A.load_asset(MOD+'M_LabSteel')
 floor=A.load_asset(MOD+'M_LabFloor');cyan=material('M_EmergencyWayfinding',(.018,.32,.43),True);amber=material('M_BackupAmber',(1.1,.14,.018),True)
 lampmat=material('M_BuildingWorkLight',(4.5,5.2,5.5),True,True);bodymat=material('M_CyborgBodyLight',(.1,12.,16.),True)
 # A thin animated rim on the actual Quinn mesh makes the body itself glow,
 # without painting the original player materials or allocating render targets.
 shellmat=material('M_CyborgGlowShell',(.16,4.4,6.2),True)
 shellmat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
 fresnel=M.create_material_expression(shellmat,unreal.MaterialExpressionFresnel);fresnel.set_editor_property('exponent',3.);fresnel.set_editor_property('base_reflect_fraction',0.)
 M.connect_material_property(fresnel,'',unreal.MaterialProperty.MP_OPACITY)
 normal=M.create_material_expression(shellmat,unreal.MaterialExpressionVertexNormalWS)
 offset=M.create_material_expression(shellmat,unreal.MaterialExpressionConstant);offset.set_editor_property('r',.18)
 expand=M.create_material_expression(shellmat,unreal.MaterialExpressionMultiply);M.connect_material_expressions(normal,'',expand,'A');M.connect_material_expressions(offset,'',expand,'B');M.connect_material_property(expand,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 M.set_material_usage(shellmat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH);M.recompile_material(shellmat);save(shellmat)
 # Existing first-floor assets can be loaded in other editors. Apply a new
 # powered material as a map-instance override instead of modifying those assets.
 env=blueprint('BP_BasementExpansion');batches={};count=0
 def inst(key,mesh,p,size=(1,1,1),yaw=0,mat=None,block=False,hidden=False):
  global count
  if key not in batches:
   c=add(env,unreal.InstancedStaticMeshComponent,key,'Root');c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.clear_instances();c.set_collision_profile_name('BlockAll' if block else 'NoCollision')
   if mat:c.set_material(0,mat)
   c.set_editor_property('cast_shadow',not hidden)
   if hidden:c.set_visibility(False);c.set_hidden_in_game(True)
   batches[key]=c
  batches[key].add_instance(unreal.Transform(location=V(p),rotation=unreal.Rotator(yaw=yaw),scale=V(size)),world_space=False);count+=1
 def box(p,size,mat=metal,block=True,hidden=False,yaw=0):inst(('InvisibleBlockers' if hidden else 'Boxes_'+mat.get_name()),cube,p,tuple(v/100 for v in size),yaw,mat,block,hidden)
 def prop(name,p,yaw=0,coll=None):
  inst(name,A.load_asset(MOD+name),p,yaw=yaw)
  if coll:box((p[0],p[1],p[2]+coll[2]/2),coll,rubber,True,True,yaw)
 def wx(x,y0,y1):
  if y1<=y0:return
  box((x,(y0+y1)/2,190),(24,y1-y0,380),wall)
  for s in (-1,1):
   box((x+s*13,(y0+y1)/2,33),(2,y1-y0,66),metal,False)
   box((x+s*13,(y0+y1)/2,342),(2,y1-y0,34),metal,False)
 def wy(y,x0,x1):
  if x1<=x0:return
  box(((x0+x1)/2,y,190),(x1-x0,24,380),wall)
  for s in (-1,1):
   box(((x0+x1)/2,y+s*13,33),(x1-x0,2,66),metal,False)
   box(((x0+x1)/2,y+s*13,342),(x1-x0,2,34),metal,False)
 def ox(x,y0,y1,y):wx(x,y0,y-160);wx(x,y+160,y1);box((x,y,355),(24,320,50),metal)
 def oy(y,x0,x1,x):wy(y,x0,x-160);wy(y,x+160,x1);box((x,y,355),(320,24,50),metal)
 def room(name,x0,x1,y0,y1):
  box(((x0+x1)/2,(y0+y1)/2,-15),(x1-x0,y1-y0,30),floor)
  box(((x0+x1)/2,(y0+y1)/2,390),(x1-x0,y1-y0,20),metal)
  r['rooms'].append({'name':name,'bounds':[x0,x1,y0,y1]})
 def sign(text,p,yaw=180,size=17):
  a=sub.spawn_actor_from_class(unreal.TextRenderActor,V(p),unreal.Rotator(yaw=yaw));a.set_actor_label('BASE_Sign_'+str(len(signs)));a.set_folder_path('LAB/Basement/Wayfinding');c=a.text_render;c.set_text(unreal.Text(text));c.set_world_size(size);c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_text_render_color(unreal.Color(r=115,g=225,b=240,a=255));signs.append(a)
 signs=[]
 # Replace one continuous corridor wall with a real 4 m side passage.
 wy(-230,900,1600);wy(-230,2000,2400);box((1800,-230,440),(400,28,60),wall)
 room('Технический проход',1600,2000,-1700,-230);wx(1600,-1700,-230);wx(2000,-1700,-230)
 room('Распределительный коридор',700,2700,-2100,-1700);oy(-1700,700,2700,1800);oy(-2100,700,2700,1700)
 room('Склад',-200,700,-2300,-1100);wx(-200,-2300,-1100);wy(-1100,-200,700);wy(-2300,-200,700);ox(700,-2300,-1100,-1900)
 room('Мастерская',1200,2200,-2900,-2100);wx(1200,-2900,-2100);wx(2200,-2900,-2100);wy(-2900,1200,2200)
 room('Электрощитовая',2700,3600,-2300,-1200);ox(2700,-2300,-1200,-1900);wx(3600,-2300,-1200);wy(-2300,2700,3600);wy(-1200,2700,3600)
 # Close corridor ends around the two actual doorways.
 ox(700,-2100,-1700,-1900);ox(2700,-2100,-1700,-1900)
 # Shelving rows with collision only on uprights / loaded bays, leaving a broad centre aisle.
 for x in (0,490):
  for y in (-1330,-1690,-2050):
   for sx in (-68,68):
    for sy in (-58,58):box((x+sx,y+sy,126),(7,7,252),steel)
   for z in (12,92,172,247):box((x,y,z),(148,132,6),metal)
   for z in (48,128,208):
    for sx in (-36,36):
     box((x+sx,y,z),(59,80,63),metal);box((x+sx,y-41,z+6),(34,2,18),steel,False)
   box((x,y,124),(147,131,248),rubber,True,True)
 for x,y in ((-75,-2210),(305,-2190)):
  inst('StorageDrums',cylinder,(x,y,58),(.64,.64,1.16),mat=metal,block=True)
  for z in (9,104):inst('DrumBands',cylinder,(x,y,z),(.67,.67,.065),mat=steel)
 prop('SM_LabUtilityBench',(1460,-2825,0),180,(190,65,93));prop('SM_ModernConsole',(1970,-2825,0),180,(180,76,84))
 prop('SM_LabEquipmentCabinet',(1255,-2450,0),90,(90,48,216));prop('SM_LabSupplyCart',(2050,-2420,0),0,(66,42,94))
 # Electrical cabinets, busbars and a compact generator set.
 for x in (2820,2940,3060,3180):prop('SM_LabEquipmentCabinet',(x,-1255,0),0,(90,48,216))
 box((3050,-2140,38),(350,190,76),metal)
 for x in (2940,3090):
  inst('GeneratorTurbines',cylinder,(x,-2140,130),(.92,.92,2.35),90,metal,False)
  box((x,-2140,132),(92,180,150),rubber,True,True)
  for z in (95,150):box((x,-2140,z),(113,198,8),steel)
 for x in range(2800,3501,140):
  box((x,-1300,330),(110,35,24),steel,False)
  for yy in (-1315,-1300,-1285):inst('BusbarCables',cylinder,(x,yy,324),(.045,.045,1.4),mat=rubber)
 prop('SM_ModernServerRack',(3515,-2190,0),-90,(86,100,240))
 # Low-powered backup LEDs stay on; working fixtures belong to the power circuit.
 for x,y in [(1800,-330),(1800,-800),(1800,-1300),(950,-1900),(1500,-1900),(2200,-1900),(2600,-1900),(2810,-1750),(3300,-1750),(1700,-2600)]:
  box((x,y,365),(115,44,10),metal,False);box((x,y,358),(96,31,3),lampmat,False)
  a=sub.spawn_actor_from_class(unreal.PointLight,V((x,y,285)),unreal.Rotator());a.set_actor_label('BASE_WorkLight_%d_%d'%(x,y));a.set_folder_path('LAB/Basement/WorkingLights');a.point_light_component.set_intensity(700);a.point_light_component.set_attenuation_radius(570);a.point_light_component.set_cast_shadows(False);a.point_light_component.set_light_color(unreal.LinearColor(r=.8,g=.88,b=1,a=1))
 for y in range(-350,-1651,-130):box((1620,y,38),(3,22,4),cyan,False)
 for x in range(800,2700,130):box((x,-2075,38),(22,3,4),cyan,False)
 for x,y in [(750,-1900),(2635,-1900),(3400,-1660)]:
  box((x,y,270),(9,34,9),amber,False)
  a=sub.spawn_actor_from_class(unreal.PointLight,V((x,y,230)),unreal.Rotator());a.set_actor_label('BASE_BackupLamp_%d'%x);a.set_folder_path('LAB/Basement/Emergency');a.tags=[unreal.Name('EmergencyBackup')];a.point_light_component.set_intensity(18);a.point_light_component.set_attenuation_radius(240);a.point_light_component.set_cast_shadows(False);a.point_light_component.set_light_color(unreal.LinearColor(r=1,g=.2,b=.04,a=1))
 for x in (50,490):
  for y in (-1420,-2000):
   a=sub.spawn_actor_from_class(unreal.PointLight,V((x,y,280)),unreal.Rotator());a.set_actor_label('BASE_WorkLight_Storage_%d_%d'%(x,y));a.set_folder_path('LAB/Basement/WorkingLights');a.point_light_component.set_intensity(700);a.point_light_component.set_attenuation_radius(530);a.point_light_component.set_cast_shadows(False)
 sign('ТЕХНИЧЕСКИЙ БЛОК  /  ПИТАНИЕ',(1800,-255,314),90,17)
 sign('СКЛАД  ←      ЭЛЕКТРОЩИТОВАЯ  →',(1800,-2078,285),90,17)
 sign('МАСТЕРСКАЯ',(1700,-2870,285),90,20)
 sign('ГЛАВНЫЙ РАСПРЕДЕЛИТЕЛЬНЫЙ ЩИТ',(3573,-1740,310),180,15)
 sign('СКЛАД ОБОРУДОВАНИЯ',(675,-1900,320),180,17)
 for h,c,n in components(env):
  if isinstance(c,unreal.SceneComponent):c.set_mobility(unreal.ComponentMobility.STATIC)
 compile_bp(env);save(env)
 expansion=sub.spawn_actor_from_class(B.generated_class(env),V((0,0,0)),unreal.Rotator());expansion.set_actor_label('BASE_Expansion');expansion.set_folder_path('LAB/Basement/Architecture')
 r['instances']=count;r['batches']=len(batches)
 # Player-mounted cyan lamps: attach to actual animated bones rather than the camera.
 body=blueprint('BP_CyborgBodyLight')
 shell=add(body,unreal.SkeletalMeshComponent,'BodyGlowShell','Root');shell.set_skeletal_mesh_asset(A.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'));shell.set_mobility(unreal.ComponentMobility.MOVABLE);shell.set_collision_profile_name('NoCollision');shell.set_editor_property('cast_shadow',False);shell.set_visibility(False)
 for i in range(shell.get_num_materials()):shell.set_material(i,shellmat)
 light=add(body,unreal.PointLightComponent,'BodyFill','Root');light.set_editor_property('intensity_units',unreal.LightUnits.LUMENS);light.set_intensity(12000);light.set_attenuation_radius(1600);light.set_light_color(unreal.LinearColor(r=.65,g=.88,b=1,a=1));light.set_cast_shadows(False);light.set_editor_property('source_radius',38.);light.set_visibility(False)
 anchors=[('ChestEmitter','spine_03',(10,0,0),(.09,.06,.07)),('BackEmitter','spine_03',(-9,0,0),(.08,.05,.1)),('LeftArmEmitter','lowerarm_l',(0,0,0),(.055,.055,.12)),('RightArmEmitter','lowerarm_r',(0,0,0),(.055,.055,.12)),('LeftLegEmitter','calf_l',(0,0,0),(.06,.06,.14)),('RightLegEmitter','calf_r',(0,0,0),(.06,.06,.14))]
 for name,bone,p,scale in anchors:
  c=add(body,unreal.StaticMeshComponent,name,'Root');c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_static_mesh(sphere);c.set_material(0,bodymat);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(scale));c.set_visibility(False)
 member(body,'bBodyLightOn',B.get_basic_type_by_name('bool'),'true');member(body,'bReady',B.get_basic_type_by_name('bool'),'false');compile_bp(body);g=Flow(body)
 g.event('ReceiveBeginPlay');g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=10.5))
 player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0));mesh=g.external('Mesh','/Script/Engine.Character',player)
 g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get('BodyGlowShell'),Parent=mesh,SocketName='None',LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
 g.do(g.call('Engine.SkinnedMeshComponent.SetLeaderPoseComponent',target=g.get('BodyGlowShell'),NewLeaderBoneComponent=mesh,bForceUpdate=True,bInFollowerShouldTickPose=False))
 g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get('BodyGlowShell'),bNewVisibility=True,bPropagateToChildren=False))
 for name,bone,_,_ in anchors+[('BodyFill','spine_03',(0,0,0),(1,1,1))]:
  g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(name),Parent=mesh,SocketName=bone,LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
  g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=True,bPropagateToChildren=False))
 g.set('bReady',True)
 g.key('K');g.branch(g.get('bReady'));g.set('bBodyLightOn',g.math('Not_PreBool',A=g.get('bBodyLightOn')))
 for name in ['BodyFill','BodyGlowShell']+[v[0] for v in anchors]:g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=g.get('bBodyLightOn'),bPropagateToChildren=False))
 compile_bp(body);cdo=unreal.get_default_object(B.generated_class(body));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',80);save(body)
 a=sub.spawn_actor_from_class(B.generated_class(body),V((0,0,0)),unreal.Rotator());a.set_actor_label('BASE_CyborgBodyLight');a.set_folder_path('LAB/00_Opening')
 # Each actual main light is referenced by the circuit instance: no Tick search,
 # no editor-only Python at runtime, no global console rendering toggles.
 mains=[];surfaces=[]
 for a in sub.get_all_level_actors():
  n=a.get_actor_label()
  if isinstance(a,unreal.Light):
   emergency='EmergencyBackup' in list(map(str,a.tags))
   # Capsule and hologram projectors are powered independently by reserve cells.
   reserve=any(s in n.lower() for s in ('capsule','holo','projector'))
   if not emergency and not reserve:mains.append(a)
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   if not c.static_mesh:continue
   for i in range(c.get_num_materials()):
    mat=c.get_material(i)
    if mat and mat.get_name()=='M_LabWhiteLight':c.set_material(i,lampmat)
   if any(c.get_material(i) and c.get_material(i).get_name() in ('M_BuildingWorkLight','M_LabWhiteLight') for i in range(c.get_num_materials())):surfaces.append(c)
   if n.startswith(('LAB_RouteLamp_Lens','REF_CeilingLampDiffuser')):
    c.set_material(0,lampmat)
    if c not in surfaces:surfaces.append(c)
 mains.sort(key=lambda a:(a.get_actor_location().z,a.get_actor_location().x))
 circuit=blueprint('BP_BuildingPower');zone=add(circuit,unreal.BoxComponent,'SwitchZone','Root');zone.set_editor_property('relative_location',V((-140,0,120)));zone.set_box_extent(V((135,130,130)));zone.set_collision_profile_name('Trigger');zone.set_editor_property('generate_overlap_events',True)
 for name,p,size,mat in [('BreakerCabinet',(0,0,155),(42,154,240),metal),('BreakerFace',(-24,0,155),(5,136,220),rubber),('SwitchLever',(-36,0,137),(16,12,62),steel),('StandbyLED',(-29,-48,221),(4,9,9),amber)]:
  c=add(circuit,unreal.StaticMeshComponent,name,'Root');c.set_static_mesh(cube);c.set_material(0,mat);c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(tuple(v/100 for v in size)));c.set_collision_profile_name('BlockAll' if name=='BreakerCabinet' else 'NoCollision')
 audio=add(circuit,unreal.AudioComponent,'GeneratorAudio','Root');audio.set_sound(A.load_asset('/Game/LabTutorial/Elevator/S_FreightMotor'));audio.set_editor_property('auto_activate',False);audio.set_editor_property('volume_multiplier',.3)
 settings=audio.get_editor_property('attenuation_overrides');settings.set_editor_property('spatialize',True);settings.set_editor_property('attenuation_shape_extents',V((150,0,0)));settings.set_editor_property('falloff_distance',900.);audio.set_editor_property('attenuation_overrides',settings);audio.set_editor_property('override_attenuation',True)
 for name,typ,default in [('bBuildingPowered',B.get_basic_type_by_name('bool'),'false'),('bRestoringPower',B.get_basic_type_by_name('bool'),'false'),('PromptWidget',B.get_object_reference_type(unreal.UserWidget),'None')]:member(circuit,name,typ,default)
 for i,a in enumerate(mains):member(circuit,'CircuitLight_%03d'%i,B.get_object_reference_type(unreal.Actor))
 for i,c in enumerate(surfaces):member(circuit,'CircuitSurface_%03d'%i,B.get_object_reference_type(unreal.MeshComponent))
 notices=[]
 for a in sub.get_all_level_actors():
  if isinstance(a,unreal.TextRenderActor) and 'ПИТАНИЕ ОТКЛЮЧЕНО' in str(a.text_render.text):notices.append(a.text_render)
 for i,c in enumerate(notices):member(circuit,'PowerNotice_%02d'%i,B.get_object_reference_type(unreal.TextRenderComponent))
 compile_bp(circuit);g=Flow(circuit)
 def pc():return g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 def player():return g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
 def hud(title,message,lifetime=8.,store=False):
  source=A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint')
  q=g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(source).get_path_name(),OwningPlayer=pc()));widget=g.out(q)
  for prop,text in [('HUDTitle',title),('HUDMessage',message)]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=prop,Value=text))
  g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=widget,PropertyName='HUDLifetime',Value=lifetime))
  if store:g.set('PromptWidget',widget)
  g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=48))
 def hide_prompt():
  q=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('PromptWidget'))));otherwise=q.find_else_pin()
  g.do(g.call('UMG.Widget.RemoveFromParent',target=g.get('PromptWidget')));reset=g.set('PromptWidget','None');link(otherwise,reset.find_execute_pin())
 g.event('ReceiveBeginPlay')
 for i in range(len(mains)):g.do(g.call('Engine.Actor.SetActorHiddenInGame',target=g.get('CircuitLight_%03d'%i),bNewHidden=True))
 for i in range(len(surfaces)):g.do(g.call('Engine.MeshComponent.SetScalarParameterValueOnMaterials',target=g.get('CircuitSurface_%03d'%i),ParameterName='BuildingPower',ParameterValue=0.))
 g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=12.));g.branch(g.math('Not_PreBool',A=g.get('bBuildingPowered')));hud('РЕЗЕРВНОЕ ПИТАНИЕ','Найдите электрощитовую в техническом блоке.\n[K] Подсветка тела · [E] Взаимодействие',12.)
 begin=g.e.add_component_bound_event_node(zone,'OnComponentBeginOverlap');g.cursor=pin(begin,'then',True);g.branch(g.math('EqualEqual_ObjectObject',A=pin(begin,'OtherActor',True),B=player()));g.branch(g.math('Not_PreBool',A=g.get('bBuildingPowered')));g.branch(g.math('Not_PreBool',A=g.get('bRestoringPower')))
 check=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=g.get('PromptWidget'))));g.cursor=check.find_else_pin();hud('ГЛАВНЫЙ РУБИЛЬНИК','[E]  ВКЛЮЧИТЬ ПИТАНИЕ',86400.,True)
 end=g.e.add_component_bound_event_node(zone,'OnComponentEndOverlap');g.cursor=pin(end,'then',True);g.branch(g.math('EqualEqual_ObjectObject',A=pin(end,'OtherActor',True),B=player()));g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('SwitchZone'),Other=player()))));hide_prompt()
 g.key('E');g.branch(g.math('Not_PreBool',A=g.get('bBuildingPowered')));g.branch(g.math('Not_PreBool',A=g.get('bRestoringPower')));g.branch(g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('SwitchZone'),Other=player())));g.set('bRestoringPower',True);hide_prompt()
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get('SwitchLever'),NewRotation='(Pitch=50,Yaw=0,Roll=0)',bSweep=False,bTeleport=False))
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=IND+'S_BlastDoorThud',Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=.6));g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=1.2));g.do(g.call('Engine.AudioComponent.FadeIn',target=g.get('GeneratorAudio'),FadeInDuration=2.,FadeVolumeLevel=.3,StartTime=0))
 for i in range(len(mains)):
  g.do(g.call('Engine.Actor.SetActorHiddenInGame',target=g.get('CircuitLight_%03d'%i),bNewHidden=False))
  if i%8==7:g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=.12))
 for i in range(len(surfaces)):g.do(g.call('Engine.MeshComponent.SetScalarParameterValueOnMaterials',target=g.get('CircuitSurface_%03d'%i),ParameterName='BuildingPower',ParameterValue=1.))
 notice_skip=None
 for i in range(len(notices)):
  notice=g.get('PowerNotice_%02d'%i)
  check=g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=notice)))
  if notice_skip:link(notice_skip,check.find_execute_pin())
  g.do(g.call('Engine.TextRenderComponent.K2_SetText',target=notice,Value=g.out(g.call('Engine.KismetTextLibrary.Conv_StringToText',InString='ПИТАНИЕ ВОССТАНОВЛЕНО · Л-1 ЗАБЛОКИРОВАН'))))
  notice_skip=check.find_else_pin()
 restored=g.set('bBuildingPowered',True)
 if notice_skip:link(notice_skip,restored.find_execute_pin())
 g.set('bRestoringPower',False);g.do(g.call('Engine.GameplayStatics.PlaySound2D',Sound='/Game/LabTutorial/Elevator/S_FreightArrival',VolumeMultiplier=.5));hud('ЭЛЕКТРОПИТАНИЕ ВОССТАНОВЛЕНО','Освещение подвала и первого этажа включено.\nВернитесь к грузовому лифту.',8.)
 compile_bp(circuit);cdo=unreal.get_default_object(B.generated_class(circuit));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0);cdo.set_editor_property('input_priority',90);save(circuit)
 panel=sub.spawn_actor_from_class(B.generated_class(circuit),V((3500,-1700,0)),unreal.Rotator());panel.set_actor_label('BASE_MainPowerSwitch');panel.set_folder_path('LAB/Basement/Interactables')
 for i,a in enumerate(mains):panel.set_editor_property('CircuitLight_%03d'%i,a)
 for i,c in enumerate(surfaces):panel.set_editor_property('CircuitSurface_%03d'%i,c)
 for i,c in enumerate(notices):panel.set_editor_property('PowerNotice_%02d'%i,c)
 r.update(main_lights=len(mains),powered_lamp_meshes=len(surfaces),body_light_key='K',interaction_key='E',restore_seconds=1.2+(len(mains)//8)*.12)
 staged=os.path.join(saved,'BasementPowerStaged','Lvl_LabTutorial.umap');os.makedirs(os.path.dirname(staged),exist_ok=True)
 unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+staged.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(staged):raise RuntimeError('Map did not save')
 r.update(saved=True,staged_map=staged)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'basement_power_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Basement/power authoring failed; see report')

