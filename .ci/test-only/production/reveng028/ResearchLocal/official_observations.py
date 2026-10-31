"""Import the three reviewed structured official observations; no HTML reconstruction."""
from pathlib import Path
import json,hashlib,os,tempfile,copy,re
from datetime import datetime,timezone
URLS={'wave-20261019':('Wave','https://www.waveapps.com/pricing'),'tripit-20261019':('TripIt Pro','https://www.tripit.com/web/pro'),'jobber-20261019':('Jobber','https://www.getjobber.com/pricing/')}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def utc_instant(value):
 if not isinstance(value,str)or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)',value):raise ValueError('Timezone-aware ISO capture timestamp required')
 stamp=datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
 if stamp>datetime.now(timezone.utc):raise ValueError('Future capture timestamp')
 return stamp
def same_observation(a,b):
 # Encoding/offset aliases are not new evidence. Preserve the first exact capture.
 return {k:v for k,v in a.items()if k not in ['retrieved_at_utc','local_observation_sha256']}=={k:v for k,v in b.items()if k not in ['retrieved_at_utc','local_observation_sha256']}
def local(path):
 p=Path(path).resolve()
 if str(p).startswith('\\\\')or any(x.is_symlink()or getattr(x,'is_junction',lambda:False)()for x in [Path(path),*Path(path).absolute().parents]):raise ValueError('Local non-reparse observation path required')
 return p
def read(path):
 path=local(path)
 if path.stat().st_size>1024*1024:raise ValueError('Observation limit 1MiB')
 with path.open('rb')as stream:raw=stream.read(1024*1024+1)
 if len(raw)>1024*1024:raise ValueError('Observation limit 1MiB')
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ValueError('Duplicate JSON key')
   out[k]=v
  return out
 return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in()).throw(ValueError('Nonfinite JSON'))),raw
def load(manifest):
 manifest=local(manifest);index,_=read(manifest);out=[]
 if not isinstance(index.get('files'),dict):raise ValueError('Observation manifest missing files')
 for key,(vendor,url)in URLS.items():
  name=key+'.json';path=manifest.parent/name;row,raw=read(path)
  if digest(raw)!=index['files'].get(name):raise ValueError('Observation file hash mismatch '+name)
  if row.get('id')!=key or row.get('url')!=url or row.get('schema')!='reveng-public-official-observation-v1':raise ValueError('Unsupported observation identity')
  if row.get('raw_http_response_saved')is not False or row.get('source_response_sha256')is not None:raise ValueError('Expected structured summary, not raw document')
  if not isinstance(row.get('observed'),dict)or not isinstance(row.get('evidence'),list):raise ValueError('Missing structured facts/provenance')
  utc_instant(row['retrieved_at_utc'])
  out.append(dict(row,vendor=vendor,local_observation_sha256=digest(raw),evidence_origin='STRUCTURED_SUMMARY_NOT_RAW_DOCUMENT',raw_spans=None))
 return out
def project(row):
 facts=row['observed'];vendor=row['vendor'];currency=facts.get('currency');unknown=lambda v:v is None or str(v).lower().startswith(('unknown','not established'))
 out={k:copy.deepcopy(row[k])for k in ['id','vendor','url','retrieved_at_utc','local_observation_sha256','evidence_origin','raw_spans','evidence','remaining_unknown','observed']}
 out.update(currency=None if unknown(currency)else currency,additional_user_charge=None,task_equivalence='unknown; structured source facts do not establish target-task coverage',automatic_admission=False,inherit_old_unknown_fields=False)
 if vendor=='Wave':
  dates=re.findall(r'\d{4}-\d{2}-\d{2}',facts.get('promo_date_window',''))
  out['promo_status']='unknown';out['promo_is_current_price']=False
  if len(dates)==2 and dates[0]<=dates[1]and dates[1]<datetime.now(timezone.utc).date().isoformat():out['promo_status']='expired'
  out['currency_options']=sorted(facts.get('pro_monthly',{}));out['unit']=facts.get('unit')
 if vendor=='TripIt Pro':out['function_distinction']='Baggage claim location is documented; airline baggage allowance-rule coverage remains unknown.'
 if vendor=='Jobber':out['additional_user_charge_status']='unknown in this new observation; historical rate not carried forward'
 return out
def verify_projection(report):
 if report.get('schema')!='reveng-structured-official-projection-v1'or report.get('owner_decisions_changed')is not False or not isinstance(report.get('candidate_pins'),dict):raise ValueError('Unsupported official observation projection')
 rows=report.get('observations',[]);projections=report.get('projections',[])
 if not isinstance(rows,list)or not isinstance(projections,list)or len(rows)!=3 or len(projections)!=3:raise ValueError('Incomplete official observations')
 byid={r.get('id'):r for r in rows};shown={r.get('id'):r for r in projections}
 if set(byid)!=set(URLS)or set(shown)!=set(URLS):raise ValueError('Ambiguous official observation identities')
 for id,(vendor,url)in URLS.items():
  row=byid[id]
  if row.get('vendor')!=vendor or row.get('url')!=url or row.get('evidence_origin')!='STRUCTURED_SUMMARY_NOT_RAW_DOCUMENT'or row.get('raw_spans')is not None or row.get('raw_http_response_saved')is not False:raise ValueError('Official observation origin mismatch')
  utc_instant(row.get('retrieved_at_utc'));expected=project(row);actual=copy.deepcopy(shown[id])
  if 'currency_options'in actual:actual['currency_options']=sorted(actual['currency_options'])
  if actual!=expected:raise ValueError('Official projection differs from source or adds unsupported evaluation')
 return sorted(byid)
def ingest(root,manifest):
 from source_ledger import require_writable
 require_writable(root)
 root=local(root);cards,cardraw=read(root/'candidates.json');observations=load(manifest);projections=[project(r)for r in observations];target=root/'official-observations.json'
 previous=None
 if target.exists():
  previous,_=read(target)
  for old in previous.get('observations',[]):
   new=next((r for r in observations if r['id']==old.get('id')),None)
   if new:
    incoming=utc_instant(new['retrieved_at_utc']);stored=utc_instant(old.get('retrieved_at_utc'))
    if incoming<stored or incoming==stored and not same_observation(new,old):raise ValueError('Older or conflicting observation; existing store preserved')
    if incoming==stored:observations[observations.index(new)]=copy.deepcopy(old)
  projections=[project(r)for r in observations]
  if previous.get('observations')==observations and previous.get('cards_sha256')==digest(cardraw):return previous
 report={'schema':'reveng-structured-official-projection-v1','observations':observations,'projections':projections,'candidate_pins':{c['candidate_id']:c.get('review_revision_hash')for c in cards},'cards_sha256':digest(cardraw),'owner_decisions_changed':False,'model_calls':0,'source_requests':0,'note':'Separate structured update; historical cards/notes unchanged, no raw source spans or automatic task equivalence.'}
 if previous==report:return report
 raw=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2).encode('utf-8');fd,name=tempfile.mkstemp(prefix='.official-observations-',suffix='.tmp',dir=root)
 try:
  with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
  if (root/'candidates.json').read_bytes()!=cardraw:raise ValueError('Candidate ledger changed during import')
  os.replace(name,target)
 finally:
  if Path(name).exists():Path(name).unlink()
 return report
