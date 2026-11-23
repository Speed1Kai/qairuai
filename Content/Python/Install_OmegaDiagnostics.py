"""Author an offline, playable AI diagnostics panel and a defense entry point."""
import json
import shutil
from datetime import datetime
from itertools import product
from pathlib import Path

import unreal

from Install_StoryMemory import (
    A, B, G, MAIN, Story, bp_asset, compile_bp, defaults, link, load, pin, save, val, var,
)
import Archive_AuthoringHelpers as widget_tools

ROOT = "/Game/FrontEnd/OmegaDiagnostics"
PANEL = ROOT + "/WBP_OmegaDiagnostics"
SIM = ROOT + "/BP_OmegaDiagnostics"
MODE = ROOT + "/Lvl_OmegaDiagnostics"
MENU = "/Game/FrontEnd/Lvl_MainMenu"
PROJECT = Path(unreal.Paths.project_dir()).resolve()
WORK = PROJECT / "Saved/OmegaDiagnostics"
V2 = unreal.Vector2D

# Graph nodes and integer edge costs in meters. Each h is floor of straight-line distance.
NODES = (
    ("Станция 07", 60), ("Главная улица", 40), ("Насосный двор", 20),
    ("Служебный проход", 44), ("Водоканал", 28), ("Убежище 07", 0),
)
EDGES = (
    (0, 1, 20, None), (1, 2, 20, "StreetClosed"), (2, 5, 20, None),
    (0, 3, 30, "ServiceClosed"), (1, 3, 20, "ServiceClosed"),
    (3, 4, 20, None), (2, 4, 20, None), (4, 5, 32, None),
)
GOAL = len(NODES) - 1
INF = 9999
ROUTE_UNIT = " м"
INPUTS = (
    ("StreetClosed", "Закрыть главную улицу"),
    ("ServiceClosed", "Закрыть служебный путь"),
    ("LowCharge", "Низкий заряд дрона · 12 %"),
    ("Patrol", "Патруль на маршруте"),
    ("ReserveOff", "Отключить ввод Б"),
)
DYNAMIC = ("Agent", "Route", "Trace", "Power")


