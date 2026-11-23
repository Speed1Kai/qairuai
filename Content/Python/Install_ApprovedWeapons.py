"""Install the approved Final Protocol weapon art and single-charge pulse."""
from datetime import datetime
import json
from pathlib import Path
import shutil

import unreal
from Build_Firearms import A, B, G, M, PLAYER, GunGraph, V, add, compile_bp, components, load, save
from Install_EnergyWeapons import can_fire, loaded, replace_defaults

ROOT = '/Game/Combat/ApprovedWeapons'
PREVIOUS = '/Game/Combat/EnergyWeapons'
MODELS = {
    'SM_Hunter_PulseCarbine': 'SM_Hunter_CrimsonCarbine',
    'SM_Hunter_PulsePack': 'SM_Hunter_CrimsonPack',
    'SM_Breaker_ArcProjector': 'SM_Atomic_DischargeEmitter',
    'SM_Breaker_ArcCell': 'SM_Atomic_DischargeCell',
}
FX = {
    'ArcCore': 'SM_Atomic_Filaments_0',
    'ArcSheath': 'SM_Atomic_Filaments_1',
    'AtomicMuzzleHalo': 'SM_Atomic_MuzzleHalo',
    'AtomicImpactHalo': 'SM_Atomic_ImpactHalo',
}
DISPLAY = {
    'AtomicDisplayReady': 'SM_Atomic_DisplayReady',
    'AtomicDisplayEmpty': 'SM_Atomic_DisplayEmpty',
}
SHOOT_SOUND = ROOT + '/S_Atomic_Discharge'
PULSE_VISUAL_SECONDS = .255
PULSE_DAMAGE = 128.0
PULSE_RANGE = 4700.0

def import_file(source, name, extension, options=None):
    path = ROOT + '/' + name
    if A.does_asset_exist(path):
        return load(path)
    task = unreal.AssetImportTask()
    for prop, value in dict(filename=str(source/(name+extension)), destination_path=ROOT,
                            destination_name=name, automated=True, save=False).items():
        task.set_editor_property(prop, value)
    if options:
        task.set_editor_property('options', options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return load(path)

def author_material(key, info, update=False):
    path = ROOT+'/M_'+key
    if A.does_asset_exist(path):
        m=load(path)
        if not update:
            return m
        M.delete_all_material_expressions(m)
    else:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_'+key, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    out = unreal.MaterialProperty
    glowing = 'emission' in info
    if glowing:
        m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        m.set_editor_property('two_sided',True)
    color = M.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -500, 0)
    rgb = list(info['color'])
    if glowing:
        rgb=[v*info['emission'] for v in rgb]
    color.set_editor_property('constant', unreal.LinearColor(*rgb,1.))
    if glowing:
        M.connect_material_property(color, '', out.MP_EMISSIVE_COLOR)
    else:
        verts = M.create_material_expression(m, unreal.MaterialExpressionVertexColor, -500, 160)
        mul = M.create_material_expression(m, unreal.MaterialExpressionMultiply, -220, 0)
        M.connect_material_expressions(color,'',mul,'A')
        M.connect_material_expressions(verts,'RGB',mul,'B')
        M.connect_material_property(mul,'',out.MP_BASE_COLOR)
        for prop, value in ((out.MP_METALLIC,info['metal']),(out.MP_ROUGHNESS,info['rough'])):
            num=M.create_material_expression(m,unreal.MaterialExpressionConstant,-220,170)
            num.set_editor_property('r',value)
            M.connect_material_property(num,'',prop)
    M.recompile_material(m)
    save(m)
    return m

def assets(source, world):
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    materials = {n:author_material(n,v) for n,v in json.loads((source/'materials.json').read_text()).items()}
    result = {}
    for name in (*MODELS.values(),*FX.values(),*DISPLAY.values()):
        options = unreal.FbxImportUI()
        for prop,value in dict(automated_import_should_detect_type=False,
                mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                import_materials=False,import_textures=False).items():
            options.set_editor_property(prop,value)
        data=options.static_mesh_import_data
        for prop,value in dict(combine_meshes=True,auto_generate_collision=False,
                               generate_lightmap_u_vs=False,vertex_color_import_option=unreal.VertexColorImportOption.REPLACE).items():
            data.set_editor_property(prop,value)
        mesh=import_file(source,name,'.fbx',options)
        assert isinstance(mesh,unreal.StaticMesh)
        for index,slot in enumerate(mesh.static_materials):
            key=str(slot.material_slot_name)
            assert key in materials,(name,key)
            mesh.set_material(index,materials[key])
        bounds=mesh.get_bounding_box()
        if name in ('SM_Hunter_CrimsonCarbine','SM_Atomic_DischargeEmitter'):
            assert bounds.min.x<-22 and bounds.max.x>58 and bounds.max.z>14,(name,str(bounds))
        if name.startswith('SM_Atomic_Filaments'):
            assert bounds.max.z>96 and bounds.min.z>-3,(name,str(bounds))
        save(mesh)
        result[name]=mesh
    sound=import_file(source,'S_Atomic_Discharge','.wav')
    assert sound.get_editor_property("duration")>.5
    save(sound)
    return result

