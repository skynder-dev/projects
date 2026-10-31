"""Journal paginated search/detail receipt publication; uncertain calls never repeat."""
import datetime as dt,json,re
from pathlib import Path
from .common import PipelineError,write_json,read_json,sha256_file,sha256_bytes,stable_json,atomic_bytes,utc_now
from .source_responses import search_payload,detail_envelope

class DiscoveryTransactionError(PipelineError):pass

def digest(value):return sha256_bytes(stable_json(value).encode())

def operation_id(kind,request,url,name,generation):return digest({'kind':kind,'request':request,'url':url,'snapshot_name':name,'generation':generation})

def fetch(root,stream_id,source,client,kind,request,url,name,generation,call,allow_new=True):
    root=Path(root).resolve();source=Path(source).resolve()
    if not re.fullmatch('[0-9a-f]{64}',stream_id) or kind not in {'search','detail'} or Path(name).name!=name or '/' in name or '\\' in name:raise DiscoveryTransactionError('Invalid bounded discovery operation identity')
    if not source.is_relative_to(root):raise DiscoveryTransactionError('Discovery source directory outside owned history scope; no request')
    descriptor={'kind':kind,'request':request,'url':url,'snapshot_name':name,'generation':generation}
    key=digest(descriptor);home=(root/'discovery_transactions'/stream_id).resolve();path=home/(key+'.json');cache=(root/'discovery_snapshots').resolve()
    if not home.is_relative_to(root) or not cache.is_relative_to(root):raise DiscoveryTransactionError('Discovery storage escaped owned history scope')
    if path.exists():
        try:record=read_json(path)
        except (OSError,ValueError,TypeError) as error:raise DiscoveryTransactionError('Discovery journal unreadable; preserved, no repeat') from error
        if not isinstance(record,dict):raise DiscoveryTransactionError('Discovery journal shape changed; no repeat')
        payload={k:v for k,v in record.items() if k!='journal_sha256'}
        if record.get('schema')!='SOCIAL_DISCOVERY_TRANSACTION_V1' or record.get('descriptor')!=descriptor or record.get('operation_id')!=key or record.get('journal_sha256')!=digest(payload) or record.get('state') not in {'intent','received','failed'} or type(record.get('failures')) is not int or not 0<=record['failures']<=3:raise DiscoveryTransactionError('Discovery journal identity/state changed; no repeat')
    else:
        if not allow_new:raise DiscoveryTransactionError('Reserved discovery journal missing; no automatic repeat')
        record={'schema':'SOCIAL_DISCOVERY_TRANSACTION_V1','operation_id':key,'descriptor':descriptor,'state':'new','failures':0}
    def save():
        record['journal_sha256']=digest({k:v for k,v in record.items() if k!='journal_sha256'});write_json(path,record)
    def cache_bytes(meta,raw):
        if meta.get('url',url)!=url or meta.get('request',request)!=request:raise DiscoveryTransactionError('Receipt belongs to another API request; no repeat')
        sha=meta.get('sha256')
        if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha) or sha256_bytes(raw)!=sha or len(raw)!=meta.get('bytes'):raise DiscoveryTransactionError('Discovery receipt bytes/hash mismatch; no repeat')
        target=(cache/sha).resolve()
        if not target.is_relative_to(root):raise DiscoveryTransactionError('Cache entry escaped owned history scope')
        if target.exists() and target.read_bytes()!=raw:raise DiscoveryTransactionError('Discovery cache conflict; preserved without overwrite or repeat')
        if not target.exists():atomic_bytes(target,raw)
        return target
    def decode(meta,raw,recovered):
        try:envelope=json.loads(raw)
        except (ValueError,UnicodeError) as error:raise PipelineError('Saved source response invalid JSON; bytes preserved') from error
        if kind=='search':
            hits,paging=search_payload(envelope,request['rows'],request['startRecordNum']);return hits,{**meta,**({'pagination':paging} if paging else {}),'transaction_recovered':recovered}
        if recovered and hasattr(client,'replay_detail'):
            return client.replay_detail(str(request['opportunityId']),meta)
        return detail_envelope(envelope,str(request['opportunityId'])),{**meta,'transaction_recovered':recovered}
    def received(meta,raw,recovered):
        cache_bytes(meta,raw);atomic_bytes(source/name,raw)
        # Keep original fetch time; recovery is never a new HTTP observation.
        stored={**meta,'file':'source/'+name};record.update(state='received',snapshot=stored);save()
        return decode(stored,raw,recovered)
    def old_outcome():
        relative=record.get('source_directory');old=(root/str(relative)).resolve()
        if not old.is_relative_to(root) or old==root:raise DiscoveryTransactionError('Journal source path escaped ownership; no repeat')
        ledger=old/'request_attempts.json'
        if not ledger.exists():return None
        saved=read_json(ledger)
        if not isinstance(saved,dict):raise DiscoveryTransactionError('Wire-attempt ledger shape changed; no repeat')
        payload={k:v for k,v in saved.items() if k!='ledger_sha256'}
        if saved.get('schema')!='SOCIAL_GRANTS_WIRE_ATTEMPTS_V1' or saved.get('ledger_sha256')!=digest(payload) or not isinstance(saved.get('attempts'),list):raise DiscoveryTransactionError('Wire-attempt ledger changed; no repeat')
        rows=saved['attempts'];base=record.get('attempt_base',0)
        matches=[r for r in rows[base:] if r.get('request_sha256')==digest(request) and r.get('url')==url and r.get('snapshot_name')==name]
        if len(matches)!=1:return None
        item=matches[0]
        if item.get('phase')=='failed':return ('failed',item)
        if item.get('phase')=='received':
            meta=item.get('snapshot_meta') or {};rawpath=(old/name).resolve()
            if not rawpath.is_relative_to(root):raise DiscoveryTransactionError('Received source path escaped owned history scope')
            if not rawpath.is_file():
                sha=meta.get('sha256')
                if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):return None
                rawpath=(cache/sha).resolve()
                if not rawpath.is_relative_to(root) or not rawpath.is_file():return None
            return ('received',(meta,rawpath.read_bytes()))
        return None
    if record['state']=='received':
        meta=record['snapshot']
        if not isinstance(meta.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',meta['sha256']):raise DiscoveryTransactionError('Journal cache identity invalid; no repeat')
        cached=(cache/meta['sha256']).resolve()
        if not cached.is_relative_to(root):raise DiscoveryTransactionError('Cache entry escaped owned history scope')
        if not cached.exists():
            outcome=old_outcome()
            if outcome and outcome[0]=='received' and outcome[1][0].get('sha256')==meta['sha256']:return received(*outcome[1],True)
            raise DiscoveryTransactionError('Committed receipt cache missing; no verifiable local response, no network repeat')
        return received(meta,cached.read_bytes(),True)
    if record['state']=='intent':
        outcome=old_outcome()
        if outcome is None:raise DiscoveryTransactionError('Previous discovery request uncertain; raw evidence/journal preserved, no automatic repeat')
        if outcome[0]=='received':return received(*outcome[1],True)
        record.update(state='failed',failures=record['failures']+1,retry_after=(dt.datetime.fromisoformat(outcome[1]['finished_at'])+dt.timedelta(minutes=10)).isoformat(),host_unavailable=outcome[1].get('host_unavailable',False));save()
    if record['state']=='failed':
        if record['failures']>=3:raise DiscoveryTransactionError('Discovery operation failed3times; review required, no automatic request')
        if utc_now()<dt.datetime.fromisoformat(record['retry_after']):
            error=PipelineError('Discovery operation transport backoff; no wire attempt');error.host_unavailable=record.get('host_unavailable',False);raise error
    record.update(state='intent',source_directory=source.relative_to(root).as_posix(),attempt_base=len(getattr(client,'attempts',[])),started_at=utc_now().isoformat());save()
    try:result,meta=call()
    except PipelineError as error:
        outcome=old_outcome()
        if outcome and outcome[0]=='received':
            # Received-but-unusable source must remain saved, not vanish into a retry.
            cache_bytes(outcome[1][0],outcome[1][1])
        if outcome is None:raise DiscoveryTransactionError('Request failed with uncertain durable outcome; no repeat') from error
        record.update(state='failed',failures=record['failures']+1,retry_after=(utc_now()+dt.timedelta(minutes=10)).isoformat(),last_error=str(error)[:250],host_unavailable=getattr(error,'host_unavailable',False));save();raise
    rawpath=source/Path(meta['file']).name
    # Decode exact bytes rather than trusting a different mutable returned object.
    return received(meta,rawpath.read_bytes(),False)
