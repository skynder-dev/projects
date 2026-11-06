"""Explicit per-change saved-evidence review into immutable, non-production fact versions."""
import copy,uuid,shutil
from pathlib import Path
from .common import read_json,write_json,sha256_file,sha256_bytes,atomic_bytes,PipelineError,utc_now
from .source_revisions import state as source_state,baseline,digest
from .topic_rotation import snapshot
from .motion_state import motion_lock

def _sha_key(value):
 if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise PipelineError('Invalid immutable review identity')
 return value
def _relative(value):
 if not isinstance(value,str) or Path(value).is_absolute() or '..' in Path(value).parts or ':' in value or value.startswith(('\\','/')):raise PipelineError('Evidence locator must stay within owned relative source scope')
 return value
def _home(store,id):return store.folder(id)/'fact_adoption'
def _manual(store,id):
 p=store.folder(id)/'manual_script_draft.json';return sha256_file(p) if p.exists() else 'absent'
def _head(store,id):
 p=_home(store,id)/'head.json'
 if not p.exists():return {'fact_version':None,'batch':None},'absent'
 value=read_json(p)
 if not isinstance(value,dict) or 'fact_version' not in value or not value.get('batch'):raise PipelineError('Fact head is malformed; preserved without falling back to the original ledger')
 _sha_key(value['batch'])
 if value['fact_version'] is not None:_sha_key(value['fact_version'])
 return value,sha256_file(p)
def _version(store,id,key):
 if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise PipelineError('Invalid fact version identity')
 folder=_home(store,id)/'versions'/key;manifest=read_json(folder/'manifest.json')
 if digest({k:v for k,v in manifest.items() if k!='fact_version'})!=key:raise PipelineError('Fact version manifest identity mismatch')
 for item in manifest['files']:
  p=(folder/_relative(item['path'])).resolve()
  if not p.is_relative_to(folder.resolve()) or not p.is_file() or sha256_file(p)!=item['sha256']:raise PipelineError('Immutable fact version changed or missing')
 return manifest,read_json(folder/'claims.json')['claims']
def _proofs(store,id,claim):
 if claim is None:return [],'Removal requires an explicit sourced replacement; omission alone is not accepted'
 source=claim.get('source') or {};refs=[source]+list(source.get('field_sources') or [])+list(source.get('supporting_sources') or []);proofs=[];root=Path(store.get(id)['run_dir']).resolve()
 for ref in refs:
  name=ref.get('snapshot_file') or ref.get('file');sha=ref.get('snapshot_sha256') or ref.get('sha256')
  if not name or not sha:continue
  try:_relative(name)
  except PipelineError as error:return [],str(error)
  if len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):return [],'Invalid saved evidence hash'
  candidates=[root/name,store.root/name];found=None
  for path in candidates:
   path=path.resolve();allowed=path.is_relative_to(root) or path.is_relative_to((store.root/'connector_observation_inbox').resolve())
   if allowed and path.suffix.lower() in {'.json','.html','.htm','.pdf','.txt','.raw'} and path.is_file() and sha256_file(path)==sha:found=path;break
  if found is None:return [],'Saved evidence bytes unavailable or hash mismatch: '+str(name)
  if all(x['sha256']!=sha for x in proofs):proofs.append({'sha256':sha,'source_path':str(found),'source_url':source.get('url'),'original_locator':name,'storage_scope':'run' if found.is_relative_to(root) else 'inbox','relative_path':found.relative_to(root if found.is_relative_to(root) else store.root).as_posix()})
 if not proofs:return [],'No byte-verifiable saved evidence for this candidate'
 return proofs,None

