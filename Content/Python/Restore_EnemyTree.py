import unreal,sys,os,json
sys.path.insert(0,os.path.dirname(__file__))
from Enemy_Common import *
import Enemy_Behavior as AI
bb=A.load_asset(ROOT+'/BB_EnemyRobot')
tasks={k:A.load_asset(ROOT+'/'+v) for k,v in {'alert':'BTT_EnemyAlert','patrol':'BTT_EnemyPatrol','search':'BTT_EnemySearch','endsearch':'BTT_EnemyFinishSearch','strike':'BTT_EnemyStrike','memory':'BTS_EnemyMemory'}.items()}
tree=AI.behavior(bb,tasks)
unreal.get_default_object(unreal.SystemLibrary).call_method('SetObjectPropertyByName',(tree,unreal.Name('BTGraph'),None))
save(tree)
r={'root':str(tree.get_editor_property('root_node')),'count':len(tree.get_editor_property('root_node').get_editor_property('children'))}
with open('S:/Final_Protocol/Saved/enemy_tree_restored.json','w') as f:json.dump(r,f)
