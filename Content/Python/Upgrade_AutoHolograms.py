"""Six native automatic holographic exhibits. Preserves projectors and level layout.
Auto boot waits for the existing awakening control-release flag. F remains a
focused toggle. Geometry, materials, animation and graphs are packaged assets.
"""
import unreal,os,sys,math,random,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,V,components,add,pin,val,link,compile_bp,save
src=os.path.join(unreal.Paths.project_content_dir(),'Python/Upgrade_PlayerVisor.py')
exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
ROOT='/Game/LabTutorial/Holograms';root=os.path.abspath(unreal.Paths.project_dir());report={'saved':False,'assets':[],'gameplay_tested':False}
def back(path):
 source=os.path.join(root,'Content',path.removeprefix('/Game/')+'.uasset')
 if os.path.isfile(source):
  dest=os.path.join(report['backup'],path.removeprefix('/Game/')+'.uasset');os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(source,dest)
def volume_material():
 path=ROOT+'/M_HoloVolume';back(path);mat=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_HoloVolume',ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(mat)
 for k,v in {'blend_mode':unreal.BlendMode.BLEND_ADDITIVE,'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,'used_with_skeletal_mesh':True}.items():mat.set_editor_property(k,v)
 custom=M.create_material_expression(mat,unreal.MaterialExpressionCustom,0,0);inputs=[]
 for name in ('Clock','Start','Pos','Center','Radius','Facing'):
  ci=unreal.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
 custom.set_editor_property('inputs',inputs);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4);custom.set_editor_property('code',open(os.path.join(root,'SourceAssets/HologramsV2/HoloVolume.hlsl'),encoding='utf-8-sig').read())
 for cls,name in [(unreal.MaterialExpressionTime,'Clock'),(unreal.MaterialExpressionScalarParameter,'Start'),(unreal.MaterialExpressionWorldPosition,'Pos'),(unreal.MaterialExpressionObjectPositionWS,'Center'),(unreal.MaterialExpressionObjectRadius,'Radius'),(unreal.MaterialExpressionFresnel,'Facing')]:
  obj=M.create_material_expression(mat,cls)
  if name=='Start':obj.set_editor_property('parameter_name','ActivationTime');obj.set_editor_property('default_value',-100.);obj.set_editor_property('use_custom_primitive_data',True);obj.set_editor_property('primitive_data_index',0)
  assert M.connect_material_expressions(obj,'',custom,name)
 for alpha,prop in [(False,unreal.MaterialProperty.MP_EMISSIVE_COLOR),(True,unreal.MaterialProperty.MP_OPACITY)]:
  mask=M.create_material_expression(mat,unreal.MaterialExpressionComponentMask)
  for ch in ('r','g','b','a'):mask.set_editor_property(ch,ch=='a' if alpha else ch!='a')
  assert M.connect_material_expressions(custom,'',mask,'');assert M.connect_material_property(mask,'',prop)
 M.recompile_material(mat);save(mat);return mat
