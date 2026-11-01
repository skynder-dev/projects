"""Read-only integrity checks for saved editorial decision history.

No selection eligibility or source/context freshness is established here.
Full decision writes remain blocked on canonical source-binding integration.
"""
from .common import PipelineError,read_json,stable_json,sha256_bytes

def digest(value):return sha256_bytes(stable_json(value).encode('utf-8'))

def ledger(store,job):
 home=store.folder(job)/'concept_decisions';files=sorted((home/'events').glob('*.json'))
 if len(files)>1000:raise PipelineError('Concept decision history exceeds bound')
 events={};requests={}
 for p in files:
  e=read_json(p);h=digest(e)
  if e.get('job_id')!=job or e.get('scope')!='editorial_choice_only' or p.stem!=e.get('request_id') or e.get('approved') is not False:raise PipelineError('Concept decision history integrity mismatch')
  events[h]=e;requests[p.stem]=(h,e)
 head=read_json(home/'head.json') if (home/'head.json').exists() else {'revision':'absent'}
 revision=head['revision'];chain=[];seen=set();cursor=revision
 while cursor!='absent':
  if cursor in seen or cursor not in events:raise PipelineError('Concept decision chain integrity mismatch')
  seen.add(cursor);e=events[cursor];chain.append({'revision':cursor,**e});cursor=e['parent_revision']
 if len(seen)!=len(events):raise PipelineError('Uncommitted concept decision event; inspect uncertainty, no automatic retry')
 return home,revision,chain,requests
