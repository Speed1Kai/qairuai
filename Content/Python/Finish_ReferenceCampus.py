"""Finish the authored site with a recoverable bridge gap and review camera."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,add,components,compile_bp,save,Graph,pin,val,link
def V(p):return unreal.Vector(x=p[0],y=p[1],z=p[2])
O=(10006.289955343997,6612.598659341473,2150.)
def L(p):return V(tuple(p[i]-O[i] for i in range(3)))
class Flow(Graph):
    def do(self,n):
        if any(str(p.get_pin_name())=='execute' for p in n.list_all_pins()):return super().do(n)
        return n
path='/Game/Surface/ReferencePlan/BP_ReferenceBridgeSafety'
if not A.does_asset_exist(path):
    f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
    bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ReferenceBridgeSafety','/Game/Surface/ReferencePlan',unreal.Blueprint,f)
    e=G.get_graph_editor_by_name(bp,'EventGraph')
    assert e.add_member_variable('SafeBankY',B.get_basic_type_by_name('real'),'18900')
    g=Flow(bp)
    event=next(m for m in g.e.list_available_nodes([]) if str(m).endswith('|СобытиеTick'))
    n=g.e.create_node_from_name(event,unreal.Vector2D(x=0,y=0),[]);g.cursor=n.find_then_pin()
    p=g.out(g.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
    g.branch(g.out(g.call('Engine.KismetSystemLibrary.IsValid',Object=p)))
    q=g.call('Engine.KismetMathLibrary.BreakVector',InVec=g.out(g.call('Engine.Actor.K2_GetActorLocation',target=p)))
    x=g.out(q,'X');y=g.out(q,'Y');z=g.out(q,'Z')
    def inside(k,a,b):return g.math('BooleanAND',A=g.math('Greater_DoubleDouble',A=k,B=a),B=g.math('Less_DoubleDouble',A=k,B=b))
    g.branch(inside(x,3500,8200));g.branch(inside(y,17800,22500))
    br=g.branch(g.math('Less_DoubleDouble',A=z,B=1200));safe=br.find_else_pin()
    g.do(g.call('Engine.Actor.K2_SetActorLocation',target=p,NewLocation=g.math('MakeVector',X=5850.,Y=g.get('SafeBankY'),Z=2270.),bSweep=False,bTeleport=True))
    g.cursor=safe;g.branch(g.math('Greater_DoubleDouble',A=z,B=2200))
    br=g.branch(g.math('Less_DoubleDouble',A=y,B=19400));far=br.find_else_pin();g.set('SafeBankY',18900.)
    g.cursor=far;g.branch(g.math('Greater_DoubleDouble',A=y,B=20600));g.set('SafeBankY',21800.)
    compile_bp(bp);cdo=unreal.get_default_object(B.generated_class(bp));t=cdo.get_editor_property('primary_actor_tick');t.set_editor_property('tick_interval',.2);cdo.set_editor_property('primary_actor_tick',t);save(bp)
else:bp=A.load_asset(path)
world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/Lvl_CampusConnected')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not any(a.get_class().get_name()=='BP_ReferenceBridgeSafety_C' for a in sub.get_all_level_actors()):
    a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label('REF_BridgeSafety');a.set_folder_path('SURFACE/ReferencePlan')
if not any(a.get_actor_label()=='REF_OverviewCamera' for a in sub.get_all_level_actors()):
    a=sub.spawn_actor_from_class(unreal.CameraActor,L((5800,9200,28000)),unreal.Rotator(pitch=-90,yaw=0,roll=0));a.set_actor_label('REF_OverviewCamera');a.set_folder_path('SURFACE/ReferencePlan')
    c=a.get_component_by_class(unreal.CameraComponent);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('projection_mode',unreal.CameraProjectionMode.ORTHOGRAPHIC);c.set_editor_property('ortho_width',32000.);c.set_editor_property('constrain_aspect_ratio',False)
assert unreal.EditorLoadingAndSavingUtils.save_current_level()
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
json.dump({'saved':True,'bridge_recovery':True,'overview_camera':True},open(os.path.join(unreal.Paths.project_saved_dir(),'reference_campus_finish.json'),'w'))

import Test_ReferenceCampus

