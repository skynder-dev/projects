"""Explicit scope and scene-binding decisions; never edits accepted facts or narration."""
import copy
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,utc_now,stable_json,atomic_bytes
from .source_revisions import digest
from .fact_versions import view as fact_view,_version,_key
from .topic_rotation import snapshot
from .motion_state import motion_lock
from . import listing_claims

def _home(store,id):return store.folder(id)/'fact_reconciliation'
def _record(home,key):
 if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise PipelineError('Invalid reconciliation identity')
 p=home/'versions'/(key+'.json')
 if p.stat().st_size>8*1024*1024:raise PipelineError('Reconciliation record exceeds bounded size')
 record=read_json(p)
 if digest(record)!=key:raise PipelineError('Immutable reconciliation decision changed')
 return record
def _head(store,id):
 path=_home(store,id)/'head.json'
 if not path.exists():return None,'absent'
 if path.stat().st_size>65536:raise PipelineError('Reconciliation head exceeds bounded size')
 value=read_json(path);key=value.get('record')
 if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise PipelineError('Malformed reconciliation head; original preserved')
 record=_record(_home(store,id),key)
 if digest(record.get('context'))!=record.get('basis'):raise PipelineError('Reconciliation context differs from its immutable basis')
 return record,sha256_file(path)

def apply(accepted,projections,pairs,resolutions,bindings,script):
 if not isinstance(resolutions,list) or len(resolutions)!=len(pairs):raise PipelineError('Resolve every exact potential conflict; no omitted or extra decisions')
 bypair={p['pair_id']:p for p in pairs};decisions={}
 for action in resolutions:
  if not isinstance(action,dict) or set(action)!={'pair_id','decision','reason'} or action['pair_id'] not in bypair or action['pair_id'] in decisions or action['decision'] not in bypair[action['pair_id']]['choices'] or not isinstance(action['reason'],str) or not action['reason'].strip() or len(action['reason'])>2000:raise PipelineError('Each exact scope pair needs one supported decision and reason')
  decisions[action['pair_id']]=action
 excluded=set();additions=[];rawkeys={p['raw_key'] for p in projections};claims=[copy.deepcopy(c) for c in accepted if c['key'] not in rawkeys]
 for p in projections:
  related=[(pair,decisions[pair['pair_id']]) for pair in pairs if pair['candidate']==p['raw_key']]
  keep=[action['decision']=='keep_prior_exclude_candidate' for pair,action in related]
  if any(keep):
   if not all(keep):raise PipelineError('Candidate exclusion must agree across all of its related scopes')
   continue
  for pair,action in related:
   if action['decision']=='replace_prior_listing':
    if not pair['prior_is_same_listing_field']:raise PipelineError('A listing field cannot replace a primary claim')
    excluded.add(pair['prior'])
  additions.append(copy.deepcopy(p['typed_claim']))
 retained={pair['prior'] for pair in pairs if decisions[pair['pair_id']]['decision'] in {'keep_prior_exclude_candidate','retain_distinct_scopes'}}
 if excluded.intersection(retained):raise PipelineError('Conflicting decisions both remove and retain the same prior claim')
 claims=[c for c in claims if c['key'] not in excluded]+additions
 listing_claims.consistency(claims)
 by={c['key']:c for c in claims}
 if len(by)!=len(claims):raise PipelineError('Typed claim key collides with a retained prior claim; explicit same-field replacement required')
 segments=script.get('segments') or []
 if not isinstance(bindings,list) or len(bindings)!=len(segments):raise PipelineError('Explicit complete scene bindings required')
 bmap={}
 for binding in bindings:
  if not isinstance(binding,dict) or set(binding)!={'scene_id','claim_keys','listing_only'} or binding['scene_id'] in bmap or type(binding['listing_only']) is not bool:raise PipelineError('Malformed or duplicate scene binding')
  keys=binding['claim_keys']
  if not isinstance(keys,list) or not keys or any(not isinstance(k,str) or k not in by for k in keys) or len(keys)!=len(set(keys)):raise PipelineError('Scene binding uses missing, excluded, duplicate or unaccepted claims')
  bmap[binding['scene_id']]=binding
 if set(bmap)!={s['id'] for s in segments}:raise PipelineError('Scene identities changed before binding')
 result=copy.deepcopy(script)
 for scene in result['segments']:
  binding=bmap[scene['id']];keys=binding['claim_keys'];listing=[by[k] for k in keys if by[k].get('listing_scope')]
  if listing:
   if len(keys)!=1 or not binding['listing_only'] or scene['voiceover']!=listing[0]['statement']:raise PipelineError('Listing scene must explicitly clear track scope and speak its single exact attributed statement')
   scene['track_ids']=[]
  elif binding['listing_only']:raise PipelineError('Listing-only scope is valid only for an exact attributed listing claim')
  scene['claim_keys']=copy.deepcopy(keys)
 return claims,result

