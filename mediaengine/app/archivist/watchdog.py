from __future__ import annotations
from .platform_adapter import process_kwargs

import json, os, subprocess, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA, HOME, VERSION
from .db import db, init_db, now_iso

REMOTE_CONFIG=DATA/"remote_lab.json"
ENDPOINT="https://ldlhnedbqeqcbqelhuhm.supabase.co/functions/v1/archivist-remote-lab"
MAX_PROCESS_RESTARTS=3
MAX_APP_RESTARTS=2
POLL_SECONDS=float(os.environ.get("ARCHIVIST_WATCHDOG_POLL_SECONDS","5"))
CONVERT_STALL_SECONDS=float(os.environ.get("ARCHIVIST_WATCHDOG_CONVERT_STALL_SECONDS","90"))
GENERIC_STALL_SECONDS=float(os.environ.get("ARCHIVIST_WATCHDOG_GENERIC_STALL_SECONDS","300"))
_STARTED=False
_LOCK=threading.Lock()
_RESTARTING=threading.Event()

def _hidden():
    return process_kwargs(detached=True)

def _age_seconds(raw):
    if not raw:return 10**9
    try:
        dt=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        return max(0.0,(datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).total_seconds())
    except Exception:return 10**9

def decide_action(kind,process_restarts,app_restarts,has_killable_process):
    process_restarts=int(process_restarts or 0);app_restarts=int(app_restarts or 0)
    cycle_used=max(0,process_restarts-app_restarts*MAX_PROCESS_RESTARTS)
    if str(kind)=="convert" and has_killable_process and cycle_used<MAX_PROCESS_RESTARTS:
        return "process_restart"
    if app_restarts<MAX_APP_RESTARTS:
        return "app_restart"
    return "fail"

def _report_incident(job,action,reason):
    try:
        cfg=json.loads(REMOTE_CONFIG.read_text(encoding="utf-8"));tok=cfg.get("device_token")
        if not tok:return
        details={"job_id":int(job["id"]),"kind":str(job["kind"]),"action":action,"reason":str(reason)[:180],
                 "stage":str(job.get("stage") or "")[:80],
                 "process_restarts":int(job.get("watchdog_process_restarts") or 0),
                 "app_restarts":int(job.get("watchdog_app_restarts") or 0),
                 "detected_at":now_iso()}
        body=json.dumps({"action":"report","command_id":None,"report_type":"watchdog_incident","app_version":VERSION,
                         "agent_version":"app-watchdog-1","status":"failed",
                         "summary":f"Watchdog {action}: job #{int(job['id'])} ({job['kind']})","details":details}).encode()
        req=urllib.request.Request(ENDPOINT,data=body,headers={"content-type":"application/json","authorization":"Bearer "+tok},method="POST")
        urllib.request.urlopen(req,timeout=15).read()
    except Exception:pass

def _record(job,action,reason,proc_count,app_count,report=True):
    ts=now_iso()
    try:
        with db() as con:
            con.execute("INSERT INTO watchdog_incidents(job_id,kind,action,reason,process_restarts,app_restarts,created_at) VALUES(?,?,?,?,?,?,?)",
                        (int(job["id"]),str(job["kind"]),action,str(reason)[:300],int(proc_count),int(app_count),ts))
            con.execute("UPDATE jobs SET watchdog_last_action=?,watchdog_last_incident_at=? WHERE id=?",(action,ts,int(job["id"])))
            con.commit()
    except Exception:pass
    if report and os.environ.get("ARCHIVIST_WATCHDOG_NO_REMOTE")!="1":
        safe=dict(job);safe["watchdog_process_restarts"]=proc_count;safe["watchdog_app_restarts"]=app_count
        _report_incident(safe,action,reason)

def _request_app_restart():
    if os.environ.get("ARCHIVIST_WATCHDOG_DISABLE_APP_RESTART")=="1":
        return False
    if _RESTARTING.is_set():return True
    _RESTARTING.set()
    try:
        pyw=HOME/".venv"/"Scripts"/"pythonw.exe";py=HOME/".venv"/"Scripts"/"python.exe";exe=pyw if pyw.exists() else py
        launcher=HOME/"launcher.py"
        if not exe.exists() or not launcher.exists():raise RuntimeError("launcher unavailable")
        subprocess.Popen([str(exe),str(launcher),"--no-browser","--restart"],cwd=str(HOME),close_fds=True,**_hidden())
        def leave():
            time.sleep(1.0);os._exit(0)
        threading.Thread(target=leave,daemon=True,name="ArchivistWatchdogExit").start()
        return True
    except Exception:
        _RESTARTING.clear();return False

