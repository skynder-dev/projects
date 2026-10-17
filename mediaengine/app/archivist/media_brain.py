from __future__ import annotations
from .platform_adapter import process_kwargs

import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .config import DB_PATH
from .db import db, now_iso

MEDIA_BRAIN_CACHE = DB_PATH.parent / "cache" / "media_brain"
ASPECTS = {"16:9": 16/9, "4:5": 4/5, "1:1": 1.0, "9:16": 9/16}
MEDIA_BRAIN_VERSION = 1
SMART_CROP_V2_SCHEMA_VERSION = 1
TRAJECTORY_STATUSES = {"draft", "approved", "rejected"}


def _hidden_kwargs():
    return process_kwargs()

def ensure_schema() -> None:
    MEDIA_BRAIN_CACHE.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS virtual_clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id INTEGER NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            kind TEXT NOT NULL DEFAULT 'scene',
            score REAL,
            label TEXT NOT NULL DEFAULT 'review',
            brightness REAL,
            detail REAL,
            motion REAL,
            center_interest REAL,
            reason TEXT,
            preview_path TEXT,
            analysis_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(inventory_id,start_ms,end_ms)
        );
        CREATE INDEX IF NOT EXISTS idx_vclips_inventory ON virtual_clips(inventory_id,start_ms);
        CREATE INDEX IF NOT EXISTS idx_vclips_score ON virtual_clips(score DESC);

        CREATE TABLE IF NOT EXISTS crop_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER NOT NULL REFERENCES virtual_clips(id) ON DELETE CASCADE,
            aspect TEXT NOT NULL,
            preset TEXT NOT NULL DEFAULT 'general',
            x REAL NOT NULL,
            y REAL NOT NULL,
            w REAL NOT NULL,
            h REAL NOT NULL,
            confidence REAL,
            mode TEXT NOT NULL DEFAULT 'static',
            reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(clip_id,aspect,preset)
        );
        CREATE INDEX IF NOT EXISTS idx_crop_clip ON crop_plans(clip_id);

        CREATE TABLE IF NOT EXISTS crop_trajectories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER NOT NULL REFERENCES virtual_clips(id) ON DELETE CASCADE,
            aspect TEXT NOT NULL,
            preset TEXT NOT NULL DEFAULT 'general',
            schema_version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved','rejected')),
            confidence REAL,
            smoothing REAL NOT NULL DEFAULT 0.35,
            max_pan_per_second REAL NOT NULL DEFAULT 0.35,
            max_zoom_per_second REAL NOT NULL DEFAULT 0.25,
            source TEXT NOT NULL DEFAULT 'smart_crop_v2',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(clip_id,aspect,preset)
        );
        CREATE INDEX IF NOT EXISTS idx_crop_trajectory_clip ON crop_trajectories(clip_id,aspect);

        CREATE TABLE IF NOT EXISTS crop_keyframes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trajectory_id INTEGER NOT NULL REFERENCES crop_trajectories(id) ON DELETE CASCADE,
            time_ms INTEGER NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            w REAL NOT NULL,
            h REAL NOT NULL,
            confidence REAL,
            locked INTEGER NOT NULL DEFAULT 0 CHECK(locked IN (0,1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(trajectory_id,time_ms)
        );
        CREATE INDEX IF NOT EXISTS idx_crop_keyframes_trajectory ON crop_keyframes(trajectory_id,time_ms);
        """)
        con.commit()


def _finite(value, name: str) -> float:
    try:
        out=float(value)
    except Exception as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def validate_crop_keyframes(keyframes: list[dict], clip_length_ms: int | None = None) -> list[dict]:
    if not isinstance(keyframes,list) or not keyframes:
        raise ValueError("at least one crop keyframe is required")
    if len(keyframes)>500:
        raise ValueError("too many crop keyframes")
    out=[]; previous=-1
    for raw in keyframes:
        t=int(raw.get("time_ms",-1))
        if t<0 or t<=previous or (clip_length_ms is not None and t>int(clip_length_ms)):
            raise ValueError("crop keyframe times must be unique, ordered and inside the clip")
        x=_finite(raw.get("x"),"x"); y=_finite(raw.get("y"),"y")
        w=_finite(raw.get("w"),"w"); h=_finite(raw.get("h"),"h")
        confidence=max(0.0,min(1.0,_finite(raw.get("confidence",0),"confidence")))
        if w<=0 or h<=0 or x<0 or y<0 or x+w>1.000001 or y+h>1.000001:
            raise ValueError("crop keyframe must stay inside normalized source bounds")
        out.append({"time_ms":t,"x":x,"y":y,"w":w,"h":h,"confidence":confidence,"locked":1 if raw.get("locked") else 0})
        previous=t
    return out


def interpolate_crop_keyframes(keyframes: list[dict], time_ms: int) -> dict:
    keys=validate_crop_keyframes(keyframes)
    t=max(keys[0]["time_ms"],min(keys[-1]["time_ms"],int(time_ms)))
    if t<=keys[0]["time_ms"]: return dict(keys[0])
    if t>=keys[-1]["time_ms"]: return dict(keys[-1])
    for a,b in zip(keys,keys[1:]):
        if a["time_ms"]<=t<=b["time_ms"]:
            q=(t-a["time_ms"])/max(1,b["time_ms"]-a["time_ms"])
            q=q*q*(3-2*q)
            return {"time_ms":t,**{k:a[k]+(b[k]-a[k])*q for k in ("x","y","w","h","confidence")},"locked":0}
    return dict(keys[-1])


def trajectory_for_clip(clip_id: int, aspect: str) -> dict | None:
    ensure_schema()
    with db() as con:
        row=con.execute("SELECT * FROM crop_trajectories WHERE clip_id=? AND aspect=? ORDER BY id DESC LIMIT 1",(int(clip_id),str(aspect))).fetchone()
        if not row: return None
        data=dict(row)
        data["keyframes"]=[dict(x) for x in con.execute("SELECT time_ms,x,y,w,h,confidence,locked FROM crop_keyframes WHERE trajectory_id=? ORDER BY time_ms",(int(row["id"]),)).fetchall()]
        return data


def trajectories_for_clip(clip_id: int) -> dict[str,dict]:
    ensure_schema()
    return {a:t for a in ASPECTS if (t:=trajectory_for_clip(clip_id,a))}


def save_crop_trajectory(clip_id: int, aspect: str, keyframes: list[dict], *, preset: str="general", status: str="draft", confidence: float=0.0, smoothing: float=0.35, max_pan_per_second: float=0.35, max_zoom_per_second: float=0.25, source: str="manual") -> dict:
    ensure_schema()
    if aspect not in ASPECTS: raise ValueError("unsupported crop aspect")
    if status not in TRAJECTORY_STATUSES: raise ValueError("invalid trajectory status")
    with db() as con:
        clip=con.execute("SELECT start_ms,end_ms FROM virtual_clips WHERE id=?",(int(clip_id),)).fetchone()
        if not clip: raise ValueError("virtual clip not found")
        keys=validate_crop_keyframes(keyframes,int(clip["end_ms"])-int(clip["start_ms"]))
        ts=now_iso()
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute("""INSERT INTO crop_trajectories(clip_id,aspect,preset,schema_version,status,confidence,smoothing,max_pan_per_second,max_zoom_per_second,source,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(clip_id,aspect,preset) DO UPDATE SET schema_version=excluded.schema_version,status=excluded.status,confidence=excluded.confidence,smoothing=excluded.smoothing,max_pan_per_second=excluded.max_pan_per_second,max_zoom_per_second=excluded.max_zoom_per_second,source=excluded.source,updated_at=excluded.updated_at""",
                (int(clip_id),aspect,"car" if preset=="car" else "general",SMART_CROP_V2_SCHEMA_VERSION,status,max(0,min(1,float(confidence))),max(0,min(1,float(smoothing))),max(.01,float(max_pan_per_second)),max(.01,float(max_zoom_per_second)),str(source)[:80],ts,ts))
            tid=int(con.execute("SELECT id FROM crop_trajectories WHERE clip_id=? AND aspect=? AND preset=?",(int(clip_id),aspect,"car" if preset=="car" else "general")).fetchone()["id"])
            con.execute("DELETE FROM crop_keyframes WHERE trajectory_id=?",(tid,))
            con.executemany("INSERT INTO crop_keyframes(trajectory_id,time_ms,x,y,w,h,confidence,locked,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",[(tid,k["time_ms"],k["x"],k["y"],k["w"],k["h"],k["confidence"],k["locked"],ts,ts) for k in keys])
            con.commit()
        except Exception:
            con.rollback(); raise
    return trajectory_for_clip(clip_id,aspect)


def build_fixture_trajectory(clip_id: int, aspect: str, plan: dict, clip_length_ms: int, preset: str="general") -> dict:
    duration=max(1,int(clip_length_ms)); w=float(plan["w"]); h=float(plan["h"])
    max_x=max(0.0,1.0-w); max_y=max(0.0,1.0-h); base_x=float(plan["x"]); base_y=float(plan["y"])
    swing=min(max_x*.12,.035); lift=min(max_y*.08,.02)
    keys=[
      {"time_ms":0,"x":max(0,min(max_x,base_x-swing)),"y":max(0,min(max_y,base_y)),"w":w,"h":h,"confidence":float(plan.get("confidence") or .5),"locked":False},
      {"time_ms":duration//2,"x":max(0,min(max_x,base_x+swing)),"y":max(0,min(max_y,base_y-lift)),"w":w,"h":h,"confidence":float(plan.get("confidence") or .5),"locked":False},
      {"time_ms":duration,"x":max(0,min(max_x,base_x)),"y":max(0,min(max_y,base_y)),"w":w,"h":h,"confidence":float(plan.get("confidence") or .5),"locked":False},
    ]
    return save_crop_trajectory(clip_id,aspect,keys,preset=preset,status="draft",confidence=sum(k["confidence"] for k in keys)/len(keys),source="fixture_v1")


def _frame_interest_center(frame: np.ndarray, preset: str="general") -> tuple[float,float,float]:
    heat=_heatmap([frame],preset)
    if heat is None or not heat.size: return .5,.48,0.0
    hh,ww=heat.shape; floor=float(np.percentile(heat,72)); weights=np.maximum(heat-floor,0.0); total=float(weights.sum())
    if total<=1e-7: return .5,.48,0.0
    yy,xx=np.mgrid[0:hh,0:ww]
    cx=float((weights*xx).sum()/total)/max(1,ww-1); cy=float((weights*yy).sum()/total)/max(1,hh-1)
    concentration=min(1.0,total/max(1.0,float(heat.sum()))*2.2); peak=min(1.0,float(heat.max())/(float(heat.mean())+1e-6)/8.0)
    return max(0.0,min(1.0,cx)),max(0.0,min(1.0,cy)),round(.55*concentration+.45*peak,3)


def _bounded_center(previous: tuple[float,float] | None, wanted: tuple[float,float], dt_seconds: float, max_pan_per_second: float) -> tuple[float,float]:
    if previous is None: return wanted
    dx=wanted[0]-previous[0]; dy=wanted[1]-previous[1]; dist=math.hypot(dx,dy); limit=max(.001,float(max_pan_per_second)*max(.001,float(dt_seconds)))
    if dist<=limit: return wanted
    q=limit/dist; return previous[0]+dx*q,previous[1]+dy*q


def _merge_locked_keyframes(existing: dict | None, generated: list[dict]) -> list[dict]:
    locked=[dict(x) for x in ((existing or {}).get("keyframes") or []) if x.get("locked")]
    if not locked: return generated
    by_time={int(k["time_ms"]):dict(k) for k in generated}
    for lock in locked: by_time[int(lock["time_ms"])]=lock
    return [by_time[t] for t in sorted(by_time)]


def build_tracked_trajectory(clip_id: int, aspect: str, plan: dict, path: Path, clip_start: float, clip_end: float, source_duration: float, preset: str="general", *, sample_interval: float=1.0, smoothing: float=.38, max_pan_per_second: float=.22) -> dict:
    """Create a bounded non-destructive crop path from lightweight visual-interest tracking."""
    length=max(.05,float(clip_end)-float(clip_start)); interval=max(.5,min(2.5,float(sample_interval))); count=max(2,min(24,int(math.ceil(length/interval))+1))
    rel_times=[length*i/(count-1) for i in range(count)]; samples=[]
    for rel in rel_times:
        frame=_extract_frame_ffmpeg(Path(path),float(clip_start)+rel,float(source_duration))
        if frame is not None:
            cx,cy,confidence=_frame_interest_center(frame,preset); samples.append((int(round(rel*1000)),cx,cy,confidence))
    if len(samples)<2: return build_fixture_trajectory(clip_id,aspect,plan,int(round(length*1000)),preset)
    w=float(plan["w"]); h=float(plan["h"]); max_x=max(0.0,1.0-w); max_y=max(0.0,1.0-h); alpha=max(.05,min(.95,1.0-float(smoothing)))
    previous=None; previous_t=None; smooth=None; keys=[]
    for time_ms,cx,cy,confidence in samples:
        wanted=(max(w/2,min(1-w/2,cx)),max(h/2,min(1-h/2,cy)))
        smooth=wanted if smooth is None else (smooth[0]+alpha*(wanted[0]-smooth[0]),smooth[1]+alpha*(wanted[1]-smooth[1]))
        dt=interval if previous_t is None else max(.001,(time_ms-previous_t)/1000.0); bounded=_bounded_center(previous,smooth,dt,max_pan_per_second)
        keys.append({"time_ms":time_ms,"x":max(0,min(max_x,bounded[0]-w/2)),"y":max(0,min(max_y,bounded[1]-h/2)),"w":w,"h":h,"confidence":confidence,"locked":False})
        previous=bounded; previous_t=time_ms
    end_ms=int(round(length*1000))
    if keys[-1]["time_ms"]!=end_ms:
        tail=dict(keys[-1]); tail["time_ms"]=end_ms; keys.append(tail)
    keys=_merge_locked_keyframes(trajectory_for_clip(clip_id,aspect),keys); avg=sum(float(k.get("confidence") or 0) for k in keys)/len(keys)
    return save_crop_trajectory(clip_id,aspect,keys,preset=preset,status="draft",confidence=avg,smoothing=smoothing,max_pan_per_second=max_pan_per_second,max_zoom_per_second=.12,source="tracking_v1")


def _ffmpeg_exe() -> str | None:
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        p = get_ffmpeg_exe()
        return p if p and Path(p).exists() else None
    except Exception:
        return shutil.which("ffmpeg")


def _duration_seconds(path: Path, duration_ms: int | None = None) -> float:
    if duration_ms and duration_ms > 0:
        return float(duration_ms) / 1000.0
    cap = cv2.VideoCapture(str(path))
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps > 0 and count > 0:
            return count / fps
    finally:
        cap.release()
    # no frame count (a browser / screen recording without a written length, or a path OpenCV cannot open):
    # FFmpeg reads the length, measuring it when the file has none
    from .media import probe_duration
    return float(probe_duration(Path(path)) or 0.0)


def _scene_cuts(path: Path, duration: float, progress_cb=None) -> list[float]:
    exe = _ffmpeg_exe()
    if not exe or duration <= 0:
        return []
    if progress_cb:
        try:
            progress_cb(0, 1, "scene scan")
        except Exception:
            pass
    try:
        # Scene detection does not need 4K pixels or every source frame.
        # Decode once, shrink early, and compare a few frames per second.
        vf = r"scale=320:-2:flags=fast_bilinear,fps=3,select=gt(scene\,0.30),showinfo"
        r = subprocess.run(
            [exe, "-hide_banner", "-loglevel", "info", "-i", str(path),
             "-an", "-sn", "-dn", "-filter:v", vf, "-f", "null", "-"],
            capture_output=True, text=True,
            timeout=max(60, min(360, int(duration * 0.25) + 45)),
            **_hidden_kwargs()
        )
        cuts = []
        for m in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", r.stderr or ""):
            t = float(m.group(1))
            if 0.5 < t < duration - 0.5:
                cuts.append(t)
        out = []
        for t in sorted(cuts):
            if not out or t - out[-1] >= 1.25:
                out.append(t)
        return out
    except Exception:
        return []


def _segments(duration: float, cuts: list[float]) -> list[tuple[float,float,str]]:
    if duration <= 0:
        return []
    bounds = [0.0]
    for t in cuts:
        if t - bounds[-1] >= 1.5 and duration - t >= 1.0:
            bounds.append(t)
    bounds.append(duration)
    raw = [(bounds[i], bounds[i+1]) for i in range(len(bounds)-1)]
    merged = []
    for s,e in raw:
        if e-s < 1.8 and merged:
            ps,pe = merged[-1]
            merged[-1] = (ps,e)
        else:
            merged.append((s,e))
    clips = []
    for s,e in merged:
        d = e-s
        if d <= 24:
            clips.append((s,e,"scene"))
            continue
        pos = s
        while pos < e - 1.8:
            ce = min(e, pos + 12.0)
            if ce-pos < 2.0:
                break
            clips.append((pos,ce,"window"))
            if ce >= e:
                break
            pos += 10.0
    if len(clips) > 180:
        stride = max(1, math.ceil(len(clips)/180))
        clips = clips[::stride][:180]
    return clips


def _extract_frame_ffmpeg(path: Path, seconds: float, duration: float) -> np.ndarray | None:
    """Fast random-access preview decode.

    Input-side -ss lets FFmpeg seek to a nearby keyframe instead of making
    OpenCV repeatedly reopen and walk a 4K/HEVC file from scratch.
    """
    exe = _ffmpeg_exe()
    if not exe:
        return None
    target = max(0.0, min(float(seconds), max(0.0, float(duration) - 0.03)))
    tries = [target]
    if target > 0.30:
        tries.append(max(0.0, target - min(0.35, max(0.08, duration * 0.005))))
    for ts in tries:
        try:
            r = subprocess.run(
                [exe, "-hide_banner", "-loglevel", "error",
                 "-ss", f"{ts:.3f}", "-i", str(path),
                 "-map", "0:v:0", "-an", "-sn", "-dn",
                 "-frames:v", "1",
                 "-vf", "scale='min(480,iw)':-2:flags=fast_bilinear",
                 "-q:v", "5", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"],
                capture_output=True, timeout=35, **_hidden_kwargs()
            )
            if r.returncode == 0 and r.stdout:
                arr = np.frombuffer(r.stdout, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    return frame
        except Exception:
            pass
    return None


def _clip_frames(path: Path, start: float, end: float, duration: float) -> list[np.ndarray]:
    # Two frames are enough for exposure/detail/motion + static crop v1 and cut
    # the old three-random-seek cost by a third.
    d = max(0.1, end - start)
    times = [start + d * 0.32, start + d * 0.68]
    frames = [f for f in (_extract_frame_ffmpeg(path, t, duration) for t in times) if f is not None]
    if len(frames) < 2:
        mid = _extract_frame_ffmpeg(path, start + d * 0.50, duration)
        if mid is not None:
            frames.append(mid)
    return frames


def _frame_metrics(frame: np.ndarray) -> tuple[float,float,float]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean()) / 255.0
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    detail = min(1.0, math.log1p(max(0.0, lap)) / math.log1p(1200.0))
    edges = cv2.Canny(gray, 70, 160)
    h,w = edges.shape
    y0,y1 = int(h*.18), int(h*.82)
    x0,x1 = int(w*.18), int(w*.82)
    all_e = float(edges.mean()) + 1e-6
    center = min(1.0, float(edges[y0:y1,x0:x1].mean()) / all_e / 1.6) if y1>y0 and x1>x0 else 0.5
    return brightness, detail, center


def _score_clip(frames: list[np.ndarray], duration: float) -> dict:
    if not frames:
        return {"score":0.0,"label":"review","brightness":0.0,"detail":0.0,"motion":0.0,"center":0.0,"reason":"preview decode failed"}
    vals = [_frame_metrics(f) for f in frames]
    brightness = sum(x[0] for x in vals)/len(vals)
    detail = sum(x[1] for x in vals)/len(vals)
    center = sum(x[2] for x in vals)/len(vals)
    motion_vals = []
    for a,b in zip(frames,frames[1:]):
        ga = cv2.cvtColor(a,cv2.COLOR_BGR2GRAY)
        gb = cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
        if ga.shape != gb.shape:
            gb = cv2.resize(gb,(ga.shape[1],ga.shape[0]))
        motion_vals.append(float(cv2.absdiff(ga,gb).mean())/255.0)
    motion = sum(motion_vals)/len(motion_vals) if motion_vals else 0.0
    exposure = max(0.0, 1.0 - abs(brightness-.50)/.50)
    motion_interest = max(0.0, min(1.0, motion/.13))
    if motion > .38:
        motion_interest *= .72
    if duration < 2:
        duration_score = .20
    elif duration < 4:
        duration_score = .65
    elif duration <= 16:
        duration_score = 1.0
    elif duration <= 24:
        duration_score = .82
    else:
        duration_score = .60
    score = 34*detail + 24*exposure + 17*motion_interest + 15*duration_score + 10*center
    score = round(max(0.0,min(100.0,score)),1)
    label = "best" if score >= 78 else ("good" if score >= 62 else "review")
    reason = f"detail {detail:.2f} · exposure {exposure:.2f} · motion {motion:.2f} · center {center:.2f}"
    return {"score":score,"label":label,"brightness":brightness,"detail":detail,"motion":motion,"center":center,"reason":reason}


def _heatmap(frames: list[np.ndarray], preset: str) -> np.ndarray | None:
    if not frames:
        return None
    target_w = 240
    gs = []
    for f in frames:
        h,w = f.shape[:2]
        nh = max(40, int(h*target_w/w))
        g = cv2.cvtColor(cv2.resize(f,(target_w,nh),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
        gs.append(g.astype(np.float32)/255.0)
    h = min(g.shape[0] for g in gs)
    gs = [g[:h,:] for g in gs]
    heat = np.zeros_like(gs[0],dtype=np.float32)
    for g in gs:
        gx = cv2.Sobel(g,cv2.CV_32F,1,0,ksize=3)
        gy = cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3)
        heat += cv2.magnitude(gx,gy)
    heat /= max(1,len(gs))
    if len(gs)>1:
        mot = np.zeros_like(heat)
        for a,b in zip(gs,gs[1:]):
            mot += cv2.absdiff(a,b)
        mot /= max(1,len(gs)-1)
        heat = .70*heat + .30*mot
    heat = cv2.GaussianBlur(heat,(0,0),3)
    yy,xx = np.mgrid[0:h,0:target_w]
    cx,cy = target_w*.5,h*.48
    sigma_x,sigma_y = target_w*.45,h*.50
    center = np.exp(-(((xx-cx)/sigma_x)**2 + ((yy-cy)/sigma_y)**2)/2).astype(np.float32)
    heat = .86*heat + .14*center*float(max(.01,heat.max()))
    if preset == "car":
        heat[int(h*.77):,:] *= .10
        heat[:, :int(target_w*.055)] *= .45
        heat[:, int(target_w*.945):] *= .45
    m = float(heat.max())
    if m>0: heat/=m
    return heat


def _rect_sum(ii,x,y,w,h):
    x2,y2=x+w,y+h
    return float(ii[y2,x2]-ii[y,x2]-ii[y2,x]+ii[y,x])


def _suggest_crop(frames: list[np.ndarray], aspect: float, preset: str) -> tuple[float,float,float,float,float,str]:
    heat = _heatmap(frames,preset)
    if heat is None:
        return 0.0,0.0,1.0,1.0,.0,"no frame data"
    hh,ww = heat.shape
    src_ratio = ww/hh
    if src_ratio >= aspect:
        ch = hh
        cw = max(8,int(ch*aspect))
    else:
        cw = ww
        ch = max(8,int(cw/aspect))
    zoom = .88 if preset=="car" else .96
    cw=max(8,min(ww,int(cw*zoom))); ch=max(8,min(hh,int(ch*zoom)))
    step_x=max(1,cw//18); step_y=max(1,ch//18)
    ii=cv2.integral(heat)
    best=(-1.0,0,0); scores=[]
    max_y=max(0,hh-ch); max_x=max(0,ww-cw)
    ys=list(range(0,max_y+1,step_y)) or [0]
    xs=list(range(0,max_x+1,step_x)) or [0]
    if ys[-1]!=max_y: ys.append(max_y)
    if xs[-1]!=max_x: xs.append(max_x)
    for y in ys:
        for x in xs:
            sc=_rect_sum(ii,x,y,cw,ch)/(cw*ch)
            scores.append(sc)
            if sc>best[0]: best=(sc,x,y)
    sc,x,y=best
    baseline=float(np.mean(scores)) if scores else sc
    conf=max(0.0,min(1.0,.5 + (sc-baseline)*1.8))
    reason=("car exclusion: avoid dashboard/edge cabin" if preset=="car" else "visual-interest crop")
    return x/ww,y/hh,cw/ww,ch/hh,round(conf,3),reason


def _save_preview(frame: np.ndarray, inv_id: int, start_ms: int, end_ms: int) -> str | None:
    try:
        root=MEDIA_BRAIN_CACHE/str(inv_id)
        root.mkdir(parents=True,exist_ok=True)
        p=root/f"{start_ms}_{end_ms}.jpg"
        # imencode + write_bytes: cv2.imwrite cannot write to a folder with non-Latin letters on Windows
        # (e.g. C:\Users\Дмитрий\...) and fails silently there
        ok,buf=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),82])
        if not ok:
            return None
        p.write_bytes(buf.tobytes())
        return str(p)
    except Exception:
        return None


def _table_exists(con, name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None


def analyze_video_into_clips(inv_id: int, path: Path, duration_ms: int | None = None, preset: str = "general", cancel_cb=None, progress_cb=None) -> dict:
    ensure_schema()
    preset = "car" if preset=="car" else "general"
    duration = _duration_seconds(path,duration_ms)
    if duration < 1.0:
        raise RuntimeError("Video duration is unavailable or too short")
    cuts = _scene_cuts(path,duration,progress_cb=progress_cb)
    segments = _segments(duration,cuts)
    if not segments:
        raise RuntimeError("No usable virtual clips found")
    if progress_cb:
        try:
            progress_cb(0, len(segments), f"clip 0/{len(segments)}")
        except Exception:
            pass
    with db() as con:
        # Re-analysis must not destroy the user's work: clips used in a composition or carrying an approved / hand-made
        # crop are kept as they are (deleting them cascaded into compositions and crops). Only unused clips are replaced.
        kept=con.execute("""SELECT id,start_ms,end_ms FROM virtual_clips v WHERE inventory_id=? AND (
                EXISTS(SELECT 1 FROM composition_items ci WHERE ci.clip_id=v.id)
                OR EXISTS(SELECT 1 FROM crop_trajectories t WHERE t.clip_id=v.id AND (t.status='approved' OR t.source='manual')))""",
                (int(inv_id),)).fetchall() if _table_exists(con,"composition_items") else con.execute(
                """SELECT id,start_ms,end_ms FROM virtual_clips v WHERE inventory_id=? AND
                EXISTS(SELECT 1 FROM crop_trajectories t WHERE t.clip_id=v.id AND (t.status='approved' OR t.source='manual'))""",(int(inv_id),)).fetchall()
        kept_ids=[int(r["id"]) for r in kept]
        kept_spans={(int(r["start_ms"]),int(r["end_ms"])) for r in kept}
        q=",".join("?"*len(kept_ids))
        old=con.execute("SELECT preview_path FROM virtual_clips WHERE inventory_id=?"+(f" AND id NOT IN ({q})" if kept_ids else ""),(int(inv_id),*kept_ids)).fetchall()
        con.execute("DELETE FROM virtual_clips WHERE inventory_id=?"+(f" AND id NOT IN ({q})" if kept_ids else ""),(int(inv_id),*kept_ids))
        con.commit()
    for r in old:
        try:
            if r["preview_path"]: Path(r["preview_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    made=0; best=0; good=0
    for idx,(start,end,kind) in enumerate(segments,1):
        if cancel_cb and cancel_cb():
            raise RuntimeError("cancelled")
        frames=_clip_frames(path,start,end,duration)
        metrics=_score_clip(frames,end-start)
        sm=int(round(start*1000)); em=int(round(end*1000))
        if (sm,em) in kept_spans:      # the user's kept clip already covers exactly this moment
            continue
        preview=_save_preview(frames[len(frames)//2],inv_id,sm,em) if frames else None
        ts=now_iso()
        with db() as con:
            cur=con.execute("""INSERT INTO virtual_clips
                (inventory_id,start_ms,end_ms,kind,score,label,brightness,detail,motion,center_interest,reason,preview_path,analysis_version,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(inv_id),sm,em,kind,metrics["score"],metrics["label"],metrics["brightness"],metrics["detail"],metrics["motion"],metrics["center"],metrics["reason"],preview,MEDIA_BRAIN_VERSION,ts,ts))
            clip_id=int(cur.lastrowid)
            for aspect_name,aspect in ASPECTS.items():
                x,y,w,h,confidence,reason=_suggest_crop(frames,aspect,preset)
                con.execute("""INSERT INTO crop_plans(clip_id,aspect,preset,x,y,w,h,confidence,mode,reason,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (clip_id,aspect_name,preset,x,y,w,h,confidence,"static",reason,ts,ts))
            con.commit()
        if os.environ.get("ARCHIVIST_SMART_CROP_V2_TRACKING")=="1":
            with db() as con:
                plans=[dict(x) for x in con.execute("SELECT * FROM crop_plans WHERE clip_id=? ORDER BY aspect",(clip_id,)).fetchall()]
            for plan in plans:
                build_tracked_trajectory(clip_id,plan["aspect"],plan,path,start,end,duration,preset)
        made+=1
        if metrics["label"]=="best": best+=1
        elif metrics["label"]=="good": good+=1
        if progress_cb:
            try: progress_cb(idx,len(segments),f"clip {idx}/{len(segments)}")
            except Exception: pass
    return {"clips":made,"best":best,"good":good,"cuts":len(cuts),"preset":preset}


def clips_for_inventory(inv_id: int) -> list[dict]:
    ensure_schema()
    with db() as con:
        rows=con.execute("SELECT * FROM virtual_clips WHERE inventory_id=? ORDER BY start_ms",(int(inv_id),)).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            crops=[dict(x) for x in con.execute("SELECT * FROM crop_plans WHERE clip_id=? ORDER BY CASE aspect WHEN '16:9' THEN 1 WHEN '4:5' THEN 2 WHEN '1:1' THEN 3 ELSE 4 END",(int(r["id"]),)).fetchall()]
            d["crops"]=crops
            out.append(d)
        return out


def best_clips(limit: int = 120) -> list[dict]:
    ensure_schema()
    with db() as con:
        rows=con.execute("""SELECT vc.*,i.filename,i.source_label,i.duration_ms,i.analysis_status,i.rights_status
            FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id
            WHERE i.excluded=0 AND i.work_selected=1 AND i.private_path IS NULL AND i.rejected_path IS NULL AND i.analysis_status<>'private'
              AND COALESCE(i.sha256,'') NOT IN (SELECT sha256 FROM ignored_hashes)
            ORDER BY vc.score DESC, vc.updated_at DESC LIMIT ?""",(max(1,min(500,int(limit))),)).fetchall()
        return [dict(r) for r in rows]


def clip_by_id(clip_id: int) -> dict | None:
    ensure_schema()
    with db() as con:
        r=con.execute("SELECT * FROM virtual_clips WHERE id=?",(int(clip_id),)).fetchone()
        return dict(r) if r else None


def purge_media_brain(ids: list[int]) -> None:
    ensure_schema()
    ids=[int(x) for x in ids]
    if not ids:
        return
    with db() as con:
        q=",".join("?" for _ in ids)
        rows=con.execute(f"SELECT preview_path FROM virtual_clips WHERE inventory_id IN ({q})",ids).fetchall()
        con.execute(f"DELETE FROM virtual_clips WHERE inventory_id IN ({q})",ids)
        con.commit()
    for r in rows:
        try:
            if r["preview_path"]: Path(r["preview_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    for inv_id in ids:
        shutil.rmtree(MEDIA_BRAIN_CACHE/str(inv_id),ignore_errors=True)