def view(store,id,draft):
 store=snapshot(store);facts=fact_view(store,id);accepted=copy.deepcopy(facts['_claims']);projections=[listing_claims.propose(store,id,c) for c in accepted if c['key'].startswith('connector_field_')];required=[];ancestor=facts['fact_version'];seen=set()
 while ancestor:
  if ancestor in seen or len(seen)>=100:raise PipelineError('Fact ancestry cycle or depth limit')
  seen.add(ancestor);m,_=_version(store,id,ancestor);required+=m.get('related_claim_scope_resolution_required',[]);ancestor=m.get('parent_fact_version')
 pairs=listing_claims.pairs(accepted,projections,required);rawkeys={p['raw_key'] for p in projections};blockers=[p['blocked_reason'] for p in projections if p.get('blocked_reason')]
 if any(p['candidate'] not in rawkeys for p in required):blockers.append('Related non-connector claims still need an independent sourced reconciliation')
 if not facts['fact_version']:blockers.append('Accepted immutable fact version required')
 if facts['pending_saves'] or any((c.get('last_decision') or {}).get('decision')!='reject' for c in facts['changes']):blockers.append('Resolve pending/deferred source facts first')
 context={'job_id':id,'fact_version':facts['fact_version'],'head_revision':facts['head_revision'],'source_revision':facts['source_revision'],'manual_revision':facts['manual_revision'],'draft_identity':draft['original'],'draft_revision':draft['revision'],'script':draft['script'],'projections':projections,'pairs':pairs};basis=digest(context);record,revision=_head(store,id);current=record is not None and record['basis']==basis;claims=accepted;script=copy.deepcopy(draft['script'])
 if current:
  expected=[{k:v for k,v in p.items() if k!='blocked_reason'} for p in projections]
  if digest(record['projections'])!=digest(expected) or digest(record['pairs'])!=digest(pairs):raise PipelineError('Saved interpretation or source-scope pairs differ from exact current evidence')
  if record['interpretations']!=sorted(rawkeys):raise PipelineError('Reconciliation does not cover exact accepted raw fields')
  claims,script=apply(accepted,record['projections'],pairs,record['resolutions'],record['bindings'],script)
 result={'schema':'SOCIAL_FACT_RECONCILIATION_VIEW_V1','job_id':id,'context':context,'basis':basis,'revision':revision,'version':digest({'basis':basis,'revision':revision}),'record':record,'record_current':current,'projections':projections,'pairs':pairs,'blocked_reasons':list(dict.fromkeys(blockers)),'requires_explicit_reconciliation':bool(projections or required),'prior_claims':[c for c in accepted if not c['key'].startswith('connector_field_')],'available_claims':[c for c in accepted if not c['key'].startswith('connector_field_')]+[p['typed_claim'] for p in projections if not p.get('blocked_reason')],'script':script,'_claims':claims,'scenario_approved':False,'publication_authorized':False}
 result['pending_saves']=[{'request_key':p.stem,'state':read_json(p)['state']} for p in sorted((_home(store,id)/'intents').glob('*.json')) if read_json(p)['state'] in {'prepared','published','conflict'}]
 result['history']=[];ancestor=record;seen=set()
 while ancestor:
  key=digest(ancestor)
  if key in seen or len(seen)>=100:raise PipelineError('Reconciliation history cycle or depth limit')
  seen.add(key);result['history'].append({'record_id':key,'reviewer':ancestor['reviewer'],'reason':ancestor['reason'],'at':ancestor['at'],'basis':ancestor['basis']});previous=ancestor.get('previous_record');ancestor=_record(_home(store,id),previous) if previous else None
 return result

def public(v):return {k:x for k,x in v.items() if not k.startswith('_')}

