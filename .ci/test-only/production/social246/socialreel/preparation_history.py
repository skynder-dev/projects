"""Recover prepared-topic reservations from verified publications, under a local kernel lock."""
import os
from pathlib import Path
from .common import PipelineError,read_json,write_json,sha256_bytes
from .motion_state import motion_lock

def reservation_file(history):
    history=Path(history)
    return history.with_name(history.stem+'_prepared.json')

def _lock(history):
    path=reservation_file(history).resolve()
    return motion_lock(path.parent,'preparation_history_'+sha256_bytes(os.path.normcase(str(path)).encode())[:16],wait=5)

def _reconcile(history,out_root):
    path=reservation_file(history)
    try:data=read_json(path) if path.exists() else {'schema':'social_prepared_history_v2','runs':[]}
    except (OSError,ValueError) as error:raise PipelineError('Preparation history unreadable; original preserved') from error
    if not isinstance(data,dict) or not isinstance(data.get('runs'),list):
        raise PipelineError('Preparation history schema invalid; original preserved')
    records=data['runs'];candidates=set(Path(out_root).glob('prepared_*/prepared.json'))
    # Only reopen stored directories under this history's own local scope.
    scope=Path(history).parent.resolve()
    # Queue jobs have distinct out_roots. Recover a package published before
    # its reservation commit, even when the next request is a different job.
    # Fixed queue layout only; never recurse arbitrary user directories.
    for marker in scope.glob('*/runs/prepared_*/prepared.json'):
        if not marker.resolve().is_relative_to(scope):raise PipelineError('Prepared history marker escapes its owned queue scope')
        candidates.add(marker)
        if len(candidates)>1000:raise PipelineError('Prepared history recovery exceeds bounded scope; preserve work and review before selecting another topic')
    for record in records:
        if not isinstance(record,dict):raise PipelineError('Preparation history entry invalid; preserved')
        if record.get('directory'):
            directory=Path(record['directory']).resolve()
            if directory.is_relative_to(scope):candidates.add(directory/'prepared.json')
    known={record.get('preparation_id') for record in records};recovered=[];problems=[]
    from .preparation import verify_preparation
    for manifest_file in sorted(candidates):
        try:
            manifest=verify_preparation(manifest_file.parent)
            if manifest['preparation_id'] in known:continue
            topic=read_json(manifest_file.parent/'topic.json')['selected']
            entry={'opportunity_id':topic['opportunity_id'],'title':topic['title'],
                   'preparation_id':manifest['preparation_id'],'directory':str(manifest_file.parent.resolve()),
                   'state':'prepared_awaiting_generation'}
            records.append(entry);known.add(entry['preparation_id']);recovered.append(entry['preparation_id'])
        except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:
            problems.append({'directory':str(manifest_file.parent),'error':str(error)[:200]})
    data['schema']='social_prepared_history_v2'
    return data,recovered,problems

def load_reservations(history,out_root):
    with _lock(history):
        data,recovered,problems=_reconcile(history,out_root)
        if recovered:write_json(reservation_file(history),data)
    return {**data,'recovered':recovered,'problems':problems}

def publish_preparation(temporary,destination,history,entry,allow_repeat=False):
    with _lock(history):
        data,_,_=_reconcile(history,Path(destination).parent)
        from .pipeline import family
        if not allow_repeat and any(r.get('opportunity_id')==entry['opportunity_id'] or family(r.get('title',''))==family(entry['title']) for r in data['runs']):
            from .reference_cycle import allow_revision
            if not allow_revision(temporary,history,data['runs']):raise PipelineError('Topic already prepared by another local run; no verified material revision, unpublished work preserved')
        if Path(destination).exists():raise PipelineError('Prepared destination exists; preserved')
        Path(temporary).rename(destination)
        data['runs'].append(entry)
        # If the owner exits here, the published manifest is rediscovered next time.
        write_json(reservation_file(history),data)