try:
 report['backup']=os.path.join(root,'Saved/Backups/AutoHolograms',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(report['backup'],exist_ok=True)
 textures=[]
 for i in range(1,7):
  task=unreal.AssetImportTask()
  for k,v in dict(filename=os.path.join(root,'SourceAssets/HologramsV2/T_HoloV2_%02d.png'%i),destination_path=ROOT,automated=True,replace_existing=True,save=True).items():task.set_editor_property(k,v)
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=A.load_asset(ROOT+'/T_HoloV2_%02d'%i);t.set_editor_property('max_texture_size',1024);t.set_editor_property('lod_group',unreal.TextureGroup.TEXTUREGROUP_UI);save(t);textures.append(t)
 # Reuse the established, correctly oriented world-space projection shader.
 legacy=os.path.join(root,'Content/Python/Build_InteractiveHolograms.py');scope={}
 code=open(legacy,encoding='utf-8-sig').read().split('\ntry:\n')[0].replace('(48.0+band*6)','(7.5+band*4)').replace('age/1.15','age/1.65').replace('age/1.3','age/1.9')
 exec(compile(code,legacy,'exec'),scope);scope['textures']=textures;back(ROOT+'/M_ArchiveProjection');master=scope['material']()
 for i,t in enumerate(textures):back(ROOT+'/MI_Archive%02d'%(i+1));scope['instance']('MI_Archive%02d'%(i+1),master,t)
 holo=volume_material();cube=A.load_asset('/Engine/BasicShapes/Cube');cylinder=A.load_asset('/Engine/BasicShapes/Cylinder');hero=A.load_asset('/Game/Characters/BlackSentinel/SK_BlackSentinel');idle=A.load_asset('/Game/Characters/BlackSentinel/Animations/BS_MM_Idle');player_class=B.generated_class(A.load_asset(PLAYER)).get_path_name()
 for i in range(1,7):
  bp=A.load_asset(ROOT+'/BP_ArchiveProjector_%02d'%i);back(ROOT+'/BP_ArchiveProjector_%02d'%i)
  member(bp,'bAutoHologramStarted','bool','false');member(bp,'bFocusedInteraction','bool','false');member(bp,'ProjectionActive','bool','false')
  vr=add(bp,unreal.SceneComponent,'HoloVolumeRoot');vr.set_mobility(unreal.ComponentMobility.MOVABLE);vr.set_visibility(False,True)
  display=[]
  def shape(name,asset,pos,size,rot=None):
   c=add(bp,unreal.StaticMeshComponent,name,'HoloVolumeRoot');c.set_static_mesh(asset);c.set_material(0,holo);c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_scale3d',V(size));c.set_editor_property('cast_shadow',False);c.set_editor_property('disallow_nanite',True);c.set_collision_profile_name('NoCollision');c.set_mobility(unreal.ComponentMobility.MOVABLE)
   if rot:c.set_editor_property('relative_rotation',rot)
   display.append(name);return c
  kind=(i-1)%3
  if kind==0:
   c=add(bp,unreal.SkeletalMeshComponent,'HoloSentinel','HoloVolumeRoot');c.set_skeletal_mesh_asset(hero);c.set_material(0,holo);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('relative_location',V((0,-38,40)));c.set_editor_property('relative_scale3d',V((1.25,1.25,1.25)));c.set_editor_property('relative_rotation',unreal.Rotator(yaw=180));c.set_editor_property('forced_lod_model',3);c.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED);display.append('HoloSentinel')
  elif kind==1:
   shape('HoloMapPlatform',cube,(0,-22,105),(1.8,1.35,.018))
   rng=random.Random(41)
   for row in range(5):
    for col in range(6):
     h=rng.uniform(22,89);x=-75+col*30;y=-76+row*27
     shape('HoloBuilding_%02d_%02d'%(row,col),cube,(x,y,107+h/2),(.14+rng.random()*.07,.16,h/100))
   for j in range(6):shape('HoloStreet_%02d'%j,cube,(-90+j*36,-22,107),(.01,1.5,.006))
   for j in range(5):shape('HoloCross_%02d'%j,cube,(0,-90+j*34,107),(1.95,.01,.006))
  else:
   shape('HoloGeneratorBase',cube,(0,-35,170),(1.1,.7,.06))
   for j in range(3):shape('HoloGenerator_%d'%j,cube,(-30+j*30,-35,192),(.24,.55,.4))
   shape('HoloGeneratorRotor',cylinder,(-66,-35,191),(.38,.38,.22),unreal.Rotator(pitch=0,roll=90,yaw=0))
  # All displays use regular rasterized translucency (Nanite does not support it).
  for h,c,n in components(bp):
   if isinstance(c,unreal.StaticMeshComponent) and n.startswith('Projection'):c.set_editor_property('disallow_nanite',True)
  compile_bp(bp)
  g=Flow(bp,'Holo_SetProjection');enabled=g.arg('Enabled',B.get_basic_type_by_name('bool'));g.set('ProjectionActive',enabled)
  for name in ('Projection','ProjectionBacking','ProjectionBeam','HoloVolumeRoot'):g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=enabled,bPropagateToChildren=True))
  g.branch(enabled);now=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))
  for name in ['Projection','ProjectionBeam']+display:g.do(g.call('Engine.PrimitiveComponent.SetCustomPrimitiveDataFloat',target=g.get(name),DataIndex=0,Value=now))
  g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=ROOT+'/S_ProjectorStartup',Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=.14))
  compile_bp(bp)
  g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
  g.event('ReceiveBeginPlay');g.set('ProjectionActive',False);g.set('bAutoHologramStarted',False);g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.08))
  for name in ('Projection','ProjectionBacking','ProjectionBeam','HoloVolumeRoot','InteractPrompt'):g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=False,bPropagateToChildren=True))
  if kind==0:g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get('HoloSentinel'),NewAnimToPlay=idle.get_path_name(),bLooping=True))
  g.event('ReceiveTick');g.branch(g.math('Not_PreBool',A=g.get('bAutoHologramStarted')))
  pawn=g.out(g.do(g.call('Engine.GameplayStatics.GetActorOfClass',ActorClass=player_class)));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=pawn)))
  getter=g.node(g.e.add_get_member_variable_node('bVisorReady',player_class));val(getter.find_self_pin(),pawn);g.branch(pin(getter,'bVisorReady',True))
  pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0));g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=pc))))
  g.set('bAutoHologramStarted',True);g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=(i-1)*.14));call=g.selfcall('Holo_SetProjection');val(pin(call,'Enabled'),True);g.do(call);g.do(g.call('Engine.Actor.SetActorTickEnabled',bEnabled=False))
  key=g.node(g.e.create_node_from_name(next(x for x in g.e.list_available_nodes([]) if x.endswith('|KeyboardEvents|F')),unreal.Vector2D(),[]));key.set_editor_property('bConsumeInput',False);g.cursor=pin(key,'Pressed',True);g.branch(g.get('bAutoHologramStarted'));g.branch(g.get('bFocusedInteraction'));call=g.selfcall('Holo_SetProjection');val(pin(call,'Enabled'),g.math('Not_PreBool',A=g.get('ProjectionActive')));g.do(call)
  compile_bp(bp);save(bp);report['assets'].append(bp.get_path_name())
 report.update(saved=True,activation='awakening control release: bVisorReady and movement unlocked',stagger_seconds=.14,boot_seconds=1.65,real_3d_heroes=2,miniature_buildings=60,map_modified=False)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:open(os.path.join(root,'Saved/auto_holograms_v2.json'),'w',encoding='utf8').write(json.dumps(report,ensure_ascii=False,indent=2))
if not report['saved']:raise RuntimeError('Automatic hologram upgrade incomplete')

