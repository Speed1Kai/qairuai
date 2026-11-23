from Industrial_Common import *
import math,json

def import_models(mats):
 source=os.path.join(unreal.Paths.project_content_dir(),'LabTutorial','Industrial','Source')
 with open(os.path.join(source,'mesh_manifest.json')) as f:manifest=json.load(f)
 assets={}
 for spec in manifest:
  name=spec['name'];path=ROOT+'/'+name
  if A.does_asset_exist(path):assets[name]=A.load_asset(path);continue
  task=unreal.AssetImportTask();task.set_editor_property('filename',os.path.abspath(os.path.join(source,name+'.obj')))
  for k,v in {'destination_path':ROOT,'destination_name':name,'automated':True,'replace_existing':True,'save':True}.items():task.set_editor_property(k,v)
  opts=unreal.FbxImportUI()
  for k,v in {'import_materials':False,'import_textures':False,'import_as_skeletal':False,'import_animations':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_STATIC_MESH}.items():opts.set_editor_property(k,v)
  smdata=opts.get_editor_property('static_mesh_import_data');smdata.set_editor_property('combine_meshes',True);smdata.set_editor_property('auto_generate_collision',False)
  task.set_editor_property('options',opts);unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Import failed '+name)
  assets[name]=mesh
 for name,mesh in assets.items():
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   key=str(slot.get_editor_property('material_slot_name'))
   match=next((n for n in mats if n.lower() in key.lower()),'M_DistressedMetal')
   mesh.set_material(i,mats[match])
  if name in ('SM_HeavyDoorPanel','SM_DockingGenerator','SM_IndustrialWorkbench'):
   sub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
   if sub:
    sub.remove_collisions(mesh);sub.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)
  save(mesh)
 return assets

def import_sound(name):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 file=os.path.abspath(os.path.join(unreal.Paths.project_content_dir(),'LabTutorial','Industrial','Source',name+'.wav'))
 t=unreal.AssetImportTask()
 for k,v in {'filename':file,'destination_path':ROOT,'automated':True,'save':True}.items():t.set_editor_property(k,v)
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);return A.load_asset(path)

def build_steam(mats,report):
 path=ROOT+'/NS_PressureVent'
 if A.does_asset_exist(path):system=A.load_asset(path)
 else:
  source=unreal.load_asset('/Niagara/DefaultAssets/Templates/Systems/DirectionalBurstLightweight')
  system=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('NS_PressureVent',ROOT,source)
 if not system:raise RuntimeError('Niagara pressure system duplication failed')
 def setrange(o,prop,lo,hi):
  d=o.get_editor_property(prop);d.set_editor_property('Min',lo);d.set_editor_property('Max',hi);o.set_editor_property(prop,d)
 emitters=[]
 for o in unreal.ObjectIterator(unreal.Object):
  if isinstance(o,type):continue
  if not unreal.SystemLibrary.get_path_name(o).startswith(system.get_path_name()+':'):continue
  if o.get_class().get_name()=='NiagaraStatelessEmitter':emitters.append(o)
 if not emitters:raise RuntimeError('Niagara lightweight emitter not found')
 for emitter in emitters:
  infos=list(emitter.get_editor_property('SpawnInfos'))
  for info in infos:
   amount=info.get_editor_property('Amount');amount.set_editor_property('Min',20);amount.set_editor_property('Max',24);info.set_editor_property('Amount',amount)
  emitter.set_editor_property('SpawnInfos',infos)
  for renderer in emitter.get_editor_property('RendererProperties'):
   if renderer.get_class().get_name()=='NiagaraSpriteRendererProperties':renderer.set_editor_property('material',mats['M_PressureSteam'])
  for module in emitter.get_editor_property('Modules'):
   cls=module.get_class().get_name()
   if cls.endswith('_InitializeParticle'):
    setrange(module,'LifetimeDistribution',1.2,2.0)
    d=module.get_editor_property('SpriteSizeDistribution')
    for k,size in [('Min',38),('Max',65)]:
     v=d.get_editor_property(k);v.set_editor_property('X',float(size));v.set_editor_property('Y',float(size));d.set_editor_property(k,v)
    module.set_editor_property('SpriteSizeDistribution',d)
   if cls.endswith('_AddVelocity'):
    setrange(module,'ConeVelocityDistribution',35.,65.);setrange(module,'PointVelocityDistribution',15.,35.)
   if cls.endswith(('_GravityForce','_CurlNoiseForce')):module.set_editor_property('bModuleEnabled',False)
  emitter.set_editor_property('FixedBounds',unreal.Box(min=V((-220,-220,-50)),max=V((220,220,300))))
 save(system);report['niagara']={'asset':path,'burst_particles_per_emitter':'20–24','lifetime_seconds':'1.2–2.0','emitters':len(emitters),'volumetric_fluids':False}
 return system

def build_shake():
 bp=bp_asset('BP_BlastDoorImpactShake',unreal.LegacyCameraShake);compile_bp(bp)
 c=unreal.get_default_object(B.generated_class(bp))
 for k,v in {'oscillation_duration':.22,'oscillation_blend_in_time':.015,'oscillation_blend_out_time':.19,'single_instance':True}.items():c.set_editor_property(k,v)
 rot=c.get_editor_property('rot_oscillation')
 for key in ('pitch','yaw'):
  osc=rot.get_editor_property(key);osc.set_editor_property('amplitude',.13);osc.set_editor_property('frequency',16.);rot.set_editor_property(key,osc)
 c.set_editor_property('rot_oscillation',rot);compile_bp(bp);save(bp);return bp

