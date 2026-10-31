"""Local publication preparation only: exact artifacts, no dispatcher or external schedule."""
import datetime as dt
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,atomic_bytes,utc_now
from .delivery_receipt import restore_delivery


def _artifact(store,job_id,job=None):
    job=job or store.get(job_id)
    if job.get('package_integrity_pass') is not True:raise PipelineError('Publication plan requires a verified finished local video')
    from .material_currentness import status as material_status
    if material_status(store,job_id,job)['requires_review']:raise PipelineError('Current material changed; original package plan cannot represent saved edits/source changes')
    root=Path(job['run_dir']);identity=read_json(root/'package_manifest.json')['package_id'];video=read_json(root/'result.json')['video'];delivery=restore_delivery(store,job_id,job)
    if delivery['state']!='verified_existing_delivery':raise PipelineError('Verified delivery ZIP required; export existing package first, without generation')
    return job,root,{'package_id':identity,'video_sha256':video['sha256'],'script_sha256':sha256_file(root/'script.json'),'ZIP_sha256':delivery['sha256']},delivery


def _slot(value,zone_name):
    if value is None:return None
    if not zone_name:raise PipelineError('Explicit publication timezone required for a planned time')
    try:
        if zone_name in {'UTC','Etc/UTC'}:zone=dt.timezone.utc
        else:
            from zoneinfo import ZoneInfo
            zone=ZoneInfo(zone_name)
        if 'T' not in value:raise ValueError('Explicit clock time required')
        stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset()!=stamp.astimezone(zone).utcoffset() or stamp.replace(tzinfo=None)!=stamp.astimezone(zone).replace(tzinfo=None):raise ValueError('Offset does not match explicit timezone')
        if stamp<=utc_now():raise ValueError('Planned time must be in the future')
    except (ValueError,KeyError,TypeError) as error:raise PipelineError('Invalid planned time/timezone; no schedule created: '+str(error)) from error
    return {'local_time':stamp.isoformat(),'timezone':zone_name,'utc':stamp.astimezone(dt.timezone.utc).isoformat()}


def prepare_plan(store,job_id,package_id,planned_for=None,timezone=None,destination=None,expected_revision=None,clear_time=False):
    store.folder(job_id)
    from .motion_state import motion_lock
    with motion_lock(store.root,'scriptdraft_'+job_id,wait=5),motion_lock(store.root,'fact_adoption_'+job_id,wait=5),motion_lock(store.root,'sourcehistory_'+job_id,wait=5),motion_lock(store.root,'publication_'+job_id,wait=5):
        job,root,identity,delivery=_artifact(store,job_id)
        if identity['package_id']!=package_id:raise PipelineError('Selected package changed; refresh before planning publication')
        path=store.folder(job_id)/'publication_plan.json';previous=read_json(path) if path.exists() else None;revision=sha256_file(path) if path.exists() else None
        if expected_revision is not None and expected_revision!=revision:raise PipelineError('Publication plan changed; refresh before overwriting')
        if destination is not None and (not isinstance(destination,str) or len(destination)>200):raise PipelineError('Destination label is limited to200characters; no account connection is made')
        old=previous if isinstance(previous,dict) and previous.get('artifact')==identity else {}
        slot=None if clear_time else _slot(planned_for,timezone) if planned_for is not None else old.get('intended_time')
        if clear_time and planned_for is not None:raise PipelineError('Cannot supply and clear planned time together')
        script=read_json(root/'script.json');topic=read_json(root/'topic.json')['selected'];sources=read_json(root/'sources.json')
        from .source_description import compose
        caption=compose(script,read_json(root/'claims.json')['claims'],topic)
        value={'schema':'SOCIAL_LOCAL_PUBLICATION_PLAN_V1','job_id':job_id,'artifact':identity,'title':script.get('title') or topic['title'],'caption':caption, 'source_url':topic.get('source_url'),'source_snapshot_observed_at':(sources.get('selected_snapshot') or {}).get('fetched_at'),'destination_label':destination if destination is not None else old.get('destination_label'),'intended_time':slot,'state':'planned_locally' if slot else 'unscheduled_draft','dispatch_scheduled':False,'dispatcher_present':False,'publication_authorized':False,'external_account_connected':False,'created_at':old.get('created_at') or utc_now().isoformat()}
        comparable=lambda v:{k:x for k,x in v.items() if k not in {'updated_at'}}
        from .workflow import remember_selection
        if isinstance(previous,dict) and comparable(previous)==value:
            remember_selection(store,job_id)
            return {**get_plan(store,job_id,job),'plan_reused':True}
        value['updated_at']=utc_now().isoformat()
        if path.exists():atomic_bytes(store.folder(job_id)/'publication_plan_history'/(revision+'.json'),path.read_bytes())
        write_json(path,value)
        remember_selection(store,job_id)
        return {**get_plan(store,job_id,job),'plan_reused':False}


def get_plan(store,job_id,job=None):
    path=store.folder(job_id)/'publication_plan.json'
    if not path.exists():return {'state':'not_prepared','publication_authorized':False,'dispatch_scheduled':False}
    try:
        saved=read_json(path);current,root,identity,delivery=_artifact(store,job_id,job)
        if not isinstance(saved,dict) or saved.get('schema')!='SOCIAL_LOCAL_PUBLICATION_PLAN_V1' or saved.get('job_id')!=job_id or saved.get('artifact')!=identity:raise PipelineError('Publication plan does not match current verified artifacts')
        decision=current.get('editorial_decision') or {};blockers=['live_source_recheck_required','explicit_publication_authorization_missing','external_dispatch_not_implemented']
        if decision.get('approved') is not True:
            state=decision.get('state','pending')
            blockers.insert(0,'editorial_review_'+state if state in {'rejected','changes_requested','package_mismatch'} else 'editorial_review_pending')
        from .source_description import compose
        expected_caption=compose(read_json(root/'script.json'),read_json(root/'claims.json')['claims'],read_json(root/'topic.json')['selected'])
        if saved.get('caption')!=expected_caption:blockers.append('description_conditions_need_refresh')
        if saved.get('destination_label') is None:blockers.append('destination_not_selected')
        if saved.get('intended_time') is None:blockers.append('time_not_selected')
        slot=saved.get('intended_time');slot_status='unscheduled' if slot is None else 'past_due' if dt.datetime.fromisoformat(slot['utc'])<=utc_now() else 'future'
        if slot_status=='past_due':blockers.append('planned_time_passed')
        return {'intended_time_status':slot_status,'state':saved['state'],'job_id':job_id,'plan':saved,'revision':sha256_file(path),'local_video':str(root/'final/reel.mp4'),'delivery_ZIP':delivery['path'],'blocking_conditions':blockers,'current_source_confirmed':False,'editorial_approved_for_this_package':decision.get('approved') is True,'publication_authorized':False,'dispatch_scheduled':False,'network_used':False,'worker_started':False}
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:return {'state':'plan_review_required','detail':str(error)[:300],'original_plan_preserved':True,'publication_authorized':False,'dispatch_scheduled':False}
