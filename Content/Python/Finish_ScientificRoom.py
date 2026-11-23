"""Match the source's plain white energy tube to the laboratory's cyan palette."""
import unreal,sys,os,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,M,save
path='/Game/Environment/ScientificLab/M_EnergyCyan'
m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_EnergyCyan','/Game/Environment/ScientificLab',unreal.Material,unreal.MaterialFactoryNew())
M.delete_all_material_expressions(m)
for color,prop in [(unreal.LinearColor(.006,.035,.065,1),unreal.MaterialProperty.MP_BASE_COLOR),(unreal.LinearColor(.015,.55,1.2,1),unreal.MaterialProperty.MP_EMISSIVE_COLOR)]:
 n=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);n.constant=color;M.connect_material_property(n,'',prop)
for value,prop in [(.35,unreal.MaterialProperty.MP_METALLIC),(.24,unreal.MaterialProperty.MP_ROUGHNESS)]:
 n=M.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=value;M.connect_material_property(n,'',prop)
m.set_editor_property('used_with_nanite',True);M.recompile_material(m);save(m)
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);count=0
for a in sub.get_all_level_actors():
 if not a.get_actor_label().startswith('SCI_'):continue
 for c in a.get_components_by_class(unreal.StaticMeshComponent):
  for i in range(c.get_num_materials()):
   old=c.get_material(i)
   if old and old.get_name()=='ENARGY':a.modify();c.modify();c.set_material(i,m);count+=1
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.modify()
if not unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Lvl_LabTutorial'):raise RuntimeError('Final room save failed')
p=os.path.join(unreal.Paths.project_saved_dir(),'scientific_start_room_report.json')
r=json.load(open(p,encoding='utf8'));r['cyan_energy_material_assignments']=count;r['saved']=True
with open(p,'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
script=os.path.join(os.path.dirname(__file__),'Capture_ScientificStartRoom.py');exec(compile(open(script,encoding='utf8').read(),script,'exec'),globals())
