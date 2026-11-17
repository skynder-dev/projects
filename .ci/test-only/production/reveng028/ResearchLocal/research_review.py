"""Reproducible provenance/scope/lineage checks, never a semantic truth oracle."""
import json,re,time,hashlib
from pathlib import Path
import commercial_review as commercial
import source_rules
import analysis_jobs
import quote_contract
import source_context
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def normalized(text):return ' '.join(str(text).casefold().split())
def duplicates(card,existing):
 urls={commercial.canonical(r['url']) for r in card.get('observed_basis',[])};task=source_rules.task_for(card);out=[]
 for old in existing:
  shared=sorted(urls&{commercial.canonical(r['url']) for r in old.get('observed_basis',[])})
  exact=all(normalized(card.get(k,''))==normalized(old.get(k,'')) and normalized(card.get(k,'')) for k in ['title','solution_hypothesis'])
  if exact or (task and task==source_rules.task_for(old) and shared):out.append({'candidate_id':old.get('candidate_id'),'title':old.get('title'),'kind':'same_proposal_text' if exact else 'same_task_shared_sources','shared_source_urls':shared,'meaning':'Review overlap/lineage; not proof of identical solution, demand or truth. Never auto-merge user decisions.'})
 return out
def assess(card,observations,existing,prepared_request=None,quote_budgets=None):
 inventory_error=None
 try:byid=quote_contract.index_observations(observations)
 except ValueError as ex:byid={};inventory_error=str(ex)
 ids=list(dict.fromkeys(card.get('evidence_ids',[])));missing=[id for id in ids if id not in byid];rows=[byid[id] for id in ids if id in byid];reasons=[]
 def reason(code,message):reasons.append({'code':code,'message':message})
 if inventory_error:reason('ambiguous_source_inventory','Исходный набор нельзя однозначно связать по E-ID: '+inventory_error+'. Строки не объединены и не признаны подтверждением.')
 if not ids or missing:reason('invalid_reference','Нет исходного E-ID для части ссылок; утверждения нельзя привязать к исходному набору.')
 placeholders=[v for key in ['risks','missing_evidence'] for v in card.get(key,[]) if isinstance(v,str) and v.strip().casefold() in {'missing_proof','market_score'}]
 if placeholders:reason('placeholder_output','Вместо содержательных рисков/неизвестного модель вернула технические заполнители: '+', '.join(placeholders)+'. Это не доказательства и не завершённая оценка.')
 # E-ID membership establishes a link only, not entailment of narrative assertions.
 support=quote_contract.verify(card.get('observations_used',[]),observations,card.get('evidence_ids',[]),quote_budgets)
 if support['status']=='invalid':reason('invalid_source_quote','Цитата не совпадает с точным фрагментом указанного поля источника или превышает допустимый объём.')
 if support['status']=='verified_literals':reason('literal_quote_only','Точная цитата привязана к полю источника. Это не подтверждает причинные или коммерческие выводы гипотезы.')
 else:reason('claim_provenance_missing','Свободный текст гипотезы не содержит проверяемой связи каждого наблюдаемого утверждения с точным фрагментом источника. Наличие E-ID не доказывает причин, частоты, покупателя или спроса.')
 titles=[r for r in rows if source_context.source_packet(r)['content_scope']=='title_only']
 if titles:reason('title_only_scope','Для '+str(len(titles))+' ссылок доступны только заголовки. Тело, причина проблемы, нерешённость и готовность платить ими не подтверждены.')
 packages=[r for r in rows if r.get('kind')=='package_listing_not_demand']
 if packages:reason('package_is_alternative_not_buyer','Запись пакета/SDK подтверждает наличие программного средства, а не клиентов, корпоративное использование, бюджет или спрос.')
 exposed=[]
 try:
  raw=prepared_request['messages'][1]['content'].split('SOURCE OBSERVATIONS:\n',1)[1];sent={r['evidence_id']:r for r in json.loads(raw)}
  exposed=[r['evidence_id'] for r in titles if sent.get(r['evidence_id'],{}).get('excerpt')]
 except (KeyError,TypeError,ValueError,IndexError):pass
 if exposed:reason('collector_metadata_exposed','В исходном AI-входе для '+', '.join(exposed)+' заметка сборщика была передана как excerpt. Это ограничение сбора, не установленная пользовательская проблема; трактовка требует проверки.')
 copy=dict(card);copy['observed_basis']=rows;overlap=duplicates(copy,existing)
 if overlap:reason('possible_duplicate','Найдена повторная формулировка либо та же задача с общими исходными ссылками. Новизна не установлена; автоматическое объединение запрещено.')
 return {'status':'held_for_evidence_review','auto_admission':False,'truth_status':'not_established','reference_membership_valid':bool(ids) and not missing,'missing_reference_ids':missing,'reasons':reasons,'overlaps':overlap,'literal_support':support,'limits':'Проверены происхождение, тип данных и связь записей. Семантическая истинность свободного текста не проверена совпадением слов.'}
