"""Existing desktop workflow API: restore, explicit review, verified OS preview opening."""
import json,os
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,sha256_bytes,atomic_bytes,utc_now


def editorial_state(review,package_id):
    value=review if isinstance(review,dict) else {}
    bound=bool(package_id and value.get('package_id')==package_id)
    approved=bound and value.get('approved') is True and value.get('decision','approved')=='approved' and value.get('listened') is True and value.get('visual_reviewed') is True
    state=('approved' if approved else value.get('decision','pending')) if bound else ('package_mismatch' if value else 'pending')
    if state not in {'approved','pending','changes_requested','rejected','package_mismatch'} or (state=='approved' and not approved):state='pending'
    invalid=[]
    if value.get('approved') is True and not approved:
        if not bound:invalid.append('Approval belongs to a different or unknown package')
        if value.get('decision','approved')!='approved':invalid.append('Explicit editorial decision is not approved')
        if value.get('listened') is not True:invalid.append('No explicit listening attestation for this package')
        if value.get('visual_reviewed') is not True:invalid.append('No explicit visual-review attestation for this package')
    return {'approval_invalid_reasons':invalid,'state':state,'approved':approved,'package_bound':bound,'package_id':package_id,'reason':value.get('reason'),'reviewer':value.get('reviewer'),'listening_attested':bound and value.get('listened') is True,'visual_review_attested':bound and value.get('visual_reviewed') is True,'publication_authorized':False}


def record_editorial(store,job_id,package_id,decision,reviewer,reason,listened=False,visual_reviewed=False,expected_revision=None,rotation_scope=None):
    if decision not in {'approved','changes_requested','rejected','pending'}:raise PipelineError('Unknown editorial decision')
    if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>120:raise PipelineError('Explicit reviewer required')
    if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise PipelineError('Editorial reason required, up to2000characters')
    if decision=='approved' and not (listened is True and visual_reviewed is True):raise PipelineError('Approval requires explicit listening and visual-review attestations')
    store.folder(job_id)  # Validate owned job identity before constructing a lock name.
    from .motion_state import motion_lock
    with motion_lock(store.root,'scriptdraft_'+job_id,wait=5),motion_lock(store.root,'fact_adoption_'+job_id,wait=5),motion_lock(store.root,'sourcehistory_'+job_id,wait=5),motion_lock(store.root,'editorial_'+job_id,wait=5):
        job=store.get(job_id)
        if job.get('package_integrity_pass') is not True:raise PipelineError('Editorial decision requires a verified completed package')
        if decision=='approved' and (job.get('current_material') or {}).get('requires_review'):raise PipelineError('Current material is unreviewed; approval of original media cannot approve saved edits or source changes')
        current=read_json(Path(job['run_dir'])/'package_manifest.json')['package_id']
        if current!=package_id:raise PipelineError('Editorial package changed; refresh the selected preview first')
        folder=store.folder(job_id);path=folder/'editorial_review.json';before=path.read_bytes() if path.exists() else None
        revision=sha256_bytes(before) if before is not None else None
        if not isinstance(expected_revision,str) or not (expected_revision=='absent' or len(expected_revision)==64 and all(c in '0123456789abcdef' for c in expected_revision)):raise PipelineError('Exact editorial revision required; refresh before reviewing')
        if expected_revision is not None:
            expected=None if expected_revision=='absent' else expected_revision
            if expected!=revision:raise PipelineError('Editorial decision changed; refresh before overwriting')
        value={'schema':'SOCIAL_EDITORIAL_DECISION_V1','package_id':current,'decision':decision,'approved':decision=='approved','reviewer':reviewer.strip(),'reason':reason.strip(),'listened':listened is True,'visual_reviewed':visual_reviewed is True,'at':utc_now().isoformat(),'previous_revision':revision,'publication_authorized':False,'topic_rotation_scope':rotation_scope}
        if before is not None:atomic_bytes(folder/'editorial_history'/(revision+'.json'),before)
        write_json(path,value)
        return {'backend_contract':'SOCIAL_BACKEND_V1','job_id':job_id,'state':'editorial_saved','editorial_decision':editorial_state(value,current),'revision':sha256_file(path),'worker_started':False,'publication_authorized':False}


def preview_open(store,job_id,launch=False,opener=None):
    from .backend_contract import describe
    job=store.get(job_id);backend=describe(store,job);artifact=backend['artifacts'].get('preview_video')
    if not artifact:raise PipelineError('No verified local video; no application opened')
    path=Path(artifact['path']).resolve();owned=store.folder(job_id).resolve()/'runs'
    if not path.is_relative_to(owned) or str(path).startswith('\\\\') or path.suffix.lower()!='.mp4':raise PipelineError('Preview must be an owned local MP4')
    if sha256_file(path)!=artifact['sha256']:raise PipelineError('Preview changed; no application opened')
    result={'backend_contract':'SOCIAL_BACKEND_V1','job_id':job_id,'state':'ready_to_open','preview':artifact,'launch_requested':launch is True,'application_open_requested':False,'playback_confirmed':False,'listening_confirmed':False,'editorial_decision':job.get('editorial_decision'),'publication_authorized':False,'worker_started':False}
    if launch:
        try:
            if opener is not None:opener(str(path))
            elif os.name=='nt':os.startfile(str(path),'open')
            else:raise OSError('Windows desktop open API unavailable on this host')
        except OSError as error:return {**result,'state':'open_failed','error_type':type(error).__name__,'detail':str(error)[:300]}
        result.update(state='open_requested',application_open_requested=True)
        write_json(store.folder(job_id)/'preview_open_receipt.json',{'at':utc_now().isoformat(),'package_id':artifact['artifact_id'],'video_sha256':artifact['sha256'],'application_open_requested':True,'playback_confirmed':False,'listening_confirmed':False})
    return result


