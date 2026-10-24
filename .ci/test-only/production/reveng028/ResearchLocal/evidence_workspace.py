"""Offline derived evidence graph. No imports of collectors, models or network clients.

Human-authored saved annotations are interpretations, never automated semantic proof.
The graph records exact revisions and quote locations; no market/customer admission.
"""
import argparse,hashlib,json,os,tempfile
from pathlib import Path

LIMIT=8*1024*1024
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True).encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def read(path):
 raw=path.read_bytes()
 if len(raw)>LIMIT:raise ValueError('Evidence input exceeds 8MiB')
 return raw,json.loads(raw.decode('utf-8-sig'))
def signed(value):
 if not isinstance(value,dict) or value.get('integrity_sha256')!=digest(canonical({k:v for k,v in value.items() if k!='integrity_sha256'})):raise ValueError('Research state integrity mismatch')
def reference(material,quote):
 text=material['text'];start=text.find(quote)
 if not quote or start<0:raise ValueError('Quotation absent from exact material revision')
 if text.find(quote,start+1)>=0:raise ValueError('Ambiguous quotation; explicit reviewed fragment required')
 return {'material_id':material['id'],'text_sha256':material['text_sha256'],'start':start,'end':start+len(quote),'quote':quote,'meaning':'Literal support only; no semantic entailment or customer verification'}
def next_step(url):
 # Transparent assistant-authored acceptance plans, not model output or executed results.
 if 'youtube' in url:
  return {'action':'Составить минимальный iframe воспроизводимый пример и сравнить запущенный через HTTP вариант с локальным файлом в настоящем Safari. Записать версию OS/Safari и фактическую ошибку, не назначать error153 без наблюдения.','success':'Получена повторяемая матрица: одинаковый URL/код, условия запуска, браузер и ошибка; изменение объясняется наблюдением.','failure':'Ошибка не воспроизведена либо меняются несколько условий — причина остаётся неизвестной.','execution':'NOT_EXECUTED_REQUIRES_SEPARATE_BROWSER_NETWORK_AUTHORIZATION','market_gap':'Сколько независимых владельцев сайтов тратят время на тот же сбой и нужен ли им продукт, неизвестно.'}
 if 'wikipedia-move' in url:
  return {'action':'Подготовить план переноса на отдельном разрешённом тестовом аккаунте: набор страниц, исходное состояние, дубликаты, частичная ошибка, повторный запуск и откат. Не использовать личную историю.','success':'Для согласованного набора сохранены все страницы и исходный список; частичная ошибка не теряет данные, повтор не дублирует, откат проверен.','failure':'Не доказана поддержка endpoint или нет проверенного отката — это не готовая миграция.','execution':'PLAN_ONLY_ACCOUNT_AND_WRITE_OPERATIONS_REQUIRE_AUTHORIZATION','market_gap':'Один публичный запрос не доказывает регулярный рынок или готовность платить.'}
 if 'wordpress.org/support' in url:
  return {'action':'Для этого отдельного обращения подготовить диагностическую карточку: точная операция, ожидаемый/фактический результат, окружение, доступный фрагмент ошибки. Отделить пользовательскую гипотезу причины от наблюдения; изменения сайта не выполнять.','success':'Есть минимальная проверяемая гипотеза причины и тест, который может её опровергнуть; связь с данным обращением сохранена.','failure':'Общий совет или лог без связи с симптомом не считается исправлением.','execution':'OFFLINE_PLAN_AVAILABLE_SITE_ACCESS_AND_CHANGES_NOT_AUTHORIZED','market_gap':'Разные симптомы пяти авторов не образуют подтверждённую единую потребность в шаблонах поддержки.'}
 if '95686' in url:
  return {'action':'Следующий отдельный обзор должен проверить одну конкретную альтернативу по recording→testcases, mocks DB/HTTP из того же трафика, Linux/headless CI, noisy fields, тарифу и предпочтению без per-service SDK.','success':'Для каждого ограничения есть ссылка на точную документацию/тариф либо явное неизвестное; PoC отделён от документированной возможности.','failure':'Название API-testing товара без матрицы покрытия не доказывает соответствие.','execution':'PLAN_ONLY_NEW_PUBLIC_READ_REQUIRES_AUTHORIZATION','market_gap':'Запрос инструмента не устанавливает покупателя или оплаченный бюджет.'}
 if '15853' in url:
  return {'action':'Для следующего разрешённого обзора составить критерии шаблонов contribution policy: полный запрет, исключения для translation/code review, источник и условия повторного использования.','success':'Сопоставлены конкретные тексты политик, а не мнения об AI; исключения и лицензия не додуманы.','failure':'Общие browser testing документы или наличие репозитория не отвечают на запрос.','execution':'PLAN_ONLY_NEW_PUBLIC_READ_REQUIRES_AUTHORIZATION','market_gap':'Наличие запроса шаблона не доказывает необходимость платного продукта.'}
 if '95688' in url:
  return {'action':'Следующий обзор должен проверить Android focused-window JSON: команда, поля результата, версия Android и требуемые права. Запускать на устройстве только после отдельного разрешения.','success':'Документированы поля и права; фактический вывод отдельно проверен на разрешённом тестовом устройстве.','failure':'Browser automation или неподтверждённое имя команды не считается Android-решением.','execution':'PLAN_ONLY_PUBLIC_READ_AND_DEVICE_TEST_REQUIRE_AUTHORIZATION','market_gap':'Автор собственной утилиты не является подтверждённым покупателем нашей гипотезы.'}
 return {'action':'Сохранить как дискуссию о предполагаемой реакции компаний на AI; не превращать мнения в запрос продукта.','success':'Возможная продуктовая гипотеза имеет отдельный конкретный problem report; иначе остаётся обсуждением.','failure':'Спекуляция о потерях компаний используется как доказанный спрос.','execution':'NO_PRODUCT_TEST_JUSTIFIED_BY_THIS_DISCUSSION','market_gap':'Гипотеза о реакции крупных компаний не доказывает потери, клиентов или спрос.'}

