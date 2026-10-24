"""Durable sequential issue of existing Social artifacts; never submits/generates jobs."""
import re,uuid,hashlib,json,os,shutil
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file,utc_now,ROOT,stable_json,sha256_bytes,atomic_bytes
from .motion_state import motion_lock

class ArtifactBatch:
    def __init__(self,store):self.store=store;self.root=store.root/'artifact_batches';self.root.mkdir(exist_ok=True)
    def list(self):
        items=[]
        for folder in self.root.iterdir():
            if not folder.is_dir() or not re.fullmatch('[0-9a-f]{32}',folder.name):continue
            try:
                state=self._read(folder)
                if state.get('validation_fixture'):continue
                items.append({'batch_id':folder.name,'state':state['state'],'created_at':state['created_at'],'completed_items':sum(i['state']=='completed' for i in state['items']),'item_count':len(state['items'])})
            except (OSError,ValueError,KeyError,PipelineError) as error:items.append({'batch_id':folder.name,'state':'unreadable','created_at':'9999','detail':str(error)[:300]})
        return {'batches':sorted(items,key=lambda i:i['created_at'],reverse=True),'new_generation':False,'worker_started':False}
    def folder(self,batch_id):
        if batch_id is None:
            items=self.list()['batches'];pending=[i for i in items if i['state']!='completed'];chosen=(pending or items)
            if not chosen:raise PipelineError('No saved artifact batch; create one before work')
            batch_id=chosen[0]['batch_id']
        if not re.fullmatch('[0-9a-f]{32}',str(batch_id)):raise PipelineError('Invalid artifact batch identity')
        return self.root/batch_id
    def _current_editorial(self,item,job=None):
        job=job or self.store.get(item['job_id'])
        if item.get('kind')=='draft':return {'state':'unvoiced_draft','approved':False,'publication_authorized':False}
        if job.get('package_integrity_pass') is not True:return {'state':'artifact_unverified','approved':False,'publication_authorized':False}
        from .workflow import editorial_state
        current=(job.get('editorial_decision') or {}).get('package_id')
        if current and current!=item['artifact_id']:return {'state':'package_mismatch','approved':False,'package_bound':False,'reason':'Current job belongs to a different package than this pinned batch item','publication_authorized':False}
        return editorial_state(job.get('editorial_review'),item['artifact_id'])

    def _artifact(self,job_id):
        job=self.store.get(job_id)
        if job['state']=='completed' and job.get('package_integrity_pass') is True:kind='video_preview';identity=read_json(Path(job['run_dir'])/'package_manifest.json')['package_id']
        elif job['state']=='prepared' and job.get('preparation_integrity_pass') is True:kind='draft';identity=job['preparation_id']
        else:raise PipelineError('Batch reuse requires an existing verified completed/prepared artifact')
        topic=read_json(Path(job['run_dir'])/'topic.json')['selected']
        item={'job_id':job_id,'artifact_id':identity,'kind':kind,'opportunity_id':topic['opportunity_id'],'title':topic['title'],'source_ready_for_generation':job.get('ready_for_generation') if kind=='draft' else None,'generation_blockers':job.get('generation_blockers',[]),'state':'pending'}
        item['editorial_decision']=self._current_editorial(item,job);item['review_archive_only']=item['editorial_decision']['state'] in {'rejected','changes_requested','package_mismatch'}
        return item
    def create(self,job_ids=None,limit=3,request_key=None):
        if request_key is None:return self._create(job_ids,limit)
        if not isinstance(request_key,str) or not 1<=len(request_key)<=128 or not request_key.strip():raise PipelineError('Batch request key must contain1..128characters')
        if type(limit) is not int or not 1<=limit<=20:raise PipelineError('Artifact batch limit must be1..20')
        if job_ids is not None and (not isinstance(job_ids,list) or not job_ids or len(job_ids)>20 or any(not isinstance(i,str) for i in job_ids)):raise PipelineError('Explicit artifact batch needs1..20existing job identities')
        signature=hashlib.sha256(json.dumps({'jobs':job_ids,'limit':limit},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        key_hash=hashlib.sha256(request_key.encode()).hexdigest()
        batch_id=hashlib.sha256(('SocialArtifactBatchV1:'+key_hash).encode()).hexdigest()[:32]
        with motion_lock(self.root,'create_'+batch_id,wait=15):
            folder=self.folder(batch_id)
            if folder.exists():
                state=self._read(folder)
                if state.get('request_key_sha256')!=key_hash or state.get('request_signature')!=signature:raise PipelineError('Batch request key reused with different arguments; original preserved')
                return {**self.status(batch_id),'request_reused':True}
            return {**self._create(job_ids,limit,batch_id,{'request_key_sha256':key_hash,'request_signature':signature}),'request_reused':False}
    def _create(self,job_ids=None,limit=3,batch_id=None,request_metadata=None):
        if type(limit) is not int or not 1<=limit<=20:raise PipelineError('Artifact batch limit must be1..20')
        selected=[];seen=set()
        if job_ids is not None:
            if not isinstance(job_ids,list) or not job_ids or len(job_ids)>20:raise PipelineError('Explicit artifact batch needs1..20existing jobs')
            candidates=job_ids
        else:candidates=[j['id'] for j in self.store.list() if (j['state']=='completed' and j.get('package_integrity_pass') and (j.get('editorial_decision') or {}).get('state') not in {'rejected','changes_requested','package_mismatch'}) or (j['state']=='prepared' and j.get('preparation_integrity_pass') and j.get('ready_for_generation'))]
        for job_id in candidates:
            item=self._artifact(job_id)
            if job_ids is None and item.get('review_archive_only'):continue
            if item['opportunity_id'] in seen:continue
            selected.append(item);seen.add(item['opportunity_id'])
            if len(selected)>=limit:break
        if not selected:raise PipelineError('No verified existing artifacts for batch reuse; no new generation attempted')
        batch_id=batch_id or uuid.uuid4().hex;folder=self.folder(batch_id);batch_id=folder.name;folder.mkdir();state={'schema':'SOCIAL_ARTIFACT_BATCH_V1','batch_id':batch_id,'created_at':utc_now().isoformat(),'state':'ready','mode':'offline_existing_artifacts_only','explicit_selection':job_ids is not None,'items':selected,'worker_started':False,'new_generation':False,'publication_authorized':False};state.update(request_metadata or {});write_json(folder/'state.json',state);self._index(folder,state);return self.status(batch_id)
    def _safe(self,value):
        path=Path(value).resolve()
        if not (path.is_relative_to(self.store.root.resolve()) or path.is_relative_to(ROOT.resolve())):raise PipelineError('Artifact path outside owned Social scope')
        return path
    def _portable(self,value):
        path=self._safe(value)
        for base,root in (('social_root',ROOT.resolve()),('queue_root',self.store.root.resolve())):
            if path.is_relative_to(root):return {'base':base,'path':path.relative_to(root).as_posix()}
        raise PipelineError('Cannot bind artifact outside owned roots')
    def _resolve(self,value,portable=None):
        if portable is None:return self._safe(value)
        if not isinstance(portable,dict) or portable.get('base') not in {'social_root','queue_root'} or not isinstance(portable.get('path'),str):raise PipelineError('Invalid portable artifact path')
        relative=Path(portable['path'])
        if relative.is_absolute() or '..' in relative.parts:raise PipelineError('Unsafe portable artifact path')
        base=ROOT if portable['base']=='social_root' else self.store.root
        resolved=(base/relative).resolve()
        if not resolved.is_relative_to(base.resolve()):raise PipelineError('Portable artifact escaped its base')
        return self._safe(resolved)
    def rebind_paths(self,batch_id,previous_root):
        previous=Path(previous_root)
        if not previous.is_absolute():raise PipelineError('Previous Social root must be absolute')
        previous=previous.resolve();folder=self.folder(batch_id)
        with motion_lock(folder,'work',wait=1):
            from .batch_rebind import require_settled,prepare,recover
            require_settled(folder)
            state=self._read(folder);changes=[]
            for n,item in enumerate(state['items'],1):
                path=folder/('item_%02d.json'%n)
                if not path.exists():continue
                if item.get('receipt_sha256') and sha256_file(path)!=item['receipt_sha256']:raise PipelineError('Saved receipt changed; cannot rebind')
                receipt=read_json(path);actual=self._artifact(item['job_id'])
                if receipt.get('job_id')!=item['job_id'] or receipt.get('artifact_id')!=actual['artifact_id'] or actual['artifact_id']!=item['artifact_id']:raise PipelineError('Artifact identity changed; cannot rebind')
                archive=receipt.get('archive') or {};old=Path(archive.get('path',''))
                if not old.is_absolute() or not old.is_relative_to(previous):raise PipelineError('Saved archive is not under the explicit previous root')
                current=self._safe(ROOT/old.relative_to(previous))
                if not current.is_file() or sha256_file(current)!=archive.get('sha256'):raise PipelineError('Relocated archive missing/changed; cannot rebind')
                archive['portable_path']=self._portable(current)
                if receipt.get('preview_video'):
                    old_preview=Path(receipt['preview_video'])
                    if not old_preview.is_relative_to(previous):raise PipelineError('Preview outside previous root')
                    current_preview=self._safe(ROOT/old_preview.relative_to(previous))
                    expected=Path(self.store.get(item['job_id'])['run_dir'])/'final/reel.mp4'
                    if current_preview!=expected.resolve():raise PipelineError('Preview does not match the verified owned job')
                    receipt['preview_portable_path']=self._portable(current_preview);receipt['preview_sha256']=sha256_file(current_preview)
                receipt['path_scope']='Absolute paths are historical issue metadata; portable_path fields resolve current owned artifacts'
                changes.append((path,receipt,item))
            payloads={};overrides={}
            for path,receipt,item in changes:
                data=stable_json(receipt).encode('utf-8');payloads[path.name]=data;overrides[path.name]=receipt;item['receipt_sha256']=sha256_bytes(data)
            state['path_rebound_at']=utc_now().isoformat();payloads['state.json']=stable_json(state).encode('utf-8')
            payloads['INDEX.md']=self._index_text(folder,state,overrides).encode('utf-8')
            prepare(folder,payloads);recover(folder,'continue')
        return {**self.status(folder.name),'path_rebound':True,'receipts_rebound':len(changes),'new_generation':False,'worker_started':False}
    def recover_paths(self,batch_id,mode='continue'):
        from .batch_rebind import recover
        folder=self.folder(batch_id)
        with motion_lock(folder,'work',wait=1):result=recover(folder,mode)
        return {**self.status(folder.name),'path_recovery':result,'worker_started':False,'new_generation':False}
    def cancel(self,batch_id=None):
        result=self.pause(batch_id);return {**result,'cancel_mode':'Stop remaining items after the current atomic issue; existing artifacts are preserved'}
    def _read(self,folder):
        state=read_json(folder/'state.json')
        if state.get('batch_id')!=folder.name or state.get('schema')!='SOCIAL_ARTIFACT_BATCH_V1' or state.get('mode')!='offline_existing_artifacts_only':raise PipelineError('Unknown batch mode/schema; original state preserved')
        return state
    def status(self,batch_id=None):
        folder=self.folder(batch_id);batch_id=folder.name;state=self._read(folder)
        from .batch_rebind import pending
        for item in state['items']:
            try:item['current_editorial_decision']=self._current_editorial(item)
            except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:item['current_editorial_decision']={'state':'unavailable','approved':False,'detail':str(error)[:250],'publication_authorized':False}
        rejected=[{'job_id':i['job_id'],'decision':i['current_editorial_decision']['state'],'reason':i['current_editorial_decision'].get('reason')} for i in state['items'] if i['current_editorial_decision']['state'] in {'rejected','changes_requested','package_mismatch'}]
        return {**state,'automatic_reuse_blocked':bool(rejected) and state.get('explicit_selection') is not True,'current_editorial_blockers':rejected,'path_rebind_recovery_required':pending(folder),'pause_requested':(folder/'pause').exists(),'completed_items':sum(i['state']=='completed' for i in state['items']),'index':str(folder/'INDEX.md'),'current_status_confirmed':False,'scope':'Saved reuse receipts and byte integrity, never new generation or live source/editorial approval'}
    def pause(self,batch_id=None):
        folder=self.folder(batch_id);batch_id=folder.name;self._read(folder);(folder/'pause').touch();return self.status(batch_id)
    def resume(self,batch_id=None):
        folder=self.folder(batch_id);batch_id=folder.name
        with motion_lock(folder,'work',wait=1):
            from .batch_rebind import require_settled
            require_settled(folder)
            state=self._read(folder)
            if (folder/'pause').exists():(folder/'pause').unlink()
            if state['state']!='completed':state['state']='ready';write_json(folder/'state.json',state)
        return self.status(batch_id)
    def _index(self,folder,state):
        atomic_bytes(folder/'INDEX.md',self._index_text(folder,state).encode('utf-8'))
    def _index_text(self,folder,state,overrides=None):
        lines=['# Social artifact batch','', 'Existing materials only. No new generation, source-current confirmation, editorial approval or publication.','']
        for n,item in enumerate(state['items'],1):
            lines.extend([str(n)+'. '+item['title']+' — '+item['state']+' ('+item['kind']+')',''])
            editorial=item.get('editorial_decision') or {}
            if editorial.get('state') in {'rejected','changes_requested','package_mismatch'}:lines.extend(['   Editorial '+editorial['state']+': '+str(editorial.get('reason') or 'Review required')+'; archive is for review only.',''])
            receipt=folder/('item_%02d.json'%n)
            if item['state']=='completed' and receipt.is_file():
                data=(overrides or {}).get(receipt.name) or read_json(receipt);preview=data.get('preview_video');archive=data.get('archive');preview_path=self._resolve(preview,data.get('preview_portable_path')) if preview else None
                if preview_path and preview_path.is_file():lines.extend(['   [Watch technical preview](<'+Path(os.path.relpath(preview_path,folder)).as_posix()+'>)',''])
                if item.get('source_ready_for_generation') is False:lines.extend(['   Source-blocked DRAFT; no generation readiness or approval.',''])
                if archive:lines.extend(['   [Open verified '+('DRAFT' if item['kind']=='draft' else 'preview')+' ZIP](<'+Path(os.path.relpath(self._resolve(archive['path'],archive.get('portable_path')),folder)).as_posix()+'>)' ,''])
        return '\n'.join(lines)
    def work(self,batch_id=None,max_items=None,on_item=None):
        if max_items is not None and (type(max_items) is not int or not 1<=max_items<=20):raise PipelineError('Batch work bound must be1..20')
        folder=self.folder(batch_id);batch_id=folder.name;processed=0
        with motion_lock(folder,'work',wait=1):
            from .batch_rebind import require_settled
            require_settled(folder)
            state=self._read(folder)
            try:
                for n,item in enumerate(state['items'],1):
                    current_review=self._current_editorial(item)
                    item['editorial_decision']=current_review
                    if current_review['state'] in {'rejected','changes_requested','package_mismatch'} and state.get('explicit_selection') is not True:
                        raise PipelineError('Automatic artifact reuse blocked by exact-package editorial '+current_review['state']+'; existing archive preserved for explicit review only')
                    if item['state']=='completed':
                        receipt=folder/('item_%02d.json'%n)
                        if not receipt.is_file() or sha256_file(receipt)!=item['receipt_sha256']:raise PipelineError('Saved batch receipt changed; no automatic replay')
                        saved=read_json(receipt);archive=saved.get('archive')
                        if saved.get('preview_sha256'):
                            preview=self._resolve(saved['preview_video'],saved.get('preview_portable_path'))
                            if not preview.is_file() or sha256_file(preview)!=saved['preview_sha256']:raise PipelineError('Saved preview changed; no regeneration')
                        if archive and (not self._resolve(archive['path'],archive.get('portable_path')).is_file() or sha256_file(self._resolve(archive['path'],archive.get('portable_path')))!=archive['sha256']):raise PipelineError('Saved batch archive changed; no regeneration')
                        continue
                    if (folder/'pause').exists():state['state']='paused';break
                    if max_items is not None and processed>=max_items:state['state']='ready';break
                    recovered=folder/('item_%02d.json'%n)
                    if recovered.is_file():
                        receipt=read_json(recovered);archive=receipt.get('archive')
                        if receipt.get('job_id')!=item['job_id'] or receipt.get('artifact_id')!=item['artifact_id'] or not archive or not self._resolve(archive['path'],archive.get('portable_path')).is_file() or sha256_file(self._resolve(archive['path'],archive.get('portable_path')))!=archive['sha256']:raise PipelineError('Interrupted receipt identity/bytes invalid; no replay')
                        item.update(state='completed',receipt_sha256=sha256_file(recovered),recovered_committed_receipt=True);write_json(folder/'state.json',state);self._index(folder,state);continue
                    actual=self._artifact(item['job_id'])
                    if actual['artifact_id']!=item['artifact_id']:raise PipelineError('Pinned batch artifact identity changed')
                    state['state']='running';item['state']='issuing';write_json(folder/'state.json',state)
                    from .production import deliver_existing
                    output=deliver_existing(self.store,item['job_id'],online=False)
                    archive=output.get('preparation_export') or output.get('export')
                    if not archive or not archive.get('path') or not archive.get('sha256'):raise PipelineError('Existing batch artifact could not be verified/exported')
                    archive={**archive,'portable_path':self._portable(archive['path'])}
                    receipt={'preview_sha256':sha256_file(output['preview_video']) if output.get('preview_video') else None,'path_scope':'Absolute paths are historical issue metadata; portable_path fields resolve current owned artifacts','preview_portable_path':self._portable(output['preview_video']) if output.get('preview_video') else None,'job_id':item['job_id'],'artifact_id':item['artifact_id'],'kind':item['kind'],'archive':archive,'preview_video':output.get('preview_video'),'issued_at':utc_now().isoformat(),'current_status_confirmed':False,'new_generation':False,'worker_started':False,'editorial_approved':False,'editorial_decision_at_issue':current_review,'review_archive_only':current_review['state'] in {'rejected','changes_requested','package_mismatch'},'output':output}
                    target=folder/('item_%02d.json'%n);write_json(target,receipt);item.update(state='completed',receipt_sha256=sha256_file(target));processed+=1;write_json(folder/'state.json',state);self._index(folder,state)
                    if on_item:on_item(n,dict(item))
                else:state['state']='completed'
                write_json(folder/'state.json',state);self._index(folder,state)
            except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:
                state['state']='blocked';state['last_error']=str(error)[:700];write_json(folder/'state.json',state);raise
        return self.status(batch_id)
