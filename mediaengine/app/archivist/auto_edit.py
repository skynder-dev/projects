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
        if _model_valid(cand):
            return cand
    for cand in model_search_roots():
        if (cand / "FAST_LOCAL" / "model_int8.onnx").exists():
            return cand
    return HOME / "models"


def model_search_roots() -> list[Path]:
    """This install first, then a stable Archivist installed next to it (read only)."""
    roots = [HOME / "models", HOME / "sidecars" / "auto_edit" / "models",
             HOME.parent / "Archivist" / "sidecars" / "auto_edit" / "models"]
    if os.name == "nt":  # a stable install at the root of any local drive, e.g. D:\Archivist
        for letter in "CDEFGH":
            roots.append(Path(f"{letter}:/") / "Archivist" / "sidecars" / "auto_edit" / "models")
    return roots


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


def _model_valid(root: Path) -> bool:
    """Same exact-identity check the engine preflight uses (model + tokenizer support files), cached by mtimes."""
    prof = Path(root) / "FAST_LOCAL"
    try:
        if not (prof / "model_int8.onnx").is_file():
            return False
        files = sorted([prof / "model_int8.onnx"] + [x for x in prof.glob("support_*/*") if x.is_file()])
        key = tuple((str(x), x.stat().st_size, x.stat().st_mtime_ns) for x in files)
    except OSError:
        return False
    hit = _MODEL_CACHE.get(str(prof))
    if hit and hit[0] == key:
        return hit[1]
    try:
        if str(ENGINE_DIR) not in sys.path:
            sys.path.insert(0, str(ENGINE_DIR))
        import validate_p11_model_contract as vc
        vc.validate("FAST_LOCAL", prof)
        ok = True
    except Exception:
        ok = False
    _MODEL_CACHE[str(prof)] = (key, ok)
    return ok


def model_status() -> dict:
    root = model_root()
    model = root / "FAST_LOCAL" / "model_int8.onnx"
    if not model.is_file():
        return {"ready": False, "reason": "MODEL_MISSING", "path": str(model)}
    if not _model_valid(root):
        return {"ready": False, "reason": "MODEL_FILES_INCOMPLETE_OR_CHANGED", "path": str(model)}
    return {"ready": True, "reason": "", "path": str(model)}


def model_identity() -> str:
    return MODEL_SHA if model_status()["ready"] else "none"


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

def folder_available(folder) -> bool:
    try:
        return Path(folder).is_dir()
    except OSError:
        return False


def list_videos(folder: Path) -> list[Path]:
    folder = Path(folder)
    try:
        if not folder.is_dir():
            return []
        vids = [p for p in folder.iterdir() if not p.name.startswith("._") and p.suffix.lower() in SUPPORTED and p.is_file()]
    except OSError:
        return []
    return sorted(vids, key=lambda p: p.name.lower())


def _probe(path: Path) -> dict:
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    import medeng_media_probe_v41 as probe_mod  # bundled engine probe (ffmpeg only)
    if not getattr(probe_mod, "_me_hidden", False):
        class _HiddenSubprocess:  # same API the module uses, but no console window on Windows
            def __getattr__(self, name):
                return getattr(subprocess, name)
            @staticmethod
            def run(*a, **k):
                return subprocess.run(*a, **process_kwargs(k))
        probe_mod.subprocess = _HiddenSubprocess()
        probe_mod._me_hidden = True
    return probe_mod.probe_json(path, _ffmpeg() or "ffmpeg", 30)


def scan_folder(folder) -> dict:
    """What the user sees before starting: usable files, problems, total footage."""
    folder = check_folder(folder)
    rows = []
    total = 0.0
    seen: dict[str, str] = {}
    for p in list_videos(folder)[: MAX_INPUTS + 1]:
        row = {"name": p.name, "bytes": 0, "ok": False, "reason": "", "duration_s": 0.0, "width": 0, "height": 0}
        try:
            row["bytes"] = p.stat().st_size
            qk = _quick_key(p)
        except OSError:
            row["reason"] = "cannot be read (locked or no access)"
            rows.append(row)
            continue
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
            "too_many": len(rows) > MAX_INPUTS, "total_s": round(total, 2), "total_bytes": sum(r["bytes"] for r in usable),
            "recommended_length": recommend_length(total)}


