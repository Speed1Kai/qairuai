"""PIE-only test setup/observation. Does not edit or save assets or maps."""
import unreal, os, json
world=unreal.EditorLevelLibrary.get_game_world()
if not world:raise RuntimeError('Start PIE before running this test')
saved=unreal.Paths.project_saved_dir()
with open(os.path.join(saved,'interaction_test_stage.txt'),encoding='utf8') as f:stage=f.read().strip()
positions={'hologram':(-170,-80,110),'recovery':(-500,200,110),'atlas':(420,430,110),'mobility':(650,-110,110),'archive':(1400,520,110),'stealth':(1760,0,110),'door':(1330,0,110),'far':(-700,-600,110)}
pawn=unreal.GameplayStatics.get_player_character(world,0)
pc=unreal.GameplayStatics.get_player_controller(world,0)
if not pawn or not pc:raise RuntimeError('PIE player not found')
if stage in positions:
    pawn.set_actor_location(unreal.Vector(x=positions[stage][0],y=positions[stage][1],z=positions[stage][2]),False,True)
    pc.set_control_rotation(unreal.Rotator(pitch=-8,yaw=0,roll=0))
actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
data={'stage':stage,'pawn_location':str(pawn.get_actor_location()),'actors':[]}
for actor in actors:
    cls=actor.get_class().get_name()
    if cls.startswith(('BP_Lab','BP_Tutorial')):
        item={'class':cls,'name':actor.get_name(),'location':str(actor.get_actor_location())}
        try:item['near']=actor.get_editor_property('bPlayerNear')
        except Exception:pass
        data['actors'].append(item)
filename=os.path.join(saved,'interaction_runtime_tests.json')
previous=[]
if os.path.isfile(filename):
    with open(filename,encoding='utf8') as f:previous=json.load(f)
previous.append(data)
with open(filename,'w',encoding='utf8') as f:json.dump(previous,f,ensure_ascii=False,indent=2)
unreal.log('INTERACTION TEST STAGE '+stage+' | '+str(pawn.get_actor_location()))
