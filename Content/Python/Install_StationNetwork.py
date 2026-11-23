"""Connect local channels, power allocation and Omega to the campaign transmitters."""
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import shutil
import traceback

import unreal

import Install_OmegaDiagnostics as solver
from Install_RepairPass import editable
from Install_StoryMemory import A, B, MISSION, Story, bp_asset, compile_bp, link, load, save, val, var


PROJECT = Path(unreal.Paths.project_dir()).resolve()
WORK = Path(__file__).resolve().parent
ROOT = "/Game/Story/StationNetwork"
PANEL = ROOT + "/WBP_StationNetwork"
ACTOR = ROOT + "/BP_StationNetwork"
BEFORE_AFTER = (
    ("FrequencyUse", "TuneStation07", "StationCarrierReady", "StationBroadcastPermit"),
    ("SecondVoiceUse", "TuneTelephone", "TelephoneCarrierReady", "TelephoneBroadcastPermit"),
)
SWITCHES = (
    ("ReserveOn", "Включить резервный ввод Б"),
    ("RoofOn", "Подключить антенну"),
    ("CableOn", "Подключить линию водоканала"),
    ("RequestSend", "Передать, когда сеть готова"),
)


def graph_call(g, owner, bp, name):
    node = g.node(g.e.add_call_function_node(B.generated_class(bp).get_path_name() + "." + name))
    val(node.find_self_pin(), owner)
    return g.do(node)


def member_bool(g, owner, name, value):
    g.do(g.call("Engine.KismetSystemLibrary.SetBoolPropertyByName", Object=owner, PropertyName=name, Value=value))


def widget():
    ui = solver.text_ui()
    tree = unreal.find_object(ui, "WidgetTree")
    for name, value in (
        ("Eyebrow", "FINAL PROTOCOL  /  МЕСТНАЯ СВЯЗЬ"),
        ("Title", "Передача в Убежище 07"),
        ("Purpose", "Частота настроена. Подай питание и подключи линию в обход Атласа."),
        ("InputHeader", "РУБИЛЬНИКИ И ПЕРЕДАЧА"),
        ("AHeader", "РЕШЕНИЕ ОМЕГИ"),
        ("SHeader", "МЕСТНЫЙ КАНАЛ"),
        ("PHeader", "ПИТАНИЕ  /  CSP"),
        ("LabelClose", "Закрыть пульт"),
    ):
        unreal.find_object(tree, name).set_text(unreal.Text(value))
    compile_bp(ui)
    save(ui)
    return ui


def open_close(bp, ui):
    g = Story(bp, "OpenNetwork")
    g.branch(g.not_(g.get("Active")))
    g.branch(g.valid(g.pc()))
    g.branch(g.not_(g.out(g.call("Engine.Controller.IsMoveInputIgnored", target=g.pc()))))
    screen = g.do(g.call("UMG.WidgetBlueprintLibrary.Create",
                        WidgetType=B.generated_class(ui).get_path_name(), OwningPlayer=g.pc()))
    g.set("Screen", g.out(screen))
    for name, _ in SWITCHES:
        g.set(name, False)
    g.set("WantsClose", False)
    g.set("ControlsChanged", False)
    g.do(g.call("UMG.UserWidget.AddToViewport", target=g.get("Screen"), ZOrder=205))
    member_bool(g, g.pc(), "bShowMouseCursor", True)
    g.do(g.call("UMG.WidgetBlueprintLibrary.SetInputMode_GameAndUIEx", PlayerController=g.pc(),
                InMouseLockMode="DoNotLock", bHideCursorDuringCapture=False, bFlushInput=False))
    g.do(g.call("Engine.Controller.SetIgnoreMoveInput", target=g.pc(), bNewMoveInput=True))
    g.do(g.call("Engine.Controller.SetIgnoreLookInput", target=g.pc(), bNewLookInput=True))
    g.set("Active", True)
    g.do(g.own("RefreshNetwork"))

    g = Story(bp, "CloseNetwork")
    g.branch(g.get("Active"))
    g.set("Active", False)
    g.do(g.call("UMG.Widget.RemoveFromParent", target=g.get("Screen")))
    g.set("Screen", "None")
    member_bool(g, g.pc(), "bShowMouseCursor", False)
    g.do(g.call("UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly", PlayerController=g.pc(), bFlushInput=False))
    g.do(g.call("Engine.Controller.SetIgnoreMoveInput", target=g.pc(), bNewMoveInput=False))
    g.do(g.call("Engine.Controller.SetIgnoreLookInput", target=g.pc(), bNewLookInput=False))
    compile_bp(bp)