def check_folder(folder) -> Path:
    """A usable source folder: exists, absolute, not inside this app's private/rejected areas, at most 64 videos."""
    from .config import PRIVATE, REJECTED
    raw = str(folder or "").strip().strip('"')
    f = Path(raw)
    if not raw or not f.is_absolute() or not folder_available(f):
        raise ValueError("Folder not found")
    rf = f.resolve()
    for guarded in (PRIVATE, REJECTED):
        g = Path(guarded).resolve()
        if rf == g or g in rf.parents:
            raise ValueError("Private and Rejected media cannot be used in a reel")
    if len(list_videos(f)) > MAX_INPUTS:
        raise ValueError(f"This folder has more than {MAX_INPUTS} videos. Choose a folder with up to {MAX_INPUTS} videos "
                         "(for example, copy the clips for one reel into their own folder).")
    return f


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
    if r == "PRIVATE":
        return "marked Private in the library"
    if r == "NO_MOMENTS":
        return "no usable moments found"
    if r == "STATIC_VIDEO":
        return "almost no movement (still image)"
    if r == "ANALYSIS_TIMEOUT":
        return "analysis took too long"
    if r.startswith("ANALYSIS_FAILED"):
        return "could not be analysed"
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
    folder = check_folder(folder)
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
    d["source_present"] = folder_available(d["folder"])
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
    is_id = lambda x: re.fullmatch(r"[0-9a-f]{8,64}", str(x)) is not None
    exclude = sorted({str(x) for x in (raw.get("exclude") or []) if is_id(x)})
    out = {"format": fmt, "sound": sound, "length": length, "mode": mode, "exclude": exclude}
    # Manual edit: an explicit list of moments in the user's order, optional source-time trims.
    selection = [str(x) for x in (raw.get("selection") or []) if is_id(x)]
    if len(set(selection)) != len(selection):
        raise ValueError("The same moment is used twice")
    if len(selection) > 30:
        raise ValueError("At most 30 moments in one reel")
    trims = {}
    for k, v in (raw.get("trims") or {}).items():
        if not is_id(k) or k not in selection:
            continue
        a, b = round(parse_seconds(v[0]), 1), round(parse_seconds(v[1]), 1)
        if a < 0 or b - a < 0.5:
            raise ValueError("A trimmed moment must be at least 0.5 s long")
        if b - a > 60:
            raise ValueError("A single moment can be at most 60 s")
        trims[str(k)] = [a, b]
    if selection:
        out["selection"] = selection
        out["exclude"] = []
    if trims:
        out["trims"] = trims
    return out


def parse_seconds(v) -> float:
    """'12.5', '12,5' -> 12.5; rejects empty, NaN and infinity."""
    import math
    x = float(str(v).strip().replace(",", "."))
    if not math.isfinite(x):
        raise ValueError("Times must be numbers of seconds")
    return x


def _folder_fingerprint(folder: Path) -> list:
    out = []
    for p in list_videos(folder):
        try:
            st = p.stat()
            out.append([p.name, st.st_size, st.st_mtime_ns])
        except OSError:
            out.append([p.name, -1, -1])
    return out


_ENGINE_ID: dict = {}


def engine_identity() -> str:
    """Hash of every bundled engine file + the ffmpeg in use: an engine update never reuses old results."""
    files = sorted(ENGINE_DIR.glob("*.py"))
    key = tuple((x.name, x.stat().st_size, x.stat().st_mtime_ns) for x in files)
    if _ENGINE_ID.get("key") != key:
        h = hashlib.sha256()
        for x in files:
            h.update(x.name.encode()); h.update(x.read_bytes())
        h.update(str(_ffmpeg() or "ffmpeg").encode())
        _ENGINE_ID.update(key=key, value=h.hexdigest())
    return _ENGINE_ID["value"]


