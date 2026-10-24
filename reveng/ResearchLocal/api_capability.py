"""One bounded API workflow documentation task. No execution or market inference."""
import hashlib,json,re,time
from pathlib import Path

TASK='api_traffic_regression_mocks'
REQUIRED=['same_capture_tests_and_mocks','dependency_off_replay','material_regression_failure','noise_only_pass']
TASKS={TASK:{'required':REQUIRED,'role':'API maintainer (hypothesis, not verified buyer)',
 'remaining':['Actual capture/replay artifacts on a matching environment','No runtime execution, pricing or demand verified']}}
SOURCES={
 'api_keploy_local':{'provider':'Keploy official local installation documentation','task':TASK,'url':'https://keploy.io/docs/server/installation/'}}
RULES={
 'same_capture_tests_and_mocks':r"Keploy captures your app.s API calls and turns them into test cases and mocks/stubs\.",
 'dependency_record_replay':r'Record real API interactions \(and dependencies\) and replay them deterministically in local or CI\.',
 'automatic_dependency_mocks':r'Mocks dependencies automatically'}
DENIALS={
 'same_capture_tests_and_mocks':r'(?:does not|cannot|never) (?:create|generate|capture|produce) (?:both )?(?:tests|test cases) and mocks',
 'dependency_record_replay':r'(?:cannot|does not) replay (?:recorded )?dependencies',
 'automatic_dependency_mocks':r'(?:does not|cannot) mock dependencies automatically'}
LIMITS=['Publisher documentation claims only; not tested capability',
 'Platform/kernel, permissions, account requirements, dependency protocols and versions need review',
 'No pricing/free-tier, customer, popularity, demand or comparative advantage inferred',
 'Absence of a matching excerpt is unknown, not proof of absent capability']

def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def parse(key,text,stamp,response_sha,schema):
 spec=SOURCES[key];text=' '.join(text.split())
 if len(text)>200000:raise ValueError('Documentation text exceeds bounded task limit; no clipping')
 claims=[];remaining=25;contradictions=[]
 for capability,pattern in RULES.items():
  match=re.search(pattern,text)
  if re.search(DENIALS[capability],text,re.I):contradictions.append(capability);continue
  if not match:continue
  # Explicit denials are conservative ambiguity signals, not semantic approval.
  words=len(match.group().split())
  if words>remaining:continue
  remaining-=words
  claims.append({'id':'D'+str(len(claims)+1),'kind':capability,'quote':match.group(),
    'start':match.start(),'end':match.end(),'evidence_type':'official_documented_claim','tested':False})
 return {'schema':schema,'provider':spec['provider'],'task':TASK,'source_url':spec['url'],
  'observed_at':stamp,'response_sha256':response_sha,'expires':time.time()+86400,
  'document_text':text,'document_text_sha256':digest(text),'facts':claims,
  'contradictory_capabilities':contradictions,'classification':'documented_claims_only' if claims else 'unknown',
  'covered':[],'unproven':REQUIRED,'limits':LIMITS,'executed_observations':[],
  'execution_status':'not_performed','market_demand':'not established','paying_customer_status':'unknown'}

def attachment(records,root):
 """Verify owned raw bindings before exposing selected publisher claims to synthesis."""
 root=Path(root).resolve();documents=[];missing=[];conflicts=set()
 for row in records:
  if row.get('task')!=TASK:raise ValueError('Evidence outside the explicit API task')
  if row.get('executed_observations') or row.get('execution_status') not in [None,'not_performed']:
   raise ValueError('Documentation collector cannot supply executed observations')
  spec=next((s for s in SOURCES.values() if s['url']==row.get('source_url')),None)
  diagnostic=None;text=row.get('document_text');rawsha=row.get('response_sha256','');raw=None
  if spec is None:diagnostic='URL outside official task allowlist'
  elif row.get('error'):diagnostic='Source unavailable: '+str(row['error'])
  elif row.get('expires',0)<=time.time():diagnostic='Original source receipt expired; no date renewal'
  elif not isinstance(row.get('observed_at'),str) or not row['observed_at']:diagnostic='Capture date missing'
  elif not re.fullmatch('[0-9a-f]{64}',rawsha):diagnostic='Raw hash unavailable'
  elif not isinstance(text,str) or digest(text)!=row.get('document_text_sha256'):diagnostic='Text binding invalid'
  else:
   path=root/'direct-source-payloads'/(rawsha+'.raw')
   if root not in path.resolve().parents or not path.is_file():diagnostic='Owned raw payload unavailable or changed'
   else:
    with path.open('rb') as source:raw=source.read(1048577)
    if len(raw)>1048576 or hashlib.sha256(raw).hexdigest()!=rawsha:diagnostic='Owned raw payload unavailable or changed'
  claims=[]
  if diagnostic is None:
   # Reparse bound raw through the existing cleaner; metadata alone cannot authenticate text.
   import direct_alternatives
   try:normalized=' '.join(direct_alternatives.body_text(raw,row['source_url']).split())
   except (ValueError,UnicodeError):diagnostic='Raw HTML source identity unavailable or invalid';normalized=None
   if diagnostic is None and normalized!=text:diagnostic='Raw-to-text binding invalid'
   if diagnostic is None:
    key=next(k for k,v in SOURCES.items() if v['url']==row['source_url'])
    derived=parse(key,text,row['observed_at'],rawsha,row.get('schema'))
    conflicts.update(derived['contradictory_capabilities']);claims=derived['facts']
  if diagnostic:missing.append({'source_url':row.get('source_url'),'reason':diagnostic})
  doc={'source_url':row.get('source_url'),'captured_at':row.get('observed_at') if diagnostic is None else None,'attempted_or_recorded_at':row.get('observed_at'),
    'raw_sha256':rawsha,'text_sha256':row.get('document_text_sha256'),
    'status':'unknown' if diagnostic else 'official_claims_not_tested','diagnostic':diagnostic,
    'claims':claims,'limits':LIMITS,'scope':'Selected exact excerpts; full raw/text retained outside prompt'}
  documents.append(doc)
 # Remove any conflicting capability across the selected evidence; never vote by popularity.
 for d in documents:
  d['claims']=[c for c in d['claims'] if c['kind'] not in conflicts]
 if conflicts:missing.append({'reason':'Contradictory documented evidence remains unknown','capabilities':sorted(conflicts)})
 documented={c['kind'] for d in documents for c in d['claims']}
 return {'schema':'api-capability-evidence-v1','task':TASK,'documents':documents,
  'documented_capabilities':sorted(documented),'unknown_required_capabilities':[c for c in REQUIRED if c not in documented],
  'missing_evidence':missing,'executed_observations':[],'execution_status':'not_performed',
  'tested_capabilities':[],'market_demand':'unknown','policy':LIMITS}

def append_to_request(request,records,root):
 block=attachment(records,root)
 marker='SOURCE OBSERVATIONS:\n'
 prefix,source=request['messages'][1]['content'].split(marker,1)
 # Keep the trailing source JSON intact for existing prepared-request validators.
 request['messages'][1]['content']=prefix+'OFFICIAL CAPABILITY EVIDENCE (publisher claims, NOT execution, buyers or demand; unavailable/contradictory stays unknown. Attribute any use as publisher-documented and untested. Existing observations_used IDs/fields remain bound only to original observations; do not invent official-document quote IDs or URLs in output):\n'+json.dumps(block,ensure_ascii=False,separators=(',',':'))+'\n'+marker+source
 return request
