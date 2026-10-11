"""Auto Edit inside the app: folder -> Length/Format/Sound -> background job on the
P11 R3 engine -> immutable revisions -> Accept/Revert -> Export one MP4.

Rules kept from the MediaEngine contract:
- source videos are referenced in place and never written to;
- one output preset per run, no hidden 1920x1080 default;
- semantic=required is the normal mode; without the exact FAST_LOCAL model the
  user must explicitly choose the labelled technical mode (no silent fallback);
- revisions are immutable, the accepted pointer moves only on Accept/Revert;
- export copies only the verified accepted revision, never overwrites.
"""
from __future__ import annotations

import hashlib, json, os, re, shutil, signal, subprocess, sys, threading, time
from pathlib import Path

from .config import DATA, HOME, load_config
from .db import db, now_iso
from .platform_adapter import process_kwargs

ENGINE_DIR = Path(__file__).resolve().parent / "engine_p11"
ORCHESTRATOR = ENGINE_DIR / "p11_folder_to_reel_r3.py"
AE_ROOT = DATA / "auto_edit"
EXPORTS = HOME / "Exports"
SUPPORTED = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
MAX_INPUTS = 64

# One output preset per run (contract 2026-10-03). Keys are what the UI submits.
FORMATS = {
    "social_hd": {"profile": "9x16", "resolution": "social_hd", "label": "Social HD · vertical 1080×1920", "short": "Social HD", "size": (1080, 1920)},
    "vertical": {"profile": "9x16", "resolution": "standard", "label": "Vertical 540×960", "short": "Vertical", "size": (540, 960)},
    "horizontal": {"profile": "16x9", "resolution": "standard", "label": "Horizontal 960×540", "short": "Horizontal", "size": (960, 540)},
}
SOUNDS = {"auto": "Auto (keep source sound, mute if it jumps)", "source": "Source sound", "mute": "Mute"}
LENGTHS = (5, 15, 30, 60)
MODES = {"semantic": "AI moments (FAST_LOCAL)", "technical": "Technical only (no AI model)"}

MODEL_SHA = "844d1a46ab18acf50c989e541b12fe3b6dc7f8d6004725b4e992d142788e0600"
MODEL_BYTES = 24281512

# Honest progress: weight of each real engine stage in the overall bar.
STAGE_SPAN = {"queued": (0, 0), "starting": (0, 1), "inputs": (1, 5), "analyze": (5, 60), "select": (60, 62),
              "trim": (62, 65), "render": (65, 95), "finish": (95, 99), "done": (100, 100)}
STAGE_LABEL = {"queued": "Waiting", "starting": "Starting", "inputs": "Checking files", "analyze": "Finding moments",
               "select": "Choosing moments", "trim": "Checking clip edges", "render": "Rendering segments",
               "finish": "Joining and verifying", "done": "Ready", "failed": "Failed", "cancelled": "Cancelled"}

_LOCK = threading.Lock()
_WAKE = threading.Event()
_WORKER: threading.Thread | None = None
_CANCEL: set[int] = set()
_RUNNING: dict[int, subprocess.Popen] = {}


# ---------------------------------------------------------------- utilities

