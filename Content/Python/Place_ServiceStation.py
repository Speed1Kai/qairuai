"""Import the city service station and place it on the connected gameplay level."""
from datetime import datetime
import json
import shutil

import unreal

from Build_CityReclaim import ROOT as CITY, material, M
from SurfacePolish_Materials import import_file
from Build_RuinedUrbanCampus import (
    A, B, GROUND, LEVEL, OFFSET, Site, V, actors, add, compile_bp,
    content, levels, local, save, saved, tools,
)

ROOT = '/Game/Environment/CityService'
SOURCE = content.parent/'SourceAssets/CityService'
X,Y,Z = 35040.,86900.,GROUND
LABEL = 'CITY_ServiceStation_07'
MESHES = ('Shell','Furniture','Details')
COMPUTER = 'SM_HackComputer'


def asset(path):
    result=A.load_asset(path)
    assert result,path
    return result


def materials():
    result={key:asset(CITY+'/M_Reclaim_'+kind) for key,kind in (
        ('Masonry','Concrete'),('Frame','Frame'),('Shards','Shards'),('Glass','Glass'),
        ('Steel','Armor'),('Glow','Cyan'),('Ivy','Leaf'))}
    result['Floor']=asset('/Game/Environment/SurfacePolish/M_Scan_Concrete')
    result['Oxide']=asset('/Game/Surface/Materials/M_Oxide')
    weather='''
float2 q=abs(N.z)>.65 ? P.xy : float2(P.x+P.y*.83,P.z);
float large=n.sample(q/79.)*.65+n.sample(q/22.)*.35;
float grain=n.sample(q/2.1);
float stain=smoothstep(.55,.88,n.sample(q*float2(.024,.0049)));
return Tint*(.69+.40*large+.08*grain-.22*stain);
'''
    wood='''
float2 q=(P.xy+P.z*float2(.53,.21))*float2(.07,.82);
float a=n.sample(q)*.6+n.sample(q*.21)*.4;
return Tint*(.65+.51*a+.075*n.sample(P.xy));
'''
    for key,tint,metal,rough,field in (
        ('Cladding',(.105,.168,.178),.55,.54,weather),('Plaster',(.34,.345,.29),0.,.86,weather),
        ('Timber',(.182,.102,.046),0.,.67,wood),('Rubber',(.036,.043,.042),.04,.84,weather),
        ('Safety',(.61,.24,.037),.24,.59,weather),('Paper',(.47,.39,.24),0.,.86,weather)):
        result[key]=material('Station'+key,tint,metal,rough,field=field)
    result['Warm']=material('StationWarm',(3.0,1.61,.63),emission=True)
    return result


