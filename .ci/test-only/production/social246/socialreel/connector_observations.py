"""Durable ingestion of existing Grants.gov detail receipts; never fetches itself."""
import copy,datetime as dt,json,sqlite3,contextlib
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_bytes,sha256_file,atomic_bytes,stable_json,check_cancel,utc_now,parse_date
from .source_revisions import state,observe,digest,baseline,SourceRevisionConflict
from .motion_state import motion_lock,MutationBusy

FIELD_NAMES={'title':'opportunityTitle','number':'opportunityNumber','close_date':'responseDate','open_date':'postingDate','description':'synopsisDesc','applicant_types':'applicantTypes','applicant_eligibility_desc':'applicantEligibilityDesc','award_floor':'awardFloor','award_ceiling':'awardCeiling','estimated_total_program_funding':'estimatedFunding','expected_number_of_awards':'numberOfAwards','cost_sharing':'costSharing','funding_instruments':'fundingInstruments','funding_categories':'fundingActivityCategories','full_announcement_url':'fundingDescLinkUrl','status':'ost'}
FIELDS=('title','number','status','open_date','close_date','description','applicant_types','applicant_eligibility_desc','award_floor','award_ceiling','estimated_total_program_funding','expected_number_of_awards','cost_sharing','funding_instruments','funding_categories','full_announcement_url')
def timestamp(value):
 try:
  parsed=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
  if parsed.tzinfo is None:raise ValueError()
  return parsed.astimezone(dt.timezone.utc)
 except (ValueError,TypeError):raise PipelineError('Receipt requires timezone-aware fetched_at')
def source_version(raw):
 data=json.loads(raw).get('data') or {};syn=data.get('synopsis') or data.get('forecast') or {}
 values=(data.get('revision'),syn.get('version'))
 return [v if type(v) is int and v>=0 else None for v in values]

