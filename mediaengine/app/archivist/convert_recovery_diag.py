from __future__ import annotations
import json, shutil, sys, time
from pathlib import Path

from .config import HOME, ensure_dirs
from .db import db, init_db, now_iso, recover_jobs
from .converter import recover_convert_jobs

def main():
    fixture=Path(sys.argv[1]).resolve()
    ensure_dirs(); init_db()
    src=HOME/'fixture.mp4'; shutil.copy2(fixture,src); st=src.stat(); ts=now_iso()
    with db() as con:
        cur=con.execute("""INSERT INTO inventory(source_key,source_kind,source_id,source_label,path,filename,ext,media_type,mime_type,size_bytes,mtime,duration_ms,width,height,discovered_at,last_seen_at,work_selected)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        ('diag:convert-recovery','fixed','diag','Recovery fixture',str(src),src.name,'.mp4','video','video/mp4',st.st_size,st.st_mtime,3000,640,360,ts,ts,1))
        iid=int(cur.lastrowid)
        cur=con.execute("""INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        ('convert','running',ts,ts,'converting','Simulated interrupted conversion',1,0,0,0,st.st_size,int(st.st_size*.25),
                         json.dumps({'preset':'small_720p','target_mb':None,'inventory_ids':[iid],'outputs':[]})))
        jid=int(cur.lastrowid); con.commit()
    recover_jobs()
    with db() as con:
        after_generic=dict(con.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    if after_generic['status']!='running' or after_generic['kind']!='convert':
        raise RuntimeError('generic recovery touched converter job: '+str(after_generic))
    rec=recover_convert_jobs()
    end=time.time()+40
    row=None
    while time.time()<end:
        with db() as con: row=dict(con.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
        if row['status'] in ('finished','failed','cancelled'): break
        time.sleep(.2)
    opts=json.loads(row.get('options_json') or '{}') if row else {}
    outs=opts.get('outputs') or []
    output_exists=bool(outs and not outs[0].get('error') and Path(outs[0].get('output','')).exists())
    if not row or row['status']!='finished' or not output_exists or int(rec.get('resumed') or 0)!=1:
        raise RuntimeError('convert restart recovery failed: '+json.dumps({'row':row,'rec':rec,'outputs':outs})[:1000])
    print(json.dumps({'status':row['status'],'resumed':rec['resumed'],'output_exists':output_exists,'kind':row['kind']}))

if __name__=='__main__': main()
