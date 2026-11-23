"""Finish the already-authored player graph without duplicating camera input nodes."""
import os
source_path=os.path.join(os.path.dirname(__file__),'Build_PlayerVisor.py')
source=open(source_path,encoding='utf-8-sig').read()
exec(compile(source.split('\ntry:\n')[0],source_path,'exec'))
player=A.load_asset(PLAYER);wbp=A.load_asset(ROOT+'/WBP_PlayerVisor');mat=A.load_asset(ROOT+'/M_VisorRim');g=Flow(player)
tail=source.split(' # Status values are gameplay variables, not fixed decorative percentages.\n',1)[1]
exec(compile('try:\n'+tail,source_path,'exec'))