def sha256_file(path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ffmpeg() -> str | None:
    from .media import _ffmpeg_exe
    return _ffmpeg_exe()


_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_filename(name: str, fallback: str = "MediaEngine Reel") -> str:
    """Windows-safe single path component (no separators, reserved names or trailing dots)."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", str(name or ""))
    s = re.sub(r"\s+", " ", s).strip().rstrip(". ")
    if not s:
        s = fallback
    if s.split(".")[0].upper() in _WIN_RESERVED:
        s = "_" + s
    return s[:120]


def model_root() -> Path:
    env = os.environ.get("MEDENG_P11_MODEL_ROOT")
    if env:
        return Path(env)
    cfg = load_config().get("auto_edit", {}) or {}
    if cfg.get("model_root"):
        return Path(cfg["model_root"])
    for cand in model_search_roots():
        if (cand / "FAST_LOCAL" / "model_int8.onnx").exists():
            return cand
    return HOME / "models"


def model_search_roots() -> list[Path]:
    """This install first, then a stable Archivist installed next to it (read only)."""
    return [HOME / "models", HOME / "sidecars" / "auto_edit" / "models",
            HOME.parent / "Archivist" / "sidecars" / "auto_edit" / "models"]


def import_model(src) -> dict:
    """Copy the exact FAST_LOCAL model (verified by the pinned validator) into this install's models folder."""
    src = Path(str(src or "").strip().strip('"'))
    candidates = [src, src / "models", src / "sidecars" / "auto_edit" / "models"]
    if src.name.upper() == "FAST_LOCAL":
        candidates.insert(0, src.parent)
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    import validate_p11_model_contract as vc
    root = None
    for c in candidates:
        try:
            vc.validate("FAST_LOCAL", c / "FAST_LOCAL")
            root = c
            break
        except Exception:
            continue
    if root is None:
        raise ValueError("No exact FAST_LOCAL model found there (model_int8.onnx + support_" + vc.COMMIT[:8] + "… with pinned hashes)")
    dst = HOME / "models" / "FAST_LOCAL"
    if root.resolve() == (HOME / "models").resolve():
        return {"path": str(dst), "copied": False}
    tmp = HOME / "models" / "FAST_LOCAL.__new__"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(root / "FAST_LOCAL", tmp)
    vc.validate("FAST_LOCAL", tmp)
    if dst.exists():
        shutil.rmtree(dst)
    os.replace(tmp, dst)
    _MODEL_CACHE.clear()
    cfg = load_config()
    cfg.setdefault("auto_edit", {})["model_root"] = str(HOME / "models")
    from .config import save_config
    save_config(cfg)
    return {"path": str(dst), "copied": True}


_MODEL_CACHE: dict = {}


def model_status() -> dict:
    """Exact-identity check of the FAST_LOCAL model (cached by size+mtime)."""
    root = model_root()
    model = root / "FAST_LOCAL" / "model_int8.onnx"
    if not model.is_file():
        return {"ready": False, "reason": "MODEL_MISSING", "path": str(model)}
    st = model.stat()
    key = (str(model), st.st_size, st.st_mtime_ns)
    if _MODEL_CACHE.get("key") != key:
        ok = st.st_size == MODEL_BYTES and sha256_file(model) == MODEL_SHA
        _MODEL_CACHE.update(key=key, ok=ok)
    if not _MODEL_CACHE["ok"]:
        return {"ready": False, "reason": "MODEL_HASH_MISMATCH", "path": str(model)}
    return {"ready": True, "reason": "", "path": str(model)}


# ---------------------------------------------------------------- schema

_SCHEMA_READY = False


def ensure_schema() -> None:
    """Create tables once per process; jobs left queued/running by a previous process become Retry-able failures."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    AE_ROOT.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS ae_projects(
              id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, folder TEXT NOT NULL,
              accepted_revision_id INTEGER, archived INTEGER NOT NULL DEFAULT 0,
              last_export_id INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS ae_jobs(
              id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES ae_projects(id),
              request_key TEXT NOT NULL, settings_json TEXT NOT NULL, status TEXT NOT NULL,
              stage TEXT, done INTEGER NOT NULL DEFAULT 0, total INTEGER NOT NULL DEFAULT 0, message TEXT,
              error TEXT, revision_id INTEGER, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_ae_jobs_project ON ae_jobs(project_id);
            CREATE INDEX IF NOT EXISTS idx_ae_jobs_key ON ae_jobs(request_key);
            CREATE TABLE IF NOT EXISTS ae_revisions(
              id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES ae_projects(id),
              job_id INTEGER NOT NULL, number INTEGER NOT NULL, video_path TEXT NOT NULL, result_path TEXT NOT NULL,
              video_sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, duration_s REAL, width INTEGER, height INTEGER,
              settings_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, number));
            CREATE TABLE IF NOT EXISTS ae_accept_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, revision_id INTEGER, action TEXT NOT NULL, at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS ae_exports(
              id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, revision_id INTEGER NOT NULL,
              path TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, created_at TEXT NOT NULL);
            """
        )
        # A job that was queued/running when the previous app process stopped has no live process any more.
        con.execute("UPDATE ae_jobs SET status='failed',stage='failed',error=?,finished_at=? WHERE status IN ('queued','running')",
                    ("Interrupted: the app was closed. Press Retry - finished analysis is reused.", now_iso()))
        con.commit()
    _SCHEMA_READY = True


