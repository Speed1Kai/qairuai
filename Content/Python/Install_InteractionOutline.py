"""Add the visible, contextual interaction contours to the first mission."""
from datetime import datetime
from pathlib import Path
import json
import shutil
import unreal

from CityCombat_Common import B, G, add, compile_bp, components, hook, save, val, var
from Install_StoryMemory import MISSION, Story, L, bp_asset, load
from Install_OwnFrequency import FIRST
from Shelter07_Waterworks import ASSETS as SHELTER_ASSETS, OUTLINES
from Install_StoryMemory import TERMINAL

ROOT = '/Game/Story/InteractionOutline'
MATERIAL = ROOT+'/M_InteractionOutline'
POWER = '/Game/LabTutorial/Basement/BP_BuildingPower'
LIFT = '/Game/LabTutorial/Elevator/BP_FreightElevatorBidirectional'
STATION = '/Game/Environment/CityService/BP_ServiceStation'
DEVICE, DOOR, LANDMARK = 253, 252, 251
PROJECT = Path(unreal.Paths.project_dir()).resolve()
OUT = PROJECT/'Saved/InteractionOutline'

SHADER = """
// Contour only outside the marked surface. CustomDepth supplies its occlusion depth.
if (CenterStencil.r >= 250.5 && CenterStencil.r <= 253.5 &&
    CenterCustomDepth.r <= CenterSceneDepth.r + 3.0)
{
    return SceneColor.rgb;
}
float2 uv = GetDefaultSceneTextureUV(Parameters, PPI_CustomStencil);
float2 step = PixelSize * 1.45;
float2 directions[4] = { float2(step.x, 0), float2(-step.x, 0),
                         float2(0, step.y), float2(0, -step.y) };
float strength = 0.0;
[unroll]
for (int i = 0; i < 4; ++i)
{
    float2 sampleUV = uv + directions[i];
    float stencil = SceneTextureLookup(sampleUV, PPI_CustomStencil, false).r;
    [branch]
    if (stencil >= 250.5 && stencil <= 253.5)
    {
        float edgeZ = SceneTextureLookup(sampleUV, PPI_CustomDepth, false).r;
        float sceneZ = SceneTextureLookup(sampleUV, PPI_SceneDepth, false).r;
        // Check both samples to avoid drawing through or over an occluding wall.
        if (edgeZ <= min(sceneZ, CenterSceneDepth.r) + max(3.5, edgeZ * 0.003))
        {
            float reach = stencil < 251.5 ? 4400.0 : (stencil < 252.5 ? 1200.0 : 680.0);
            float opacity = stencil < 251.5 ? 0.50 * smoothstep(700.0, 1100.0, edgeZ)
                                           : (stencil < 252.5 ? 0.81 : 0.96);
            strength = max(strength, opacity * (1.0 - smoothstep(reach * 0.65, reach, edgeZ)));
        }
    }
}
return lerp(SceneColor.rgb, float3(0.94, 0.98, 1.00), strength);
"""

def make_material():
    library = unreal.EditorAssetLibrary
    mel = unreal.MaterialEditingLibrary
    if library.does_asset_exist(MATERIAL):
        mat=load(MATERIAL)
        mel.delete_all_material_expressions(mat)
    else:
        mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_InteractionOutline',ROOT,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    custom=mel.create_material_expression(mat,unreal.MaterialExpressionCustom,20,0)
    custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property('code',SHADER)
    scenes = (
        ('SceneColor','PPI_POST_PROCESS_INPUT0','Color'),
        ('CenterStencil','PPI_CUSTOM_STENCIL','Color'),
        ('CenterCustomDepth','PPI_CUSTOM_DEPTH','Color'),
        ('CenterSceneDepth','PPI_SCENE_DEPTH','Color'),
        ('PixelSize','PPI_CUSTOM_STENCIL','InvSize'),
    )
    inputs=[]
    for name, _, _ in scenes:
        item=unreal.CustomInput()
        item.set_editor_property('input_name',name)
        inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    for i,(name,scene,output) in enumerate(scenes):
        tex=mel.create_material_expression(mat,unreal.MaterialExpressionSceneTexture,-320,i*118)
        tex.set_editor_property('scene_texture_id',getattr(unreal.SceneTextureId,scene))
        assert mel.connect_material_expressions(tex,output,custom,name),(name,scene,output)
    assert mel.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    save(mat)
    return mat