def text_ui():
    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property("parent_class", unreal.UserWidget)
    bp = load(PANEL) if A.does_asset_exist(PANEL) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        PANEL.rsplit("/", 1)[1], ROOT, unreal.WidgetBlueprint, factory)
    tree = unreal.find_object(bp, "WidgetTree")
    def widget(klass, name):
        item = unreal.find_object(tree, name) or unreal.new_object(klass, outer=tree, name=name)
        if isinstance(item, unreal.PanelWidget):
            item.clear_children()
        return item

    canvas = widget(unreal.CanvasPanel, "DiagnosticsCanvas")
    widget_tools.assign_object(tree, "RootWidget", canvas)
    canvas.set_visibility(unreal.SlateVisibility.SELF_HIT_TEST_INVISIBLE)
    background = widget(unreal.Border, "Backdrop")
    background.set_brush_color(unreal.LinearColor(.006, .021, .030, .98))
    fill = canvas.add_child_to_canvas(background)
    fill.set_anchors(unreal.Anchors(minimum=V2(0, 0), maximum=V2(1, 1)))
    fill.set_offsets(unreal.Margin(0, 0, 0, 0))

    scale = widget(unreal.ScaleBox, "Fit")
    scale.set_stretch(unreal.Stretch.SCALE_TO_FIT)
    inset = canvas.add_child_to_canvas(scale)
    inset.set_anchors(unreal.Anchors(minimum=V2(0, 0), maximum=V2(1, 1)))
    inset.set_offsets(unreal.Margin(28, 18, 28, 18))
    size = widget(unreal.SizeBox, "DesignSize")
    size.set_width_override(1080)
    size.set_height_override(610)
    scale.add_child(size)
    layout = widget(unreal.CanvasPanel, "Layout")
    size.add_child(layout)

    cyan = (.34, .87, .94, 1)
    ink = (.90, .96, .98, 1)
    muted = (.60, .73, .77, 1)
    amber = (.99, .76, .43, 1)
    def block(name, value, x, y, w, h, fontsize, color, bold=False, container=None):
        obj = widget(unreal.TextBlock, name)
        if name in DYNAMIC:
            defaults(widget_tools.helper).call_method("AssignFlag", args=(obj, unreal.Name("bIsVariable"), True))
        obj.set_text(unreal.Text(value))
        obj.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
        obj.set_auto_wrap_text(True)
        font = obj.get_editor_property("font")
        font.set_editor_property("font_object", load("/Engine/EngineFonts/Roboto"))
        font.set_editor_property("size", fontsize)
        font.set_editor_property("typeface_font_name", "Bold" if bold else "Regular")
        obj.set_font(font)
        if container is not None:
            container.add_child(obj)
        else:
            slot = layout.add_child_to_canvas(obj)
            slot.set_position(V2(x, y))
            slot.set_size(V2(w, h))

    def checkbox(name, label, y, color):
        control = widget(unreal.CheckBox, "Check"+name)
        defaults(widget_tools.helper).call_method("AssignFlag", args=(control, unreal.Name("bIsVariable"), True))
        block("Label"+name, label, 0, 0, 0, 0, 17, color, container=control)
        slot = layout.add_child_to_canvas(control)
        slot.set_position(V2(6, y))
        slot.set_size(V2(324, 44))

    block("Eyebrow", "FINAL PROTOCOL  /  СТАНЦИЯ 07", 4, 4, 700, 26, 15, cyan, True)
    block("Title", "Диагностика Омеги", 4, 32, 1030, 58, 40, ink, True)
    block("Purpose", "Доставь ретранслятор в убежище 07 и проверь питание местной сети.", 5, 96, 1055, 38, 20, muted)
    block("InputHeader", "УСЛОВИЯ ПРОВЕРКИ", 6, 158, 325, 30, 16, cyan, True)
    for i,(name,label) in enumerate(INPUTS):
        checkbox(name,label,200+51*i,ink)
    checkbox("Close","Выйти из диагностики",528,amber)
    block("AHeader", "1  /  ИНТЕЛЛЕКТУАЛЬНЫЙ АГЕНТ", 353, 150, 697, 28, 17, cyan, True)
    block("Agent", "", 353, 183, 697, 83, 21, ink)
    block("SHeader", "2  /  ПОИСК МАРШРУТА A*", 353, 272, 697, 28, 17, cyan, True)
    block("Route", "", 353, 305, 697, 65, 20, ink)
    block("Trace", "", 353, 374, 697, 72, 16, muted)
    block("PHeader", "3  /  РАСПРЕДЕЛЕНИЕ ПИТАНИЯ CSP", 353, 457, 697, 28, 17, cyan, True)
    block("Power", "", 353, 492, 697, 110, 19, ink)
    Story(bp, "RefreshText")
    for name in DYNAMIC:
        var(bp, "View"+name, "string", "")
    var(bp, "NeedsRefresh", "bool", "false")
    for name,_ in INPUTS:
        var(bp,"Previous"+name,"bool","false")
    compile_bp(bp)
    display = Story(bp, "RefreshText")
    display.branch(display.get("NeedsRefresh"))
    for name in DYNAMIC:
        value = display.out(display.call("Engine.KismetTextLibrary.Conv_StringToText", InString=display.get("View"+name)))
        display.do(display.call("UMG.TextBlock.SetText", target=display.get(name), InText=value))
    display.set("NeedsRefresh", False)
    compile_bp(bp)
    read = Story(bp,"ReadControls")
    closed = read.out(read.call("UMG.CheckBox.IsChecked",target=read.get("CheckClose")))
    state = {name:read.out(read.call("UMG.CheckBox.IsChecked",target=read.get("Check"+name))) for name,_ in INPUTS}
    changed=closed
    for name,value in state.items():
        diff=read.math("NotEqual_BoolBool",A=value,B=read.get("Previous"+name))
        changed=any_of(read,changed,diff)
    read.branch(changed)
    owner=read.out(read.do(read.call("Engine.GameplayStatics.GetActorOfClass",ActorClass=B.generated_class(load(SIM)).get_path_name())))
    read.branch(read.valid(owner))
    for name,value in state.items():
        read.set("Previous"+name,value)
        read.do(read.call("Engine.KismetSystemLibrary.SetBoolPropertyByName",Object=owner,PropertyName=name,Value=value))
    read.do(read.call("Engine.KismetSystemLibrary.SetBoolPropertyByName",Object=owner,PropertyName="ControlsChanged",Value=True))
    read.do(read.call("Engine.KismetSystemLibrary.SetBoolPropertyByName",Object=owner,PropertyName="WantsClose",Value=closed))
    compile_bp(bp)
    event = Story(bp)
    event.e.remove_nodes([n for n in event.e.list_all_nodes() if n.get_class().get_name() != "K2Node_Event"])
    event.override("Tick")
    event.do(event.own("ReadControls"))
    event.do(event.own("RefreshText"))
    compile_bp(bp)
    save(bp)
    return bp