def display_material():
    name='M_HackComputer_Display'
    path=ROOT+'/'+name
    if A.does_asset_exist(path):
        return asset(path)
    tex=import_file(SOURCE/'T_HackComputer_Atlas.png',root=ROOT)
    tex.set_editor_property('srgb',True)
    tex.set_editor_property('max_texture_size',1024)
    save(tex)
    display=tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    display.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    sample=M.create_material_expression(display,unreal.MaterialExpressionTextureSample,-310,0)
    sample.set_editor_property('texture',tex)
    assert M.connect_material_property(sample,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    M.set_material_usage(display,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    M.recompile_material(display)
    save(display)
    return display


def import_meshes(reimport=()):
    A.make_directory(ROOT)
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
    mats=materials()
    mats['HackDisplay']=display_material()
    mats['HackCase']=mats['Frame']
    options=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,import_materials=False,
                          import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(key,value)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    result={}
    mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for kind in (*MESHES,'Computer'):
        name=COMPUTER if kind=='Computer' else 'SM_ServiceStation_'+kind
        path=ROOT+'/'+name
        if kind in reimport or not A.does_asset_exist(path):
            task=unreal.AssetImportTask()
            for key,value in dict(filename=str(SOURCE/(name+'.fbx')),destination_path=ROOT,
                                  destination_name=name,automated=True,save=False,replace_existing=True,options=options).items():
                task.set_editor_property(key,value)
            tools.import_asset_tasks([task])
            assert task.get_objects(),name
        mesh=asset(path)
        slots={}
        for i,slot in enumerate(mesh.static_materials):
            imported=str(slot.get_editor_property('imported_material_slot_name'))
            if imported in mats:
                mesh.set_material(i,mats[imported])
                slots[imported]=i
        if kind=='Details':
            assert len(slots)==mesh.get_num_sections(0),(name,slots)
            for section,key in enumerate(sorted(slots)):
                index=slots[key]
                if mesh_editor.get_lod_material_slot(mesh,0,section)!=index:
                    mesh_editor.set_lod_material_slot(mesh,index,0,section)
        if kind=='Computer':
            assert set(slots)=={'HackCase','HackDisplay'},slots
        if kind in ('Shell','Furniture'):
            body=mesh.get_editor_property('body_setup')
            body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            body.set_editor_property('double_sided_geometry',True)
        save(mesh)
        result[kind]=mesh
    b=result['Shell'].get_bounding_box()
    assert b.min.y<-640 and 475<b.max.y<510 and 1320<b.max.x-b.min.x<1390,str(b)
    b=result['Computer'].get_bounding_box()
    assert 101<b.max.x-b.min.x<107 and abs(b.min.z)<.15 and 49<b.max.z<56,str(b)
    return result


def station_point(x,y,z):
    # FBX flips Y. The -90 degree placement turns the entrance toward the street.
    return (X-y*100,Y-x*100,Z+z*100)


def label(bp,name,message,x,y,z,size,facing,color):
    c=add(bp,unreal.TextRenderComponent,name,'SiteRoot')
    c.set_mobility(unreal.ComponentMobility.STATIC)
    c.set_text(unreal.Text(message))
    c.set_world_size(size)
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    c.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    c.set_text_render_color(unreal.Color(*color,255))
    c.set_editor_property('relative_location',local(*station_point(x,y,z)))
    c.set_editor_property('relative_rotation',unreal.Rotator(yaw=facing))
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)


def author(meshes):
    path=ROOT+'/BP_ServiceStation'
    if A.does_asset_exist(path):
        bp=asset(path)
    else:
        factory=unreal.BlueprintFactory()
        factory.set_editor_property('parent_class',unreal.Actor)
        bp=tools.create_asset('BP_ServiceStation',ROOT,unreal.Blueprint,factory)
    site=Site(bp)
    for kind in MESHES:
        site.mesh(kind,meshes[kind],X,Y,Z,yaw=-90,collide=kind!='Details')
        site.batches[kind].set_cull_distances(0,0)
        site.batches[kind].set_editor_property('can_ever_affect_navigation',False)
    for x,y,yaw in ((-3.93,2.03,90.),(-3.22,-4.01,-90.)):
        site.mesh('Computers',meshes['Computer'],*station_point(x,y,.97),yaw=yaw)
    site.batches['Computers'].set_cull_distances(3600,8500)
    site.batches['Computers'].set_editor_property('can_ever_affect_navigation',False)
    label(bp,'FacadeSign','MUNICIPAL SERVICE  /  07',0.,4.991,3.52,20.,180,(171,196,188))
    label(bp,'ReceptionSign','SERVICE DESK',-3.62,-.514,2.45,19.,180,(166,194,190))
    label(bp,'WorkshopSign','WORKSHOP',0.,-.446,2.69,15.,180,(169,193,185))
    label(bp,'StorageSign','PARTS',1.29,1.43,2.68,15.,0,(207,166,102))
    for name,x,y,z,power,radius,color in (
        ('ReceptionLight',-3.3,2.08,3.07,520.,550.,(.67,.84,1.)),
        ('HallLight',.52,3.10,3.07,310.,465.,(.78,.89,1.)),
        ('WorkLight',-2.9,-2.9,3.07,690.,610.,(1.,.72,.44)),
        ('StorageLight',4.46,-.91,3.06,480.,490.,(1.,.77,.52)),
    ):
        c=add(bp,unreal.PointLightComponent,name,'SiteRoot')
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_location',local(*station_point(x,y,z)))
        c.set_intensity(power)
        c.set_attenuation_radius(radius)
        c.set_source_radius(17.)
        c.set_light_color(unreal.LinearColor(*color,1.))
        c.set_editor_property('volumetric_scattering_intensity',0.)
        c.set_cast_shadows(True)
    ivy=asset(CITY+'/SM_Reclaim_IvyCurtain')
    for index,(x,y,z,s,angle) in enumerate(((-5.84,5.015,3.60,.73,90),(5.23,4.99,3.57,.53,90),
                                           (6.69,1.2,3.55,.61,0),(-6.67,-1.0,3.57,.57,180))):
        site.mesh('FacadeIvy',ivy,*station_point(x,y,z),scale=(s,.74,s),yaw=angle)
    site.batches['FacadeIvy'].set_cull_distances(8400,21500)
    compile_bp(bp)
    save(bp)
    return bp


def clear_planting(city):
    removed=0
    for c in city.get_components_by_class(unreal.InstancedStaticMeshComponent):
        if not c.get_name().startswith(('HorizonFir','StreetFir','LowShrub','Grass_')):
            continue
        for i in range(c.get_instance_count()-1,-1,-1):
            p=c.get_instance_transform(i,True).translation
            x,y=p.x+OFFSET[0],p.y+OFFSET[1]
            if X-760<x<X+530 and abs(y-Y)<725:
                c.modify()
                assert c.remove_instance(i)
                removed+=1
    return removed


def main(reimport=()):
    world=levels.load_map(LEVEL)
    assert world
    meshes=import_meshes(reimport=reimport)
    bp=author(meshes)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    backup=saved/'Backups/ServiceStation'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(LEVEL.removeprefix('/Game/')+'.umap'),backup)
    removed=clear_planting(scene['RECLAIM_City'])
    if LABEL in scene:
        assert actors.destroy_actor(scene[LABEL])
    station=actors.spawn_actor_from_class(B.generated_class(bp),unreal.Vector())
    assert station
    station.set_actor_label(LABEL)
    station.set_folder_path('SURFACE/City Service')
    world.modify()
    assert levels.save_map(world,LEVEL)
    assert levels.load_map(LEVEL)
    scene={a.get_actor_label():a for a in actors.get_all_level_actors()}
    assert LABEL in scene and clear_planting(scene['RECLAIM_City'])==0
    (saved/'service_station_placement.json').write_text(json.dumps(dict(saved=True,actor=LABEL,
        position_cm=[X,Y,Z],planting_cleared=removed,backup=str(backup)),indent=2),encoding='utf-8')
