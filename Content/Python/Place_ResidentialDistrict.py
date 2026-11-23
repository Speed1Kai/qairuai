"""Shared PBR materials and ten residential exteriors beyond the lab campus."""
import unreal,os,sys,json,math,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,V,components,compile_bp,save
ROOT='/Game/Environment/Residential';MAIN='/Game/Lvl_LabTutorial';LEVEL='/Game/Surface/Lvl_SurfaceArrival'
project=os.path.abspath(unreal.Paths.project_dir());out=os.path.join(project,'Saved','residential_district.json')
report={'saved':False,'placements':[],'removed_blockout':[],'gameplay_tested':False}
tools=unreal.AssetToolsHelpers.get_asset_tools();actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
def material(name):
 path=ROOT+'/Materials/'+name
 m=A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(name,ROOT+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m);return m
def node(m,cls,**props):
 n=M.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def connect(a,b,pin):M.connect_material_expressions(a,'',b,pin)
def prop(m,a,p):M.connect_material_property(a,'',p)
def number(m,x):return node(m,unreal.MaterialExpressionConstant,r=x)
def texture(m,name,uv=None,normal=False):
 n=node(m,unreal.MaterialExpressionTextureSample,texture=A.load_asset(ROOT+'/Textures/'+name),sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if name=='T_Facade_Color' else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
 if uv:connect(uv,n,'Coordinates')
 return n
try:
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Current level save failed')
 backup=os.path.join(project,'Saved','Backups','ResidentialDistrict',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);report['backup']=backup
 for rel in ['Content/Surface/Lvl_SurfaceArrival.umap','Content/Surface/BP_SurfaceEnvironment.uasset']:
  shutil.copy2(os.path.join(project,rel),os.path.join(backup,os.path.basename(rel)))
 m=material('M_ResidentialFacade')
 uv=node(m,unreal.MaterialExpressionTextureCoordinate,u_tiling=5.,v_tiling=5.)
 color=texture(m,'T_Facade_Color',uv);ao=texture(m,'T_Building_AO')
 tint=node(m,unreal.MaterialExpressionVectorParameter,parameter_name='FacadeTint',default_value=unreal.LinearColor(.55,.61,.64,1))
 multiply=node(m,unreal.MaterialExpressionMultiply);connect(color,multiply,'A');connect(tint,multiply,'B')
 shade=node(m,unreal.MaterialExpressionLinearInterpolate,const_a=.4,const_b=1.)
 M.connect_material_expressions(ao,'R',shade,'Alpha')
 final=node(m,unreal.MaterialExpressionMultiply);connect(multiply,final,'A');connect(shade,final,'B');prop(m,final,unreal.MaterialProperty.MP_BASE_COLOR)
 prop(m,ao,unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
 prop(m,texture(m,'T_Facade_Normal',uv,True),unreal.MaterialProperty.MP_NORMAL)
 prop(m,number(m,.86),unreal.MaterialProperty.MP_ROUGHNESS);prop(m,number(m,0),unreal.MaterialProperty.MP_METALLIC)
 spec=node(m,unreal.MaterialExpressionMultiply,const_b=.25);M.connect_material_expressions(texture(m,'T_Facade_Specular',uv),'R',spec,'A');prop(m,spec,unreal.MaterialProperty.MP_SPECULAR)
 M.recompile_material(m);save(m)
 glass=material('M_ResidentialDeadGlass')
 prop(glass,node(glass,unreal.MaterialExpressionVectorParameter,parameter_name='GlassTint',default_value=unreal.LinearColor(.028,.052,.065,1)),unreal.MaterialProperty.MP_BASE_COLOR)
 for value,p in [(.24,unreal.MaterialProperty.MP_ROUGHNESS),(.3,unreal.MaterialProperty.MP_METALLIC),(.65,unreal.MaterialProperty.MP_SPECULAR)]:prop(glass,number(glass,value),p)
 M.recompile_material(glass);save(glass)
 inventory=json.load(open(os.path.join(project,'Saved','residential_import.json'),encoding='utf8'))
 sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
 for row in inventory['meshes']:
  mesh=A.load_asset(row['path'])
  for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,glass if 'glas' in str(slot.material_slot_name).lower() else m)
  sms.remove_collisions(mesh);sms.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)
  save(mesh)
 unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
 env=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='SURF_Environment')
 bp=A.load_asset('/Game/Surface/BP_SurfaceEnvironment')
 previous=json.load(open(out,encoding='utf8')) if os.path.exists(out) else {}
 plots=[]
 for h,c,n in components(bp):
  if not c or not isinstance(c,unreal.InstancedStaticMeshComponent) or not c.static_mesh or not c.static_mesh.get_name().startswith('SM_Ruin_'):continue
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,False);p=t.translation
   if abs(p.x)<4500 and 2000<p.y<22000 and abs(p.y-9300)>100:
    plots.append({'component':n,'position':[p.x,p.y,p.z]})
 # Subobject data can expose both inherited and native handles for one template.
 plots=list({tuple(round(v,2) for v in q['position']):q for q in plots}.values())
 if not plots:plots=previous.get('removed_blockout',[])
 if len(plots)!=10:raise RuntimeError('Expected ten replacement plots, found '+str(len(plots)))
 report['removed_blockout']=plots
 def clear_plots(cs):
  for c in cs:
   if not c or not isinstance(c,unreal.InstancedStaticMeshComponent) or not c.static_mesh:continue
   if not (c.static_mesh.get_name().startswith('SM_Ruin_') or c.get_name().startswith('Boxes_M_Charcoal_Block')):continue
   for i in reversed(range(c.get_instance_count())):
    p=c.get_instance_transform(i,False).translation
    if any(abs(p.x-q['position'][0])<5 and abs(p.y-q['position'][1])<5 for q in plots):c.remove_instance(i)
 clear_plots([c for h,c,n in components(bp)]);compile_bp(bp);save(bp)
 env=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='SURF_Environment')
 clear_plots(env.get_components_by_class(unreal.InstancedStaticMeshComponent))
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith('CITY_Residential_'):actors.destroy_actor(a)
 ordered=sorted(plots,key=lambda q:(q['position'][1],q['position'][0]))
 for row,plot in zip(inventory['meshes'],ordered):
  mesh=A.load_asset(row['path']);x,y,z=plot['position'];yaw=90 if x<0 else -90
  ox,oy,oz=row['origin'];ex,ey,ez=row['extent'];r=math.radians(yaw)
  position=(x-ox*math.cos(r)+oy*math.sin(r),y+26000-ox*math.sin(r)-oy*math.cos(r),ez-oz)
  a=actors.spawn_actor_from_class(unreal.StaticMeshActor,V(position),unreal.Rotator(yaw=yaw))
  a.set_actor_label('CITY_Residential_%03d'%row['index']);a.set_folder_path('SURFACE/Residential District')
  c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll');c.set_editor_property('can_ever_affect_navigation',False)
  report['placements'].append({'label':a.get_actor_label(),'mesh':mesh.get_path_name(),'position':position,'yaw':yaw,'height_m':2*ez/100})
 report['saved']=bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
 if not report['saved']:raise RuntimeError('Surface level save failed')
 editor.set_level_viewport_camera_info(V((0,28300,210)),unreal.Rotator(pitch=12,yaw=90))
 unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
 with open(out,'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
