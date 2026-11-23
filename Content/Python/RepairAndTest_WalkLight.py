import os
for script in ('Fix_WalkAndExitLight.py','Test_WalkAndExitLight.py'):
 path=os.path.join(os.path.dirname(__file__),script);exec(compile(open(path,encoding='utf-8-sig').read(),path,'exec'))
