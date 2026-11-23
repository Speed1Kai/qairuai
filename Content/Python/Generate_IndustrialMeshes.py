"""Generate modest polygon counts and reusable industrial assets in centimetres."""
import math,os,json,wave,struct,random
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','LabTutorial','Industrial','Source'))
os.makedirs(ROOT,exist_ok=True)

class Model:
    def __init__(self,name):self.name=name;self.faces=[]
    def face(self,pts,mat='M_DistressedMetal'):self.faces.append((pts,mat))
    def box(self,p,s,mat='M_DistressedMetal',bevel=0,axis=2):
        first=len(self.faces)
        a,b=[i for i in range(3) if i!=axis];c=axis
        hx,hy=s[a]/2,s[b]/2;d=min(bevel,hx*.5,hy*.5)
        poly=[(-hx+d,-hy),(hx-d,-hy),(hx,-hy+d),(hx,hy-d),(hx-d,hy),(-hx+d,hy),(-hx,hy-d),(-hx,-hy+d)] if d else [(-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy)]
        rings=[]
        for z in (-s[c]/2,s[c]/2):
            ring=[]
            for x,y in poly:
                q=list(p);q[a]+=x;q[b]+=y;q[c]+=z;ring.append(tuple(q))
            rings.append(ring)
        self.face(list(reversed(rings[0])),mat);self.face(rings[1],mat)
        for i in range(len(poly)):j=(i+1)%len(poly);self.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],mat)
        if axis==1:self.faces[first:]=[(p[::-1],m) for p,m in self.faces[first:]]
    def cylinder(self,p,r,h,mat='M_DistressedMetal',segments=16,axis=2):
        first=len(self.faces)
        a,b=[i for i in range(3) if i!=axis];rings=[]
        for z in (-h/2,h/2):
            ring=[]
            for i in range(segments):
                t=i*math.tau/segments;q=list(p);q[a]+=r*math.cos(t);q[b]+=r*math.sin(t);q[axis]+=z;ring.append(tuple(q))
            rings.append(ring)
        self.face(list(reversed(rings[0])),mat);self.face(rings[1],mat)
        for i in range(segments):j=(i+1)%segments;self.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],mat)
        if axis==1:self.faces[first:]=[(p[::-1],m) for p,m in self.faces[first:]]
    def ring(self,p,ro,ri,h,mat='M_DistressedMetal',n=48):
        for i in range(n):
            t=i*math.tau/n;u=(i+1)*math.tau/n
            def v(r,a,z):return (p[0]+r*math.cos(a),p[1]+r*math.sin(a),p[2]+z)
            self.face([v(ri,t,h/2),v(ro,t,h/2),v(ro,u,h/2),v(ri,u,h/2)],mat)
            self.face([v(ro,t,-h/2),v(ro,u,-h/2),v(ro,u,h/2),v(ro,t,h/2)],mat)
            self.face([v(ri,u,-h/2),v(ri,t,-h/2),v(ri,t,h/2),v(ri,u,h/2)],mat)
            self.face([v(ri,u,-h/2),v(ro,u,-h/2),v(ro,t,-h/2),v(ri,t,-h/2)],mat)
    def pipe(self,pts,r=2,mat='M_Rubber',n=8):
        for a,b in zip(pts,pts[1:]):
            d=[b[j]-a[j] for j in range(3)];l=math.sqrt(sum(v*v for v in d));d=[v/l for v in d]
            ref=(0,0,1) if abs(d[2])<.95 else (0,1,0)
            u=[d[1]*ref[2]-d[2]*ref[1],d[2]*ref[0]-d[0]*ref[2],d[0]*ref[1]-d[1]*ref[0]];l=math.sqrt(sum(v*v for v in u));u=[v/l for v in u]
            v=[d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0]]
            rings=[[(p[j]+r*(math.cos(t*math.tau/n)*u[j]+math.sin(t*math.tau/n)*v[j])) for j in range(3)] for p in (a,b) for t in range(n)]
            for i in range(n):j=(i+1)%n;self.face([rings[i],rings[j],rings[n+j],rings[n+i]],mat)
    def save(self):
        path=os.path.join(ROOT,self.name+'.obj');idx=1;materials=sorted({m for p,m in self.faces})
        with open(path,'w') as f:
            f.write('mtllib '+self.name+'.mtl\no '+self.name+'\ns off\n')
            for pts,mat in self.faces:
                f.write('usemtl '+mat+'\n')
                # OBJ is right handed; reverse Y for the import into Unreal.
                pts=[(x,-y,z) for x,y,z in pts][::-1]
                for x,y,z in pts:f.write('v %.6f %.6f %.6f\n'%(x,y,z))
                for j in range(1,len(pts)-1):f.write('f %d %d %d\n'%(idx,idx+j,idx+j+1))
                idx+=len(pts)
        with open(path[:-4]+'.mtl','w') as f:
            for m in materials:f.write('newmtl '+m+'\nKd .2 .2 .2\n')
        return {'name':self.name,'vertices':idx-1,'faces':len(self.faces),'materials':materials}

