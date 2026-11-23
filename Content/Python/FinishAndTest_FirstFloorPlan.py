import os
for file in ('Finish_FirstFloorAisles.py','Test_AlignedFirstFloor.py'):
    src=os.path.join(os.path.dirname(__file__),file)
    exec(compile(open(src,encoding='utf-8').read(),src,'exec'))
