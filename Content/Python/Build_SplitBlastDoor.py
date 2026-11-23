"""Replace the old corridor gate with a saved, native two-leaf Blueprint."""
import unreal,sys,os,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
from Industrial_Door import import_sound,build_shake
from Industrial_Materials import make_material
from Author_DoorCurve import build_float_track

class DoorGraph(Graph):
 def do(self,n):return super().do(n) if n.find_execute_pin().is_valid() else n

report={'saved':False,'replaced':[]}
content=unreal.Paths.project_content_dir();saved=unreal.Paths.project_saved_dir()
backup=os.path.join(saved,'Backups','SplitBlastDoor',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(backup,exist_ok=True)
for rel in ('Lvl_LabTutorial.umap','LabTutorial/Industrial/BP_HeavyBlastDoor.uasset'):
 src=os.path.join(content,rel);dst=os.path.join(backup,rel)
 if os.path.isfile(src):os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
report['backup']=backup

def material_signal(name,rgb):
 path=ROOT+'/'+name
 mat=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 n=M.create_material_expression(mat,unreal.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name','SignalColor');n.set_editor_property('default_value',unreal.LinearColor(r=rgb[0]*80,g=rgb[1]*80,b=rgb[2]*80,a=1))
 M.connect_material_property(n,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(mat);save(mat);return mat

def models():
 make_material('M_DoorArmor','metal',(.13,.15,.145),.76,.44)
 make_material('M_DoorHazard','hazard',(.5,.3,.02),.4,.62)
 # Object-space stripes travel with each leaf instead of sliding over its face.
 mat=A.load_asset(ROOT+'/M_DoorHazard')
 pos=next(o for o in unreal.ObjectIterator(unreal.MaterialExpressionWorldPosition) if o.get_outer()==mat)
 local=M.create_material_expression(mat,unreal.MaterialExpressionTransformPosition)
 local.set_editor_property('transform_source_type',unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
 local.set_editor_property('transform_type',unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
 if not M.connect_material_expressions(pos,'',local,M.get_material_expression_input_names(local)[0]):raise RuntimeError('Cannot wire local hazard coordinates')
 for node in unreal.ObjectIterator(unreal.MaterialExpressionCustom):
  if node.get_outer()!=mat:continue
  code=node.get_editor_property('code')
  if 'float patch=' in code:
   M.connect_material_expressions(local,'',node,'P')
 M.recompile_material(mat);save(mat)
 source=os.path.join(content,'LabTutorial','Industrial','Source')
 with open(os.path.join(source,'split_door_manifest.json')) as f:manifest=json.load(f)
 result={}
 for spec in manifest:
  name=spec['name'];path=ROOT+'/'+name
  task=unreal.AssetImportTask()
  for k,v in {'filename':os.path.abspath(os.path.join(source,name+'.obj')),'destination_path':ROOT,'destination_name':name,'automated':True,'replace_existing':True,'save':True}.items():task.set_editor_property(k,v)
  opts=unreal.FbxImportUI()
  for k,v in {'import_materials':False,'import_textures':False,'import_as_skeletal':False,'import_animations':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_STATIC_MESH}.items():opts.set_editor_property(k,v)
  opts.static_mesh_import_data.set_editor_property('combine_meshes',True);opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
  task.set_editor_property('options',opts);unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=A.load_asset(path)
  if not mesh:raise RuntimeError('Mesh import failed '+name)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   key=str(slot.get_editor_property('material_slot_name'));mesh.set_material(i,A.load_asset(ROOT+'/'+key))
  save(mesh);result[name]=mesh
 report['meshes']=manifest
 return result

def build(meshes):
 path='/Game/LabTutorial/Doors/BP_HeavyBlastDoor'
 if A.does_asset_exist(path):bp=A.load_asset(path)
 else:
  factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
  bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_HeavyBlastDoor','/Game/LabTutorial/Doors',unreal.Blueprint,factory)
  add(bp,unreal.SceneComponent,'SceneRoot');compile_bp(bp)
 g=DoorGraph(bp)
 # Remove old logic before removing the vertical slab and its collision child.
 g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 if 'bDoorOpen' not in map(str,B.list_member_variable_names(bp)):g.e.add_member_variable('bDoorOpen',B.get_basic_type_by_name('bool'),'False')
 red=material_signal('M_DoorStatus_Red',(1.,.012,.004));green=material_signal('M_DoorStatus_Green',(.025,1.,.075))
 def meshcomp(name,mesh,p=(0,0,0),s=(1,1,1),parent=None):
  c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('relative_location',V(p));c.set_editor_property('relative_scale3d',V(s));return c
 meshcomp('StaticMesh_DoorFrame',meshes['SM_BlastDoor_SplitFrame'])
 meshcomp('HydraulicServices',meshes['SM_BlastDoor_HydraulicServices'])
 for sign,label in [(-1,'Left'),(1,'Right')]:
  meshcomp(label+'DoorPanel',meshes['SM_BlastDoor_'+label],(0,sign*87.5,0))
  c=add(bp,unreal.BoxComponent,label+'PanelCollision',label+'DoorPanel');c.set_box_extent(V((23,87,201)));c.set_editor_property('relative_location',V((0,0,205)));c.set_collision_profile_name('BlockAll');c.set_editor_property('generate_overlap_events',False)
  for face in (-1,1):
   meshcomp(label+'PistonRod'+str(face),meshes['SM_BlastDoor_PistonRod'],(face*40,sign*260,350))
  c=add(bp,unreal.BoxComponent,'FrameCollision'+str(sign));c.set_box_extent(V((57,28,210)));c.set_editor_property('relative_location',V((0,sign*202,212)));c.set_collision_profile_name('BlockAll');c.set_editor_property('generate_overlap_events',False)
  c=add(bp,unreal.BoxComponent,label+'PocketCollision');c.set_box_extent(V((54,72,205)));c.set_editor_property('relative_location',V((0,sign*288,205)));c.set_collision_profile_name('BlockAll');c.set_editor_property('generate_overlap_events',False)
 box=add(bp,unreal.BoxComponent,'BoxCollision');box.set_box_extent(V((290,170,210)));box.set_editor_property('relative_location',V((0,0,205)));box.set_collision_profile_name('Trigger');box.set_editor_property('generate_overlap_events',True)
 # Blocking leaves move with their collision; side pockets never block the opening.
 for face in (-1,1):
  c=meshcomp('StatusLens'+str(face),A.load_asset('/Engine/BasicShapes/Cube'),(face*73,0,422),(.045,.9,.18));c.set_material(0,red);c.set_editor_property('cast_shadow',False)
 light=add(bp,unreal.PointLightComponent,'StatusLight');light.set_editor_property('relative_location',V((-95,0,420)));light.set_intensity(55.);light.set_attenuation_radius(230.);light.set_cast_shadows(False);light.set_light_color(unreal.LinearColor(r=1,g=.012,b=.004,a=1));light.set_editor_property('indirect_lighting_intensity',0.)
 slide=import_sound('S_BlastDoorSlide');slide.set_editor_property('looping',True);save(slide)
 hiss=import_sound('S_BlastDoorHydraulicRelease');thud=import_sound('S_BlastDoorThud')
 audio=add(bp,unreal.AudioComponent,'MovementAudio');audio.set_sound(slide);audio.set_editor_property('auto_activate',False);audio.set_editor_property('relative_location',V((0,0,190)));audio.set_editor_property('volume_multiplier',.6)
 settings=audio.get_editor_property('attenuation_overrides');settings.set_editor_property('attenuation_shape_extents',V((100,0,0)));settings.set_editor_property('falloff_distance',850.);settings.set_editor_property('spatialize',True);audio.set_editor_property('attenuation_overrides',settings);audio.set_editor_property('override_attenuation',True)
 path=ROOT+'/SA_BlastDoor'
 atten=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('SA_BlastDoor',ROOT,unreal.SoundAttenuation,unreal.SoundAttenuationFactory())
 atten.set_editor_property('attenuation',settings);save(atten)
 steam_path=ROOT+'/NS_SteamVent'
 steam=A.load_asset(steam_path) if A.does_asset_exist(steam_path) else unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('NS_SteamVent',ROOT,A.load_asset(ROOT+'/NS_PressureVent'))
 save(steam)
 for side in (-1,1):
  c=add(bp,unreal.NiagaraComponent,'BaseSteam'+str(side));c.set_asset(steam);c.set_editor_property('auto_activate',False);c.set_editor_property('relative_location',V((-42,side*130,8)));c.set_editor_property('relative_scale3d',V((.7,.7,.7)));c.set_editor_property('cast_shadow',False)
 compile_bp(bp);g=DoorGraph(bp)
 actions=[n for n in g.e.list_available_nodes([]) if n.startswith('|') and ('шкалу' in n or 'Timeline' in n)]
 timeline=g.node(g.e.create_node_from_name(actions[0],unreal.Vector2D(),[]))
 template=next(o for o in unreal.ObjectIterator(unreal.TimelineTemplate) if o.get_outer()==B.generated_class(bp))
 native=unreal.get_default_object(unreal.SystemLibrary)
 native.call_method('SetNamePropertyByName',(timeline,unreal.Name('TimelineName'),unreal.Name('TL_DoorMovement')))
 template.rename('TL_DoorMovement_Template')
 template.set_editor_property('timeline_length',1.8);template.set_editor_property('length_mode',unreal.TimelineLengthMode.TL_TIMELINE_LENGTH)
 curve=build_float_track(template)
 compile_bp(bp);g=DoorGraph(bp)
 # Read the same external Float Track curve at the Timeline playback position.
 # This also works when editor automation has not reconstructed the track pin.
 playback=g.out(g.call('Engine.TimelineComponent.GetPlaybackPosition',target=g.get('TL_DoorMovement')))
 alpha=g.call('Engine.CurveFloat.GetFloatValue',target=curve.get_path_name(),InTime=playback)
 g.cursor=pin(timeline,'Update',True);g.do(alpha);a=g.out(alpha)
 for sign,label in [(-1,'Left'),(1,'Right')]:
  closed=g.math('MakeVector',X=0,Y=sign*87.5,Z=0);opened=g.math('MakeVector',X=0,Y=sign*263.5,Z=0)
  position=g.math('VLerp',A=closed,B=opened,Alpha=a)
  g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get(label+'DoorPanel'),NewLocation=position,bSweep=False,bTeleport=False))
  # Rods retract into their fixed drive cylinders as the leaves slide sideways.
  for face in (-1,1):
   y=g.math('Lerp',A=sign*260,B=sign*347,Alpha=a)
   g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get(label+'PistonRod'+str(face)),NewLocation=g.math('MakeVector',X=face*40,Y=y,Z=350),bSweep=False,bTeleport=False))
   scale=g.math('Lerp',A=1.,B=.045,Alpha=a)
   g.do(g.call('Engine.SceneComponent.SetRelativeScale3D',target=g.get(label+'PistonRod'+str(face)),NewScale3D=g.math('MakeVector',X=1,Y=scale,Z=1)))
 shake=A.load_asset(ROOT+'/BP_BlastDoorImpactShake')
 def camera_shake():g.do(g.call('Engine.GameplayStatics.PlayWorldCameraShake',Shake=B.generated_class(shake).get_path_name(),Epicenter=g.out(g.call('Engine.Actor.K2_GetActorLocation')),InnerRadius=80,OuterRadius=580,Falloff=1.5,bOrientShakeTowardsEpicenter=False))
 def sound(asset,volume):g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=asset.get_path_name(),Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=volume,AttenuationSettings=atten.get_path_name()))
 for eventname,opening in [('OnComponentBeginOverlap',True),('OnComponentEndOverlap',False)]:
  event=g.e.add_component_bound_event_node(box,eventname);g.cursor=pin(event,'then',True)
  player=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
  g.branch(g.math('EqualEqual_ObjectObject',A=pin(event,'OtherActor',True),B=player))
  g.branch(g.math('Not_PreBool',A=g.get('bDoorOpen')) if opening else g.get('bDoorOpen'))
  if not opening:
   overlaps=g.out(g.call('Engine.PrimitiveComponent.IsOverlappingActor',target=g.get('BoxCollision'),Other=player));g.branch(g.math('Not_PreBool',A=overlaps))
  g.set('bDoorOpen',opening)
  for face in (-1,1):g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=g.get('StatusLens'+str(face)),ElementIndex=0,Material=(green if opening else red).get_path_name()))
  color='(R=0.025,G=1.0,B=0.075,A=1.0)' if opening else '(R=1.0,G=0.012,B=0.004,A=1.0)'
  g.do(g.call('Engine.LightComponent.SetLightColor',target=g.get('StatusLight'),NewLightColor=color,bSRGB=False))
  if opening:
   sound(hiss,.65)
   for side in (-1,1):g.do(g.call('Engine.ActorComponent.Activate',target=g.get('BaseSteam'+str(side)),bReset=True))
  g.do(g.call('Engine.AudioComponent.FadeIn',target=g.get('MovementAudio'),FadeInDuration=.12,FadeVolumeLevel=.65,StartTime=0))
  camera_shake();link(g.cursor,pin(timeline,'Play' if opening else 'Reverse'))
 g.cursor=pin(timeline,'Finished',True)
 g.do(g.call('Engine.AudioComponent.Stop',target=g.get('MovementAudio')))
 g.branch(g.math('LessEqual_DoubleDouble',A=playback,B=.01))
 sound(thud,.65);camera_shake()
 compile_bp(bp)
 save(bp)
 report['blueprint']=bp.get_path_name();report['timeline']={'name':'TL_DoorMovement','duration':1.8,'float_track':'Alpha','curve':curve.get_path_name(),'leaf_travel_cm':176,'clear_width_cm':350,'interruptible':True}
 report['niagara']={'asset':steam.get_path_name(),'bursts':2,'scale':.7,'volumetric_fluids':False}
 return bp