# ---------------------------------------------------------------- folder scan

def list_videos(folder: Path) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    vids = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED]
    return sorted(vids, key=lambda p: p.name.lower())


def _probe(path: Path) -> dict:
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    from medeng_media_probe_v41 import probe_json  # bundled engine probe (ffmpeg only)
    return probe_json(path, _ffmpeg() or "ffmpeg", 30)


def scan_folder(folder) -> dict:
    """What the user sees before starting: usable files, problems, total footage."""
    folder = Path(str(folder or "").strip().strip('"'))
    if not str(folder) or not folder.is_dir():
        raise ValueError("Folder not found")
    rows = []
    total = 0.0
    seen: dict[str, str] = {}
    for p in list_videos(folder)[: MAX_INPUTS + 1]:
        row = {"name": p.name, "bytes": p.stat().st_size, "ok": False, "reason": "", "duration_s": 0.0, "width": 0, "height": 0}
        qk = _quick_key(p)
        if qk in seen:
            row["reason"] = "duplicate of " + seen[qk]
            rows.append(row)
            continue
        try:
            info = _probe(p)
            v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
            dur = float(info.get("format", {}).get("duration") or 0)
            if not v:
                row["reason"] = "no video stream"
            elif dur < 0.5:
                row["reason"] = "too short"
            else:
                row.update(ok=True, duration_s=round(dur, 2), width=int(v[0].get("width") or 0), height=int(v[0].get("height") or 0))
                total += dur
                seen[qk] = p.name
        except Exception:  # unreadable / damaged: skipped, never fatal for the folder
            row["reason"] = "damaged or not a video"
        rows.append(row)
    usable = [r for r in rows if r["ok"]]
    return {"folder": str(folder), "files": rows, "usable": len(usable), "skipped": len(rows) - len(usable),
            "too_many": len(rows) > MAX_INPUTS, "total_s": round(total, 2), "recommended_length": recommend_length(total)}


def _quick_key(p: Path) -> str:
    """Cheap identical-file key for the scan screen (size + first/last MiB). The engine re-checks with full SHA-256."""
    size = p.stat().st_size
    h = hashlib.sha256(str(size).encode())
    with p.open("rb") as fh:
        h.update(fh.read(1 << 20))
        if size > (2 << 20):
            fh.seek(-(1 << 20), os.SEEK_END)
            h.update(fh.read(1 << 20))
    return h.hexdigest()


def friendly_skip(reason: str) -> str:
    r = str(reason or "")
    if r.startswith("DUPLICATE_OF:"):
        return "duplicate of " + r.split(":", 1)[1]
    if "TOO_SHORT" in r:
        return "too short"
    if "NO_VIDEO_STREAM" in r:
        return "no video"
    return "damaged or not a video"


def recommend_length(total_s: float) -> int:
    """Adaptive default: never ask for more than the footage can honestly give."""
    t = float(total_s or 0)
    if t >= 90:
        return 30
    if t >= 30:
        return 15
    return 5


# ---------------------------------------------------------------- projects

def create_project(folder, title="") -> int:
    ensure_schema()
    folder = Path(str(folder or "").strip().strip('"'))
    if not folder.is_dir():
        raise ValueError("Folder not found")
    if not list_videos(folder):
        raise ValueError("This folder has no supported video files (.mp4 .mov .m4v .avi .mkv .webm)")
    ts = now_iso()
    name = str(title or "").strip()[:80] or folder.name or "Auto Edit"
    with db() as con:
        cur = con.execute("INSERT INTO ae_projects(title,folder,created_at,updated_at) VALUES(?,?,?,?)", (name, str(folder.resolve()), ts, ts))
        con.commit()
        return int(cur.lastrowid)


def _project_dir(pid: int) -> Path:
    return AE_ROOT / f"p{int(pid)}"


