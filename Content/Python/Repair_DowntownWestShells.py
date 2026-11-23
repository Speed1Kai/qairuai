"""Finish the exposed party walls of the four free-standing Downtown West buildings."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import unreal
from Industrial_Common import A, add, components, compile_bp, save

ASSET = '/Game/Environment/CityRealism/BP_DowntownWestStreet'
OFFSET = unreal.Vector(10006.289955343997, 6612.598659341473, 2150)
BASE = 2192
# Surveyed wall lines in the streamed city, excluding awnings, chairs and signs.
BUILDINGS = {
    'Cafe': (1534, 4017, 24375, 26356, 3555),
    'Market': (7453, 10054, 24280, 26500, 4024),
    'Residence': (1735, 4241, 27866, 30272, 3402),
    'Bistro': (7702, 10277, 28280, 29805, 3422),
}
# Use the same meshes and painted materials as the existing street elevations.
MODULES = {
    'CafeWindow': ('West_030', 'SM_build_cafe_a_mod_windows_f'),
    'CafeUpper': ('West_023', 'SM_build_cafe_a_mod_lvl2_windows_b'),
    'CafeDoor': ('West_018', 'SM_build_cafe_a_mod_door_b'),
    'CafeBrick': ('West_029', 'SM_build_cafe_a_mod_wall_a'),
    'MarketWindow': ('West_061', 'SM_build_b_mod_lvl2_doublewindow'),
    'MarketUpper': ('West_063', 'SM_build_b_mod_lvl3_doublewindow'),
    'MarketBrick': ('West_054', 'SM_build_cafe_a_mod_wall_a'),
    'HomeWindow': ('West_104', 'SM_build_cafe_a_mod_windows_f'),
    'HomeUpper': ('West_093', 'SM_build_f_mod_lvl2_window_a'),
    'ShopWindow': ('West_117', 'SM_build_d_mod_wall_lvl2_window'),
    'ShopGlass': ('WestMirror_008', 'SM_build_d_mod_lvl1_window'),
    'ShopDoor': ('WestMirror_010', 'SM_build_d_mod_lvl1_window_door'),
    'ShopVent': ('WestMirror_015', 'SM_build_d_mod_lvl1_window_vent'),
    'ShopBand': ('WestMirror_016', 'SM_build_d_mod_trim_lvl2_a'),
    'Coping': ('West_103', 'SM_build_e_mod_trim_top_a'),
}
# Each screen faces the avenue and has two posts anchored in its own roof.
# label, building, screen pivot X/Y, horizontal offset of the post from centre, screen half-height
SIGNS = [
    ('CITY_LED_Arrival_01_Overwatch', 'Market', 7680, 25390, 440, 338),
    ('CITY_LED_Arrival_02_System', 'Cafe', 3770, 25390, 440, 338),
    ('CITY_LED_Arrival_03_Connecting', 'Bistro', 7890, 29055, 330, 254),
    ('CITY_LED_Arrival_04_Neural', 'Residence', 4050, 29130, 330, 254),
]
CITY = '/Game/Surface/Lvl_CampusConnected'
TINT = {
    'MarketGround': ('CafeWindow','MarketBrick'), 'MarketDoor': ('CafeDoor','MarketBrick'),
    'HomeDoor': ('CafeDoor','HomeWindow'), 'HomeBrick': ('CafeBrick','HomeWindow'),
}
CUBE = '/Engine/BasicShapes/Cube'
MATERIAL = '/Game/Surface/Materials/'
AXES = {'south': (0,-1,-90), 'north': (0,1,90), 'west': (-1,0,180), 'east': (1,0,0)}

def fit_collision(component):
    # West_057 contains only the four legacy building envelopes, including
    # space formerly occupied by awnings. Fit the ground floor and arcade.
    assert component.static_mesh.get_name()=='Cube' and component.hidden_in_game
    assert str(component.get_collision_profile_name())=='BlockAll' and component.get_instance_count() in (4,14)
    component.modify()
    component.clear_instances()
    def body(x0,x1,y0,y1,z0,z1):
        centre=unreal.Vector((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)-OFFSET
        component.add_instance(unreal.Transform(location=centre,
            scale=unreal.Vector((x1-x0)/100,(y1-y0)/100,(z1-z0)/100)),False)
    for name,(x0,x1,y0,y1,top) in BUILDINGS.items():
        floor=BASE-60
        if name=='Cafe':
            body(x0,x1-360,y0,y1,floor,top)
            body(x1-360,x1,y0+360,y1,floor,top)
            # Fill the clipped entrance with short strips behind the diagonal.
            for j in range(4):
                body(x1-360+j*90,x1-270+j*90,y0+(j+1)*90,y0+361,floor,top)
        elif name=='Market':
            body(x0,x1,y0,y1,2620,top)
            body(8085,x1,y0,y1,floor,2620)
            body(x0,8085,y0,24365,floor,2620)
            body(x0,8085,26415,y1,floor,2620)
            body(7840,8085,24365,25200,floor,2620)
            body(7840,8085,25585,26415,floor,2620)
        else:
            body(x0,x1,y0,y1,floor,top)
    assert component.get_instance_count()==14

def install(bp=None):
    bp = bp or A.load_asset(ASSET)
    project = Path(unreal.Paths.project_dir()).resolve()
    disk = project / ('Content/' + ASSET.removeprefix('/Game/') + '.uasset')
    backup = project/'Saved/Backups/WestShells'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup.mkdir(parents=True)
    shutil.copy2(disk, backup/disk.name)
    originals = {n:c for _,c,n in components(bp)}
    batches = {}
    counts = {}
    for key,(source,expected) in MODULES.items():
        assert originals[source].static_mesh.get_name() == expected, (source,expected)
    def batch(key):
        if key in batches:
            return batches[key]
        c = add(bp,unreal.InstancedStaticMeshComponent,'Shell_'+key,'Root')
        source_key = TINT.get(key,(key,None))[0]
        if source_key in MODULES:
            ref = originals[MODULES[source_key][0]]
            mesh,materials = ref.static_mesh, list(ref.get_materials())
            if key in TINT:
                materials[0]=originals[MODULES[TINT[key][1]][0]].get_material(0)
        else:
            mesh,materials = A.load_asset(CUBE), [A.load_asset(MATERIAL+key)]
        assert mesh and all(materials), key
        c.modify()
        c.clear_instances()
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_static_mesh(mesh)
        for i,mat in enumerate(materials):
            c.set_material(i,mat)
        c.set_collision_profile_name('NoCollision')
        c.set_editor_property('can_ever_affect_navigation',False)
        c.set_cull_distances(0,48000)
        batches[key]=c
        return c
    def instance(key,position,scale,yaw=0):
        batch(key).add_instance(unreal.Transform(location=unreal.Vector(*position)-OFFSET,
            rotation=unreal.Rotator(yaw=yaw),scale=unreal.Vector(*scale)),False)
        counts[key] = counts.get(key,0)+1
    def slab(key,x0,x1,y0,y1,z0,z1):
        dx,dy,dz=x1-x0,y1-y0,z1-z0
        assert min(dx,dy,dz)>0
        instance(key,((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),(dx/100,dy/100,dz/100))
    def row(building,side,bottom,top,modules):
        x0,x1,y0,y1,_=BUILDINGS[building]
        nx,ny,yaw=AXES[side]
        start,end=(y0,y1) if nx else (x0,x1)
        widths=[]
        for key in modules:
            box=batch(key).static_mesh.get_bounding_box()
            widths.append(box.max.y-box.min.y)
        units=(end-start)/sum(widths)
        cursor=start
        for i,key in enumerate(modules):
            box=batch(key).static_mesh.get_bounding_box()
            width=units*widths[i]
            sy=units
            sz=(top-bottom)/(box.max.z-box.min.z)
            mid=cursor+.5*width
            cursor+=width
            lateral=(box.min.y+box.max.y)*.5*sy
            x=(x1 if nx>0 else x0) if nx else mid
            y=(y1 if ny>0 else y0) if ny else mid
            instance(key,(x+ny*lateral,y-nx*lateral,bottom-sz*box.min.z),(1,sy,sz),yaw)
    # The pack had an adjacent taller party's cornice in this selection.
    # Remove just those six elevated pieces. Use mesh centres, independent of pivots.
    removed=0
    for n,c in originals.items():
        if not isinstance(c,unreal.InstancedStaticMeshComponent) or not c.static_mesh:continue
        if c.static_mesh.get_name() not in ('SM_build_b_mod_top_trim','SM_build_b_mod_top_trim_support_a'):continue
        box=c.static_mesh.get_bounding_box()
        for i in reversed(range(c.get_instance_count())):
            t=c.get_instance_transform(i,False)
            p=unreal.MathLibrary.transform_location(t,(box.min+box.max)*.5)+OFFSET
            if 7600<p.x<10030 and 29640<p.y<29900 and 3890<p.z<4100:
                c.modify()
                assert c.remove_instance(i)
                removed+=1
    assert removed==6 or (removed==0 and 'Shell_ShopBand' in originals), removed
    for name,(x0,x1,y0,y1,roof) in BUILDINGS.items():
        # Inside the glass there is a setback and a dark interior. The cafe's
        # bevel and the market's recessed arcade need deeper clearances.
        left=680 if name=='Market' else 145
        right=240 if name=='Cafe' else 160
        front=245 if name=='Cafe' else 130
        slab('M_Charcoal',x0+left,x1-right,y0+front,y1-140,BASE-23,roof-12)
        # The existing cafe roof follows the clipped entry. Keep the slab
        # behind that corner, including its plinth.
        cuts=[(x0,x1,y0,y1)] if name!='Cafe' else [(x0,x1-410,y0,y1),(x1-410,x1,y0+410,y1)]
        for ax,bx,ay,by in cuts:
            slab('M_RuinConcrete',ax,bx,ay,by,BASE-60,BASE+1)
            slab('M_RuinSteel',ax,bx,ay,by,roof-23,roof-4)
    for side in ('west','north'):
        row('Cafe',side,BASE,2792,['CafeBrick','CafeWindow','CafeDoor','CafeWindow','CafeBrick'])
        row('Cafe',side,2792,3392,['CafeUpper','CafeBrick','CafeUpper','CafeUpper','CafeBrick'])
        row('Cafe',side,3392,3551,['CafeBrick']*5)
    for side in ('south','north'):
        row('Market',side,BASE,2742,['MarketBrick','MarketGround','MarketDoor','MarketGround','MarketBrick'])
        row('Market',side,2742,3342,['MarketWindow']*5)
        row('Market',side,3342,3942,['MarketUpper']*5)
        row('Market',side,3942,4028,['MarketBrick']*5)
    # The market's original rear has a service door; fill missing courses from inside.
    x0,x1,y0,y1,_=BUILDINGS['Market']
    slab('M_Charcoal',x1-105,x1-90,y0+4,y1-4,BASE-15,4020)
    for side in ('south','north'):
        row('Bistro',side,BASE,2642,['ShopVent','ShopGlass','ShopGlass','ShopDoor','ShopGlass','ShopGlass','ShopVent'])
        row('Bistro',side,2642,2802,['ShopBand']*5)
        row('Bistro',side,2802,3332,['ShopWindow']*5)
        row('Bistro',side,3332,3430,['Coping']*5)
    row('Residence','south',BASE,2792,['HomeWindow','HomeDoor','HomeWindow','HomeBrick','HomeWindow'])
    row('Residence','south',2792,3360,['HomeUpper']*5)
    row('Residence','south',3360,3422,['Coping']*5)
    for _,name,x,y,spread,half_height in SIGNS:
        roof=BUILDINGS[name][4]
        back=-1 if name in ('Cafe','Residence') else 1
        post=x+back*19
        for leg in (y-spread,y+spread):
            slab('M_RuinConcrete',post-31,post+31,leg-38,leg+38,roof-6,roof+14)
            slab('M_RuinSteel',post-14,post+14,leg-14,leg+14,roof+13,roof+76+half_height*1.72)
        slab('M_RuinSteel',post-12,post+12,y-spread-10,y+spread+10,roof+88,roof+107)
    # A rerun may no longer use a previous batch after replacing a material.
    for n,c in originals.items():
        if n.startswith('Shell_') and n[6:] not in batches:
            c.modify()
            c.clear_instances()
    fit_collision(originals['West_057'])
    compile_bp(bp)
    save(bp)
    result={'backup':str(backup),'removed_stray_cornice_pieces':removed,'instances':counts}
    dest=project/'Saved/WestShells/20261118'
    dest.mkdir(parents=True,exist_ok=True)
    (dest/'Repair.json').write_text(json.dumps(result,indent=2))
    return result


def finish_placement():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0]==CITY
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_name={a.get_actor_label():a for a in actors.get_all_level_actors()}
    block=by_name['CITY_FirstDowntownBlock']
    project=Path(unreal.Paths.project_dir()).resolve()
    report=project/'Saved/WestShells/20261118/Repair.json'
    data=json.loads(report.read_text())
    disk=project/'Content/Surface/Lvl_CampusConnected.umap'
    map_backup=Path(data['backup'])/disk.name
    if map_backup.exists():
        map_backup=map_backup.parent.parent/datetime.now().strftime('%Y%m%d_%H%M%S_%f')/disk.name
        map_backup.parent.mkdir(parents=True)
    shutil.copy2(disk,map_backup)
    data['placement_backup']=str(map_backup)
    attached={}
    for label,name,x,y,spread,h in SIGNS:
        sign=by_name[label]
        target=unreal.Vector(x,y,BUILDINGS[name][4]+76+h)-OFFSET
        sign.modify()
        sign.set_actor_location(target,False,True)
        assert (sign.get_actor_location()-target).length()<.1
        attached[label]=list((target+OFFSET).to_tuple())
    # A placed HISM may retain its own serialized instance array after
    # compiling the Blueprint. Remove the same surveyed orphan pieces there.
    block.modify()
    templates={n:c for _,c,n in components(A.load_asset(ASSET)) if n.startswith('Shell_')}
    placed={c.get_name():c for c in block.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    fit_collision(placed['West_057'])
    for n,template in templates.items():
        c=placed[n]
        ts=[template.get_instance_transform(i,False) for i in range(template.get_instance_count())]
        c.modify()
        c.clear_instances()
        for t in ts:
            c.add_instance(t,False)
        assert c.get_instance_count()==len(ts)
    removed=0
    for c in block.get_components_by_class(unreal.InstancedStaticMeshComponent):
        if not c.static_mesh or c.static_mesh.get_name() not in ('SM_build_b_mod_top_trim','SM_build_b_mod_top_trim_support_a'):continue
        box=c.static_mesh.get_bounding_box()
        for i in reversed(range(c.get_instance_count())):
            t=c.get_instance_transform(i,True)
            p=unreal.MathLibrary.transform_location(t,(box.min+box.max)*.5)+OFFSET
            if 7600<p.x<10030 and 29640<p.y<29900 and 3890<p.z<4100:
                c.modify()
                assert c.remove_instance(i)
                removed+=1
    assert removed in (0,6)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,CITY)
    data.update(placed_stray_pieces_removed=removed,screen_pivots=attached)
    report.write_text(json.dumps(data,indent=2))

if __name__=='__main__':
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world(), 'End PIE before editing the city.'
    assert editor.get_editor_world().get_path_name().split('.')[0]==CITY, 'Open the connected city level first.'
    dirty={p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
    dirty.update(p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    assert not dirty.intersection({CITY,ASSET}), 'Save pending author edits before installing.'
    install()
    finish_placement()
