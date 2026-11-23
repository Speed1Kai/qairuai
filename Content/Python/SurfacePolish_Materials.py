"""Build world-scaled, scan-based surfaces for the outdoor map."""
import unreal

from Build_RiverForest import constant, custom, expr, output, persist
from Build_RuinedUrbanCampus import A, content, save, tools

ROOT = '/Game/Environment/SurfacePolish'
SCANS = content.parent/'SourceAssets/PolyHaven'
M = unreal.MaterialEditingLibrary
DX = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
MASKS = unreal.MaterialSamplerType.SAMPLERTYPE_MASKS


def import_file(source, root=ROOT, options=None):
    path=root+'/'+source.stem
    if A.does_asset_exist(path):
        return A.load_asset(path)
    task=unreal.AssetImportTask()
    for key,value in dict(filename=str(source),destination_path=root,automated=True,
                          save=False,options=options).items():
        task.set_editor_property(key,value)
    tools.import_asset_tasks([task])
    result=A.load_asset(path)
    assert result,source
    return result


def textures(slug):
    result={}
    for role in ('diff','nor_dx','rough'):
        texture=import_file(SCANS/slug/f'{slug}_{role}_1k.jpg')
        texture.set_editor_property('srgb',role=='diff')
        texture.set_editor_property('max_texture_size',1024)
        if role!='diff':
            texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP
                                        if role=='nor_dx' else unreal.TextureCompressionSettings.TC_MASKS)
        save(texture)
        result[role]=texture
    return result


def asset_material(name):
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return A.load_asset(path)
    return tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())


def sample(material, texture, sampler=None, coords=None):
    kwargs={'texture':texture}
    if sampler is not None:
        kwargs['sampler_type']=sampler
    node=expr(material,'TextureSample',**kwargs)
    if coords:
        assert M.connect_material_expressions(coords,'',node,'UVs')
    return node


NOISE = """
struct Noise {
 float hash(float2 q){return frac(sin(dot(q,float2(127.1,311.7)))*43758.5453);}
 float value(float2 q){float2 i=floor(q), f=frac(q); f=f*f*(3-2*f);
 return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
             lerp(hash(i+float2(0,1)),hash(i+float2(1,1)),f.x),f.y);}
}; Noise n;
"""


