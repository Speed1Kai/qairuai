import unreal,os,json,hashlib
A=unreal.EditorAssetLibrary;ROOT='/Game/City/Props/LunarAeroPod'
mesh=A.load_asset(ROOT+'/SM_LunarAeroPod');assert mesh
assert mesh.get_material(0).get_path_name().startswith(ROOT+'/M_LunarAeroPod')
sms=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
assert sms.get_simple_collision_count(mesh)+sms.get_convex_collision_count(mesh)>0
R={'passed':False,'maps':[],'material':mesh.get_material(0).get_path_name()}
for name in ('Lvl_SurfaceArrival','Lvl_CampusConnected'):
 assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Surface/'+name)
 sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);actors=sub.get_all_level_actors()
 pods=[a for a in actors if a.get_actor_label()=='CITY_LunarAeroPod'];assert len(pods)==1
 a=pods[0];assert a.static_mesh_component.static_mesh==mesh
 assert str(a.static_mesh_component.get_collision_profile_name())=='BlockAll'
 p,e=a.get_actor_bounds(False);assert 540<max(e.x,e.y)*2<560
 npc=[a for a in actors if a.get_actor_label().startswith('CITY_Enceladus_')];assert len(npc)==6
 R['maps'].append(dict(map=name,position=str(p),size=str(e*2),npc_count=len(npc),collision=True))
lab=os.path.join(unreal.Paths.project_content_dir(),'Lvl_LabTutorial.umap')
assert hashlib.sha256(open(lab,'rb').read()).hexdigest()=='18fa88868e98ae4252e60c9d99b8fa8b85372d9695f694d850ae299fec0058ea'
R.update(passed=True,lab_unchanged=True)
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'city_aeropod_validation.json'),'w'),indent=2)