try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 meshes=models();bp=build(meshes)
 # Replace only the corridor door and the obsolete vertical-door roof pockets.
 for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
  label=actor.get_actor_label()
  if label in ('IND_HeavyBlastDoor','IND_DoorFrontPocket','IND_DoorRearPocket'):
   report['replaced'].append(label);unreal.EditorLevelLibrary.destroy_actor(actor)
 door=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V((1450,0,0)),unreal.Rotator())
 door.set_actor_label('IND_HeavyBlastDoor');door.set_folder_path('LAB/03_Interactables')
 # Clear obsolete instance overrides by replacing the actor after recompiling.
 report['location_cm']=[1450,0,0]
 staged=os.path.abspath(os.path.join(saved,'SplitDoorStaged','Lvl_LabTutorial.umap'));os.makedirs(os.path.dirname(staged),exist_ok=True)
 unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(),'OBJ SAVEPACKAGE PACKAGE="/Game/Lvl_LabTutorial" FILE="'+staged.replace('\\','/')+'" SILENT=true')
 if not os.path.isfile(staged):raise RuntimeError('Staged map save failed')
 report['staged_map']=staged;report['saved']=False;report['asset_saved']=True
 unreal.log('SPLIT BLAST DOOR ASSET AND STAGED MAP SAVED')
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error']);raise
finally:
 with open(os.path.join(saved,'split_blast_door_report.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
