from __future__ import annotations
from .platform_adapter import process_kwargs
import os, subprocess, tempfile, threading
from pathlib import Path
from .config import HOME
from .db import VISIBLE_SQL, db, now_iso
from .media import _ffmpeg_exe
from .media_brain import ensure_schema as ensure_media_brain_schema

EXPORTS=HOME/"Exports"
ASPECTS={"16:9":(1280,720),"4:5":(720,900),"1:1":(720,720),"9:16":(720,1280)}
MAX_CLIPS=20
MAX_DURATION_S=180.0
_ACTIVE=set()
_ACTIVE_LOCK=threading.Lock()

def _flags():
    kw = process_kwargs()
    return int(kw.get("creationflags", 0) or 0), kw.get("startupinfo")

def _ensure_col(con,name,ddl):
    cols={r["name"] for r in con.execute("PRAGMA table_info(compositions)").fetchall()}
    if name not in cols:con.execute(f"ALTER TABLE compositions ADD COLUMN {name} {ddl}")

def ensure_schema():
    ensure_media_brain_schema();EXPORTS.mkdir(parents=True,exist_ok=True)
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS compositions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,aspect TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',
          output_path TEXT,output_bytes INTEGER NOT NULL DEFAULT 0,last_error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS composition_items(
          composition_id INTEGER NOT NULL REFERENCES compositions(id) ON DELETE CASCADE,
          position INTEGER NOT NULL,clip_id INTEGER NOT NULL REFERENCES virtual_clips(id) ON DELETE CASCADE,
          PRIMARY KEY(composition_id,position)
        );
        CREATE INDEX IF NOT EXISTS idx_comp_items_clip ON composition_items(clip_id);
        """)
        _ensure_col(con,"render_started_at","TEXT");_ensure_col(con,"render_finished_at","TEXT")
        with _ACTIVE_LOCK:active=set(_ACTIVE)
        rows=con.execute("SELECT id FROM compositions WHERE status IN ('queued','rendering')").fetchall()
        for r in rows:
            if int(r["id"]) not in active:
                con.execute("UPDATE compositions SET status='failed',last_error='render_interrupted_restart',render_finished_at=?,updated_at=? WHERE id=?",
                            (now_iso(),now_iso(),int(r["id"])))
        con.commit()

def recovery_policy():
    return {"queued_after_restart":"failed","rendering_after_restart":"failed","partial_final_removed":True,"retry":"user_safe"}

def create_composition(clip_ids,aspect,title=""):
    ensure_schema();ids=[]
    for x in clip_ids:
        try:i=int(x)
        except Exception:continue
        if i not in ids:ids.append(i)
    if not ids:raise ValueError("Choose at least one virtual clip")
    if len(ids)>MAX_CLIPS:raise ValueError(f"Composer currently supports up to {MAX_CLIPS} clips")
    if aspect not in ASPECTS:raise ValueError("Choose a supported target aspect")
    with db() as con:
        q=",".join("?" for _ in ids)
        rows=con.execute(f"""SELECT vc.id,vc.start_ms,vc.end_ms FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id
          WHERE vc.id IN ({q}) AND {VISIBLE_SQL}""",ids).fetchall()
        found={int(r["id"]):r for r in rows}
        if len(found)!=len(ids):raise ValueError("One or more clips are unavailable for normal Library composition")
        total=sum(max(0,int(found[i]["end_ms"])-int(found[i]["start_ms"])) for i in ids)/1000.0
        if total>MAX_DURATION_S:raise ValueError(f"Composition is limited to {int(MAX_DURATION_S)} seconds")
        ts=now_iso();cur=con.execute("INSERT INTO compositions(title,aspect,status,created_at,updated_at) VALUES(?,?,?,?,?)",
            ((str(title or "").strip()[:80] or "Untitled composition"),aspect,"draft",ts,ts));cid=int(cur.lastrowid)
        con.executemany("INSERT INTO composition_items(composition_id,position,clip_id) VALUES(?,?,?)",[(cid,p+1,i) for p,i in enumerate(ids)]);con.commit()
    return cid

def composition_detail(composition_id):
    ensure_schema()
    with db() as con:
        c=con.execute("SELECT * FROM compositions WHERE id=?",(int(composition_id),)).fetchone()
        if not c:return None
        items=[dict(r) for r in con.execute(f"""SELECT ci.position,vc.*,i.filename,i.source_label,
          CASE WHEN {VISIBLE_SQL} THEN 0 ELSE 1 END hidden FROM composition_items ci
          JOIN virtual_clips vc ON vc.id=ci.clip_id JOIN inventory i ON i.id=vc.inventory_id
          WHERE ci.composition_id=? ORDER BY ci.position""",(int(composition_id),)).fetchall()]
        hidden=sum(1 for x in items if x["hidden"])
        # a video made Private (or removed) after the render: its moments are not listed and the MP4 is not offered
        d=dict(c);d["items"]=[{k:v for k,v in x.items() if k!="hidden"} for x in items if not x["hidden"]];d["hidden_items"]=hidden
        if hidden:
            d["output_path"]=None
        return d

def move_item(composition_id,position,direction):
    ensure_schema();pos=int(position);other=pos+(-1 if str(direction)=="up" else 1)
    if other<1:return
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        st=con.execute("SELECT status FROM compositions WHERE id=?",(int(composition_id),)).fetchone()
        if st and st["status"] in ("queued","rendering"):     # the video being made keeps the order it started with
            con.rollback();raise ValueError("Wait until the video of this composition is made, then change the order.")
        a=con.execute("SELECT clip_id FROM composition_items WHERE composition_id=? AND position=?",(int(composition_id),pos)).fetchone()
        b=con.execute("SELECT clip_id FROM composition_items WHERE composition_id=? AND position=?",(int(composition_id),other)).fetchone()
        if not a or not b:return
        con.execute("UPDATE composition_items SET position=0 WHERE composition_id=? AND position=?",(int(composition_id),pos))
        con.execute("UPDATE composition_items SET position=? WHERE composition_id=? AND position=?",(pos,int(composition_id),other))
        con.execute("UPDATE composition_items SET position=? WHERE composition_id=? AND position=0",(other,int(composition_id)))
        # the order changed: the last MP4 is not this composition any more (Render makes it again)
        con.execute("UPDATE compositions SET status='draft',output_path=NULL,output_bytes=0,updated_at=? WHERE id=? AND status NOT IN ('queued','rendering')",
                    (now_iso(),int(composition_id)));con.commit()

def remove_item(composition_id,position,clip_id=None):
    """One moment out of a composition (the others close up); never while its video is being made. With clip_id: only
    if that moment is still at that place (a page from before another change removes nothing else)."""
    ensure_schema();cid=int(composition_id);pos=int(position)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        st=con.execute("SELECT status FROM compositions WHERE id=?",(cid,)).fetchone()
        if not st:con.rollback();raise ValueError("Composition not found")
        if st["status"] in ("queued","rendering"):
            con.rollback();raise ValueError("Wait until the video of this composition is made, then change it.")
        here=con.execute("SELECT clip_id FROM composition_items WHERE composition_id=? AND position=?",(cid,pos)).fetchone()
        if not here or (clip_id is not None and int(here["clip_id"])!=int(clip_id)):
            con.rollback();return
        con.execute("DELETE FROM composition_items WHERE composition_id=? AND position=?",(cid,pos))
        for r in con.execute("SELECT position FROM composition_items WHERE composition_id=? AND position>? ORDER BY position",(cid,pos)).fetchall():
            con.execute("UPDATE composition_items SET position=? WHERE composition_id=? AND position=?",(int(r["position"])-1,cid,int(r["position"])))
        con.execute("UPDATE compositions SET status='draft',output_path=NULL,output_bytes=0,last_error=NULL,updated_at=? WHERE id=?",(now_iso(),cid))
        con.commit()

def drop_hidden(composition_id):
    """The moments of videos now Private or no longer in the Library taken out (the rest close up in their order)."""
    ensure_schema();cid=int(composition_id)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        st=con.execute("SELECT status FROM compositions WHERE id=?",(cid,)).fetchone()
        if not st or st["status"] in ("queued","rendering"):
            con.rollback();return 0
        rows=con.execute(f"""SELECT ci.position,CASE WHEN {VISIBLE_SQL} THEN 1 ELSE 0 END visible FROM composition_items ci
          JOIN virtual_clips vc ON vc.id=ci.clip_id JOIN inventory i ON i.id=vc.inventory_id WHERE ci.composition_id=? ORDER BY ci.position""",(cid,)).fetchall()
        gone=[int(r["position"]) for r in rows if not r["visible"]]
        if not gone:con.rollback();return 0
        con.executemany("DELETE FROM composition_items WHERE composition_id=? AND position=?",[(cid,x) for x in gone])
        left=[int(r["position"]) for r in rows if r["visible"]]
        for new,old in enumerate(left,1):     # (positions only move down: no clash with a row not moved yet)
            if new!=old:con.execute("UPDATE composition_items SET position=? WHERE composition_id=? AND position=?",(new,cid,old))
        con.execute("UPDATE compositions SET status='draft',output_path=NULL,output_bytes=0,last_error=NULL,updated_at=? WHERE id=?",(now_iso(),cid))
        con.commit()
    return len(gone)

def delete_composition(composition_id):
    """A composition forgotten (its moments stay in the Library); its own MP4s in Exports go, unless one was recorded
    as published or handed off for upload."""
    ensure_schema();cid=int(composition_id)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        st=con.execute("SELECT status FROM compositions WHERE id=?",(cid,)).fetchone()
        if not st:con.rollback();return False
        if st["status"] in ("queued","rendering"):
            con.rollback();raise ValueError("Wait until the video of this composition is made.")
        con.execute("DELETE FROM composition_items WHERE composition_id=?",(cid,))
        con.execute("DELETE FROM compositions WHERE id=?",(cid,));con.commit()
    if not _recorded(cid):             # (a published or handed-off composition: its videos all stay)
        try:
            for old in EXPORTS.iterdir():
                if _ours(old,cid):
                    try:old.unlink()
                    except OSError:pass
        except OSError:
            pass
    return True

def _center_plan(width,height,aspect):
    tw,th=ASPECTS[aspect];target=tw/th;sw=max(1.0,float(width or 1));sh=max(1.0,float(height or 1));src=sw/sh
    if src>target:
        w=target/src;return {"x":(1-w)/2,"y":0.0,"w":w,"h":1.0}
    h=src/target;return {"x":0.0,"y":(1-h)/2,"w":1.0,"h":h}

class _Done:
    def __init__(self,returncode,stdout,stderr):self.returncode,self.stdout,self.stderr=returncode,stdout,stderr

def _run(cmd,timeout):
    """FFmpeg for a render, tied to the app on Windows (a Quit or a crash never leaves it writing into Exports)."""
    flags,si=_flags()
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",
                          creationflags=flags,startupinfo=si,close_fds=True)
    try:
        from .auto_edit import _attach_job_object
        _attach_job_object(proc)
    except Exception:
        pass
    try:
        out,err=proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill();out,err=proc.communicate()
        raise RuntimeError("FFmpeg took too long and was stopped")
    finally:      # the job object's handle closed with its FFmpeg (one per segment otherwise, all app long)
        try:
            from .auto_edit import _JOB_HANDLES
            h=_JOB_HANDLES.pop(proc.pid,None)
            if h is not None:
                import ctypes
                from ctypes import wintypes
                ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
        except Exception:
            pass
    return _Done(proc.returncode,out,err)

def _has_audio(source):
    exe=_ffmpeg_exe()
    if not exe:return False
    flags,si=_flags()
    try:
        rr=subprocess.run([str(exe),"-hide_banner","-i",str(source)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            encoding="utf-8",errors="replace",timeout=15,creationflags=flags,startupinfo=si,close_fds=True)
        return "Audio:" in (rr.stderr or "")
    except Exception:return False

def _render_segment(source,start_s,end_s,out,plan,aspect):
    exe=_ffmpeg_exe()
    if not exe:raise RuntimeError("FFmpeg is not available")
    tw,th=ASPECTS[aspect];x=float(plan["x"]);y=float(plan["y"]);w=float(plan["w"]);h=float(plan["h"])
    vf=f"crop=iw*{w:.8f}:ih*{h:.8f}:iw*{x:.8f}:ih*{y:.8f},scale={tw}:{th}:flags=lanczos,fps=30,setsar=1"
    start=max(0,float(start_s));dur=max(.05,float(end_s)-start);flags,si=_flags();audio=_has_audio(source)
    cmd=[str(exe),"-y","-hide_banner","-loglevel","error","-ss",f"{start:.3f}","-t",f"{dur:.3f}","-i",str(source)]
    if audio:
        cmd+=["-map","0:v:0","-map","0:a:0","-vf",vf,"-af","aresample=48000:async=1:first_pts=0,apad","-ac","2","-ar","48000"]
    else:
        cmd+=["-f","lavfi","-t",f"{dur:.3f}","-i","anullsrc=channel_layout=stereo:sample_rate=48000",
              "-map","0:v:0","-map","1:a:0","-vf",vf,"-ac","2","-ar","48000"]
    cmd+=["-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
          "-t",f"{dur:.3f}","-movflags","+faststart",str(out)]
    rr=_run(cmd,max(90,int(dur*8)+60))
    if rr.returncode!=0 or not out.exists() or out.stat().st_size<1024:raise RuntimeError("segment render failed: "+(rr.stderr or "").strip()[-400:])

def _concat_segments(parts,out):
    exe=_ffmpeg_exe()
    if not exe:raise RuntimeError("FFmpeg is not available")
    # The list lives next to the parts (per-render temp dir), not in the shared Exports folder.
    flags,si=_flags();lst=Path(parts[0]).parent/"concat.txt";tmp=out.with_name(out.stem+f".{os.getpid()}.part.mp4")
    lst.write_text("".join("file '"+Path(p).resolve().as_posix().replace("'","'\\''")+"'\n" for p in parts),encoding="utf-8")
    try:
        rr=_run([str(exe),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(lst),"-c","copy","-movflags","+faststart",str(tmp)],120)
        if rr.returncode!=0 or not tmp.exists() or tmp.stat().st_size<1024:raise RuntimeError("composition concat failed: "+(rr.stderr or "").strip()[-400:])
        os.replace(tmp,out)
    finally:
        tmp.unlink(missing_ok=True)

def _unique_output(cid,aspect):
    EXPORTS.mkdir(parents=True,exist_ok=True);n=1
    while True:
        p=EXPORTS/(f"composition_{int(cid)}_{aspect.replace(':','x')}"+(f"_{n}" if n>1 else "")+".mp4")
        try:
            with open(p,"xb"):pass   # atomic name reservation
            return p
        except FileExistsError:
            n+=1

def render_composition(composition_id):
    ensure_schema();cid=int(composition_id)
    with db() as con:
        comp=con.execute("SELECT * FROM compositions WHERE id=?",(cid,)).fetchone()
        if not comp:raise ValueError("Composition not found")
        aspect=str(comp["aspect"]);rows=[dict(r) for r in con.execute(f"""SELECT ci.position,vc.id clip_id,vc.start_ms,vc.end_ms,
          i.width,i.height,i.path,i.staging_path,i.archive_path,i.private_path,i.rejected_path,i.analysis_status,i.excluded,
          CASE WHEN {VISIBLE_SQL} THEN 1 ELSE 0 END visible,
          cp.x,cp.y,cp.w,cp.h FROM composition_items ci JOIN virtual_clips vc ON vc.id=ci.clip_id
          JOIN inventory i ON i.id=vc.inventory_id LEFT JOIN crop_plans cp ON cp.id=(
            SELECT id FROM crop_plans x WHERE x.clip_id=vc.id AND x.aspect=? ORDER BY id DESC LIMIT 1)
          WHERE ci.composition_id=? ORDER BY ci.position""",(aspect,cid)).fetchall()]
        if not rows:          # (its videos removed from the catalog): said on the page, not only in a log
            ts=now_iso();con.execute("UPDATE compositions SET status='failed',last_error=?,render_finished_at=?,updated_at=? WHERE id=?",
                                     ("This composition has no moments left: its videos are no longer in the catalog.",ts,ts,cid));con.commit()
            raise ValueError("Composition is empty")
        ts=now_iso();con.execute("UPDATE compositions SET status='rendering',last_error=NULL,render_started_at=?,render_finished_at=NULL,updated_at=? WHERE id=?",(ts,ts,cid));con.commit()
    total=sum(max(0,int(r["end_ms"])-int(r["start_ms"])) for r in rows)/1000.0
    out=None
    try:      # (everything after 'rendering' inside: any failure is said as itself, not as "interrupted by a restart")
        if len(rows)>MAX_CLIPS or total>MAX_DURATION_S:raise ValueError("Composition exceeds current safe render limits")
        out=_unique_output(cid,aspect)
        # (a part file held by an antivirus at the end does not throw the finished video away)
        with tempfile.TemporaryDirectory(prefix="archivist_composer_",ignore_cleanup_errors=True) as td:
            tdir=Path(td);parts=[]
            for idx,r in enumerate(rows):
                if int(r["excluded"] or 0) or r["private_path"] or r["rejected_path"] or str(r["analysis_status"] or "")=="private" \
                        or not r["visible"]:          # (a copy of a Private video too)
                    raise ValueError("A composition clip is no longer exportable")
                src=next((Path(r[k]) for k in ("staging_path","archive_path","path") if r[k] and Path(r[k]).exists()),None)
                if not src:raise FileNotFoundError("A composition source is unavailable")
                plan={"x":r["x"],"y":r["y"],"w":r["w"],"h":r["h"]} if r["x"] is not None else _center_plan(r["width"],r["height"],aspect)
                part=tdir/f"{idx:03d}.mp4";_render_segment(src,float(r["start_ms"])/1000,float(r["end_ms"])/1000,part,plan,aspect);parts.append(part)
            _concat_segments(parts,out)
        ids=[int(r["clip_id"]) for r in rows]
        with db() as con:      # a video made Private (or removed) while this was made: its picture is not kept
            q=",".join("?" for _ in ids)
            still=con.execute(f"SELECT COUNT(*) FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id WHERE vc.id IN ({q}) AND {VISIBLE_SQL}",ids).fetchone()[0]
        if int(still)!=len(set(ids)):
            raise ValueError("A video of this composition was made Private or removed while it was being made: the new video was not kept.")
        ts=now_iso()
        with db() as con:
            con.execute("UPDATE compositions SET status='finished',output_path=?,output_bytes=?,last_error=NULL,render_finished_at=?,updated_at=? WHERE id=?",
                        (str(out),int(out.stat().st_size),ts,ts,cid));con.commit()
        res={"composition_id":cid,"output":str(out),"output_bytes":int(out.stat().st_size),"clips":len(rows),"duration_s":total,"aspect":aspect,"audio":True}
    except Exception as exc:
        if out is not None:out.unlink(missing_ok=True)
        ts=now_iso()
        with db() as con:
            con.execute("UPDATE compositions SET status='failed',last_error=?,render_finished_at=?,updated_at=? WHERE id=?",(str(exc)[:500],ts,ts,cid));con.commit()
        raise
    # the video this one replaces goes (it was this composition's previous render, never offered again) - only a file
    # of exactly the name a render gives, never one recorded as published or handed off, never one open in a player;
    # a failure here never touches the new video
    try:      # (also those of before a reorder, which forgot its file: every one of exactly a render's name)
        if not _recorded(cid):
            for old in EXPORTS.iterdir():
                if old!=out and _ours(old,cid):
                    try:old.unlink()
                    except OSError:pass
    except Exception:
        pass
    return res

def _ours(path,cid):
    """A file of exactly the name render_composition gives this composition's videos (a copy or a renamed file of
    the owner's in Exports never is)."""
    import re
    return re.fullmatch(rf"composition_{int(cid)}_(16x9|9x16|4x5|1x1)(_\d+)?\.mp4",Path(path).name) is not None

