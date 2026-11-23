
"""Polish the supplied shelter NPCs without altering their mission flow."""
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

import unreal

from Build_RiverForest import connect, constant, expr, output
from CityCombat_Common import A, G, compile_bp, components, link, save
from Install_StoryMemory import CITY, Story, load
import Install_ShelterMedic as medic

PROJECT=Path(unreal.Paths.project_dir()).resolve()
FEMALE='/Game/Characters/ShelterMedic'
MALE='/Game/Characters/ShelterResident'
RESIDENT=MALE+'/BP_ShelterResident'
EDITOR=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
U=unreal.EditorLoadingAndSavingUtils
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
M=unreal.MaterialEditingLibrary

# Tune the existing texture-based materials; preserve their normal and opacity inputs.
# Values are saturation, brightness, roughness interval, specular value.
MATERIALS={
    FEMALE+'/Materials/M_Std_Skin_Head':(.56,.87,(.50,.70),.235),
    FEMALE+'/Materials/M_Std_Skin_Body':(.68,.88,(.52,.70),.235),
    FEMALE+'/Materials/M_Std_Skin_Arm':(.70,.92,(.52,.70),.235),
    FEMALE+'/Materials/M_Std_Skin_Leg':(.70,.92,(.53,.73),.235),
    FEMALE+'/Materials/M_Std_Eye_L':(.84,.85,(.32,.41),.29),
    FEMALE+'/Materials/M_Std_Eye_R':(.84,.85,(.32,.41),.29),
    FEMALE+'/Materials/M_Std_Cornea_L':(.90,.89,(.33,.44),.28),
    FEMALE+'/Materials/M_Std_Cornea_R':(.90,.89,(.33,.44),.28),
    FEMALE+'/Materials/M_long_straight_Transparency':(.83,.82,(.58,.77),.24),
    FEMALE+'/Materials/M_scalp_long_straight_Transparency':(.83,.85,(.59,.77),.24),
    FEMALE+'/Materials/M_THD_Jacket_1SG':(.83,.90,(.57,.76),.27),
    FEMALE+'/Materials/M_THD_Jacket_1SG1':(.83,.90,(.57,.76),.27),
    MALE+'/Materials/M_S07_Head':(.80,.86,(.47,.69),.24),
    MALE+'/Materials/M_S07_Arms':(.81,.91,(.52,.72),.24),
    MALE+'/Materials/M_S07_Torso':(.81,.91,(.52,.72),.24),
    MALE+'/Materials/M_S07_Eye':(.82,.86,(.32,.43),.29),
    MALE+'/Materials/M_S07_Hair':(.76,.77,(.56,.75),.24),
    MALE+'/Materials/M_S07_Jacket':(.86,.90,(.54,.77),.27),
    MALE+'/Materials/M_S07_Backpack':(.76,.91,(.56,.76),.27),
}
MORPH_MALE=('eyeBlinkLeft','eyeBlinkRight')
MARK='S07PeopleLook'

def preserve(paths, work):
    f=work/'Backup.json'
    if f.exists():
        backup=Path(json.loads(f.read_text(encoding='utf8'))['backup'])
        assert backup.resolve().is_relative_to((PROJECT/'Saved/Backups/ShelterPeople').resolve())
    else:
        backup=PROJECT/'Saved/Backups/ShelterPeople'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        f.write_text(json.dumps({'backup':str(backup)}),encoding='utf8')
    for path in paths:
        part=Path('Content')/Path(path.removeprefix('/Game/')+'.uasset')
        target=backup/part
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            shutil.copy2(PROJECT/part,target)
    return backup

def fbx(file,destination,options,replace=False):
    p=destination+'/'+file.stem
    if A.does_asset_exist(p) and not replace:
        return load(p)
    t=unreal.AssetImportTask()
    for k,v in dict(filename=str(file),destination_path=destination,destination_name=file.stem,options=options,
                    automated=True,replace_existing=replace,replace_existing_settings=replace,save=False).items():
        t.set_editor_property(k,v)
    TOOLS.import_asset_tasks([t])
    assert t.get_editor_property('imported_object_paths'),file
    return load(p)

def opts(skeleton,mode):
    o=unreal.FbxImportUI()
    for k,v in dict(import_mesh=mode=='mesh',import_as_skeletal=True,import_animations=mode=='anim',
                    import_materials=False,import_textures=False,create_physics_asset=False,skeleton=skeleton,
                    automated_import_should_detect_type=False,mesh_type_to_import=(
                    unreal.FBXImportType.FBXIT_SKELETAL_MESH if mode=='mesh' else unreal.FBXImportType.FBXIT_ANIMATION)).items():
        o.set_editor_property(k,v)
    if mode=='mesh':
        data=o.skeletal_mesh_import_data
        data.set_editor_property('import_morph_targets',True)
        data.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        data.set_editor_property('update_skeleton_reference_pose',False)
    else:
        o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',True)
    return o

