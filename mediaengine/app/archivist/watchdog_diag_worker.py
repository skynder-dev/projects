from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path
from .db import db,init_db,now_iso
from .watchdog import recover_job,decide_action
from .platform_adapter import process_kwargs

def main():
    init_db();ts=now_iso()
    sleeper=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**process_kwargs())
    with db() as con:
        cur=con.execute("""INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,
                          options_json,heartbeat_at,progress_at,worker_pid) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        ("convert","running",ts,ts,"converting","probe",1,0,0,0,1,0,"{}",ts,ts,int(sleeper.pid)))
        jid=int(cur.lastrowid);con.commit()
    # The diagnostic has no converter global process owner; it therefore verifies
    # policy/escalation DB behavior without touching the host app.
    with db() as con:
        con.execute("UPDATE jobs SET watchdog_process_restarts=3,watchdog_app_restarts=0 WHERE id=?",(jid,));con.commit()
    os.environ["ARCHIVIST_WATCHDOG_DISABLE_APP_RESTART"]="1";os.environ["ARCHIVIST_WATCHDOG_NO_REMOTE"]="1"
    action=recover_job(jid,"diagnostic",allow_app_restart=False,report=False)
    try:sleeper.terminate();sleeper.wait(timeout=3)
    except Exception:
        try:sleeper.kill()
        except Exception:pass
    with db() as con:r=dict(con.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone())
    policy={
      "convert_process":decide_action("convert",0,0,True),
      "convert_escalate":decide_action("convert",3,0,True),
      "generic_escalate":decide_action("analyze",0,0,False),
      "exhausted":decide_action("convert",9,2,True)
    }
    assert policy=={"convert_process":"process_restart","convert_escalate":"app_restart","generic_escalate":"app_restart","exhausted":"fail"},policy
    assert action=="failed" and r["status"]=="failed" and r["error"]=="watchdog_exhausted",(action,r)
    print(json.dumps({"policy":policy,"terminal":r["status"],"error":r["error"]}))

if __name__=="__main__":main()