def _request_key(pid: int, folder: Path, settings: dict) -> str:
    raw = json.dumps({"project": int(pid), "inputs": _folder_fingerprint(folder), "settings": settings,
                      "engine": engine_identity(), "model": model_identity() if settings.get("mode") == "semantic" else "off",
                      # marking a file Private later must never reuse a reel that contains it
                      "private": hashlib.sha256("\n".join(_private_hashes()).encode()).hexdigest()},
                     sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def start_job(pid: int, raw_settings: dict, *, retry=False) -> int:
    """Queue a reel build. Same project + same inputs + same settings never builds twice."""
    ensure_schema()
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    folder = Path(p["folder"])
    if not folder_available(folder):
        raise ValueError("The source folder is not available (disconnected drive?)")
    settings = normalize_settings(raw_settings, model_ready=model_status()["ready"])
    key = _request_key(pid, folder, settings)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")  # lookup + insert as one step: a double click never queues twice
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


def job_elapsed_s(j: dict) -> float:
    """Seconds since the job started (or its total run time once finished); 0 while queued."""
    from datetime import datetime
    try:
        if not j.get("started_at"):
            return 0.0
        t0 = datetime.fromisoformat(j["started_at"])
        t1 = datetime.fromisoformat(j["finished_at"]) if j.get("finished_at") else datetime.now()
        return max(0.0, (t1 - t0).total_seconds())
    except (TypeError, ValueError):
        return 0.0


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
            cur = con.execute("UPDATE ae_jobs SET status='cancelled',stage='cancelled',finished_at=? WHERE id=? AND status='queued'", (now_iso(), jid))
            con.commit()
            if cur.rowcount:
                return True
    with _LOCK:
        _CANCEL.add(jid)
        proc = _RUNNING.get(jid)
    if proc is not None:
        _kill_tree(proc)
    return True


def _kill_tree(proc: subprocess.Popen) -> None:
    job = _JOB_HANDLES.get(proc.pid)
    if job is not None:
        try:
            import ctypes
            from ctypes import wintypes
            ctypes.windll.kernel32.TerminateJobObject(wintypes.HANDLE(job), 1)   # the engine and every ffmpeg it started
            return
        except Exception:
            pass
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
        jid = None
        try:
            with db() as con:
                r = con.execute("SELECT id FROM ae_jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
            if not r:
                _WAKE.wait(5)
                _WAKE.clear()
                continue
            jid = int(r["id"])
            _run_job(jid)
        except Exception as exc:  # never let the worker die
            try:
                if jid is not None:
                    with db() as con:
                        con.execute("UPDATE ae_jobs SET status='failed',stage='failed',error=?,finished_at=? WHERE id=? AND status IN ('queued','running')",
                                    (("Internal error: " + str(exc))[:500], now_iso(), jid))
                        con.commit()
            except Exception:
                pass
            time.sleep(1)


def _engine_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
    ff = _ffmpeg() or "ffmpeg"
    env.update({"MEDENG_FFMPEG": ff, "MEDENG_FFPROBE": ff, "MEDENG_P11_MODEL_ROOT": str(model_root()),
                "MEDENG_P11_ADAPTER_ROOT": str(ENGINE_DIR), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    return env


def engine_python() -> str:
    """Console python.exe next to pythonw.exe: started with CREATE_NO_WINDOW it owns ONE hidden console that all
    ffmpeg children inherit. Started from pythonw, every child would open its own visible console window."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        cand = exe.with_name("python.exe")
        if cand.exists():
            return str(cand)
    return str(exe)


_JOB_HANDLES: dict = {}


def _attach_job_object(proc: subprocess.Popen) -> None:
    """Windows: the engine dies with the app (no orphan writing into the cache after a crash or restart)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.CreateJobObjectW.restype = wintypes.HANDLE

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

        class EXTENDED(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        job = k32.CreateJobObjectW(None, None)
        if not job:
            return
        info = EXTENDED()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
        if k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(proc._handle))):
            _JOB_HANDLES[proc.pid] = job   # handle stays open for the app's lifetime of this job
    except Exception:
        pass


def engine_command(folder: Path, out_dir: Path, work_dir: Path, progress_file: Path, s: dict, edits_file: Path | None = None,
                   skip_sha_file: Path | None = None) -> list[str]:
    f = FORMATS[s["format"]]
    cmd = [engine_python(), "-s", "-E", "-X", "utf8", str(ORCHESTRATOR), "--input-dir", str(folder), "--output-dir", str(out_dir),
           "--work-dir", str(work_dir), "--runtime-dir", str(ENGINE_DIR), "--target-seconds", str(float(s["length"])),
           "--audio", s["sound"], "--semantic", "required" if s["mode"] == "semantic" else "off",
           "--profile", f["profile"], "--resolution", f["resolution"], "--progress-file", str(progress_file)]
    if edits_file is not None and (s.get("selection") or s.get("trims")):
        cmd += ["--edits", str(edits_file)]
    if s.get("exclude"):
        cmd += ["--exclude-events", ",".join(s["exclude"])]
    if skip_sha_file is not None:
        cmd += ["--skip-sha-file", str(skip_sha_file)]
    return cmd


def _set(jid: int, **fields) -> None:
    keys = ",".join(f"{k}=?" for k in fields)
    with db() as con:
        con.execute(f"UPDATE ae_jobs SET {keys} WHERE id=?", (*fields.values(), int(jid)))
        con.commit()


def _run_job(jid: int) -> None:
    with db() as con:  # claim: a job cancelled while queued is never started
        cur = con.execute("UPDATE ae_jobs SET status='running',stage='starting',done=0,total=0,message='',error=NULL,started_at=? WHERE id=? AND status='queued'",
                          (now_iso(), int(jid)))
        con.commit()
        if not cur.rowcount:
            return
    j = job(jid)
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
    edits_file = jobs_dir / f"j{jid}.edits.json"
    edits_file.write_text(json.dumps({"selection": s.get("selection") or [], "trims": s.get("trims") or {}}), encoding="utf-8")
    skip_file = jobs_dir / f"j{jid}.private_sha.txt"
    skip_file.write_text("\n".join(_private_hashes()), encoding="utf-8")
    cmd = engine_command(Path(p["folder"]), out_dir, work_dir, progress_file, s, edits_file, skip_file)
    kw = process_kwargs(below_normal=True) if os.name == "nt" else {"start_new_session": True}
    with log_file.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=_engine_env(), cwd=str(ENGINE_DIR), **kw)
        _attach_job_object(proc)
        with _LOCK:
            _RUNNING[jid] = proc
        try:
            while proc.poll() is None:
                with _LOCK:
                    want_cancel = jid in _CANCEL
                if want_cancel:
                    _kill_tree(proc)
                    proc.wait(30)
                    break
                try:
                    _pump_progress(jid, progress_file)
                except Exception:
                    pass
                time.sleep(0.5)
        except BaseException:
            _kill_tree(proc)   # never leave an engine running after the loop fails
            raise
        finally:
            with _LOCK:
                _RUNNING.pop(jid, None)
                cancelled = jid in _CANCEL
                _CANCEL.discard(jid)
            h = _JOB_HANDLES.pop(proc.pid, None)
            if h is not None:
                try:
                    import ctypes
                    from ctypes import wintypes
                    ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
                except Exception:
                    pass
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


def _private_hashes() -> list[str]:
    """SHA-256 of media marked Private (forever, or by the privacy check): never used in a reel."""
    try:
        with db() as con:
            rows = con.execute("SELECT sha256 FROM ignored_hashes UNION "
                               "SELECT sha256 FROM inventory WHERE analysis_status='private' AND sha256 IS NOT NULL").fetchall()
            return sorted({str(r["sha256"]).lower() for r in rows if r["sha256"]})
    except Exception:
        return []


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
    "TOO_MANY_INPUT_FILES": f"The folder has more than {MAX_INPUTS} videos.",
    "REALMEDIA_PIPELINE_FAILED": "Analysis of the footage failed.",
    "EDIT_UNKNOWN_MOMENT": "A chosen moment no longer exists (the source files changed). Start a new build.",
    "EDIT_SOURCE_MISSING": "The source file of a trimmed moment is not available.",
    "EDIT_TRIM_TOO_SHORT": "A trimmed moment is shorter than 0.5 s.",
    "NO_READABLE_VIDEO_FILES": "None of the videos in the folder can be used (damaged, duplicate or marked Private).",
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
    # Leftover files from an interrupted publish must not block the project: skip past them, never overwrite.
    while (rev_dir / f"R{n:03d}.mp4").exists() or (rev_dir / f"R{n:03d}.json").exists():
        n += 1
    vdst = rev_dir / f"R{n:03d}.mp4"
    rdst = rev_dir / f"R{n:03d}.json"
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


def accepted_history(log: list[dict]) -> list[int]:
    """Stack of accepted revisions: Accept pushes, Revert pops."""
    stack: list[int] = []
    for r in log:
        if r["action"] == "accept" and r["revision_id"] is not None:
            stack.append(int(r["revision_id"]))
        elif r["action"] == "revert" and stack:
            stack.pop()
    return stack


def revert(pid: int) -> int | None:
    """Move the accepted pointer back to the previously accepted revision (files untouched)."""
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("SELECT accepted_revision_id FROM ae_projects WHERE id=?", (int(pid),)).fetchone()
        if not cur:
            con.rollback()
            raise ValueError("Project not found")
        log = [dict(r) for r in con.execute("SELECT action,revision_id FROM ae_accept_log WHERE project_id=? ORDER BY id", (int(pid),)).fetchall()]
        stack = accepted_history(log)
        if stack:
            stack.pop()
        prev = stack[-1] if stack else None
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
        try:
            with open(dst, "xb"):   # atomic reservation: an existing file is never overwritten
                pass
            break
        except FileExistsError:
            try:
                if dst.stat().st_size == r["bytes"] and sha256_file(dst) == r["video_sha256"]:
                    return _record_export(pid, r, dst, reused=True)      # same export again: no-op
            except OSError:
                pass
            n += 1
    tmp = dest_dir / f".{dst.stem}.{os.getpid()}.{threading.get_ident()}.part"
    try:
        shutil.copyfile(src, tmp)
        if sha256_file(tmp) != r["video_sha256"]:
            raise RuntimeError("Export verification failed")
        os.replace(tmp, dst)   # replaces only our own empty reservation
    except BaseException:
        tmp.unlink(missing_ok=True)
        dst.unlink(missing_ok=True)
        raise
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
