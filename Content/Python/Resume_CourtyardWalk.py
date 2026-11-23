import unreal,os,time
w=unreal.EditorLevelLibrary.get_game_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor):
 if a.get_class().get_name()=='BP_FreightElevatorBidirectional_C':
  a.get_editor_property('CabinRoot').set_relative_location(unreal.Vector(0,0,2126),False,False)
  for group,x,z in [('UpperGate',350,2150),('CabRear',248,24)]:
   for side,sgn in [('Left',-1),('Right',1)]:a.get_editor_property(group+side).set_relative_location(unreal.Vector(x,sgn*246,z),False,False)
  a.get_editor_property('UpperThreshold').set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
src=os.path.join(os.path.dirname(__file__),'Test_CourtyardWalk.py');code=open(src,encoding='utf8').read();code=code.replace("unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()",'')
exec(compile(code,src,'exec'));walk['t']=time.monotonic()-24
