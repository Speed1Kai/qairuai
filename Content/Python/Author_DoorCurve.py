"""Editor-only reflected property authoring for native Timeline float tracks.

The native generic Blueprint property setters import correctly typed struct
defaults. No binary asset patching or runtime Python is used.
"""
from Industrial_Common import *

def build_float_track(template):
 # Expose native structs only to the transient authoring graph in this process.
 # Their metadata is not saved; gameplay assets do not depend on the helper.
 for path in ('/Script/Engine.RichCurve','/Script/Engine.TTFloatTrack','/Script/Engine.TTTrackId'):
  s=unreal.load_object(None,path);A.set_metadata_tag(s,'BlueprintType','true')
  kind=B.get_struct_type(s)
  if kind==B.get_basic_type_by_name('int'):raise RuntimeError('Native struct type unavailable: '+path)
 helper=bp_asset('BP_DoorCurveAuthoring')
 e=G.get_graph_editor_by_name(helper,'EventGraph')
 if 'CurvePayload' not in map(str,B.list_member_variable_names(helper)):
  rich=unreal.load_object(None,'/Script/Engine.RichCurve')
  track=unreal.load_object(None,'/Script/Engine.TTFloatTrack')
  e.add_member_variable('CurvePayload',B.get_struct_type(rich),'(Keys=((InterpMode=RCIM_Cubic,TangentMode=RCTM_User,Time=0.0,Value=0.0,ArriveTangent=0.0,LeaveTangent=0.0),(InterpMode=RCIM_Cubic,TangentMode=RCTM_User,Time=1.8,Value=1.0,ArriveTangent=0.0,LeaveTangent=0.0)))')
  e.add_member_variable('TrackPayload',B.get_array_type(B.get_struct_type(track)),'()')
  for name in ('CurveObject','TimelineObject'):e.add_member_variable(name,B.get_object_reference_type(unreal.Object.static_class()),'None')
 compile_bp(helper)
 # Curve is an independently saved asset, and the Timeline owns a reference.
 path=ROOT+'/C_BlastDoorMotion'
 curve=A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset('C_BlastDoorMotion',ROOT,unreal.CurveFloat,unreal.CurveFloatFactory())
 # Exact property name convention used by UTimelineTemplate::SetTrackName.
 prop='TL_DoorMovement_Alpha'
 default='((TrackName="Alpha",PropertyName="'+prop+'",bIsExternalCurve=True,CurveFloat=CurveFloat\''+curve.get_path_name()+'\'))'
 # Update the typed array default through its variable declaration.
 e.remove_member_variable('TrackPayload')
 e.add_member_variable('TrackPayload',B.get_array_type(B.get_struct_type(unreal.load_object(None,'/Script/Engine.TTFloatTrack'))),default)
 if 'DisplayPayload' not in map(str,B.list_member_variable_names(helper)):
  e.add_member_variable('DisplayPayload',B.get_array_type(B.get_struct_type(unreal.load_object(None,'/Script/Engine.TTTrackId'))),'((TrackType=1,TrackIndex=0))')
 g=Graph(helper);g.e.remove_nodes([n for n in g.e.list_all_nodes() if n.get_class().get_name()!='K2Node_Event'])
 event=g.e.add_custom_event_node('ApplyCurveAndTrack');g.cursor=pin(event,'then',True)
 g.do(g.call('Engine.KismetSystemLibrary.SetStructurePropertyByName',Object=g.get('CurveObject'),PropertyName='FloatCurve',Value=g.get('CurvePayload')))
 g.do(g.call('Engine.KismetArrayLibrary.SetArrayPropertyByName',Object=g.get('TimelineObject'),PropertyName='FloatTracks',Value=g.get('TrackPayload')))
 g.do(g.call('Engine.KismetArrayLibrary.SetArrayPropertyByName',Object=g.get('TimelineObject'),PropertyName='TrackDisplayOrder',Value=g.get('DisplayPayload')))
 compile_bp(helper)
 cdo=unreal.get_default_object(B.generated_class(helper));cdo.set_editor_property('CurveObject',curve);cdo.set_editor_property('TimelineObject',template)
 cdo.call_method('ApplyCurveAndTrack',())
 save(curve)
 # No helper Blueprint is saved or referenced by the gameplay door.
 if abs(curve.get_float_value(0.9)-.5)>.001:raise RuntimeError('Timeline curve was not authored')
 return curve