def build_actor(bp, ui, mission):
    for name, _ in SWITCHES:
        var(bp, name, "bool", "false")
    for name in ("Active", "WantsClose", "ControlsChanged", "LineConnected", "PowerFound",
                 "Telephone", "MayBroadcast"):
        var(bp, name, "bool", "false")
    var(bp, "ReserveOff", "bool", "true")
    var(bp, "Assignments", "int", "0")
    for name in ("AgentResult", "PowerResult"):
        var(bp, name, "string", "")
    var(bp, "Screen", B.get_object_reference_type(unreal.UserWidget), "None")
    for fn in ("ResolveNetwork", "RefreshNetwork", "OpenNetwork", "CloseNetwork", "SubmitBroadcast"):
        Story(bp, fn)
    compile_bp(bp)
    solver.power(bp)

    g = Story(bp, "ResolveNetwork")
    g.set("LineConnected", solver.any_of(g, g.get("RoofOn"), g.get("CableOn")))
    g.set("ReserveOff", g.not_(g.get("ReserveOn")))
    g.do(g.own("AssignPower"))
    g.set("MayBroadcast", g.both(g.get("LineConnected"), g.get("PowerFound")))
    channel = g.select("Передача разрешена. Можно вызвать жителей.", "Ожидаю местный канал. Магистраль слушает Атлас.",
                       g.get("LineConnected"), "String")
    g.set("AgentResult", g.select(channel, "Ожидаю резерв питания для связи, света и насоса.",
                                  g.get("PowerFound"), "String"))
    compile_bp(bp)

    g = Story(bp, "RefreshNetwork")
    g.do(g.own("ResolveNetwork"))
    solver.write_ui(g, "Agent", g.get("AgentResult"))
    antenna = g.select("Антенна подключена", "Антенна отключена", g.get("RoofOn"), "String")
    cable = g.select("Кабель водоканала подключён", "Кабель водоканала отключён", g.get("CableOn"), "String")
    solver.write_ui(g, "Route", solver.text(g, antenna, "\n", cable))
    solver.write_ui(g, "Trace", g.select("Местная линия готова.",
                                          "Для связи подключи антенну или кабель водоканала.",
                                          g.get("LineConnected"), "String"))
    solver.write_ui(g, "Power", solver.text(g, g.get("PowerResult"), "\nПроверено схем: ",
                                           solver.number(g, g.get("Assignments")), " из 8."))
    member_bool(g, g.get("Screen"), "NeedsRefresh", True)
    compile_bp(bp)

    open_close(bp, ui)
    g = Story(bp, "SubmitBroadcast")
    g.branch(g.get("RequestSend"))
    g.branch(g.get("MayBroadcast"))
    g.set("RequestSend", False)
    found = g.do(g.call("Engine.GameplayStatics.GetActorOfClass", ActorClass=B.generated_class(mission).get_path_name()))
    owner = g.out(found)
    g.branch(g.valid(owner))
    permit = g.select("TelephoneBroadcastPermit", "StationBroadcastPermit", g.get("Telephone"), "Name")
    member_bool(g, owner, permit, True)
    g.do(g.own("CloseNetwork"))
    graph_call(g, owner, mission, "RequestRecovery")
    member_bool(g, owner, permit, False)
    compile_bp(bp)

    g = Story(bp)
    g.e.remove_nodes([node for node in g.e.list_all_nodes() if node.get_class().get_name() != "K2Node_Event"])
    g.override("ReceiveTick")
    g.branch(g.get("Active"))
    g.branch(g.valid(g.pc()))
    g.branch(g.get("ControlsChanged"))
    g.set("ControlsChanged", False)
    close = g.branch(g.get("WantsClose"))
    g.do(g.own("CloseNetwork"))
    g.cursor = close.find_else_pin()
    g.do(g.own("RefreshNetwork"))
    g.do(g.own("SubmitBroadcast"))
    compile_bp(bp)
    remove_old_signal_search(bp)
    save(bp)


