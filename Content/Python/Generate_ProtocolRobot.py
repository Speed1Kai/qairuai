"""Named rigid robot parts on the mannequin skeleton; original placeholder art."""
import ast,os,json,math
scripts=os.path.dirname(__file__);ROOT=os.path.abspath(os.path.join(scripts,'..','Characters','ProtocolRobot','Models','Source'));os.makedirs(ROOT,exist_ok=True)
for file,kind,names in [('Generate_IndustrialMeshes.py',ast.ClassDef,['Model']),('Generate_SplitDoorMeshes.py',ast.FunctionDef,['save_uv_model']),('Generate_HeroCyborg.py',ast.FunctionDef,['ellipsoid','plate'])]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name in names],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
rig=json.load(open(os.path.join(scripts,'..','..','Saved','protocol_robot_rig.json')))
D='M_RobotGunmetal';S='M_RobotChrome';R='M_RobotRed';B='M_RobotJoint';out=[]
def finish(m,bone,category):
 s=m.save();s.update(bone=bone,category=category);out.append(s)
def lerp(a,b,t):return tuple(a[i]+(b[i]-a[i])*t for i in range(3))
m=Model('SM_Robot_Head');ellipsoid(m,(0,.5,170),(9.2,10.4,13.2),D,32,16)
# An unbroken oval face: no projecting nose or ear housings.
plate(m,[(-7.6,176),(0,178),(7.6,176),(7,164),(0,159.4),(-7,164)],11,2,D)
for s in (-1,1):
 plate(m,[(s*1.4,173.4),(s*7,174.1),(s*6.3,171.8),(s*2,171.4)],11.5,.6,R)
 m.pipe([(s*1.8,11.2,178),(s*5,11.5,175.8)],.22,R,6)
 plate(m,[(s*1,165),(s*7,166.5),(s*5.7,160.5),(s*1,159.6)],11.5,1,S)
 m.pipe([(s*6.5,11.8,169),(s*5.7,11.8,167),(s*3,12,166)],.2,R,6)
m.box((0,12,163),(7,.8,.7),B,.2)
for x in (-3,-1.5,0,1.5,3):m.box((x,11.9,160.8),(1.1,1,2.1),D,.2)
finish(m,'head','Head')
m=Model('SM_Robot_Neck')
for x in (-3.5,0,3.5):m.pipe([(x,0,152),(x,1.5,159)],1.4,S,10)
m.cylinder((0,1,155),4.8,2,R,20);finish(m,'neck_01','Neck')
m=Model('SM_Robot_Chest');plate(m,[(-21,146),(-15,151),(15,151),(21,146),(13,125),(0,121),(-13,125)],12.5,4,B)
for s in (-1,1):
 for z,w in [(144,18),(138,15),(132,12)]:
  plate(m,[(s*2,z+4),(s*w,z+3),(s*(w-2),z-3),(s*4,z-7)],16.7,3,D)
  m.pipe([(s*4,18,z+2),(s*(w-2),18,z+1)],.45,S,6)
 for z in (127,133,139):m.pipe([(s*8,15.1,z),(s*15,11,z+1)],1.1,R,8)
 m.pipe([(s*17,2,146),(s*16,9,135),(s*10,9,123)],1.3,S,8)
finish(m,'spine_05','Chest')
m=Model('SM_Robot_Back')
for x in (-7,7):
 m.pipe([(x,-11,148),(x,-12,125)],3,D,10)
 for z in range(127,147,4):m.box((x,-15,z),(7,3,1.3),S,.3)
m.box((0,-12,135),(2,2,23),R,.5);finish(m,'spine_05','Back')
m=Model('SM_Robot_Abdomen')
for z in (109,114,119,124):
 m.box((0,10.8,z),(8,5,4.4),D,1.3,1)
 for s in (-1,1):m.box((s*6,10,z),(1,2,3.2),R,.25)
finish(m,'spine_03','Abdomen')
m=Model('SM_Robot_Pelvis')
for s in (-1,1):
 plate(m,[(s*2,103),(s*13,105),(s*16,98),(s*8,91),(s*2,93)],12,4,D)
 m.pipe([(s*7,7,103),(s*13,9,94)],.6,S,8)