def view(store,id):
 store=snapshot(store);job=store.get(id)
 if not(job.get('preparation_integrity_pass') is True or job.get('package_integrity_pass') is True):raise PipelineError('Verified original source/script required for fact review')
 source=source_state(store,id);base=baseline(store,id);head,revision=_head(store,id);claims=base['claims'];manifest=None
 if head['fact_version']:
  manifest,claims=_version(store,id,head['fact_version'])
  if manifest['base_claims_sha256']!=sha256_file(Path(job['run_dir'])/'claims.json'):raise PipelineError('Fact version belongs to another immutable base ledger; preserved without adoption')
 candidate=source['history'][-1]['observation']['claims'] if source['history'] else base['claims'];old={c['key']:c for c in claims};new={c['key']:c for c in candidate};script=read_json(Path(job['run_dir'])/'script.json');changes=[]
 prior={};batch_key=head.get('batch');visited=set();reviews=[]
 while batch_key:
  if batch_key in visited:raise PipelineError('Fact review history cycle')
  visited.add(batch_key);batch=read_json(_home(store,id)/'batches'/(_sha_key(batch_key)+'.json'))
  if digest(batch)!=batch_key:raise PipelineError('Immutable fact review history changed')
  reviews.append(batch);batch_key=batch.get('previous_batch')
 for batch in reversed(reviews):
  if batch.get('source_revision')==source['latest_hash']:prior.update({x['change_id']:x for x in batch['decisions']})
 for key in sorted(old.keys()|new.keys()):
  a=old.get(key);b=new.get(key)
  if a==b:continue
  related={key}|set((a or {}).get('related_claim_keys',[]))|set((b or {}).get('related_claim_keys',[]));scenes=[s['id'] for s in script.get('segments',[]) if related.intersection(s.get('claim_keys',[]))]
  proof,blocked=_proofs(store,id,b);change_id=digest({'source_revision':source['latest_hash'],'claim_key':key,'before':a,'after':b})
  changes.append({'change_id':change_id,'claim_key':key,'before':a,'after':b,'affected_scenes':scenes,'description_affected':any(d.get('claim_key') in related for d in script.get('description_details',[])) or bool(a and a.get('statement') and a['statement'] in script.get('description','')),'proofs':proof,'acceptance_blocker':blocked,'last_decision':prior.get(change_id),'related_existing_claims':[old[k] for k in related-{key} if k in old]})
 pending=[]
 home=_home(store,id)
 for p in sorted((home/'intents').glob('*.json')):
  intent=read_json(p)
  if intent['state'] in {'prepared','published','conflict'}:pending.append({'request_key':p.stem,'state':intent['state'],'reason':intent.get('conflict_reason')})
 result={'schema':'SOCIAL_FACT_ADOPTION_V1','job_id':id,'head_revision':revision,'fact_version':head['fact_version'],'manifest':manifest,'source_revision':source['latest_hash'],'manual_revision':_manual(store,id),'changes':changes,'pending_saves':pending,'review_history':reviews,'script_revalidation_required':bool(head['fact_version']),'new_concept_approval_required':bool(head['fact_version']),'live_currentness_confirmed':False,'scenario_approved':False,'publication_authorized':False,'_claims':claims}
 result['version']=digest({k:v for k,v in result.items() if k not in {'_claims','version','pending_saves'}})
 return result

def public(value):return {k:v for k,v in value.items() if not k.startswith('_')}
def _key(value):
 try:return uuid.UUID(str(value)).hex
 except (ValueError,TypeError,AttributeError):raise PipelineError('Fact save needs a UUID request key')
def _publish(store,id,home,intent):
 key=intent.get('fact_version')
 if not key:return
 destination=home/'versions'/key
 if destination.exists():return
 temp=home/('partial_'+intent['request_key']);temp.mkdir(exist_ok=True,parents=True)
 for entry in intent['evidence']:
  root=Path(store.get(id)['run_dir']).resolve();source=((root if entry['storage_scope']=='run' else store.root)/_relative(entry['relative_path'])).resolve()
  if not (source.is_relative_to(root) or source.is_relative_to((store.root/'connector_observation_inbox').resolve())):raise PipelineError('Recovery evidence escapes owned Social source scope')
  data=source.read_bytes()
  if sha256_bytes(data)!=entry['sha256']:raise PipelineError('Bound saved evidence changed during recovery')
  atomic_bytes(temp/'evidence'/entry['sha256'],data)
 write_json(temp/'claims.json',{'claims':intent['claims']});write_json(temp/'review.json',intent['review_record']);write_json(temp/'evidence.json',intent['evidence'])
 files=[{'path':p.relative_to(temp).as_posix(),'sha256':sha256_file(p),'bytes':p.stat().st_size} for p in sorted(temp.rglob('*')) if p.is_file() and p.name!='manifest.json']
 files.sort(key=lambda item:item['path'])
 manifest={**intent['manifest_payload'],'files':files}
 if digest(manifest)!=key:raise PipelineError('Fact version materialization identity changed; nothing promoted')
 write_json(temp/'manifest.json',{**manifest,'fact_version':key});destination.parent.mkdir(exist_ok=True);temp.rename(destination)

