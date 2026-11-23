"""Repair the player's PBR shader and persist skeletal mesh usage."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,components,save
root='/Game/Characters/BlackSentinel';p=os.path.abspath(unreal.Paths.project_dir());r={'saved':False}
try:
 mat=A.load_asset(root+'/M_BlackSentinel')
 if not mat:raise RuntimeError('Player material is missing')
 r['skeletal_usage_before']=mat.get_editor_property('used_with_skeletal_mesh')
 r['textures']={}
 for role in ('Color','Normal','Metal','Roughness'):
  tex=A.load_asset(root+'/T_Sentinel_'+role)
  if not isinstance(tex,unreal.Texture2D):raise RuntimeError('Missing texture: '+role)
  r['textures'][role]=tex.get_path_name()
 backup=os.path.join(p,'Saved/Backups/SentinelMaterial',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
 shutil.copy2(os.path.join(p,'Content/Characters/BlackSentinel/M_BlackSentinel.uasset'),os.path.join(backup,'M_BlackSentinel.uasset'));r['backup']=backup
 M.delete_all_material_expressions(mat)
 for i,(role,prop) in enumerate([('Color',unreal.MaterialProperty.MP_BASE_COLOR),('Normal',unreal.MaterialProperty.MP_NORMAL),('Metal',unreal.MaterialProperty.MP_METALLIC),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]):
  sample=M.create_material_expression(mat,unreal.MaterialExpressionTextureSample,-400,i*220)
  sample.set_editor_property('texture',A.load_asset(r['textures'][role]))
  sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='Color' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
  if not M.connect_material_property(sample,'RGB' if role in ('Color','Normal') else 'R',prop):raise RuntimeError('Shader connection rejected: '+role)
 mat.set_editor_property('used_with_skeletal_mesh',True)
 mat.set_editor_property('used_with_morph_targets',True)
 M.recompile_material(mat);save(mat)
 r['skeletal_usage_after']=mat.get_editor_property('used_with_skeletal_mesh')
 mesh=A.load_asset(root+'/SK_BlackSentinel');r['mesh_materials']=[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.materials]
 bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
 r['player_components']=[{'name':n,'mesh':c.get_skinned_asset().get_path_name() if c.get_skinned_asset() else None,'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]} for h,c,n in components(bp) if isinstance(c,unreal.SkeletalMeshComponent)]
 r['saved']=True
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(p,'Saved/sentinel_material_fix.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