def meshes(bp):
    return {n:c for _,c,n in components(bp) if isinstance(c,unreal.StaticMeshComponent)}

def mark(mesh,stencil,visible):
    mesh.set_custom_depth_stencil_value(stencil)
    mesh.set_render_custom_depth(visible)

def tick(bp,method):
    compile_bp(bp)
    graph=G.get_graph_editor_by_name(bp,'EventGraph')
    tag='InteractionOutlineTick'
    if any(n.get_name()==tag for n in graph.list_all_nodes()):
        return
    event=graph.find_event_node('ReceiveTick')
    if not event:
        Story(bp).override('ReceiveTick')
        event=graph.find_event_node('ReceiveTick')
    source=event.find_then_pin()
    if source.list_connected_pins():
        hook(bp,source,method,tag)
    else:
        g=Story(bp);g.cursor=source
        g.do(g.own(method)).rename(tag)

def update_meshes(g,names,enabled):
    for name in names:
        g.do(g.call('Engine.PrimitiveComponent.SetRenderCustomDepth',target=g.get(name),bValue=enabled))

def power_and_lift():
    power=load(POWER)
    parts=meshes(power)
    names=('BreakerCabinet','BreakerFace','SwitchLever')
    for name in names:
        mark(parts[name],DEVICE,False)
    g=Story(power,'UpdateInteractionOutline')
    enabled=g.both(g.not_(g.get('bBuildingPowered')),g.not_(g.get('bRestoringPower')))
    update_meshes(g,names,enabled)
    tick(power,'UpdateInteractionOutline')
    compile_bp(power);save(power)
    lift=load(LIFT)
    parts=meshes(lift)
    door_parts=('LowerGateFrame','LowerGateLeft','LowerGateRight',
                'UpperGateFrame','UpperGateLeft','UpperGateRight')
    panels=('ControlPanel','OutsideCallPanel','UpperCallPanel')
    for name in ('CabFrontLeft','CabFrontRight','CabRearLeft','CabRearRight'):
        mark(parts[name],0,False)
    for name in door_parts:
        mark(parts[name],DOOR,False)
    for name in panels:
        mark(parts[name],DEVICE,False)
    g=Story(lift,'UpdateInteractionOutline')
    idle=g.compare('EqualEqual',g.get('LiftState'),0)
    update_meshes(g,door_parts+panels,idle)
    tick(lift,'UpdateInteractionOutline')
    compile_bp(lift);save(lift)
def proxy(bp,name,location,dimensions=None,template=None,rotation=None,scale=None):
    marker=add(bp,unreal.StaticMeshComponent,name,'Root')
    marker.set_static_mesh(template or load('/Engine/BasicShapes/Cube'))
    marker.set_editor_property('relative_location',unreal.Vector(*location))
    marker.set_editor_property('relative_scale3d',unreal.Vector(*scale) if scale else unreal.Vector(*[d/100 for d in dimensions]))
    marker.set_editor_property('relative_rotation',rotation or unreal.Rotator())
    marker.set_editor_property('render_in_main_pass',False)
    marker.set_editor_property('render_in_depth_pass',False)
    marker.set_cast_shadow(False)
    marker.set_collision_profile_name('NoCollision')
    marker.set_editor_property('can_ever_affect_navigation',False)
    mark(marker,DEVICE,False)

