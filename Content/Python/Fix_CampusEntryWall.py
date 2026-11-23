"""Preserve the existing lift-to-first-floor entrance in the exterior shell."""
import unreal,os,sys,shutil,datetime,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,components,add,V,compile_bp,save
root=os.path.abspath(unreal.Paths.project_dir());backup=os.path.join(root,'Saved/Backups/EntryWall',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(backup,exist_ok=True)
for f in ('Surface/BP_SurfaceDeparture.uasset','Lvl_LabTutorial.umap'):
 source=os.path.join(root,'Content',f);dest=os.path.join(backup,os.path.basename(f));shutil.copy2(source,dest)
bp=A.load_asset('/Game/Surface/BP_SurfaceDeparture');cs={n:c for h,c,n in components(bp)}
wall=cs['ExteriorWestWall'];wall.modify();wall.set_editor_property('relative_location',V((-3110,-1730,320)));wall.set_editor_property('relative_scale3d',V((.35,8.6,8)))
for name,pos,size in [('ExteriorWestNorth',(-3110,-160,320),(.35,14,8)),('ExteriorWestLintel',(-3110,-1080,525),(.35,4.4,3.9))]:
 c=add(bp,unreal.StaticMeshComponent,name,'Root');c.modify();c.set_static_mesh(wall.get_editor_property('static_mesh'));c.set_material(0,wall.get_material(0));c.set_editor_property('relative_location',V(pos));c.set_editor_property('relative_scale3d',V(size));c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('BlockAll')
compile_bp(bp);save(bp)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 if a.get_class().get_name()=='BP_SurfaceDeparture_C':
  a.modify()
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   if c.get_name()=='ExteriorWestWall':c.modify();c.set_relative_location(V((-3110,-1730,320)),False,False);c.set_relative_scale3d(V((.35,8.6,8)))
world.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Lvl_LabTutorial')
json.dump({'saved':True,'backup':backup,'entry_opening_y':[-220,220],'entry_floor':2150,'entry_clear_height':440},open(os.path.join(root,'Saved/entry_wall_fix.json'),'w'),indent=2)