def set_mesh(component, mesh):
    component.set_static_mesh(mesh)
    # The original weapon template had a material override on its first slot.
    component.set_editor_property('override_materials',[])
    component.set_collision_profile_name('NoCollision')
    component.set_editor_property('generate_overlap_events',False)

def setup_visuals(bp,meshes):
    replace_defaults(bp,'Atomic_Equip','NewMesh',
        {f'{PREVIOUS}/{old}.{old}':meshes[new].get_path_name() for old,new in MODELS.items()},8)
    cs={name:c for _,c,name in components(bp)}
    for view in ('FP','TP'):
        set_mesh(cs['Atomic'+view+'Gun'],meshes['SM_Hunter_CrimsonCarbine'])
        set_mesh(cs['Weapon'+view+'Magazine'],meshes['SM_Hunter_CrimsonPack'])
    for name,mesh in (*DISPLAY.items(),*FX.items()):
        c=cs.get(name)
        if c is None:
            parent='AtomicFPGun' if name in DISPLAY else 'CapsuleComponent'
            c=add(bp,unreal.StaticMeshComponent,name,parent)
        set_mesh(c,meshes[mesh])
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_visibility(False)
        c.set_cast_shadow(False)
        if name in DISPLAY:
            c.set_editor_property('only_owner_see',True)
            c.set_editor_property('relative_location',V())
    cs['WeaponViewFill'].set_intensity(315.)
    cs['WeaponViewFill'].set_attenuation_radius(170.)
    light=add(bp,unreal.PointLightComponent,'AtomicDischargeFlash','CapsuleComponent')
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_light_color(unreal.LinearColor(.10,.66,1.,1.))
    light.set_attenuation_radius(315.)
    light.set_intensity(1700.)
    light.set_editor_property("cast_shadows",False)
    light.set_visibility(False)
    compile_bp(bp)

def update_reload(bp):
    replace_defaults(bp,'Weapon_Reload','A',{'30':'1'},1)
    replace_defaults(bp,'Modes_DrawHUD','A',{'ЛУЧ  /  УДЕРЖИВАЙ ЛКМ':'РАЗРЯД  /  ЛКМ'},1)
    replace_defaults(bp,'Weapon_DrawHUD','A',{'BREAKER  /  ЛУЧ':'BREAKER  /  РАЗРЯД'},1)
    g=GunGraph(bp,'Weapon_SeatBreaker')
    g.branch(g.eq(g.get('BreakerMagazine'),0))
    g.branch(loaded(g,'BreakerReserve'))
    g.set('BreakerMagazine',1)
    g.set('BreakerReserve',g.math('Subtract_IntInt',A=g.get('BreakerReserve'),B=1))
    compile_bp(bp)

def fx_position(g,name,location,rot):
    return g.do(g.call('Engine.SceneComponent.K2_SetWorldLocationAndRotation',target=g.get(name),
                       NewLocation=location,NewRotation=rot,bSweep=False,bTeleport=True))

def fx_scale(g,name,xyz):
    return g.do(g.call('Engine.SceneComponent.SetWorldScale3D',target=g.get(name),NewScale=xyz))

