import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
var(bp,'ModeTriggerPulls','int','0');compile_bp(bp)
g=Graph(bp,'Modes_StartFire');g.branch(g.math('Not_PreBool',A=g.get('bModeMenuOpen')));g.count('ModeTriggerPulls');hunter=g.branch(g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=1));other=hunter.find_else_pin();g.set('bLaserHeld',True);g.do(g.own('Laser_Fire'));g.cursor=other;g.set('bLaserHeld',False);g.branch(g.math('EqualEqual_IntInt',A=g.get('CyborgMode'),B=2));g.do(g.own('Protocol_Fire'));compile_bp(bp);save(bp)
