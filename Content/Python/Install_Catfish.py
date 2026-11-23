"""Install Jungle Jim's Catfish visuals on the existing Marauder encounter."""
from datetime import datetime
import json
import shutil

import unreal

from Build_RuinedUrbanCampus import A, B, V, add, components, content, save, saved, tools
from CityCombat_Common import compile_bp, link, pin
from CityMachine_Logic import Logic
from Industrial_Common import M
from SurfacePolish_Materials import import_file

MARAUDER='/Game/Enemies/CityMachines/BP_Marauder'
ROOT='/Game/Enemies/CityMachines/Catfish'
SOURCE=content.parent/'SourceAssets/CityMachines/Catfish'
HEIGHT=480.
HULL_LIFT=-244.


def native_material(name, root):
    path=root+'/'+name
    return A.load_asset(path) if A.does_asset_exist(path) else tools.create_asset(
        name,root,unreal.Material,unreal.MaterialFactoryNew())


def texture(file,kind,root,source):
    path=root+'/'+(source/file).stem
    if A.does_asset_exist(path):
        return A.load_asset(path)
    t=import_file(source/file,root)
    t.set_editor_property('srgb',kind in ('Base','Emissive'))
    t.set_editor_property('max_texture_size',1024)
    t.set_editor_property('never_stream',False)
    if kind=='Normal':
        t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
        t.set_editor_property('flip_green_channel',True)
    if kind=='ORM':
        t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    save(t)
    return t


def materials(spec,root=ROOT,source=SOURCE,stem='Catfish'):
    output={}
    for index,(slot,settings) in enumerate(spec.items()):
        name=f'M_{stem}_{index:02d}'
        path=root+'/'+name
        if A.does_asset_exist(path):
            output[slot.casefold()]=A.load_asset(path)
            continue
        m=native_material(name,root)
        M.delete_all_material_expressions(m)
        m.set_editor_property('used_with_skeletal_mesh',True)
        if not settings.get('Base'):
            glow=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-200,0)
            strength=settings['emission_strength']*.68
            glow.set_editor_property('constant',unreal.LinearColor(*(c*strength for c in settings['emissive']),1.))
            m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
            m.set_editor_property('two_sided',True)
            assert M.connect_material_property(glow,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        else:
            entries={}
            m.set_editor_property('two_sided',settings.get('two_sided',False))
            for k,sampler,y in (('Base',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,-200),
                                ('ORM',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,60),
                                ('Normal',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,370),
                                ('Emissive',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,580)):
                if k not in settings:
                    continue
                n=M.create_material_expression(m,unreal.MaterialExpressionTextureSample,-480,y)
                n.set_editor_property('texture',texture(settings[k],k,root,source))
                n.set_editor_property('sampler_type',sampler)
                entries[k]=n
            assert M.connect_material_property(entries['Base'],'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
            if 'Normal' in entries:
                assert M.connect_material_property(entries['Normal'],'RGB',unreal.MaterialProperty.MP_NORMAL)
            if 'ORM' in entries and settings.get('packed_occlusion',True):
                assert M.connect_material_property(entries['ORM'],'R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
            for key,mask,prop,y in (('roughness','G',unreal.MaterialProperty.MP_ROUGHNESS,80),
                                    ('metallic','B',unreal.MaterialProperty.MP_METALLIC,250)):
                if 'ORM' in entries:
                    factor=M.create_material_expression(m,unreal.MaterialExpressionMultiply,-180,y)
                    factor.set_editor_property('const_b',settings[key])
                    assert M.connect_material_expressions(entries['ORM'],mask,factor,'A')
                else:
                    factor=M.create_material_expression(m,unreal.MaterialExpressionConstant,-180,y)
                    factor.set_editor_property('r',settings[key])
                assert M.connect_material_property(factor,'',prop)
            if 'Emissive' in entries:
                tint=M.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-480,780)
                strength=settings['emission_strength']
                tint.set_editor_property('constant',unreal.LinearColor(*(c*strength for c in settings['emissive']),1.))
                emissive=M.create_material_expression(m,unreal.MaterialExpressionMultiply,-180,580)
                assert M.connect_material_expressions(entries['Emissive'],'RGB',emissive,'A')
                assert M.connect_material_expressions(tint,'',emissive,'B')
                assert M.connect_material_property(emissive,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        M.recompile_material(m)
        save(m)
        output[slot.casefold()]=m
    return output


def import_animated_mesh(root=ROOT,source=SOURCE,stem='Catfish'):
    A.make_directory(root)
    mesh_name='SK_'+stem
    path=root+'/'+mesh_name
    mesh=A.load_asset(path) if A.does_asset_exist(path) else None
    if not mesh or not mesh.skeleton:
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
        options=unreal.FbxImportUI()
        for key,value in dict(import_mesh=True,import_as_skeletal=True,import_animations=True,
                              import_materials=False,import_textures=False,create_physics_asset=False,
                              automated_import_should_detect_type=False,
                              mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH).items():
            options.set_editor_property(key,value)
        options.skeletal_mesh_import_data.set_editor_property('import_morph_targets',False)
        anim=options.anim_sequence_import_data
        anim.set_editor_property('use_default_sample_rate',True)
        task=unreal.AssetImportTask()
        for key,value in dict(filename=str(source/(stem+'.fbx')),destination_path=root,
                              destination_name=mesh_name,automated=True,save=False,options=options,
                              replace_existing=True,replace_existing_settings=True).items():
            task.set_editor_property(key,value)
        tools.import_asset_tasks([task])
        objects=[A.load_asset(name) for name in task.imported_object_paths]
        mesh=next(m for m in objects if isinstance(m,unreal.SkeletalMesh))
    clips=[a for p in A.list_assets(root,recursive=False,include_folder=False)
           if isinstance(a:=A.load_asset(p),unreal.AnimSequence)]
    assert len(clips)==1 and clips[0].get_play_length()>0.,clips
    assert mesh.skeleton and clips[0].get_editor_property('skeleton')==mesh.skeleton
    return mesh,clips[0]


def animation_graphs(bp,clip,stem='Catfish',stride_speed=455.,max_rate=1.64):
    body=stem+'Body'
    g=Logic(bp,'MachineInit')
    g.set('Home',g.position())
    g.set('Goal',g.addv(g.get('Home'),g.get('PointA')))
    tags=g.e.add_get_member_variable_node('Tags','/Script/Engine.Actor')
    for tag in ('CyborgHostile',stem):
        name=g.out(g.call('Engine.KismetSystemLibrary.MakeLiteralName',Value=tag))
        g.do(g.call('Engine.KismetArrayLibrary.Array_AddUnique',TargetArray=pin(tags,'Tags',True),NewItem=name))
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get(body),
                NewAnimToPlay=clip.get_path_name(),bLooping=True))
    for name in ('Muzzle','Sensor'):
        g.do(g.call('Engine.SceneComponent.K2_AttachToComponent',target=g.get(name),Parent=g.get(body),
            SocketName=stem+name,LocationRule='SnapToTarget',RotationRule='SnapToTarget',
            ScaleRule='KeepWorld',bWeldSimulatedBodies=False))
    compile_bp(bp)

    g=Logic(bp,'AnimateMachine')
    pos=g.position()
    look=g.select(g.get('LastPoint'),g.get('Goal'),g.get('HasSight'))
    direction=g.flatten(g.subv(look,pos))
    facing=g.math('MakeRotFromX',X=direction)
    current=g.out(g.call('Engine.Actor.K2_GetActorRotation'))
    rot=g.math('RInterpTo',Current=current,Target=facing,DeltaTime=g.dt(),InterpSpeed=3.15)
    have_heading=g.branch(g.num('Greater',g.math('VSize',A=direction),24.))
    g.do(g.call('Engine.Actor.K2_SetActorRotation',NewRotation=rot,bTeleportPhysics=False))
    displacement=g.distance(pos,g.get('BeforeMove'))
    speed=g.num('Divide',displacement,g.math('FMax',A=g.dt(),B=.001))
    rate=g.math('FClamp',Value=g.num('Divide',speed,stride_speed),Min=0.,Max=max_rate)
    set_rate=g.do(g.call('Engine.SkeletalMeshComponent.SetPlayRate',target=g.get(body),Rate=rate))
    link(have_heading.find_else_pin(),set_rate.find_execute_pin())
    compile_bp(bp)


def repair_assets(root=ROOT,source=SOURCE,stem='Catfish'):
    manifest=json.loads((source/'Manifest.json').read_text())
    mesh,clip=import_animated_mesh(root,source,stem)
    palette=materials(manifest['material_spec'],root,source,stem)
    normalized={''.join(c for c in name if c.isalnum()):material for name,material in palette.items()}
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.material_slot_name).casefold()
        material=palette.get(name) or normalized.get(''.join(c for c in name if c.isalnum()))
        assert material,(name,list(palette))
        slot.set_editor_property('material_interface',material)
    mesh.set_editor_property('materials',slots)
    save(mesh.skeleton)
    save(mesh)
    save(clip)
    return manifest,mesh,clip


