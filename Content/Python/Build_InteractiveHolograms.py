"""Author six independent F-operated archive projectors in the existing lab.
All runtime behaviour is saved Blueprint logic. Python is authoring only.
"""
import unreal, os, math, json, shutil, traceback, wave, struct, random
A=unreal.EditorAssetLibrary; B=unreal.BlueprintEditorLibrary
G=unreal.BlueprintGraphEditor; M=unreal.MaterialEditingLibrary
ROOT='/Game/LabTutorial/Holograms'
CONTENT=unreal.Paths.project_content_dir(); SAVED=unreal.Paths.project_saved_dir()
REPORT=os.path.join(SAVED,'interactive_holograms_report.json')
def V(p):return unreal.Vector(*p)
def pin(n,k,out=False):
    if not n:raise RuntimeError('Missing node for '+k)
    p=n.find_output_pin(k) if out else n.find_input_pin(k)
    if not p.is_valid():raise RuntimeError('Missing '+n.get_name()+'.'+k)
    return p
def value(p,x):
    if hasattr(x,'is_valid'):
        if not x.try_create_connection(p):raise RuntimeError('Connection failed to '+str(p.get_pin_name()))
    elif not p.set_pin_value(str(x).lower() if isinstance(x,bool) else str(x)):
        raise RuntimeError('Default failed '+str(p.get_pin_name())+'='+str(x))