def radio_eyelids(work):
    skel=load(MALE+'/SK_S07_Resident_Skeleton')
    mesh=fbx(work/'SK_S07_Resident_Face.fbx',MALE,opts(skel,'mesh'))
    names={o.get_name() for o in mesh.get_editor_property('morph_targets')}
    assert set(MORPH_MALE)<=names,names
    slots=list(mesh.materials)
    assert len(slots)==12 and mesh.skeleton==skel
    for slot in slots:
        n=str(slot.get_editor_property('imported_material_slot_name')).removesuffix('_Mat')
        material=load(MALE+'/Materials/M_S07_'+n)
        if n in ('Head','Brows'):
            material.set_editor_property('used_with_morph_targets',True)
            save(material)
        slot.set_editor_property('material_interface',material)
    mesh.set_editor_property('materials',slots)
    save(mesh)
    save(skel)
    return mesh,skel,list(sorted(names))

def adjust(mat,name,code,tag):
    prop=getattr(unreal.MaterialProperty,'MP_'+name)
    old=M.get_material_property_input_node(mat,prop)
    if old and isinstance(old,unreal.MaterialExpressionCustom) and str(old.get_editor_property('description'))==tag:
        old.set_editor_property('code',code)
        return
    if not old:
        old=expr(mat,'Constant',r=.5)
    out=M.get_material_property_input_node_output_name(mat,prop)
    inp=unreal.CustomInput()
    inp.set_editor_property('input_name','C')
    kind=unreal.CustomMaterialOutputType.CMOT_FLOAT1 if name=='ROUGHNESS' else unreal.CustomMaterialOutputType.CMOT_FLOAT3
    n=expr(mat,'Custom',code=code,description=tag,inputs=[inp],output_type=kind)
    connect(old,n,'C',out)
    output(n,name)

def appearance():
    for path,(sat,gain,rough,spec) in MATERIALS.items():
        m=load(path)
        adjust(m,'BASE_COLOR',f'float l=dot(C.rgb,float3(.2126,.7152,.0722)); return lerp(l.xxx,C.rgb,{sat})*{gain};',
               MARK+'Color')
        adjust(m,'ROUGHNESS',f'return lerp({rough[0]},{rough[1]},saturate(C.r));',MARK+'Roughness')
        current=M.get_material_property_input_node(m,unreal.MaterialProperty.MP_SPECULAR)
        if isinstance(current,unreal.MaterialExpressionConstant):
            current.set_editor_property('r',spec)
        else:
            constant(m,'SPECULAR',spec)
        M.recompile_material(m)
        save(m)

def curve(anim,name,points):
    controller=anim.get_editor_property('controller')
    identifier=unreal.AnimationCurveIdentifier()
    identifier.set_curve_identifier(unreal.Name(name),unreal.RawCurveTrackTypes.RCT_FLOAT)
    assert identifier.is_valid(),name
    controller.add_curve(identifier,4,False)
    keys=[]
    for t,value in points:
        key=unreal.RichCurveKey()
        key.set_editor_property('interp_mode',unreal.RichCurveInterpMode.RCIM_LINEAR)
        key.set_editor_property('time',float(t))
        key.set_editor_property('value',float(value))
        keys.append(key)
    assert controller.set_curve_keys(identifier,keys,False),name

def blink(anim,name,times,shift=0.):
    length=anim.get_play_length()
    points=[(0.,0.)]
    for t in times:
        t+=shift
        if t+.19<length:
            points.extend([(t,0.),(t+.048,.98),(t+.072,.93),(t+.158,0.)])
    curve(anim,name,points+[(length,0.)])

def speech(anim,row):
    envelope=row['lip']
    ts=[t for t,v in envelope]
    rms=[v for t,v in envelope]
    end=anim.get_play_length()
    vowels=[s for s in row['text'].lower() if s in 'аоуыэяёюие']
    total=sum(rms)
    voiced_distance=0.
    motion={n:[] for n in ('Open','Wide','Tight','Dental_Lip')}
    for i,t in enumerate(ts):
        if t>=end:
            break
        voiced_distance+=rms[i]
        level=sum(rms[max(0,i-1):i+2])/len(rms[max(0,i-1):i+2])
        k=min(len(vowels)-1,int(voiced_distance/max(total,1e-6)*len(vowels)))
        letter=vowels[k]
        narrow=letter in 'оуёю'
        broad=letter in 'иеыэ'
        change=abs(rms[min(i+1,len(rms)-1)]-rms[max(i-1,0)])
        motion['Open'].append((t,level*(.60 if narrow or broad else .81)))
        motion['Wide'].append((t,level*(.32 if broad else .075)))
        motion['Tight'].append((t,level*(.27 if narrow else .04)))
        motion['Dental_Lip'].append((t,min(.14,change*.30) if level>.055 else 0.))
    for name,points in motion.items():
        curve(anim,name,points+[(end,0.)])

