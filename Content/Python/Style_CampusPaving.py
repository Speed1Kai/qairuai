"""Dedicated world-scale exterior paving; preserve all collision and lift holes."""
import unreal,os,sys,json,datetime,shutil,traceback
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,M,add,components,compile_bp,save
P=os.path.abspath(unreal.Paths.project_dir());ROOT='/Game/Surface/Materials/CampusPaving';LEVEL='/Game/Surface/Lvl_CampusConnected'
r={'saved':False,'assignments':[]}
back=os.path.join(P,'Saved/Backups/CampusPaving',datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));os.makedirs(back,exist_ok=True)
def backup(path,ext='.uasset'):
    src=os.path.join(P,'Content',path.removeprefix('/Game/')+ext)
    if os.path.isfile(src):
        dest=os.path.join(back,path.removeprefix('/Game/')+ext);os.makedirs(os.path.dirname(dest),exist_ok=True);shutil.copy2(src,dest)
NOISE='''struct Grain {float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}};Grain g;
float grain=g.n(P.xy*.35);float dust=g.n(P.xy*.003);float fleck=g.n(P.xy*.11);
'''
def mat(name,slab):
    path=ROOT+'/'+name;backup(path)
    m=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    M.delete_all_material_expressions(m)
    def node(cls,**kw):
        n=M.create_material_expression(m,cls)
        for k,v in kw.items():n.set_editor_property(k,v)
        return n
    pos=node(unreal.MaterialExpressionWorldPosition)
    code=NOISE
    if slab:
        code+='''float scale=SLAB;float2 cell=floor(P.xy/scale);float2 q=frac(P.xy/scale)*scale;
float d=min(min(q.x,scale-q.x),min(q.y,scale-q.y));float aa=max(.12,max(fwidth(P.x),fwidth(P.y)));
float seam=1-smoothstep(.45,.95+aa,d);float edge=1-smoothstep(1.0,3.8+aa,d);
float panel=g.h(cell);float stain=smoothstep(.52,.82,dust)*.12;
float3 col=float3(.19,.185,.17)*(.83+.22*panel+.11*fleck+.07*grain-stain);
col=lerp(col,float3(.04,.043,.041),edge*.25);col=lerp(col,float3(.022,.025,.024),seam*.85);
return float4(col,grain*.035+fleck*.06-seam*.18-edge*.03);'''.replace('SLAB',str(slab)+'.0')
    else:
        code+='''float aggregate=smoothstep(.53,.83,fleck);float3 col=lerp(float3(.025,.028,.029),float3(.053,.055,.052),dust);
col+=aggregate*.012+(grain-.5)*.012;return float4(col,grain*.025+fleck*.035);'''
    q=node(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    inp=unreal.CustomInput();inp.set_editor_property('input_name','P');q.set_editor_property('inputs',[inp]);q.set_editor_property('code',code);M.connect_material_expressions(pos,'',q,'P')
    rgb=node(unreal.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);height=node(unreal.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    M.connect_material_expressions(q,'',rgb,'');M.connect_material_expressions(q,'',height,'');M.connect_material_property(rgb,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(unreal.MaterialProperty.MP_METALLIC,0.),(unreal.MaterialProperty.MP_ROUGHNESS,.93),(unreal.MaterialProperty.MP_SPECULAR,.23)]:
        M.connect_material_property(node(unreal.MaterialExpressionConstant,r=value),'',prop)
    bump=node(unreal.MaterialExpressionCustom,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs=[]
    for name in ('P','N','H'):
        i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    bump.set_editor_property('inputs',inputs);bump.set_editor_property('code','float3 n=normalize(N);float3 a=cross(ddy(P),n),b=cross(n,ddx(P));float det=dot(ddx(P),a);return normalize(abs(det)*n-sign(det)*(ddx(H)*a+ddy(H)*b));')
    for n,k in [(pos,'P'),(node(unreal.MaterialExpressionVertexNormalWS),'N'),(height,'H')]:M.connect_material_expressions(n,'',bump,k)
    m.set_editor_property('tangent_space_normal',False);M.connect_material_property(bump,'',unreal.MaterialProperty.MP_NORMAL)
    M.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);M.recompile_material(m);save(m);return m
try:
    assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE'
    backup(LEVEL,'.umap');backup('/Game/Surface/ReferencePlan/BP_ReferenceCampus')
    paving=mat('M_CampusConcreteSlabs',200);walk=mat('M_CampusWalkwaySlabs',80);road=mat('M_CampusAsphalt',0)
    bp=A.load_asset('/Game/Surface/ReferencePlan/BP_ReferenceCampus');assert bp
    for h,c,name in components(bp):
        if not isinstance(c,unreal.InstancedStaticMeshComponent):continue
        target=paving if name in ('Box_floor_Collision','RestoredCheckpointGround') else road if name in ('Box_asphalt_Detail','RestoredCheckpointRoad') else None
        if target:c.modify();c.set_material(0,target);r['assignments'].append(name)
    # Sidewalks and court panels share a batch with other concrete decoration.
    # Split only low paving instances, never buildings or raised planters.
    old=next(c for h,c,name in components(bp) if name=='Box_concrete_Detail')
    dest=add(bp,unreal.HierarchicalInstancedStaticMeshComponent,'ExteriorWalkwayPaving','PlanRoot');dest.modify();dest.clear_instances();dest.set_static_mesh(old.static_mesh);dest.set_material(0,walk);dest.set_mobility(unreal.ComponentMobility.MOVABLE);dest.set_collision_profile_name('NoCollision')
    count=0;old.modify()
    for i in range(old.get_instance_count()-1,-1,-1):
        t=old.get_instance_transform(i,False)
        if -20<=t.translation.z<=20:
            dest.add_instance(t,False);old.remove_instance(i);count+=1
    r['walkway_instances']=count;compile_bp(bp);save(bp)
    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
    for a in list(sub.get_all_level_actors()):
        if a.get_class().get_name()=='BP_ReferenceCampus_C':
            p=a.get_actor_location();rot=a.get_actor_rotation();label=a.get_actor_label();sub.destroy_actor(a)
            a=sub.spawn_actor_from_class(B.generated_class(bp),p,rot);a.set_actor_label(label);a.set_folder_path('SURFACE/ReferencePlan')
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();w.modify();assert unreal.EditorLoadingAndSavingUtils.save_map(w,LEVEL)
    o=(10006.289955343997,6612.598659341473,2150.)
    def L(p):return unreal.Vector(x=p[0]-o[0],y=p[1]-o[1],z=p[2]-o[2])
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(L((5850,3300,2500)),unreal.Rotator(pitch=-25,yaw=90))
    r.update(saved=True,backup=back,texture_allocations=0,collision_changed=False)
except Exception:r['error']=traceback.format_exc();unreal.log_error(r['error'])
finally:json.dump(r,open(os.path.join(P,'Saved/campus_paving.json'),'w'),indent=2)
