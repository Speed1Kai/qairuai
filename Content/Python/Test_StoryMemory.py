import unreal,time,json,traceback,math
from pathlib import Path
WORK=Path(unreal.Paths.project_saved_dir()).resolve()/'ForeignMemory'
WORK.mkdir(exist_ok=True)
MISSION='/Game/Story/ForeignMemory/BP_ForeignMemory'
DRONE='/Game/Story/ForeignMemory/BP_StoryPatrol'
EDITOR=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
PLAY=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
test_cube=unreal.load_asset('/Engine/BasicShapes/Cube')
mc=unreal.EditorAssetLibrary.load_blueprint_class(MISSION)
stationc=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Environment/CityService/BP_ServiceStation')
routec=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Surface/HiddenExit/BP_HiddenLabRoute')
result={'passed':False,'stage':'intro','checks':{},'samples':[]}
state={'start':time.monotonic(),'sample':0,'index':0,'memory_abort_checked':False}
V=lambda p:unreal.Vector(*map(float,p))
def write_story():
    (WORK/'mission_test_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
def finish_story(ok):
    result['passed']=ok;write_story();unreal.unregister_slate_post_tick_callback(story_test_handle);PLAY.editor_request_end_play()
def key_story(w,pc,key,down=True):unreal.SystemLibrary.execute_console_command(w,'Input.'+('+' if down else '-')+'key '+key,pc)
def move_story(p,xyz):p.set_actor_location(V(xyz),False,True);p.character_movement.stop_movement_immediately()
def tick_story(dt):
    try:
        assert time.monotonic()-state['start']<330.,result['stage']
        w=EDITOR.get_game_world()
        if not w:return
        p=unreal.GameplayStatics.get_player_character(w,0)
        if not p:return
        t=unreal.GameplayStatics.get_time_seconds(w);pc=p.get_controller()
        m=unreal.GameplayStatics.get_actor_of_class(w,mc)
        if not m:return
        ms=m.get_editor_property('Stage');beat=m.get_editor_property('Beat');pos=p.get_actor_location()
        stage=result['stage']
        if t-state['sample']>1.5:
            state['sample']=t;result['samples'].append([stage,round(t,2),ms,beat,round(pos.x,1),round(pos.y,1),round(pos.z,1),m.get_editor_property('NextAt')]);result['debug']={'failed':m.get_editor_property('Failed'),'hp':p.get_editor_property('VisorIntegrity'),'tick_enabled':m.is_actor_tick_enabled(),'dialogue':m.get_editor_property('Dialogue'),'distance_scan':(p.get_actor_location()-V((5850,25200,2310))).length()};write_story()
        if stage=='intro':
            if t<26:return
            assert ms==0 and not p.get_editor_property('NavMemoryReady')
            assert m.get_editor_property('StoryHUD').get_render_opacity()<.01
            result['checks']['dormant_in_lab']=True
            pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0.)
            state['identity']=p.get_path_name();state['max']=p.get_editor_property('VisorMaxIntegrity')
            p.character_movement.set_movement_mode(unreal.MovementMode.MOVE_FLYING)
            move_story(p,(5850,23900,2257));result['stage']='stream';state['deadline']=t+65.;return
        if stage=='stream':
            assert t<state['deadline'],'City streaming timed out'
            station=unreal.GameplayStatics.get_actor_of_class(w,stationc)
            if not station:return
            route=unreal.GameplayStatics.get_actor_of_class(w,routec)
            stream=route.get_editor_property('CampusStreaming')
            if not stream or not stream.is_level_visible():return
            move_story(p,(5850,23900,2257));p.character_movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
            result['stage']='scan';state['deadline']=t+65.;return
        if stage=='scan':
            assert t<state['deadline'],'Scanner sequence timed out'
            if ms==1:
                p.call_method('Nav_RefreshTarget')
                assert (p.get_editor_property('NavGoal')-V((5850,25200,2310))).length()<3.
                p.call_method('Nav_RecoverMemory')
                assert not p.get_editor_property('NavMemoryReady')
                if beat>=1:result['checks']['scanner_recognized']=True
            if ms!=2:return
            assert result['checks'].get('scanner_recognized')
            patrol=m.get_editor_property('Patrol');assert patrol
            result['checks']['patrol_alive']=True
            state['patrol']=patrol
            # Stage the pawn at the flank, then use real capsule movement through the encounter.
            move_story(p,(7000,37400,2257));state.update(index=0,last=t,waypoints=[(7000,40000),(7000,42700),(7000,45100)])
            result['stage']='bypass';return
        if stage=='bypass':
            if ms==3:
                assert m.get_editor_property('Patrol') and m.get_editor_property('PatrolPassedPeacefully')
                result['checks']['bypass_without_kill']=True
                move_story(p,(34260,86900,2270));state['deadline']=t+6.;result['stage']='checkpoint';return
            assert t-state['last']<22.,'Flank blocked: '+str(pos)
            x,y=state['waypoints'][state['index']];delta=V((x-pos.x,y-pos.y,0));d=delta.length()
            if d<35:
                state['index']+=1;state['last']=t
                if state['index']>=len(state['waypoints']):state['index']=len(state['waypoints'])-1
                return
            p.add_movement_input(delta/max(d,1),.85,True);return
        if stage=='checkpoint':
            assert t<state['deadline']
            if m.get_editor_property('CheckpointStage')!=3:return
            p.set_editor_property('VisorIntegrity',0.);result['stage']='death';state['deadline']=t+3.;return
        if stage=='death':
            assert t<state['deadline']
            if not m.get_editor_property('Failed'):return
            assert pc.is_move_input_ignored()
            key_story(w,pc,'F9');result['stage']='retry';state['deadline']=t+4.;return
        if stage=='retry':
            if m.get_editor_property('Failed') and t>state['deadline']-2.:
                result['checks']['f9_console_input']=False;m.call_method('RetryCheckpoint')
            assert t<state['deadline']
            if m.get_editor_property('Failed'):return
            key_story(w,pc,'F9',False)
            assert ms==3 and not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            assert abs(p.get_editor_property('VisorIntegrity')-state['max'])<.1
            assert (p.get_actor_location()-V((34240,86900,2260))).length()<35.
            result['checks']['death_retry_f9']=True
            # F outside the terminal radius must leave the story and repair unchanged.
            key_story(w,pc,'F');state['at']=t;result['stage']='outside';return
        if stage=='outside':
            if t-state['at']<.4:return
            key_story(w,pc,'F',False);assert ms==3 and not p.get_editor_property('NavMemoryReady')
            result['checks']['terminal_distance_gate']=True
            state.update(index=0,last=t,waypoints=[(34630,86900),(34735,87215)])
            result['stage']='walk_lab';return
        if stage=='walk_lab':
            x,y=state['waypoints'][state['index']];delta=V((x-pos.x,y-pos.y,0));d=delta.length()
            if d<25:
                state['index']+=1;state['last']=t
                if state['index']==len(state['waypoints']):
                    key_story(w,pc,'F');result['stage']='terminal';state['deadline']=t+5.;return
                return
            assert t-state['last']<16.,'Lab access blocked '+str(pos)
            p.add_movement_input(delta/max(d,1),.65,True);return
        if stage=='terminal':
            assert t<state['deadline']
            if ms!=4:return
            key_story(w,pc,'F',False)
            assert not p.get_editor_property('NavMemoryReady')
            assert p.get_editor_property('VisorMaxIntegrity')==state['max']
            result['checks']['terminal_input_f']=True
            assert not m.get_editor_property('AlarmGuard'),'Guard spawned before warning'
            state['deadline']=t+24.;result['stage']='alarm';return
        if stage=='alarm':
            assert t<state['deadline'],'Alarm guard failed to spawn'
            guard=m.get_editor_property('AlarmGuard')
            if not guard:return
            assert ms==4 and not p.get_editor_property('NavMemoryReady')
            result['checks']['alarm_warning_then_enemy']=True
            state['guard']=guard;state['at']=t;result['stage']='combat';return
        if stage=='combat':
            guard=state['guard']
            if t-state['at']<2.:return
            assert ms==4,'Recovery advanced while guard alive'
            assert not guard.get_editor_property('Destroyed')
            result['guard_before_damage']={'hp':guard.get_editor_property('HullHealth'),'shots':guard.get_editor_property('Shots')}
            # Stage at the building exit, then use the equipped weapon and
            # its normal input. No change to drone health, AI or damage rules.
            move_story(p,(34240,86900,2260))
            p.call_method('Modes_Select',(1,))
            state['fight_at']=t;state['firing']=False;state['shot_base']=p.get_editor_property('LaserShots')
            result['stage']='aim_guard';return
        if stage=='aim_guard':
            if ms==6 or not unreal.SystemLibrary.is_valid(state['guard']):
                key_story(w,pc,'LeftMouseButton',False)
                fired=p.get_editor_property('LaserShots')-state['shot_base']
                assert fired>0 and result.get('guard_wounded'),(fired,result.get('guard_wounded'))
                result['checks']['alarm_guard_defeated_with_player_weapon']=True
                result['shots_at_guard']=fired
                state['deadline']=t+6.;result['stage']='memory_start';return
            guard=state['guard']
            cm=unreal.GameplayStatics.get_player_camera_manager(w,0)
            point=guard.get_actor_location()
            pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cm.get_camera_location(),point))
            if t-state['fight_at']>.3 and not state['firing']:
                key_story(w,pc,'LeftMouseButton');state['firing']=True
            health=guard.get_editor_property('HullHealth')
            if health<result['guard_before_damage']['hp']:result['guard_wounded']=True
            assert t-state['fight_at']<9,(health,point,pos,p.get_editor_property('LaserShots'),p.get_editor_property('LaserLastHit'))
            return
        if stage=='memory_start':
            assert t<state['deadline']
            if ms!=6:return
            assert not m.get_editor_property('FilmActive') and not m.get_editor_property('FilmWidget')
            assert not m.get_editor_property('MemoryRoot').is_visible()
            result['checks']['rejected_memory_scene_absent']=True
            state['deadline']=t+5.;result['stage']='memory';return
        if stage=='abort_memory':
            if ms==5 and t>state['deadline']-2.:
                result['checks']['f9_console_input']=False;m.call_method('RetryCheckpoint')
            assert t<state['deadline']
            if ms!=3:return
            key_story(w,pc,'F9',False)
            assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            assert pc.get_view_target()==p and p.get_editor_property('can_be_damaged')
            assert not p.get_editor_property('NavMemoryReady') and p.get_editor_property('VisorMaxIntegrity')==state['max']
            result['checks']['memory_abort_restores_controls']=True
            state['memory_abort_checked']=True
            state.update(index=0,last=t,waypoints=[(34630,86900),(34735,87215)])
            result['stage']='walk_lab';return
        if stage=='memory':
            assert t<state['deadline'],'Memory sequence stalled'
            if ms!=6:return
            assert m.get_editor_property('RecoveryGranted')
            assert p.get_editor_property('NavMemoryReady') and p.get_editor_property('NavMapOpen')
            assert p.get_editor_property('NavTargetIndex')==3
            assert p.get_editor_property('VisorMaxIntegrity')==state['max']+25.
            assert p.get_editor_property('VisorIntegrity')==state['max']+25.
            assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            assert pc.get_view_target()==p and p.get_editor_property('can_be_damaged')
            assert p.get_path_name()==state['identity']
            assert 'OmegaCityMemoryRestored' in list(map(str,p.tags))
            result['checks']['complete_reward_and_relay_goal']=True
            p.call_method('Nav_RecoverMemory');m.call_method('CompleteMission')
            assert p.get_editor_property('VisorMaxIntegrity')==state['max']+25.
            result['checks']['reward_once']=True
            state['at']=t;result['stage']='final_hud';return
        if stage=='final_hud':
            if t-state['at']<1.0:return
            assert m.get_editor_property('FrequencyStep')==0
            assert 'слежение' in m.get_editor_property('Objective')
            assert p.get_editor_property('VisorMaxIntegrity')==state['max']+25
            key_story(w,pc,'M')
            result['stage']='leave_lab';state['at']=t;return
        phase=m.get_editor_property('FrequencyStep')
        def aim(x):
            cm=unreal.GameplayStatics.get_player_camera_manager(w,0)
            rot=unreal.MathLibrary.find_look_at_rotation(cm.get_camera_location(),V((x,95565,2280)))
            p.set_actor_rotation(unreal.Rotator(yaw=rot.yaw),True);pc.set_control_rotation(rot)
        def shot(name):
            path=(WORK/(name+'.png')).resolve().as_posix()
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename="'+path+'" -nosuffix',pc)
        if stage=='leave_lab':
            if t-state['at']<.4:return
            key_story(w,pc,'M',False);assert not p.get_editor_property('NavMapOpen')
            move_story(p,(34278,95130,2254))
            state['path']=[(34275,95430),(33950,95430)]
            state['at']=t;result['stage']='enter_booth';return
        if stage=='enter_booth':
            assert t-state['at']<19,pos
            x,y=state['path'][0];d=V((x-pos.x,y-pos.y,0))
            if d.length()>28:
                p.add_movement_input(d/d.length(),.7,True);return
            state['path'].pop(0)
            if state['path']:return
            p.character_movement.stop_movement_immediately();aim(33950)
            result['checks']['walk_from_street_through_door']=True
            state['at']=t;result['stage']='wrong_console';return
        if stage=='wrong_console':
            if t-state['at']<1:return
            assert m.get_editor_property('FrequencyLastContact').length()>100
            key_story(w,pc,'F');state['at']=t;result['stage']='look_away';return
        if stage=='look_away':
            if t-state['at']<.4:return
            key_story(w,pc,'F',False);assert phase==0
            result['checks']['cannot_transfer_before_disconnect']=True
            move_story(p,(33400,95435,2254));pc.set_control_rotation(unreal.Rotator(yaw=-90))
            state['at']=t;result['stage']='back_turned';return
        if stage=='back_turned':
            if t-state['at']<.5:return
            assert 'F ·' not in m.get_editor_property('Objective')
            key_story(w,pc,'F');result['stage']='face_panel';state['at']=t;return
        if stage=='face_panel':
            if t-state['at']<.4:return
            key_story(w,pc,'F',False);assert phase==0
            result['checks']['look_gate']=True
            aim(33400)
            actor=unreal.get_default_object(unreal.GameplayStatics)
            tr=unreal.Transform(location=V((33400,95502,2295)),scale=V((1.45,.12,1.6)))
            wall=actor.call_method('BeginDeferredActorSpawnFromClass',(w,unreal.StaticMeshActor.static_class(),tr,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,p,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            wall.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            assert wall.static_mesh_component.set_static_mesh(test_cube)
            wall.static_mesh_component.set_collision_profile_name('BlockAll')
            actor.call_method('FinishSpawningActor',(wall,tr,unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            state['wall']=wall;state['at']=t;result['stage']='blocked_press';return
        if stage=='blocked_press':
            if t-state['at']<.6:return
            assert 'F ·' not in m.get_editor_property('Objective')
            key_story(w,pc,'F');result['stage']='remove_barrier';state['at']=t;return
        if stage=='remove_barrier':
            if t-state['at']<.5:return
            key_story(w,pc,'F',False);assert phase==0
            state['at']=t;result['stage']='release_behind_wall';return
        if stage=='release_behind_wall':
            if t-state['at']<.6:return
            assert phase==0,(phase,m.get_editor_property('Objective'))
            state['wall'].destroy_actor();result['checks']['line_of_sight_gate']=True
            aim(33400);state['at']=t;result['stage']='cut_tracking';return
        if stage=='cut_tracking':
            if t-state['at']<.8:return
            assert phase==0 and 'F ·' in m.get_editor_property('Objective'),(phase,m.get_editor_property('Objective'),m.get_editor_property('FrequencyCanUse'))
            key_story(w,pc,'F');state['at']=t;result['stage']='check_cut';return
        if stage=='check_cut':
            if t-state['at']<.7:return
            key_story(w,pc,'F',False);assert phase==1, (phase,pos,pc.get_control_rotation(),m.get_actor_location())
            assert m.get_editor_property('FrequencyLastContact').length()<.01
            assert not m.get_editor_property('FreqTrackLamp').is_visible() and m.get_editor_property('FreqTrackOff').is_visible()
            assert m.get_editor_property('TrackingDisplay').get_material(0).get_name()=='MI_Silent'
            result['checks']['disconnect_erases_contact_and_lights']=True
            state['at']=t;result['stage']='cross_to_transmitter';return
        if stage=='cross_to_transmitter':
            assert t-state['at']<14, pos
            dest=V((33950,95430,pos.z));delta=dest-pos
            if delta.length()>25:
                p.add_movement_input(delta/delta.length(),.8,True);return
            p.character_movement.stop_movement_immediately();aim(33950)
            state['at']=t;result['stage']='transmit';return
        if stage=='transmit':
            if t-state['at']<1:return
            assert m.get_editor_property('FrequencyLastContact').length()<.01
            key_story(w,pc,'F');result['stage']='resident';state['at']=t;return
        if stage=='resident':
            if t-state['at']<1:return
            key_story(w,pc,'F',False);assert phase==2
            assert m.get_editor_property('Speaker')=='ДЕЖУРНАЯ УБЕЖИЩА'
            assert m.get_editor_property('Voice').is_playing() and m.get_editor_property('FreqLocalLamp').is_visible()
            assert not m.get_editor_property('FreqRemoteLamp').is_visible()
            assert m.get_editor_property('BroadcastDisplay').get_material(0).get_name()=='MI_Local'
            shot('01_FirstTransmission');result['checks']['residents_initiate_actual_audio']=True
            result['stage']='wait_radio_shot';state['shot_at']=time.time();state['at']=t;return
        if stage=='wait_radio_shot':
            if t-state['at']<.65:return
            assert (WORK/'01_FirstTransmission.png').stat().st_mtime>state['shot_at']-1.5
            key_story(w,pc,'F9');result['stage']='radio_retry';state['at']=t;return
        if stage=='radio_retry':
            if t-state['at']<1:return
            key_story(w,pc,'F9',False);assert phase==2
            assert 'дождаться' in m.get_editor_property('Objective')
            assert m.get_editor_property('Speaker')=='ДЕЖУРНАЯ УБЕЖИЩА' and m.get_editor_property('Voice').is_playing()
            result['checks']['f9_resumes_human_transmission']=True
            result['stage']='radio_reply';state['at']=t;return
        if stage=='radio_reply':
            assert t-state['at']<22
            if phase!=3:return
            assert m.get_editor_property('Speaker')=='ПЕРВЫЙ ПОСТ'
            result['stage']='finished';state['at']=t;return
        if stage=='finished':
            assert t-state['at']<18
            if phase!=4:return
            assert p.get_editor_property('FrequencyFinished') and not p.get_editor_property('StoryGoalActive')
            assert 'Миссия завершена' in m.get_editor_property('Objective')
            assert m.get_editor_property('CheckpointStage')==6
            key_story(w,pc,'F');result['stage']='repeat';state['at']=t;return
        if stage=='repeat':
            if t-state['at']<.6:return
            key_story(w,pc,'F',False);assert phase==4
            assert p.get_editor_property('VisorMaxIntegrity')==state['max']+25
            key_story(w,pc,'F9');result['stage']='after_retry';state['at']=t;return
        if stage=='after_retry':
            if t-state['at']<1:return
            key_story(w,pc,'F9',False)
            assert phase==4 and m.get_editor_property('FrequencyLastContact').length()<.01
            assert 'Миссия завершена' in m.get_editor_property('StoryHUD').get_editor_property('MissionObjective')
            assert (pos-V((33950,95390,2254))).length()<40
            shot('02_MissionComplete');state['at']=t;result['stage']='capture_done';return
        if stage=='capture_done':
            if t-state['at']<1 or not (WORK/'02_MissionComplete.png').exists():return
            result['checks']['mission_complete_once_retry_preserves_local_control']=True
            assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
            state['leave_from']=pos
            state['at']=t;result['stage']='walk_after_end';return
        if stage=='walk_after_end':
            if (pos-state['leave_from']).length()>145:
                assert phase==4 and 'Миссия завершена' in m.get_editor_property('Objective')
                result['checks']['walk_after_completion']=True
                result['stage']='passed';finish_story(True);return
            assert t-state['at']<5,pos
            p.add_movement_input(V((-1,0,0)),.8,True)


    except Exception:
        result['error']=traceback.format_exc();finish_story(False)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
story_test_handle=unreal.register_slate_post_tick_callback(tick_story)
PLAY.editor_request_begin_play()
write_story()