def text(g, *parts):
    out = parts[0]
    for part in parts[1:]:
        out = g.out(g.call("Engine.KismetStringLibrary.Concat_StrStr", A=out, B=part))
    return out

def number(g, value):
    return g.out(g.call("Engine.KismetStringLibrary.Conv_IntToString", InInt=value))

def any_of(g, a, b):
    return g.math("BooleanOR", A=a, B=b)

def integer(g, op, a, b):
    return g.math(op+"_IntInt", A=a, B=b)

def member(kind, node):
    return kind + str(node)

def after_branch(g, case, body):
    """Run an optional body, then continue through a common join."""
    split = g.branch(case)
    body()
    join = g.node(g.e.add_branch_node())
    val(pin(join, "Condition"), True)
    link(g.cursor, join.find_execute_pin())
    link(split.find_else_pin(), join.find_execute_pin())
    g.cursor = join.find_then_pin()

def init(bp, ui):
    for name, *_ in INPUTS:
        var(bp, name, "bool", "false")
    for name in ("AutoOpen", "Active", "ToggleDown", "ControlsChanged", "WantsClose", "RouteFound", "PowerFound"):
        var(bp, name, "bool", "false")
    for name in ("Expanded", "Best", "Chosen", "RouteLength", "Assignments"):
        var(bp, name, "int", "0")
    for name in ("AgentResult", "RouteResult", "SearchOrder", "PowerResult"):
        var(bp, name, "string", "")
    for i in range(len(NODES)):
        var(bp, member("Cost", i), "int", str(INF))
        var(bp, member("Path", i), "string", "")
        var(bp, member("Closed", i), "bool", "false")
    var(bp, "Screen", B.get_object_reference_type(unreal.UserWidget), "None")
    compile_bp(bp)
    B.set_blueprint_variable_instance_editable(bp, "AutoOpen", True)

def relax_node(bp, current):
    g = Story(bp, member("Relax", current))
    for i, j, cost, restriction in EDGES:
        if current not in (i, j):
            continue
        neighbor = j if current == i else i
        distance = integer(g, "Add", g.get(member("Cost", current)), cost)
        valid = g.compare("Less", distance, g.get(member("Cost", neighbor)))
        valid = g.both(valid, g.not_(g.get(member("Closed", neighbor))))
        if restriction:
            valid = g.both(valid, g.not_(g.get(restriction)))
        def update():
            g.set(member("Cost", neighbor), distance)
            g.set(member("Path", neighbor), text(g, g.get(member("Path", current)), " → " + NODES[neighbor][0]))
        after_branch(g, valid, update)

