import unreal,os,sys,json,traceback,shutil,datetime
sys.path.insert(0,os.path.dirname(__file__))
from Enemy_Common import *
import Enemy_Character as C,Enemy_Behavior as AI
r={'saved':False,'visual_source':'Manny skeleton and segmented mesh; reference image is not a rigged 3D asset','stages':[]}
try:
 A.make_directory(ROOT);unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
 backup='S:/Final_Protocol/Saved/Backups/EnemyRobot/'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S');os.makedirs(backup,exist_ok=True);shutil.copy2('S:/Final_Protocol/Content/Lvl_LabTutorial.umap',backup+'/Lvl_LabTutorial.umap');r['backup']=backup
 mats=C.materials();sounds=C.sound();r['stages'].append('materials and audio')
 abp=C.animation();r['stages'].append('animation blueprint')
 enemy=C.character(abp,mats,sounds);r['stages'].append('enemy character')
 bb=AI.blackboard();tasks=AI.tasks(sounds['S_EnemyAlert']);tree=AI.behavior(bb,tasks);r['stages'].append('blackboard and behavior tree')
 controller=AI.controller(bb,tree,sounds['S_EnemyAlert']);r['stages'].append('perception and controller')
 cdo=unreal.get_default_object(B.generated_class(enemy));cdo.set_editor_property('ai_controller_class',B.generated_class(controller));save(enemy)
 for a in unreal.EditorLevelLibrary.get_all_level_actors():
  if a.get_actor_label().startswith('ENEMY_'):unreal.EditorLevelLibrary.destroy_actor(a)
 robot=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(enemy),V((3960,-170,2255)),unreal.Rotator(yaw=180));robot.set_actor_label('ENEMY_EliteGuard');robot.set_folder_path('LAB/08_Enemies')
 nav=unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.NavMeshBoundsVolume,V((3550,0,2370)),unreal.Rotator());nav.set_actor_scale3d(V((10,5.5,4.)));nav.set_actor_label('ENEMY_FirstFloorNavBounds');nav.set_folder_path('LAB/08_Enemies')
 if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Close Unreal to release map file')
 r.update(saved=True,enemy=enemy.get_path_name(),controller=controller.get_path_name(),behavior_tree=tree.get_path_name(),blackboard=bb.get_path_name(),sight_radius=1800,lose_sight_radius=2200,vision_half_angle=60,patrol_speed=180,chase_speed=550,health=320,placement=(3960,-170,2255))
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
with open('S:/Final_Protocol/Saved/enemy_robot_build.json','w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Enemy authoring incomplete; see Saved/enemy_robot_build.json')
