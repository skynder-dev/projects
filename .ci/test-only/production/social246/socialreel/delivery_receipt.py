"""Durable verified local delivery receipt; never searches, exports or refreshes sources."""
from pathlib import Path
import zipfile,json
from .common import ROOT,PipelineError,read_json,write_json,sha256_file,utc_now


def _identity(job):
    if job.get('package_integrity_pass') is True:return read_json(Path(job['run_dir'])/'package_manifest.json')['package_id'],'package_manifest.json'
    if job.get('preparation_integrity_pass') is True:return job['preparation_id'],'prepared.json'
    raise PipelineError('Delivery receipt requires a verified saved package or preparation')


def _roots(store):
    roots={'queue_drafts':store.root/'draft_exports','backend_exports':ROOT/'runs/exports'}
    if (ROOT/'release-catalog.json').is_file():roots['release_packages']=ROOT.parent/'packages'
    return roots


def _location(store,path):
    target=Path(path).resolve()
    if str(target).startswith('\\\\') or target.suffix.lower()!='.zip':raise PipelineError('Receipt must reference a local ZIP in an owned export location')
    for base,root in _roots(store).items():
        if target.is_relative_to(root.resolve()):return {'base':base,'path':target.relative_to(root.resolve()).as_posix()}
    raise PipelineError('ZIP is outside known Social export locations; not persisted')


def _resolve(store,location):
    if not isinstance(location,dict) or location.get('base') not in _roots(store):raise PipelineError('Unknown delivery location')
    root=_roots(store)[location['base']].resolve();path=(root/location['path']).resolve()
    if not path.is_relative_to(root) or path.suffix.lower()!='.zip' or str(path).startswith('\\\\'):raise PipelineError('Unsafe delivery location; original receipt preserved')
    return path


def _verify_archive(path,digest,identity,member):
    if not path.is_file():raise FileNotFoundError('Recorded delivery ZIP is missing')
    if sha256_file(path)!=digest:raise PipelineError('Recorded delivery ZIP hash changed')
    try:
        with zipfile.ZipFile(path) as archive:
            info=archive.getinfo(member)
            if info.file_size>2*1024*1024:raise PipelineError('Delivery identity manifest exceeds bound')
            manifest=json.loads(archive.read(info))
    except (zipfile.BadZipFile,KeyError,ValueError,RuntimeError) as error:
        raise PipelineError('Delivery ZIP identity cannot be verified: '+type(error).__name__) from error
    if manifest.get('package_id',manifest.get('preparation_id'))!=identity:raise PipelineError('ZIP belongs to a different saved package')


def remember_delivery(store,job_id,archive):
    job=store.get(job_id);identity,member=_identity(job)
    if not isinstance(archive,dict) or not archive.get('path') or not archive.get('sha256'):raise PipelineError('Verified delivery archive receipt required')
    declared=archive.get('package_id') or archive.get('preparation_id')
    if declared!=identity:raise PipelineError('Delivery archive identity differs from selected job')
    location=_location(store,archive['path']);path=_resolve(store,location);_verify_archive(path,archive['sha256'],identity,member)
    receipt=store.folder(job_id)/'delivery_receipt.json'
    try:previous=read_json(receipt)
    except (FileNotFoundError,ValueError):previous=None
    if isinstance(previous,dict) and previous.get('schema')=='SOCIAL_DELIVERY_RECEIPT_V1' and previous.get('job_id')==job_id and all(previous.get(k)==v for k,v in {'artifact_id':identity,'sha256':archive['sha256'],'location':location}.items()):return {**restore_delivery(store,job_id,job),'receipt_reused':True}
    value={'schema':'SOCIAL_DELIVERY_RECEIPT_V1','job_id':job_id,'artifact_id':identity,'identity_member':member,'sha256':archive['sha256'],'bytes':path.stat().st_size,'location':location,'recorded_at':utc_now().isoformat(),'source_observed_at':((archive.get('delivery_check_now') or {}).get('official_observation') or {}).get('fetched_at'),'scope':'Recorded past local delivery; restore verifies bytes, not current official status or editorial approval','publication_authorized':False}
    if receipt.exists():
        from .common import atomic_bytes
        old=receipt.read_bytes();atomic_bytes(store.folder(job_id)/'delivery_history'/(sha256_file(receipt)+'.json'),old)
    write_json(receipt,value)
    return {**restore_delivery(store,job_id,job),'receipt_reused':False}


def restore_delivery(store,job_id,job=None):
    receipt=store.folder(job_id)/'delivery_receipt.json'
    try:
        saved=read_json(receipt)
        if not isinstance(saved,dict) or saved.get('schema')!='SOCIAL_DELIVERY_RECEIPT_V1' or saved.get('job_id')!=job_id:raise PipelineError('Malformed delivery receipt')
        job=job or store.get(job_id);identity,member=_identity(job)
        if saved.get('artifact_id')!=identity or saved.get('identity_member')!=member:raise PipelineError('Saved delivery belongs to a different current artifact')
        path=_resolve(store,saved['location']);_verify_archive(path,saved['sha256'],identity,member)
        return {'state':'verified_existing_delivery','artifact_id':identity,'path':str(path),'sha256':saved['sha256'],'bytes':path.stat().st_size,'recorded_at':saved['recorded_at'],'source_observed_at_issue':saved.get('source_observed_at'),'current_source_confirmed':False,'editorial_approval_inferred':False,'publication_authorized':False,'re_export_required':False}
    except FileNotFoundError as error:
        return {'state':'not_recorded' if not receipt.exists() else 'missing_archive','detail':str(error),'current_source_confirmed':False,'re_export_required':receipt.exists()}
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError,RuntimeError,zipfile.BadZipFile) as error:
        return {'state':'delivery_review_required','detail':str(error)[:300],'current_source_confirmed':False,'re_export_required':True,'original_files_preserved':True}
