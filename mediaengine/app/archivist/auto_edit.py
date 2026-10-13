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

from .config import DATA, HOME, INSTALL, load_config
from .db import db, now_iso
from .platform_adapter import keep_awake, process_kwargs

ENGINE_DIR = Path(__file__).resolve().parent / "engine_p11"
ORCHESTRATOR = ENGINE_DIR / "p11_folder_to_reel_r3.py"
AE_ROOT = DATA / "auto_edit"
EXPORTS = HOME / "Exports"
SUPPORTED = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mts", ".m2ts", ".ts", ".3gp", ".mpg", ".mpeg",
             ".wmv", ".asf", ".flv", ".vob", ".mod", ".tod", ".m2t", ".dv"}   # + older Windows, web, DVD, tape camcorders
SUPPORTED_TEXT = ".mp4 .mov .m4v .avi .mkv .webm .mts .m2ts .ts .3gp .mpg .wmv .flv .vob .mod .tod .m2t .dv"
MAX_INPUTS = 64

# One output preset per run (contract 2026-10-03). Keys are what the UI submits.
FORMATS = {
    "social_hd": {"profile": "9x16", "resolution": "social_hd", "label": "Social HD · vertical 1080×1920", "short": "Social HD", "size": (1080, 1920)},
    "vertical": {"profile": "9x16", "resolution": "standard", "label": "Vertical 540×960", "short": "Vertical", "size": (540, 960)},
    "horizontal": {"profile": "16x9", "resolution": "standard", "label": "Horizontal 960×540", "short": "Horizontal", "size": (960, 540)},
}
SOUNDS = {"auto": "Auto (keep source sound, mute if it jumps)", "source": "Source sound", "mute": "Mute"}
LENGTHS = (5, 15, 30, 60)
MODES = {"semantic": "AI moments (FAST_LOCAL)", "semantic_plus": "AI+ moments (PE-Core L/14)", "technical": "Technical only (no AI model)"}
AI_MODES = ("semantic", "semantic_plus")
# AI+ themes: key -> name shown (English; Russian in auto_edit_ru). The descriptions are in the engine (p13_event_semantic_pe).
THEMES = {"sea": "Sea and beach", "mountains": "Mountains", "kids": "Children", "family": "Family and friends",
          "party": "Celebration", "animals": "Animals", "sunset": "Sunset", "nature": "Nature", "snow": "Winter and snow",
          "city": "City", "food": "Food", "sport": "Sport", "road": "Road trip"}

MODEL_SHA = "844d1a46ab18acf50c989e541b12fe3b6dc7f8d6004725b4e992d142788e0600"
MODEL_BYTES = 24281512

# Honest progress: weight of each real engine stage in the overall bar.
# shares of the whole build as measured (CI, 7 videos: analysis 12 %, cutting 34 %, final encode + check 50 %);
# the final stage has no steps of its own, so it starts well before the end instead of sitting at 95 % for minutes
STAGE_SPAN = {"queued": (0, 0), "starting": (0, 1), "inputs": (1, 5), "analyze": (5, 50), "select": (50, 51),
              "trim": (51, 54), "render": (54, 80), "finish": (80, 99), "done": (100, 100)}
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
    if s.split(".")[0].strip().upper() in _WIN_RESERVED:
        s = "_" + s
    return s[:120].rstrip(". ") or fallback


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
    roots = [HOME / "models", HOME / "sidecars" / "auto_edit" / "models"]
    if INSTALL != HOME:
        roots += [INSTALL / "models", INSTALL / "sidecars" / "auto_edit" / "models"]
    roots += [HOME.parent / "Archivist" / "sidecars" / "auto_edit" / "models",
              INSTALL.parent / "Archivist" / "sidecars" / "auto_edit" / "models"]
    if os.name == "nt":  # a stable install at the root of any local drive, e.g. D:\Archivist
        from .platform_adapter import _is_fixed_drive
        for letter in "CDEFGH":   # fixed disks only: a mapped network drive or an empty card reader would stall every page
            if _is_fixed_drive(f"{letter}:\\"):
                roots.append(Path(f"{letter}:/") / "Archivist" / "sidecars" / "auto_edit" / "models")
    return roots


def model_folder_hint() -> str | None:
    """Where the model folder window opens: an existing Archivist install's models folder, else the install itself."""
    for root in model_search_roots():
        if "Archivist" in root.parts and root.is_dir():
            return str(root)
    if os.name == "nt":
        from .platform_adapter import _is_fixed_drive
        for letter in "DCEF":
            a = Path(f"{letter}:/") / "Archivist"
            try:
                if _is_fixed_drive(f"{letter}:\\") and a.is_dir():
                    return str(a)
            except OSError:
                pass
    return None


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


# ---------------------------------------------------------------- AI+ model (PE-Core L/14, optional, ~680 MB)
# Not part of the package: the user downloads it once from Hugging Face (public, pinned commit, every file checked by
# size and SHA-256) with an explicit button, or copies the four files from another PC. Never downloaded on its own.

def aiplus_dir() -> Path:
    env = os.environ.get("MEDENG_P13_PE_DIR")
    return Path(env) if env else HOME / "models" / "PE_CORE_L14"


def _pe_contract():
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    import p13_pe_core_contract as pc
    return pc


_AIPLUS_CACHE: dict = {}
_AIPLUS_DL = {"state": "idle", "done": 0, "total": 0, "error": "", "file": ""}
_AIPLUS_STOP = threading.Event()
_AIPLUS_LOCK = threading.Lock()
_AIPLUS_STAMP = ".verified.json"     # sizes + times of files whose SHA-256 was checked: no 650 MB hash on every start


def _aiplus_key(d: Path, pc) -> tuple:
    return tuple((n, (d / n).stat().st_size, (d / n).stat().st_mtime_ns) for n in pc.ALL_FILES)


def _aiplus_mark_verified(d: Path, pc) -> None:
    key = _aiplus_key(d, pc)
    _AIPLUS_CACHE[str(d)] = (key, True)
    try:
        (d / _AIPLUS_STAMP).write_text(json.dumps([list(x) for x in key]), encoding="utf-8")
    except OSError:
        pass


def aiplus_status() -> dict:
    """{ready, reason, path, bytes, download}. Ready = every file has the exact size and was checked by SHA-256
    (once; remembered by size + modification time). The engine checks every SHA-256 again before each AI+ build."""
    pc = _pe_contract()
    d = aiplus_dir()
    out = {"ready": False, "reason": "AIPLUS_MISSING", "path": str(d), "bytes": pc.TOTAL_BYTES, "download": dict(_AIPLUS_DL)}
    try:
        key = _aiplus_key(d, pc)
    except OSError:
        return out
    with _AIPLUS_LOCK:
        hit = _AIPLUS_CACHE.get(str(d))
        if not hit or hit[0] != key:
            try:
                stamp = [tuple(x) for x in json.loads((d / _AIPLUS_STAMP).read_text(encoding="utf-8"))]
            except (OSError, ValueError, TypeError):
                stamp = None
            ok = stamp == list(key)
            if not ok:
                try:
                    pc.validate(d, True)
                    _aiplus_mark_verified(d, pc)
                    ok = True
                except Exception:
                    ok = False
            _AIPLUS_CACHE[str(d)] = (key, ok)
        ok = _AIPLUS_CACHE[str(d)][1]
    out.update(ready=ok, reason="" if ok else "AIPLUS_FILES_CHANGED")
    return out


def aiplus_downloading() -> bool:
    return _AIPLUS_DL["state"] == "running"


def _replace_retry(src: Path, dst: Path, tries: int = 10) -> None:
    """os.replace that waits for a virus scanner (or an open model) to let go of the file on Windows."""
    for k in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(1.0)


def aiplus_identity() -> str:
    pc = _pe_contract()
    return "PE_CORE_L14|" + pc.MODEL_REVISION + "|" + "|".join(v[2] for v in pc.ALL_FILES.values())


def aiplus_download_start() -> bool:
    """Start the one-time download in the background (False when it is already running)."""
    with _LOCK:
        if _AIPLUS_DL["state"] == "running":
            return False
        _AIPLUS_DL.update(state="running", done=0, total=0, error="", file="")
    _AIPLUS_STOP.clear()
    threading.Thread(target=_aiplus_download, name="aiplus-download", daemon=True).start()
    return True


