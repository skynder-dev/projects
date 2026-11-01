"""Sequential resumable official-source review of the saved candidate ledger. No models."""
import asyncio,json,time,copy
import commercial_review
from pathlib import Path
import reveng_local_research as m
import buyer_evidence as buyer
import direct_alternatives as direct
import source_rules
import research_review
import source_context
import candidate_publication

def digest(obj):return m.sha(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode())
def save(path,obj):m.dump(path,dict(obj,integrity_sha256=digest(obj)))
def signature(card):
 raw={k:card.get(k) for k in ['candidate_id','review_revision_hash','title','buyer','solution_hypothesis','market_category']}
 raw['review_revision_policy']='semantic_saved_observations_and_assessments_v4'
 raw['alternative_review_policy']=direct.REVIEW_POLICY
 raw['saved_context_binding']=digest(card.get('observed_basis',[]))
 raw['urls']=[x['url'] for x in card.get('observed_basis',[])]
 raw['rules']=digest(source_rules.SOURCES)
 raw['task_requirements']=source_rules.TASKS
 return digest(raw)
def apply_saved_review(card,item):
 incoming=copy.deepcopy(card)
 for field in ['buyer_demand_review','direct_alternatives']:incoming[field]=copy.deepcopy(item[field])
 if 'updated_observed_basis'in item:incoming['observed_basis']=copy.deepcopy(item['updated_observed_basis'])
 revised=commercial_review.merge_ledger([card],[incoming])[0]
 revised['direct_alternatives'].update(candidate_id=revised['candidate_id'],review_revision_hash=revised['review_revision_hash'])
 return revised

def refresh_saved_reviews(root,run):
 try:research_review.refresh(m,root,run)
 except (ValueError,KeyError,TypeError,OSError) as ex:
  try:m.dump(run/'research-refresh-error.json',{'error':str(ex),'model_calls':0,'source_requests':0})
  except OSError:pass
