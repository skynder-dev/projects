"""Owned advisory file locks for concept storage only."""
import os,time
from pathlib import Path
from contextlib import contextmanager
from .common import PipelineError

class MutationBusy(PipelineError):
 pass

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
