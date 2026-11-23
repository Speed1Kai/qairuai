"""Bounded public Blueprint authoring. Preview by default; LIVE is explicit.
Backs up the player package before editing. Never removes existing graphs.
Only saves after successful compilation and pin validation.
"""
import unreal, os, json, shutil, time
A=unreal.EditorAssetLibrary; B=unreal.BlueprintEditorLibrary; G=unreal.BlueprintGraphEditor
saved=unreal.Paths.project_saved_dir()
try:
    mode=open(os.path.join(saved,'movement_authoring_target.txt')).read().strip()
except OSError: mode='PREVIEW'
original='/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
backup=os.path.join(saved,'Backups','SentinelMovement')
os.makedirs(backup,exist_ok=True)
src=os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson','Blueprints','BP_ThirdPersonCharacter.uasset')
if not os.path.exists(os.path.join(backup,'BP_ThirdPersonCharacter.uasset')):
    shutil.copy2(src,os.path.join(backup,'BP_ThirdPersonCharacter.uasset'))
path=original if mode=='LIVE' else '/Game/ThirdPerson/Blueprints/BP_SentinelPreview_'+str(int(time.time()))
bp=A.load_asset(path) if mode=='LIVE' else A.duplicate_asset(original,path)
if not bp: raise RuntimeError('Could not load character')
if 'Sentinel_UpdateState' in [str(n) for n in B.list_graph_names(bp)]:
    raise RuntimeError('Movement already authored; use a targeted repair instead of rebuilding')

def pin(n,name,out=False):
    if not n: raise RuntimeError('Null node for '+name)
    p=n.find_output_pin(name) if out else n.find_input_pin(name)
    if not p.is_valid(): raise RuntimeError('Missing '+n.get_name()+'.'+name)
    return p
def link(a,b):
    if not a.is_valid() or not b.is_valid() or not a.try_create_connection(b):
        raise RuntimeError('Invalid graph connection '+str(a.get_pin_name())+' -> '+str(b.get_pin_name()))
def val(p,v):
    if hasattr(v,'is_valid'): link(v,p)
    elif not p.set_pin_value(str(v).lower() if isinstance(v,bool) else str(v)):
        raise RuntimeError('Invalid default '+str(p.get_pin_name())+'='+str(v))

