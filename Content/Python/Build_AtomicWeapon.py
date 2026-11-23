"""Native gun4 weapon, robot hands, recoil and bounded travelling atomic shots.
All gameplay runs in saved Blueprints. Python is authoring only.
"""
import unreal,os,sys,json,math,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
D='/Game/Combat/AtomicWeapon';P='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter';S=os.path.abspath(unreal.Paths.project_saved_dir());R={'saved':False}
def hookfn(bp,graph,fn,tag):
 e=G.get_graph_editor_by_name(bp,graph)
 if any(n.get_name()==tag for n in e.list_all_nodes()):return
 entry=e.find_graph_entry_pin();old=list(entry.list_connected_pins());entry.break_pin_links();n=e.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+fn);n.rename(tag);link(entry,n.find_execute_pin())
 for p in old:link(n.find_then_pin(),p)
def material(name,color,metal=.8,rough=.32,glow=False,alpha=False,smoke=False):
 path=D+'/'+name;m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,D,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m)
 if glow:m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 if alpha:m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT if smoke else unreal.BlendMode.BLEND_ADDITIVE)
 c=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1));M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if glow else unreal.MaterialProperty.MP_BASE_COLOR)
 for v,prop in [(metal,unreal.MaterialProperty.MP_METALLIC),(rough,unreal.MaterialProperty.MP_ROUGHNESS)]:
  n=M.create_material_expression(m,unreal.MaterialExpressionConstant);n.set_editor_property('r',v);M.connect_material_property(n,'',prop)
 if alpha:
  p=M.create_material_expression(m,unreal.MaterialExpressionScalarParameter);p.set_editor_property('parameter_name','Fade');p.set_editor_property('default_value',.7)
  f=M.create_material_expression(m,unreal.MaterialExpressionFresnel);f.set_editor_property('exponent',2.5)
  mult=M.create_material_expression(m,unreal.MaterialExpressionMultiply);M.connect_material_expressions(p,'',mult,'A');M.connect_material_expressions(f,'',mult,'B');M.connect_material_property(mult,'',unreal.MaterialProperty.MP_OPACITY)
 M.recompile_material(m);save(m);return m
def comp(bp,name,mesh,mat,parent=None,scale=(1,1,1),loc=(0,0,0)):
 c=add(bp,unreal.StaticMeshComponent,name,parent);c.set_static_mesh(mesh);c.set_material(0,mat);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('relative_scale3d',V(*scale));c.set_editor_property('relative_location',V(*loc));return c
def rel(g,name,pos=None,rot=None,scale=None):
 if pos is not None:g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get(name),NewLocation=pos,bSweep=False,bTeleport=False))
 if rot is not None:g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=g.get(name),NewRotation=rot,bSweep=False,bTeleport=False))
 if scale is not None:g.do(g.call('Engine.SceneComponent.SetRelativeScale3D',target=g.get(name),NewScale3D=scale))
