from pathlib import Path
import sys,os,json,hashlib,time,uuid,copy,shutil
from unittest.mock import patch
home=Path(sys.argv[1]);sys.path[:0]=[str(home),str(home/'app')]
os.environ.update(SOCIAL_AI_HOME=str(home/'fake-ai'),SOCIAL_RUNTIME_PATHS=str(home/'runtime-ci.json'),SOCIAL_VOICE_CACHE=str(home/'voice'),HF_HOME=str(home/'hf'))
(home/'runtime-ci.json').write_text('{"ai_home":"MISSING_AI","ffmpeg":"MISSING_FFMPEG","ffprobe":"MISSING_FFPROBE"}')
from socialreel.jobs import JobStore
from socialreel.common import write_json,stable_json,sha256_bytes
from socialreel.workflow import remember_selection
from socialreel.relocation import copy_backend
from local_bridge import LocalBridge
store=JobStore(home/'owned-jobs');jid='1'*32;run=store.folder(jid)/'runs/fixture';run.mkdir(parents=True)
script={'segments':[{'id':'scene1','role':'hook','claim_keys':[],'voiceover':'Synthetic saved statement.','on_screen':{'headline':'Synthetic statement.'}}]};write_json(run/'script.json',script);write_json(run/'package_manifest.json',{'package_id':'a'*64,'files':[]});write_json(run/'topic.json',{'selected':{'title':'Synthetic fixture','opportunity_id':'1','source_url':'https://example.invalid'}})
with store.connect()as c:c.execute('INSERT INTO jobs(id,request_json,state,created,updated,run_dir)VALUES(?,?,?,?,?,?)',(jid,'{}','completed',time.time(),time.time(),store.stored_directory(run)))
write_json(run/'media_manifest.json',{'files':[]});write_json(run/'result.json',{'voice':{}})
remember_selection(store,jid)
cfg={'writer':'template','voice':{'backend':'silent_test'},'llm':{'allow_spend':False},'selection':{'audience':'general_us','min_days_left':24},'search':{'keywords':['fixture'],'pagination':True,'max_search_requests':1,'max_detail_fetch':1},'generation_hold':'Synthetic CI; no production'};write_json(home/'config.json',cfg)
with patch('socialreel.packages.verify_package',return_value={'pass':True,'errors':[]}),patch('socialreel.packages.source_freshness',return_value={'fresh':True,'reasons':[]}):
 # Media verification stubs: this test concerns relocation/selection, not media integrity.
 original=(run/'script.json').read_bytes();dest=home/'relocated';copy_backend(store,dest,[jid]);assert (dest/'socialreel/owner_ru.json').read_bytes()==(home/'socialreel/owner_ru.json').read_bytes();assert json.loads((dest/'config.json').read_bytes())==cfg
 shutil.copytree(home/'app',dest/'app')
 target=JobStore(dest/'data/jobs');assert (target.root/'workflow_selection.json').read_bytes()==(store.root/'workflow_selection.json').read_bytes();assert Path(target.get(jid)['run_dir']).is_relative_to(dest)
 from socialreel.workflow import restore_workflow
 restore_workflow(target)
 bridge=LocalBridge(target);selection=bridge.get('/local/selection');assert selection['selection']['job_id']==jid
 write_json(home/'config.ai-local.json',{'selection':{'audience':'small_business'}});dest2=home/'override';copy_backend(store,dest2,[jid]);assert json.loads((dest2/'config.json').read_bytes())['selection']=={'audience':'small_business','min_days_left':24}
 resource=home/'socialreel/owner_ru.json';raw=resource.read_bytes();resource.unlink()
 try:
  try:copy_backend(store,home/'missing-resource',[jid])
  except Exception as e:assert 'resource missing'in str(e)
  else:raise AssertionError('Missing resource admitted')
  assert not(home/'missing-resource').exists()
 finally:resource.write_bytes(raw)
 assert (run/'script.json').read_bytes()==original
print('PASS Social246 config merge / exact RU resource / selected identity / LocalBridge; media gates explicitly stubbed')
