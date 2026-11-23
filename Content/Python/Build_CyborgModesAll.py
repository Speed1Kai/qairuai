import runpy,os
for script in ('Build_CyborgModes.py','Build_CyborgModesHUD.py'):runpy.run_path(os.path.join(os.path.dirname(__file__),script))
