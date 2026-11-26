import argparse,asyncio,json,pathlib,contextlib,msvcrt,hashlib
import reveng_local_research as m
import buyer_evidence as b
import candidate_publication
import commercial_review
import copy
def signature(cards):return m.sha(json.dumps([{'id':c['candidate_id'],'revision':c.get('review_revision_hash'),'urls':[r['url'] for r in c['observed_basis']]} for c in cards],sort_keys=True).encode())
async def execute(root,run,offline):
 candidate_publication.recover(root)
 before_latest=(root/'latest-result.json').read_bytes()
 m.cancelled(run);path=root/'candidates.json';before=path.read_bytes();cards=json.loads(before.decode('utf-8-sig'));data=json.loads((root/'latest-result.json').read_text(encoding='utf-8-sig'));sig=signature(cards);known=data.get('buyer_evidence',{})
 saved=root/'buyer-results.json'
 if not known and saved.exists():
  cache=json.loads(saved.read_text(encoding='utf-8'));claim=cache.pop('integrity_sha256',None)
  if claim!=m.sha(json.dumps(cache,sort_keys=True,ensure_ascii=False).encode()):raise ValueError('Buyer result cache integrity mismatch')
  if cache.get('input_sha256')==sig:known=cache.get('summary',{});reviews=cache.get('reviews',{})
  else:reviews={}
 else:reviews={}
 if known.get('input_sha256')==sig and known.get('expires',0)>b.time.time():
  if not saved.exists():
   cache={'input_sha256':sig,'summary':known,'reviews':{x['candidate_id']:x['buyer_demand_review'] for x in cards if 'buyer_demand_review' in x}};cache['integrity_sha256']=m.sha(json.dumps(cache,sort_keys=True,ensure_ascii=False).encode());m.dump(saved,cache)
  data['buyer_evidence']=known
  for card in data.get('hypotheses',[]):
   if card.get('candidate_id') in reviews:card['buyer_demand_review']=reviews[card['candidate_id']]
  data.update(source_requests=0,model_requests=0,result_cache_hit=True);m.dump(run/'result.json',data);return
 if offline:raise ValueError('No current buyer-evidence cache; offline replay refused')
 stats={'source_requests':0,'source_cache_hits':0,'model_requests':0};m.dump(run/'result.json',{'status':'running','note':'Checking original public self-reports; no model calls','hypotheses':data.get('hypotheses',[])})
 active={x['candidate_id'] for x in data.get('hypotheses',[])};ordered=sorted(cards,key=lambda x:x['candidate_id'] not in active)
 reports=await b.collect(root,run,ordered,stats)
 if path.read_bytes()!=before:raise ValueError('Candidate history changed while fetching; preserve new work and retry')
 oldcards=copy.deepcopy(cards)
 for card in cards:card['buyer_demand_review']=b.review(card,reports)
 cards=commercial_review.merge_ledger(oldcards,cards)
 lookup={x['candidate_id']:x['buyer_demand_review'] for x in cards}
 data['hypotheses']=[copy.deepcopy(next(x for x in cards if x['candidate_id']==card['candidate_id']))for card in data['hypotheses']]
 data['buyer_evidence']={'status':'completed','input_sha256':sig,'expires':min([r['expires'] for r in reports.values()] or [b.time.time()+900]),'stats':stats,'sources':len(reports),'failures':sum(bool(x.get('error')) for x in reports.values()),'verified_customers':0}
 cache={'input_sha256':sig,'summary':data['buyer_evidence'],'reviews':lookup};cache['integrity_sha256']=m.sha(json.dumps(cache,sort_keys=True,ensure_ascii=False).encode());m.dump(saved,cache)
 data.update(note='Original reports checked; payer and purchase remain unknown',source_requests=stats['source_requests'],source_cache_hits=stats['source_cache_hits'],model_requests=0)
 m.cancelled(run);data.pop('cache_payload_sha256',None);data['cache_payload_sha256']=m.sha(json.dumps(data,sort_keys=True,ensure_ascii=False).encode());candidate_publication.publish(root,run,before,before_latest,cards,data);m.dump(run/'reports.json',reports);m.dump(run/'result.json',data)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--run',required=True);p.add_argument('--offline-replay',action='store_true');a=p.parse_args();root=pathlib.Path(a.root).resolve();run=pathlib.Path(a.run).resolve()
 if run.parent!=root/'runs':raise ValueError('Invalid buyer run path')
 run.mkdir(parents=True,exist_ok=True)
 with (root/'active.lock').open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:m.dump(run/'result.json',{'status':'busy','note':'Existing RevEng run owns lock','hypotheses':[]});return
  async def watched():
   work=asyncio.create_task(execute(root,run,a.offline_replay))
   async def cancel():
    while not (run/'cancel.request').exists():await asyncio.sleep(.2)
   monitor=asyncio.create_task(cancel())
   try:
    done,_=await asyncio.wait([work,monitor],timeout=400,return_when=asyncio.FIRST_COMPLETED)
    if work in done:await work
    else:
     work.cancel()
     with contextlib.suppress(asyncio.CancelledError):await work
     m.dump(run/'result.json',{'status':'cancelled','note':'Own buyer check cancelled; saved data unchanged','hypotheses':[]})
   finally:monitor.cancel()
  try:asyncio.run(watched())
  except asyncio.CancelledError:m.dump(run/'result.json',{'status':'cancelled','note':'Cancelled','hypotheses':[]})
  except Exception as ex:m.dump(run/'result.json',{'status':'failed','note':str(ex),'hypotheses':[]})
  finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':main()
