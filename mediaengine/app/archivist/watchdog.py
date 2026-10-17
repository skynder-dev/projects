from __future__ import annotations
from .platform_adapter import process_kwargs

import json, os, subprocess, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA, HOME, INSTALL, VERSION
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
        # db.now_iso() writes LOCAL naive time; treating it as UTC made every job look hours
        # old (or never stalled) depending on the timezone, e.g. UTC-5 -> app restarts mid-import.
        if dt.tzinfo is None:dt=dt.astimezone()
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
    # MediaEngine sends nothing anywhere (owner: offline, no Supabase). Incidents stay in the local database / log.
    return
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
        pyw=INSTALL/".venv"/"Scripts"/"pythonw.exe";py=INSTALL/".venv"/"Scripts"/"python.exe";exe=pyw if pyw.exists() else py
        launcher=INSTALL/"launcher.py"
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
                           message='Job stalled repeatedly; restarting MediaEngine automatically…' WHERE id=?""",
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

def _other_work() -> str:
    """Work an app restart would kill that is not the stalled Library task: a reel being made, an order, AI+ preparing
    the Library, a Composer render. The watchdog never restarts the app over it."""
    try:
        from . import auto_edit as _ae
        with db() as con:
            if con.execute("SELECT 1 FROM ae_jobs WHERE status IN ('queued','running') LIMIT 1").fetchone():
                return "reel"
        try:
            from . import aiplus_library as _al
            if _al.running():return "aiplus"
        except Exception:pass
        try:
            from . import orders as _or
            if _or.busy():return "order"
        except Exception:pass
        try:
            from . import composer as _cp
            with _cp._ACTIVE_LOCK:
                if _cp._ACTIVE:return "composer"
        except Exception:pass
    except Exception:
        return ""
    return ""

def verdict(kind,age,limit,in_grace,io_recent,other_work)->str:
    """'ok' (not late), 'touch' (late but alive or must not be restarted: its clock starts again) or 'recover'."""
    if age<limit:return "ok"
    if in_grace:return "touch"                      # after sleep: the clock starts again from now
    if kind!="convert" and io_recent:return "touch" # still reading / copying / hashing its file
    if kind!="convert" and other_work():return "touch"   # a restart would kill a reel / an order: never
    return "recover"

def _touch(job_id):
    ts=now_iso()
    try:
        with db() as con:
            con.execute("UPDATE jobs SET progress_at=?,heartbeat_at=? WHERE id=? AND status='running'",(ts,ts,int(job_id)));con.commit()
    except Exception:pass

def _loop():
    from .media import io_ticks
    last_poll=time.time(); grace_until=0.0
    ticks=io_ticks(); ticks_moved=time.monotonic()
    while True:
        try:
            now=time.time(); gap=now-last_poll; last_poll=now
            if gap>max(60.0,POLL_SECONDS*6):
                # the PC slept (or this process was frozen): every heartbeat looks old - give the work time to go on
                grace_until=time.monotonic()+GENERIC_STALL_SECONDS
            t=io_ticks()
            if t!=ticks:ticks=t;ticks_moved=time.monotonic()
            if _RESTARTING.is_set():time.sleep(1);continue
            with db() as con:
                r=con.execute("SELECT * FROM jobs WHERE status='running' ORDER BY id LIMIT 1").fetchone()
            if r:
                job={k:r[k] for k in r.keys()}
                age=_age_seconds(job.get("progress_at") or job.get("started_at") or job.get("created_at"))
                limit=CONVERT_STALL_SECONDS if str(job.get("kind"))=="convert" else GENERIC_STALL_SECONDS
                v=verdict(str(job.get("kind")),age,limit,time.monotonic()<grace_until,time.monotonic()-ticks_moved<min(limit,120),
                          (lambda:_other_work()) if str(job.get("kind"))!="convert" else (lambda:""))
                if v=="touch":_touch(job["id"])
                elif v=="recover":recover_job(int(job["id"]),reason=f"no_progress_{int(age)}s")
        except Exception:
            pass
        time.sleep(max(1.0,POLL_SECONDS))

def start_watchdog():
    global _STARTED
    init_db()
    with _LOCK:
        if _STARTED:return
        threading.Thread(target=_loop,daemon=True,name="ArchivistWatchdog").start();_STARTED=True
