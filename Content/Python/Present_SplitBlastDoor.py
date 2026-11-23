"""Render the saved door in two static art poses; never saves preview poses."""
import unreal,os,sys,time,json,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *

folder=os.path.abspath(os.path.join(unreal.Paths.project_saved_dir(),'SplitDoorPreview'));os.makedirs(folder,exist_ok=True)
# Refresh mesh import with explicit UVs; preserve the authored material slots.
with open(os.path.join(unreal.Paths.project_content_dir(),'LabTutorial','Industrial','Source','split_door_manifest.json')) as f:manifest=json.load(f)
for spec in manifest:
 name=spec['name'];task=unreal.AssetImportTask()
 for k,v in {'filename':os.path.abspath(os.path.join(unreal.Paths.project_content_dir(),'LabTutorial','Industrial','Source',name+'.obj')),'destination_path':ROOT,'destination_name':name,'automated':True,'replace_existing':True,'save':True}.items():task.set_editor_property(k,v)
 opts=unreal.FbxImportUI()
 for k,v in {'import_materials':False,'import_textures':False,'import_as_skeletal':False,'import_animations':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_STATIC_MESH}.items():opts.set_editor_property(k,v)
 opts.static_mesh_import_data.set_editor_property('combine_meshes',True);opts.static_mesh_import_data.set_editor_property('auto_generate_collision',False);task.set_editor_property('options',opts)
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 mesh=A.load_asset(ROOT+'/'+name)
 for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,A.load_asset(ROOT+'/'+str(slot.get_editor_property('material_slot_name'))))
 save(mesh)

unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
door=next(a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_actor_label()=='IND_HeavyBlastDoor')
if '/Doors/' not in door.get_class().get_path_name():raise RuntimeError('Saved map still references the old door')
bp=A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor');compile_bp(bp)
g=Graph(bp);rows=[]
for node in g.e.list_all_nodes():
 if node.get_class().get_name()=='K2Node_Timeline':rows.append({'pins':[str(p.get_pin_name()) for p in node.list_all_pins()],'alpha_connections':len(pin(node,'Alpha',True).list_connected_pins())})
with open(os.path.join(folder,'SavedAsset.json'),'w') as f:json.dump({'door_class':door.get_class().get_path_name(),'timeline':rows,'components':[{'name':c.get_name(),'class':c.get_class().get_name()} for c in door.get_components_by_class(unreal.ActorComponent)]},f,indent=2)
world=unreal.EditorLevelLibrary.get_editor_world()
for command in ('t.MaxFPS 30','r.ScreenPercentage 100','r.Streaming.PoolSize 1200'):
 unreal.SystemLibrary.execute_console_command(world,command)
sub=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);sub.editor_set_game_view(True)
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor.set_level_viewport_camera_info(V((950,-30,232)),unreal.MathLibrary.find_look_at_rotation(V((950,-30,232)),V((1450,0,220))))
started=time.monotonic();last=started;stage=0;busy=False
def update(dt):
 global stage,last,busy
 if busy:return
 busy=True
 try:
  now=time.monotonic()
  if now-started>140:raise RuntimeError('Art preview timeout')
  if now-last<12:return
  if stage==0:
   stage=1;last=now
   unreal.AutomationLibrary.take_high_res_screenshot(1280,720,os.path.join(folder,'Door_Closed.png'),delay=1.)
  elif stage==1:
   stage=2;last=now
   for c in door.get_components_by_class(unreal.StaticMeshComponent):
    if c.get_name() in ('LeftDoorPanel','RightDoorPanel'):
     sign=-1 if c.get_name().startswith('Left') else 1;c.set_relative_location(V((0,sign*263.5,0)),False,False)
    if c.get_name().startswith('StatusLens'):c.set_material(0,A.load_asset(ROOT+'/M_DoorStatus_Green'))
    if 'PistonRod' in c.get_name():c.set_visibility(False)
   door.get_component_by_class(unreal.PointLightComponent).set_light_color(unreal.LinearColor(r=.025,g=1,b=.075,a=1))
  elif stage==2:
   stage=3;last=now
   unreal.AutomationLibrary.take_high_res_screenshot(1280,720,os.path.join(folder,'Door_Open.png'),delay=1.)
  else:
   unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
 except Exception:
  with open(os.path.join(folder,'error.txt'),'w') as f:f.write(traceback.format_exc())
  unreal.unregister_slate_post_tick_callback(handle);unreal.SystemLibrary.quit_editor()
 finally:busy=False
handle=unreal.register_slate_post_tick_callback(update)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
