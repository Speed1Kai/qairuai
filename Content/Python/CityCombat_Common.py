import unreal,os,sys
from Industrial_Common import A,B,G,M,Graph as BaseGraph,pin,val,link,add,components,compile_bp,save
ROOT='/Game/Enemies/Enceladus';FX='/Game/Combat/Protocol'
def V(x=0,y=0,z=0):return unreal.Vector(x=x,y=y,z=z)
def asset(path,parent=unreal.Actor):
 if A.does_asset_exist(path):return A.load_asset(path)
 folder,name=path.rsplit('/',1);A.make_directory(folder);f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent)
 return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Blueprint,f)
def var(bp,name,kind,default):
 if name not in map(str,B.list_member_variable_names(bp)):
  typ=B.get_basic_type_by_name(kind) if isinstance(kind,str) else kind
  assert G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,typ,str(default))
def actorref():return B.get_object_reference_type(unreal.Actor)
class Graph(BaseGraph):
 def __init__(self,bp,name=None):
  super().__init__(bp)
  if name:
   self.e=G.get_graph_editor_by_name(bp,name) if name in map(str,B.list_graph_names(bp)) else G.create_and_edit_function_graph(bp,name)
   self.e.remove_nodes([n for n in self.e.list_all_nodes() if n.get_class().get_name() not in ('K2Node_FunctionEntry','K2Node_FunctionResult')]);self.cursor=self.e.find_graph_entry_pin()
 def do(self,n):
  return super().do(n) if n.find_execute_pin().is_valid() else n
 def math(self,n,**kw):
  if n=='Multiply_VectorFloat':
   v=self.call('Engine.KismetMathLibrary.BreakVector',InVec=kw['A'])
   xyz={k:super(Graph,self).math('Multiply_DoubleDouble',A=self.out(v,k),B=kw['B']) for k in ('X','Y','Z')}
   return super().math('MakeVector',**xyz)
  return super().math(n,**kw)
 def override(self,name):
  n=self.e.find_event_node(name)
  if not n:n=B.add_event_override(self.bp,name,unreal.IntPoint(x=0,y=2000))
  self.cursor=n.find_then_pin();return n
 def own(self,n):return self.node(self.e.add_call_function_node(B.generated_class(self.bp).get_path_name()+'.'+n))
 def self(self,component='CapsuleComponent'):return self.out(self.call('Engine.ActorComponent.GetOwner',target=self.get(component)))
 def now(self):return self.out(self.call('Engine.GameplayStatics.GetTimeSeconds'))
 def dt(self):return self.out(self.call('Engine.GameplayStatics.GetWorldDeltaSeconds'))
 def player(self):return self.out(self.call('Engine.GameplayStatics.GetPlayerCharacter',PlayerIndex=0))
 def pc(self):return self.out(self.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
 def count(self,n):self.set(n,self.math('Add_IntInt',A=self.get(n),B=1))
 def valid(self,x):return self.out(self.call('Engine.KismetSystemLibrary.IsValid',Object=x))
 def spawn(self,cls,location,rotation=None,owner=None):
  t=self.math('MakeTransform',Location=location,**({'Rotation':rotation} if rotation is not None else {}))
  kw=dict(ActorClass=cls,SpawnTransform=t,CollisionHandlingOverride='AlwaysSpawn')
  if owner is not None:kw['Owner']=owner
  n=self.do(self.call('Engine.GameplayStatics.BeginDeferredActorSpawnFromClass',**kw))
  return self.out(self.do(self.call('Engine.GameplayStatics.FinishSpawningActor',Actor=self.out(n),SpawnTransform=t)))
 def cmset(self,n,v):
  a=self.e.add_set_member_variable_node(n,'/Script/Engine.CharacterMovementComponent');val(a.find_self_pin(),self.get('CharacterMovement'));val(pin(a,n),v);return self.do(a)
 def print(self,s,color='(R=0.1,G=0.8,B=1,A=1)',duration=1.5):return self.do(self.call('Engine.KismetSystemLibrary.PrintString',InString=s,bPrintToScreen=True,bPrintToLog=False,TextColor=color,Duration=duration))
def hook(bp,source,fn,tag):
 e=G.get_graph_editor_by_name(bp,'EventGraph');old=list(source.list_connected_pins());source.break_pin_links()
 options=[str(m) for m in e.list_available_nodes([]) if str(m).split('|')[-1] in ('Sequence','Последовательность')];assert len(options)==1
 seq=e.create_node_from_name(options[0],unreal.Vector2D(x=1200,y=8500),[]);link(source,seq.find_execute_pin())
 for p in old:link(pin(seq,'then_0',True),p)
 n=e.add_call_function_node(B.generated_class(bp).get_path_name()+'.'+fn);n.rename(tag);link(pin(seq,'then_1',True),n.find_execute_pin());return n