def _recover_locked(store,id,key):
 home=_home(store,id);p=home/'intents'/(key+'.json');intent=read_json(p);head,revision=_head(store,id);_sha_key(intent['batch_id'])
 if intent['state']=='committed':
  batch=read_json(home/'batches'/(intent['batch_id']+'.json'))
  if digest(batch)!=intent['batch_id']:raise PipelineError('Committed fact decision changed')
  if intent.get('fact_version'):_version(store,id,intent['fact_version'])
  result=public(view(store,id));result['save_receipt']={'state':'committed','batch':intent['batch_id'],'fact_version':intent.get('fact_version'),'head_is_current':head.get('batch')==intent['batch_id']};return result
 if head.get('batch')==intent['batch_id']:
  if head.get('fact_version'):_version(store,id,head['fact_version'])
  intent['state']='committed';write_json(p,intent);return public(view(store,id))
 if intent['state']=='conflict':raise PipelineError('Interrupted save has a newer source/manual/head conflict; reopen and make a new explicit decision')
 current=source_state(store,id)
 if revision!=intent['expected_head'] or current['latest_hash']!=intent['source_revision'] or _manual(store,id)!=intent['manual_revision']:
  intent['state']='conflict';intent['conflict_reason']='Source, manual draft or fact head changed before commit; old prepared version preserved without promotion';write_json(p,intent);raise PipelineError(intent['conflict_reason'])
 _publish(store,id,home,intent)
 if intent.get('fact_version'):_version(store,id,intent['fact_version'])
 intent['state']='published';write_json(p,intent)
 batch_path=home/'batches'/(intent['batch_id']+'.json')
 if batch_path.exists():
  if digest(read_json(batch_path))!=intent['batch_id']:raise PipelineError('Immutable fact review batch differs; not overwritten')
 else:write_json(batch_path,intent['review_record'])
 write_json(home/'head.json',{'fact_version':intent.get('fact_version') or head.get('fact_version'),'batch':intent['batch_id'],'previous_head_revision':revision})
 intent['state']='committed';write_json(p,intent)
 return public(view(store,id))

def _recover(store,id,request_key):
 store=snapshot(store)
 key=_key(request_key)
 with motion_lock(store.root,'fact_adoption_'+id,wait=5):
  with motion_lock(store.root,'sourcehistory_'+id,wait=5):return _recover_locked(store,id,key)