def aiplus_download_cancel() -> None:
    _AIPLUS_STOP.set()


def _aiplus_download() -> None:
    import socket, urllib.error, urllib.request
    pc = _pe_contract()
    d = aiplus_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
        for x in d.glob("*.part"):          # left by an earlier stop, crash or Quit
            x.unlink(missing_ok=True)
        need = sum(v[1] for n, v in pc.ALL_FILES.items() if not ((d / n).is_file() and (d / n).stat().st_size == v[1]))
        if shutil.disk_usage(d).free < need + 500_000_000:
            raise RuntimeError("Not enough free disk space for the AI+ model (about " + str(round(need / 1e9, 1)) + " GB needed).")
        _AIPLUS_DL.update(total=pc.TOTAL_BYTES)
        done = 0
        for name, (_path, size, sha) in pc.ALL_FILES.items():
            dst = d / name
            _AIPLUS_DL.update(file=name)
            if dst.is_file() and dst.stat().st_size == size and sha256_file(dst) == sha:
                done += size
                _AIPLUS_DL.update(done=done)
                continue
            part = d / (name + ".part")
            req = urllib.request.Request(pc.download_url(name), headers={"User-Agent": "MediaEngine"})
            with urllib.request.urlopen(req, timeout=60) as r, part.open("wb") as fh:
                while True:
                    if _AIPLUS_STOP.is_set():
                        raise RuntimeError("Download cancelled.")
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    _AIPLUS_DL.update(done=done)
            if part.stat().st_size != size or sha256_file(part) != sha:
                part.unlink(missing_ok=True)
                raise RuntimeError("A downloaded file is not the exact model file (" + name + "). Try again.")
            _replace_retry(part, dst)
        with _AIPLUS_LOCK:
            _aiplus_mark_verified(d, pc)      # every file was just checked: no second 650 MB hash
        _AIPLUS_DL.update(state="done", done=pc.TOTAL_BYTES, file="")
    except Exception as exc:
        try:
            for x in d.glob("*.part"):
                x.unlink(missing_ok=True)
        except OSError:
            pass
        msg = str(exc)
        if isinstance(exc, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError)):
            msg = "No connection to huggingface.co. Check the internet connection and try again. [" + msg[:120] + "]"
        _AIPLUS_DL.update(state="failed", error=msg[:300])


