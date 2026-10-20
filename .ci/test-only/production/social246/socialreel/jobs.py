"""Durable, serial Social jobs. No UI, autostart, remote endpoint or arbitrary commands."""
import ctypes
from contextlib import contextmanager
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

from .common import AI_HOME, PipelineError, read_json, write_json, sha256_bytes
from .runtime import load_config, validate_config

TERMINAL = {'prepared','completed', 'rejected', 'failed', 'cancelled', 'interrupted', 'review_required'}


def process_token(pid):
    """Read process identity without sending any signal or terminating it."""
    if os.name == 'nt':
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x1000, False, int(pid))
        if not handle:
            # Access denied is uncertain, never interpreted as a dead owner.
            return 'unknown' if ctypes.get_last_error() == 5 else None
        try:
            code = wintypes.DWORD()
            if not api.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
                return None
            values = [wintypes.FILETIME() for _ in range(4)]
            if not api.GetProcessTimes(handle, *(ctypes.byref(v) for v in values)):
                return 'unknown'
            return str((values[0].dwHighDateTime << 32) | values[0].dwLowDateTime)
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
        stat = Path(f'/proc/{pid}/stat')
        return stat.read_text().rsplit(')', 1)[1].split()[19] if stat.exists() else 'unknown'
    except ProcessLookupError:
        return None
    except PermissionError:
        return 'unknown'


