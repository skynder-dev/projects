from __future__ import annotations
from .platform_adapter import process_kwargs

import json, os, shutil, subprocess, threading, time
from datetime import datetime, timezone
from pathlib import Path

from .config import HOME
from .db import db
from .media import _ffmpeg_exe, probe_duration

PRESETS = {
    "share_1080p": {"label": "Share 1080p", "crf": 24, "cap": 1920, "audio_k": 128, "suffix": "share_1080p"},
    "small_720p": {"label": "Small 720p", "crf": 27, "cap": 1280, "audio_k": 96, "suffix": "small_720p"},
    "hq_1080p": {"label": "High Quality 1080p", "crf": 20, "cap": 1920, "audio_k": 160, "suffix": "hq_1080p"},
    "keep_resolution": {"label": "Original Resolution", "crf": 23, "cap": None, "audio_k": 160, "suffix": "keep"},
}

_LOCK = threading.Lock()
_CURRENT_PROCESS = None
_CURRENT_PROCESS_JOB_ID = None


def _now():
    return datetime.now(timezone.utc).isoformat()


def _flags():
    kw = process_kwargs()
    return int(kw.get("creationflags", 0) or 0), kw.get("startupinfo")

def _local_path(row):
    for key in ("staging_path", "archive_path"):
        raw = row[key] if key in row.keys() else None
        if raw and Path(raw).exists():
            return Path(raw)
    raw = row["path"] if "path" in row.keys() else None
    if raw and Path(raw).exists():
        return Path(raw)
    return None


def _unique_output(source: Path, preset: str, target_mb: int | None, output_dir: Path | None = None) -> Path:
    cfg = PRESETS[preset]
    # Never write next to the source: it may be an SD card, a phone folder or another app's archive.
    folder = output_dir or (HOME / "Converted")
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        folder = HOME / "Converted"
        folder.mkdir(parents=True, exist_ok=True)
    suffix = f"target_{int(target_mb)}mb" if target_mb else cfg["suffix"]
    base = folder / f"{source.stem}_{suffix}.mp4"
    if not base.exists():
        return base
    n = 2
    while True:
        p = folder / f"{source.stem}_{suffix}_{n}.mp4"
        if not p.exists():
            return p
        n += 1


def _scale_args(preset: str):
    cap = PRESETS[preset]["cap"]
    if not cap:
        return []
    # Cap the long edge. 1920 => 1920x1080 landscape or 1080x1920 portrait.
    vf = f"scale='min({int(cap)},iw)':'min({int(cap)},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"
    return ["-vf", vf]


def _cancelled(job_id: int | None):
    if not job_id:
        return False
    with db() as con:
        r = con.execute("SELECT cancel_requested FROM jobs WHERE id=?", (int(job_id),)).fetchone()
    return bool(r and r["cancel_requested"])


def _run_progress(cmd, duration_s: float, progress_cb=None, cancel_cb=None, phase_base=0.0, phase_span=1.0, job_id=None):
    global _CURRENT_PROCESS, _CURRENT_PROCESS_JOB_ID
    flags, si = _flags()
    full = [str(x) for x in cmd[:-1]] + ["-progress", "pipe:1", "-nostats", str(cmd[-1])]
    errors = []
    p = subprocess.Popen(
        full, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        creationflags=flags, startupinfo=si, close_fds=True
    )
    with _LOCK:
        _CURRENT_PROCESS = p
        _CURRENT_PROCESS_JOB_ID = int(job_id) if job_id else None
    if job_id:
        ts=_now()
        with db() as con:
            con.execute("UPDATE jobs SET worker_pid=?,heartbeat_at=?,progress_at=? WHERE id=?",(int(p.pid),ts,ts,int(job_id)));con.commit()
    try:
        if p.stdout:
            for raw in p.stdout:
                line = raw.strip()
                if cancel_cb and cancel_cb():
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    raise RuntimeError("cancelled")
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k in ("out_time_us", "out_time_ms"):
                        try:
                            sec = float(v) / 1_000_000.0
                            frac = 0 if duration_s <= 0 else max(0.0, min(1.0, sec / duration_s))
                            if progress_cb:
                                progress_cb((phase_base + phase_span * frac) * 100.0)
                        except Exception:
                            pass
                    elif k == "progress" and v == "end" and progress_cb:
                        progress_cb((phase_base + phase_span) * 100.0)
                elif line:
                    errors.append(line[-500:])
                    if len(errors) > 12:
                        errors.pop(0)
        code = p.wait()
        if code != 0:
            raise RuntimeError(("FFmpeg failed: " + " | ".join(errors[-4:]))[:1200])
    finally:
        with _LOCK:
            if _CURRENT_PROCESS is p:
                _CURRENT_PROCESS = None
                _CURRENT_PROCESS_JOB_ID = None
        if job_id:
            with db() as con:
                con.execute("UPDATE jobs SET worker_pid=NULL,heartbeat_at=? WHERE id=? AND worker_pid=?",(_now(),int(job_id),int(p.pid)));con.commit()