def fade(g,name,amount):g.do(g.call('Engine.MeshComponent.SetScalarParameterValueOnMaterials',target=g.get(name),ParameterName='Fade',ParameterValue=amount))
def lin(g,a,b,t):return g.math('Lerp',A=a,B=b,Alpha=t)
try:
 assert not unreal.EditorLevelLibrary.get_game_world()
 back=os.path.join(S,'Backups/AtomicWeapon',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(back,exist_ok=True)
 shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),back);R['backup']=back
 gun=A.load_asset(D+'/SM_AtomicGun');arms=A.load_asset(D+'/SK_SentinelArms');assert gun and arms
 mats={'steel':material('M_GunSteel',(.11,.14,.17)), 'dark':material('M_GunDark',(.016,.022,.03),.65,.42),'grip':material('M_GunGrip',(.025,.027,.03),.1,.7),'glow':material('M_AtomicCoils',(.1,4.,7.),glow=True),'core':material('M_AtomicCore',(14.,8.,2.),glow=True,alpha=True),'wave':material('M_AtomicWave',(.1,5.,12.),glow=True,alpha=True),'smoke':material('M_AtomicSmoke',(.055,.07,.085),metal=0,rough=1,alpha=True,smoke=True)}
 for i,slot in enumerate(gun.static_materials):
  name=str(slot.material_slot_name).lower();gun.set_material(i,mats['glow' if any(x in name for x in ('light','lits','glass')) else 'grip' if 'leather' in name else 'dark' if 'black' in name else 'steel'])
 # Three modest LODs; no Nanite, collision or unique large textures.
 ses=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
 opts=unreal.EditorScriptingMeshReductionOptions();opts.set_editor_property('auto_compute_lod_screen_size',False)
 settings=[]
 for fraction,screen in ((1.,1.),(.5,.25),(.2,.08)):
  q=unreal.EditorScriptingMeshReductionSettings();q.set_editor_property('percent_triangles',fraction);q.set_editor_property('screen_size',screen);settings.append(q)
 opts.set_editor_property('reduction_settings',settings)
 (ses.set_lods(gun,opts) if ses else unreal.EditorStaticMeshLibrary.set_lods(gun,opts));save(gun)
 sphere=A.load_asset('/Engine/BasicShapes/Sphere');cylinder=A.load_asset('/Engine/BasicShapes/Cylinder')
 # Small reusable shock ring, 256 triangles, generated once at authoring time.
 ringpath=D+'/SM_AtomicRing'
 if not A.does_asset_exist(ringpath):
  source=os.path.join(unreal.Paths.project_dir(),'SourceAssets/AtomicWeapon/ring.obj');lines=[];N=32;K=4
  for i in range(N):
   a=2*math.pi*i/N
   for j in range(K):
    b=2*math.pi*j/K;r=45+3*math.cos(b);lines.append('v %f %f %f'%(r*math.cos(a),r*math.sin(a),3*math.sin(b)))
  for i in range(N):
   for j in range(K):
    a=i*K+j+1;b=((i+1)%N)*K+j+1;c=((i+1)%N)*K+(j+1)%K+1;d=i*K+(j+1)%K+1;lines.extend(['f %d %d %d'%(a,b,c),'f %d %d %d'%(a,c,d)])
  open(source,'w').write('\n'.join(lines));t=unreal.AssetImportTask();o=unreal.FbxImportUI();o.set_editor_property('import_materials',False);o.set_editor_property('import_textures',False);o.static_mesh_import_data.set_editor_property('combine_meshes',True);o.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
  for k,v in dict(filename=source,destination_path=D,destination_name='SM_AtomicRing',automated=True,save=True,options=o).items():t.set_editor_property(k,v)
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
 ring=A.load_asset(ringpath);assert ring
 impact=asset(D+'/BP_AtomicImpact');root=add(impact,unreal.SceneComponent,'ImpactRoot');root.set_mobility(unreal.ComponentMobility.MOVABLE)
 comp(impact,'Core',sphere,mats['core'],'ImpactRoot',(.5,.5,.5));comp(impact,'ShockRing',ring,mats['wave'],'ImpactRoot',(.2,.2,.2))
 for i in range(5):comp(impact,'Smoke'+str(i),sphere,mats['smoke'],'ImpactRoot',(.1,.1,.1))
 for i in range(10):comp(impact,'Spark'+str(i),sphere,mats['core'],'ImpactRoot',(.035,.035,.035))
 light=add(impact,unreal.PointLightComponent,'Flash','ImpactRoot');light.set_intensity(7000.);light.set_attenuation_radius(1100.);light.set_light_color(unreal.LinearColor(r=.4,g=.7,b=1.,a=1.));light.set_editor_property('cast_shadows',False);light.set_editor_property('volumetric_scattering_intensity',0.)
 force=add(impact,unreal.RadialForceComponent,'Force','ImpactRoot');force.set_editor_property('radius',1100.);force.set_editor_property('impulse_strength',2600.);force.set_editor_property('impulse_vel_change',True);force.set_editor_property('ignore_owning_actor',True)
 for n,k,v in [('Birth','real','0'),('BlastDamage','real','1800'),('BlastRadius','real','1100')]:var(impact,n,k,v)
 var(impact,'Ignored',B.get_array_type(actorref()),'()');compile_bp(impact)
 g=Graph(impact);g.e.remove_nodes(g.e.list_all_nodes());g.override('ReceiveBeginPlay');g.set('Birth',g.now());owner=g.out(g.call('Engine.Actor.GetOwner'));g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=g.get('Ignored'),NewItem=owner));pos=g.out(g.call('Engine.Actor.K2_GetActorLocation'))
 g.do(g.call('Engine.GameplayStatics.ApplyRadialDamageWithFalloff',BaseDamage=g.get('BlastDamage'),MinimumDamage=120.,Origin=pos,DamageInnerRadius=250.,DamageOuterRadius=g.get('BlastRadius'),DamageFalloff=1.,IgnoreActors=g.get('Ignored'),DamageCauser=owner,InstigatedByController=g.pc(),DamagePreventionChannel='ECC_Visibility'));g.do(g.call('Engine.RadialForceComponent.FireImpulse',target=g.get('Force')));g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=FX+'/S_ProtocolBlast',Location=pos,VolumeMultiplier=.8));g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=1.6))
 g.override('ReceiveTick');age=g.math('Subtract_DoubleDouble',A=g.now(),B=g.get('Birth'));wave=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=age,B=.65),Min=0.,Max=1.);corefade=g.math('FMax',A=0.,B=g.math('Subtract_DoubleDouble',A=1.,B=g.math('Divide_DoubleDouble',A=age,B=.24)))
 rel(g,'Core',scale=g.math('MakeVector',X=lin(g,.3,3.,wave),Y=lin(g,.3,3.,wave),Z=lin(g,.3,3.,wave)));fade(g,'Core',corefade)
 rel(g,'ShockRing',scale=g.math('MakeVector',X=lin(g,.2,19.,wave),Y=lin(g,.2,19.,wave),Z=.3));fade(g,'ShockRing',g.math('Subtract_DoubleDouble',A=1.,B=wave));g.do(g.call('Engine.LightComponent.SetIntensity',target=g.get('Flash'),NewIntensity=g.math('Multiply_DoubleDouble',A=corefade,B=7000.)))
 for i in range(5):
  radius=g.math('Add_DoubleDouble',A=.4,B=g.math('Multiply_DoubleDouble',A=age,B=1.8+i*.13));rel(g,'Smoke'+str(i),pos=g.math('MakeVector',X=math.cos(i*2.4)*70.,Y=math.sin(i*2.4)*70.,Z=g.math('Add_DoubleDouble',A=25.+i*28.,B=g.math('Multiply_DoubleDouble',A=age,B=90.))),scale=g.math('MakeVector',X=radius,Y=radius,Z=radius));fade(g,'Smoke'+str(i),g.math('FMax',A=0.,B=g.math('Multiply_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=1.6,B=age),B=.25)))
 for i in range(10):
  a=i*2.399;travel=g.math('Multiply_DoubleDouble',A=age,B=500.+i*23.);rel(g,'Spark'+str(i),pos=g.math('MakeVector',X=g.math('Multiply_DoubleDouble',A=travel,B=math.cos(a)),Y=g.math('Multiply_DoubleDouble',A=travel,B=math.sin(a)),Z=g.math('Subtract_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=travel,B=.4+(i%3)*.3),B=g.math('Multiply_DoubleDouble',A=g.math('Square',A=age),B=420.))));fade(g,'Spark'+str(i),g.math('FMax',A=0.,B=g.math('Subtract_DoubleDouble',A=1.,B=age)))
 compile_bp(impact);save(impact)
 # A travelling bolt sweeps a line every frame to prevent tunnelling.
 bolt=asset(D+'/BP_AtomicBolt');comp(bolt,'BoltCore',sphere,mats['glow'],scale=(.65,.1,.1));var(bolt,'Birth','real','0');var(bolt,'Speed','real','6500');var(bolt,'HitOnce','bool','false');var(bolt,'Ignore',B.get_array_type(actorref()),'()');compile_bp(bolt)
 g=Graph(bolt);g.e.remove_nodes(g.e.list_all_nodes());g.override('ReceiveBeginPlay');g.set('Birth',g.now());g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=g.get('Ignore'),NewItem=g.out(g.call('Engine.Actor.GetOwner'))));g.do(g.call('Engine.Actor.SetLifeSpan',InLifespan=1.9))
 g.override('ReceiveTick');g.branch(g.math('Not_PreBool',A=g.get('HitOnce')));start=g.out(g.call('Engine.Actor.K2_GetActorLocation'));fw=g.out(g.call('Engine.Actor.GetActorForwardVector'));end=g.math('Add_VectorVector',A=start,B=g.math('Multiply_VectorFloat',A=fw,B=g.math('Multiply_DoubleDouble',A=g.get('Speed'),B=g.dt())))
 trace=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=start,End=end,TraceChannel='TraceTypeQuery1',bTraceComplex=False,ActorsToIgnore=g.get('Ignore'),bIgnoreSelf=True,DrawDebugType='None'));br=g.branch(g.out(trace));miss=br.find_else_pin();g.set('HitOnce',True);hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(trace,'OutHit'));point=g.math('Add_VectorVector',A=g.out(hit,'ImpactPoint'),B=g.math('Multiply_VectorFloat',A=g.out(hit,'ImpactNormal'),B=12.));g.spawn(B.generated_class(impact).get_path_name(),point,owner=g.out(g.call('Engine.Actor.GetOwner')));g.do(g.call('Engine.Actor.K2_DestroyActor'));g.cursor=miss;g.do(g.call('Engine.Actor.K2_SetActorLocation',NewLocation=end,bSweep=False,bTeleport=False));compile_bp(bolt);save(bolt)
 muzzlefx=asset(D+'/BP_AtomicMuzzle');comp(muzzlefx,'Flash',sphere,mats['core'],scale=(.45,.3,.3));compile_bp(muzzlefx);unreal.get_default_object(B.generated_class(muzzlefx)).set_editor_property('initial_life_span',.08);save(muzzlefx)
 shake=asset(D+'/CS_AtomicRecoil',unreal.LegacyCameraShake);compile_bp(shake);cd=unreal.get_default_object(B.generated_class(shake));cd.set_editor_property('oscillation_duration',.32);cd.set_editor_property('oscillation_blend_in_time',.015);cd.set_editor_property('oscillation_blend_out_time',.25)
 rr=cd.get_editor_property('rot_oscillation');pitch=rr.get_editor_property('pitch');pitch.set_editor_property('amplitude',1.5);pitch.set_editor_property('frequency',10.);rr.set_editor_property('pitch',pitch);cd.set_editor_property('rot_oscillation',rr);save(shake)
 # First-person hands share the rig transform with the gun, so kickback cannot detach them.
 bp=A.load_asset(P)
 for n,k,v in [('AtomicLastShot','real','-100'),('AtomicEquipAlpha','real','0'),('bAtomicWasEquipped','bool','false'),('bAtomicFPArmsHidden','bool','false'),('AtomicEquipSpeed','real','6'),('AtomicRecoilDistance','real','7'),('AtomicRecoilPitch','real','5')]:var(bp,n,k,v)
 var(bp,'AtomicLastMuzzle',B.get_struct_type(unreal.Vector.static_struct()),'(X=0,Y=0,Z=0)');compile_bp(bp)
 rig=add(bp,unreal.SceneComponent,'AtomicFPRig','FirstPersonCamera');rig.set_mobility(unreal.ComponentMobility.MOVABLE)
 hand=add(bp,unreal.SkeletalMeshComponent,'AtomicFPArms','AtomicFPRig');hand.set_skeletal_mesh_asset(arms);hand.set_mobility(unreal.ComponentMobility.MOVABLE);hand.set_collision_profile_name('NoCollision');hand.set_editor_property('only_owner_see',True);hand.set_editor_property('cast_shadow',False);hand.set_editor_property('relative_location',V(-5,-6,-180));hand.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90));hand.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
 fg=comp(bp,'AtomicFPGun',gun,mats['steel'],'AtomicFPRig',(.65,.65,.65),(28,16,-19));fg.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90));fg.set_editor_property('only_owner_see',True)
 tg=comp(bp,'AtomicTPGun',gun,mats['steel'],'Mesh',(.65,.65,.65));tg.set_editor_property('owner_no_see',False)
 # Restore per-section material slots after the generic component helper.
 for c in (fg,tg):
  for i,slot in enumerate(gun.static_materials):c.set_material(i,slot.material_interface)
 fm=add(bp,unreal.SceneComponent,'AtomicFPMuzzle','AtomicFPRig');fm.set_editor_property('relative_location',V(75,16,-14))
 tm=add(bp,unreal.SceneComponent,'AtomicTPMuzzle','AtomicTPGun');tm.set_editor_property('relative_location',V(0,64,3))
 compile_bp(bp)
 g=Graph(bp,'Atomic_Equip');g.do(g.call('Engine.SkeletalMeshComponent.SetAnimInstanceClass',target=g.get('Mesh'),NewClass=B.generated_class(A.load_asset(D+'/ABP_AtomicBody')).get_path_name()));g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get('AtomicFPArms'),NewAnimToPlay=D+'/Animations/Atomic_MF_Rifle_Idle_ADS',bLooping=True));g.set('bAtomicWasEquipped',True)
 g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get('AtomicTPGun'),Parent=g.get('Mesh'),SocketName='CC_Base_R_Hand',LocationRule='KeepRelative',RotationRule='KeepRelative',ScaleRule='KeepRelative',bWeldSimulatedBodies=False))
 seq=A.load_asset(D+'/Animations/Atomic_MF_Rifle_Idle_ADS');pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,0.,unreal.AnimPoseEvaluationOptions());ht=unreal.AnimPoseExtensions.get_bone_pose(pose,'CC_Base_R_Hand',unreal.AnimPoseSpaces.WORLD);desired=ht.translation+V(4,22,7);offset=unreal.MathLibrary.inverse_transform_location(ht,desired);rot=unreal.MathLibrary.inverse_transform_rotation(ht,unreal.Rotator())
 rel(g,'AtomicTPGun',pos=str(offset.export_text()),rot=g.math('MakeRotator',Pitch=rot.pitch,Yaw=rot.yaw,Roll=rot.roll));compile_bp(bp)
 g=Graph(bp,'Atomic_Unequip');g.do(g.call('Engine.SkeletalMeshComponent.SetAnimInstanceClass',target=g.get('Mesh'),NewClass='/Game/Characters/BlackSentinel/Animations/BS_ABP_PlayerGuard.BS_ABP_PlayerGuard_C'));g.set('bAtomicWasEquipped',False);compile_bp(bp)
 g=Graph(bp,'Atomic_Update');active=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=2);br=g.branch(active);off=br.find_else_pin();need=g.branch(g.math('Not_PreBool',A=g.get('bAtomicWasEquipped')));skip=need.find_else_pin();g.do(g.own('Atomic_Equip'));merge=g.set('AtomicEquipAlpha',g.math('FInterpTo',Current=g.get('AtomicEquipAlpha'),Target=1.,DeltaTime=g.dt(),InterpSpeed=g.get('AtomicEquipSpeed')));link(skip,merge.find_execute_pin());onend=g.cursor
 g.cursor=off;need=g.branch(g.get('bAtomicWasEquipped'));skip=need.find_else_pin();g.do(g.own('Atomic_Unequip'));merge=g.set('AtomicEquipAlpha',g.math('FInterpTo',Current=g.get('AtomicEquipAlpha'),Target=0.,DeltaTime=g.dt(),InterpSpeed=10.));link(skip,merge.find_execute_pin());common=g.set('AtomicLastShot',g.get('AtomicLastShot'));link(onend,common.find_execute_pin())
 first=g.math('BooleanAND',A=active,B=g.get('bFirstPerson'));third=g.math('BooleanAND',A=active,B=g.math('Not_PreBool',A=g.get('bFirstPerson')))
 for name,show in [('AtomicFPArms',first),('AtomicFPGun',first),('AtomicTPGun',third)]:g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(name),bNewVisibility=show,bPropagateToChildren=True))
 # Hide only the original body's arms while its separate view-model is visible.
 br=g.branch(first);other=br.find_else_pin()
 for side in ('L','R'):g.do(g.call('Engine.SkinnedMeshComponent.HideBoneByName',target=g.get('Mesh'),BoneName='CC_Base_'+side+'_Upperarm',PhysBodyOption='PBO_None'))
 endpoint=g.cursor;g.cursor=other
 for side in ('L','R'):g.do(g.call('Engine.SkinnedMeshComponent.UnHideBoneByName',target=g.get('Mesh'),BoneName='CC_Base_'+side+'_Upperarm'))
 merge=g.set('bAtomicFPArmsHidden',first);link(endpoint,merge.find_execute_pin())
 age=g.math('Subtract_DoubleDouble',A=g.now(),B=g.get('AtomicLastShot'));kick=g.math('Square',A=g.math('FClamp',Value=g.math('Subtract_DoubleDouble',A=1.,B=g.math('Divide_DoubleDouble',A=age,B=.42)),Min=0.,Max=1.));lower=g.math('Subtract_DoubleDouble',A=1.,B=g.get('AtomicEquipAlpha'))
 rel(g,'AtomicFPRig',pos=g.math('MakeVector',X=g.math('Multiply_DoubleDouble',A=kick,B=g.math('Multiply_DoubleDouble',A=g.get('AtomicRecoilDistance'),B=-1.)),Y=0.,Z=g.math('Multiply_DoubleDouble',A=lower,B=-28.)),rot=g.math('MakeRotator',Pitch=g.math('Add_DoubleDouble',A=g.math('Multiply_DoubleDouble',A=kick,B=g.get('AtomicRecoilPitch')),B=g.math('Multiply_DoubleDouble',A=lower,B=-15.)),Yaw=0.,Roll=0.));compile_bp(bp)
 hookfn(bp,'Modes_Update','Atomic_Update','AtomicWeaponTick')
 # The laser belongs exclusively to Hunter; atomic mode uses the supplied rifle.
 g=Graph(bp,'Modes_ApplyVisuals');hunter=g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=1)
 for n,fp in [('FP_LaserWeapon',True),('TP_LaserWeapon',False)]:g.do(g.call('Engine.SceneComponent.SetVisibility',target=g.get(n),bNewVisibility=g.math('BooleanAND',A=hunter,B=g.get('bFirstPerson') if fp else g.math('Not_PreBool',A=g.get('bFirstPerson'))),bPropagateToChildren=True))
 compile_bp(bp)
 g=Graph(bp,'Protocol_Fire');g.branch(g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=2));g.branch(g.math('Not_PreBool',A=g.get('bModeMenuOpen')));g.branch(g.math('Not_PreBool',A=g.get('bAdminFlight')));g.branch(g.math('Not_PreBool',A=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc()))));g.branch(g.math('Greater_DoubleDouble',A=g.get('VisorIntegrity'),B=0.));g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('ProtocolNextFire')))
 g.set('ProtocolNextFire',g.math('Add_DoubleDouble',A=g.now(),B=g.get('ProtocolCooldown')));g.set('AtomicLastShot',g.now());g.count('ProtocolShots')
 cam=g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0));eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=cam));forward=g.math('GetForwardVector',InRot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=cam)));end=g.math('Add_VectorVector',A=eye,B=g.math('Multiply_VectorFloat',A=forward,B=12000.))
 tr=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=eye,End=end,TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'));h=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(tr,'OutHit'));aim=g.math('SelectVector',A=g.out(h,'ImpactPoint'),B=end,bPickA=g.out(tr))
 muzzle=g.math('SelectVector',A=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('AtomicFPMuzzle'))),B=g.out(g.call('Engine.SceneComponent.K2_GetComponentLocation',target=g.get('AtomicTPMuzzle'))),bPickA=g.get('bFirstPerson'));g.set('AtomicLastMuzzle',muzzle)
 # An initial sweep from camera to muzzle prevents firing through a near wall.
 near=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=eye,End=muzzle,TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'));nh=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(near,'OutHit'));safe=g.math('SelectVector',A=g.math('Add_VectorVector',A=g.out(nh,'ImpactPoint'),B=g.math('Multiply_VectorFloat',A=g.out(nh,'ImpactNormal'),B=3.)),B=muzzle,bPickA=g.out(near))
 g.spawn(B.generated_class(bolt).get_path_name(),safe,g.math('FindLookAtRotation',Start=safe,Target=aim),g.self());g.spawn(B.generated_class(muzzlefx).get_path_name(),safe,owner=g.self());g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=FX+'/S_Plasma',Location=safe,VolumeMultiplier=.65));g.do(g.call('Engine.PlayerCameraManager.StartCameraShake',target=cam,ShakeClass=B.generated_class(shake).get_path_name(),Scale=1.));compile_bp(bp);save(bp)
 R.update(saved=True,gun=gun.get_path_name(),arms=arms.get_path_name(),cooldown=8,projectile_lifetime=1.9,impact_lifetime=1.6,new_unique_textures=0,impact_meshes=17,shadow_casting_fx_lights=0)
except Exception:R['error']=traceback.format_exc();unreal.log_error(R['error'])
json.dump(R,open(os.path.join(S,'atomic_weapon_build.json'),'w'),indent=2)
assert R['saved'],R
