"""Source-only child preparations from exact accepted facts and saved scenario text."""
import copy,json,uuid,shutil,time
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,sha256_bytes,atomic_bytes,stable_json
from .source_revisions import digest
from .fact_versions import view as fact_view,_version,_relative,_key
from .motion_state import motion_lock
from .preparation import verify_preparation
from .topic_rotation import snapshot

CONTRACT='SOCIAL_FACT_RECONCILED_SOURCE_V1'
HOLD='Source-only materialization: separate exact concept approval, current source check and authorized measured production required'

def validate(script,claims):
 errors=[];segments=script.get('segments') or []
 if not 4<=len(segments)<=10:errors.append('Reconciled source scenario needs4..10scenes')
 if not 25<=sum(len(s.get('voiceover','').split()) for s in segments)<=170:errors.append('Reconciled source scenario needs25..170words; duration remains unmeasured')
 ids=[s.get('id') for s in segments]
 if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):errors.append('Unique source scene identities required')
 from .meaning_review import accent_issues
 from .narrative_checks import screen_field
 for s in segments:
  voice=s.get('voiceover','');screen=s.get('on_screen') or {};accent=screen.get('headline');anchor=s.get('screen_anchor') or {};a,b=anchor.get('start_char'),anchor.get('end_char')
  if not isinstance(accent,str) or not accent or len(accent.split())>9 or not isinstance(a,int) or not isinstance(b,int) or not 0<=a<b<=len(voice) or voice[a:b]!=accent or anchor.get('text')!=accent:errors.append('Exact short spoken screen span required: '+str(s.get('id')))
  else:errors+=accent_issues(voice,accent)
  if isinstance(accent,str) and not screen_field(accent)['preparation_valid']:errors.append('Visible wording/staging separation requires review: '+str(s.get('id')))
  if any(screen.get(k) for k in ('kicker','sub','big')):errors.append('Unspoken screen extras are not allowed')
  listed=[c for c in claims if c.get('listing_scope') and c['key'] in s.get('claim_keys',[])]
  if listed and (len(s.get('claim_keys',[]))!=1 or len(listed)!=1 or voice!=listed[0]['statement'] or s.get('track_ids')):errors.append('Listing evidence requires its exact attributed statement without inherited track scope')
 keys=[c.get('key') for c in claims]
 if len(keys)!=len(set(keys)):errors.append('Duplicate fact keys')
 details=script.get('description_details') or []
 if {d.get('claim_key') for d in details}!=set(keys) or len(details)!=len(keys):errors.append('All accepted active facts and conditions must remain in the description')
 by={c['key']:c for c in claims}
 for d in details:
  c=by.get(d.get('claim_key'))
  if not c or d.get('text')!=c.get('statement') or d.get('source')!=c.get('source'):errors.append('Description is not exactly bound to accepted facts')
 if script.get('production_status')!='source_only_new_concept_required':errors.append('Source materialization cannot authorize production')
 return errors

def board(script):
 return {'schema':'SOCIAL_RECONCILED_SOURCE_STORYBOARD_V1','timing_status':'unmeasured_no_audio','scenes':[{'id':s['id'],'voiceover':s['voiceover'],'on_screen':s['on_screen'],'screen_anchor':s['screen_anchor'],'claim_keys':s['claim_keys'],'track_ids':s.get('track_ids',[])} for s in script['segments']],'models_started':False,'production_authorized':False}