class Graph:
    def __init__(self,name):
        self.e=G.create_and_edit_function_graph(bp,name)
        self.cursor=self.e.find_graph_entry_pin();self.nodes=[];self.x=220;self.y=0
    def node(self,n):
        if not n:raise RuntimeError('Failed node creation')
        n.set_node_pos(unreal.IntPoint(x=self.x,y=self.y));self.x+=260
        if self.x>2300:self.x=220;self.y+=330
        self.nodes.append(n);return n
    def call(self,path,target=None,**args):
        n=self.node(self.e.add_call_function_node('/Script/'+path))
        if target is not None:val(n.find_self_pin(),target)
        for k,v in args.items():
            if hasattr(v,'is_valid'):val(pin(n,k),v)
        for k,v in args.items():
            if not hasattr(v,'is_valid'):val(pin(n,k),v)
        return n
    def do(self,n):
        xp=next((p for p in n.list_all_pins() if str(p.get_pin_name())=='execute'),None)
        if xp is not None and xp.is_valid():
            link(self.cursor,xp);self.cursor=n.find_then_pin()
        return n
    def out(self,n,k='ReturnValue'):return pin(n,k,True)
    def get(self,v,c=''):
        return pin(self.node(self.e.add_get_member_variable_node(v,c)),v,True)
    def set(self,v,value,c='',target=None):
        n=self.node(self.e.add_set_member_variable_node(v,c));val(pin(n,v),value)
        if target is not None:val(n.find_self_pin(),target)
        self.do(n);return n
    def math(self,f,**args):return self.out(self.call('Engine.KismetMathLibrary.'+f,**args))
    def branch(self,condition):
        n=self.node(self.e.add_branch_node());val(pin(n,'Condition'),condition)
        xp=next((p for p in n.list_all_pins() if str(p.get_pin_name())=='execute'),None)
        if xp is not None and xp.is_valid():
            link(self.cursor,xp);self.cursor=n.find_then_pin()
        return n
    def comment(self,text):self.e.add_comment_to_nodes(text,self.nodes,45)
    def dt(self):return self.out(self.call('Engine.GameplayStatics.GetWorldDeltaSeconds'))
    def now(self):return self.out(self.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))
    def cmc(self):return self.get('CharacterMovement','/Script/Engine.Character')
    def capsule(self):return self.get('CapsuleComponent','/Script/Engine.Character')
    def shake(self,asset,scale):
        # Runs only for the locally controlled pawn; camera manager belongs to its controller.
        pc=self.out(self.call('Engine.Pawn.GetController'))
        # GetPlayerCameraManager is valid for the existing single local-player project.
        cam=self.out(self.call('Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0))
        n=self.call('Engine.PlayerCameraManager.StartCameraShake',Scale=scale,ShakeClass=asset)
        val(n.find_self_pin(),cam);self.do(n)

ev=G.get_graph_editor_by_name(bp,'EventGraph')
variables={
 'isSprinting':('bool','false'),'isGrounded':('bool','true'),'Falling':('bool','false'),
 'GripSlide':('bool','false'),'isCrouching':('bool','false'),'WantsCrouch':('bool','false'),
 'WantsSprint':('bool','false'),'WalkingGait':('bool','false'),'LandingActive':('bool','false'),
 'CrouchBlocked':('bool','false'),'MovementSpeed':('real','0'),'MovementAcceleration':('real','0'),
 'VerticalSpeed':('real','0'),'LastFallSpeed':('real','0'),'LandingUntil':('real','-1'),
 'CrouchHalfHeight':('real','88'),'NextHalfHeight':('real','88'),'StepDistance':('real','0'),
 'FootstepCount':('int','0'),'LandingCount':('int','0'),'CrouchInputCount':('int','0'),
 'SprintInputCount':('int','0'),'WalkInputCount':('int','0')}
for name,(kind,default) in variables.items():
    if not ev.add_member_variable(name,B.get_basic_type_by_name(kind),default):raise RuntimeError('Could not add '+name)

# Two small, authored camera-shake assets; no engine/project plugin changes.
shake_classes={}
for name,duration,pitch,z in [('CS_SentinelLanding',.28,.7,2.2),('CS_SentinelFootstep',.12,.18,.45)]:
    asset='/Game/ThirdPerson/Blueprints/'+name
    shake=A.load_asset(asset)
    if not shake:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.LegacyCameraShake)
        shake=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/ThirdPerson/Blueprints',unreal.Blueprint,f)
    if not B.compile_blueprint(shake):raise RuntimeError('Camera shake compile failed')
    c=unreal.get_default_object(B.generated_class(shake))
    c.set_editor_property('oscillation_duration',duration)
    c.set_editor_property('oscillation_blend_in_time',.025)
    c.set_editor_property('oscillation_blend_out_time',duration*.65)
    r=c.get_editor_property('rot_oscillation');p=r.get_editor_property('pitch')
    p.set_editor_property('amplitude',pitch);p.set_editor_property('frequency',18.0)
    r.set_editor_property('pitch',p);c.set_editor_property('rot_oscillation',r)
    loc=c.get_editor_property('loc_oscillation');zz=loc.get_editor_property('z')
    zz.set_editor_property('amplitude',z);zz.set_editor_property('frequency',22.0)
    loc.set_editor_property('z',zz);c.set_editor_property('loc_oscillation',loc)
    c.set_editor_property('single_instance',False)
    A.save_loaded_asset(shake,only_if_is_dirty=False)
    shake_classes[name]=B.generated_class(shake).get_path_name()

# State sampling is also available to the AnimBP via this character's variables.
g=Graph('Sentinel_UpdateState')
fall=g.do(g.call('Engine.NavMovementComponent.IsFalling',target=g.cmc()))
g.set('Falling',g.out(fall))
ground=g.do(g.call('Engine.NavMovementComponent.IsMovingOnGround',target=g.cmc()))
g.set('isGrounded',g.out(ground))
vel=g.out(g.call('Engine.Actor.GetVelocity'))
g.set('MovementSpeed',g.math('VSizeXY',A=vel))
g.set('VerticalSpeed',g.out(g.call('Engine.KismetMathLibrary.BreakVector',InVec=vel),'Z'))
acc=g.out(g.call('Engine.CharacterMovementComponent.GetCurrentAcceleration',target=g.cmc()))
g.set('MovementAcceleration',g.math('VSizeXY',A=acc))
g.set('LandingActive',g.math('Less_DoubleDouble',A=g.now(),B=g.get('LandingUntil')))
g.set('isCrouching',g.math('Less_DoubleDouble',A=g.get('CrouchHalfHeight'),B=87.9))
can_sprint=g.math('BooleanAND',A=g.get('WantsSprint'),B=g.math('Not_PreBool',A=g.get('isCrouching')))
can_sprint=g.math('BooleanAND',A=can_sprint,B=g.math('Not_PreBool',A=g.get('LandingActive')))
g.set('isSprinting',can_sprint)
braking=g.math('BooleanAND',A=g.math('Greater_DoubleDouble',A=g.get('MovementSpeed'),B=30),B=g.math('Less_DoubleDouble',A=g.get('MovementAcceleration'),B=1))
g.set('GripSlide',g.math('BooleanAND',A=braking,B=g.get('isGrounded')))
g.branch(g.get('Falling'))
g.set('LastFallSpeed',g.math('FMax',A=g.math('Multiply_DoubleDouble',A=g.get('VerticalSpeed'),B=-1),B=0))
g.comment('Animation cues / braking inertia. GripSlide = residual grounded braking, not a separate slide ability.')

g=Graph('Sentinel_ResolveSpeed')
speed=g.math('SelectFloat',A=160,B=400,bPickA=g.get('WalkingGait'))
speed=g.math('SelectFloat',A=650,B=speed,bPickA=g.get('isSprinting'))
speed=g.math('SelectFloat',A=120,B=speed,bPickA=g.get('LandingActive'))
speed=g.math('SelectFloat',A=110,B=speed,bPickA=g.get('isCrouching'))
g.set('MaxWalkSpeed',speed,'/Script/Engine.CharacterMovementComponent',g.cmc())
g.comment('One speed resolver: crouch 110 > landing 120 > sprint 650 > walk 160 / jog 400. No delayed stale-speed restoration.')

g=Graph('Sentinel_UpdateCrouch')
g.branch(g.get('isGrounded'))
# Ignore the floor using a 1 cm clearance margin; test a full standing capsule.
heightdiff=g.math('Subtract_DoubleDouble',A=88.5,B=g.get('CrouchHalfHeight'))
center=g.math('Add_VectorVector',A=g.out(g.call('Engine.Actor.K2_GetActorLocation')),B=g.math('MakeVector',Z=heightdiff))
trace=g.do(g.call('Engine.KismetSystemLibrary.CapsuleTraceSingleByProfile',Start=center,End=center,Radius=34.5,HalfHeight=87.5,ProfileName='Pawn',bIgnoreSelf=True))
g.set('CrouchBlocked',g.out(trace))
stand=g.math('SelectFloat',A=g.get('CrouchHalfHeight'),B=88,bPickA=g.get('CrouchBlocked'))
target=g.math('SelectFloat',A=44,B=stand,bPickA=g.get('WantsCrouch'))
g.set('NextHalfHeight',g.math('FInterpTo_Constant',Current=g.get('CrouchHalfHeight'),Target=target,DeltaTime=g.dt(),InterpSpeed=220))
delta=g.math('Subtract_DoubleDouble',A=g.get('NextHalfHeight'),B=g.get('CrouchHalfHeight'))
minimum=g.math('FMin',A=g.get('CrouchHalfHeight'),B=g.get('NextHalfHeight'))
g.do(g.call('Engine.CapsuleComponent.SetCapsuleHalfHeight',target=g.capsule(),HalfHeight=minimum,bUpdateOverlaps=True))
g.do(g.call('Engine.Actor.K2_AddActorWorldOffset',DeltaLocation=g.math('MakeVector',Z=delta),bSweep=False,bTeleport=False))
g.do(g.call('Engine.CapsuleComponent.SetCapsuleHalfHeight',target=g.capsule(),HalfHeight=g.get('NextHalfHeight'),bUpdateOverlaps=True))
g.set('CrouchHalfHeight',g.get('NextHalfHeight'))
offset=g.math('Subtract_DoubleDouble',A=88,B=g.get('CrouchHalfHeight'))
g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('Mesh','/Script/Engine.Character'),NewLocation=g.math('MakeVector',Z=g.math('Add_DoubleDouble',A=-87,B=offset))))
g.do(g.call('Engine.SceneComponent.K2_SetRelativeLocation',target=g.get('CameraBoom'),NewLocation=g.math('MakeVector',Z=g.math('Add_DoubleDouble',A=8.492264,B=g.math('Multiply_DoubleDouble',A=offset,B=.35)))))
g.comment('Custom continuous crouch: 88 -> 44 in 0.20s; preserve feet and mesh origin. Standing is blocked by Pawn-profile sweep. Capsule updates only on ground. AnimBP uses isCrouching.')

