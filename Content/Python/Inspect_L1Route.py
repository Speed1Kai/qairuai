"""Read the current editor/PIE lift state without moving or triggering anything."""
import unreal,json
def value(o,n):
 try:return str(o.get_editor_property(n))
 except Exception as e:return str(e)
def actors(world):
 r=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
  if a.get_class().get_name() not in ['BP_SurfaceDeparture_C','BP_FreightElevatorBidirectional_C']:continue
  d={'name':a.get_name(),'class':a.get_class().get_name(),'location':str(a.get_actor_location()),'tick_enabled':a.is_actor_tick_enabled(),'input':value(a,'auto_receive_input'),'block':value(a,'block_input')}
  for n in ['bNear','bTravelling','Prompt','LiftState','FocusCabButton','CurrentFloor','input_component','input_priority']:d[n]=value(a,n)
  r.append(d)
 return r
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);r={'editor':actors(editor.get_editor_world())}
w=unreal.EditorLevelLibrary.get_game_world()
if w:
 p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0);camera=unreal.GameplayStatics.get_player_camera_manager(w,0)
 r.update(player=str(p.get_actor_location()) if p else None,camera=str(camera.get_camera_location()),runtime=actors(w))
bp=unreal.EditorAssetLibrary.load_asset('/Game/Surface/BP_SurfaceDeparture');g=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph');r['keys']=[]
for n in g.list_all_nodes() if g else []:
 if n.get_class().get_name()=='K2Node_InputKey':r['keys'].append({'title':str(n.get_node_title()),'consume':value(n,'bConsumeInput'),'outputs':[(str(p.get_pin_name()),len(p.list_connected_pins())) for p in n.list_all_pins()]})
with open('S:/Final_Protocol/Saved/l1_route_inspection.json','w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
