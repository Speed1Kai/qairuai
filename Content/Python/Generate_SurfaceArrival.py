"""Original low-memory surface kit: damaged architecture, wrecks and ambient audio."""
import ast, math, os, json, random, wave, struct
scripts=os.path.dirname(__file__)
ROOT=os.path.abspath(os.path.join(scripts,'..','Surface','Source'));os.makedirs(ROOT,exist_ok=True)
for file,kind,name in [('Generate_IndustrialMeshes.py',ast.ClassDef,'Model'),('Generate_SplitDoorMeshes.py',ast.FunctionDef,'save_uv_model')]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read())
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name==name],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
R=random.Random(731);models=[]
con='M_RuinConcrete';steel='M_RuinSteel';black='M_Charcoal';glass='M_DeadGlass';rust='M_Oxide';pale='M_AIWhite';glow='M_AILight'
# Windows have actual recesses. Missing bays expose floor plates and rebar.
for variant,floors,w,d in [('A',9,1680,1320),('B',13,1260,1260),('C',6,2100,1260),('D',17,1680,1680)]:
 m=Model('SM_Ruin_'+variant);cols=round(w/420);step=w/cols
 for level in range(floors):
  z=level*350;top=level>=floors-3
  broken=R.randint(1,cols-1) if top else cols
  # Each floor has a different broken edge instead of a perfect roof box.
  width=w if not top else w-(cols-broken)*step
  cx=-(w-width)/2
  m.box((cx,0,z+14),(width,d,28),con,12)
  m.box((cx,0,z-8),(width,d-80,18),black)
  for ix in range(cols+1):
   x=-w/2+ix*step
   if top and ix>broken:continue
   for sy in (-1,1):
    m.box((x,sy*(d/2-24),z+170),(48,62,328),con,5)
    if R.random()<.18:
     m.pipe([(x,sy*d/2,z+320),(x+R.uniform(-35,35),sy*d/2,z+410)],3,rust,5)
  for sy in (-1,1):
   for ix in range(cols):
    if top and ix>=broken:continue
    x=-w/2+(ix+.5)*step
    m.box((x,sy*d/2,z+304),(step-40,45,88),con,4)
    if R.random()<(.5 if top else .22):continue
    m.box((x,sy*(d/2-14),z+161),(step-62,8,185),glass)
    for dx in (-step/2+35,0,step/2-35):m.box((x+dx,sy*(d/2+2),z+161),(8,12,190),steel)
    m.box((x,sy*(d/2+4),z+68),(step-57,24,10),steel)
  for sx in (-1,1):
   if top and sx==1:continue
   for iy in range(round(d/420)):
    y=-d/2+(iy+.5)*420
    m.box((sx*w/2,y,z+173),(35,45,315),con,4)
    m.box((sx*w/2,y,z+300),(35,414,86),con,3)
    if R.random()>.28:m.box((sx*(w/2-10),y+180,z+157),(8,280,184),glass)
 for ix in range(broken+1):
  x=-w/2+ix*step
  m.pipe([(x,-d/2,(floors-1)*350+320),(x+30,-d/2+10,floors*350+180)],4,rust,5)
 m.box((-w*.25,0,floors*350+18),(w*.22,d*.65,35),steel,12)
 models.append(m.save())
m=Model('SM_RubbleCluster')
for i in range(18):
 x,y=R.uniform(-240,240),R.uniform(-170,170);sx,sy,sz=R.uniform(35,125),R.uniform(30,90),R.uniform(15,65)
 start=len(m.faces);m.box((x,y,sz*.45),(sx,sy,sz),con if i%4 else rust,8)
 m.faces[start:]=[([(px+R.uniform(-6,6),py+R.uniform(-6,6),pz+R.uniform(-5,5)) for px,py,pz in pts],mat) for pts,mat in m.faces[start:]]
for i in range(5):m.pipe([(R.uniform(-190,190),R.uniform(-120,120),30),(R.uniform(-190,190),R.uniform(-120,120),R.uniform(70,120))],2.5,rust,5)
models.append(m.save())
m=Model('SM_WreckedSedan')
m.box((0,0,50),(490,184,70),steel,24)
m.box((-20,0,105),(238,163,85),black,29,1)
m.box((-17,0,141),(196,147,12),steel,15)
for sy in (-1,1):
 for x in (-72,46):m.box((x,sy*83,111),(103,5,49),glass,9,1)
 for x in (-158,151):
  m.cylinder((x,sy*92,40),40,20,black,12,1);m.cylinder((x,sy*105,40),21,3,rust,10,1)
 m.box((10,sy*95,60),(290,4,5),rust)
 m.box((197,sy*67,69),(30,22,15),glass,3)
 m.box((-240,sy*67,68),(9,28,13),rust,2)
