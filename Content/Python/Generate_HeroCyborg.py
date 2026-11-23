"""Original segmented hero armour in Manny reference mesh space, centimetres."""
import ast,math,os,json
scripts=os.path.dirname(__file__);ROOT=os.path.abspath(os.path.join(scripts,'..','Characters','FinalSentinel','Source'));os.makedirs(ROOT,exist_ok=True)
for file,kind,name in [('Generate_IndustrialMeshes.py',ast.ClassDef,'Model'),('Generate_SplitDoorMeshes.py',ast.FunctionDef,'save_uv_model')]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name==name],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
rig=json.load(open(os.path.join(scripts,'..','..','Saved','hero_rig_reference.json')))
S='M_HeroSilver';D='M_HeroGraphite';G='M_HeroGold';C='M_HeroCore';V='M_HeroVisor';specs=[]
def finish(m,bone):
 spec=m.save();spec['bone']=bone;specs.append(spec)
def ellipsoid(m,p,r,mat,segments=24,rings=12):
 for j in range(rings):
  a=-math.pi/2+math.pi*j/rings;b=-math.pi/2+math.pi*(j+1)/rings
  for i in range(segments):
   t=i*math.tau/segments;u=(i+1)*math.tau/segments
   def q(a,t):return (p[0]+r[0]*math.cos(a)*math.cos(t),p[1]+r[1]*math.cos(a)*math.sin(t),p[2]+r[2]*math.sin(a))
   m.face([q(a,t),q(a,u),q(b,u),q(b,t)],mat)
def plate(m,poly,y,depth,mat):
 front=[(x,y,z) for x,z in poly];back=[(x,y-depth,z) for x,z in poly]
 m.face(front[::-1],mat);m.face(back,mat)
 for i in range(len(poly)):
  j=(i+1)%len(poly);m.face([front[i],front[j],back[j],back[i]],mat)
m=Model('SM_HeroHelmet');ellipsoid(m,(0,.5,170),(10.3,10.5,13.1),S)
m.box((0,9.8,169),(17.8,5.8,16.5),D,3,1)
for side in (-1,1):
 x=side*4.4
 m.box((x,13,172.1),(6.4,1,2.25),C,.9,1)
 plate(m,[(side*1.2,175),(side*7.4,176.5),(side*9.3,174),(side*1.2,173.6)],13,1.5,S)
 m.box((side*9.6,.5,170),(2.6,8,12),D,1)
 m.cylinder((side*11,.5,171),3.1,1.5,G,16,0)
 plate(m,[(side*2,164),(side*8.4,167),(side*7.3,160),(side*2.2,158.6)],12,2.6,S)
m.box((0,13.6,167.6),(2.5,2.5,5.8),S,1)
m.box((0,11.8,161.4),(7.5,2.8,2.4),D,1)
for x in (-2.3,0,2.3):m.box((x,13.4,161.5),(.7,.5,1.2),G)
finish(m,'head')
m=Model('SM_HeroChest')
plate(m,[(-22,143),(-15,149),(15,149),(22,143),(17,127),(9,122),(-9,122),(-17,127)],14.7,6,D)
for side in (-1,1):
 plate(m,[(side*1.8,145.5),(side*14.3,146.5),(side*21,141),(side*15.4,129),(side*5.8,125),(side*2,133)],18.3,4,S)
 m.pipe([(side*3.5,19,144.7),(side*12.5,19,144.8),(side*17.6,19,140)],.7,G,8)
 m.pipe([(side*6,19,130.2),(side*13,19,134),(side*16,19,140)],.7,C,8)
# Chest reactor and a small sunrise crest, avoiding enemy-like red eyes.
m.cylinder((0,19,136),4.4,3,G,24,1);m.cylinder((0,21,136),3.1,1.3,D,24,1);m.cylinder((0,22,136),2.3,.8,C,24,1)
m.box((0,18.8,146.6),(1.2,1,4),G,.3)
finish(m,'spine_05')
m=Model('SM_HeroBack');plate(m,[(-14,148),(14,148),(13,124),(0,120),(-13,124)],-11,4,D)
for x in (-7,7):
 m.box((x,-16,136),(7,4,21),S,2)
 for z in (129,133,137,141):m.box((x,-18.3,z),(5.5,1,1),D)
m.box((0,-17,135),(3,3,19),C,1)
finish(m,'spine_05')
m=Model('SM_HeroAbdomen')
for z,w in [(122,18),(116,21),(110,22)]:
 m.box((0,12,z),(w,5,4.8),S,1.8,1);m.box((0,15,z),(3,.8,2.3),G,.5)
finish(m,'spine_03')
m=Model('SM_HeroPelvis');m.box((0,5,97),(30,20,9),D,4)
for s in (-1,1):
 plate(m,[(s*2,100),(s*16,101),(s*15,91),(s*8,87),(s*3,91)],14.5,5,S)
 m.box((s*16,4,98),(4,12,8),G,1)
finish(m,'pelvis')
for side,suffix in [(1,'l'),(-1,'r')]:
 upper=rig['upperarm_'+suffix]['p'];elbow=rig['lowerarm_'+suffix]['p'];thigh=rig['thigh_'+suffix]['p'];knee=rig['calf_'+suffix]['p']
 # Mirrored hand/foot endpoints; the supplied mannequin is symmetric.
 hand=rig['hand_l']['p'];hand=(side*hand[0],hand[1],hand[2]);foot=rig['foot_l']['p'];foot=(side*foot[0],foot[1],foot[2])
 m=Model('SM_HeroShoulder_'+suffix);p=(side*24,-1,145)
 ellipsoid(m,p,(11.5,10.5,10.6),S,20,10)
 m.pipe([(side*16,7,149),(side*24,9,153),(side*31,7,148)],1.2,G,8)
 m.cylinder((side*29,8,144),3,2,D,16,1);m.cylinder((side*29,9.3,144),1.8,.5,C,16,1)
 finish(m,'upperarm_'+suffix)
 def lerp(a,b,t):return tuple(a[i]+(b[i]-a[i])*t for i in range(3))
 for name,bone,a,b,radius in [('UpperArm','upperarm_'+suffix,upper,elbow,6.7),('Gauntlet','lowerarm_'+suffix,elbow,hand,6.6),('Thigh','thigh_'+suffix,thigh,knee,9.3),('Shin','calf_'+suffix,knee,foot,7.1)]:
  m=Model('SM_Hero'+name+'_'+suffix);start=lerp(a,b,.21);end=lerp(a,b,.78)
  m.pipe([start,end],radius,S,8)
  frontstart=(start[0],start[1]+radius*.88,start[2]);frontend=(end[0],end[1]+radius*.88,end[2])
  m.pipe([frontstart,frontend],1.05,D,6)
  for t in (.27,.72):
   p=lerp(a,b,t);m.box((p[0],p[1]+radius,p[2]),(3.2,1.8,3.2),G,.6)
  if name in ('Gauntlet','Shin'):
   m.pipe([(frontstart[0]+side*2,frontstart[1]+.5,frontstart[2]),(frontend[0]+side*2,frontend[1]+.5,frontend[2])],.65,C,6)
  finish(m,bone)
with open(os.path.join(ROOT,'hero_armour_manifest.json'),'w') as f:json.dump(specs,f,indent=2)
print('Original hero armour parts:',len(specs))
