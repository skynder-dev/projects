"""Same public buyer/direct collectors for research cards, never a business ledger merge."""
import asyncio,json,time,re,copy,os,tempfile
import collection_versions
from urllib.parse import urlsplit,parse_qs
import reveng_local_research as m,buyer_evidence as buyer,direct_alternatives as direct,source_rules
def digest(value):return m.sha(json.dumps(value,sort_keys=True,ensure_ascii=False).encode())
def signature(card):return digest({'research_id':card['research_id'],'model':{k:card.get(k) for k in ['title','buyer','problem_hypothesis','solution_hypothesis','market_category','evidence_ids']},'urls':[r['url'] for r in card.get('observed_basis',[])],'rules':source_rules.SOURCES,'tasks':source_rules.TASKS,'public_review_contract':2,'collection_projection_contract':3,'routing_policy':source_rules.ROUTING_POLICY})
def load(root):
 path=root/'research-candidate-reviews.json'
 if not path.exists():return {'items':{}}
 data=json.loads(path.read_text(encoding='utf-8'));claim=data.pop('integrity_sha256',None)
 if claim!=digest(data):raise ValueError('Research public review integrity mismatch')
 return data
def save(root,data):
 raw=json.dumps(dict(data,integrity_sha256=digest(data)),ensure_ascii=False,indent=2,allow_nan=False).encode()
 if len(raw)>8*1024*1024:raise ValueError('Research versions exceed8MiB viewer limit; previous file preserved, no pruning')
 fd,name=tempfile.mkstemp(prefix='research-candidate-reviews-',suffix='.tmp',dir=root)
 try:
  with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  os.replace(name,root/'research-candidate-reviews.json')
 finally:
  if os.path.exists(name):os.unlink(name)

def collection_status(item):
 if item.get('review_mode')=='source_material_collection_no_semantic_review':return 'public_material_collection_unreviewed' if item.get('expires',0)>time.time() else 'public_material_collection_stale_unreviewed'
 return 'public_checks_historical' if item.get('review_mode')=='saved_material_only_no_freshness_renewal' else 'public_checks_completed' if item.get('expires',0)>time.time() else 'public_checks_stale'

def attach(root,cards):
 saved=load(root)
 for card in cards:
  item=saved.get('items',{}).get(card['research_id'])
  if not item:continue
  # Version identity and source membership are checked by their viewer/index, independently of current collection rules.
  card['public_research_versions']=item.get('research_versions',[])
  if item.get('signature')!=signature(card):
   if item.get('followup_evidence'):card['public_validation']={'status':'historical_saved_followup_only','followup_evidence':item['followup_evidence'],'review_mode':'saved_artifact_reference_only_not_current_collection','checked_at':item.get('checked_at'),'active_candidate_admission':False,'next_step':'Сохранённая заметка/план остаётся доступной по точному хешу. Текущий разбор смотрите в версиях материалов; это не выполненный тест или разрешение его выполнить.'}
   continue
  card['public_research_versions']=item.get('research_versions',[]);card['buyer_demand_review']=item['buyer_demand_review'];card['direct_alternatives']=item['direct_alternatives'];card['public_validation']={'status':collection_status(item),'checked_at':item['checked_at'],'next_step':item['next_step'],'followup_evidence':item.get('followup_evidence'),'active_candidate_admission':False,'review_mode':item.get('review_mode','public_source_collection'),'derived_reviewed_at':item.get('derived_reviewed_at'),'source_capture_dates':item.get('source_capture_dates',[]),'next_evidence_tasks':item.get('next_evidence_tasks',[])}
 return cards

def public_basis(card):
 # Public collection is independent of AI quote/semantic quality and buyer proof.
 hosts={'superuser.com','webapps.stackexchange.com','travel.stackexchange.com','diy.stackexchange.com','graphicdesign.stackexchange.com','webmasters.stackexchange.com','softwarerecs.stackexchange.com','opensource.stackexchange.com'}
 rows=[];seen=set()
 for row in card.get('observed_basis',[]):
  if not isinstance(row,dict):continue
  url=row.get('url','')
  try:
   p=urlsplit(url)
   if p.scheme!='https' or p.username or p.password or p.port not in [None,443]:continue
   host=p.hostname or ''
   approved=(host in hosts and re.match(r'^/questions/[0-9]+(?:/|$)',p.path)) or (host=='wordpress.org' and p.path.startswith('/support/topic/')) or (host=='news.ycombinator.com' and p.path=='/item' and parse_qs(p.query).get('id',[''])[0].isdigit())
   if approved and url not in seen:rows.append(row);seen.add(url)
  except (ValueError,TypeError):continue
 return rows

