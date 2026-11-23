"""Install the original pulse carbine and arc projector in the existing player Blueprint."""
from datetime import datetime
from pathlib import Path
import json
import shutil

import unreal
from Build_Firearms import (A, B, G, M, PLAYER, GunGraph, V, add, compile_bp,
                            components, load, pin, save, val, var)
from Install_InfimaFPS import route_hunter_graph

ROOT = '/Game/Combat/EnergyWeapons'
OLD = '/Game/Combat/Firearms'
CAPACITY = 30
ARC_INTERVAL = .10
ARC_DAMAGE = 32.
ARC_RANGE = 4700.
SWAPS = {
    'SM_Hunter_Carbine': 'SM_Hunter_PulseCarbine',
    'SM_Hunter_Magazine': 'SM_Hunter_PulsePack',
    'SM_Breaker_Railgun': 'SM_Breaker_ArcProjector',
    'SM_Breaker_Cell': 'SM_Breaker_ArcCell',
}
SOUNDS = ('S_Pulse_1','S_Pulse_2','S_Pulse_3','S_Arc_Engage','S_Arc_Sustain','S_Arc_Release')
BEAM_COMPONENTS = ('ArcCore','ArcSheath')
PALETTE = {
    'Ceramic': ((.32,.235,.135),.32,.51),
    'Steel': ((.16,.205,.23),.82,.38),
    'Graphite': ((.040,.055,.066),.65,.46),
    'Elastomer': ((.026,.032,.038),.08,.76),
    'Titanium': ((.21,.165,.10),.77,.49),
    'Ice': ((.09,1.6,2.9),0.,1.),
    'Violet': ((1.24,.29,3.55),0.,1.),
    'ArcCore': ((5.6,4.1,13.),0.,1.),
    'ArcSheath': ((.65,.052,3.7),0.,1.),
}

def pkg(name):
    return f'{ROOT}/{name}'

def import_file(source, stem, ext, options=None):
    if A.does_asset_exist(pkg(stem)):
        return load(pkg(stem))
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(source/(stem+ext)),destination_path=ROOT,
                           destination_name=stem,automated=True,save=False).items():
        task.set_editor_property(key,value)
    if options:
        task.set_editor_property('options',options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return load(pkg(stem))

def make_material(key, rgb, metal, rough):
    name = 'M_'+key
    if A.does_asset_exist(pkg(name)):
        return load(pkg(name))
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    emissive = key in ('Ice','Violet',*BEAM_COMPONENTS)
    if emissive:
        material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    if key=='ArcSheath':
        material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)

    color = M.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,-220,0)
    color.set_editor_property('constant',unreal.LinearColor(*rgb,1.))
    M.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR if emissive else
                                unreal.MaterialProperty.MP_BASE_COLOR)
    if not emissive:
        for value, prop in ((metal,unreal.MaterialProperty.MP_METALLIC),
                            (rough,unreal.MaterialProperty.MP_ROUGHNESS)):
            scalar = M.create_material_expression(material,unreal.MaterialExpressionConstant,-220,150)
            scalar.set_editor_property('r',value)
            M.connect_material_property(scalar,'',prop)
    M.recompile_material(material)
    save(material)
    return material

def import_assets(source, world):
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    mats = {key:make_material(key,*value) for key,value in PALETTE.items()}
    imported = {}
    for name in SWAPS.values():
        options=unreal.FbxImportUI()
        for key,value in dict(automated_import_should_detect_type=False,
                              mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                              import_materials=False,import_textures=False).items():
            options.set_editor_property(key,value)
        options.static_mesh_import_data.set_editor_property('combine_meshes',True)
        options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        mesh=import_file(source,name,'.fbx',options)
        for slot_index,slot in enumerate(mesh.static_materials):
            slot_name=str(slot.material_slot_name)
            key=next(key for key in mats if slot_name.casefold().startswith(key.casefold()))
            mesh.set_material(slot_index,mats[key])
        if name.endswith(('Carbine','Projector')):
            bounds=mesh.get_bounding_box()
            assert bounds.min.x < -25 and bounds.max.x > 55 and bounds.max.z > 15, (name,str(bounds))
        save(mesh)
        imported[name]=mesh
    for name in SOUNDS:
        wave=import_file(source,name,'.wav')
        if name=='S_Arc_Sustain':
            wave.set_editor_property('looping',True)
        save(wave)
    return imported, mats

