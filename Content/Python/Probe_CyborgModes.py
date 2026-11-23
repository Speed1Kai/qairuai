import unreal,os,json,sys
sys.path.insert(0,os.path.dirname(__file__))
from CityCombat_Common import *
p=A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter');e=G.get_graph_editor_by_name(p,'EventGraph')
R={'cast_menus':[str(m) for m in e.list_available_nodes([]) if 'ThirdPersonCharacter' in str(m) or ('KeyboardEvents' in str(m) and str(m).split('|')[-1] in ('1','2','3','4','Tab'))], 'hudclass':str(unreal.get_default_object(B.generated_class(A.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode'))).get_editor_property('hud_class'))}
R['graphs']=list(map(str,B.list_graph_names(p)))
json.dump(R,open(os.path.join(unreal.Paths.project_saved_dir(),'cyborg_modes_api.json'),'w'),indent=2)