async def execute(root,run,offline=False):
 candidate_publication.recover(root)
 m.cancelled(run);ledger=root/'candidates.json';latest=root/'latest-result.json';ledger_bytes=ledger.read_bytes();latest_bytes=latest.read_bytes()
 try:research_cards=research_review.refresh(m,root,run)
 except (ValueError,KeyError,TypeError,OSError) as ex:research_cards={'cards':[]};m.dump(root/'research-output-cards.json',{'status':'unavailable','cards':[],'failures':[{'error':str(ex)}],'active_candidates_added':0,'model_calls':0})
 cards=json.loads(ledger_bytes.decode('utf-8-sig'));data=json.loads(latest_bytes.decode('utf-8-sig'));claim=data.pop('cache_payload_sha256',None)
 if claim!=digest(data):raise ValueError('Result integrity mismatch; no review started')
 path=root/'candidate-progress.json';previous={}
 if path.exists():
  old=json.loads(path.read_text(encoding='utf-8'));claim=old.pop('integrity_sha256',None)
  if claim!=digest(old):raise ValueError('Progress integrity mismatch; original cards unchanged')
  previous=old.get('items',{})
 state={'status':'running','total':len(cards),'completed':0,'active_candidate':None,'items':{},'updated_at':m.now()}
 stats={'source_requests':0,'source_cache_hits':0,'model_requests':0,'candidate_cache_hits':0};reviewed={}
 context_index,context_warnings=source_context.saved_question_contexts(m,root)
 def progress(note):
  state['updated_at']=m.now();state['stats']=dict(stats);save(path,state)
  m.dump(run/'result.json',{'status':state['status'],'note':note,'progress':{'completed':state['completed'],'total':state['total'],'active_candidate':state['active_candidate']},'source_requests':stats['source_requests'],'source_cache_hits':stats['source_cache_hits'],'model_requests':0,'hypotheses':data.get('hypotheses',[])})
 try:
  progress('Reviewing saved candidates sequentially; no model calls')
  for card in cards:
   card,context_changes=source_context.refresh_saved_basis(card,context_index)
   await asyncio.sleep(0);m.cancelled(run);id=card['candidate_id'];sig=signature(card);state['active_candidate']=id
   cached=previous.get(id,{})
   if cached.get('signature')==sig and cached.get('status')=='completed' and cached.get('expires',0)>time.time():
    item=cached;stats['candidate_cache_hits']+=1
   else:
    state['items'][id]={'signature':sig,'status':'running'};progress('Проверено %s/%s; покупатель: %s'%(state['completed'],len(cards),card['title']))
    reports=await buyer.collect(root,run,[card],stats,offline=offline);m.cancelled(run)
    if any('budget exhausted' in r.get('error','').lower() for r in reports.values()):
     state['status']='paused_budget';progress('Лимит запросов: прогресс сохранён, повтор продолжит незавершённого кандидата');return
    demand=buyer.review(card,reports);task=source_rules.task_for(card)
    progress('Проверено %s/%s; функции и тариф: %s'%(state['completed'],len(cards),card['title']))
    sources=await direct.collect(root,run,{task} if task else set(),stats,offline=offline);m.cancelled(run)
    if any('budget exhausted' in r.get('error','').lower() for r in sources):
     state['status']='paused_budget';progress('Лимит запросов: прогресс сохранён, повтор продолжит незавершённого кандидата');return
    alternatives=direct.for_task(task,sources,card)
    alternatives.update(candidate_id=id,review_revision_hash=card.get('review_revision_hash'))
    expiries=[r.get('expires',0) for r in sources]+[r.get('expires',0) for r in reports.values()]
    if any('no HTTP fallback' in r.get('error','') for r in sources+list(reports.values())):expiries.append(0)
    item={'signature':sig,'status':'completed','expires':min(expiries or [time.time()+900]),'buyer_demand_review':demand,'direct_alternatives':alternatives,'completed_at':m.now()}
    if context_changes:item.update(updated_observed_basis=copy.deepcopy(card['observed_basis']),source_context_refresh=context_changes)
    if context_warnings:item['source_context_warnings']=context_warnings
   reviewed[id]=item;state['items'][id]=item;state['completed']+=1;progress('Проверено %s/%s'%(state['completed'],len(cards)))
  m.cancelled(run)
  import research_candidate_review
  data['research_public_review']=await research_candidate_review.collect(root,run,research_cards.get('cards',[]),stats,offline=offline)
  research_review.refresh(m,root,run)
  if ledger.read_bytes()!=ledger_bytes or latest.read_bytes()!=latest_bytes:raise ValueError('Saved candidates changed during review; progress retained, no cards overwritten')
  revised_cards=[]
  for card in cards:
   item=reviewed[card['candidate_id']];revised=apply_saved_review(card,item);revised_cards.append(revised)
   # Cache the materialized revision, not its pre-review parent; otherwise every
   # subsequent read invalidates the just-produced cache and repeats collection.
   item['signature']=signature(revised);item['direct_alternatives']=copy.deepcopy(revised['direct_alternatives'])
  cards=revised_cards
  data['hypotheses']=[apply_saved_review(card,reviewed[card['candidate_id']]) if card.get('candidate_id') in reviewed else card for card in data.get('hypotheses',[])]
  data['cohort_review']={'candidate_count':len(cards),'reviewed_at':m.now(),'candidate_revisions':{c['candidate_id']:c.get('review_revision_hash') for c in cards},'summary':[{'candidate_id':c['candidate_id'],'title':c['title'],'function_status':c['direct_alternatives']['status'],'buyer_status':c['buyer_demand_review']['payer_status'],'payment_evidence':None} for c in cards]}
  all_reports={r['source_url']:r for c in cards for r in c['buyer_demand_review'].get('original_reports',[])}
  buyer_sig=m.sha(json.dumps([{'id':c['candidate_id'],'revision':c.get('review_revision_hash'),'urls':[r['url'] for r in c['observed_basis']]} for c in cards],sort_keys=True).encode())
  data['buyer_evidence']={'status':'completed','input_sha256':buyer_sig,'sources':len(all_reports),'failures':sum(bool(r.get('error')) for r in all_reports.values()),'verified_customers':0,'expires':min([r.get('expires',0) for r in all_reports.values()] or [time.time()+900])}
  # Publish completed business reviews even if independent research work paused.
  # Their materialized signatures stay reusable on resume; no recapture is needed.
  final_status=data['research_public_review'].get('status','failed')
  final_note='Saved candidate queue completed; buyer/payment remain unproven' if final_status=='completed' else 'Saved candidate reviews retained; research review '+final_status+'; resume unfinished research cards; buyer/payment remain unproven'
  data.update(status=final_status,note=final_note,source_requests=stats['source_requests'],source_cache_hits=stats['source_cache_hits'],model_requests=0,candidate_cache_hits=stats['candidate_cache_hits'])
  data['progress']={'completed':len(cards),'total':len(cards),'active_candidate':None};data['cache_payload_sha256']=digest(data)
  candidate_publication.publish(root,run,ledger_bytes,latest_bytes,cards,data)
  state.update(status=final_status,active_candidate=None,research_public_review=data['research_public_review']);save(path,state);m.dump(run/'result.json',data)
 except asyncio.CancelledError:
  refresh_saved_reviews(root,run)
  state['status']='cancelled';progress('Отменено: %s/%s; прогресс сохранён для продолжения'%(state['completed'],len(cards)));raise
 except Exception as ex:
  refresh_saved_reviews(root,run)
  state['status']='failed';progress(str(ex));raise