def nodes(bp, graph):
    return G.get_graph_editor_by_name(bp,graph).list_all_nodes()

def replace_defaults(bp, graph, pin_name, replacements, expected):
    count=0
    for node in nodes(bp,graph):
        target=next((item for item in node.list_input_pins()
                     if str(item.get_pin_name())==pin_name),None)
        if target is None or target.list_connected_pins():
            continue
        current=str(target.get_pin_value())
        if current in replacements:
            val(target,replacements[current])
            count+=1
    assert count==expected,(graph,pin_name,count)

def set_view(bp, meshes):
    replace_defaults(bp,'Atomic_Equip','NewMesh',
                     {f'{OLD}/{old}.{old}':meshes[new].get_path_name() for old,new in SWAPS.items()}, 8)
    replace_defaults(bp,'Atomic_Equip','B',{'90.0':91.2,'59.0':60.2},2)
    templates={name:c for _,c,name in components(bp)}
    # Preassign the new default mesh so both views start with matching materials and bounds.
    for view in ('FP','TP'):
        templates['Atomic'+view+'Gun'].set_static_mesh(meshes['SM_Hunter_PulseCarbine'])
        templates['Weapon'+view+'Magazine'].set_static_mesh(meshes['SM_Hunter_PulsePack'])
    templates['InfimaFPArms'].set_visibility(False,True)
    tick=GunGraph(bp,'Atomic_Update',keep=True)
    old_tick,=[n for n in tick.e.list_all_nodes() if str(n.get_node_title())=='Weapon_InfimaTick']
    tick.e.remove_nodes([old_tick])

    for graph, targets in (('Weapon_UpdateView',('AtomicFPGun','AtomicFPArms')),
                           ('Weapon_ViewMotion',('WeaponFPMagazine',))):
        g=GunGraph(bp,graph,keep=True)
        for name in targets:
            dest,=[n.find_input_pin('bNewVisibility') for n in g.e.list_all_nodes()
                   if n.find_input_pin('bNewVisibility').is_valid() and n.find_self_pin().is_valid()
                   and any(str(p.get_pin_name())==name for p in n.find_self_pin().list_connected_pins())]
            result,=dest.list_connected_pins()
            original,=result.get_owning_node().find_input_pin('A').list_connected_pins()
            dest.break_pin_links()
            val(dest,original)

    compile_bp(bp)
    route_hunter_graph(bp,'Laser_Fire',(('InfimaFPMuzzle','AtomicFPMuzzle'),('InfimaFPPort','WeaponFPPort')))
    route_hunter_graph(bp,'Lock_FireIfClear',(('InfimaFPMuzzle','AtomicFPMuzzle'),))
    replace_defaults(bp,'Laser_Fire','Sound',
                     {f'{OLD}/S_Hunter_Shot_{i}.S_Hunter_Shot_{i}':pkg(f'S_Pulse_{i}') for i in (1,2,3)},3)
    replace_defaults(bp,'Weapon_Reload','A',{'1':CAPACITY},1)
    replace_defaults(bp,'Weapon_DrawHUD','A',{'BREAKER  /  ИМПУЛЬС':'BREAKER  /  ЛУЧ',
                                            'ПАТРОНЫ / РЕЗЕРВ':'ЗАРЯД / РЕЗЕРВ'},2)
    replace_defaults(bp,'Weapon_DrawHUD','B',{'HUNTER  /  АВТО':'HUNTER  /  ОЧЕРЕДЬ x3'},1)
    # Reuse the existing support-hand reload animation and magazine accounting.
    g=GunGraph(bp,'Weapon_SeatBreaker')
    missing=g.math('Subtract_IntInt',A=CAPACITY,B=g.get('BreakerMagazine'))
    g.set('WeaponReloadAmount',g.math('Min',A=missing,B=g.get('BreakerReserve')))
    g.set('BreakerMagazine',g.math('Add_IntInt',A=g.get('BreakerMagazine'),B=g.get('WeaponReloadAmount')))
    g.set('BreakerReserve',g.math('Subtract_IntInt',A=g.get('BreakerReserve'),B=g.get('WeaponReloadAmount')))
    compile_bp(bp)

