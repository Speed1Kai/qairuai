"""Repair the video UI's sampler mismatch found in the native compiler log.

UE 5.8 uses MediaTexture NewStyleOutput/Texture2D here, which requires Color.
External samples fail SM6 compilation and render the default black UI material.
"""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,compile_bp,save
ROOT='/Game/Cinematics/Prologue'
report={'saved':False,'gameplay_tested':False}
try:
 backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups','ProloguePicture',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
 os.makedirs(backup,exist_ok=True);report['backup']=os.path.abspath(backup)
 for name in ['MT_Prologue','M_PrologueScreen','WBP_Prologue']:
  shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'Cinematics/Prologue',name+'.uasset'),backup)
 texture=A.load_asset(ROOT+'/MT_Prologue');media=A.load_asset(ROOT+'/MP_Prologue')
 texture.set_media_player(media);texture.set_editor_property('new_style_output',True)
 save(texture)
 mat=A.load_asset(ROOT+'/M_PrologueScreen')
 M.delete_all_material_expressions(mat)
 mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI)
 mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
 tex=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample)
 tex.set_editor_property('texture',texture)
 tex.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
 if not M.connect_material_property(tex,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Media color connection rejected')
 M.recompile_material(mat);save(mat)
 widget=A.load_asset(ROOT+'/WBP_Prologue');tree=unreal.find_object(widget,'WidgetTree')
 image=unreal.find_object(tree,'MovieImage');image.set_brush_from_material(mat)
 compile_bp(widget);save(widget)
 report.update(saved=True,new_style_output=bool(texture.get_editor_property('new_style_output')),sampler=str(tex.get_editor_property('sampler_type')),material=mat.get_path_name())
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(os.path.join(unreal.Paths.project_saved_dir(),'prologue_picture_repair.json'),'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Picture repair incomplete')