def play_radio(mesh,clip):
    bp=load(RESIDENT)
    body=next(obj for _,obj,name in components(bp) if name=='Body')
    body.set_skeletal_mesh_asset(mesh)
    body.override_animation_data(clip,True,True,0.,1.)
    compile_bp(bp)
    g=Story(bp,'StartRadioDuty')
    g.do(g.call('Engine.SkeletalMeshComponent.SetSkeletalMeshAsset',target=g.get('Body'),NewMesh=mesh.get_path_name()))
    g.do(g.call('Engine.SkeletalMeshComponent.PlayAnimation',target=g.get('Body'),
                NewAnimToPlay=clip.get_path_name(),bLooping=True))
    compile_bp(bp)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    if not any(n.get_name()=='S07RadioDutyBegin' for n in graph.list_all_nodes()):
        g=Story(bp)
        g.override('ReceiveBeginPlay')
        previous=list(g.cursor.list_connected_pins())
        g.cursor.break_pin_links()
        g.do(g.own('StartRadioDuty')).rename('S07RadioDutyBegin')
        for pin in previous:
            link(g.cursor,pin)
    compile_bp(bp)
    save(bp)

def install(work):
    assert not EDITOR.get_game_world() and not U.get_dirty_map_packages()
    world=EDITOR.get_editor_world()
    if world.get_path_name().split('.')[0]!=CITY:
        levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        assert levels.load_level(CITY)
        world=EDITOR.get_editor_world()
    backup=preserve((*MATERIALS,FEMALE+'/BP_ShelterMedic',RESIDENT,MALE+'/SK_S07_Resident',
        MALE+'/SK_S07_Resident_Skeleton',MALE+'/Materials/M_S07_Brows'),work)
    unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    resident_mesh,resident_skeleton,morphs=radio_eyelids(work)
    duty=fbx(work/'AN_S07_RadioDuty.fbx',MALE+'/Animations',opts(resident_skeleton,'anim'),True)
    assert abs(duty.get_play_length()-26.)<.06
    for i,name in enumerate(MORPH_MALE):
        blink(duty,name,(1.2,4.4,7.63,10.85,14.76,18.27,18.65,22.78,25.04),i*.009)
    save(duty)
    root=PROJECT/'SourceAssets/Shelter07/Medic'
    manifest=json.loads((root/'MedicAssets.json').read_text(encoding='utf8'))
    audio_timing={r['id']:r for r in json.loads((root/'SpeechMotion.json').read_text(encoding='utf8'))}
    skel=load(manifest['skeleton'])
    rest=fbx(work/'AN_Medic_NaturalRest.fbx',FEMALE+'/Animations',opts(skel,'anim'))
    blink(rest,'Eye_Blink',(1.6,4.02,7.85,11.09,11.46,14.3))
    save(rest)
    manifest['clip_paths']['Idle']=rest.get_path_name()
    for i,row in enumerate(manifest['rows']):
        clip=fbx(work/('AN_Medic_Natural'+row['id']+'.fbx'),FEMALE+'/Animations',opts(skel,'anim'))
        assert clip.get_play_length()>=row['duration']
        speech(clip,audio_timing[row['id']])
        blink(clip,'Eye_Blink',(1.31+i*.22,4.78+i*.50,8.13+i*.44,10.61+i*.34))
        save(clip)
        row['clip']=clip.get_path_name()
        manifest['clip_paths'][row['id']]=clip.get_path_name()
        manifest['lengths'][row['id']]=clip.get_play_length()
    manifest['lengths']['Idle']=rest.get_play_length()
    appearance()
    # The medic retains her original route, interaction focus and lines.
    medic.npc(manifest,-90.,0.,132.)
    play_radio(resident_mesh,duty)
    for folder,stem in ((FEMALE,'SK_S07_Medic'),(MALE,'SK_S07_Resident')):
        assert load(folder+'/'+stem).skeleton
    (work/'MedicAssets.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (work/'Installed.json').write_text(json.dumps({'passed':True,'backup':str(backup),'material_count':len(MATERIALS),
        'radio_clip':duty.get_path_name(),'radio_blink_shapes':morphs,'medic_clips':manifest['clip_paths']},indent=2),encoding='utf8')

if __name__=='__main__':
    install(PROJECT/'SourceAssets/Shelter07/People')
