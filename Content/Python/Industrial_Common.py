import unreal,os,shutil
A=unreal.EditorAssetLibrary;B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor;M=unreal.MaterialEditingLibrary
ROOT='/Game/LabTutorial/Industrial'
def V(p):return unreal.Vector(*map(float,p))
def xyz(p):return (p.x,p.y,p.z)
def pin(n,k,out=False):
 p=n.find_output_pin(k) if out else n.find_input_pin(k)
 if not p.is_valid():raise RuntimeError('Missing pin '+n.get_name()+'.'+k)
 return p
def val(p,v):
 if hasattr(v,'try_create_connection'):
  if not v.try_create_connection(p):raise RuntimeError('Connection failed '+str(p.get_pin_name()))
 elif not p.set_pin_value(str(v).lower() if isinstance(v,bool) else str(v)):raise RuntimeError('Default rejected '+str(p.get_pin_name())+'='+str(v))
def link(a,b):val(b,a)
def compile_bp(bp):
 if not B.compile_blueprint(bp):raise RuntimeError('Compile failed '+bp.get_name())
 for gn in B.list_graph_names(bp):
  if G.get_graph_editor_by_name(bp,gn).list_nodes_with_errors():raise RuntimeError('Graph compiler error '+bp.get_name())
def save(a):
 if not A.save_loaded_asset(a,only_if_is_dirty=False):raise RuntimeError('Save failed '+a.get_path_name())
def bp_asset(name,parent=unreal.Actor):
 p=ROOT+'/'+name
 if A.does_asset_exist(p):return A.load_asset(p)
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',parent)
 return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
def components(bp):
 sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
 return [(h,lib.get_object_for_blueprint(lib.get_data(h),bp),str(lib.get_variable_name(lib.get_data(h)))) for h in sub.k2_gather_subobject_data_for_blueprint(bp)]
def add(bp,cls,name,parent=None):
 cs=components(bp)
 for h,c,n in cs:
  if n==name:return c
 sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
 ph=next((h for h,c,n in cs if n==parent),cs[0][0])
 h,reason=sub.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=ph,new_class=cls,blueprint_context=bp))
 c=lib.get_object_for_blueprint(lib.get_data(h),bp)
 if not c:raise RuntimeError(str(reason))
 sub.rename_subobject(h,unreal.Text(name));return c
class Graph:
 def __init__(self,bp):self.bp=bp;self.e=G.get_graph_editor_by_name(bp,'EventGraph');self.cursor=None;self.i=0
 def node(self,n):
  if not n:raise RuntimeError('Cannot create graph node')
  n.set_node_pos(unreal.IntPoint(x=(self.i%8)*280,y=(self.i//8)*310));self.i+=1;return n
 def call(self,path,target=None,**kw):
  n=self.node(self.e.add_call_function_node('/Script/'+path))
  if target is not None:val(n.find_self_pin(),target)
  for k,v in kw.items():
   if hasattr(v,'try_create_connection'):val(pin(n,k),v)
  for k,v in kw.items():
   if not hasattr(v,'try_create_connection'):val(pin(n,k),v)
  return n
 def get(self,n):return pin(self.node(self.e.add_get_member_variable_node(n)),n,True)
 def out(self,n,k='ReturnValue'):return pin(n,k,True)
 def do(self,n):link(self.cursor,n.find_execute_pin());self.cursor=n.find_then_pin();return n
 def set(self,k,v):
  n=self.node(self.e.add_set_member_variable_node(k));val(pin(n,k),v);return self.do(n)
 def math(self,n,**kw):return self.out(self.call('Engine.KismetMathLibrary.'+n,**kw))
 def branch(self,condition):
  n=self.node(self.e.add_branch_node());val(pin(n,'Condition'),condition);self.do(n);return n
 def event(self,n):
  q=self.e.find_event_node(n)
  if not q:raise RuntimeError('Missing event '+n)
  self.cursor=pin(q,'then',True);return q
def spawn(name,asset,p,rot=None,collision=False):
 a=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor,V(p),rot or unreal.Rotator())
 a.set_actor_label(name);a.set_folder_path('LAB/07_Industrial')
 c=a.static_mesh_component;c.set_static_mesh(asset);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
 c.set_mobility(unreal.ComponentMobility.STATIC);return a
