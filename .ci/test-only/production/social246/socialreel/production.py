"""One explicit production request, with durable identity and targeted execution."""
from .common import PipelineError
from .backend_contract import command


def produce(store, config=None, opportunity=None, key=None, timeout=900, on_submitted=None, stop_after=None, writer=None, resume_job=None):
    options={}
    if stop_after is not None:options['stop_after']=stop_after
    if writer is not None:options['writer']=writer
    if resume_job is not None:options['resume_job']=resume_job
    job=store.submit(config,opportunity,key,timeout,**options)
    if on_submitted is not None:on_submitted({'event':'job_known','job_id':job['id'],'state':job['state'],'cancel_command':command(store,'cancel',job['id'])['command']})
    from .workflow import remember_selection
    remember_selection(store,job['id'])
    if job['state']=='queued':
        worked=store.work_once(job['id'])
        job=worked if worked is not None else store.get(job['id'])
    return _deliver(store,job,online=True)

def deliver_existing(store,job_id,online=False):
    job=store.get(job_id)
    if job['state'] not in {'completed','prepared'}:raise PipelineError('Existing artifact is not completed/prepared; no worker started')
    return {**_deliver(store,job,online=online),'reuse_only':True,'worker_started':False,'new_generation':False}

def _deliver(store,job,online=True):
    from .backend_contract import describe,command
    backend=describe(store,job)
    historical_state=job.get('historical_state',job['state'])
    if job['state']=='completed' and job.get('package_integrity_pass') is not True:
        job={**job,'state':'review_required','detail':'Stored completion is not deliverable: '+ '; '.join(job.get('package_errors') or ['Package/video integrity not verified'])}
    video=str(job['run_dir'])+'/final/reel.mp4' if job.get('run_dir') and job.get('package_integrity_pass') is True else None
    preview_video=video
    export=None
    if job['state']=='completed' and job.get('package_integrity_pass') is True:
        from .export import export_package
        try:
            if online:export=export_package(job['run_dir'])
            else:
                from .common import ROOT,read_json
                from pathlib import Path
                package_id=read_json(Path(job['run_dir'])/'package_manifest.json')['package_id'];matches=list((ROOT/'runs/exports').glob(Path(job['run_dir']).name+'_'+package_id[:16]+'_v*.zip'))
                existing=max(matches,key=lambda p:int(p.stem.rsplit('_v',1)[1])) if matches else None
                export=export_package(job['run_dir'],existing,online=False)
            from .nofo_review import revoke_editorial
            if online:revoke_editorial(store.folder(job['id']),export['package_id'],export.get('delivery_check_now') or {})
            if export.get('ready_for_current_use') is not True:
                job={**job,'state':'review_required','detail':'Current delivery source check requires review','technical_ready_for_reuse':False}
                video=None
        except (PipelineError,OSError,ValueError) as error:
            export={'exported':False,'detail':str(error)}
            job={**job,'state':'review_required','detail':'Delivery export failed; current readiness unconfirmed','technical_ready_for_reuse':False}
            video=None
    preparation_export=None
    if job['state']=='prepared' and job.get('preparation_integrity_pass') is True:
        from .preparation_export import export_preparation
        try:preparation_export=export_preparation(job['run_dir'],store.root/'draft_exports'/(job['id']+'_'+job['preparation_id'][:16]+'.zip'))
        except (PipelineError,OSError,ValueError) as error:
            preparation_export={'exported':False,'detail':str(error)}
            job={**job,'state':'review_required','detail':'Draft bundle could not be verified; original inputs preserved'}
    failure=None
    if job['state'] in {'failed','rejected','interrupted','review_required'}:
        from .common import read_json
        try:
            files=sorted((store.folder(job['id'])/'runs').glob('failure_*.json'))
            if files:failure=read_json(files[-1])
        except (OSError,ValueError):failure={'detail':'Failure evidence is unreadable; see owned worker log'}
    receipt=backend.get('delivery_receipt')
    issued=export if export and export.get('path') else preparation_export
    if issued and issued.get('path'):
        from .delivery_receipt import remember_delivery
        try:receipt=remember_delivery(store,job['id'],issued)
        except (PipelineError,OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
            receipt={'state':'delivery_receipt_not_saved','detail':str(error)[:300],'archive_preserved':True,'retry_export_without_generation':True}
    from .source_failure import source_blockers,discovery_coverage
    blockers=source_blockers(store.folder(job['id']),job) if failure is not None else []
    return {'delivery_receipt':receipt,'backend_version':backend['backend_version'],'content_quality':backend['content_quality'],'backend_contract':backend['backend_contract'],'id':job['id'],'queue_state':backend['queue_state'],'delivery_state':job['state'],'delivery_waiting':{'code':'live_source_recheck_required' if not online else 'delivery_review_required','detail':job.get('detail')} if job['state']=='review_required' else None,'queue_root':str(store.root),'artifacts':backend['artifacts'],'artifact_id':backend['artifact_id'],'waiting':backend['waiting'],'actions':backend['actions'],'preview_video':preview_video,'preview_scope':'Verified local technical preview; current-source/editorial/publication approval is separate' if preview_video else None,'discovery_coverage':discovery_coverage(store.folder(job['id']),job),'source_blockers':blockers,'resumed_from_job':job.get('resumed_from_job'),'preparation_export':preparation_export,'mode':job.get('mode'),'preparation_integrity_pass':job.get('preparation_integrity_pass',False),
            'preparation_id':job.get('preparation_id'),'production_plan':job.get('production_plan'),
            'ready_for_generation':job.get('ready_for_generation',False),'generation_blockers':job.get('generation_blockers',[]),
            'ready_for_current_use':bool(export and export.get('ready_for_current_use') is True),
            'current_status_confirmed':bool(export and (export.get('delivery_check_now') or {}).get('current_status_confirmed') is True),
            'export':export,'failure':failure,'job_id':job['id'],'state':job['state'],'run_dir':job.get('run_dir'),
            'video':video,'historical_state':historical_state,
            'detail':job.get('detail'),'technical_ready_for_reuse':job.get('technical_ready_for_reuse',False),
            'editorial_approved':job['state']=='completed' and (job.get('editorial_decision') or {}).get('approved') is True,
            'cancel_command':command(store,'cancel',job['id'])['command'],
            'retry_command':command(store,'retry',job['id'])['command'],
            'ui_connected':False}
