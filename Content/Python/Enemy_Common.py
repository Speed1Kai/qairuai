import unreal,os,json,sys
from Industrial_Common import Graph as BaseGraph,V,xyz,pin,val,link,compile_bp,save,components,add
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
ROOT='/Game/Enemies/Architect'
def cls(path):return unreal.load_class(None,path)
def obj(path):return unreal.load_object(None,path)
def asset(name,parent=unreal.Actor):
 path=ROOT+'/'+name
 if A.does_asset_exist(path):return A.load_asset(path)
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent)
 return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
def data(name,type,factory):
 return A.load_asset(ROOT+'/'+name) if A.does_asset_exist(ROOT+'/'+name) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,type,factory)
def var(bp,name,kind,default):
 if name not in map(str,B.list_member_variable_names(bp)):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable(name,B.get_basic_type_by_name(kind),str(default))
def graph(bp):
 g=Graph(bp);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event']);return Graph(bp)
class Graph(BaseGraph):
 def call(self,path,target=None,**kw):
  if 'KeyName' in kw and isinstance(kw['KeyName'],str):
   kw['KeyName']=self.out(super().call('Engine.KismetSystemLibrary.MakeLiteralName',Value=kw['KeyName']))
  return super().call(path,target=target,**kw)
 def do(self,n):
  return super().do(n) if n.find_execute_pin().is_valid() else n
 def override(self,name):
  node=self.e.find_event_node(name)
  if not node:node=B.add_event_override(self.bp,name,unreal.IntPoint(x=0,y=self.i*100))
  self.cursor=pin(node,'then',True);return node
 def bb(self,controller=None):return self.out(self.call('AIModule.AIBlueprintHelperLibrary.GetBlackboard',**({'Target':controller} if controller is not None else {})))
 def bbget(self,bb,key,type='Object'):
  if type=='Object' and key=='TargetActor':return self.out(self.call('AIModule.BTFunctionLibrary.GetBlackboardValueAsActor',Key=self.get('TargetKey')))
  return self.out(self.call('AIModule.BlackboardComponent.GetValueAs'+type,target=bb,KeyName=key))
 def bbset(self,bb,key,value,type='Object'):return self.do(self.call('AIModule.BlackboardComponent.SetValueAs'+type,target=bb,KeyName=key,**{('ObjectValue' if type=='Object' else 'VectorValue' if type=='Vector' else 'BoolValue' if type=='Bool' else 'EnumValue' if type=='Enum' else 'FloatValue'):value}))
 def speed(self,pawn,value):
  move=self.call('Engine.Pawn.GetMovementComponent',target=pawn);self.do(move)
  self.do(self.call('Engine.KismetSystemLibrary.SetDoublePropertyByName',Object=self.out(move),PropertyName='MaxWalkSpeed',Value=value))
 def finish(self,success=True):return self.do(self.call('AIModule.BTTask_BlueprintBase.FinishExecute',bSuccess=success))
 def external(self,name,path,target):
  node=self.node(self.e.add_get_member_variable_node(name,path));val(node.find_self_pin(),target);return pin(node,name,True)
def task(name):
 bp=asset(name,unreal.BTTask_BlueprintBase);target_key(bp);compile_bp(bp);g=graph(bp);event=g.override('ReceiveExecuteAI');return bp,g,pin(event,'OwnerController',True),pin(event,'ControlledPawn',True)
def target_key(bp):
 if 'TargetKey' not in map(str,B.list_member_variable_names(bp)):G.get_graph_editor_by_name(bp,'EventGraph').add_member_variable('TargetKey',B.get_struct_type(unreal.BlackboardKeySelector.static_struct()),'(SelectedKeyName="TargetActor")')
