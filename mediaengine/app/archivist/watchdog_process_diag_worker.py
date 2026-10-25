from __future__ import annotations
from .platform_adapter import process_kwargs
import json, os, shutil, subprocess, sys, time
from pathlib import Path
from .config import HOME,ensure_dirs
from .db import db,init_db,now_iso
from .converter import start_convert_job
from .watchdog import recover_job
from .media import _ffmpeg_exe

def hidden():
    return process_kwargs()

def main():
    fixture=Path(sys.argv[1]).resolve();assert fixture.exists()
    ensure_dirs();init_db();ff=_ffmpeg_exe();assert ff
    long=HOME/"watchdog_process_probe.mp4"
    r=subprocess.run([str(ff),"-y","-hide_banner","-loglevel","error","-stream_loop","9","-i",str(fixture),"-t","18","-c","copy",str(long)],
                     capture_output=True,timeout=30,**hidden())
    if r.returncode!=0 or not long.exists():raise RuntimeError("failed to create watchdog probe video")
    st=long.stat();ts=now_iso()
    with db() as con:
        cur=con.execute("""INSERT INTO inventory(source_key,source_kind,source_id,source_label,path,filename,ext,media_type,mime_type,size_bytes,mtime,duration_ms,width,height,discovered_at,last_seen_at,work_selected)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        ("diag:watchdog-process","fixed","diag","Watchdog probe",str(long),long.name,".mp4","video","video/mp4",st.st_size,st.st_mtime,18000,640,360,ts,ts,1))
        iid=int(cur.lastrowid);con.commit()
    jid=start_convert_job([iid],"hq_1080p",None,card_test=False)
    deadline=time.time()+12;pid=0
    while time.time()<deadline:
        with db() as con:row=dict(con.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone())
        pid=int(row.get("worker_pid") or 0)
        if pid:break
        if row.get("status") in ("finished","failed","cancelled"):raise RuntimeError("conversion finished before watchdog probe could interrupt it")
        time.sleep(.02)
    if not pid:raise RuntimeError("converter process pid did not appear")
    action=recover_job(jid,"diagnostic_forced_stall",allow_app_restart=False,report=False)
    if action!="process_restart":raise RuntimeError("expected process_restart, got "+str(action))
    deadline=time.time()+90;row=None
    while time.time()<deadline:
        with db() as con:row=dict(con.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone())
        if row.get("status") in ("finished","failed","cancelled"):break
        time.sleep(.1)
    opts=json.loads(row.get("options_json") or "{}") if row else {}
    outs=opts.get("outputs") or []
    output_exists=any((not x.get("error")) and x.get("output") and Path(x["output"]).exists() for x in outs)
    if not row or row.get("status")!="finished" or int(row.get("watchdog_process_restarts") or 0)<1 or not output_exists:
        raise RuntimeError("watchdog process restart failed: "+json.dumps({"row":row,"outputs":outs})[:1200])
    print(json.dumps({"action":action,"status":row["status"],"process_restarts":int(row["watchdog_process_restarts"] or 0),"output_exists":output_exists}))

if __name__=="__main__":main()
