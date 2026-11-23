"""Original campus access bridge: centimetres, explicit UVs, shared materials."""
import ast,os,math,json,random
scripts=os.path.dirname(__file__)
ROOT=os.path.abspath(os.path.join(scripts,'..','..','SourceAssets','CampusBridge'));os.makedirs(ROOT,exist_ok=True)
for file,kind,name in [('Generate_IndustrialMeshes.py',ast.ClassDef,'Model'),('Generate_SplitDoorMeshes.py',ast.FunctionDef,'save_uv_model')]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name==name],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
rng=random.Random(219);specs=[]
con='M_RuinConcrete';steel='M_RuinSteel';rust='M_Oxide';road='M_Asphalt';paint='M_LanePaint'
def slab(m,outline,top,bottom,mat):
 m.face([(x,y,top) for x,y in outline],mat);m.face([(x,y,bottom) for x,y in reversed(outline)],con)
 for i in range(len(outline)):
  a=outline[i];b=outline[(i+1)%len(outline)];m.face([(*a,bottom),(*b,bottom),(*b,top),(*a,top)],con)
for side,name in [(-1,'SM_BridgeCampusHalf'),(1,'SM_BridgeCityHalf')]:
 m=Model(name)
 # Relative Y=0 is the centre of the missing span. All paths are physically split.
 edge=[(-1100,side*550),(-820,side*490),(-540,side*600),(-240,side*480),(30,side*550),(310,side*470),(600,side*620),(880,side*530),(1100,side*590)]
 outline=[(-1100,side*3000),(1100,side*3000)]+list(reversed(edge))
 if side==1:outline=list(reversed(outline))
 slab(m,outline,0,-110,con)
 inner=[(-900,side*3000),(900,side*3000),(900,side*640),(300,side*620),(0,side*680),(-350,side*600),(-900,side*650)]
 if side==1:inner=list(reversed(inner))
 slab(m,inner,3,-1,road)
 for y in range(900,2901,420):
  m.box((0,side*y,4),(16,220,1),paint)
  for x in (-890,890):m.box((x,side*y,4),(10,360,1),paint)
 for x in (-1000,1000):
  m.box((x,side*1800,16),(150,2400,32),con,6)
  for y in range(850,3000,240):
   m.box((x,side*y,84),(12,15,136),steel,2)
  m.pipe([(x,side*3000,145),(x,side*900,145),(x+side*25,side*650,115),(x+side*80,side*510,65)],6,steel,10)
  m.pipe([(x,side*3000,80),(x,side*900,80),(x-side*40,side*630,40)],4,steel,8)
 for x in (-710,0,710):
  m.box((x,side*1800,-135),(75,2350,80),steel,3)
  m.pipe([(x,side*700,-135),(x+45,side*500,-210),(x+60,side*380,-280)],5,rust,8)
 for i in range(29):
  x=-1040+i*74;y=side*rng.uniform(510,625)
  m.pipe([(x,y+side*90,-40),(x+12,y,-55),(x+rng.uniform(-30,30),y-side*rng.uniform(80,210),-rng.uniform(35,120))],1.7,rust,6)
 # Abutments and paired piers leave the channel visibly open beneath the deck.
 m.box((0,side*2700,-600),(2500,280,1200),con,18)
 for x in (-800,800):m.box((x,side*1500,-900),(220,350,1700),con,16)
 specs.append(m.save())
m=Model('SM_BridgeFallenSpan')
slab(m,[(-900,-400),(850,-510),(1100,330),(700,510),(-950,430)],0,-110,con)
m.box((0,0,3),(1570,700,5),road,12)
for x in (-710,0,710):m.box((x,0,-130),(75,840,65),steel,3)
for i in range(10):m.pipe([(-850+i*180,350,-40),(-820+i*180,590,-85)],2,rust,6)
specs.append(m.save())
with open(os.path.join(ROOT,'bridge_meshes.json'),'w') as f:json.dump(specs,f,indent=2)
