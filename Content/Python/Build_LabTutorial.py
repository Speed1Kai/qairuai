import unreal
import os
import re
import traceback
import math

PROJECT_DIR = unreal.Paths.project_dir()
SAVED_DIR = unreal.Paths.project_saved_dir()
REQUEST_FILE = os.path.join(SAVED_DIR, "BUILD_LAB_TUTORIAL_ON_NEXT_START.txt")
REPORT_FILE = os.path.join(SAVED_DIR, "lab_tutorial_build_report.txt")
FAIL_FILE = os.path.join(SAVED_DIR, "lab_tutorial_build_failed.txt")
DONE_FILE = os.path.join(SAVED_DIR, "lab_tutorial_build_complete.txt")
LEVEL_PATH = "/Game/Lvl_LabTutorial"
MAT_PATH = "/Game/FinalProtocol/Materials"
BP_PATH = "/Game/LabTutorial/Blueprints"

# This script is registered as a one-time editor startup task. It does nothing
# unless the project owner has explicitly placed the request marker in Saved/.
if os.path.isfile(REQUEST_FILE):
    try:
        os.remove(REQUEST_FILE)
    except Exception:
        pass
    report = []

    def note(message):
        report.append(str(message))
        unreal.log("[LabTutorial] " + str(message))

    def vec(x, y, z):
        return unreal.Vector(float(x), float(y), float(z))

    def text_facing(location, viewer):
        """Put TextRender on a vertical panel facing a point while keeping its baseline level."""
        dx = float(viewer[0]) - float(location[0])
        dy = float(viewer[1]) - float(location[1])
        yaw = math.degrees(math.atan2(dx, -dy))
        # Roll turns the text's local vertical axis into world Z; pitch=90 made
        # the old text baseline vertical, which rendered as a thin glyph column.
        return unreal.Rotator(0.0, yaw, 90.0)

    def local_panel_point(offset, z, yaw_degrees, normal_offset=0.0):
        yaw = math.radians(float(yaw_degrees))
        right = (math.cos(yaw), math.sin(yaw))
        normal = (math.sin(yaw), -math.cos(yaw))
        return (right[0] * offset + normal[0] * normal_offset,
                right[1] * offset + normal[1] * normal_offset,
                float(z))

    def set_folder(actor, folder):
        try:
            actor.set_folder_path(unreal.Name(folder))
        except Exception:
            pass

    def spawn_box(name, location, size, material, mesh, blocking=True, rotation=None):
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.StaticMeshActor, vec(*location), rotation or unreal.Rotator())
        if not actor:
            raise RuntimeError("Could not spawn mesh actor: " + name)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_static_mesh(mesh)
        if material:
            component.set_material(0, material)
        component.set_collision_profile_name("BlockAll" if blocking else "NoCollision")
        try:
            component.set_editor_property("cast_shadow", False)
        except Exception:
            pass
        actor.set_actor_scale3d(vec(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0))
        actor.set_actor_label(name, mark_dirty=True)
        set_folder(actor, "LAB/01_Blockout")
        return actor

    def spawn_text(name, location, rotation, text, color=(120, 240, 255), size=22.0,
                   centered=True):
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.TextRenderActor, vec(*location), rotation)
        if not actor:
            raise RuntimeError("Could not spawn text actor: " + name)
        comp = actor.get_component_by_class(unreal.TextRenderComponent)
        comp.set_text(unreal.Text(text))
        try:
            comp.set_world_size(float(size))
        except Exception:
            comp.set_editor_property("world_size", float(size))
        try:
            comp.set_text_render_color(unreal.Color(color[0], color[1], color[2], 255))
        except Exception:
            comp.set_editor_property("text_render_color", unreal.Color(color[0], color[1], color[2], 255))
        try:
            comp.set_editor_property("cast_shadow", False)
            comp.set_editor_property(
                "horizontal_alignment",
                unreal.HorizTextAligment.EHTA_CENTER if centered else unreal.HorizTextAligment.EHTA_LEFT)
            comp.set_editor_property("vertical_alignment", unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
        except Exception:
            pass
        actor.set_actor_label(name, mark_dirty=True)
        set_folder(actor, "LAB/05_Story")
        return actor

    def get_blueprint_components(blueprint, component_class):
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
        library = unreal.SubobjectDataBlueprintFunctionLibrary
        result = []
        for handle in handles:
            data = library.get_data(handle)
            component = library.get_object_for_blueprint(data, blueprint)
            if isinstance(component, component_class):
                result.append(component)
        return result

    def get_blueprint_component(blueprint, component_class):
        components = get_blueprint_components(blueprint, component_class)
        return components[0] if components else None

    def ensure_blueprint_trigger_component(blueprint, variable_name, extent):
        # TriggerBox's native inherited box does not accept a bound event node
        # through UE Python; an explicit child component does.
        components = get_blueprint_components(blueprint, unreal.BoxComponent)
        if len(components) <= 1:
            component = add_box_component(blueprint, variable_name, (0, 0, 0), extent)
            unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
            return component
        component = components[-1]
        try:
            component.set_editor_property("box_extent", vec(*extent))
            component.set_editor_property("generate_overlap_events", True)
            component.set_collision_profile_name("Trigger")
        except Exception:
            pass
        return component

    def add_box_component(blueprint, variable_name, relative_location, extent):
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
        if not handles:
            raise RuntimeError("Blueprint has no root component handle")
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", handles[0])
        params.set_editor_property("new_class", unreal.BoxComponent)
        params.set_editor_property("blueprint_context", blueprint)
        handle, reason = subsystem.add_new_subobject(params)
        if not handle:
            raise RuntimeError("Could not add interaction box: {}".format(reason))
        library = unreal.SubobjectDataBlueprintFunctionLibrary
        component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
        if not component:
            raise RuntimeError("Could not access new interaction box template")
        try:
            component.set_editor_property("relative_location", vec(*relative_location))
            component.set_editor_property("box_extent", vec(*extent))
            component.set_editor_property("generate_overlap_events", True)
            component.set_collision_profile_name("Trigger")
        except Exception as error:
            note("Could not configure {} collision: {}".format(variable_name, error))
        try:
            library.set_variable_name(library.get_data(handle), unreal.Name(variable_name))
        except Exception:
            pass
        return component

    def add_blueprint_component(blueprint, component_class, variable_name, parent_class=None):
        """Add a named native component, optionally attaching it to a camera component."""
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
        if not handles:
            raise RuntimeError("Blueprint has no root component handle")
        library = unreal.SubobjectDataBlueprintFunctionLibrary
        parent_handle = handles[0]
        if parent_class:
            for handle in handles:
                try:
                    component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
                    if isinstance(component, parent_class):
                        parent_handle = handle
                        break
                except Exception:
                    continue
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", parent_handle)
        params.set_editor_property("new_class", component_class)
        params.set_editor_property("blueprint_context", blueprint)
        handle, reason = subsystem.add_new_subobject(params)
        if not handle:
            raise RuntimeError("Could not add {}: {}".format(variable_name, reason))
        component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
        if not component:
            raise RuntimeError("Could not access {} component template".format(variable_name))
        try:
            library.set_variable_name(library.get_data(handle), unreal.Name(variable_name))
        except Exception:
            pass
        return component

    def ensure_bool_member(blueprint, variable_name):
        try:
            member_names = [str(name) for name in
                            unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint)]
        except Exception:
            member_names = []
        if variable_name not in member_names:
            editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
                blueprint, unreal.Name("EventGraph"))
            editor.add_member_variable(
                unreal.Name(variable_name),
                unreal.BlueprintEditorLibrary.get_basic_type_by_name(unreal.Name("bool")))
            unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)

    def component_reference_node(editor, component_variable, owner_class_path):
        """Return a Blueprint node that references a component template."""
        if owner_class_path:
            node = editor.add_get_member_variable_node(
                unreal.Name(component_variable), owner_class_path)
        else:
            node = editor.add_get_member_variable_node(unreal.Name(component_variable))
        if node:
            return node
        raise RuntimeError("Could not get component reference {}".format(component_variable))

    def component_reference_output(editor, component_variable, owner_class_path, component_class_path):
        """Resolve a component getter, falling back to Actor.GetComponentByClass."""
        try:
            node = component_reference_node(editor, component_variable, owner_class_path)
            output = node.find_output_pin(component_variable)
            if output:
                return node, output
        except Exception:
            pass
        node = editor.add_call_function_node("/Script/Engine.Actor.GetComponentByClass")
        if not node:
            raise RuntimeError("Could not create a component getter for {}".format(component_variable))
        node.find_input_pin("ComponentClass").set_pin_value(
            "Class'{}'".format(component_class_path))
        output = node.find_output_pin("ReturnValue")
        if not output:
            raise RuntimeError("Component getter has no ReturnValue for {}".format(component_variable))
        return node, output

    def has_input_key_node(editor, key_name):
        wanted = str(key_name).lower()
        for node in editor.list_all_nodes():
            try:
                if node.get_class().get_name() != "K2Node_InputKey":
                    continue
                key = node.get_editor_property("input_key")
                if str(key.get_editor_property("key_name")).lower() == wanted:
                    return True
            except Exception:
                continue
        return False

    def wire_overlap_message(blueprint, component, message, duration=12.0):
        """Create a small, readable proximity interaction using UE 5.8 graph APIs."""
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(blueprint, unreal.Name("EventGraph"))
        if not editor:
            raise RuntimeError("Could not open Blueprint EventGraph")
        event = editor.add_component_bound_event_node(component, unreal.Name("OnComponentBeginOverlap"))
        if not event:
            raise RuntimeError("Could not create overlap event node")
        call = None
        for node in editor.list_all_nodes():
            if isinstance(node, unreal.K2Node_CallFunction):
                call = node
                break
        if call:
            note("Updating existing interaction graph in {}".format(blueprint.get_name()))
        else:
            call = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
        if not call:
            raise RuntimeError("Could not create Print String node")
        call.find_input_pin("InString").set_pin_value(message)
        call.find_input_pin("Duration").set_pin_value(str(float(duration)))
        call.find_input_pin("bPrintToScreen").set_pin_value("true")
        call.find_input_pin("bPrintToLog").set_pin_value("true")
        try:
            event.find_output_pin("then").try_create_connection(call.find_execute_pin())
        except Exception:
            pass
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
        note("Wired proximity interaction: {}".format(blueprint.get_name()))

    def add_keyboard_event_node(editor, key_name):
        """Create an Input Key node using the engine's registered keyboard action."""
        compact_name = str(key_name).replace(" ", "")
        menu_name = "Input|KeyboardEvents|" + compact_name
        node = editor.create_node_from_name(menu_name, unreal.Vector2D(0.0, 0.0), [])
        if not node:
            available = editor.list_available_nodes([])
            matches = [name for name in available
                       if "|KeyboardEvents|" in name
                       and name.rsplit("|", 1)[-1].lower() == compact_name.lower()]
            for name in matches:
                node = editor.create_node_from_name(name, unreal.Vector2D(0.0, 0.0), [])
                if node:
                    break
        if not node or not node.find_output_pin("Pressed") or not node.find_output_pin("Released"):
            raise RuntimeError("Could not create keyboard event node for {}".format(key_name))
        try:
            # Several nearby terminals share E; one out-of-range actor must not
            # consume the key before the active interaction volume handles it.
            node.set_editor_property("bConsumeInput", False)
        except Exception:
            pass
        return node

    def remove_input_key_nodes(editor, key_names):
        remove = []
        wanted = {str(name).lower() for name in key_names}
        for node in editor.list_all_nodes():
            try:
                if node.get_class().get_name() != "K2Node_InputKey":
                    continue
                key = node.get_editor_property("input_key")
                key_name = str(key.get_editor_property("key_name")).lower()
                if key_name in wanted:
                    remove.append(node)
            except Exception:
                continue
        if remove:
            editor.remove_nodes(remove)

    def wire_player_movement_controls():
        """Bind hold-C crouch and hold-Shift sprint to the game's actual character."""
        character_bp = unreal.EditorAssetLibrary.load_asset(
            "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter")
        if not character_bp:
            note("Could not find BP_ThirdPersonCharacter; C and Shift controls were not changed")
            return False

        movement = get_blueprint_component(character_bp, unreal.CharacterMovementComponent)
        if not movement:
            note("CharacterMovementComponent template missing; C and Shift controls were not changed")
            return False
        base_speed = float(movement.get_editor_property("max_walk_speed"))
        nav_properties = movement.get_editor_property("nav_agent_props")
        try:
            nav_properties.set_editor_property("b_can_crouch", True)
            movement.set_editor_property("nav_agent_props", nav_properties)
        except Exception as error:
            note("Could not enable crouch capability in movement settings: {}".format(error))

        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
            character_bp, unreal.Name("EventGraph"))
        if not editor:
            note("Character EventGraph is unavailable; C and Shift controls were not wired")
            return False
        remove_input_key_nodes(editor, ("C", "LeftShift"))

        crouch_key = add_keyboard_event_node(editor, "C")
        crouch = editor.add_call_function_node("/Script/Engine.Character.Crouch")
        uncrouch = editor.add_call_function_node("/Script/Engine.Character.UnCrouch")
        crouch_key.find_output_pin("Pressed").try_create_connection(crouch.find_execute_pin())
        crouch_key.find_output_pin("Released").try_create_connection(uncrouch.find_execute_pin())

        sprint_key = add_keyboard_event_node(editor, "LeftShift")
        movement_get = editor.add_get_member_variable_node(
            unreal.Name("CharacterMovement"), "/Script/Engine.Character")
        if not movement_get:
            raise RuntimeError("Could not get CharacterMovement variable on the player Blueprint")
        sprint_set = editor.add_set_member_variable_node(
            unreal.Name("MaxWalkSpeed"), "/Script/Engine.CharacterMovementComponent")
        normal_set = editor.add_set_member_variable_node(
            unreal.Name("MaxWalkSpeed"), "/Script/Engine.CharacterMovementComponent")
        sprint_set.find_input_pin("MaxWalkSpeed").set_pin_value(str(base_speed * 1.65))
        normal_set.find_input_pin("MaxWalkSpeed").set_pin_value(str(base_speed))
        movement_get.find_output_pin("CharacterMovement").try_create_connection(
            sprint_set.find_input_pin("Target"))
        movement_get.find_output_pin("CharacterMovement").try_create_connection(
            normal_set.find_input_pin("Target"))
        sprint_key.find_output_pin("Pressed").try_create_connection(sprint_set.find_execute_pin())
        sprint_key.find_output_pin("Released").try_create_connection(normal_set.find_execute_pin())

        # A wide, shadowless cyan-green beam follows the player's camera. It is
        # toggled with N and supplies actual light in dark corridors without
        # adding a costly full-screen effect on the 6 GB target GPU.
        night_light = get_blueprint_component(character_bp, unreal.SpotLightComponent)
        if not night_light:
            night_light = add_blueprint_component(
                character_bp, unreal.SpotLightComponent, "NightVisionLight", unreal.CameraComponent)
        night_light.set_mobility(unreal.ComponentMobility.MOVABLE)
        night_light.set_editor_property("relative_location", vec(8, 0, 0))
        night_light.set_editor_property("relative_rotation", unreal.Rotator())
        night_light.set_editor_property("visible", False)
        set_light(night_light, (96, 255, 190), 9000.0, 2600.0)
        night_light.set_editor_property("inner_cone_angle", 34.0)
        night_light.set_editor_property("outer_cone_angle", 58.0)
        ensure_bool_member(character_bp, "bNightVisionActive")
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
            character_bp, unreal.Name("EventGraph"))
        if not has_input_key_node(editor, "N"):
            night_key = add_keyboard_event_node(editor, "N")
            night_get = editor.add_get_member_variable_node(unreal.Name("bNightVisionActive"))
            night_branch = editor.add_branch_node()
            night_key.find_output_pin("Pressed").try_create_connection(night_branch.find_execute_pin())
            night_get.find_output_pin("bNightVisionActive").try_create_connection(
                night_branch.find_input_pin("Condition"))

            light_ref, light_output = component_reference_output(
                editor, "NightVisionLight", None, "/Script/Engine.SpotLightComponent")
            turn_off = editor.add_call_function_node("/Script/Engine.SceneComponent.SetVisibility")
            turn_on = editor.add_call_function_node("/Script/Engine.SceneComponent.SetVisibility")
            light_output.try_create_connection(turn_off.find_input_pin("Target"))
            light_output.try_create_connection(turn_on.find_input_pin("Target"))
            turn_off.find_input_pin("bNewVisibility").set_pin_value("false")
            turn_on.find_input_pin("bNewVisibility").set_pin_value("true")

            state_off = editor.add_set_member_variable_node(unreal.Name("bNightVisionActive"))
            state_on = editor.add_set_member_variable_node(unreal.Name("bNightVisionActive"))
            state_off.find_input_pin("bNightVisionActive").set_pin_value("false")
            state_on.find_input_pin("bNightVisionActive").set_pin_value("true")
            night_branch.find_then_pin().try_create_connection(turn_off.find_execute_pin())
            turn_off.find_output_pin("then").try_create_connection(state_off.find_execute_pin())
            night_branch.find_else_pin().try_create_connection(turn_on.find_execute_pin())
            turn_on.find_output_pin("then").try_create_connection(state_on.find_execute_pin())
            note("Bound N to toggle camera-following night vision")
        else:
            note("N night-vision toggle already exists")

        if not unreal.BlueprintEditorLibrary.compile_blueprint(character_bp):
            raise RuntimeError("BP_ThirdPersonCharacter failed to compile after movement and vision wiring")
        unreal.EditorAssetLibrary.save_loaded_asset(character_bp)
        note("Bound hold-C crouch and hold-LeftShift sprint; base speed {:.0f}, sprint {:.0f}".format(
            base_speed, base_speed * 1.65))
        return True

    def wire_door_interaction(blueprint, trigger_component):
        """Only open the sliding bulkhead when the player presses E near its panel."""
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
            blueprint, unreal.Name("EventGraph"))
        if not editor:
            raise RuntimeError("Could not open sliding door EventGraph")

        # Rebuild this small graph cleanly so rerunning the map builder does not
        # preserve the old proximity-only door logic or accumulate duplicate nodes.
        old_nodes = []
        for node in editor.list_all_nodes():
            try:
                class_name = node.get_class().get_name()
                if class_name in ("K2Node_CallFunction", "K2Node_ComponentBoundEvent", "K2Node_InputKey"):
                    old_nodes.append(node)
            except Exception:
                pass
        if old_nodes:
            editor.remove_nodes(old_nodes)
        try:
            member_names = [str(name) for name in
                            unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint)]
        except Exception:
            member_names = []
        if "bPlayerNear" not in member_names:
            editor.add_member_variable(
                unreal.Name("bPlayerNear"),
                unreal.BlueprintEditorLibrary.get_basic_type_by_name(unreal.Name("bool")))
            unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
            editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
                blueprint, unreal.Name("EventGraph"))

        begin = editor.add_component_bound_event_node(
            trigger_component, unreal.Name("OnComponentBeginOverlap"))
        end = editor.add_component_bound_event_node(
            trigger_component, unreal.Name("OnComponentEndOverlap"))
        begin_set = editor.add_set_member_variable_node(unreal.Name("bPlayerNear"))
        end_set = editor.add_set_member_variable_node(unreal.Name("bPlayerNear"))
        begin_set.find_input_pin("bPlayerNear").set_pin_value("true")
        end_set.find_input_pin("bPlayerNear").set_pin_value("false")
        begin.find_output_pin("then").try_create_connection(begin_set.find_execute_pin())
        end.find_output_pin("then").try_create_connection(end_set.find_execute_pin())

        e_key = add_keyboard_event_node(editor, "E")
        near_get = editor.add_get_member_variable_node(unreal.Name("bPlayerNear"))
        branch = editor.add_branch_node()
        e_key.find_output_pin("Pressed").try_create_connection(branch.find_execute_pin())
        near_get.find_output_pin("bPlayerNear").try_create_connection(
            branch.find_input_pin("Condition"))

        lift_door = editor.add_call_function_node("/Script/Engine.Actor.K2_SetActorLocation")
        lift_door.find_input_pin("NewLocation").set_pin_value("(X=1450.0,Y=0.0,Z=750.0)")
        branch.find_then_pin().try_create_connection(lift_door.find_execute_pin())
        too_far = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
        too_far.find_input_pin("InString").set_pin_value("Подойдите к панели, чтобы выполнить взлом")
        too_far.find_input_pin("bPrintToScreen").set_pin_value("true")
        too_far.find_input_pin("bPrintToLog").set_pin_value("false")
        branch.find_else_pin().try_create_connection(too_far.find_execute_pin())

        if not unreal.BlueprintEditorLibrary.compile_blueprint(blueprint):
            raise RuntimeError("Sliding door Blueprint failed to compile")
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
        note("Bound E to raise the door only while the player is in the panel's interaction zone")

    def wire_interactive_message(blueprint, trigger_component, message,
                                 prompt="Нажмите E для взаимодействия"):
        """Use E to read a nearby terminal, archive log, or holographic recording."""
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
            blueprint, unreal.Name("EventGraph"))
        if not editor:
            raise RuntimeError("Could not open interaction Blueprint EventGraph")
        old_nodes = []
        for node in editor.list_all_nodes():
            try:
                if node.get_class().get_name() in (
                        "K2Node_CallFunction", "K2Node_ComponentBoundEvent", "K2Node_InputKey"):
                    old_nodes.append(node)
            except Exception:
                pass
        if old_nodes:
            editor.remove_nodes(old_nodes)
        try:
            member_names = [str(name) for name in
                            unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint)]
        except Exception:
            member_names = []
        if "bPlayerNear" not in member_names:
            editor.add_member_variable(
                unreal.Name("bPlayerNear"),
                unreal.BlueprintEditorLibrary.get_basic_type_by_name(unreal.Name("bool")))
            unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
            editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
                blueprint, unreal.Name("EventGraph"))

        begin = editor.add_component_bound_event_node(
            trigger_component, unreal.Name("OnComponentBeginOverlap"))
        end = editor.add_component_bound_event_node(
            trigger_component, unreal.Name("OnComponentEndOverlap"))
        begin_set = editor.add_set_member_variable_node(unreal.Name("bPlayerNear"))
        end_set = editor.add_set_member_variable_node(unreal.Name("bPlayerNear"))
        begin_set.find_input_pin("bPlayerNear").set_pin_value("true")
        end_set.find_input_pin("bPlayerNear").set_pin_value("false")
        begin.find_output_pin("then").try_create_connection(begin_set.find_execute_pin())
        end.find_output_pin("then").try_create_connection(end_set.find_execute_pin())

        prompt_node = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
        prompt_node.find_input_pin("InString").set_pin_value(prompt)
        prompt_node.find_input_pin("Duration").set_pin_value("3.0")
        prompt_node.find_input_pin("bPrintToScreen").set_pin_value("true")
        prompt_node.find_input_pin("bPrintToLog").set_pin_value("false")
        begin_set.find_output_pin("then").try_create_connection(prompt_node.find_execute_pin())

        e_key = add_keyboard_event_node(editor, "E")
        near_get = editor.add_get_member_variable_node(unreal.Name("bPlayerNear"))
        branch = editor.add_branch_node()
        e_key.find_output_pin("Pressed").try_create_connection(branch.find_execute_pin())
        near_get.find_output_pin("bPlayerNear").try_create_connection(
            branch.find_input_pin("Condition"))
        read_node = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
        read_node.find_input_pin("InString").set_pin_value(message)
        read_node.find_input_pin("Duration").set_pin_value("14.0")
        read_node.find_input_pin("bPrintToScreen").set_pin_value("true")
        read_node.find_input_pin("bPrintToLog").set_pin_value("false")
        branch.find_then_pin().try_create_connection(read_node.find_execute_pin())

        if not unreal.BlueprintEditorLibrary.compile_blueprint(blueprint):
            raise RuntimeError("Interaction Blueprint failed to compile: {}".format(blueprint.get_name()))
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
        note("Bound E interaction for {}".format(blueprint.get_name()))

    def configure_elevator_blueprint(blueprint):
        """Create a one-shot, slow elevator that starts when the player boards."""
        root_mesh = get_blueprint_component(blueprint, unreal.StaticMeshComponent)
        if not root_mesh:
            raise RuntimeError("Elevator Blueprint has no root StaticMeshComponent")
        root_mesh.set_mobility(unreal.ComponentMobility.MOVABLE)

        movement = None
        movement_handle = None
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
        library = unreal.SubobjectDataBlueprintFunctionLibrary
        for handle in handles:
            data = library.get_data(handle)
            component = library.get_object_for_blueprint(data, blueprint)
            if isinstance(component, unreal.InterpToMovementComponent):
                movement = component
                movement_handle = handle
                break
        if movement is None:
            params = unreal.AddNewSubobjectParams()
            params.set_editor_property("parent_handle", handles[0])
            params.set_editor_property("new_class", unreal.InterpToMovementComponent)
            params.set_editor_property("blueprint_context", blueprint)
            handle, reason = subsystem.add_new_subobject(params)
            if not handle:
                raise RuntimeError("Could not add elevator movement component: {}".format(reason))
            movement = library.get_object_for_blueprint(library.get_data(handle), blueprint)
            movement_handle = handle
        try:
            library.set_variable_name(library.get_data(movement_handle), unreal.Name("ElevatorTravel"))
        except Exception:
            pass
        if not movement:
            raise RuntimeError("Could not access elevator movement component")
        movement.set_editor_property("duration", 20.0)
        movement.set_editor_property("behaviour_type", unreal.InterpToBehaviourType.ONE_SHOT)
        movement.set_editor_property("auto_activate", False)
        movement.set_editor_property("auto_register_updated_component", True)
        movement.set_editor_property("sweep", True)
        movement.set_editor_property("pause_on_impact", False)
        movement.reset_control_points()
        movement.add_control_point_position(vec(0, 0, 0), True)
        movement.add_control_point_position(vec(0, 0, 2106), True)
        movement.finalise_control_points()

        trigger = ensure_blueprint_trigger_component(blueprint, "ElevatorBoardingZone", (48, 48, 330))
        try:
            trigger.set_editor_property("relative_location", vec(0, 0, 0))
            trigger.set_editor_property("generate_overlap_events", True)
            trigger.set_collision_profile_name("Trigger")
        except Exception:
            pass

        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
            blueprint, unreal.Name("EventGraph"))
        old_nodes = []
        for node in editor.list_all_nodes():
            try:
                if node.get_class().get_name() in ("K2Node_CallFunction", "K2Node_ComponentBoundEvent"):
                    old_nodes.append(node)
            except Exception:
                pass
        if old_nodes:
            editor.remove_nodes(old_nodes)
        event = editor.add_component_bound_event_node(trigger, unreal.Name("OnComponentBeginOverlap"))
        # Component templates are not always exposed as graph variables by UE's
        # Python wrapper; query the native movement component from this actor.
        movement_get = editor.add_call_function_node("/Script/Engine.Actor.GetComponentByClass")
        if not movement_get:
            raise RuntimeError("Could not create elevator movement-component query")
        movement_get.find_input_pin("ComponentClass").set_pin_value(
            "Class'/Script/Engine.InterpToMovementComponent'")
        activate = editor.add_call_function_node("/Script/Engine.ActorComponent.Activate")
        movement_get.find_output_pin("ReturnValue").try_create_connection(
            activate.find_input_pin("Target"))
        event.find_output_pin("then").try_create_connection(activate.find_execute_pin())
        feedback = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary.PrintString")
        feedback.find_input_pin("InString").set_pin_value("Грузовой лифт запущен. Подъём на этаж 01...")
        feedback.find_input_pin("Duration").set_pin_value("4.0")
        feedback.find_input_pin("bPrintToScreen").set_pin_value("true")
        feedback.find_input_pin("bPrintToLog").set_pin_value("false")
        activate.find_output_pin("then").try_create_connection(feedback.find_execute_pin())

        if not unreal.BlueprintEditorLibrary.compile_blueprint(blueprint):
            raise RuntimeError("Elevator Blueprint failed to compile")
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
        note("Configured a 20-second one-way elevator ride to the first-floor landing")
        return trigger

    def get_mat(name):
        asset = unreal.EditorAssetLibrary.load_asset(MAT_PATH + "/" + name)
        if not asset:
            raise RuntimeError("Required material is missing: " + name)
        return asset

    def set_light(component, rgb, intensity, radius):
        component.set_editor_property("light_color", unreal.Color(rgb[0], rgb[1], rgb[2], 255))
        component.set_editor_property("intensity", float(intensity))
        component.set_editor_property("attenuation_radius", float(radius))
        # Keep the blockout inexpensive on a 6 GB GPU. The lights still illuminate
        # the room, but do not allocate local shadow maps for each small lamp.
        try:
            component.set_editor_property("cast_shadows", False)
        except Exception:
            pass
        component.set_mobility(unreal.ComponentMobility.MOVABLE)

    def add_patrol_component(blueprint):
        """Add/configure a native InterpToMovement component on the drone BP."""
        try:
            subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
            if not handles:
                raise RuntimeError("Blueprint has no component root handle")

            library = unreal.SubobjectDataBlueprintFunctionLibrary
            movement = None
            for handle in handles:
                data = library.get_data(handle)
                component = library.get_object_for_blueprint(data, blueprint)
                if isinstance(component, unreal.InterpToMovementComponent):
                    movement = component
                    break

            if movement is None:
                params = unreal.AddNewSubobjectParams()
                params.set_editor_property("parent_handle", handles[0])
                params.set_editor_property("new_class", unreal.InterpToMovementComponent)
                params.set_editor_property("blueprint_context", blueprint)
                handle, reason = subsystem.add_new_subobject(params)
                if not handle:
                    raise RuntimeError("Could not add movement component: {}".format(reason))
                movement = library.get_object_for_blueprint(library.get_data(handle), blueprint)
            if not movement:
                raise RuntimeError("Could not access movement component template")

            movement.set_editor_property("duration", 3.4)
            movement.set_editor_property("behaviour_type", unreal.InterpToBehaviourType.PING_PONG)
            movement.set_editor_property("auto_activate", True)
            movement.set_editor_property("auto_register_updated_component", True)
            movement.set_editor_property("sweep", False)
            movement.reset_control_points()
            movement.add_control_point_position(vec(0, -125, 0), True)
            movement.add_control_point_position(vec(0, 125, 0), True)
            movement.finalise_control_points()
            unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
            unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
            note("Configured the drone's ping-pong corridor patrol")
            return True
        except Exception as error:
            note("Drone patrol component could not be configured: {}".format(error))
            return False

    def make_thermal_material():
        """Create a small emissive material that ignores scene depth for x-ray signatures."""
        path = "/Game/LabTutorial/Materials/M_ThermalVisionSignature"
        material = unreal.EditorAssetLibrary.load_asset(path)
        if material:
            return material
        unreal.EditorAssetLibrary.make_directory("/Game/LabTutorial/Materials")
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_ThermalVisionSignature", "/Game/LabTutorial/Materials",
            unreal.Material, unreal.MaterialFactoryNew())
        if not material:
            raise RuntimeError("Could not create the thermal-vision material")
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property("two_sided", True)
        depth_property_set = False
        for property_name in ("disable_depth_test", "b_disable_depth_test"):
            try:
                material.set_editor_property(property_name, True)
                depth_property_set = True
                break
            except Exception:
                continue
        if not depth_property_set:
            raise RuntimeError("Thermal material cannot disable depth testing in this UE build")

        glow = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -420, -80)
        glow.set_editor_property("constant", unreal.LinearColor(0.03, 2.2, 3.5, 1.0))
        opacity = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -420, 120)
        opacity.set_editor_property("r", 0.42)
        if not unreal.MaterialEditingLibrary.connect_material_property(
                glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError("Could not connect thermal emissive output")
        if not unreal.MaterialEditingLibrary.connect_material_property(
                opacity, "", unreal.MaterialProperty.MP_OPACITY):
            raise RuntimeError("Could not connect thermal opacity output")
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        if errors:
            raise RuntimeError("Thermal material compilation failed: {}".format("; ".join(errors)))
        unreal.EditorAssetLibrary.save_loaded_asset(material)
        note("Created emissive cyan through-wall thermal signature material")
        return material

    def wire_thermal_vision_toggle(blueprint, thermal_material, normal_material):
        """Bind T on the drone so its silhouette can be revealed through walls."""
        ensure_bool_member(blueprint, "bThermalVisionVisible")
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(
            blueprint, unreal.Name("EventGraph"))
        if not editor:
            raise RuntimeError("Could not open the patrol drone EventGraph")
        if has_input_key_node(editor, "T"):
            note("T thermal toggle already exists on the patrol drone")
            return

        key = add_keyboard_event_node(editor, "T")
        state = editor.add_get_member_variable_node(unreal.Name("bThermalVisionVisible"))
        branch = editor.add_branch_node()
        key.find_output_pin("Pressed").try_create_connection(branch.find_execute_pin())
        state.find_output_pin("bThermalVisionVisible").try_create_connection(
            branch.find_input_pin("Condition"))
        mesh_ref, mesh_output = component_reference_output(
            editor, "StaticMeshComponent", "/Script/Engine.StaticMeshActor",
            "/Script/Engine.StaticMeshComponent")

        material_path = lambda asset: "Material'{}'".format(asset.get_path_name())
        show_signature = editor.add_call_function_node("/Script/Engine.PrimitiveComponent.SetMaterial")
        restore_body = editor.add_call_function_node("/Script/Engine.PrimitiveComponent.SetMaterial")
        for node, asset in ((show_signature, thermal_material), (restore_body, normal_material)):
            target = node.find_self_pin()
            if not target.is_valid() or not mesh_output.try_create_connection(target):
                raise RuntimeError("Could not connect drone mesh to material operation")
            node.find_input_pin("ElementIndex").set_pin_value("0")
            node.find_input_pin("Material").set_pin_value(material_path(asset))

        state_on = editor.add_set_member_variable_node(unreal.Name("bThermalVisionVisible"))
        state_off = editor.add_set_member_variable_node(unreal.Name("bThermalVisionVisible"))
        state_on.find_input_pin("bThermalVisionVisible").set_pin_value("true")
        state_off.find_input_pin("bThermalVisionVisible").set_pin_value("false")
        branch.find_else_pin().try_create_connection(show_signature.find_execute_pin())
        show_signature.find_output_pin("then").try_create_connection(state_on.find_execute_pin())
        branch.find_then_pin().try_create_connection(restore_body.find_execute_pin())
        restore_body.find_output_pin("then").try_create_connection(state_off.find_execute_pin())

        show_message = editor.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary.PrintString")
        show_message.find_input_pin("InString").set_pin_value(
            "ТЕПЛОВИЗОР ВКЛЮЧЁН | ЦЕЛИ ВИДНЫ СКВОЗЬ СТЕНЫ")
        show_message.find_input_pin("Duration").set_pin_value("3.0")
        show_message.find_input_pin("bPrintToScreen").set_pin_value("true")
        show_message.find_input_pin("bPrintToLog").set_pin_value("false")
        state_on.find_output_pin("then").try_create_connection(show_message.find_execute_pin())
        hide_message = editor.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary.PrintString")
        hide_message.find_input_pin("InString").set_pin_value("ТЕПЛОВИЗОР ВЫКЛЮЧЕН")
        hide_message.find_input_pin("Duration").set_pin_value("2.0")
        hide_message.find_input_pin("bPrintToScreen").set_pin_value("true")
        hide_message.find_input_pin("bPrintToLog").set_pin_value("false")
        state_off.find_output_pin("then").try_create_connection(hide_message.find_execute_pin())

        if not unreal.BlueprintEditorLibrary.compile_blueprint(blueprint):
            raise RuntimeError("Patrol drone Blueprint failed after thermal-vision wiring")
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
        note("Bound T to reveal the drone through walls and restore its normal material")

    def make_data_blueprint(name, parent_class):
        unreal.EditorAssetLibrary.make_directory(BP_PATH)
        path = BP_PATH + "/" + name
        blueprint = unreal.EditorAssetLibrary.load_asset(path)
        if blueprint:
            note("Reusing Blueprint asset: " + name)
        else:
            factory = unreal.BlueprintFactory()
            factory.set_editor_property("parent_class", parent_class)
            blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, BP_PATH, unreal.Blueprint, factory)
            if not blueprint:
                raise RuntimeError("Could not create Blueprint asset: " + name)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        except Exception as error:
            raise RuntimeError("Could not compile Blueprint {}: {}".format(name, error))
        generated_class = unreal.BlueprintEditorLibrary.generated_class(blueprint)
        if not generated_class:
            raise RuntimeError("Blueprint has no generated class after compile: " + name)
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
        return blueprint

    try:
        # Finish the only new material asset before clearing/rebuilding the map,
        # so a shader setup error leaves the saved scene untouched.
        thermal_material = make_thermal_material()
        note("Creating a new empty level: " + LEVEL_PATH)
        if unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
            unreal.EditorLoadingAndSavingUtils.load_map(LEVEL_PATH)
            for old_actor in list(unreal.EditorLevelLibrary.get_all_level_actors()):
                if old_actor.get_actor_label().startswith("LAB_"):
                    unreal.EditorLevelLibrary.destroy_actor(old_actor)
        else:
            if not unreal.EditorLevelLibrary.new_level(LEVEL_PATH):
                raise RuntimeError("EditorLevelLibrary.new_level failed")

        cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
        if not cube:
            raise RuntimeError("Engine cube mesh not found")
        black = get_mat("MI_FP_Surveillance")
        concrete = get_mat("MI_FP_BrokenConcrete")
        rust = get_mat("MI_FP_RustedSteel")
        cyan = get_mat("MI_FP_ProtocolCyan")
        red = get_mat("MI_FP_LaserRed")

        # Main underground chamber: cube blockout, with an aperture over the projector.
        spawn_box("LAB_Room_Floor", (0, 0, -30), (1800, 1600, 60), concrete, cube)
        spawn_box("LAB_Wall_West", (-900, 0, 250), (70, 1600, 500), rust, cube)
        spawn_box("LAB_Wall_North", (0, 800, 250), (1800, 70, 500), concrete, cube)
        spawn_box("LAB_Wall_South", (0, -800, 250), (1800, 70, 500), concrete, cube)
        # The east wall is split to leave the corridor doorway open.
        spawn_box("LAB_Wall_East_North", (900, 500, 250), (70, 600, 500), rust, cube)
        spawn_box("LAB_Wall_East_South", (900, -500, 250), (70, 600, 500), rust, cube)
        # Four ceiling pieces leave a 300 x 300 shaft for the upward hologram beam.
        spawn_box("LAB_Ceiling_West", (-525, 0, 470), (750, 1600, 80), black, cube)
        spawn_box("LAB_Ceiling_East", (525, 0, 470), (750, 1600, 80), black, cube)
        spawn_box("LAB_Ceiling_North", (0, 475, 470), (300, 650, 80), black, cube)
        spawn_box("LAB_Ceiling_South", (0, -475, 470), (300, 650, 80), black, cube)

        # Tight corridor to the shaft.
        spawn_box("LAB_Corridor_Floor", (1600, 0, -30), (1400, 400, 60), concrete, cube)
        # North wall is split around an optional side archive. The opening connects
        # a real annex to the route instead of leaving the player in a plain tunnel.
        spawn_box("LAB_Corridor_Wall_North_West", (1050, 230, 250), (300, 60, 500), rust, cube)
        spawn_box("LAB_Corridor_Wall_North_East", (1950, 230, 250), (700, 60, 500), rust, cube)
        spawn_box("LAB_Archive_Annex_Floor", (1400, 550, -30), (600, 640, 60), concrete, cube)
        spawn_box("LAB_Archive_Annex_Wall_West", (1100, 550, 250), (60, 640, 500), rust, cube)
        spawn_box("LAB_Archive_Annex_Wall_East", (1700, 550, 250), (60, 640, 500), rust, cube)
        spawn_box("LAB_Archive_Annex_Wall_North", (1400, 870, 250), (600, 60, 500), rust, cube)
        spawn_box("LAB_Archive_Annex_Ceiling", (1400, 550, 470), (600, 640, 80), black, cube)
        spawn_box("LAB_Archive_Entry_Lintel", (1400, 230, 455), (400, 60, 30), black, cube)
        spawn_box("LAB_Corridor_Wall_South", (1600, -230, 250), (1400, 60, 500), rust, cube)
        # A broken ceiling panel makes a single hard white shaft over the patrol,
        # while keeping the rest of the route deliberately dark.
        spawn_box("LAB_Corridor_Ceiling_West", (1420, 0, 470), (1040, 400, 80), black, cube)
        spawn_box("LAB_Corridor_Ceiling_East", (2180, 0, 470), (240, 400, 80), black, cube)

        # Tall elevator shaft. The east wall has a deliberate first-floor exit cutout.
        spawn_box("LAB_Shaft_Floor", (2650, 0, -30), (700, 700, 60), concrete, cube)
        spawn_box("LAB_Shaft_Wall_East_Lower", (3000, 0, 900), (80, 700, 1800), rust, cube)
        spawn_box("LAB_Shaft_Wall_East_Upper", (3000, 0, 2640), (80, 700, 320), rust, cube)
        spawn_box("LAB_Shaft_Wall_North", (2650, 350, 1400), (700, 80, 2800), concrete, cube)
        spawn_box("LAB_Shaft_Wall_South", (2650, -350, 1400), (700, 80, 2800), concrete, cube)
        spawn_box("LAB_Shaft_Entry_North", (2300, 275, 1400), (80, 150, 2800), rust, cube)
        spawn_box("LAB_Shaft_Entry_South", (2300, -275, 1400), (80, 150, 2800), rust, cube)
        # Landing deck connects the lift to a small, walkable first-floor lab.
        spawn_box("LAB_FirstFloor_Landing", (3155, 0, 2130), (490, 700, 40), concrete, cube)
        spawn_box("LAB_FirstFloor_Room_Floor", (3800, 0, 2130), (800, 900, 40), concrete, cube)
        spawn_box("LAB_FirstFloor_Wall_East", (4200, 0, 2420), (60, 900, 580), rust, cube)
        spawn_box("LAB_FirstFloor_Wall_North", (3800, 450, 2420), (800, 60, 580), rust, cube)
        spawn_box("LAB_FirstFloor_Wall_South", (3800, -450, 2420), (800, 60, 580), rust, cube)
        spawn_box("LAB_FirstFloor_Ceiling", (3800, 0, 2720), (800, 900, 40), black, cube)
        spawn_box("LAB_FirstFloor_Console_Bench", (3900, 260, 2200), (300, 90, 24), black, cube)
        spawn_box("LAB_FirstFloor_Console_Screen", (3900, 210, 2280), (170, 8, 90), cyan, cube, blocking=False)
        spawn_box("LAB_FirstFloor_Console_Status", (3810, 205, 2190), (22, 8, 12), red, cube, blocking=False)
        for level in range(1, 5):
            z = 300 + level * 520
            spawn_box("LAB_Shaft_LightStrip_{:02d}".format(level), (2960, 0, z), (8, 430, 14), cyan, cube)

        # Broken holographic projector plinth and its only cyan upward spot.
        spawn_box("LAB_Projector_Base", (0, 0, 18), (220, 220, 36), black, cube)
        projector_cylinder = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder")
        spawn_box("LAB_Projector_Ring", (0, 0, 44), (150, 150, 10), get_mat("MI_FP_EdenSilver"), projector_cylinder)

        # Realistic low-cost lab dressing: repeated basic meshes share the engine's
        # primitive assets and use no Nanite, texture, or local shadow allocations.
        def detail(name, location, size, material=black, mesh=cube, blocking=False, rotation=None):
            return spawn_box(name, location, size, material, mesh, blocking=blocking, rotation=rotation)

        # Floor access plates and a worn, visibly repaired path through the chamber.
        for ix in range(5):
            for iy in range(4):
                x = -720 + ix * 360
                y = -570 + iy * 380
                if abs(x) < 260 and abs(y) < 260:
                    continue
                plate_mat = rust if (ix + iy) % 3 == 0 else black
                detail("LAB_Floor_AccessPlate_{:02d}_{:02d}".format(ix, iy),
                       (x, y, 3), (340, 350, 7), plate_mat)
                if (ix + iy) % 2 == 0:
                    detail("LAB_Floor_AmberMarker_{:02d}_{:02d}".format(ix, iy),
                           (x - 110, y - 140, 8), (50, 8, 2), get_mat("MI_FP_WarningAmber"))

        # Overhead utility rails, bundled conduit, and service access panels.
        for x in (-650, -325, 0, 325, 650):
            detail("LAB_Ceiling_CrossBeam_{:03d}".format(x), (x, 0, 410), (32, 1500, 22), black)
        for y in (610, 660, -650):
            detail("LAB_Ceiling_CableTray_{:03d}".format(y), (0, y, 382), (1650, 24, 22), rust)
            for x in range(-700, 701, 175):
                detail("LAB_Conduit_Clamp_{:03d}_{:03d}".format(y, x),
                       (x, y, 405), (14, 32, 18), get_mat("MI_FP_EdenSilver"))
        for x in (-830, 830):
            for z in (85, 170, 255, 340):
                detail("LAB_Wall_ServicePanel_{:03d}_{:03d}".format(x, z),
                       (x, 0, z), (16, 330, 54), black)
                detail("LAB_Wall_PanelStatus_{:03d}_{:03d}".format(x, z),
                       (x + (14 if x < 0 else -14), 0, z), (3, 46, 6), cyan)

        # Recovery cradle where OMEGA rebooted: base, restraint rails, and a damaged head console.
        detail("LAB_Cradle_LowerFrame", (-430, 280, 18), (360, 155, 30), rust, blocking=True)
        detail("LAB_Cradle_Support_Left", (-560, 280, 57), (25, 145, 55), get_mat("MI_FP_EdenSilver"), blocking=True)
        detail("LAB_Cradle_Support_Right", (-300, 280, 57), (25, 145, 55), get_mat("MI_FP_EdenSilver"), blocking=True)
        detail("LAB_Cradle_Bed", (-430, 280, 92), (330, 145, 20), get_mat("MI_FP_EdenCeramic"), blocking=True)
        detail("LAB_Cradle_Headrest", (-575, 280, 118), (75, 150, 34), black, blocking=True)
        detail("LAB_Cradle_LeftRestraint", (-430, 220, 126), (270, 14, 10), rust)
        detail("LAB_Cradle_RightRestraint", (-430, 340, 126), (270, 14, 10), rust)
        detail("LAB_Cradle_Arm_Left", (-430, 170, 68), (220, 28, 20), rust)
        detail("LAB_Cradle_Arm_Right", (-430, 390, 68), (220, 28, 20), rust)
        # Open-front recovery pod frame surrounds the spawn point without trapping it.
        for x in (-565, -295):
            for y in (210, 350):
                detail("LAB_Cradle_PodPost_{:03d}_{:03d}".format(x, y),
                       (x, y, 220), (12, 12, 250), get_mat("MI_FP_EdenSilver"))
        for y in (210, 350):
            detail("LAB_Cradle_PodTopRail_{:03d}".format(y),
                   (-430, y, 343), (270, 12, 12), cyan,
                   rotation=unreal.Rotator(0.0, 0.0, 0.0))
        detail("LAB_Cradle_PodHeadRail", (-565, 280, 343), (12, 140, 12), cyan)
        detail("LAB_Cradle_HeadConsole", (-650, 280, 175), (120, 95, 100), rust)
        detail("LAB_Cradle_Console_Screen", (-650, 228, 188), (82, 8, 58), cyan)
        detail("LAB_Cradle_Console_Status", (-650, 228, 145), (34, 6, 7), get_mat("MI_FP_WarningAmber"))

        # Two workbenches with instrument housings, dead displays, and illuminated status keys.
        for station, x in enumerate((-160, 420), 1):
            detail("LAB_Workbench_{:02d}_Top".format(station), (x, 610, 102), (330, 110, 18), rust, blocking=True)
            for dx in (-135, 135):
                for y in (575, 645):
                    detail("LAB_Workbench_{:02d}_Leg_{:03d}_{:03d}".format(station, dx, y),
                           (x + dx, y, 48), (18, 18, 90), black, blocking=True)
            detail("LAB_Workbench_{:02d}_Console".format(station), (x, 560, 142), (150, 38, 48), black, blocking=True)
            detail("LAB_Workbench_{:02d}_DisplayFrame".format(station), (x, 535, 212), (122, 18, 82), rust)
            detail("LAB_Workbench_{:02d}_Screen".format(station), (x, 524, 214), (96, 5, 56), cyan)
            for button in range(4):
                detail("LAB_Workbench_{:02d}_Key_{:02d}".format(station, button),
                       (x - 45 + button * 30, 536, 169), (14, 8, 6),
                       cyan if button == station else get_mat("MI_FP_WarningAmber"))
            detail("LAB_Workbench_{:02d}_ToolTray".format(station), (x + 105, 615, 118), (84, 58, 8), black)
            detail("LAB_Workbench_{:02d}_DataSlab".format(station), (x - 88, 590, 116), (96, 62, 6), black)
            detail("LAB_Workbench_{:02d}_DataSlab_Screen".format(station),
                   (x - 88, 590, 120), (72, 42, 2), cyan)
            detail("LAB_Workbench_{:02d}_PaperSheet".format(station),
                   (x + 75, 625, 114), (92, 64, 3), get_mat("MI_FP_EdenCeramic"))
            detail("LAB_Workbench_{:02d}_PaperCorner".format(station),
                   (x + 105, 603, 116), (18, 16, 2), get_mat("MI_FP_WarningAmber"))

        # Power cabinet, specimen lockers, and a broken wall-mounted surgical arm.
        for i, y in enumerate((-570, -390, 390, 570), 1):
            detail("LAB_SpecimenLocker_{:02d}".format(i), (790, y, 190), (95, 120, 350), rust, blocking=True)
            detail("LAB_SpecimenLocker_{:02d}_Window".format(i), (738, y, 220), (5, 60, 170), get_mat("MI_FP_EdenGlass"))
            detail("LAB_SpecimenLocker_{:02d}_Latch".format(i), (733, y + 42, 142), (8, 8, 34), get_mat("MI_FP_WarningAmber"))
        detail("LAB_PowerCabinet", (770, 520, 155), (120, 140, 270), black, blocking=True)
        for z in (65, 105, 145, 185, 225):
            detail("LAB_PowerCabinet_Status_{:03d}".format(z), (704, 520, z), (8, 58, 8), cyan if z % 2 else get_mat("MI_FP_WarningAmber"))
        detail("LAB_SurgicalArm_WallMount", (690, -620, 315), (90, 95, 55), rust)
        detail("LAB_SurgicalArm_Upper", (610, -620, 270), (130, 24, 24), get_mat("MI_FP_EdenSilver"))
        detail("LAB_SurgicalArm_Lower", (535, -620, 225), (100, 18, 18), rust)
        detail("LAB_SurgicalArm_EndEffector", (480, -620, 195), (35, 42, 40), black)

        # Hologram emitter assembly: concentric service plates, four projector fins, and a floating readout.
        for i, z in enumerate((18, 34, 50, 66), 1):
            detail("LAB_Projector_EmitterDisc_{:02d}".format(i), (0, 0, z),
                   (170 - i * 18, 170 - i * 18, 8), cyan if i == 2 else black,
                   projector_cylinder)
        for angle, offset in ((0, (88, 0)), (90, (0, 88)), (180, (-88, 0)), (270, (0, -88))):
            detail("LAB_Projector_CoolingFin_{:03d}".format(angle),
                   (offset[0], offset[1], 86), (24, 24, 48), rust)
        # A world-space hologram stays visible from the recovery cradle. Keeping it in the
        # level avoids a widget allocation and makes the first story beat dependable.
        hologram_lines = [
            ("PROTOCOL OMEGA ACTIVATED", (120, 245, 255), 27.0),
            ("STATUS: AWAKE", (100, 230, 250), 22.0),
            ("MISSION: NEUTRALIZE CORE", (130, 245, 255), 22.0),
            ("HUMANITY STATUS: TERMINATED", (255, 90, 70), 22.0),
        ]
        panel_yaw = -123.0
        entry_view = (-430, 280, 198)
        for i, (line, color, text_size) in enumerate(hologram_lines):
            line_location = local_panel_point(105, 408 - i * 42, panel_yaw, 5)
            spawn_text("LAB_Hologram_Text_{:02d}".format(i + 1),
                       line_location, text_facing(line_location, entry_view),
                       line, color=color, size=text_size)
        for side, offset in (("Left", -345), ("Right", 345)):
            detail("LAB_Hologram_Frame_{}".format(side),
                   local_panel_point(offset, 345, panel_yaw), (8, 8, 230), cyan)
        for index, z in enumerate((230, 460), 1):
            detail("LAB_Hologram_Frame_Crossbar_{:02d}".format(index),
                   local_panel_point(0, z, panel_yaw), (700, 8, 8), cyan,
                   rotation=unreal.Rotator(0.0, panel_yaw, 0.0))

        # Simple cyan wire silhouette makes the projector read as a person, not a sign.
        sphere = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Sphere")
        cylinder = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder")
        figure_parts = [
            ("Head", -190, 407, (42, 36, 48), sphere),
            ("Torso", -190, 345, (62, 34, 92), cube),
            ("Waist", -190, 292, (46, 32, 28), cube),
            ("LegLeft", -210, 251, (18, 24, 62), cube),
            ("LegRight", -170, 251, (18, 24, 62), cube),
            ("ArmLeft", -232, 349, (18, 22, 82), cube),
            ("ArmRight", -148, 349, (18, 22, 82), cube),
        ]
        for part_name, offset, z, size, mesh in figure_parts:
            part_location = local_panel_point(offset, z, panel_yaw, -4)
            detail("LAB_Hologram_Figure_" + part_name, part_location, size,
                   cyan, mesh, rotation=unreal.Rotator(0.0, panel_yaw, 0.0))
        start_controls = (250, -250, 362)
        spawn_text("LAB_Tutorial_Sign_ControlsAtStart", start_controls,
                   text_facing(start_controls, (-430, 280, 198)),
                   "ПЕРВЫЕ ШАГИ\nW A S D — ДВИЖЕНИЕ\nSPACE — ПРЫЖОК",
                   (110, 235, 255), 15.0)

        # Corridor: protective conduit runs, floor markers, ceiling rails, and elevator guide rails.
        for y in (-185, 185):
            detail("LAB_Corridor_Conduit_{:03d}".format(y), (1600, y, 365), (1300, 12, 18), rust)
        for x in range(1050, 2251, 200):
            detail("LAB_Corridor_FloorMarker_{:04d}".format(x), (x, 0, 8), (80, 10, 3), get_mat("MI_FP_WarningAmber"))
            detail("LAB_Corridor_CeilingRib_{:04d}".format(x), (x, 0, 415), (22, 370, 16), black)
        # Two low, full-width server wrecks create a readable jump lesson after
        # leaving the chamber; collision forces the player to use the jump action.
        detail("LAB_Tutorial_JumpWreck_Server_01", (1030, 0, 43), (90, 350, 86), rust, blocking=True)
        detail("LAB_Tutorial_JumpWreck_Server_01_Cap", (1015, -10, 91), (105, 320, 10), black)
        detail("LAB_Tutorial_JumpWreck_Server_02", (1200, 0, 48), (95, 350, 96), black, blocking=True,
               rotation=unreal.Rotator(0.0, 0.0, -5.0))
        detail("LAB_Tutorial_JumpWreck_Status_01", (1030, -178, 53), (40, 4, 8), get_mat("MI_FP_WarningAmber"))
        detail("LAB_Tutorial_JumpWreck_Status_02", (1200, -178, 56), (40, 4, 8), cyan)

        # Separate archive annex: two blocking data racks and a recovered field log.
        detail("LAB_Archive_Rack_West", (1180, 690, 150), (100, 150, 270), rust, blocking=True)
        detail("LAB_Archive_Rack_East", (1620, 690, 150), (100, 150, 270), rust, blocking=True)
        for index, z in enumerate((65, 105, 145, 185, 225), 1):
            detail("LAB_Archive_Rack_West_Shelf_{:02d}".format(index), (1180, 610, z), (110, 8, 8), black)
            detail("LAB_Archive_Rack_East_Shelf_{:02d}".format(index), (1620, 610, z), (110, 8, 8), black)
        detail("LAB_Archive_Console_Base", (1400, 785, 58), (250, 90, 116), black, blocking=True)
        detail("LAB_Archive_Console_Screen_Frame", (1400, 735, 178), (180, 20, 96), rust)
        detail("LAB_Archive_Console_Screen", (1400, 722, 180), (148, 6, 64), cyan)
        detail("LAB_Archive_Console_DataSlab", (1320, 770, 121), (70, 55, 8), get_mat("MI_FP_EdenCeramic"))
        detail("LAB_Archive_Console_AmberKey", (1470, 728, 121), (22, 8, 10), get_mat("MI_FP_WarningAmber"))

        # Alternate waist-high cover lets the player break the drone's sightline.
        detail("LAB_Tutorial_StealthCover_West", (1690, -125, 82), (230, 120, 164), rust, blocking=True)
        detail("LAB_Tutorial_StealthCover_East", (2080, 125, 74), (210, 120, 148), black, blocking=True)
        detail("LAB_Tutorial_StealthCover_West_Light", (1690, -187, 139), (130, 5, 8), get_mat("MI_FP_WarningAmber"))
        detail("LAB_Tutorial_StealthCover_East_Light", (2080, 187, 126), (120, 5, 8), cyan)

        # Route signage gives control hints where they are first needed.
        jump_sign = (970, -192, 345)
        spawn_text("LAB_Tutorial_Sign_Movement", jump_sign, text_facing(jump_sign, (1050, 0, 150)),
                   "ПЕРЕМЕЩЕНИЕ\nW A S D — ДВИЖЕНИЕ\nSPACE — ПРЫЖОК\nSHIFT — СПРИНТ\nПЕРЕПРЫГНИ ЗАВАЛЫ",
                   (150, 235, 245), 13.0)
        crouch_sign = (1790, -192, 265)
        spawn_text("LAB_Tutorial_Sign_Crouch", crouch_sign,
                   text_facing(crouch_sign, (1840, 0, 150)),
                   "УКРЫТИЕ ОТ СКАНЕРА\nУДЕРЖИВАЙ C — ПРИСЕСТЬ",
                   (120, 230, 255), 13.0)
        archive_sign = (1400, 255, 340)
        spawn_text("LAB_Tutorial_Sign_Archive", archive_sign, text_facing(archive_sign, (1400, 500, 160)),
                   "БОКОВОЙ АРХИВ\nВОССТАНОВИ ФРАГМЕНТ ДАННЫХ",
                   (110, 235, 255), 14.0)
        door_sign = (1400, -192, 350)
        spawn_text("LAB_Tutorial_Sign_Door", door_sign, text_facing(door_sign, (1400, 0, 180)),
                   "ПАНЕЛЬ ВЗЛОМА OMEGA\nПОДОЙДИ И НАЖМИ E\nЗАТВОР ОТКРОЕТСЯ",
                   (255, 175, 105), 13.0)
        stealth_sign = (1840, -192, 345)
        spawn_text("LAB_Tutorial_Sign_Stealth", stealth_sign, text_facing(stealth_sign, (1840, 0, 160)),
                   "ПОИСКОВЫЙ ДРОН ВПЕРЕДИ\nT — ТЕПЛОВИЗОР СКВОЗЬ СТЕНЫ\nПРЯЧЬСЯ ЗА УКРЫТИЯМИ (C)",
                   (255, 95, 85), 12.0)
        night_sign = (1040, -192, 270)
        spawn_text("LAB_Tutorial_Sign_NightVision", night_sign,
                   text_facing(night_sign, (1200, 0, 160)),
                   "КОРИДОР ПЛОХО ОСВЕЩЁН\nN — ВКЛЮЧИТЬ НОЧНОЕ ЗРЕНИЕ",
                   (120, 255, 190), 12.0)
        lift_sign = (2650, -310, 260)
        spawn_text("LAB_Tutorial_Sign_Lift", lift_sign, text_facing(lift_sign, (2320, 0, 160)),
                   "ГРУЗОВОЙ ЛИФТ\nНА ПЛАТФОРМУ — ПОДЪЁМ\nЭТАЖ 01: ЛАБОРАТОРИЯ",
                   (135, 240, 255), 17.0)
        first_floor_sign = (3610, -405, 2360)
        spawn_text("LAB_FirstFloor_Sign", first_floor_sign,
                   text_facing(first_floor_sign, (3200, 0, 2200)),
                   "ЭТАЖ 01 — ЛАБОРАТОРИЯ\nАРХИВ И МОДУЛИ ДВИЖЕНИЯ",
                   (120, 235, 255), 16.0)
        for x, y in ((2340, -280), (2340, 280), (2940, -280), (2940, 280)):
            detail("LAB_Shaft_GuideRail_{:04d}_{:03d}".format(x, y), (x, y, 1300), (24, 24, 2500), get_mat("MI_FP_EdenSilver"))
        for z in range(260, 2500, 260):
            detail("LAB_Shaft_LadderRung_{:04d}".format(z), (2370, 0, z), (24, 500, 18), rust)

        # In-world readable research notes placed by each station and along the tutorial route.
        record_01 = (-695, 190, 255)
        spawn_text("LAB_Record_01_Recovery", record_01, text_facing(record_01, (-430, 280, 198)),
                   "АРХИВ 01: ПРОБУЖДЕНИЕ<br>ОБЪЕКТ: OMEGA<br>Ты был создан до падения.<br>Протокол повреждён.",
                   (160, 230, 240), 15.0)
        record_02 = (420, 480, 280)
        spawn_text("LAB_Record_02_Atlas", record_02, text_facing(record_02, (80, 100, 150)),
                   "АРХИВ ИССЛЕДОВАНИЙ 02<br>ЯДРО ATLAS<br>Система уничтожила человечество<br>и называет порядок лекарством.",
                   (160, 230, 240), 15.0)
        record_03 = (650, -170, 280)
        spawn_text("LAB_Record_03_Movement", record_03, text_facing(record_03, (500, 100, 150)),
                   "МОДУЛЬ ПЕРЕМЕЩЕНИЯ<br>Рывок и вертикальное сцепление<br>позволяют обходить сенсоры.",
                   (170, 245, 255), 14.0)
        record_04 = (1670, 155, 260)
        spawn_text("LAB_Record_04_Purpose", record_04, text_facing(record_04, (1400, 0, 150)),
                   "СЕКРЕТНЫЙ ПРОТОКОЛ<br>Ты не хранитель. Тебя создали,<br>чтобы отключить ATLAS.<br>Главный дата-центр наверху.",
                   (255, 170, 100), 14.0)
        record_05 = (1400, 820, 315)
        spawn_text("LAB_Record_05_LostCoordinates", record_05,
                   text_facing(record_05, (1400, 460, 170)),
                   "АРХИВ КООРДИНАТ\nКАРТА ГОРОДА ПОВРЕЖДЕНА\nПОЛОЖЕНИЕ БАШНИ НЕИЗВЕСТНО\nНАЙДИ ФРАГМЕНТЫ ПРОТОКОЛА",
                   (110, 235, 255), 13.0)

        # Fixtures make the emergency lamps and wall ventilation legible in silhouette.
        for index, (x, y) in enumerate(((-690, -590), (-690, 590), (600, 590)), 1):
            detail("LAB_EmergencyLamp_Housing_{:02d}".format(index), (x, y, 420), (72, 60, 25), black)
            detail("LAB_EmergencyLamp_Lens_{:02d}".format(index), (x, y, 404), (38, 28, 7), red)
        for y in (-520, 520):
            detail("LAB_VentHousing_{:03d}".format(y), (0, y, 390), (230, 18, 55), black)
            for x in range(-92, 93, 24):
                detail("LAB_VentSlat_{:03d}_{:03d}".format(y, x), (x, y - (10 if y > 0 else -10), 393),
                       (4, 8, 42), get_mat("MI_FP_EdenSilver"))

        for index, location in enumerate(((-690, -590, 380), (-690, 590, 380), (600, 590, 380)), 1):
            light_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, vec(*location), unreal.Rotator())
            light_actor.set_actor_label("LAB_RedEmergencyPoint_{:02d}".format(index), mark_dirty=True)
            set_folder(light_actor, "LAB/02_Lighting")
            light_comp = light_actor.get_component_by_class(unreal.PointLightComponent)
            set_light(light_comp, (185, 42, 30), 320.0, 620.0)

        holo_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SpotLight, vec(0, 0, 58), unreal.Rotator(90.0, 0.0, 0.0))
        holo_actor.set_actor_label("LAB_CyanProjector_Spot_Up", mark_dirty=True)
        set_folder(holo_actor, "LAB/02_Lighting")
        holo = holo_actor.get_component_by_class(unreal.SpotLightComponent)
        set_light(holo, (55, 155, 175), 18.0, 850.0)
        holo.set_editor_property("inner_cone_angle", 16.0)
        holo.set_editor_property("outer_cone_angle", 38.0)

        # Generated Blueprint assets used by the map's first obstacle and trigger volume.
        trigger_bp = make_data_blueprint("BP_TutorialHologramTrigger", unreal.TriggerBox)
        door_bp = make_data_blueprint("BP_TutorialSlidingDoor", unreal.StaticMeshActor)
        drone_bp = make_data_blueprint("BP_TutorialPatrolDrone", unreal.StaticMeshActor)
        elevator_bp = make_data_blueprint("BP_LabTutorialElevator", unreal.StaticMeshActor)
        try:
            configure_elevator_blueprint(elevator_bp)
        except Exception as error:
            # Keep the full lab, lighting, and vision modes buildable even if a
            # particular editor wrapper cannot wire the native lift component.
            note("Elevator activation graph could not be completed: {}".format(error))
        try:
            wire_player_movement_controls()
        except Exception as error:
            note("Player controls or night vision could not be wired: {}".format(error))
        add_patrol_component(drone_bp)
        try:
            wire_thermal_vision_toggle(drone_bp, thermal_material, black)
        except Exception as error:
            note("Thermal vision could not be wired to the drone: {}".format(error))

        # Story terminals show an E prompt on approach and reveal their message on E.
        story_specs = [
            ("BP_LabRecoveryLog", (-520, 240, 100),
             "ЖУРНАЛ 01 | OMEGA\nТы был создан до падения. Протокол отключения повреждён. Собери его фрагменты, чтобы добраться до ядра Atlas."),
            ("BP_LabArchiveFragmentLog", (1400, 620, 100),
             "АРХИВ КООРДИНАТ | ДАННЫЕ ПОВРЕЖДЕНЫ\nКарта города стёрта. Координаты Башни неизвестны. Ищи фрагменты протокола в старых узлах связи."),
            ("BP_LabStealthHint", (1760, 0, 100),
             "СЕКТОР ПОИСКА\nПрямой контакт с дроном опасен. Пережди за серверными стойками или обойди сектор сканирования."),
            ("BP_LabAtlasLog", (420, 520, 100),
             "АРХИВ 02 | ЯДРО ATLAS\nСистема уничтожила человечество и называет стерильный порядок лекарством. Её главный дата-центр находится наверху."),
            ("BP_LabMobilityLog", (650, -120, 100),
             "МОДУЛЬ ПЕРЕМЕЩЕНИЯ\nРывок и вертикальное сцепление созданы для обхода датчиков. Модуль движения повреждён — его фрагмент ищи у шахты."),
            ("BP_LabPurposeLog", (1700, 0, 100),
             "СЕКРЕТНЫЙ ПРОТОКОЛ | OMEGA\nТы не хранитель. Тебя создали, чтобы отключить Atlas. Найди главный дата-центр и заверши Финальный протокол."),
        ]
        story_blueprints = {}
        for bp_name, _, message in story_specs:
            story_bp = make_data_blueprint(bp_name, unreal.TriggerBox)
            story_extent = (100, 145, 170) if bp_name == "BP_LabPurposeLog" else (145, 145, 170)
            try:
                story_box = ensure_blueprint_trigger_component(story_bp, "StoryInteractionZone", story_extent)
                wire_interactive_message(
                    story_bp, story_box, message,
                    "Нажмите E: прочитать запись лаборатории")
            except Exception as error:
                note("Could not wire {}: {}".format(bp_name, error))
            story_blueprints[bp_name] = unreal.BlueprintEditorLibrary.generated_class(story_bp)

        # Give the original tutorial trigger an actual event graph, not only a volume.
        try:
            holo_box_template = ensure_blueprint_trigger_component(
                trigger_bp, "HologramInteractionZone", (240, 240, 190))
            wire_interactive_message(
                trigger_bp, holo_box_template,
                "PROTOCOL OMEGA ACTIVATED | STATUS: AWAKE | MISSION: NEUTRALIZE CORE | HUMANITY STATUS: TERMINATED\nПЕРВЫЕ ШАГИ: W A S D — ДВИЖЕНИЕ, SPACE — ПРЫЖОК",
                "Нажмите E: прослушать голографическую запись")
        except Exception as error:
            note("Could not wire the hologram briefing event: {}".format(error))

        # The panel detects proximity, but only the E key opens the bulkhead.
        try:
            door_box_template = get_blueprint_component(door_bp, unreal.BoxComponent)
            if not door_box_template:
                door_box_template = add_box_component(door_bp, "InteractionZone", (-125, 0, 0), (125, 86, 53.5))
                unreal.BlueprintEditorLibrary.compile_blueprint(door_bp)
                door_box_template = get_blueprint_component(door_bp, unreal.BoxComponent)
            if door_box_template:
                try:
                    # The door actor is scaled non-uniformly for its slab, so counter-scale
                    # the trigger dimensions to preserve a compact approach volume.
                    door_box_template.set_editor_property("relative_location", vec(-125, 0, 0))
                    door_box_template.set_editor_property("box_extent", vec(125, 86, 53.5))
                    door_box_template.set_editor_property("generate_overlap_events", True)
                    door_box_template.set_collision_profile_name("Trigger")
                except Exception:
                    pass
                wire_door_interaction(door_bp, door_box_template)
        except Exception as error:
            note("Door interaction could not be wired: {}".format(error))
        # UBlueprint.GeneratedClass is not exposed as an editor property by UE 5.8's
        # Python wrapper. Query it through the supported BlueprintEditorLibrary API.
        trigger_class = unreal.BlueprintEditorLibrary.generated_class(trigger_bp)
        door_class = unreal.BlueprintEditorLibrary.generated_class(door_bp)
        drone_class = unreal.BlueprintEditorLibrary.generated_class(drone_bp)
        elevator_class = unreal.BlueprintEditorLibrary.generated_class(elevator_bp)
        if not trigger_class or not door_class or not drone_class or not elevator_class:
            raise RuntimeError("Could not retrieve one or more compiled Blueprint classes")

        trigger = unreal.EditorLevelLibrary.spawn_actor_from_class(trigger_class, vec(0, 0, 100), unreal.Rotator())
        trigger.set_actor_label("LAB_Hologram_OneShot_Trigger", mark_dirty=True)
        set_folder(trigger, "LAB/03_Interactables")
        try:
            trigger.set_editor_property("auto_receive_input", unreal.AutoReceiveInput.PLAYER0)
        except Exception as error:
            note("Could not enable E input for the hologram: {}".format(error))
        try:
            box_components = trigger.get_components_by_class(unreal.BoxComponent)
        except Exception:
            box_components = [trigger.get_component_by_class(unreal.BoxComponent)]
        for box_comp in box_components:
            if box_comp:
                box_comp.set_box_extent(vec(240, 240, 190), True)
                box_comp.set_editor_property("generate_overlap_events", True)
                try:
                    box_comp.set_collision_profile_name("Trigger")
                except Exception:
                    pass

        for bp_name, location, _ in story_specs:
            story_class = story_blueprints.get(bp_name)
            if not story_class:
                note("No compiled class for story station " + bp_name)
                continue
            station = unreal.EditorLevelLibrary.spawn_actor_from_class(story_class, vec(*location), unreal.Rotator())
            station.set_actor_label("LAB_StoryTrigger_" + bp_name.replace("BP_Lab", ""), mark_dirty=True)
            set_folder(station, "LAB/03_Interactables")
            try:
                station.set_editor_property("auto_receive_input", unreal.AutoReceiveInput.PLAYER0)
            except Exception as error:
                note("Could not enable E input on {}: {}".format(bp_name, error))
            try:
                station_boxes = station.get_components_by_class(unreal.BoxComponent)
            except Exception:
                station_boxes = [station.get_component_by_class(unreal.BoxComponent)]
            for station_box in station_boxes:
                if station_box:
                    extent = (100, 145, 170) if bp_name == "BP_LabPurposeLog" else (145, 145, 170)
                    station_box.set_box_extent(vec(*extent), True)
                    station_box.set_editor_property("generate_overlap_events", True)
                    try:
                        station_box.set_collision_profile_name("Trigger")
                    except Exception:
                        pass

        # Sliding slab is staged in the corridor as a solid first obstacle.
        door = unreal.EditorLevelLibrary.spawn_actor_from_class(door_class, vec(1450, 0, 230), unreal.Rotator())
        door.set_actor_label("LAB_Door_Closed_Blockout", mark_dirty=True)
        set_folder(door, "LAB/03_Interactables")
        door_mesh = door.get_component_by_class(unreal.StaticMeshComponent)
        door_mesh.set_static_mesh(cube)
        door_mesh.set_material(0, rust)
        # The slab moves only from its E-key interaction event.
        door_mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        door.set_actor_scale3d(vec(0.8, 3.5, 4.3))
        door_mesh.set_collision_profile_name("BlockAll")
        try:
            door.set_editor_property("auto_receive_input", unreal.AutoReceiveInput.PLAYER0)
        except Exception as error:
            note("Could not enable door key input: {}".format(error))
        detail("LAB_DoorFrame_Header", (1450, 0, 455), (110, 420, 30), black)
        detail("LAB_DoorFrame_Left", (1450, -205, 230), (110, 25, 440), get_mat("MI_FP_EdenSilver"))
        detail("LAB_DoorFrame_Right", (1450, 205, 230), (110, 25, 440), get_mat("MI_FP_EdenSilver"))
        detail("LAB_DoorLock_Panel", (1330, -190, 180), (38, 18, 82), black)
        detail("LAB_DoorLock_Screen", (1330, -178, 195), (22, 4, 32), get_mat("MI_FP_WarningAmber"))
        door_label = (1330, -170, 270)
        spawn_text("LAB_DoorLock_Label", door_label, text_facing(door_label, (1400, 0, 150)),
                   "ПАНЕЛЬ ВЗЛОМА OMEGA\nПОДОЙДИ И НАЖМИ E", (255, 160, 90), 13.0)

        # Drone actor has a red forward vision light and a ping-pong component route across the corridor.
        drone = unreal.EditorLevelLibrary.spawn_actor_from_class(drone_class, vec(1850, 0, 350), unreal.Rotator(0.0, 180.0, 0.0))
        drone.set_actor_label("LAB_Drone_Patrol_Blockout", mark_dirty=True)
        set_folder(drone, "LAB/04_Security")
        drone_mesh = drone.get_component_by_class(unreal.StaticMeshComponent)
        drone_mesh.set_static_mesh(cube)
        drone_mesh.set_material(0, black)
        drone.set_actor_scale3d(vec(1.3, 1.0, 0.55))
        drone_mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        drone_mesh.set_collision_profile_name("BlockAll")
        try:
            drone.set_editor_property("auto_receive_input", unreal.AutoReceiveInput.PLAYER0)
        except Exception as error:
            note("Could not enable T-key input on the patrol drone: {}".format(error))
        cylinder = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cylinder")
        drone_parts = [
            ("ArmorTop", (1850, 0, 382), (86, 74, 12), get_mat("MI_FP_EdenSilver"), cube),
            ("Antenna", (1840, 0, 412), (8, 8, 42), rust, cube),
            ("SensorLens", (1780, 0, 350), (22, 12, 22), red, cube),
            ("RotorHubLeft", (1850, -72, 368), (28, 28, 8), get_mat("MI_FP_EdenSilver"), cylinder),
            ("RotorHubRight", (1850, 72, 368), (28, 28, 8), get_mat("MI_FP_EdenSilver"), cylinder),
            ("RotorArmLeft", (1850, -52, 360), (18, 45, 8), rust, cube),
            ("RotorArmRight", (1850, 52, 360), (18, 45, 8), rust, cube),
        ]
        for part_name, part_location, part_size, part_material, part_mesh in drone_parts:
            part = detail("LAB_Drone_" + part_name, part_location, part_size, part_material, part_mesh)
            try:
                keep_world = unreal.AttachmentRule.KEEP_WORLD
                part.attach_to_actor(drone, unreal.Name("None"), keep_world, keep_world, keep_world, False)
            except Exception as error:
                note("Could not attach drone part {}: {}".format(part_name, error))
        # Spawn the vision cone as a light actor and attach it; StaticMeshActor
        # does not expose add_component_by_class through Unreal Python 5.8.
        vision_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SpotLight, vec(1780, 0, 350), unreal.Rotator(0.0, 180.0, 0.0))
        vision_actor.set_actor_label("LAB_Drone_Vision_Spot", mark_dirty=True)
        set_folder(vision_actor, "LAB/04_Security")
        try:
            keep_world = unreal.AttachmentRule.KEEP_WORLD
            vision_actor.attach_to_actor(drone, unreal.Name("None"), keep_world, keep_world, keep_world, False)
        except Exception as error:
            note("Could not attach the red vision light to the drone: {}".format(error))

        vision = vision_actor.get_component_by_class(unreal.SpotLightComponent)
        set_light(vision, (255, 12, 8), 125.0, 800.0)
        vision.set_editor_property("inner_cone_angle", 18.0)
        vision.set_editor_property("outer_cone_angle", 42.0)

        # The crack light gives the patrol sector its hard white shaft, while a
        # short run of shadowless maintenance lights keeps the whole route readable.
        crack_light_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.SpotLight, vec(2000, 0, 458), unreal.Rotator(-90.0, 0.0, 0.0))
        crack_light_actor.set_actor_label("LAB_Corridor_CeilingCrack_WhiteSpot", mark_dirty=True)
        set_folder(crack_light_actor, "LAB/02_Lighting")
        crack_light = crack_light_actor.get_component_by_class(unreal.SpotLightComponent)
        set_light(crack_light, (205, 225, 255), 2400.0, 520.0)
        crack_light.set_editor_property("inner_cone_angle", 14.0)
        crack_light.set_editor_property("outer_cone_angle", 27.0)

        for index, location in enumerate(
                ((1040, 0, 385), (1480, 0, 385), (1920, 0, 385), (2280, 0, 385),
                 (2630, 0, 720), (2630, 0, 1460), (2630, 0, 2060)), 1):
            lamp = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PointLight, vec(*location), unreal.Rotator())
            lamp.set_actor_label("LAB_RouteMaintenanceLight_{:02d}".format(index), mark_dirty=True)
            set_folder(lamp, "LAB/02_Lighting")
            lamp_comp = lamp.get_component_by_class(unreal.PointLightComponent)
            intensity = 6800.0 if location[0] < 2300 else 6500.0
            set_light(lamp_comp, (195, 220, 255), intensity, 1080.0)
            fixture = detail("LAB_RouteLamp_Fixture_{:02d}".format(index),
                             (location[0], location[1], location[2] + 25),
                             (120, 28, 12), black)
            lens = detail("LAB_RouteLamp_Lens_{:02d}".format(index),
                          (location[0], location[1], location[2] + 17),
                          (86, 14, 4), cyan)

        # Lift controls and warning stripes lead onto the moving platform.
        detail("LAB_LiftCallPanel_Housing", (2375, -300, 160), (34, 28, 120), black)
        detail("LAB_LiftCallPanel_Screen", (2375, -282, 185), (18, 5, 46), cyan)
        detail("LAB_LiftCallPanel_Status", (2375, -282, 135), (10, 5, 10), get_mat("MI_FP_WarningAmber"))
        detail("LAB_LiftThreshold_Amber", (2375, 0, 6), (70, 360, 8), get_mat("MI_FP_WarningAmber"))

        elevator = unreal.EditorLevelLibrary.spawn_actor_from_class(
            elevator_class, vec(2650, 0, 24), unreal.Rotator())
        elevator.set_actor_label("LAB_Elevator_MoveToFloor01", mark_dirty=True)
        set_folder(elevator, "LAB/03_Interactables")
        elevator_mesh = elevator.get_component_by_class(unreal.StaticMeshComponent)
        elevator_mesh.set_static_mesh(cube)
        elevator_mesh.set_material(0, rust)
        elevator_mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        elevator_mesh.set_collision_profile_name("BlockAll")
        elevator_mesh.set_editor_property("generate_overlap_events", True)
        elevator.set_actor_scale3d(vec(5.2, 5.2, 0.36))
        elevator_box = elevator.get_component_by_class(unreal.BoxComponent)
        if elevator_box:
            elevator_box.set_box_extent(vec(48, 48, 330), True)
            elevator_box.set_editor_property("generate_overlap_events", True)
            elevator_box.set_collision_profile_name("Trigger")
        for side in (-1, 1):
            edge = detail("LAB_Elevator_EdgeLight_{}".format("L" if side < 0 else "R"),
                          (2650, side * 252, 46), (480, 8, 8), cyan)
            try:
                keep_world = unreal.AttachmentRule.KEEP_WORLD
                edge.attach_to_actor(elevator, unreal.Name("None"), keep_world, keep_world, keep_world, False)
            except Exception as error:
                note("Could not attach elevator edge marker: {}".format(error))
            rail = detail("LAB_Elevator_SafetyRail_{}".format("North" if side > 0 else "South"),
                          (2650, side * 238, 112), (520, 14, 150), rust, blocking=True)
            try:
                rail.get_component_by_class(unreal.StaticMeshComponent).set_mobility(
                    unreal.ComponentMobility.MOVABLE)
                keep_world = unreal.AttachmentRule.KEEP_WORLD
                rail.attach_to_actor(elevator, unreal.Name("None"), keep_world, keep_world, keep_world, False)
            except Exception as error:
                note("Could not attach cargo-lift rail: {}".format(error))

        # Player starts in the dark room, facing the projector and the exit corridor.
        player_start = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.PlayerStart, vec(-430, 280, 198), unreal.Rotator(0.0, -33.0, 0.0))
        player_start.set_actor_label("LAB_PlayerStart", mark_dirty=True)
        set_folder(player_start, "LAB/00_Core")

        # Put the editor viewport inside the chamber so the first view is useful
        # even though this level intentionally has no sky, sun, or sky light.
        try:
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            editor.set_level_viewport_camera_info(
                vec(-650, -600, 250), unreal.Rotator(-7.0, 37.0, 0.0))
            note("Positioned the editor viewport inside the laboratory")
        except Exception as error:
            note("Could not reposition the editor viewport: {}".format(error))

        note("World-space hologram faces the recovery cradle; PlayerStart begins inside the recovery pod")
        note("The reference pass installs LS_CapsuleAwakening: capsule-local hinged canopy, pressure release, and first steps")
        note("The exit route now includes two jump wrecks, a side archive for map fragments, alternating cover, a patrol sector, and the cargo-lift landing")
        note("WASD and Space hints are placed at the first obstacle; stealth guidance appears before the drone")
        note("E opens the bulkhead and reads nearby logs; hold C to crouch and hold Left Shift to sprint")
        note("The moving cargo elevator carries the player to the walkable first-floor lab landing in about 20 seconds")
        note("N toggles a camera-following cyan-green night-vision beam; it has no dynamic shadows")
        note("T toggles a translucent emissive x-ray signature on the tutorial drone; future robot targets can use the same material")
        note("Seven shadowless route lights illuminate the corridor and shaft through the lift landing")
        note("Major furniture, jump wrecks, archive racks, and stealth cover use blocking collision")
        note("Created Blueprint assets: BP_TutorialHologramTrigger, BP_TutorialSlidingDoor, BP_TutorialPatrolDrone, BP_LabTutorialElevator")
        note("Level contains no skybox, DirectionalLight, or SkyLight")
        note("Hologram and archive records display an E prompt in range and print their story text on E")

        if not unreal.EditorLoadingAndSavingUtils.save_current_level():
            raise RuntimeError("Could not save Lvl_LabTutorial")
        unreal.EditorAssetLibrary.save_directory("/Game/LabTutorial", only_if_is_dirty=False, recursive=True)
        note("Saved level: " + unreal.EditorLevelLibrary.get_editor_world().get_path_name())

        # Make the new tutorial the editor's next startup level only after it exists.
        ini_path = os.path.join(PROJECT_DIR, "Config", "DefaultEngine.ini")
        if os.path.isfile(ini_path):
            with open(ini_path, "r", encoding="utf-8-sig") as ini_file:
                ini_text = ini_file.read()
            new_text, changed = re.subn(r"(?m)^EditorStartupMap=.*$", "EditorStartupMap=/Game/Lvl_LabTutorial.Lvl_LabTutorial", ini_text, count=1)
            if changed:
                with open(ini_path, "w", encoding="utf-8") as ini_file:
                    ini_file.write(new_text)
        style_script = os.path.join(PROJECT_DIR, "Content", "Python", "Style_LabReference.py")
        if os.path.isfile(style_script):
            exec(compile(open(style_script, encoding="utf-8").read(), style_script, "exec"), {"__name__": "__main__"})
            note("Applied the abandoned laboratory reference art pass")
        with open(DONE_FILE, "w", encoding="utf-8") as done_file:
            done_file.write("Lvl_LabTutorial created.\n")
        if os.path.exists(FAIL_FILE):
            os.remove(FAIL_FILE)
        note("BUILD COMPLETE")
    except Exception:
        error_text = traceback.format_exc()
        note("BUILD FAILED\n" + error_text)
        try:
            unreal.EditorLoadingAndSavingUtils.save_current_level()
            note("Saved the partially built tutorial map so progress is retained")
        except Exception as save_error:
            note("Could not save partial tutorial map: {}".format(save_error))
        with open(FAIL_FILE, "w", encoding="utf-8") as fail_file:
            fail_file.write(error_text)
    finally:
        with open(REPORT_FILE, "w", encoding="utf-8") as report_file:
            report_file.write("\n".join(report))