def recover_job(job_id,reason="stalled",allow_app_restart=True,report=True):
    from .converter import terminate_current_process
    with db() as con:
        r=con.execute("SELECT * FROM jobs WHERE id=?",(int(job_id),)).fetchone()
    if not r:return "missing"
    job={k:r[k] for k in r.keys()}
    if job.get("status")!="running":return "not_running"
    pid=int(job.get("worker_pid") or 0)
    action=decide_action(job.get("kind"),job.get("watchdog_process_restarts"),job.get("watchdog_app_restarts"),bool(pid))
    if action=="process_restart":
        proc_count=int(job.get("watchdog_process_restarts") or 0)+1;app_count=int(job.get("watchdog_app_restarts") or 0)
        ts=now_iso()
        with db() as con:
            con.execute("""UPDATE jobs SET watchdog_process_restarts=?,watchdog_retry_requested=1,
                           watchdog_last_action='process_restart',watchdog_last_incident_at=?,progress_at=?,heartbeat_at=?,
                           message='Process stalled; restarting automatically…' WHERE id=?""",
                        (proc_count,ts,ts,ts,int(job_id)));con.commit()
        killed=terminate_current_process(int(job_id))
        _record(job,"process_restart" if killed else "process_restart_requested",reason,proc_count,app_count,report)
        return "process_restart"
    if action=="app_restart" and allow_app_restart:
        proc_count=int(job.get("watchdog_process_restarts") or 0);app_count=int(job.get("watchdog_app_restarts") or 0)+1
        ts=now_iso();retry_code=2 if str(job.get("kind"))=="convert" else 0
        with db() as con:
            con.execute("""UPDATE jobs SET watchdog_app_restarts=?,watchdog_retry_requested=?,
                           watchdog_last_action='app_restart',watchdog_last_incident_at=?,progress_at=?,heartbeat_at=?,
                           message='Job stalled repeatedly; restarting Archivist automatically…' WHERE id=?""",
                        (app_count,retry_code,ts,ts,ts,int(job_id)));con.commit()
        if str(job.get("kind"))=="convert":terminate_current_process(int(job_id))
        _record(job,"app_restart",reason,proc_count,app_count,report)
        if not _request_app_restart():
            return "app_restart_deferred"
        return "app_restart"
    proc_count=int(job.get("watchdog_process_restarts") or 0);app_count=int(job.get("watchdog_app_restarts") or 0)
    ts=now_iso()
    if str(job.get("kind"))=="convert":terminate_current_process(int(job_id))
    with db() as con:
        con.execute("""UPDATE jobs SET status='failed',stage='watchdog_failed',
                       message='Stopped after automatic recovery attempts',error='watchdog_exhausted',
                       finished_at=?,worker_pid=NULL,watchdog_retry_requested=0,
                       watchdog_last_action='failed',watchdog_last_incident_at=?,heartbeat_at=?,progress_at=? WHERE id=?""",
                    (ts,ts,ts,ts,int(job_id)));con.commit()
    _record(job,"failed",reason,proc_count,app_count,report)
    return "failed"

def _loop():
    while True:
        try:
            if _RESTARTING.is_set():time.sleep(1);continue
            with db() as con:
                r=con.execute("SELECT * FROM jobs WHERE status='running' ORDER BY id LIMIT 1").fetchone()
            if r:
                job={k:r[k] for k in r.keys()}
                age=_age_seconds(job.get("progress_at") or job.get("started_at") or job.get("created_at"))
                limit=CONVERT_STALL_SECONDS if str(job.get("kind"))=="convert" else GENERIC_STALL_SECONDS
                if age>=limit:
                    recover_job(int(job["id"]),reason=f"no_progress_{int(age)}s")
        except Exception:
            pass
        time.sleep(max(1.0,POLL_SECONDS))

def start_watchdog():
    global _STARTED
    init_db()
    with _LOCK:
        if _STARTED:return
        threading.Thread(target=_loop,daemon=True,name="ArchivistWatchdog").start();_STARTED=True
