"""Align the supplied +Y-facing mesh and prepare courtyard lighting before exit."""
import unreal,os,sys,datetime,shutil,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,V,pin,val,components,compile_bp,save
src=os.path.join(os.path.dirname(__file__),'Upgrade_PlayerVisor.py');exec(compile(open(src,encoding='utf-8-sig').read().split('\ntry:\n')[0],src,'exec'))
project=os.path.abspath(unreal.Paths.project_dir());backup=os.path.join(project,'Saved/Backups/WalkAndExitLight',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
paths=['/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter','/Game/Surface/BP_CampusReadability','/Game/Surface/Lvl_CampusConnected']
for path in paths:
 f=os.path.join(project,'Content',path.removeprefix('/Game/')+('.umap' if path.endswith('Lvl_CampusConnected') else '.uasset'))
 if os.path.isfile(f):shutil.copy2(f,os.path.join(backup,os.path.basename(f)))
bp=A.load_asset(paths[0]);seen=set()
for h,c,n in components(bp):
 if not c or c.get_path_name() in seen:continue
 seen.add(c.get_path_name())
 if n=='Mesh':c.modify();c.set_editor_property('relative_rotation',unreal.Rotator(yaw=270))
 if isinstance(c,unreal.CharacterMovementComponent):c.modify();c.set_editor_property('orient_rotation_to_movement',True);c.set_editor_property('use_controller_desired_rotation',False);c.set_editor_property('rotation_rate',unreal.Rotator(yaw=540))
compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('use_controller_rotation_yaw',False);save(bp)
light=A.load_asset(paths[1]);member(light,'ExteriorBlend','real','0');compile_bp(light)
for h,c,n in components(light):
 if n=='ExteriorGrade':
  c.modify();s=c.settings;s.set_editor_property('auto_exposure_bias',-.7);s.set_editor_property('ambient_cubemap_intensity',.08);c.set_editor_property('settings',s)
g=Flow(light);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);g.event('ReceiveBeginPlay');g.set('ExteriorBlend',0.);g.do(g.call('Engine.Actor.SetActorTickInterval',TickInterval=0.));g.do(g.call('Engine.SkyLightComponent.RecaptureSky',target=g.get('OvercastSkyFill')))
tick=g.event('ReceiveTick');cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=cam)));v=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam)))
# The transition finishes while the player is still in the lift/upper laboratory.
# Crossing the exit door no longer changes exposure or ambient illumination.
target=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=pin(v,'Z',True),B=1720.),B=330.),Min=0.,Max=1.)
g.set('ExteriorBlend',g.math('FInterpTo',Current=g.get('ExteriorBlend'),Target=target,DeltaTime=pin(tick,'DeltaSeconds',True),InterpSpeed=2.));g.do(g.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=g.get('ExteriorGrade'),PropertyName='BlendWeight',Value=g.get('ExteriorBlend')));compile_bp(light);save(light)
# Refresh this small placed actor only; preserve all courtyard geometry.
world=unreal.EditorLoadingAndSavingUtils.load_map(paths[2]);sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in list(sub.get_all_level_actors()):
 if a.get_class().get_name()=='BP_CampusReadability_C':sub.destroy_actor(a)
a=sub.spawn_actor_from_class(B.generated_class(light),V((0,0,0)));a.set_actor_label('CAMPUS_ExteriorReadability');world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,paths[2]);del world
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
json.dump({'saved':True,'backup':backup,'mesh_yaw':270,'rotation_rate':540,'exterior_height_range':[1720,2050],'interpolation_speed':2,'door_threshold_independent':True},open(os.path.join(project,'Saved/walk_and_exit_light_fix.json'),'w'),indent=2)
