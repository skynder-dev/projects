import argparse,asyncio,json,pathlib,contextlib,msvcrt,copy
import commercial_review
import candidate_publication
import reveng_local_research as m
import competitor_match as c
import plan_mapping
import direct_alternatives as direct
import source_rules
import candidate_queue
async def execute(root,run,offline,plans_only=False,direct_only=False,observation_manifest=None):
 if observation_manifest:
  import official_observations
  report=official_observations.ingest(root,observation_manifest)
  cards,_=official_observations.read(root/"candidates.json")
  m.dump(run/"result.json",dict(status="official_observations_imported",note=report["note"],hypotheses=cards,source_requests=0,model_requests=0,source_errors=[]))
  return
 if direct_only:return await candidate_queue.execute(root,run,offline)
 candidate_publication.recover(root)
 m.cancelled(run)
 before_latest=(root/'latest-result.json').read_bytes();before_ledger=(root/'candidates.json').read_bytes()
 baseline_result=m.sha((root/'latest-result.json').read_bytes());baseline_ledger=m.sha((root/'candidates.json').read_bytes()) if (root/'candidates.json').exists() else None
 data=json.loads((root/'latest-result.json').read_text(encoding='utf-8-sig'));claimed=data.pop('cache_payload_sha256',None)
 if claimed!=c.digest(data):raise ValueError('Saved result integrity mismatch; no requests made')
 pairs=c.pairs_for(data.get('hypotheses',[]));input_sha=c.digest(pairs)
 existing=data.get('competitor_comparison',{});stats={'source_requests':0,'source_cache_hits':0,'model_requests':0}
 separate=root/'functional-results.json'
 if not existing and separate.exists():
  stored=json.loads(separate.read_text(encoding='utf-8-sig'));claim=stored.pop('integrity_sha256',None)
  if claim!=c.digest(stored):raise ValueError('Functional cache integrity mismatch')
  existing=stored.get(input_sha,{})
 same_input=existing.get('input_sha256')==input_sha
 mapping_current=same_input and all(x.get('plan_feature_mapping',{}).get('schema')==plan_mapping.SCHEMA and x.get('plan_feature_mapping',{}).get('expires',0)>c.time.time() for x in existing.get('comparisons',[]))
 direct_current=data.get('cohort_review',{}).get('candidate_revisions')=={card['candidate_id']:card.get('review_revision_hash') for card in json.loads((root/'candidates.json').read_text(encoding='utf-8-sig'))} and direct.review_cache_matches(existing) and all(x.get('expires',0)>c.time.time() for x in existing.get('direct_sources',[]))
 if same_input and existing.get('expires',0)>c.time.time() and mapping_current and direct_current and all(card.get('direct_alternatives',{}).get('schema')==direct.SCHEMA for card in data.get('hypotheses',[]) if any(pair['candidate_id']==card.get('candidate_id') for pair in pairs)) and not plans_only and not direct_only:
  data['competitor_comparison']=existing
  for card in data.get('hypotheses',[]):card['functional_comparisons']=[x for x in existing.get('comparisons',[]) if x.get('candidate_id')==card.get('candidate_id')]
  data.update(result_cache_hit=True,source_requests=0,model_requests=0);m.dump(run/'result.json',data);return
 if offline:raise ValueError('Offline replay has no current functional comparison and plan mapping')
 if (plans_only or direct_only) and not same_input:raise ValueError('Source-only plan refresh requires matching existing comparisons; no model fallback')
 cache=root/'functional-profiles';cache.mkdir(exist_ok=True)
 m.dump(run/'result.json',{'status':'running','note':'Checking official plan sections','hypotheses':data.get('hypotheses',[])})
 if direct_only:profiles=existing.get('profiles',{});failures=existing.get('failures',[])
 else:profiles,failures=await c.collect_profiles(m,cache,run,stats,[p['vendor'] for p in pairs])
 all_cards=json.loads((root/'candidates.json').read_text(encoding='utf-8-sig'))
 tasks=set(filter(None,(source_rules.task_for(card) for card in all_cards)))
 direct_sources=await direct.collect(root,run,tasks,stats)
 reviewed={}
 for card in all_cards:
  task=source_rules.task_for(card)
  review=direct.for_task(task,direct_sources,card)
  review['review_revision_hash']=card.get('review_revision_hash');review['candidate_id']=card['candidate_id']
  reviewed[card['candidate_id']]=review
 data['cohort_review']={'candidate_count':len(all_cards),'reviewed_at':m.now(),'candidate_revisions':{card['candidate_id']:card.get('review_revision_hash') for card in all_cards},'summary':[{"candidate_id":card['candidate_id'],"title":card['title'],"function_status":reviewed[card['candidate_id']]['status'],"buyer_status":card.get('buyer_demand_review',{}).get('payer_status','unknown'),"payment_evidence":None} for card in all_cards]}
 # Upgrade existing comparisons with source-only mapping. Never silently regenerate them.
 if same_input:
  comparisons=[plan_mapping.attach(x,profiles.get(x['vendor'])) for x in existing.get('comparisons',[])]
 else:comparisons=await c.compare_with_qwen(m,pairs,profiles,run,stats) if pairs else []
 for row in comparisons:
  pair=next((p for p in pairs if p['candidate_id']==row.get('candidate_id')),{});row['target_task_plan_mapping']['required_task_evidence']=pair.get('required_task_evidence',[])
  row['functional_assessment_observed_until']=existing.get('expires') if same_input else min([p['expires'] for p in profiles.values()] or [c.time.time()])
  row['functional_assessment_freshness']='historical; not regenerated' if same_input and existing.get('expires',0)<=c.time.time() else 'within original assessment window'
 for card in data['hypotheses']:
  card['functional_comparisons']=[x for x in comparisons if x['candidate_id']==card.get('candidate_id') and not x['negative_control']]
  if card.get('candidate_id') in reviewed:card['direct_alternatives']=reviewed[card['candidate_id']]
  card['functional_comparison_status']='evaluated' if card['functional_comparisons'] else 'unknown; no documented functional alternative'
 # Materialize through the existing revision/history policy.
 lookup={x['candidate_id']:x for x in data['hypotheses']};incoming=[]
 for old in all_cards:
  record=copy.deepcopy(old);id=record['candidate_id']
  if id in lookup:
   record['functional_comparisons']=copy.deepcopy(lookup[id]['functional_comparisons']);record['functional_comparison_status']=lookup[id]['functional_comparison_status']
  if id in reviewed:record['direct_alternatives']=copy.deepcopy(reviewed[id])
  incoming.append(record)
 refreshed=commercial_review.merge_ledger(all_cards,incoming)
 for card in refreshed:
  if card.get('direct_alternatives'):card['direct_alternatives'].update(candidate_id=card['candidate_id'],review_revision_hash=card['review_revision_hash'])
 byid={x['candidate_id']:x for x in refreshed};data['hypotheses']=[copy.deepcopy(byid[x['candidate_id']])for x in data['hypotheses']]
 data['cohort_review']['candidate_revisions']={x['candidate_id']:x['review_revision_hash']for x in refreshed}
 data.update(source_requests=stats['source_requests'],model_requests=stats['model_requests']);data['competitor_comparison']={'status':'completed','input_sha256':input_sha,'expires':existing.get('expires',0) if same_input else min([p['expires'] for p in profiles.values()] or [c.time.time()+3600]),'direct_schema':direct.SCHEMA,'direct_review_policy':direct.REVIEW_POLICY,'direct_sources':direct_sources,'comparisons':comparisons,'profiles':profiles,'failures':failures,'stats':stats}
 if m.sha((root/'latest-result.json').read_bytes())!=baseline_result or ((root/'candidates.json').exists() and m.sha((root/'candidates.json').read_bytes())!=baseline_ledger):raise ValueError('Saved cards changed during source check; no result overwrite')
 stored={}
 if separate.exists():
  stored=json.loads(separate.read_text(encoding='utf-8-sig'));stored.pop('integrity_sha256',None)
 stored[input_sha]=data['competitor_comparison'];stored['integrity_sha256']=c.digest(stored);m.dump(separate,stored)
 data['note']='Functional alternatives checked; no customer or profitability proven';data.pop('cache_payload_sha256',None);data['cache_payload_sha256']=m.sha(json.dumps(data,sort_keys=True,ensure_ascii=False).encode());candidate_publication.publish(root,run,before_ledger,before_latest,refreshed,data);m.dump(run/'result.json',data)
 ledger=root/'candidates.json'
 # Candidate/latest pair already published through its sealed run receipt.