models=[]
m=Model('SM_IndustrialWorkbench')
m.box((0,0,101),(310,115,12),bevel=6)
for x in (-135,135):
 m.box((x,30,48),(28,74,96),bevel=4);m.box((x,-44,48),(18,16,96));m.box((x,0,7),(45,110,12),'M_RustyIron',3)
 m.box((x,35,65),(30,76,30),'M_Rubber',2)
m.box((0,43,50),(270,13,70),bevel=2)
m.box((-25,18,114),(85,65,16),bevel=5)
m.box((-25,20,155),(119,82,78),bevel=9,axis=1)
m.box((-25,-24,156),(105,7,65),'M_Rubber',7,axis=1)
m.box((-25,-28,157),(89,3,49),'M_CRTGlass',6,axis=1)
for x in (15,24):m.cylinder((x,-30,126),2.4,3,'M_Chrome',10,1)
m.box((-22,-36,112),(128,40,7),'M_Rubber',3)
for row in range(4):
 for col in range(15):m.box((-79+col*7.8,-50+row*8,117),(6,5.4,3),'M_Keys',.6)
m.box((96,18,135),(61,70,53),bevel=4,axis=1)
m.box((96,-18,142),(48,3,29),'M_Rubber',2,axis=1)
m.box((96,-20,142),(39,1,22),'M_CRTGlass',1,axis=1)
for x in (77,89,101,113):m.cylinder((x,-21,119),2,2,'M_Chrome',8,1)
for z in range(121,159,6):m.box((-88,22,z),(1,37,2),'M_Rubber')
for x in (-145,145):
 for y in (-47,47):m.cylinder((x,y,108),2.3,2,'M_Chrome',6)
m.pipe([(104,41,118),(120,50,110),(147,40,108),(166,40,42),(160,24,5),(203,18,3)],1.8)
m.pipe([(-70,55,130),(-76,60,103),(-120,66,87),(-141,55,32),(-158,50,4)],2.2)
models.append(m.save())

m=Model('SM_DockingGenerator')
m.cylinder((0,0,6),64,12,'M_Rubber',48);m.cylinder((0,0,17),56,18,segments=48)
m.ring((0,0,29),53,42,6,n=48);m.ring((0,0,31),43,39,3,'M_CyanIndicator')
m.cylinder((0,0,28),38,5,'M_Rubber',48);m.cylinder((0,0,32),16,2,'M_CyanIndicator',32)
for i in range(12):
 a=i*math.tau/12;x=math.cos(a)*51;y=math.sin(a)*51
 m.cylinder((x,y,34),2,3,'M_Chrome',6)
for i in range(8):
 a=i*math.tau/8;x=math.cos(a)*57;y=math.sin(a)*57
 m.box((x,y,19),(14,14,28),bevel=2)
m.pipe([(55,20,12),(72,32,5),(95,40,4)],3)
models.append(m.save())

m=Model('SM_HeavyDoorPanel')
m.box((0,0,207),(38,350,414),bevel=8,axis=0)
for side in (-1,1):
 for j in range(3):
  m.box((side*22,0,91+j*108),(7,318,96),bevel=4,axis=0)
  m.box((side*28,0,44+j*113),(8,328,9),'M_RustyIron',2,0)
 for y in (-153,153):
  m.box((side*28,y,207),(9,16,367),bevel=2,axis=0)
  for z in range(33,399,42):m.cylinder((side*35,y,z),3,4,'M_Chrome',6,0)
 m.box((side*29,0,34),(3,302,44),'M_HazardStripes',2,0)
 m.box((side*29,0,405),(5,330,12),'M_Rubber',2,0)
models.append(m.save())

m=Model('SM_HeavyDoorFrame')
for side in (-1,1):
 y=side*206
 m.box((0,y,225),(98,52,450),bevel=7,axis=0)
 m.box((-55,y,228),(15,38,446),bevel=3,axis=0)
 m.box((-56,side*177,225),(8,10,423),'M_Rubber')
 m.cylinder((-64,y,230),10,348,'M_Chrome',16)
 m.cylinder((-64,y,146),16,171,'M_DistressedMetal',20)
 for z in (63,207,369):m.box((-70,y,z),(26,63,16),bevel=3)
 for z in (43,105,292,417):m.cylinder((-66,side*222,z),3,5,'M_Chrome',6,0)
 m.box((-64,y,385),(8,17,34),'M_AmberIndicator',2,0)
 m.box((0,y,11),(126,82,22),'M_RustyIron',4)
