"""Game assets and layout for the approved Shelter 07 at the municipal waterworks."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unreal
from Build_RiverForest import connect, constant, custom, expr, output, persist
from Build_RuinedUrbanCampus import local
from CityCombat_Common import A,B,add,compile_bp,components,save
from Install_StoryMemory import Story,bp_asset,load
from SurfacePolish_Materials import NOISE,import_file,sample

PROJECT=Path(unreal.Paths.project_dir()).resolve()
SOURCE=PROJECT/'SourceAssets/Shelter07/Unreal'
ASSETS='/Game/Environment/Shelter07/Waterworks'
SHELTER='/Game/Environment/Shelter07/BP_Shelter07'
ORIGIN=(30464.,88239.,1438.)
HATCH_ORIGIN=(29520.,88820.,2150.)
HATCH=(29520.,88820.,2176.)
SURFACE=(29387.,88757.,2262.)
LOW_LANDING=.848+1.075
ENTRY_YAW=-90
SURFACE_YAW=17

def position(x,y,z):
    return tuple(round(base+100*v,2) for base,v in zip(ORIGIN,(x,y,z)))

ENTRY=position(-8.58,2.42,LOW_LANDING)
EXIT_PANEL=position(-10.29,3.07,1.91)
TRIAGE=position(3.12,4.87,1.08)
BREAKER=position(10.05,-2.92,-.45)
OUTLINES={
    'OutlineShelterLid': (HATCH_ORIGIN, (104,104,46)),
    'OutlineTriageStation': (position(3.08,5.35,1.005),(188,86,13)),
    'OutlineReserveBreaker': (position(10.11,-2.56,-.846),(81,69,140)),
    'OutlineShelterExit': (position(-10.35,3.07,1.91),(10,38,49)),
}
CUBE='/Engine/BasicShapes/Cube'

def floor_maps():
    p=PROJECT/'SourceAssets/CampusWall'
    items={}
    for role in ('Diffuse','Glossiness','Normal'):
        t=import_file(p/('concrete_a_'+role+'.png'),ASSETS+'/Textures')
        t.set_editor_property('max_texture_size',1024)
        t.set_editor_property('srgb',role=='Diffuse')
        if role!='Diffuse':
            t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else unreal.TextureCompressionSettings.TC_MASKS)
        save(t);items[role]=t
    return items

def floor_material(mat):
    maps=floor_maps()
    p=expr(mat,'WorldPosition')
    uv=custom(mat,'''
float2 M=(P.xy-float2(30464.,88239.))/100.0;
float2 Q=(M+float2(.11,.77))/float2(2.65,2.93);
return frac(Q)*.459+.018 + frac(floor(Q)*.5);
''',{'P':p},unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    base=sample(mat,maps['Diffuse'],coords=uv)
    gloss=sample(mat,maps['Glossiness'],unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,uv)
    norm=sample(mat,maps['Normal'],unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,uv)
    humidity=custom(mat,NOISE+'''
float2 M=(P.xy-float2(30464.,88239.))/100.0;
float stains=(1-smoothstep(.29,.57,n.value(M*.62)*.84+n.value(M*16.)*.16))*.49;
float close=length((M-float2(2.56,-1.23))*float2(1.,1.57));
stains=max(stains,(1-smoothstep(.33,.75,close+n.value(M*12)*.20))*.68);
return stains;
''',{'P':p},unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    output(custom(mat,'''
float2 M=(P.xy-float2(30464.,88239.))/100.0;
float2 Cell=frac((M+float2(.11,.77))/float2(2.65,2.93));
float2 edge=min(Cell,1.0-Cell);
float seam=1-smoothstep(.0008,.002,min(edge.x,edge.y));
return lerp(lerp(C*float3(.64,.66,.66),float3(.031,.036,.035),F),float3(.027,.025,.022),seam*.45);
''',{'P':p,'C':base,'F':humidity}),'BASE_COLOR')
    output(custom(mat,'return clamp(.87-G.r*.30-F*.23,.30,.88);',{'G':gloss,'F':humidity},
                  unreal.CustomMaterialOutputType.CMOT_FLOAT1),'ROUGHNESS')
    output(custom(mat,'return normalize(float3(N.xy*.44,max(N.z,.18)));',{'N':norm}),'NORMAL')
    constant(mat,'SPECULAR',.31)

def emission_power(row):
    if 'smoked glass' in row['name']:return .84
    if 'phosphor' in row['name']:return 3.1
    if 'raster' in row['name']:return .74
    return min(row['glow'],3.2)

def material_asset(row):
    key=row['key']
    folder=ASSETS+'/Materials'
    path=folder+'/M_'+key
    if A.does_asset_exist(path):return load(path)
    factory=unreal.MaterialFactoryNew()
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+key,folder,unreal.Material,factory)
    assert mat,path
    name=row['name']
    if name.startswith('Floor'):
        floor_material(mat)
        return persist(mat,False)
    uv=expr(mat,'TextureCoordinate')
    color=tuple(row['color'])
    v=expr(mat,'Constant3Vector',constant=unreal.LinearColor(*color,1))
    cloth=any(x in name for x in ('Mattress','Blanket','Pillow','canvas','fabric','linen','stitching'))
    drum=name.startswith('Old drum')
    contrast=.11 if ('CRT casing' in name or 'worn industrial sage' in name) else .27
    scale=7.8 if drum else 5.4 if cloth else 3.1
    if row['glow']>0 or 'CRT ·' in name or name=='Dusty rubber':
        output(v,'BASE_COLOR')
    else:
        code=NOISE+'''
float b=n.value(UV.xy*S)*.68 + n.value(UV.xy*S*3.2)*.32;
float m=lerp(1.-Weight,1.+Weight,b);
float3 R=Tint*m;
'''
        if drum:
            code+='R=lerp(R,float3(.124,.064,.027),smoothstep(.44,.73,b)*.86);'
        elif name.startswith('Mattress'):
            code+='R*=lerp(.75,1.03,smoothstep(.055,.14,frac(UV.y*12.6)));'
        elif name.startswith('Board-formed'):
            code+='R*=lerp(.72,1.11,n.value(UV.xy*float2(7.8,1.5)));'
        elif 'pine' in name:
            code+='R*=lerp(.71,1.19,n.value(UV.xy*float2(7.,49.)));'
        output(custom(mat,code+'return R;',{'UV':uv,'Tint':v,'S':expr(mat,'Constant',r=scale),
                         'Weight':expr(mat,'Constant',r=contrast)}),'BASE_COLOR')
    if cloth or drum or name.startswith('Board-formed'):
        rough=max(.38,row['roughness'])
        strength=.085 if cloth else .14 if drum else .21
        n=custom(mat,NOISE+'''
float2 P=UV.xy*Scale;
float c=n.value(P),x=n.value(P+float2(.16,0)),y=n.value(P+float2(0,.16));
return normalize(float3(float2(c-x,c-y)*Str,1.0));
''',{'UV':uv,'Scale':expr(mat,'Constant',r=71. if cloth else 21.),
          'Str':expr(mat,'Constant',r=strength)})
        output(n,'NORMAL')
        constant(mat,'ROUGHNESS',rough)
    else:
        constant(mat,'ROUGHNESS',max(row['roughness'],.29) if 'CRT ·' in name else row['roughness'])
    constant(mat,'METALLIC',row['metallic'])
    if row['glow']>0:
        power=emission_power(row)
        e=expr(mat,'Constant3Vector',constant=unreal.LinearColor(*(power*k for k in row['emission']),1))
        output(e,'EMISSIVE_COLOR')
    return persist(mat,False)

def import_models(source,world):
    manifest=json.loads((source/'ShelterExport.json').read_text(encoding='utf8'))
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    mats={row['key']:material_asset(row) for row in manifest['materials']}
    settings=unreal.FbxImportUI()
    for k,v in dict(import_mesh=True,automated_import_should_detect_type=False,
                    import_materials=False,import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        settings.set_editor_property(k,v)
    data=settings.static_mesh_import_data
    data.set_editor_property('combine_meshes',True)
    data.set_editor_property('auto_generate_collision',False)
    data.set_editor_property('generate_lightmap_u_vs',False)
    data.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    meshes={}
    axes=set()
    for row in manifest['meshes']:
        name=row['name']
        mesh=import_file(source/(name+'.obj'),ASSETS+'/Meshes',settings)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        low,high=row['obj_bounds_cm']
        bb=mesh.get_bounding_box()
        assert abs(bb.min.x-low[0])<4 and abs(bb.max.z-high[2])<4,(name,str(bb),row)
        if abs(low[1]+high[1])>12:
            if abs(bb.min.y-low[1])<4:axes.add(-1)
            elif abs(bb.min.y+high[1])<4:axes.add(1)
            else:raise RuntimeError((name,str(bb),row))
        for i,slot in enumerate(mesh.static_materials):
            labels=[str(slot.get_editor_property('imported_material_slot_name')),str(slot.material_slot_name)]
            material=next((mats[key] for key in mats if any(key.lower() in label.lower() for label in labels)),None)
            assert material,(name,labels)
            mesh.set_material(i,material)
        save(mesh)
        meshes[name.removeprefix('SM_S07_')]=mesh
    assert len(axes)==1,axes
    return meshes,manifest['colliders'],axes.pop()

def attach_mesh(bp,name,mesh,point,scale=(1.,1.,1.),collision='NoCollision'):
    part=add(bp,unreal.StaticMeshComponent,name,'SiteRoot')
    part.set_static_mesh(mesh)
    part.set_editor_property('relative_location',local(*point))
    part.set_editor_property('relative_scale3d',unreal.Vector(*scale))
    part.set_mobility(unreal.ComponentMobility.STATIC)
    part.set_collision_profile_name(collision)
    return part

def collider(bp,name,point,extent,parent='SiteRoot',solid=True):
    c=add(bp,unreal.BoxComponent,name,parent)
    c.set_editor_property('relative_location',local(*point))
    c.set_box_extent(unreal.Vector(*extent),False)
    c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
    c.set_editor_property('generate_overlap_events',False)
    c.set_editor_property('can_ever_affect_navigation',False)
    return c

def light(bp,name,p,color,power,radius,enabled,shadow=False):
    c=add(bp,unreal.PointLightComponent,name,'SiteRoot')
    c.set_editor_property('relative_location',local(*position(*p)))
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_light_color(unreal.LinearColor(*color,1))
    c.set_intensity(power)
    c.set_attenuation_radius(radius)
    c.set_cast_shadows(shadow)
    c.set_editor_property('volumetric_scattering_intensity',0.)
    c.set_visibility(enabled)

def label(bp,name,msg,point,yaw,size):
    c=add(bp,unreal.TextRenderComponent,name,'SiteRoot')
    c.set_text(unreal.Text(msg))
    c.set_world_size(size)
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    c.set_text_render_color(unreal.Color(222,210,171,255))
    c.set_editor_property('relative_location',local(*point))
    c.set_editor_property('relative_rotation',unreal.Rotator(yaw=yaw))
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return c

def radio_exposure(bp):
    bounds=collider(bp,'RadioExposureBox',position(8.42,-1.06,-.63),(188,252,92),solid=False)
    bounds.set_collision_profile_name('OverlapAllDynamic')
    pp=add(bp,unreal.PostProcessComponent,'RadioExposure','RadioExposureBox')
    pp.set_editor_property('unbound',False)
    pp.set_editor_property('blend_radius',31.)
    pp.set_editor_property('priority',64.)
    settings=pp.get_editor_property('settings')
    for key,value in (
        ('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),
        ('auto_exposure_apply_physical_camera_exposure',False),
        ('auto_exposure_bias',2.10),
        ('ambient_cubemap_intensity',.14),
    ):
        settings.set_editor_property('override_'+key,True)
        settings.set_editor_property(key,value)
    settings.set_editor_property('ambient_cubemap',load('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    pp.set_editor_property('settings',settings)

def assemble(source):
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    meshes,boxes,axis=import_models(source,editor.get_editor_world())
    bp=bp_asset(SHELTER)
    cs=components(bp)
    protect={'SiteRoot','DefaultSceneRoot',*(f'ShelterLight{i}' for i in range(7))}
    previous=[h for h,c,n in cs if c and n not in protect and n!='Root']
    if previous and not any(n=='WaterworksShell' for _,_,n in cs):
        sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        sub.delete_subobjects(cs[0][0],list(reversed(previous)),bp)
    add(bp,unreal.SceneComponent,'SiteRoot')
    for name,mesh in meshes.items():
        if name=='ExteriorHatch':continue
        attach_mesh(bp,'Waterworks'+name,mesh,ORIGIN,(1,axis,1))
    attach_mesh(bp,'WaterworksSurfaceHatch',meshes['ExteriorHatch'],HATCH_ORIGIN,(1,axis,.42))
    attach_mesh(bp,'WaterworksSurfaceRim',load('/Engine/BasicShapes/Cylinder'),
                (HATCH_ORIGIN[0],HATCH_ORIGIN[1],2152.),(2.16,2.16,.11)).set_material(0,load('/Game/Surface/Materials/M_RuinConcrete'))
    collider(bp,'SurfaceHatchSolid',(HATCH[0],HATCH[1],2156.),(98,98,9))
    for i,shape in enumerate(boxes):
        p=position(*shape['position'])
        c=collider(bp,'WalkSolid%03d'%i,p,tuple(50*d for d in shape['dimensions']))
        c.component_tags=[unreal.Name(shape['name'])]
    for side,(lo,hi) in enumerate(((4.88,5.28),(6.79,10.53))):
        for k,z in enumerate((.48,.96)):
            c=attach_mesh(bp,f'RadioLandingRail{side}{k}',load(CUBE),
                          position((lo+hi)/2,-3.57,z),(hi-lo,.047,.044))
            c.set_material(0,load('/Game/Surface/Materials/M_RuinSteel'))
        for j,x in enumerate((lo,hi)):
            c=attach_mesh(bp,f'RadioLandingPost{side}{j}',load(CUBE),position(x,-3.57,.47),(.051,.051,.94))
            c.set_material(0,load('/Game/Surface/Materials/M_RuinSteel'))
        collider(bp,f'RadioLandingSolid{side}',position((lo+hi)/2,-3.57,.50),((hi-lo)*50.,4.,50.))
    portal=attach_mesh(bp,'ExitIntercom',load(CUBE),position(-10.34,3.07,1.91),(.10,.38,.49))
    portal.set_material(0,load('/Game/LabTutorial/Industrial/M_DoorArmor'))
    label(bp,'ShelterExitLabel','ВЫХОД',position(-10.277,3.07,2.20),0,14)
    label(bp,'WaterworksCoverSign','ВОДОКАНАЛ  ·  07',(HATCH[0],HATCH[1]+117,2186),-90,11)
    # Keep the approved roof and walls dark while separating lamp pools and unpowered reserve circuits.
    for i,(p,color,power,radius,visible,shadow) in enumerate((
        ((-8.6,2.65,3.65),(.72,.84,1.),2100,490,True,False),
        ((-4.25,3.43,3.25),(1.,.76,.50),1720,445,True,False),
        ((1.95,.60,3.54),(.83,.91,1.),2250,585,True,False),
        ((2.56,-1.04,.46),(1.,.59,.31),84,137,True,False),
        ((3.20,4.97,3.27),(.80,.93,.98),3400,480,False,False),
        ((8.44,4.50,3.33),(1.,.91,.75),3300,480,False,False),
        ((8.48,-1.27,.15),(.73,.93,.98),8200,490,False,False),
        ((7.44,-1.51,.14),(.57,.78,.85),1950,410,True,False),
        ((8.45,3.28,3.38),(.92,.92,.98),1340,425,True,False),
    )):light(bp,'ShelterLight'+str(i),p,color,power,radius,visible,shadow)
    bounds=collider(bp,'WaterworksExposureBox',position(0,0,1.51),(1140,675,323),solid=False)
    pp=add(bp,unreal.PostProcessComponent,'WaterworksExposure','WaterworksExposureBox')
    pp.set_editor_property('unbound',False)
    pp.set_editor_property('blend_radius',35.)
    pp.set_editor_property('priority',63.)
    settings=pp.get_editor_property('settings')
    for name,value in (
        ('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),
        ('auto_exposure_apply_physical_camera_exposure',False),
        ('auto_exposure_bias',1.20),
        ('ambient_cubemap_intensity',.11),
    ):
        settings.set_editor_property('override_'+name,True)
        settings.set_editor_property(name,value)
    settings.set_editor_property('ambient_cubemap',load('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    pp.set_editor_property('settings',settings)
    radio_exposure(bp)
    compile_bp(bp)
    power=Story(bp,'EnableShelterPower')
    for i in range(4,7):power.visibility('ShelterLight'+str(i),True)
    compile_bp(bp)
    save(bp)
    return bp

def build_room(source=SOURCE):
    source=Path(source)
    if (source/'ShelterExport.json').exists():return assemble(source)
    with TemporaryDirectory(prefix='Shelter07_') as temp:
        with ZipFile(source/'ShelterMeshes.zip') as archive:
            for name in archive.namelist():
                assert Path(name).name==name,name
            archive.extractall(temp)
        return assemble(Path(temp))
