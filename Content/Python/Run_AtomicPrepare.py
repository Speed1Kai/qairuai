import os,runpy
for name in ('Prepare_AtomicArms.py','Build_AtomicPose.py'):
 runpy.run_path(os.path.join(os.path.dirname(__file__),name))