def advance_node(bp, i):
    g = Story(bp, member("Expand", i))
    g.branch(g.compare("EqualEqual", g.get("Chosen"), i))
    g.set(member("Closed", i), True)
    g.set("Expanded", integer(g, "Add", g.get("Expanded"), 1))
    previous = g.get("SearchOrder")
    glue = g.select("", " → ", g.compare("EqualEqual", g.get("Expanded"), 1), "String")
    g.set("SearchOrder", text(g, previous, glue, NODES[i][0]))
    if i == GOAL:
        g.set("RouteFound", True)
        g.set("RouteLength", g.get(member("Cost", i)))
        g.set("RouteResult", text(g, g.get(member("Path", i)), "  ·  ", number(g, g.get("RouteLength")), ROUTE_UNIT))
    else:
        g.do(g.own(member("Relax", i)))

def search(bp):
    for i in range(len(NODES)):
        relax_node(bp, i)
    compile_bp(bp)
    for i in range(len(NODES)):
        advance_node(bp, i)
    compile_bp(bp)
    g = Story(bp, "SearchStep")
    g.branch(g.not_(g.get("RouteFound")))
    g.set("Best", INF)
    g.set("Chosen", -1)
    for i, (_, heuristic) in enumerate(NODES):
        score = integer(g, "Add", g.get(member("Cost", i)), heuristic)
        eligible = g.both(g.not_(g.get(member("Closed", i))), g.compare("Less", score, g.get("Best")))
        def pick():
            g.set("Best", score)
            g.set("Chosen", i)
        after_branch(g, eligible, pick)
    g.branch(g.compare("GreaterEqual", g.get("Chosen"), 0))
    for i in range(len(NODES)):
        g.do(g.own(member("Expand", i)))
    compile_bp(bp)

    g = Story(bp, "CalculateRoute")
    g.set("RouteFound", False)
    g.set("RouteLength", 0)
    g.set("Expanded", 0)
    g.set("SearchOrder", "")
    g.set("RouteResult", "Путь закрыт. Открой улицу или служебный проход.")
    for i, (name, _) in enumerate(NODES):
        g.set(member("Cost", i), 0 if i == 0 else INF)
        g.set(member("Path", i), name if i == 0 else "")
        g.set(member("Closed", i), False)
    # At most six expansions are possible because a vertex closes on expansion.
    for _ in NODES:
        g.do(g.own("SearchStep"))
    compile_bp(bp)

def power(bp):
    # Test every assignment until the first that satisfies the constraints.
    candidates = tuple(product((0, 1), repeat=3))
    for slot, assignment in enumerate(candidates):
        g = Story(bp, member("TestAssignment", slot))
        g.branch(g.not_(g.get("PowerFound")))
        g.set("Assignments", integer(g, "Add", g.get("Assignments"), 1))
        radio, light, pump = assignment
        units = (3, 2, 4)
        a = sum(n for line, n in zip(assignment, units) if line == 0)
        b = sum(units) - a
        if a > 6 or radio == pump:
            continue
        reserve_budget = g.select(0, 4, g.get("ReserveOff"), "Int")
        g.branch(g.compare("GreaterEqual", reserve_budget, b))
        g.set("PowerFound", True)
        lines = ("А", "Б")
        g.set("PowerResult",
              f"Связь → {lines[radio]}  ·  свет → {lines[light]}  ·  насос → {lines[pump]}\n"
              f"Нагрузка {a}/6 на А и {b}/4 на Б. Связь и насос на разных вводах.")
    compile_bp(bp)
    g = Story(bp, "AssignPower")
    g.set("PowerFound", False)
    g.set("Assignments", 0)
    g.set("PowerResult", "Допустимой схемы нет. Ввод Б отключён.\n"
          "Три устройства требуют 9 ед. Ввод А даёт 6 ед.")
    for i in range(len(candidates)):
        g.do(g.own(member("TestAssignment", i)))
    compile_bp(bp)

