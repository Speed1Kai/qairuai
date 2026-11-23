"""Directed, animated translucent air jets; compact dark exhaust nozzles.
Only effects and their visibility hooks change. Movement physics is unchanged.
"""
import unreal,os,sys,math,shutil,datetime,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,M,add,components,compile_bp,save,pin,val,link
try:
    import Test_AirJetRegression as test
    if test.T.get('handle'):unreal.unregister_slate_post_tick_callback(test.T['handle'])
    test.write()
except (ImportError,KeyError):pass
assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE first'
ROOT='/Game/Characters/AirJet';bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
backup=os.path.join(unreal.Paths.project_saved_dir(),'Backups/AirJetFX',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True);shutil.copy2(os.path.join(unreal.Paths.project_content_dir(),'ThirdPerson/Blueprints/BP_ThirdPersonCharacter.uasset'),backup)
source=os.path.join(unreal.Paths.project_dir(),'SourceAssets/AirJet');os.makedirs(source,exist_ok=True)
obj=os.path.join(source,'SM_PressureAirCone.obj')
if not os.path.exists(obj):
    vertices=[];uvs=[];faces=[]
    # Nested translucent shells create depth without a new particle simulation.
    for shell in range(3):
        start=len(vertices);N=20;R=10
        for j in range(R+1):
            t=j/R
            for i in range(N+1):
                a=i/N*math.tau;rad=(3+31*t)*(1-shell*.22)
                vertices.append((rad*math.cos(a),-rad*math.sin(a),t*(190-shell*22)));uvs.append((i/N,t))
        for j in range(R):
            for i in range(N):
                k=start+j*(N+1)+i+1
                faces.extend([(k,k+1,k+N+2),(k,k+N+2,k+N+1)])
    with open(obj,'w') as f:
        f.write('o SM_PressureAirCone\n')
        for v in vertices:f.write('v %.6f %.6f %.6f\n'%v)
        for v in uvs:f.write('vt %.6f %.6f\n'%v)
        for face in faces:f.write('f '+' '.join('%d/%d'%(k,k) for k in face)+'\n')
meshpath=ROOT+'/SM_PressureAirCone'
if not A.does_asset_exist(meshpath):
    task=unreal.AssetImportTask();opt=unreal.FbxImportUI()
    for k,v in [('import_materials',False),('import_textures',False),('automated_import_should_detect_type',False),('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)]:opt.set_editor_property(k,v)
    opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
    for k,v in dict(filename=obj,destination_path=ROOT,destination_name='SM_PressureAirCone',options=opt,automated=True,save=True).items():task.set_editor_property(k,v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=A.load_asset(meshpath);assert mesh
mp=ROOT+'/M_CompressedAir';mat=A.load_asset(mp) if A.does_asset_exist(mp) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_CompressedAir',ROOT,unreal.Material,unreal.MaterialFactoryNew())
M.delete_all_material_expressions(mat);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('two_sided',True);mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
uv=M.create_material_expression(mat,unreal.MaterialExpressionTextureCoordinate,-500,0);tm=M.create_material_expression(mat,unreal.MaterialExpressionTime,-500,180)
custom=M.create_material_expression(mat,unreal.MaterialExpressionCustom,-100,80)
inputs=[]
for name in ('UV','T'):
    i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
custom.set_editor_property('inputs',inputs);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
custom.set_editor_property('code','float u=UV.x; float v=saturate(UV.y); float n=sin(u*37+v*23-T*18)*sin(u*19-v*39+T*13); float bands=pow(saturate(0.5+0.5*sin(v*48-T*42+n*0.8)),5); float axial=(1-smoothstep(0.55,1.0,v))*smoothstep(0.0,0.035,v); float ragged=0.55+0.45*sin(u*18.8496+v*18-T*6); return axial*(0.045+0.18*bands)*(0.4+0.6*ragged);')
M.connect_material_expressions(uv,'',custom,'UV');M.connect_material_expressions(tm,'',custom,'T');M.connect_material_property(custom,'',unreal.MaterialProperty.MP_OPACITY)
color=M.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-100,-140);color.set_editor_property('constant',unreal.LinearColor(r=.46,g=.58,b=.62,a=1));M.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);M.recompile_material(mat);save(mat);mesh.set_material(0,mat);save(mesh)
for side,label in [(-1,'Left'),(1,'Right')]:
    c=add(bp,unreal.StaticMeshComponent,'AirJetPlume'+label,'CapsuleComponent');c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);c.set_editor_property('cast_shadow',False)
    c.set_editor_property('relative_location',unreal.Vector(x=-30,y=side*18,z=30));c.set_editor_property('relative_rotation',unreal.Rotator(pitch=145,yaw=0,roll=0));c.set_visibility(False)
    for h,n,name in components(bp):
        if name=='AirJetNozzle'+label:n.set_material(0,A.load_asset('/Game/LabTutorial/FirstFloor/M_LabGraphite'));n.set_editor_property('relative_scale3d',unreal.Vector(x=.1,y=.1,z=.16))
compile_bp(bp)
for fn,visible,lasttitle in [('AirJet_Start',True,'LaunchCharacter'),('AirJet_Stop',False,'FadeOut')]:
    e=G.get_graph_editor_by_name(bp,fn)
    tag='AirJetPlumeVisibility'+('On' if visible else 'Off')
    if any(n.get_name()==tag for n in e.list_all_nodes()):continue
    last=next(n for n in e.list_all_nodes() if str(n.get_node_title())==lasttitle)
    cursor=last.find_then_pin();assert not cursor.list_connected_pins()
    for label in ('Left','Right'):
        get=e.add_get_member_variable_node('AirJetPlume'+label);n=e.add_call_function_node('/Script/Engine.SceneComponent.SetVisibility');link(pin(get,'AirJetPlume'+label,True),n.find_self_pin());val(pin(n,'bNewVisibility'),visible);link(cursor,n.find_execute_pin());cursor=n.find_then_pin();n.rename(tag if label=='Left' else tag+'Right')
compile_bp(bp);save(bp)
json.dump({'saved':True,'backup':backup,'directed_air_mesh':meshpath,'nozzle_material':'M_LabGraphite','movement_unchanged':True},open(os.path.join(unreal.Paths.project_saved_dir(),'airjet_visuals_report.json'),'w'),indent=2)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