def preview(store,id,draft):
 store=snapshot(store)
 job=store.get(id);root=Path(job['run_dir']);facts=fact_view(store,id);blockers=[]
 if not facts['fact_version']:blockers.append('Accept an immutable saved-evidence fact version first')
 if facts['pending_saves']:blockers.append('Finish or resolve interrupted fact saves first')
 if any((c.get('last_decision') or {}).get('decision')!='reject' for c in facts['changes']):blockers.append('Every remaining source difference needs an explicit rejection or acceptance; deferred changes remain unresolved')
 from .fact_reconciliation import view as reconciliation_view
 reconciliation=reconciliation_view(store,id,draft)
 if reconciliation['record_current']:
  claims=copy.deepcopy(reconciliation['_claims']);effective_script=reconciliation['script']
 else:
  claims=copy.deepcopy(facts['_claims']);effective_script=draft['script']
  if reconciliation['requires_explicit_reconciliation'] or reconciliation['record'] is not None:blockers.append('Exact typed source-scope and scene reconciliation required; reopen stale decisions')
 blockers+=reconciliation['blocked_reasons']
 if any(c['key'].startswith('connector_field_') for c in claims):blockers.append('Raw connector fields require exact typed source-scope reconciliation before preparation')
 original=read_json(root/'script.json');script=copy.deepcopy(effective_script)
 # Keep manual narration/accents exactly. Quarantine all old editorial projections.
 reference={k:v for k,v in script.items() if k not in {'segments','title','description','synthetic'}}
 script={k:copy.deepcopy(script[k]) for k in ('segments','title','synthetic') if k in script}
 script.update(editorial_contract=CONTRACT,production_status='source_only_new_concept_required',description_detail_policy='all_active_fact_claims_v1',description_details=[{'claim_key':c['key'],'text':c['statement'],'source':c['source']} for c in claims],description=draft['script'].get('description',''),fact_version=facts['fact_version'],prior_editorial_metadata_reference=reference,spoken_delivery={'post_atempo':1.0})
 from .claims import validate_script
 errors=validate_script(script,claims)
 if errors:blockers+=errors
 from .source_description import compose
 topic=read_json(root/'topic.json');record=copy.deepcopy(topic.get('selected',topic))
 for key in ('editorial_brief','primary_conditions','track_conditions'):record.pop(key,None)
 try:description=compose(script,claims,record)
 except (PipelineError,ValueError,TypeError,KeyError) as error:description='';blockers.append(str(error))
 identity={'parent_job_id':id,'parent_identity':draft['original'],'source_revision':facts['source_revision'],'fact_version':facts['fact_version'],'head_revision':facts['head_revision'],'fact_view_version':facts['version'],'manual_revision':facts['manual_revision'],'draft_revision':draft['revision'],'reconciliation_record_id':digest(reconciliation['record']) if reconciliation['record_current'] else None,'reconciliation_revision':reconciliation['revision'],'reconciliation_record':reconciliation['record'] if reconciliation['record_current'] else None,'script':script,'claims':claims,'description':description}
 result={'schema':'SOCIAL_SOURCE_MATERIALIZATION_PREVIEW_V1',**identity,'blocked_reasons':list(dict.fromkeys(blockers)),'ready_to_materialize':not blockers,'scenario_approved':False,'production_authorized':False,'publication_authorized':False,'models_started':False,'original_narration_preserved':all(a['voiceover']==b['voiceover'] and a.get('on_screen')==b.get('on_screen') for a,b in zip(draft['script']['segments'],script['segments']))}
 result['version']=digest(result)
 result['pending_materializations']=[]
 for p in sorted((store.folder(id)/'source_materializations').glob('*.json')):
  intent=read_json(p)
  if intent.get('state') in {'prepared','published','conflict'}:result['pending_materializations'].append({'request_key':p.stem,'state':intent['state'],'reason':intent.get('conflict_reason')})
 return result

def _copy_file(src,dest,expected=None):
 if src.stat().st_size>128*1024*1024:raise PipelineError('Source evidence file exceeds128MiB bound')
 data=src.read_bytes()
 if expected and sha256_bytes(data)!=expected:raise PipelineError('Bound source evidence changed')
 if dest.exists():
  if dest.read_bytes()!=data:raise PipelineError('Two source versions use the same locator with different bytes; explicit relocation required')
 else:atomic_bytes(dest,data)

