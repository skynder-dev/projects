"""Bounded saved-response diagnostics only; never repairs, imports or runs a model."""
from pathlib import Path
import hashlib,json,os,re,shutil,tempfile
from datetime import datetime,timezone

LIMIT=8*1024*1024

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def strict_json(raw):
 def pairs(items):
  value={}
  for key,item in items:
   if key in value:raise ValueError('Duplicate JSON key: '+key)
   value[key]=item
  return value
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Non-JSON constant')))

class RejectedResponse(ValueError):
 def __init__(self,diagnostic):
  self.diagnostic=diagnostic
  super().__init__(diagnostic['message'])

def inspect(raw,max_output_tokens=None,context_tokens=None):
 if type(raw)is not bytes or len(raw)>LIMIT:raise ValueError('Response must be original bytes, at most8MiB')
 d={'schema':'reveng-response-diagnostic-v1','reason_code':None,'message':None,'raw_response_sha256':sha(raw),'raw_response_bytes':len(raw),'finish_reason':None,'output_tokens':None,'prompt_tokens':None,'configured_max_output_tokens':max_output_tokens,'configured_context_tokens':context_tokens,'eligible_for_structure_validation':False,'research_imported':False,'automatic_admission':False,'semantic_PASS':False,'model_calls':0}
 try:value=strict_json(raw.decode('utf-8-sig'))
 except (ValueError,UnicodeError) as ex:
  d.update(reason_code='MALFORMED_RESPONSE_JSON',message='Saved response is not valid JSON; no complete research was imported.',parse_error=str(ex));return d
 if type(value)is not dict:
  d.update(reason_code='INVALID_RESPONSE_SHAPE',message='Saved response must be a JSON object; not imported.');return d
 if 'choices' not in value:
  d.update(reason_code='STRUCTURE_ONLY_NO_RUNTIME_RECEIPT',message='Structured saved content has no runtime completion receipt; exact validation and semantic review are still required.',eligible_for_structure_validation=True);return d
 choices=value['choices']
 if type(choices)is not list or len(choices)!=1 or type(choices[0])is not dict:
  d.update(reason_code='INVALID_NATIVE_ENVELOPE',message='Expected exactly one saved native choice; not imported.');return d
 choice=choices[0];finish=choice.get('finish_reason');d['finish_reason']=finish
 usage=value.get('usage') or {}
 if type(usage)is dict:
  for name,key in [('output_tokens','completion_tokens'),('prompt_tokens','prompt_tokens')]:
   n=usage.get(key)
   if type(n)is int and n>=0:d[name]=n
 message=choice.get('message');content=message.get('content') if type(message)is dict else None
 d['content_bytes']=len(content.encode('utf-8')) if type(content)is str else None
 if finish=='length':
  d.update(reason_code='TOKEN_LENGTH_LIMIT',message='Token length limit reached (finish_reason=length'+('; output_tokens='+str(d['output_tokens']) if d['output_tokens']is not None else '')+'). The response is incomplete and was NOT imported.')
  if type(max_output_tokens)is int and max_output_tokens>0 and d['output_tokens']is not None and d['output_tokens']>=max_output_tokens:
   d['confirmed_output_budget_exhausted']=True
  else:d['confirmed_output_budget_exhausted']=None
 elif finish!='stop':
  d.update(reason_code='NATIVE_NOT_COMPLETED',message='Native response did not complete (finish_reason='+str(finish)+'); not imported.')
 elif type(content)is not str:
  d.update(reason_code='MISSING_NATIVE_CONTENT',message='Completed native response has no text content; not imported.')
 else:
  try:strict_json(content)
  except ValueError as ex:d.update(reason_code='MALFORMED_MODEL_CONTENT',message='Native finish_reason=stop, but model content is invalid JSON; not imported.',parse_error=str(ex))
  else:d.update(reason_code='COMPLETED_EXACT_VALIDATION_REQUIRED',message='Native response completed; exact citation and semantic checks remain required.',eligible_for_structure_validation=True)
 return d

def unwrap(raw):
 d=inspect(raw)
 if not d['eligible_for_structure_validation']:raise RejectedResponse(d)
 value=strict_json(raw.decode('utf-8-sig'))
 return value['choices'][0]['message']['content'].encode('utf-8') if 'choices' in value else raw

def no_reparse(path):
 p=Path(path).absolute()
 for item in [p]+list(p.parents):
  if item.exists() and (item.is_symlink() or getattr(os.lstat(item),'st_file_attributes',0)&0x400):raise ValueError('Diagnostic path contains a reparse point')

def bounded(path):
 with Path(path).open('rb') as stream:raw=stream.read(LIMIT+1)
 if len(raw)>LIMIT:raise ValueError('Diagnostic file exceeds8MiB')
 return raw