def agent(bp):
    g = Story(bp, "DecideFlight")
    result = "Доставляет ретранслятор. Маршрут открыт, связь обеспечена."
    for name, condition, decision in (
        ("PowerFound", False, "Ожидает питание. Без связи дрон не вылетает."),
        ("RouteFound", False, "Ожидает маршрут. Оба прохода перекрыты."),
        ("Patrol", True, "Остаётся на станции. Датчик обнаружил патруль."),
        ("LowCharge", True, "Возвращается к зарядке. Осталось 12 % энергии."),
    ):
        selected = g.get(name) if condition else g.not_(g.get(name))
        result = g.select(decision, result, selected, "String")
    g.set("AgentResult", result)
    compile_bp(bp)

def write_ui(g, name, value):
    g.do(g.call("Engine.KismetSystemLibrary.SetStringPropertyByName", Object=g.get("Screen"),
                PropertyName="View"+name, Value=value))

def diagnostics(bp, ui):
    g = Story(bp, "RefreshDiagnostics")
    g.do(g.own("CalculateRoute"))
    g.do(g.own("AssignPower"))
    g.do(g.own("DecideFlight"))
    write_ui(g, "Agent", g.get("AgentResult"))
    write_ui(g, "Route", g.get("RouteResult"))
    write_ui(g, "Trace", text(g, "Проверено узлов: ", number(g, g.get("Expanded")),
                                "/6. A* выбирает узел с наименьшим g + h.\n", g.get("SearchOrder")))
    write_ui(g, "Power", text(g, g.get("PowerResult"), "\nПроверено вариантов: ",
                                number(g, g.get("Assignments")), "/8."))
    g.do(g.call("Engine.KismetSystemLibrary.SetBoolPropertyByName", Object=g.get("Screen"),
                PropertyName="NeedsRefresh", Value=True))
    compile_bp(bp)

    g = Story(bp, "OpenDiagnostics")
    g.branch(g.not_(g.get("Active")))
    g.branch(g.valid(g.pc()))
    g.branch(g.not_(g.out(g.call("Engine.Controller.IsMoveInputIgnored", target=g.pc()))))
    screen = g.do(g.call("UMG.WidgetBlueprintLibrary.Create",
                        WidgetType=B.generated_class(ui).get_path_name(), OwningPlayer=g.pc()))
    g.set("Screen", g.out(screen))
    for name,_ in INPUTS:
        g.set(name,False)
    g.set("WantsClose",False)
    g.set("ControlsChanged",False)
    g.do(g.call("UMG.UserWidget.AddToViewport", target=g.get("Screen"), ZOrder=205))
    g.do(g.call("Engine.KismetSystemLibrary.SetBoolPropertyByName",Object=g.pc(),
                PropertyName="bShowMouseCursor",Value=True))
    g.do(g.call("UMG.WidgetBlueprintLibrary.SetInputMode_GameAndUIEx",PlayerController=g.pc(),
                InMouseLockMode="DoNotLock", bHideCursorDuringCapture=False, bFlushInput=False))
    g.do(g.call("Engine.Controller.SetIgnoreMoveInput", target=g.pc(), bNewMoveInput=True))
    g.do(g.call("Engine.Controller.SetIgnoreLookInput", target=g.pc(), bNewLookInput=True))
    g.set("Active", True)
    g.do(g.own("RefreshDiagnostics"))

    g = Story(bp, "CloseDiagnostics")
    g.branch(g.get("Active"))
    g.do(g.call("UMG.Widget.RemoveFromParent", target=g.get("Screen")))
    g.set("Screen", "None")
    g.set("Active", False)
    g.do(g.call("Engine.KismetSystemLibrary.SetBoolPropertyByName",Object=g.pc(),
                PropertyName="bShowMouseCursor",Value=False))
    g.do(g.call("UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly",PlayerController=g.pc(),bFlushInput=False))
    g.do(g.call("Engine.Controller.SetIgnoreMoveInput", target=g.pc(), bNewMoveInput=False))
    g.do(g.call("Engine.Controller.SetIgnoreLookInput", target=g.pc(), bNewLookInput=False))
    g.branch(g.get("AutoOpen"))
    g.do(g.call("Engine.GameplayStatics.OpenLevel", LevelName="Lvl_MainMenu"))
    compile_bp(bp)

    toggle=Story(bp,"ReadToggleKey")
    down=toggle.out(toggle.call("Engine.PlayerController.IsInputKeyDown",target=toggle.pc(),Key='(KeyName="J")'))
    key=toggle.branch(down)
    toggle.branch(toggle.not_(toggle.get("ToggleDown")))
    toggle.set("ToggleDown",True)
    opened=toggle.branch(toggle.get("Active"))
    toggle.do(toggle.own("CloseDiagnostics"))
    toggle.cursor=opened.find_else_pin()
    toggle.do(toggle.own("OpenDiagnostics"))
    toggle.cursor=key.find_else_pin()
    toggle.set("ToggleDown",False)
    compile_bp(bp)

    g = Story(bp)
    g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name() != "K2Node_Event"])
    g.override("ReceiveTick")
    g.branch(g.valid(g.pc()))
    auto=g.branch(g.get("AutoOpen"))
    g.cursor=auto.find_else_pin()
    g.do(g.own("ReadToggleKey"))
    next_tick=g.node(g.e.add_branch_node())
    val(pin(next_tick,"Condition"),g.both(g.get("AutoOpen"),g.not_(g.get("Active"))))
    link(g.cursor,next_tick.find_execute_pin())
    link(auto.find_then_pin(),next_tick.find_execute_pin())
    g.cursor=next_tick.find_then_pin()
    g.do(g.own("OpenDiagnostics"))
    g.cursor=next_tick.find_else_pin()
    g.branch(g.both(g.get("Active"),g.get("ControlsChanged")))
    g.set("ControlsChanged",False)
    quit_control=g.branch(g.get("WantsClose"))
    g.do(g.own("CloseDiagnostics"))
    g.cursor=quit_control.find_else_pin()
    g.do(g.own("RefreshDiagnostics"))
    compile_bp(bp)
    save(bp)