def aiplus_import(src) -> dict:
    """Copy the exact AI+ files from a folder (e.g. copied from another PC): verified before and after copying."""
    pc = _pe_contract()
    if aiplus_downloading():
        raise ValueError("The AI+ model is being downloaded right now. Wait until it is finished or stop it first.")
    src = Path(str(src or "").strip().strip('"'))
    for cand in (src, src / "PE_CORE_L14", src / "models" / "PE_CORE_L14"):
        try:
            pc.validate(cand, True)
        except Exception:
            continue
        d = aiplus_dir()
        if cand.resolve() == d.resolve():
            return {"path": str(d), "copied": False}
        d.mkdir(parents=True, exist_ok=True)
        try:
            for name in pc.ALL_FILES:
                tmp = d / (name + ".part")
                shutil.copyfile(cand / name, tmp)
                _replace_retry(tmp, d / name)
        finally:
            for x in d.glob("*.part"):
                x.unlink(missing_ok=True)
        pc.validate(d, True)
        with _AIPLUS_LOCK:
            _aiplus_mark_verified(d, pc)
        return {"path": str(d), "copied": True}
    raise ValueError("No exact AI+ model there (vision_model_int8.onnx, text_model_int8.onnx, vocab.json, merges.txt).")


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
            CREATE TABLE IF NOT EXISTS ae_reviews(
              id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, left_revision_id INTEGER NOT NULL,
              right_revision_id INTEGER NOT NULL, choice TEXT, note TEXT, created_at TEXT NOT NULL, decided_at TEXT);
            """
        )
        if "files_json" not in [r[1] for r in con.execute("PRAGMA table_info(ae_projects)").fetchall()]:
            con.execute("ALTER TABLE ae_projects ADD COLUMN files_json TEXT")   # chosen files instead of a whole folder
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


# a shooting date in a file name: VID_20260714_123456, PXL_20260714_..., 2026-07-14 12.30.01, IMG-20260714-WA0003
_DAY_IN_NAME = re.compile(r"(?<!\d)(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?=\D|$|\d{6}(?:\D|$))")


def video_day(p: Path, mtime: float) -> str:
    m = _DAY_IN_NAME.search(Path(p).stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return time.strftime("%Y-%m-%d", time.localtime(mtime))


def videos_by_day(folder) -> list[dict]:
    """A folder with more videos than one reel takes (a phone camera folder): its videos grouped by the day they were
    shot (date in the file name, else the file's date), newest day first, so the user can pick a day or tick videos.
    Only file names and sizes are read here - nothing is opened."""
    days: dict[str, list] = {}
    for p in list_videos(Path(folder)):
        try:
            st = p.stat()
        except OSError:
            continue
        days.setdefault(video_day(p, st.st_mtime), []).append({"path": str(p), "name": p.name, "bytes": st.st_size})
    # newest first, also within a day (VID_20260714_183005 before VID_20260714_120001), so "tick the newest" is right
    return [{"day": d, "files": sorted(days[d], key=lambda f: f["name"].lower(), reverse=True)} for d in sorted(days, reverse=True)]


_SYSTEM_DIRS = {"$recycle.bin", "system volume information", "windows", "program files", "program files (x86)", "programdata",
                "appdata", "node_modules", "__pycache__", "thumbnails", ".thumbnails", "misc", "cache", ".cache"}


def subfolders_with_videos(folder, limit: int = 40, depth: int = 4, max_dirs: int = 3000) -> list[tuple[str, int]]:
    """For a folder with no videos of its own: the folders inside it (up to 4 levels: D:\\Videos\\2023, a camera card's
    DCIM\\100GOPRO or PRIVATE\\AVCHD\\BDMV\\STREAM) that do have videos, with how many, so the user can open one
    instead of guessing. Only folder listings are read; system folders are skipped."""
    out: list[tuple[str, int]] = []
    level, seen = [Path(folder)], 0
    for _ in range(depth):
        nxt = []
        for base in level:
            try:
                subs = sorted((d for d in base.iterdir() if d.is_dir() and not d.name.startswith((".", "$"))
                               and d.name.lower() not in _SYSTEM_DIRS), key=lambda d: d.name.lower())
            except OSError:
                continue
            for d in subs:
                seen += 1
                if seen > max_dirs:
                    return out
                try:
                    _guard_private(d)              # Private / Rejected are never offered (nor looked into)
                except ValueError:
                    continue
                except OSError:
                    pass
                n = len(list_videos(d))
                if n:
                    out.append((str(d), n))
                    if len(out) >= limit:
                        return out
                nxt.append(d)
        level = nxt
    return out


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


# A recording made in a web browser or by a screen recorder (and one stopped by a crash or a full disk) often has
# no length written in the file. The pictures and sound are fine, but the engine needs the length. Such a file is
# measured by reading it once; for a build it is copied once - without re-encoding - into the project's cache with
# the length filled in, and the engine works on that copy. The original is never changed.
_LENGTH_MAY_BE_MISSING = {".webm", ".mkv"}
_MEASURED: dict = {}
_TIME_RE = re.compile(r"time=\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def _measured_probe(path: Path) -> dict | None:
    """Probe of a file without a written length, with the length measured by reading the file (no decoding).
    None when the file really is unreadable."""
    try:
        st = path.stat()
    except OSError:
        return None
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key in _MEASURED:
        return _MEASURED[key]
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    import medeng_media_probe_v41 as probe_mod
    res = None
    try:
        cp = subprocess.run([_ffmpeg() or "ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:v:0", "-c", "copy",
                             "-f", "null", "-"], **process_kwargs(dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                                                    errors="replace", timeout=600, check=False)))
        text = cp.stderr or ""
        head = text
        for mark in ("\nOutput #", "\nStream mapping:"):    # only the input's description (a path may contain "Output #")
            head = head.split(mark, 1)[0]
        times = _TIME_RE.findall(text)
        dur = (int(times[-1][0]) * 3600 + int(times[-1][1]) * 60 + float(times[-1][2])) if times else 0.0
        streams = []
        for raw in head.splitlines():
            sm = probe_mod._STREAM_RE.match(raw)
            if not sm:
                continue
            row = {"index": int(sm.group(1)), "codec_type": sm.group(2).lower(), "codec_name": sm.group(3).lower()}
            zm = probe_mod._SIZE_RE.search(raw) if row["codec_type"] == "video" else None
            if zm:
                row["width"], row["height"] = int(zm.group(1)), int(zm.group(2))
            streams.append(row)
        if cp.returncode == 0 and dur > 0 and any(x["codec_type"] == "video" for x in streams):
            res = {"format": {"duration": f"{dur:.6f}"}, "streams": streams, "length_measured": True}
    except Exception:
        res = None
    _MEASURED[key] = res
    return res


def probe_any(path: Path) -> dict:
    """_probe, but a browser / screen recording without a written length is measured instead of being called
    damaged. Raises like _probe when the file cannot be used."""
    try:
        return _probe(path)
    except Exception as exc:
        if Path(path).suffix.lower() in _LENGTH_MAY_BE_MISSING and "DURATION_MISSING" in str(exc):
            got = _measured_probe(Path(path))
            if got:
                return got
        raise


def length_missing(path: Path) -> bool:
    """True for a .webm / .mkv whose length is not written in the file (quick check, the file is not read through)."""
    if Path(path).suffix.lower() not in _LENGTH_MAY_BE_MISSING:
        return False
    try:
        _probe(Path(path))
        return False
    except Exception as exc:
        return "DURATION_MISSING" in str(exc)


class _Stopped(Exception):
    """Cancel pressed while the inputs were being prepared."""


def _copy_with_length(src: Path, tmp: Path, jid=None) -> bool:
    """Stream copy (no re-encoding) into Matroska, which writes the length. Runs like the engine: in the build's job
    object, killed by Cancel."""
    cmd = [_ffmpeg() or "ffmpeg", "-v", "error", "-y", "-nostdin", "-i", str(src), "-map", "0:v", "-map", "0:a?", "-c", "copy",
           "-fflags", "+bitexact", "-f", "matroska", str(tmp)]
    kw = process_kwargs(below_normal=True) if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, **kw)
    _attach_job_object(proc)
    if jid is not None:
        with _LOCK:
            _RUNNING[jid] = proc
    try:
        t0 = time.time()
        while proc.poll() is None:
            with _LOCK:
                stop = jid is not None and jid in _CANCEL
            if stop or time.time() - t0 > 3600:
                _kill_tree(proc)
                proc.wait(30)
                if stop:
                    raise _Stopped()
                return False
            time.sleep(0.2)
        return proc.returncode == 0
    finally:
        if jid is not None:
            with _LOCK:
                if _RUNNING.get(jid) is proc:
                    _RUNNING.pop(jid, None)
        h = _JOB_HANDLES.pop(proc.pid, None)
        if h is not None:
            try:
                import ctypes
                from ctypes import wintypes
                ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
            except Exception:
                pass


def _with_length(paths, work_dir: Path, note=None, jid=None) -> tuple[list[Path], bool]:
    """The build's inputs, with every file that has no written length replaced by a copy (in the project's cache)
    that has it. A file marked Private is never copied (the copy would have another fingerprint) and an earlier
    copy of it is deleted, like copies of files that are no longer among the inputs. Raises _Stopped on Cancel."""
    out, changed, private = [], False, None
    fixed_dir = work_dir / "fixed_inputs"
    keep: set[str] = set()
    for p in paths:
        p = Path(p)
        with _LOCK:
            if jid is not None and jid in _CANCEL:
                raise _Stopped()
        if not length_missing(p):
            out.append(p)
            continue
        if private is None:
            private = set(_private_hashes())
        dst = fixed_dir / p.name
        stamp = fixed_dir / (p.name + ".source.json")
        tmp = fixed_dir / (p.name + ".part")          # never a video name, so never another input's copy
        try:
            if sha256_file(p) in private:
                out.append(p)                          # the engine skips it as unusable; it is never copied
                continue
            st = p.stat()
            want = {"source": str(p.resolve()), "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
            try:
                ok = dst.is_file() and json.loads(stamp.read_text(encoding="utf-8")) == want
            except (OSError, ValueError):
                ok = False
            if not ok:
                if note:
                    note(p.name)
                fixed_dir.mkdir(parents=True, exist_ok=True)
                if not _copy_with_length(p, tmp, jid) or not tmp.is_file():
                    tmp.unlink(missing_ok=True)
                    out.append(p)                      # the engine reports it as unusable
                    continue
                os.replace(tmp, dst)
                stamp_tmp = fixed_dir / (p.name + ".source.json.part")
                stamp_tmp.write_text(json.dumps(want), encoding="utf-8")
                os.replace(stamp_tmp, stamp)
            out.append(dst)
            keep.update({dst.name, stamp.name})
            changed = True
        except (OSError, ValueError, subprocess.SubprocessError):
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            out.append(p)
    if fixed_dir.is_dir():                              # copies of Private, removed or changed files go
        for x in fixed_dir.iterdir():
            if x.name not in keep:
                try:
                    x.unlink()
                except OSError:
                    pass
    return out, changed


def fixed_copy_seconds(pid: int, name: str) -> float:
    """Length of the fixed copy of a recording without a written length (0 when there is none). Quick."""
    try:
        cp = _project_dir(int(pid)) / "work" / "fixed_inputs" / name
        return float(_probe(cp).get("format", {}).get("duration") or 0) if cp.is_file() else 0.0
    except Exception:
        return 0.0


def scan_folder(folder) -> dict:
    """What the user sees before starting: usable files, problems, total footage."""
    folder = check_folder(folder)
    return _scan_paths(list_videos(folder)[: MAX_INPUTS + 1], str(folder), None)


def scan_files(files) -> dict:
    """Same as scan_folder for individually chosen files (they stay where they are)."""
    paths = check_files(files)
    return _scan_paths(paths, str(_common_parent(paths)), [str(x) for x in paths])


def _common_parent(paths) -> Path:
    try:
        return Path(os.path.commonpath([str(Path(x).parent) for x in paths]))
    except ValueError:              # different drives
        return Path(paths[0]).parent


# OneDrive "Files On-Demand" (and other cloud folders): a placeholder that is not on this PC. Reading even its
# first bytes makes Windows download the whole file - a folder of cloud-only videos would quietly download
# everything. Such files are skipped with a clear reason; the attribute is read from the folder listing only.
_CLOUD_ONLY_ATTRS = 0x1000 | 0x40000 | 0x400000      # OFFLINE | RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS
CLOUD_ONLY_REASON = "only in the cloud (OneDrive), not on this PC: choose 'Always keep on this device' first"


def cloud_only(p, st=None) -> bool:
    try:
        st = st if st is not None else os.stat(p)
    except OSError:
        return False
    return bool(getattr(st, "st_file_attributes", 0) & _CLOUD_ONLY_ATTRS)


def local_inputs(paths) -> list[Path]:
    """The videos that are really on this PC (cloud-only placeholders left out)."""
    return [Path(x) for x in paths if not cloud_only(x)]


def _scan_paths(paths, folder_label: str, files) -> dict:
    rows = []
    total = 0.0
    seen: dict[str, str] = {}
    for p in paths:
        row = {"name": p.name, "bytes": 0, "ok": False, "reason": "", "duration_s": 0.0, "width": 0, "height": 0}
        try:
            st = p.stat()
            if cloud_only(p, st):
                row["bytes"], row["reason"] = st.st_size, CLOUD_ONLY_REASON
                rows.append(row)
                continue
            row["bytes"] = st.st_size
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
            info = probe_any(p)
            v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
            dur = float(info.get("format", {}).get("duration") or 0)
            if not v:
                row["reason"] = "no video stream"
            elif dur < MIN_CLIP_S:      # the analysis needs a few frames a second apart: shorter clips always fail it
                row["reason"] = "too short (under 2.5 s)"
            else:
                row.update(ok=True, duration_s=round(dur, 2), width=int(v[0].get("width") or 0), height=int(v[0].get("height") or 0),
                           length_measured=bool(info.get("length_measured")))
                total += dur
                seen[qk] = p.name
        except Exception:  # unreadable / damaged: skipped, never fatal for the folder
            row["reason"] = "damaged or not a video"
        rows.append(row)
    usable = [r for r in rows if r["ok"]]
    return {"folder": folder_label, "files_chosen": files, "files": rows, "usable": len(usable), "skipped": len(rows) - len(usable),
            "too_many": len(rows) > MAX_INPUTS, "total_s": round(total, 2), "total_bytes": sum(r["bytes"] for r in usable),
            "recommended_length": recommend_length(total)}


def _guard_private(f: Path) -> None:
    from .config import PRIVATE, REJECTED
    rf = Path(f).resolve()
    for guarded in (PRIVATE, REJECTED):
        g = Path(guarded).resolve()
        if rf == g or g in rf.parents:
            raise ValueError("Private and Rejected media cannot be used in a reel")


def check_files(files) -> list[Path]:
    """Individually chosen videos: absolute, existing, supported, unique names (the reel refers to sources by name)."""
    out, names = [], set()
    for raw in files or []:
        raw = str(raw or "").strip().strip('"')
        if not raw:
            continue
        f = Path(raw)
        if not f.is_absolute() or not f.is_file():
            raise ValueError(f"File not found: {raw}")
        if f.suffix.lower() not in SUPPORTED or f.name.startswith("._"):
            raise ValueError(f"Not a supported video file: {f.name} ({SUPPORTED_TEXT})")
        _guard_private(f)
        if f.name.lower() in names:
            raise ValueError(f"Two chosen files have the same name ({f.name}). Rename one of them, or choose a folder.")
        names.add(f.name.lower())
        out.append(f.resolve())
    if not out:
        raise ValueError("No video files chosen")
    if len(out) > MAX_INPUTS:
        raise ValueError(f"Choose at most {MAX_INPUTS} videos for one reel.")
    return sorted(out, key=lambda x: x.name.lower())


def project_inputs(p: dict) -> list[Path]:
    """The project's source videos: the chosen files, or the supported videos in its folder."""
    if p.get("files"):
        return [Path(x) for x in p["files"] if Path(x).is_file()]
    return list_videos(Path(p["folder"]))


