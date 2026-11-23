import unreal,os,sys
sys.path.insert(0,os.path.dirname(__file__))
from Enemy_Common import *
import Enemy_Character as C
abp=C.animation()
enemy=A.load_asset(ROOT+'/BP_EnemyRobot')
cdo=unreal.get_default_object(B.generated_class(enemy));cdo.get_component_by_class(unreal.SkeletalMeshComponent).set_anim_instance_class(B.generated_class(abp));save(enemy)
