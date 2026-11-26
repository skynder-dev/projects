"""Disabled file-only executor boundary. No process, service, credential or model code."""
from pathlib import Path
import json,hashlib,datetime
from response_diagnostics import strict_json
LIMIT=8*1024*1024
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()
def read(path):
 if str(path).startswith(('\\\\','//')):raise ValueError('Only local exchange files are supported; no network file lookup')
 path=Path(path)
 if path.stat().st_size>LIMIT:raise ValueError('Local exchange file exceeds8MiB cap')
 with path.open('rb') as file:raw=file.read(LIMIT+1)
 if len(raw)>LIMIT:raise ValueError('Local exchange file exceeds8MiB cap')
 return raw,strict_json(raw.decode('utf-8-sig'))
def write_new(path,raw):
 with Path(path).open('xb') as file:file.write(raw)
def inline_schema(schema):
 if isinstance(schema,dict):
  if '$ref' in schema or '$dynamicRef' in schema:raise ValueError('Only inline schemas are allowed; no external/local reference resolution or network lookup')
  for value in schema.values():inline_schema(value)
 elif isinstance(schema,list):
  for value in schema:inline_schema(value)
def prepare(folder,request_path,catalog_path):
 folder=Path(folder)
 if folder.exists():raise ValueError('Exchange folder already exists; do not overwrite research')
 request_raw,request=read(request_path);catalog_raw,catalog=read(catalog_path)
 if not isinstance(request,dict) or not isinstance(request.get('messages'),list) or not isinstance(request.get('format'),dict):raise ValueError('Exact existing messages/schema required')
 inline_schema(request['format'])
 try:import jsonschema
 except ImportError:raise RuntimeError('JSONSchema validator unavailable; use an already prepared environment. No automatic installation.')
 jsonschema.Draft202012Validator.check_schema(request['format'])
 folder.mkdir(parents=True)
 write_new(folder/'task-request.json',request_raw);write_new(folder/'source-catalog.json',catalog_raw)
 envelope={'schema':'reveng-executor-exchange-v1','task':'source-message-index','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{'task-request.json':digest(request_raw),'source-catalog.json':digest(catalog_raw)},'schema_sha256':digest(canonical(request['format'])),'execution_disabled':True,'executor_selected':None,'authorization':None,'no_automatic_downloads':True,'no_automatic_retry':True,'source_dates_renewed':False,'semantic_gate':'REQUIRED_SEPARATELY; shape is not entailment','automatic_admission':False,'owner_mutations_allowed':False,'current_configuration_readiness':'FAILED_SEMANTIC_ATTRIBUTION; no more prompt variants','budget_if_separately_authorized':{'CPU_threads':2,'CPU_hard_percent':10,'private_GiB':10,'GPU':0,'wall_seconds':900,'output_tokens':1800,'paid_services_allowed':False},'output_protocol':{'binding':'request_integrity_sha256 must equal this envelope integrity_sha256','file':'executor-result.json','finish_reason':'stop','task_output':'Exact task JSON matching task-request.json.format','provider_raw_capture':'Optional local raw bytes; preserve, never execute','runtime_receipt':'Reported metadata, not automatically trusted; actual runtime proof required separately'}}
 envelope['integrity_sha256']=digest(canonical(envelope));write_new(folder/'exchange.json',canonical(envelope))
 return envelope
def inspect_result(folder,result_path):
 folder=Path(folder);_,envelope=read(folder/'exchange.json');claim=envelope.get('integrity_sha256');base={k:v for k,v in envelope.items() if k!='integrity_sha256'}
 if digest(canonical(base))!=claim:raise ValueError('Exchange envelope integrity mismatch')
 for name,expected in envelope['files'].items():
  if name not in ['task-request.json','source-catalog.json']:raise ValueError('Unexpected/nonlocal exchange file')
  raw,_=read(folder/name)
  if digest(raw)!=expected:raise ValueError('Exchange input changed: '+name)
 _,request=read(folder/'task-request.json');raw,result=read(result_path)
 if result.get('request_integrity_sha256')!=claim:raise ValueError('Executor output belongs to another request')
 if result.get('finish_reason')!='stop':raise ValueError('Incomplete executor output retained; no repair or automatic retry')
 try:import jsonschema
 except ImportError:raise RuntimeError('JSONSchema validator unavailable; cannot confirm structure. No automatic installation.')
 inline_schema(request['format']);jsonschema.Draft202012Validator(request['format']).validate(result.get('task_output'))
 return {'status':'STRUCTURE_ONLY_SEMANTIC_REVIEW_REQUIRED','request_integrity_sha256':claim,'result_file_sha256':digest(raw),'shape_valid':True,'semantic_entailment_verified':False,'source_field_attribution_verified':False,'runtime_receipt':'not automatically trusted','execution_authorized_by_hash':False,'execution_was_enabled':False,'automatic_admission':False,'ready_for_stage2':False,'owner_changes':0,'model_calls':0,'network_calls':0,'meaning':'A valid or existing executor result is data only. This boundary never starts an executor, accepts its claims as verified, or changes owner decisions.'}
