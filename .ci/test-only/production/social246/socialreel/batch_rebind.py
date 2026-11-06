"""Recoverable local metadata transaction for batch path rebinding only."""
import re,uuid
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_bytes,sha256_file,atomic_bytes,utc_now
JOURNAL='path_rebind_transaction.json'

def pending(folder):
    path=Path(folder)/JOURNAL
    if not path.exists():return False
    journal=read_json(path)
    if not isinstance(journal,dict) or journal.get('schema')!='SOCIAL_REBIND_TRANSACTION_V1' or journal.get('phase') not in {'prepared','committed','rolled_back'}:raise PipelineError('Unknown rebind journal; original preserved')
    return journal['phase']=='prepared'

def require_settled(folder):
    if pending(folder):raise PipelineError('Path rebind interrupted; use batch recover-paths --mode continue or rollback; no issue attempted')

def _digest(path):return sha256_file(path) if path.is_file() else None

def prepare(folder,payloads):
    folder=Path(folder);require_settled(folder);identity=uuid.uuid4().hex;transaction=folder/'path_rebind_transactions'/identity;transaction.mkdir(parents=True)
    entries=[]
    for name,after in payloads.items():
        if not re.fullmatch(r'(state\.json|INDEX\.md|item_[0-9]{2}\.json)',name):raise PipelineError('Unsupported rebind metadata file')
        path=folder/name;before=path.read_bytes() if path.exists() else None
        for stage,data in (('before',before),('after',after)):
            if data is not None:atomic_bytes(transaction/stage/name,data)
        entries.append({'name':name,'before_sha256':sha256_bytes(before) if before is not None else None,'after_sha256':sha256_bytes(after)})
    journal={'schema':'SOCIAL_REBIND_TRANSACTION_V1','transaction_id':identity,'phase':'prepared','created_at':utc_now().isoformat(),'entries':entries}
    write_json(transaction/'plan.json',journal);write_json(folder/JOURNAL,journal)
    return journal

def recover(folder,mode):
    folder=Path(folder)
    if mode not in {'continue','rollback'}:raise PipelineError('Recovery mode must be continue or rollback')
    journal=read_json(folder/JOURNAL)
    if journal.get('schema')!='SOCIAL_REBIND_TRANSACTION_V1' or not re.fullmatch('[0-9a-f]{32}',str(journal.get('transaction_id',''))):raise PipelineError('Unknown rebind journal; original preserved')
    if journal.get('phase')!='prepared':return {'recovery_needed':False,'phase':journal.get('phase'),'files_written':0}
    transaction=(folder/'path_rebind_transactions'/journal['transaction_id']).resolve()
    if not transaction.is_relative_to(folder.resolve()):raise PipelineError('Rebind transaction outside owned folder')
    plan=read_json(transaction/'plan.json')
    if plan!=journal:raise PipelineError('Rebind plan/journal mismatch; no write')
    writes=[];conflicts=[]
    for entry in journal['entries']:
        name=entry['name']
        if not re.fullmatch(r'(state\.json|INDEX\.md|item_[0-9]{2}\.json)',name):raise PipelineError('Unsafe rebind journal path')
        path=(folder/name).resolve()
        if path.parent!=folder.resolve():raise PipelineError('Rebind target escaped its folder')
        for stage in ('before','after'):
            staged=(transaction/stage/name).resolve();digest=entry[stage+'_sha256']
            if not staged.is_relative_to(transaction) or (digest is not None and _digest(staged)!=digest):raise PipelineError('Rebind staged bytes changed; no write')
        current=_digest(path)
        if current not in (entry['before_sha256'],entry['after_sha256']):conflicts.append(name);continue
        stage='after' if mode=='continue' else 'before';expected=entry[stage+'_sha256']
        if current!=expected:writes.append((path,transaction/stage/name,expected,current))
    if conflicts:raise PipelineError('Recovery conflict; concurrent changes preserved, no files written: '+','.join(conflicts))
    for path,staged,expected,current in writes:
        if _digest(path)!=current:raise PipelineError('Recovery target changed during apply; preserved; retry recovery')
        if expected is None:path.unlink()
        else:atomic_bytes(path,staged.read_bytes())
    journal['phase']='committed' if mode=='continue' else 'rolled_back';journal['settled_at']=utc_now().isoformat();write_json(folder/JOURNAL,journal)
    return {'recovery_needed':False,'phase':journal['phase'],'files_written':len(writes),'transaction_id':journal['transaction_id']}