def ground_material(material, kind, asphalt, forest, concrete):
    M.delete_all_material_expressions(material)
    material.set_editor_property('tangent_space_normal',False)
    p=expr(material,'WorldPosition')
    normal=expr(material,'VertexNormalWS')
    rock=kind=='bank'
    paved=kind=='concrete'
    primary=asphalt if kind=='asphalt' else concrete if paved else forest
    scale=265. if kind=='asphalt' else 370. if paved else 290. if rock else 300.
    uv=custom(material,('float2 side = float2(abs(N.x)>abs(N.y)?P.y:P.x,P.z); '
                        'return lerp(side,P.xy,smoothstep(.40,.72,abs(N.z)))/%.1f;'%scale)
              if rock else 'return P.xy/%.1f;'%scale,
              {'P':p,'N':normal},unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    base=sample(material,primary['diff'],coords=uv)
    bump=sample(material,primary['nor_dx'],DX,uv)
    inputs={'P':p,'N':normal,'C':base}
    normal_inputs={'G':normal,'B':bump}
    blend_bump='float2 Detail=B.xy;'
    formulas={
        'asphalt': 'return lerp(C.rgb,C2.rgb,F)*lerp(.65,1.14,broad)+float3(.020,.016,.011)*grime*.50;',
        'concrete': 'return lerp(C.rgb*float3(.80,.82,.79),float3(.052,.050,.035),grime*.29);',
        'forest': 'return lerp(C.rgb*float3(.75,.81,.64),C.rgb*float3(.48,.70,.38),moss)*(.76+.36*broad);',
        'burned': 'return lerp(C.rgb*float3(.60,.54,.43),float3(.025,.020,.016),grime*.58)*(.74+.36*broad);',
        'bank': 'return lerp(C.rgb*float3(.58,.66,.69),C.rgb*float3(.55,.72,.44),moss*abs(N.z))*(.61+.32*broad);',
        'mixed': '''
float zone=smoothstep(21500,24700,P.y)*(1-smoothstep(97500,103000,P.y))
  *smoothstep(-28000,-24200,P.x)*(1-smoothstep(35100,39300,P.x));
float3 soil=lerp(C.rgb*float3(.72,.76,.63),C.rgb*float3(.54,.70,.40),moss);
return lerp(soil,A.rgb*(.75+.36*broad),zone*(.42+.50*broad));
''',
    }
    if kind=='asphalt':
        alt=custom(material,'''
return float2(P.x*.515+P.y*.857,-P.x*.857+P.y*.515)/313.+float2(.31,.73);
''',{'P':p},unreal.CustomMaterialOutputType.CMOT_FLOAT2)
        factor=custom(material,NOISE+'''
return smoothstep(.32,.67,n.value(P.xy/455.0)*.79+n.value(P.xy/162.0)*.21);
''',{'P':p},unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        inputs.update(C2=sample(material,primary['diff'],coords=alt),F=factor)
        normal_inputs.update(B2=sample(material,primary['nor_dx'],DX,alt),F=factor)
        blend_bump='''
float2 rotated=float2(B2.x*.515-B2.y*.857,B2.x*.857+B2.y*.515);
float2 Detail=lerp(B.xy,rotated,F);
'''
    if kind=='mixed':
        inputs['A']=sample(material,asphalt['diff'],coords=uv)
    shade=custom(material,NOISE+'''
float broad=n.value(P.xy/1260.0)*.69+n.value(P.xy/453.0)*.31;
float grime=smoothstep(.39,.76,n.value(P.xy/695.0)*.68+n.value(P.xy/163.0)*.32);
float moss=smoothstep(.44,.76,n.value(P.xy/521.0)*.73+n.value(P.xy/147.0)*.27);
'''+formulas[kind],inputs)
    output(shade,'BASE_COLOR')
    n=custom(material,blend_bump+'''
float3 Z=normalize(G);
float3 axis=abs(Z.x)<.88?float3(1,0,0):float3(0,1,0);
float3 X=normalize(axis-Z*dot(axis,Z));
float3 Y=normalize(cross(Z,X));
return normalize(Z+X*Detail.x*.62+Y*Detail.y*.62);
''',normal_inputs)
    output(n,'NORMAL')
    if 'rough' in primary:
        rough=sample(material,primary['rough'],MASKS,uv)
        output(custom(material,'return lerp(.62,.96,R.r);',{'R':rough},
                      unreal.CustomMaterialOutputType.CMOT_FLOAT1),'ROUGHNESS')
    else:
        constant(material,'ROUGHNESS',.91)
    constant(material,'SPECULAR',.28)
    return persist(material)


def coast_material(scans):
    material=asset_material('M_CoastRockScan')
    M.delete_all_material_expressions(material)
    output(sample(material,scans['diff']),'BASE_COLOR','RGB')
    output(sample(material,scans['nor_dx'],DX),'NORMAL','RGB')
    output(sample(material,scans['rough'],MASKS),'ROUGHNESS','R')
    return persist(material)


def sets():
    concrete={key:A.load_asset('/Game/CityDowntown/Textures/T_Concrete_'+suffix)
              for key,suffix in (('diff','BC'),('nor_dx','N'))}
    assert all(concrete.values())
    return textures('asphalt_02'),textures('forest_ground_04'),concrete


def prepare():
    A.make_directory(ROOT)
    sources=sets()
    materials={kind:ground_material(asset_material('M_Scan_'+kind.title()),kind,*sources)
               for kind in ('asphalt','forest','mixed','concrete','bank','burned')}
    materials['coast']=coast_material(textures('coast_rocks_03'))
    return materials
