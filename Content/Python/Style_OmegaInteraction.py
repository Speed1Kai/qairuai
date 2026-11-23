"""Reskin existing OMEGA prompts without changing interaction rules or texts.
Native UMG + procedural UI material; no runtime Python or external dependencies.
"""
import unreal,os,sys,datetime,json,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,compile_bp,save
import Archive_AuthoringHelpers as H
root=os.path.abspath(unreal.Paths.project_dir());report={'saved':False,'widgets':[],'gameplay_tested':False}
try:
 backup=os.path.join(root,'Saved/Backups/OmegaInteraction',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 paths=['/Game/LabTutorial/UI/WBP_InteractionHint','/Game/LabTutorial/Elevator/WBP_ElevatorPrompt'];mp='/Game/LabTutorial/UI/M_OmegaInteraction'
 for path in paths+[mp]:
  src=os.path.join(root,'Content',path.removeprefix('/Game/')+'.uasset')
  if os.path.isfile(src):
   dst=os.path.join(backup,path.removeprefix('/Game/')+'.uasset');os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
 mat=A.load_asset(mp) if A.does_asset_exist(mp) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_OmegaInteraction','/Game/LabTutorial/UI',unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
 custom=M.create_material_expression(mat,unreal.MaterialExpressionCustom,100,0);inputs=[]
 for name in ('UV','T'):
  ci=unreal.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
 custom.set_editor_property('inputs',inputs);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4);custom.set_editor_property('code',open(os.path.join(root,'SourceAssets/OmegaUI/OmegaInteraction.hlsl'),encoding='utf-8-sig').read())
 for cls,name in ((unreal.MaterialExpressionTextureCoordinate,'UV'),(unreal.MaterialExpressionTime,'T')):
  node=M.create_material_expression(mat,cls,-300,0 if name=='UV' else 150);assert M.connect_material_expressions(node,'',custom,name)
 for alpha,prop in ((False,unreal.MaterialProperty.MP_EMISSIVE_COLOR),(True,unreal.MaterialProperty.MP_OPACITY)):
  mask=M.create_material_expression(mat,unreal.MaterialExpressionComponentMask,400,200 if alpha else 0)
  for ch in ('r','g','b','a'):mask.set_editor_property(ch,(ch=='a') if alpha else ch!='a')
  assert M.connect_material_expressions(custom,'',mask,'');assert M.connect_material_property(mask,'',prop)
 M.recompile_material(mat);save(mat)
 for path in paths:
  bp=A.load_asset(path)
  if not bp:continue
  tree=unreal.find_object(bp,'WidgetTree')
  def w(cls,name):return unreal.find_object(tree,name) or unreal.new_object(cls,outer=tree,name=name)
  canvas=w(unreal.CanvasPanel,'CyberCanvas');canvas.clear_children();H.assign_object(tree,'RootWidget',canvas);canvas.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
  panel=w(unreal.CanvasPanel,'OmegaGlassLayout');panel.clear_children();sl=canvas.add_child_to_canvas(panel);sl.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,1),maximum=unreal.Vector2D(.5,1)));sl.set_alignment(unreal.Vector2D(.5,1));sl.set_position(unreal.Vector2D(0,-112));sl.set_size(unreal.Vector2D(820,164))
  def place(obj,x,y,width,height):
   obj.remove_from_parent();s=panel.add_child_to_canvas(obj);s.set_position(unreal.Vector2D(x,y));s.set_size(unreal.Vector2D(width,height));return obj
  bg=place(w(unreal.Image,'OmegaHologlass'),0,0,820,164);bg.set_brush_from_material(mat);bg.set_color_and_opacity(unreal.LinearColor(1,1,1,1))
  def text(name,label,x,y,width,height,size,color,bold=False):
   t=place(w(unreal.TextBlock,name),x,y,width,height);t.set_text(unreal.Text(label));t.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
   f=t.get_editor_property('font');f.set_editor_property('font_object',A.load_asset('/Engine/EngineFonts/Roboto'));f.set_editor_property('size',size);f.set_editor_property('typeface_font_name','Bold' if bold else 'Regular');t.set_font(f);t.set_auto_wrap_text(True);t.set_editor_property('wrap_text_at',float(width));t.set_shadow_color_and_opacity(unreal.LinearColor(0,.01,.02,.8));t.set_shadow_offset(unreal.Vector2D(0,1));return t
  text('SubsystemLabel','OMEGA / НЕЙРОИНТЕРФЕЙС',200,31,450,23,12,(.64,.85,.86,.9))
  heading=text('Heading','ВЗАИМОДЕЙСТВИЕ',200,56,450,36,22,(.33,.93,1,1))
  body=text('MessageBody','[F]  ГОЛОГРАММА',200,95,450,54,19,(.90,.97,1,1))
  text('OmegaSystemLabel','SYSTEM READY',32,22,132,15,7,(.37,.84,.86,.9))
  text('OmegaNeuralLabel','NEURAL LINK / 01',34,134,132,14,6,(.27,.68,.72,.8))
  text('OmegaSignalLabel','LOCAL / SYNC',665,21,130,12,6,(.40,.79,.81,.65))
  # Preserve these variables: existing Blueprint graphs supply each device's
  # actual title, key and action, and already animate the card in and out.
  for obj in (heading,body):unreal.get_default_object(B.generated_class(H.helper)).call_method('AssignFlag',args=(obj,unreal.Name('bIsVariable'),True))
  if 'RefreshWidgetVariableTracking' in map(str,B.list_graph_names(H.helper)):unreal.get_default_object(B.generated_class(H.helper)).call_method('RefreshWidgetVariableTracking',args=(bp,{}))
  compile_bp(bp);save(bp);report['widgets'].append(path)
 save(H.helper);report.update(saved=True,backup=backup,material=mp,logical_size=[820,164],preserved_dynamic_text=True)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:open(os.path.join(root,'Saved/omega_interaction_style.json'),'w',encoding='utf8').write(json.dumps(report,ensure_ascii=False,indent=2))
if not report['saved']:raise RuntimeError('OMEGA style incomplete')

