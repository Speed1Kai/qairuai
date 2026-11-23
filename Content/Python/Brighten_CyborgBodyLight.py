"""Only tune the player's light asset; do not rebuild or replace the map."""
import unreal,os,sys,json,shutil,datetime,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,components,compile_bp
root='/Game/LabTutorial/Basement/'
saved=os.path.abspath(unreal.Paths.project_saved_dir());content=os.path.abspath(unreal.Paths.project_content_dir())
backup=os.path.join(saved,'Backups','BodyLightBrightness',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
stage=os.path.join(saved,'BodyLightBrightnessStaged');os.makedirs(stage,exist_ok=True)
r={'saved':False,'installed':False,'files':[],'backup':backup}
try:
 bp=A.load_asset(root+'BP_CyborgBodyLight')
 light=next(c for h,c,n in components(bp) if n=='BodyFill')
 light.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
 light.set_intensity(12000.);light.set_attenuation_radius(1600.)
 light.set_light_color(unreal.LinearColor(r=.65,g=.88,b=1,a=1));light.set_cast_shadows(False)
 compile_bp(bp)
 targets=[bp]
 for name,color in [('M_CyborgBodyLight',(.1,12.,16.)),('M_CyborgGlowShell',(.16,4.4,6.2))]:
  mat=A.load_asset(root+name)
  expressions=[o for o in unreal.ObjectIterator(unreal.MaterialExpressionConstant3Vector) if o.get_outer()==mat]
  if len(expressions)!=1:raise RuntimeError('Expected one emission color: '+name)
  expressions[0].set_editor_property('constant',unreal.LinearColor(r=color[0],g=color[1],b=color[2],a=1))
  M.recompile_material(mat);targets.append(mat)
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 for asset in targets:
  name=asset.get_name();src=os.path.join(content,'LabTutorial','Basement',name+'.uasset');dst=os.path.join(stage,name+'.uasset')
  shutil.copy2(src,os.path.join(backup,name+'.uasset'))
  unreal.SystemLibrary.execute_console_command(world,'OBJ SAVEPACKAGE PACKAGE="'+root+name+'" FILE="'+dst.replace('\\','/')+'" SILENT=true')
  if not os.path.isfile(dst):raise RuntimeError('Staged save failed: '+name)
  r['files'].append({'source':dst,'destination':src})
 r.update(saved=True,intensity_lumens=12000,radius_cm=1600,shadows=False,body_glow_multiplier=2.,key='K')
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:
 with open(os.path.join(saved,'body_light_brightness_report.json'),'w',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
if not r['saved']:raise RuntimeError('Body light brightness tuning failed; see report')
