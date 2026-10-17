from __future__ import annotations

import itertools
import json
import os
import queue
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from . import android
from .config import HOME, LOGS, PRIVATE, REJECTED, STAGING, STORYBOARDS, THUMBS, load_config
from .db import create_job, db, init_db, now_iso, recover_jobs, upsert_inventory
from .media import analyze_combined, copy_file, make_storyboard, make_thumbnail, media_type_for, probe_rights_flags, sha256_file, walk_media
from .media_brain import analyze_video_into_clips, purge_media_brain


def log(msg: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    path = LOGS / "archivist.log"
    try:
        # Keep desktop logs bounded. Rotate before appending once the file exceeds 5 MB.
        if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
            for i in range(3, 0, -1):
                src = LOGS / ("archivist.log" if i == 1 else f"archivist.log.{i-1}")
                dst = LOGS / f"archivist.log.{i}"
                if src.exists():
                    try:
                        if dst.exists(): dst.unlink()
                        src.replace(dst)
                    except Exception:
                        pass
        line = f"[{now_iso()}] {msg}"
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class RuntimeState:
    def __init__(self):
        self.lock = threading.Lock()
        self.discovery = {"running": False, "message": "Idle", "found": 0, "current_source": "", "per_source": {}, "errors": 0}

    def snapshot(self):
        with self.lock:
            return {"discovery": json.loads(json.dumps(self.discovery))}


STATE = RuntimeState()
DISCOVERY_LOCK = threading.Lock()
THUMB_LOCK = threading.Semaphore(1)
THUMB_QUEUE: queue.PriorityQueue[tuple[int,int,int]] = queue.PriorityQueue()
THUMB_PENDING: dict[int,int] = {}
THUMB_SEQ = itertools.count()
THUMB_PENDING_LOCK = threading.Lock()
THUMB_WORKER_STARTED = False
THUMB_WORKER_LOCK = threading.Lock()
STORYBOARD_LOCK = threading.Semaphore(1)
STORYBOARD_QUEUE: queue.PriorityQueue[tuple[int,int,int]] = queue.PriorityQueue()
STORYBOARD_PENDING: dict[int,int] = {}
STORYBOARD_SEQ = itertools.count()
STORYBOARD_PENDING_LOCK = threading.Lock()
STORYBOARD_WORKER_STARTED = False
STORYBOARD_WORKER_LOCK = threading.Lock()
# Bound speculative preview work while foreground ingest/analyze pauses workers.
# Negative priorities are explicit browser/item requests and get a larger budget.
THUMB_PENDING_SOFT_LIMIT = 768
THUMB_PENDING_HARD_LIMIT = 2048
STORYBOARD_PENDING_SOFT_LIMIT = 384
STORYBOARD_PENDING_HARD_LIMIT = 1024
JOB_WORKER_STARTED = False
JOB_WORKER_LOCK = threading.Lock()
STOP_EVENT = threading.Event()


def windows_drives():
    out = []
    if os.name != "nt":
        return out
    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                root = f"{chr(65+i)}:\\"
                dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
                kind = {2: "removable", 3: "fixed", 4: "network", 5: "cdrom", 6: "ramdisk"}.get(dtype, "other")
                out.append({"root": root, "kind": kind})
    except Exception:
        pass
    return out


def _drive_of(path) -> str:
    try:
        d = os.path.splitdrive(os.path.expandvars(str(path or "")))[0]
        return (d.rstrip("\\/") + "\\").lower() if d else ""
    except Exception:
        return ""


def configured_sources(cfg):
    """The places discovery walks. A folder the user added that is on a card or USB stick is a removable source (its
    videos are copied in, never used in place: the card goes away), and that card is then not walked a second time as
    a whole - the same file seen as "fixed" and "removable" in turn was once reported imported without a copy."""
    removable = {d["root"].lower() for d in windows_drives() if d["kind"] == "removable"}
    sources = []
    for s in cfg.get("sources", []):
        if not s.get("enabled", True):
            continue
        kind = s.get("kind") or "fixed"
        if kind == "fixed" and _drive_of(s.get("path")) in removable:
            kind = "removable"
        sources.append({"path": s.get("path"), "label": s.get("label") or s.get("path"), "kind": kind})
    if cfg.get("auto_removable", True):
        on_drive = {_drive_of(s.get("path")) for s in sources}
        for d in windows_drives():
            if d["kind"] == "removable" and d["root"].lower() not in on_drive:
                sources.append({"path": d["root"], "label": f"SD/USB {d['root'][0]}:", "kind": "removable"})
    return sources


def _effective_kind(row: dict) -> str:
    """A "fixed" (used in place) file that is on a card or USB stick is imported like a card's file: copied in. Used
    in place, it would be gone with the stick - and once it was reported imported with no copy made."""
    kind = str(row.get("source_kind") or "")
    if kind == "fixed" and os.name == "nt":
        try:
            if _drive_of(row.get("path")) in {d["root"].lower() for d in windows_drives() if d["kind"] == "removable"}:
                return "removable"
        except Exception:
            pass
    return kind


def _forget_old_content(ids: list[int]) -> None:
    """A file in a folder source changed (other size or time). Its picture is made again. When its length changed too
    it is another video: the moments (and crops) made from the old one go and its length is measured again. Same length
    (tags edited by another program): moments and hand-made crops stay."""
    from .media import probe_duration
    other = []
    for i in ids:
        try:
            with db() as con:
                r = con.execute("SELECT path,duration_ms,media_type FROM inventory WHERE id=?", (int(i),)).fetchone()
                con.execute("UPDATE inventory SET preview_status='pending',preview_path=NULL,storyboard_status='pending' WHERE id=?", (int(i),))
                con.commit()
            (THUMBS / f"{int(i)}.jpg").unlink(missing_ok=True)
            if not r or r["media_type"] != "video":
                continue
            new_s = probe_duration(Path(r["path"])) if r["path"] else None
            if not r["duration_ms"] or not new_s or abs(float(new_s) * 1000 - float(r["duration_ms"])) > 500:
                other.append(int(i))
        except Exception as exc:
            log(f"discovery: changed file {i}: {exc}")
    if other:
        try:
            from .media_brain import purge_media_brain
            purge_media_brain(other)
            with db() as con:
                con.executemany("UPDATE inventory SET duration_ms=NULL,width=NULL,height=NULL WHERE id=?", [(x,) for x in other])
                con.commit()
        except Exception as exc:
            log(f"discovery: old moments of replaced files not removed: {exc}")


def transfers_pending() -> bool:
    """A queued or running import still has to copy a file from a card or a phone: "safe to disconnect" must not be
    shown (by any job) until it has."""
    try:
        with db() as con:
            return con.execute(
                "SELECT 1 FROM job_items ji JOIN jobs j ON j.id=ji.job_id JOIN inventory i ON i.id=ji.inventory_id "
                "WHERE j.status IN ('queued','running') AND j.kind IN ('import','import_analyze') "
                "AND ji.status NOT IN ('done','skipped') AND i.source_kind IN ('removable','android') "
                "AND i.staging_path IS NULL AND i.archive_path IS NULL LIMIT 1").fetchone() is not None
    except Exception:
        return True


def _foreground_busy() -> bool:
    try:
        with db() as con:
            return con.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running') AND kind IN ('import','import_analyze','analyze','media_brain','archive','private','reject','convert') LIMIT 1").fetchone() is not None
    except Exception:
        return False


def run_discovery():
    if _foreground_busy():
        with STATE.lock:
            STATE.discovery.update({"running": False, "message": "Discovery paused while a foreground job is running", "current_source": ""})
        return
    if not DISCOVERY_LOCK.acquire(blocking=False):
        return
    try:
        init_db(); cfg = load_config(); started = now_iso()
        with STATE.lock:
            STATE.discovery = {"running": True, "message": "Discovering", "found": 0, "current_source": "", "per_source": {}, "errors": 0, "started": started}
        with db() as con:
            if cfg.get("android", {}).get("enabled", True):
                adb = android.find_adb()
                if not adb:
                    with STATE.lock: STATE.discovery["per_source"]["Android"] = {"count": 0, "size": 0, "status": "ADB not installed"}
                else:
                    devices, err = android.adb_devices(adb, refresh=True)
                    if err: log(f"ADB device check: {err}")
                    if not devices:
                        with STATE.lock: STATE.discovery["per_source"]["Android"] = {"count": 0, "size": 0, "status": "not connected"}
                    for dev in devices:
                        label = dev.get("model") or f"Android {dev['serial']}"
                        serial = dev["serial"]
                        if (dev.get("state") or "unknown") != "device":
                            with STATE.lock: STATE.discovery["per_source"][label] = {"count": 0, "size": 0, "status": dev.get("state") or "unknown"}
                            continue
                        with STATE.lock:
                            STATE.discovery["current_source"] = label
                            STATE.discovery["per_source"][label] = {"count": 0, "size": 0, "status": "querying MediaStore"}
                        items, errs = android.list_media(adb, serial)
                        for er in errs: log(f"Android {label}: {er}")
                        count = total = 0
                        for item in items:
                            source_key = f"android:{serial}:{item['media_type']}:{item['media_id']}"
                            fp = f"{source_key}|{item.get('size_bytes') or ''}|{item.get('mtime') or ''}"
                            row = {**item, "source_key": source_key, "source_kind": "android", "source_id": serial, "source_label": label, "source_fingerprint": fp}
                            upsert_inventory(con, row)
                            count += 1; total += int(item.get("size_bytes") or 0)
                            if count % 250 == 0:
                                con.commit()
                                with STATE.lock: STATE.discovery["per_source"][label] = {"count": count, "size": total, "status": "connected"}
                        con.commit()
                        with STATE.lock:
                            STATE.discovery["found"] += count
                            STATE.discovery["per_source"][label] = {"count": count, "size": total, "status": "connected"}
                        # Never delete locally-imported history when a phone is disconnected later. Only stale, never-imported catalog rows are removed.
                        if not errs:
                            con.execute("DELETE FROM inventory WHERE source_kind='android' AND source_id=? AND last_seen_at < ? AND staging_path IS NULL AND archive_path IS NULL AND private_path IS NULL AND rejected_path IS NULL AND COALESCE(work_selected,0)=0", (serial, started))
                        con.commit()

            filt = cfg.get("filters", {})
            for src in configured_sources(cfg):
                p = Path(os.path.expandvars(str(src.get("path") or ""))).expanduser()
                label = src.get("label") or str(p); kind = src.get("kind") or "fixed"
                if not p.exists():
                    with STATE.lock:
                        STATE.discovery["errors"] += 1; STATE.discovery["per_source"][label] = {"count": 0, "size": 0, "status": "missing"}
                    continue
                with STATE.lock:
                    STATE.discovery["current_source"] = label; STATE.discovery["per_source"][label] = {"count": 0, "size": 0, "status": "scanning"}
                count = total = 0
                walk_errors: list = []
                last_commit = time.monotonic()
                batch: list = []

                def flush():
                    # rows are written in one short transaction: no write lock is held while the walk waits for a slow
                    # folder listing (a NAS, a huge folder, a card that hangs) - "Add to Library" never waits for it
                    replaced = [x for x in (upsert_inventory(con, r_) for r_ in batch) if x]
                    con.commit(); batch.clear()
                    if replaced:      # a video replaced in its folder: its moments, crops and picture were of the old one
                        _forget_old_content(replaced)
                    with STATE.lock:
                        STATE.discovery["per_source"][label] = {"count": count, "size": total, "status": "scanning"}
                for f in walk_media(p, bool(filt.get("ignore_noise", True)), int(filt.get("min_image_bytes", 0)), int(filt.get("min_video_bytes", 0)), errors=walk_errors):
                    try: st = f.stat()
                    except Exception: continue
                    mt = media_type_for(f); source_key = "local:" + os.path.normcase(os.path.abspath(str(f)))
                    batch.append({"source_key": source_key, "source_kind": kind, "source_id": str(p), "source_label": label, "path": str(f), "filename": f.name,
                                  "ext": f.suffix.lower(), "media_type": mt, "mime_type": None, "size_bytes": st.st_size, "mtime": st.st_mtime,
                                  "date_taken": None, "duration_ms": None, "width": None, "height": None,
                                  "source_fingerprint": f"{source_key}|{st.st_size}|{st.st_mtime}"})
                    count += 1; total += st.st_size
                    if len(batch) >= 250 or time.monotonic() - last_commit > 1.0:
                        flush(); last_commit = time.monotonic()
                flush()
                with STATE.lock:
                    STATE.discovery["found"] += count; STATE.discovery["per_source"][label] = {"count": count, "size": total, "status": "done"}
                # Prune unseen rows only after a complete, error-free walk, and never Library items
                # (fixed-folder Library items have no local copy path because they stay in place).
                if not walk_errors:
                    con.execute("DELETE FROM inventory WHERE source_kind IN ('fixed','removable') AND source_id=? AND last_seen_at < ? AND staging_path IS NULL AND archive_path IS NULL AND private_path IS NULL AND rejected_path IS NULL AND COALESCE(work_selected,0)=0", (str(p), started))
                else:
                    log(f"discovery {label}: {len(walk_errors)} unreadable folder(s); keeping unseen rows")
                con.commit()
        with STATE.lock: STATE.discovery.update({"running": False, "message": "Discovery finished", "current_source": "", "finished": now_iso()})
    except Exception as exc:
        log(f"Discovery failed: {exc}")
        with STATE.lock: STATE.discovery.update({"running": False, "message": f"Discovery error: {exc}", "current_source": "", "finished": now_iso()})
    finally:
        DISCOVERY_LOCK.release()


def start_discovery() -> bool:
    if DISCOVERY_LOCK.locked() or _foreground_busy(): return False
    threading.Thread(target=run_discovery, daemon=True, name="ArchivistDiscovery").start()
    return True


def _row_dict(r): return {k: r[k] for k in r.keys()}

_WIN_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", *(f"COM{i}" for i in "0123456789¹²³"),
                       *(f"LPT{i}" for i in "0123456789¹²³")}


