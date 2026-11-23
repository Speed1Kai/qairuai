"""Author reusable blast-door meshes and original mono audio in centimetres."""
import ast,math,os,json,wave,struct,random
# Reuse the established mesh builder without running the older room generator.
source=os.path.join(os.path.dirname(__file__),'Generate_IndustrialMeshes.py')
tree=ast.parse(open(source,encoding='utf8').read(),source)
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','LabTutorial','Industrial','Source'))
os.makedirs(ROOT,exist_ok=True)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Model'],type_ignores=[]),source,'exec'))

def save_uv_model(self):
 path=os.path.join(ROOT,self.name+'.obj');idx=1;materials=sorted({m for p,m in self.faces})
 with open(path,'w') as f:
  f.write('mtllib '+self.name+'.mtl\no '+self.name+'\n')
  for points,mat in self.faces:
   pts=[(x,-y,z) for x,y,z in points][::-1]
   d=[pts[1][i]-pts[0][i] for i in range(3)];e=[pts[2][i]-pts[0][i] for i in range(3)]
   normal=(d[1]*e[2]-d[2]*e[1],d[2]*e[0]-d[0]*e[2],d[0]*e[1]-d[1]*e[0])
   drop=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=drop]
   for p in pts:f.write('v %.6f %.6f %.6f\nvt %.6f %.6f\n'%(*p,p[axes[0]]*.01,p[axes[1]]*.01))
   f.write('usemtl '+mat+'\n')
   for j in range(1,len(pts)-1):
    ids=(idx,idx+j,idx+j+1);f.write('f '+' '.join('%d/%d'%(n,n) for n in ids)+'\n')
   idx+=len(pts)
 with open(path[:-4]+'.mtl','w') as f:
  for mat in materials:f.write('newmtl '+mat+'\nKd .2 .2 .2\n')
 return {'name':self.name,'vertices':idx-1,'faces':len(self.faces),'materials':materials}
Model.save=save_uv_model

models=[]
for sign,label in [(-1,'Left'),(1,'Right')]:
 m=Model('SM_BlastDoor_'+label)
 m.box((0,0,205),(38,174,402),bevel=7,axis=0)
 for face in (-1,1):
  x=face*23
  m.box((x,0,205),(8,156,381),'M_Rubber',6,0)
  for z,h in [(52,68),(190,174),(343,86)]:
   m.box((x+face*4,0,z),(7,147,h),bevel=9,axis=0)
   m.box((x+face*8,0,z),(2,128,h-19),'M_DoorArmor',8,0)
  for y in (-78,78):
   m.box((x+face*6,y,205),(12,12,382),bevel=2,axis=0)
   for z in range(28,395,31):m.cylinder((face*36,y,z),2.2,3,'M_Chrome',6,0)
  for z in (95,296,386):
   m.box((face*33,0,z),(5,148,6),'M_RustyIron',1,0)
  for z,h in [(111,33),(371,16)]:m.box((face*35,0,z),(3,145,h),'M_DoorHazard',2,0)
  # Chamfered diagonal reinforcement across the central armour panel.
  y0,y1=-62,62;z0,z1=(242,155) if sign<0 else (155,242)
  m.pipe([(face*39,y0,z0),(face*39,y1,z1)],4.2,'M_DistressedMetal',6)
  for y,z in [(y0,z0),(y1,z1)]:m.cylinder((face*43,y,z),3.,3,'M_Chrome',6,0)
  m.box((face*35,-sign*52,201),(4,18,49),'M_Rubber',4,0)
  for z in (185,217):m.cylinder((face*39,-sign*52,z),2.,3,'M_Chrome',6,0)
  m.box((face*34,sign*24,268),(2,51,21),'M_Rubber',2,0)
  for z in (264,270):m.box((face*35.5,sign*24,z),(1,40,1.6),'M_Keys')
 # Central interlocking seal; the two leaves do not intersect.
 m.box((0,-sign*85,205),(41,3,396),'M_Rubber',1,0)
 models.append(m.save())