def check_folder(folder) -> Path:
    """A usable source folder: exists, absolute, not inside this app's private/rejected areas, at most 64 videos."""
    from .config import PRIVATE, REJECTED
    raw = str(folder or "").strip().strip('"')
    f = Path(raw)
    if not raw or not f.is_absolute() or not folder_available(f):
        raise ValueError("Folder not found")
    _guard_private(f)
    if len(list_videos(f)) > MAX_INPUTS:
        raise ValueError(f"This folder has more than {MAX_INPUTS} videos. Use 'Choose videos…' to pick up to {MAX_INPUTS} of them, "
                         "or choose a folder with fewer videos.")
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
    if r == "TOO_SHORT_FOR_ANALYSIS":
        return "too short to analyse"
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

def create_project(folder, title="", files=None) -> int:
    ensure_schema()
    chosen = None
    if files:
        paths = check_files(files)
        chosen = json.dumps([str(x) for x in paths])
        folder = _common_parent(paths)
    else:
        folder = check_folder(folder)
        if not list_videos(folder):
            raise ValueError(f"This folder has no supported video files ({SUPPORTED_TEXT})")
    ts = now_iso()
    name = str(title or "").strip()[:80] or folder.name or "Auto Edit"
    if files and not str(title or "").strip():      # one shooting day picked from a big folder: "Camera 2026-07-14"
        picked = [Path(x) for x in json.loads(chosen)]
        days = {video_day(x, 0) for x in picked}
        if len(days) == 1 and all(_DAY_IN_NAME.search(x.stem) for x in picked):
            name = f"{name} {days.pop()}"[:80]
    with db() as con:
        cur = con.execute("INSERT INTO ae_projects(title,folder,files_json,created_at,updated_at) VALUES(?,?,?,?,?)",
                          (name, str(folder.resolve()), chosen, ts, ts))
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
        d["reviews"] = [dict(r) for r in con.execute("SELECT * FROM ae_reviews WHERE project_id=? ORDER BY id DESC", (int(pid),)).fetchall()]
    for r in d["revisions"]:
        r["settings"] = json.loads(r["settings_json"])
    for j in d["jobs"]:
        j["settings"] = json.loads(j["settings_json"])
        j["percent"] = job_percent(j)
    d["files"] = json.loads(d.get("files_json") or "null") or None
    d["source_present"] = all(Path(x).is_file() for x in d["files"]) if d["files"] else folder_available(d["folder"])
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
    if mode == "semantic_plus" and not aiplus_status()["ready"]:
        raise ValueError("The AI+ model is not on this computer yet. Download it once on 'Check this PC' or choose another mode.")
    theme = str(raw.get("theme") or "")
    if theme and theme not in THEMES:
        raise ValueError("Unknown theme")
    if mode != "semantic_plus":
        theme = ""                       # themes need AI+ (the descriptions of the accepted AI model are fixed)
    is_id = lambda x: re.fullmatch(r"[0-9a-f]{8,64}", str(x)) is not None
    exclude = sorted({str(x) for x in (raw.get("exclude") or []) if is_id(x)})
    out = {"format": fmt, "sound": sound, "length": length, "mode": mode, "exclude": exclude}
    if theme:
        out["theme"] = theme
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
    """'12.5', '12,5', '0:12.5', '1:05', '1:02:03' -> seconds. Rejects empty, negative, NaN and infinity."""
    import math
    raw = str(v).strip().replace(",", ".")
    try:
        if ":" in raw:
            parts = raw.split(":")
            if len(parts) > 3 or any(not x.strip() for x in parts):
                raise ValueError
            x = 0.0
            for part in parts:
                x = x * 60 + float(part)
            if any(float(part) >= 60 for part in parts[1:]):
                raise ValueError
        else:
            x = float(raw)
    except ValueError:
        raise ValueError(f"Not a time: {str(v)[:20]!r} (use seconds like 12.5 or minutes like 1:05)")
    if not math.isfinite(x) or x < 0:
        raise ValueError("Times must be zero or more seconds")
    return x


def _inputs_fingerprint(p: dict) -> list:
    out = []
    for p in project_inputs(p):
        try:
            st = p.stat()
            # a cloud-only file is not used; once it is downloaded the same reel must be built again with it
            out.append([p.name, st.st_size, st.st_mtime_ns] + (["cloud-only"] if cloud_only(p, st) else []))
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


