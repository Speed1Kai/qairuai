import unreal,json
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
r={};bt=unreal.load_asset('/Game/Enemies/Architect/BT_EnemyRobot')
def visit(n):
 if not n:return None
 row={'class':n.get_class().get_name(),'path':n.get_path_name(),'name':n.get_editor_property('node_name')}
 if isinstance(n,unreal.BTCompositeNode):row['children']=[visit(c.child_composite or c.child_task) for c in n.get_editor_property('children')]
 return row
r['tree']=visit(bt.get_editor_property('root_node'))
w=unreal.EditorLevelLibrary.get_editor_world();nav=unreal.NavigationSystemV1.get_navigation_system(w);r['nav']=str(nav)
if nav:
 for prop in ('auto_create_navigation_data','spawn_nav_data_in_nav_bounds_level','initial_building_locked','generate_navigation_only_around_navigation_invokers','supported_agents'):
  try:r[prop]=str(nav.get_editor_property(prop))
  except Exception as ex:r[prop]=str(ex)
r['actors']=[]
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 n=a.get_actor_label()
 if n.startswith('ENEMY_') or isinstance(a,unreal.RecastNavMesh):
  row={'name':n,'class':a.get_class().get_name(),'p':str(a.get_actor_location()),'bounds':str(a.get_actor_bounds(False))}
  if isinstance(a,unreal.NavMeshBoundsVolume):row['components']=[str(c) for c in a.get_components_by_class(unreal.BrushComponent)]
  r['actors'].append(row)
with open('S:/Final_Protocol/Saved/enemy_saved_inspection.json','w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