def build_door(meshes,steam,report):
 bp=bp_asset('BP_HeavyBlastDoor');compile_bp(bp)
 for name,mesh,collision in [('StaticMesh_DoorFrame',meshes['SM_HeavyDoorFrame'],False),('StaticMesh_DoorPanel',meshes['SM_HeavyDoorPanel'],True)]:
  c=add(bp,unreal.StaticMeshComponent,name);c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.MOVABLE)
  c.set_collision_profile_name('NoCollision');c.set_editor_property('relative_location',V((0,0,0)))
 panelbody=add(bp,unreal.BoxComponent,'DoorPanelCollision',parent='StaticMesh_DoorPanel');panelbody.set_box_extent(V((36,175,207)));panelbody.set_editor_property('relative_location',V((0,0,207)));panelbody.set_collision_profile_name('BlockAll');panelbody.set_editor_property('generate_overlap_events',False)
 box=add(bp,unreal.BoxComponent,'BoxCollision');box.set_box_extent(V((255,235,230)));box.set_editor_property('relative_location',V((0,0,220)));box.set_collision_profile_name('Trigger');box.set_editor_property('generate_overlap_events',True)
 for side in (-1,1):
  c=add(bp,unreal.BoxComponent,'FrameCollision'+str(side));c.set_box_extent(V((50,26,225)));c.set_editor_property('relative_location',V((0,side*206,225)));c.set_collision_profile_name('BlockAll');c.set_editor_property('generate_overlap_events',False)
 audio=add(bp,unreal.AudioComponent,'MovementAudio');audio.set_sound(import_sound('S_BlastDoorMotor'));audio.set_editor_property('auto_activate',False);audio.set_editor_property('relative_location',V((0,0,210)));audio.set_editor_property('volume_multiplier',.65)
 settings=audio.get_editor_property('attenuation_overrides');settings.set_editor_property('attenuation_shape_extents',V((150,0,0)));settings.set_editor_property('falloff_distance',1200.);audio.set_editor_property('attenuation_overrides',settings);audio.set_editor_property('override_attenuation',True)
 for side in (-1,1):
  c=add(bp,unreal.NiagaraComponent,'BaseSteam'+str(side));c.set_asset(steam);c.set_editor_property('auto_activate',False);c.set_editor_property('relative_location',V((-42,side*130,10)));c.set_editor_property('relative_scale3d',V((.8,.8,.8)));c.set_editor_property('cast_shadow',False)
 compile_bp(bp);g=Graph(bp)
 g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 actions=[n for n in g.e.list_available_nodes([]) if n.startswith('|') and ('шкалу' in n or 'Timeline' in n)]
 timeline=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(x=0,y=0),[]))
 templates=[o for o in unreal.ObjectIterator(unreal.TimelineTemplate) if o.get_outer()==B.generated_class(bp)]
 if len(templates)!=1:raise RuntimeError('Expected one door Timeline '+str(templates))
 template=templates[0];template.set_editor_property('timeline_length',1.5);template.set_editor_property('length_mode',unreal.TimelineLengthMode.TL_TIMELINE_LENGTH)
 tlname=template.get_name().removesuffix('_Template')
 compile_bp(bp);g=Graph(bp)
 # Timeline remains reversible from its current time, including interrupted motion.
 now=g.out(g.call('Engine.TimelineComponent.GetPlaybackPosition',target=g.get(tlname)))
 t=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=now,B=1.5),Min=0,Max=1)
 eased=g.math('Multiply_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=t,B=t),B=g.math('Subtract_DoubleDouble',A=3,B=g.math('Multiply_DoubleDouble',A=t,B=2)))
 z=g.math('Multiply_DoubleDouble',A=eased,B=432)
 g.cursor=pin(timeline,'Update',True)
 g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('StaticMesh_DoorPanel'),NewLocation=g.math('MakeVector',X=0,Y=0,Z=z),bSweep=True,bTeleport=False))
 for eventname,opening in [('OnComponentBeginOverlap',True),('OnComponentEndOverlap',False)]:
  event=g.e.add_component_bound_event_node(box,eventname);g.cursor=pin(event,'then',True)
  pawn=g.out(g.call('Engine.GameplayStatics.GetPlayerPawn',PlayerIndex=0))
  isplayer=g.math('EqualEqual_ObjectObject',A=pin(event,'OtherActor',True),B=pawn)
  g.branch(isplayer)
  if not opening:
   remains=g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('BoxCollision'),Other=pawn))
   g.branch(g.math('Not_PreBool',A=remains))
  g.do(g.call('Engine.AudioComponent.Play',target=g.get('MovementAudio'),StartTime=0))
  if opening:
   for side in (-1,1):g.do(g.call('Engine.ActorComponent.Activate',target=g.get('BaseSteam'+str(side)),bReset=True))
  link(g.cursor,pin(timeline,'Play' if opening else 'Reverse'))
 g.cursor=pin(timeline,'Finished',True);g.do(g.call('Engine.AudioComponent.Stop',target=g.get('MovementAudio')))
 reverse=g.out(g.call('Engine.TimelineComponent.IsReversing',target=g.get(tlname)));g.branch(reverse)
 g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=import_sound('S_BlastDoorThud').get_path_name(),Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=.6))
 shake=build_shake()
 g.do(g.call('Engine.GameplayStatics.PlayWorldCameraShake',Shake=B.generated_class(shake).get_path_name(),Epicenter=g.out(g.call('Engine.Actor.K2_GetActorLocation')),InnerRadius=120,OuterRadius=650,Falloff=1,bOrientShakeTowardsEpicenter=False))
 compile_bp(bp);save(bp)
 report['door']={'blueprint':bp.get_path_name(),'timeline':tlname,'duration':1.5,'travel_cm':432,'curve':'smoothstep(t): t*t*(3-2*t)','auto_open':'local player only','auto_close':'player exits approach volume; reversed from current time','audio':'motor/hiss + impact','camera_shake_seconds':.22}
 return bp
