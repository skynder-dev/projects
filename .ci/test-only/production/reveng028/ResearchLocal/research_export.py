"""Local evidence export only: explicit data allowlist, no network/model/config or credential access."""
import argparse,csv,hashlib,io,json,re,zipfile,os,uuid
import source_ledger,portable_paths
import manual_hypotheses,analysis_readiness,legacy_candidate_reviews,editor_recovery,field_references,decision_recovery
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
LIMIT=32*1024*1024
# Every structured JSON decode uses the existing strict local-data decoder.
# It rejects root/nested/escaped-equivalent keys without rewriting saved bytes.
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False).encode()
SENSITIVE={'apikey','accesstoken','refreshtoken','authorization','password','privatekey','clientsecret','cookie','connectionstring','servicerolekey'}
def scan(value,path='data'):
 if isinstance(value,dict):
  for k,v in value.items():
   if re.sub('[^a-z]','',k.lower()) in SENSITIVE and v not in [None,'',False]:raise ValueError('Sensitive field excluded from export: '+path+'.'+k)
   scan(v,path+'.'+k)
 elif isinstance(value,list):
  for i,v in enumerate(value):scan(v,path+'['+str(i)+']')
 elif isinstance(value,str):
  if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}|\bAKIA[A-Z0-9]{16}\b|\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|https?://[^\s/:@]+:[^\s/@]+@|Authorization\s*:\s*Bearer\s+\S+',value,re.I):raise ValueError('Credential-like value excluded from export at '+path)
def signed(data):
 claim=data.get('integrity_sha256');plain={k:v for k,v in data.items() if k!='integrity_sha256'}
 if claim!=sha(canonical(plain)):raise ValueError('Signed research data integrity mismatch')

def check_lineage(fetch,names):
 records={PurePosixPath(n).stem:n for n in names if n.startswith('analysis-lineage/')}
 if 'analysis-lineage-index.json' in names:
  index=manual_hypotheses.loads(fetch('analysis-lineage-index.json'));signed(index)
  if not set(index.get('events',[]))<=set(records):raise ValueError('Analysis lineage event missing from export')
 for id,name in records.items():
  data=manual_hypotheses.loads(fetch(name));signed(data)
  if data.get('integrity_sha256')!=id or data.get('kind')!='preparation_superseded':raise ValueError('Invalid analysis lineage identity')
  old=data.get('superseded_input','');new=data.get('completed_input','')
  if not all(re.fullmatch('[0-9a-f]{64}',x) for x in [old,new]):raise ValueError('Invalid analysis lineage input')
  for job,key in [(old,'superseded_input_sha256'),(new,'completed_input_sha256')]:
   path='analysis-inputs/'+job+'.json'
   if path not in names or sha(fetch(path))!=data[key]:raise ValueError('Lineage input bytes mismatch')
  result='analysis-results/'+new+'.json'
  if result not in names or sha(fetch(result))!=data['completed_result_sha256'] or manual_hypotheses.loads(fetch(result)).get('model_output',{}).get('source_job')!=new:raise ValueError('Lineage completed result mismatch')
  if 'analysis-results/'+old+'.json' in names:raise ValueError('Lineage cannot supersede a completed result')