def save(store,id,draft_loader,expected_version,interpretations,resolutions,bindings,reviewer,reason,evidence_reviewed,request_key):
 store=snapshot(store);key=_key(request_key)
 if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120 or not isinstance(reason,str) or not reason.strip() or len(reason)>2000 or evidence_reviewed is not True:raise PipelineError('Explicit reviewer, reason and saved-source/scope attestation required')
 request={'version':expected_version,'interpretations':interpretations,'resolutions':resolutions,'bindings':bindings,'reviewer':reviewer,'reason':reason,'evidence_reviewed':True};request_hash=digest(request);home=_home(store,id);intentpath=home/'intents'/(key+'.json')
 with motion_lock(store.root,'scriptdraft_'+id,wait=5):
  with motion_lock(store.root,'fact_adoption_'+id,wait=5):
   with motion_lock(store.root,'sourcehistory_'+id,wait=5):
    old,revision=_head(store,id)
    if intentpath.exists():
     intent=read_json(intentpath)
     if intent['request_hash']!=request_hash:raise PipelineError('Request key belongs to another reconciliation')
     if intent['state']=='committed' or old and digest(old)==intent['record_id']:
      record=read_json(home/'versions'/(intent['record_id']+'.json'))
      if digest(record)!=intent['record_id']:raise PipelineError('Committed reconciliation changed')
      intent['state']='committed';write_json(intentpath,intent);result=public(view(store,id,draft_loader(store,id)));result['save_receipt']={'record_id':intent['record_id'],'head_is_current':old is not None and digest(old)==intent['record_id']};return result
     if intent['state']=='conflict':raise PipelineError('Historical reconciliation conflicts with newer source/manual/head')
    current=view(store,id,draft_loader(store,id))
    if current['version']!=expected_version:
     if intentpath.exists():intent['state']='conflict';write_json(intentpath,intent)
     raise PipelineError('Source, accepted facts, receipt, manual scenario or reconciliation head changed; reopen')
    if current['blocked_reasons']:raise PipelineError('; '.join(current['blocked_reasons']))
    if any(p['state'] in {'prepared','published'} and p['request_key']!=key for p in current['pending_saves']):raise PipelineError('Recover the pending exact reconciliation before another decision')
    rawkeys=sorted(p['raw_key'] for p in current['projections'])
    if not isinstance(interpretations,list) or sorted(interpretations)!=rawkeys or len(interpretations)!=len(set(interpretations)):raise PipelineError('Explicitly review every exact finite type projection')
    projected=[{k:v for k,v in p.items() if k!='blocked_reason'} for p in current['projections']]
    apply(fact_view(store,id)['_claims'],projected,current['pairs'],resolutions,bindings,current['context']['script'])
    if intentpath.exists():record=intent['record']
    else:record={'schema':'SOCIAL_FACT_RECONCILIATION_RECORD_V1','basis':current['basis'],'context':current['context'],'previous_record':digest(old) if old else None,'interpretations':sorted(interpretations),'projections':projected,'pairs':current['pairs'],'resolutions':resolutions,'bindings':bindings,'reviewer':reviewer.strip(),'reason':reason.strip(),'at':utc_now().isoformat(),'source_scope_reviewed':True,'scenario_approved':False,'concept_approved':False,'publication_authorized':False}
    record_id=digest(record);intent={'state':'prepared','request_hash':request_hash,'request':request,'record':record,'record_id':record_id};write_json(intentpath,intent)
    data=stable_json(record).encode()
    if len(data)>8*1024*1024:raise PipelineError('Reconciliation record exceeds8MiB')
    dest=home/'versions'/(record_id+'.json')
    if dest.exists():
     if digest(read_json(dest))!=record_id:raise PipelineError('Immutable reconciliation record changed')
    else:atomic_bytes(dest,data)
    intent['state']='published';write_json(intentpath,intent);write_json(home/'head.json',{'record':record_id,'previous_revision':revision});intent['state']='committed';write_json(intentpath,intent)
    return public(view(store,id,draft_loader(store,id)))

def recover(store,id,draft_loader,request_key):
 key=_key(request_key);intent=read_json(_home(store,id)/'intents'/(key+'.json'));r=intent['request']
 return save(store,id,draft_loader,r['version'],r['interpretations'],r['resolutions'],r['bindings'],r['reviewer'],r['reason'],True,key)

def verify_record(root,record,accepted,prior):
 if record.get('schema')!='SOCIAL_FACT_RECONCILIATION_RECORD_V1' or record.get('source_scope_reviewed') is not True or any(record.get(k) is not False for k in ('scenario_approved','concept_approved','publication_authorized')):raise PipelineError('Invalid source-scope reconciliation flags')
 if digest(record['context'])!=record['basis']:raise PipelineError('Reconciliation exact context changed')
 by={c['key']:c for c in accepted};projected=[]
 for p in record['projections']:
  rawclaim=by.get(p['raw_key'])
  if rawclaim!=p['raw_claim']:raise PipelineError('Reconciliation projected a different accepted raw claim')
  from .fact_versions import _relative
  rawpath=(Path(root)/_relative(rawclaim['source']['snapshot_file'])).resolve()
  if not rawpath.is_relative_to(Path(root).resolve()) or rawpath.stat().st_size>8*1024*1024:raise PipelineError('Reconciliation evidence escapes source scope or size bound')
  raw=rawpath.read_bytes();current=listing_claims.convert(rawclaim,raw,p['receipt'],p['opportunity_id'])
  if digest(current)!=digest(p):raise PipelineError('Deterministic typed projection changed')
  projected.append(current)
 if record['interpretations']!=sorted(c['key'] for c in accepted if c['key'].startswith('connector_field_')):raise PipelineError('Accepted raw field coverage differs')
 # Pair IDs bind both exact before/after claims, including all explicit historical related pairs.
 required=[{'candidate':p['candidate'],'retained_claim':p['prior']} for p in record['pairs']]
 pairs=listing_claims.pairs(accepted,projected,required)
 if pairs!=record['pairs']:raise PipelineError('Reconciliation source-scope pairs changed')
 return apply(accepted,projected,pairs,record['resolutions'],record['bindings'],prior)