def add_archived_materials(root,graph,materials):
 """Read only registered sealed inputs/snapshots and fully bound diagnostic catalogs.
 E-IDs are local origin labels, never global identities; original and answer roles stay separate.
 """
 import re
 def load(name):
  raw,obj=read(root/name);graph['inputs'][name]=digest(raw);return obj
 def error(origin,field,ex):graph['errors'].append({'origin':origin,'field':field,'error':str(ex),'action':'Only invalid saved field/container excluded; no repair, refetch or inference'})
 def insert(row,origin,field,kind,text,expected,author,url,stamp,response,scope):
  if not isinstance(text,str) or not text:return
  if expected and digest(text.encode())!=expected:raise ValueError('Saved field hash mismatch')
  identity=digest(canonical({'kind':kind,'field':field,'url':url,'text_sha256':digest(text.encode()),'captured_at':stamp,'response_sha256':response}))
  m={'id':identity,'kind':kind,'url':url,'author':'unknown' if author is None or author=='' else str(author),'role':kind,'captured_at':stamp,'published_at':row.get('published_at'),'text':text,'text_sha256':digest(text.encode()),'response_sha256':response,'text_scope':scope,'source_field':field,'card_ids':[],'version_ids':[],'origins':[],'epistemic_status':'SAVED_METADATA_NOT_AUTHOR_BODY' if kind=='metadata_only' else 'PACKAGE_DESCRIPTION_NOT_DEMAND' if kind=='package_listing' else 'COMMUNITY_ANSWER_NOT_QUESTION_AUTHOR_OR_VERIFIED_FIX' if kind=='community_answer' else 'AUTHOR_REPORT_NOT_VERIFIED'}
  dest=materials.setdefault(identity,m)
  ref=dict(origin,source_field=field,evidence_id=row.get('evidence_id'),observation_id=row.get('observation_id'),reported_author_id=author,url=url,captured_at=stamp)
  if dest['author']!=m['author']:dest['author']='differing saved author metadata; see exact origins; identity not inferred'
  if ref not in dest.setdefault('origins',[]):dest['origins'].append(ref)
  # Joins to a model card require its exact sealed source-job container and source URL, not just E-ID.
  for h in graph['hypotheses']:
   if origin.get('job_id')==h.get('source_job') and (row.get('url') or url) in h.get('saved_source_urls',[]):
    if h['id'] not in dest['card_ids']:dest['card_ids'].append(h['id'])
    if identity not in h['material_ids']:h['material_ids'].append(identity)
 def observation(row,origin):
  url=row.get('url','');body=row.get('context_text');expected=row.get('context_text_sha256');scope=row.get('content_scope');package=row.get('kind')=='package_listing_not_demand'
  if body and expected:
   kind='package_listing' if package else 'archived_original' if scope in ['question_body','original_post_only','original_ask_post'] else 'unscoped_observation'
   try:insert(row,origin,'context_text',kind,body,expected,row.get('author_id'),url,row.get('context_observed_at') or row.get('observed_at'),row.get('context_response_sha256') or row.get('response_sha256'),'Exact saved normalized context_text; scope='+str(scope)+'; truncated='+str(row.get('context_truncated','unknown'))+'; not a new source capture')
   except (ValueError,TypeError) as ex:error(origin,'context_text',ex)
  else:
   # Never turn a title or legacy unscoped excerpt into a complete author report.
   text=row.get('title') or ''
   insert(row,origin,'title','package_listing' if package else 'metadata_only',text,None,row.get('author_id'),url,row.get('observed_at'),row.get('response_sha256'),'Saved title metadata only; full original body unavailable/unverified; legacy excerpt not substituted')
  if row.get('answer_text'):
   try:
    expected=row.get('answer_text_sha256')
    if not expected:raise ValueError('Answer has no saved hash; not attributed to question author')
    insert(row,origin,'answer_text','community_answer',row['answer_text'],expected,row.get('answer_author_id'),row.get('answer_url') or url,row.get('answer_observed_at'),row.get('answer_response_sha256'),'Exact saved normalized answer; selection='+str(row.get('answer_selection'))+'; scope='+str(row.get('answer_scope'))+'; truncated='+str(row.get('answer_text_truncated','unknown'))+'; advice is not an independently verified fix')
   except (ValueError,TypeError) as ex:error(origin,'answer_text',ex)
 if (root/'analysis-queue.json').exists():
  try:
   queue=load('analysis-queue.json');signed(queue)
   for id,job in queue.get('jobs',{}).items():
    name=job.get('input_file','')
    try:
     if not re.fullmatch('[0-9a-f]{64}',id) or name!='analysis-inputs/'+id+'.json':raise ValueError('Noncanonical registered input')
     obj=load(name);payload={k:v for k,v in obj.items() if k not in ['input_sha256','payload_sha256','prepared_at']};identity={k:v for k,v in payload.items() if k!='source_expires'}
     if digest(canonical(identity))!=id or obj.get('input_sha256')!=id or digest(canonical(payload))!=obj.get('payload_sha256'):raise ValueError('Sealed input integrity mismatch')
     if job.get('input_file_sha256') and graph['inputs'][name]!=job['input_file_sha256']:raise ValueError('Registered input bytes mismatch')
     for row in obj.get('observations',[]):observation(row,{'container':name,'job_id':id})
    except (ValueError,KeyError,TypeError,OSError) as ex:error(name,'sealed_input',ex)
  except (ValueError,KeyError,TypeError,OSError) as ex:error('analysis-queue.json','registry',ex)
 if (root/'observation-index.json').exists():
  try:
   index=load('observation-index.json');signed(index)
   for id in index.get('snapshots',[]):
    name='observation-snapshots/'+id+'.json'
    try:
     if not re.fullmatch('[0-9a-f]{64}',id):raise ValueError('Noncanonical snapshot')
     obj=load(name);signed(obj)
     if obj['integrity_sha256']!=id:raise ValueError('Snapshot identity mismatch')
     for row in obj.get('observations',[]):observation(row,{'container':name,'snapshot_id':id})
    except (ValueError,KeyError,TypeError,OSError) as ex:error(name,'snapshot',ex)
  except (ValueError,KeyError,TypeError,OSError) as ex:error('observation-index.json','registry',ex)
 if (root/'attribution-cases/cases.json').exists():
  try:
   import research_export
   index=load('attribution-cases/cases.json')
   for case in index.get('cases',[]):
    try:
     id=case['id']
     if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',id):raise ValueError('Invalid diagnostic case ID')
     blobs={'attribution-cases/cases.json':json.dumps({'schema':index['schema'],'cases':[case]}).encode()}
     for field in ['input','catalog','output','response']:
      name=case[field]
      if name!=id+'-'+field+'.json':raise ValueError('Noncanonical diagnostic filename')
      raw,obj=read(root/'attribution-cases'/name);graph['inputs']['attribution-cases/'+name]=digest(raw);blobs['attribution-cases/'+name]=raw
     research_export.check_attribution(lambda n:blobs[n],set(blobs))
     catalog=json.loads(blobs['attribution-cases/'+case['catalog']])
     for eid,source in catalog['sources'].items():
      for field,row in source['fields'].items():
       text=row.get('text',row.get('full_text'));expected=row.get('reference',{}).get('source_field_sha256') or row.get('sha256')
       if not expected:raise ValueError('Diagnostic source hash missing')
       insert(dict(row,evidence_id=eid),{'container':'attribution-cases/'+case['catalog'],'diagnostic_case':id},field,'community_answer' if field=='answer_text' else 'archived_original',text,expected,row.get('reported_author_id'),row.get('url') or source.get('url'),row.get('captured_at') or source.get('observed_at'),None,'Frozen diagnostic field; role='+str(row.get('field_role',row.get('source_role','unknown')))+'; exact input/catalog and response/output binding checked; not a new model run')
    except (ValueError,KeyError,TypeError,OSError) as ex:error(case.get('id','unknown'),'diagnostic_catalog',ex)
  except (ValueError,KeyError,TypeError,OSError) as ex:error('attribution-cases/cases.json','case_index',ex)

