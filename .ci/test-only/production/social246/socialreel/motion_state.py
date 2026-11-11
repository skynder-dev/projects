"""Kernel-owned local locks and bounded recovery for Social's own preparation data."""
import os,time,uuid
from contextlib import contextmanager
from pathlib import Path
from .common import PipelineError,write_json,read_json,utc_now
from .jobs import process_token

class MutationBusy(PipelineError):
 pass

OWNER='SocialMotion006'

@contextmanager
def motion_lock(root,name,wait=0):
    directory=Path(root)/'cache/motion_locks';directory.mkdir(parents=True,exist_ok=True)
    handle=open(directory/(name+'.lock'),'a+b');handle.seek(0,2)
    if not handle.tell():handle.write(b'\0');handle.flush()
    deadline=time.monotonic()+wait;acquired=False
    try:
        while True:
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                acquired=True;break
            except OSError:
                if time.monotonic()>=deadline:raise MutationBusy('Motion '+name+' busy; active owner is not interrupted')
                time.sleep(.05)
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_UN)
        handle.close()

def catalogue_locked(function):
    from functools import wraps
    @wraps(function)
    def call(self,*args,**kwargs):
        with motion_lock(self.root,'catalogue',wait=5):return function(self,*args,**kwargs)
    return call

def attempt(directory,kind,signature):
    directory=Path(directory)
    value={'owner':OWNER,'pid':os.getpid(),'token':process_token(os.getpid()),'kind':kind,'phase':'working','signature':signature,'at':utc_now().isoformat()}
    write_json(directory/'.motion_attempt.json',value);return value

def failed(directory,error):
    path=Path(directory)/'.motion_attempt.json'
    if path.exists():
        value=read_json(path);value.update(phase='failed',error=type(error).__name__);write_json(path,value)

def quarantine(root,directory,reason):
    root=Path(root).resolve();directory=Path(directory).resolve()
    allowed=[root/'input/motion_staging',root/'input/motion_jobs',root/'input/motion_bases',root/'cache/motion_reviews']
    if not any(directory!=p and directory.is_relative_to(p) for p in allowed):raise PipelineError('Recovery target outside owned motion data')
    destination=root/'cache/motion_quarantine'/uuid.uuid4().hex
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:directory.rename(destination)
    except OSError as error:raise PipelineError('Recovery data still locked or unavailable; preserved, no process stopped') from error
    write_json(destination/'RECOVERY.json',{'source':str(directory),'reason':reason,'at':utc_now().isoformat(),'owner':OWNER})
    return {'source':str(directory),'quarantine':str(destination),'reason':reason}

def recover_staging(root):
    root=Path(root).resolve();staging=root/'input/motion_staging';events=[]
    if not staging.exists():return events
    for directory in sorted(staging.iterdir()):
        marker=directory/'.motion_attempt.json'
        if not directory.is_dir() or not marker.is_file():continue
        try:value=read_json(marker)
        except (OSError,ValueError):raise PipelineError('Owned staging marker unreadable; recovery pending, preserved')
        if value.get('owner')!=OWNER:continue
        if value.get('phase')!='failed':
            try:live=process_token(int(value['pid']))
            except (ValueError,KeyError,TypeError):raise PipelineError('Preparation owner unknown; recovery pending')
            if live=='unknown' or (live is not None and live==value.get('token')):
                raise PipelineError('Preparation owner alive or uncertain; recovery pending, not interrupted')
        events.append(quarantine(root,directory,'interrupted_or_failed_preparation'))
    return events


def published(directory):
    path=Path(directory)/'.motion_attempt.json'
    value=read_json(path);value['phase']='published';write_json(path,value)