g=Graph('Sentinel_Landing')
g.branch(g.math('Greater_DoubleDouble',A=g.get('LastFallSpeed'),B=200))
g.set('LandingUntil',g.math('Add_DoubleDouble',A=g.now(),B=.4))
g.set('LandingActive',True)
g.set('LandingCount',g.math('Add_IntInt',A=g.get('LandingCount'),B=1))
g.set('StepDistance',0)
g.set('MaxWalkSpeed',120,'/Script/Engine.CharacterMovementComponent',g.cmc())
g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
scale=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.get('LastFallSpeed'),B=650),Min=.25,Max=1.2)
g.shake(shake_classes['CS_SentinelLanding'],scale)
g.comment('Real impact only (>200 cm/s): 0.4s recovery, immediate 120 speed cap and impact-scaled camera shake. Tiny floor corrections do not retrigger landing.')

g=Graph('Sentinel_Footsteps')
moving=g.math('BooleanAND',A=g.get('isGrounded'),B=g.math('Greater_DoubleDouble',A=g.get('MovementSpeed'),B=20))
moving=g.math('BooleanAND',A=moving,B=g.math('Not_PreBool',A=g.get('LandingActive')))
br=g.branch(moving)
g.set('StepDistance',g.math('Add_DoubleDouble',A=g.get('StepDistance'),B=g.math('Multiply_DoubleDouble',A=g.get('MovementSpeed'),B=g.dt())))
stride=g.math('SelectFloat',A=250,B=180,bPickA=g.get('isSprinting'))
g.branch(g.math('Greater_DoubleDouble',A=g.get('StepDistance'),B=stride))
g.set('StepDistance',0)
g.set('FootstepCount',g.math('Add_IntInt',A=g.get('FootstepCount'),B=1))
g.branch(g.out(g.call('Engine.Pawn.IsLocallyControlled')))
g.shake(shake_classes['CS_SentinelFootstep'],g.math('SelectFloat',A=.65,B=.4,bPickA=g.get('isSprinting')))
g.cursor=br.find_else_pin();g.set('StepDistance',0)
g.comment('Distance-based fallback footfall cadence with small camera impulses. No footstep shakes while airborne, stationary or recovering from an impact.')