def check_workspace(fetch,names):
 if 'evidence-workspace.json' not in names:return None
 wrapper=manual_hypotheses.loads(fetch('evidence-workspace.json'));payload=wrapper.get('payload_json')
 if not isinstance(payload,str) or sha(payload.encode())!=wrapper.get('payload_sha256'):raise ValueError('Evidence workspace payload mismatch')
 graph=manual_hypotheses.loads(payload)
 if graph.get('schema')!='reveng-evidence-workspace-v1' or graph.get('auto_admission') is not False:raise ValueError('Unsupported evidence workspace policy')
 inputs=graph.get('inputs',{})
 if not {'research-candidate-reviews.json','research-output-cards.json'}<=set(inputs):raise ValueError('Required evidence inputs missing')
 for name in inputs:
  if name not in ['research-candidate-reviews.json','research-output-cards.json','candidates.json','analysis-queue.json','observation-index.json','attribution-cases/cases.json'] and not re.fullmatch(r'analysis-inputs/[0-9a-f]{64}\.json|observation-snapshots/[0-9a-f]{64}\.json|attribution-cases/[a-z0-9][a-z0-9-]{0,63}-(?:catalog|output|input|response)\.json',name):raise ValueError('Unexpected evidence input path')
 for name,h in inputs.items():
  if h is None:
   if name!='research-candidate-reviews.json' or name in names:raise ValueError('Absent optional workspace input appeared or is not optional')
   continue
  if name not in names or sha(fetch(name))!=h:raise ValueError('Stale evidence workspace input')
 materials={}
 for m in graph.get('materials',[]):
  if m['id'] in materials or sha(m['text'].encode())!=m['text_sha256']:raise ValueError('Evidence material mismatch')
  materials[m['id']]=m
  for origin in m.get('origins',[]):
   name=origin['container'];field=origin['source_field']
   if name not in inputs:raise ValueError('Archived field container outside evidence inputs')
   obj=manual_hypotheses.loads(fetch(name))
   if name.startswith('attribution-cases/'):
    row=obj['sources'][origin['evidence_id']]['fields'][field];actual=row.get('text',row.get('full_text'))
   else:
    rows=[r for r in obj['observations'] if r.get('evidence_id')==origin.get('evidence_id') and r.get('observation_id')==origin.get('observation_id')]
    if len(rows)!=1:raise ValueError('Ambiguous archived field origin')
    actual=rows[0].get(field)
   if actual!=m['text']:raise ValueError('Archived field text binding mismatch')
 for a in graph.get('analyses',[]):
  if a['original_id'] not in materials or any(i not in materials for i in a['document_ids']):raise ValueError('Evidence comparison reference missing')
  for r in a['supporting_document_fragments']:
   m=materials[r['material_id']]
   if type(r['start']) is not int or type(r['end']) is not int or not 0<=r['start']<r['end']<=len(m['text']) or m['text_sha256']!=r['text_sha256'] or m['text'][r['start']:r['end']]!=r['quote']:raise ValueError('Evidence fragment mismatch')
 return graph['coverage']

def check_attribution(fetch,names):
 prefix='attribution-cases/';index=prefix+'cases.json';actual={n for n in names if n.startswith(prefix)}
 if index not in names:
  if actual:raise ValueError('Attribution cases have no index')
  return 0
 data=manual_hypotheses.loads(fetch(index));wanted={index};seen=set()
 if data.get('schema')!='saved-attribution-cases-v1':raise ValueError('Unsupported attribution case schema')
 for case in data.get('cases',[]):
  id=case.get('id','')
  if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',id) or id in seen:raise ValueError('Invalid or duplicate attribution case id')
  seen.add(id);loaded={}
  for key in ['catalog','output','input','response']:
   name=case.get(key,'')
   if name!=id+'-'+key+'.json':raise ValueError('Noncanonical attribution file path')
   path=prefix+name;wanted.add(path)
   if path not in names:raise ValueError('Attribution evidence missing: '+path)
   raw=fetch(path)
   if len(raw)>8*1024*1024 or sha(raw)!=case.get(key+'_sha256'):raise ValueError('Attribution case bytes mismatch: '+path)
   loaded[key]=manual_hypotheses.loads(raw.decode('utf-8-sig'))
  user=[m for m in loaded['input'].get('messages',[]) if m.get('role')=='user']
  if not user:raise ValueError('Attribution input user message missing')
  content=user[-1]['content'];start=content.find('{')
  if start<0 or manual_hypotheses.loads(content[start:])!=loaded['catalog']:raise ValueError('Attribution input/catalog snapshot mismatch')
  choices=loaded['response'].get('choices',[])
  if not choices or choices[0].get('finish_reason')!='stop' or manual_hypotheses.loads(choices[0]['message']['content'])!=loaded['output']:raise ValueError('Attribution raw response/output mismatch')
 if actual!=wanted:raise ValueError('Unlisted attribution case content')
 return len(seen)

def owner_decision_projection(card,notes):
 id=card.get('candidate_id')or card.get('research_id');current=card.get('review_revision_hash')
 result={'binding':'NO_SAVED_OWNER_DECISION','current_review_revision_hash':current,'meaning':'Saved owner preference only; not buyer, market, semantic approval or execution authorization'}
 if id not in notes:return result
 entry=notes[id];result['saved_entry']=entry
 bound=isinstance(entry,dict)and entry.get('decision')in ['keep','reject']and isinstance(current,str)and bool(current)and entry.get('revision_hash')==current
 result['binding']='CURRENT_EXACT_REVISION'if bound else'HISTORICAL_OR_UNBOUND'
 return result

