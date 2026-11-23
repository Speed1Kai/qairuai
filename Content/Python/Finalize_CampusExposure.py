import unreal,os,sys,json,datetime,shutil
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,pin,val,compile_bp,save,components
src=os.path.join(os.path.dirname(__file__),'Upgrade_PlayerVisor.py');exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
# Explicitly gate the exterior grade by camera position. This avoids relying on
# physics-disabled BoxComponent bounds in a dynamically streamed level.
bp=A.load_asset('/Game/Surface/BP_CampusReadability')
for h,c,n in components(bp):
 if n=='ExteriorGrade':
  c.modify();c.set_editor_property('unbound',True);c.set_editor_property('blend_weight',0.);s=c.settings
  for k,v in [('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),('auto_exposure_apply_physical_camera_exposure',False),('auto_exposure_bias',0.),('ambient_cubemap_intensity',.15)]:s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
  s.set_editor_property('ambient_cubemap',A.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'));c.set_editor_property('settings',s)
 if n=='OvercastSkyFill':c.set_intensity(1.6)
compile_bp(bp)
g=Flow(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);g.event('ReceiveBeginPlay');g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=.1));g.do(g.call('Engine.SkyLightComponent.RecaptureSky',target=g.get('OvercastSkyFill')))
g.event('ReceiveTick');cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=cam)));v=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam)))
y=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=pin(v,'Y',True),B=1600.),B=650.),Min=0.,Max=1.);z=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=pin(v,'Z',True),B=2100.),B=200.),Min=0.,Max=1.)
g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('ExteriorGrade'),PropertyName='BlendWeight',Value=g.math('Multiply_DoubleDouble',A=y,B=z)));compile_bp(bp);save(bp)
# Refresh the placed copy to avoid stale component overrides.
level='/Game/Surface/Lvl_CampusConnected';world=unreal.EditorLoadingAndSavingUtils.load_map(level);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in list(sub.get_all_level_actors()):
 if a.get_class().get_name()=='BP_CampusReadability_C':sub.destroy_actor(a)
 if isinstance(a,unreal.DirectionalLight):a.modify();a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.)
a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label('CAMPUS_ExteriorReadability');world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,level);del world
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
# Clear an unfinished editor helper preview graph, preserving its other functions.
helper=A.load_asset('/Game/LabTutorial/UI/BP_ArchiveAuthoring')
if 'PreviewCampusNotice' in map(str,B.list_graph_names(helper)):
 g=Flow(helper,'PreviewCampusNotice');compile_bp(helper);save(helper)
bp=A.load_asset('/Game/Surface/BP_SurfaceArrival');g=Flow(bp,'PreviewCampusNotice');pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0));widget=g.out(g.do(g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint')).get_path_name(),OwningPlayer=pc)))
for name,text in [('HUDTitle','ЦЕЛЬ / ПЕРИМЕТР КОМПЛЕКСА'),('HUDMessage','Найдите северные ворота. Они заблокированы — потребуется способ преодолеть периметр.')]:g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=name,Value=text))
g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=widget,PropertyName='HUDLifetime',Value=60.));g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=70));compile_bp(bp);save(bp)
json.dump({'saved':True,'manual_exposure':True,'ambient_cubemap':.15},open(os.path.join(unreal.Paths.project_saved_dir(),'campus_exposure_final.json'),'w'),indent=2)

