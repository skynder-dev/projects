"""Reusable local motion inputs for the existing bounded VACE adapter."""
import copy,hashlib,json,shutil,tempfile
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_file
from . import replacement as adapter
from .motion_state import motion_lock,catalogue_locked,attempt,failed,quarantine,recover_staging,OWNER,published
from .motion_review import overview,mask_geometry
from .motion_contract import normalize_template,resolved_prompt


class MotionCatalog:
    def __init__(self, root=None):
        self.root=Path(root or adapter.VACE_HOME).resolve()
        self.file=self.root/'catalog/motion_catalog.json'

    def load(self):
        if not self.file.exists():return {'schema':'social_motion_catalog_v1','templates':{},'references':{}}
        try:
            data=read_json(self.file)
            if data.get('schema')!='social_motion_catalog_v1' or not isinstance(data['templates'],dict) or not isinstance(data['references'],dict) or not isinstance(data.get('prepared_requests',{}),dict):raise ValueError()
            if any(not isinstance(value,dict) for value in list(data['templates'].values())+list(data['references'].values())):raise ValueError()
            return data
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:raise PipelineError('Motion catalog unreadable; preserved, no input opened') from error

    def _id(self,value):
        import re
        if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,80}',value):raise PipelineError('Invalid motion identifier')
        return value

    def _approved(self,item):
        if not isinstance(item,dict):raise PipelineError('Motion input metadata malformed; no file opened')
        if item.get('test_allowed') is not True or item.get('identity_approved') is not False:
            raise PipelineError('Motion input lacks explicit test approval; no identity approval is inferred')
        if item.get('production_approved',False) is not False:raise PipelineError('Motion catalogue cannot confer production approval')
        if not isinstance(item.get('source_url'),str) or not isinstance(item.get('license'),str) or not item['source_url'].strip() or not item['license'].strip():raise PipelineError('Motion input needs source and license evidence')

    def _file(self,item):
        if not isinstance(item,dict):raise PipelineError('Motion file metadata malformed; no file opened')
        path=Path(item.get('path','')).resolve()
        # Standing denial must not turn into an alternative local-file retrieval.
        if 'fullbody02' in str(path).lower():raise PipelineError('Reference is outside authorized input scope; file not opened')
        if not path.is_relative_to(self.root) or not path.is_file():raise PipelineError('Motion file missing or outside approved root')
        if not item.get('sha256') or sha256_file(path)!=item['sha256']:raise PipelineError('Motion source file damaged or changed')
        return path

    @catalogue_locked
    def register_reference(self,item):
        self._approved(item);self._id(item.get('id'));path=self._file(item)
        size=adapter.reference_info(path)
        data=self.load();value=copy.deepcopy(item);value['size']=list(size)
        old=data['references'].get(item['id'])
        if old is not None and old!=value:raise PipelineError('Reference ID already describes different input; use a new ID')
        data['references'][item['id']]=value;self.file.parent.mkdir(parents=True,exist_ok=True);write_json(self.file,data)
        return value

    @catalogue_locked
    def register_template(self,item):
        item=normalize_template(item)
        self._approved(item);self._id(item.get('id'))
        if not isinstance(item.get('mask_scope'),str) or not item['mask_scope'].strip():raise PipelineError('Motion template needs explicit mask region; full-body coverage is not inferred')
        video,mask=self._file(item.get('video',{})),self._file(item.get('mask',{}))
        media=adapter.media_pair(video,mask,item.get('media'))
        if item.get('control_type'):adapter.media_pair(video,self._file(item['control_video']),media)
        data=self.load();reference=data['references'].get(item.get('default_reference'))
        if reference is None:raise PipelineError('Default motion reference is not registered')
        self._approved(reference);self._file(reference)
        value=copy.deepcopy(item);value['media']=media;value['ready_scope']='17-frame experimental adapter; not full body or dance approval'
        old=data['templates'].get(item['id'])
        if old is not None and normalize_template(old)!=value:raise PipelineError('Template ID already describes different input; use a new ID')
        data['templates'][item['id']]=value;self.file.parent.mkdir(parents=True,exist_ok=True);write_json(self.file,data)
        return value

    @catalogue_locked
    def _note_prepared(self,key,template_id,reference_id,directory):
        data=self.load()
        plan=read_json(Path(directory)/'prepared.json')
        data.setdefault('prepared_requests',{})[key]={'template_id':template_id,'reference_id':reference_id,'directory':str(directory),'window':plan.get('window'),'mask_scope':plan.get('mask_scope'),'semantic_accuracy_verified':False}
        write_json(self.file,data)

    def list(self):
        data=self.load()
        templates=[]
        for item in data['templates'].values():
            cached=[entry for entry in data.get('prepared_requests',{}).values() if isinstance(entry,dict) and entry.get('template_id')==item['id'] and Path(entry.get('directory','')).resolve().is_relative_to((self.root/'input/motion_jobs').resolve()) and (Path(entry.get('directory',''))/'cache.json').is_file()]
            templates.append({**item,'full_body_replacement_approved':False,'cached_preparations':cached,'preparation_status':'cached_available' if cached else 'registered_unprepared','cache_hashes_checked_on_prepare':True})
        return {'templates':templates,'references':list(data['references'].values()),
                'production_approved':False,'scope':'Registered local inputs only; availability checked again on prepare'}

    def _valid(self,directory,name,signature):
        try:
            plan=read_json(directory/name)
            if plan.get('signature')!=signature:raise ValueError()
            for entry in plan['files']:
                path=(directory/entry['path']).resolve()
                if not path.is_relative_to(directory) or not path.is_file() or sha256_file(path)!=entry['sha256']:raise ValueError()
            if not plan['files']:raise ValueError()
            return plan
        except (OSError,ValueError,KeyError,TypeError,AttributeError):raise PipelineError('Motion preparation cache damaged; preserved, no workflow submitted')

    def _prepare_unlocked(self,template_id,reference_id=None,canvas=None,start_frame=0,repair_cache=False):
        data=self.load();template=data['templates'].get(self._id(template_id))
        if template is None:raise PipelineError('Unknown motion template; no input opened')
        self._approved(template)
        if not isinstance(template.get('mask_scope'),str) or not template['mask_scope'].strip():raise PipelineError('Motion template needs explicit mask region; no full-body coverage inferred')
        reference_id=reference_id or template.get('default_reference')
        reference=data['references'].get(self._id(reference_id))
        if reference is None:raise PipelineError('Unknown or unapproved reference; no input opened')
        template=normalize_template(template)
        self._approved(template);self._approved(reference)
        for value in [template['video'],template['mask'],reference]+([template['control_video']] if template.get('control_type') else []):self._file(value)
        if template.get('control_type'):adapter.media_pair(Path(template['video']['path']),Path(template['control_video']['path']),template['media'])
        media=adapter.media_pair(Path(template['video']['path']),Path(template['mask']['path']),template['media'])
        adapter.reference_info(Path(reference['path']))
        canvas=tuple(canvas or adapter.choose_canvas(media['width'],media['height']))
        window=adapter.valid_window(media,start_frame)
        review=self._review_unlocked(template,media,repair_cache)
        signature=adapter.base_signature(template,canvas,start_frame)
        base_key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        prompt=resolved_prompt(template)
        request_signature={'base':signature,'reference_sha256':reference['sha256'],'reference_id':reference_id,'template_id':template_id,'mask_scope':template['mask_scope'],'reference_method':'whole-reference-white-contain-v1','prompt':prompt}
        key=hashlib.sha256(json.dumps(request_signature,sort_keys=True).encode()).hexdigest()
        directory=self.root/'input/motion_jobs'/key
        if directory.exists():
            try:
                self._valid(directory,'cache.json',request_signature)
                adapter.validate_prepared(directory)
            except PipelineError:
                if not repair_cache:raise
                self._repair_events.append(quarantine(self.root,directory,'requested_cache_corruption'))
        if directory.exists():
            self._note_prepared(key,template_id,reference_id,directory)
            return {**read_json(directory/'prepared.json'),'directory':str(directory),'cache_hit':True,'base_cache_hit':True,'reference_id':reference_id}
        base=self.root/'input/motion_bases'/base_key
        base_hit=base.exists()
        if base_hit:
            try:self._valid(base,'base.json',signature)
            except PipelineError:
                if not repair_cache:raise
                self._repair_events.append(quarantine(self.root,base,'base_cache_corruption'));base_hit=False
        effective={**template,'reference':reference,'prompt':prompt};effective['id']=template_id
        staging=self.root/'input/motion_staging';staging.mkdir(parents=True,exist_ok=True)
        work=Path(tempfile.mkdtemp(prefix='prepare_',dir=staging))
        attempt(work,'request',request_signature)
        manifest=work/'input_manifest.json';write_json(manifest,effective)
        try:
            result=adapter.prepare(manifest,work,canvas,base_directory=base if base_hit else None,start_frame=start_frame)
            self._checkpoint('adapter_prepared',work)
            if not base_hit:
                build=Path(tempfile.mkdtemp(prefix='base_',dir=staging));attempt(build,'base',signature)
                try:
                    for name in ['original.mkv','mask.mkv','control.mkv']+(['structure.mkv'] if template.get('control_type') else []):shutil.copy2(work/name,build/name)
                    shutil.copytree(work/'mask_frames',build/'mask_frames')
                    # Full source mask review is a shared immutable cache across windows.
                    local_media={'width':canvas[0],'height':canvas[1],'fps':media['fps'],'frames':17}
                    overview(build/'original.mkv',build/'mask_frames',local_media,template['mask_scope'],build,source_offset=start_frame)
                    files=self._entries(build)
                    write_json(build/'base.json',{'owner':OWNER,'signature':signature,'media':media,'window':window,'source_review':str(review),'selected_mask_frames':17,'files':files})
                    self._checkpoint('base_prepared',build)
                    base.parent.mkdir(parents=True,exist_ok=True);published(build);build.rename(base)
                except BaseException as error:failed(build,error);raise
            directory.parent.mkdir(parents=True,exist_ok=True)
            # Rebind only prepared paths after staging: no hand-editing of node graph.
            relative=directory.relative_to(self.root/'input').as_posix();prefix='social_replacement/'+key
            graph=adapter.build_workflow(relative+'/control.mkv',relative+'/mask.mkv',relative+'/original.mkv',relative+'/reference.png',canvas,prompt,prefix)
            write_json(work/'workflow_api.json',graph);result['prefix']=prefix
            result['input_relative']=relative;result['motion_prompt']=prompt;result['metadata_warnings']=template.get('metadata_warnings',[])
            result['source_review']=str(review);result['semantic_mask_accuracy_verified']=False;result['window']=window
            result['reference_id']=reference_id;result['source_media']=media;result['mask_scope']=template['mask_scope'];result['full_body_replacement_approved']=False;result['base_cache_key']=base_key
            result['files']=[{'path':p.relative_to(work).as_posix(),'sha256':sha256_file(p)} for p in sorted(work.rglob('*')) if p.is_file() and p.name not in ['prepared.json','cache.json','input_manifest.json','.motion_attempt.json']]
            write_json(work/'prepared.json',result)
            files=[{'path':p.relative_to(work).as_posix(),'sha256':sha256_file(p)} for p in sorted(work.rglob('*')) if p.is_file() and p.name not in ['cache.json','.motion_attempt.json']]
            write_json(work/'cache.json',{'owner':OWNER,'signature':request_signature,'files':files})
            adapter.validate_prepared(work)
            self._checkpoint('request_prepared',work)
            published(work);work.rename(directory)
            self._note_prepared(key,template_id,reference_id,directory)
            return {**result,'directory':str(directory),'cache_hit':False,'base_cache_hit':base_hit,'reference_id':reference_id}
        except BaseException as error:
            failed(work,error)
            raise


    def _checkpoint(self,stage,directory):
        """Internal diagnostic boundary; fault tests never invoke a GPU worker."""
        pass

    def _entries(self,directory):
        return [{'path':p.relative_to(directory).as_posix(),'sha256':sha256_file(p)} for p in sorted(directory.rglob('*')) if p.is_file() and p.name not in ['.motion_attempt.json','base.json','review.json']]

    def _review_unlocked(self,template,media,repair_cache=False):
        signature={'video':template['video']['sha256'],'mask':template['mask']['sha256'],'media':media,'mask_scope':template['mask_scope'],'method':'full-mask-geometry-source-overlays-v1'}
        key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        directory=self.root/'cache/motion_reviews'/key
        if directory.exists():
            try:
                self._valid(directory,'review.json',signature)
                mask_geometry(directory/'source_mask_frames',media['frames'],(media['width'],media['height']))
            except PipelineError:
                if not repair_cache:raise
                self._repair_events.append(quarantine(self.root,directory,'source_review_cache_corruption'))
        if not directory.exists():
            staging=self.root/'input/motion_staging';staging.mkdir(parents=True,exist_ok=True)
            work=Path(tempfile.mkdtemp(prefix='review_',dir=staging));attempt(work,'source_review',signature)
            try:
                adapter.extract_source_masks(Path(template['mask']['path']),work/'source_mask_frames',media)
                overview(Path(template['video']['path']),work/'source_mask_frames',media,template['mask_scope'],work)
                write_json(work/'review.json',{'owner':OWNER,'signature':signature,'files':self._entries(work)})
                self._checkpoint('source_review_prepared',work)
                directory.parent.mkdir(parents=True,exist_ok=True);published(work);work.rename(directory)
            except BaseException as error:failed(work,error);raise
        return directory

    def prepare(self,template_id,reference_id=None,canvas=None,start_frame=0,repair_cache=False):
        if type(repair_cache) is not bool:raise PipelineError('Cache repair flag must be boolean')
        with motion_lock(self.root,'prepare'):
            self._repair_events=recover_staging(self.root)
            result=self._prepare_unlocked(template_id,reference_id,canvas,start_frame,repair_cache)
            result['recovery_events']=list(self._repair_events);return result

    def inspect(self,template_id,repair_cache=False):
        with motion_lock(self.root,'prepare'):
            self._repair_events=recover_staging(self.root)
            template=self.load()['templates'].get(self._id(template_id))
            if template is None:raise PipelineError('Unknown template; no input opened')
            self._approved(template)
            for entry in [template['video'],template['mask']]:self._file(entry)
            media=adapter.media_pair(Path(template['video']['path']),Path(template['mask']['path']),template['media'])
            directory=self._review_unlocked(template,media,repair_cache)
            return {'directory':str(directory),'metrics':read_json(directory/'mask_metrics.json'),'overview':str(directory/'mask_overview.png'),'recovery_events':self._repair_events,'gpu_started':False}

    def recover(self,repair_cache=False):
        with motion_lock(self.root,'prepare'):
            events=recover_staging(self.root)
            if repair_cache:
                for folder,name in [('input/motion_jobs','cache.json'),('input/motion_bases','base.json'),('cache/motion_reviews','review.json')]:
                    parent=self.root/folder
                    if not parent.exists():continue
                    for directory in sorted(parent.iterdir()):
                        if not directory.is_dir():continue
                        try:plan=read_json(directory/name)
                        except (OSError,ValueError):
                            try:marker=read_json(directory/'.motion_attempt.json')
                            except (OSError,ValueError):continue
                            if isinstance(marker,dict) and marker.get('owner')==OWNER and marker.get('phase')=='published':events.append(quarantine(self.root,directory,'owned_commit_manifest_corruption'))
                            continue # unknown/unowned data is never swept
                        if plan.get('owner')!=OWNER:continue
                        try:self._valid(directory,name,plan['signature'])
                        except (PipelineError,KeyError):events.append(quarantine(self.root,directory,'explicit_owned_cache_repair'))
            return {'recovered':events,'gpu_started':False,'policy':'Kernel lock released on process death; live/unknown owners preserved; no process stopped'}
