"""Same-origin bridge for existing v82 views, over existing durable Social APIs."""

import uuid,json

from pathlib import Path

from urllib.parse import urlsplit,parse_qs

from socialreel.common import PipelineError,read_json

from socialreel.workflow import restore_workflow,remember_selection,record_editorial
from socialreel.writer_contract import route as writer_route

from socialreel.publication_plan import prepare_plan,get_plan



WORKSPACE='e52df899-57aa-4aef-a853-1ad9427ed086'

def uid(jid):return str(uuid.UUID(hex=jid))

def jid(value):

 try:return uuid.UUID(value).hex

 except (ValueError,TypeError,AttributeError):raise PipelineError('Invalid owned job identity')



class LocalBridge:

 def __init__(self,store,prepare_config=None,prepare_launcher=None):self.store=store;self.prepare_config=prepare_config;self.prepare_launcher=prepare_launcher

 def rotation_scope(self,id,group=None):
  from socialreel.topic_rotation import scope,selected_audience
  return scope(self.store,id,group or selected_audience(self.store),original=True)

 def snapshot(self,id):return restore_workflow(self.store,jid(id))

 def row(self,id):

  v=restore_workflow(self.store,id);decision=v['editorial_decision']['state'];ready=v['stages']['video']=='verified'

  return {'id':uid(id),'title':(v.get('topic') or {}).get('title') or id,'state':'review' if (v.get('current_material') or {}).get('requires_review') else 'approved' if decision=='approved' else 'review' if ready else v['state'],'research_versions':1 if v.get('topic') else 0,'artifact_versions':1 if ready else 0,'reason_codes':[v['content_quality'].get('state','review_required'),'current_source_unconfirmed'],'_workflow':v}

 def rows(self):

  with self.store.connect() as conn:ids=[row[0] for row in conn.execute('SELECT id FROM jobs ORDER BY updated DESC')]

  return [self.row(id) for id in ids]

 def review(self,row):

  v=row['_workflow'];pkg=(v['artifacts'].get('preview_video') or {}).get('artifact_id');dec=v['editorial_decision']

  return {'id':row['id'],'story_id':row['id'],'story_title':row['title'],'decision':dec['state'] if dec['state'] in {'approved','rejected','changes_requested'} else 'pending','content_artifact_id':row['id'],'factual_version':1,'artifact_version':1,'package_version':1,'factual_state':'saved_source_not_revalidated','artifact_state':'technical_preview','package_state':row['state'],'reason':dec.get('reason') or 'Technical preview. Inspect actual video/audio; current official source and editorial acceptance remain unconfirmed.','package_id':pkg}

 def get(self,path):
  from socialreel.owner_locale import present,error
  try:return present(self._get(path))
  except PipelineError as original:
   error(original)
   raise

 def post(self,path,body):
  from socialreel.owner_locale import present,error
  try:return present(self._post(path,body))
  except PipelineError as original:
   error(original)
   raise

 def _get(self,path):

  u=urlsplit(path);q=parse_qs(u.query);route=u.path

  if q.get('workspace_id',[WORKSPACE])[0]!=WORKSPACE:raise PipelineError('Unknown local workspace')

  if route in {'/local/concept','/local/order-preflight'}:

   from socialreel.concept_review import inspect,order_preflight

   id=jid(q.get('id',[''])[0])

   return inspect(self.store,id) if route=='/local/concept' else order_preflight(self.store,id)

  if route=='/local/track-angle':
   from socialreel.track_angle import proposal
   from local_script_draft import load
   id=jid(q.get('id',[''])[0]);return proposal(self.store,id,load(self.store,id))

  if route=='/local/fact-reconciliation':
   from socialreel.fact_reconciliation import view,public
   from local_script_draft import load
   from socialreel.topic_rotation import snapshot
   store=snapshot(self.store);id=jid(q.get('id',[''])[0]);return public(view(store,id,load(store,id)))

  if route=='/local/source-materialization':
   from socialreel.source_materialization import preview
   from local_script_draft import load
   from socialreel.topic_rotation import snapshot
   store=snapshot(self.store);id=jid(q.get('id',[''])[0]);return preview(store,id,load(store,id))

  if route=='/local/fact-adoption':
   from socialreel.fact_versions import view,public
   return public(view(self.store,jid(q.get('id',[''])[0])))

  if route=='/local/topic-audience':
   from socialreel.topic_rotation import selected_audience
   return {'audience':selected_audience(self.store)}

  if route=='/local/topic-queue':
   from socialreel.topic_rotation import view,public,scope
   snapshot=view(self.store,q.get('audience',[None])[0]);result=public(snapshot)
   if q.get('id'):result['current_scope']=scope(snapshot['_store'],jid(q['id'][0]),result['audience'])
   return result

  if route=='/local/editorial-brief':
   from socialreel.editorial_card import inspect
   from local_script_draft import load
   id=jid(q.get('id',[''])[0]);return inspect(self.store,id,load(self.store,id))

  if route=='/local/source-history':
   from socialreel.source_revisions import state
   return state(self.store,jid(q.get('id',[''])[0]))

  if route=='/local/script-draft':

   from local_script_draft import load

   return load(self.store,jid(q.get('id',[''])[0]))

  if route=='/local/workflow':return self.snapshot(q.get('id',[''])[0])

  if route=='/local/preparation-options':

   cfg=read_json(self.prepare_config) if self.prepare_config else {}

   return {'writer_route':writer_route(cfg),'public_page_available':bool((cfg.get('public_page') or {}).get('enabled') and (cfg.get('public_page') or {}).get('network_authorized')),'public_page_request_key':(cfg.get('public_page') or {}).get('request_key'),'audiences':[{'id':'general_us','label':'General US audience'},{'id':'small_business','label':'Small businesses'},{'id':'institutional','label':'Institutions and organizations'}],'selected':(cfg.get('selection') or {}).get('audience','general_us'),'editorial_model_configured':cfg.get('writer')=='ollama' and (cfg.get('local_editorial') or {}).get('enabled') is True,'scope':'Topic relevance only; no eligibility promise'}

  if route=='/local/selection':

   try:return {'selection':restore_workflow(self.store)}

   except (PipelineError,OSError,ValueError,TypeError,KeyError):return {'selection':None,'selection_error':'Saved selection unavailable; choose an existing story. Original selection file preserved.'}

  if route=='/workspaces':return {'workspaces':[{'id':WORKSPACE,'name':'Social local review','role':'owner'}]}

  if route=='/research-queue':return {'research_queue':[],'source_refresh_performed':False}

  if route=='/channels':return {'channels':[],'social_accounts':[]}

  if route=='/capabilities':return {'capabilities':{'critical_gaps':['Local review only; models paused; current sources not refreshed; publication disabled.']}}

  empty={'/metrics':'metrics','/learnings':'learnings','/publications':'publications','/campaigns':'campaigns','/community':'items','/brands':'brands'}

  if route in empty:return {empty[route]:[],'connection_state':'not_connected','publication_authorized':False}

  if route=='/planning-options':return {'brands':[],'campaigns':[],'accounts':[],'packages':[],'timezone':None}

  rows=[self.row(jid(q.get('id',[''])[0]))] if route=='/story' else self.rows()

  if route=='/stories':return {'stories':[{k:v for k,v in x.items() if not k.startswith('_')} for x in rows]}

  if route=='/reviews':return {'reviews':[self.review(x) for x in rows if x['_workflow']['stages']['video']=='verified'],'correction_cases':[]}

  if route=='/story':

   id=q.get('id',[''])[0];row=next((x for x in rows if x['id']==id),None)

   if not row:raise PipelineError('Owned story not found')

   v=row['_workflow'];source=(v.get('topic') or {}).get('source');script={}

   if 'script' in v['artifacts']:script=read_json(Path(v['artifacts']['script']['path']))

   return {'story':{k:x for k,x in row.items() if not k.startswith('_')},'sources':[{'source_name':'Official saved source','source_url':source,'source_type':'saved official evidence','factual_use_status':'current_source_unconfirmed'}]+([{'source_name':'Saved full primary announcement','source_url':v['track_conditions']['source'].get('final_url') or v['track_conditions']['source']['url'],'source_type':'hash-verified primary source snapshot','factual_use_status':'overview_policy_snapshot_reviewed' if v.get('source_dependencies') else 'track_facts_extracted_linked_policies_unknown'}] if v.get('track_conditions') else []) if source else [],'claims':[],'research':[],'factual_cores':[{'version':1,'state':'source_extracted_draft','facts':{'schema':v['track_conditions']['schema'],'tracks':list(v['track_conditions']['tracks']),'raw_source_sha256':v['track_conditions']['source']['sha256'],'remaining_unknown':v['track_conditions']['unresolved_conditions'],'editorial_approved':False}}] if v.get('track_conditions') else [],'artifacts':[{'id':id,'version':1,'state':'technical_preview' if v['stages']['video']=='verified' else 'unvoiced_draft','content':script}] if script else [],'package_variants':[],'reviews':[self.review(row)] if v['stages']['video']=='verified' else []}

  if route=='/dashboard':return {'counts':{'pending_reviews':sum(x['state']=='review' for x in rows)},'active_work':[],'recent_completed_work':[]}

  if route=='/calendar':

   slots=[]

   for x in rows:

    p=x['_workflow'].get('publication_plan',{});body=p.get('plan') or {};when=body.get('intended_time')

    if when:slots.append({'id':x['id'],'story_title':x['title'],'scheduled_for':when.get('local_time'),'state':'planned_locally','publishing_state':'blocked','blocking_reason':'Local intention only; no dispatch scheduled'})

   return {'calendar':slots,'dispatch_scheduled':False}

  raise PipelineError('This cloud feature is unavailable in local review: '+route)

 def _post(self,path,body):

  route=urlsplit(path).path

  if route=='/local/materialize-visual':

   if not self.prepare_launcher:raise PipelineError('Source-only materialization worker unavailable')

   if set(body)!={'id','revision','request_key'}:raise PipelineError('Visual materialization accepts only job, exact manual revision and idempotency key')

   id=jid(body['id'])

   try:key=str(uuid.UUID(body['request_key']))

   except (ValueError,TypeError,AttributeError):raise PipelineError('Explicit materialization UUID required')

   from socialreel.motion_state import motion_lock

   with motion_lock(self.store.root,'cpu_submit',wait=3),motion_lock(self.store.root,'scriptdraft_'+id,wait=5):

    with self.store.connect() as connection:active=connection.execute("SELECT id,request_key FROM jobs WHERE state IN ('queued','running') LIMIT 1").fetchone()

    if active and active['request_key']!='ui-visual:'+key:raise PipelineError('Another source preparation is active; materialization not started')

    from local_script_draft import load,original

    from socialreel.preparation import verify_preparation

    from socialreel.visual_revision import build_recipe

    job=self.store.get(id)

    if job.get('state')!='prepared' or not job.get('preparation_integrity_pass'):raise PipelineError('Verified source preparation required')

    draft=load(self.store,id)
    if draft.get('fact_revalidation_required'):raise PipelineError('Accepted facts require a fact-aligned preparation; screen-only materialization cannot reuse the old ledger')

    if draft['state']!='unrendered_script_draft' or draft['revision']!=body['revision']:raise PipelineError('Saved manual revision changed; reopen before materializing')

    identity,base=original(self.store,id);root=Path(job['run_dir']);manifest=verify_preparation(root)

    recipe=build_recipe(manifest,base,read_json(root/'claims.json')['claims'],draft['script'],draft['revision'],description_override=draft['publication_text']['description_draft']['text'])

    child=self.store.submit(config=None,request_key='ui-visual:'+key,timeout=300,stop_after='script',writer='template',resume_job=id,visual_revision=recipe)

    worker=self.prepare_launcher(self.store,child['id'])

    remember_selection(self.store,child['id'])

   return {'job_id':uid(child['id']),'state':child['state'],'target':'immutable_visual_only_source_revision','models_allowed':False,'source_fetch_allowed':False,'production_authorized':False,'worker':worker}

  if route=='/local/prepare-public':

   if not self.prepare_config or not self.prepare_launcher:raise PipelineError('Public source-only preparation unavailable')

   if set(body)!={'request_key'}:raise PipelineError('Fixed public page accepts only the approved idempotency key')

   cfg=read_json(self.prepare_config);policy=cfg.get('public_page') or {}

   try:key=str(uuid.UUID(body['request_key']));approved_key=str(uuid.UUID(policy.get('request_key','')))

   except (ValueError,TypeError,AttributeError):raise PipelineError('Approved one-run UUID required in server policy')

   if key!=approved_key:raise PipelineError('Public page request differs from approved one-run identity')

   from socialreel.public_page import validate

   spec={'kind':'usa_gov_unclaimed','mode':'live'};validate(spec,cfg)

   from socialreel.motion_state import motion_lock

   with motion_lock(self.store.root,'cpu_submit',wait=3):

    with self.store.connect() as connection:active=connection.execute("SELECT id,request_key FROM jobs WHERE state IN ('queued','running') LIMIT 1").fetchone()

    if active and active['request_key']!='ui-public:'+key:raise PipelineError('Another preparation is active; public source not requested')

    job=self.store.submit(config=self.prepare_config,request_key='ui-public:'+key,timeout=300,stop_after='script',writer=cfg.get('writer','template'),public_source=spec)

    worker=self.prepare_launcher(self.store,job['id'])

    remember_selection(self.store,job['id'])

   return {'job_id':uid(job['id']),'state':job['state'],'target':'fixed_public_page_source_script_only','writer_route':job.get('writer_route'),'models_allowed':writer_route(cfg)['configured_editorial_inference_allowed'],'media_models_allowed':False,'source_facts_confirmed':False,'worker':worker}

  if route=='/local/prepare':

   if not self.prepare_config or not self.prepare_launcher:raise PipelineError('CPU preparation unavailable in this host')

   if set(body) not in ({'request_key'},{'request_key','audience'}):raise PipelineError('CPU preparation accepts only request_key and a known audience')

   from socialreel.audience_selection import AUDIENCES

   audience=body.get('audience')

   if audience is not None and audience not in AUDIENCES:raise PipelineError('Unknown editorial audience')

   try:key=str(uuid.UUID(body['request_key']))

   except (ValueError,TypeError,AttributeError):raise PipelineError('Explicit UUID request key required')

   cfg=read_json(self.prepare_config);search=cfg.get('search') or {}

   from socialreel.local_editorial import authorized as editorial_authorized
   if (cfg.get('writer')!='template' and not editorial_authorized(cfg)) or (cfg.get('llm') or {}).get('allow_spend') is not False or search.get('pagination') is not True or not 1<=int(search.get('max_search_requests',0))<=3 or not 1<=int(search.get('max_detail_fetch',0))<=14:raise PipelineError('CPU preparation server configuration violates resource/request budget')

   if audience is not None:cfg['selection']={**(cfg.get('selection') or {}),'audience':audience}

   history=self.store.root/'history.json'

   if not history.exists():

    from socialreel.common import write_json

    records=[]

    for previous in self.store.list():

     if previous.get('package_integrity_pass') or previous.get('preparation_integrity_pass'):

      topic=read_json(Path(previous['run_dir'])/'topic.json')['selected'];records.append({'opportunity_id':topic['opportunity_id'],'title':topic['title'],'reason':'Exclude already saved topic and family; no forced opportunity'})

    write_json(history,{'runs':records})

   from socialreel.motion_state import motion_lock

   with motion_lock(self.store.root,'cpu_submit',wait=3):

    with self.store.connect() as connection:active=connection.execute("SELECT id,request_key FROM jobs WHERE state IN ('queued','running') LIMIT 1").fetchone()

    if active and active['request_key']!='ui-cpu:'+key:raise PipelineError('Another preparation is queued/running; no second job or search started')

    from socialreel.common import write_json

    request_config=self.store.root/'preparation_requests'/(key+'.json')

    if request_config.exists() and read_json(request_config)!=cfg:raise PipelineError('Request key already belongs to another audience/configuration')

    if not request_config.exists():write_json(request_config,cfg)

    job=self.store.submit(config=request_config,request_key='ui-cpu:'+key,timeout=300,stop_after='script',writer=cfg.get('writer','template'))

    worker=self.prepare_launcher(self.store,job['id'])

    remember_selection(self.store,job['id'])

    return {'job_id':uid(job['id']),'state':job['state'],'target':'source_script_storyboard_only','writer_route':job.get('writer_route'),'models_allowed':writer_route(cfg)['configured_editorial_inference_allowed'],'media_models_allowed':False,'publication_authorized':False,'worker':worker}

  if route=='/local/retry-preparation':

   if not self.prepare_launcher:raise PipelineError('CPU preparation unavailable in this host')

   if set(body)!={'id','request_key'}:raise PipelineError('Retry accepts only owned job and UUID request key')

   id=jid(body['id'])

   try:key=str(uuid.UUID(body['request_key']))

   except (ValueError,TypeError,AttributeError):raise PipelineError('Explicit UUID retry key required')

   previous=self.store.get(id)

   if previous['state'] not in {'failed','interrupted','cancelled'}:raise PipelineError('Only failed, interrupted or cancelled source preparations can be retried here')

   with self.store.connect() as connection:row=connection.execute('SELECT request_json FROM jobs WHERE id=?',(id,)).fetchone()

   request=json.loads(row[0]);cfg=read_json(self.store.folder(id)/'config.json')

   if request.get('stop_after')!='script' or cfg!=request.get('config') or cfg.get('writer')!='template':raise PipelineError('Retry is limited to unchanged source-only preparations; media/model jobs cannot start here')

   search=cfg.get('search') or {}

   if (cfg.get('llm') or {}).get('allow_spend') is not False or search.get('pagination') is not True or not 1<=int(search.get('max_search_requests',0))<=3 or not 1<=int(search.get('max_detail_fetch',0))<=14:raise PipelineError('Retry resource/request budget is invalid')

   from socialreel.motion_state import motion_lock

   with motion_lock(self.store.root,'cpu_submit',wait=3):

    with self.store.connect() as connection:active=connection.execute("SELECT id,request_key FROM jobs WHERE state IN ('queued','running') LIMIT 1").fetchone()

    if active and active['request_key']!='ui-cpu-retry:'+key:raise PipelineError('Another preparation is queued/running; retry did not start')

    job=self.store.retry(id,request_key='ui-cpu-retry:'+key)

    worker=self.prepare_launcher(self.store,job['id'])

    remember_selection(self.store,job['id'])

   return {'job_id':uid(job['id']),'state':job['state'],'target':'source_script_storyboard_only','models_allowed':False,'publication_authorized':False,'worker':worker}

  if route=='/local/export-track-angle':
   from socialreel.track_angle import proposal,export
   from local_script_draft import load
   id=jid(body.get('id'));return export(self.store,id,proposal(self.store,id,load(self.store,id)),body.get('proposal_version'))

  if route=='/local/fact-reconciliation':
   from socialreel.fact_reconciliation import save
   from local_script_draft import load
   return save(self.store,jid(body.get('id')),load,body.get('version'),body.get('interpretations'),body.get('resolutions'),body.get('bindings'),body.get('reviewer'),body.get('reason'),body.get('evidence_reviewed') is True,body.get('request_key'))
  if route=='/local/fact-reconciliation-recover':
   from socialreel.fact_reconciliation import recover
   from local_script_draft import load
   return recover(self.store,jid(body.get('id')),load,body.get('request_key'))

  if route=='/local/source-materialization-recover':
   from socialreel.source_materialization import recover
   from local_script_draft import load
   result=recover(self.store,jid(body.get('id')),load,body.get('request_key'));result['job_id']=uid(result['job_id']);return result

  if route=='/local/source-materialization':
   from socialreel.source_materialization import materialize
   from local_script_draft import load
   result=materialize(self.store,jid(body.get('id')),load,body.get('version'),body.get('request_key'),body.get('reviewer'),body.get('reason'),body.get('scenario_reviewed') is True)
   result['job_id']=uid(result['job_id']);return result

  if route=='/local/fact-adoption':
   from socialreel.fact_versions import commit
   return commit(self.store,jid(body.get('id')),body.get('version'),body.get('source_revision'),body.get('manual_revision'),body.get('actions'),body.get('reviewer'),body.get('reason'),body.get('evidence_reviewed') is True,body.get('request_key'))
  if route=='/local/fact-recover':
   from socialreel.fact_versions import recover
   return recover(self.store,jid(body.get('id')),body.get('request_key'))

  if route=='/local/topic-audience':
   from socialreel.topic_rotation import set_audience
   return set_audience(self.store,body.get('previous_audience'),body.get('audience'),body.get('version'))

  if route=='/local/topic-next':
   from socialreel.topic_rotation import advance
   result=advance(self.store,body.get('audience'),body.get('version'))
   if result['selected']:result['selected']['story_id']=uid(result['selected']['job_id'])
   return result
  if route=='/local/topic-decision':
   from socialreel.topic_rotation import decide
   return decide(self.store,jid(body.get('id')),body.get('audience'),body.get('basis'),body.get('version'),body.get('decision'),body.get('reviewer'),body.get('reason'))

  if route=='/local/create':raise PipelineError('Model execution paused: new reel generation is disabled; no job or worker created')

  if route not in {'/local/select','/local/cancel','/local/review','/local/plan','/local/script-draft','/local/export-preparation','/local/export-manual','/local/concept-review','/local/source-observation','/local/source-decision','/local/topic-decision','/local/topic-next','/local/topic-audience'}:raise PipelineError('Unavailable locally; no request forwarded: '+route)

  id=jid(body.get('id'));self.store.get(id)

  if route=='/local/source-observation':
   from socialreel.source_revisions import observe
   return observe(self.store,id,body.get('latest_hash'),body.get('observation'),body.get('label'))
  if route=='/local/source-decision':
   from socialreel.source_revisions import decide
   return decide(self.store,id,body.get('latest_hash'),body.get('revision'),body.get('decision'),body.get('reviewer'),body.get('reason'))
  if route=='/local/concept-review':

   from socialreel.concept_review import record

   return record(self.store,id,body.get('concept_version'),body.get('revision'),body.get('decision'),body.get('reviewer'),body.get('reason'),source_reviewed=body.get('source_reviewed') is True,rotation_scope=self.rotation_scope(id,body.get('audience')))

  if route=='/local/export-manual':

   from local_manual_export import exported

   return exported(self.store,id,body.get('revision'),create=True)

  if route=='/local/export-preparation':

   from socialreel.motion_state import motion_lock
   with motion_lock(self.store.root,'scriptdraft_'+id,wait=5),motion_lock(self.store.root,'fact_adoption_'+id,wait=5),motion_lock(self.store.root,'sourcehistory_'+id,wait=5):

    job=self.store.get(id)

    if job['state']!='prepared' or not job.get('preparation_integrity_pass'):raise PipelineError('Verified prepared job required; no generation/export of unfinished inputs')

    if (job.get('current_material') or {}).get('requires_review'):raise PipelineError('Current material changed; original preparation export would ignore saved edits or source changes. Export the exact manual review revision or materialize/revalidate the intended version first')

    from socialreel.preparation_export import export_preparation

    return export_preparation(job['run_dir'],self.store.root/'draft_exports'/(id+'_'+job['preparation_id'][:16]+'.zip'))

  if route=='/local/script-draft':

   from local_script_draft import save

   return save(self.store,id,body.get('package_id'),body.get('revision'),body.get('voiceovers'),screen_accents=body.get('screen_accents'),description_text=body.get('description_text'))

  if route=='/local/select':remember_selection(self.store,id);return restore_workflow(self.store,id)

  if route=='/local/cancel':return self.store.cancel(id)

  if route=='/local/review':
   revision=body.get('revision')
   if not isinstance(revision,str) or not (revision=='absent' or (len(revision)==64 and all(c in '0123456789abcdef' for c in revision))):raise PipelineError('Review snapshot revision required; refresh the selected version')
   return record_editorial(self.store,id,body.get('package_id'),body.get('decision'),body.get('reviewer'),body.get('reason'),body.get('listened') is True,body.get('visual_reviewed') is True,body.get('revision'),rotation_scope=self.rotation_scope(id,body.get('audience')))

  return prepare_plan(self.store,id,body.get('package_id'),planned_for=body.get('when'),timezone=body.get('timezone'),destination=body.get('destination'),expected_revision=body.get('revision'),clear_time=body.get('clear_time') is True)