def convert_file(source, preset="share_1080p", target_mb=None, progress_cb=None, cancel_cb=None, output_dir=None, job_id=None):
    source = Path(source)
    if preset not in PRESETS:
        raise ValueError("Unknown preset")
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(str(source))
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not available")
    duration = float(probe_duration(source) or 0.0)
    if duration <= 0:
        raise RuntimeError("Could not read video duration")
    target_mb = int(target_mb) if target_mb else None
    out = _unique_output(source, preset, target_mb, Path(output_dir) if output_dir else None)
    part = out.with_name(out.stem + ".part.mp4")
    try:
        if part.exists():
            part.unlink()
    except Exception:
        pass

    try:
        cfg = PRESETS[preset]
        common = [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a?", *_scale_args(preset),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        ]

        if target_mb:
            audio_k = int(cfg["audio_k"])
            total_bits = float(target_mb) * 1024 * 1024 * 8 * 0.94
            video_k = max(250, int(total_bits / duration / 1000.0 - audio_k))
            passlog = str((HOME / "data" / f"ffmpeg2pass-{os.getpid()}-{threading.get_ident()}").resolve())
            pass1 = [
                str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
                "-map", "0:v:0", *_scale_args(preset),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
                "-b:v", f"{video_k}k", "-maxrate", f"{int(video_k*1.25)}k", "-bufsize", f"{int(video_k*2)}k",
                "-pass", "1", "-passlogfile", passlog, "-an", "-f", "null", os.devnull
            ]
            _run_progress(pass1, duration, progress_cb, cancel_cb, 0.0, 0.48, job_id=job_id)
            pass2 = common + [
                "-b:v", f"{video_k}k", "-maxrate", f"{int(video_k*1.25)}k", "-bufsize", f"{int(video_k*2)}k",
                "-pass", "2", "-passlogfile", passlog,
                "-c:a", "aac", "-b:a", f"{audio_k}k", "-movflags", "+faststart", str(part)
            ]
            _run_progress(pass2, duration, progress_cb, cancel_cb, 0.50, 0.50, job_id=job_id)
            for extra in ("-0.log", "-0.log.mbtree", ".log", ".log.mbtree"):
                try:
                    Path(passlog + extra).unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            cmd = common + [
                "-crf", str(int(cfg["crf"])),
                "-c:a", "aac", "-b:a", f"{int(cfg['audio_k'])}k",
                "-movflags", "+faststart", str(part)
            ]
            _run_progress(cmd, duration, progress_cb, cancel_cb, job_id=job_id)

        if cancel_cb and cancel_cb():
            raise RuntimeError("cancelled")
        part.replace(out)
        src_size = source.stat().st_size
        out_size = out.stat().st_size
        return {
            "source": str(source),
            "output": str(out),
            "source_bytes": src_size,
            "output_bytes": out_size,
            "saved_percent": round(max(0.0, (1.0 - out_size / max(1, src_size)) * 100.0), 1),
            "preset": preset,
            "target_mb": target_mb,
        }
    except BaseException:
        # never leave a half-written .part file behind (it would be re-discovered as media)
        try:
            part.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _job_update(job_id, **fields):
    if not fields:
        return
    ts=_now()
    fields.setdefault("heartbeat_at",ts)
    fields.setdefault("progress_at",ts)
    cols = ",".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [int(job_id)]
    with db() as con:
        con.execute(f"UPDATE jobs SET {cols} WHERE id=?", vals)
        con.commit()


def _consume_watchdog_request(job_id):
    with db() as con:
        r=con.execute("SELECT watchdog_retry_requested FROM jobs WHERE id=?",(int(job_id),)).fetchone()
        code=int(r["watchdog_retry_requested"] or 0) if r else 0
        if code: con.execute("UPDATE jobs SET watchdog_retry_requested=0 WHERE id=?",(int(job_id),));con.commit()
    return code


def terminate_current_process(job_id):
    with _LOCK:
        p=_CURRENT_PROCESS
        owner=_CURRENT_PROCESS_JOB_ID
    if not p or owner!=int(job_id):
        return False
    try:
        if os.name=="nt":
            flags,si=_flags()
            subprocess.run(["taskkill","/PID",str(int(p.pid)),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           timeout=10,creationflags=flags,startupinfo=si,close_fds=True)
        else:
            p.terminate()
        return True
    except Exception:
        try:p.kill();return True
        except Exception:return False


def _convert_worker(job_id: int, inventory_ids: list[int], preset: str, target_mb: int | None):
    with db() as con:
        jr=con.execute("SELECT options_json FROM jobs WHERE id=?",(int(job_id),)).fetchone()
    try: prior=json.loads(jr["options_json"] or "{}") if jr else {}
    except Exception: prior={}
    outputs=list(prior.get("outputs") or [])
    finished_ids=set()
    for x in (prior.get("finished_ids") or []):
        try:finished_ids.add(int(x))
        except Exception:pass
    success=sum(1 for x in outputs if not x.get("error"))
    failed=sum(1 for x in outputs if x.get("error"))
    processed_bytes = 0
    try:
        with db() as con:
            rows = con.execute(
                f"SELECT * FROM inventory WHERE id IN ({','.join('?' for _ in inventory_ids)}) AND excluded=0 AND media_type='video' AND COALESCE(analysis_status,'')<>'private' AND private_path IS NULL",
                inventory_ids,
            ).fetchall()
        by_id = {int(r["id"]): r for r in rows}
        ordered = [by_id[i] for i in inventory_ids if i in by_id]
        total_bytes = sum(int(r["size_bytes"] or 0) for r in ordered)
        for r in ordered:
            if int(r["id"]) in finished_ids:
                processed_bytes += int(r["size_bytes"] or 0)
        _job_update(job_id, total=len(ordered), bytes_total=total_bytes, bytes_done=processed_bytes, stage="converting",
                    message=f"Preparing {len(ordered)} video(s)…")
        for index, row in enumerate(ordered, start=1):
            inv_id=int(row["id"])
            if inv_id in finished_ids:
                continue
            if _cancelled(job_id):
                raise RuntimeError("cancelled")
            src = _local_path(row)
            if not src:
                failed += 1
                _job_update(job_id, failed=failed, done=index, message=f"Skipped missing local file: {row['filename']}")
                continue
            size = int(row["size_bytes"] or (src.stat().st_size if src.exists() else 0))
            _job_update(job_id, current_inventory_id=int(row["id"]), current_filename=row["filename"],
                        message=f"Converting {index}/{len(ordered)} · {row['filename']}")
            def prog(pct):
                approx = processed_bytes + int(size * max(0.0, min(100.0, pct)) / 100.0)
                _job_update(job_id, bytes_done=approx,
                            message=f"Converting {index}/{len(ordered)} · {pct:.0f}% · {row['filename']}")
            while True:
                try:
                    result = convert_file(src, preset, target_mb, progress_cb=prog, cancel_cb=lambda: _cancelled(job_id), job_id=job_id)
                    outputs.append(result); success += 1
                    break
                except Exception as exc:
                    if str(exc).lower() == "cancelled":
                        raise
                    request=_consume_watchdog_request(job_id)
                    if request==1:
                        _job_update(job_id,stage="watchdog_retry",message=f"Converter stalled; process restarted automatically · {index}/{len(ordered)}",error=None)
                        continue
                    if request==2:
                        _job_update(job_id,stage="watchdog_app_restart",message="Converter stalled; restarting Archivist automatically…",error=None)
                        return
                    failed += 1
                    outputs.append({"source": str(src), "error": str(exc)[:1000]})
                    break
            finished_ids.add(inv_id)
            processed_bytes += size
            _job_update(job_id, done=len(finished_ids), success=success, failed=failed, bytes_done=processed_bytes,
                        options_json=json.dumps({"preset":preset,"target_mb":target_mb,"inventory_ids":inventory_ids,
                                                "finished_ids":sorted(finished_ids),"outputs":outputs},ensure_ascii=False))
        status = "finished" if failed == 0 else ("finished" if success else "failed")
        _job_update(job_id, status=status, stage="done", finished_at=_now(), current_inventory_id=None,
                    current_filename=None, message=f"Converted {success}; failed {failed}",
                    options_json=json.dumps({"preset": preset, "target_mb": target_mb, "inventory_ids": inventory_ids, "finished_ids": sorted(finished_ids), "outputs": outputs}, ensure_ascii=False))
    except Exception as exc:
        cancelled = str(exc).lower() == "cancelled"
        _job_update(job_id, status="cancelled" if cancelled else "failed", stage="cancelled" if cancelled else "error",
                    finished_at=_now(), error=None if cancelled else str(exc)[:1500],
                    message="Conversion cancelled" if cancelled else f"Conversion failed: {str(exc)[:300]}",
                    options_json=json.dumps({"preset": preset, "target_mb": target_mb, "inventory_ids": inventory_ids, "finished_ids": sorted(finished_ids), "outputs": outputs}, ensure_ascii=False))


def recover_convert_jobs():
    """Resume durable converter jobs after an app restart.

    New converter jobs persist inventory_ids. Legacy interrupted jobs that lack
    those ids are closed with an explicit message instead of being routed to the
    generic worker as an unknown job kind.
    """
    with db() as con:
        # Repair the exact legacy failure exposed by job #5.
        con.execute(
            "UPDATE jobs SET stage='interrupted',message='Conversion interrupted by app restart. Start it again.',"
            "error='interrupted_by_restart',finished_at=COALESCE(finished_at,?) "
            "WHERE kind='convert' AND status='failed' AND (message='Unknown job kind' OR error LIKE 'Unknown job kind convert%')",
            (_now(),),
        )
        rows=con.execute("SELECT * FROM jobs WHERE kind='convert' AND status IN ('running','queued') AND cancel_requested=0 ORDER BY id").fetchall()
        con.commit()
    resumed=0; interrupted=0
    for row in rows:
        d={k:row[k] for k in row.keys()}
        try:
            opts=json.loads(d.get("options_json") or "{}")
        except Exception:
            opts={}
        ids=[]
        for x in (opts.get("inventory_ids") or []):
            try:
                i=int(x)
            except Exception:
                continue
            if i>0 and i not in ids: ids.append(i)
        preset=str(opts.get("preset") or "")
        target_mb=opts.get("target_mb")
        if ids and preset in PRESETS:
            _job_update(int(d["id"]),status="running",stage="resuming",message="Resuming conversion after restart…",
                        started_at=d.get("started_at") or _now(),finished_at=None,error=None,worker_pid=None,watchdog_retry_requested=0)
            threading.Thread(target=_convert_worker,args=(int(d["id"]),ids,preset,target_mb),daemon=True,
                             name=f"ArchivistConvert{int(d['id'])}").start()
            resumed+=1
        else:
            _job_update(int(d["id"]),status="failed",stage="interrupted",
                        message="Conversion interrupted by app restart. Start it again.",
                        error="interrupted_by_restart",finished_at=_now())
            interrupted+=1
    return {"resumed":resumed,"interrupted":interrupted}



def _ffprobe_meta(source: Path):
    ffmpeg=_ffmpeg_exe()
    candidates=[]
    if ffmpeg:
        fp=Path(ffmpeg)
        candidates.append(fp.with_name('ffprobe.exe' if fp.suffix.lower()=='.exe' else 'ffprobe'))
    found=shutil.which('ffprobe')
    if found: candidates.append(Path(found))
    ffprobe=next((p for p in candidates if p and Path(p).exists()),None)
    duration_ms=0; width=0; height=0
    if ffprobe:
        flags,si=_flags()
        try:
            rr=subprocess.run([str(ffprobe),'-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(source)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=20,
                creationflags=flags,startupinfo=si,close_fds=True)
            if rr.returncode==0 and rr.stdout:
                data=json.loads(rr.stdout); streams=data.get('streams') or []
                if streams:
                    width=int(streams[0].get('width') or 0); height=int(streams[0].get('height') or 0)
                sec=float((data.get('format') or {}).get('duration') or 0)
                if sec>0: duration_ms=max(1,int(round(sec*1000)))
        except Exception: pass
    if (width<=0 or height<=0) and ffmpeg:
        import re
        flags,si=_flags()
        try:
            rr=subprocess.run([str(ffmpeg),'-hide_banner','-i',str(source)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',timeout=20,creationflags=flags,startupinfo=si,close_fds=True)
            txt=(rr.stderr or '')+'\n'+(rr.stdout or '')
            m=re.search(r'Video:[^\n]*?[, ](\d{2,5})x(\d{2,5})(?:[ ,\[])',txt,re.I)
            if m:
                width=int(m.group(1));height=int(m.group(2))
        except Exception: pass
    if duration_ms<=0:
        try:
            sec=float(probe_duration(source) or 0)
            if sec>0: duration_ms=max(1,int(round(sec*1000)))
        except Exception: pass
    return {'duration_ms':duration_ms,'width':width,'height':height}

def probe_local_media_meta(inventory_ids):
    ids=[]; seen=set()
    for x in inventory_ids:
        try:i=int(x)
        except Exception:continue
        if i>0 and i not in seen: ids.append(i);seen.add(i)
    if not ids:return {}
    with db() as con:
        rows=con.execute(f"SELECT id,duration_ms,width,height,path,staging_path,archive_path,source_kind FROM inventory WHERE id IN ({','.join('?' for _ in ids)}) AND excluded=0 AND media_type='video'",ids).fetchall()
    out={}; updates=[]
    for row in rows:
        iid=int(row['id']); ms=int(row['duration_ms'] or 0); w=int(row['width'] or 0); h=int(row['height'] or 0)
        if ms<=0 or w<=0 or h<=0:
            local=_local_path(row)
            if local and local.exists():
                meta=_ffprobe_meta(local)
                if ms<=0: ms=int(meta.get('duration_ms') or 0)
                if w<=0: w=int(meta.get('width') or 0)
                if h<=0: h=int(meta.get('height') or 0)
                updates.append((ms,w,h,iid))
        out[str(iid)]={'duration_ms':ms,'width':w,'height':h}
    if updates:
        with db() as con:
            con.executemany("UPDATE inventory SET duration_ms=?,width=?,height=? WHERE id=?",updates); con.commit()
    return out

def probe_local_durations(inventory_ids):
    return {k:int(v.get('duration_ms') or 0) for k,v in probe_local_media_meta(inventory_ids).items()}

def start_convert_job(inventory_ids, preset="share_1080p", target_mb=None):
    ids = []
    seen = set()
    for x in inventory_ids:
        try:
            i = int(x)
        except Exception:
            continue
        if i > 0 and i not in seen:
            ids.append(i); seen.add(i)
    if not ids:
        raise ValueError("Select at least one video")
    if len(ids) > 50:
        raise ValueError("Convert up to 50 videos at once")
    if preset not in PRESETS:
        raise ValueError("Unknown preset")
    target_mb = int(target_mb) if target_mb else None
    if target_mb is not None and not (50 <= target_mb <= 100000):
        raise ValueError("Target size must be between 50 MB and 100000 MB")
    with db() as con:
        ok_ids = {int(r["id"]) for r in con.execute(
            f"SELECT id FROM inventory WHERE id IN ({','.join('?' for _ in ids)}) AND excluded=0 AND media_type='video' "
            "AND COALESCE(analysis_status,'')<>'private' AND private_path IS NULL AND rejected_path IS NULL", ids).fetchall()}
        ids = [i for i in ids if i in ok_ids]
        if not ids:
            raise ValueError("None of the selected videos can be converted (private, rejected or removed)")
        busy = con.execute("SELECT id,kind FROM jobs WHERE status IN ('running','queued') ORDER BY id LIMIT 1").fetchone()
        if busy:
            raise RuntimeError(f"Job #{busy['id']} ({busy['kind']}) is already running")
        cur = con.execute(
            "INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("convert", "running", _now(), _now(), "starting", "Starting converter…", len(ids), 0, 0, 0, 0, 0,
             json.dumps({"preset": preset, "target_mb": target_mb, "inventory_ids": ids, "finished_ids": [], "outputs": []}))
        )
        job_id = int(cur.lastrowid)
        con.commit()
    threading.Thread(target=_convert_worker, args=(job_id, ids, preset, target_mb), daemon=True, name=f"ArchivistConvert{job_id}").start()
    return job_id


def convert_job_snapshot(job_id=None):
    with db() as con:
        if job_id:
            r = con.execute("SELECT * FROM jobs WHERE id=? AND kind='convert'", (int(job_id),)).fetchone()
        else:
            r = con.execute("SELECT * FROM jobs WHERE kind='convert' ORDER BY id DESC LIMIT 1").fetchone()
    if not r:
        return None
    d = {k: r[k] for k in r.keys()}
    try:
        d["options"] = json.loads(d.get("options_json") or "{}")
    except Exception:
        d["options"] = {}
    total_bytes = int(d.get("bytes_total") or 0)
    done_bytes = int(d.get("bytes_done") or 0)
    d["percent"] = round(done_bytes * 100.0 / total_bytes, 1) if total_bytes else (100.0 if d.get("status") == "finished" else 0.0)
    return d