def review_notes(saved,index,title):
 review=saved.get('review',{})
 if review.get('status')!='REVIEW_COMPLETED':return None
 notes=review.get('cards',[])
 if not isinstance(notes,list) or index>=len(notes) or not isinstance(notes[index],dict) or notes[index].get('title')!=title:return None
 # Display only. These annotations are never evidence or owner/admission decisions.
 fields=['source_problem_alignment','quote_issue','unsupported_extension','independence','overlap','missed_constraint','buyer_and_demand']
 selected={k:notes[index][k] for k in fields if isinstance(notes[index].get(k),str)}
 model=saved.get('model_output');pin=review.get('model_output_sha256')
 bound=isinstance(model,dict) and isinstance(pin,str) and pin==digest(model)
 if not bound:return {'reviewer':'assistant','used_for_automatic_outcomes':False,'binding':'LEGACY_UNBOUND_OR_STALE_MODEL_OUTPUT','notes':{},'historical_notes_unbound':selected,'limitation':'Title/index alone do not bind a review to this model output. Historical notes preserved, not applied as current.'}
 cards=model.get('hypotheses',[])
 if not isinstance(cards,list) or index>=len(cards) or not isinstance(cards[index],dict) or cards[index].get('title')!=title:return None
 return {'reviewer':'assistant','used_for_automatic_outcomes':False,'binding':'EXACT_SAVED_MODEL_OUTPUT','model_output_sha256':pin,'notes':selected}

def refresh(m,root,run=None):
 root=Path(root).resolve()
 queue=analysis_jobs.load_queue(m,root);existing=json.loads((root/'candidates.json').read_text(encoding='utf-8-sig'));cards=[];failures=[]
 for job_id,job in queue.get('jobs',{}).items():
  if not job.get('analysis_result'):continue
  try:
   result=(root/job['analysis_result']).resolve();allowed=(root/'analysis-results').resolve()
   if result.parent!=allowed:raise ValueError('Result outside local analysis-results')
   input=(root/job['input_file']).resolve()
   if input.parent!=(root/'analysis-inputs').resolve():raise ValueError('Input outside local analysis-inputs')
   checked_id,_=analysis_jobs.inspect_input(m,root,input)
   if checked_id!=job_id:raise ValueError('Job/input mismatch')
   source=json.loads(input.read_text(encoding='utf-8'));saved=json.loads(result.read_text(encoding='utf-8'))
   if saved['model_output'].get('source_job')!=job_id:raise ValueError('Model output belongs to a different input job')
   raw=saved['model_output']['hypotheses']
   # Developer-authored saved review is deliberately not used in automatic outcomes.
   quote_budgets={}
   for i,original in enumerate(raw):
    card=dict(original);card['research_id']=digest({'job':job_id,'index':i,'model_card':original})[:24];card['source_job']=job_id;card['output_review']=assess(card,source['observations'],existing,source.get('request'),quote_budgets);card['observed_basis']=[r for r in source['observations'] if r['evidence_id'] in card.get('evidence_ids',[])];notes=review_notes(saved,i,card.get('title'));
    if notes is not None:card['assistant_source_review']=notes
    cards.append(card)
  except (ValueError,KeyError,TypeError,OSError) as ex:failures.append({'job':job_id,'error':str(ex)})
 try:
  import research_candidate_review
  research_candidate_review.attach(root,cards)
 except (ValueError,KeyError,TypeError,OSError) as ex:failures.append({'scope':'research_public_review','error':str(ex)})
 data={'status':'reviewed','cards':cards,'failures':failures,'active_candidates_added':0,'model_calls':0,'meaning':'Derived research review cards only; user business candidates and decisions unchanged.'};data['integrity_sha256']=digest(data);m.dump(root/'research-output-cards.json',data)
 if run:m.dump(run/'research-output-review.json',data)
 # Build only the local derived evidence graph; no collector or inference dependency.
 try:
  import evidence_workspace
  evidence_workspace.save(root,evidence_workspace.build(root))
 except (ValueError,KeyError,TypeError,OSError) as ex:
  # Invalid public evidence must not erase otherwise readable historical model cards.
  m.dump(root/'evidence-workspace-error.json',{'status':'DERIVED_INDEX_UNAVAILABLE','error':str(ex),'source_requests':0,'model_calls':0,'historical_cards_preserved':True})
 return data
