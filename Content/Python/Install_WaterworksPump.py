"""Install Manual Mode at the existing water tower on the streamed city map."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0,str(project/'Content/Python'))
from CityCombat_Common import A, B, G, add, compile_bp, components, link, save, val, var
from Build_RiverForest import custom, expr, output as material_output, persist
from Install_StoryMemory import MISSION, Story, insert_entry, load, L
from Install_EvacuationRelay import checkpoint_graphs, focus, phase, player_outside
from Install_DemoCheckpoint import finish_restore
from SurfacePolish_Materials import import_file

ROOT='/Game/Story/WaterworksPump'
SITE=(29570.,89340.,2156.)
TITLE='РУЧНОЙ РЕЖИМ'
LOCAL=(-106.,-41.,155.)
DRAIN=(-63.,-56.,106.)
FEED=(45.,-56.,106.)
GAUGE=(-6.,-22.,188.)
TAP=(109.,-57.,111.)
APPROACH=(29562.,89087.,2258.)
ENTRY=(30783.,88046.,2261.)
EXIT=(33105.,88046.,2260.)
RADIO_COMPLETE=13
SAVED=6
V=unreal.Vector
COLOR={
    'Iron':'/Game/Surface/Materials/M_RuinSteel',
    'Pipe':'/Game/Environment/CityReclaim/M_Reclaim_StationCladding',
    'Steel':'/Game/Environment/CityReclaim/M_Reclaim_InfillSteel',
    'Oxide':'/Game/Surface/Materials/M_Oxide',
    'Paint':'/Game/LabTutorial/Industrial/M_DoorArmor',
    'Card':'/Game/Environment/CityReclaim/M_Reclaim_StationPaper',
    'Wheel':'/Game/Environment/CityReclaim/M_Reclaim_MachineCrimson',
    'Black':'/Game/Surface/Materials/M_Charcoal',
    'Concrete':'/Game/Surface/Materials/CampusPaving/M_CampusConcreteSlabs',
    'Warning':'/Game/Environment/CityReclaim/M_Reclaim_StationSafety',
    'Letter':'/Game/Environment/CityReclaim/M_Reclaim_StationPaper',
}
RED='/Game/LabTutorial/Industrial/M_DoorStatus_Red'
GREEN='/Game/LabTutorial/Industrial/M_DoorStatus_Green'
AMBER='/Game/Combat/Firearms/M_StatusAmber'
CLICK='/Game/Combat/CyborgModes/S_ModeSelect'
START='/Game/LabTutorial/Industrial/S_BlastDoorHydraulicRelease'
WHEEL_RATE=.34

def at(point):
    return tuple(base+coord for base,coord in zip(SITE,point))

def water_material():
    name='M_Waterworks_Stream'
    if A.does_asset_exist(ROOT+'/'+name):
        return load(ROOT+'/'+name)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    asset=tools.create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    assert asset,name
    asset.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    asset.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    asset.set_editor_property('two_sided',True)
    position=expr(asset,'WorldPosition')
    time=expr(asset,'Time')
    shade=custom(asset,
        'float shimmer=pow(0.5+0.5*sin(P.z*0.43+T*21.5+sin(P.x*0.84+P.y*0.38)),5.0);'
        'return lerp(float3(0.055,0.24,0.33),float3(0.55,0.81,0.90),shimmer);',
        {'P':position,'T':time})
    material_output(shade,'EMISSIVE_COLOR')
    material_output(expr(asset,'Constant',r=.66),'OPACITY')
    return persist(asset,False)

def meshes():
    source=project/'SourceAssets/WaterworksPump'
    ui=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False, import_materials=False,
                          import_textures=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        ui.set_editor_property(key,value)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    ui.static_mesh_import_data.set_editor_property('combine_meshes',True)
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    models={}
    materials={}
    for name in ('Manifold','Handwheel','Selector','Needle','WaterStream','Placards'):
        model=import_file(source/('SM_Waterworks_'+name+'.fbx'),ROOT,ui)
        for index,slot in enumerate(model.static_materials):
            key=str(slot.get_editor_property('imported_material_slot_name'))
            if key not in materials:
                materials[key]=water_material() if key=='Water' else load(COLOR[key])
            model.set_material(index,materials[key])
        save(model)
        models[name]=model
    return models

def hardware(bp,models):
    site=add(bp,unreal.SceneComponent,'PumpSite','Root')
    site.set_editor_property('relative_location',V(*SITE))
    wheel=models['Handwheel'].get_bounding_box()
    # The switch and wheels must face the path regardless of the FBX handedness.
    front_sign=-1 if abs(wheel.min.y)>abs(wheel.max.y) else 1
    def mesh(key,model,pos,shape=(1,1,1),material=None,rotation=0.,target=False):
        c=add(bp,unreal.StaticMeshComponent,'Pump'+key,'PumpSite')
        c.set_static_mesh(model)
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('relative_scale3d',V(*shape))
        c.set_editor_property('relative_location',V(*pos))
        c.set_editor_property('relative_rotation',unreal.Rotator(pitch=rotation))
        c.set_collision_profile_name('NoCollision')
        c.set_custom_depth_stencil_value(253)
        c.set_render_custom_depth(False)
        if material:
            index=next((i for i,s in enumerate(model.static_materials)
                        if str(s.get_editor_property('imported_material_slot_name'))=='Wheel'),0)
            c.set_material(index,load(material))
        return c
    mirror=(1,-front_sign,1)
    mesh('Body',models['Manifold'],(0.,0.,0.),mirror)
    mesh('Placards',models['Placards'],(0.,0.,0.),mirror).set_cast_shadow(False)
    mesh('Selector',models['Selector'],LOCAL,mirror,rotation=-35.)
    mesh('Drain',models['Handwheel'],DRAIN,mirror)
    mesh('Feed',models['Handwheel'],FEED,mirror,material=COLOR['Pipe'])
    mesh('Needle',models['Needle'],GAUGE,mirror,rotation=-128.)
    water=mesh('Flow',models['WaterStream'],TAP)
    water.set_visibility(False)
    cube=load('/Engine/BasicShapes/Cube')
    mesh('Lamp',cube,(-106.,-39.,177.),(.30,.042,.055),RED)
    marker=mesh('ServiceLamp',cube,(0.,-26.,253.),(.27,.037,.033),AMBER)
    marker.set_cast_shadow(False)
    blocker=add(bp,unreal.BoxComponent,'PumpManifoldBlock','PumpSite')
    blocker.set_editor_property('relative_location',V(0.,3.,58.))
    blocker.set_box_extent(V(145.,43.,59.))
    blocker.set_collision_profile_name('BlockAll')
    blocker.set_hidden_in_game(True)
    lamp=add(bp,unreal.PointLightComponent,'PumpServiceLight','PumpSite')
    lamp.set_editor_property('relative_location',V(0.,-100.,250.))
    lamp.set_light_color(unreal.LinearColor(.84,.90,1.,1.))
    lamp.set_intensity(840)
    lamp.set_attenuation_radius(340.)
    lamp.set_cast_shadows(False)

    old_labels=('PumpName','PumpInstructions','PumpLocalMarker','PumpDrainMarker','PumpFeedMarker','PumpTapMarker')
    for _,old,name in components(bp):
        if name in old_labels:
            old.set_visibility(False)
    return front_sign

def component(g,name):
    return g.get('Pump'+name)

def depth(g,name,on):
    g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=component(g,name),bValue=on))

def paint(g,name,mat):
    g.do(g.call('Engine.PrimitiveComponent.SetMaterial',target=component(g,name),ElementIndex=0,Material=mat))

def rotate(g,name,pitch):
    g.do(g.call('Engine.SceneComponent.K2_SetRelativeRotation',target=component(g,name),
        NewRotation=g.math('MakeRotator',Pitch=pitch,Yaw=0.,Roll=0.),bSweep=False,bTeleport=True))

def listen(g,name):
    g.do(g.own('EvacFocusPump'+name))
    return g.get('EvacFocus')

def world_sound(g,path,point,gain=.45):
    g.do(g.call('Engine.GameplayStatics.PlaySoundAtLocation',Sound=path,Location=L(at(point)),
                VolumeMultiplier=gain,AttenuationSettings='/Game/LabTutorial/Industrial/SA_BlastDoor'))

def objective(g,text,target):
    g.pset('StoryGoalActive',True,'Bool')
    g.set('Objective',text)
    g.set('GoalPoint',L(target))
    g.pset('StoryGoal',L(target),'Vector')
    g.pset('StoryGoalName',text,'String')

def service_status(g,stage):
    g.set('PumpStage',stage)
    depth(g,'Selector',stage==1)
    depth(g,'Drain',stage==2)
    depth(g,'Feed',stage==2 or stage==3)
    paint(g,'Lamp',RED if stage==1 else (GREEN if stage==4 else AMBER))
    if stage>1:
        rotate(g,'Selector',35.)
    if stage>=3:
        rotate(g,'Drain',430.)
    if stage==4:
        rotate(g,'Feed',-510.)
        rotate(g,'Needle',106.)
        g.visibility('PumpFlow',True)
        paint(g,'ServiceLamp',GREEN)

def use(bp):
    g=Story(bp,'PumpUse')
    for stage,key in ((1,'Selector'),(2,'Drain'),(3,'Feed')):
        active=g.branch(g.compare('EqualEqual',g.get('PumpStage'),stage))
        wanted=g.branch(listen(g,key))
        if stage==1:
            world_sound(g,CLICK,LOCAL,.55)
            service_status(g,2)
        else:
            g.branch(g.not_(g.get('PumpTurning')))
            g.set('EvacFHeld',True)
            g.set('PumpTurning',True)
            g.set('PumpLastTurn',g.now())
            world_sound(g,CLICK,DRAIN if stage==2 else FEED,.31)
            if stage==2:
                g.cursor=wanted.find_else_pin()
                g.branch(listen(g,'Feed'))
                g.branch(g.num('GreaterEqual',g.now(),g.get('PumpErrorUntil')))
                g.set('PumpErrorUntil',g.num('Add',g.now(),3.))
                world_sound(g,START,FEED,.33)
        g.cursor=active.find_else_pin()

def spin(g,name,fraction,sign):
    rotate(g,name,g.num('Multiply',fraction,sign))

def tick_valve(bp,stage,name,field,turn,target):
    g=Story(bp,'PumpTurn'+name)
    g.branch(g.get('PumpTurning'))
    keep=g.branch(g.both(g.get('EvacFHeld'),listen(g,name)))
    g.cursor=keep.find_else_pin()
    g.set('PumpTurning',False)
    g.cursor=keep.find_then_pin()
    step=g.math('FMin',A=.18,B=g.num('Subtract',g.now(),g.get('PumpLastTurn')))
    g.set(field,g.math('FMin',A=1.,B=g.num('Add',g.get(field),g.num('Multiply',step,WHEEL_RATE))))
    g.set('PumpLastTurn',g.now())
    spin(g,name,g.get(field),turn)
    g.branch(g.num('GreaterEqual',g.get(field),1.))
    g.set('PumpTurning',False)
    service_status(g,stage+1)
    world_sound(g,CLICK if stage==2 else START,target)
    if stage==3:
        g.set('EvacuationMilestone',SAVED)
        g.do(g.own('EvacSave'))

def tick(bp):
    g=Story(bp,'PumpTick')
    g.branch(player_outside(g))
    g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=g.get('StoryHUD'),
                PropertyName='ShelterChapter',Value=TITLE))
    start=g.branch(g.compare('EqualEqual',g.get('PumpStage'),0))
    service_status(g,1)
    g.cursor=start.find_else_pin()
    for stage in (1,2,3,4):
        active=g.branch(g.compare('EqualEqual',g.get('PumpStage'),stage))
        if stage==1:
            # Two waypoints keep the player on the connected main street and the service entrance.
            reached=g.branch(g.near(EXIT,420.))
            g.set('PumpPassedStreet',True)
            approach=g.node(g.e.add_branch_node())
            val(approach.find_condition_pin(),g.both(g.get('PumpPassedStreet'),g.near(ENTRY,530.)))
            link(g.cursor,approach.find_execute_pin())
            link(reached.find_else_pin(),approach.find_execute_pin())
            g.cursor=approach.find_then_pin()
            g.set('PumpPassedDoor',True)
            near=g.node(g.e.add_branch_node())
            val(near.find_condition_pin(),g.near(APPROACH,580.))
            link(g.cursor,near.find_execute_pin())
            link(approach.find_else_pin(),near.find_execute_pin())
            g.cursor=near.find_then_pin()
            g.set('PumpPassedDoor',True)
            g.set('PumpPassedStreet',True)
            focused=listen(g,'Selector')
            objective(g,g.select('F · перевести рубильник в «МЕСТНОЕ»',
                                  'Насосная · переведи управление на местный пульт',focused,'String'),at(LOCAL))
            g.cursor=near.find_else_pin()
            door=g.branch(g.get('PumpPassedDoor'))
            objective(g,'Водоканал · зайди к трубам справа от башни',APPROACH)
            g.cursor=door.find_else_pin()
            street=g.branch(g.get('PumpPassedStreet'))
            objective(g,'С городской улицы сверни под вывеску водоканала',ENTRY)
            g.cursor=street.find_else_pin()
            objective(g,'От поста выйди на главную улицу к водоканалу',EXIT)
        elif stage==2:
            g.do(g.own('PumpTurnDrain'))
            error=g.num('Less',g.now(),g.get('PumpErrorUntil'))
            rotate(g,'Needle',g.select(-98.,-128.,error,'Float'))
            objective(g,g.select('Давление уходит в слив · закрой красный вентиль',
                                  'Удерживай F на красном вентиле, чтобы перекрыть слив',error,'String'),at(DRAIN))
        elif stage==3:
            g.do(g.own('PumpTurnFeed'))
            angle=g.num('Add',-128.,g.num('Multiply',g.get('PumpFeedFraction'),234.))
            rotate(g,'Needle',angle)
            objective(g,'Удерживай F на синем вентиле до пуска подачи',at(FEED))
        else:
            g.set('Objective','Ручной режим · вода снова идёт по местной ветке')
            g.pset('StoryGoalActive',False,'Bool')
            # A failed disk write can be retried without replaying the repair.
            retry=g.branch(g.both(g.compare('Less',g.get('EvacuationSaved'),SAVED),
                                 g.num('GreaterEqual',g.now(),g.get('PumpRetryAt'))))
            g.set('PumpRetryAt',g.num('Add',g.now(),3.))
            g.do(g.own('EvacSave'))
        g.cursor=active.find_else_pin()

def restore(bp):
    g=Story(bp,'PumpRestore')
    g.branch(g.compare('EqualEqual',g.get('EvacuationMilestone'),SAVED))
    g.set('PumpDrainFraction',1.)
    g.set('PumpFeedFraction',1.)
    g.set('PumpTurning',False)
    service_status(g,4)
    finish_restore(g,L(APPROACH),90.)

def restore_previous(bp):
    # Saved milestone 6 includes the successful rescue. Reconcile its existing visual state first.
    g=Story(bp)
    g.e=G.get_graph_editor_by_name(bp,'Post12Restore')
    for node in g.e.list_all_nodes():
        if node.get_class().get_name()!='K2Node_IfThenElse':
            continue
        condition=node.find_condition_pin()
        incoming=list(condition.list_connected_pins())
        if len(incoming)!=1:
            continue
        compare=incoming[0].get_owning_node()
        number=next((p for p in compare.list_all_pins() if str(p.get_pin_name())=='B'),None)
        if number is None or str(number.get_pin_value())!='5':
            continue
        condition.break_pin_links()
        val(condition,g.compare('GreaterEqual',g.get('EvacuationMilestone'),5))
        return
    raise RuntimeError('Cannot find the original completed-rescue branch')

def dispatch(bp):
    def tick_entry(g,old,tag):
        sounded=g.both(g.num('LessEqual',g.get('Post12RadioAt'),0.),
                       g.num('GreaterEqual',g.now(),g.get('VisorRadioUntil')))
        active=g.branch(g.both(phase(g,RADIO_COMPLETE),g.math('BooleanOR',A=sounded,
                        B=g.compare('Greater',g.get('PumpStage'),0))))
        active.rename(tag)
        g.do(g.own('PumpTick'))
        for p in old:
            link(active.find_else_pin(),p)
    def use_entry(g,old,tag):
        active=g.branch(g.both(phase(g,RADIO_COMPLETE),g.compare('Greater',g.get('PumpStage'),0)))
        active.rename(tag)
        g.do(g.own('PumpUse'))
        for p in old:
            link(active.find_else_pin(),p)
    def restore_entry(g,old,tag):
        existing=next(n for n in g.e.list_all_nodes() if n.get_name()=='Post12RestoreDispatch')
        g.cursor=existing.find_then_pin()
        tails=list(g.cursor.list_connected_pins())
        g.cursor.break_pin_links()
        g.do(g.own('PumpRestore')).rename(tag)
        for p in tails:
            link(g.cursor,p)
        for p in old:
            link(g.e.find_graph_entry_pin(),p)
    insert_entry(bp,'Post12Tick','PumpDispatchTick',tick_entry)
    insert_entry(bp,'EvacUse','PumpDispatchUse',use_entry)
    insert_entry(bp,'ShelterTick','PumpDispatchRestore',restore_entry)

def install():
    bp=load(MISSION)
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert bp.get_outermost() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    rel=Path('Content')/(MISSION.removeprefix('/Game/')+'.uasset')
    backup=project/'Saved/Backups/WaterworksPump'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    copy=backup/rel
    copy.parent.mkdir(parents=True)
    shutil.copy2(project/rel,copy)
    mesh_backup=backup/'Content/Story/WaterworksPump'
    existing=project/'Content/Story/WaterworksPump'
    if existing.is_dir():
        shutil.copytree(existing,mesh_backup)

    models=meshes()
    front=hardware(bp,models)
    for key,kind,default in (
        ('Stage','int','0'),('PassedStreet','bool','false'),('PassedDoor','bool','false'),
        ('Turning','bool','false'),('LastTurn','real','0'),('ErrorUntil','real','0'),
        ('RetryAt','real','0'),('DrainFraction','real','0'),('FeedFraction','real','0'),
    ):
        var(bp,'Pump'+key,kind,default)
    for method in ('PumpUse','PumpTick','PumpTurnDrain','PumpTurnFeed','PumpRestore'):
        Story(bp,method)
    for name,point,span in (('Selector',LOCAL,14.),('Drain',DRAIN,22.),('Feed',FEED,22.)):
        focus(bp,'Pump'+name,at(point),span)
    compile_bp(bp)
    checkpoint_graphs(bp,SAVED)
    use(bp)
    tick_valve(bp,2,'Drain','PumpDrainFraction',430.,DRAIN)
    tick_valve(bp,3,'Feed','PumpFeedFraction',-510.,FEED)
    tick(bp)
    restore(bp)
    if not any(n.get_name()=='PumpDispatchRestore' for n in G.get_graph_editor_by_name(bp,'ShelterTick').list_all_nodes()):
        restore_previous(bp)
    dispatch(bp)
    compile_bp(bp)
    save(bp)
    report={'asset':MISSION,'backup':str(copy),'site':SITE,'approach':APPROACH,
            'controls':{name:at(point) for name,point in (('selector',LOCAL),('drain',DRAIN),('feed',FEED),('gauge',GAUGE))},
            'mesh_front_before_correction':front,'checkpoint':SAVED}
    output=project/'Saved/WaterworksPump'
    output.mkdir(exist_ok=True)
    (output/'Installed.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    unreal.log('WaterworksPump: Manual Mode installed and saved.')

if __name__=='__main__':
    install()