def _request_key(p: dict, settings: dict) -> str:
    pid = int(p["id"])
    raw = json.dumps({"project": int(pid), "inputs": _inputs_fingerprint(p), "settings": settings,
                      "engine": engine_identity(), "model": (model_identity() if settings.get("mode") == "semantic" else
                                                             aiplus_identity() if settings.get("mode") == "semantic_plus" else "off"),
                      # marking a file Private later must never reuse a reel that contains it
                      "private": hashlib.sha256("\n".join(_private_hashes()).encode()).hexdigest()},
                     sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


MIN_FREE_BYTES = 1_000_000_000
MIN_CLIP_S = 2.5   # measured: 2.0 s phone clips are rejected by the accepted analysis (fewer than 3 samples, 1 s apart)


def check_free_space() -> None:
    """Refuse to start a build that would surely fail half-way on a full data drive."""
    try:
        AE_ROOT.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(AE_ROOT).free
    except OSError:
        return
    if free < MIN_FREE_BYTES:
        raise ValueError(f"Not enough free space on the data drive: {free / 1e9:.1f} GB. "
                         "A reel needs at least 1 GB to work in. Free some space (for example 'Free cache' on old projects) and try again.")


def start_job(pid: int, raw_settings: dict, *, retry=False) -> int:
    """Queue a reel build. Same project + same inputs + same settings never builds twice."""
    ensure_schema()
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    if not p["source_present"]:
        raise ValueError("The source videos are not available (disconnected drive?)" if p["files"] else
                         "The source folder is not available (disconnected drive?)")
    settings = normalize_settings(raw_settings, model_ready=model_status()["ready"])
    key = _request_key(p, settings)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")  # lookup + insert as one step: a double click never queues twice
        same = con.execute("SELECT * FROM ae_jobs WHERE project_id=? AND request_key=? ORDER BY id DESC LIMIT 1", (int(pid), key)).fetchone()
        if same and (same["status"] in ("queued", "running", "done")):
            return int(same["id"])
        check_free_space()
        ts = now_iso()
        cur = con.execute("INSERT INTO ae_jobs(project_id,request_key,settings_json,status,stage,created_at) VALUES(?,?,?,?,?,?)",
                          (int(pid), key, json.dumps(settings, sort_keys=True), "queued", "queued", ts))
        con.execute("UPDATE ae_projects SET updated_at=? WHERE id=?", (ts, int(pid)))
        con.commit()
        jid = int(cur.lastrowid)
    _ensure_worker()
    _WAKE.set()
    return jid


def recent_jobs(limit: int = 20) -> list[dict]:
    """Latest reel builds of all projects (for Activity → Jobs)."""
    ensure_schema()
    with db() as con:
        rows = con.execute("SELECT j.id, j.project_id, j.status, j.stage, j.error, j.settings_json, j.created_at, j.finished_at, "
                           "p.title FROM ae_jobs j JOIN ae_projects p ON p.id=j.project_id ORDER BY j.id DESC LIMIT ?", (int(limit),)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["settings"] = json.loads(d.pop("settings_json") or "{}")
        d["label"] = STAGE_LABEL.get(d["status"] if d["status"] in ("failed", "cancelled", "done") else (d.get("stage") or "queued"), d["status"])
        out.append(d)
    return out


def job(jid: int) -> dict | None:
    ensure_schema()
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
        # stored as local wall-clock time: made zone-aware before subtracting, so a build that runs across a summer /
        # winter clock change does not show an hour too much or too little
        t0 = datetime.fromisoformat(j["started_at"]).astimezone()
        t1 = datetime.fromisoformat(j["finished_at"]).astimezone() if j.get("finished_at") else datetime.now().astimezone()
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
    env.update({"MEDENG_FFMPEG": ff, "MEDENG_FFPROBE": ff, "MEDENG_P11_MODEL_ROOT": str(model_root()), "MEDENG_P13_PE_DIR": str(aiplus_dir()),
                "MEDENG_P13_TEXT_CACHE": str(AE_ROOT / "shared" / "semantic_text_pe"),
                "MEDENG_P11_ADAPTER_ROOT": str(ENGINE_DIR), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1"})   # engine helpers started without -E: nothing written into the program folder
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
                   skip_sha_file: Path | None = None, input_list: Path | None = None) -> list[str]:
    f = FORMATS[s["format"]]
    src = ["--input-list", str(input_list)] if input_list is not None else ["--input-dir", str(folder)]
    cmd = [engine_python(), "-B", "-s", "-E", "-X", "utf8", str(ORCHESTRATOR), *src, "--output-dir", str(out_dir),
           "--work-dir", str(work_dir), "--runtime-dir", str(ENGINE_DIR), "--target-seconds", str(float(s["length"])),
           "--audio", s["sound"], "--semantic", "required" if s["mode"] in AI_MODES else "off",
           *(["--semantic-model", "pe_core_l14"] if s["mode"] == "semantic_plus" else []),
           *(["--theme", s["theme"]] if s["mode"] == "semantic_plus" and s.get("theme") else []),
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
    input_list = None
    note = lambda name: _set(jid, message="Preparing a recording without a length: " + name)
    try:
        with keep_awake():
            if p.get("files"):
                local, _ = _with_length(local_inputs(p["files"]), work_dir, note, jid)
                input_list = jobs_dir / f"j{jid}.inputs.txt"
                input_list.write_text("\n".join(str(x) for x in local) + "\n", encoding="utf-8")
            else:
                vids = list_videos(Path(p["folder"]))
                local, fixed = _with_length(local_inputs(vids), work_dir, note, jid)
                if fixed or len(local) != len(vids):   # cloud-only placeholders / fixed copies: give the engine the exact list
                    input_list = jobs_dir / f"j{jid}.inputs.txt"
                    input_list.write_text("\n".join(str(x) for x in local) + "\n", encoding="utf-8")
    except _Stopped:
        with _LOCK:
            _CANCEL.discard(jid)
        _set(jid, status="cancelled", stage="cancelled", finished_at=now_iso(), message="Cancelled by user")
        return
    cmd = engine_command(Path(p["folder"]), out_dir, work_dir, progress_file, s, edits_file, skip_file, input_list)
    kw = process_kwargs(below_normal=True) if os.name == "nt" else {"start_new_session": True}
    with log_file.open("w", encoding="utf-8", errors="replace") as log, keep_awake():
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
    "AIPLUS_MODEL_NOT_READY": "The AI+ model files are missing or changed. Download the AI+ model again on 'Check this PC'.",
    "AIPLUS_MODEL_LOAD_FAILED": "The AI+ model could not be started (not enough memory?). Close other programs and press Retry, or use AI.",
    "NO_SUPPORTED_VIDEO_FILES": "No supported video files in the folder.",
    "TOO_MANY_INPUT_FILES": f"The folder has more than {MAX_INPUTS} videos.",
    "REALMEDIA_PIPELINE_FAILED": "Analysis of the footage failed.",
    "EDIT_UNKNOWN_MOMENT": "A chosen moment no longer exists (the source files changed or the cache was freed). "
                           "Use 'Let MediaEngine choose again' or make a new reel.",
    "NO_ANALYZABLE_VIDEO_FILES": "None of the videos could be analysed (too short, still images or damaged).",
    "NO_MOMENTS_LEFT_AFTER_EXCLUSIONS": "All moments were removed. Remove fewer moments or let MediaEngine choose again.",
    "PRESET_NOT_ACCEPTED": "This format is not available.",
    "INPUT_NAMES_NOT_UNIQUE": "Two chosen videos have the same file name. Rename one of them.",
    "SEGMENT_DECODE_FAILED": "A rendered piece could not be read back. Try again; if it repeats, free the cache.",
    "No space left on device": "The disk is full. Free some space (for example 'Free cache' on old projects) and press Retry.",
    "There is not enough space on the disk": "The disk is full. Free some space (for example 'Free cache' on old projects) and press Retry.",
    "Permission denied": "Windows refused access to a file (another program may be using it). Close it and press Retry.",
    "Access is denied": "Windows refused access to a file (another program may be using it). Close it and press Retry.",
    "MemoryError": "The PC ran out of memory. Close other programs or choose fewer / shorter videos, then Retry.",
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
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("SELECT accepted_revision_id FROM ae_projects WHERE id=?", (int(pid),)).fetchone()
        if cur and cur[0] is not None and int(cur[0]) == int(rid):
            con.rollback()          # already the accepted one (a second click): nothing to record, Revert stays right
            return
        con.execute("UPDATE ae_projects SET accepted_revision_id=?,updated_at=? WHERE id=?", (int(rid), now_iso(), int(pid)))
        con.execute("INSERT INTO ae_accept_log(project_id,revision_id,action,at) VALUES(?,?,?,?)", (int(pid), int(rid), "accept", now_iso()))
        con.commit()


def accepted_history(log: list[dict]) -> list[int]:
    """Stack of accepted revisions: Accept pushes, Revert pops."""
    stack: list[int] = []
    for r in log:
        if r["action"] == "accept" and r["revision_id"] is not None:
            if stack and stack[-1] == int(r["revision_id"]):
                continue            # the same one accepted twice in a row (double click in older builds)
            stack.append(int(r["revision_id"]))
        elif r["action"] == "revert" and stack:
            stack.pop()
    return stack


def previous_accepted(pid: int) -> int | None:
    """The revision Revert would go back to (None: Revert only un-accepts)."""
    with db() as con:
        log = [dict(r) for r in con.execute("SELECT action,revision_id FROM ae_accept_log WHERE project_id=? ORDER BY id", (int(pid),)).fetchall()]
    stack = accepted_history(log)
    return stack[-2] if len(stack) >= 2 else None


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

def revision_thumb(rid: int, pos: int) -> Path | None:
    """Small JPEG of a moment in a revision (filmstrip). Cached next to the project's data; never touches sources."""
    r = revision(rid)
    if not r:
        return None
    seg = next((x for x in ((r.get("result") or {}).get("segments") or []) if int(x.get("position", 0)) == int(pos)), None)
    if not seg:
        return None
    out = _project_dir(r["project_id"]) / "thumbs" / f"r{int(rid)}_{int(pos)}.jpg"
    if out.is_file() and out.stat().st_size > 0:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    t = (float(seg["reel_in_s"]) + float(seg["reel_out_s"])) / 2.0
    tmp = out.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part.jpg")
    try:
        subprocess.run([_ffmpeg() or "ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(r["video_path"]), "-frames:v", "1",
                        "-vf", "scale=-2:120", "-q:v", "4", str(tmp)], **process_kwargs({"capture_output": True, "timeout": 60}))
        if tmp.is_file() and tmp.stat().st_size > 0:
            os.replace(tmp, out)
            return out
    except Exception:
        pass
    finally:
        tmp.unlink(missing_ok=True)
    return None


# ---------------------------------------------------------------- "Check this PC"

def system_check() -> list[dict]:
    """What the user (or support) needs to know about this PC before blaming a reel. Read-only."""
    rows = []

    def add(name, ok, detail, level="ok"):
        rows.append({"name": name, "ok": bool(ok), "detail": str(detail), "level": level if ok else "bad"})
    from .config import INSTALL
    add("Program folder", True, INSTALL)
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        probe = DATA / f".write_test_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8"); probe.unlink()
        add("Data folder (projects, exports)", True, HOME)
    except OSError as exc:
        add("Data folder (projects, exports)", False, f"{HOME}: not writable ({exc})")
    try:
        free = shutil.disk_usage(HOME).free
        add("Free space on the data drive", free > 5e9, f"{free / 1e9:.1f} GB" + ("" if free > 5e9 else " - less than 5 GB, builds may fail"))
    except OSError as exc:
        add("Free space on the data drive", False, exc)
    ff = _ffmpeg()
    if ff:
        try:
            ver = subprocess.run([ff, "-hide_banner", "-version"], **process_kwargs({"capture_output": True, "text": True, "timeout": 30})).stdout.splitlines()[0]
            filt = subprocess.run([ff, "-hide_banner", "-filters"], **process_kwargs({"capture_output": True, "text": True, "timeout": 30})).stdout
            add("FFmpeg", True, ver)
            add("HDR phone video conversion (zscale)", " zscale " in filt, "available" if " zscale " in filt else "missing - HDR video will look grey")
        except Exception as exc:
            add("FFmpeg", False, exc)
    else:
        add("FFmpeg", False, "not found")
    ms = model_status()
    add("AI model (FAST_LOCAL)", ms["ready"], ms["path"] if ms["ready"] else
        ("not found - only 'Technical only' reels" if ms["reason"] == "MODEL_MISSING" else "files changed or incomplete - not used"))
    ap = aiplus_status()
    add("AI+ model (PE-Core L/14, optional)", ap["ready"], ap["path"] if ap["ready"] else
        ("not downloaded yet (optional) - see AI+ below" if ap["reason"] == "AIPLUS_MISSING" else "files changed or incomplete - not used"))
    try:
        cp = subprocess.run([engine_python(), "-B", "-s", "-E", "-c",
                             "import numpy, cv2, onnxruntime; print('numpy', numpy.__version__, '| opencv', cv2.__version__, '| onnxruntime', onnxruntime.__version__)"],
                            **process_kwargs({"capture_output": True, "text": True, "timeout": 120}))
        add("Engine libraries load (numpy, OpenCV, ONNX Runtime)", cp.returncode == 0,
            cp.stdout.strip() or (cp.stderr.strip().splitlines() or ["failed"])[-1][:300])
    except Exception as exc:
        add("Engine libraries load (numpy, OpenCV, ONNX Runtime)", False, exc)
    add("Processor", True, f"{os.cpu_count() or '?'} logical cores")
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as k:
                lp = winreg.QueryValueEx(k, "LongPathsEnabled")[0]
        except Exception:
            lp = 0
        add("Windows long paths", True, "on" if lp else "off (handled: long-named videos are analysed under short names)")
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms_ = MEMORYSTATUSEX(); ms_.dwLength = ctypes.sizeof(ms_)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms_)):
                tot = ms_.ullTotalPhys / 1e9
                add("Memory (RAM)", tot >= 6, f"{tot:.0f} GB" + ("" if tot >= 6 else " - less than 6 GB, long 4K videos may be slow"))
        except Exception:
            pass
    import platform
    from .config import BUILD, VERSION
    add("MediaEngine version", True, f"{VERSION} {BUILD}".strip())
    add("Windows", True, platform.platform() if os.name == "nt" else platform.system())
    return rows


def selftest_passed() -> bool:
    """A test reel was built on this PC at least once ("Check this PC")."""
    try:
        return bool((load_config().get("auto_edit") or {}).get("selftest_ok_at"))
    except Exception:
        return False


def _remember_selftest(res: dict) -> None:
    if not res.get("ok"):
        return
    try:
        from .config import save_config
        cfg = load_config()
        a = dict(cfg.get("auto_edit") or {})
        a["selftest_ok_at"] = now_iso()
        a["selftest_mode"] = str(res.get("selection_mode") or "")
        cfg["auto_edit"] = a
        save_config(cfg)
    except Exception:
        pass


def selftest_video() -> Path | None:
    v = DATA / "selftest" / "out" / "MediaEngine Reel.mp4"
    return v if v.is_file() else None


def quick_selftest(timeout_s: int = 900, mode: str = "technical") -> dict:
    """Build a 5 s reel from two generated clips with the real engine. mode='semantic' runs the AI model
    (semantic=required, the same pinned check as a normal AI build). Never touches user media."""
    import time as _t
    ff = _ffmpeg() or "ffmpeg"
    root = DATA / "selftest"
    shutil.rmtree(root, ignore_errors=True)
    src = root / "in"; src.mkdir(parents=True, exist_ok=True)
    for i, lav in enumerate(("testsrc2=size=640x360:rate=30", "mandelbrot=size=640x360:rate=30"), 1):
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", lav, "-f", "lavfi", "-i", f"sine=frequency={300 + 100 * i}:sample_rate=48000",
                        "-t", "8", "-vf", f"hue=h=t*{20 * i}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(src / f"test_{i}.mp4")], **process_kwargs({"capture_output": True, "timeout": 120}))
    s = {"length": 5, "format": "vertical", "sound": "auto", "mode": mode if mode in AI_MODES else "technical"}
    cmd = engine_command(src, root / "out", root / "work", root / "progress.json", s)
    t0 = _t.time()
    # same handling as a build: on Windows a job object, so a time-out stops the engine AND every ffmpeg it started
    kw = process_kwargs() if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(cmd, env=_engine_env(), cwd=str(ENGINE_DIR), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
    _attach_job_object(proc)
    try:
        out, _ = proc.communicate(timeout=timeout_s)
        ok = proc.returncode == 0 and (root / "out" / "MediaEngine Reel.mp4").is_file()
        err = "" if ok else (out or "")[-600:]
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=30)
        except Exception:
            pass
        ok, err = False, f"no result within {timeout_s} s"
    finally:
        h = _JOB_HANDLES.pop(proc.pid, None)
        if h is not None:
            try:
                import ctypes
                from ctypes import wintypes
                ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(h))
            except Exception:
                pass
    res = {"ok": ok, "seconds": round(_t.time() - t0, 1), "error": err}
    if ok:
        r = json.loads((root / "out" / "MediaEngine Result.json").read_text(encoding="utf-8"))
        res.update(video=str(root / "out" / "MediaEngine Reel.mp4"), duration_s=r.get("actual_duration_s"), stages=r.get("stage_seconds"),
                   selection_mode=r.get("selection_mode"))
    return res


