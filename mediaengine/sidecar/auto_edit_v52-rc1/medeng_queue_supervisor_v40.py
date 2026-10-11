#!/usr/bin/env python3
from __future__ import annotations
import argparse, contextlib, json, os, signal, socket, subprocess, sys, time
from pathlib import Path

CANDIDATE='MEDENG_QUEUE_SUPERVISOR_V40_RC1'

def atomic_json(path:Path,obj:object):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8'); os.replace(tmp,path)

def read_json(path:Path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return None

def pid_alive(pid:int,host:str):
    if host and host!=socket.gethostname():return None
    if pid<=0:return False
    if os.name=='nt':
        try:
            cp=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'],capture_output=True,text=True,timeout=5)
            t=(cp.stdout or '')+(cp.stderr or '')
            return cp.returncode==0 and str(pid) in t and 'No tasks are running' not in t
        except Exception:return None
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True
    except Exception:return None

def acquire_lock(path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    payload={'candidate':CANDIDATE,'pid':os.getpid(),'host':socket.gethostname(),'created_at_unix':time.time()}
    try:
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(payload,f,indent=2)
        return payload
    except FileExistsError:
        old=read_json(path) or {}; alive=pid_alive(int(old.get('pid') or 0),str(old.get('host') or ''))
        if alive is False:
            stale=path.with_name(f'supervisor.lock.stale.{int(time.time())}.{os.getpid()}');os.replace(path,stale);return acquire_lock(path)
        raise RuntimeError('SUPERVISOR_LOCKED')

def release_lock(path:Path,payload:dict):
    old=read_json(path)
    if old and old.get('pid')==payload.get('pid') and old.get('host')==payload.get('host'):path.unlink(missing_ok=True)

def kill_tree(proc:subprocess.Popen):
    if proc.poll() is not None:return
    if os.name=='nt':
        with contextlib.suppress(Exception):subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
    else:
        with contextlib.suppress(Exception):os.killpg(proc.pid,signal.SIGKILL)
    with contextlib.suppress(Exception):proc.kill()
    with contextlib.suppress(Exception):proc.wait(timeout=10)

def spawn(cmd:list[str],logdir:Path):
    logdir.mkdir(parents=True,exist_ok=True); out=(logdir/'queue.stdout.log').open('ab');err=(logdir/'queue.stderr.log').open('ab')
    kw={}
    if os.name=='nt':kw['creationflags']=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
    else:kw['start_new_session']=True
    p=subprocess.Popen(cmd,stdout=out,stderr=err,**kw)
    p._medeng_logs=(out,err)
    return p

def close_logs(proc):
    for f in getattr(proc,'_medeng_logs',[]):
        with contextlib.suppress(Exception):f.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--queue',required=True);ap.add_argument('--inbox',required=True);ap.add_argument('--outbox',required=True);ap.add_argument('--queue-root',required=True)
    ap.add_argument('--target-seconds',type=float,default=30);ap.add_argument('--per-file-timeout-s',type=float,default=180);ap.add_argument('--job-hard-timeout-s',type=float,default=0)
    ap.add_argument('--settle-seconds',type=float,default=5);ap.add_argument('--batch-settle-seconds',type=float,default=30);ap.add_argument('--poll-seconds',type=float,default=3);ap.add_argument('--require-batch-ready-marker',action='store_true')
    ap.add_argument('--restart-delay-s',type=float,default=2);ap.add_argument('--max-restarts',type=int,default=3);ap.add_argument('--restart-window-s',type=float,default=60)
    a=ap.parse_args(); qroot=Path(a.queue_root).resolve();lock=qroot/'supervisor.lock';statep=qroot/'SUPERVISOR_STATE.json';logdir=qroot/'supervisor_logs'
    if a.max_restarts<0 or a.restart_window_s<=0 or a.restart_delay_s<0:raise SystemExit('V37_INVALID_ARGUMENT')
    try:lp=acquire_lock(lock)
    except RuntimeError as e:
        print(json.dumps({'candidate':CANDIDATE,'status':'LOCKED','error':str(e)}));raise SystemExit(9)
    stop_requested=False;child=None;failures=[];restart_count=0
    def write(status,**extra):
        d={'candidate':CANDIDATE,'status':status,'supervisor_pid':os.getpid(),'host':socket.gethostname(),'updated_at_unix':time.time(),'restart_count':restart_count,**extra};atomic_json(statep,d)
    try:
        while True:
            cmd=[sys.executable,str(Path(a.queue).resolve()),'--watch','--inbox',str(Path(a.inbox).resolve()),'--outbox',str(Path(a.outbox).resolve()),'--queue-root',str(qroot),'--target-seconds',str(a.target_seconds),'--per-file-timeout-s',str(a.per_file_timeout_s),'--settle-seconds',str(a.settle_seconds),'--batch-settle-seconds',str(a.batch_settle_seconds),'--poll-seconds',str(a.poll_seconds),'--recover-stale-lock']
            if a.job_hard_timeout_s>0:cmd += ['--job-hard-timeout-s',str(a.job_hard_timeout_s)]
            if a.require_batch_ready_marker:cmd += ['--require-batch-ready-marker']
            child=spawn(cmd,logdir);write('RUNNING',child_pid=child.pid,last_rc=None)
            rc=child.wait();close_logs(child);child=None
            if rc==0:
                write('STOPPED_CLEAN',child_pid=None,last_rc=0);return
            if rc==8:
                write('PARKED_QUEUE_ALREADY_RUNNING',child_pid=None,last_rc=rc);raise SystemExit(8)
            now=time.time(); failures=[t for t in failures if now-t<=a.restart_window_s];failures.append(now);restart_count+=1
            if len(failures)>a.max_restarts:
                write('PARKED_CRASH_LOOP',child_pid=None,last_rc=rc,failures_in_window=len(failures));raise SystemExit(12)
            write('RESTARTING',child_pid=None,last_rc=rc,failures_in_window=len(failures))
            time.sleep(a.restart_delay_s)
    except KeyboardInterrupt:
        if child:kill_tree(child);close_logs(child)
        write('STOPPED_SIGNAL',child_pid=None);raise SystemExit(130)
    finally:
        release_lock(lock,lp)

if __name__=='__main__':main()
