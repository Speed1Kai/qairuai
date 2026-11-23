"""Align the five-zone first-floor circulation with the supplied floor plan.
Preserves the basement, player, real lift and connected courtyard doorway.
"""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,add,components,compile_bp,save
P=os.path.abspath(unreal.Paths.project_dir());ROOT='/Game/LabTutorial/FirstFloor';MAIN='/Game/Lvl_LabTutorial';Z=2150
r={'saved':False,'installed':False,'files':[],'reference':'Gemini_Generated_Image_qbcg9aqbcg9aqbcg.jpg'}
back=os.path.join(P,'Saved/Backups/FirstFloorPlan',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(back,exist_ok=True)
stage=os.path.join(P,'Saved/FirstFloorPlanStaged');os.makedirs(stage,exist_ok=True)
def stage_package(path,ext):
    dest=os.path.join(stage,path.removeprefix('/Game/')+ext);os.makedirs(os.path.dirname(dest),exist_ok=True)
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(w,'OBJ SAVEPACKAGE PACKAGE="'+path+'" FILE="'+dest.replace('\\','/')+'" SILENT=true')
    assert os.path.isfile(dest),'Staging failed '+path
    r['files'].append({'source':dest,'destination':os.path.join(P,'Content',path.removeprefix('/Game/')+ext)})
def save(asset):stage_package(asset.get_path_name().split('.')[0],'.uasset')
def V(p):return unreal.Vector(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def backup(path,ext='.uasset'):
    src=os.path.join(P,'Content',path.removeprefix('/Game/')+ext)
    if os.path.isfile(src):
        dst=os.path.join(back,path.removeprefix('/Game/')+ext);os.makedirs(os.path.dirname(dst),exist_ok=True);shutil.copy2(src,dst)
try:
    assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE'
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()=='Lvl_LabTutorial'
    backup(MAIN,'.umap');backup(ROOT+'/BP_ModernFirstFloor');backup(ROOT+'/BP_FloorPlanCorrections')
    floor=A.load_asset(ROOT+'/BP_ModernFirstFloor');removed={}
    # Replace only the partitions around the former dead-end shower room.
    for h,c,name in components(floor):
        if not isinstance(c,unreal.InstancedStaticMeshComponent) or name not in ('Boxes_M_LabCeramic','Boxes_M_LabGraphite','Boxes_M_LabTeal','Boxes_M_LabSteel'):continue
        c.modify();n=0
        for i in range(c.get_instance_count()-1,-1,-1):
            t=c.get_instance_transform(i,False);p=t.translation
            vertical=((abs(p.x-3600)<12 and 300<p.y<=900) or (abs(p.x-3900)<12 and 300<p.y<=1250))
            cross=abs(p.y-300)<12 and 3600<p.x<3900
            if 2151<p.z<2590 and (vertical or cross):c.remove_instance(i);n+=1
        if n:removed[name]=n
    compile_bp(floor);save(floor);r['removed_partition_instances']=removed
    path=ROOT+'/BP_FloorPlanCorrections'
    if A.does_asset_exist(path):bp=A.load_asset(path)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_FloorPlanCorrections',ROOT,unreal.Blueprint,f)
    root=add(bp,unreal.SceneComponent,'PlanRoot');root.set_mobility(unreal.ComponentMobility.STATIC)
    batches={};mats={};cube=A.load_asset('/Engine/BasicShapes/Cube')
    for n in ('M_LabCeramic','M_LabGraphite','M_LabSteel','M_LabFloor','M_LabTeal','M_LabCyan'):
        mats[n]=A.load_asset(ROOT+'/'+n)
    def item(key,mesh,p,scale=(1,1,1),yaw=0,mat=None,collision=False):
        if key not in batches:
            c=add(bp,unreal.InstancedStaticMeshComponent,key,'PlanRoot');c.modify();c.clear_instances();c.set_static_mesh(mesh);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
            if mat:c.set_material(0,mats[mat])
            batches[key]=c
        batches[key].add_instance(unreal.Transform(location=V(p),rotation=unreal.Rotator(yaw=yaw),scale=V(scale)),False)
    def box(p,size,mat='M_LabCeramic',collision=True):item(mat+('_Solid' if collision else '_Trim'),cube,p,tuple(x/100 for x in size),mat=mat,collision=collision)
    def wall_x(x,a,b):
        if b<=a:return
        box((x,(a+b)/2,Z+220),(20,b-a,440))
        for side in (-1,1):
            for z,h,mat in ((12,24,'M_LabGraphite'),(122,16,'M_LabTeal'),(414,32,'M_LabSteel')):box((x+side*10.5,(a+b)/2,Z+z),(1.5,b-a,h),mat,False)
    def opening(x,a,b,center):
        wall_x(x,a,center-183);wall_x(x,center+183,b);box((x,center,Z+424),(20,366,32))
    opening(3600,300,900,600);opening(3900,300,1250,600)
    box((3750,900,Z+220),(300,20,440))
    # Continuous 3m-wide clean corridor, with walkable foundation under seams.
    box((3750,600,Z-15),(300,600,30),'M_LabGraphite')
    for x in range(3600,3900,100):
        for y in range(300,900,100):box((x+50,y+50,Z+.35),(98.8,98.8,.7),'M_LabFloor',False)
    box((3750,600,Z+450),(300,600,20),'M_LabGraphite')
    box((3750,600,Z+1.1),(4,550,1),'M_LabCyan',False)
    lightmesh=A.load_asset(ROOT+'/SM_CleanroomLight')
    item('CeilingLights',lightmesh,(3750,610,Z+427))
    compile_bp(bp);save(bp)
    # Reinstance the architectural actor to discard serialized stale partitions.
    for a in list(sub.get_all_level_actors()):
        cls=a.get_class().get_name();label=a.get_actor_label()
        if cls=='BP_ModernFirstFloor_C':
            p=a.get_actor_location();rot=a.get_actor_rotation();sub.destroy_actor(a)
            q=sub.spawn_actor_from_class(B.generated_class(floor),p,rot);q.set_actor_label(label);q.set_folder_path('LAB/Floor01/Architecture')
        elif label.startswith('PLAN01_'):sub.destroy_actor(a)
    a=sub.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)));a.set_actor_label('PLAN01_Layout');a.set_folder_path('LAB/Floor01/PlanAlignment')
    # Reuse tested automatic door actors rather than inventing a second input path.
    doorclass=B.generated_class(A.load_asset('/Game/LabTutorial/Doors/BP_HeavyBlastDoor'))
    for x in (3600,3900):
        a=sub.spawn_actor_from_class(doorclass,V((x,600,Z)));a.set_actor_label('PLAN01_DeconDoor_'+str(x));a.set_folder_path('LAB/Floor01/Doors')
    # Clear, short signs match the five zones on the drawing.
    signs=[('02 / ЧИСТЫЙ ШЛЮЗ',(3750,865,Z+330),-90),('03 / СЕРВЕРНАЯ',(3875,600,Z+407),180),('01 / САНОБРАБОТКА',(3575,600,Z+407),180)]
    for i,(text,p,yaw) in enumerate(signs):
        a=sub.spawn_actor_from_class(unreal.TextRenderActor,V(p),unreal.Rotator(yaw=yaw));a.set_actor_label('PLAN01_Sign_'+str(i));a.set_folder_path('LAB/Floor01/Wayfinding');c=a.text_render;c.set_text(unreal.Text(text));c.set_world_size(15);c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);c.set_text_render_color(unreal.Color(r=128,g=232,b=245,a=255));c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    for a in sub.get_all_level_actors():
        if isinstance(a,unreal.TextRenderActor) and a.get_actor_label() in ('F01_Sign_08','F01_Sign_09'):
            a.modify();a.text_render.set_text(unreal.Text('A-01 / ВЫХОД ВО ДВОР' if a.get_actor_label()=='F01_Sign_08' else ''))
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();w.modify();stage_package(MAIN,'.umap')
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(V((3710,370,Z+190)),unreal.Rotator(pitch=-5,yaw=55))
    r.update(saved=True,backup=back,new_corridor_bounds=[3600,3900,300,900],door_centres=[[3600,600,Z],[3900,600,Z]],original_lifts_preserved=True)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:json.dump(r,open(os.path.join(P,'Saved/first_floor_plan_alignment.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