finish(m,'pelvis','Pelvis')
for side,suffix in [(1,'l'),(-1,'r')]:
 p=rig['upperarm_'+suffix]['p'];m=Model('SM_Robot_Shoulder_'+suffix)
 for dy,rad in [(0,10.5),(-3,11.5)]:ellipsoid(m,(side*23,-2+dy,145),(rad,8,rad*.95),D,24,10)
 m.cylinder((side*24,7.5,145),6.6,2.5,S,24,1);m.cylinder((side*24,9,145),4.8,1.2,B,24,1);m.cylinder((side*24,9.8,145),3.3,.6,R,24,1)
 finish(m,'upperarm_'+suffix,'Shoulder')
 for name,bone,endbone,radius in [('UpperArm','upperarm_'+suffix,'lowerarm_'+suffix,5.8),('Forearm','lowerarm_'+suffix,'hand_'+suffix,6.2),('Thigh','thigh_'+suffix,'calf_'+suffix,8.2),('Shin','calf_'+suffix,'foot_'+suffix,6.5)]:
  a=rig[bone]['p'];b=rig[endbone]['p'];m=Model('SM_Robot_'+name+'_'+suffix)
  start=lerp(a,b,.2);end=lerp(a,b,.82);m.pipe([start,end],radius,D,12)
  for offset in (-2.6,2.6):m.pipe([(start[0]+offset,start[1]+radius*.85,start[2]),(end[0]+offset,end[1]+radius*.85,end[2])],.7,S,8)
  # Fine hydraulic lines along the sides of each limb.
  for sign in (-1,1):m.pipe([(start[0]+sign*radius*.85,start[1]-2,start[2]),(end[0]+sign*radius*.85,end[1]-2,end[2])],.7,B,8)
  if name=='Shin':
   for t in (.24,.34,.44,.54,.64,.74):
    q=lerp(a,b,t);m.box((q[0],q[1]+radius,q[2]),(9,2.5,2.7),D,.8)
  finish(m,bone,name)
 m=Model('SM_Robot_Elbow_'+suffix);p=rig['lowerarm_'+suffix]['p'];m.cylinder((p[0],p[1]+5,p[2]),3.5,2.5,R,16,1);finish(m,'lowerarm_'+suffix,'Elbow')
 m=Model('SM_Robot_Knee_'+suffix);p=rig['calf_'+suffix]['p'];ellipsoid(m,(p[0],p[1]+4.5,p[2]+1),(6,4,6.5),D,20,10);finish(m,'calf_'+suffix,'Knee')
 m=Model('SM_Robot_Hand_'+suffix);p=rig['hand_'+suffix]['p'];ellipsoid(m,(p[0],p[1],p[2]),(4.8,3.4,6),D,16,8)
 for digit in ('thumb','index','middle','ring','pinky'):
  names=[digit+'_%02d_'%i+suffix for i in (1,2,3)]
  if not all(n in rig for n in names):continue
  points=[rig[n]['p'] for n in names]
  for i in range(2):m.pipe(points[i:i+2],1.0 if digit=='thumb' else .85,S,8)
  last=points[-1];prev=points[-2];tip=tuple(last[i]+(last[i]-prev[i])*.9 for i in range(3));tip=(tip[0],tip[1],tip[2]-1.8)
  m.pipe([last,tip],.65,D,6)
 finish(m,'hand_'+suffix,'Hand')
 m=Model('SM_Robot_Foot_'+suffix);p=rig['foot_'+suffix]['p'];m.box((p[0],p[1]+3,5.5),(12,20,9),D,3)
 for dx in (-4.3,0,4.3):
  m.pipe([(p[0]+dx,p[1]+9,5),(p[0]+dx,p[1]+18,3),(p[0]+dx,p[1]+22,1.4)],1.8,S,8)
 finish(m,'foot_'+suffix,'Foot')
with open(os.path.join(ROOT,'robot_parts.json'),'w') as f:json.dump(out,f,indent=2)
print('Robot placeholder parts:',len(out))
