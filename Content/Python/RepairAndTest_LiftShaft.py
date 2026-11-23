import os
for name in ('Cut_CampusLiftShaft.py','Test_FullLiftRide.py'):
 path=os.path.join(os.path.dirname(__file__),name)
 exec(compile(open(path,encoding='utf8').read(),path,'exec'))