def put_actor(levels, actors, editor, bp, map_path, auto):
    if A.does_asset_exist(map_path):
        assert levels.load_level(map_path)
    else:
        assert levels.new_level(map_path)
    obj = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == "FP_OmegaDiagnostics"), None)
    if obj is None:
        obj = actors.spawn_actor_from_class(B.generated_class(bp), unreal.Vector(), unreal.Rotator())
        obj.set_actor_label("FP_OmegaDiagnostics")
    obj.set_editor_property("AutoOpen", auto)
    if auto:
        world_settings = editor.get_editor_world().get_world_settings()
        world_settings.set_editor_property("default_game_mode", unreal.GameModeBase)
        if not any(isinstance(a, unreal.PlayerStart) for a in actors.get_all_level_actors()):
            actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 125), unreal.Rotator())
    assert unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), map_path)

def install():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert not editor.get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    backup = PROJECT / "Saved/Backups/OmegaDiagnostics" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for item, ext in ((MAIN, ".umap"), (MODE, ".umap"), (SIM, ".uasset"), (PANEL, ".uasset")):
        rel = Path("Content") / (item[6:] + ext)
        if (PROJECT / rel).is_file():
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT / rel, backup / rel)
    WORK.mkdir(parents=True, exist_ok=True)
    A.make_directory(ROOT)
    bp = bp_asset(SIM)
    compile_bp(bp)
    ui = text_ui()
    init(bp, ui)
    search(bp)
    power(bp)
    agent(bp)
    diagnostics(bp, ui)
    put_actor(levels, actors, editor, bp, MODE, True)
    put_actor(levels, actors, editor, bp, MAIN, False)
    (WORK / "Installed.json").write_text(json.dumps({"backup": str(backup), "assets": [PANEL, SIM, MODE],
        "campaignEntry": MAIN, "key": "J", "weeks": [1,2,3]}, ensure_ascii=False, indent=2), encoding="utf8")

if __name__ == "__main__":
    install()

