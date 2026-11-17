import sys,json,time,os
def ci_audit(event,args):
 if event.startswith('socket.') or event in ('urllib.Request','subprocess.Popen','os.system','os.startfile'):raise PermissionError('CI offline child guard')
 if event=='import' and str(args[0]).split('.')[0] in ('torch','transformers','onnxruntime'):raise PermissionError('No model imports')
sys.addaudithook(ci_audit)
from pathlib import Path
source,home,runname,mode=map(str,sys.argv[1:]);sys.path.insert(0,source);root=Path(home);run=root/'runs'/runname;run.mkdir(parents=True,exist_ok=True)
import candidate_queue as q,reveng_local_research as m
m.read_http=lambda *a,**k:(_ for _ in ()).throw(AssertionError('HTTP forbidden'))
m.ask_qwen=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Model forbidden'))
# Controlled markers distinguish independent persistence updates; not real
# source/business facts. Actual saved card and queue implementation are used.
import commercial_review as commercial,copy
apply=q.apply_saved_review
def marked(card,item):
 revised=apply(card,item);incoming=copy.deepcopy(revised);tag='CONTROLLED PERSISTENCE UPDATE '+runname+'; not a source fact'
 if tag not in incoming.get('risks',[]):incoming['risks']=incoming.get('risks',[])+[tag]
 updated=commercial.merge_ledger([card],[incoming])[0]
 updated['direct_alternatives'].update(candidate_id=updated['candidate_id'],review_revision_hash=updated['review_revision_hash'])
 return updated
q.apply_saved_review=marked
real=m.dump;triggered=False
try:import candidate_publication as pub
except ImportError:pub=None

def pause():
 (run/'paused').write_text('owned test child paused',encoding='utf-8')
 deadline=time.monotonic()+25
 while not (run/'release').exists():
  if time.monotonic()>deadline:raise RuntimeError('Owned fixture pause timeout')
  time.sleep(.02)
def hooked(path,data):
 global triggered
 path=Path(path)
 if not triggered and mode=='late'and path==root/'candidate-progress.json':triggered=True;pause()
 if not triggered and pub is None and mode=='before_pair'and path==root/'candidates.json':triggered=True;pause()
 real(path,data)
 if not triggered and pub is None and mode=='after_first'and path==root/'candidates.json':triggered=True;pause()
m.dump=hooked
if pub:
 write=pub._write
 def publication_write(path,raw):
  global triggered
  path=Path(path)
  if not triggered and mode=='before_pair'and path==root/'candidates.json':triggered=True;pause()
  write(path,raw)
  if not triggered and mode=='after_first'and path==root/'candidates.json':triggered=True;pause()
 pub._write=publication_write
try:
 call=q.execute(root,run,offline=True)
 while True:
  try:call.send(None)
  except StopIteration:break
 (run/'outcome.json').write_text(json.dumps({'status':'completed'}),encoding='utf-8')
except Exception as e:
 (run/'outcome.json').write_text(json.dumps({'status':'rejected','reason':str(e)}),encoding='utf-8')