def install():
    manifest,mesh,clip=repair_assets()
    bp=A.load_asset(MARAUDER)
    assert bp
    backup=saved/'Backups/Catfish'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    shutil.copy2(content/(MARAUDER.removeprefix('/Game/')+'.uasset'),backup)
    c=add(bp,unreal.SkeletalMeshComponent,'CatfishBody','Hull')
    c.set_skeletal_mesh_asset(mesh)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name('NoCollision')
    c.set_editor_property('can_ever_affect_navigation',False)
    c.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    scale=HEIGHT/(manifest['model_height']*100.)
    assert .6<scale<2.,scale
    c.set_editor_property('relative_scale3d',V((scale,)*3))
    c.set_editor_property('relative_location',V((0.,0.,HULL_LIFT)))
    c.override_animation_data(clip,True,False,0.,1.)
    cs={key:obj for _,obj,key in components(bp)}
    for key,info in (('Muzzle','muzzle'),('Sensor','sensor')):
        x,y,z=manifest[info]
        cs[key].set_editor_property('relative_location',V((x*scale*100.,-y*scale*100.,HULL_LIFT+z*scale*100.)))
    animation_graphs(bp,clip)
    for _,component,name in components(bp):
        if name in ('Chassis','Leg0','Leg1'):
            component.set_visibility(False)
            component.set_static_mesh(None)
    compile_bp(bp)
    save(bp)
    (saved/'Catfish/Install.json').write_text(json.dumps(dict(blueprint=MARAUDER,mesh=mesh.get_path_name(),
        animation=clip.get_path_name(),play_length=clip.get_play_length(),height_cm=HEIGHT,scale=scale,
        bounds=str(mesh.get_bounds()),backup=str(backup)),indent=2))


if __name__=='__main__':
    install()