def _recorded(cid):
    """A composition recorded as published or handed off for upload: its videos are kept (a record points at one)."""
    try:
        with db() as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='social_publications'").fetchone():
                cols={r["name"] for r in con.execute("PRAGMA table_info(social_publications)").fetchall()}
                if "composition_id" in cols and con.execute("SELECT 1 FROM social_publications WHERE composition_id=? LIMIT 1",(int(cid),)).fetchone():
                    return True
    except Exception:
        return True
    try:
        return any((HOME/"exports"/"social_handoffs").glob(f"composition-{int(cid)}-*.json"))
    except OSError:
        return True

def _runner(cid):
    try:render_composition(cid)
    except Exception:pass       # (its reason is on the composition: last_error / the page)
    finally:
        with _ACTIVE_LOCK:_ACTIVE.discard(int(cid))

def start_render(composition_id):
    ensure_schema();cid=int(composition_id)
    with _ACTIVE_LOCK:
        if cid in _ACTIVE:return {"started":False,"status":"already_running"}
        _ACTIVE.add(cid)
    with db() as con:
        if not con.execute("SELECT 1 FROM compositions WHERE id=?",(cid,)).fetchone():
            with _ACTIVE_LOCK:_ACTIVE.discard(cid)
            raise ValueError("Composition not found")
        con.execute("UPDATE compositions SET status='queued',last_error=NULL,updated_at=? WHERE id=?",(now_iso(),cid));con.commit()
    threading.Thread(target=_runner,args=(cid,),name=f"composer-{cid}",daemon=True).start()
    return {"started":True,"status":"queued"}

def render_fixture(sources,aspect,out):
    plan=_center_plan(640,360,aspect)
    with tempfile.TemporaryDirectory(prefix="archivist_composer_fixture_") as td:
        parts=[]
        for idx,(src,start,end) in enumerate(sources):
            p=Path(td)/f"{idx:03d}.mp4";_render_segment(Path(src),start,end,p,plan,aspect);parts.append(p)
        _concat_segments(parts,Path(out))
    return {"output_bytes":Path(out).stat().st_size,"clips":len(sources),"aspect":aspect,"audio":_has_audio(out)}