def received_references(value):
 if isinstance(value,dict):
  if value.get('source_identity_status')=='integrity_failure_no_refetch':raise ValueError('Unresolved received-payload integrity failure; no portable evidence claim')
  if 'received_payloads'in value:
   receipts=value['received_payloads']
   if not isinstance(receipts,list):raise ValueError('Invalid received payload inventory')
   for r in receipts:
    if not isinstance(r,dict):raise ValueError('Invalid received payload reference')
    digest=r.get('payload_sha256','');size=r.get('bytes')
    if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest)or r.get('payload_file')!='buyer-source-payloads/'+digest+'.raw'or type(size)is not int or not 0<=size<=1048576:raise ValueError('Noncanonical received payload path/hash/size')
    yield r
  for k,v in value.items():
   if k!='received_payloads':yield from received_references(v)
 elif isinstance(value,list):
  for v in value:yield from received_references(v)

def check_portable_sources(fetch,names):
 refs=[]
 for name in ['candidates.json','research-output-cards.json']:
  if name in names:refs+=list(received_references(manual_hypotheses.loads(fetch(name))))
 wanted=set()
 for r in refs:
  name=r['payload_file'];wanted.add(name)
  if name not in names:raise ValueError('Received payload missing from portable snapshot: '+name)
  raw=fetch(name)
  if len(raw)!=r['bytes']or sha(raw)!=r['payload_sha256']:raise ValueError('Received payload bytes differ from receipt')
 actual={n for n in names if n.startswith('buyer-source-payloads/')}
 if actual!=wanted:raise ValueError('Unreferenced raw payload in portable snapshot')
 ids=[]
 if 'official-observations.json'in names:
  import official_observations
  ids=official_observations.verify_projection(manual_hypotheses.loads(fetch('official-observations.json')))
 return {'schema':'reveng-portable-source-evidence-v1','official_observation_ids':ids,'received_payload_files':sorted(wanted),'receipt_references':len(refs),'meaning':'Exact received bytes and structured summaries; no source truth, customer, ranking or execution authority inferred'}

def export(root,output):
 output=Path(output).resolve()
 portable_paths.check_files([output,output.with_suffix('.csv'),output.parent/('.export-'+'0'*32+'.tmp'),output.parent/('.summary-'+'0'*32+'.tmp')],'Research export')
 with source_ledger.writer_lock(Path(root).resolve()/'.research-export-write-v2.lock'):
  return _export_locked(root,output)

def _publish_no_replace(staged,target):
 # Same-directory hard-link publication is atomic and cannot replace another file.
 # Unsupported filesystems fail closed; a pre-existing export is never overwritten.
 os.link(staged,target)

