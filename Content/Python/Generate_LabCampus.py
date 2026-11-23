"""Original exterior laboratory architecture, centimetres, shared materials."""
import ast,os,math,json
scripts=os.path.dirname(__file__);ROOT=os.path.abspath(os.path.join(scripts,'..','Surface','CampusSource'));os.makedirs(ROOT,exist_ok=True)
for file,kind,name in [('Generate_IndustrialMeshes.py',ast.ClassDef,'Model'),('Generate_SplitDoorMeshes.py',ast.FunctionDef,'save_uv_model')]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name==name],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
wall='M_LabCeramic';dark='M_LabGraphite';steel='M_LabSteel';glass='M_DeadGlass';cyan='M_LabCyan';con='M_RuinConcrete';models=[]
for name,w,d,floors in [('SM_CampusResearchWing',3200,2400,4),('SM_CampusHeadquarters',4400,3200,6)]:
 m=Model(name);height=floors*400
 m.box((0,0,-20),(w+110,d+110,40),con,15)
 # An open ground-floor central portal belongs to the player's actual exit.
 for sy in (-1,1):
  for z in range(0,height,400):
   for x in range(-int(w/2)+200,int(w/2),400):
    if sy==-1 and z==0 and abs(x)<400:continue
    m.box((x,sy*d/2,z+65),(395,45,130),wall,5)
    if (x//400+z//400)%11!=0:m.box((x,sy*(d/2-10),z+250),(342,15,230),glass,3)
    m.box((x-190,sy*(d/2+15),z+220),(22,65,360),wall,3)
    m.box((x,sy*(d/2+31),z+373),(390,12,23),dark)
  m.box((0,sy*(d/2+10),height+23),(w+50,70,46),steel,6)
 for sx in (-1,1):
  for z in range(0,height,400):
   for y in range(-int(d/2)+200,int(d/2),400):
    m.box((sx*w/2,y,z+65),(45,395,130),wall,5)
    if (y//400+z//400)%9!=0:m.box((sx*(w/2-10),y,z+250),(15,340,230),glass,3)
    m.box((sx*(w/2+14),y-190,z+220),(65,22,360),wall,3)
 for sx in (-1,1):
  for sy in (-1,1):m.box((sx*w/2,sy*d/2,height/2),(95,95,height),wall,10)
 m.box((0,0,height+10),(w+60,d+60,40),dark,18)
 # Roof plant and original metal service assemblies define the lab silhouette.
 for x in (-w*.30,w*.30):
  m.box((x,d*.15,height+100),(460,600,190),steel,15)
  for y in range(-180,181,70):m.box((x-235,d*.15+y,height+90),(8,24,130),dark)
  for yy in (-160,160):m.cylinder((x,d*.15+yy,height+210),100,25,dark,16)
 for x in (-w*.43,w*.43):
  m.box((x,-d/2-10,height*.47),(45,55,height*.82),dark)
  m.box((x,-d/2-42,height*.47),(12,8,height*.72),cyan)
 # Covered entrance with two braces. The portal remains physically clear.
 m.box((0,-d/2-220,530),(1040,600,70),steel,20)
 m.box((0,-d/2-220,490),(950,500,7),cyan,8)
 for x in (-450,450):m.box((x,-d/2-420,240),(45,45,480),wall,6)
 if name=='SM_CampusHeadquarters':
  m.box((0,0,height+180),(1500,1200,320),wall,20)
  m.cylinder((0,0,height+420),470,170,steel,32)
  m.cylinder((0,0,height+590),28,250,steel,12)
  m.ring((0,0,height+450),580,548,35,cyan,40)
  for z in range(650,2300,400):
   m.box((0,-d/2-22,z),(1150,70,42),steel,8)
 else:
  m.box((0,d*.28,height+230),(760,600,400),dark,12)
 models.append(m.save())
with open(os.path.join(ROOT,'campus_meshes.json'),'w') as f:json.dump(models,f,indent=2)
print('Campus kit:',len(models),'models;',sum(m['vertices'] for m in models),'vertices')