def fit_view(bp):
    replace_defaults(bp,'Modes_DrawHUD','A',{'ИМПУЛЬС  /  8 С':'ЛУЧ  /  УДЕРЖИВАЙ ЛКМ'},1)
    replace_defaults(bp,'Modes_DrawHUD','B',{'ЛАЗЕР  /  ЛКМ':'3 ИМПУЛЬСА  /  ЛКМ'},1)
    replace_defaults(bp,'Weapon_ViewMotion','A',{'-12.7':1.3},1)
    templates={name:c for _,c,name in components(bp)}
    templates['WeaponViewFill'].set_intensity(245.)
    templates['WeaponViewFill'].set_light_color(unreal.LinearColor(.84,.91,1.,1.))
    for name in ('WeaponFPMagazine','WeaponTPMagazine'):
        templates[name].set_editor_property('relative_location',V(17.5,0.,1.3))
    compile_bp(bp)


def install_components(bp, mats):
    for name in BEAM_COMPONENTS:
        component=add(bp,unreal.StaticMeshComponent,name,'CapsuleComponent')
        component.set_static_mesh(load('/Engine/BasicShapes/Cylinder'))
        component.set_material(0,mats[name])
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_collision_profile_name('NoCollision')
        component.set_editor_property('generate_overlap_events',False)
        component.set_cast_shadow(False)
        component.set_visibility(False)
    audio=add(bp,unreal.AudioComponent,'ArcLoop','CapsuleComponent')
    audio.set_sound(load(pkg('S_Arc_Sustain')))
    audio.set_auto_activate(False)
    audio.set_volume_multiplier(.62)
    audio.set_editor_property('attenuation_settings',load(OLD+'/ATT_Weapon'))
    for name,kind,default in (('HunterBurstLeft','int','0'),('WeaponTriggerDown','bool','false'),('ArcHeld','bool','false'),
                              ('ArcActive','bool','false'),('ArcImpact','Vector','(X=0,Y=0,Z=0)'),
                              ('ArcHits','int','0')):
        var(bp,name,B.get_struct_type(unreal.Vector.static_struct()) if kind=='Vector' else kind,default)
    compile_bp(bp)

def loaded(g, name):
    return g.math('Greater_IntInt',A=g.get(name),B=0)

def can_fire(g):
    idle=g.eq(g.get('WeaponReloadMode'),0)
    free=g.yes(g.no(g.get('bModeMenuOpen')),g.no(g.get('bAdminFlight')))
    no_map=g.no(g.out(g.call('Engine.Controller.IsMoveInputIgnored',target=g.pc())))
    return g.yes(idle,g.yes(free,g.yes(no_map,g.gt(g.get('VisorIntegrity'),0.))))

def hunter_burst(bp):
    g=GunGraph(bp,'Weapon_PulseTick')
    g.branch(loaded(g,'HunterBurstLeft'))
    allowed=g.yes(g.mode(1),g.yes(can_fire(g),loaded(g,'HunterMagazine')))
    valid=g.branch(allowed)
    g.cursor=valid.find_else_pin()
    g.set('HunterBurstLeft',0)
    g.cursor=valid.find_then_pin()
    g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('LaserNextFire')))
    g.do(g.own('Laser_Fire'))
    g.set('HunterBurstLeft',g.math('Subtract_IntInt',A=g.get('HunterBurstLeft'),B=1))
    compile_bp(bp)

    # Existing optional target-lock shots defer while a manual burst is playing.
    g=GunGraph(bp,'Lock_FireIfClear',keep=True)
    entry=g.e.find_graph_entry_pin()
    previous,=entry.list_connected_pins()
    entry.break_pin_links()
    g.cursor=entry
    g.branch(g.eq(g.get('HunterBurstLeft'),0))
    val(previous,g.cursor)
    compile_bp(bp)

def emit_sound(g,name,muzzle,gain):
    g.shot_sound(pkg(name),muzzle,gain)

