"""Local release review entry point over existing backend; no inference, UI or installs."""
import json,sqlite3,zipfile,shutil,uuid,time,importlib.metadata
from pathlib import Path
from . import __version__
from .common import ROOT,CONTRACT,PipelineError,read_json,write_json,sha256_file,sha256_bytes,stable_json,utc_now

def _core():
    checks=[]
    for name in ('Pillow','num2words'):
        try:checks.append({'dependency':name,'available':True,'version':importlib.metadata.version(name)})
        except importlib.metadata.PackageNotFoundError:checks.append({'dependency':name,'available':False,'detail':'Missing in this interpreter; use configured installed Python; no download attempted'})
    return checks

def _manifest():
    manifest=read_json(ROOT/'release_manifest.json')
    if manifest.get('version')!=__version__ or manifest.get('contract')!=CONTRACT:raise PipelineError('Release version/contract mismatch; originals preserved')
    for entry in manifest['files']:
        path=(ROOT/entry['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or path.stat().st_size!=entry['bytes'] or sha256_file(path)!=entry['sha256']:raise PipelineError('Release code/config changed: '+entry['path'])
    return manifest

def _saved_request(item):
    meta=item.get('saved_job_metadata') or {}
    return meta.get('request') or {'config':read_json(ROOT/'config.json'),'opportunity':item['opportunity_id'],'timeout':600}

def _intent(item,request):
    return {'schema':'SOCIAL_RC_IMPORT_INTENT_V1','job_id':item['job_id'],'package_id':item['package_id'],'archive_sha256':item['archive_sha256'],'run_name':item['run_name'],
            'request_sha256':sha256_bytes(stable_json(request).encode()),'config_sha256':sha256_bytes(stable_json(request['config']).encode())}

def _validate_import(folder,item,request):
    from .packages import verify_package
    expected=_intent(item,request);saved=read_json(folder/'release_import_receipt.json')
    if any(saved.get(k)!=v for k,v in expected.items()):raise PipelineError('Unregistered folder has no matching owned import receipt; preserved')
    if sha256_file(folder/'config.json')!=expected['config_sha256']:raise PipelineError('Import config changed after interruption; external changes preserved, no registration')
    run=folder/'runs'/item['run_name'];check=verify_package(run)
    if not check['pass'] or read_json(run/'package_manifest.json')['package_id']!=item['package_id']:raise PipelineError('Relocated import bytes changed; preserved, no registration')

def _register_import(store,item,folder,request):
    metadata=item.get('saved_job_metadata') or {};now=time.time();key=metadata.get('request_key') or 'release-import:'+item['package_id']
    with store.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT id FROM jobs WHERE id=?',(item['job_id'],)).fetchone():raise PipelineError('Another writer registered this ID; preserved, retry check')
        conn.execute('INSERT INTO jobs(id,request_key,request_json,state,created,updated,return_code,run_dir,detail) VALUES(?,?,?,?,?,?,?,?,?)',
          (item['job_id'],key,json.dumps(request,sort_keys=True),'completed',metadata.get('created',now),metadata.get('updated',now),metadata.get('return_code',0),
           (folder/'runs'/item['run_name']).relative_to(store.root).as_posix(),'Imported existing verified local package; original saved request/identity preserved; no generation'))

def _bootstrap(store):
    from .motion_state import motion_lock
    with motion_lock(store.root,'release_import',wait=5):
        imports=_bootstrap_locked(store)
        from .delivery_receipt import remember_delivery
        labels={i['job_id']:i for i in imports}
        for item in read_json(ROOT/'release-catalog.json')['packages']:
            archive={'path':str(ROOT.parent/'packages'/item['archive']),'sha256':item['archive_sha256'],'package_id':item['package_id']}
            try:
                receipt=remember_delivery(store,item['job_id'],archive)
                labels[item['job_id']]['delivery_receipt_state']=receipt['state']
            except (PipelineError,OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
                labels[item['job_id']]['delivery_receipt_state']='not_saved'
                labels[item['job_id']]['delivery_receipt_error']=str(error)[:200]
        return imports

def _bootstrap_locked(store):
    from .packages import verify_package
    catalog=read_json(ROOT/'release-catalog.json');imports=[];packages=(ROOT.parent/'packages').resolve()
    for item in catalog['packages']:
        jid=item['job_id'];store.folder(jid)
        if Path(item['run_name']).name!=item['run_name']:raise PipelineError('Invalid release run name')
        archive=(packages/item['archive']).resolve()
        if archive.parent!=packages or not archive.is_file() or sha256_file(archive)!=item['archive_sha256']:raise PipelineError('Separate local package missing/changed: '+item['archive'])
        with store.connect() as conn:existing=conn.execute('SELECT id FROM jobs WHERE id=?',(jid,)).fetchone()
        if existing:
            job=store.get(jid)
            if job.get('package_integrity_pass') is not True or read_json(Path(job['run_dir'])/'package_manifest.json')['package_id']!=item['package_id']:raise PipelineError('Saved job identity conflict; no overwrite: '+jid)
            imports.append({'job_id':jid,'reused_saved_job':True});continue
        final=store.folder(jid);request=_saved_request(item)
        if final.exists():
            _validate_import(final,item,request);_register_import(store,item,final,request)
            imports.append({'job_id':jid,'recovered_registration':True,'media_recopied':False});continue
        stage=store.root/('_release_import_'+uuid.uuid4().hex);run=stage/'runs'/item['run_name'];run.mkdir(parents=True)
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            if len(infos)>1000 or sum(i.file_size for i in infos)>128*1024**2:raise PipelineError('Package exceeds local review import bounds')
            for info in infos:
                target=(run/info.filename).resolve()
                if not target.is_relative_to(run.resolve()) or info.flag_bits&1 or (info.external_attr>>16)&0o170000==0o120000:raise PipelineError('Unsafe package member; no import')
            if z.testzip() is not None:raise PipelineError('Package CRC failure')
            z.extractall(run)
        check=verify_package(run)
        if not check['pass'] or read_json(run/'package_manifest.json')['package_id']!=item['package_id']:raise PipelineError('Imported package failed exact verification: '+str(check['errors'])[:300])
        write_json(stage/'config.json',request['config']);write_json(stage/'editorial_review.json',{'approved':False,'package_id':item['package_id'],'reason':'Release technical review only; no subjective listening/editorial approval','publication_authorized':False})
        write_json(stage/'release_import_receipt.json',{**_intent(item,request),'prepared_at':utc_now().isoformat(),'scope':'Owned import intent; database row is registration status; preserve all unrelated user files'})
        stage.rename(final);_register_import(store,item,final,request);imports.append({'job_id':jid,'imported_existing_package':True})
    return imports

def run(action,job_id=None,root=None,limit=100,cursor=None,remember=False,launch=False,editorial=None,publication=None):
    envelope={'version':__version__,'contract':CONTRACT,'ui_connected':False,'animation_accepted':False,'editorial_approved':False,'publication_authorized':False,'inference_started':False}
    _manifest();core=_core()
    if not all(i['available'] for i in core):return {**envelope,'state':'blocked','reason':'review_dependencies_missing','dependencies':core,'downloads_attempted':False},2
    from .jobs import JobStore
    from .backend_contract import describe
    store=JobStore(root or ROOT/'data/jobs');imports=_bootstrap(store) if root is None else []
    if action=='check':
        from .runtime import doctor
        jobs=store.list();verified=[describe(store,j) for j in jobs];issues=[{'job_id':j['id'],'state':j['state'],'detail':j.get('detail')} for j in jobs if j.get('row_unavailable') or (j['queue_state']=='completed' and not j.get('package_integrity_pass'))]
        return {**envelope,'state':'technical_review_ready' if not issues else 'review_required','release_integrity_pass':True,'review_dependencies':core,'generation_dependencies':doctor(),'queue_root':str(store.root),'local_imports':imports,'saved_job_count':store.history(1)['total'],'full_integrity_job_count':len(jobs),'verification_scope':'Latest100 saved jobs; use paginated list/status for older history','job_checks':[{'job_id':j['job_id'],'queue_state':j['queue_state'],'integrity':j.get('package_integrity_pass',j.get('preparation_integrity_pass',False)),'content_quality':j['content_quality']} for j in verified],'issues':issues,'scope':'Local technical release review; no live source check, UI acceptance, animation acceptance or listening approval'},0 if not issues else 2
    if action=='list':
        history=store.history(limit,cursor);labels={i['job_id']:i for i in read_json(ROOT/'release-catalog.json')['packages']}
        for item in history['items']:
            label=labels.get(item['job_id'])
            if label:item.update(title=label['title'],opportunity_id=label['opportunity_id'],title_scope='Saved release catalog label; selected artifact verification remains required')
        return {**envelope,**history},0
    if action=='workflow':
        from .workflow import restore_workflow
        return {**envelope,**restore_workflow(store,job_id,remember)},0
    if action=='open-preview':
        from .workflow import preview_open
        value=preview_open(store,job_id,launch)
        return {**envelope,**value},2 if value['state']=='open_failed' else 0
    if action=='review':
        from .workflow import record_editorial
        return {**envelope,**record_editorial(store,job_id,**(editorial or {}))},0
    if action in {'plan-publication','publication-plan'}:
        from .publication_plan import prepare_plan,get_plan
        options=publication or {}
        value=prepare_plan(store,job_id,options['package_id'],options.get('when'),options.get('timezone'),options.get('destination'),options.get('revision'),options.get('clear_time',False)) if action=='plan-publication' else get_plan(store,job_id)
        return {**envelope,**value},2 if value['state']=='plan_review_required' else 0
    if action=='preview':
        job=store.get(job_id);return {**envelope,**describe(store,job)},0 if job.get('package_integrity_pass') is True or job.get('preparation_integrity_pass') is True else 2
    if action=='export':
        from .production import deliver_existing
        job=store.get(job_id)
        if job.get('package_integrity_pass') is True:
            package=read_json(Path(job['run_dir'])/'package_manifest.json')['package_id'];matches=list((ROOT.parent/'packages').glob('*.zip'));catalog=read_json(ROOT/'release-catalog.json');entry=next((i for i in catalog['packages'] if i['package_id']==package),None)
            if entry:
                from .export import export_package
                archive=export_package(job['run_dir'],ROOT.parent/'packages'/entry['archive'],online=False)
                from .delivery_receipt import remember_delivery
                receipt=remember_delivery(store,job_id,archive)
                return {**envelope,**describe(store,job),'export':archive,'delivery_receipt':receipt,'current_status_confirmed':False,'scope':'Existing verified local ZIP reused; source currency and editorial quality remain separate'},0
        result=deliver_existing(store,job_id,online=False);archive=result.get('export') or result.get('preparation_export');return {**envelope,**result},0 if archive and archive.get('path') else 2
    raise PipelineError('Unknown release action')
