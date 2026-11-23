"""Remove the broken bridge from the connected campus and seal the main checkpoint."""
import unreal, os, sys, json, shutil, datetime, traceback
sys.path.insert(0, os.path.dirname(__file__))
from Industrial_Common import A, B, add, components, compile_bp, save
ROOT='/Game/Surface/ReferencePlan'; LEVEL='/Game/Surface/Lvl_CampusConnected'
O=(10006.289955343997,6612.598659341473,2150.)
project=os.path.abspath(unreal.Paths.project_dir())
report={'saved':False,'removed_instances':{}}
def V(p): return unreal.Vector(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def L(p): return V(tuple(p[i]-O[i] for i in range(3)))
def backup(path,ext='.uasset'):
    src=os.path.join(project,'Content',path.removeprefix('/Game/')+ext)
    if os.path.isfile(src):
        dst=os.path.join(back,path.removeprefix('/Game/')+ext)
        os.makedirs(os.path.dirname(dst),exist_ok=True); shutil.copy2(src,dst)
try:
    assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before authoring'
    back=os.path.join(project,'Saved/Backups/SteelCheckpoint',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(back,exist_ok=True);report['backup']=back
    backup(LEVEL,'.umap');backup(ROOT+'/BP_ReferenceCampus');backup(ROOT+'/BP_ReferenceSteelGate');backup('/Game/Surface/BP_SurfaceArrival')
    bp=A.load_asset(ROOT+'/BP_ReferenceCampus');assert bp
    # Clear only bridge batches. Remove the channel bottom/bank walls, keeping
    # all laboratory buildings, city batches and the real elevator aperture.
    for h,c,name in components(bp):
        if not isinstance(c,unreal.InstancedStaticMeshComponent): continue
        c.modify(); removed=0
        if name in ('SM_BridgeCampusHalf','SM_BridgeCityHalf','FallenSpan'):
            removed=c.get_instance_count();c.clear_instances()
        elif name in ('Box_dark_Collision','Box_concrete_Collision'):
            for i in range(c.get_instance_count()-1,-1,-1):
                p=c.get_instance_transform(i,False).translation
                wx,wy,wz=p.x+O[0],p.y+O[1],p.z+O[2]
                if abs(wx-5850)<2 and ((abs(wy-20050)<2 and abs(wz+125)<2) or (min(abs(wy-18625),abs(wy-21475))<2 and abs(wz-1040)<2)):
                    c.remove_instance(i);removed+=1
        if removed: report['removed_instances'][name]=removed
    cube=A.load_asset('/Engine/BasicShapes/Cube')
    floor=A.load_asset('/Game/LabTutorial/FirstFloor/M_LabFloor')
    asphalt=A.load_asset('/Game/Surface/Materials/M_Asphalt')
    for name,mat,p,size,collision in [
        ('RestoredCheckpointGround',floor,(5850,19700,2115),(4600,4400,70),True),
        ('RestoredCheckpointRoad',asphalt,(5850,19700,2153),(1400,4400,6),False)]:
        c=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,name,'PlanRoot');c.modify();c.clear_instances();c.set_static_mesh(cube);c.set_material(0,mat);c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        c.add_instance(unreal.Transform(location=L(p),scale=V(tuple(x/100 for x in size))),False)
    compile_bp(bp);save(bp)
    path=ROOT+'/BP_ReferenceSteelGate'
    if A.does_asset_exist(path):gate=A.load_asset(path)
    else:
        f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.Actor)
        gate=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ReferenceSteelGate',ROOT,unreal.Blueprint,f)
    root=add(gate,unreal.SceneComponent,'GateRoot');root.set_mobility(unreal.ComponentMobility.MOVABLE)
    mats={'Steel':'/Game/LabTutorial/Industrial/M_DistressedMetal','Frame':'/Game/LabTutorial/FirstFloor/M_LabGraphite','Hazard':'/Game/LabTutorial/FirstFloor/M_LabAmber','Red':'/Game/LabTutorial/FirstFloor/M_LabRed'}
    batches={}
    for n,path in mats.items():
        mat=A.load_asset(path) if A.does_asset_exist(path) else None
        mat=mat or A.load_asset('/Game/LabTutorial/FirstFloor/M_LabSteel')
        c=add(gate,unreal.HierarchicalInstancedStaticMeshComponent,n,'GateRoot');c.modify();c.clear_instances();c.set_static_mesh(cube);c.set_material(0,mat);c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_collision_profile_name('BlockAll' if n in ('Steel','Frame') else 'NoCollision');batches[n]=c
    def box(p,size,mat='Frame',pitch=0):
        batches[mat].add_instance(unreal.Transform(location=V(p),rotation=unreal.Rotator(pitch=pitch),scale=V(tuple(x/100 for x in size))),False)
    # World X spans the opening, Y is the travel direction. 15.2m width
    # overlaps the concrete fence at both ends; 6.3m height seals the throat.
    for side in (-1,1):
        x=side*379
        box((x,0,310),(754,100,620),'Steel')
        for z in (35,180,435,585):box((x,-66,z),(730,32,28))
        for z in (285,515):
            box((x,-55,z),(655,20,150))
            box((x,-69,z),(600,12,116),'Steel')
        for xx in (side*35,side*730):
            box((xx,-64,310),(25,28,590))
            for zz in range(50,600,80):box((xx,-84,zz),(14,12,14),'Steel')
        box((x,-85,108),(726,12,100))
        for xx in range(60,720,100):box((side*xx,-94,108),(47,8,90),'Hazard',pitch=-28)
        box((side*799,0,325),(100,190,650))
        box((side*799,-112,325),(44,48,520),'Steel')
    box((0,0,665),(1720,200,110));box((0,-75,310),(22,50,620))
    box((0,-117,663),(210,28,43),'Red')
    compile_bp(gate)
    cdo=unreal.get_default_object(B.generated_class(gate));t=cdo.get_editor_property('primary_actor_tick');t.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',t);save(gate)
    # Remove stale bridge objectives. The gate intentionally has no interaction.
    arrival=A.load_asset('/Game/Surface/BP_SurfaceArrival')
    G=unreal.BlueprintGraphEditor
    for gn in B.list_graph_names(arrival):
        for n in G.get_graph_editor_by_name(arrival,gn).list_all_nodes():
            for p in n.list_all_pins():
                text=p.get_pin_value()
                if 'Мост в город разрушен' in text:
                    p.set_pin_value('Выйдите из корпуса А. Следуйте по внутренней дороге к главному КПП. Стальные ворота заблокированы — найдите способ преодолеть периметр.')
    compile_bp(arrival);save(arrival)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
    removed=[]
    for a in list(sub.get_all_level_actors()):
        label=a.get_actor_label();cls=a.get_class().get_name()
        obsolete=cls in ('BP_ReferenceBridgeSafety_C','BP_BridgeRecovery_C','BP_ReferenceSteelGate_C') or label.startswith('BRIDGE_')
        if isinstance(a,unreal.TextRenderActor):
            text=str(a.text_render.text)
            obsolete=obsolete or any(k in text for k in ('РАЗРУШЕННЫЙ МОСТ','ДЛЯ ПЕРЕЛЁТА'))
        if obsolete:removed.append(label);sub.destroy_actor(a)
        elif cls=='BP_ReferenceCampus_C':
            # Reinstance the edited BP so serialized HISM overrides cannot
            # retain the obsolete bridge in this map.
            p=a.get_actor_location();rot=a.get_actor_rotation();sub.destroy_actor(a)
            fresh=sub.spawn_actor_from_class(B.generated_class(bp),p,rot);fresh.set_actor_label(label);fresh.set_folder_path('SURFACE/ReferencePlan')
    a=sub.spawn_actor_from_class(B.generated_class(gate),L((5850,17424,2150)));a.set_actor_label('REF_ClosedSteelCheckpoint');a.set_folder_path('SURFACE/ReferencePlan')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.modify()
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,LEVEL),'Campus map save failed'
    report.update(saved=True,gate_world=[5850,17424,2150],gate_locked=True,removed_actors=removed)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(L((5850,15200,2600)),unreal.Rotator(pitch=-3,yaw=90))
except Exception:
    report['error']=traceback.format_exc();unreal.log_error(report['error'])
finally:
    json.dump(report,open(os.path.join(project,'Saved/steel_checkpoint_replace.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not report['saved']:raise RuntimeError('Checkpoint replacement incomplete')