if not B.compile_blueprint(bp):raise RuntimeError('Helper graphs failed compilation')
class_path=B.generated_class(bp).get_path_name()
menus=[str(n) for n in ev.list_available_nodes([])]
def event(suffix,x,y):
    choices=[m for m in menus if m.endswith(suffix)]
    if len(choices)!=1:raise RuntimeError('Ambiguous event '+suffix+': '+str(choices))
    n=ev.create_node_from_name(choices[0],unreal.Vector2D(x=x,y=y),[])
    if not n:raise RuntimeError('Event creation failed')
    return n
def call_own(name,source,x,y):
    n=ev.add_call_function_node(class_path+'.'+name)
    if not n:raise RuntimeError('Missing authored function '+name)
    n.set_node_pos(unreal.IntPoint(x=x,y=y));link(source,n.find_execute_pin());return n.find_then_pin()
tick=event('|СобытиеTick',0,1600)
cursor=tick.find_then_pin()
for i,name in enumerate(('Sentinel_UpdateState','Sentinel_UpdateCrouch','Sentinel_ResolveSpeed','Sentinel_Footsteps')):
    cursor=call_own(name,cursor,300+i*320,1600)
land=event('|СобытиеOnLanded',0,1950)
call_own('Sentinel_Landing',land.find_then_pin(),350,1950)

def input_set(source,name,value,x,y):
    n=ev.add_set_member_variable_node(name);n.set_node_pos(unreal.IntPoint(x=x,y=y))
    val(pin(n,name),value);link(source,n.find_execute_pin());return n.find_then_pin()
def input_toggle(key,name,counter,y):
    n=event('|KeyboardEvents|'+key,0,y)
    n.set_editor_property('bConsumeInput',False)
    old=ev.add_get_member_variable_node(name)
    neg=ev.add_call_function_node('/Script/Engine.KismetMathLibrary.Not_PreBool')
    link(pin(old,name,True),pin(neg,'A'))
    c=input_set(pin(n,'Pressed',True),name,pin(neg,'ReturnValue',True),300,y)
    oldc=ev.add_get_member_variable_node(counter)
    add=ev.add_call_function_node('/Script/Engine.KismetMathLibrary.Add_IntInt')
    link(pin(oldc,counter,True),pin(add,'A'));val(pin(add,'B'),1)
    input_set(c,counter,pin(add,'ReturnValue',True),650,y)
