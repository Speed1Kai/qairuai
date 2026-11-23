import unreal,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from Enemy_Common import *
import Enemy_Character as C
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
mats=C.materials();sounds=C.sound();abp=A.load_asset(ROOT+'/ABP_EnemyRobot');enemy=C.character(abp,mats,sounds)
controller=A.load_asset(ROOT+'/AIC_EnemyRobot');unreal.get_default_object(B.generated_class(enemy)).set_editor_property('ai_controller_class',B.generated_class(controller));save(enemy)
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 if a.get_actor_label()=='ENEMY_EliteGuard':unreal.EditorLevelLibrary.destroy_actor(a)
a=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(enemy),V((3960,-170,2255)),unreal.Rotator(yaw=180));a.set_actor_label('ENEMY_EliteGuard');a.set_folder_path('LAB/08_Enemies')
if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Enemy map save failed')