def re_safe(s: str) -> str:
    """A folder / file name for Staging, the archive, Private and Rejected that keeps the user's own letters
    (Cyrillic, accents, CJK): only what Windows does not allow in a name is replaced. It used to keep ASCII only,
    so 'Отпуск на даче.mp4' from the source 'Мои видео' was archived as '_ _ _/_ _ _.mp4'."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(s)).strip(" .")
    units = lambda t: len(t.encode("utf-16-le")) // 2      # Windows counts path length in UTF-16 units
    if units(s) > 90:   # folder + name stay well below the Windows path limit (260) with long paths off
        suffix = Path(s).suffix if len(Path(s).suffix) <= 10 else ""
        stem = s[: len(s) - len(suffix)] if suffix else s
        while stem and units(stem) + units(suffix) > 90:
            stem = stem[:-1]
        s = stem.rstrip(" .") + suffix
    s = s.strip(" .")
    if not s or s == Path(s).suffix:
        return "Source" if not s else "Source" + s
    if s.split(".")[0].strip().upper() in _WIN_RESERVED_NAMES:
        s = "_" + s
    return s


def cached_thumbnail(inv_id: int) -> Path | None:
    with db() as con:
        row = con.execute("SELECT preview_path FROM inventory WHERE id=? AND excluded=0", (inv_id,)).fetchone()
    if not row: return None
    p = row["preview_path"]
    if p and Path(p).exists(): return Path(p)
    dest = THUMBS / f"{inv_id}.jpg"
    return dest if dest.exists() else None


def ensure_thumbnail(inv_id: int) -> Path | None:
    with db() as con:
        rr = con.execute("SELECT * FROM inventory WHERE id=? AND excluded=0", (inv_id,)).fetchone()
    if not rr: return None
    item = _row_dict(rr)
    cached = cached_thumbnail(inv_id)
    if cached: return cached
    dest = THUMBS / f"{inv_id}.jpg"; ok = False
    with THUMB_LOCK:
        local = item.get("staging_path") or item.get("archive_path") or item.get("private_path")
        if local and Path(local).exists(): ok = make_thumbnail(Path(local), item["media_type"], dest)
        elif item["source_kind"] == "android":
            adb = android.find_adb(); devices, _ = android.adb_devices(adb) if adb else ([], None)
            if adb and any(d["serial"] == item["source_id"] and d["state"] == "device" for d in devices):
                ok = android.fetch_thumbnail(adb, item["source_id"], item, dest)
        else:
            p = Path(item.get("path") or "")
            if p.exists(): ok = make_thumbnail(p, item["media_type"], dest)
    with db() as con:
        con.execute("UPDATE inventory SET preview_status=?,preview_path=?,preview_attempted_at=?,preview_error=? WHERE id=?",
                    ("ready" if ok else "unavailable", str(dest) if ok else None, now_iso(), None if ok else "preview_unavailable", inv_id)); con.commit()
    return dest if ok else None


def _admit_preview_work(pending: dict[int,int], pending_lock: threading.Lock,
                        work_queue: queue.PriorityQueue, seq_counter,
                        inv_id: int, priority: int, soft_limit: int, hard_limit: int) -> bool:
    with pending_lock:
        current = pending.get(inv_id)
        if current is not None and current <= priority:
            return False
        if current is None:
            limit = hard_limit if priority < 0 else soft_limit
            if len(pending) >= limit:
                if priority < 0:
                    # Explicit current-item work may displace a lower-priority prefetch.
                    worse = [(p, iid) for iid, p in pending.items() if p > priority]
                    if not worse:
                        return False
                    _worst_priority, worst_id = max(worse)
                    pending.pop(worst_id, None)
                else:
                    return False
        pending[inv_id] = priority
        seq = next(seq_counter)
    work_queue.put((priority, seq, inv_id))
    return True


def _thumbnail_worker():
    while not STOP_EVENT.is_set():
        try:
            priority, _seq, inv_id = THUMB_QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            # A preview can be promoted after it was queued (for example when the
            # user opens the page that was being prefetched). Stale lower-priority
            # queue entries are ignored instead of doing the same work twice.
            with THUMB_PENDING_LOCK:
                best = THUMB_PENDING.get(inv_id)
            if best is None or priority != best:
                continue
            # Foreground ingest gets priority over previews.
            while active_foreground_job() and not STOP_EVENT.is_set():
                time.sleep(0.5)
            if not STOP_EVENT.is_set():
                ensure_thumbnail(inv_id)
        except Exception as exc:
            log(f"thumbnail {inv_id}: {exc}")
        finally:
            with THUMB_PENDING_LOCK:
                if THUMB_PENDING.get(inv_id) == priority:
                    THUMB_PENDING.pop(inv_id, None)
            THUMB_QUEUE.task_done()


def queue_thumbnail(inv_id: int, priority: int = 10) -> None:
    global THUMB_WORKER_STARTED
    inv_id = int(inv_id); priority = int(priority)
    if cached_thumbnail(inv_id):
        return
    # A missing preview must not trigger an ADB attempt on every browser refresh.
    # Back off for five minutes after an unavailable result, then allow a retry.
    try:
        with db() as con:
            r = con.execute("SELECT preview_status,preview_attempted_at,source_kind,path,staging_path,archive_path,private_path FROM inventory WHERE id=? AND excluded=0", (inv_id,)).fetchone()
        if not r:
            return
        if r["preview_status"] == "unavailable" and r["preview_attempted_at"]:
            try:
                has_local=bool((r["staging_path"] and Path(r["staging_path"]).exists()) or (r["archive_path"] and Path(r["archive_path"]).exists()) or (r["private_path"] and Path(r["private_path"]).exists()) or (r["source_kind"]=="fixed" and r["path"] and Path(r["path"]).exists()))
                backoff=30 if has_local else 300
                if (datetime.now() - datetime.fromisoformat(r["preview_attempted_at"])).total_seconds() < backoff:
                    return
            except Exception:
                pass
    except Exception:
        pass
    admitted = _admit_preview_work(
        THUMB_PENDING, THUMB_PENDING_LOCK, THUMB_QUEUE, THUMB_SEQ,
        inv_id, priority, THUMB_PENDING_SOFT_LIMIT, THUMB_PENDING_HARD_LIMIT
    )
    if not admitted:
        return
    with THUMB_WORKER_LOCK:
        if not THUMB_WORKER_STARTED:
            threading.Thread(target=_thumbnail_worker, daemon=True, name="ArchivistThumbnailWorker").start(); THUMB_WORKER_STARTED = True



def _storyboard_dir(inv_id: int) -> Path:
    return STORYBOARDS / str(int(inv_id))


def storyboard_info(inv_id: int) -> dict | None:
    folder = _storyboard_dir(inv_id)
    meta_path = folder / "meta.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        frames = []
        for f in meta.get("frames") or []:
            fp = folder / str(f.get("file") or "")
            if fp.exists():
                frames.append({"index": int(f.get("index", len(frames))), "time": float(f.get("time", 0)), "path": fp})
        if not frames:
            return None
        return {**meta, "frames": frames}
    except Exception:
        return None



def cached_storyboard(inv_id: int) -> dict | None:
    info = storyboard_info(inv_id)
    if not info:
        return None
    try:
        with db() as con:
            row = con.execute("SELECT source_fingerprint FROM inventory WHERE id=? AND excluded=0", (int(inv_id),)).fetchone()
        if not row:
            return None
        current = row["source_fingerprint"] or ""
        stored = info.get("fingerprint") or ""
        if stored and current and stored != current:
            return None

        # v2 storyboards are complete, fixed-slot previews. Old partial v1 caches are
        # deliberately regenerated in the background the next time Library sees them.
        cfg = load_config()
        expected = max(4, min(12, int(cfg.get("analysis", {}).get("storyboard_frames", 8) or 8)))
        if int(info.get("version") or 0) < 2:
            return None
        if int(info.get("target_frames") or 0) != expected:
            return None
        if len(info.get("frames") or []) != expected:
            return None
    except Exception:
        return None
    return info


def ensure_storyboard(inv_id: int) -> dict | None:
    inv_id = int(inv_id)
    with db() as con:
        rr = con.execute("SELECT * FROM inventory WHERE id=? AND excluded=0", (inv_id,)).fetchone()
    if not rr or rr["media_type"] != "video":
        return None
    row = _row_dict(rr)
    cached = cached_storyboard(inv_id)
    if cached:
        return cached
    local = _existing_local_path(row)
    if not local or not local.exists():
        return None
    cfg = load_config()
    count = int(cfg.get("analysis", {}).get("storyboard_frames", 8) or 8)
    folder = _storyboard_dir(inv_id)
    ok = None
    err = None
    with STORYBOARD_LOCK:
        try:
            ok = make_storyboard(local, folder, frames=count, fingerprint=row.get("source_fingerprint") or "")
            if ok:
                best = int(ok.get("best_index") or 0)
                frames = ok.get("frames") or []
                if 0 <= best < len(frames):
                    src = folder / frames[best]["file"]
                    if src.exists():
                        dest = THUMBS / f"{inv_id}.jpg"
                        tmp = THUMBS / f"{inv_id}.jpg.storypart"
                        shutil.copy2(src, tmp)
                        tmp.replace(dest)
        except Exception as exc:
            err = str(exc)
            ok = None
    with db() as con:
        con.execute(
            "UPDATE inventory SET storyboard_status=?,storyboard_frames=?,storyboard_best_index=?,storyboard_attempted_at=?,storyboard_error=?,preview_status=CASE WHEN ? THEN 'ready' ELSE preview_status END,preview_path=CASE WHEN ? THEN ? ELSE preview_path END WHERE id=?",
            ("ready" if ok else "unavailable", len(ok.get("frames") or []) if ok else 0, int(ok.get("best_index") or 0) if ok else None, now_iso(), err or (None if ok else "storyboard_unavailable"), 1 if ok else 0, 1 if ok else 0, str(THUMBS / f"{inv_id}.jpg"), inv_id),
        )
        con.commit()
    return cached_storyboard(inv_id) if ok else None


def _storyboard_worker():
    while not STOP_EVENT.is_set():
        try:
            priority, _seq, inv_id = STORYBOARD_QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            with STORYBOARD_PENDING_LOCK:
                best = STORYBOARD_PENDING.get(inv_id)
            if best is None or priority != best:
                continue
            while active_foreground_job() and not STOP_EVENT.is_set():
                time.sleep(0.5)
            if not STOP_EVENT.is_set():
                ensure_storyboard(inv_id)
        except Exception as exc:
            log(f"storyboard {inv_id}: {exc}")
        finally:
            with STORYBOARD_PENDING_LOCK:
                if STORYBOARD_PENDING.get(inv_id) == priority:
                    STORYBOARD_PENDING.pop(inv_id, None)
            STORYBOARD_QUEUE.task_done()


def queue_storyboard(inv_id: int, priority: int = 30) -> None:
    global STORYBOARD_WORKER_STARTED
    inv_id = int(inv_id); priority = int(priority)
    if cached_storyboard(inv_id):
        return
    try:
        with db() as con:
            r = con.execute("SELECT media_type,source_kind,path,staging_path,archive_path,private_path,rejected_path,storyboard_status,storyboard_attempted_at FROM inventory WHERE id=? AND excluded=0", (inv_id,)).fetchone()
        if not r or r["media_type"] != "video":
            return
        has_local = bool((r["staging_path"] and Path(r["staging_path"]).exists()) or (r["archive_path"] and Path(r["archive_path"]).exists()) or (r["private_path"] and Path(r["private_path"]).exists()) or (r["rejected_path"] and Path(r["rejected_path"]).exists()) or (r["source_kind"] == "fixed" and r["path"] and Path(r["path"]).exists()))
        if not has_local:
            return
        if r["storyboard_status"] == "unavailable" and r["storyboard_attempted_at"]:
            try:
                if (datetime.now() - datetime.fromisoformat(r["storyboard_attempted_at"])).total_seconds() < 300:
                    return
            except Exception:
                pass
    except Exception:
        return
    admitted = _admit_preview_work(
        STORYBOARD_PENDING, STORYBOARD_PENDING_LOCK, STORYBOARD_QUEUE, STORYBOARD_SEQ,
        inv_id, priority, STORYBOARD_PENDING_SOFT_LIMIT, STORYBOARD_PENDING_HARD_LIMIT
    )
    if not admitted:
        return
    with STORYBOARD_WORKER_LOCK:
        if not STORYBOARD_WORKER_STARTED:
            threading.Thread(target=_storyboard_worker, daemon=True, name="ArchivistStoryboardWorker").start()
            STORYBOARD_WORKER_STARTED = True

def _staging_dest(row: dict) -> Path:
    label = re_safe(row.get("source_label") or "Source")
    folder = STAGING / label; folder.mkdir(parents=True, exist_ok=True)
    name = re_safe(row.get("filename") or f"media_{row['id']}{row.get('ext') or ''}")
    # Inventory id makes the target deterministic and prevents same-name/same-size
    # files from being mistaken for an existing successful import.
    return folder / f"{int(row['id']):08d}__{name}"


def _free_name(folder: Path, name: str, tags: list[str]) -> Path:
    """The first name not taken in <folder>: name, then name_<tag> for each tag, then name_<last tag>_2, _3, ...
    (two cards' VID_0001.mp4 never share one Private / Rejected copy - one would be overwritten)."""
    base = Path(name)
    cands = [folder / name] + [folder / f"{base.stem}_{t}{base.suffix}" for t in tags]
    for c in cands:
        if not c.exists():
            return c
    last = cands[-1]
    n = 2
    while (folder / f"{last.stem}_{n}{base.suffix}").exists():
        n += 1
    return folder / f"{last.stem}_{n}{base.suffix}"


def _no_overwrite(dest: Path, size: int, sha: str) -> None:
    """Never replace a different file that has the destination's name (an identical one is fine)."""
    if dest.exists():
        try:
            if dest.stat().st_size == size and sha256_file(dest) == sha:
                return
        except OSError:
            pass
        raise RuntimeError("A different file already has that name: " + str(dest))


def _private_dest(row: dict, src: Path, sha: str) -> Path:
    folder = PRIVATE / re_safe(row.get("source_label") or "Source"); folder.mkdir(parents=True, exist_ok=True)
    return _free_name(folder, re_safe(row.get("filename") or src.name), [str(sha)[:8], f"{str(sha)[:8]}_{int(row['id'])}"])


def _rejected_dest(row: dict, src: Path) -> Path:
    folder = REJECTED / re_safe(row.get("source_label") or "Source"); folder.mkdir(parents=True, exist_ok=True)
    return _free_name(folder, re_safe(row.get("filename") or src.name), [str(int(row['id']))])


def _same_volume(a: Path, b: Path) -> bool:
    try:
        return os.path.splitdrive(str(a.resolve()))[0].lower() == os.path.splitdrive(str(b.resolve()))[0].lower() if os.name == "nt" else a.stat().st_dev == b.parent.stat().st_dev
    except Exception:
        return False


def _verified_move(src: Path, dest: Path, sha: str | None = None) -> None:
    """Move without risking the only local copy on a cross-volume transfer."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected_size = src.stat().st_size
    expected_sha = sha or sha256_file(src)
    if dest.resolve() != src.resolve():
        _no_overwrite(dest, expected_size, expected_sha)
    if _same_volume(src, dest):
        # Same-volume rename is atomic; content bytes are not rewritten.
        src.replace(dest)
        if dest.stat().st_size != expected_size:
            raise RuntimeError("Move verification failed: size mismatch")
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)
    copy_file(src, tmp)
    if tmp.stat().st_size != expected_size or sha256_file(tmp) != expected_sha:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Cross-volume move verification failed")
    tmp.replace(dest)
    src.unlink()


def _archive_dest(root: Path, row: dict, src: Path, sha: str) -> Path:
    ts = row.get("date_taken") or row.get("mtime") or time.time()
    try: dt = datetime.fromtimestamp(float(ts))
    except Exception: dt = datetime.now()
    folder = root / f"{dt.year:04d}" / f"{dt.month:02d}" / f"{dt.day:02d}" / re_safe(row.get("source_label") or "Source")
    folder.mkdir(parents=True, exist_ok=True)
    name = re_safe(row.get("filename") or src.name)
    dest = folder / name
    if not dest.exists() or dest.resolve() == src.resolve():
        return dest
    try:
        if dest.stat().st_size == src.stat().st_size and sha256_file(dest) == sha:
            return dest
    except Exception:
        pass
    candidate = folder / f"{dest.stem}_{sha[:8]}{dest.suffix}"
    if not candidate.exists():
        return candidate
    try:
        if candidate.stat().st_size == src.stat().st_size and sha256_file(candidate) == sha:
            return candidate
    except Exception:
        pass
    return _free_name(folder, name, [f"{sha[:8]}_{int(row['id'])}"])


def _job_update(job_id: int, **fields):
    if not fields:
        return
    ts=now_iso()
    fields.setdefault("heartbeat_at",ts)
    fields.setdefault("progress_at",ts)
    with db() as con:
        con.execute(f"UPDATE jobs SET {','.join(k+'=?' for k in fields)} WHERE id=?", [*fields.values(), job_id])
        con.commit()


def _item_update(item_id: int, **fields):
    if not fields:
        return
    ts=now_iso()
    with db() as con:
        con.execute(f"UPDATE job_items SET {','.join(k+'=?' for k in fields)} WHERE id=?", [*fields.values(), item_id])
        r=con.execute("SELECT job_id FROM job_items WHERE id=?",(item_id,)).fetchone()
        if r: con.execute("UPDATE jobs SET heartbeat_at=?,progress_at=? WHERE id=?",(ts,ts,int(r["job_id"])))
        con.commit()


def _cancel_requested(job_id: int) -> bool:
    with db() as con:
        r = con.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
    return bool(r and r["cancel_requested"])


def cancel_job(job_id: int) -> bool:
    with db() as con:
        r = con.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not r or r["status"] not in ("queued", "running"):
            return False
        if r["status"] == "queued":
            # not started yet: cancelled at once (the worker only takes jobs without a cancel request, so a queued
            # job would otherwise stay "queued" forever and block previews, discovery and Convert)
            now = now_iso()
            con.execute("UPDATE job_items SET status='skipped',phase='cancelled',error='cancelled',finished_at=? "
                        "WHERE job_id=? AND status IN ('queued','running')", (now, job_id))
            con.execute("UPDATE jobs SET cancel_requested=1,status='cancelled',stage='done',message='Cancelled',finished_at=? "
                        "WHERE id=? AND status='queued'", (now, job_id))
            con.commit()
            return True
        con.execute("UPDATE jobs SET cancel_requested=1,message='Cancelling after current operation…' WHERE id=?", (job_id,))
        con.commit()
    return True


def _reads_sources_in_place(job_id: int) -> bool:
    """Some items of this job are used where they are (a folder added on Import, files not copied): their disk must
    stay connected, whatever the job does."""
    try:
        with db() as con:
            return con.execute(
                "SELECT 1 FROM job_items ji JOIN inventory i ON i.id=ji.inventory_id WHERE ji.job_id=? AND i.source_kind='fixed' "
                "AND i.staging_path IS NULL AND i.archive_path IS NULL LIMIT 1", (job_id,)).fetchone() is not None
    except Exception:
        return True


def _check_free_space(expected: int):
    cfg = load_config()
    free = shutil.disk_usage(STAGING).free
    reserve = int(float(cfg.get("ingest", {}).get("min_free_gb", 10)) * (1024**3))
    if free - expected < reserve:
        raise RuntimeError(f"Not enough free space: need {expected/(1024**3):.1f} GB plus {reserve/(1024**3):.0f} GB reserve")


def _copy_local_with_progress(src: Path, tmp: Path, progress_cb, cancel_cb=None):
    tmp.parent.mkdir(parents=True, exist_ok=True)
    copied = 0
    with src.open("rb") as fi, tmp.open("wb") as fo:
        while True:
            if cancel_cb and cancel_cb():
                raise RuntimeError("cancelled")
            chunk = fi.read(8 * 1024 * 1024)
            if not chunk:
                break
            fo.write(chunk)
            copied += len(chunk)
            progress_cb(copied)
        fo.flush()
        os.fsync(fo.fileno())
    shutil.copystat(src, tmp, follow_symlinks=True)


def _job_item_bytes(item_id: int) -> int:
    with db() as con:
        r = con.execute("SELECT bytes_done FROM job_items WHERE id=?", (item_id,)).fetchone()
        return int(r["bytes_done"] or 0) if r else 0


def _job_bytes_done(job_id: int) -> int:
    with db() as con:
        r = con.execute("SELECT COALESCE(SUM(CASE WHEN transfer_required=1 THEN bytes_done ELSE 0 END),0) n FROM job_items WHERE job_id=?", (job_id,)).fetchone()
        return int(r["n"] or 0)


def _same_size_duplicate_candidates(row: dict) -> list[dict]:
    size = int(row.get("size_bytes") or 0)
    if not size:
        return []
    with db() as con:
        rows = con.execute(
            "SELECT id,sha256,source_kind,path,staging_path,archive_path FROM inventory WHERE id<>? AND size_bytes=? AND sha256 IS NOT NULL AND sha256<>'' AND excluded=0 LIMIT 20",
            (row["id"], size),
        ).fetchall()
    out = []
    for r in map(_row_dict, rows):
        # A duplicate only counts if a local copy really exists now; otherwise skipping the
        # transfer would leave zero copies after the user wipes the phone/card.
        local = [r.get("staging_path"), r.get("archive_path")] + ([r.get("path")] if r.get("source_kind") == "fixed" else [])
        if any(x and Path(x).is_file() and Path(x).stat().st_size == size for x in local):
            out.append(r)
    return out


def _preflight_duplicate(row: dict) -> tuple[int | None, str | None]:
    """Avoid transferring an exact duplicate when a same-size known asset exists.

    We only pay the source-side hashing cost when a same-size candidate already exists.
    Android hashing happens on the phone, so a multi-GB duplicate does not cross USB.
    """
    candidates = _same_size_duplicate_candidates(row)
    if not candidates:
        return None, None
    candidate_hashes = {r["sha256"]: int(r["id"]) for r in candidates if r.get("sha256")}
    sha = None
    try:
        if row.get("source_kind") == "android" and row.get("path"):
            adb = android.find_adb()
            if adb:
                devices, _ = android.adb_devices(adb, refresh=True)
                if any(d["serial"] == row.get("source_id") and d["state"] == "device" for d in devices):
                    sha = android.remote_sha256(adb, row["source_id"], row.get("path"))
        elif row.get("source_kind") == "removable":
            p = Path(row.get("path") or "")
            if p.exists():
                sha = sha256_file(p)
    except Exception:
        sha = None
    return (candidate_hashes.get(sha), sha) if sha else (None, None)


def _existing_local_path(row: dict) -> Path | None:
    for key in ("staging_path", "archive_path", "private_path", "rejected_path"):
        p = row.get(key)
        if p and Path(p).exists():
            return Path(p)
    if row.get("source_kind") == "fixed":
        p = Path(row.get("path") or "")
        if p.exists():
            return p
    return None


def _ensure_imported(row: dict, job_id: int, item_id: int) -> Path:
    row = dict(row, source_kind=_effective_kind(row))
    # Already-local assets do not need an unnecessary second copy or source access.
    local = _existing_local_path(row)
    if local:
        return local
    if row.get("source_kind") == "fixed":
        raise RuntimeError("Local source file is unavailable")

    expected = int(row.get("size_bytes") or 0)
    _check_free_space(expected)
    dest = _staging_dest(row)
    expected_sha = str(row.get("sha256") or "").strip().lower() or None
    source_sha = expected_sha

    # Deterministic path + byte count are not content identity. A stale or
    # unrelated same-size staging file must not be accepted after a restart.
    if dest.exists() and (not expected or dest.stat().st_size == expected):
        if source_sha is None:
            try:
                if row.get("source_kind") == "removable":
                    src = Path(row.get("path") or "")
                    if src.exists():
                        source_sha = sha256_file(src)
                elif row.get("source_kind") == "android" and row.get("path"):
                    adb = android.find_adb()
                    if adb:
                        devices, _ = android.adb_devices(adb, refresh=True)
                        if any(d["serial"] == row.get("source_id") and d["state"] == "device" for d in devices):
                            source_sha = android.remote_sha256(adb, row["source_id"], row.get("path"))
            except Exception as exc:
                log(f"staging integrity source hash {row.get('id')}: {exc}")
                source_sha = None

        verified_existing = False
        if source_sha:
            try:
                verified_existing = sha256_file(dest) == source_sha
            except Exception:
                verified_existing = False

        if verified_existing:
            with db() as con:
                con.execute(
                    "UPDATE inventory SET staging_path=?,imported_at=COALESCE(imported_at,?),import_status='imported',import_error=NULL,error=NULL,sha256=COALESCE(sha256,?) WHERE id=?",
                    (str(dest), now_iso(), source_sha, row["id"]),
                )
                con.commit()
            return dest
        # Unknown/mismatched content falls through to a fresh copy. If the
        # source is unavailable, the normal source path below fails closed.

    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)
    base_done = _job_bytes_done(job_id) - int(_job_item_bytes(item_id))
    last = {"at": 0.0, "n": -1}

    def progress(n):
        n = int(n)
        now = time.time()
        # SQLite is durable, but committing every 350 ms for a multi-hour 4K ingest
        # creates needless disk churn. Persist at most ~1 Hz or every 32 MB.
        if n != 0 and now - last["at"] < 0.9 and n - last["n"] < 32 * 1024 * 1024:
            return
        last["at"] = now
        last["n"] = n
        _item_update(item_id, bytes_done=n)
        _job_update(job_id, bytes_done=max(0, base_done) + n)

    try:
        _item_update(item_id, status="running", phase="importing", started_at=now_iso(), error=None)
        with db() as con:
            con.execute("UPDATE inventory SET import_status='importing',import_error=NULL WHERE id=?", (row["id"],))
            con.commit()
        if _cancel_requested(job_id):
            raise RuntimeError("cancelled")
        if row.get("source_kind") == "android":
            adb = android.find_adb()
            if not adb:
                raise RuntimeError("ADB is not installed or not found")
            devices, err = android.adb_devices(adb, refresh=True)
            if not any(d["serial"] == row.get("source_id") and d["state"] == "device" for d in devices):
                raise RuntimeError(f"Android device is not connected/authorized{': '+err if err else ''}")
            ok, err = android.pull_original_progress(
                adb, row["source_id"], row.get("path"), row.get("content_uri"), tmp, progress,
                cancel_cb=lambda: _cancel_requested(job_id),
            )
            if not ok:
                raise RuntimeError(err or "Android import failed")
            if not expected and not source_sha and row.get("path"):
                # the phone did not say the size: the copy is checked against the phone's own SHA-256 instead (a cut
                # transfer must never count as imported and the phone as safe to disconnect)
                source_sha = android.remote_sha256(adb, row["source_id"], row.get("path"))
                if not source_sha:
                    raise RuntimeError("The copy from the phone could not be checked (its size is unknown). Try again.")
        elif row.get("source_kind") == "removable":
            src = Path(row.get("path") or "")
            if not src.exists():
                raise RuntimeError("SD/USB source file is unavailable")
            _copy_local_with_progress(src, tmp, progress, cancel_cb=lambda: _cancel_requested(job_id))
        else:
            raise RuntimeError(f"Unsupported ingest source: {row.get('source_kind')}")

        actual = tmp.stat().st_size
        if expected and actual != expected:
            raise RuntimeError(f"Copy verification failed: expected {expected} bytes, got {actual}")
        if source_sha and sha256_file(tmp) != source_sha:
            raise RuntimeError("Copy verification failed: SHA-256 mismatch")
        tmp.replace(dest)
        with db() as con:
            con.execute(
                "UPDATE inventory SET staging_path=?,imported_at=?,import_status='imported',import_error=NULL,error=NULL,sha256=COALESCE(sha256,?) WHERE id=?",
                (str(dest), now_iso(), source_sha, row["id"]),
            )
            con.commit()
        _item_update(item_id, bytes_done=actual, phase="imported")
        return dest
    except Exception as exc:
        if not load_config().get("ingest", {}).get("keep_failed_partials", False):
            tmp.unlink(missing_ok=True)
        with db() as con:
            con.execute("UPDATE inventory SET import_status='error',import_error=?,error=? WHERE id=?", (str(exc), str(exc), row["id"]))
            con.commit()
        raise


def _analyze_one(row: dict, local: Path, cancel_cb=None, progress_cb=None) -> tuple[str, float | None, str, float | None, str, str, str]:
    cfg = load_config()
    sha = row.get("sha256") or sha256_file(local)
    with db() as con:
        if con.execute("SELECT 1 FROM ignored_hashes WHERE sha256=?", (sha,)).fetchone():
            return "private", None, "private_forever", None, "unreviewed", "", sha
        dup = con.execute(
            "SELECT id FROM inventory WHERE sha256=? AND id<>? AND (archive_path IS NOT NULL OR staging_path IS NOT NULL OR analysis_status NOT IN ('unreviewed','error')) LIMIT 1",
            (sha, row["id"]),
        ).fetchone()
    if dup:
        return "duplicate", None, f"duplicate_of:{dup['id']}", None, "unreviewed", "", sha

    privacy_cfg = cfg.get("privacy", {})
    quality_cfg = cfg.get("analysis", {})
    a = analyze_combined(
        local, row["media_type"],
        privacy_enabled=bool(privacy_cfg.get("enabled", True)),
        privacy_threshold=float(privacy_cfg.get("review_threshold", 0.42)),
        privacy_samples=int(privacy_cfg.get("video_samples", 10)),
        quality_enabled=bool(quality_cfg.get("technical_quality", True)),
        quality_review_below=float(quality_cfg.get("quality_review_below", 55)),
        ffmpeg_threads=int(quality_cfg.get("ffmpeg_threads", 2)),
        cancel_cb=cancel_cb, progress_cb=progress_cb,
    )
    return (
        a["privacy_status"], a["privacy_score"], a["privacy_reason"],
        a["quality_score"], a["quality_status"], a["quality_reason"], sha,
    )



RIGHTS_PRESETS = {
    "review": {
        "status": "review", "place": "",
        "reason": "manual: review publishing rights/permissions before use",
        "url": "",
    },
    "permission": {
        "status": "permission", "place": "",
        "reason": "manual: permission or release is needed before publishing",
        "url": "",
    },
    "cleared": {
        "status": "cleared", "place": "",
        "reason": "manual: user confirmed rights/permission are cleared for intended use",
        "url": "",
    },
    "blocked": {
        "status": "blocked", "place": "",
        "reason": "manual: do not publish/use commercially",
        "url": "",
    },
}


def set_rights(ids: list[int], preset: str, notes: str = "") -> int:
    ids = [int(x) for x in ids]
    if not ids:
        return 0
    if preset == "reset":
        with db() as con:
            q = f"UPDATE inventory SET rights_status='unknown',rights_reason=NULL,rights_place=NULL,rights_source_url=NULL,rights_notes=?,rights_manual=0,rights_checked_at=? WHERE id IN ({','.join('?' for _ in ids)})"
            cur = con.execute(q, [notes or None, now_iso(), *ids]); con.commit(); return cur.rowcount
    x = RIGHTS_PRESETS.get(preset)
    if not x:
        raise ValueError("Unknown rights preset")
    with db() as con:
        q = f"UPDATE inventory SET rights_status=?,rights_reason=?,rights_place=CASE WHEN ?<>'' THEN ? ELSE rights_place END,rights_source_url=?,rights_notes=?,rights_manual=1,rights_checked_at=? WHERE id IN ({','.join('?' for _ in ids)})"
        cur = con.execute(q, [x['status'], x['reason'], x['place'], x['place'], x['url'] or None, notes or None, now_iso(), *ids]); con.commit(); return cur.rowcount


def set_rights_custom(inv_id: int, status: str, place: str = "", notes: str = "", source_url: str = "") -> None:
    allowed = {"unknown", "review", "permission", "cleared", "blocked"}
    if status not in allowed:
        raise ValueError("Invalid rights status")
    with db() as con:
        con.execute("UPDATE inventory SET rights_status=?,rights_reason=?,rights_place=?,rights_source_url=?,rights_notes=?,rights_manual=1,rights_checked_at=? WHERE id=?",
                    (status, f"manual: custom status {status}", place or None, source_url or None, notes or None, now_iso(), int(inv_id)))
        con.commit()



def _auto_rights_triage(row: dict, local: Path) -> dict:
    """Return generic non-destructive rights-risk hints.

    Archivist must not encode one-off venue cases into the product. Automatic
    triage can report generic signals such as an audio track or possible
    performance/show metadata, while the actual place/permission decision stays
    with the user.
    """
    flags = probe_rights_flags(local, row.get("media_type") or "")
    audio = 1 if flags.get("audio_present") else 0

    # Never override a human decision. We only keep the audio hint fresh.
    if int(row.get("rights_manual") or 0):
        return {
            "audio": audio,
            "status": row.get("rights_status") or "unknown",
            "reason": row.get("rights_reason"),
            "place": row.get("rights_place"),
            "url": row.get("rights_source_url"),
        }

    hints = set(flags.get("hints") or [])
    if "possible_performance_audio" in hints:
        return {
            "audio": audio,
            "status": "review",
            "place": row.get("rights_place"),
            "reason": "auto: audio/metadata may indicate a performance or show; review music, performance and venue permissions before publishing",
            "url": None,
        }

    reason = row.get("rights_reason") or (
        "auto: audio track present; publishing rights not reviewed"
        if audio else
        "auto: publishing rights not reviewed"
    )
    return {
        "audio": audio,
        "status": row.get("rights_status") or "unknown",
        "place": row.get("rights_place"),
        "reason": reason,
        "url": row.get("rights_source_url"),
    }


def _write_auto_rights(inv_id: int, row: dict, local: Path) -> None:
    rr = _auto_rights_triage(row, local)
    with db() as con:
        con.execute("UPDATE inventory SET rights_audio_present=?,rights_status=?,rights_reason=?,rights_place=?,rights_source_url=?,rights_checked_at=? WHERE id=?",
                    (rr['audio'], rr['status'], rr['reason'], rr['place'], rr['url'], now_iso(), int(inv_id)))
        con.commit()


def _mark_remaining_cancelled(job_id: int):
    with db() as con:
        con.execute(
            "UPDATE job_items SET status='skipped',phase='cancelled',error='cancelled',finished_at=? "
            "WHERE job_id=? AND status NOT IN ('done','error','skipped')",
            (now_iso(), job_id),
        )
        con.commit()


def _not_copied_back_to_import(job_id: int) -> None:
    """A card / phone file whose copy failed or was cancelled is not in the Library (it has no copy here): it shows on
    Import again ("Not in Library"), where it can be added again - instead of vanishing from both views."""
    try:
        with db() as con:
            con.execute("UPDATE inventory SET work_selected=0 WHERE id IN (SELECT inventory_id FROM job_items WHERE job_id=? "
                        "AND status IN ('error','skipped')) AND staging_path IS NULL AND archive_path IS NULL "
                        "AND source_kind IN ('removable','android')", (int(job_id),))
            con.commit()
    except Exception as exc:
        log(f"job {job_id}: could not return uncopied files to Import: {exc}")


def _run_import_analyze_job(job: dict):
    """Two explicit phases: import ALL selected files first, then analyze locally.

    The source device is no longer needed once phase 1 ends. This is intentionally
    different from v2.0, which interleaved copy -> analyze -> copy and kept the
    phone tethered during slow analysis.
    """
    job_id = int(job["id"])
    options = json.loads(job.get("options_json") or "{}")
    analyze_after = bool(options.get("analyze", job["kind"] == "import_analyze"))
    with db() as con:
        items = con.execute(
            "SELECT ji.*,i.filename FROM job_items ji JOIN inventory i ON i.id=ji.inventory_id WHERE ji.job_id=? AND ji.status NOT IN ('done','skipped') ORDER BY ji.seq",
            (job_id,),
        ).fetchall()

    # Fail before touching the source if the complete selected transfer cannot fit.
    # This is conservative (duplicates may reduce the actual transfer), but avoids a
    # half-imported batch that only discovers the disk is full near the end.
    # Only what is still to be copied counts (after a restart half of it may be here already), and only those
    # files fail for lack of space - files already copied are still analysed.
    with db() as con:
        need = con.execute(
            "SELECT ji.id, i.size_bytes FROM job_items ji JOIN inventory i ON i.id=ji.inventory_id WHERE ji.job_id=? "
            "AND ji.status NOT IN ('done','skipped') AND i.source_kind IN ('removable','android') "
            "AND i.staging_path IS NULL AND i.archive_path IS NULL", (job_id,)).fetchall()
    transfer_total = sum(int(r["size_bytes"] or 0) for r in need)
    if transfer_total:
        try:
            _check_free_space(transfer_total)
        except Exception as exc:
            msg = str(exc)
            lacking = {int(r["id"]) for r in need}
            with db() as con:
                con.executemany("UPDATE job_items SET status='error',phase='error',error=?,finished_at=? WHERE id=?",
                                [(msg, now_iso(), i) for i in lacking])
                con.commit()
            _not_copied_back_to_import(job_id)
            items = [x for x in items if int(x["id"]) not in lacking]
            if not items:
                with db() as con:
                    con.execute("UPDATE jobs SET status='failed',stage='done',message=?,error=?,failed=total,done=total,finished_at=? WHERE id=?", (msg, msg, now_iso(), job_id))
                    con.commit()
                return
            _refresh_job_counts(job_id)

    _job_update(job_id, status="running", started_at=job.get("started_at") or now_iso(), stage="import", message="Importing selected files", source_releasable=0)

    # Phase 1: source I/O only. No privacy/quality work is allowed to delay the next copy.
    for ji in items:
        iid = int(ji["id"]); inv_id = int(ji["inventory_id"])
        if _cancel_requested(job_id):
            _mark_remaining_cancelled(job_id)
            break
        with db() as con:
            rr = con.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
        if not rr:
            _item_update(iid, status="error", phase="error", error="Catalog item missing", finished_at=now_iso())
            _refresh_job_counts(job_id)
            continue
        row = _row_dict(rr)
        row["source_kind"] = _effective_kind(row)
        _job_update(job_id, current_inventory_id=inv_id, current_filename=row["filename"], stage="import", message=f"Importing {row['filename']}")
        try:
            # Never touch the phone/SD again when this item is already local. Only
            # source-side hash when a transfer is actually still required.
            if _existing_local_path(row) is None and row.get("source_kind") in ("android", "removable"):
                _job_update(job_id, message=f"Checking duplicate before transfer: {row['filename']}")
                dup_id, pre_sha = _preflight_duplicate(row)
                if dup_id:
                    with db() as con:
                        con.execute("UPDATE inventory SET analysis_status='duplicate',privacy_reason=?,sha256=?,import_status='skipped_duplicate',import_error=NULL,error=NULL WHERE id=?", (f"duplicate_of:{dup_id}", pre_sha, inv_id))
                        con.commit()
                    _item_update(iid, status="done", phase="done", result_status="duplicate", finished_at=now_iso(), error=None)
                    _refresh_job_counts(job_id)
                    continue

            local = _ensure_imported(row, job_id, iid)
            if analyze_after:
                _item_update(iid, status="ready", phase="imported", result_status="imported", error=None)
            else:
                _item_update(iid, status="done", phase="done", result_status="local" if row.get("source_kind") == "fixed" else "imported", finished_at=now_iso(), error=None)
                if row.get("media_type") == "video": queue_storyboard(inv_id, priority=15)
        except Exception as exc:
            if str(exc).lower() == "cancelled":
                _item_update(iid, status="skipped", phase="cancelled", error="cancelled", finished_at=now_iso())
                _mark_remaining_cancelled(job_id)
                break
            log(f"job {job_id} item {inv_id} failed: {exc}")
            _item_update(iid, status="error", phase="error", error=str(exc), finished_at=now_iso())
        _refresh_job_counts(job_id)

    _not_copied_back_to_import(job_id)
    if _cancel_requested(job_id):
        _finish_job(job_id)
        return

    if not analyze_after:
        with db() as con:
            errs = con.execute("SELECT COUNT(*) n FROM job_items WHERE job_id=? AND status='error'", (job_id,)).fetchone()["n"]
        inplace = _reads_sources_in_place(job_id)
        _job_update(job_id, source_releasable=0 if (errs or inplace) else 1, import_completed_at=now_iso(),
                    message=(f"Import finished with {errs} error(s) — keep the source connected" if errs else
                             "Added. The files stay in their folder — keep that disk connected." if inplace else
                             "Import complete — source can be disconnected"))
        _finish_job(job_id)
        return

    with db() as con:
        ok_imports = con.execute("SELECT COUNT(*) n FROM job_items WHERE job_id=? AND phase='imported' AND status='ready'", (job_id,)).fetchone()["n"]
        import_errors = con.execute("SELECT COUNT(*) n FROM job_items WHERE job_id=? AND status='error'", (job_id,)).fetchone()["n"]
    inplace = _reads_sources_in_place(job_id)
    _job_update(
        job_id, stage="analyze", source_releasable=0 if (import_errors or inplace) else 1, import_completed_at=now_iso(), bytes_done=_job_bytes_done(job_id),
        current_inventory_id=None, current_filename=None,
        message=(f"Analyzing {ok_imports} local file(s); {import_errors} import error(s) — keep the source connected." if import_errors
                 else f"Analyzing {ok_imports} file(s) where they are — keep that disk connected." if inplace
                 else f"Import complete — source can be disconnected. Analyzing {ok_imports} local file(s)."),
    )

    # Phase 2: local-only analysis. The Android/SD source can now disappear safely.
    with db() as con:
        imported = con.execute("SELECT * FROM job_items WHERE job_id=? AND phase='imported' AND status='ready' ORDER BY seq", (job_id,)).fetchall()
    for ji in imported:
        iid = int(ji["id"]); inv_id = int(ji["inventory_id"])
        if _cancel_requested(job_id):
            _mark_remaining_cancelled(job_id)
            break
        with db() as con:
            rr = con.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
        if not rr:
            _item_update(iid, status="error", phase="error", error="Catalog item missing", finished_at=now_iso())
            _refresh_job_counts(job_id)
            continue
        row = _row_dict(rr)
        local = next((Path(row[k]) for k in ("staging_path", "archive_path", "private_path", "path") if row.get(k) and Path(row[k]).exists()), None)
        _job_update(job_id, current_inventory_id=inv_id, current_filename=row["filename"], stage="analyze", message=f"Analyzing local copy: {row['filename']}")
        try:
            if not local:
                raise RuntimeError("Imported local copy is missing")
            _item_update(iid, status="running", phase="analyzing")
            def aprog(n, total, phase):
                _job_update(job_id, message=f"Analyzing local copy: {row['filename']} · {phase} {n}/{total}")
            pstatus, pscore, preason, qscore, qstatus, qreason, sha = _analyze_one(
                row, local, cancel_cb=lambda: _cancel_requested(job_id), progress_cb=aprog
            )
            with db() as con:
                con.execute(
                    "UPDATE inventory SET analysis_status=?,privacy_score=?,privacy_reason=?,sha256=?,quality_score=?,quality_status=?,quality_reason=?,analysis_version=4,error=NULL WHERE id=?",
                    (pstatus, pscore, preason, sha, qscore, qstatus, qreason, inv_id),
                )
                con.commit()
            # Rights/property/audio risk is separate from privacy/quality and is never
            # treated as a legal conclusion. Manual tags are preserved.
            _write_auto_rights(inv_id, row, local)
            _fill_video_length(inv_id, row, local, job_id, pstatus)
            _item_update(iid, status="done", phase="done", result_status=pstatus, finished_at=now_iso(), error=None)
            if row.get("media_type") == "video": queue_storyboard(inv_id, priority=15)
        except Exception as exc:
            if str(exc).lower() == "cancelled":
                _item_update(iid, status="skipped", phase="cancelled", error="cancelled", finished_at=now_iso())
                _mark_remaining_cancelled(job_id)
                _refresh_job_counts(job_id)
                break
            _item_update(iid, status="error", phase="error", error=str(exc), finished_at=now_iso())
        _refresh_job_counts(job_id)
    _finish_job(job_id)


def _run_analyze_job(job: dict):
    job_id = int(job["id"])
    with db() as con:
        items = con.execute("SELECT * FROM job_items WHERE job_id=? AND status NOT IN ('done','skipped') ORDER BY seq", (job_id,)).fetchall()
    _job_update(job_id, status="running", started_at=job.get("started_at") or now_iso(), stage="analyze", message="Analyzing local/staged files", source_releasable=0 if _reads_sources_in_place(job_id) else 1)
    for ji in items:
        iid = int(ji["id"]); inv_id = int(ji["inventory_id"])
        if _cancel_requested(job_id):
            _mark_remaining_cancelled(job_id); break
        with db() as con:
            rr = con.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
        if not rr:
            _item_update(iid, status="error", phase="error", error="Catalog item missing", finished_at=now_iso()); _refresh_job_counts(job_id); continue
        row = _row_dict(rr)
        local = next((Path(row[k]) for k in ("staging_path", "archive_path", "private_path", "path") if row.get(k) and Path(row[k]).exists()), None)
        _job_update(job_id, current_inventory_id=inv_id, current_filename=row["filename"], stage="analyze", message=f"Analyzing {row['filename']}")
        try:
            if not local:
                raise RuntimeError("File is not local. Import it first.")
            _item_update(iid, status="running", phase="analyzing", started_at=now_iso())
            def aprog(n, total, phase):
                _job_update(job_id, message=f"Analyzing {row['filename']} · {phase} {n}/{total}")
            pstatus, pscore, preason, qscore, qstatus, qreason, sha = _analyze_one(
                row, local, cancel_cb=lambda: _cancel_requested(job_id), progress_cb=aprog
            )
            with db() as con:
                con.execute(
                    "UPDATE inventory SET analysis_status=?,privacy_score=?,privacy_reason=?,sha256=?,quality_score=?,quality_status=?,quality_reason=?,analysis_version=4,error=NULL WHERE id=?",
                    (pstatus, pscore, preason, sha, qscore, qstatus, qreason, inv_id),
                )
                con.commit()
            # Rights/property/audio risk is separate from privacy/quality and is never
            # treated as a legal conclusion. Manual tags are preserved.
            _write_auto_rights(inv_id, row, local)
            _fill_video_length(inv_id, row, local, job_id, pstatus)
            _item_update(iid, status="done", phase="done", result_status=pstatus, finished_at=now_iso(), error=None)
            if row.get("media_type") == "video": queue_storyboard(inv_id, priority=15)
        except Exception as exc:
            if str(exc).lower() == "cancelled":
                _item_update(iid, status="skipped", phase="cancelled", error="cancelled", finished_at=now_iso())
                _mark_remaining_cancelled(job_id)
                _refresh_job_counts(job_id)
                break
            _item_update(iid, status="error", phase="error", error=str(exc), finished_at=now_iso())
        _refresh_job_counts(job_id)
    _finish_job(job_id)



def _run_media_brain_job(job: dict):
    job_id=int(job["id"])
    try: options=json.loads(job.get("options_json") or "{}")
    except Exception: options={}
    preset="car" if options.get("preset")=="car" else "general"
    with db() as con:
        items=con.execute("SELECT * FROM job_items WHERE job_id=? AND status NOT IN ('done','skipped') ORDER BY seq",(job_id,)).fetchall()
    _job_update(job_id,status="running",started_at=job.get("started_at") or now_iso(),stage="media_brain",message="Building virtual clips + Smart Crop",source_releasable=0 if _reads_sources_in_place(job_id) else 1)
    for ji in items:
        iid=int(ji["id"]); inv_id=int(ji["inventory_id"])
        if _cancel_requested(job_id):
            _mark_remaining_cancelled(job_id); break
        with db() as con:
            rr=con.execute("SELECT * FROM inventory WHERE id=?",(inv_id,)).fetchone()
        if not rr:
            _item_update(iid,status="error",phase="error",error="Catalog item missing",finished_at=now_iso()); _refresh_job_counts(job_id); continue
        row=_row_dict(rr)
        _job_update(job_id,current_inventory_id=inv_id,current_filename=row["filename"],stage="media_brain",message=f"Media Brain: {row['filename']}")
        try:
            if row.get("media_type")!="video":
                raise RuntimeError("Media Brain v1 currently works on video")
            local=next((Path(row[k]) for k in ("staging_path","archive_path","path") if row.get(k) and Path(row[k]).exists()),None)
            if not local:
                raise RuntimeError("File is not local. Import it first.")
            _item_update(iid,status="running",phase="media_brain",started_at=now_iso())
            def mprog(n,total,phase):
                _job_update(job_id,message=f"Media Brain: {row['filename']} · {phase}")
                _item_update(iid,result_status=phase)
            result=analyze_video_into_clips(inv_id,local,row.get("duration_ms"),preset,cancel_cb=lambda:_cancel_requested(job_id),progress_cb=mprog)
            _item_update(iid,status="done",phase="done",result_status=f"{result['clips']} clips · {result['best']} best",finished_at=now_iso(),error=None)
        except Exception as exc:
            if str(exc).lower()=="cancelled":
                _item_update(iid,status="skipped",phase="cancelled",error="cancelled",finished_at=now_iso()); _mark_remaining_cancelled(job_id); _refresh_job_counts(job_id); break
            _item_update(iid,status="error",phase="error",error=str(exc),finished_at=now_iso())
        _refresh_job_counts(job_id)
    _finish_job(job_id)


def _verified_copy(src: Path, dest: Path, sha: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _no_overwrite(dest, src.stat().st_size, sha)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)
    copy_file(src, tmp)
    if tmp.stat().st_size != src.stat().st_size or sha256_file(tmp) != sha:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Archive copy verification failed")
    tmp.replace(dest)


def _run_archive_job(job: dict):
    job_id = int(job["id"])
    from .config import archive_root
    root = archive_root(); root.mkdir(parents=True, exist_ok=True)
    with db() as con:
        items = con.execute("SELECT * FROM job_items WHERE job_id=? AND status NOT IN ('done','skipped') ORDER BY seq", (job_id,)).fetchall()
    _job_update(job_id, status="running", started_at=job.get("started_at") or now_iso(), stage="archive", message="Archiving", source_releasable=0 if _reads_sources_in_place(job_id) else 1)
    for ji in items:
        iid = int(ji["id"]); inv_id = int(ji["inventory_id"])
        if _cancel_requested(job_id):
            _mark_remaining_cancelled(job_id); break
        with db() as con:
            rr = con.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
        if not rr:
            _item_update(iid, status="error", phase="error", error="Catalog item missing", finished_at=now_iso()); _refresh_job_counts(job_id); continue
        row = _row_dict(rr)
        _job_update(job_id, current_inventory_id=inv_id, current_filename=row["filename"], stage="archive", message=f"Archiving {row['filename']}")
        try:
            if row.get("analysis_status") == "private":
                raise RuntimeError("Private item cannot be archived to main library")
            local = None; staged = False
            if row.get("staging_path") and Path(row["staging_path"]).exists(): local = Path(row["staging_path"]); staged = True
            elif row.get("path") and Path(row["path"]).exists(): local = Path(row["path"])
            elif row.get("archive_path") and Path(row["archive_path"]).exists(): local = Path(row["archive_path"])
            if not local:
                raise RuntimeError("No local file available")
            sha = row.get("sha256") or sha256_file(local)
            dest = _archive_dest(root, row, local, sha)
            size = local.stat().st_size
            # If the canonical name already exists with identical content, reuse it.
            plain = dest
            if plain.exists() and plain != local:
                try:
                    if plain.stat().st_size == size and sha256_file(plain) == sha:
                        if staged: local.unlink()
                        with db() as con:
                            con.execute("UPDATE inventory SET archive_path=?,staging_path=NULL,import_status='archived',sha256=?,error=NULL WHERE id=?", (str(plain), sha, inv_id)); con.commit()
                        _item_update(iid, status="done", phase="done", result_status="archived_existing", finished_at=now_iso(), error=None)
                        _refresh_job_counts(job_id)
                        continue
                except Exception:
                    pass
            if staged:
                _verified_move(local, dest, sha)
            elif local.resolve() != dest.resolve():
                _verified_copy(local, dest, sha)
            if dest.stat().st_size != size or sha256_file(dest) != sha:
                raise RuntimeError("Archive verification failed")
            with db() as con:
                con.execute("UPDATE inventory SET archive_path=?,staging_path=NULL,import_status='archived',sha256=?,error=NULL WHERE id=?", (str(dest), sha, inv_id)); con.commit()
            _item_update(iid, status="done", phase="done", result_status="archived", finished_at=now_iso(), error=None)
        except Exception as exc:
            _item_update(iid, status="error", phase="error", error=str(exc), finished_at=now_iso())
        _refresh_job_counts(job_id)
    _finish_job(job_id)


def _owned_copy(row: dict) -> Path | None:
    """The Archivist-owned copy of an item (Staging or archive), never the source original."""
    roots = [STAGING.resolve()]
    try:
        from .config import archive_root
        roots.append(archive_root().resolve())
    except Exception:
        pass
    original = None
    try:
        original = Path(row["path"]).resolve() if row.get("path") else None
    except Exception:
        pass
    for key in ("staging_path", "archive_path"):
        if not row.get(key):
            continue
        p = Path(row[key])
        try:
            rp = p.resolve()
        except Exception:
            continue
        if not p.is_file() or (original is not None and rp == original):
            continue
        if any(rp == r or r in rp.parents for r in roots):
            return p
    return None


def _mark_private_one(inv_id: int) -> str:
    with db() as con:
        rr = con.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
    if not rr:
        raise RuntimeError("Catalog item missing")
    row = _row_dict(rr)
    local = next((Path(row[k]) for k in ("staging_path", "archive_path", "private_path", "path") if row.get(k) and Path(row[k]).exists()), None)
    # the file as it is NOW (it may have been replaced since its hash was taken); the old hash stays Private too
    old_sha = row.get("sha256")
    changed = True
    try:     # (a background job: reading the file once is fine) - but never a file only in the cloud: no download for it
        from .auto_edit import cloud_only
        if local is not None and cloud_only(local):
            changed = False
    except Exception:
        pass
    sha = (sha256_file(local) if (local and changed) else None) or old_sha
    private_path = row.get("private_path")
    # Never move the user's original (phone, card, fixed folder). Only a copy Archivist owns
    # (an existing file inside Staging or the archive root) may move into the private area.
    owned = _owned_copy(row)
    if owned and not private_path:
        dest = _private_dest(row, owned, sha or "unknown")
        _verified_move(owned, dest, sha)
        private_path = str(dest)
    with db() as con:
        con.execute("INSERT OR REPLACE INTO ignored_source_keys(source_key,reason,created_at) VALUES(?,?,?)", (row["source_key"], "private_forever", now_iso()))
        for h in {x for x in (sha, old_sha) if x}:
            con.execute("INSERT OR REPLACE INTO ignored_hashes(sha256,reason,created_at) VALUES(?,?,?)", (h, "private_forever", now_iso()))
        con.execute(
            "UPDATE inventory SET analysis_status='private',privacy_reason='private_forever',sha256=COALESCE(?,sha256),private_path=COALESCE(?,private_path),staging_path=CASE WHEN ? IS NOT NULL THEN NULL ELSE staging_path END,archive_path=CASE WHEN ? IS NOT NULL THEN NULL ELSE archive_path END,import_status='private',excluded=1,error=NULL WHERE id=?",
            (sha, private_path, private_path, private_path, inv_id),
        )
        con.commit()
    return "private"


def _fill_video_length(inv_id: int, row: dict, local: Path, job_id: int | None = None, status: str = "") -> None:
    """Length of a video for the Library page: videos in a folder on this PC are listed without opening them, so the
    length was never known ("—"). Read once here (measured when the file has none written).
    Also the recording time from the video's header (a copied video's file date is the day it was copied)."""
    if row.get("media_type") == "video" and not row.get("date_taken") and status not in ("duplicate", "private"):
        try:
            from .media import shot_time
            t = shot_time(Path(local))
            if t:
                with db() as con:
                    con.execute("UPDATE inventory SET date_taken=? WHERE id=? AND date_taken IS NULL", (float(t), inv_id))
                    con.commit()
        except Exception as exc:
            log(f"recording time not read for item {inv_id}: {exc}")
    if row.get("media_type") != "video" or row.get("duration_ms") or status in ("duplicate", "private"):
        return
    try:
        if job_id:     # a recording without a written length is read through: tell the watchdog the job is alive
            _job_update(job_id, message=f"Reading video length: {row.get('filename') or ''}")
        from .media import probe_duration
        d = probe_duration(Path(local))
        if d and d > 0:
            with db() as con:
                con.execute("UPDATE inventory SET duration_ms=? WHERE id=? AND (duration_ms IS NULL OR duration_ms<=0)", (int(round(d * 1000)), inv_id))
                con.commit()
    except Exception as exc:
        log(f"video length not read for item {inv_id}: {exc}")


def _run_private_job(job: dict):
    job_id = int(job["id"])
    with db() as con:
        items = con.execute("SELECT * FROM job_items WHERE job_id=? AND status NOT IN ('done','skipped') ORDER BY seq", (job_id,)).fetchall()
    _job_update(job_id, status="running", started_at=job.get("started_at") or now_iso(), stage="private", message="Moving/marking private items", source_releasable=1)
    for ji in items:
        iid = int(ji["id"]); inv_id = int(ji["inventory_id"])
        if _cancel_requested(job_id): _mark_remaining_cancelled(job_id); break
        try:
            _item_update(iid, status="running", phase="private", started_at=now_iso())
            res = _mark_private_one(inv_id)
            _item_update(iid, status="done", phase="done", result_status=res, finished_at=now_iso(), error=None)
        except Exception as exc:
            _item_update(iid, status="error", phase="error", error=str(exc), finished_at=now_iso())
        _refresh_job_counts(job_id)
    _finish_job(job_id)


def _reject_one(inv_id: int) -> str:
    with db() as con:
        rr = con.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
    if not rr:
        raise RuntimeError("Catalog item missing")
    row = _row_dict(rr)
    rejected_path = row.get("rejected_path")
    if row.get("staging_path") and Path(row["staging_path"]).exists():
        src = Path(row["staging_path"])
        if load_config().get("ingest", {}).get("keep_rejected", True):
            dest = _rejected_dest(row, src)
            _verified_move(src, dest, row.get("sha256"))
            rejected_path = str(dest)
        else:
            src.unlink(missing_ok=True)
    with db() as con:
        con.execute("UPDATE inventory SET staging_path=NULL,rejected_path=?,import_status='rejected',analysis_status='rejected',excluded=1,error=NULL WHERE id=?", (rejected_path, inv_id))
        con.commit()
    return "rejected"


def _run_reject_job(job: dict):
    job_id = int(job["id"])
    with db() as con:
        items = con.execute("SELECT * FROM job_items WHERE job_id=? AND status NOT IN ('done','skipped') ORDER BY seq", (job_id,)).fetchall()
    _job_update(job_id, status="running", started_at=job.get("started_at") or now_iso(), stage="reject", message="Moving rejected staging copies to quarantine", source_releasable=1)
    for ji in items:
        iid = int(ji["id"]); inv_id = int(ji["inventory_id"])
        if _cancel_requested(job_id): _mark_remaining_cancelled(job_id); break
        try:
            _item_update(iid, status="running", phase="rejecting", started_at=now_iso())
            res = _reject_one(inv_id)
            _item_update(iid, status="done", phase="done", result_status=res, finished_at=now_iso(), error=None)
        except Exception as exc:
            _item_update(iid, status="error", phase="error", error=str(exc), finished_at=now_iso())
        _refresh_job_counts(job_id)
    _finish_job(job_id)


def _refresh_job_counts(job_id: int):
    with db() as con:
        r = con.execute(
            "SELECT COUNT(*) total,"
            "SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) success,"
            "SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) failed,"
            "SUM(CASE WHEN status IN ('done','error','skipped') THEN 1 ELSE 0 END) done,"
            "COALESCE(SUM(CASE WHEN transfer_required=1 THEN bytes_done ELSE 0 END),0) bytes_done "
            "FROM job_items WHERE job_id=?",
            (job_id,),
        ).fetchone()
        con.execute("UPDATE jobs SET total=?,done=?,success=?,failed=?,bytes_done=?,heartbeat_at=?,progress_at=? WHERE id=?", (r["total"], r["done"], r["success"], r["failed"], r["bytes_done"], now_iso(), now_iso(), job_id))
        con.commit()


def _finish_job(job_id: int):
    _refresh_job_counts(job_id)
    with db() as con:
        r = con.execute("SELECT total,success,failed,cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
        if int(r["cancel_requested"] or 0):
            status = "cancelled"; message = "Cancelled"
        else:
            status = "finished" if int(r["failed"] or 0) == 0 else ("partial" if int(r["success"] or 0) > 0 else "failed")
            message = "Finished" if status == "finished" else f"Finished with {r['failed']} error(s)"
        con.execute("UPDATE jobs SET status=?,stage='done',message=?,finished_at=?,current_inventory_id=NULL,current_filename=NULL,worker_pid=NULL,heartbeat_at=?,progress_at=? WHERE id=?", (status, message, now_iso(), now_iso(), now_iso(), job_id))
        con.commit()


def _job_worker():
    while not STOP_EVENT.is_set():
        try:
            with db() as con:
                convert_running = con.execute("SELECT 1 FROM jobs WHERE status='running' AND kind='convert' LIMIT 1").fetchone()
                r = None if convert_running else con.execute("SELECT * FROM jobs WHERE status='queued' AND cancel_requested=0 AND kind<>'convert' ORDER BY id LIMIT 1").fetchone()
        except Exception as exc:  # e.g. "database is locked": never let the worker thread die
            log(f"job worker poll failed: {exc}"); time.sleep(2); continue
        if not r:
            time.sleep(0.5); continue
        job = _row_dict(r)
        from .platform_adapter import keep_awake
        _awake = keep_awake(); _awake.__enter__()       # an overnight import must not stop when the PC goes to sleep
        try:
            if job["kind"] in ("import", "import_analyze"):
                _run_import_analyze_job(job)
            elif job["kind"] == "analyze":
                _run_analyze_job(job)
            elif job["kind"] == "media_brain":
                _run_media_brain_job(job)
            elif job["kind"] == "archive":
                _run_archive_job(job)
            elif job["kind"] == "private":
                _run_private_job(job)
            elif job["kind"] == "reject":
                _run_reject_job(job)
            else:
                _job_update(job["id"], status="failed", stage="done", message="Unknown job kind", error=f"Unknown job kind {job['kind']}", finished_at=now_iso())
        except Exception as exc:
            log(f"job {job['id']} crashed: {exc}")
            try:
                _job_update(job["id"], status="failed", stage="done", message=f"Job crashed: {exc}", error=str(exc), finished_at=now_iso())
            except Exception as exc2:
                log(f"job {job['id']} could not be marked failed: {exc2}"); time.sleep(2)
        finally:
            _awake.__exit__(None, None, None)

def start_workers() -> None:
    global JOB_WORKER_STARTED
    with JOB_WORKER_LOCK:
        if not JOB_WORKER_STARTED:
            # Recovery only once per process: running it on every queue_job() reset the job that
            # was actually running to 'queued' (breaking the restart guard and the watchdog).
            init_db(); recover_jobs()
            threading.Thread(target=_job_worker,daemon=True,name="ArchivistJobWorker").start(); JOB_WORKER_STARTED=True


def queue_job(kind:str, ids:list[int], options:dict|None=None) -> int:
    start_workers(); return create_job(kind,ids,options)


def active_foreground_job() -> bool:
    with db() as con:
        return con.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running') AND kind IN ('import','import_analyze','analyze','media_brain','archive','private','reject','convert') LIMIT 1").fetchone() is not None


def latest_jobs(limit=20):
    with db() as con:
        rows=con.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?",(int(limit),)).fetchall()
        return [_row_dict(r) for r in rows]


def job_detail(job_id:int):
    with db() as con:
        j=con.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
        if not j: return None
        items=con.execute("SELECT ji.*,i.filename,i.source_label FROM job_items ji JOIN inventory i ON i.id=ji.inventory_id WHERE ji.job_id=? ORDER BY ji.seq",(job_id,)).fetchall()
        return {"job":_row_dict(j),"items":[_row_dict(x) for x in items]}


def retry_failed(job_id:int) -> int:
    with db() as con:
        ids=[int(r["inventory_id"]) for r in con.execute("SELECT inventory_id FROM job_items WHERE job_id=? AND status='error' ORDER BY seq",(job_id,)).fetchall()]
        old=con.execute("SELECT kind,options_json FROM jobs WHERE id=?",(job_id,)).fetchone()
    if not old or not ids: raise ValueError("No failed items to retry")
    return queue_job(old["kind"],ids,json.loads(old["options_json"] or "{}"))


def mark_private_forever(ids:list[int]) -> dict:
    # Compatibility helper for non-UI callers. UI uses durable jobs in v2.1.
    result={"private":0,"errors":0}
    for inv_id in ids:
        try: _mark_private_one(int(inv_id)); result["private"]+=1
        except Exception as exc: log(f"private {inv_id}: {exc}"); result["errors"]+=1
    return result


def reject_staging(ids:list[int]) -> dict:
    result={"rejected":0,"errors":0}
    for inv_id in ids:
        try: _reject_one(int(inv_id)); result["rejected"]+=1
        except Exception as exc: log(f"reject {inv_id}: {exc}"); result["errors"]+=1
    return result

def set_excluded(ids:list[int], excluded=True):
    if not ids: return
    with db() as con:
        q=','.join('?' for _ in ids); con.execute(f"UPDATE inventory SET excluded=? WHERE id IN ({q})",[1 if excluded else 0,*ids]); con.commit()


def remove_from_library(ids:list[int]) -> dict:
    """Remove items from the working Library without blacklisting their source.

    Archivist-owned Staging copies are moved to Rejected/Removed from Library (never
    hard-deleted). Source originals, Archive,
    Private, Rejected and ordinary fixed-local files are never deleted.
    Analysis/Media Brain metadata is preserved so re-adding the source does
    not throw away work already done.
    """
    ids=[int(x) for x in ids]
    result={"removed":0,"staging_deleted":0,"errors":[]}
    if not ids: return result
    with db() as con:
        q=','.join('?' for _ in ids)
        rows=con.execute(f"SELECT id,filename,staging_path FROM inventory WHERE excluded=0 AND id IN ({q})",ids).fetchall()
        removable=[]
        staging_root=STAGING.resolve()
        for r in rows:
            inv_id=int(r['id']); sp=r['staging_path']
            if sp:
                try:
                    p=Path(sp); rp=p.resolve()
                    if rp==staging_root or staging_root not in rp.parents:
                        result["errors"].append(f"{r['filename']}: invalid Staging path")
                        continue
                    if p.exists():
                        # Never hard-delete: the phone/card original may already be gone. The copy goes
                        # to a quarantine folder the user can empty deliberately.
                        qdir = REJECTED / "Removed from Library"; qdir.mkdir(parents=True, exist_ok=True)
                        dest = qdir / p.name
                        if dest.exists():
                            dest = qdir / f"{p.stem}_{inv_id}{p.suffix}"
                        shutil.move(str(p), str(dest))
                        result["staging_deleted"]+=1
                except Exception as exc:
                    log(f"remove library staging {inv_id}: {exc}")
                    result["errors"].append(f"{r['filename']}: could not move the Staging copy")
                    continue
            removable.append(inv_id)
        if removable:
            q2=','.join('?' for _ in removable)
            con.execute(
                f"""UPDATE inventory
                    SET work_selected=0,
                        staging_path=NULL,
                        import_status=CASE WHEN archive_path IS NOT NULL THEN 'archived' ELSE 'not_imported' END,
                        import_error=NULL,
                        error=NULL
                    WHERE id IN ({q2})""",
                removable,
            )
            con.commit()
    result["removed"]=len(removable)
    return result
