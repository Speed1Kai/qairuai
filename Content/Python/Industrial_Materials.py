from Industrial_Common import *

def make_material(name,kind='metal',base=(.055,.075,.072),metal=.7,rough=.65):
 path=ROOT+'/'+name
 m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m)
 def node(cls,**kw):
  n=M.create_material_expression(m,cls)
  for k,v in kw.items():n.set_editor_property(k,v)
  return n
 def constant(v):return node(unreal.MaterialExpressionConstant,r=v)
 def rgb(v):return node(unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(r=v[0],g=v[1],b=v[2],a=1))
 if kind in ('glow','crt','red','amber'):
  m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
  time=node(unreal.MaterialExpressionTime);p=node(unreal.MaterialExpressionWorldPosition)
  q=node(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3)
  inputs=[]
  for k in ('P','T'):
   x=unreal.CustomInput();x.set_editor_property('input_name',k);inputs.append(x)
  q.set_editor_property('inputs',inputs)
  scan='(.7+.3*step(.24,frac(P.z*.16)))' if kind=='crt' else '1.0'
  q.set_editor_property('code','float flicker=.94+.04*sin(T*7.1)+.02*sin(T*29.0); return float3(%s,%s,%s)*flicker*%s;'%(*base,scan))
  M.connect_material_expressions(p,'',q,'P');M.connect_material_expressions(time,'',q,'T');M.connect_material_property(q,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 else:
  m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
  pos=node(unreal.MaterialExpressionWorldPosition)
  q=node(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
  inp=unreal.CustomInput();inp.set_editor_property('input_name','P');q.set_editor_property('inputs',[inp])
  code='''struct Weather {
 float h(float3 p) { return frac(sin(dot(p,float3(127.1,311.7,74.7)))*43758.5453); }
 float n(float3 p) { float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
 return lerp(lerp(lerp(h(i),h(i+float3(1,0,0)),f.x),lerp(h(i+float3(0,1,0)),h(i+float3(1,1,0)),f.x),f.y),lerp(lerp(h(i+float3(0,0,1)),h(i+float3(1,0,1)),f.x),lerp(h(i+float3(0,1,1)),h(i+float3(1,1,1)),f.x),f.y),f.z); }
}; Weather w;
float patch=w.n(P*.025); float grain=w.n(P*.23);
float rust=smoothstep(.57,.79,patch+.10*grain);
float leak=smoothstep(.57,.8,w.n(float3(P.xy*.045,P.z*.003)));
float scratch=smoothstep(.96,.999,w.n(P*float3(.03,2.1,.04)))*.2;
float3 base=float3(BASE);
float3 color=lerp(base*.88,base*1.12,grain);
color=lerp(color,float3(.17,.052,.018),rust*RUST);
color*=1-leak*.44; color+=scratch*SCRATCH;
return float4(color,saturate(ROUGH+rust*.22+leak*.08+grain*.12));'''
  code=code.replace('BASE',','.join(map(str,base))).replace('RUST','0.0' if kind in ('concrete','rubber','keys') else '.7').replace('SCRATCH','.03' if kind=='concrete' else '.25').replace('ROUGH',str(rough))
  if kind=='hazard':code=code.replace('float3 base=float3('+','.join(map(str,base))+');','float3 base=lerp(float3(.012,.014,.012),float3(.5,.28,.025),step(.5,frac((P.y+P.z)*.025)));')
  q.set_editor_property('code',code);M.connect_material_expressions(pos,'',q,'P')
  c=node(unreal.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);a=node(unreal.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
  for n in (c,a):
   if not M.connect_material_expressions(q,'',n,''):raise RuntimeError('Cannot connect weathering channel '+name)
  M.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR);M.connect_material_property(a,'',unreal.MaterialProperty.MP_ROUGHNESS)
  M.connect_material_property(constant(metal),'',unreal.MaterialProperty.MP_METALLIC)
  if kind not in ('rubber','keys'):
   # Derivative bump from the same weathering signal: no normal texture, extra
   # noise evaluation, or per-object render target is allocated.
   normal=node(unreal.MaterialExpressionVertexNormalWS)
   bump=node(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3)
   inputs=[]
   for k in ('P','N','H'):
    inp=unreal.CustomInput();inp.set_editor_property('input_name',k);inputs.append(inp)
   bump.set_editor_property('inputs',inputs)
   bump.set_editor_property('code','float3 n=normalize(N); float3 dx=ddx(P),dy=ddy(P); float3 r1=cross(dy,n),r2=cross(n,dx); float det=dot(dx,r1); float3 grad=sign(det)*(ddx(H)*r1+ddy(H)*r2); return normalize(abs(det)*n-grad*1.8);')
   for source,k in ((pos,'P'),(normal,'N'),(a,'H')):
    if not M.connect_material_expressions(source,'',bump,k):raise RuntimeError('Cannot connect surface relief '+name)
   m.set_editor_property('tangent_space_normal',False);M.connect_material_property(bump,'',unreal.MaterialProperty.MP_NORMAL)
 M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 M.recompile_material(m);save(m);return m

def steam_material():
 name='M_PressureSteam';path=ROOT+'/'+name
 m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
 M.delete_all_material_expressions(m);m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('two_sided',True)
 m.set_editor_property('usage',unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES) if False else None
 M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
 uv=M.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate)
 q=M.create_material_expression(m,unreal.MaterialExpressionCustom);q.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
 ci=unreal.CustomInput();ci.set_editor_property('input_name','UV');q.set_editor_property('inputs',[ci]);q.set_editor_property('code','float2 p=(UV-.5)*2; return pow(saturate(1-dot(p,p)),2)*.15;')
 M.connect_material_expressions(uv,'',q,'UV')
 pc=M.create_material_expression(m,unreal.MaterialExpressionParticleColor)
 mul=M.create_material_expression(m,unreal.MaterialExpressionMultiply);M.connect_material_expressions(q,'',mul,'A');M.connect_material_expressions(pc,'A',mul,'B')
 M.connect_material_property(mul,'',unreal.MaterialProperty.MP_OPACITY)
 col=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);col.set_editor_property('constant',unreal.LinearColor(r=.22,g=.27,b=.29,a=1))
 M.connect_material_property(col,'',unreal.MaterialProperty.MP_BASE_COLOR)
 M.recompile_material(m);save(m);return m

def build_materials():
 specs=[('M_DistressedMetal','metal',(.075,.095,.09),.72,.56),('M_Concrete_Dirty','concrete',(.20,.22,.20),0,.83),('M_RustyIron','metal',(.17,.058,.025),.35,.77),('M_Rubber','rubber',(.008,.012,.013),.05,.77),('M_Chrome','metal',(.27,.3,.29),.91,.3),('M_Keys','keys',(.32,.3,.23),.1,.58),('M_HazardStripes','hazard',(.5,.3,.02),.4,.65),('M_CRTGlass','crt',(.025,2.4,2.8),0,.5),('M_CyanIndicator','glow',(.04,3.1,3.5),0,.5),('M_RedIndicator','red',(1.3,.012,.004),0,.5),('M_AmberIndicator','amber',(1.4,.38,.015),0,.5)]
 mats={n:make_material(n,k,b,me,r) for n,k,b,me,r in specs};mats['M_PressureSteam']=steam_material();return mats
