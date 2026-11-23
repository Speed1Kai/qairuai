import unreal,sys,os
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
mat=A.load_asset(ROOT+'/M_DoorHazard')
pos=next(o for o in unreal.ObjectIterator(unreal.MaterialExpressionWorldPosition) if o.get_outer()==mat)
local=next(o for o in unreal.ObjectIterator(unreal.MaterialExpressionTransformPosition) if o.get_outer()==mat)
inputs=M.get_material_expression_input_names(local)
unreal.log('DOOR MATERIAL TRANSFORM INPUTS '+str(inputs))
if not M.connect_material_expressions(pos,'',local,inputs[0]):raise RuntimeError('Cannot wire material coordinates')
M.recompile_material(mat);save(mat)
for name,rgb in [('M_DoorStatus_Red',(1.,.012,.004)),('M_DoorStatus_Green',(.025,1.,.075))]:
 signal=A.load_asset(ROOT+'/'+name)
 vector=next(o for o in unreal.ObjectIterator(unreal.MaterialExpressionVectorParameter) if o.get_outer()==signal)
 vector.set_editor_property('default_value',unreal.LinearColor(r=rgb[0]*80,g=rgb[1]*80,b=rgb[2]*80,a=1))
 M.recompile_material(signal);save(signal)
bp=A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor');compile_bp(bp);g=Graph(bp)
timeline=next(n for n in g.e.list_all_nodes() if n.get_class().get_name()=='K2Node_Timeline')
# Reopening the asset reconstructed the real native Float Track output pin.
for node in list(g.e.list_all_nodes()):
 if node.find_input_pin('InTime').is_valid():
  result=node.find_result_pin()
  if result.is_valid():
   links=list(result.list_connected_pins());result.break_pin_links()
   for target in links:link(pin(timeline,'Alpha',True),target)
   g.e.remove_nodes([node])
for h,c,name in components(bp):
 if 'PistonRod' in name:
  p=c.get_editor_property('relative_location');p.y=260 if name.startswith('Right') else -260;c.set_editor_property('relative_location',p)
for node in g.e.list_all_nodes():
 # Move the retracting upper rod guides towards the outer jambs.
 for key in ('A','B'):
  p=node.find_input_pin(key)
  if not p.is_valid() or p.list_connected_pins():continue
  value=p.get_pin_value()
  if str(node.get_node_title()).lower().find('lerp')<0:continue
  try:number=float(value)
  except ValueError:continue
  replacements={161.:260.,-161.:-260.,249.:347.,-249.:-347.}
  if number in replacements:val(p,replacements[number])
compile_bp(bp);save(bp)
unreal.log('SPLIT DOOR POLISH SAVED')
