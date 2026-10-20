from pathlib import Path
import json,subprocess,time,sys,hashlib,copy,os
R=Path(__file__).resolve().parent;source=Path(sys.argv[1]).resolve();T=Path(sys.argv[2]).resolve();T.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(source));import commercial_review as c
flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
def stage(name):
 root=T/name;root.mkdir();card=json.loads((R.parent.parent/'fixtures/reveng/card.json').read_bytes());card=c.merge_ledger([],[card])[0];cards=[card];(root/'candidates.json').write_text(json.dumps(cards,ensure_ascii=False),encoding='utf-8');data={'hypotheses':copy.deepcopy(cards),'status':'completed'};data['cache_payload_sha256']=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest();(root/'latest-result.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');notes={card['candidate_id']:{'decision':'keep','revision_hash':card['review_revision_hash'],'note':'Explicit test-only owner pin to existing fixture revision'}};(root/'review-notes.json').write_text(json.dumps(notes),encoding='utf-8');return root
children=[]
def start(root,name,mode='normal'):
 p=subprocess.Popen([sys.executable,'-B',str(R/'worker_child.py'),str(source),str(root),name,mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags);children.append(p);return p

def paused(root,name,p):
 until=time.monotonic()+12
 while not(root/'runs'/name/'paused').exists():
  if p.poll()is not None:raise ValueError(p.communicate()[1].decode())
  if time.monotonic()>until:raise ValueError('Test child did not reach controlled boundary')
  time.sleep(.02)
def done(p):
 out,err=p.communicate(timeout=30)
 if p.returncode:raise ValueError(err.decode())
def release(root,name): (root/'runs'/name/'release').write_text('resume own test child',encoding='utf-8')
def read(root):return json.loads((root/'candidates.json').read_bytes())[0],json.loads((root/'latest-result.json').read_bytes())['hypotheses'][0]
def outcome(root,name):return json.loads((root/'runs'/name/'outcome.json').read_bytes())
def pins(root):return (root/'review-notes.json').read_bytes()
result={'source':str(source),'cases':{},'model_calls':0,'HTTP_calls':0,'only_owned_children':True}
try:
 root=stage('interleave');note=pins(root);a=start(root,'A','before_pair');paused(root,'A',a);b=start(root,'B');done(b);bcard,_=read(root);release(root,'A');done(a);final,latest=read(root)
 result['cases']['two_workers']={'A':outcome(root,'A'),'B':outcome(root,'B'),'B_revision_retained_after_A':bcard['review_revision_hash']==final['review_revision_hash'],'pair_equal':final==latest,'notes_same':pins(root)==note,'history':len(final.get('history',[]))}
 # Retry a rejected worker from the materialized current state, not its old proposal.
 retry=start(root,'B-retry');done(retry);after,_=read(root);result['cases']['two_workers']['retry']=outcome(root,'B-retry');result['cases']['two_workers']['prior_revision_in_retry_history']=any(x.get('review_revision_hash')==final['review_revision_hash']for x in after.get('history',[]))
 root=stage('late');a=start(root,'old-research-review','late');paused(root,'old-research-review',a);b=start(root,'new-review');done(b);before=(root/'candidates.json').read_bytes();release(root,'old-research-review');done(a);result['cases']['late_old_review']={'old':outcome(root,'old-research-review'),'new':outcome(root,'new-review'),'new_bytes_preserved':before==(root/'candidates.json').read_bytes()}
 root=stage('interrupted');notes=pins(root);before=(root/'latest-result.json').read_bytes();a=start(root,'interrupted','after_first');paused(root,'interrupted',a);a.kill();a.communicate(timeout=5);card,latest=read(root);result['cases']['interrupted']={'partial_pair_seen':card!=latest,'latest_before_recovery_unchanged':before==(root/'latest-result.json').read_bytes(),'killed_only_own_child':True,'pending_receipt':(root/'candidate-publication.pending.json').exists()}
 b=start(root,'retry');done(b);card,latest=read(root);result['cases']['interrupted'].update(retry=outcome(root,'retry'),pair_equal_after_retry=card==latest,revision_correct=card['review_revision_hash']==c.revision(card),owner_note_same=pins(root)==notes,owner_pin_not_renewed=json.loads(notes)[card['candidate_id']]['revision_hash']!=card['review_revision_hash'])
 # No invented source_job, model completion or execution receipt is created.
 stored=json.loads((R.parent.parent/'fixtures/reveng/research-output-cards.json').read_bytes()).get('cards',[])
 result['cases']['late_saved_model_result']={'status':'NOT_QUALIFIED_NO_SAVED_RESULT','saved_example_research_cards':len(stored),'reason':'The supplied example has no completed prepared-analysis result to replay. Late actual source-review queue run is tested separately. No model execution or fabricated result/source_job.'}
except Exception as e:result['error']=str(e);raise
finally:
 for p in children:
  if p.poll()is None:p.kill();p.communicate(timeout=5)
 (T/'proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