m=Model('SM_BlastDoor_SplitFrame')
for side in (-1,1):
 y=side*199
 m.box((0,y,212),(108,46,424),bevel=6,axis=0)
 for face in (-1,1):
  m.box((face*58,y,210),(15,40,420),bevel=3,axis=0)
  for z in (28,95,167,242,319,390):m.cylinder((face*68,side*208,z),3.2,3,'M_Chrome',6,0)
  # Chamfer corner gussets.
  m.pipe([(face*59,side*176,360),(face*59,side*141,401)],9,'M_DistressedMetal',6)
 m.box((0,y,9),(120,65,18),'M_RustyIron',3)
 m.box((0,side*176,205),(48,7,402),'M_Rubber',1,0)
 # Side pockets conceal the fully retracted panels, with an open mouth at y=220.
 for face in (-1,1):
  m.box((face*48,side*287,205),(10,142,410),bevel=5,axis=0)
  for z in (72,205,337):m.box((face*55,side*291,z),(5,122,14),bevel=2,axis=0)
 m.box((0,side*362,205),(102,10,410),bevel=3,axis=0)
 m.box((0,side*287,414),(102,148,12),bevel=3)
 m.box((0,side*287,4),(102,148,8),'M_Rubber')
m.box((0,0,425),(112,451,42),bevel=6,axis=0)
for face in (-1,1):
 m.box((face*61,0,422),(14,174,34),'M_Rubber',4,0)
 m.box((face*69,0,422),(4,124,27),bevel=2,axis=0)
 for y in (-73,73):m.cylinder((face*73,y,422),2.5,3,'M_Chrome',6,0)
m.box((0,0,3),(108,350,6),'M_RustyIron',2)
models.append(m.save())

m=Model('SM_BlastDoor_HydraulicServices')
for side in (-1,1):
 y=side*243
 for face in (-1,1):
  x=face*66
  m.cylinder((x,y,174),10,208,'M_Chrome',16)
  m.cylinder((x,y,104),15,140,'M_DistressedMetal',20)
  for z in (38,168,285):
   m.box((x,side*247,z),(33,47,13),bevel=3)
   m.cylinder((face*85,side*250,z),3,3,'M_Chrome',6,0)
  for n in range(3):
   yy=side*(265+n*7)
   m.pipe([(face*58,yy,50),(face*69,yy,80),(face*75,yy,215),(face*77,yy,330),(face*60,side*(264+n*8),393),(face*30,side*(257+n*8),412)],2.2,'M_Rubber',8)
  # Horizontal drive cylinders connect to leaf-mounted sliding piston rods.
  m.cylinder((face*40,side*270,350),8,155,'M_DistressedMetal',16,1)
  m.cylinder((face*40,side*177,350),4,43,'M_Chrome',12,1)
models.append(m.save())

m=Model('SM_BlastDoor_PistonRod')
m.cylinder((0,0,0),4,168,'M_Chrome',12,1)
m.cylinder((0,-77,0),9,12,'M_DistressedMetal',12,1)
models.append(m.save())

for name,duration in [('S_BlastDoorHydraulicRelease',.55),('S_BlastDoorSlide',2.2)]:
 rng=random.Random(252);sr=22050;data=bytearray();low=0.
 for i in range(int(duration*sr)):
  t=i/sr;n=rng.uniform(-1,1);low=.91*low+.09*n
  if 'Release' in name:env=min(1,t*100)*math.exp(-t*7);sample=(n-low)*.23*env+low*.15*env
  else:
   env=min(1,t*7)*min(1,(duration-t)*8)
   sample=env*(.13*math.sin(math.tau*42*t)+.045*math.sin(math.tau*83*t)+.18*low+.012*n)
  data.extend(struct.pack('<h',int(max(-.8,min(.8,sample))*32767)))
 with wave.open(os.path.join(ROOT,name+'.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(data)
with open(os.path.join(ROOT,'split_door_manifest.json'),'w') as f:json.dump(models,f,indent=2)
print(json.dumps(models))