def project(pid: int) -> dict | None:
    ensure_schema()
    with db() as con:
        p = con.execute("SELECT * FROM ae_projects WHERE id=?", (int(pid),)).fetchone()
        if not p:
            return None
        d = dict(p)
        d["revisions"] = [dict(r) for r in con.execute("SELECT * FROM ae_revisions WHERE project_id=? ORDER BY number", (int(pid),)).fetchall()]
        d["jobs"] = [dict(r) for r in con.execute("SELECT * FROM ae_jobs WHERE project_id=? ORDER BY id DESC", (int(pid),)).fetchall()]
        d["exports"] = [dict(r) for r in con.execute("SELECT * FROM ae_exports WHERE project_id=? ORDER BY id DESC", (int(pid),)).fetchall()]
        d["accept_log"] = [dict(r) for r in con.execute("SELECT * FROM ae_accept_log WHERE project_id=? ORDER BY id", (int(pid),)).fetchall()]
    for r in d["revisions"]:
        r["settings"] = json.loads(r["settings_json"])
    for j in d["jobs"]:
        j["settings"] = json.loads(j["settings_json"])
        j["percent"] = job_percent(j)
    d["source_present"] = Path(d["folder"]).is_dir()
    d["state"] = project_state(d)
    return d


def project_state(d: dict) -> str:
    jobs = d.get("jobs") or []
    if any(j["status"] in ("queued", "running") for j in jobs):
        return "PROCESSING"
    if not d.get("source_present", True):
        return "ATTENTION"
    if d.get("accepted_revision_id"):
        return "READY"
    if d.get("revisions"):
        return "REVIEW"
    if jobs and jobs[0]["status"] == "failed":
        return "ATTENTION"
    return "DRAFT"


def list_projects(include_archived=False) -> list[dict]:
    ensure_schema()
    with db() as con:
        ids = [int(r["id"]) for r in con.execute(
            "SELECT id FROM ae_projects WHERE archived=0 OR ?=1 ORDER BY updated_at DESC, id DESC", (1 if include_archived else 0,)).fetchall()]
    return [project(i) for i in ids]


def rename_project(pid: int, title: str) -> None:
    t = str(title or "").strip()[:80]
    if not t:
        raise ValueError("Title is empty")
    with db() as con:
        con.execute("UPDATE ae_projects SET title=?,updated_at=? WHERE id=?", (t, now_iso(), int(pid)))
        con.commit()


def archive_project(pid: int, archived=True) -> None:
    """Registry-only: never deletes revisions, exports or sources."""
    with db() as con:
        con.execute("UPDATE ae_projects SET archived=?,updated_at=? WHERE id=?", (1 if archived else 0, now_iso(), int(pid)))
        con.commit()


# ---------------------------------------------------------------- jobs

def normalize_settings(raw: dict, *, model_ready: bool | None = None) -> dict:
    fmt = str(raw.get("format") or "social_hd")
    if fmt not in FORMATS:
        raise ValueError("Unknown format")
    sound = str(raw.get("sound") or "auto")
    if sound not in SOUNDS:
        raise ValueError("Unknown sound option")
    try:
        length = int(float(raw.get("length") or 0))
    except Exception:
        raise ValueError("Length must be a number of seconds")
    if length not in LENGTHS:
        raise ValueError("Length must be one of " + ", ".join(map(str, LENGTHS)) + " seconds")
    mode = str(raw.get("mode") or "semantic")
    if mode not in MODES:
        raise ValueError("Unknown selection mode")
    if mode == "semantic" and model_ready is False:
        raise ValueError("The AI model (FAST_LOCAL) is not available on this computer. Choose 'Technical only' explicitly or install the model.")
    exclude = sorted({x for x in (raw.get("exclude") or []) if re.fullmatch(r"[0-9a-f]{8,64}", str(x))})
    return {"format": fmt, "sound": sound, "length": length, "mode": mode, "exclude": exclude}


def _folder_fingerprint(folder: Path) -> list:
    return [[p.name, p.stat().st_size, p.stat().st_mtime_ns] for p in list_videos(folder)]


