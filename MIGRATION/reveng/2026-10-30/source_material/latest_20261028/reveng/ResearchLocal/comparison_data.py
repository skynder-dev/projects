"""Offline source-bound candidate comparison. No scoring, winning, execution or source collection."""
from pathlib import Path
import argparse,json,hashlib,re,os
import field_references,evidence_workspace,legacy_candidate_reviews,manual_hypotheses,price_experiments
LIMIT=8*1024*1024
def sha(raw):return hashlib.sha256(raw).hexdigest()
def build(root,include_chain=True):
 root=Path(root).resolve();inputs={};read={};raws={}
 marker=root/'.readonly-research-preview';historical=json.loads(marker.read_text(encoding='utf-8'))if marker.exists()else{}
 legacy_raw_scope=marker.exists()and historical.get('portable_source_evidence',{'schema':'legacy_metadata_only'}).get('schema')=='legacy_metadata_only'
 def fetch(name,optional=False):
  if name not in ['official-observations.json','candidates.json','research-output-cards.json','analysis-queue.json','manual-hypotheses.json','legacy-candidate-reviews.json','research-candidate-reviews.json','attribution-cases/cases.json','observation-index.json'] and not re.fullmatch(r'analysis-inputs/[0-9a-f]{64}\.json|observation-snapshots/[0-9a-f]{64}\.json|attribution-cases/[a-z0-9][a-z0-9-]{0,63}-(?:catalog|output|input|response)\.json',name):raise ValueError('Unexpected comparison input')
  if name in read:return read[name]
  path=(root/name).resolve()
  if not path.is_relative_to(root):raise ValueError('Comparison input outside root')
  if not path.exists() and optional:inputs[name]=None;return None
  raw=path.read_bytes()
  if len(raw)>LIMIT:raise ValueError('Comparison input exceeds8MiB')
  inputs[name]=sha(raw);raws[name]=raw;obj=json.loads(raw.decode('utf-8-sig'));read[name]=obj;return obj
 def raw(name):fetch(name);return raws[name]
 available={n for n in ['official-observations.json','candidates.json','research-output-cards.json','analysis-queue.json','manual-hypotheses.json','legacy-candidate-reviews.json','research-candidate-reviews.json','attribution-cases/cases.json','observation-index.json'] if (root/n).is_file()}
 for folder in ['analysis-inputs','observation-snapshots','attribution-cases']:
  for p in (root/folder).glob('*.json'):available.add(p.relative_to(root).as_posix())
 legacy=fetch('candidates.json');research=fetch('research-output-cards.json');evidence_workspace.signed(research);rows=[]
 if (root/'official-observations.json').exists():
  import official_observations
  official_observations.verify_projection(fetch('official-observations.json'))
 import research_export
 for receipt in list(research_export.received_references(legacy))+list(research_export.received_references(research)):
  name=receipt['payload_file'];path=(root/name).resolve()
  if legacy_raw_scope and not path.exists():inputs[name]=None;continue
  if not path.is_relative_to(root)or not path.is_file()or path.stat().st_size!=receipt['bytes']:raise ValueError('Comparison received payload missing or changed')
  raw_bytes=path.read_bytes()
  if sha(raw_bytes)!=receipt['payload_sha256']:raise ValueError('Comparison received payload SHA256 changed')
  inputs[name]=sha(raw_bytes)
 if not (root/'research-candidate-reviews.json').exists():fetch('research-candidate-reviews.json',True) # pin absence without changing historical present-input review snapshots
 if not isinstance(legacy,list) or not isinstance(research.get('cards'),list):raise ValueError('Invalid candidate arrays')
 plans=fetch('legacy-candidate-reviews.json',True);plans_by_id={}
 if plans:
  p=plans['payload_json']
  if sha(p.encode())!=plans['payload_sha256']:raise ValueError('Legacy plan hash mismatch')
  plans_by_id={r['candidate_id']:r for r in json.loads(p)['reviews']}
  legacy_candidate_reviews.verify(raw,available)
 for kind,cards in [('legacy_hypothesis',legacy),('model_hypothesis',research['cards'])]:
  for c in cards:
   id=c.get('research_id') or c['candidate_id'];job=c.get('source_job')
   if job:
    sealed=fetch('analysis-inputs/'+job+'.json');payload={k:v for k,v in sealed.items() if k not in ['input_sha256','payload_sha256','prepared_at']};identity={k:v for k,v in payload.items() if k!='source_expires'}
    if sha(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode())!=sealed.get('payload_sha256') or sha(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode())!=job or sealed.get('input_sha256')!=job:raise ValueError('Sealed input integrity mismatch')
    originals=sealed['observations']
    byid={r['evidence_id']:r for r in originals}
    if len(byid)!=len(originals):raise ValueError('Ambiguous E-ID within sealed source container')
    if any(r!=byid.get(r['evidence_id']) for r in c.get('observed_basis',[])):raise ValueError('Card/source input field mismatch')
   refs=field_references.references(c,inputs);snapshot=json.loads(plans_by_id[c['candidate_id']]['candidate_snapshot_json']) if kind=='legacy_hypothesis' and c['candidate_id'] in plans_by_id else None;plan=plans_by_id.get(c.get('candidate_id')) if snapshot==c else None
   rows.append({**price_experiments.comparison_fields(c),'id':id,'kind':kind,'title':c.get('title',''),'buyer_hypothesis':c.get('buyer'),'problem_hypothesis':c.get('problem_hypothesis'),'solution_hypothesis':c.get('solution_hypothesis'),'unverified_old_validation_proposal':c.get('validation_step'),'historical_status_not_approval':c.get('status'),'unverified_saved_alternatives':{k:c.get(k) for k in ['alternatives_and_limits','direct_alternatives']},'missing_evidence':c.get('missing_evidence',[]),'risks':c.get('risks',[]),'assistant_source_review':c.get('assistant_source_review'),'source_references':refs,'source_texts':[{**r,'text':(next(o for o in c['observed_basis'] if o['evidence_id']==r['evidence_id_local_to_container'] and o.get('url')==r['question_url'] and o.get('source')==r['source']).get(r['container_field']) or '')} for r in refs],'model_review':c.get('output_review'),'current_manual_plan':plan['assessment'] if plan else None,'plan_status':'CURRENT_SNAPSHOT_MANUAL_PLAN_NOT_EXECUTED' if plan else 'NO_CURRENT_MANUAL_PLAN','next_permitted_local_action':'Read the displayed saved fields and literal claims; compare the actual task and qualifications; write a source-bound manual hypothesis or acceptance criteria. No model, GET, device/account action, outreach, publication or payment is authorized by this comparison.','verified_customer':'UNKNOWN','market_advantage':'UNKNOWN','winner':False,'auto_admission':False})
 # Committed manual notes have their own path; incomplete editor recovery never enters comparison.
 manual_notes_error=None
 try:
  notes=fetch('manual-hypotheses.json',True)
  if notes is None and(root/'manual-hypotheses.prev').exists():raise ValueError('Manual primary missing; previous copy retained locally, not current manual records')
  if notes:
   manual_hypotheses.verify(raw,available)
   payload=notes['payload_json']
   if sha(payload.encode())!=notes['payload_sha256']:raise ValueError('Manual root hash mismatch')
   for wrapper in json.loads(payload)['notes']:
    p=wrapper['payload_json']
    if sha(p.encode())!=wrapper['payload_sha256']:raise ValueError('Manual note hash mismatch')
    note=json.loads(p);rows.append({'id':wrapper['payload_sha256'],'kind':'manual_hypothesis','title':note['title'],'buyer_hypothesis':note.get('buyer_role'),'problem_hypothesis':note['interpretation'],'solution_hypothesis':None,'missing_evidence':[note['assumptions']],'source_references':[{'source_snapshot':note['source_snapshot'],'reference':note['reference']}],'source_texts':[{'source_snapshot':note['source_snapshot'],'reference':note['reference'],'text':note['source_snapshot']['text']}],'current_manual_plan':{k:note[k] for k in ['next_action','success','failure']},'plan_status':'USER_MANUAL_DRAFT_UNVERIFIED','next_permitted_local_action':'Review exact saved source and criteria; no external action or model run authorized','verified_customer':'UNKNOWN','market_advantage':'UNKNOWN','winner':False,'auto_admission':False})
 except (ValueError,KeyError,TypeError,AttributeError,OSError) as ex:
  manual_notes_error=type(ex).__name__+': '+str(ex);rows=[r for r in rows if r['kind']!='manual_hypothesis']
 rows.sort(key=lambda r:(r['title'].casefold(),r['kind'],r['id']))
 chain=None
 if include_chain:
  import research_chain
  chain=research_chain.build(root,{'inputs':dict(inputs),'rows':rows});inputs.update(chain['inputs'])
  byclaim={c['claim_id']:c for c in chain['claims']}
  for row in rows:
   link=chain['candidate_links'].get(row['kind']+':'+row['id'])
   row['research_chain']=link
   row['source_condition_annotations']=[byclaim[id] for id in link['claim_ids']] if link else []

 assessments={}
 if include_chain:
  graph=evidence_workspace.build(root)
  for name,expected in graph['inputs'].items():
   if name not in inputs:fetch(name,True)
   if inputs.get(name)!=expected:raise ValueError('Alternative assessment source revision differs from comparison')
  assessments={r['kind']+':'+r['id']:[a for a in graph['analyses'] if r['id'] in a.get('card_ids',[])] for r in rows}
 for name,expected in inputs.items():
  path=root/name
  if expected is None and path.exists() or expected is not None and sha(path.read_bytes())!=expected:raise ValueError('Comparison input changed during capture')
 marker=root/'.readonly-research-preview'
 scope=json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else None
 import decision_recovery
 owner_preferences=decision_recovery.preference_snapshot(root,legacy,'HISTORICAL_READ_ONLY_ARCHIVE' if scope else 'LOCAL_CURRENT_RESEARCH')
 return {'owner_preferences':owner_preferences,'schema':'reveng-evidence-comparison-v1','workspace_scope':'HISTORICAL_READ_ONLY_ARCHIVE' if scope else 'LOCAL_CURRENT_RESEARCH','archive_sha256':scope.get('archive_sha256') if scope else None,'inputs':inputs,'rows':rows,'ordering':'Title/kind/id only; never score, revenue or recommendation','manual_notes_error':manual_notes_error,'saved_alternative_assessments':assessments,'alternative_assessment_meaning':'Saved assistant source review, not new AI output, semantic proof or tested capability','research_chain':chain,'winner_selected':False,'verified_market_priority':None,'auto_admission':False,'network_calls':0,'model_calls':0}