def _commit(store,id,expected_version,source_revision,manual_revision,actions,reviewer,reason,evidence_reviewed,request_key):
 store=snapshot(store)
 key=_key(request_key)
 if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120 or not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise PipelineError('Fact review requires reviewer and reason')
 if not isinstance(actions,list) or not actions or len(actions)>200:raise PipelineError('Choose bounded individual change decisions')
 request={'version':expected_version,'source_revision':source_revision,'manual_revision':manual_revision,'actions':actions,'reviewer':reviewer,'reason':reason,'evidence_reviewed':evidence_reviewed is True};request_hash=digest(request)
 with motion_lock(store.root,'fact_adoption_'+id,wait=5):
  with motion_lock(store.root,'sourcehistory_'+id,wait=5):
   home=_home(store,id);p=home/'intents'/(key+'.json')
   if p.exists():
    if read_json(p)['request_hash']!=request_hash:raise PipelineError('Request key already belongs to another fact decision')
    return _recover_locked(store,id,key)
   current=view(store,id)
   if current['version']!=expected_version or current['source_revision']!=source_revision or current['manual_revision']!=manual_revision:raise PipelineError('Source, fact view or manual draft changed; reopen before accepting facts')
   if any(x['state'] in {'prepared','published'} for x in current['pending_saves']):raise PipelineError('Recover the pending fact save before starting another')
   changes={c['change_id']:c for c in current['changes']};seen=set();claims={c['key']:copy.deepcopy(c) for c in current['_claims']};decisions=[];accepted=[];proofs=[]
   for action in actions:
    if not isinstance(action,dict) or set(action)!={'change_id','decision','reason'} or action['change_id'] not in changes or action['change_id'] in seen:raise PipelineError('Unknown or duplicate exact change decision')
    seen.add(action['change_id']);change=changes[action['change_id']]
    if action['decision'] not in {'accept','defer','reject'} or not isinstance(action['reason'],str) or not action['reason'].strip() or len(action['reason'])>2000:raise PipelineError('Each change needs an explicit decision and reason')
    if action['decision']=='accept':
     if evidence_reviewed is not True:raise PipelineError('Accepting facts requires explicit saved-evidence review attestation')
     if change['acceptance_blocker']:raise PipelineError(change['acceptance_blocker'])
     claims[change['claim_key']]=copy.deepcopy(change['after']);accepted.append(change['claim_key']);proofs+=change['proofs']
    decisions.append({**action,'claim_key':change['claim_key'],'before':change['before'],'after':change['after'],'affected_scenes':change['affected_scenes'],'description_affected':change['description_affected'],'related_existing_claims':change['related_existing_claims']})
   stamp=utc_now().isoformat();review={'schema':'SOCIAL_FACT_REVIEW_BATCH_V1','request_key':key,'source_revision':source_revision,'manual_revision':manual_revision,'parent_fact_version':current['fact_version'],'previous_batch':_head(store,id)[0].get('batch'),'decisions':decisions,'reviewer':reviewer.strip(),'reason':reason.strip(),'saved_evidence_reviewed':evidence_reviewed is True,'at':stamp,'scenario_approved':False,'concept_approval_inherited':False,'publication_authorized':False};batch_id=digest(review)
   proofs=list({x['sha256']:x for x in proofs}.values())
   if sum(Path(x['source_path']).stat().st_size for x in proofs)>64*1024*1024:raise PipelineError('Fact batch saved evidence exceeds64MiB; split the review')
   values=list(claims.values());payload={'schema':'SOCIAL_IMMUTABLE_FACT_VERSION_V1','parent_fact_version':current['fact_version'],'base_claims_sha256':sha256_file(Path(store.get(id)['run_dir'])/'claims.json'),'source_revision':source_revision,'manual_revision_reference':manual_revision,'review_batch':batch_id,'accepted_claim_keys':accepted,'related_claim_scope_resolution_required':[{'candidate':d['claim_key'],'retained_claim':c['key']} for d in decisions if d['decision']=='accept' for c in d['related_existing_claims']],'affected_scenes':sorted({scene for d in decisions if d['decision']=='accept' for scene in d['affected_scenes']}),'description_revalidation_required':bool(accepted),'scenario_approved':False,'new_concept_approval_required':True,'live_currentness_confirmed':False,'publication_authorized':False}
   intent={'state':'prepared','request_key':key,'request_hash':request_hash,'source_revision':source_revision,'manual_revision':manual_revision,'expected_head':current['head_revision'],'batch_id':batch_id,'review_record':review,'claims':values,'evidence':proofs,'manifest_payload':payload,'fact_version':None}
   if accepted:
    # Identity is computed from exact future file bytes, independent of partial-directory paths.
    from .common import stable_json
    files=[]
    for name,value in [('claims.json',{'claims':values}),('review.json',review),('evidence.json',proofs)]:
     data=stable_json(value).encode('utf-8');files.append({'path':name,'sha256':sha256_bytes(data),'bytes':len(data)})
    for proof in proofs:files.append({'path':'evidence/'+proof['sha256'],'sha256':proof['sha256'],'bytes':Path(proof['source_path']).stat().st_size})
    intent['fact_version']=digest({**payload,'files':sorted(files,key=lambda f:f['path'])})
   write_json(p,intent)
   return _recover_locked(store,id,key)


def recover(store,id,request_key):
 with motion_lock(store.root,'scriptdraft_'+id,wait=5):return _recover(store,id,request_key)

def commit(store,id,expected_version,source_revision,manual_revision,actions,reviewer,reason,evidence_reviewed,request_key):
 with motion_lock(store.root,'scriptdraft_'+id,wait=5):
  return _commit(store,id,expected_version,source_revision,manual_revision,actions,reviewer,reason,evidence_reviewed,request_key)
