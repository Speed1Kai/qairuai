"""Compile weathered materials and author a small, shadowless light flicker rig."""
import unreal,os,sys,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
from Industrial_Materials import build_materials
r={'saved':False}
try:
 unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 mats=build_materials()
 for name in ('M_CableRubber','M_CyanPhosphor','M_RedEmergency'):
  m=A.load_asset('/Game/LabTutorial/ReferenceStyle/'+name)
  M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(m);save(m)
 bp=bp_asset('BP_IndustrialLightFlicker');compile_bp(bp)
 actors=unreal.EditorLevelLibrary.get_all_level_actors();sources=[]
 for a in actors:
  n=a.get_actor_label()
  if n.startswith(('REF_AlarmGlow','LAB_RedEmergency')) and a.get_actor_location().x<950:
   sources.append(a)
 comps=[]
 for i,a in enumerate(sources):
  source=a.get_component_by_class(unreal.PointLightComponent)
  if not source:continue
  c=add(bp,unreal.PointLightComponent,'EmergencyLamp%02d'%i);c.set_mobility(unreal.ComponentMobility.MOVABLE)
  c.set_editor_property('relative_location',a.get_actor_location());c.set_intensity(850);c.set_light_color(unreal.LinearColor(r=1.,g=.065,b=.022,a=1));c.set_cast_shadows(False)
  for k in ('attenuation_radius','source_radius','soft_source_radius','source_length','use_inverse_squared_falloff','light_falloff_exponent','intensity_units','indirect_lighting_intensity'):
   try:c.set_editor_property(k,source.get_editor_property(k))
   except Exception:pass
  comps.append('EmergencyLamp%02d'%i)
 if not comps:comps=[n for h,c,n in components(bp) if n.startswith('EmergencyLamp')]
 compile_bp(bp);g=Graph(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 g.event('ReceiveBeginPlay');g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.10))
 g.event('ReceiveTick');time=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))
 for i,name in enumerate(comps):
  phase=g.math('Add_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=time,B=8.1),B=i*1.73)
  ripple=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=phase),B=43.)
  buzz=g.math('Multiply_DoubleDouble',A=g.math('Sin',A=g.math('Multiply_DoubleDouble',A=phase,B=3.17)),B=12.)
  intensity=g.math('Add_DoubleDouble',A=795,B=g.math('Add_DoubleDouble',A=ripple,B=buzz))
  g.do(g.call('Engine.LightComponent.SetIntensity',target=g.get(name),NewIntensity=intensity))
 compile_bp(bp);save(bp)
 for a in actors:
  if a.get_actor_label()=='IND_LightFlicker':unreal.EditorLevelLibrary.destroy_actor(a)
 controller=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)),unreal.Rotator());controller.set_actor_label('IND_LightFlicker');controller.set_folder_path('LAB/02_Lighting')
 for a in sources:unreal.EditorLevelLibrary.destroy_actor(a)
 editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
 if editor:editor.set_level_viewport_camera_info(V((360,-560,225)),unreal.MathLibrary.find_look_at_rotation(V((360,-560,225)),V((-330,480,145))))
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Cannot save final lab lighting')
 r.update(saved=True,red_flicker_lights=len(comps),tick_interval=.10,material_channel_inputs_repaired=True)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
with open(os.path.join(unreal.Paths.project_saved_dir(),'industrial_finish_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Industrial final pass incomplete')
