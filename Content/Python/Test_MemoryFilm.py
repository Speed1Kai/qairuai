"""PIE integration test: playback, Space, F9, decode failure and one-time reward."""
import unreal,time,json,traceback
from pathlib import Path
WORK=Path(unreal.Paths.project_dir())/'work/MemoryFilm'
WORK.mkdir(parents=True,exist_ok=True)
ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
play=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
mc=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Story/ForeignMemory/BP_ForeignMemory')
rc=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Surface/HiddenExit/BP_HiddenLabRoute')
result={'passed':False,'stage':'intro','checks':{},'samples':[]}
state={'start':time.monotonic(),'sample':0.,'at':0.}
def write_film_test():
    (WORK/'Test_Result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
def end_film_test(ok):
    result['passed']=ok;write_film_test();unreal.unregister_slate_post_tick_callback(film_test_handle);play.editor_request_end_play()
def movie_key(w,pc,key,down=True):unreal.SystemLibrary.execute_console_command(w,'Input.'+('+' if down else '-')+'key '+key,pc)
def move_movie_pawn(p,xyz):p.set_actor_location(unreal.Vector(*xyz),False,True);p.character_movement.stop_movement_immediately()
def tick_film_test(dt):
    try:
        assert time.monotonic()-state['start']<210.,result['stage']
        w=ed.get_game_world()
        if not w:return
        p=unreal.GameplayStatics.get_player_character(w,0)
        if not p:return
        t=unreal.GameplayStatics.get_time_seconds(w);pc=p.get_controller()
        m=unreal.GameplayStatics.get_actor_of_class(w,mc)
        if not m:return
        media=m.get_editor_property('FilmPlayer');active=m.get_editor_property('FilmActive');stage=result['stage']
        if t-state['sample']>1.:
            state['sample']=t;result['samples'].append([stage,round(t,2),m.get_editor_property('Stage'),m.get_editor_property('Beat'),active,media.is_playing(),m.get_editor_property('FilmFailed'),m.get_editor_property('FilmLastPosition')]);result['probe']={'failed':m.get_editor_property('Failed'),'hp':p.get_editor_property('VisorIntegrity'),'age':m.get_editor_property('FilmAge'),'started':m.get_editor_property('FilmStarted'),'media_time':str(media.get_time()),'texture_player':str(m.get_editor_property('FilmTexture').get_media_player()),'player':str(media),'sound_active':m.get_editor_property('FilmAudio').is_active()};write_film_test()
        if stage=='intro':
            if t<26:return
            pc.reset_ignore_move_input();pc.reset_ignore_look_input();pc.set_view_target_with_blend(p,0.)
            state['identity']=p.get_path_name();state['max']=p.get_editor_property('VisorMaxIntegrity')
            p.character_movement.set_movement_mode(unreal.MovementMode.MOVE_FLYING)
            move_movie_pawn(p,(34735.,87215.,2267.));result['stage']='stream';state['deadline']=t+35.;return
        if stage=='stream':
            assert t<state['deadline']
            route=unreal.GameplayStatics.get_actor_of_class(w,rc);stream=route.get_editor_property('CampusStreaming')
            if not stream or not stream.is_level_visible():return
            move_movie_pawn(p,(34735.,87215.,2267.));p.character_movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
            m.call_method('BeginChapter');m.call_method('LabTick');assert m.get_editor_property('CheckpointStage')==3
            m.call_method('BeginMemory');result['stage']='first_play';state['deadline']=t+10.;return
        if stage=='first_play':
            assert t<state['deadline'],'Movie did not start'
            if not media.is_playing():return
            assert active and not m.get_editor_property('FilmFailed')
            assert unreal.GameplayStatics.get_enable_world_rendering(w)
            assert pc.is_move_input_ignored() and not p.get_editor_property('can_be_damaged')
            assert m.get_editor_property('FilmWidget')
            assert 'ForeignMemory_Evacuation.mp4' in media.get_url()
            result['checks']['actual_video_playing']=True
            result['video_dimensions']=str(media.get_video_track_dimensions(0,0))
            result['audio_tracks']=media.get_num_tracks(unreal.MediaPlayerTrack.AUDIO)
            assert result['audio_tracks']>=1
            state['at']=t;result['stage']='capture';return
        if stage=='capture':
            if t-state['at']<2.2:return
            assert media.is_playing() and m.get_editor_property('FilmLastPosition')>1.,'Decoder clock did not advance'
            assert m.get_editor_property('FilmTexture').get_editor_property('current_aspect_ratio')>1.7,'No decoded video frames'
            assert m.get_editor_property('FilmAudio').is_playing(),'Movie audio is not running'
            result['checks']['decoded_frames_clock_and_sound']=True
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename="'+str(WORK/'MemoryFilm_InGame.png').replace('\\','/')+'" -nosuffix',pc)
            state['at']=t;result['stage']='request_retry';return
        if stage=='request_retry':
            if t-state['at']<.5:return
            movie_key(w,pc,'F9');state['deadline']=t+4.;result['stage']='check_retry';return
        if stage=='check_retry':
            assert t<state['deadline'],'F9 did not close the movie'
            if active:return
            movie_key(w,pc,'F9',False)
            assert not media.is_playing() and not m.get_editor_property('FilmWidget')
            assert unreal.GameplayStatics.get_enable_world_rendering(w)
            assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored() and p.get_editor_property('can_be_damaged')
            assert m.get_editor_property('Stage')==3 and not p.get_editor_property('NavMemoryReady')
            result['checks']['f9_closes_and_restores']=True
            state['at']=t;result['stage']='settle_retry';return
        if stage=='settle_retry':
            if t-state['at']<.65:return
            m.call_method('BeginMemory');state['deadline']=t+10.;result['stage']='play_for_skip';return
        if stage=='play_for_skip':
            assert t<state['deadline']
            if not media.is_playing():return
            movie_key(w,pc,'SpaceBar');state['deadline']=t+4.;result['stage']='skip';return
        if stage=='skip':
            assert t<state['deadline'],'Space did not skip the movie'
            if active:return
            movie_key(w,pc,'SpaceBar',False)
            if pc.is_move_input_ignored():return
            assert unreal.GameplayStatics.get_enable_world_rendering(w) and not media.is_playing()
            result['checks']['space_skips_and_restores']=True
            m.call_method('RetryCheckpoint');state['at']=t;result['stage']='settle_skip';return
        if stage=='settle_skip':
            if t-state['at']<.65:return
            m.call_method('BeginMemory');state['deadline']=t+10.;result['stage']='play_for_fault';return
        if stage=='play_for_fault':
            assert t<state['deadline']
            if not media.is_playing():return
            bad=unreal.new_object(unreal.FileMediaSource)
            bad.set_file_path(str(WORK/'intentional_missing_movie.mp4'))
            state['bad_source']=bad;media.open_source(bad)
            state['deadline']=t+12.;result['stage']='decode_fault';return
        if stage=='decode_fault':
            assert t<state['deadline'],'Decoder failure did not restore the terminal'
            if active:return
            assert m.get_editor_property('FilmFailed') and m.get_editor_property('Stage')==3
            assert unreal.GameplayStatics.get_enable_world_rendering(w) and not pc.is_move_input_ignored() and p.get_editor_property('can_be_damaged')
            assert not p.get_editor_property('NavMemoryReady') and p.get_editor_property('VisorMaxIntegrity')==state['max']
            assert m.get_editor_property('ArchiveUnlocked')
            result['checks']['decode_failure_recovers_without_reward']=True
            move_movie_pawn(p,(34735.,87215.,2267.));p.call_method('Nav_RecoverMemory')
            assert m.get_editor_property('Stage')==5 and m.get_editor_property('FilmActive')
            assert not m.get_editor_property('AlarmGuard')
            result['checks']['terminal_retries_without_another_fight']=True
            state['deadline']=t+12.;result['stage']='natural_start';return
        if stage=='natural_start':
            assert t<state['deadline']
            if not media.is_playing():return
            state['natural_wall']=time.monotonic();state['deadline']=t+35.;result['stage']='natural_end';return
        if stage=='natural_end':
            assert t<state['deadline'],'Natural ending did not complete the mission'
            if m.get_editor_property('Stage')!=6:return
            result['natural_elapsed']=time.monotonic()-state['natural_wall'];assert result['natural_elapsed']>=14.
            assert not active and not media.is_playing() and not m.get_editor_property('FilmWidget')
            assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored() and p.get_editor_property('can_be_damaged')
            assert unreal.GameplayStatics.get_enable_world_rendering(w)
            assert p.get_editor_property('NavMemoryReady') and p.get_editor_property('NavTargetIndex')==3
            assert p.get_editor_property('VisorMaxIntegrity')==state['max']+25.
            assert p.get_path_name()==state['identity']
            result['checks']['natural_ending_restores_and_rewards_once']=True
            m.call_method('CompleteMission');assert p.get_editor_property('VisorMaxIntegrity')==state['max']+25.
            result['checks']['reward_not_duplicated']=True
            result['stage']='passed';end_film_test(True)
    except Exception:
        result['error']=traceback.format_exc();end_film_test(False)
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Lvl_LabTutorial')
film_test_handle=unreal.register_slate_post_tick_callback(tick_film_test)
play.editor_request_begin_play();write_film_test()