def arc_graphs(bp):
    g=GunGraph(bp,'Weapon_ArcStop')
    g.set('ArcHeld',False)
    g.branch(g.get('ArcActive'))
    g.set('ArcActive',False)
    for name in BEAM_COMPONENTS:
        g.visibility(name,False)
    g.do(g.call('Engine.AudioComponent.Stop',target=g.get('ArcLoop')))
    loc=g.pick('Vector',g.loc('AtomicFPMuzzle'),g.loc('AtomicTPMuzzle'),g.get('bFirstPerson'))
    emit_sound(g,'S_Arc_Release',loc,.52)
    compile_bp(bp)

    g=GunGraph(bp,'Protocol_Fire')
    g.branch(g.mode(2))
    g.branch(can_fire(g))
    g.branch(loaded(g,'BreakerMagazine'))
    g.set('ArcHeld',True)
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_ArcTick')
    g.branch(g.get('ArcHeld'))
    allowed=g.yes(g.mode(2),g.yes(can_fire(g),loaded(g,'BreakerMagazine')))
    active=g.branch(allowed)
    g.cursor=active.find_else_pin()
    g.do(g.own('Weapon_ArcStop'))
    g.cursor=active.find_then_pin()

    camera=g.view()
    eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=camera))
    rotation=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=camera))
    forward=g.math('GetForwardVector',InRot=rotation)
    muzzle=g.pick('Vector',g.loc('AtomicFPMuzzle'),g.loc('AtomicTPMuzzle'),g.get('bFirstPerson'))

    def trace(start,end):
        result=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=start,End=end,
                            TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
        return result,g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(result,'OutHit'))

    maximum=g.va(eye,g.vm(forward,ARC_RANGE))
    aim,aim_hit=trace(eye,maximum)
    point=g.pick('Vector',g.out(aim_hit,'ImpactPoint'),maximum,g.out(aim))
    near,near_hit=trace(eye,muzzle)
    near_point=g.va(g.out(near_hit,'ImpactPoint'),g.vm(g.out(near_hit,'ImpactNormal'),2.))
    g.set('WeaponMuzzle',g.pick('Vector',near_point,muzzle,g.out(near)))
    origin=g.get('WeaponMuzzle')
    ray,ray_hit=trace(origin,g.va(point,g.vm(forward,3.)))
    g.set('ArcImpact',g.pick('Vector',g.out(ray_hit,'ImpactPoint'),point,g.out(ray)))

    delta=g.vs(g.get('ArcImpact'),origin)
    length=g.math('VSize',A=delta)
    center=g.vm(g.va(origin,g.get('ArcImpact')),.5)
    angle=g.math('MakeRotFromZ',Z=delta)
    wav=g.plus(1.,g.mul(g.math('Sin',A=g.mul(g.now(),46.)),.23))
    for name,width in (('ArcSheath',.021),('ArcCore',.013)):
        g.do(g.call('Engine.SceneComponent.K2_SetWorldLocationAndRotation',target=g.get(name),
                    NewLocation=center,NewRotation=angle,bSweep=False,bTeleport=True))
        size=g.mul(wav,width)
        g.do(g.call('Engine.SceneComponent.SetWorldScale3D',target=g.get(name),
                    NewScale=g.vec(size,size,g.div(length,100.))))

    first=g.branch(g.no(g.get('ArcActive')))
    g.set('ArcActive',True)
    for name in BEAM_COMPONENTS:
        g.visibility(name,True)
    g.do(g.call('Engine.AudioComponent.Play',target=g.get('ArcLoop'),StartTime=0.))
    emit_sound(g,'S_Arc_Engage',origin,.75)
    g.set('WeaponKick',1.12)
    connect=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.now(),B=g.get('ProtocolNextFire')))
    val(connect.find_execute_pin(),first.find_else_pin())
    g.set('ProtocolNextFire',g.plus(g.now(),ARC_INTERVAL))
    g.set('BreakerMagazine',g.math('Subtract_IntInt',A=g.get('BreakerMagazine'),B=1))
    g.set('WeaponKick',g.math('FMax',A=g.get('WeaponKick'),B=.24))
    g.count('ProtocolShots')
    g.branch(g.valid(g.out(ray_hit,'HitActor')))
    g.count('ArcHits')
    g.do(g.call('Engine.GameplayStatics.ApplyPointDamage',DamagedActor=g.out(ray_hit,'HitActor'),
                BaseDamage=ARC_DAMAGE,HitFromDirection=forward,HitInfo=g.out(ray,'OutHit'),
                EventInstigator=g.pc(),DamageCauser=g.self()))
    compile_bp(bp)

