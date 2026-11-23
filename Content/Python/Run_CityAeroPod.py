import runpy,unreal,os
base=os.path.dirname(__file__)
runpy.run_path(base+'/Add_CityAeroPod.py',run_name='__main__')
runpy.run_path(base+'/Verify_CityAeroPod.py',run_name='__main__')
runpy.run_path(base+'/Review_CityAeroPod.py',run_name='__main__')
