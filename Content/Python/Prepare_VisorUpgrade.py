import os
for name in ('Inspect_VisorUpgrade.py','Capture_VisorHeroDiagram.py'):
 path=os.path.join(os.path.dirname(__file__),name)
 exec(compile(open(path,encoding='utf8').read(),path,'exec'),globals())