def link(a,b):value(b,a)
def import_asset(filename):
    existing=ROOT+'/'+os.path.splitext(os.path.basename(filename))[0]
    if A.does_asset_exist(existing):return A.load_asset(existing)
    task=unreal.AssetImportTask()
    for k,v in dict(filename=filename,destination_path=ROOT,automated=True,replace_existing=True,save=True).items():task.set_editor_property(k,v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return A.load_asset(ROOT+'/'+os.path.splitext(os.path.basename(filename))[0])
def material():
    path=ROOT+'/M_ArchiveProjection'
    mat=A.load_asset(path) or unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_ArchiveProjection',ROOT,unreal.Material,unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    def n(cls,**kw):
        q=M.create_material_expression(mat,cls)
        for k,v in kw.items():q.set_editor_property(k,v)
        return q
    tex=n(unreal.MaterialExpressionTextureSampleParameter2D,parameter_name='Archive',texture=textures[0])
    uv=n(unreal.MaterialExpressionTextureCoordinate)
    corrected_uv=n(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    item=unreal.CustomInput();item.set_editor_property('input_name','UV')
    corrected_uv.set_editor_property('inputs',[item])
    corrected_uv.set_editor_property('code','return 1.0-UV;')
    M.connect_material_expressions(uv,'',corrected_uv,'UV')
    M.connect_material_expressions(corrected_uv,'',tex,'UVs')
    clock=n(unreal.MaterialExpressionTime)
    start=n(unreal.MaterialExpressionScalarParameter,parameter_name='ActivationTime',default_value=-100.0,
            use_custom_primitive_data=True,primitive_data_index=0)
    custom=n(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    names=['Graphic','Alpha','UV','Clock','Start']
    inputs=[]
    for name in names:
        item=unreal.CustomInput()
        item.set_editor_property('input_name',name)
        inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    custom.set_editor_property('code','''
float age=max(0,Clock-Start);
float rise=saturate(age/1.15);
float reveal=smoothstep(1-rise-.035,1-rise+.035,UV.y);
float scan=.91+.09*sin(UV.y*1400-Clock*7);
float boot=lerp(.45+.55*step(.1,sin(age*59)),1,saturate(age/1.3));
float band=exp(-abs(UV.y-(1-rise))*140)*(1-step(1.2,age));
return float4(Graphic*float3(.45,1.0,1.1)*(48.0+band*6),Alpha*reveal*scan*boot);
''')
    for src,out,name in ((tex,'RGB','Graphic'),(tex,'A','Alpha'),(corrected_uv,'','UV'),(clock,'','Clock'),(start,'','Start')):
        if not M.connect_material_expressions(src,out,custom,name):raise RuntimeError('Material input '+name)
    rgb=n(unreal.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=n(unreal.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    for dst in (rgb,alpha):
        if not M.connect_material_expressions(custom,'',dst,'Input'):
            if not M.connect_material_expressions(custom,'',dst,''):raise RuntimeError('Mask input')
    M.connect_material_property(rgb,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    M.connect_material_property(alpha,'',unreal.MaterialProperty.MP_OPACITY)
    M.recompile_material(mat);A.save_loaded_asset(mat)
    return mat
def instance(name,parent,texture):
    mi=A.load_asset(ROOT+'/'+name) or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    M.set_material_instance_parent(mi,parent)
    M.set_material_instance_texture_parameter_value(mi,'Archive',texture)
    A.save_loaded_asset(mi);return mi
def components(bp):
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    return [(h,lib.get_object_for_blueprint(lib.get_data(h),bp),str(lib.get_variable_name(lib.get_data(h)))) for h in sub.k2_gather_subobject_data_for_blueprint(bp)]
def add(bp,cls,name):
    for h,c,k in components(bp):
        if k==name:return c
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    params=unreal.AddNewSubobjectParams(parent_handle=components(bp)[0][0],new_class=cls,blueprint_context=bp)
    h,reason=sub.add_new_subobject(params)
    c=lib.get_object_for_blueprint(lib.get_data(h),bp)
    if not c:raise RuntimeError(str(reason))
    sub.rename_subobject(h,unreal.Text(name));return c
def setup_mesh(bp,name,mesh,mat,pos,scale,collision=False,hidden=False,rotation=None):
    c=add(bp,unreal.StaticMeshComponent,name);c.set_static_mesh(mesh);c.set_material(0,mat)
    c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_scale3d',V(scale))
    if rotation:c.set_editor_property('relative_rotation',rotation)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    c.set_editor_property('cast_shadow',False);c.set_visibility(not hidden)
    return c

def setup_backing(bp,panel):
    path=ROOT+'/M_ProjectionBacking'
    mat=A.load_asset(path)
    if not mat:
        mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_ProjectionBacking',ROOT,unreal.Material,unreal.MaterialFactoryNew())
        mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided',True)
        c=M.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector)
        c.set_editor_property('constant',unreal.LinearColor(r=0,g=.002,b=.004,a=1))
        M.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        a=M.create_material_expression(mat,unreal.MaterialExpressionConstant)
        a.set_editor_property('r',.48)
        M.connect_material_property(a,'',unreal.MaterialProperty.MP_OPACITY)
        M.recompile_material(mat);A.save_loaded_asset(mat)
    c=setup_mesh(bp,'ProjectionBacking',panel,mat,(0,2,0),(1,1,1),hidden=True)
    handles={name:h for h,obj,name in components(bp)}
    unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).attach_subobject(handles['Projection'],handles['ProjectionBacking'])
    c.set_editor_property('relative_location',V((0,2,0)))
    c.set_editor_property('relative_scale3d',V((1,1,1)))

class Graph:
    def __init__(self,bp):self.e=G.get_graph_editor_by_name(bp,'EventGraph');self.x=0;self.y=0;self.cursor=None
    def node(self,n):
        if not n:raise RuntimeError('Node creation failed')
        n.set_node_pos(unreal.IntPoint(x=self.x,y=self.y));self.x+=260
        if self.x>1900:self.x=0;self.y+=320
        return n
    def call(self,f,target=None,**args):
        n=self.node(self.e.add_call_function_node('/Script/'+f))
        if target is not None:value(n.find_self_pin(),target)
        for k,v in args.items():value(pin(n,k),v)
        return n
    def out(self,n,k='ReturnValue'):return pin(n,k,True)
    def get(self,k):return self.out(self.node(self.e.add_get_member_variable_node(k)),k)
    def do(self,n):link(self.cursor,n.find_execute_pin());self.cursor=n.find_then_pin();return n
    def set(self,k,v):
        n=self.node(self.e.add_set_member_variable_node(k));value(pin(n,k),v);return self.do(n)
    def math(self,f,**args):return self.out(self.call('Engine.KismetMathLibrary.'+f,**args))
    def visible(self,comp,visible):return self.do(self.call('Engine.SceneComponent.SetVisibility',target=self.get(comp),bNewVisibility=visible,bPropagateToChildren=True))
    def branch(self,condition):
        n=self.node(self.e.add_branch_node());value(pin(n,'Condition'),condition);self.do(n);return n
    def event(self,name):
        event=self.e.find_event_node(name)
        if not event:raise RuntimeError('Factory event missing '+name)
        self.cursor=pin(event,'then',True)

try:
    commandlet='-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower()
    if not commandlet:
        unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before authoring')
    world=unreal.EditorLevelLibrary.get_editor_world()
    if not world or not world.get_path_name().startswith('/Game/Lvl_LabTutorial.'):
        unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
    backup=os.path.join(SAVED,'Backups','Holograms');os.makedirs(backup,exist_ok=True)
    for src in (os.path.join(CONTENT,'Lvl_LabTutorial.umap'),):
        dst=os.path.join(backup,os.path.basename(src))
        if not os.path.exists(dst):shutil.copy2(src,dst)
    A.make_directory(ROOT)
    textures=[]
    for i in range(1,7):
        t=import_asset(os.path.join(CONTENT,'LabTutorial','Holograms','Source','T_HoloArchive_%02d.png'%i))
        t.set_editor_property('lod_group',unreal.TextureGroup.TEXTUREGROUP_UI)
        t.set_editor_property('never_stream',False)
        t.set_editor_property('max_texture_size',1024)
        A.save_loaded_asset(t);textures.append(t)
    panel=import_asset(os.path.join(CONTENT,'LabTutorial','Holograms','Source','SM_ArchivePanel.obj'))
    beam_texture=import_asset(os.path.join(CONTENT,'LabTutorial','Holograms','Source','T_ProjectorBeam.png'))
    master=material()
    materials=[instance('MI_Archive%02d'%(i+1),master,t) for i,t in enumerate(textures)]
    beam_mat=instance('MI_ProjectorBeam',master,beam_texture)
    sound=import_asset(os.path.join(CONTENT,'LabTutorial','Holograms','Source','S_ProjectorStartup.wav'))
    steel=A.load_asset('/Game/LabTutorial/ReferenceStyle/M_OxidizedPaint')
    black=A.load_asset('/Game/LabTutorial/ReferenceStyle/M_CableRubber')
    glow=A.load_asset('/Game/LabTutorial/ReferenceStyle/M_CyanPhosphor')
    cylinder=A.load_asset('/Engine/BasicShapes/Cylinder');cube=A.load_asset('/Engine/BasicShapes/Cube')
    bps=[]
    for index in range(6):
        name='BP_ArchiveProjector_%02d'%(index+1);path=ROOT+'/'+name
        bp=A.load_asset(path)
        if not bp:
            if index>0:
                bp=A.duplicate_asset(ROOT+'/BP_ArchiveProjector_01',path)
            else:
                f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
                bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Blueprint,f)
        if not B.compile_blueprint(bp):raise RuntimeError('Initial compile '+name)
        setup_mesh(bp,'Foot',cylinder,black,(0,0,7),(1.28,1.28,.14),True)
        setup_mesh(bp,'Housing',cylinder,steel,(0,0,19),(1.1,1.1,.2),True)
        setup_mesh(bp,'EmitterRim',cylinder,glow,(0,0,30),(.83,.83,.035))
        setup_mesh(bp,'Lens',cylinder,black,(0,0,32),(.72,.72,.04))
        setup_mesh(bp,'EmitterCore',cylinder,glow,(0,0,34),(.32,.32,.02))
        for j in range(6):
            a=math.radians(j*60);setup_mesh(bp,'CoolingRib%d'%j,cube,steel,
                (math.cos(a)*52,math.sin(a)*52,20),(.16,.18,.34),rotation=unreal.Rotator(yaw=j*60))
        setup_mesh(bp,'Projection',panel,materials[index],(0,-20,224),(1.15,1,1),hidden=True)
        setup_backing(bp,panel)
        setup_mesh(bp,'ProjectionBeam',panel,beam_mat,(0,1,95),(.58,1,.43),hidden=True)
        prompt=add(bp,unreal.TextRenderComponent,'InteractPrompt')
        prompt.set_text(unreal.Text('[F]'));prompt.set_world_size(17.)
        prompt.set_editor_property('relative_location',V((0,-12,108)))
        prompt.set_editor_property('relative_rotation',unreal.Rotator(yaw=-90))
        prompt.set_editor_property('horizontal_alignment',unreal.HorizTextAligment.EHTA_CENTER)
        prompt.set_text_render_color(unreal.Color(r=110,g=238,b=255,a=255))
        prompt.set_text_material(A.load_asset('/Game/LabTutorial/ReferenceStyle/M_HologramText'))
        prompt.set_visibility(False);prompt.set_editor_property('cast_shadow',False)
        if not B.compile_blueprint(bp):raise RuntimeError('Component compile '+name)
        if 'ProjectionActive' in [str(n) for n in B.list_member_variable_names(bp)]:
            if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Save '+name)
            bps.append(bp)
            continue
        g=Graph(bp)
        # Rerunnable: clear the authored graph while preserving native event stubs.
        g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
        members=[str(x) for x in B.list_member_variable_names(bp)]
        for var in ('PlayerNear','ProjectionActive'):
            if var not in members:g.e.add_member_variable(var,B.get_basic_type_by_name('bool'),'false')
        B.compile_blueprint(bp);g=Graph(bp)
        g.event('ReceiveTick')
        pawn=g.out(g.call('Engine.GameplayStatics.GetPlayerPawn',PlayerIndex=0))
        distance=g.out(g.call('Engine.Actor.GetDistanceTo',OtherActor=pawn))
        pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
        locked=g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=pc))
        near=g.math('BooleanAND',A=g.math('Less_DoubleDouble',A=distance,B=175),B=g.math('Not_PreBool',A=locked))
        g.set('PlayerNear',near);g.visible('InteractPrompt',g.get('PlayerNear'))
        menu=[n for n in g.e.list_available_nodes([]) if n.endswith('|KeyboardEvents|F')]
        if len(menu)!=1:raise RuntimeError('F action missing '+str(menu))
        event=g.node(g.e.create_node_from_name(menu[0],unreal.Vector2D(x=0,y=1400),[]))
        event.set_editor_property('bConsumeInput',False)
        g.cursor=pin(event,'Pressed',True);g.branch(g.get('PlayerNear'))
        g.set('ProjectionActive',g.math('Not_PreBool',A=g.get('ProjectionActive')))
        g.visible('Projection',g.get('ProjectionActive'));g.visible('ProjectionBeam',g.get('ProjectionActive'))
        g.branch(g.get('ProjectionActive'))
        now=g.out(g.call('Engine.KismetSystemLibrary.GetGameTimeInSeconds'))
        for comp in ('Projection','ProjectionBeam'):
            g.do(g.call('Engine.PrimitiveComponent.SetCustomPrimitiveDataFloat',target=g.get(comp),DataIndex=0,Value=now))
        g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound="SoundWave'"+sound.get_path_name()+"'",
                    Location=g.out(g.call('Engine.Actor.K2_GetActorLocation')),VolumeMultiplier=.35))
        g.e.add_comment_to_nodes('F: nearby local player only. Toggle projection; restart scan reveal and audio on activation.',
                                  [n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'],30)
        cdo=unreal.get_default_object(B.generated_class(bp));cdo.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
        tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('tick_interval',.08);cdo.set_editor_property('primary_actor_tick',tick)
        if not B.compile_blueprint(bp):raise RuntimeError('Graph compile '+name)
        if not A.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Save '+name)
        bps.append(bp)
    # Replace the old always-visible billboard and block figure with local projectors.
    for actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
        n=actor.get_actor_label()
        if n.startswith(('HOLO_','LAB_Hologram_','LAB_Projector_')) or n=='LAB_CyanProjector_Spot_Up':
            unreal.EditorLevelLibrary.destroy_actor(actor)
    placements=[(-210,405,0),(130,405,0),(470,405,0),(-420,-340,180),(-70,-340,180),(280,-340,180)]
    for i,(x,y,yaw) in enumerate(placements):
        a=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bps[i]),V((x,y,0)),unreal.Rotator(yaw=yaw))
        a.set_actor_label('HOLO_ArchiveProjector_%02d'%(i+1));a.set_folder_path('LAB/05_Story/Projectors')
        a.set_editor_property('auto_receive_input',unreal.AutoReceiveInput.PLAYER0)
    if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Map save failed')
    with open(REPORT,'w',encoding='utf8') as f:json.dump(dict(saved=True,blueprints=[b.get_path_name() for b in bps],positions=placements,
        interaction='F within 175cm, hidden during capsule intro, repeat F toggles off',
        rendering='six 768x1024 RGBA graphics, shared unlit scan shader, no capture or volumetric fog'),f,indent=2)
    unreal.log('INTERACTIVE HOLOGRAM PROJECTORS SAVED')
except Exception:
    with open(REPORT,'w',encoding='utf8') as f:json.dump(dict(error=traceback.format_exc()),f,indent=2)
    raise