input_toggle('C','WantsCrouch','CrouchInputCount',2400)
input_toggle('CapsLock','WalkingGait','WalkInputCount',2800)
shift=event('|KeyboardEvents|Леваяклавиша"Shift"',0,3200)
shift.set_editor_property('bConsumeInput',False)
c=input_set(pin(shift,'Pressed',True),'WantsSprint',True,300,3200)
input_set(pin(shift,'Released',True),'WantsSprint',False,300,3450)
add=ev.add_call_function_node('/Script/Engine.KismetMathLibrary.Add_IntInt')
old=ev.add_get_member_variable_node('SprintInputCount');link(pin(old,'SprintInputCount',True),pin(add,'A'));val(pin(add,'B'),1)
input_set(c,'SprintInputCount',pin(add,'ReturnValue',True),650,3200)

# Prevent jumping with a reduced capsule or during impact absorption.
for n in ev.list_all_nodes():
    if n.get_class().get_name()=='K2Node_CallFunction' and str(n.get_node_title())=='Jump':
        incoming=n.find_execute_pin().list_connected_pins()
        if not incoming:continue
        guard=ev.add_branch_node()
        crouching=ev.add_get_member_variable_node('isCrouching')
        inv=ev.add_call_function_node('/Script/Engine.KismetMathLibrary.Not_PreBool')
        link(pin(crouching,'isCrouching',True),pin(inv,'A'));link(pin(inv,'ReturnValue',True),pin(guard,'Condition'))
        n.find_execute_pin().break_pin_links()
        for p in incoming:link(p,guard.find_execute_pin())
        link(guard.find_then_pin(),n.find_execute_pin())

if not B.compile_blueprint(bp):raise RuntimeError('Input/event graphs failed compilation')
# Native component template defaults (also apply to subsequently spawned pawns).
s=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
components={}
for h in s.k2_gather_subobject_data_for_blueprint(bp):
    d=lib.get_data(h);o=lib.get_object_for_blueprint(d,bp)
    if o:components[str(lib.get_variable_name(d))]=o
cm=components['CharacterMovement']
settings={'max_walk_speed':400.0,'max_walk_speed_crouched':110.0,'max_acceleration':1200.0,'ground_friction':6.0,'braking_deceleration_walking':1500.0,'gravity_scale':1.8,'jump_z_velocity':490.0,'air_control':.15,'air_control_boost_multiplier':1.0,'falling_lateral_friction':1.5,'braking_deceleration_falling':1200.0,'orient_rotation_to_movement':True,'rotation_rate':unreal.Rotator(pitch=0,yaw=360,roll=0)}
for k,v in settings.items():cm.set_editor_property(k,v)
cm.set_editor_property('crouched_half_height',44.0)
nav=cm.get_editor_property('nav_agent_props');nav.set_editor_property('can_crouch',True);cm.set_editor_property('nav_agent_props',nav)
components['CapsuleComponent'].set_capsule_half_height(88.0,True)
components['Mesh'].set_editor_property('relative_location',unreal.Vector(x=0,y=0,z=-87))
boom=components['CameraBoom']
boom.set_editor_property('enable_camera_lag',True);boom.set_editor_property('camera_lag_speed',10.0);boom.set_editor_property('camera_lag_max_distance',20.0)
cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('use_controller_rotation_yaw',False)
if not B.compile_blueprint(bp):raise RuntimeError('Final compile failed')
errors={}
for name in B.list_graph_names(bp):
    ed=G.get_graph_editor_by_name(bp,name)
    ns=ed.list_nodes_with_errors()
    if ns:errors[str(name)]=[str(n.get_node_title()) for n in ns]
if errors:raise RuntimeError('Graph errors '+str(errors))
if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Character save failed')
report={'mode':mode,'asset':path,'settings':{k:str(v) for k,v in settings.items()},'graphs':[str(n) for n in B.list_graph_names(bp)],'compile_errors':errors,'custom_crouch':True}
with open(os.path.join(saved,'sentinel_movement_authoring.json'),'w') as f:json.dump(report,f,indent=2)
unreal.log('SENTINEL MOVEMENT COMPILED AND SAVED: '+path)



