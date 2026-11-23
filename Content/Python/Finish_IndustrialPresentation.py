"""Final surface and presentation pass; uses existing cinematic hint widget."""
import unreal,os,sys,json
sys.path.insert(0,os.path.dirname(__file__))
from Industrial_Common import *
from Industrial_Materials import build_materials
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
build_materials()
# Archive contents already open through the cinematic HUD. Suppress the old
# floating copies and the obsolete overhead WASD billboard in the room.
hidden=[]
for a in unreal.EditorLevelLibrary.get_all_level_actors():
 n=a.get_actor_label()
 if n.startswith('LAB_Record_') or n in ('LAB_Tutorial_Sign_ControlsAtStart','LAB_Tutorial_Sign_Door'):
  c=a.get_component_by_class(unreal.TextRenderComponent)
  if c:c.set_editor_property('visible',False);hidden.append(n)
 if n=='IND_FirstControls':unreal.EditorLevelLibrary.destroy_actor(a)
bp=bp_asset('BP_FirstControlsHint');compile_bp(bp);g=Graph(bp)
g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
g.event('ReceiveBeginPlay');g.do(g.call('Engine.KismetSystemLibrary.Delay',Duration=10.5))
pc=g.out(g.call('Engine.GameplayStatics.GetPlayerController',PlayerIndex=0))
wbp=A.load_asset('/Game/LabTutorial/UI/WBP_InteractionHint')
create=g.call('UMG.WidgetBlueprintLibrary.Create',WidgetType=B.generated_class(wbp).get_path_name(),OwningPlayer=pc);g.do(create);widget=g.out(create)
for prop,text in [('HUDTitle','ДВИГАТЕЛЬНАЯ СИСТЕМА'),('HUDMessage','WASD · движение    Space · прыжок\nShift · спринт    Ctrl / C · присесть')]:
 g.do(g.call('Engine.KismetSystemLibrary.SetStringPropertyByName',Object=widget,PropertyName=prop,Value=text))
g.do(g.call('UMG.UserWidget.AddToViewport',target=widget,ZOrder=40));compile_bp(bp);save(bp)
a=unreal.EditorLevelLibrary.spawn_actor_from_class(B.generated_class(bp),V((0,0,0)),unreal.Rotator());a.set_actor_label('IND_FirstControls');a.set_folder_path('LAB/00_Opening')
if not unreal.EditorLoadingAndSavingUtils.save_current_level():raise RuntimeError('Cannot save final presentation')
with open('S:/Final_Protocol/Saved/industrial_presentation.json','w',encoding='utf8') as f:json.dump({'saved':True,'hidden_legacy_billboards':hidden,'controls':'WBP_InteractionHint at 10.5s','normal_maps':'procedural derivative, no texture allocation'},f,ensure_ascii=False,indent=2)