def _build(store,id,current,temp):
 parent=Path(store.get(id)['run_dir']).resolve();parent_manifest=read_json(parent/('prepared.json' if (parent/'prepared.json').exists() else 'package_manifest.json'))
 parent_is_fact_source=parent_manifest.get('mode')=='source_only_fact_materialization'
 source_prefixes=('source/','source_recheck/','connector_observation_inbox/')
 size=sum(e['bytes'] for e in parent_manifest['files'] if e['path'].startswith(source_prefixes))
 if parent_is_fact_source:size+=sum(e['bytes'] for e in parent_manifest['files'])+(parent/'prepared.json').stat().st_size
 if size>120*1024*1024:raise PipelineError('Parent source provenance exceeds bounded preparation budget')
 ancestor=current['fact_version'];bounded=set()
 while ancestor:
  if ancestor in bounded or len(bounded)>=100:raise PipelineError('Fact ancestry cycle or review depth exceeds100')
  bounded.add(ancestor);am,_=_version(store,id,ancestor);size+=2*sum(e['bytes'] for e in am['files'])
  if size>120*1024*1024:raise PipelineError('Source evidence and fact ancestry exceed bounded preparation budget')
  ancestor=am.get('parent_fact_version')
 # Copy only sealed source inputs, never old media, concept approvals or tasks.
 for entry in parent_manifest['files']:
  name=_relative(entry['path'])
  if name.startswith(source_prefixes):_copy_file(parent/name,temp/name,entry['sha256'])
  if parent_is_fact_source:_copy_file(parent/name,temp/'lineage/parent_preparation'/name,entry['sha256'])
 if parent_is_fact_source:_copy_file(parent/'prepared.json',temp/'lineage/parent_preparation/prepared.json')
 key=current['fact_version'];manifest,accepted=_version(store,id,key);claims=current['claims'];factroot=store.folder(id)/'fact_adoption/versions'/key
 ancestor=key;seen=set()
 while ancestor:
  if ancestor in seen:raise PipelineError('Fact ancestry cycle')
  seen.add(ancestor);am,_=_version(store,id,ancestor);aroot=store.folder(id)/'fact_adoption/versions'/ancestor;target=temp/('lineage/fact_version' if ancestor==key else 'lineage/fact_ancestors/'+ancestor)
  for entry in am['files']:_copy_file(aroot/_relative(entry['path']),target/_relative(entry['path']),entry['sha256'])
  _copy_file(aroot/'manifest.json',target/'manifest.json')
  for proof in read_json(aroot/'evidence.json'):
   # Only locators used by the current ledger become active source bytes. Older
   # conflicting snapshots remain in immutable ancestor evidence directories.
   active=any(proof['sha256']==ref.get('snapshot_sha256',ref.get('sha256')) and proof['original_locator']==ref.get('snapshot_file',ref.get('file')) for c in accepted for ref in [c.get('source') or {}]+list((c.get('source') or {}).get('field_sources') or [])+list((c.get('source') or {}).get('supporting_sources') or []))
   if active or proof['original_locator'].startswith('connector_observation_inbox/'):_copy_file(aroot/'evidence'/proof['sha256'],temp/_relative(proof['original_locator']),proof['sha256'])
  ancestor=am.get('parent_fact_version')
 for name in ('sources.json','topic.json','preparation_config.json'):
  if (parent/name).is_file():_copy_file(parent/name,temp/name)
 if not (temp/'preparation_config.json').exists():raise PipelineError('Parent configuration snapshot missing; no inferred configuration')
 topic=read_json(temp/'topic.json');selected=topic.get('selected',topic)
 write_json(temp/'lineage/parent_topic.json',topic)
 # Stale parsed projections stay in lineage only, not active source metadata.
 for k in ('editorial_brief','primary_conditions','track_conditions'):
  selected.pop(k,None)
 selected['source_materialization']={'fact_version':key,'source_revision':current['source_revision'],'semantic_projection_status':'not_recomputed_no_eligibility_or_audience_inference'}
 write_json(temp/'topic.json',topic)
 if current.get('reconciliation_record'):
  from .fact_reconciliation import _record,_home
  write_json(temp/'lineage/reconciliation.json',current['reconciliation_record']);ancestor=current['reconciliation_record'];seen=set();total=0
  while ancestor:
   rid=digest(ancestor)
   if rid in seen or len(seen)>=100:raise PipelineError('Reconciliation history cycle/depth')
   seen.add(rid);data=stable_json(ancestor).encode();total+=len(data)
   if total>64*1024*1024:raise PipelineError('Reconciliation history exceeds64MiB')
   atomic_bytes(temp/'lineage/reconciliation_history'/(rid+'.json'),data);previous=ancestor.get('previous_record');ancestor=_record(_home(store,id),previous) if previous else None
 write_json(temp/'claims.json',{'claims':claims});write_json(temp/'script.json',current['script']);write_json(temp/'storyboard.json',board(current['script']));atomic_bytes(temp/'description.md',current['description'].encode('utf-8'))
 for name in ('script.json','claims.json'):_copy_file(parent/name,temp/'lineage/parent'/name)
 manual=store.folder(id)/'manual_script_draft.json'
 if manual.exists():_copy_file(manual,temp/'lineage/manual_script_draft.json',current['manual_revision'])
 from .source_revisions import state
 write_json(temp/'lineage/source_history.json',state(store,id))
 from .fact_versions import view,public
 write_json(temp/'lineage/fact_review.json',public(view(store,id)))
 write_json(temp/'source_materialization.json',{k:v for k,v in current.items() if k not in {'script','claims','description','blocked_reasons','ready_to_materialize','pending_materializations','reconciliation_record'}})
 write_json(temp/'production_plan.json',{'schema':'SOCIAL_SOURCE_ONLY_PLAN_V1','tasks':[],'ready_for_generation':False,'generation_blockers':[HOLD],'accepted':False,'model_execution_started':False,'production_authorized':False,'publication_authorized':False})
 entries=[{'path':p.relative_to(temp).as_posix(),'bytes':p.stat().st_size,'sha256':sha256_file(p)} for p in sorted(temp.rglob('*')) if p.is_file()]
 if sum(e['bytes'] for e in entries)>128*1024*1024:raise PipelineError('Source preparation exceeds128MiB bound')
 identity=sha256_bytes('\n'.join(e['path']+' '+e['sha256'] for e in entries).encode())
 write_json(temp/'prepared.json',{'schema':'SOCIAL_PREPARATION_V1','preparation_id':identity,'mode':'source_only_fact_materialization','accepted':False,'model_execution_started':False,'ready_for_generation':False,'generation_blockers':[HOLD],'files':entries})
 verify_preparation(temp);verify_materialization(temp);return identity