def verify_bundle(folder):
 folder=Path(folder);no_reparse(folder)
 manifest=strict_json(bounded(folder/'manifest.json').decode('utf-8'))
 if manifest.get('schema')!='reveng-response-diagnostic-bundle-v1' or set(manifest.get('files',{}))!={'contract.json','response.raw','diagnostic.json'}:raise ValueError('Invalid diagnostic bundle manifest')
 for name,want in manifest['files'].items():
  p=folder/name;no_reparse(p)
  if p.stat().st_size>LIMIT or sha(bounded(p))!=want:raise ValueError('Diagnostic bundle hash mismatch: '+name)
 d=strict_json(bounded(folder/'diagnostic.json').decode('utf-8'))
 if d.get('research_imported')is not False or d.get('automatic_admission')is not False or d.get('semantic_PASS')is not False:raise ValueError('Diagnostic cannot claim research admission or semantic PASS')
 if d.get('raw_response_sha256')!=sha(bounded(folder/'response.raw')) or d.get('contract_sha256')!=sha(bounded(folder/'contract.json')):raise ValueError('Diagnostic response/contract binding mismatch')
 if d.get('reason_code')!='SOURCE_CONTRACT_OR_LITERAL_VALIDATION_REJECTED':
  actual=inspect(bounded(folder/'response.raw'))
  for key in ['reason_code','message','finish_reason','output_tokens','prompt_tokens']:
   if d.get(key)!=actual.get(key):raise ValueError('Diagnostic reason differs from original saved response')
 return d

def save_rejected(root,contract,raw,diagnostic):
 root=Path(root).absolute();no_reparse(root)
 if (root/'.readonly-research-preview').exists():raise ValueError('Historical archive snapshot is read-only; no diagnostic saved')
 if diagnostic.get('eligible_for_structure_validation')is not False:raise ValueError('Only a rejected response may be retained here')
 if len(raw)>LIMIT:raise ValueError('Diagnostic response exceeds8MiB')
 contract_raw=canonical(contract)
 if len(contract_raw)>LIMIT:raise ValueError('Diagnostic contract exceeds8MiB')
 base=root/'response-diagnostics';no_reparse(base);base.mkdir(exist_ok=True)
 import source_ledger as ledger
 with ledger.writer_lock(base/'.writer-v1.lock'):
  key=sha(contract_raw+b'\0'+raw);target=base/key
  if target.exists():return {'path':str(target),'diagnostic':verify_bundle(target),'already_saved':True}
  existing=[p for p in base.iterdir() if p.is_dir() and re.fullmatch('[0-9a-f]{64}',p.name)]
  if len(existing)>=20:raise ValueError('Diagnostic history has20 entries; existing work is preserved')
  total=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
  if total+len(contract_raw)+len(raw)+65536>128*1024*1024:raise ValueError('Diagnostic history exceeds128MiB; existing work is preserved')
  details=dict(diagnostic,saved_UTC=datetime.now(timezone.utc).isoformat(),contract_sha256=sha(contract_raw))
  payloads={'contract.json':contract_raw,'response.raw':raw,'diagnostic.json':canonical(details)}
  temp=Path(tempfile.mkdtemp(dir=base,prefix='.pending-'))
  try:
   for name,data in payloads.items():
    with (temp/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
   manifest={'schema':'reveng-response-diagnostic-bundle-v1','files':{n:sha(b) for n,b in payloads.items()}}
   with (temp/'manifest.json').open('xb') as stream:stream.write(canonical(manifest));stream.flush();os.fsync(stream.fileno())
   verify_bundle(temp);os.rename(temp,target)
  finally:
   if temp.exists():
    if not temp.resolve().is_relative_to(base.resolve()):raise ValueError('Diagnostic cleanup escaped its owned staging directory')
    no_reparse(temp);shutil.rmtree(temp)
  return {'path':str(target),'diagnostic':details,'already_saved':False}

def latest(root):
 base=Path(root)/'response-diagnostics'
 if not base.exists():return None
 try:
  no_reparse(base);folders=[p for p in base.iterdir() if p.is_dir() and re.fullmatch('[0-9a-f]{64}',p.name)]
  if not folders:return None
  if len(folders)>20:raise ValueError('Diagnostic inventory exceeds20 entries')
  folder=max(folders,key=lambda p:p.stat().st_mtime_ns)
  return {'path':str(folder),'diagnostic':verify_bundle(folder),'research_imported':False}
 except (ValueError,OSError,UnicodeError) as ex:return {'status':'DIAGNOSTIC_UNREADABLE','message':str(ex),'research_imported':False,'automatic_admission':False,'semantic_PASS':False}