def _export_locked(root,output):
 root=Path(root).resolve();output=Path(output).resolve();allowed=(root/'exports').resolve()
 if not allowed.is_relative_to(root) or not output.is_relative_to(allowed) or output.suffix!='.zip':raise ValueError('Export must be a ZIP inside this research root/exports')
 if output.exists() or output.with_suffix('.csv').exists():raise ValueError('Export destination already exists')
 for name in ['review-notes.json','manual-hypotheses.json']:
  primary=root/name
  if not primary.exists() and primary.with_suffix('.prev').exists():raise ValueError('Primary missing with retained previous copy; resolve local recovery before export: '+name)
 files={};captured={};absent=set()
 def add(name,required=True,verify_signed=False):
  p=(root/name).resolve()
  if not p.is_relative_to(root):raise ValueError('Export source outside research root')
  if not p.exists():
   if required:raise ValueError('Required research evidence missing: '+name)
   absent.add(name);return None
  with p.open('rb') as stream:raw=stream.read(LIMIT+1)
  if len(raw)>LIMIT:raise ValueError('Research evidence exceeds bounded size')
  obj=manual_hypotheses.loads(raw.decode('utf-8-sig'));scan(obj,name)
  if verify_signed:signed(obj)
  files[name]=raw;captured[name]=sha(raw);return obj
 candidates=add('candidates.json');research=add('research-output-cards.json',verify_signed=True);queue=add('analysis-queue.json',verify_signed=True)
 official=add('official-observations.json',False)
 for receipt in list(received_references(candidates))+list(received_references(research)):
  name=receipt['payload_file']
  if name in files:continue
  p=(root/name).resolve()
  if not p.is_relative_to(root)or not p.is_file():raise ValueError('Required received payload unavailable: '+name)
  with p.open('rb')as f:raw=f.read(1048577)
  if len(raw)!=receipt['bytes']or sha(raw)!=receipt['payload_sha256']:raise ValueError('Received payload integrity failure: '+name)
  text=raw.decode('utf-8',errors='replace')
  try:decoded=json.loads(text)
  except ValueError:decoded=text
  scan(decoded,name);files[name]=raw;captured[name]=sha(raw)
 portable_sources=check_portable_sources(lambda n:files[n],set(files))
 notes=add('review-notes.json',False) or {};public=add('research-candidate-reviews.json',False,True)
 add(decision_recovery.NAME,False);decision_recovery_count=decision_recovery.verify(lambda n:files[n],set(files))
 add('evidence-workspace.json',False)
 add('manual-hypotheses.json',False)
 add('source-ledger-catalog.json',False)
 add('source-ledger.json',False)
 add('source-model-proposals.json',False)
 add('research-chain.json',False)
 add('research-reviews.json',False)
 add('legacy-candidate-reviews.json',False)
 recovery_inventory={p.name for p in (root/'manual-editor-recovery').glob('*.json')}
 for name in sorted(recovery_inventory):
  if not re.fullmatch('[0-9a-f]{32}\.json',name):raise ValueError('Invalid recovery filename')
  add('manual-editor-recovery/'+name)
 recovery_count=editor_recovery.verify(lambda n:files[n],set(files))
 readiness=add('analysis-readiness.json',False)
 if readiness:
  for suffix in ['semantic-review','receipt','completion']:add('analysis-quality/qualified-comparison-001-'+suffix+'.json')
 result_jobs=sorted({c['source_job'] for c in research['cards']});jobs=sorted(queue.get('jobs',{}));missing=[]
 if not set(result_jobs)<=set(jobs):raise ValueError('Research card refers to a missing source job')
 for id in jobs:
  if not re.fullmatch('[0-9a-f]{64}',id):raise ValueError('Invalid source job identifier')
  job=queue.get('jobs',{}).get(id,{})
  if job.get('input_file')!='analysis-inputs/'+id+'.json':raise ValueError('Source job input path is not canonical')
  if job.get('analysis_result') and job['analysis_result']!='analysis-results/'+id+'.json':raise ValueError('Source job result path is not canonical')
  if id in result_jobs and not job.get('analysis_result'):raise ValueError('Research card result is missing')
  data=add(job['input_file'])
  if job.get('input_file_sha256') and sha(files[job['input_file']])!=job['input_file_sha256']:raise ValueError('Sealed input file bytes changed')
  payload={k:v for k,v in data.items() if k not in ['input_sha256','payload_sha256','prepared_at']};identity={k:v for k,v in payload.items() if k!='source_expires'}
  if sha(canonical(identity))!=id or data.get('input_sha256')!=id or sha(canonical(payload))!=data.get('payload_sha256'):raise ValueError('Sealed input integrity mismatch')
  if job.get('analysis_result'):
   result=add(job['analysis_result'])
   if result.get('model_output',{}).get('source_job')!=id:raise ValueError('Result/input attribution mismatch')
   add('analysis-results/'+id+'-metrics.json',False)
  for row in data.get('observations',[]):
   for key in ['response_sha256','context_response_sha256','answer_response_sha256']:
    if row.get(key):missing.append({'evidence_id':row['evidence_id'],'job':id,'raw_sha256':row[key],'raw_bytes_exported':False})
 for card in research['cards']:
  follow=card.get('public_validation',{}).get('followup_evidence')
  if follow:
   name=follow['file']
   if not re.fullmatch(r'research-followups/[0-9a-f]{24}-(?:static-review|acceptance-plan)\.json',name):raise ValueError('Invalid follow-up path')
   add(name)
   if sha(files[name])!=follow['sha256']:raise ValueError('Follow-up evidence hash mismatch')
 history=add('observation-index.json',False,True)
 if history:
  for id in history.get('snapshots',[]):
   if not re.fullmatch('[0-9a-f]{64}',id):raise ValueError('Invalid observation snapshot identifier')
   snapshot=add('observation-snapshots/'+id+'.json',True,True)
   if snapshot.get('integrity_sha256')!=id:raise ValueError('Snapshot identity mismatch')
  if set(history.get('snapshots',[]))!={p.stem for p in (root/'observation-snapshots').glob('*.json')}:raise ValueError('Collection snapshot inventory changed; retry export')
 lineage=add('analysis-lineage-index.json',False,True)
 lineage_inventory={p.stem for p in (root/'analysis-lineage').glob('*.json')}
 for id in sorted(lineage_inventory):
  if not re.fullmatch('[0-9a-f]{64}',id):raise ValueError('Invalid analysis lineage filename')
  add('analysis-lineage/'+id+'.json',True,True)
 attribution=add('attribution-cases/cases.json',False)
 attribution_inventory={p.name for p in (root/'attribution-cases').glob('*.json')}
 if attribution is None and attribution_inventory:raise ValueError('Attribution evidence has no case index')
 if attribution is not None:
  for case in attribution.get('cases',[]):
   id=case.get('id','')
   if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',id):raise ValueError('Invalid attribution case id')
   for key in ['catalog','output','input','response']:
    name=case.get(key,'')
    if name!=id+'-'+key+'.json':raise ValueError('Noncanonical attribution file path')
    add('attribution-cases/'+name)
  attribution_inventory={p.name for p in (root/'attribution-cases').glob('*.json')}
  if attribution_inventory!={Path(n).name for n in files if n.startswith('attribution-cases/')}:raise ValueError('Attribution inventory differs from index')
 attribution_cases=check_attribution(lambda n:files[n],set(files))
 workspace_coverage=check_workspace(lambda n:files[n],set(files))
 manual_drafts=manual_hypotheses.verify(lambda n:files[n],set(files))
 readiness_summary=analysis_readiness.verify(lambda n:files[n],set(files))
 legacy_summary=legacy_candidate_reviews.verify(lambda n:files[n],set(files))
 check_lineage(lambda n:files[n],set(files))
 # Prepared, unexecuted jobs are user work too; keep the registry and all sealed inputs byte-exact.
 def cell(v):
  text=v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,separators=(',',':'))
  return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
 stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(['record_kind','id','title','buyer_hypothesis','problem_hypothesis','solution_hypothesis','review_status','unconfirmed','source_references','direct_alternatives','owner_decision'])
 for kind,rows in [('business_candidate',candidates),('research_hypothesis',research['cards'])]:
  for c in rows:
   id=c.get('candidate_id') or c.get('research_id');sources=field_references.references(c,captured);alternatives=c.get('direct_alternatives',{});writer.writerow([cell(v) for v in [kind,id,c.get('title',''),c.get('buyer',''),c.get('problem_hypothesis',''),c.get('solution_hypothesis',''),c.get('output_review',{}).get('status',c.get('status','unknown')),c.get('missing_evidence',[]),sources,alternatives,owner_decision_projection(c,notes)]])
 if official:
  for observation in official['projections']:
   writer.writerow([cell(v)for v in ['structured_official_observation_not_raw',observation['id'],observation['vendor'],'UNVERIFIED','Structured source summary; task fit not established','','STRUCTURED_SUMMARY_NOT_RAW_DOCUMENT',observation['remaining_unknown'],{'source_url':observation['url'],'retrieved_at_utc':observation['retrieved_at_utc'],'local_observation_sha256':observation['local_observation_sha256'],'raw_spans':None},observation,{'binding':'NOT_AN_OWNER_DECISION','automatic_admission':False}]])
 for note in manual_drafts:
  source=note['source_snapshot'];writer.writerow([cell(v) for v in ['manual_hypothesis_draft',note['id'],note['title'],note.get('buyer_role','unknown'),note['interpretation'],note['next_action'],'DRAFT_UNVERIFIED',note['assumptions'],{'source_snapshot_reference':{k:v for k,v in source.items() if k!='text'},'field_role':source.get('kind'),'reported_author':source.get('author'),'author_status':'reported_metadata_not_verified_person','quote_reference':note['reference'],'meaning':'Exact stored manual reference; no person/customer independence inferred'},[],{'owner_decision':'UNCHANGED','supersedes':note.get('supersedes')}]] )
 if 'legacy-candidate-reviews.json' in files:
  wrapper=manual_hypotheses.loads(files['legacy-candidate-reviews.json']);plans=manual_hypotheses.loads(wrapper['payload_json']);current_candidates={c['candidate_id']:c for c in candidates}
  for plan in plans['reviews']:
   original=manual_hypotheses.loads(plan['candidate_snapshot_json']);matching=current_candidates.get(plan['candidate_id'])==original;assessment=plan['assessment'];refs=[{'url':r['url'],'saved_title_sha256':r['saved_title_sha256'],'original_input_scope':r['old_input_scope'],'additional_original_body_available':bool(r.get('additional_saved_original')),'additional_original_reference':{k:v for k,v in (r.get('additional_saved_original') or {}).items() if k!='text'},'additional_original_meaning':'Later saved source revision, not retroactive model input or independent person'} for r in plan['source_references']];docs=[{'url':r['url'],'body_evidence':r['body_evidence'],'task_fit':'not automatically verified','preserved_field_reference':{k:v for k,v in (r.get('preserved_snapshot') or {}).items() if k!='text'},'literal_fragments':r.get('saved_fragments',[])} for r in plan['documents']]
   writer.writerow([cell(v) for v in ['assistant_manual_acceptance_plan_not_execution',plan['candidate_id']+'@'+plan['candidate_snapshot_sha256'][:12],original['title'],'UNVERIFIED',assessment['alignment'],assessment['next_action'],'MANUAL_PLAN_ONLY_CURRENT_SNAPSHOT' if matching else 'HISTORICAL_PLAN_CANDIDATE_CHANGED',{'market_gap':assessment['market_gap'],'permission_boundary':assessment['permission_boundary']},refs,docs,{'owner_decision':'UNCHANGED; this is not an owner decision','execution':'NOT_EXECUTED'}]])
 # Owner declarations and open conditions must survive the human-facing summary too.
 review_summary_count=0
 if 'research-reviews.json' in files:
  import comparison_data
  current=comparison_data.build(root)['research_chain']
  for key,status in current['revision_reviews']['candidates'].items():
   if not status['history']:continue
   review_summary_count+=1
   writer.writerow([cell(v) for v in ['declared_revision_review_not_execution',key,'Exact research revision '+status['current_revision_sha256'],'UNKNOWN','NOT_SEMANTICALLY_VERIFIED','NO_EXECUTION_AUTHORIZATION',status['coverage'],{'unclosed_conditions':status['unclosed_conditions'],'open_questions':status.get('open_questions',[])},status['history'],{}, {'declared_choice':status['decision'],'rationale':status.get('decision_rationale'),'identity':'NOT_AUTHENTICATED','automatic_admission':False}]])
  for history in current['revision_reviews']['orphan_history']:
   review_summary_count+=1
   writer.writerow([cell(v) for v in ['historical_orphan_review_not_current',history['candidate_key'],'HISTORICAL','UNKNOWN','','','STALE_OR_ABSENT_REVISION',history['open_questions'],history,{},'NO_CURRENT_DECISION']])
 csv_bytes=stream.getvalue().encode('utf-8-sig');files['research-summary.csv']=csv_bytes
 manifest={'kind':'reveng-local-research-export','created_at':datetime.now(timezone.utc).isoformat(),'research_cards':len(research['cards']),'business_candidates':len(candidates),'source_jobs':jobs,'result_source_jobs':result_jobs,'prepared_without_result':[id for id in jobs if not queue['jobs'][id].get('analysis_result')],'analysis_registry_preserved_byte_exact':True,'meaning':'Evidence and hypotheses snapshot only; export is not validation, owner approval, automatic import or authorization to execute prepared jobs','raw_source_policy':'Raw HTML/scripts/config/logs/model files are excluded. Exact sealed inputs, normalized source text, URLs, capture times, source hashes, model results and research reviews are retained. Raw hashes below identify evidence not included as bytes.','raw_source_references':missing,'csv_safety':'Summary text formula prefixes are escaped; exact JSON source files remain unchanged. No revenue/market scores are asserted by the summary.','files':[{'path':name,'sha256':sha(raw),'bytes':len(raw)} for name,raw in sorted(files.items())]}
 manifest['csv_source_reference_schema']='reveng-exact-field-references-v1'
 manifest['csv_source_reference_meaning']='Container-scoped E-ID, actual source field/hash, separate question/answer author metadata, codepoint quote ranges; no independent people inferred'
 manifest['incomplete_editor_recovery_files']=recovery_count
 manifest['incomplete_editor_recovery_meaning']='Unsaved editor work, possibly incomplete/stale source; not committed hypotheses, source proof, model output or execution'
 manifest['legacy_candidate_reviews']=legacy_summary
 manifest['portable_source_evidence']=portable_sources
 manifest['analysis_readiness']=readiness_summary
 manifest['manual_hypothesis_drafts']=len(manual_drafts)
 manifest['decision_recovery_entries']=decision_recovery_count
 manifest['decision_recovery_meaning']='Separate protected or pending copy, not current owner authority; conflicts require explicit reconciliation, no automatic merge'
 manifest['declared_revision_review_summary_rows']=review_summary_count
 manifest['manual_meaning']='Local manual input, source-bound unverified drafts; not model output, customer proof, business admission or owner decision'
 manifest['evidence_workspace_coverage']=workspace_coverage
 manifest['analysis_lineage_events']=len(lineage_inventory)
 manifest['attribution_cases']=attribution_cases
 manifest['attribution_meaning']='Exact historical input/catalog/response/output preserved; literal provenance is not semantic validation or demand evidence'
 if sum(len(r) for r in files.values())>128*1024*1024:raise ValueError('Export exceeds bounded total size')
 output.parent.mkdir(parents=True,exist_ok=True);temp=output.parent/('.export-'+uuid.uuid4().hex+'.tmp');csv_temp=output.parent/('.summary-'+uuid.uuid4().hex+'.tmp');csv_warning=None
 try:
  with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
   for name,raw in files.items():z.writestr(name,raw)
   z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
  verify(temp)
  for name,digest in captured.items():
   p=(root/name).resolve()
   if not p.is_relative_to(root):raise ValueError('Research path changed during export')
   with p.open('rb') as stream:current=stream.read(LIMIT+1)
   if len(current)>LIMIT or sha(current)!=digest:raise ValueError('Research changed during export; retry after the current update completes')
  if any((root/name).exists() for name in absent):raise ValueError('Research changed during export; optional evidence appeared during capture')
  if lineage_inventory!={p.stem for p in (root/'analysis-lineage').glob('*.json')}:raise ValueError('Analysis lineage changed during export; retry')
  if attribution_inventory!={p.name for p in (root/'attribution-cases').glob('*.json')}:raise ValueError('Attribution inventory changed during export')
  if recovery_inventory!={p.name for p in (root/'manual-editor-recovery').glob('*.json')}:raise ValueError('Editor recovery changed during export; retry')
  # ZIP is the authoritative, verified snapshot and already contains the CSV.
  # A failed optional loose summary must not turn a committed valid export into failure.
  _publish_no_replace(temp,output)
  try:
   with csv_temp.open('xb')as stream:stream.write(csv_bytes);stream.flush();os.fsync(stream.fileno())
   _publish_no_replace(csv_temp,output.with_suffix('.csv'))
  except OSError as ex:csv_warning=type(ex).__name__+': '+str(ex)
 finally:
  if temp.exists():temp.unlink()
  if csv_temp.exists():csv_temp.unlink()
 return {'status':'exported','zip':str(output),'csv':None if csv_warning else str(output.with_suffix('.csv')),'csv_warning':csv_warning,'summary_in_verified_zip':True,'sha256':sha(output.read_bytes()),'files':len(files)+1,'research_cards':len(research['cards']),'business_candidates':len(candidates),'model_calls':0,'network_calls':0}