def verify_materialization(directory):
 root=Path(directory).resolve();lineage=read_json(root/'source_materialization.json');key=lineage['fact_version'];seen=set();ancestor=key
 while ancestor:
  if ancestor in seen:raise PipelineError('Materialized fact ancestry cycle')
  seen.add(ancestor);home=root/('lineage/fact_version' if ancestor==key else 'lineage/fact_ancestors/'+ancestor);manifest=read_json(home/'manifest.json')
  if manifest.get('fact_version')!=ancestor or digest({k:v for k,v in manifest.items() if k!='fact_version'})!=ancestor:raise PipelineError('Materialized immutable fact identity changed')
  for entry in manifest['files']:
   p=(home/_relative(entry['path'])).resolve()
   if not p.is_relative_to(home.resolve()) or not p.is_file() or sha256_file(p)!=entry['sha256'] or p.stat().st_size!=entry['bytes']:raise PipelineError('Materialized fact evidence changed or escaped source scope')
  if manifest.get('related_claim_scope_resolution_required') and not lineage.get('reconciliation_record_id'):raise PipelineError('Unresolved related fact scopes cannot become a source preparation')
  ancestor=manifest.get('parent_fact_version')
 claims=read_json(root/'claims.json')['claims'];accepted=read_json(root/'lineage/fact_version/claims.json')['claims'];review=read_json(root/'lineage/fact_review.json');history=read_json(root/'lineage/source_history.json');script=read_json(root/'script.json')
 if (not lineage.get('reconciliation_record_id') and claims!=accepted) or script.get('fact_version')!=key or review.get('fact_version')!=key or lineage['source_revision']!=history['latest_hash'] or review.get('source_revision')!=lineage['source_revision'] or review.get('head_revision')!=lineage['head_revision'] or review.get('manual_revision')!=lineage['manual_revision']:raise PipelineError('Materialized fact/source/manual lineage differs')
 original=lineage['parent_identity']
 if (root/'lineage/parent_preparation/prepared.json').is_file():
  parent_manifest=verify_preparation(root/'lineage/parent_preparation')
  if parent_manifest['preparation_id']!=original.get('preparation_id'):raise PipelineError('Nested parent source preparation identity differs')
 if sha256_file(root/'lineage/parent/script.json')!=original['script_sha256']:raise PipelineError('Materialized parent scenario identity differs')
 base=read_json(root/'lineage/fact_version/manifest.json')
 if sha256_file(root/'lineage/parent/claims.json')!=base['base_claims_sha256']:raise PipelineError('Materialized parent fact identity differs')
 manual=root/'lineage/manual_script_draft.json'
 if lineage['manual_revision']=='absent':prior=read_json(root/'lineage/parent/script.json')
 else:
  if not manual.is_file() or sha256_file(manual)!=lineage['manual_revision']:raise PipelineError('Materialized manual revision differs')
  from .manual_draft_integrity import read as read_manual_draft
  prior=read_manual_draft(manual,original,read_json(root/'lineage/parent/script.json'))['script']
 if lineage.get('reconciliation_record_id'):
  from .fact_reconciliation import verify_record
  rec=read_json(root/'lineage/reconciliation.json')
  if digest(rec)!=lineage['reconciliation_record_id'] or any(rec['context'].get(k)!=lineage.get(k) for k in ('fact_version','head_revision','source_revision','manual_revision')):raise PipelineError('Reconciliation belongs to another exact source/fact/manual context')
  active,expected=verify_record(root,rec,accepted,prior)
  if active!=claims:raise PipelineError('Active prepared ledger differs from explicit scope resolutions')
  ancestor=key;required=set()
  while ancestor:
   home=root/('lineage/fact_version' if ancestor==key else 'lineage/fact_ancestors/'+ancestor);m=read_json(home/'manifest.json');required.update((p['candidate'],p['retained_claim']) for p in m.get('related_claim_scope_resolution_required',[]));ancestor=m.get('parent_fact_version')
  if not required.issubset({(p['candidate'],p['prior']) for p in rec['pairs']}):raise PipelineError('Explicit scope resolution lost a historical related claim')
  ancestor=rec;seen=set()
  while ancestor:
   rid=digest(ancestor)
   if rid in seen or len(seen)>=100:raise PipelineError('Materialized reconciliation history cycle/depth')
   seen.add(rid);saved=read_json(root/'lineage/reconciliation_history'/(rid+'.json'))
   if digest(saved)!=rid:raise PipelineError('Materialized reconciliation history changed')
   previous=ancestor.get('previous_record');ancestor=read_json(root/'lineage/reconciliation_history'/(previous+'.json')) if previous else None
   if ancestor is not None and digest(ancestor)!=previous:raise PipelineError('Reconciliation parent identity changed')
  prior=expected
 if len(prior['segments'])!=len(script['segments']) or any(any(a.get(k)!=b.get(k) for k in ('id','voiceover','on_screen','screen_anchor','claim_keys','track_ids')) for a,b in zip(prior['segments'],script['segments'])):raise PipelineError('Materialized scenario changed saved manual wording or evidence bindings')
 for c in claims:
  if c.get('listing_scope'):
   from .listing_claims import verify_typed
   verify_typed(root,c)
  for ref in [c.get('source') or {}]+list((c.get('source') or {}).get('field_sources') or [])+list((c.get('source') or {}).get('supporting_sources') or []):
   name=ref.get('snapshot_file',ref.get('file'));sha=ref.get('snapshot_sha256',ref.get('sha256'))
   if name and sha:
    p=(root/_relative(name)).resolve()
    if not p.is_relative_to(root) or not p.is_file() or sha256_file(p)!=sha:raise PipelineError('Active accepted claim lacks exact self-contained source bytes')
 from .claims import validate_script
 errors=validate_script(script,claims)
 if errors:raise PipelineError('; '.join(errors))
 if read_json(root/'storyboard.json')!=board(script):raise PipelineError('Materialized storyboard differs')
 plan=read_json(root/'production_plan.json')
 if plan.get('tasks')!=[] or plan.get('ready_for_generation') is not False or plan.get('model_execution_started') is not False:raise PipelineError('Source materialization cannot start production tasks')
 return {'integrity_pass':True,'fact_version':key,'source_revision':lineage['source_revision'],'fact_ancestors_preserved':len(seen)-1,'scenario_approved':False}