def store_view(root):
 from .jobs import JobStore
 class View(JobStore):
  def __init__(self):self.root=Path(root);self.db=self.root/'queue.sqlite3'
  @contextlib.contextmanager
  def connect(self):
   c=sqlite3.connect(self.db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
   try:yield c
   finally:c.close()
 return View()
def targets(store,oid):
 with store.connect() as c:rows=list(c.execute("SELECT id,run_dir FROM jobs WHERE state IN ('prepared','completed','review_required')"))
 result=[]
 for row in rows:
  check_cancel()
  root=Path(row['run_dir']);root=root if root.is_absolute() else store.root/root
  topic_path=root/'topic.json'
  if not topic_path.is_file():continue
  topic=read_json(topic_path);record=topic.get('selected') or topic
  if str(record.get('opportunity_id'))!=str(oid):continue
  job=store.get(row['id'])
  if job.get('preparation_integrity_pass') is True or job.get('package_integrity_pass') is True:result.append(row['id'])
 return result

def raw_at(directory,meta):
 name=meta.get('file')
 if not isinstance(name,str) or Path(name).name!=name.replace('\\','/').split('/')[-1]:raise PipelineError('Invalid receipt snapshot name')
 p=(Path(directory)/Path(name).name).resolve()
 if not p.is_relative_to(Path(directory).resolve()):raise PipelineError('Snapshot escapes source directory')
 raw=p.read_bytes()
 if len(raw)>8*1024*1024 or len(raw)!=meta.get('bytes') or sha256_bytes(raw)!=meta.get('sha256'):raise PipelineError('Receipt raw bytes/hash mismatch')
 return raw

def project(raw,oid,previous=None):
 from .grants import normalize
 data=json.loads(raw)
 if not isinstance(data,dict) or data.get('errorcode',0) not in (0,'0',None):raise PipelineError('Incomplete/error detail response')
 detail=data.get('data')
 if not isinstance(detail,dict) or str(detail.get('id'))!=str(oid) or not detail.get('opportunityTitle'):raise PipelineError('Incomplete or wrong opportunity detail')
 synopsis=detail.get('synopsis') or detail.get('forecast')
 if not isinstance(synopsis,dict) or not synopsis:raise PipelineError('Incomplete detail synopsis')
 if previous is not None:
  old=json.loads(previous)['data'];old_syn=old.get('synopsis') or old.get('forecast') or {}
  if any(key not in synopsis for key in old_syn if old_syn[key] not in (None,'',[])):raise PipelineError('Incomplete detail: previously supplied synopsis fields missing')
 value=normalize({'id':str(oid)},detail)
 for field in ('open_date','close_date'):
  parsed=parse_date(value.get(field))
  if parsed:value[field]=parsed.isoformat()
 for field in ('applicant_types','funding_instruments','funding_categories'):
  if isinstance(value.get(field),list):value[field]=sorted(value[field])
 return {k:value.get(k) for k in FIELDS}

def deliver(history_path,directory,oid,meta,mode='live'):
 """Called only after existing connector returned bytes; replay uses saved original receipt."""
 from .grants import DETAIL_URL
 if mode not in {'live','replay'}:raise PipelineError('Unknown connector observation mode')
 root=Path(history_path).parent
 if not (root/'queue.sqlite3').is_file():return {'state':'no_owned_queue','mode':mode}
 if meta.get('url')!=DETAIL_URL or meta.get('http_status')!=200 or str((meta.get('request') or {}).get('opportunityId'))!=str(oid):raise PipelineError('Wrong Grants.gov detail receipt binding')
 timestamp(meta.get('fetched_at'));raw=raw_at(directory,meta)
 inbox=root/'connector_observation_inbox';inbox.mkdir(exist_ok=True)
 identity=digest({'oid':str(oid),'sha256':meta['sha256'],'fetched_at':meta['fetched_at'],'mode':mode})
 with motion_lock(root,'connector_inbox_'+identity[:20],wait=5):
  p=inbox/(identity+'.json');blob=inbox/(identity+'.raw')
  if not p.exists():
   atomic_bytes(blob,raw);write_json(p,{'schema':'SOCIAL_CONNECTOR_OBSERVATION_V1','event_id':identity,'opportunity_id':str(oid),'receipt':meta,'mode':mode,'raw_sha256':meta['sha256'],'state':'pending','results':{},'source_reviewed':False,'live_currentness_proved':False})
 return recover(history_path,identity)

def _event_json(path,inbox):
 if not path.resolve().is_relative_to(inbox.resolve()) or path.stat().st_size>1024*1024:raise PipelineError('Event metadata outside owned inbox or above1MiB')
 return read_json(path)

def recover(history_path,event_id=None):
 root=Path(history_path).parent;inbox=root/'connector_observation_inbox';store=store_view(root);results=[]
 if event_id is not None and (len(event_id)!=64 or any(c not in '0123456789abcdef' for c in event_id)):raise PipelineError('Invalid event identity')
 if event_id:paths=[inbox/(event_id+'.json')]
 else:
  pending=[]
  for p in inbox.glob('*.json'):
   try:e=_event_json(p,inbox)
   except (OSError,ValueError,TypeError,PipelineError):e={'state':'unreadable_event','_unreadable':True}
   if not isinstance(e,dict):e={'state':'unreadable_event','_unreadable':True}
   if e.get('state')!='processed':pending.append((p,e))
  pending.sort(key=lambda pair:(pair[1].get('state')!='pending',pair[1].get('_unreadable',False) or pair[1].get('state')=='quarantined_invalid_receipt',pair[1].get('last_attempt_at','')))
  paths=[p for p,e in pending[:5]]
 for p in paths:
  check_cancel()
  if not p.resolve().is_relative_to(inbox.resolve()):
   results.append({'event_id':p.stem,'state':'unsafe_event_locator_preserved','revision_created':False});continue
  try:
   event=_event_json(p,inbox)
   if not isinstance(event,dict):raise PipelineError('Connector event is not an object')
  except (OSError,ValueError,TypeError,PipelineError) as error:
   results.append({'event_id':p.stem,'state':'unreadable_event_preserved','revision_created':False,'reason':str(error)[:300]});continue
  try:
   meta=event.get('receipt') or {};oid=str(event.get('opportunity_id'));rawfile=p.with_suffix('.raw').resolve()
   if not rawfile.is_relative_to(inbox.resolve()):raise PipelineError('Durable connector bytes outside owned inbox')
   if rawfile.stat().st_size>8*1024*1024:raise PipelineError('Durable connector response exceeds8MiB')
   raw=rawfile.read_bytes();sha=sha256_bytes(raw)
   from .grants import DETAIL_URL
   if event.get('schema')!='SOCIAL_CONNECTOR_OBSERVATION_V1' or event.get('mode') not in {'live','replay'} or meta.get('url')!=DETAIL_URL or meta.get('http_status')!=200 or str((meta.get('request') or {}).get('opportunityId'))!=oid or type(meta.get('bytes')) is not int or meta['bytes']!=len(raw) or meta.get('sha256')!=sha or event.get('raw_sha256')!=sha:raise PipelineError('Durable receipt/event/raw binding differs')
   timestamp(meta.get('fetched_at'));identity=digest({'oid':oid,'sha256':sha,'fetched_at':meta['fetched_at'],'mode':event['mode']})
   if identity!=p.stem or event.get('event_id')!=identity:raise PipelineError('Durable connector event identity differs')
   body=json.loads(raw)
   if not isinstance(body,dict) or type(body.get('errorcode')) not in (int,str) or body.get('errorcode') not in (0,'0'):raise PipelineError('Incomplete/error API receipt')
   prior_results=event.get('results')
   if not isinstance(prior_results,dict) or any(not isinstance(v,dict) for v in prior_results.values()):raise PipelineError('Malformed connector application results')
  except (OSError,ValueError,TypeError,KeyError,AttributeError,PipelineError) as error:
   event['state']='quarantined_invalid_receipt';event['last_attempt_at']=utc_now().isoformat();event['integrity_error']=str(error)[:300];write_json(p,event);results.append({'event_id':p.stem,'state':event['state'],'revision_created':False,'reason':event['integrity_error']});continue
  ids=targets(store,event['opportunity_id']);matched=bool(ids)
  retry_pending=any(v.get('state')=='pending_source_retry' for v in prior_results.values())
  if event.get('state') in {'processed','pending'}:
   ids=[id for id in ids if id not in prior_results or prior_results[id].get('state')=='pending_source_retry']
   if not ids and event.get('state')=='processed':
    if retry_pending:
     event['state']='pending';event['last_attempt_at']=utc_now().isoformat();write_json(p,event)
    results.append({'event_id':event['event_id'],'mode':event['mode'],'state':event['state'],'results':event['results'],'facts_approved':False});continue
  for id in ids:
   try:
    with motion_lock(root,'connector_apply_'+id,wait=5):
     current=state(store,id);base=baseline(store,id);jobroot=Path(store.get(id)['run_dir']);snap=base['sources'].get('selected_snapshot') or {}
     baseline_path=(jobroot/str(snap.get('file',''))).resolve()
     if not baseline_path.is_relative_to(jobroot.resolve()) or not baseline_path.is_file() or sha256_file(baseline_path)!=snap.get('sha256'):
      outcome={'state':'baseline_receipt_unavailable','revision_created':False}
     else:
      cursor_path=store.folder(id)/'connector_observation_cursor.json';cursor=read_json(cursor_path) if cursor_path.exists() else {'fetched_at':snap.get('fetched_at'),'raw_sha256':snap['sha256'],'projection':project(baseline_path.read_bytes(),event['opportunity_id']),'source_version':source_version(baseline_path.read_bytes())}
      existing=next((x for x in current['history'] if (x['observation']['sources'].get('connector_observation') or {}).get('event_id')==event['event_id']),None)
      try:
       incoming=project(raw,event['opportunity_id'],baseline_path.read_bytes())
       if existing:
        outcome={'state':'recovered_already_applied','revision_created':False};accepted=True
       elif any(a is not None and b is not None and a<b for a,b in zip(source_version(raw),cursor.get('source_version',[None,None]))) or timestamp(event['receipt']['fetched_at'])<timestamp(cursor['fetched_at']):
        outcome={'state':'stale_response_preserved','revision_created':False};accepted=False
       elif timestamp(event['receipt']['fetched_at'])==timestamp(cursor['fetched_at']) and incoming!=cursor['projection']:
        outcome={'state':'same_time_conflict_quarantined','revision_created':False};accepted=False
       elif incoming==cursor['projection']:
        outcome={'state':'unchanged_repeat','revision_created':False};accepted=True
       else:
        changed=[key for key in FIELDS if incoming[key]!=cursor['projection'][key]]
        observation=copy.deepcopy(current['history'][-1]['observation'] if current['history'] else base)
        claims={c['key']:c for c in observation['claims']}
        for field in changed:
         key='connector_field_'+field
         related=[c['key'] for c in base['claims'] if any(str(path).split('.')[-1]==FIELD_NAMES[field] for path in c.get('source',{}).get('fields',[]))]
         claims[key]={'key':key,'related_claim_keys':related,'statement':'Unreviewed Grants.gov field '+field+': '+json.dumps(incoming[field],ensure_ascii=False),'values':{'field':field,'previous':cursor['projection'][field],'candidate':incoming[field]},'source':{'url':'https://www.grants.gov/search-results-detail/'+event['opportunity_id'],'snapshot_sha256':event['raw_sha256'],'snapshot_file':'connector_observation_inbox/'+event['event_id']+'.raw','fields':[field]},'source_reviewed':False}
        observation['claims']=list(claims.values());observation['sources']['connector_observation']={'event_id':event['event_id'],'mode':event['mode'],'original_fetched_at':event['receipt']['fetched_at'],'raw_sha256':event['raw_sha256'],'changed_fields':changed,'primary_documents_refreshed':False,'facts_approved':False}
        observe(store,id,current['latest_hash'],observation,('REPLAY saved receipt' if event['mode']=='replay' else 'LIVE connector response')+'; unreviewed Grants.gov fields')
        outcome={'state':'source_revision_created','revision_created':True,'changed_fields':changed};accepted=True
       if accepted and timestamp(event['receipt']['fetched_at'])>=timestamp(cursor['fetched_at']):write_json(cursor_path,{'fetched_at':event['receipt']['fetched_at'],'raw_sha256':event['raw_sha256'],'projection':incoming,'source_version':source_version(raw),'mode':event['mode'],'source_reviewed':False})
      except (MutationBusy,SourceRevisionConflict):raise
      except (PipelineError,ValueError,KeyError,TypeError) as error:outcome={'state':'incomplete_or_invalid_preserved','revision_created':False,'reason':str(error)[:300]}
     event['results'][id]=outcome;write_json(p,event)
   except (MutationBusy,SourceRevisionConflict) as error:
    event['results'][id]={'state':'pending_source_retry','revision_created':False,'reason':str(error)[:300]};event['state']='pending';write_json(p,event)
  event['state']='pending' if any(v.get('state')=='pending_source_retry' for v in event['results'].values()) else ('processed' if matched or event['results'] else 'waiting_for_matching_preparation');event['last_attempt_at']=utc_now().isoformat();write_json(p,event);results.append({'event_id':event['event_id'],'mode':event['mode'],'state':event['state'],'results':event['results'],'facts_approved':False})
 return results


def status(store,id):
 records=[];unreadable=[]
 def modified(p):
  try:return p.lstat().st_mtime
  except OSError:return 0
 for p in sorted((store.root/'connector_observation_inbox').glob('*.json'),key=modified,reverse=True):
  try:
   if not p.resolve().is_relative_to((store.root/'connector_observation_inbox').resolve()) or p.stat().st_size>1024*1024:raise PipelineError('Unsafe or oversized event metadata')
   event=_event_json(p,store.root/'connector_observation_inbox');outcome=event.get('results',{}).get(id)
   if outcome:records.append({'event_id':event['event_id'],'mode':event['mode'],'original_fetched_at':event['receipt']['fetched_at'],'raw_sha256':event['raw_sha256'],'event_state':event.get('state'),'integrity_error':event.get('integrity_error'),'result':outcome,'facts_approved':False})
  except (OSError,ValueError,TypeError,KeyError,AttributeError,PipelineError) as error:
   if len(unreadable)<20:unreadable.append({'event_id':p.stem,'state':'unreadable_event_preserved','reason':str(error)[:200]})
  if len(records)>=20:break
 return {'recent_receipts':records,'unreadable_receipts':unreadable,'live_run_validated':False,'facts_approved':False}
