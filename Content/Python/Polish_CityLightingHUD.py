"""Rebalance city lights and compact the live combat HUD in the Unreal Editor."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import shutil

import unreal

from Build_SciFiNight import MAPS, ROOT, actors, component, content, levels, saved
from CityCombat_Common import A, M, Graph, compile_bp, components, pin, save, val

PLAYER = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
VISOR = '/Game/Characters/PlayerVisor/WBP_PlayerVisor'
BODY = '/Game/LabTutorial/Basement/'
HUD_FONT = '/Game/Characters/PlayerVisor/Font_VisorLight'
ROBOTO = '/Engine/EngineFonts/Roboto'
MODULES = ('Head', 'Core', 'ArmL', 'ArmR', 'LegL', 'LegR')
COLOR = unreal.LinearColor


def tune_fog(fog):
    fog.modify()
    fog.set_editor_property('enable_volumetric_fog', True)
    fog.set_fog_density(0.010)
    fog.set_fog_max_opacity(0.36)
    fog.set_volumetric_fog_albedo(unreal.Color(r=103, g=119, b=144, a=255))
    fog.set_volumetric_fog_scattering_distribution(0.45)
    fog.set_volumetric_fog_extinction_scale(0.95)


def tune_post(post):
    settings = post.get_editor_property('settings')
    for key, value in (
        ('bloom_intensity', 0.40), ('bloom_threshold', 0.90),
        ('auto_exposure_bias', 0.90), ('color_gamma', unreal.Vector4(1.14, 1.14, 1.14, 1.0)),
    ):
        settings.set_editor_property('override_' + key, True)
        settings.set_editor_property(key, value)
    post.set_editor_property('settings', settings)


def lighting():
    grade = A.load_asset('/Game/Surface/BP_SciFi_CityGrade')
    for _, obj, name in components(grade):
        if name == 'CityFog':
            tune_fog(obj)
        if name == 'NightGrade':
            tune_post(obj)
    compile_bp(grade)
    save(grade)
    for variant, intensity in (('Cyan', 3.5), ('Magenta', 2.7), ('Amber', 3.0)):
        neon = A.load_asset(ROOT + '/MI_SciFi_Neon_' + variant)
        M.set_material_instance_scalar_parameter_value(neon, 'EmissiveIntensity', intensity)
        assert abs(M.get_material_instance_scalar_parameter_value(neon, 'EmissiveIntensity') - intensity) < 0.001
        save(neon)

    report = {}
    for name in MAPS:
        path = '/Game/Surface/' + name
        world = levels.load_map(path)
        assert world, path
        scene = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
        city_transform = scene['CITY_FirstDowntownBlock'].get_actor_transform()
        removed = []
        for label, actor in scene.items():
            if not isinstance(actor, unreal.PointLight):
                continue
            light = actor.get_component_by_class(unreal.PointLightComponent)
            tint = light.get_light_color()
            local = unreal.MathLibrary.inverse_transform_location(city_transform, actor.get_actor_location())
            cyan = tint.g > tint.r * 1.4 and tint.b > tint.r * 1.4
            pink = tint.r > tint.g * 1.5 and tint.b > tint.g * 1.5
            city_wash = local.y > 18000 and (cyan or pink) and light.intensity >= 500
            if (label.startswith('CITY_Night_') and label.endswith('_FogLight')) or city_wash:
                assert actors.destroy_actor(actor), label
                removed.append(label)
        sky = component(scene, 'SURF_SkyFill', unreal.SkyLight, unreal.SkyLightComponent, unreal.Vector())
        sky.set_intensity(0.85)
        sky.set_light_color(COLOR(0.48, 0.64, 0.95, 1))
        sky.recapture_sky()
        moon = scene['SURF_LateSun'].get_component_by_class(unreal.DirectionalLightComponent)
        moon.modify()
        moon.set_intensity(0.48)
        moon.set_light_color(COLOR(0.52, 0.65, 0.86, 1))
        moon.set_editor_property('volumetric_scattering_intensity', 3.0)
        if 'SURF_AshHaze' in scene:
            tune_fog(scene['SURF_AshHaze'].get_component_by_class(unreal.ExponentialHeightFogComponent))
        if 'SURF_SurfaceGrade' in scene:
            tune_post(scene['SURF_SurfaceGrade'])
        world.modify()
        assert levels.save_map(world, path)
        del world
        assert levels.load_map(path)
        after = {actor.get_actor_label() for actor in actors.get_all_level_actors()}
        assert not set(removed).intersection(after)
        assert sum(label.startswith('CITY_Night_') and label.endswith('_Neon') for label in after) == 6
        report[name] = removed

    body = A.load_asset(BODY + 'BP_CyborgBodyLight')
    fill = next(obj for _, obj, name in components(body) if name == 'BodyFill')
    fill.set_intensity(320.0)
    fill.set_attenuation_radius(520.0)
    compile_bp(body)
    save(body)
    for name, rgb in (('M_CyborgBodyLight', (0.08, 1.4, 2.1)), ('M_CyborgGlowShell', (0.04, 0.15, 0.22))):
        material = A.load_asset(BODY + name)
        [emission] = [expr for expr in unreal.ObjectIterator(unreal.MaterialExpressionConstant3Vector)
                      if expr.get_outer() == material]
        emission.set_editor_property('constant', COLOR(*rgb, 1))
        M.recompile_material(material)
        save(material)
    return report


def canvas_font():
    font = A.load_asset(HUD_FONT) if A.does_asset_exist(HUD_FONT) else A.duplicate_asset(ROBOTO, HUD_FONT)
    composite = font.get_editor_property('composite_font')
    data = composite.export_text()
    assert 'RobotoRegular' in data or 'RobotoLight' in data, data[:300]
    if 'RobotoRegular' in data:
        assert composite.import_text(data.replace('RobotoRegular', 'RobotoLight'))
    font.set_editor_property('composite_font', composite)
    save(font)
    return font.get_path_name()


def arg(g, name):
    return pin(g.e.find_graph_entry_pin().get_owning_node(), name, True)


def plus(g, a, b):
    return g.math('Add_DoubleDouble', A=a, B=b)


def minus(g, a, b):
    return g.math('Subtract_DoubleDouble', A=a, B=b)


def mul(g, a, b):
    return g.math('Multiply_DoubleDouble', A=a, B=b)


def rgba(r, g, b, a=1):
    return f'(R={r},G={g},B={b},A={a})'


CYAN = rgba(.39, .83, .94, .92)
WHITE = rgba(.76, .88, .92, .94)
MUTED = rgba(.51, .66, .71, .77)
RED = rgba(1, .16, .19, .90)
GLASS = rgba(.025, .08, .115, .26)
TRACK = rgba(.13, .25, .30, .22)


def text(g, font, label, x, y, tint, size):
    g.do(g.call('Engine.HUD.DrawText', target=g.get('ModeCanvasHUD'), Text=label,
                TextColor=tint, ScreenX=x, ScreenY=y, Font=font,
                Scale=mul(g, g.get('ModeUIScale'), size), bScalePosition=False))


def rect(g, x, y, w, h, tint):
    g.do(g.call('Engine.HUD.DrawRect', target=g.get('ModeCanvasHUD'), RectColor=tint,
                ScreenX=x, ScreenY=y, ScreenW=w, ScreenH=h))


def build_threats(bp, font):
    g = Graph(bp, 'Modes_DrawOneThreat')
    enemy = arg(g, 'Enemy')
    g.branch(g.valid(enemy))
    lifespan = g.out(g.call('Engine.Actor.GetLifeSpan', target=enemy))
    g.branch(g.math('LessEqual_DoubleDouble', A=lifespan, B=0.0))
    distance = g.out(g.call('Engine.Actor.GetDistanceTo', OtherActor=enemy))
    g.branch(g.math('Less_DoubleDouble', A=distance, B=4000.0))
    cam = g.out(g.call('Engine.GameplayStatics.GetPlayerCameraManager', PlayerIndex=0))
    eye = g.out(g.call('Engine.PlayerCameraManager.GetCameraLocation', target=cam))
    g.branch(g.out(g.call('Engine.Controller.LineOfSightTo', target=g.pc(), Other=enemy,
                          ViewPoint=eye, bAlternateChecks=False)))
    bounds = g.do(g.call('Engine.Actor.GetActorBounds', target=enemy, bOnlyCollidingComponents=True))
    center = g.call('Engine.KismetMathLibrary.BreakVector', InVec=g.out(bounds, 'Origin'))
    extent = g.call('Engine.KismetMathLibrary.BreakVector', InVec=g.out(bounds, 'BoxExtent'))
    anchor = g.math('MakeVector', X=g.out(center, 'X'), Y=g.out(center, 'Y'),
                    Z=plus(g, g.out(center, 'Z'), plus(g, g.out(extent, 'Z'), 18.0)))
    projected = g.do(g.call('Engine.PlayerController.ProjectWorldLocationToScreen', target=g.pc(),
                            WorldLocation=anchor, bPlayerViewportRelative=True))
    g.branch(g.out(projected))
    screen = g.call('Engine.KismetMathLibrary.BreakVector2D', InVec=g.out(projected, 'ScreenLocation'))
    x, y = (g.out(screen, axis) for axis in ('X', 'Y'))
    for axis, maximum, margin in ((x, g.get('ModeScreenW'), 36.), (y, g.get('ModeScreenH'), 26.)):
        g.branch(g.math('BooleanAND', A=g.math('Greater_DoubleDouble', A=axis, B=margin),
                        B=g.math('Less_DoubleDouble', A=axis, B=minus(g, maximum, margin))))
    ring = '/Game/Combat/CyborgModes/M_ThreatRing.M_ThreatRing'
    g.do(g.call('Engine.HUD.DrawMaterial', target=g.get('ModeCanvasHUD'), Material=ring,
                ScreenX=minus(g, x, 6.), ScreenY=minus(g, y, 6.), ScreenW=12., ScreenH=12.,
                MaterialU=0., MaterialV=0., MaterialUWidth=1., MaterialVHeight=1.,
                Scale=1., bScalePosition=False))
    g.count('ModeDetectedCount')
    # Reserve text for nearby threats and retain a small marker for distant enemies.
    g.branch(g.math('Less_DoubleDouble', A=distance, B=1800.))
    text(g, font, 'УГРОЗА', minus(g, x, mul(g, g.get('ModeUIScale'), 59.)), minus(g, y, 23.), RED, 1.55)


def build_panel(bp, font):
    g = Graph(bp, 'Modes_DrawHUD')
    canvas, width, height = (arg(g, name) for name in ('HUD', 'Width', 'Height'))
    ignored = g.out(g.call('Engine.Controller.IsMoveInputIgnored', target=g.pc()))
    g.branch(g.math('Not_PreBool', A=ignored))
    g.set('ModeCanvasHUD', canvas)
    g.set('ModeScreenW', width)
    g.set('ModeScreenH', height)
    scale = g.math('Divide_DoubleDouble', A=g.get('ModeScreenH'), B=900.)
    g.set('ModeUIScale', mul(g, g.math('FClamp', Value=scale, Min=.8, Max=1.4), .5))
    g.count('ModeHUDFrames')
    g.set('ModeDetectedCount', 0)
    u = g.get('ModeUIScale')
    x, top, w, h = mul(g, u, 26.), mul(g, g.get('ModeScreenH'), .22), mul(g, u, 294.), mul(g, u, 62.)
    text(g, font, 'БОЕВЫЕ ПРОТОКОЛЫ', x, minus(g, top, mul(g, u, 32.)), CYAN, 1.70)
    for i, label in enumerate(('СКОРОСТЬ', 'ОХОТНИК', 'АТОМНОЕ КРУШЕНИЕ', 'НЕЙРОКОНТРОЛЬ ×')):
        y = plus(g, top, mul(g, u, i * 79.))
        chosen = g.math('EqualEqual_IntInt', A=g.get('CyborgMode'), B=i)
        accent = g.math('SelectColor', A=CYAN, B=MUTED, bPickA=chosen)
        rect(g, x, y, w, h, GLASS)
        rect(g, x, y, mul(g, u, 3.), h, accent)
        text(g, font, str(i + 1), plus(g, x, mul(g, u, 14.)), plus(g, y, mul(g, u, 12.)), accent, 1.75)
        text(g, font, label, plus(g, x, mul(g, u, 51.)), plus(g, y, mul(g, u, 12.)),
             MUTED if i == 3 else WHITE, 1.72)
        g.do(g.call('Engine.HUD.AddHitBox', target=canvas, Position=g.math('MakeVector2D', X=x, Y=y),
                    Size=g.math('MakeVector2D', X=w, Y=h), InName='Mode' + str(i), bConsumesInput=True, Priority=10))
    text(g, font, '1–3  РЕЖИМ  /  TAB  КУРСОР', x, plus(g, top, mul(g, u, 320.)), MUTED, 1.40)
    atomic = g.math('EqualEqual_IntInt', A=g.get('CyborgMode'), B=2)
    speed = g.math('EqualEqual_IntInt', A=g.get('CyborgMode'), B=0)
    weapon = g.out(g.call('Engine.KismetMathLibrary.SelectString', A='ИМПУЛЬС  /  8 С', B='ЛАЗЕР  /  ЛКМ', bPickA=atomic))
    label = g.out(g.call('Engine.KismetMathLibrary.SelectString', A='ОРУЖИЕ ОТКЛЮЧЕНО', B=weapon, bPickA=speed))
    yy = plus(g, top, mul(g, u, 352.))
    text(g, font, label, x, yy, CYAN, 1.40)
    charge = minus(g, 1., g.math('FClamp', Value=g.math('Divide_DoubleDouble',
                   A=g.get('ProtocolCooldownRemaining'), B=8.), Min=0., Max=1.))
    rail = plus(g, yy, mul(g, u, 30.))
    rect(g, x, rail, w, 1., TRACK)
    rect(g, x, rail, mul(g, w, g.math('SelectFloat', A=charge, B=1., bPickA=atomic)), 1., CYAN)

    cx, cy = mul(g, g.get('ModeScreenW'), .5), mul(g, g.get('ModeScreenH'), .5)
    for dx, dy, ww, hh in ((-9, 0, 4, 1), (5, 0, 4, 1), (0, -9, 1, 4), (0, 5, 1, 4)):
        rect(g, plus(g, cx, dx), plus(g, cy, dy), ww, hh, CYAN)
    hp = g.math('FClamp', Value=g.math('Divide_DoubleDouble', A=g.get('VisorIntegrity'),
                B=g.math('FMax', A=g.get('VisorMaxIntegrity'), B=1.)), Min=0., Max=1.)
    floor = minus(g, g.get('ModeScreenH'), 20.)
    rect(g, x, floor, w, 1., TRACK)
    rect(g, x, floor, mul(g, w, hp), 1., g.math('SelectColor', A=RED, B=CYAN,
         bPickA=g.math('Less_DoubleDouble', A=hp, B=.25)))
    g.branch(g.get('bFirstPerson'))
    targets = g.do(g.call('Engine.GameplayStatics.GetAllActorsWithTag', Tag='CyborgHostile'))
    g.set('ModeTargets', g.out(targets, 'OutActors'))
    draw = g.own('Modes_DrawThreats')
    val(pin(draw, 'Index'), 0)
    g.do(draw)


def tune_visor():
    visor = A.load_asset(VISOR)
    tree = unreal.find_object(visor, 'WidgetTree')
    right_middle = unreal.Anchors(minimum=unreal.Vector2D(1., .5), maximum=unreal.Vector2D(1., .5))

    def place(name, x, y, width, height, align_y=0.):
        widget = unreal.find_object(tree, name)
        assert widget, name
        slot = widget.slot
        slot.set_anchors(right_middle)
        slot.set_alignment(unreal.Vector2D(0., align_y))
        slot.set_position(unreal.Vector2D(x, y))
        slot.set_size(unreal.Vector2D(width, height))
        return widget

    diagram = place('BodyDiagnostics', -153, 33.5, 120, 240, .5)
    diagram.set_color_and_opacity(COLOR(.82, .93, 1., .72))
    title = place('DiagnosticsTitle', -155, -82, 145, 12)
    title.set_text(unreal.Text('ДИАГНОСТИКА'))
    for index, name in enumerate(MODULES):
        x = -154 + (index % 2) * 66
        y = 153.5 + (index // 2) * 11.5
        place('Module' + name + 'Label', x, y, 47, 12)
        place('Module' + name + 'Value', x + 42, y, 23, 12)
        place('Module' + name + 'LED', x - 4, y + 2, 1, 5)
    root = unreal.find_object(tree, 'VisorCanvas')
    for index in range(root.get_children_count()):
        widget = root.get_child_at(index)
        name = widget.get_name()
        if isinstance(widget, unreal.TextBlock):
            font = widget.get_editor_property('font')
            font.set_editor_property('font_object', A.load_asset(HUD_FONT))
            font.set_editor_property('typeface_font_name', 'Regular')
            size = font.get_editor_property('size')
            is_diagnostics = name == 'DiagnosticsTitle' or name.startswith('Module')
            font.set_editor_property('size', 9 if is_diagnostics else min(size, 10))
            widget.set_font(font)
        if isinstance(widget, unreal.ProgressBar):
            style = widget.get_editor_property('widget_style')
            bg = style.get_editor_property('background_image')
            bg.set_editor_property('tint_color', unreal.SlateColor(specified_color=COLOR(.03, .08, .12, .22)))
            style.set_editor_property('background_image', bg)
            widget.set_editor_property('widget_style', style)
        if isinstance(widget, unreal.Image) and name.startswith(('EnergyGap_', 'Meter')):
            widget.set_render_opacity(.32)
    compile_bp(visor)
    save(visor)


def main():
    assert not levels.get_dirty_map_packages()
    backup = saved / 'Backups/CityLightingHUD' / datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True, exist_ok=True)
    paths = [PLAYER, VISOR, '/Game/Surface/BP_SciFi_CityGrade',
             *[ROOT + '/MI_SciFi_Neon_' + v for v in ('Cyan', 'Magenta', 'Amber')],
             *[BODY + v for v in ('BP_CyborgBodyLight', 'M_CyborgBodyLight', 'M_CyborgGlowShell')]]
    for path in paths:
        shutil.copy2(content / (path.removeprefix('/Game/') + '.uasset'), backup)
    for name in MAPS:
        shutil.copy2(content / f'Surface/{name}.umap', backup)
    lab = content / 'Lvl_LabTutorial.umap'
    original_lab = hashlib.sha256(lab.read_bytes()).hexdigest()
    font = canvas_font()
    bp = A.load_asset(PLAYER)
    build_threats(bp, font)
    compile_bp(bp)
    build_panel(bp, font)
    compile_bp(bp)
    save(bp)
    tune_visor()
    removed = lighting()
    assert hashlib.sha256(lab.read_bytes()).hexdigest() == original_lab
    assert levels.load_map('/Game/Lvl_LabTutorial')
    (saved / 'city_lighting_hud.json').write_text(json.dumps({'removed': removed, 'font': font, 'backup': str(backup)}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
