"""Read-only integrity checks for saved editorial decision history.

No selection eligibility or source/context freshness is established here.
Saved trial choices use the same verifier on events embedded in the committed
ConceptStore revision chain. They do not grant publication or source approval.
"""
from .common import PipelineError,read_json,stable_json,sha256_bytes

def digest(value):return sha256_bytes(stable_json(value).encode('utf-8'))

def ledger(store,job):
 home=store.folder(job)/'concept_decisions';files=sorted((home/'events').glob('*.json'))
 if len(files)>1000:raise PipelineError('Concept decision history exceeds bound')
 events=[(p.stem,read_json(p)) for p in files]
 head=read_json(home/'head.json') if (home/'head.json').exists() else {'revision':'absent'}
 revision,chain,requests=verify_events(job,events,head['revision'])
 return home,revision,chain,requests

def verify_events(job,items,revision):
 """Verify a complete committed event set, without writing or granting approval."""
 if len(items)>1000:raise PipelineError('Concept decision history exceeds bound')
 events={};requests={}
 for request_id,e in items:
  h=digest(e)
  if e.get('job_id')!=job or e.get('scope')!='editorial_choice_only' or request_id!=e.get('request_id') or e.get('approved') is not False or request_id in requests:raise PipelineError('Concept decision history integrity mismatch')
  events[h]=e;requests[request_id]=(h,e)
 chain=[];seen=set();cursor=revision
 while cursor!='absent':
  if cursor in seen or cursor not in events:raise PipelineError('Concept decision chain integrity mismatch')
  seen.add(cursor);e=events[cursor];chain.append({'revision':cursor,**e});cursor=e['parent_revision']
 if len(seen)!=len(events):raise PipelineError('Uncommitted concept decision event; inspect uncertainty, no automatic retry')
 return revision,chain,requests
