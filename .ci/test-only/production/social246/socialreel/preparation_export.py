"""Atomic portable DRAFT handoff, separate from finished Reel export."""
import hashlib
import json
import os
import tempfile
import zipfile
import zlib
from pathlib import Path
from .common import ROOT,PipelineError,read_json,sha256_file,utc_now
from .preparation import verify_preparation
from .draft_check import check

def export_preparation(directory,destination=None):
    root=Path(directory).resolve();manifest=verify_preparation(root)
    destination=Path(destination or root.parent.parent.parent/'draft_exports'/(root.name+'.zip')).resolve()
    if destination.is_relative_to(root):raise PipelineError('Draft export must be outside original inputs')
    from .source_quality import inspect_directory
    quality=inspect_directory(root)
    names={e['path'] for e in manifest['files']}|{'prepared.json'}
    checker=ROOT/'socialreel/draft_check.py';checker_sha=sha256_file(checker)
    receipt={'artifact_type':'draft_source_and_plan','accepted':False,'preparation_id':manifest['preparation_id'],
             'exported_at':utc_now().isoformat(),'source_as_of':read_json(root/'sources.json').get('selected_snapshot',{}).get('fetched_at'),
             'current_status_confirmed':False,'ready_for_current_use':False,'generation_blockers':manifest.get('generation_blockers',[]),
             'models_included':False,'source_quality':quality,'ready_for_assembly':False,'checker_sha256':checker_sha}
    destination.parent.mkdir(parents=True,exist_ok=True)
    reused=destination.exists()
    with tempfile.TemporaryDirectory(prefix='_draft_export_',dir=destination.parent) as temp:
        temp=Path(temp);archive=destination if reused else temp/'draft.zip'
        if not reused:
            with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for name in sorted(names):z.write(root/name,name)
                z.write(checker,'check_draft.py');z.writestr('draft_export.json',json.dumps(receipt,indent=2))
        try:
            with zipfile.ZipFile(archive) as z:
                if len(z.namelist())!=len(set(z.namelist())):raise PipelineError('Draft archive contains duplicate names')
                if set(z.namelist())!=names|{'check_draft.py','draft_export.json'} or z.testzip() is not None:
                    raise PipelineError('Draft archive contents differ or CRC failed')
                saved=json.loads(z.read('draft_export.json'))
                if saved['preparation_id']!=manifest['preparation_id'] or saved.get('accepted') is not False:
                    raise PipelineError('Draft archive identity/state mismatch')
                if hashlib.sha256(z.read('check_draft.py')).hexdigest()!=saved['checker_sha256']:
                    raise PipelineError('Draft checker damaged')
                for name in names:
                    if hashlib.sha256(z.read(name)).hexdigest()!=sha256_file(root/name):
                        raise PipelineError('Draft bytes changed during export: '+name)
                unpack=temp/'verify';unpack.mkdir()
                for info in z.infolist():
                    if not (unpack/info.filename).resolve().is_relative_to(unpack):raise PipelineError('Unsafe draft archive path')
                z.extractall(unpack)
            result=check(unpack)
            if not result['integrity_pass']:raise PipelineError('Portable draft verification failed')
        except (zipfile.BadZipFile,zlib.error,ValueError,KeyError) as error:
            raise PipelineError('Existing draft archive invalid; preserved: '+str(error)) from error
        digest=sha256_file(archive);size=archive.stat().st_size
        if not reused:os.link(archive,destination)
    return {'path':str(destination),'bytes':size,'sha256':digest,'preparation_id':manifest['preparation_id'],
            'artifact_type':'draft_source_and_plan','accepted':False,'current_status_confirmed':False,
            'ready_for_current_use':False,'archive_quality_matches_current_policy':saved.get('source_quality')==quality,'archive_checker_matches_current':saved.get('checker_sha256')==checker_sha,'source_quality':quality,'ready_for_assembly':False,'reused':reused,'integrity_verified':True,'source_as_of':receipt['source_as_of']}
