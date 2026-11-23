import os
for script in ('Separate_OmegaNotices.py','Test_CampusReady.py'):
 path=os.path.join(os.path.dirname(__file__),script);exec(compile(open(path,encoding='utf-8-sig').read(),path,'exec'))
