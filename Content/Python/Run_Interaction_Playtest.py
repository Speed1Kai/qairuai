"""Finite PIE test fixture. Teleports only the running pawn to eight fixed test
positions and observes existing actors. Never edits/compiles/saves any asset.
E is pressed separately through the real game viewport.
"""
import unreal, os, json, time
_playtest_positions={'hologram':(-170,-80,110),'recovery':(-500,200,110),'atlas':(420,430,110),'mobility':(650,-110,110),'archive':(1400,520,110),'stealth':(1760,0,110),'door':(1330,0,110),'far':(-700,-600,110)}
_playtest_stage=None
_playtest_data={}
_playtest_next=0
_playtest_deadline=time.monotonic()+600
_playtest_saved=unreal.Paths.project_saved_dir()
def _playtest_tick(delta):
    global _playtest_stage,_playtest_next
    now=time.monotonic()
    if now<_playtest_next:return
    _playtest_next=now+.25
    world=unreal.EditorLevelLibrary.get_game_world()
    if not world or now>_playtest_deadline:
        unreal.unregister_slate_post_tick_callback(_playtest_handle);return
    try:
        with open(os.path.join(_playtest_saved,'interaction_test_stage.txt'),encoding='utf8') as f:stage=f.read().strip()
    except OSError:return
    if stage=='STOP':
        unreal.unregister_slate_post_tick_callback(_playtest_handle);return
    if stage not in _playtest_positions:return
    pawn=unreal.GameplayStatics.get_player_character(world,0)
    pc=unreal.GameplayStatics.get_player_controller(world,0)
    if not pawn or not pc:return
    if stage!=_playtest_stage:
        _playtest_stage=stage
        p=_playtest_positions[stage]
        pawn.set_actor_location(unreal.Vector(x=p[0],y=p[1],z=p[2]),False,True)
        pc.set_control_rotation(unreal.Rotator(pitch=-8,yaw=0,roll=0))
        unreal.log('INTERACTION PLAYTEST STAGE '+stage)
        return
    actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
    near=[];door=None
    for a in actors:
        name=a.get_class().get_name()
        if name.startswith(('BP_Tutorial','BP_Lab')):
            if name=='BP_TutorialSlidingDoor_C':door=a.get_actor_location().z
            try:
                if a.get_editor_property('bPlayerNear'):near.append(name)
            except Exception:pass
    _playtest_data[stage]={'pawn_location':str(pawn.get_actor_location()),'near':near,'door_z':door}
    with open(os.path.join(_playtest_saved,'interaction_playtest_states.json'),'w',encoding='utf8') as f:json.dump(_playtest_data,f,ensure_ascii=False,indent=2)
_playtest_handle=unreal.register_slate_post_tick_callback(_playtest_tick)
unreal.log('Finite interaction PIE fixture ready; no assets will be changed')