def install_story_outline(material):
    station=load(STATION)
    station_meshes=meshes(station)
    mark(station_meshes['Shell'],LANDMARK,True)
    compile_bp(station);save(station)
    bp=load(MISSION)
    # The computers in the station share an instance batch. Duplicate only the
    # active terminal silhouette into the custom-depth pass.
    terminal=load('/Game/Environment/CityService/SM_HackComputer')
    proxy(bp,'OutlineServiceTerminal',(TERMINAL[0],TERMINAL[1],2247),
          template=terminal,rotation=unreal.Rotator(yaw=90),scale=(1,1,1))
    for name,(position,dimensions) in OUTLINES.items():
        if name=='OutlineShelterLid':
            proxy(bp,name,position,template=load(SHELTER_ASSETS+'/Meshes/SM_S07_ExteriorHatch'),scale=(1,1,.42))
        else:
            proxy(bp,name,position,dimensions)
    pp=add(bp,unreal.PostProcessComponent,'InteractionOutlinePass','Root')
    pp.set_editor_property('unbound',True)
    pp.set_editor_property('priority',65.)
    pp.add_or_update_blendable(material,1.)
    groups = (
       (('ScannerPost','ScannerHead','ScannerLens'),1, None, None),
       (('OutlineServiceTerminal',),3,None,None),
       (('UplinkEnclosure','TrackingDisplay07','UplinkSpine','UplinkBeacon',
         'UplinkYagi0','UplinkYagi1','UplinkYagi2','UplinkYagi3','UplinkYagi4'),6,0,None),
       (('RadioReceiver','BroadcastDisplay07','RadioWhip'),6,1,None),
       (('LockBack','MedicalDisplay','ManualSwitch'),6,2,None),
       (('OutlineShelterLid',),6,None,1),
       (('OutlineTriageStation',),6,None,2),
       (('OutlineReserveBreaker',),6,None,3),
       (('OutlineShelterExit',),6,None,4),
    )
    existing=meshes(bp)
    for names, _, _, _ in groups:
        for name in names:
            mark(existing[name],DEVICE,False)
    mark(existing['StationIdentity'],DOOR,True)
    compile_bp(bp)
    g=Story(bp,'UpdateInteractionOutline')
    g.branch(g.valid(g.get('Player')))
    fail=g.not_(g.get('Failed'))
    outside=g.num('Greater',g.axis(g.position(g.get('Player')),'Z'),1950.)
    for names,stage,frequency,shelter in groups:
        condition=g.both(fail,g.isstage(stage))
        if frequency is not None:
            condition=g.both(condition,g.get('RecoveryGranted'))
            condition=g.both(condition,g.compare('EqualEqual',g.get('FrequencyStep'),frequency))
        if shelter is not None:
            active=g.compare('EqualEqual',g.get('ShelterStep'),shelter)
            if shelter==1:
                return_available=g.compare('GreaterEqual',g.get('ShelterStep'),2)
                active=g.math('BooleanOR',A=active,B=return_available)
                active=g.both(active,outside)
            else:
                active=g.both(active,g.not_(outside))
            condition=g.both(condition,active)
        update_meshes(g,names,condition)
    tick(bp,'UpdateInteractionOutline')
    compile_bp(bp);save(bp)

def install():
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    assets=(POWER,LIFT,STATION,MISSION,MATERIAL)
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert not dirty.intersection(assets),dirty.intersection(assets)
    backup=PROJECT/'Saved/Backups/InteractionOutline'/datetime.now().strftime('%Y%m%d_%H%M%S')
    for path in assets:
        relative=Path('Content')/(path[6:]+'.uasset')
        source=PROJECT/relative
        if source.exists():
            target=backup/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    OUT.mkdir(exist_ok=True)
    mat=make_material()
    power_and_lift()
    install_story_outline(mat)
    (OUT/'Installed.json').write_text(json.dumps({'assets':assets,'backup':str(backup)},indent=2))

if __name__=='__main__':
    install()

