import unreal, os, traceback
root=unreal.Paths.project_content_dir()
scope={}
report=os.path.join(unreal.Paths.project_saved_dir(),'capsule_motion_build.txt')
try:
    script=os.path.join(root,'Python','Capsule_WakeMotion.py')
    exec(compile(open(script,encoding='utf8').read(),script,'exec'),scope)
    asset=scope['build_motion']()
    with open(report,'w') as f:f.write('SAVED: '+asset.get_path_name())
except Exception:
    with open(report,'w') as f:f.write(traceback.format_exc())
    raise
