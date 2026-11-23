"""Independent disk-load verification; never compiles or saves project assets."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import A,B,G,components
bp=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
names=set(map(str,B.list_graph_names(bp)));required={'AirJet_Stop','AirJet_Start','AirJet_Update','AirJet_Pressed','AirJet_Released','AirJet_Landed'}
assert required<=names
cdo=unreal.get_default_object(B.generated_class(bp));checks={}
checks['capacity_four_seconds']=cdo.get_editor_property('AirJetCapacity')==4
checks['starts_full']=cdo.get_editor_property('AirJetRemaining')==4
checks['starts_inactive']=not cdo.get_editor_property('bAirJetActive')
ev=G.get_graph_editor_by_name(bp,'EventGraph');nn={n.get_name():n for n in ev.list_all_nodes()}
for tag in ('AirJetRuntimeTick','AirJetJumpPressed','AirJetJumpReleased','AirJetJumpCanceled','AirJetLandingRecharge'):
    checks[tag]=tag in nn and bool(nn[tag].find_execute_pin().list_connected_pins())
cc={n:c for h,c,n in components(bp) if c}
for side in ('Left','Right'):
    checks['steam_'+side]=isinstance(cc['AirJet'+side],unreal.ParticleSystemComponent) and not cc['AirJet'+side].get_editor_property('auto_activate')
    checks['plume_'+side]=not cc['AirJetPlume'+side].is_visible() and cc['AirJetPlume'+side].get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION
checks['sound_loops']=A.load_asset('/Game/Characters/AirJet/AirJet_PressureLoop').get_editor_property('looping')
checks['capsule_unchanged']=cc['CapsuleComponent'].get_unscaled_capsule_half_height()==105
checks['no_graph_errors']=all(not G.get_graph_editor_by_name(bp,n).list_nodes_with_errors() for n in names)
previews={}
for p in A.list_assets('/Game/Characters/AirJet',recursive=False,include_folder=False):
    if '/BP_AirJetPreview_' in p:previews[p]=list(map(str,A.find_package_referencers_for_asset(p,load_assets_to_confirm=True)))
result={'passed':all(checks.values()),'checks':checks,'preview_references':previews}
json.dump(result,open(os.path.join(unreal.Paths.project_saved_dir(),'airjet_saved_verified.json'),'w'),indent=2)
assert result['passed'],result
unreal.log('AIRJET SAVED VERIFICATION PASSED')

