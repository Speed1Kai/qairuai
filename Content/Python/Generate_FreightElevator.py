"""Original lightweight elevator cabin, control station and mono audio."""
import ast,math,os,json,wave,struct,random
scripts=os.path.dirname(__file__)
ROOT=os.path.abspath(os.path.join(scripts,'..','LabTutorial','Elevator','Source'));os.makedirs(ROOT,exist_ok=True)
for file,kind,name in [('Generate_IndustrialMeshes.py',ast.ClassDef,'Model'),('Generate_SplitDoorMeshes.py',ast.FunctionDef,'save_uv_model')]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read())
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name==name],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
models=[]
m=Model('SM_FreightCabin')
m.box((0,0,12),(520,510,24),bevel=8)
for y in (-195,-65,65,195):m.box((0,y,24),(488,124,1),'M_DoorArmor',3)
for x in range(-230,231,28):
 for y in (-205,-155,-105,-55,-5,45,95,145,195):
  m.box((x,y,25),(12,2,1),'M_Chrome',.5)
for side in (-1,1):
 y=side*252
 m.box((0,y,231),(448,18,414),bevel=6,axis=1)
 for x in (-172,-57,57,172):
  m.box((x,side*240,232),(105,8,368),'M_DoorArmor',5,1)
  for z in (80,180,280,386):m.cylinder((x-42,side*234,z),2.2,3,'M_Chrome',6,1)
 for x in (-221,-108,108,221):m.box((x,side*233,231),(12,16,410),'M_RustyIron',2)
 for z in (307,337):
  m.cylinder((0,side*225,z),4,420,'M_DistressedMetal',12,0)
  for x in (-195,-95,95,195):m.cylinder((x,side*225,z),7,7,'M_Chrome',12,0)
 for x in (-150,150):
  m.box((x,side*225,374),(76,20,36),bevel=3,axis=1)
  m.box((x,side*212,374),(56,4,19),'M_DoorStatus_Red',2,1)
 for x in (-135,135):
  m.box((x,side*231,100),(80,7,43),'M_Rubber',2,1)
  for dx in range(-30,31,10):m.box((x+dx,side*226,100),(3,4,31),'M_Chrome')
 # Door jambs and chamfered header on both ends of the moving cabin.
 for end in (-1,1):
  m.box((end*251,side*181,221),(40,34,398),bevel=4,axis=0)
  m.box((end*251,side*248,424),(47,165,32),bevel=3,axis=0)
  for z in (46,140,240,340,405):m.cylinder((end*275,side*185,z),3,4,'M_Chrome',6,0)
for end in (-1,1):
 m.box((end*251,0,426),(44,380,34),bevel=5,axis=0)
 m.box((end*252,0,27),(44,330,6),'M_DoorHazard',2)
 for side in (-1,1):m.pipe([(end*244,side*160,402),(end*244,side*131,426)],8,'M_DistressedMetal',6)
m.box((0,0,449),(530,518,20),bevel=6)
m.box((0,0,434),(236,278,14),'M_Rubber',3)
m.box((0,0,425),(200,242,4),'M_ElevatorWarm',2)
for x in range(-96,97,16):m.box((x,0,421),(3,244,4),'M_DistressedMetal')
for y in range(-112,113,16):m.box((0,y,420),(198,3,4),'M_DistressedMetal')
for side in (-1,1):
 m.pipe([(-205,side*199,418),(-130,side*199,405),(-20,side*199,393),(85,side*199,402),(205,side*199,418)],2.5,'M_Rubber',8)
models.append(m.save())

m=Model('SM_FreightControlPanel')
m.box((0,0,180),(110,36,166),bevel=8,axis=1)
m.box((0,-21,181),(98,8,149),'M_Rubber',5,1)
m.box((-12,-27,220),(63,4,45),'M_Chrome',3,1)
m.box((-12,-30,220),(52,3,33),'M_CRTGlass',2,1)
for z in (210,218,226):m.box((-16,-32,z),(35,1,1.3),'M_CyanIndicator')
for x in (-33,-12,9,30):
 for z in (177,190):m.box((x,-28,z),(14,5,8),'M_Keys',1)
m.cylinder((24,-32,144),13,7,'M_Chrome',20,1)
m.cylinder((24,-37,144),9,4,'M_DoorStatus_Green',20,1)
m.box((-22,-28,144),(33,5,22),'M_AmberIndicator',2,1)
for x in (-46,46):
 for z in (112,252):m.cylinder((x,-27,z),2.5,3,'M_Chrome',6,1)
m.pipe([(-39,17,102),(-38,24,75),(-20,24,53),(8,20,45)],3,'M_Rubber',10)
models.append(m.save())

m=Model('SM_FreightRoofDrive')
for x in (-190,190):
 m.cylinder((x,0,484),10,480,'M_Chrome',16,1)
 for side in (-1,1):
  y=side*222
  m.box((x,y,466),(73,48,34),bevel=4)
  m.cylinder((x,y,490),34,18,'M_DistressedMetal',32,1)
  m.cylinder((x,y-12,490),22,6,'M_Rubber',24,1)
  m.cylinder((x,y-17,490),10,9,'M_Chrome',16,1)
  for i in range(24):
   t=i*math.tau/24;m.box((x+35*math.cos(t),y,490+35*math.sin(t)),(7,21,7),'M_RustyIron',1)
models.append(m.save())
with open(os.path.join(ROOT,'elevator_manifest.json'),'w') as f:json.dump(models,f,indent=2)

for name,duration in [('S_FreightMotor',4.),('S_FreightDoor',2.8),('S_FreightArrival',1.1)]:
 sr=22050;rng=random.Random(441);data=bytearray();low=0.
 for i in range(int(sr*duration)):
  t=i/sr;n=rng.uniform(-1,1);low=.96*low+.04*n
  if 'Arrival' in name:sample=(.18*math.sin(math.tau*660*t)+.08*math.sin(math.tau*990*t))*math.exp(-t*4)
  else:
   env=min(1,t*8)*min(1,(duration-t)*8);freq=43 if 'Motor' in name else 61
   sample=env*(.12*math.sin(math.tau*freq*t)+.055*math.sin(math.tau*(freq+29)*t)+low*.24)+n*.055*math.exp(-t*9)
  data.extend(struct.pack('<h',int(max(-.8,min(.8,sample))*32767)))
 with wave.open(os.path.join(ROOT,name+'.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(data)
print(json.dumps(models))
