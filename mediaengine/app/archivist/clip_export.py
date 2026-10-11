from __future__ import annotations
from .platform_adapter import process_kwargs
import os, subprocess
from pathlib import Path
from .config import HOME
from .db import db, now_iso
from .media import _ffmpeg_exe

EXPORTS=HOME/"Exports"
ASPECTS={"16:9":(1920,1080),"4:5":(1080,1350),"1:1":(1080,1080),"9:16":(1080,1920)}

def _flags():
    kw = process_kwargs()
    return int(kw.get("creationflags", 0) or 0), kw.get("startupinfo")

def ensure_schema():
    EXPORTS.mkdir(parents=True,exist_ok=True)
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS clip_exports(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          clip_id INTEGER NOT NULL,
          aspect TEXT NOT NULL,
          output_path TEXT NOT NULL,
          size_bytes INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'finished',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_clip_exports_clip ON clip_exports(clip_id,created_at DESC);
        """)
        con.commit()

def _unique_output(clip_id,aspect):
    EXPORTS.mkdir(parents=True,exist_ok=True)
    stem=f"clip_{int(clip_id)}_{str(aspect).replace(':','x')}"
    p=EXPORTS/(stem+".mp4");n=2
    while True:
        try:
            with open(p,"xb"):pass   # reserve the name atomically: two exports never share a file
            return p
        except FileExistsError:
            p=EXPORTS/(stem+f"_{n}.mp4");n+=1

def _render_source(source:Path,start_s:float,end_s:float,out:Path,plan=None,aspect="original"):
    exe=_ffmpeg_exe()
    if not exe: raise RuntimeError("FFmpeg is not available")
    start=max(0.0,float(start_s));end=max(start+.05,float(end_s));dur=end-start
    vf=[]
    if aspect!="original":
        if aspect not in ASPECTS: raise ValueError("unsupported aspect")
        if not plan: raise ValueError("Smart Crop plan is unavailable for this aspect")
        w=max(.02,min(1.0,float(plan["w"])));h=max(.02,min(1.0,float(plan["h"])))
        x=max(0.0,min(1.0-w,float(plan["x"])));y=max(0.0,min(1.0-h,float(plan["y"])))
        tw,th=ASPECTS[aspect]
        vf=[f"crop=iw*{w:.8f}:ih*{h:.8f}:iw*{x:.8f}:ih*{y:.8f},scale={tw}:{th}:flags=lanczos"]
    else:
        vf=["scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"]
    out.parent.mkdir(parents=True,exist_ok=True)
    flags,si=_flags()
    tmp=out.with_name(out.stem+f".{os.getpid()}.part.mp4")
    cmd=[str(exe),"-y","-hide_banner","-loglevel","error","-ss",f"{start:.3f}","-t",f"{dur:.3f}","-i",str(source),
         "-map","0:v:0","-map","0:a?","-vf",vf[0],"-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest",str(tmp)]
    try:
        rr=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",
                          timeout=max(90,int(dur*8)+60),creationflags=flags,startupinfo=si,close_fds=True)
        if rr.returncode!=0 or not tmp.exists() or tmp.stat().st_size<1024:
            raise RuntimeError(("FFmpeg export failed: "+(rr.stderr or ""))[-900:])
        os.replace(tmp,out)   # never leave a half-written file under the final name
    except BaseException:
        tmp.unlink(missing_ok=True);out.unlink(missing_ok=True);raise
    return {"output":str(out),"output_bytes":int(out.stat().st_size),"duration_s":dur,"aspect":aspect}

def export_clip(clip_id:int,aspect:str="original"):
    ensure_schema();aspect=str(aspect or "original")
    with db() as con:
        row=con.execute("""SELECT vc.id,vc.start_ms,vc.end_ms,vc.inventory_id,
          i.path,i.staging_path,i.archive_path,i.private_path,i.rejected_path,i.analysis_status,i.excluded
          FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id
          WHERE vc.id=?""",(int(clip_id),)).fetchone()
        if not row: raise ValueError("Clip not found")
        if int(row["excluded"] or 0) or row["private_path"] or row["rejected_path"] or str(row["analysis_status"] or "")=="private":
            raise ValueError("This clip is not exportable from the normal Library")
        plan=None
        if aspect!="original":
            plan=con.execute("SELECT x,y,w,h FROM crop_plans WHERE clip_id=? AND aspect=? ORDER BY id DESC LIMIT 1",(int(clip_id),aspect)).fetchone()
            if not plan: raise ValueError("Smart Crop plan is unavailable for this aspect")
        source=next((Path(row[k]) for k in ("staging_path","archive_path","path") if row[k] and Path(row[k]).exists()),None)
    if not source: raise FileNotFoundError("Local source video is unavailable")
    out=_unique_output(clip_id,aspect)
    result=_render_source(source,float(row["start_ms"])/1000.0,float(row["end_ms"])/1000.0,out,dict(plan) if plan else None,aspect)
    with db() as con:
        cur=con.execute("INSERT INTO clip_exports(clip_id,aspect,output_path,size_bytes,status,created_at) VALUES(?,?,?,?,?,?)",
                        (int(clip_id),aspect,str(out),int(result["output_bytes"]),"finished",now_iso()))
        export_id=int(cur.lastrowid);con.commit()
    result["export_id"]=export_id
    return result

def export_by_id(export_id:int):
    ensure_schema()
    with db() as con:r=con.execute("SELECT * FROM clip_exports WHERE id=?",(int(export_id),)).fetchone()
    return dict(r) if r else None
