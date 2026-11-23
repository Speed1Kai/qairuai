import unreal,json,os
B=unreal.BlueprintEditorLibrary;G=unreal.BlueprintGraphEditor
f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Character)
bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_MovementAPIProbe','/Game/MovementDiagnostics',unreal.Blueprint,f)
e=G.get_graph_editor_by_name(bp,'EventGraph');r={}
paths=['Engine.KismetMathLibrary.SelectFloat','Engine.KismetMathLibrary.FInterpTo_Constant','Engine.KismetMathLibrary.VSizeXY','Engine.KismetMathLibrary.Add_VectorVector','Engine.KismetMathLibrary.MakeVector','Engine.KismetMathLibrary.BreakVector','Engine.KismetMathLibrary.BooleanAND','Engine.KismetMathLibrary.Add_DoubleDouble','Engine.CharacterMovementComponent.IsFalling','Engine.CharacterMovementComponent.GetCurrentAcceleration','Engine.Actor.GetVelocity','Engine.CapsuleComponent.GetUnscaledCapsuleHalfHeight','Engine.CapsuleComponent.SetCapsuleHalfHeight','Engine.SceneComponent.K2_SetRelativeLocation','Engine.Actor.K2_AddActorWorldOffset','Engine.KismetSystemLibrary.CapsuleTraceSingleByProfile','Engine.GameplayStatics.GetPlayerCameraManager','Engine.Camera.PlayerCameraManager.StartCameraShake','Engine.PlayerCameraManager.StartCameraShake','Engine.KismetSystemLibrary.GetGameTimeInSeconds','Engine.Character.GetMesh']
for p in paths:
 try:
  n=e.add_call_function_node('/Script/'+p)
  r[p]=[(str(x.get_pin_name()),x.get_pin_value()) for x in n.list_all_pins()] if n else None
 except Exception as ex:r[p]=str(ex)
for v,c in [('CharacterMovement','/Script/Engine.Character'),('CapsuleComponent','/Script/Engine.Character'),('Mesh','/Script/Engine.Character')]:
 try:
  n=e.add_get_member_variable_node(v,c);r[v]=[(str(x.get_pin_name()),x.get_pin_value()) for x in n.list_all_pins()]
 except Exception as ex:r[v]=str(ex)
r['keymenu']=[str(x) for x in e.list_available_nodes([]) if 'KeyboardEvents' in str(x) and 'Shift' in str(x)]
s=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
orig=unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
r['component_vars']=[]
for h in s.k2_gather_subobject_data_for_blueprint(orig):
 d=lib.get_data(h)
 try:r['component_vars'].append(str(lib.get_variable_name(d)))
 except Exception as ex:r['component_vars'].append(str(ex))
with open(os.path.join(unreal.Paths.project_saved_dir(),'movement_api_probe.json'),'w') as f:json.dump(r,f,indent=2)
