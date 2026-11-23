import unreal, os, json

actors=unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    if a.get_actor_label() in ('REF_Atmosphere','REF_Exposure','REF_OpenGlassCanopy'):
        unreal.EditorLevelLibrary.destroy_actor(a)
pp=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector())
pp.set_actor_label('REF_Exposure'); pp.set_editor_property('unbound',True)
s=pp.get_editor_property('settings')
values={'auto_exposure_method':unreal.AutoExposureMethod.AEM_HISTOGRAM,
        'auto_exposure_min_brightness':5.0,'auto_exposure_max_brightness':5.0,
        'auto_exposure_bias':0.0,'bloom_intensity':.35,'vignette_intensity':.3}
for k,v in values.items():
    s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
pp.set_editor_property('settings',s)
fog=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.ExponentialHeightFog,unreal.Vector(0,0,60))
fog.set_actor_label('REF_Atmosphere')
f=fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
f.set_editor_property('fog_density',.014)
f.set_editor_property('fog_height_falloff',.25)
f.set_editor_property('fog_max_opacity',.4)
f.set_editor_property('start_distance',100.)
f.set_editor_property('enable_volumetric_fog',False)
f.set_editor_property('volumetric_fog_scattering_distribution',.25)
try:
    f.set_editor_property('fog_inscattering_color',unreal.LinearColor(r=.18,g=.29,b=.36,a=1.))
except Exception:
    pass
# Capsule canopy and first steps are authored together by Build_CapsuleIntro.py.
path='/Game/LabTutorial/ReferenceStyle/M_CanopyGlass'
lib=unreal.MaterialEditingLibrary
m=unreal.EditorAssetLibrary.load_asset(path)
if not m:
    m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_CanopyGlass','/Game/LabTutorial/ReferenceStyle',unreal.Material,unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(m)
m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('two_sided',True)
c=lib.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
c.set_editor_property('constant',unreal.LinearColor(r=.08,g=.24,b=.25,a=1))
lib.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
for value,prop in ((.16,unreal.MaterialProperty.MP_OPACITY),(.18,unreal.MaterialProperty.MP_ROUGHNESS)):
    n=lib.create_material_expression(m,unreal.MaterialExpressionConstant);n.set_editor_property('r',value)
    lib.connect_material_property(n,'',prop)
lib.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor.set_level_viewport_camera_info(unreal.Vector(250,-500,230),unreal.Rotator(pitch=-3,yaw=133,roll=0))
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    label=actor.get_actor_label()
    lc=actor.get_component_by_class(unreal.LightComponent)
    if lc:
        if label.startswith(('LAB_RedEmergency','LAB_Drone_Vision')):
            lc.set_light_color(unreal.LinearColor(r=1,g=.018,b=.008,a=1))
        elif label.startswith(('LAB_RouteMaintenance','LAB_Corridor_CeilingCrack')):
            lc.set_light_color(unreal.LinearColor(r=.48,g=.65,b=.7,a=1))
        elif label=='LAB_CyanProjector_Spot_Up':
            lc.set_light_color(unreal.LinearColor(r=.03,g=.7,b=.8,a=1))
        if label in ('REF_CeilingPool0','REF_PodInterior'):
            lc.set_cast_shadows(True)
    if label=='LAB_PlayerStart':
        actor.set_actor_location(unreal.Vector(-430,280,198),False,False)
        actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=45,roll=0),False)
    if isinstance(actor,unreal.TextRenderActor):
        tc=actor.get_component_by_class(unreal.TextRenderComponent)
        tc.set_text_render_color(unreal.Color(r=90,g=230,b=235,a=255))
        if label.startswith('LAB_Hologram_Text_'):
            actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=0),False)
unreal.EditorLoadingAndSavingUtils.save_current_level()
lines=[str(editor.get_level_viewport_camera_info())]
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if isinstance(a,unreal.PostProcessVolume): lines.append(a.get_actor_label()+': '+str(a.get_editor_property('settings')))
    if a.get_actor_label().startswith('LAB_') and a.get_component_by_class(unreal.LightComponent):
        c=a.get_component_by_class(unreal.LightComponent);lines.append(a.get_actor_label()+': '+str(c.get_editor_property('intensity')))
    if isinstance(a,unreal.Light): lines.append(a.get_actor_label()+' '+str(a.get_actor_location()))
with open(os.path.join(unreal.Paths.project_saved_dir(),'reference_verification.txt'),'w',encoding='utf8') as file: file.write('\n'.join(lines))
exec(compile(open(os.path.join(unreal.Paths.project_content_dir(),'Python/Verify_LabReference.py'),encoding='utf8').read(),'Verify_LabReference.py','exec'))
intro_script=os.path.join(unreal.Paths.project_content_dir(),'Python/Build_CapsuleIntro.py')
exec(compile(open(intro_script,encoding='utf8').read(),intro_script,'exec'),{'__name__':'__main__'})
hologram_script=os.path.join(unreal.Paths.project_content_dir(),'Python/Build_InteractiveHolograms.py')
if os.path.exists(hologram_script):
    exec(compile(open(hologram_script,encoding='utf8').read(),hologram_script,'exec'),{'__name__':'__main__'})