def update_discharge(bp):
    g=GunGraph(bp,'Weapon_ArcStop')
    g.set('ArcHeld',False)
    g.set('ArcActive',False)
    for name in (*FX,'AtomicDischargeFlash'):
        g.visibility(name,False)
    compile_bp(bp)

    g=GunGraph(bp,'Protocol_Fire')
    g.branch(g.mode(2))
    g.branch(can_fire(g))
    g.branch(loaded(g,'BreakerMagazine'))
    # One cell launches one pulse. Release of the input leaves its visual decay intact.
    g.set('BreakerMagazine',0)
    g.set('AtomicLastShot',g.now())
    g.set('ProtocolNextFire',g.plus(g.now(),PULSE_VISUAL_SECONDS))
    g.count('ProtocolShots')
    camera=g.view()
    eye=g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation',target=camera))
    forward=g.math('GetForwardVector',InRot=g.out(g.call('Engine.PlayerCameraManager.GetCameraRotation',target=camera)))
    muzzle=g.pick('Vector',g.loc('AtomicFPMuzzle'),g.loc('AtomicTPMuzzle'),g.get('bFirstPerson'))

    def trace(start,end):
        shot=g.do(g.call('Engine.KismetSystemLibrary.LineTraceSingle',Start=start,End=end,
                         TraceChannel='TraceTypeQuery1',bTraceComplex=False,bIgnoreSelf=True,DrawDebugType='None'))
        hit=g.call('Engine.GameplayStatics.BreakHitResult',Hit=g.out(shot,'OutHit'))
        return shot,hit

    maximum=g.va(eye,g.vm(forward,PULSE_RANGE))
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
    angle=g.math('MakeRotFromZ',Z=delta)
    for name in ('ArcCore','ArcSheath'):
        fx_position(g,name,origin,angle)
        fx_scale(g,name,g.vec(1.,1.,g.div(length,100.)))
    fx_position(g,'AtomicMuzzleHalo',g.va(origin,g.vm(forward,8.)),angle)
    fx_position(g,'AtomicImpactHalo',g.va(g.get('ArcImpact'),g.vm(forward,-7.)),angle)
    fx_position(g,'AtomicDischargeFlash',origin,g.rot())
    fx_scale(g,'AtomicMuzzleHalo',g.vec(.43,.43,.43))
    fx_scale(g,'AtomicImpactHalo',g.vec(.29,.29,.29))
    g.visibility('ArcCore',True)
    g.visibility('ArcSheath',False)
    g.visibility('AtomicMuzzleHalo',True)
    g.visibility('AtomicImpactHalo',g.out(ray))
    g.visibility('AtomicDischargeFlash',True)
    g.set('ArcActive',True)
    g.set('WeaponKick',1.86)
    g.shot_sound(SHOOT_SOUND,origin,.94)
    g.branch(g.valid(g.out(ray_hit,'HitActor')))
    g.count('ArcHits')
    g.do(g.call('Engine.GameplayStatics.ApplyPointDamage',DamagedActor=g.out(ray_hit,'HitActor'),
            BaseDamage=PULSE_DAMAGE,HitFromDirection=forward,HitInfo=g.out(ray,'OutHit'),
            EventInstigator=g.pc(),DamageCauser=g.self()))
    compile_bp(bp)

    g=GunGraph(bp,'Modes_StopFire')
    g.set('WeaponTriggerDown',False)
    compile_bp(bp)

    g=GunGraph(bp,'Weapon_ArcTick')
    first=g.yes(g.mode(2),g.get('bFirstPerson'))
    charged=loaded(g,'BreakerMagazine')
    g.visibility('AtomicDisplayReady',g.yes(first,charged))
    g.visibility('AtomicDisplayEmpty',g.yes(first,g.no(charged)))
    g.branch(g.get('ArcActive'))
    age=g.minus(g.now(),g.get('AtomicLastShot'))
    alive=g.branch(g.yes(g.mode(2),g.gt(PULSE_VISUAL_SECONDS,age)))
    g.cursor=alive.find_else_pin()
    g.do(g.own('Weapon_ArcStop'))
    g.cursor=alive.find_then_pin()
    filament=g.gt(.101,age)
    alternate=g.gt(g.math('Sin',A=g.mul(age,143.)),0.)
    g.visibility('ArcCore',g.yes(filament,alternate))
    g.visibility('ArcSheath',g.yes(filament,g.no(alternate)))
    ramp=g.limit(g.div(age,PULSE_VISUAL_SECONDS))
    for name,start,end in (('AtomicMuzzleHalo',.39,1.71),('AtomicImpactHalo',.28,2.3)):
        scale=g.plus(start,g.mul(ramp,end-start))
        fx_scale(g,name,g.vec(scale,scale,scale))
    g.visibility('AtomicDischargeFlash',g.gt(.10,age))
    compile_bp(bp)

def install(source):
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    bp=load(PLAYER)
    present={name for _,_,name in components(bp)}
    assert set(FX).difference({'AtomicMuzzleHalo','AtomicImpactHalo'})<=present
    assert not set(DISPLAY)&present,'Approved weapon patch already present'
    rel=Path(PLAYER.removeprefix('/Game/')+'.uasset')
    saved=Path(unreal.Paths.project_saved_dir()).resolve()
    backup=saved/'Backups/ApprovedWeapons'/datetime.now().strftime('%Y%m%d-%H%M%S')/rel
    backup.parent.mkdir(parents=True,exist_ok=False)
    shutil.copy2(Path(unreal.Paths.project_content_dir()).resolve()/rel,backup)
    data=assets(source,editor.get_editor_world())
    setup_visuals(bp,data)
    update_reload(bp)
    update_discharge(bp)
    cd=unreal.get_default_object(B.generated_class(bp))
    for key,value in dict(BreakerMagazine=1,BreakerReserve=5,ProtocolCooldown=PULSE_VISUAL_SECONDS).items():
        cd.set_editor_property(key,value)
    compile_bp(bp)
    report={'blueprint':PLAYER,'backup':str(backup),'assets':list(data),'sound':SHOOT_SOUND,
            'charge_capacity':1,'reserve':5,'shot_duration':PULSE_VISUAL_SECONDS,'shot_damage':PULSE_DAMAGE}
    out=saved/'ApprovedWeapons'
    out.mkdir(parents=True,exist_ok=True)
    (out/'Install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return bp





if __name__ == "__main__":
    model_source = Path(unreal.Paths.project_dir()).resolve()/"SourceAssets/ApprovedWeapons"
    save(install(model_source))
