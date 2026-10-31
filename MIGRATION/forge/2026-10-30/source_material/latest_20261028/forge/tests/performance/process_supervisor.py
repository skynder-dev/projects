"""Bounded owned process trees; child waits for job assignment before execution."""
from pathlib import Path
import json,os,signal,subprocess,sys

class WindowsJob:
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w
        self.c=c;self.k=c.WinDLL('kernel32',use_last_error=True)
        class Basic(c.Structure):
            _fields_=[('PerProcessUserTimeLimit',c.c_longlong),('PerJobUserTimeLimit',c.c_longlong),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',c.c_size_t),('MaximumWorkingSetSize',c.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',c.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
        class IO(c.Structure):
            _fields_=[(n,c.c_ulonglong) for n in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
        class Extended(c.Structure):
            _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',c.c_size_t),('JobMemoryLimit',c.c_size_t),('PeakProcessMemoryUsed',c.c_size_t),('PeakJobMemoryUsed',c.c_size_t)]
        self.k.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];self.k.CreateJobObjectW.restype=w.HANDLE
        self.k.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD];self.k.SetInformationJobObject.restype=w.BOOL
        self.k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];self.k.AssignProcessToJobObject.restype=w.BOOL
        self.k.CloseHandle.argtypes=[w.HANDLE];self.k.CloseHandle.restype=w.BOOL
        self.handle=self.k.CreateJobObjectW(None,None)
        if not self.handle:raise c.WinError(c.get_last_error())
        info=Extended();info.BasicLimitInformation.LimitFlags=0x2000 # KILL_ON_JOB_CLOSE, no breakaway
        if not self.k.SetInformationJobObject(self.handle,9,c.byref(info),c.sizeof(info)):
            error=c.WinError(c.get_last_error());self.close();raise error
    def assign(self,process):
        if not self.k.AssignProcessToJobObject(self.handle,int(process._handle)):
            raise self.c.WinError(self.c.get_last_error())
    def close(self):
        if self.handle:
            handle=self.handle;self.handle=None
            if not self.k.CloseHandle(handle):raise self.c.WinError(self.c.get_last_error())

def run_owned(command,*,cwd,env,timeout,log):
    """No executable receives its command until the waiting child is supervised."""
    job=WindowsJob() if os.name=='nt' else None
    process=None
    try:
        process=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--waiting-child'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='strict',cwd=cwd,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),start_new_session=os.name!='nt')
        if job:job.assign(process)
        payload=json.dumps([str(arg) for arg in command])+'\n'
        try:
            output,_=process.communicate(payload,timeout=timeout)
        except subprocess.TimeoutExpired:
            if job:job.close()
            else:os.killpg(process.pid,signal.SIGKILL)
            output,_=process.communicate(timeout=10)
            Path(log).write_text(output+'\nSUPERVISOR TIMEOUT: FAIL\n',encoding='utf-8')
            raise TimeoutError('Owned process tree exceeded deadline')
        Path(log).write_text(output,encoding='utf-8')
        if process.returncode!=0:raise RuntimeError('Owned process failed: '+str(process.returncode)+'\n'+output[-6000:])
        return output
    finally:
        if job:job.close() # Also terminates residual descendants on ordinary completion.
        if process and os.name != 'nt':
            # The group can retain descendants after its waiting parent exits.
            # Always close the entire owned group, including nonzero/ordinary exit.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        if process and process.poll() is None:
            if os.name == 'nt': process.kill()
            process.wait(timeout=10)

def waiting_child():
    # Only standard-library imports above occur before parent assignment.
    line=sys.stdin.readline()
    if not line:raise RuntimeError('Supervisor did not release child')
    command=json.loads(line)
    if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):raise ValueError('Invalid command')
    result=subprocess.run(command,stdin=subprocess.DEVNULL)
    raise SystemExit(result.returncode)

if __name__=='__main__':
    if sys.argv[1:]!=['--waiting-child']:raise SystemExit('Internal supervised child mode only')
    waiting_child()
