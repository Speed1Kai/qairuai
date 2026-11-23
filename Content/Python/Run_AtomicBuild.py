import os,runpy,json,unreal
runpy.run_path(os.path.join(os.path.dirname(__file__),'Build_AtomicPose.py'))
assert json.load(open(os.path.join(unreal.Paths.project_saved_dir(),'atomic_pose_build.json'))).get('saved')
runpy.run_path(os.path.join(os.path.dirname(__file__),'Build_AtomicWeapon.py'))