def saved_original(row):
 # Prefer a verified body already embedded in the original observation; never an answer/title.
 text=row.get('context_text');expected=row.get('context_text_sha256')
 if not isinstance(text,str) or not text or m.sha(text.encode())!=expected:return None
 import monetary_utterances
 url=row['url'];stamp=row.get('context_observed_at') or row.get('observed_at');events=monetary_utterances.extract(text,urlsplit(url).hostname,None,'buyer_original_normalized_text',url,stamp)['events']
 return {'source_url':url,'observed_at':stamp,'published_at':row.get('published_at'),'response_sha256':row.get('context_response_sha256') or row.get('response_sha256'),'answer_status':row.get('answer_status','unknown'),'facts':[],'expires':0,'payer_verified':False,'customer_verified':False,'monetary_source_text':text,'monetary_source_field_sha256':expected,'monetary_utterance_contract':1,'monetary_utterances':events,'reported_author_id':row.get('author_id'),'source_field':'context_text','source_role':'original_post','source_body_origin':'hash_verified_saved_observation_not_new_HTTP','source_text_truncated':row.get('context_truncated',False),'meaning':'Original saved body retained byte-for-byte; no normalization, fresh fetch, semantic approval or buyer inference'}

def reviewed_task_routes(root,card):
 """Only explicit saved manual source/document comparisons may route research alternatives.

 Model titles/categories, unrelated documents and E-ID membership cannot establish task fit.
 This selects collection scope only; no full coverage, buyer or semantic validation is claimed.
 """
 item=load(root).get('items',{}).get(card['research_id'],{});allowed={r['url'] for r in public_basis(card)};tasks=set();reviewed_urls=set();errors=[]
 for wrap in item.get('research_versions',[]):
  try:
   payload=wrap['payload_json']
   if not isinstance(payload,str) or m.sha(payload.encode())!=wrap['payload_sha256']:raise ValueError('Version hash mismatch')
   v=json.loads(payload)
   if v['research_id']!=card['research_id']:raise ValueError('Version belongs to another card')
   originals={r['url']:r for r in v['sources']};documents={r['url']:r for r in v['documents']};local=set();local_urls=set()
   for c in v['comparisons']:
    url=c['original_url']
    if url not in allowed or url not in originals:raise ValueError('Manual task source outside card')
    source=originals[url]
    if m.sha(source['text'].encode())!=source['text_sha256']:raise ValueError('Original text hash mismatch')
    for url in c['document_urls']:
     doc=documents[url]
     if m.sha(doc['text'].encode())!=doc['text_sha256']:raise ValueError('Document text hash mismatch')
     matches=[spec['task'] for spec in direct.SOURCES.values() if spec['url']==url]
     local.update(matches);local_urls.add(url)
   tasks.update(local);reviewed_urls.update(local_urls)
  except (KeyError,TypeError,ValueError) as ex:errors.append(str(ex))
 return {'tasks':sorted(tasks),'document_urls':sorted(reviewed_urls),'errors':errors,'origin':'saved_assistant_manual_source_document_comparisons','scope':'Collection routing only; task equivalence, buyer and demand are unverified'}

def preserve_research_history(old,new):
 """Collection may update its current projection, never discard immutable versions/user followups."""
 result=dict(new)
 for key in ['research_versions','followup_evidence']:
  if key in old:result[key]=copy.deepcopy(old[key])
 return result

def source_hint_routes(card):
 """Provisional collection scope from saved source words/metadata, never model category or task fit."""
 tasks=set();hints=[]
 for row in public_basis(card):
  url=row['url'];p=urlsplit(url);title=row.get('title','') if isinstance(row.get('title'),str) else '';body=row.get('context_text');fields=['source_url_slug']+(['saved_title_metadata'] if title else [])
  if not isinstance(body,str) or not body or m.sha(body.encode())!=row.get('context_text_sha256'):body=''
  else:fields.append('hash_verified_saved_original_context')
  text=(title+' '+body+' '+p.path.replace('-',' ')).casefold();local=set()
  if p.hostname=='wordpress.org' and any(word in text for word in ['critical error','blank screen']):local.add('wordpress_support_templates')
  if 'wikipedia_watchlist_migration' in source_rules.research_tasks.task_hints({'title':text}):local.add('wikipedia_watchlist_migration')
  if 'safari' in text and 'youtube' in text:local.update(['safari_embed_repair','safari_embed_debug'])
  if local:hints.append({'source_url':url,'hint_tasks':sorted(local),'hint_fields':fields,'meaning':'Lexical/source-metadata collection hint only; no semantic relevance or buyer proof'});tasks.update(local)
 return {'tasks':sorted(tasks),'hints':hints,'routing_policy':source_rules.ROUTING_POLICY,'discovery_status':'specific_hints_require_review' if tasks else 'unmapped_needs_discovery','origin':'provisional_saved_source_hints_not_model_category','mode':'COLLECTION_HINT_ONLY','scope':'Documents may be collected before manual review. No classification as a matching solution follows from this routing.'}