def verify(path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>100:raise ValueError('Invalid or oversized export inventory')
  for name in names:
   p=PurePosixPath(name)
   if p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('Unsafe archive path')
  if sum(i.file_size for i in z.infolist())>128*1024*1024:raise ValueError('Oversized export')
  manifest=manual_hypotheses.loads(z.read('manifest.json'));expected={f['path']:f for f in manifest['files']}
  if manifest.get('kind')!='reveng-local-research-export':raise ValueError('Unsupported export kind')
  for name in expected:
   if name=='official-observations.json'or re.fullmatch(r'buyer-source-payloads/[0-9a-f]{64}\.raw',name):continue
   if re.fullmatch(r'manual-editor-recovery/[0-9a-f]{32}\.json',name):continue
   if name in ['candidates.json','research-output-cards.json','candidates.json','analysis-queue.json','review-notes.json',decision_recovery.NAME,'research-candidate-reviews.json','research-summary.csv','observation-index.json','analysis-lineage-index.json','attribution-cases/cases.json','evidence-workspace.json','manual-hypotheses.json','analysis-readiness.json','legacy-candidate-reviews.json','source-ledger-catalog.json','source-ledger.json','source-model-proposals.json','research-chain.json','research-reviews.json']:continue
   if re.fullmatch(r'analysis-inputs/[0-9a-f]{64}\.json|analysis-results/[0-9a-f]{64}(?:-metrics)?\.json|research-followups/[0-9a-f]{24}-(?:static-review|acceptance-plan)\.json|observation-snapshots/[0-9a-f]{64}\.json|analysis-lineage/[0-9a-f]{64}\.json',name):continue
   if re.fullmatch(r'attribution-cases/[a-z0-9][a-z0-9-]{0,63}-(?:catalog|output|input|response)\.json',name):continue
   if re.fullmatch(r'analysis-quality/qualified-comparison-001-(?:semantic-review|receipt|completion)\.json',name):continue
   raise ValueError('Non-research file in export inventory')
  if set(names)!=set(expected)|{'manifest.json'}:raise ValueError('Unlisted export content')
  for name,info in expected.items():
   raw=z.read(name)
   if len(raw)!=info['bytes'] or sha(raw)!=info['sha256']:raise ValueError('Export checksum mismatch: '+name)
   if name.endswith('.json'):
    data=manual_hypotheses.loads(raw.decode('utf-8-sig'));scan(data,name)
    if name=='observation-index.json' or name.startswith('observation-snapshots/'):
     signed(data)
     if name.startswith('observation-snapshots/') and PurePosixPath(name).stem!=data.get('integrity_sha256'):raise ValueError('Snapshot identity mismatch')
  recovery_count=editor_recovery.verify(z.read,set(names))
  if 'portable_source_evidence'in manifest:
   if manifest['portable_source_evidence']!=check_portable_sources(z.read,set(names)):raise ValueError('Portable source evidence inventory mismatch')
  elif 'official-observations.json'in names or any(n.startswith('buyer-source-payloads/')for n in names):raise ValueError('Portable source evidence manifest missing')
  if manifest.get('decision_recovery_entries',0)!=decision_recovery.verify(z.read,set(names)):raise ValueError('Decision recovery export count mismatch')
  if manifest.get('incomplete_editor_recovery_files',0)!=recovery_count:raise ValueError('Editor recovery count mismatch')
  check_lineage(z.read,set(names))
  check_workspace(z.read,set(names))
  manual_drafts=manual_hypotheses.verify(z.read,set(names))
  readiness_summary=analysis_readiness.verify(z.read,set(names))
  legacy_summary=legacy_candidate_reviews.verify(z.read,set(names))
  if manifest.get('legacy_candidate_reviews')!=legacy_summary:raise ValueError('Legacy manual review export summary mismatch')
  if manifest.get('analysis_readiness')!=readiness_summary:raise ValueError('Readiness export summary mismatch')
  if manifest.get('manual_hypothesis_drafts',0)!=len(manual_drafts):raise ValueError('Manual draft count mismatch')
  source_ledger.verify_portable(z.read,set(names))
  import research_chain
  research_chain.verify_portable(z.read,set(names))
  count=check_attribution(z.read,set(names))
  if manifest.get('attribution_cases',0)!=count:raise ValueError('Attribution count mismatch')
 return manifest
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 try:print(json.dumps(export(args.root,args.output),ensure_ascii=True))
 except Exception as ex:print(json.dumps({'status':'failed','error':type(ex).__name__+': '+str(ex)}));raise SystemExit(1)
