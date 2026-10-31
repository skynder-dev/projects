"""Bound a Social worker and its own children; never address unrelated processes."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import time


class WindowsJob:
    def __init__(self, process):
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('read', 'write', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]
        class Limits(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Limits()
        limits.basic.flags = 0x2000  # kill this worker and its descendants when job closes
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.api.AssignProcessToJobObject(self.handle, wintypes.HANDLE(process._handle)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _resume_windows_worker(process):
    """Resume only the process we created suspended, after its job is assigned."""
    api = ctypes.WinDLL('ntdll', use_last_error=True)
    api.NtResumeProcess.argtypes = [wintypes.HANDLE]
    api.NtResumeProcess.restype = wintypes.LONG
    status = api.NtResumeProcess(wintypes.HANDLE(process._handle))
    if status != 0:
        raise OSError('Own suspended worker could not resume: NTSTATUS ' + hex(status & 0xffffffff))


def run_command(command, log, timeout=900, cancel_file=None, env=None, cwd=None):
    if cancel_file and Path(cancel_file).is_file():
        return 130
    if timeout <= 0:
        raise ValueError('timeout must be positive')
    started = time.monotonic()
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    job = None
    with log.open('w', encoding='utf-8') as output:
        proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, env=env, cwd=cwd,
                                creationflags=(0x08000000 | 0x00000004) if os.name == 'nt' else 0)
        try:
            if os.name == 'nt':
                job = WindowsJob(proc)
                _resume_windows_worker(proc)
            while proc.poll() is None:
                if cancel_file and Path(cancel_file).is_file():
                    output.write('\nPIPELINE CANCELLED\n')
                    return 130
                if time.monotonic() - started > timeout:
                    output.write('\nPIPELINE TIMEOUT\n')
                    return 124
                time.sleep(.2)
            return proc.returncode
        finally:
            if job:
                job.close()
            elif proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Only this own worker is addressed; a job-close race must not
                # turn a cancellation/deadline receipt into a stray live worker.
                proc.kill()
                proc.wait(timeout=10)


def managed_run(out, timeout, cancel_file):
    env = dict(os.environ, SOCIAL_MANAGED_WORKER='1', PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
    if cancel_file:
        env['SOCIAL_CANCEL_FILE'] = str(cancel_file)
    log = Path(out) / ('worker_' + str(time.time_ns()) + '.log')
    code = run_command([sys.executable, '-m', 'socialreel', *sys.argv[1:]], log, timeout, cancel_file, env)
    print(log.read_text(encoding='utf-8', errors='replace'))
    return code