def document_candidates(tasks,rows,routing):
 projected=[]
 for raw in rows:
  record=copy.deepcopy(raw);record['document_rule_classification']=record.get('classification');record['classification']='document_candidate_task_fit_unreviewed';record['task_fit_to_original']='UNREVIEWED_FOR_THIS_CAPTURE';record['documented_rule_covered']=record.get('covered',[]);record['covered']=[];record['buyer_match']={'role':'unknown','status':'unknown_source_role_and_buyer','meaning':'Documented workflow role is not the source author, a verified buyer, or a client of the user'};record['interpretation']='Documented words/capabilities only. Collection routing does not establish that this source task is solved.';projected.append(record)
 return {'schema':'document-candidates-unreviewed-v1','status':'document_sources_unavailable' if projected and all(r.get('error') for r in projected) else 'document_candidates_unreviewed' if projected else 'not_evaluated_no_document_scope' if not tasks else 'no_document_body_verified','task':'collection_hints_only','alternatives':projected,'routing_review':routing,'scope':'No semantic task fit, complete coverage, customer or market absence inferred. Frozen prior comparisons remain in their own versions.'}

async def collect(root,run,cards,stats,offline=False):
 data=load(root);eligible=[dict(c,observed_basis=public_basis(c)) for c in cards if public_basis(c)];summary={'status':'completed','public_review_contract':2,'eligible':len(eligible),'completed':0,'skipped_no_approved_public_source':len(cards)-len(eligible),'quote_quality_is_not_collection_gate':True,'verified_buyers_required':False}
 for card in eligible:
  m.cancelled(run);id=card['research_id'];sig=signature(card);old=data['items'].get(id)
  if old and collection_versions.append(root,card,old,'previous-saved-projection-no-new-capture'):save(root,data)
  if old and old.get('signature')==sig and old.get('expires',0)>time.time():summary['completed']+=1;continue
  routing=reviewed_task_routes(root,card);tasks=set(routing['tasks'])
  if not tasks:routing=source_hint_routes(card);tasks=set(routing['tasks'])
  reports=await buyer.collect(root,run,[card],stats,offline=offline);m.cancelled(run)
  sources=await direct.collect(root,run,tasks,stats,offline=offline);m.cancelled(run)
  if any('budget exhausted' in r.get('error','').lower() for r in list(reports.values())+sources):summary['status']='paused_budget';break
  demand=buyer.review(card,reports)
  alternatives=document_candidates(tasks,sources,routing)
  authors={r['author_id'] for r in card.get('observed_basis',[]) if r.get('author_id')}
  demand['observed_need']={'status':'public_source_collection_attempted_not_semantically_validated','source_posts':len({r['url'] for r in card.get('observed_basis',[])}),'public_author_ids_in_saved_metadata':len(authors),'independent_buyers':None,'problem_claim_validated':False,'meaning':'Reading source material is permitted independently of AI quote quality or proven buyers. A public question, metadata role or literal signal is not a verified customer, semantic endorsement or representative demand.'}
  steps={'safari_embed_repair':'Проверить код iframe/referrer-policy исходной публичной страницы по документации ошибки153; затем отдельно проверить воспроизведение в Safari.','wikipedia_watchlist_migration':'Проверить штатный перенос и сохранность/обратимость на документации и синтетическом списке; без доступа к аккаунту.'}
  expiries=[r.get('expires',0) for r in list(reports.values())+sources]
  if any('no HTTP fallback' in r.get('error','') for r in list(reports.values())+sources):expiries.append(0)
  data['items'][id]=preserve_research_history(old or {},{'signature':sig,'buyer_demand_review':demand,'direct_alternatives':alternatives,'checked_at':m.now(),'expires':min(expiries or [time.time()+900]),'next_step':steps.get(next(iter(tasks)) if len(tasks)==1 else None,'Проверить функциональное преимущество и ограничения пользователя; оплата остаётся неизвестной.'),'active_candidate_admission':False})
  data['items'][id]['review_mode']='source_material_collection_no_semantic_review'
  data['items'][id]['source_capture_dates']=sorted({r['observed_at'] for r in list(reports.values())+sources if r.get('observed_at') and not r.get('error')})
  collection_versions.append(root,card,data['items'][id],run.name)
  save(root,data);summary['completed']+=1
 if (root/'analysis-queue.json').exists() and (root/'candidates.json').exists():
  try:
   import research_review
   research_review.refresh(m,root,run);summary['derived_views']='refreshed_without_model_or_network'
  except (ValueError,KeyError,TypeError,OSError) as ex:
   m.dump(run/'research-refresh-error.json',{'error':str(ex),'saved_evidence_versions_preserved':True,'model_calls':0,'source_requests':0});summary['derived_views']='unavailable_saved_versions_preserved'
 summary['model_calls']=0;summary['active_candidates_added']=0;m.dump(run/'research-public-review.json',summary);return summary