m.box((228,0,43),(32,154,16),rust,5)
for y in range(-45,46,15):m.box((247,y,57),(2,7,20),black)
models.append(m.save())
m=Model('SM_FallenOverpass')
m.box((0,0,0),(1600,940,96),con,28)
for y in (-405,405):
 m.box((0,y,-115),(1540,82,210),steel,8)
 for x in range(-740,741,130):m.box((x,y,105),(34,35,160),con,5)
 m.box((0,y,181),(1560,40,24),steel,6)
for y in range(-340,341,100):m.pipe([(-900,y,-28),(-780,y,12),(830,y,-10),(940,y,65)],4,rust,6)
models.append(m.save())
m=Model('SM_DeadStreetlight')
m.cylinder((0,0,12),38,24,con,12)
m.pipe([(0,0,0),(0,0,600),(0,45,820),(0,220,870)],11,steel,10)
m.box((0,235,851),(100,135,28),steel,12)
m.box((0,235,833),(72,100,3),glass,8)
models.append(m.save())
m=Model('SM_ConcreteBarrier')
m.box((0,0,35),(300,70,70),con,12)
m.box((0,0,86),(290,32,34),con,8)
for x in (-105,105):m.box((x,-36,66),(22,2,21),rust,2)
models.append(m.save())
m=Model('SM_DeadTree')
m.pipe([(0,0,0),(18,3,170),(-7,14,380),(30,13,610)],12,black,7)
for sign in (-1,1):
 for z in (220,370,500):
  m.pipe([(8,10,z),(sign*75,15,z+80),(sign*160,40,z+180)],5,black,5)
  m.pipe([(sign*75,15,z+80),(sign*90,-45,z+148)],3,black,5)
models.append(m.save())
# The AI core is deliberately clean and geometrically unbroken against the ruins.
m=Model('SM_ArchitectTower');rings=[]
for z,rx,ry in [(0,2400,2000),(3500,1900,1700),(32000,1250,1100),(44000,780,680),(49000,250,220),(52000,25,25)]:
 rings.append([(math.cos(math.tau*i/8)*rx,math.sin(math.tau*i/8)*ry,z) for i in range(8)])
for a,b in zip(rings,rings[1:]):
 for i in range(8):j=(i+1)%8;m.face([a[i],a[j],b[j],b[i]],pale)
for i in range(8):
 angle=math.tau*i/8
 m.pipe([(math.cos(angle)*2420,math.sin(angle)*2020,0),(math.cos(angle)*1920,math.sin(angle)*1720,3500),(math.cos(angle)*1270,math.sin(angle)*1120,32000),(math.cos(angle)*795,math.sin(angle)*695,44000),(math.cos(angle)*265,math.sin(angle)*235,49000)],24,glow,5)
for z in (3700,18000,32000):m.ring((0,0,z),2200 if z==3700 else 1750 if z==18000 else 1400,2150 if z==3700 else 1700 if z==18000 else 1350,40,glow,48)
models.append(m.save())
with open(os.path.join(ROOT,'surface_kit.json'),'w') as f:json.dump(models,f,indent=2)
# Original stereo-free loop: turbulent wind, a far siren, substation resonance.
rate=22050;duration=12;count=rate*duration;low=0.;rng=random.Random(42);samples=[]
for i in range(count):
 t=i/rate;low=.985*low+.015*rng.uniform(-1,1)
 wind=low*1.35*(.55+.20*math.sin(math.tau*t/duration)+.1*math.sin(math.tau*3*t/duration))
 siren=.018*math.sin(math.tau*(260*t-20*duration/math.tau*math.cos(math.tau*t/duration)))*(.5+.5*math.cos(math.tau*t/duration))
 hum=.025*math.sin(math.tau*40*t)+.012*math.sin(math.tau*67*t)
 samples.append(struct.pack('<h',int(max(-1,min(1,wind+siren+hum))*21000)))
with wave.open(os.path.join(ROOT,'S_SurfaceWind.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(b''.join(samples))
print('Surface kit:',len(models),'meshes;',sum(x['vertices'] for x in models),'vertices')
