"""Append-only saved-source observations; candidate facts never imply approval."""
from pathlib import Path
from .common import read_json,write_json,sha256_file,sha256_bytes,stable_json,utc_now,PipelineError
from .motion_state import motion_lock

class SourceRevisionConflict(PipelineError):
 pass

def digest(value):return sha256_bytes(stable_json(value).encode('utf-8'))
def baseline(store,id):
 root=Path(store.get(id)['run_dir'])
 return {'claims':read_json(root/'claims.json')['claims'],'sources':read_json(root/'sources.json')}
def state(store,id):
 folder=store.folder(id)/'source_revisions';base=baseline(store,id);previous=base;items=[]
 script=read_json(Path(store.get(id)['run_dir'])/'script.json');chain=digest(base)
 for path in sorted(folder.glob('*.json')) if folder.exists() else []:
  item=read_json(path)
  if digest(item['observation'])!=item['observation_hash']:raise PipelineError('Source history integrity mismatch')
  if item['previous_hash']!=chain:raise PipelineError('Source history chain mismatch')
  old={c['key']:c for c in previous['claims']};new={c['key']:c for c in item['observation']['claims']};changes=[]
  for key in sorted(old.keys()|new.keys()):
   a=old.get(key);b=new.get(key)
   if a==b:continue
   fields=[k for k in sorted((a or {}).keys()|(b or {}).keys()) if (a or {}).get(k)!=(b or {}).get(k)]
   related={key}|set((a or {}).get('related_claim_keys',[]))|set((b or {}).get('related_claim_keys',[]))
   scenes=[s['id'] for s in script.get('segments',[]) if related.intersection(s.get('claim_keys',[]))]
   details=script.get('description_details',[])
   description=any(any(k in stable_json(x) for k in related) for x in details) or bool(a and a.get('statement') and a['statement'] in script.get('description',''))
   changes.append({'claim_key':key,'before':a,'after':b,'changed_fields':fields,'affected_scenes':scenes,'description_affected':description,'status':'unreviewed_source_candidate'})
  item['source_reference_changed']=previous['sources']!=item['observation']['sources']
  item['changes']=changes;items.append(item);previous=item['observation'];chain=digest({'previous':chain,'observation':item['observation_hash'],'sequence':len(items)})
 from .connector_observations import status as connector_status
 path=store.folder(id)/'source_revision_decision.json';decision=read_json(path) if path.exists() else None
 return {'schema':'SOCIAL_SOURCE_HISTORY_V1','connector_observations':connector_status(store,id),'baseline_hash':digest(base),'latest_hash':chain,'latest_observation_hash':digest(previous),'history':items,'revision':sha256_file(path) if path.exists() else 'absent','decision':decision,'requires_review':bool(items),'manual_draft_preserved':(store.folder(id)/'manual_script_draft.json').exists(),'facts_approved':False,'publication_authorized':False}
def observe(store,id,expected_hash,observation,label):
 if not isinstance(label,str) or not label.strip() or len(label)>200:raise PipelineError('Source observation label required')
 if not isinstance(observation,dict) or set(observation)!={'claims','sources'}:raise PipelineError('Expected saved claims and sources only')
 if len(stable_json(observation))>1000000:raise PipelineError('Source observation too large')
 claims=observation['claims']
 if not isinstance(claims,list) or not claims or len(claims)>200:raise PipelineError('Bounded claim list required')
 keys=[]
 for c in claims:
  if not isinstance(c,dict) or not isinstance(c.get('key'),str) or not isinstance(c.get('statement'),str) or not isinstance(c.get('source'),dict):raise PipelineError('Each candidate needs key, statement and source reference')
  keys.append(c['key'])
 if len(keys)!=len(set(keys)):raise PipelineError('Duplicate claim identities')
 if not isinstance(observation['sources'],dict):raise PipelineError('Saved sources object required')
 with motion_lock(store.root,'sourcehistory_'+id,wait=5):
  current=state(store,id)
  if expected_hash!=current['latest_hash']:raise SourceRevisionConflict('Source version changed; reopen')
  value=digest(observation)
  if value==current['latest_observation_hash']:return current
  folder=store.folder(id)/'source_revisions';folder.mkdir(exist_ok=True)
  path=folder/('%06d.json'%(len(current['history'])+1))
  if path.exists():raise PipelineError('History identity collision')
  write_json(path,{'observation':observation,'observation_hash':value,'previous_hash':current['latest_hash'],'label':label.strip(),'at':utc_now().isoformat(),'source_reviewed':False})
 return state(store,id)
def decide(store,id,latest_hash,revision,decision,reviewer,reason):
 if decision not in {'deferred','correction_draft_required'}:raise PipelineError('Choose defer or correction draft; fact approval is separate')
 if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120 or not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise PipelineError('Reviewer and reason required')
 with motion_lock(store.root,'sourcehistory_'+id,wait=5):
  current=state(store,id)
  if latest_hash!=current['latest_hash'] or revision!=current['revision']:raise PipelineError('Source review changed; reopen')
  if not current['history']:raise PipelineError('No source revision to decide')
  folder=store.folder(id);path=folder/'source_revision_decision.json'
  if path.exists():
   history=folder/'source_revision_decision_history';history.mkdir(exist_ok=True)
   write_json(history/(current['revision']+'.json'),read_json(path))
  write_json(path,{'latest_hash':latest_hash,'decision':decision,'reviewer':reviewer.strip(),'reason':reason.strip(),'at':utc_now().isoformat(),'facts_approved':False})
 return state(store,id)
