"""Prepared analysis inputs, not generated ideas or authorization to execute a model."""
import json,time,re,shutil
import analysis_lineage
from pathlib import Path
def inspect_input(m,root,path):
 data=json.loads(path.read_text(encoding='utf-8'));payload={k:v for k,v in data.items() if k not in ['input_sha256','payload_sha256','prepared_at']}
 import quote_contract
 quote_contract.index_observations(data.get('observations'))
 identity={k:v for k,v in payload.items() if k!='source_expires'}
 id=m.sha(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode())
 if id!=path.stem or id!=data.get('input_sha256') or m.sha(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode())!=data.get('payload_sha256'):raise ValueError('Prepared input integrity mismatch')
 return id,{'status':'awaiting_authorized_executor' if data.get('source_expires',0)>time.time() else 'stale_sources','input_file':path.relative_to(root).as_posix(),'input_sha256':id,'input_file_sha256':m.sha(path.read_bytes()),'source_expires':data.get('source_expires',0),'prepared_at':data.get('prepared_at'),'observations':len(data.get('observations',[])),'source_errors':len(data.get('source_errors',[])),'model_calls':0}
def rebuild_queue(m,root,backup=None):
 jobs={};invalid=[]
 for candidate in (root/'analysis-inputs').glob('*.json'):
  if not re.fullmatch('[0-9a-f]{64}',candidate.stem):continue
  try:
   id,job=inspect_input(m,root,candidate)
   result=root/'analysis-results'/(id+'.json')
   if result.exists():
    # A saved result must never silently become a new pending model request.
    job.update(status='completed_needs_review',analysis_result=result.relative_to(root).as_posix(),result_file_sha256=m.sha(result.read_bytes()),model_calls=None,recovered_at=m.now(),execution_verified=False)
    try:
     record=json.loads(result.read_text(encoding='utf-8'));model=record['model_output']
     if model.get('source_job')!=id:raise ValueError('Result belongs to a different input job')
     original=json.loads(candidate.read_text(encoding='utf-8'));fields=set(m.schema([])['properties']['hypotheses']['items']['properties'])
     m.validate_cards({'hypotheses':[{k:c[k] for k in fields if k in c} for c in model['hypotheses']]},original['observations'])
     job['recovered_result_structurally_valid']=True
    except (ValueError,KeyError,TypeError) as ex:job.update(recovered_result_structurally_valid=False,recovery_warning=str(ex))
    # Output correctness and the fact of one completed model attempt are separate.
    metrics=root/'analysis-results'/(id+'-metrics.json')
    if metrics.exists():
     try:
      proof=json.loads(metrics.read_text(encoding='utf-8'));recognized=proof.get('status') in ['VALIDATED_MODEL_OUTPUT','MODEL_OUTPUT_NEEDS_REVIEW']
      if proof.get('source_job')!=id or proof.get('model_calls')!=1 or not recognized:raise ValueError('Unrecognized/misattributed execution receipt')
      job.update(analysis_metrics=metrics.relative_to(root).as_posix(),model_calls=1,execution_verified=True,execution_receipt_status=proof['status'],output_completion_evidenced=proof.get('finish_reason')=='stop' or proof['status']=='VALIDATED_MODEL_OUTPUT')
     except (ValueError,KeyError,TypeError) as ex:job['execution_receipt_warning']=str(ex)
   jobs[id]=job
  except (ValueError,KeyError,TypeError):invalid.append(candidate.name)
 analysis_lineage.apply(m,root,jobs)
 return {'jobs':jobs,'recovery':{'backup':backup,'valid_inputs':len(jobs),'invalid_inputs':invalid,'model_calls':0}}
