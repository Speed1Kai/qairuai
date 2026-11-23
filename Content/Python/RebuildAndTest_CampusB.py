import os
for name in ('Build_AllCampusInteriors.py','Test_CampusBOnly.py'):
    src=os.path.join(os.path.dirname(__file__),name)
    exec(compile(open(src,encoding='utf-8').read(),src,'exec'))
