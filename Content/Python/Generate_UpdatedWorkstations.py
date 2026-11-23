"""Detailed lightweight widescreen workstations, in centimetres."""
import ast,os,math,json
scripts=os.path.dirname(__file__)
ROOT=os.path.abspath(os.path.join(scripts,'..','..','SourceAssets','LabWorkstations'))
os.makedirs(ROOT,exist_ok=True)
for file,kind,name in [('Generate_IndustrialMeshes.py',ast.ClassDef,'Model'),('Generate_SplitDoorMeshes.py',ast.FunctionDef,'save_uv_model')]:
 tree=ast.parse(open(os.path.join(scripts,file),encoding='utf8').read())
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,kind) and n.name==name],type_ignores=[]),file,'exec'))
Model.save=save_uv_model
specs=[]
def monitor(m,x,y,desk,width=76):
 dark='M_LabGraphite';steel='M_LabSteel';rubber='M_LabRubber'
 height=width*.56;z=desk+18+height/2
 m.box((x,y,desk+1.5),(width*.4,23,3),steel,3)
 m.box((x,y+4,desk+13),(5,6,24),steel,1)
 m.cylinder((x,y,z-5),5,6,steel,12,1)
 m.box((x,y,z),(width,5,height),dark,3,1)
 m.box((x,y-2.7,z),(width-2.4,.8,height-2.4),rubber,2,1)
 m.box((x,y-3.2,z+.2),(width-4,.3,height-5),'M_WorkstationDisplay',1,1)
 m.box((x+width/2-5,y-3.5,z-height/2+1.5),(1.7,.5,.6),'M_LabCyan')
 for vx in range(-24,25,4):m.box((x+vx,y+2.8,z+height/2-5),(1.3,.6,4),rubber)
 for vx in (-width/2+4,width/2-4):
  for vz in (-height/2+4,height/2-4):m.cylinder((x+vx,y+3.2,z+vz),.65,1,steel,8,1)
 m.pipe([(x,y+6,z-8),(x+8,y+9,desk+10),(x+12,y+10,desk),(x+20,y+16,desk-25)],.65,rubber,6)
 # Raised diagnostics, grouped into a readable graph and a right status column.
 sx=x-width*.38;sy=y-3.45
 m.box((x-width*.2,sy,z+height*.31),(width*.36,.25,.7),'M_LabCyan')
 for i in range(14):
  h=2+abs(math.sin(i*.7))*7
  m.box((sx+i*width*.032,sy,z-height*.23+h/2),(width*.019,.25,h),'M_LabCyan')
 for i in range(5):m.box((x+width*.22,sy,z+height*.2-i*height*.105),(width*(.16 if i%2 else .23),.25,.7),'M_LabCyan')
def keyboard(m,x,y,z):
 m.box((x,y,z+2),(61,20,3),'M_LabGraphite',2)
 for r in range(4):
  for c in range(13):m.box((x-27+c*4.4,y-7+r*4.3,z+4),(3.5,3.2,.8),'M_LabSteel',.4)
 m.box((x+40,y+1,z+2),(8,12,4),'M_LabRubber',2)
for name,industrial in [('SM_ModernConsole',False),('SM_IndustrialWorkbench',True)]:
 m=Model(name)
 if not industrial:
  m.box((0,0,80),(180,76,8),'M_LabCeramic',5)
  for x in (-74,74):m.box((x,14,39),(20,46,78),'M_LabGraphite',3)
  m.box((0,28,44),(140,6,55),'M_LabSteel',2)
  for x in (-43,43):monitor(m,x,18,84,79);keyboard(m,x,-16,84)
 else:
  m.box((0,0,101),(310,115,12),'M_DistressedMetal',6)
  for x in (-135,135):
   m.box((x,30,48),(28,74,96),'M_DistressedMetal',4)
   m.box((x,-44,48),(18,16,96),'M_DistressedMetal',2)
   m.box((x,0,7),(45,110,12),'M_RustyIron',3)
  m.box((0,43,50),(270,13,70),'M_DistressedMetal',2)
  for x in (-65,65):monitor(m,x,20,107,108);keyboard(m,x,-27,107)
  m.pipe([(-100,55,108),(-120,61,87),(-141,55,32),(-158,50,4)],1.8,'M_Rubber',8)
 specs.append(m.save())
with open(os.path.join(ROOT,'workstations.json'),'w') as f:json.dump(specs,f,indent=2)
