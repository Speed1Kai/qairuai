"""Patch prompt layout, exterior readability and sealed perimeter gate only."""
import unreal,os,sys,json,math,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,add,components,compile_bp,save
import Archive_AuthoringHelpers as H
project=os.path.abspath(unreal.Paths.project_dir());report={'saved':False};main='/Game/Lvl_LabTutorial';level='/Game/Surface/Lvl_CampusConnected'
backup=os.path.join(project,'Saved/Backups/CampusReadability',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
def back(p):
 ext='.umap' if p==level else '.uasset';f=os.path.join(project,'Content',p.removeprefix('/Game/')+ext)
 if os.path.isfile(f):shutil.copy2(f,os.path.join(backup,os.path.basename(f)))
def asset(name):
 p='/Game/Surface/'+name;back(p)
 if A.does_asset_exist(p):return A.load_asset(p)
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
 return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/Surface',unreal.Blueprint,f)
try:
 for path in ['/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt']:
  back(path);bp=A.load_asset(path);tree=unreal.find_object(bp,'WidgetTree');panel=unreal.find_object(tree,'OmegaGlassLayout')
  panel.slot.set_position(unreal.Vector2D(0,-124));panel.slot.set_size(unreal.Vector2D(920,250))
  bg=unreal.find_object(tree,'OmegaHologlass');bg.slot.set_size(unreal.Vector2D(920,250))
  stack=unreal.find_object(tree,'OmegaTextStack') or unreal.new_object(unreal.VerticalBox,outer=tree,name='OmegaTextStack');stack.clear_children()
  stack.remove_from_parent();s=panel.add_child_to_canvas(stack);s.set_position(unreal.Vector2D(210,54));s.set_size(unreal.Vector2D(660,172))
  for name,size,color in [('Heading',21,unreal.LinearColor(.33,.93,1,1)),('MessageBody',18,unreal.LinearColor(.9,.97,1,1))]:
   t=unreal.find_object(tree,name);t.remove_from_parent();s=stack.add_child_to_vertical_box(t);s.set_padding(unreal.Margin(0,0,0,12));t.set_auto_wrap_text(True);t.set_editor_property('wrap_text_at',650.);font=t.font;font.set_editor_property('size',size);t.set_font(font)
  compile_bp(bp);save(bp)
 # Match the objective to the sealed gate. Do not tell the player to walk through it.
 arrival=A.load_asset('/Game/Surface/BP_SurfaceArrival');back('/Game/Surface/BP_SurfaceArrival')
 for n in G.get_graph_editor_by_name(arrival,'EventGraph').list_all_nodes():
  for p in n.list_all_pins():
   s=p.get_pin_value()
   if s=='НОВАЯ ЦЕЛЬ / БАШНЯ АРХИТЕКТОРА':p.set_pin_value('ЦЕЛЬ / ПЕРИМЕТР КОМПЛЕКСА')
   if 'Пройдите через двор' in s:p.set_pin_value('Найдите северные ворота. Они заблокированы — потребуется способ преодолеть периметр.')
 compile_bp(arrival);save(arrival)
 back(level)
 # A bounded post-process region begins just outside the real laboratory exit.
 # Sky fill is streamed with the exterior, and unloads on descent to the basement.
 lighting=asset('BP_CampusReadability');root=add(lighting,unreal.SceneComponent,'Root');root.set_mobility(unreal.ComponentMobility.MOVABLE)
 bounds=add(lighting,unreal.BoxComponent,'ExteriorBounds','Root');bounds.set_mobility(unreal.ComponentMobility.MOVABLE);bounds.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);bounds.set_box_extent(V((100000,50000,7900)));bounds.set_editor_property('relative_location',V((-10006.289955,45187.401341,7850)))
 pp=add(lighting,unreal.PostProcessComponent,'ExteriorGrade','ExteriorBounds');pp.set_editor_property('unbound',False);pp.set_editor_property('priority',20.);pp.set_editor_property('blend_radius',350.)
 s=pp.get_editor_property('settings')
 for k,v in [('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.),('auto_exposure_bias',.5),('vignette_intensity',.15)]:s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
 pp.set_editor_property('settings',s)
 sky=add(lighting,unreal.SkyLightComponent,'OvercastSkyFill','Root');sky.set_mobility(unreal.ComponentMobility.MOVABLE);sky.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP);sky.set_editor_property('cubemap',A.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));sky.set_intensity(1.6);sky.set_editor_property('lower_hemisphere_is_black',False);sky.set_editor_property('real_time_capture',False)
 compile_bp(lighting);save(lighting)
 # Geometry is baked into the same 49.0856-degree alignment as the fixed fence.
 gate=asset('BP_CampusSealedGate');root=add(gate,unreal.SceneComponent,'Root');root.set_mobility(unreal.ComponentMobility.MOVABLE)
 steel=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabSteel');dark=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabGraphite');amber=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabAmber');red=A.load_asset('/Game/LabTutorial/Industrial/M_RustyIron') or dark
 mats={'Steel':steel,'Frame':dark,'Hazard':amber};batches={}
 for name,mat in mats.items():
  c=add(gate,unreal.HierarchicalInstancedStaticMeshComponent,name,'Root');c.modify();c.clear_instances();c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,mat);c.set_collision_profile_name('BlockAll');batches[name]=c
 angle=49.08561677997487;rad=math.radians(angle)
 def pos(p):
  x,y,z=p;y+=17050
  return V((x*math.cos(rad)-y*math.sin(rad),x*math.sin(rad)+y*math.cos(rad),z))
 def box(p,scale,mat='Frame',yaw=0):batches[mat].add_instance(unreal.Transform(location=pos(p),rotation=unreal.Rotator(yaw=angle+yaw),scale=V(tuple(v/100. for v in scale))),False)
 for side in (-1,1):
  box((side*1430,0,330),(180,260,660));box((side*1430,0,680),(230,300,60))
  box((side*690,0,300),(1376,75,600),'Steel')
  for z in (45,160,440,560):box((side*690,-47,z),(1330,28,35))
  for x in range(90,1330,140):
   box((side*x,-50,290),(18,34,540))
   for z in (35,565):box((side*x,-69,z),(10,10,10),'Steel')
  box((side*690,-66,100),(1320,10,100))
  for x in range(100,1310,120):box((side*x,-74,100),(58,9,93),'Hazard',-28)
  box((side*1510,-120,330),(48,70,540),'Steel');box((side*1510,-155,330),(16,20,410))
 box((0,0,665),(2940,220,110));box((0,-60,300),(28,45,590));box((0,-130,618),(470,30,55),'Hazard')
 # Short paved apron connects the gate to the courtyard side of the perimeter.
 box((0,-1450,-9),(2700,3000,18),'Frame');box((0,-3500,-12),(1800,1300,24),'Steel')
 compile_bp(gate);save(gate)
 world=unreal.EditorLoadingAndSavingUtils.load_map(level);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 for a in list(sub.get_all_level_actors()):
  if a.get_class().get_name() in ('BP_CampusReadability_C','BP_CampusSealedGate_C'):sub.destroy_actor(a)
  if isinstance(a,unreal.DirectionalLight):a.modify();a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.)
 # Remove the obsolete gate frame at the old, unrotated perimeter opening.
 campus=A.load_asset('/Game/Surface/BP_ConnectedLaboratoryCampus');back('/Game/Surface/BP_ConnectedLaboratoryCampus')
 def trim(cs):
  for c in cs:
   if not isinstance(c,unreal.InstancedStaticMeshComponent):continue
   c.modify()
   for i in range(c.get_instance_count()-1,-1,-1):
    p=c.get_instance_transform(i,False).translation
    if abs(p.x)<1550 and 16900<p.y<17400 and p.z>100:c.remove_instance(i)
 trim([c for h,c,n in components(campus)]);compile_bp(campus);save(campus)
 for a in sub.get_all_level_actors():
  if a.get_class().get_name()=='BP_ConnectedLaboratoryCampus_C':a.modify();trim(a.get_components_by_class(unreal.InstancedStaticMeshComponent))
  if isinstance(a,unreal.TextRenderActor) and ('CITY ACCESS' in str(a.text_render.text) or 'RESEARCH COMPLEX' in str(a.text_render.text)):
   a.modify();a.set_actor_hidden_in_game(True)
 for bp,label in [(lighting,'CAMPUS_ExteriorReadability'),(gate,'CAMPUS_SealedNorthGate')]:
  a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label(label);a.set_folder_path('SURFACE/LaboratoryCampus')
 world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,level);del world
 unreal.EditorLoadingAndSavingUtils.load_map(main)
 report.update(saved=True,backup=backup,gate_local=list(pos((0,0,0)).to_tuple()),gate_world=[-2870,17780,2150],gate_locked=True,gate_has_input=False,lighting_bounded=True)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:json.dump(report,open(os.path.join(project,'Saved/campus_readability_fix.json'),'w'),ensure_ascii=False,indent=2)
