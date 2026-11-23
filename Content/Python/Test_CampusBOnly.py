import os
src=os.path.join(os.path.dirname(__file__),'Test_AllCampusInteriors.py')
code=open(src,encoding='utf-8').read().replace('all_interiors_walk.json','all_interiors_B_walk.json')
code=code.replace('def V(p):','cases=[c for c in cases if c[\'id\']==\'B\']\ndef V(p):')
exec(compile(code,src,'exec'))