class JobStore:
    def __init__(self, root=None):
        self.root = Path(root or AI_HOME / 'jobs').resolve()
        if any((p/'MIGRATION_REVIEW_ONLY.json').is_file() for p in (self.root,*self.root.parents)):raise PipelineError('Review-only discovery migration copy cannot run jobs')
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'queue.sqlite3'
        with self.connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, request_key TEXT UNIQUE, request_json TEXT NOT NULL,
                  state TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                  owner_pid INTEGER, owner_token TEXT, return_code INTEGER,
                  run_dir TEXT, detail TEXT);
                CREATE INDEX IF NOT EXISTS pending ON jobs(state, created);
            ''')

    @contextmanager
    def connect(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=FULL')
            with conn:
                yield conn
        except sqlite3.DatabaseError as error:
            raise PipelineError('Queue database unavailable or corrupt; original files preserved: ' + type(error).__name__) from error
        finally:
            if conn is not None:
                conn.close()

    def folder(self, job_id):
        if not isinstance(job_id,str) or len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
            raise PipelineError('Invalid Social job identifier')
        return self.root / job_id

    def local_directory(self,value):
        path=Path(value)
        return (path if path.is_absolute() else self.root/path).resolve()

    def stored_directory(self,value):
        path=Path(value).resolve()
        return path.relative_to(self.root).as_posix() if path.is_relative_to(self.root) else str(path)

    def submit(self, config=None, opportunity=None, request_key=None, timeout=900, stop_after=None, writer=None, resume_job=None, public_source=None, retry_of=None, visual_revision=None):
        if resume_job is not None and opportunity is not None:
            raise PipelineError("Cannot combine resume job with opportunity override")
        resume=None
        if resume_job is not None:
            source=self.get(resume_job)
            if (source.get('current_material') or {}).get('requires_review') and not (stop_after=='script' and visual_revision is not None):raise PipelineError('Current material changed; plain resume would ignore saved edits/source version')
            if source.get('mode')=='source_only_fact_materialization':raise PipelineError('Fact-aligned source-only preparation cannot enter the legacy resume writer; preserve its exact scenario and accepted ledger')
            from .fact_versions import view as fact_view
            if fact_view(self,resume_job)['fact_version']:raise PipelineError('Accepted fact version needs a new aligned source/script preparation; resuming the old preparation is refused')
            if source.get('state')!='prepared' or source.get('preparation_integrity_pass') is not True:
                raise PipelineError('Resume source must be a verified prepared job in this queue')
            if stop_after is None and source.get('ready_for_generation') is not True:raise PipelineError('Prepared source conditions are blocked; model generation refused, prepare-only correction remains available')
            resume={'job_id':resume_job,'directory':self.stored_directory(source['run_dir']),'preparation_id':source['preparation_id']}
            if config is None:config=Path(source['run_dir'])/'preparation_config.json'
        cfg=load_config(config)
        if writer is not None:cfg['writer']=writer
        if visual_revision is not None:
            if stop_after!='script' or resume is None or public_source is not None:raise PipelineError('Visual materialization is a source-only resume with no source/network override')
            from .visual_revision import validate_parent
            validate_parent(self.local_directory(resume['directory']),visual_revision)
            cfg={**cfg,'preparation_refresh_source':False}

        if public_source is not None:
            from .public_page import validate
            validate(public_source,cfg)
            if stop_after!='script' or resume_job is not None or opportunity is not None:raise PipelineError('Public jobs must use only source/script target and fixed source')
        if stop_after is None and cfg.get('generation_hold'):raise PipelineError('Generation held before queue submission: '+str(cfg['generation_hold']))
        validate_config(cfg,require_models=stop_after is None)
        if stop_after not in (None,'script'):raise PipelineError('Unsupported durable preparation target')
        from .local_editorial import authorized as editorial_authorized
        if stop_after and cfg.get('writer')!='template' and not editorial_authorized(cfg):raise PipelineError('Prepare-only jobs require explicit template writer')
        if not 1 <= int(timeout) <= 900:
            raise PipelineError('Production timeout must be between 1 and 900 seconds')
        if opportunity is not None and not str(opportunity).isdigit():
            raise PipelineError('Opportunity identifier must be numeric')
        if request_key is not None and not 1 <= len(request_key) <= 128:
            raise PipelineError('Invalid idempotency key')
        retry_parent=None
        if retry_of is not None:
            self.folder(retry_of)
            previous=self.get(retry_of)
            if previous['state'] not in {'failed','interrupted','cancelled','rejected','review_required'}:raise PipelineError('Retry parent is not a finished unsuccessful job')
            with self.connect() as connection:parent_row=connection.execute('SELECT request_json FROM jobs WHERE id=?',(retry_of,)).fetchone()
            parent_request=json.loads(parent_row[0])
            if cfg!=parent_request.get('config') or int(timeout)!=parent_request.get('timeout') or opportunity!=parent_request.get('opportunity') or stop_after!=parent_request.get('stop_after') or public_source!=parent_request.get('public_source') or visual_revision!=parent_request.get('visual_revision') or resume!=(parent_request.get('resume_preparation')):raise PipelineError('Retry inputs differ from the durable parent; submit an explicit new request instead')
            retry_parent={'job_id':retry_of,'request_sha256':sha256_bytes(parent_row[0].encode('utf-8'))}
        payload_data={'config':cfg,'opportunity':opportunity,'timeout':int(timeout)}
        if stop_after:payload_data['stop_after']=stop_after
        if public_source is not None:payload_data['public_source']=public_source
        if retry_parent is not None:payload_data['retry_parent']=retry_parent
        if visual_revision is not None:payload_data['visual_revision']=visual_revision
        if resume:payload_data['resume_preparation']=resume
        payload=json.dumps(payload_data,sort_keys=True)
        job_id = uuid.uuid4().hex
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if request_key:
                old = conn.execute('SELECT * FROM jobs WHERE request_key=?', (request_key,)).fetchone()
                if old:
                    old_request=json.loads(old['request_json'])
                    if old_request.get('resume_preparation'):
                        old_request['resume_preparation']['directory']=self.stored_directory(self.local_directory(old_request['resume_preparation']['directory']))
                    if json.dumps(old_request,sort_keys=True) != payload:
                        raise PipelineError('Idempotency key already belongs to a different request')
                    return self.get(old['id'])
            folder = self.folder(job_id)
            folder.mkdir()
            write_json(folder / 'config.json', cfg)
            if retry_parent is not None and public_source is not None:
                from .public_page import clone_cache
                try:clone_cache(self.folder(retry_parent['job_id'])/'public_input',folder/'public_input')
                except (OSError,PipelineError) as error:raise PipelineError('Retry source cache copy failed; no queued child was committed: '+str(error)[:250]) from error
            now = time.time()
            conn.execute('INSERT INTO jobs(id,request_key,request_json,state,created,updated) VALUES(?,?,?,?,?,?)',
                         (job_id, request_key, payload, 'queued', now, now))
        return self.get(job_id)

    def get(self, job_id):
        folder = self.folder(job_id)
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            raise PipelineError('Social job not found')
        if row['state'] not in TERMINAL | {'queued','running'}:
            raise PipelineError('Unknown durable job state; original database preserved')
        result = {k: row[k] for k in row.keys() if k != 'request_json'}
        if result.get('run_dir'):result['run_dir']=str(self.local_directory(result['run_dir']))
        result.update(job_id=row['id'],queue_state=row['state'],cancel_requested=(folder/'cancel').exists())
        from .writer_contract import route
        try:
            pinned=json.loads(row['request_json']);result['writer_route']=route(pinned.get('config'))
        except (ValueError,TypeError,AttributeError):result['writer_route']=route()
        try:
            request=json.loads(row['request_json']);result['resumed_from_job']=(request.get('resume_preparation') or {}).get('job_id');result['retry_parent']=request.get('retry_parent')
        except (ValueError,TypeError,AttributeError):result['resumed_from_job']=None;result['retry_parent']=None
        try:
            result['progress'] = read_json(folder / 'progress.json')
        except (OSError, ValueError) as error:
            result['progress'] = None
            result['progress_error'] = type(error).__name__
        if isinstance(result.get('progress'),dict) and result['progress'].get('run_dir') and not Path(result['progress']['run_dir']).is_absolute():
            result['progress']['run_dir']=str(self.local_directory(result['progress']['run_dir']))
        if result['state']=='completed':
            result['package_integrity_pass']=False;result['technical_ready_for_reuse']=False;result['ready_for_reuse']=False
            if not result.get('run_dir'):result['package_errors']=['Completed job has no run directory']
        if result['state'] == 'completed' and result.get('run_dir'):
            from .packages import source_freshness, verify_package
            directory = Path(result['run_dir']).resolve()
            if not directory.is_relative_to((folder/'runs').resolve()):
                result['ready_for_reuse'] = False
                result['package_errors'] = ['Run directory outside owned job']
            else:
                integrity = verify_package(directory)
                result['package_integrity_pass']=integrity['pass']
                freshness = source_freshness(directory)
                result['source_freshness'] = freshness
                result['technical_ready_for_reuse'] = integrity['pass'] and freshness['fresh']
                editorial_raw=None
                try:
                    editorial_raw=(folder/'editorial_review.json').read_bytes()
                    editorial=json.loads(editorial_raw.decode('utf-8'))
                except FileNotFoundError:
                    editorial = None
                except (OSError,ValueError):
                    editorial = {'approved':False,'reason':'Unreadable editorial state'}
                if editorial is not None and not isinstance(editorial,dict):
                    editorial={'approved':False,'reason':'Malformed editorial state'}
                result['editorial_review'] = editorial
                from .workflow import editorial_state
                package_id=read_json(directory/'package_manifest.json')['package_id'] if integrity['pass'] else None
                result['editorial_decision']=editorial_state(editorial,package_id)
                result['editorial_decision']['revision']=sha256_bytes(editorial_raw) if editorial_raw is not None else None
                result['stored_editorially_ready'] = result['technical_ready_for_reuse'] and result['editorial_decision']['approved']
                result['ready_for_reuse'] = False
                result['current_status_confirmed'] = False
                result['delivery_recheck_required'] = True
                result['readiness_scope'] = 'Stored technical/editorial checks only; issue-time live source recheck required'
                result['package_errors'] = integrity['errors']
        if result['state']=='prepared':
            result.update(preparation_integrity_pass=False,ready_for_generation=False,ready_for_reuse=False,current_status_confirmed=False)
            from .preparation import verify_preparation
            try:
                directory=Path(result['run_dir']).resolve()
                if not directory.is_relative_to((folder/'runs').resolve()):raise PipelineError('Prepared run outside owned job')
                manifest=verify_preparation(directory)
                from .claims import validate_script
                errors=validate_script(read_json(directory/'script.json'),read_json(directory/'claims.json')['claims'])
                if errors:raise PipelineError('; '.join(errors))
                plan=read_json(directory/'production_plan.json')
                from .packages import source_freshness
                fresh=source_freshness(directory)
                result['stored_snapshot_freshness_now']=fresh
                result.update(preparation_integrity_pass=True,preparation_id=manifest['preparation_id'],
                              ready_for_generation=manifest.get('ready_for_generation') is True and fresh['fresh'],
                              generation_blockers=manifest.get('generation_blockers',[])+fresh['reasons'],mode=manifest['mode'],production_plan=str(directory/'production_plan.json'))
                from .source_quality import inspect_directory
                quality=inspect_directory(directory)
                result['source_quality']=quality
                result['generation_blockers']=list(dict.fromkeys(result['generation_blockers']+quality['generation_blockers']))
                result['ready_for_generation']=result['ready_for_generation'] and quality['ready_for_generation']
                correction=folder/'preparation_correction.json'
                if correction.exists():
                    note=read_json(correction)
                    if not isinstance(note,dict):raise PipelineError('Preparation correction has invalid shape')
                    if not isinstance(note.get('reason'),str) or not note['reason'].strip() or len(note['reason'])>1000:raise PipelineError('Preparation correction needs a nonempty bounded reason')
                    if note.get('schema')!='SOCIAL_PREPARATION_CORRECTION_V1' or note.get('preparation_id')!=manifest['preparation_id']:raise PipelineError('Preparation correction identity mismatch')
                    result.update(ready_for_generation=False,generation_blockers=result['generation_blockers']+[note['reason']],source_correction=note)
            except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:
                reason='Prepared inputs unavailable: '+str(error)[:300]
                if 'source_quality' in result:result['historical_source_quality']=result['source_quality']
                result.update(state='review_required',historical_state='prepared',detail=reason,preparation_integrity_pass=False,ready_for_generation=False,ready_for_reuse=False,current_status_confirmed=False,preparation_identity_scope='historical_only',generation_blockers=list(dict.fromkeys(list(result.get('generation_blockers') or [])+[reason])),source_quality={'editorial_integrity_pass':False,'ready_for_generation':False,'generation_blockers':[reason],'errors':[reason],'scope':'Current preparation failed validation; earlier intermediate readiness revoked'})
        if result['state']=='completed' and result.get('package_integrity_pass') is not True:
            result['historical_state']='completed';result['state']='review_required'
            result['detail']='Stored completion is not deliverable: '+ '; '.join(result.get('package_errors') or ['Package/video integrity unavailable'])
        from .material_currentness import status as material_status,effective_decision
        material=material_status(self,job_id,result);result['current_material']=material
        if material['requires_review']:
            result['original_package_editorial_decision']=result.get('editorial_decision')
            result['editorial_decision']=effective_decision(result.get('editorial_decision'),material)
            result['stored_editorially_ready']=False;result['ready_for_generation']=False
            result['generation_blockers']=list(result.get('generation_blockers') or [])+material['reasons']
        return result

    def list(self):
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute('SELECT id,state,created,updated FROM jobs ORDER BY created DESC LIMIT 100')]
        items=[]
        for row in rows:
            try:items.append(self.get(row['id']))
            except (PipelineError,OSError,ValueError,TypeError,KeyError,AttributeError) as error:
                items.append({**row,'job_id':row['id'],'queue_state':row['state'],'historical_state':row['state'],'state':'review_required',
                              'row_unavailable':True,'detail':'Saved job unavailable; original preserved: '+str(error)[:500],
                              'package_integrity_pass':False,'preparation_integrity_pass':False,'ready_for_reuse':False,'current_status_confirmed':False})
        return items

    def history(self,limit=50,cursor=None):
        """Paginated metadata only. Never substitutes for get/artifact verification."""
        import base64,math
        if type(limit) is not int or not 1<=limit<=100:raise PipelineError('History page limit must be1..100')
        after=None
        if cursor is not None:
            try:
                if not isinstance(cursor,str) or not 1<=len(cursor)<=512:raise ValueError('cursor length')
                token=json.loads(base64.urlsafe_b64decode(cursor.encode('ascii')).decode('utf-8'))
                if not isinstance(token,dict) or token.get('v')!=1:raise ValueError('cursor version')
                created=token['created'];identity=token['id']
                if type(created) not in (float,int) or not math.isfinite(created):raise ValueError('cursor timestamp')
                self.folder(identity);after=(created,identity)
            except (ValueError,KeyError,TypeError,UnicodeError,OverflowError) as error:raise PipelineError('Invalid Social history cursor') from error
        with self.connect() as conn:
            conn.execute('BEGIN')
            total=conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
            query='SELECT id,state,created,updated,return_code,detail FROM jobs'
            params=[]
            if after is not None:query+=' WHERE (created,id)<(?,?)';params.extend(after)
            query+=' ORDER BY created DESC,id DESC LIMIT ?';params.append(limit+1)
            rows=[dict(row) for row in conn.execute(query,params)]
        more=len(rows)>limit;rows=rows[:limit];next_cursor=None
        if more and rows:
            last=rows[-1];next_cursor=base64.urlsafe_b64encode(json.dumps({'v':1,'created':last['created'],'id':last['id']},separators=(',',':')).encode()).decode('ascii')
        items=[]
        for row in rows:
            state=row['state'];known=state in TERMINAL|{'queued','running'}
            items.append({**row,'job_id':row['id'],'queue_state':state,'state':state if known else 'review_required',
                          'row_unavailable':not known,'content_quality_checked':False,'integrity_checked':False,'artifact_lookup_required':True,
                          'ready_for_reuse':False,'current_status_confirmed':False,'readiness_scope':'Queue metadata only; use status/artifact-preview/export for actual artifact checks'})
        return {'backend_contract':'SOCIAL_BACKEND_V1','items':items,'total':total,'limit':limit,'next_cursor':next_cursor,'has_more':more,
                'queue_root':str(self.root),'verification_scope':'metadata_only','integrity_checked':False,
                'worker_started':False,'new_generation':False,'pagination':'Descending(created,id); newer inserted jobs do not shift subsequent pages'}

    def cancel(self, job_id):
        folder = self.folder(job_id)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                raise PipelineError('Social job not found')
            if row['state'] not in TERMINAL:
                (folder / 'cancel').touch()
                if row['state'] == 'queued':
                    conn.execute('UPDATE jobs SET state=?,updated=?,detail=? WHERE id=?',
                                 ('cancelled', time.time(), 'Cancelled before execution', job_id))
        return self.get(job_id)

    def claim(self, job_id=None):
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            allowed = sorted(TERMINAL | {'queued','running'})
            invalid = conn.execute('SELECT id FROM jobs WHERE state NOT IN (' + ','.join('?' for _ in allowed) + ') LIMIT 1', allowed).fetchone()
            if invalid:
                raise PipelineError('Unknown durable job state; queue execution refused, data preserved')
            if conn.execute("SELECT 1 FROM jobs WHERE state='running'").fetchone():
                return None
            row = (conn.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1") if job_id is None else conn.execute("SELECT * FROM jobs WHERE state='queued' AND id=?", (job_id,))).fetchone()
            if row is None:
                return None
            conn.execute('UPDATE jobs SET state=?,owner_pid=?,owner_token=?,updated=? WHERE id=?',
                         ('running', os.getpid(), process_token(os.getpid()), time.time(), row['id']))
            return dict(row)

    def finish(self, job_id, state, code=None, run_dir=None, detail=None):
        if state not in TERMINAL:
            raise PipelineError('Invalid terminal job state')
        folder = self.folder(job_id)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:raise PipelineError('Social job not found')
            # A late worker/recovery result cannot rewrite a terminal receipt.
            if row['state'] not in TERMINAL:
                if (folder/'cancel').exists():
                    state,code,run_dir,detail='cancelled',130,None,'Cancellation preserved before terminal commit'
                conn.execute('UPDATE jobs SET state=?,return_code=?,run_dir=?,detail=?,updated=? WHERE id=?',
                             (state, code, self.stored_directory(run_dir) if run_dir else None, detail, time.time(), job_id))
        return self.get(job_id)

    def completed_package(self, job_id):
        from .packages import verify_package
        runs = self.folder(job_id) / 'runs'
        for path in sorted(runs.glob('*/result.json')):
            if path.parent.name.startswith('_incomplete_'):
                continue
            try:
                result = read_json(path)
                integrity = verify_package(path.parent)
                if integrity['pass']:
                    return path.parent, result
            except (OSError, ValueError):
                pass
        return None, None

    def prepared_package(self,job_id):
        from .preparation import verify_preparation
        from .claims import validate_script
        for path in sorted((self.folder(job_id)/'runs').glob('prepared_*/prepared.json')):
            try:
                manifest=verify_preparation(path.parent)
                if not validate_script(read_json(path.parent/'script.json'),read_json(path.parent/'claims.json')['claims']):
                    return path.parent,manifest
            except (PipelineError,OSError,ValueError,KeyError,TypeError):pass
        return None,None

    def recover(self):
        """Recover verified completed bytes, otherwise mark dead work interrupted; never resubmit it."""
        with self.connect() as conn:
            rows = list(conn.execute("SELECT * FROM jobs WHERE state='running'"))
        recovered = []
        for row in rows:
            current = process_token(row['owner_pid']) if row['owner_pid'] else None
            if current == 'unknown' or (current is not None and current == row['owner_token']):
                continue
            if (self.folder(row['id']) / 'cancel').exists():
                recovered.append(self.finish(row['id'], 'cancelled', detail='Cancellation preserved after owner exit'))
                continue
            try:target=json.loads(row['request_json']).get('stop_after')
            except (ValueError,TypeError,AttributeError):target=None
            if target=='script':
                prepared,manifest=self.prepared_package(row['id'])
                if manifest:
                    recovered.append(self.finish(row['id'],'prepared',run_dir=prepared,detail='Recovered verified preparation; generation not started'))
                    continue
            directory, result = self.completed_package(row['id'])
            if result:
                from .packages import source_freshness
                state = ('completed' if source_freshness(directory)['fresh'] else 'review_required') if result.get('accepted') is True else 'rejected'
                recovered.append(self.finish(row['id'], state, run_dir=directory, detail='Recovered verified package after worker exit'))
            else:
                state = 'cancelled' if (self.folder(row['id']) / 'cancel').exists() else 'interrupted'
                recovered.append(self.finish(row['id'], state, detail='Owner exited; no automatic replay. Cached assets retained.'))
        return recovered

    def retry(self, job_id, request_key=None):
        old = self.get(job_id)
        if old['state'] not in {'failed', 'interrupted', 'cancelled', 'rejected', 'review_required'}:
            raise PipelineError('Only a finished unsuccessful job can be retried explicitly')
        with self.connect() as conn:
            row = conn.execute('SELECT request_json FROM jobs WHERE id=?', (job_id,)).fetchone()
        request = json.loads(row[0])
        new=self.submit(self.folder(job_id) / 'config.json', request['opportunity'], request_key, request['timeout'],stop_after=request.get('stop_after'),resume_job=(request.get('resume_preparation') or {}).get('job_id'),public_source=request.get('public_source'),retry_of=job_id,visual_revision=request.get('visual_revision'))
        return new

    def work_once(self, job_id=None):
        from .watchdog import run_command
        self.recover()
        row = self.claim(job_id)
        if row is None:
            return None
        job_id = row['id']
        folder = self.folder(job_id)
        try:
            request = json.loads(row['request_json'])
            if not isinstance(request, dict) or not {'config','opportunity','timeout'}.issubset(request):
                raise PipelineError('Incomplete durable request')
            if type(request['timeout']) is not int or not 1 <= request['timeout'] <= 900:
                raise PipelineError('Invalid durable timeout')
            if request['opportunity'] is not None and not str(request['opportunity']).isdigit():
                raise PipelineError('Invalid durable opportunity')
            config = read_json(folder / 'config.json')
            if config != request['config']:
                raise PipelineError('Job config differs from the durable submitted snapshot')
            if request.get('stop_after') is None and config.get('generation_hold'):raise PipelineError('Generation held before worker launch: '+str(config['generation_hold']))
            validate_config(config,require_models=request.get('stop_after') is None)
            if request.get('public_source') is not None:
                from .public_page import validate
                validate(request['public_source'],config)
                if request.get('stop_after')!='script' or request.get('resume_preparation') or request['opportunity'] is not None:raise PipelineError('Invalid public source-only durable request')
            resume=request.get('resume_preparation')
            if resume is not None:
                if not isinstance(resume,dict):raise PipelineError('Invalid prepared input reference')
                source=self.get(resume['job_id'])
                if (source.get('current_material') or {}).get('requires_review') and request.get('visual_revision') is None:raise PipelineError('Pinned current material changed since enqueue; no worker launched')
                if source.get('state')!='prepared' or source.get('preparation_integrity_pass') is not True or source.get('preparation_id')!=resume['preparation_id'] or Path(source['run_dir']).resolve()!=self.local_directory(resume['directory']):
                    raise PipelineError('Pinned prepared inputs changed or unavailable')
                if request.get('stop_after') is None and source.get('ready_for_generation') is not True:
                    raise PipelineError('Pinned preparation is no longer generation-ready; no worker launched')
            if request.get('visual_revision') is not None:
                if request.get('stop_after')!='script' or resume is None or request.get('public_source') or config.get('preparation_refresh_source') is not False:raise PipelineError('Invalid durable visual-only request')
                from .visual_revision import validate_parent
                validate_parent(self.local_directory(resume['directory']),request['visual_revision'])
            from .local_editorial import authorized as editorial_authorized
            if request.get('stop_after') not in (None,'script') or (request.get('stop_after') and config.get('writer')!='template' and not editorial_authorized(config)):
                raise PipelineError('Invalid durable preparation target/writer')
        except (OSError, ValueError, KeyError, TypeError, PipelineError) as error:
            return self.finish(job_id, 'failed', detail='Invalid durable job request: ' + type(error).__name__ + ': ' + str(error)[:300])
        request = json.loads(row['request_json'])
        command = [sys.executable, '-m', 'socialreel', 'run', '--config', str(folder / 'config.json'),
                   '--out', str(folder / 'runs'), '--history', str(self.root / 'history.json')]
        if request.get('resume_preparation'):command+=['--resume-prepared',str(self.local_directory(request['resume_preparation']['directory']))]
        if request.get('stop_after')=='script':command+=['--stop-after','script']
        if request.get('visual_revision') is not None:
            write_json(folder/'visual_revision.json',request['visual_revision']);command+=['--visual-revision',str(folder/'visual_revision.json')]
        if request['opportunity']:
            command += ['--opportunity', str(request['opportunity'])]
        if request.get('public_source') is not None:
            write_json(folder/'public_request.json',{'public_source':request['public_source']})
            command=[sys.executable,'-m','socialreel.public_page','--job-folder',str(folder),'--history',str(self.root/'history.json')]
        env = dict(os.environ, SOCIAL_MANAGED_WORKER='1', SOCIAL_CANCEL_FILE=str(folder / 'cancel'),
                   SOCIAL_PROGRESS_FILE=str(folder / 'progress.json'), SOCIAL_NETWORK_AUDIT_FILE=str(folder / 'network.json'), PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
        for secret in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY'):
            env.pop(secret, None)
        try:
            from .common import ROOT
            code = run_command(command, folder / 'worker.log', request['timeout'], folder / 'cancel', env, cwd=ROOT)
            directory, result = self.completed_package(job_id)
            prepared,manifest=self.prepared_package(job_id) if request.get('stop_after')=='script' else (None,None)
            if code == 130 or (request.get('public_source') and (folder/'cancel').exists()):
                state, detail = 'cancelled', 'Cancelled own worker and descendants'
            elif code == 124:
                state, detail = 'failed', 'Production deadline exceeded; own worker stopped'
            elif code==0 and manifest:
                state,detail='prepared','Verified source/script/tasks saved; generation not started'
                directory=prepared
            elif result and code in (0, 1) and (code == 0 or result.get('accepted') is False):
                from .packages import source_freshness
                fresh = source_freshness(directory)
                state = ('completed' if fresh['fresh'] else 'review_required') if result.get('accepted') is True else 'rejected'
                detail = 'Package bytes verified' if fresh['fresh'] else 'Stored source stale; refresh required before reuse'
            else:
                state, detail = 'failed', 'No valid package; see this job worker log'
                if request.get('public_source') and (folder/'public_error.json').is_file():detail='Public source preparation: '+str(read_json(folder/'public_error.json').get('detail','See saved receipt'))[:500]
            return self.finish(job_id, state, code, directory, detail)
        except Exception as e:
            return self.finish(job_id, 'failed', detail='Worker error: ' + type(e).__name__)