# ---------------------------------------------------------------- disk space

def _tree_bytes(root: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            try:
                total += (Path(dirpath) / f).stat().st_size
            except OSError:
                pass
    return total


BUILD_MARKERS = ("BUILD.txt", "port.txt", "Start MediaEngine.vbs")


def _holds_user_data(d: Path) -> bool:
    """Early 3.13 candidates kept projects, database and exports INSIDE the release folder, and the data folder,
    the export folder or the archive may have been chosen inside one: such a folder is never offered for removal."""
    if any((d / n).exists() for n in ("data", "Exports", "MediaArchive", "Staging", "Private")):
        return True
    try:
        rd = d.resolve()
        places = [HOME, DATA, EXPORTS, default_export_dir()]
        arch = str(load_config().get("archive_root") or "")
        if arch:
            places.append(Path(arch))
        for x in places:
            rx = Path(x).resolve()
            if rx == rd or rd in rx.parents:
                return True
    except Exception:
        return True                       # unsure: keep it
    return False


def other_builds(install: Path | None = None) -> list[dict]:
    """Other MediaEngine build folders next to this one. Every update adds a folder (the old one is the rollback),
    so they pile up (~0.5 GB each) unless the user removes the ones they no longer need."""
    from .config import INSTALL
    here = Path(install or INSTALL).resolve()
    if not (here / "port.txt").is_file():          # only side-by-side releases
        return []
    out = []
    try:
        sibs = [d for d in here.parent.iterdir() if d.is_dir() and d.name.startswith("MediaEngine-") and d.resolve() != here]
    except OSError:
        return []
    sibs = [d for d in sibs if not d.name.endswith(".removing")]
    for d in sorted(sibs, key=lambda d: d.name.lower()):
        if not all((d / n).is_file() for n in BUILD_MARKERS) or _holds_user_data(d):
            continue
        try:
            built = next((ln.split(None, 1)[1][:10] for ln in (d / "BUILD.txt").read_text(encoding="utf-8", errors="replace").splitlines()
                          if ln.startswith("built ")), "")
        except OSError:
            built = ""
        mt = (d / "BUILD.txt").stat().st_mtime
        hit = _BUILD_BYTES.get(str(d))
        if not hit or hit[0] != mt:          # a release folder does not change once installed: count its size once
            hit = _BUILD_BYTES[str(d)] = (mt, _tree_bytes(d))
        out.append({"name": d.name, "path": str(d), "built": built, "bytes": hit[1], "mtime": mt})
    return out


_BUILD_BYTES: dict[str, tuple[float, int]] = {}


def delete_build(name: str, install: Path | None = None) -> int:
    """Remove one OTHER build folder (never the running one, never the data folder). Returns bytes freed."""
    b = next((x for x in other_builds(install) if x["name"] == str(name or "")), None)
    if not b:
        raise ValueError("That is not another MediaEngine version next to this one.")
    src = Path(b["path"])
    for left in src.parent.glob("MediaEngine-*.removing"):   # an earlier removal that was interrupted
        if not _holds_user_data(left):
            shutil.rmtree(left, ignore_errors=True)
    gone = src.with_name(src.name + ".removing")
    try:
        os.rename(src, gone)          # fails while something inside is open: then nothing is half-deleted
    except OSError:
        raise ValueError("Some files of that version are in use. Close anything opened from that folder and try again.")
    shutil.rmtree(gone, ignore_errors=True)
    return int(b["bytes"])


def project_disk_usage(pid: int) -> dict:
    d = _project_dir(pid)
    return {"cache_bytes": _tree_bytes(d / "work"), "versions_bytes": _tree_bytes(d / "revisions")}


def clear_work_cache(pid: int) -> int:
    """Delete the project's analysis/render cache (versions and exports stay). The next build analyses again."""
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    if any(j["status"] in ("queued", "running") for j in p["jobs"]):
        raise ValueError("Wait until the current build has finished")
    work = _project_dir(pid) / "work"
    freed = _tree_bytes(work)
    shutil.rmtree(work, ignore_errors=True)
    return freed


# ---------------------------------------------------------------- blind comparison (human quality review)

def start_review(pid: int, rev_a: int, rev_b: int) -> int:
    """Two revisions of one project shown side by side in random order, without numbers or settings."""
    import secrets
    a, b = revision(rev_a), revision(rev_b)
    if not a or not b or int(a["project_id"]) != int(pid) or int(b["project_id"]) != int(pid):
        raise ValueError("Choose two versions of this project")
    if int(a["id"]) == int(b["id"]):
        raise ValueError("Choose two different versions")
    left, right = (a, b) if secrets.randbelow(2) == 0 else (b, a)
    with db() as con:
        rid = int(con.execute("INSERT INTO ae_reviews(project_id,left_revision_id,right_revision_id,created_at) VALUES(?,?,?,?)",
                              (int(pid), int(left["id"]), int(right["id"]), now_iso())).lastrowid)
        con.commit()
    return rid


def review(review_id: int) -> dict | None:
    ensure_schema()
    with db() as con:
        r = con.execute("SELECT * FROM ae_reviews WHERE id=?", (int(review_id),)).fetchone()
    return dict(r) if r else None


def decide_review(review_id: int, choice: str, note: str = "") -> dict:
    if choice not in ("left", "right", "same"):
        raise ValueError("Unknown choice")
    with db() as con:
        cur = con.execute("UPDATE ae_reviews SET choice=?,note=?,decided_at=? WHERE id=? AND decided_at IS NULL",
                          (choice, str(note or "")[:500], now_iso(), int(review_id)))
        con.commit()
    if not cur.rowcount:
        raise ValueError("This comparison was already decided")
    return review(review_id)


def ui_language() -> str:
    from .i18n import ui_language as _ui
    return _ui()


def set_ui_language(lang: str) -> None:
    from .i18n import set_ui_language as _set
    _set(lang)


def default_export_dir() -> Path:
    """The folder the user exported to last time (if it still exists), otherwise <data>/Exports."""
    try:
        d = Path(str(load_config().get("auto_edit", {}).get("export_dir") or ""))
        if d.is_absolute() and d.is_dir():
            return d
    except Exception:
        pass
    return EXPORTS


def check_export_dir(p: dict, dest) -> Path:
    raw = str(dest or "").strip().strip('"')
    d = Path(raw)
    if not raw or not d.is_absolute() or not d.is_dir():
        raise ValueError("Export folder not found: " + (raw or "(empty)"))
    rd = d.resolve()
    try:
        _guard_private(rd)
    except ValueError:
        raise ValueError("Choose a folder outside Private / Rejected for exports")
    # an export inside the source folder would become an input of the next build of this reel
    srcs = [Path(p["folder"]).resolve()] if not p.get("files") else []
    if any(rd == s_ for s_ in srcs):
        raise ValueError("Choose a different folder: the source folder of this reel would then contain the reel itself")
    return rd


_EXPORT_LOCKS: dict[int, threading.Lock] = {}
_EXPORT_LOCKS_GUARD = threading.Lock()


def export_accepted(pid: int, dest_dir: Path | None = None, remember: bool = False) -> dict:
    """One export of a project at a time: a double click waits for the first copy and then finds it (no "(2)" copy)."""
    with _EXPORT_LOCKS_GUARD:
        lock = _EXPORT_LOCKS.setdefault(int(pid), threading.Lock())
    with lock:
        return _export_accepted(pid, dest_dir, remember)


def _export_accepted(pid: int, dest_dir: Path | None = None, remember: bool = False) -> dict:
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    if dest_dir:
        dest_dir = check_export_dir(p, dest_dir)
        if remember:
            from .config import save_config
            cfg = load_config()
            cfg.setdefault("auto_edit", {})["export_dir"] = str(dest_dir)
            save_config(cfg)
    if not p["accepted_revision_id"]:
        raise ValueError("Accept a revision before exporting")
    r = revision(p["accepted_revision_id"])
    src = Path(r["video_path"])
    if sha256_file(src) != r["video_sha256"]:
        raise ValueError("Accepted revision changed on disk; export refused")
    if not dest_dir:
        dest_dir = default_export_dir()
        try:                       # the remembered folder may be this reel's own source folder: then the usual one
            dest_dir = check_export_dir(p, dest_dir) if dest_dir.is_dir() else dest_dir
        except ValueError:
            dest_dir = check_export_dir(p, EXPORTS) if Path(EXPORTS).is_dir() else Path(EXPORTS)
    dest_dir = Path(dest_dir)
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
    if p.get("files"):
        allowed = {str(Path(x).resolve()) for x in p["files"]}
        for v in project_inputs(p):
            if v.name == name and str(v.resolve()) in allowed:
                return v.resolve()
        return None
    folder = Path(p["folder"]).resolve()
    for v in list_videos(folder):
        if v.name == name:
            rp = v.resolve()
            if rp.parent == folder:
                return rp
    return None


# ---------------------------------------------------------------- Windows file / folder pickers

def _dialog_title(en: str) -> str:
    """Native Windows dialogs are not HTML pages: their titles follow the interface language here."""
    ru = {"Choose videos for one reel": "Выбери видео для одного ролика (Ctrl+щелчок — несколько)",
          "Choose a folder with your videos on this computer (copy phone videos to the computer first)":
              "Выбери папку с видео на этом компьютере (видео с телефона сначала скопируй на компьютер)",
          "Choose the folder that contains the FAST_LOCAL model": "Выбери папку, в которой лежит модель FAST_LOCAL",
          "Choose a folder for the exported reel": "Выбери папку для готового ролика",
          "Choose the folder with the AI+ model files": "Выбери папку с файлами модели ИИ+"}
    try:
        return ru.get(en, en) if ui_language() == "ru" else en
    except Exception:
        return en


def pick_files(title="Choose videos for one reel", initial: str | None = None) -> list[str] | None:
    """Native Windows Open dialog with multi-select (GetOpenFileNameW). initial = the folder it opens in."""
    if os.name != "nt":
        return None
    box: dict = {}

    def run():
        import ctypes
        from ctypes import wintypes

        class OPENFILENAMEW(ctypes.Structure):
            _fields_ = [("lStructSize", wintypes.DWORD), ("hwndOwner", wintypes.HWND), ("hInstance", wintypes.HINSTANCE),
                        ("lpstrFilter", wintypes.LPCWSTR), ("lpstrCustomFilter", wintypes.LPWSTR), ("nMaxCustFilter", wintypes.DWORD),
                        ("nFilterIndex", wintypes.DWORD), ("lpstrFile", wintypes.LPWSTR), ("nMaxFile", wintypes.DWORD),
                        ("lpstrFileTitle", wintypes.LPWSTR), ("nMaxFileTitle", wintypes.DWORD), ("lpstrInitialDir", wintypes.LPCWSTR),
                        ("lpstrTitle", wintypes.LPCWSTR), ("Flags", wintypes.DWORD), ("nFileOffset", wintypes.WORD),
                        ("nFileExtension", wintypes.WORD), ("lpstrDefExt", wintypes.LPCWSTR), ("lCustData", wintypes.LPARAM),
                        ("lpfnHook", ctypes.c_void_p), ("lpTemplateName", wintypes.LPCWSTR), ("pvReserved", ctypes.c_void_p),
                        ("dwReserved", wintypes.DWORD), ("FlagsEx", wintypes.DWORD)]

        size = 65536
        buf = ctypes.create_unicode_buffer(size)
        ru = ui_language() == "ru"
        flt = ("Видео" if ru else "Videos") + "\0" + ";".join("*" + x for x in sorted(SUPPORTED)) + "\0" + ("Все файлы" if ru else "All files") + "\0*.*\0\0"
        ofn = OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
        ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
        ofn.lpstrFilter = flt
        ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
        ofn.nMaxFile = size
        ofn.lpstrTitle = _dialog_title(title)
        if initial and Path(initial).is_dir():
            ofn.lpstrInitialDir = str(initial)
        # OFN_ALLOWMULTISELECT | OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR
        ofn.Flags = 0x200 | 0x80000 | 0x1000 | 0x800 | 0x8
        if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
            parts = ctypes.wstring_at(ctypes.addressof(buf), size).split("\0")
            parts = parts[: parts.index("")] if "" in parts else parts
            if len(parts) == 1:
                box["files"] = parts
            elif parts:
                box["files"] = [str(Path(parts[0]) / n) for n in parts[1:]]

    t = threading.Thread(target=run, name="file-picker", daemon=True)
    t.start()
    t.join(600)
    return box.get("files")


def last_source_folder() -> str | None:
    """The folder of the last reel's videos, if it is there (the file window opens in it)."""
    try:
        ensure_schema()
        with db() as con:
            row = con.execute("SELECT folder FROM ae_projects ORDER BY updated_at DESC, id DESC LIMIT 1").fetchone()
        return row[0] if row and row[0] and Path(row[0]).is_dir() else None
    except Exception:
        return None


def last_source_parent() -> str | None:
    """Where the folder window opens: next to the last reel's videos (their parent folder), if it is there."""
    f = last_source_folder()
    parent = Path(f).parent if f else None
    return str(parent) if parent and parent.is_dir() else None


def _pick_folder_explorer(title: str, initial: str | None, owner) -> tuple[bool, str | None]:
    """The Explorer-style folder window (IFileOpenDialog with FOS_PICKFOLDERS: address bar, Quick access, paste a
    path). Returns (shown, path); shown=False when it is not available, then the older tree dialog is used.
    Must run on a COM STA thread."""
    import ctypes
    from ctypes import wintypes
    HRESULT = ctypes.c_long

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    ole32, shell32 = ctypes.windll.ole32, ctypes.windll.shell32
    ole32.CLSIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
    ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = HRESULT
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    shell32.SHCreateItemFromParsingName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    shell32.SHCreateItemFromParsingName.restype = HRESULT

    def guid(text):
        g = GUID()
        if ole32.CLSIDFromString(text, ctypes.byref(g)) != 0:
            raise OSError("bad GUID " + text)
        return g

    def method(obj, index, *argtypes):     # COM call through the object's vtable
        vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return lambda *a: ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, *argtypes)(vtbl[index])(obj, *a)

    iid_item = guid("{43826d1e-e718-42ee-bc55-a1e261c37bfe}")
    dlg = ctypes.c_void_p()
    if ole32.CoCreateInstance(ctypes.byref(guid("{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}")), None, 1,   # CLSCTX_INPROC_SERVER
                              ctypes.byref(guid("{d57c7288-d4ad-4768-be02-9d969532d960}")), ctypes.byref(dlg)) != 0 or not dlg:
        return False, None
    item = ctypes.c_void_p()
    try:
        opts = wintypes.DWORD()
        method(dlg, 10, ctypes.POINTER(wintypes.DWORD))(ctypes.byref(opts))                                  # GetOptions
        method(dlg, 9, wintypes.DWORD)(opts.value | 0x20 | 0x40 | 0x800 | 0x8)   # SetOptions: PICKFOLDERS FORCEFILESYSTEM PATHMUSTEXIST NOCHANGEDIR
        method(dlg, 17, wintypes.LPCWSTR)(title)                                                            # SetTitle
        if initial and Path(initial).is_dir():
            start = ctypes.c_void_p()
            if shell32.SHCreateItemFromParsingName(str(initial), None, ctypes.byref(iid_item), ctypes.byref(start)) == 0 and start:
                method(dlg, 12, ctypes.c_void_p)(start)                                                     # SetFolder
                method(start, 2)()                                                                          # Release
        hr = method(dlg, 3, wintypes.HWND)(owner)                                                           # Show
        if hr != 0:
            return True, None                      # Cancel (0x800704C7) or closed
        if method(dlg, 20, ctypes.POINTER(ctypes.c_void_p))(ctypes.byref(item)) != 0 or not item:           # GetResult
            return True, None
        name = ctypes.c_void_p()
        if method(item, 5, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p))(0x80058000, ctypes.byref(name)) != 0 or not name:  # GetDisplayName(FILESYSPATH)
            return True, None
        path = ctypes.wstring_at(name.value)
        ole32.CoTaskMemFree(name)
        return True, path
    finally:
        if item:
            method(item, 2)()
        method(dlg, 2)()


def pick_folder(title="Choose a folder with your videos on this computer (copy phone videos to the computer first)",
                initial: str | None = None) -> str | None:
    """Native Windows folder window: the Explorer-style one, else the older tree dialog (SHBrowseForFolderW).
    Runs on a COM STA thread. initial = the folder it opens in (e.g. where the last reel's videos were)."""
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
        if os.environ.get("MEDIAENGINE_OLD_FOLDER_DIALOG") != "1":
            try:
                shown, path = _pick_folder_explorer(_dialog_title(title), initial, user32.GetForegroundWindow())
            except Exception:
                shown, path = False, None
            if shown:
                if path:
                    box["path"] = path
                ole32.CoUninitialize()
                return

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
        bi.lpszTitle = _dialog_title(title)
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