def materialize(store,id,draft_loader,expected_version,request_key,reviewer,reason,scenario_reviewed=False):
 store=snapshot(store)
 key=_key(request_key)
 if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120 or not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise PipelineError('Materialization needs reviewer and reason')
 if scenario_reviewed is not True:raise PipelineError('Explicit agreement to this exact saved scenario and fact bindings required; no concept approval implied')
 request={'version':expected_version,'reviewer':reviewer.strip(),'reason':reason.strip(),'scenario_reviewed':True};request_hash=digest(request)
 # Same order as manual/fact review; prevent source/manual/head races through registration.
 with motion_lock(store.root,'scriptdraft_'+id,wait=5):
  with motion_lock(store.root,'fact_adoption_'+id,wait=5):
   with motion_lock(store.root,'sourcehistory_'+id,wait=5):
    journal=store.folder(id)/'source_materializations'/(key+'.json')
    if journal.exists():
     intent=read_json(journal)
     if intent['request_hash']!=request_hash:raise PipelineError('Materialization request key belongs to another decision')
     # Check registered outcome first: an uncertain caller retry cannot duplicate children.
     with store.connect() as conn:row=conn.execute('SELECT id,run_dir,request_json FROM jobs WHERE request_key=?',('source-materialization:'+id+':'+key,)).fetchone()
     if row:
      if row['id']!=intent['child_job_id'] or json.loads(row['request_json']).get('source_materialization')!=intent['lineage']:raise PipelineError('Registered materialization identity differs')
      sealed=verify_preparation(store.root/row['run_dir']);verify_materialization(store.root/row['run_dir'])
      if sealed['preparation_id']!=intent['receipt']['preparation_id']:raise PipelineError('Registered child differs from materialization receipt')
      intent['state']='committed';write_json(journal,intent);return intent['receipt']
    current=preview(store,id,draft_loader(store,id))
    if current['version']!=expected_version:
     if journal.exists():
      intent['state']='conflict';intent['conflict_reason']='Source, fact head or saved scenario changed before registration; historical partial preserved without promotion';write_json(journal,intent)
     raise PipelineError('Source, fact head or saved scenario changed; reopen before materializing')
    if not current['ready_to_materialize']:raise PipelineError('; '.join(current['blocked_reasons']))
    if journal.exists() and intent.get('state')=='conflict':raise PipelineError('Conflicted materialization requires a new request')
    child=(intent['child_job_id'] if journal.exists() else uuid.uuid4().hex);folder=store.folder(child);folder.mkdir(exist_ok=True);temp=folder/'source_partial';destination=folder/'runs/source_materialized'
    lineage={k:current[k] for k in ('parent_job_id','parent_identity','source_revision','fact_version','head_revision','manual_revision','version')}
    receipt={'schema':'SOCIAL_SOURCE_MATERIALIZATION_RECEIPT_V1','job_id':child,'parent_job_id':id,'fact_version':current['fact_version'],'models_started':False,'concept_approved':False,'production_authorized':False,'publication_authorized':False}
    intent={'state':'prepared','child_job_id':child,'request_hash':request_hash,'lineage':lineage,'receipt':receipt,'reviewer':request['reviewer'],'reason':request['reason']};write_json(journal,intent)
    if destination.exists():
     verify_preparation(destination)
     if read_json(destination/'source_materialization.json').get('version')!=current['version']:raise PipelineError('Interrupted child preparation has another context')
    else:
     if temp.exists():
      # Known owned partial only; preserve interrupted bytes for inspection.
      temp.rename(folder/('source_partial_history_'+uuid.uuid4().hex))
     temp.mkdir();_build(store,id,current,temp);destination.parent.mkdir(exist_ok=True);temp.rename(destination)
    identity=verify_preparation(destination)['preparation_id'];receipt['preparation_id']=identity;intent['receipt']=receipt;intent['state']='published';write_json(journal,intent)
    config=read_json(destination/'preparation_config.json');write_json(folder/'config.json',config)
    payload={'config':config,'stop_after':'script','source_materialization':lineage,'reviewer':reviewer,'reason':reason,'models_allowed':False};now=time.time()
    with store.connect() as conn:
     conn.execute('INSERT INTO jobs(id,request_key,request_json,state,created,updated,owner_pid,owner_token,return_code,run_dir,detail) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(child,'source-materialization:'+id+':'+key,json.dumps(payload),'prepared',now,now,None,None,0,destination.relative_to(store.root).as_posix(),HOLD))
    intent['state']='committed';write_json(journal,intent);return receipt

def recover(store,id,draft_loader,request_key):
 key=_key(request_key);intent=read_json(store.folder(id)/'source_materializations'/(key+'.json'))
 if intent.get('state')=='conflict':raise PipelineError('Historical materialization conflicts with newer input; reopen and review a new exact version')
 return materialize(store,id,draft_loader,intent['lineage']['version'],key,intent['reviewer'],intent['reason'],True)