def load_queue(m,root,recover=False):
 path=root/'analysis-queue.json'
 if not path.exists():return rebuild_queue(m,root) if recover else {'jobs':{}}
 try:
  queue=json.loads(path.read_text(encoding='utf-8'));claim=queue.pop('integrity_sha256',None)
  if claim!=m.sha(json.dumps(queue,sort_keys=True,ensure_ascii=False).encode()):raise ValueError('Analysis queue integrity mismatch')
  analysis_lineage.apply(m,root,queue['jobs']);return queue
 except (ValueError,KeyError,TypeError):
  if not recover:raise
  backup=root/('analysis-queue.invalid-'+str(time.time_ns())+'.json');shutil.copyfile(path,backup)
  return rebuild_queue(m,root,backup.name)
def prepare(m,root,run,observations,prices,errors,expiry,request):
 payload={'schema':'reveng-prepared-analysis','observations':observations,'public_price_records':prices,'source_errors':errors,'request':request,'source_expires':expiry,'execution_policy':'await explicit authorized executor; tokenize full enriched input before dispatch, never silently truncate; no automatic model dispatch','preflight':{'context_sizing_required':True,'available_context_chars':sum(len(r.get('context_text') or r.get('excerpt') or '')+len(r.get('answer_text') or '') for r in observations),'truncated_source_ids':[r['evidence_id'] for r in observations if r.get('context_truncated') or r.get('answer_text_truncated')],'quote_contract':'Exact fragments of supplied observed_text, bound to E-ID/source_field/text hash; no semantic truth inferred from a quote match'},'meaning':'Observed source records only. No AI hypotheses, demand, buyers or revenue established.'}
 identity={k:v for k,v in payload.items() if k!='source_expires'}
 id=m.sha(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode());input_path=root/'analysis-inputs'/(id+'.json')
 path=root/'analysis-queue.json';queue=load_queue(m,root,recover=True)
 if not input_path.exists():
  saved=dict(payload,input_sha256=id,payload_sha256=m.sha(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()),prepared_at=m.now())
  try:analysis_lineage.write_new_json(input_path,saved)
  except FileExistsError:pass # Another identical preparation won; inspect, never overwrite.
 _,sealed_entry=inspect_input(m,root,input_path);saved=json.loads(input_path.read_text(encoding='utf-8'))
 for job in queue['jobs'].values():
  if job.get('status') in ['awaiting_authorized_executor','stale_sources'] and job.get('source_expires',0)<=time.time():job['status']='stale_sources'
 previous=queue['jobs'].get(id,{})
 entry=dict(previous);entry.update(sealed_entry)
 if (root/'analysis-results'/(id+'.json')).exists():
  entry.update(rebuild_queue(m,root)['jobs'][id])
  if previous.get('status')=='completed_verified':entry['status']='completed_verified'
 elif previous.get('status') in ['completed_verified','completed_needs_review']:raise ValueError('Completed job lost its result; recover artifacts instead of preparing a repeat')
 elif previous.get('status') not in [None,'awaiting_authorized_executor','stale_sources']:
  entry['status']=previous['status'];entry['model_calls']=previous.get('model_calls',0)
 queue['jobs'][id]=entry;analysis_lineage.apply(m,root,queue['jobs'])
 queue['updated_at']=m.now();queue['integrity_sha256']=m.sha(json.dumps(queue,sort_keys=True,ensure_ascii=False).encode());m.dump(path,queue)
 shutil.copyfile(input_path,run/'analysis-input.json')
 return id

def assert_dispatchable(m,root,id):
 """Read-only preflight for a future authorized executor. Never dispatches a model."""
 if not re.fullmatch('[0-9a-f]{64}',id):raise ValueError('Invalid analysis identity')
 queue=load_queue(m,root,recover=True);job=queue['jobs'].get(id,{})
 if (root/'analysis-results'/(id+'.json')).exists() or (root/'analysis-results'/(id+'-metrics.json')).exists():raise ValueError('Saved attempt/result exists; repeat dispatch refused')
 if job.get('status')!='awaiting_authorized_executor' or job.get('superseded_by'):raise ValueError('Analysis is completed, held, superseded or stale; no dispatch')
 _,entry=inspect_input(m,root,root/'analysis-inputs'/(id+'.json'))
 if entry['status']!='awaiting_authorized_executor':raise ValueError('Cache TTL expired; no implicit historical dispatch')
 return entry
