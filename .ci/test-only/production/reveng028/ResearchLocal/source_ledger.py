"""Lossless saved-source reading/quotation ledger, not semantic/business extraction."""
from pathlib import Path
import argparse,hashlib,json,os,tempfile
import evidence_workspace
LIMIT=8*1024*1024
KINDS=['reported_statement','reported_condition_or_preference','author_question']
def rawsha(raw):return hashlib.sha256(raw).hexdigest()
def require_writable(root):
 if (Path(root)/'.readonly-research-preview').exists():raise ValueError('Historical archive snapshot is read-only; current workspace and decisions are unchanged')
from contextlib import contextmanager

@contextmanager
def writer_lock(path):
 """Nonblocking OS lock; keep the inode/path so active writers cannot be bypassed.

 A leftover file is harmless: ownership is the live descriptor lock, not existence.
 All cooperating writers must use this protocol (do not mix legacy writers).
 """
 with Path(path).open('a+b') as gate:
  gate.seek(0,2)
  if gate.tell()==0:gate.write(b'0');gate.flush()
  gate.seek(0)
  try:
   if os.name=='nt':
    import msvcrt
    msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl
    fcntl.flock(gate.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError as error:raise ValueError('Another writer is active; retry after it finishes') from error
  # Closing releases the OS lock even on an exception or process termination.
  yield

def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def seal(value):
 p=canonical(value).decode();return {'payload_json':p,'payload_sha256':rawsha(p.encode())}
def unseal(value):
 if not isinstance(value,dict) or not isinstance(value.get('payload_json'),str) or rawsha(value['payload_json'].encode())!=value.get('payload_sha256'):raise ValueError('Ledger payload hash mismatch')
 return json.loads(value['payload_json'])
def read(path):
 raw=path.read_bytes()
 if len(raw)>LIMIT:raise ValueError('Local data exceeds8MiB')
 return raw,json.loads(raw.decode('utf-8-sig'))
def write(path,value):
 raw=canonical(value)
 if len(raw)>LIMIT:raise ValueError('Ledger limit reached; preserve existing data')
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.ledger-',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if Path(tmp).exists():Path(tmp).unlink()
def units(text,identity):
 """Mechanical punctuation/line boundaries only; concatenate quotes = exact source."""
 cuts=[0];i=0
 while i<len(text):
  ch=text[i];cut=ch in '\r\n' or ch in '.!?;:' and i+1<len(text) and text[i+1].isspace()
  if cut:
   j=i+1
   while j<len(text) and text[j].isspace():j+=1
   if j<len(text):cuts.append(j)
   i=j
  else:i+=1
 cuts.append(len(text));result=[]
 for a,b in zip(cuts,cuts[1:]):
  if a==b:continue
  q=text[a:b];result.append({'id':rawsha(canonical([identity,a,b,rawsha(q.encode())])),'start':a,'end':b,'quote':q,'quote_sha256':rawsha(q.encode()),'classification':'UNCLASSIFIED_SOURCE_FRAGMENT','source_truth':'UNVERIFIED','meaning':'Mechanical reading unit; not automatically identified fact or condition'})
 assert ''.join(u['quote'] for u in result)==text
 return result
def build(root):
 root=Path(root).resolve();graph=evidence_workspace.build(root);items=[]
 for m in graph['materials']:
  if rawsha(m['text'].encode())!=m['text_sha256']:raise ValueError('Material text hash mismatch')
  metadata={k:v for k,v in m.items() if k!='text'}
  for k in ['origins','card_ids','version_ids']:
   if isinstance(metadata.get(k),list):metadata[k]=sorted(metadata[k],key=canonical)
  item={'id':m['id'],'text':m['text'],'text_sha256':m['text_sha256'],'metadata':metadata,'units':units(m['text'],m['id'])};items.append(item)
 for n,h in graph['inputs'].items():
  p=(root/n).resolve()
  if not p.is_relative_to(root) or (p.exists() if h is None else not p.is_file() or rawsha(p.read_bytes())!=h):raise ValueError('Source changed during catalog capture')
 return {'schema':'reveng-source-ledger-catalog-v1','inputs':graph['inputs'],'materials':sorted(items,key=lambda x:x['id']),'source_errors':sorted(graph['errors'],key=canonical),'source_policy':'All saved fields/revisions, not only model-candidate inputs. Mechanical units preserve every codepoint. No automatic fact/condition classification, people count or market analysis.','automatic_admission':False,'model_calls':0,'network_calls':0}
def validate_catalog(root,cat):
 if cat['schema']!='reveng-source-ledger-catalog-v1' or cat['automatic_admission'] is not False:raise ValueError('Invalid catalog policy')
 seen=set()
 for n,h in cat['inputs'].items():
  p=(Path(root)/n).resolve()
  if not p.is_relative_to(Path(root).resolve()) or (p.exists() if h is None else not p.is_file() or rawsha(p.read_bytes())!=h):raise ValueError('Catalog inputs changed; rebuild, do not rewrite source')
 for item in cat['materials']:
  if item['id'] in seen or rawsha(item['text'].encode())!=item['text_sha256'] or units(item['text'],item['id'])!=item['units']:raise ValueError('Invalid source material/partition')
  seen.add(item['id'])
 if canonical(cat)!=canonical(build(root)):raise ValueError('Catalog differs from actual saved sources or new input appeared; rebuild required')
 return cat
def catalog(root):return validate_catalog(root,unseal(read(Path(root)/'source-ledger-catalog.json')[1]))
def notes(root):
 p=Path(root)/'source-ledger.json'
 if not p.exists():return {'schema':'reveng-manual-source-ledger-v1','entries':[],'automatic_admission':False},None
 raw,obj=read(p);data=unseal(obj)
 if data['schema']!='reveng-manual-source-ledger-v1' or data['automatic_admission'] is not False:raise ValueError('Invalid ledger policy')
 ids=set()
 for wrap in data['entries']:
  row=unseal(wrap);s=row['source_snapshot'];a=row['start'];b=row['end']
  if wrap['payload_sha256'] in ids or type(a)is not int or type(b)is not int or a<0 or b<=a or b>len(s['text']) or s['text'][a:b]!=row['quote'] or rawsha(s['text'].encode())!=s['text_sha256'] or row['category'] not in KINDS or row['classification_origin']!='EXPLICIT_HUMAN_SELECTION' or row['semantic_verification']!='UNVERIFIED_REPORTED_CONTENT':raise ValueError('Invalid saved quotation; preserve original file')
  ids.add(wrap['payload_sha256'])
 return data,rawsha(raw)
def append(root,proposal):
 require_writable(root)
 root=Path(root).resolve()
 with writer_lock(root/'.source-ledger-write-v2.lock'):
  data,current=notes(root)
  if proposal.get('expected_ledger_sha256')!=current:raise ValueError('Another writer changed ledger; reload before saving')
  cat=catalog(root);verify_notes(cat,data);source=next(x for x in cat['materials'] if x['id']==proposal['material_id']);a=proposal['start'];b=proposal['end'];category=proposal['category']
  if type(a)is not int or type(b)is not int or not 0<=a<b<=len(source['text']) or source['text'][a:b]!=proposal['quote'] or category not in KINDS:raise ValueError('Exact selected quotation/category required')
  entry={'source_snapshot':{k:v for k,v in source.items() if k!='units'},'start':a,'end':b,'quote':proposal['quote'],'category':category,'classification_origin':'EXPLICIT_HUMAN_SELECTION','semantic_verification':'UNVERIFIED_REPORTED_CONTENT','buyer_payment_market_status':'UNKNOWN','automatic_admission':False}
  wrap=seal(entry)
  if any(r['payload_sha256']==wrap['payload_sha256'] for r in data['entries']):raise ValueError('Same quotation/category already recorded')
  data['entries'].append(wrap);write(root/'source-ledger.json',seal(data));return {'status':'SAVED_EXACT_QUOTATION_ONLY','entry_id':wrap['payload_sha256'],'ledger_sha256':rawsha((root/'source-ledger.json').read_bytes()),'automatic_admission':False}
def provenance_status(actual,snapshot):
 # Text identity and provenance confidence are distinct. Empty provenance is
 # never evidence of an origin match, even though the empty set is a subset.
 if not same_source_revision(actual,snapshot):return 'SOURCE_REVISION_MISMATCH'
 a=actual['metadata'];s=snapshot['metadata']
 if not s.get('origins'):return 'SOURCE_BYTES_MATCH_PROVENANCE_UNKNOWN_UNVERIFIED'
 if all({canonical(x) for x in s.get(k,[])}=={canonical(x) for x in a.get(k,[])} for k in ['origins','card_ids','version_ids']):return 'EXACT_SOURCE_BYTES_AND_SAVED_ORIGINS_MATCH'
 return 'EXACT_SOURCE_BYTES_AND_PRESERVED_ORIGINS_SUBSET_MATCH'

def same_source_revision(actual,snapshot):
 if any(actual.get(k)!=snapshot.get(k) for k in ['id','text','text_sha256']):return False
 a=actual['metadata'];s=snapshot['metadata'];derived={'origins','card_ids','version_ids','author'}
 if {k:v for k,v in a.items() if k not in derived}!={k:v for k,v in s.items() if k not in derived}:return False
 for metadata in [a,s]:
  for k in ['origins','card_ids','version_ids']:
   if not isinstance(metadata.get(k,[]),list):return False
  if any(not isinstance(x,dict) or not x for x in metadata.get('origins',[])):return False
 for k in ['origins','card_ids','version_ids']:
  if not {canonical(x) for x in s.get(k,[])}<={canonical(x) for x in a.get(k,[])}:return False
 if a.get('author')!=s.get('author'):
  # A graph may add a conflicting origin. Preserve the former reported-author snapshot,
  # only if that exact author metadata still occurs in its exact saved origins.
  authors={'unknown' if x.get('reported_author_id') in [None,''] else str(x['reported_author_id']) for x in s.get('origins',[])}
  if s.get('author') not in authors:return False
 return True
def same_manual_source_revision(cat,actual,snapshot):
 """Manual editor v1 stores a flat graph material, plus validated container hashes."""
 if 'metadata' in snapshot:return same_source_revision(actual,snapshot)
 metadata={k:v for k,v in snapshot.items() if k not in ['text','units']}
 origins=[]
 for origin in metadata.get('origins',[]):
  copied=dict(origin);captured=copied.pop('container_sha256',None)
  if captured is None or cat['inputs'].get(copied.get('container'))!=captured:return False
  origins.append(copied)
 metadata['origins']=origins
 return same_source_revision(actual,{'id':snapshot.get('id'),'text':snapshot.get('text'),'text_sha256':snapshot.get('text_sha256'),'metadata':metadata})
def verify_notes(cat,data):
 materials={m['id']:{k:v for k,v in m.items() if k!='units'} for m in cat['materials']};statuses=[]
 for wrap in data['entries']:
  row=unseal(wrap);s=row['source_snapshot'];actual=materials.get(s['id'])
  if actual is not None and not same_source_revision(actual,s):raise ValueError('Saved note snapshot differs from exact source material; preserve and inspect, do not reclassify')
  statuses.append({'entry_id':wrap['payload_sha256'],'source_status':provenance_status(actual,s) if actual is not None else 'HISTORICAL_SNAPSHOT_NOT_CURRENTLY_RESOLVABLE_NO_FACT_VERIFICATION'})
 return statuses
def view(root):
 cat=catalog(root);ledger_error=None;proposal_error=None
 try:data,h=notes(root);verification=verify_notes(cat,data)
 except Exception as ex:data={'entries':[]};h=None;verification=[];ledger_error=type(ex).__name__+': '+str(ex)
 proposals={'entries':[]};proposal_bindings=[]
 if (Path(root)/'source-model-proposals.json').exists():
  try:
   import source_proposals
   proposals=source_proposals.load(root,cat);proposal_bindings=source_proposals.bindings(proposals,cat)
  except Exception as ex:proposal_error=type(ex).__name__+': '+str(ex)
 import response_diagnostics
 return {'last_response_diagnostic':response_diagnostics.latest(root),'catalog':cat,'ledger':data,'ledger_error':ledger_error,'ledger_verification':verification,'model_proposals':proposals,'model_proposal_bindings':proposal_bindings,'model_proposal_error':proposal_error,'ledger_sha256':h,'AI_interpretation_status':'SEPARATE_UNVERIFIED_NOT_FACTS','automatic_admission':False}
def verify_portable(fetch,names):
 if 'source-ledger-catalog.json' not in names:
  if {'source-ledger.json','source-model-proposals.json'} & set(names):raise ValueError('Ledger/proposal source catalog missing')
  return
 cat=unseal(json.loads(fetch('source-ledger-catalog.json')))
 with tempfile.TemporaryDirectory(prefix='reveng-ledger-verify-') as folder:
  root=Path(folder)
  for n,h in cat['inputs'].items():
   p=(root/n).resolve()
   if h is None:
    if n!='research-candidate-reviews.json' or n in names:raise ValueError('Absent optional ledger input appeared or is not optional')
    continue
   if not p.is_relative_to(root) or n not in names:raise ValueError('Ledger input missing/unsafe in export')
   raw=fetch(n)
   if rawsha(raw)!=h:raise ValueError('Ledger source bytes changed in export')
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  validate_catalog(root,cat)
  if 'source-ledger.json' in names:
   (root/'source-ledger.json').write_bytes(fetch('source-ledger.json'));verify_notes(cat,notes(root)[0])
  if 'source-model-proposals.json' in names:
   import source_proposals
   (root/'source-model-proposals.json').write_bytes(fetch('source-model-proposals.json'));source_proposals.load(root,cat)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--build',action='store_true');p.add_argument('--proposal',type=Path);a=p.parse_args()
 if a.build:require_writable(a.root);write(a.root/'source-ledger-catalog.json',seal(build(a.root)))
 result=append(a.root,json.loads(a.proposal.read_text(encoding='utf-8-sig'))) if a.proposal else view(a.root)
 print(json.dumps(result,ensure_ascii=True))