def _atomic_bytes(path,raw):
 import tempfile
 fd,name=tempfile.mkstemp(dir=path.parent,prefix='.comparison-',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
def save(root,data,preserve_chain=False):
 root=Path(root);payload=json.dumps(data,ensure_ascii=False,sort_keys=True);raw=json.dumps({'payload_json':payload,'payload_sha256':sha(payload.encode())},ensure_ascii=False).encode()
 writes={}
 if data.get('research_chain') is not None and not preserve_chain and not (root/'.readonly-research-preview').exists():
  import source_ledger
  writes[root/'research-chain.json']=source_ledger.canonical(source_ledger.seal(data['research_chain']))
 writes[root/'comparison-state.json']=raw
 if any(len(b)>8*1024*1024 for b in writes.values()):raise ValueError('Derived comparison exceeds8MiB; previous state preserved')
 # OS lock is released even if our process is interrupted; retained lock file is not source data.
 with (root/'.comparison-write.lock').open('a+b') as gate:
  gate.seek(0,2)
  if gate.tell()==0:gate.write(b'0');gate.flush()
  gate.seek(0)
  if os.name=='nt':
   import msvcrt
   msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
  else:
   import fcntl
   fcntl.flock(gate.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  previous={p:p.read_bytes() if p.exists() else None for p in writes};committed=[]
  try:
   for path,content in writes.items():_atomic_bytes(path,content);committed.append(path)
  except Exception:
   for path in reversed(committed):
    # Never undo a manual or external edit made after our own replacement.
    if not path.exists() or path.read_bytes()!=writes[path]:continue
    if previous[path] is None:path.unlink()
    else:_atomic_bytes(path,previous[path])
   raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();d=build(a.root)
 if a.verify:
  import source_ledger
  stored=source_ledger.unseal(source_ledger.read(a.root/'comparison-state.json')[1])
  if stored!=d:raise ValueError('Stored comparison/chain differs from exact current source-derived state')
 else:save(a.root,d)
 print(json.dumps({'status':'VERIFIED_READ_ONLY_COMPARISON' if a.verify else 'BUILT_READ_ONLY_COMPARISON','rows':len(d['rows']),'network_calls':0,'model_calls':0}))
