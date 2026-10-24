"""Additive desktop backend contract; no server, UI, automatic work or network."""
import subprocess,sys
from pathlib import Path
from .common import read_json

def command(store,action,job_id):
    argv=[sys.executable,'-m','socialreel','jobs','--root',str(store.root),action,job_id]
    return {'argv':argv,'command':subprocess.list2cmdline(argv)}

def describe(store,job):
    """Describe already verified JobStore results without starting or exporting work."""
    value=dict(job);jid=job['id'];state=job['state'];queue_state=job.get('queue_state',job.get('historical_state',state))
    actions={name:command(store,name,jid) for name in ('status','cancel','retry','artifact-preview','export')}
    if state=='prepared' and job.get('preparation_integrity_pass') is True:
        argv=[sys.executable,'-m','socialreel','jobs','--root',str(store.root),'submit','--resume-job',jid]
        actions['resume']={'argv':argv,'command':subprocess.list2cmdline(argv),'creates_new_child':True,'idempotency_option':'--key','ready_for_generation':job.get('ready_for_generation',False)}
    waiting=None
    if job.get('cancel_requested') and queue_state=='running':waiting={'code':'cancellation_pending','detail':'Cancellation requested; waiting for the owned worker checkpoint/watchdog. No second worker is started.'}
    elif state=='queued':waiting={'code':'awaiting_explicit_worker','detail':'Durable request saved. Explicit work is required; the serial queue may already have an owner.'}
    elif state=='running':waiting={'code':'worker_running','detail':'Owned worker is running; poll status. Do not resubmit.'}
    elif state=='prepared':waiting={'code':'prepared_awaiting_generation' if job.get('ready_for_generation') else 'source_review_required','detail':'Saved preparation has no generated audio/video.' if job.get('ready_for_generation') else '; '.join(job.get('generation_blockers') or ['Source readiness unconfirmed'])}
    elif state=='review_required':waiting={'code':'artifact_review_required','detail':job.get('detail') or 'Stored inputs need review; automatic replay is disabled.'}
    elif state in {'failed','interrupted','rejected','cancelled'}:waiting={'code':state,'detail':job.get('detail') or 'Terminal job; no automatic replay.'}
    if state=='prepared' and job.get('source_quality'):
        quality=job['source_quality']
        if not quality.get('editorial_integrity_pass'):waiting={'code':'editorial_inputs_need_review','detail':'; '.join(quality.get('errors') or ['Script/storyboard/source consistency needs review']),'next_step':'Review source-bound script and storyboard; do not regenerate unchanged inputs'}
        elif not quality.get('ready_for_generation'):waiting={'code':'draft_awaiting_evidence_or_authorization','detail':'; '.join(quality.get('generation_blockers') or ['Generation is not authorized/ready']),'next_step':'Keep this draft; complete only the listed evidence or authorization step'}
        if 'resume' in actions:actions['resume'].update(ready_for_generation=job.get('ready_for_generation') is True,blocked_reason=waiting.get('detail') if waiting else None)
    material=job.get('current_material') or {}
    if material.get('requires_review'):
        waiting={'code':'current_material_review_required','detail':'; '.join(material['reasons']),'next_step':'Preserve saved edit; revalidate/materialize the intended exact version'}
        if 'resume' in actions:actions['resume'].update(ready_for_generation=False,blocked_reason=waiting['detail'])
    artifacts={};directory=Path(job['run_dir']) if job.get('run_dir') else None
    manifest=None;identity=None
    if directory and job.get('package_integrity_pass') is True:
        manifest=read_json(directory/'package_manifest.json');identity=manifest['package_id'];manifest={**manifest,'files':manifest['files']+read_json(directory/'media_manifest.json')['files']}
    elif directory and job.get('preparation_integrity_pass') is True:
        manifest=read_json(directory/'prepared.json');identity=manifest['preparation_id']
    if manifest:
        entries={e['path'].replace(chr(92),'/'):e for e in manifest['files']}
        oid=str(manifest.get('opportunity_id') or '')
        condition_path='source/track_conditions_'+oid+'.json'
        if oid.isascii() and oid.isdigit() and condition_path in entries:
            entry=entries[condition_path];artifacts['track_conditions']={'path':str((directory/condition_path).resolve()),'sha256':entry['sha256'],'bytes':entry['bytes'],'artifact_id':identity,'integrity_verified':True}
        for name,relative in {'source_dependencies':'source/dependencies/dependency_graph.json','script':'script.json','storyboard':'storyboard.json','claims':'claims.json','sources':'sources.json','audio':'audio/narration.wav','subtitles_srt':'subtitles.srt','subtitles_vtt':'subtitles.vtt','preview_video':'final/reel.mp4','production_plan':'production_plan.json','description':'description.md','source_quality':'source_quality.json','editorial_source_brief':'editorial_source_brief.json','assembly_inputs':'assembly-input.json'}.items():
            if relative in entries:
                entry=entries[relative];artifacts[name]={'path':str((directory/relative).resolve()),'sha256':entry['sha256'],'bytes':entry['bytes'],'artifact_id':identity,'integrity_verified':True}
    narration_profile=None
    if manifest and 'preparation_config.json' in entries:
        voice=read_json(directory/'preparation_config.json').get('voice',{})
        narration_profile={'state':'planned_not_synthesized','backend':voice.get('backend'),'voice':'af_heart' if voice.get('backend')=='kokoro' else voice.get('piper_voice'),'baseline_speed':voice.get('speed',1.0),'actual_voice_audition_verified':False}
    elif manifest and job.get('package_integrity_pass'):
        voice=read_json(directory/'result.json').get('voice') or {}
        narration_profile={'state':'stored_identity','backend':voice.get('backend'),'voice':voice.get('voice'),'baseline_speed':voice.get('speed'),'effective_playback_rate_inferred':False,'actual_voice_audition_verified':False}
    actions['workflow']=command(store,'workflow',jid)
    if 'preview_video' in artifacts:
        actions['open_preview']=command(store,'open-preview',jid)
        actions['open_preview']['launch_requires_explicit_flag']='--launch'
    from .delivery_receipt import restore_delivery
    value['delivery_receipt']=restore_delivery(store,jid,job)
    from .publication_plan import get_plan
    value['publication_plan']=get_plan(store,jid,job)
    if 'preview_video' in artifacts:actions['publication_plan']=command(store,'publication-plan',jid)
    from .content_quality import stored_quality
    from . import __version__
    value.update(narration_profile=narration_profile,source_quality=job.get('source_quality'),backend_version=__version__,content_quality=stored_quality(job),backend_contract='SOCIAL_BACKEND_V1',job_id=jid,queue_state=queue_state,queue_root=str(store.root),waiting=waiting,artifacts=artifacts,artifact_id=identity,actions=actions,ui_connected=False,publication_authorized=False)
    return value

def error(error,store=None,job_id=None):
    return {'backend_contract':'SOCIAL_BACKEND_V1','error':str(error),'detail':str(error),'error_type':type(error).__name__,'error_code':'request_blocked','state':'blocked','job_id':job_id,'queue_root':str(store.root) if store else None,'worker_started':None,'new_generation':None,'execution_outcome':'Not inferred from an error response; query the saved job identity','ui_connected':False}