m.box((0,0,459),(100,465,60),bevel=7,axis=0)
m.box((-56,0,457),(14,352,32),'M_RustyIron',3,0)
for y in (-180,180):m.box((-63,y,464),(8,25,18),'M_RedIndicator',2,0)
m.box((0,0,5),(110,357,10),'M_Rubber')
for side in (-1,1):
 m.pipe([(35,side*213,440),(72,side*220,410),(78,side*223,180),(85,side*240,80)],5,'M_Rubber',10)
models.append(m.save())

m=Model('SM_WallReinforcement')
m.box((0,0,225),(36,40,450),bevel=4)
m.box((-25,0,225),(18,86,450),bevel=3)
for z in (35,135,235,335,425):
 m.box((-36,0,z),(5,68,34),'M_RustyIron',3,0)
 for y in (-23,23):m.cylinder((-40,y,z),3,4,'M_Chrome',6,0)
models.append(m.save())

m=Model('SM_VentDuct')
m.box((0,0,0),(300,82,58),bevel=8)
for x in range(-140,141,30):m.box((x,0,0),(4,88,64),'M_RustyIron',3)
for y in (-28,28):m.box((0,y,-30),(280,4,3),'M_Rubber')
models.append(m.save())

# Rear cylindrical capsule shell, cable glands and a ceiling umbilical.
m=Model('SM_CapsuleArmor')
for i in range(46):
 a=math.radians(65+i*5);b=a+math.radians(5)
 def q(r,t,z):return (r*math.cos(t),r*math.sin(t),z)
 for r,reverse in ((117,False),(109,True)):
  pts=[q(r,a,25),q(r,b,25),q(r,b,268),q(r,a,268)]
  m.face(pts[::-1] if reverse else pts)
 m.face([q(109,a,268),q(117,a,268),q(117,b,268),q(109,b,268)])
 m.face([q(109,b,25),q(117,b,25),q(117,a,25),q(109,a,25)])
for z in (55,116,177,238):
 m.box((-119,0,z),(12,84,44),bevel=4,axis=0)
 for y in (-33,33):m.cylinder((-127,y,z),2.7,3,'M_Chrome',6,0)
for a in (90,135,180,225,270):
 t=math.radians(a);x,y=123*math.cos(t),123*math.sin(t)
 m.cylinder((x,y,150),6,230,'M_RustyIron',12)
for side in (-1,1):
 m.pipe([(-30,side*126,47),(-55,side*135,60),(-85,side*130,120),(-90,side*115,220)],4,'M_Chrome',12)
models.append(m.save())
m=Model('SM_CapsuleUmbilical')
for i in range(7):
 x=-40-i*12;y=-34+i*10
 m.pipe([(x,y,290),(x-7,y+12,336),(x-50,y+28,380),(x-65,y+30,448),(x-95,y+35,463)],4+i%3,'M_Rubber',10)
 m.cylinder((x,y,286),8,10,'M_RustyIron',12)
for i in range(3):
 m.pipe([(-85,-62+i*14,40),(-147,-80+i*14,57),(-186,-100+i*16,124),(-192,-100+i*16,350),(-215,-100+i*16,449)],7,'M_RustyIron',12)
models.append(m.save())

# Original mono samples; mechanical door movement and closure impact.
for name,duration in [('S_BlastDoorMotor',1.65),('S_BlastDoorThud',.8)]:
 rng=random.Random(142);sr=22050;frames=bytearray();smooth=0
 for i in range(int(sr*duration)):
  t=i/sr;n=rng.uniform(-1,1);smooth=.94*smooth+.06*n
  if 'Motor' in name:
   env=min(1,t*10)*min(1,(duration-t)*7)
   signal=env*(.14*math.sin(math.tau*48*t)+.07*math.sin(math.tau*71*t)+.12*smooth)+.10*n*math.exp(-t*5)
  else:signal=(.36*math.sin(math.tau*(55-20*t)*t)+.23*smooth+.13*n)*math.exp(-t*8)
  frames.extend(struct.pack('<h',int(max(-.85,min(.85,signal))*32767)))
 with wave.open(os.path.join(ROOT,name+'.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(frames)
with open(os.path.join(ROOT,'mesh_manifest.json'),'w') as f:json.dump(models,f,indent=2)
print(json.dumps(models))
