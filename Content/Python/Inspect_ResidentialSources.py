"""Read FBX metadata and texture dimensions without changing the supplied files."""
import struct,zlib,json,os,glob
def read_fbx(path):
 data=open(path,'rb').read();version=struct.unpack_from('<I',data,23)[0];wide=version>=7500;header=25 if wide else 13
 def prop(pos):
  kind=chr(data[pos]);pos+=1
  types={'Y':'h','C':'?','I':'i','F':'f','D':'d','L':'q'}
  if kind in types:
   fmt='<'+types[kind];return struct.unpack_from(fmt,data,pos)[0],pos+struct.calcsize(fmt)
  if kind in ('S','R'):
   length=struct.unpack_from('<I',data,pos)[0];pos+=4;v=data[pos:pos+length];return (v.decode('utf8','replace') if kind=='S' else '<raw:%d>'%length),pos+length
  if kind in 'fdlibc':
   length,encoding,nbytes=struct.unpack_from('<III',data,pos);pos+=12;raw=data[pos:pos+nbytes]
   if encoding:raw=zlib.decompress(raw)
   fmt={'f':'f','d':'d','l':'q','i':'i','b':'B','c':'B'}[kind];return list(struct.unpack('<'+str(length)+fmt,raw)),pos+nbytes
  raise ValueError('FBX property '+kind)
 def node(pos):
  if wide:end,count,size,nlen=struct.unpack_from('<QQQB',data,pos)
  else:end,count,size,nlen=struct.unpack_from('<IIIB',data,pos)
  if not end:return None,pos+header
  pos+=header;name=data[pos:pos+nlen].decode();pos+=nlen;values=[]
  for _ in range(count):v,pos=prop(pos);values.append(v)
  children=[]
  while pos<end-header:
   child,pos=node(pos)
   if child:children.append(child)
   else:break
  return {'name':name,'values':values,'children':children},end
 nodes=[];pos=27
 while pos<len(data)-header:
  n,pos=node(pos)
  if not n:break
  nodes.append(n)
 return version,nodes
def child(n,name):return next((x for x in n['children'] if x['name']==name),None)
report=[]
for path in sorted(glob.glob('S:/fbx/*.fbx')):
 version,nodes=read_fbx(path);objects=next(n for n in nodes if n['name']=='Objects');settings=next(n for n in nodes if n['name']=='GlobalSettings')
 r={'file':path,'version':version,'settings':child(settings,'Properties70'),'geometry':[],'materials':[],'textures':[],'models':[]}
 for obj in objects['children']:
  kind=obj['name']
  if kind=='Geometry':
   verts=child(obj,'Vertices')['values'][0];inds=child(obj,'PolygonVertexIndex')['values'][0];bounds=[[min(verts[j::3]),max(verts[j::3])] for j in range(3)]
   r['geometry'].append({'name':obj['values'],'vertices':len(verts)//3,'polygons':sum(i<0 for i in inds),'bounds':bounds,'uv_layers':len([c for c in obj['children'] if c['name']=='LayerElementUV'])})
  elif kind=='Material':r['materials'].append({'name':obj['values'],'properties':child(obj,'Properties70')})
  elif kind=='Texture':r['textures'].append({'name':obj['values'],'files':[(c['name'],c['values']) for c in obj['children'] if c['name'] in ['FileName','RelativeFilename','TextureName']]})
  elif kind=='Model':r['models'].append({'name':obj['values'],'properties':child(obj,'Properties70')})
 r['connections']=next(n for n in nodes if n['name']=='Connections')['children'];report.append(r)
out='S:/Final_Protocol/Saved/residential_source_inventory.json'
with open(out,'w',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
for r in report:print(os.path.basename(r['file']),r['geometry'],[m['name'][1] for m in r['materials']],r['textures'])
