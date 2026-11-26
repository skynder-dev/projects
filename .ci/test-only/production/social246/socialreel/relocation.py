"""Copy verified Social CPU backend/jobs for local relocation; no installs or model copies."""
import json,shutil
from pathlib import Path
from .common import ROOT,PipelineError,read_json,write_json,sha256_file,utc_now,resolve_tool,AI_HOME,atomic_bytes
from .jobs import JobStore

EXCLUDED={'motion_catalog.py','motion_contract.py','motion_review.py','replacement.py','replacement_worker.py'}

def copy_backend(store,destination,job_ids):
    destination=Path(destination).resolve()
    if destination.is_relative_to(store.root) or destination.is_relative_to(ROOT/'socialreel'):raise PipelineError('Portable destination overlaps copied queue/backend; recursive copy refused')
    if destination.exists():raise PipelineError('Portable destination already exists; no overwrite')
    if not isinstance(job_ids,list) or not 1<=len(job_ids)<=20 or len(set(job_ids))!=len(job_ids):raise PipelineError('Select1..20distinct existing verified jobs')
    jobs=[store.get(i) for i in job_ids]
    if any(not (j.get('package_integrity_pass') is True or j.get('preparation_integrity_pass') is True) for j in jobs):raise PipelineError('Portable copy requires verified existing artifacts only')
    # Match the normal product config loader; the optional local file may be
    # absent in an installed release or contain only partial overrides.
    from .runtime import load_config,validate_config
    cfg=load_config();cfg['writer']='template';cfg['llm']={'allow_spend':False};cfg.pop('ollama',None)
    validate_config(cfg,require_models=False)
    resource=ROOT/'socialreel/owner_ru.json'
    if not resource.is_file():raise PipelineError('Required owner locale resource missing; portable copy not started')
    selected=None;selection_bytes=None;selection_state='absent'
    selection_path=store.root/'workflow_selection.json'
    if selection_path.is_file():
        try:
            selection_bytes=selection_path.read_bytes();selection=json.loads(selection_bytes.decode('utf-8'))
            if not isinstance(selection,dict) or selection.get('schema')!='SOCIAL_WORKFLOW_SELECTION_V1':raise ValueError('Invalid saved selection')
            selected=selection.get('job_id')
            selection_state='preserved' if selected in job_ids else 'not_in_selected_jobs'
        except (OSError,ValueError,UnicodeError):selection_state='unavailable_original_preserved';selected=None
    destination.mkdir(parents=True);(destination/'socialreel').mkdir()
    write_json(destination/'TRANSFER_PENDING.json',{'at':utc_now().isoformat(),'state':'copying','originals_preserved':True})
    for path in (ROOT/'socialreel').glob('*.py'):
        if path.name not in EXCLUDED:shutil.copy2(path,destination/'socialreel'/path.name)
    if (ROOT/'assets/fonts').is_dir():shutil.copytree(ROOT/'assets/fonts',destination/'assets/fonts')
    shutil.copy2(resource,destination/'socialreel/owner_ru.json')
    if sha256_file(destination/'socialreel/owner_ru.json')!=sha256_file(resource):raise PipelineError('Copied owner locale resource differs; originals preserved')
    write_json(destination/'config.json',cfg)
    write_json(destination/'runtime-paths.json',{'ai_home':str(AI_HOME),'python_executable':__import__('sys').executable,'ffmpeg':resolve_tool('ffmpeg') or 'MISSING_FFMPEG','ffprobe':resolve_tool('ffprobe') or 'MISSING_FFPROBE','models_copied':False,'downloads_allowed':False})
    target=JobStore(destination/'data/jobs');records=[]
    for job in jobs:
        jid=job['id'];folder=target.folder(jid);shutil.copytree(store.folder(jid),folder)
        with store.connect() as conn:row=dict(conn.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
        run=Path(job['run_dir']);relative=run.relative_to(store.root);row['run_dir']=relative.as_posix()
        request=json.loads(row['request_json'])
        if request.get('resume_preparation'):
            value=store.local_directory(request['resume_preparation']['directory'])
            if not value.is_relative_to(store.root):raise PipelineError('Resume reference outside source queue; copy preserved for review')
            request['resume_preparation']['directory']=value.relative_to(store.root).as_posix()
        row['request_json']=json.dumps(request,sort_keys=True)
        with target.connect() as conn:conn.execute('INSERT INTO jobs('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
        progress=folder/'progress.json'
        if progress.is_file():
            value=read_json(progress)
            if isinstance(value,dict) and isinstance(value.get('run_dir'),str):
                old=Path(value['run_dir'])
                if old.is_absolute() and old.is_relative_to(store.root):value['run_dir']=old.relative_to(store.root).as_posix();write_json(progress,value)
        if job.get('package_integrity_pass') is True:
            identity=read_json(run/'package_manifest.json')['package_id'];matches=list((ROOT/'runs/exports').glob(run.name+'_'+identity[:16]+'_v*.zip'))
            archive=max(matches,key=lambda p:int(p.stem.rsplit('_v',1)[1])) if matches else None;out=destination/'runs/exports'
        else:
            identity=job['preparation_id'];archive=store.root/'draft_exports'/(jid+'_'+identity[:16]+'.zip');out=target.root/'draft_exports'
        archive_copy=None
        if archive and archive.is_file():
            out.mkdir(parents=True,exist_ok=True);copied=out/archive.name;shutil.copy2(archive,copied)
            if sha256_file(copied)!=sha256_file(archive):raise PipelineError('Copied archive differs; originals preserved')
            archive_copy={'path':copied.relative_to(destination).as_posix(),'sha256':sha256_file(copied)}
        copied_job=target.get(jid)
        if not (copied_job.get('package_integrity_pass') is True or copied_job.get('preparation_integrity_pass') is True):raise PipelineError('Relocated artifact failed verification; originals preserved')
        records.append({'job_id':jid,'artifact_id':identity,'run_dir':relative.as_posix(),'archive':archive_copy})
    if selection_state=='preserved':atomic_bytes(target.root/'workflow_selection.json',selection_bytes)
    receipt={'schema':'SOCIAL_LOCAL_TRANSFER_V1','at':utc_now().isoformat(),'queue_root':'data/jobs','selection':{'state':selection_state,'job_id':selected if selection_state=='preserved' else None},'jobs':records,'models_copied':False,'new_generation':False,'publication_authorized':False,'scope':'Existing CPU native backend and selected verified artifacts; optional motion/replacement routes excluded, original sealed package bytes preserved'}
    write_json(destination/'TRANSFER.json',receipt);(destination/'TRANSFER_PENDING.json').unlink();return {**receipt,'destination':str(destination)}