def build(root):
 root=Path(root).resolve();inputs={};loaded={}
 for name in ['research-candidate-reviews.json','research-output-cards.json']:
  if name=='research-candidate-reviews.json' and not(root/name).exists():inputs[name]=None;loaded[name]=None;continue
  raw,loaded[name]=read(root/name);inputs[name]=digest(raw);signed(loaded[name])
 state=loaded['research-candidate-reviews.json'];output=loaded['research-output-cards.json']
 if not isinstance(output.get('cards'),list):raise ValueError('Required research cards array missing; not an empty result')
 if state is not None and not isinstance(state.get('items'),dict):raise ValueError('Public review items invalid; not an absent optional file')
 public_absent=state is None;state=state if state is not None else {'items':{}};cards=output['cards']
 graph={'schema':'reveng-evidence-workspace-v1','inputs':inputs,'materials':[],'analyses':[],'hypotheses':[],'errors':[],'provenance':'Offline deterministic joins over saved material and existing assistant-authored annotations; no new model or semantic classifier','auto_admission':False,'market_status':'UNVERIFIED','model_calls':0,'network_calls':0}
 if public_absent:graph['errors'].append({'scope':'research-candidate-reviews.json','error':'Optional public review state absent; public comparisons unknown','action':'Saved source/model fields retained; no synthetic review or document result created'})
 materials={};analysis={}
 for card in cards:
  rid=card['research_id'];graph['hypotheses'].append({'id':rid,'title':card.get('title',''),'text':{k:card.get(k,'') for k in ['buyer','problem_hypothesis','solution_hypothesis','validation_step']},'origin':'HISTORICAL_MODEL_OUTPUT_NOT_SEMANTICALLY_VALIDATED','source_job':card.get('source_job'),'material_ids':[],'market_status':'UNVERIFIED','owner_decision':'SEPARATE_UNCHANGED','saved_source_urls':[r['url'] for r in card.get('observed_basis',[]) if isinstance(r,dict) and r.get('url')]})
  h=graph['hypotheses'][-1];allowed={r.get('url') for r in card.get('observed_basis',[]) if isinstance(r,dict)}
  versions=state.get('items',{}).get(rid,{}).get('research_versions',[])
  for wrap in versions:
   try:
    payload=wrap['payload_json']
    if not isinstance(payload,str) or len(payload.encode())>LIMIT or digest(payload.encode())!=wrap['payload_sha256']:raise ValueError('Version hash mismatch')
    v=json.loads(payload)
    if v['research_id']!=rid:raise ValueError('Version belongs to another hypothesis')
    # Validate entire version before adding any of its materials or annotations.
    local={};validdocs=set()
    for kind,rows in [('original_post',v['sources']),('provider_document',v['documents'])]:
     for r in rows:
      if not isinstance(r['text'],str) or not r['text'] or digest(r['text'].encode())!=r['text_sha256']:raise ValueError('Material hash mismatch')
      if kind=='original_post' and r['url'] not in allowed:raise ValueError('Original outside sealed card source URLs')
      identity=digest(canonical({'kind':kind,'url':r['url'],'text_sha256':r['text_sha256'],'response_sha256':r.get('response_sha256'),'captured_at':r.get('captured_at'),'author_metadata':r.get('author'),'role_metadata':r.get('role')}))
      row=dict(r,id=identity,kind=kind,role=r.get('role','unknown'),author=r.get('author','unknown'),card_ids=[],version_ids=[],epistemic_status='AUTHOR_REPORT_NOT_VERIFIED' if kind=='original_post' else 'DOCUMENTED_DESCRIPTION_NOT_RUNTIME_VERIFIED')
      if r['url'] in local and local[r['url']]['id']!=identity:raise ValueError('Ambiguous URL revisions within version')
      local[r['url']]=row
      if kind=='provider_document':validdocs.add(r['url'])
    localanalyses=[]
    for c in v['comparisons']:
     if c['original_url'] not in allowed or c['original_url'] not in local:raise ValueError('Annotation original missing')
     original=local[c['original_url']];docurls=c['document_urls']
     if not set(docurls)<=validdocs:raise ValueError('Annotation document outside version')
     refs=[];quote_errors=[]
     for u in docurls:
      for f in local[u].get('facts',[]):
       try:refs.append(dict(reference(local[u],f['quote']),capability_label=f['kind'],origin='SAVED_RULE_MATCH_NOT_SEMANTIC_APPROVAL'))
       except ValueError as ex:quote_errors.append({'url':u,'quote':f.get('quote'),'error':str(ex)+'; excluded, not repaired'})
     a={'original_id':original['id'],'task':c['task_as_read'],'assessment':c['assessment'],'origin':'ASSISTANT_MANUAL_REVIEW_OF_SAVED_MATERIAL','document_ids':[local[u]['id'] for u in docurls],'supporting_document_fragments':refs,'quote_errors':quote_errors,'version_id':wrap['payload_sha256'],'card_ids':[rid],'next_step':dict(next_step(c['original_url']),origin='ASSISTANT_AUTHORED_PROPOSAL_NOT_EXECUTED'),'demand_status':'UNVERIFIED_NO_CUSTOMER_INFERENCE','semantic_entailment':'MANUAL_INTERPRETATION_NOT_AUTOMATICALLY_VERIFIED','unrelated_document_ids':[local[u]['id'] for u in validdocs-set(docurls)]}
     a['version_ids']=[a.pop('version_id')];a['id']=digest(canonical({k:a[k] for k in ['original_id','task','assessment','document_ids','supporting_document_fragments','quote_errors']}));localanalyses.append(a)
    for row in local.values():
     dest=materials.setdefault(row['id'],row)
     if rid not in dest['card_ids']:dest['card_ids'].append(rid)
     if wrap['payload_sha256'] not in dest['version_ids']:dest['version_ids'].append(wrap['payload_sha256'])
     if row['id'] not in h['material_ids']:h['material_ids'].append(row['id'])
    for a in localanalyses:
     dest=analysis.setdefault(a['id'],a)
     if rid not in dest['card_ids']:dest['card_ids'].append(rid)
     for version_id in a['version_ids']:
      if version_id not in dest['version_ids']:dest['version_ids'].append(version_id)
   except (ValueError,KeyError,TypeError) as ex:graph['errors'].append({'research_id':rid,'version_id':wrap.get('payload_sha256') if isinstance(wrap,dict) else None,'error':str(ex),'action':'Version excluded; other versions remain readable; originals not repaired'})
 add_archived_materials(root,graph,materials)
 graph['materials']=list(materials.values());graph['analyses']=list(analysis.values())
 graph['legacy_hypotheses']=[]
 if (root/'candidates.json').exists():
  raw,legacy=read(root/'candidates.json');graph['inputs']['candidates.json']=digest(raw)
  for c in legacy:
   if not isinstance(c,dict) or not c.get('candidate_id'):continue
   urls={r.get('url') for r in c.get('observed_basis',[]) if isinstance(r,dict)}
   graph['legacy_hypotheses'].append({'id':c['candidate_id'],'title':c.get('title',''),'origin':'LEGACY_UNVALIDATED_HYPOTHESIS_IN_PRESERVED_OWNER_LEDGER','status':c.get('status','unverified'),'material_ids':[m['id'] for m in graph['materials'] if m['url'] in urls],'source_refs':c.get('observed_basis',[]),'text':{k:c.get(k,'') for k in ['buyer','problem_hypothesis','solution_hypothesis','validation_step']}})
 # A URL or two posts about one website does not establish independent people or repeated demand.
 graph['coverage']={'unique_original_revisions':sum(r['kind']=='original_post' for r in graph['materials']),'unique_document_revisions':sum(r['kind']=='provider_document' for r in graph['materials']),'archived_fields':sum(r['kind'] not in ['original_post','provider_document'] for r in graph['materials']),'community_answer_fields':sum(r['kind']=='community_answer' for r in graph['materials']),'all_material_fields':len(materials),'hypotheses':len(cards),'legacy_hypotheses':len(graph.get('legacy_hypotheses',[])),'verified_customers':None,'independent_authors':None,'limits':'Distinct URLs, revisions and model hypotheses are not independent buyers; no market score computed. Missing alternatives reflect this saved corpus, not market absence.'}
 return graph

def save(root,graph):
 payload=canonical(graph).decode();raw=json.dumps({'payload_json':payload,'payload_sha256':digest(payload.encode())},ensure_ascii=False,indent=2).encode();target=Path(root)/'evidence-workspace.json'
 fd,name=tempfile.mkstemp(prefix='evidence-workspace-',suffix='.tmp',dir=root)
 try:
  with os.fdopen(fd,'wb') as stream:stream.write(raw)
  os.replace(name,target)
 finally:
  if os.path.exists(name):os.unlink(name)
 return target
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path);args=parser.parse_args();g=build(args.root);p=save(args.root,g);print(json.dumps({'status':'PARTIAL' if g['errors'] else 'READY','path':str(p),'coverage':g['coverage'],'errors':g['errors'],'network_calls':0,'model_calls':0},ensure_ascii=False))