def remember_selection(store,job_id):
    store.get(job_id)  # Save only an existing owned durable identity.
    write_json(store.root/'workflow_selection.json',{'schema':'SOCIAL_WORKFLOW_SELECTION_V1','job_id':job_id,'selected_at':utc_now().isoformat()})


def retry_chain(store,job):
    result=[];seen={job['id']};reference=job.get('retry_parent')
    while reference and len(result)<32:
        if not isinstance(reference,dict) or not isinstance(reference.get('job_id'),str):
            result.append({'state':'retry_reference_invalid'});break
        parent=reference['job_id']
        if parent in seen:result.append({'job_id':parent,'state':'retry_cycle_blocked'});break
        seen.add(parent)
        with store.connect() as connection:row=connection.execute('SELECT id,state,detail,return_code,request_json FROM jobs WHERE id=?',(parent,)).fetchone()
        if row is None:result.append({'job_id':parent,'state':'parent_not_bundled'});break
        if sha256_bytes(row['request_json'].encode('utf-8'))!=reference.get('request_sha256'):
            result.append({'job_id':parent,'state':'retry_parent_request_changed'});break
        result.append({'job_id':parent,'state':row['state'],'detail':row['detail'],'return_code':row['return_code'],'scope':'Failed-attempt lineage, not new source observation or inherited editorial approval'})
        try:reference=json.loads(row['request_json']).get('retry_parent')
        except (ValueError,TypeError,AttributeError):result.append({'job_id':parent,'state':'retry_reference_unreadable'});break
    return result,bool(reference and len(result)>=32)

def restore_workflow(store,job_id=None,remember=False):
    selection=store.root/'workflow_selection.json'
    if job_id is None:
        try:saved=read_json(selection)
        except FileNotFoundError:raise PipelineError('No saved selection; select an existing job once, without starting generation')
        if not isinstance(saved,dict) or saved.get('schema')!='SOCIAL_WORKFLOW_SELECTION_V1':raise PipelineError('Saved selection is unreadable; original file preserved')
        job_id=saved.get('job_id')
    job=store.get(job_id)
    from .backend_contract import describe
    backend=describe(store,job);artifacts=backend['artifacts'];directory=Path(job['run_dir']) if job.get('run_dir') else None
    topic=read_json(directory/'topic.json')['selected'] if directory and (job.get('package_integrity_pass') or job.get('preparation_integrity_pass')) else None
    retry_lineage,retry_truncated=retry_chain(store,job)
    lineage=[];seen={job_id};parent=job.get('resumed_from_job')
    while parent and len(lineage)<32:
        if parent in seen:lineage.append({'job_id':parent,'state':'lineage_cycle_blocked'});break
        seen.add(parent)
        with store.connect() as connection:row=connection.execute('SELECT id,state,request_json FROM jobs WHERE id=?',(parent,)).fetchone()
        if row is None:lineage.append({'job_id':parent,'state':'parent_not_bundled'});break
        lineage.append({'job_id':row['id'],'state':row['state']});parent=(json.loads(row['request_json']).get('resume_preparation') or {}).get('job_id')
    stages={name:('verified' if key in artifacts else 'not_available') for name,key in [('script','script'),('voice','audio'),('captions','subtitles_srt'),('video','preview_video')]}
    decision=job.get('editorial_decision') or editorial_state(None,backend.get('artifact_id'))
    state='preview_ready' if 'preview_video' in artifacts else 'draft_ready' if job.get('preparation_integrity_pass') else job['state']
    material=job.get('current_material') or {}
    if material.get('requires_review'):
        state='current_material_review_required';stages={k:('manual_draft_unverified' if k=='script' and material.get('manual_draft_saved') else 'original_reference' if v=='verified' else v) for k,v in stages.items()}
    opening={'state':'not_recorded','playback_confirmed':False,'listening_confirmed':False}
    try:
        receipt=read_json(store.folder(job_id)/'preview_open_receipt.json')
        video=artifacts.get('preview_video') or {}
        if receipt.get('package_id')==video.get('artifact_id') and receipt.get('video_sha256')==video.get('sha256') and video:
            opening.update(state='application_open_previously_requested',at=receipt.get('at'))
        else:opening['state']='different_or_unverified_preview'
    except FileNotFoundError:pass
    except (OSError,ValueError,TypeError,AttributeError):opening['state']='open_receipt_unreadable'
    if remember:remember_selection(store,job_id)
    return {'backend_contract':'SOCIAL_BACKEND_V1','workflow_contract':'SOCIAL_WORKFLOW_V1','writer_route':job.get('writer_route'),'job_id':job_id,'state':state,'queue_state':job['queue_state'],'selection_saved':selection.exists(),'topic':{'id':topic.get('opportunity_id'),'title':topic.get('title'),'source':topic.get('source_url')} if topic else None,'stages':stages,'artifacts':artifacts,'track_conditions':topic.get('track_conditions') if topic else None,'source_dependencies':topic.get('source_dependencies') if topic else None,'retry_lineage':retry_lineage,'retry_lineage_truncated':retry_truncated,'lineage':lineage,'lineage_truncated':bool(parent and len(lineage)>=32),'editorial_decision':decision,'current_material':material,'original_package_editorial_decision':job.get('original_package_editorial_decision'),'preview_open_status':opening,'delivery_receipt':backend['delivery_receipt'],'publication_plan':backend['publication_plan'],'content_quality':backend['content_quality'],'source_quality':backend.get('source_quality'),'narration_profile':backend.get('narration_profile'),'waiting':backend['waiting'],'actions':backend['actions'],'restore_starts_no_work':True,'worker_started':False,'current_source_confirmed':False,'ui_connected':False,'publication_authorized':False}