def _request_key(pid: int, folder: Path, settings: dict) -> str:
    raw = json.dumps({"project": int(pid), "inputs": _folder_fingerprint(folder), "settings": settings,
                      "engine": sha256_file(ORCHESTRATOR)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def start_job(pid: int, raw_settings: dict, *, retry=False) -> int:
    """Queue a reel build. Same project + same inputs + same settings never builds twice."""
    ensure_schema()
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    folder = Path(p["folder"])
    if not folder.is_dir():
        raise ValueError("The source folder is not available (disconnected drive?)")
    settings = normalize_settings(raw_settings, model_ready=model_status()["ready"])
    key = _request_key(pid, folder, settings)
    with db() as con:
        same = con.execute("SELECT * FROM ae_jobs WHERE project_id=? AND request_key=? ORDER BY id DESC LIMIT 1", (int(pid), key)).fetchone()
        if same and (same["status"] in ("queued", "running", "done")):
            return int(same["id"])
        ts = now_iso()
        cur = con.execute("INSERT INTO ae_jobs(project_id,request_key,settings_json,status,stage,created_at) VALUES(?,?,?,?,?,?)",
                          (int(pid), key, json.dumps(settings, sort_keys=True), "queued", "queued", ts))
        con.execute("UPDATE ae_projects SET updated_at=? WHERE id=?", (ts, int(pid)))
        con.commit()
        jid = int(cur.lastrowid)
    _ensure_worker()
    _WAKE.set()
    return jid


def job(jid: int) -> dict | None:
    with db() as con:
        r = con.execute("SELECT * FROM ae_jobs WHERE id=?", (int(jid),)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["settings"] = json.loads(d["settings_json"])
    d["percent"] = job_percent(d)
    d["stage_label"] = STAGE_LABEL.get(d["status"] if d["status"] in ("failed", "cancelled") else (d.get("stage") or "queued"), d.get("stage") or "")
    return d


def job_percent(j: dict) -> int:
    if j.get("status") == "done":
        return 100
    lo, hi = STAGE_SPAN.get(j.get("stage") or "queued", (0, 0))
    tot = int(j.get("total") or 0)
    frac = (int(j.get("done") or 0) / tot) if tot > 0 else 0.0
    return int(lo + (hi - lo) * max(0.0, min(1.0, frac)))


def cancel_job(jid: int) -> bool:
    jid = int(jid)
    with db() as con:
        r = con.execute("SELECT status FROM ae_jobs WHERE id=?", (jid,)).fetchone()
        if not r or r["status"] not in ("queued", "running"):
            return False
        if r["status"] == "queued":
            con.execute("UPDATE ae_jobs SET status='cancelled',stage='cancelled',finished_at=? WHERE id=?", (now_iso(), jid))
            con.commit()
            return True
    with _LOCK:
        _CANCEL.add(jid)
        proc = _RUNNING.get(jid)
    if proc is not None:
        _kill_tree(proc)
    return True


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=20, **process_kwargs())
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _ensure_worker() -> None:
    global _WORKER
    with _LOCK:
        if _WORKER and _WORKER.is_alive():
            return
        _WORKER = threading.Thread(target=_worker_loop, name="auto-edit-worker", daemon=True)
        _WORKER.start()


def _worker_loop() -> None:
    while True:
        with db() as con:
            r = con.execute("SELECT id FROM ae_jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        if not r:
            _WAKE.wait(5)
            _WAKE.clear()
            continue
        try:
            _run_job(int(r["id"]))
        except Exception as exc:  # never let the worker die
            with db() as con:
                con.execute("UPDATE ae_jobs SET status='failed',error=?,finished_at=? WHERE id=? AND status IN ('queued','running')",
                            (("Internal error: " + str(exc))[:500], now_iso(), int(r["id"])))
                con.commit()


def _engine_env() -> dict:
    env = dict(os.environ)
    ff = _ffmpeg() or "ffmpeg"
    env.update({"MEDENG_FFMPEG": ff, "MEDENG_FFPROBE": ff, "MEDENG_P11_MODEL_ROOT": str(model_root()),
                "MEDENG_P11_ADAPTER_ROOT": str(ENGINE_DIR), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    return env


def engine_command(folder: Path, out_dir: Path, work_dir: Path, progress_file: Path, s: dict) -> list[str]:
    f = FORMATS[s["format"]]
    cmd = [sys.executable, str(ORCHESTRATOR), "--input-dir", str(folder), "--output-dir", str(out_dir),
           "--work-dir", str(work_dir), "--runtime-dir", str(ENGINE_DIR), "--target-seconds", str(float(s["length"])),
           "--audio", s["sound"], "--semantic", "required" if s["mode"] == "semantic" else "off",
           "--profile", f["profile"], "--resolution", f["resolution"], "--progress-file", str(progress_file)]
    if s.get("exclude"):
        cmd += ["--exclude-events", ",".join(s["exclude"])]
    return cmd


def _set(jid: int, **fields) -> None:
    keys = ",".join(f"{k}=?" for k in fields)
    with db() as con:
        con.execute(f"UPDATE ae_jobs SET {keys} WHERE id=?", (*fields.values(), int(jid)))
        con.commit()


def _run_job(jid: int) -> None:
    j = job(jid)
    if not j or j["status"] != "queued":
        return
    p = project(j["project_id"])
    s = j["settings"]
    pdir = _project_dir(p["id"])
    work_dir = pdir / "work"            # shared per project: analysis cache is reused by variants
    jobs_dir = pdir / "jobs"
    out_dir = jobs_dir / f"j{jid}"
    progress_file = jobs_dir / f"j{jid}.progress.json"
    log_file = jobs_dir / f"j{jid}.log"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    progress_file.unlink(missing_ok=True)
    _set(jid, status="running", stage="starting", done=0, total=0, message="", error=None, started_at=now_iso())
    cmd = engine_command(Path(p["folder"]), out_dir, work_dir, progress_file, s)
    kw = process_kwargs() if os.name == "nt" else {"start_new_session": True}
    with log_file.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=_engine_env(), cwd=str(ENGINE_DIR), **kw)
        with _LOCK:
            _RUNNING[jid] = proc
        try:
            while proc.poll() is None:
                _pump_progress(jid, progress_file)
                time.sleep(0.5)
        finally:
            with _LOCK:
                _RUNNING.pop(jid, None)
                cancelled = jid in _CANCEL
                _CANCEL.discard(jid)
    _pump_progress(jid, progress_file)
    if cancelled:
        shutil.rmtree(out_dir, ignore_errors=True)   # never advertise a half-made reel
        _set(jid, status="cancelled", stage="cancelled", finished_at=now_iso(), message="Cancelled by user")
        return
    if proc.returncode != 0:
        shutil.rmtree(out_dir, ignore_errors=True)
        _set(jid, status="failed", stage="failed", finished_at=now_iso(), error=_engine_error(log_file))
        return
    rid = _publish_revision(p["id"], jid, out_dir, s)
    _set(jid, status="done", stage="done", done=1, total=1, revision_id=rid, finished_at=now_iso(), message="Ready")


def _pump_progress(jid: int, progress_file: Path) -> None:
    try:
        d = json.loads(progress_file.read_text(encoding="utf-8"))
    except Exception:
        return
    stage = str(d.get("stage") or "")
    if stage in ("failed",):
        return
    _set(jid, stage=stage, done=int(d.get("done") or 0), total=int(d.get("total") or 0), message=str(d.get("message") or "")[:300])


_FRIENDLY = {
    "SEMANTIC_RUNTIME_REQUIRED_BUT_NOT_EXACT": "The AI model files are missing or not the exact pinned version.",
    "NO_SUPPORTED_VIDEO_FILES": "No supported video files in the folder.",
    "NO_READABLE_VIDEO_FILES": "None of the videos in the folder could be read.",
    "INPUT_FOLDER_MISSING": "The source folder is not available.",
    "NO_DIVERSE_TARGET_COMBINATION": "Not enough different moments for this length. Try a shorter length.",
    "NO_EVENTS_SELECTED": "No usable moments were found. Try a shorter length or other footage.",
}


def _engine_error(log_file: Path) -> str:
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        text = ""
    m = re.findall(r'"error":\s*"([^"]+)"', text)
    raw = m[-1] if m else (text.strip().splitlines() or ["Engine stopped without a result"])[-1]
    for code, msg in _FRIENDLY.items():
        if code in raw:
            return msg + " [" + raw[:200] + "]"
    return raw[:500]


def _publish_revision(pid: int, jid: int, out_dir: Path, settings: dict) -> int:
    video = out_dir / "MediaEngine Reel.mp4"
    result = out_dir / "MediaEngine Result.json"
    res = json.loads(result.read_text(encoding="utf-8"))
    sha = sha256_file(video)
    if sha != res["output"]["sha256"]:
        raise RuntimeError("Rendered reel does not match its result manifest")
    rev_dir = _project_dir(pid) / "revisions"
    rev_dir.mkdir(parents=True, exist_ok=True)
    with db() as con:
        n = int(con.execute("SELECT COALESCE(MAX(number),0)+1 n FROM ae_revisions WHERE project_id=?", (int(pid),)).fetchone()["n"])
    vdst = rev_dir / f"R{n:03d}.mp4"
    rdst = rev_dir / f"R{n:03d}.json"
    if vdst.exists() or rdst.exists():
        raise RuntimeError("Revision file already exists; refusing to overwrite")
    os.replace(video, vdst)
    os.replace(result, rdst)
    shutil.rmtree(out_dir, ignore_errors=True)
    if sha256_file(vdst) != sha:
        raise RuntimeError("Revision copy verification failed")
    out = res.get("output", {})
    with db() as con:
        cur = con.execute(
            "INSERT INTO ae_revisions(project_id,job_id,number,video_path,result_path,video_sha256,bytes,duration_s,width,height,settings_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (int(pid), int(jid), n, str(vdst), str(rdst), sha, vdst.stat().st_size, float(res.get("actual_duration_s") or 0),
             int(out.get("width") or 0), int(out.get("height") or 0), json.dumps(settings, sort_keys=True), now_iso()))
        con.execute("UPDATE ae_projects SET updated_at=? WHERE id=?", (now_iso(), int(pid)))
        con.commit()
        return int(cur.lastrowid)


def revision(rid: int) -> dict | None:
    with db() as con:
        r = con.execute("SELECT * FROM ae_revisions WHERE id=?", (int(rid),)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["settings"] = json.loads(d["settings_json"])
    try:
        d["result"] = json.loads(Path(d["result_path"]).read_text(encoding="utf-8"))
    except Exception:
        d["result"] = {}
    return d


# ---------------------------------------------------------------- accept / revert

def accept(pid: int, rid: int) -> None:
    r = revision(rid)
    if not r or int(r["project_id"]) != int(pid):
        raise ValueError("Revision not found in this project")
    if sha256_file(r["video_path"]) != r["video_sha256"]:
        raise ValueError("Revision file changed on disk; it cannot be accepted")
    with db() as con:
        con.execute("UPDATE ae_projects SET accepted_revision_id=?,updated_at=? WHERE id=?", (int(rid), now_iso(), int(pid)))
        con.execute("INSERT INTO ae_accept_log(project_id,revision_id,action,at) VALUES(?,?,?,?)", (int(pid), int(rid), "accept", now_iso()))
        con.commit()


def revert(pid: int) -> int | None:
    """Move the accepted pointer back to the previously accepted revision (files untouched)."""
    with db() as con:
        cur = con.execute("SELECT accepted_revision_id FROM ae_projects WHERE id=?", (int(pid),)).fetchone()
        if not cur:
            raise ValueError("Project not found")
        log = [int(r["revision_id"]) for r in con.execute(
            "SELECT revision_id FROM ae_accept_log WHERE project_id=? AND action='accept' ORDER BY id", (int(pid),)).fetchall()]
        current = cur["accepted_revision_id"]
        prev = None
        if current is not None and current in log:
            idx = len(log) - 1 - log[::-1].index(current)
            earlier = [x for x in log[:idx] if x != current]
            prev = earlier[-1] if earlier else None
        con.execute("UPDATE ae_projects SET accepted_revision_id=?,updated_at=? WHERE id=?", (prev, now_iso(), int(pid)))
        con.execute("INSERT INTO ae_accept_log(project_id,revision_id,action,at) VALUES(?,?,?,?)", (int(pid), prev, "revert", now_iso()))
        con.commit()
    return prev


# ---------------------------------------------------------------- export

def export_accepted(pid: int, dest_dir: Path | None = None) -> dict:
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    if not p["accepted_revision_id"]:
        raise ValueError("Accept a revision before exporting")
    r = revision(p["accepted_revision_id"])
    src = Path(r["video_path"])
    if sha256_file(src) != r["video_sha256"]:
        raise ValueError("Accepted revision changed on disk; export refused")
    dest_dir = Path(dest_dir) if dest_dir else EXPORTS
    dest_dir.mkdir(parents=True, exist_ok=True)
    fmt = FORMATS.get(r["settings"]["format"], {}).get("short", "Reel")
    base = safe_filename(f"{p['title']} - {fmt} - R{int(r['number']):03d}")
    n = 1
    while True:
        dst = dest_dir / (base + (f" ({n})" if n > 1 else "") + ".mp4")
        if not dst.exists():
            break
        if dst.stat().st_size == r["bytes"] and sha256_file(dst) == r["video_sha256"]:
            return _record_export(pid, r, dst, reused=True)      # same export again: no-op
        n += 1
    tmp = dst.with_name(dst.name + ".part")
    shutil.copyfile(src, tmp)
    if sha256_file(tmp) != r["video_sha256"]:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Export verification failed")
    os.replace(tmp, dst)
    return _record_export(pid, r, dst, reused=False)


def _record_export(pid: int, r: dict, dst: Path, reused: bool) -> dict:
    with db() as con:
        row = con.execute("SELECT id FROM ae_exports WHERE project_id=? AND path=? AND sha256=?", (int(pid), str(dst), r["video_sha256"])).fetchone()
        if row:
            eid = int(row["id"])
        else:
            eid = int(con.execute("INSERT INTO ae_exports(project_id,revision_id,path,sha256,bytes,created_at) VALUES(?,?,?,?,?,?)",
                                  (int(pid), int(r["id"]), str(dst), r["video_sha256"], int(r["bytes"]), now_iso())).lastrowid)
        con.execute("UPDATE ae_projects SET last_export_id=?,updated_at=? WHERE id=?", (eid, now_iso(), int(pid)))
        con.commit()
    return {"export_id": eid, "path": str(dst), "sha256": r["video_sha256"], "reused": reused}


def export_row(eid: int) -> dict | None:
    with db() as con:
        r = con.execute("SELECT * FROM ae_exports WHERE id=?", (int(eid),)).fetchone()
    return dict(r) if r else None


def open_path(path: Path, reveal=False) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    if os.name == "nt":
        if reveal:
            subprocess.Popen(["explorer", "/select,", str(path)], **process_kwargs(hidden=False, below_normal=False))
        else:
            os.startfile(str(path))  # type: ignore[attr-defined]
        return True
    return False


# ---------------------------------------------------------------- source preview (path-safe)

def source_file(pid: int, name: str) -> Path | None:
    p = project(pid)
    if not p:
        return None
    folder = Path(p["folder"]).resolve()
    for v in list_videos(folder):
        if v.name == name:
            rp = v.resolve()
            if rp.parent == folder:
                return rp
    return None


# ---------------------------------------------------------------- Windows folder picker

def pick_folder(title="Choose a folder with your videos") -> str | None:
    """Native Windows folder dialog (SHBrowseForFolderW). Runs on a COM STA thread."""
    if os.name != "nt":
        return None
    box: dict = {}

    def run():
        import ctypes
        from ctypes import wintypes
        ole32 = ctypes.windll.ole32
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED

        class BROWSEINFOW(ctypes.Structure):
            _fields_ = [("hwndOwner", wintypes.HWND), ("pidlRoot", ctypes.c_void_p), ("pszDisplayName", wintypes.LPWSTR),
                        ("lpszTitle", wintypes.LPCWSTR), ("ulFlags", wintypes.UINT), ("lpfn", ctypes.c_void_p),
                        ("lParam", wintypes.LPARAM), ("iImage", ctypes.c_int)]

        shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
        shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
        shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
        ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        display = ctypes.create_unicode_buffer(260)
        bi = BROWSEINFOW()
        bi.hwndOwner = user32.GetForegroundWindow()
        bi.pszDisplayName = ctypes.cast(display, wintypes.LPWSTR)
        bi.lpszTitle = title
        bi.ulFlags = 0x0001 | 0x0040 | 0x0200  # RETURNONLYFSDIRS | NEWDIALOGSTYLE | NONEWFOLDERBUTTON
        pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
        if pidl:
            buf = ctypes.create_unicode_buffer(32768)
            if shell32.SHGetPathFromIDListW(pidl, buf):
                box["path"] = buf.value
            ole32.CoTaskMemFree(pidl)
        ole32.CoUninitialize()

    t = threading.Thread(target=run, name="folder-picker", daemon=True)
    t.start()
    t.join(600)
    return box.get("path")