def main():
 p=argparse.ArgumentParser();p.add_argument('--official-observations');p.add_argument('--root',required=True);p.add_argument('--run',required=True);p.add_argument('--offline-replay',action='store_true');p.add_argument('--plans-only',action='store_true');p.add_argument('--direct-only',action='store_true');a=p.parse_args();root=pathlib.Path(a.root).resolve();run=pathlib.Path(a.run).resolve()
 if run.parent!=root/'runs':raise ValueError('Invalid comparison run directory')
 run.mkdir(parents=True,exist_ok=True)
 with (root/'active.lock').open('a+b') as lock:
  lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
  try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:m.dump(run/'result.json',{'status':'busy','note':'An existing local RevEng run owns the lock','hypotheses':[]});return
  async def watched():
   work=asyncio.create_task(execute(root,run,a.offline_replay,a.plans_only,a.direct_only,a.official_observations))
   async def cancellation():
    while not (run/'cancel.request').exists():await asyncio.sleep(.2)
   cancel=asyncio.create_task(cancellation())
   try:
    done,_=await asyncio.wait([work,cancel],timeout=600,return_when=asyncio.FIRST_COMPLETED)
    if work in done:await work
    else:
     work.cancel()
     with contextlib.suppress(asyncio.CancelledError):await work
     m.dump(run/'result.json',{'status':'cancelled','note':'Own comparison cancelled or timed out; saved data unchanged','hypotheses':[]})
   finally:cancel.cancel()
  try:
   asyncio.run(watched())
  except asyncio.CancelledError:m.dump(run/'result.json',{'status':'cancelled','note':'Own comparison cancelled; saved data unchanged','hypotheses':[]})
  except Exception as ex:m.dump(run/'result.json',{'status':'failed','note':str(ex),'hypotheses':[]})
  finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':main()
