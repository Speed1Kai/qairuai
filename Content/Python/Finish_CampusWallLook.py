import runpy,os
folder=os.path.dirname(__file__)
runpy.run_path(os.path.join(folder,'Materialize_CampusWall.py'))
runpy.run_path(os.path.join(folder,'Present_CampusWallAsset.py'))