def wire_controls(bp):
    g=GunGraph(bp,'Modes_StartFire')
    g.gate()
    g.branch(g.no(g.get('WeaponTriggerDown')))
    g.set('WeaponTriggerDown',True)
    g.count('ModeTriggerPulls')
    g.do(g.own('Weapon_DryClick'))
    hunter=g.branch(g.mode(1))
    g.branch(can_fire(g))
    g.branch(loaded(g,'HunterMagazine'))
    g.branch(g.eq(g.get('HunterBurstLeft'),0))
    g.set('HunterBurstLeft',3)
    g.do(g.own('Weapon_PulseTick'))
    g.cursor=hunter.find_else_pin()
    g.do(g.own('Protocol_Fire'))
    compile_bp(bp)

    g=GunGraph(bp,'Modes_StopFire')
    g.set('WeaponTriggerDown',False)
    g.do(g.own('Weapon_ArcStop'))
    compile_bp(bp)

    g=GunGraph(bp,'Modes_Update',keep=True)
    old,=[n for n in g.e.list_all_nodes() if str(n.get_node_title())=='Modes_ApplyVisuals']
    # The old automatic-fire chain has no other callers.
    retire={'K2Node_VariableGet_1','K2Node_IfThenElse_2','K2Node_CallFunction_7','K2Node_CallFunction_8',
            'K2Node_IfThenElse_3','K2Node_CallFunction_9','K2Node_VariableSet_1'}
    g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_name() in retire])
    g.cursor=old.find_then_pin()
    assert not g.cursor.list_connected_pins(), 'Unexpected automatic-fire chain'
    g.do(g.own('Weapon_PulseTick'))
    compile_bp(bp)

    g=GunGraph(bp,'Atomic_Update',keep=True)
    motion,=[n for n in g.e.list_all_nodes() if str(n.get_node_title())=='Weapon_ViewMotion']
    g.cursor=motion.find_then_pin()
    assert not g.cursor.list_connected_pins()
    g.do(g.own('Weapon_ArcTick'))
    compile_bp(bp)

def main(source):
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    bp=load(PLAYER)
    if 'Weapon_ArcTick' in map(str,B.list_graph_names(bp)):
        raise RuntimeError('Energy weapon graph is already installed.')
    from_dir=Path(unreal.Paths.project_content_dir()).resolve()
    rel=Path(PLAYER.removeprefix('/Game/')+'.uasset')
    backup=Path(unreal.Paths.project_saved_dir()).resolve()/'Backups/EnergyWeapons'/datetime.now().strftime('%Y%m%d-%H%M%S')/rel
    backup.parent.mkdir(parents=True,exist_ok=False)
    shutil.copy2(from_dir/rel,backup)
    meshes,mats=import_assets(source,editor.get_editor_world())
    set_view(bp,meshes)
    fit_view(bp)
    install_components(bp,mats)
    hunter_burst(bp)
    arc_graphs(bp)
    wire_controls(bp)
    cd=unreal.get_default_object(B.generated_class(bp))
    for name,value in dict(BreakerMagazine=CAPACITY,BreakerReserve=150,LaserInterval=.083,
                           ProtocolCooldown=ARC_INTERVAL).items():
        cd.set_editor_property(name,value)
    compile_bp(bp)
    save(bp)
    out=Path(unreal.Paths.project_saved_dir())/'EnergyWeapons'
    out.mkdir(parents=True,exist_ok=True)
    (out/'Install.json').write_text(json.dumps({'saved':True,'backup':str(backup),'models':list(meshes),
                            'sounds':list(SOUNDS),'burst_rounds':3,'arc_charges':CAPACITY},indent=2),encoding='utf8')

if __name__=='__main__':
    main(Path(unreal.Paths.project_dir()).resolve()/'SourceAssets/EnergyWeapons')






