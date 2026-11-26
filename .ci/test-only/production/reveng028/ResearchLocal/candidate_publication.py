"""CAS publication of the existing candidate/latest pair, not an execution queue.
Only cooperating local writers are serialized. Run-local sealed bytes allow a
partially replaced pair to roll forward; foreign changes are never rolled back.
"""
from pathlib import Path
from contextlib import contextmanager
import json,hashlib,os,uuid,msvcrt
class PublicationConflict(ValueError):pass
def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _json(value):return json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8')
def _write(path,raw):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.parent/('.candidate-'+uuid.uuid4().hex+'.tmp')
 try:
  with tmp.open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  os.replace(tmp,path)
 finally:
  if tmp.exists():tmp.unlink()
@contextmanager
def _locked(root):
 root=Path(root);path=root/'candidate-publication.lock'
 with path.open('a+b')as stream:
  if path.stat().st_size==0:stream.write(b'0');stream.flush()
  stream.seek(0)
  try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
  except OSError:raise PublicationConflict('Candidate publication busy; no overwrite; retry from current state')
  try:yield
  finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
def _recover_locked(root):
 pointer=root/'candidate-publication.pending.json'
 if not pointer.exists():return False
 ref=json.loads(pointer.read_bytes());manifest=(root/ref['manifest']).resolve()
 if root.resolve()not in manifest.parents or any(x.is_symlink()for x in [manifest,*manifest.parents]if x!=root.parent):raise PublicationConflict('Unsafe pending candidate receipt; no overwrite')
 raw=manifest.read_bytes()
 if _sha(raw)!=ref['sha256']:raise PublicationConflict('Pending candidate receipt changed; no overwrite')
 report=json.loads(raw);stage=manifest.parent;payloads={}
 if report.get('schema')!='candidate-pair-publication-v1'or set(report.get('files',{}))!={'candidates.json','latest-result.json'}:raise PublicationConflict('Invalid pending candidate manifest; no overwrite')
 for name in ['candidates.json','latest-result.json']:
  entry=report['files'][name]
  if entry.get('before_file')!=name+'.before'or entry.get('after_file')!=name+'.after':raise PublicationConflict('Unsafe pending candidate payload path; no overwrite')
  old=(stage/entry['before_file']).read_bytes();new=(stage/entry['after_file']).read_bytes()
  if _sha(old)!=entry['before_sha256']or _sha(new)!=entry['after_sha256']:raise PublicationConflict('Pending candidate payload changed; no overwrite')
  current=(root/name).read_bytes()
  if current not in [old,new]:raise PublicationConflict('Foreign candidate change during pending publication; all files and receipt preserved')
  payloads[name]=new
 for name,raw in payloads.items():
  if (root/name).read_bytes()!=raw:_write(root/name,raw)
 _write(stage/'committed.json',_json({'status':'committed','recovered_or_idempotent':True,'files':{k:_sha(v)for k,v in payloads.items()}}));pointer.unlink();return True
def recover(root):
 root=Path(root).resolve()
 with _locked(root):return _recover_locked(root)
def publish(root,run,before_ledger,before_latest,cards,data):
 root=Path(root).resolve();run=Path(run).resolve()
 if root not in run.parents:raise ValueError('Candidate publication receipt must stay in its existing local run')
 stage=run/('candidate-publication-'+uuid.uuid4().hex);stage.mkdir(parents=True);files={}
 for name,old,new in [('candidates.json',before_ledger,_json(cards)),('latest-result.json',before_latest,_json(data))]:
  before=name+'.before';after=name+'.after';_write(stage/before,old);_write(stage/after,new);files[name]={'before_file':before,'after_file':after,'before_sha256':_sha(old),'after_sha256':_sha(new)}
 manifest=stage/'manifest.json';_write(manifest,_json({'schema':'candidate-pair-publication-v1','files':files,'owner_notes_written':False}))
 with _locked(root):
  _recover_locked(root)
  if (root/'candidates.json').read_bytes()!=before_ledger or (root/'latest-result.json').read_bytes()!=before_latest:raise PublicationConflict('Saved candidate pair changed before publication; computed proposal retained, no overwrite')
  _write(root/'candidate-publication.pending.json',_json({'manifest':manifest.relative_to(root).as_posix(),'sha256':_sha(manifest.read_bytes())}))
  _recover_locked(root)
 return manifest
