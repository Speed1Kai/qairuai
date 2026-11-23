import unreal,os,json
w=unreal.EditorLevelLibrary.get_game_world();p=unreal.GameplayStatics.get_player_character(w,0);R={}
for name in ('FirstPersonCamera','AtomicFPArms','AtomicFPGun','AtomicFPRig','AtomicFPMuzzle','Mesh'):
 c=p.get_editor_property(name);R[name]={'world':str(c.get_world_transform()),'visible':c.is_visible()}
 if isinstance(c,unreal.SkeletalMeshComponent):
  R[name]['bones']={b:str(c.get_socket_transform(b,unreal.RelativeTransformSpace.RTS_COMPONENT)) for b in ('CC_Base_R_Hand','CC_Base_L_Hand','CC_Base_R_Upperarm','CC_Base_L_Upperarm')}
  R[name]['animation']=str(c.get_editor_property('animation_data'))
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'atomic_live_probe.json'),'w'),indent=2)