def remove_old_signal_search(bp):
    # Upgrade older packages after all callers have been rebuilt.
    graphs = set(map(str, B.list_graph_names(bp)))
    retired = ["CalculateRoute", "SearchStep"]
    for prefix in ("Expand", "Relax"):
        retired.extend(prefix + str(i) for i in range(6))
    for name in retired:
        if name in graphs:
            B.remove_function_graph(bp, name)
    assert not set(retired).intersection(map(str, B.list_graph_names(bp)))
    compile_bp(bp)


def connect_gate(mission, network, fn, native_name, tuned, permit, phone):
    g = editable(mission, fn)
    if any(node.get_name() == "CampaignNetwork" + native_name for node in g.e.list_all_nodes()):
        return
    native = next(node for node in g.e.list_all_nodes() if node.get_name() == native_name)
    native_input = native.find_execute_pin()
    [former_input] = native_input.list_connected_pins()
    [guard_input] = native.find_then_pin().list_connected_pins()
    guard = guard_input.get_owning_node()
    [next_input] = guard.find_then_pin().list_connected_pins()
    native_input.break_pin_links()
    next_input.break_pin_links()

    g.cursor = former_input
    aligned = g.branch(g.get(tuned))
    aligned.rename("CampaignNetwork" + native_name)
    link(aligned.find_else_pin(), native_input)

    g.cursor = guard.find_then_pin()
    mark = g.set(tuned, True)
    g.cursor = aligned.find_then_pin()
    permitted = g.branch(g.get(permit))
    link(mark.find_then_pin(), permitted.find_execute_pin())
    g.set(tuned, False)
    g.set(permit, False)
    link(g.cursor, next_input)

    g.cursor = permitted.find_else_pin()
    cls = B.generated_class(network).get_path_name()
    owner = g.out(g.do(g.call("Engine.GameplayStatics.GetActorOfClass", ActorClass=cls)))
    existing = g.branch(g.valid(owner))
    member_bool(g, owner, "Telephone", phone)
    graph_call(g, owner, network, "OpenNetwork")
    g.cursor = existing.find_else_pin()
    g.spawn(cls, "(X=0,Y=0,Z=0)")
    owner = g.out(g.do(g.call("Engine.GameplayStatics.GetActorOfClass", ActorClass=cls)))
    g.branch(g.valid(owner))
    member_bool(g, owner, "Telephone", phone)
    graph_call(g, owner, network, "OpenNetwork")


@contextmanager
def station_widget_settings():
    # The shared authoring helper can be reused for the diagnostic map in this same editor.
    original = solver.ROOT, solver.SIM, solver.PANEL, solver.INPUTS
    solver.ROOT, solver.SIM, solver.PANEL, solver.INPUTS = ROOT, ACTOR, PANEL, SWITCHES
    try:
        yield
    finally:
        solver.ROOT, solver.SIM, solver.PANEL, solver.INPUTS = original


def install():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert not dirty.intersection((MISSION, ACTOR, PANEL)), dirty
    backup = PROJECT / "Saved/Backups/StationNetwork" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for asset in (MISSION, ACTOR, PANEL):
        rel = Path("Content") / (asset[6:] + ".uasset")
        src = PROJECT / rel
        if src.is_file():
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    mission = load(MISSION)
    A.make_directory(ROOT)
    network = bp_asset(ACTOR)
    compile_bp(network)
    with station_widget_settings():
        ui = widget()
    for _, _, tuned, permit in BEFORE_AFTER:
        for field in (tuned, permit):
            var(mission, field, "bool", "false")
    compile_bp(mission)
    build_actor(network, ui, mission)
    for index, integration in enumerate(BEFORE_AFTER):
        connect_gate(mission, network, *integration, index == 1)
    compile_bp(mission)
    save(mission)
    return {"passed": True, "backup": str(backup), "assets": [MISSION, ACTOR, PANEL]}


if __name__ == "__main__":
    status = {"passed": False}
    try:
        status = install()
    except Exception:
        status["error"] = traceback.format_exc()
        unreal.log_error(status["error"])
    (WORK / "Install.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf8")
    if not status["passed"]:
        raise RuntimeError(status["error"])
