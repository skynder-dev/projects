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
    "social_hd": {"profile": "9x16", "resolution": "social_hd", "label": "Vertical Full HD 1080×1920 (phone, Reels, Shorts)", "short": "Vertical HD", "size": (1080, 1920)},
    "horizontal_hd": {"profile": "16x9", "resolution": "social_hd", "label": "Horizontal Full HD 1920×1080 (TV, YouTube)",
                      "short": "Horizontal HD", "size": (1920, 1080)},
    "vertical": {"profile": "9x16", "resolution": "standard", "label": "Vertical small 540×960 (quick to send)", "short": "Vertical small", "size": (540, 960)},
    "horizontal": {"profile": "16x9", "resolution": "standard", "label": "Horizontal small 960×540 (quick to send)", "short": "Horizontal small", "size": (960, 540)},
}
FRAMINGS = {"fill": "Fill the screen (cropped to the interesting part)", "fit_blur": "Whole picture, blurred edges"}
# the reel's colours (the engine's LOOKS): "as filmed" changes nothing; the videos themselves are never changed
LOOKS = {"natural": "As filmed", "vivid": "Brighter and richer", "warm": "Warm", "film": "Cinematic"}
SOUNDS = {"auto": "Auto (keep source sound, mute if it jumps)", "source": "Source sound", "mute": "Mute"}
LENGTHS = (5, 15, 30, 60, 120)    # 120 s: about 25 moments (the engine takes up to 30; checked 2026-10-14)
MODES = {"semantic": "AI moments (FAST_LOCAL)", "semantic_plus": "AI+ moments (PE-Core L/14)", "technical": "Technical only (no AI model)"}
AI_MODES = ("semantic", "semantic_plus")
# AI+ themes: key -> name shown (English; Russian in auto_edit_ru). The descriptions are in the engine (p13_event_semantic_pe).
THEMES = {"sea": "Sea and beach", "mountains": "Mountains", "kids": "Children", "family": "Family and friends",
          "party": "Celebration", "animals": "Animals", "sunset": "Sunset", "nature": "Nature", "snow": "Winter and snow",
          "city": "City", "food": "Food", "sport": "Sport", "road": "Road trip",
          "aerial": "Aerial view (drone)"}

MODEL_SHA = "844d1a46ab18acf50c989e541b12fe3b6dc7f8d6004725b4e992d142788e0600"
MODEL_BYTES = 24281512

# Honest progress: weight of each real engine stage in the overall bar.
# shares of the whole build as measured (CI, 7 videos: analysis 12 %, cutting 34 %, final encode + check 50 %);
# the final stage has no steps of its own, so it starts well before the end instead of sitting at 95 % for minutes
STAGE_SPAN = {"queued": (0, 0), "starting": (0, 1), "inputs": (1, 5), "analyze": (5, 50), "select": (50, 51),
              "trim": (51, 54), "render": (54, 80), "finish": (80, 99), "done": (100, 100)}
# "Prepare in advance" (analysis only, no reel): finding moments is nearly all of it
STAGE_SPAN_PREPARE = {"queued": (0, 0), "starting": (0, 1), "inputs": (1, 5), "analyze": (5, 95), "select": (95, 96),
                      "trim": (96, 99), "done": (100, 100)}
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


_FORMAT_WORD_RU = {"social_hd": "Вертикально HD", "horizontal_hd": "Горизонтально HD",
                   "vertical": "Вертикально маленький", "horizontal": "Горизонтально маленький"}


def _ui_ru() -> bool:
    try:
        from .i18n import ui_language
        return ui_language() == "ru"
    except Exception:
        return False


def format_file_word(fmt: str) -> str:
    """The format in a saved file's name, in the language of the program (the same names as on the new-reel page)."""
    if _ui_ru() and fmt in _FORMAT_WORD_RU:
        return _FORMAT_WORD_RU[fmt]
    return FORMATS.get(fmt, {}).get("short", "Reel")


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
    if cfg.get("model_root") and "Archivist" not in Path(cfg["model_root"]).parts and _model_valid(Path(cfg["model_root"])):
        return Path(cfg["model_root"])        # (a remembered folder that moved away is not trusted: the usual places are)
    for cand in model_search_roots():
        if _model_valid(cand):
            return cand
    for cand in model_search_roots():
        if (cand / "FAST_LOCAL" / "model_int8.onnx").exists():
            return cand
    return HOME / "models"


def model_search_roots() -> list[Path]:
    """MediaEngine's own models folder (in its data folder) first, then the program folder. No other program's
    folders are looked at (the owner, 2026-10-14: MedEng keeps everything in its own folder)."""
    roots = [HOME / "models", HOME / "sidecars" / "auto_edit" / "models"]
    if INSTALL != HOME:
        roots += [INSTALL / "models", INSTALL / "sidecars" / "auto_edit" / "models"]
    return roots


def model_folder_hint() -> str | None:
    """Where the model folder window opens (copy from a folder): the data folder."""
    return str(HOME) if HOME.is_dir() else None


# ---------------------------------------------------------------- AI model (FAST_LOCAL, ~30 MB)
# Downloaded by MediaEngine itself into its own data folder (models/FAST_LOCAL) with an explicit button: the exact
# public files of the pinned Hugging Face commit, every file checked by size and SHA-256 (the engine's contract).
FAST_REPO = "onnx-community/TinyCLIP-ViT-8M-16-Text-3M-YFCC15M-ONNX"
_MODEL_DL = {"state": "idle", "done": 0, "total": 0, "error": "", "file": ""}
_MODEL_STOP = threading.Event()      # never set: the 30 MB download is not stopped half way


def _fast_contract():
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    import validate_p11_model_contract as vc
    return vc


def fast_files() -> list[tuple[str, str, int, str]]:
    """(path inside models/FAST_LOCAL, url, size, sha256) of every file of the exact model."""
    vc = _fast_contract()
    base = f"https://huggingface.co/{FAST_REPO}/resolve/{vc.COMMIT}/"
    out = [(vc.MODEL_NAME, base + "onnx/" + vc.MODEL_NAME, vc.MODEL_SIZE, vc.MODEL_SHA256)]
    out += [(vc.SUPPORT_DIR + "/" + n, base + n, size, sha) for n, (size, sha) in vc.SUPPORT.items()]
    return out


def model_downloading() -> bool:
    return _MODEL_DL["state"] == "running"


def model_download_start() -> bool:
    with _LOCK:
        if _MODEL_DL["state"] == "running":
            return False
        _MODEL_DL.update(state="running", done=0, total=0, error="", file="")
    threading.Thread(target=_model_download, name="model-download", daemon=True).start()
    return True


def _model_download() -> None:
    import http.client, socket, urllib.error
    files = fast_files()
    total = sum(f[2] for f in files)
    root = HOME / "models"
    tmp = root / "FAST_LOCAL.__download__"
    try:
        tmp.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(tmp).free < total + 200_000_000:
            raise RuntimeError("Not enough free disk space for the AI model.")
        _MODEL_DL.update(total=total)
        done = 0
        for rel, url, size, sha in files:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            _MODEL_DL.update(file=Path(rel).name)
            if not (dst.is_file() and dst.stat().st_size == size and sha256_file(dst) == sha):
                part = dst.with_name(dst.name + ".part")
                base = done
                _fetch_resumable(url, part, size, lambda have, base=base: _MODEL_DL.update(done=base + have), stop=_MODEL_STOP)
                if part.stat().st_size != size or sha256_file(part) != sha:
                    part.unlink(missing_ok=True)
                    raise RuntimeError("A downloaded file is not the exact model file (" + Path(rel).name + "). Try again.")
                _replace_retry(part, dst)
            done += size
            _MODEL_DL.update(done=done)
        _fast_contract().validate("FAST_LOCAL", tmp)
        dst = root / "FAST_LOCAL"
        if dst.exists():
            shutil.rmtree(dst)
        os.replace(tmp, dst)
        _MODEL_CACHE.clear()
        cfg = load_config()
        cfg.setdefault("auto_edit", {})["model_root"] = str(root)
        from .config import save_config
        save_config(cfg)
        _MODEL_DL.update(state="done", done=total, file="")
    except Exception as exc:
        msg = str(exc)
        if isinstance(exc, urllib.error.HTTPError):       # (an HTTPError is also a URLError: it is not "no connection")
            msg = (f"huggingface.co answered HTTP {exc.code}: the model cannot be downloaded from there now. "
                   "Try later, or copy it from another PC (Copy from a folder…).")
        elif isinstance(exc, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException)):
            print("model download: no connection:", msg[:300], flush=True)       # (details for support: app_console.log)
            msg = "No connection to huggingface.co. Check the internet connection and try again, or copy the model from another PC (Copy from a folder…)."
        _MODEL_DL.update(state="failed", error=msg[:300], failed_at=time.time())


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
        cfg = load_config()                   # already here: remember it (an old remembered folder no longer wins)
        cfg.setdefault("auto_edit", {})["model_root"] = str(HOME / "models")
        from .config import save_config
        save_config(cfg)
        _MODEL_CACHE.clear()
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
    out = {"ready": False, "reason": "AIPLUS_MISSING", "path": str(d), "bytes": pc.TOTAL_BYTES, "download": dict(_AIPLUS_DL),
           "partial": False}
    try:
        key = _aiplus_key(d, pc)
    except OSError:
        try:      # a download stopped part-way: "Continue the download" goes on from there
            out["partial"] = any(d.glob("*.part")) and not aiplus_downloading()
        except OSError:
            pass
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


def _fetch_resumable(url: str, part: Path, size: int, progress, tries: int = 4, stop: threading.Event | None = None) -> None:
    """Download into `part`, continuing what is already there (HTTP Range); a dropped connection is tried again
    from where it stopped, a few times, before giving up (the part stays for the next try)."""
    import http.client, socket, urllib.error, urllib.request
    stop = stop or _AIPLUS_STOP
    for attempt in range(tries):
        have = part.stat().st_size if part.is_file() else 0
        if have > size:
            part.unlink(); have = 0
        if have == size:
            return
        headers = {"User-Agent": "MediaEngine"}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                status = getattr(r, "status", 200)
                resumed = have and status == 206 and str(r.headers.get("Content-Range", "")).startswith(f"bytes {have}-")
                length = r.headers.get("Content-Length")
                whole = status == 200 and (length is None or str(length).strip() == str(size))
                if "text/html" in str(r.headers.get("Content-Type", "")).lower() or not (resumed or whole) or \
                        (resumed and length is not None and str(length).strip() != str(size - have)):
                    # a hotel / proxy sign-in page (200 + HTML) or an answer of the wrong size: never written over
                    # what is already downloaded
                    raise ConnectionError(f"not the model file (HTTP {status}, {r.headers.get('Content-Type', '?')})")
                if have and not resumed:          # the server sent the whole file: start again
                    have = 0
                progress(have)
                with part.open("ab" if resumed else "wb") as fh:
                    while True:
                        if stop.is_set():
                            raise RuntimeError("Download cancelled.")
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
                        have += len(chunk)
                        progress(have)
            if have >= size:
                return
            raise ConnectionError("the connection ended early")
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, OSError, http.client.HTTPException) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == tries - 1 or stop.is_set():
                raise
            time.sleep(min(20, 3 * (attempt + 1)))


def _aiplus_download() -> None:
    import http.client, socket, urllib.error
    pc = _pe_contract()
    d = aiplus_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
        parts = {x.name for x in d.glob("*.part")}          # left by an earlier stop or lost connection: continued
        for x in d.glob("*.part"):
            if x.name[:-5] not in pc.ALL_FILES:
                x.unlink(missing_ok=True)
        need = sum(v[1] - ((d / (n + ".part")).stat().st_size if (n + ".part") in parts else 0)
                   for n, v in pc.ALL_FILES.items() if not ((d / n).is_file() and (d / n).stat().st_size == v[1]))
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
            base = done
            _fetch_resumable(pc.download_url(name), part, size, lambda have, base=base: _AIPLUS_DL.update(done=base + have))
            done = base + size
            if part.stat().st_size != size or sha256_file(part) != sha:
                part.unlink(missing_ok=True)
                raise RuntimeError("A downloaded file is not the exact model file (" + name + "). Try again.")
            _replace_retry(part, dst)
        with _AIPLUS_LOCK:
            _aiplus_mark_verified(d, pc)      # every file was just checked: no second 650 MB hash
        _AIPLUS_DL.update(state="done", done=pc.TOTAL_BYTES, file="")
    except Exception as exc:
        msg = str(exc)
        if isinstance(exc, urllib.error.HTTPError):       # (an HTTPError is also a URLError: it is not "no connection")
            msg = (f"huggingface.co answered HTTP {exc.code}: the model cannot be downloaded from there now. "
                   "Try later, or copy it from another PC (Copy from a folder…).")
        elif isinstance(exc, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException)):
            print("model download: no connection:", msg[:300], flush=True)       # (details for support: app_console.log)
            msg = "No connection to huggingface.co. Check the internet connection and try again, or copy the model from another PC (Copy from a folder…)."
        _AIPLUS_DL.update(state="failed", error=msg[:300], failed_at=time.time())


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
_SCHEMA_LOCK = threading.Lock()


def ensure_schema() -> None:
    """Create tables once per process; jobs left queued/running by a previous process become Retry-able failures."""
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:      # two first requests at once: the second must not mark a job just started as interrupted
        if not _SCHEMA_READY:
            _ensure_schema_now()


def _ensure_schema_now() -> None:
    global _SCHEMA_READY
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
        if "auto_resumed" not in [r[1] for r in con.execute("PRAGMA table_info(ae_jobs)").fetchall()]:
            con.execute("ALTER TABLE ae_jobs ADD COLUMN auto_resumed INTEGER NOT NULL DEFAULT 0")
        # The job that was running when the previous app process stopped has no live process any more. Quit (or a
        # switch, a restart of the app) stopped it on purpose: interrupted, Retry reuses the finished analysis. The app
        # stopped WITHOUT quitting (a restart of the PC at night, a crash, power): it is made again by itself, once.
        # Queued jobs just wait: the next app start builds them (overnight sets).
        unclean = _run_mark().is_file()
        for r in con.execute("SELECT id, auto_resumed FROM ae_jobs WHERE status='running'").fetchall():
            again = unclean and not int(r["auto_resumed"] or 0)
            con.execute("UPDATE ae_jobs SET status='failed',stage='failed',error=?,finished_at=? WHERE id=?",
                        (AUTO_RESUME_MSG if again else INTERRUPTED_MSG, now_iso(), int(r["id"])))
            if again:
                _AUTO_RESUME.append(int(r["id"]))
        con.commit()
    try:                     # this process runs now; Quit removes the mark (mark_clean_exit)
        _run_mark().parent.mkdir(parents=True, exist_ok=True)
        _run_mark().write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        pass
    _SCHEMA_READY = True


INTERRUPTED_MSG = "Interrupted: the app was closed. Press Retry - finished analysis is reused."
AUTO_RESUME_MSG = "Stopped when MediaEngine stopped unexpectedly (for example a restart of the PC). It is made again by itself."
_AUTO_RESUME: list[int] = []        # failed job ids to make again once (resume_queued, at the app's first request)


def _run_mark() -> Path:
    return DATA / "app_running.txt"


def mark_clean_exit() -> None:
    """The app quits on purpose (Quit, a switch to another build, a restart of the app): a build it stops is
    interrupted (Retry), not made again by itself at the next start."""
    try:
        _run_mark().unlink(missing_ok=True)
    except OSError:
        pass


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


from .media import shot_time  # noqa: E402  (recording time from the video header)


def _header_day_time(p: Path, mtime: float) -> float | None:
    """The recording time from the video's header, used for its day only when the file's date looks like the day it
    was copied (later than the recording). GoPro / DJI write their own clock there (read as that wall-clock time by
    shot_time); other cameras that do so: a file date that agrees with it within a day is kept as it is."""
    t = shot_time(p)
    if not t:
        return None
    return t if mtime - t > 86400 else None


def video_day(p: Path, mtime: float) -> str:
    m = _DAY_IN_NAME.search(Path(p).stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return time.strftime("%Y-%m-%d", time.localtime(mtime))


def videos_by_day(folder) -> list[dict]:
    """A folder with more videos than one reel takes (a phone camera folder): its videos grouped by the day they were
    shot (date in the file name, else the recording time in the video's header, else the file's date), newest day
    first, so the user can pick a day or tick videos. Only names, sizes and a few header bytes are read."""
    days: dict[str, list] = {}
    for p in list_videos(Path(folder)):
        try:
            st = p.stat()
        except OSError:
            continue
        # the header is read only when the name has no date, and never for a OneDrive file kept only in the cloud
        # (reading it would make Windows download the whole video)
        t = st.st_mtime if (_DAY_IN_NAME.search(p.stem) or cloud_only(p, st)) else (_header_day_time(p, st.st_mtime) or st.st_mtime)
        days.setdefault(video_day(p, t), []).append({"path": str(p), "name": p.name, "bytes": st.st_size})
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
                cp = subprocess.run(*a, **process_kwargs(k))
                _PROBE_TEXT.text = cp.stderr if isinstance(getattr(cp, "stderr", None), str) else ""
                return cp
        probe_mod.subprocess = _HiddenSubprocess()
        probe_mod._me_hidden = True
    _PROBE_TEXT.text = ""
    info = probe_mod.probe_json(path, _ffmpeg() or "ffmpeg", 30)
    # a phone video stored lying on its side with "rotate 90" in it: shown (and used by the engine) upright
    m = _ROTATION_RE.search((getattr(_PROBE_TEXT, "text", "") or "").split("Stream mapping:", 1)[0])
    if m and isinstance(info, dict):
        info = {**info, "rotation": int(round(float(m.group(1)))) % 360}
    return info


_PROBE_TEXT = threading.local()
_ROTATION_RE = re.compile(r"rotation of (-?\d+(?:\.\d+)?) degrees")


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
        if not p.is_file():          # (a card unplugged for now) its copy, if any, stays for when it is back
            keep.update({_fixed_name(p), _fixed_name(p) + ".source.json"})
            out.append(p)
            continue
        if not length_missing(p):
            out.append(p)
            continue
        if private is None:
            private = set(_private_hashes())
        fx = _fixed_name(p)          # per source file: two recordings with the same name never share one copy
        dst = fixed_dir / fx
        stamp = fixed_dir / (fx + ".source.json")
        tmp = fixed_dir / (fx + ".part")              # never a video name, so never another input's copy
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
                stamp_tmp = fixed_dir / (fx + ".source.json.part")
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
        gone = []
        for x in fixed_dir.iterdir():
            if x.name not in keep:
                try:
                    if x.suffix.lower() not in (".json", ".part"):
                        gone.append(sha256_file(x))      # the AI knows the copy by its own SHA-256
                    x.unlink()
                except OSError:
                    pass
        try:
            forget_in_shared(gone)
        except Exception:
            pass
    return out, changed


def _fixed_name(p) -> str:
    """The file name of a recording's fixed copy: its source path's hash + its own name (the engine is told the name
    the reel uses for it)."""
    key = os.path.normcase(str(Path(p).resolve()))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12] + "_" + Path(p).name


def fixed_copy_seconds(pid: int, name: str) -> float:
    """Length of the fixed copy of a recording without a written length (0 when there is none). Quick."""
    try:
        src = source_file(int(pid), name)
        if not src:
            return 0.0
        cp = _project_dir(int(pid)) / "work" / "fixed_inputs" / _fixed_name(src)
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
                w_, h_ = int(v[0].get("width") or 0), int(v[0].get("height") or 0)
                if info.get("rotation") in (90, 270):        # stored on its side, played upright
                    w_, h_ = h_, w_
                row.update(ok=True, duration_s=round(dur, 2), width=w_, height=h_, length_measured=bool(info.get("length_measured")))
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
        rp = f.resolve()
        if str(rp).lower() in names:
            continue                     # the same file twice: once (two files with the same NAME are fine: see input_names)
        names.add(str(rp).lower())
        out.append(rp)
    if not out:
        raise ValueError("No video files chosen")
    if len(out) > MAX_INPUTS:
        raise ValueError(f"Choose at most {MAX_INPUTS} videos for one reel.")
    return sorted(out, key=lambda x: x.name.lower())


def input_names(paths) -> list[tuple[Path, str]]:
    """Each input video with the name the reel uses for it: its file name, or - for a second video with the same name
    from another folder (two cameras' DJI_0001.MP4) - "DJI_0001 (2).MP4". Always the same names for the same files."""
    items = sorted((Path(x) for x in paths), key=lambda x: (x.name.lower(), str(x).lower()))
    used, out = set(), []
    for x in items:
        nm, k = x.name, 2
        while nm.lower() in used:
            nm, k = f"{x.stem} ({k}){x.suffix}", k + 1
        used.add(nm.lower())
        out.append((x, nm))
    return out


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
    if r in ("MISSING", "NOT_FOUND", "FILE_MISSING"):
        return "not found (moved or deleted)"
    if r == "SAME_NAME_NO_ROOM":
        return "another video has the same name and there was no room on the drive to analyse it apart"
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

_CAMERA_FOLDER = re.compile(r"\d{3}[A-Za-z0-9_]{5}|DCIM|Camera|CAMERA|camera|Movies|Video|Videos|VIDEO", re.I)


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
    if not str(title or "").strip() and not files and _CAMERA_FOLDER.fullmatch(folder.name or ""):
        # a camera's own folder name (100MEDIA, 100GOPRO, DCIM, Camera ...): every project of every card would have the
        # same name - the days it was filmed added ("100MEDIA · 2026-10-14 – 2026-10-16")
        try:
            span = sorted(d["day"] for d in videos_by_day(folder))
            if span:
                name = f"{name} · {span[0]}" + (f" – {span[-1]}" if span[-1] != span[0] else "")
        except Exception:
            pass
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


def project_with_files(files) -> int | None:
    """The project (not archived) made of exactly these chosen videos, or None: "A reel for every day" pressed again
    after "Prepare in advance" (or twice) continues the day's project instead of making a second one."""
    want = sorted(str(x).lower() for x in check_files(files))
    ensure_schema()
    with db() as con:
        rows = con.execute("SELECT id, files_json FROM ae_projects WHERE archived=0 AND files_json IS NOT NULL ORDER BY id DESC").fetchall()
    for r in rows:
        try:
            have = sorted(str(x).lower() for x in json.loads(r["files_json"] or "[]"))
        except ValueError:
            continue
        if have == want:
            return int(r["id"])
    return None


def prepared_project_for(folder, files=None) -> int | None:
    """The project (not archived, nothing building) prepared in advance from exactly this folder or these videos and
    not built yet, or None."""
    try:
        if files:
            cands = [project_with_files(files)]
        else:
            f = check_folder(folder)
            ensure_schema()
            with db() as con:
                rows = con.execute("SELECT id, folder FROM ae_projects WHERE archived=0 AND files_json IS NULL ORDER BY id DESC").fetchall()
            cands = [int(r["id"]) for r in rows if str(r["folder"]).lower() == str(f.resolve()).lower()]
    except (ValueError, OSError):
        return None
    for pid in cands:
        p = project(pid) if pid else None
        if p and p["state"] != "PROCESSING" and prepared_job(p):
            return int(pid)
    return None


def prepared_job(d: dict) -> dict | None:
    """The "Prepare in advance" job of a project not built yet, or None. A later build that was cancelled or failed
    (or the card being unplugged for a while) does not undo the preparing: its analysis and cut pieces are still there."""
    if d.get("revisions"):
        return None
    for j in d.get("jobs") or []:                # newest first
        if j["status"] != "done":
            continue
        if not (j.get("settings") or {}).get("prepare"):
            return None
        if j.get("id") and d.get("id") and not prepared_info(int(j["id"]), _project_dir(int(d["id"])) / "jobs" / f"j{int(j['id'])}"):
            return None                           # freed since (no Prepared.json any more)
        return j
    return None


def _sql_int(x) -> bool:
    """An id SQLite can look up (a huge number from a typed URL would raise OverflowError -> a server error)."""
    try:
        return -(2 ** 63) <= int(x) < 2 ** 63
    except (TypeError, ValueError):
        return False


def _project_dir(pid: int) -> Path:
    return AE_ROOT / f"p{int(pid)}"


def project(pid: int) -> dict | None:
    if not _sql_int(pid):
        return None
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
    # chosen videos: one moved or deleted video does not block the project (the rest is still there)
    d["missing_files"] = [x for x in d["files"] if not Path(x).is_file()] if d["files"] else []
    d["source_present"] = (len(d["missing_files"]) < len(d["files"])) if d["files"] else folder_available(d["folder"])
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
    if prepared_job(d):
        return "PREPARED"            # analysed in advance (and not freed since): the reel is made in minutes
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
    # horizontal videos in a vertical reel: cropped to the interesting part (default) or the whole picture on blurred
    # edges; stored only when not the default, so older reels keep their key
    framing = str(raw.get("framing") or "fill")
    if framing not in FRAMINGS:
        raise ValueError("Unknown framing")
    if framing != "fill" and FORMATS[fmt]["profile"] == "9x16":
        out["framing"] = framing
    # the reel's colours: stored only when not "as filmed" (older reels keep their key)
    look = str(raw.get("look") or "natural")
    if look not in LOOKS:
        raise ValueError("Unknown colours")
    if look != "natural":
        out["look"] = look
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
        # removed moments are remembered with a hand-made selection (they stay out when MediaEngine chooses again for
        # another length); the engine only marks them in the pool, the selection decides the reel
        out["exclude"] = sorted(set(exclude) - set(selection))
    if trims:
        out["trims"] = trims
    if raw.get("prepare") in (True, 1, "1", "on", "true") and not selection:
        out["prepare"] = True     # "Prepare in advance": analysis only, no reel (a request of its own)
    # titles and own music (optional): only stored when set, so a reel without them keeps its old key
    clean = lambda t: " ".join(str(t or "").replace("\x00", " ").split())
    title, subtitle = clean(raw.get("title")), clean(raw.get("subtitle"))
    if len(title) > 80 or len(subtitle) > 80:
        raise ValueError("A title can be at most 80 characters long")
    if title:
        out["title"] = title
    if subtitle:
        out["subtitle"] = subtitle
    music = str(raw.get("music") or "").strip().strip('"')
    if music:
        mp = Path(music)
        if not mp.is_absolute() or not mp.is_file():
            raise ValueError("Music file not found: " + music)
        if mp.suffix.lower() not in MUSIC_EXT:
            raise ValueError("Not a music file: " + mp.name + " (" + ", ".join(sorted(MUSIC_EXT)) + ")")
        _guard_private(mp)
        out["music"] = str(mp)
        out["music_mode"] = "music" if raw.get("music_mode") == "music" else "mix"
        if raw.get("beat_sync") in (False, 0, "0", "off", "false"):     # cuts on the beat: on unless switched off
            out["beat_sync"] = False
    return out


MUSIC_EXT = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma"}


def music_identity(path: str) -> str:
    """A changed music file (same name, new content) must make a new version: name + size + time."""
    try:
        st = Path(path).stat()
        return f"{path}|{st.st_size}|{st.st_mtime_ns}"
    except OSError:
        return path + "|missing"


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
                      "private": hashlib.sha256("\n".join(_private_hashes()).encode()).hexdigest(),
                      **({"private_paths": hashlib.sha256("\n".join(sorted(_private_paths())).encode()).hexdigest()}
                         if _private_paths() else {}),
                      **({"music_file": music_identity(settings["music"])} if settings.get("music") else {})},
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


def resume_queued() -> None:
    """At the app's start (the serving process only): builds still waiting from the last run go on."""
    ensure_schema()
    try:
        sweep_deleting()
    except OSError:
        pass
    while _AUTO_RESUME:        # builds the app stopped without quitting (a restart of the PC): made again, once
        jid = _AUTO_RESUME.pop(0)
        try:
            j = job(jid)
            new = start_job(j["project_id"], j["settings"]) if j else None
            if new:
                with db() as con:
                    con.execute("UPDATE ae_jobs SET auto_resumed=1 WHERE id=?", (int(new),))
                    con.commit()
        except Exception:      # (its videos are not there now, ...): it stays a failed build with Retry
            with db() as con:
                con.execute("UPDATE ae_jobs SET error=? WHERE id=?", (INTERRUPTED_MSG, int(jid)))
                con.commit()
    with db() as con:
        waiting = con.execute("SELECT 1 FROM ae_jobs WHERE status='queued' LIMIT 1").fetchone()
    if waiting:
        _ensure_worker()
        _WAKE.set()


def start_job(pid: int, raw_settings: dict, *, retry=False) -> int:
    """Queue a reel build. Same project + same inputs + same settings never builds twice."""
    ensure_schema()
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    if not p["source_present"]:
        raise ValueError("The source videos are not available (disconnected drive?)" if p["files"] else
                         "The source folder is not available (disconnected drive?)")
    if not p["files"] and len(local_inputs(list_videos(Path(p["folder"])))) > MAX_INPUTS:     # as the build counts them
        raise ValueError(f"This folder has more than {MAX_INPUTS} videos now. Make a new reel from it (Auto Edit → New reel): "
                         "you can pick a day or the videos there.")
    settings = normalize_settings(raw_settings, model_ready=model_status()["ready"])
    key = _request_key(p, settings)
    with _CACHE_LOCK, db() as con:      # (not while a Free empties the folders this build would write into)
        con.execute("BEGIN IMMEDIATE")  # lookup + insert as one step: a double click never queues twice
        same = con.execute("SELECT * FROM ae_jobs WHERE project_id=? AND request_key=? ORDER BY id DESC LIMIT 1", (int(pid), key)).fetchone()
        n_same = con.execute("SELECT COUNT(*) n FROM ae_jobs WHERE project_id=? AND request_key=? AND status='done'",
                             (int(pid), key)).fetchone()["n"]
        # a reel made worse by a passing problem is built once more; if it comes out the same, that is the video itself
        if same and (same["status"] in ("queued", "running")
                     or (same["status"] == "done" and not _result_gone(same) and (n_same >= 2 or not _degraded(same)))):
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


def _result_gone(job_row) -> bool:
    """The reel of a finished build is not on this PC any more (deleted or quarantined outside the app): the same
    request builds it again instead of pointing at a missing file. A prepare job has no reel: never gone."""
    try:
        rid = job_row["revision_id"]
        if not rid:
            return False
        r = revision(int(rid))
        return not r or not Path(r["video_path"]).is_file()
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return False


def _degraded(job_row) -> bool:
    """A finished reel made worse by a passing problem (a video skipped for a time-out or an error, pieces from the
    small previews): the same request builds it again instead of returning it."""
    try:
        rid = job_row["revision_id"]
        if not rid:
            return False
        res = json.loads(Path((revision(int(rid)) or {}).get("result_path") or "").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return False
    if any(str(x.get("reason") or "").startswith(("ANALYSIS_TIMEOUT", "ANALYSIS_FAILED"))
           for x in res.get("skipped_inputs") or [] if isinstance(x, dict)):
        return True              # (a damaged or Private video, a duplicate, "no moments" are the videos themselves)
    return any(str(w).startswith("PREVIEW_QUALITY_USED") for w in res.get("warnings") or [])


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
        if d["status"] == "done" and d["settings"].get("prepare"):
            d["label"] = "Prepared"
        out.append(d)
    return out


def job(jid: int) -> dict | None:
    if not _sql_int(jid):
        return None
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


def is_prepare(j: dict) -> bool:
    """A "Prepare in advance" job (analysis only, no reel)."""
    s = j.get("settings")
    if s is None:
        try:
            s = json.loads(j.get("settings_json") or "{}")
        except (TypeError, ValueError):
            s = {}
    return bool((s or {}).get("prepare"))


def job_percent(j: dict) -> int:
    if j.get("status") == "done":
        return 100
    lo, hi = (STAGE_SPAN_PREPARE if is_prepare(j) else STAGE_SPAN).get(j.get("stage") or "queued", (0, 0))
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
            cur = con.execute("UPDATE ae_jobs SET status='cancelled',stage='cancelled',finished_at=?,message='Cancelled by user' "
                              "WHERE id=? AND status='queued'", (now_iso(), jid))
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
            if _pc_test_running():        # a reel next to the PC test would skew the test's numbers: it waits
                with db() as con:
                    con.execute("UPDATE ae_jobs SET message=? WHERE id=? AND status='queued'",
                                ("Waiting for the test on Check this PC to finish", jid))
                    con.commit()
                jid = None
                _WAKE.wait(5)
                _WAKE.clear()
                continue
            _run_job(jid)
        except Exception as exc:  # never let the worker die
            try:
                if jid is not None:
                    with db() as con:
                        con.execute("UPDATE ae_jobs SET status='failed',stage='failed',error=?,finished_at=? WHERE id=? AND status IN ('queued','running')",
                                    (friendly_error("Internal error: " + str(exc)), now_iso(), jid))
                        con.commit()
            except Exception:
                pass
            time.sleep(1)


def _pc_test_running() -> str:
    """The test reel or the graphics-card test of Check this PC is running (they measure this PC's speed)."""
    try:
        if selftest_state()["running"]:
            return "The test reel of Check this PC is being made. Wait until it is ready."
    except Exception:
        pass
    try:
        from . import hwdecode
        if hwdecode.state().get("running"):
            return "The graphics card is being tested (Check this PC). Wait until the test has finished."
    except Exception:
        pass
    return ""


def _engine_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
    ff = _ffmpeg() or "ffmpeg"
    env.update({"MEDENG_FFMPEG": ff, "MEDENG_FFPROBE": ff, "MEDENG_P11_MODEL_ROOT": str(model_root()), "MEDENG_P13_PE_DIR": str(aiplus_dir()),
                "MEDENG_P13_TEXT_CACHE": str(AE_ROOT / "shared" / "semantic_text_pe"),
                "MEDENG_P13_SCOUT_CACHE": str(AE_ROOT / "shared" / "semantic_scout_pe"),
                # what the AI found in each video and the moment clips, for every project (by the video's SHA-256)
                "MEDENG_AI_SHARED_CACHE": str(AE_ROOT / "shared"),
                "MEDENG_P11_ADAPTER_ROOT": str(ENGINE_DIR), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1"})   # engine helpers started without -E: nothing written into the program folder
    try:      # decoding on the graphics card: only a method THIS PC proved identical and faster (Check this PC)
        from . import hwdecode
        hw = hwdecode.method_for_engine(ff)
        kinds = hwdecode.proven_kinds(hwdecode.saved(), hw) if hw else []
        if hw and kinds:
            env["MEDENG_HWACCEL"] = hw
            env["MEDENG_HWACCEL_KINDS"] = ",".join(kinds)
        else:
            env.pop("MEDENG_HWACCEL", None); env.pop("MEDENG_HWACCEL_KINDS", None)
    except Exception:
        env.pop("MEDENG_HWACCEL", None); env.pop("MEDENG_HWACCEL_KINDS", None)
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
                   skip_sha_file: Path | None = None, input_list: Path | None = None, dress_file: Path | None = None) -> list[str]:
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
    if s.get("framing") == "fit_blur":
        cmd += ["--vertical-framing", "fit_blur"]
    if dress_file is not None and (s.get("title") or s.get("subtitle") or s.get("music") or s.get("look")) and not s.get("prepare"):
        cmd += ["--dress", str(dress_file)]
    if s.get("prepare"):
        cmd += ["--prepare-only"]
    return cmd


def running_elsewhere(pid: int) -> dict | None:
    """The reel being made now in another project (reels are made one at a time): its id and title."""
    with db() as con:
        r = con.execute("SELECT p.id,p.title FROM ae_jobs j JOIN ae_projects p ON p.id=j.project_id "
                        "WHERE j.status='running' AND j.project_id<>? ORDER BY j.id LIMIT 1", (int(pid),)).fetchone()
    return dict(r) if r else None


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
    for sub in ("semantic_candidates", "semantic_candidates_pe"):   # this project's full-size clips of b100-b113: unused now
        shutil.rmtree(work_dir / sub, ignore_errors=True)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    progress_file.unlink(missing_ok=True)
    edits_file = jobs_dir / f"j{jid}.edits.json"
    edits_file.write_text(json.dumps({"selection": s.get("selection") or [], "trims": s.get("trims") or {}}), encoding="utf-8")
    skip_file = jobs_dir / f"j{jid}.private_sha.txt"
    skip_file.write_text("\n".join(_private_hashes()), encoding="utf-8")
    try:
        tidy_shared_cache(_private_hashes())
    except Exception:
        pass
    try:
        tidy_work_caches(keep_pid=int(p["id"]))
    except Exception:
        pass
    # checked again when the build really starts (an overnight batch was queued hours ago): a card unplugged since, a
    # disk filled since - a clear reason instead of "no supported video files" or a build that dies half-way
    late = ""
    if not p.get("source_present", True):
        late = ("The source videos are not available (card or drive disconnected?). Plug it in and press Retry."
                if p.get("files") else "The source folder is not available (card or drive disconnected?). Plug it in and press Retry.")
    else:
        try:
            check_free_space()
        except ValueError as exc:
            late = str(exc)
    if late:
        _set(jid, status="failed", stage="failed", finished_at=now_iso(), error=late)
        _notify_finished(jid, p, False)
        return
    dress_file = jobs_dir / f"j{jid}.dress.json"
    dress_file.write_text(json.dumps({"title": s.get("title") or "", "subtitle": s.get("subtitle") or "", "music": s.get("music") or "",
                                      "music_mode": s.get("music_mode") or "mix", "beat_sync": s.get("beat_sync") is not False,
                                      "look": s.get("look") or ""},
                                     ensure_ascii=False), encoding="utf-8")
    input_list = None
    note = lambda name: _set(jid, message="Preparing a recording without a length: " + name)
    try:
        with keep_awake():
            if p.get("files"):
                chosen = local_inputs(_not_private_paths(p["files"]))
                # over every chosen file, there or not: names never swap when one of two cards is unplugged
                alias = {str(x): nm for x, nm in input_names([Path(f) for f in p["files"]])}
                local, _ = _with_length(chosen, work_dir, note, jid)
                input_list = jobs_dir / f"j{jid}.inputs.txt"
                # "path<TAB>name" for a video whose reel name is not its file name (same name in two folders)
                input_list.write_text("".join(str(x) + (("\t" + alias[str(o)]) if alias.get(str(o), Path(o).name) != Path(x).name else "") + "\n"
                                              for o, x in zip(chosen, local)), encoding="utf-8", errors="surrogatepass")
            else:
                vids = list_videos(Path(p["folder"]))
                usable = local_inputs(_not_private_paths(vids))
                local, fixed = _with_length(usable, work_dir, note, jid)
                if fixed or len(local) != len(vids):   # cloud-only placeholders / fixed copies: give the engine the exact list
                    input_list = jobs_dir / f"j{jid}.inputs.txt"     # (a fixed copy keeps its video's name in the reel)
                    input_list.write_text("".join(str(x) + (("\t" + Path(o).name) if Path(o).name != Path(x).name else "") + "\n"
                                                  for o, x in zip(usable, local)), encoding="utf-8", errors="surrogatepass")
    except _Stopped:
        with _LOCK:
            _CANCEL.discard(jid)
        _set(jid, status="cancelled", stage="cancelled", finished_at=now_iso(), message="Cancelled by user")
        return
    cmd = engine_command(Path(p["folder"]), out_dir, work_dir, progress_file, s, edits_file, skip_file, input_list, dress_file)
    kw = process_kwargs(below_normal=True) if os.name == "nt" else {"start_new_session": True}
    with log_file.open("w", encoding="utf-8", errors="replace") as log, keep_awake():
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=_engine_env(), cwd=str(ENGINE_DIR), **kw)
        _attach_job_object(proc)
        with _LOCK:
            _RUNNING[jid] = proc
        stalled = False
        alive_at = time.monotonic()
        last_seen = None
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
                try:          # the engine says nothing (progress, log) for a long time: a hung FFmpeg on a stalled drive
                    seen = tuple((f.stat().st_mtime_ns, f.stat().st_size) if f.exists() else None for f in (progress_file, log_file))
                except OSError:
                    seen = last_seen
                if seen != last_seen:
                    last_seen, alive_at = seen, time.monotonic()
                elif time.monotonic() - alive_at > ENGINE_STALL_S:
                    stalled = True                 # (the rest of an overnight queue goes on)
                    _kill_tree(proc)
                    proc.wait(30)
                    break
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
    if stalled:
        shutil.rmtree(out_dir, ignore_errors=True)
        _set(jid, status="failed", stage="failed", finished_at=now_iso(),
             error=f"The build made no progress for {ENGINE_STALL_S // 60} minutes and was stopped (a drive or a video "
                   "that does not answer?). Press Retry - finished analysis is reused.")
        _notify_finished(jid, p, False)
        return
    if proc.returncode != 0:
        shutil.rmtree(out_dir, ignore_errors=True)
        _set(jid, status="failed", stage="failed", finished_at=now_iso(), error=_engine_error(log_file))
        _notify_finished(jid, p, False)
        return
    if s.get("prepare"):
        # "Prepare in advance": no reel, only the analysis in the caches; what was done is kept for the project page
        info = prepared_info(jid, out_dir)
        if not info:
            _set(jid, status="failed", stage="failed", finished_at=now_iso(), error=friendly_error("PREPARED_RESULT_MISSING"))
            _notify_finished(jid, p, False)
            return
        _set(jid, status="done", stage="done", done=1, total=1, finished_at=now_iso(), message="Prepared")
        _notify_finished(jid, p, True)
        return
    try:          # a video marked Private while this reel was being built: the reel is not kept
        gone = private_in_result(json.loads((out_dir / "MediaEngine Result.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        gone = []
    if gone:
        shutil.rmtree(out_dir, ignore_errors=True)
        _set(jid, status="failed", stage="failed", finished_at=now_iso(), error=friendly_error("PRIVATE_DURING_BUILD: " + ", ".join(gone)[:200]))
        _notify_finished(jid, p, False)
        return
    rid = _publish_revision(p["id"], jid, out_dir, s)
    _set(jid, status="done", stage="done", done=1, total=1, revision_id=rid, finished_at=now_iso(), message="Ready")
    _notify_finished(jid, p, True)


def prepared_info(jid: int, out_dir: Path | None = None) -> dict | None:
    """What a finished "Prepare in advance" job did (the engine's MediaEngine Prepared.json), or None."""
    if out_dir is None:
        j = job(jid)
        if not j:
            return None
        out_dir = _project_dir(j["project_id"]) / "jobs" / f"j{int(jid)}"
    try:
        d = json.loads((Path(out_dir) / "MediaEngine Prepared.json").read_text(encoding="utf-8"))
        return d if d.get("prepared") is True else None
    except (OSError, ValueError):
        return None


ENGINE_STALL_S = 90 * 60     # no word from the engine for this long: stopped (a hung read; normal steps report sooner)
_BATCH = {"started": None, "ok": 0, "failed": 0}


def _notify_finished(jid: int, p: dict, ok: bool) -> None:
    """A Windows notification after a long build, when nothing else is waiting (reels for every day: one at the end,
    saying how many were made and how many failed, timed from the first one)."""
    try:
        j = job(jid) or {}
        with _LOCK:
            if _BATCH["started"] is None:
                _BATCH["started"] = time.time() - job_elapsed_s(j)
            _BATCH["ok" if ok else "failed"] += 1
        with db() as con:
            if con.execute("SELECT 1 FROM ae_jobs WHERE status IN ('queued','running') AND id<>? LIMIT 1", (int(jid),)).fetchone():
                return
        with _LOCK:
            n_ok, n_bad, t0 = _BATCH["ok"], _BATCH["failed"], _BATCH["started"]
            _BATCH.update(started=None, ok=0, failed=0)
        from . import notify
        from .config import APP_PORT
        ru = ui_language() == "ru"
        if n_ok + n_bad > 1:
            title = (f"Готово: {n_ok}, не получилось: {n_bad}" if ru else f"Ready: {n_ok}, failed: {n_bad}")
            notify.reel_finished(title, n_bad == 0, time.time() - float(t0 or time.time()),
                                 f"http://127.0.0.1:{APP_PORT}/auto", ru, prepared=is_prepare(j))
            return
        notify.reel_finished(str(p.get("title") or ""), ok, job_elapsed_s(j),
                             f"http://127.0.0.1:{APP_PORT}/auto/p/{int(p['id'])}", ru, prepared=is_prepare(j))
    except Exception:
        pass


def _private_paths() -> set:
    """Files marked Private in the Library whose content was never hashed (marked while the drive was unplugged):
    kept out of reels by their path (the engine skips Private videos by SHA-256)."""
    try:
        with db() as con:
            rows = con.execute("SELECT path,staging_path,archive_path FROM inventory WHERE analysis_status='private' "
                               "AND (sha256 IS NULL OR sha256='')").fetchall()
    except Exception:
        return set()
    return {_path_key(r[k]) for r in rows for k in ("path", "staging_path", "archive_path") if r[k]}


def _path_key(x) -> str:
    """The same key for one file however it is written (a mapped drive, a junction, letter case) - as the project
    stores it (resolved)."""
    try:
        return os.path.normcase(os.path.realpath(str(x)))
    except (OSError, ValueError):
        return os.path.normcase(os.path.abspath(str(x)))


def _not_private_paths(paths) -> list:
    priv = _private_paths()
    return [x for x in paths if _path_key(x) not in priv] if priv else list(paths)


def private_in_result(res: dict) -> list[str]:
    """Names of the videos in a reel (its result) that are marked Private now."""
    priv = set(_private_hashes())
    if not priv:
        return []
    by_name = {str(x.get("name")): str(x.get("sha256") or "").lower() for x in (res or {}).get("inputs") or []}
    used = {str(sg.get("source_name")) for sg in (res or {}).get("segments") or []}
    return sorted(n for n in used if by_name.get(n) in priv)


def _refuse_private(r: dict) -> None:
    if private_in_result(r.get("result") or {}):
        raise ValueError("This version contains a video that is marked Private now. Make a new version (Let MediaEngine "
                         "choose again, or a variant): it is made without that video.")


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
    if "eta_s" in d:      # the engine's own estimate for this stage (None: not known yet)
        ENGINE_ETA[int(jid)] = (stage, d.get("eta_s"), float(d.get("at") or time.time()))
    else:
        ENGINE_ETA.pop(int(jid), None)
    _set(jid, stage=stage, done=int(d.get("done") or 0), total=int(d.get("total") or 0), message=str(d.get("message") or "")[:300])


ENGINE_ETA: dict = {}     # job id -> (stage, seconds left or None, when the engine wrote it)


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
    "MUSIC_FILE_MISSING": "The music file is not there any more. Choose it again or make the version without music.",
    "MUSIC_FILE_NOT_AUDIO": "The chosen music is not an audio file (mp3, m4a, wav, flac, ogg...).",
    "MUSIC_FILE_NO_SOUND": "The chosen music file has no sound that can be read. Choose another file.",
    "NO_SEMANTIC_CANDIDATES": "The AI found no usable moments in these videos. Press Retry; if it repeats, build without AI.",
    "SEMANTIC_CANDIDATE_EXTRACT_FAILED": "A moment could not be cut from one of the videos. Press Retry; if it repeats, build without AI.",
    "DISSOLVE_BLOCK_RENDER_FAILED": "The final video could not be put together. Press Retry; if it repeats, free the cache of this project.",
    "FINAL_DECODE_FAILED": "The finished reel could not be read back for the check. Press Retry; if it repeats, free the cache of this project.",
    "CAMERA_DROP_PRETRIM_FAILED": "A moment could not be prepared. Press Retry; if it repeats, free the cache of this project.",
    "EDIT_TRIM_FAILED": "A trimmed moment could not be cut. Check its times or let MediaEngine choose again.",
    "EDIT_DUPLICATE_MOMENT": "The same moment was chosen twice. Choose another one.",
    "OUTPUT_DIMENSIONS_MISMATCH": "The reel came out in a wrong size. Press Retry; if it repeats, free the cache of this project.",
    "FINAL_COPY_VERIFY_FAILED": "The finished reel could not be saved correctly. Check the free space and press Retry.",
    "UNKNOWN_THEME": "This theme is not available. Choose another one.",
    "PRIVATE_DURING_BUILD": "A video of this reel was marked Private while the reel was being built, so the reel was not kept. Press Retry (for a version edited by hand: Let MediaEngine choose again): it is made without that video.",
    "Rendered reel does not match": "The finished reel could not be saved correctly. Press Retry.",
}

# shown when nothing above matches: a plain sentence, the technical code only in small print
UNKNOWN_FAILURE = "The reel could not be built. Press Retry; if it repeats, build without AI or free the cache of this project."


def _engine_error(log_file: Path) -> str:
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        text = ""
    m = re.findall(r'"error":\s*"([^"]+)"', text)
    raw = m[-1] if m else (text.strip().splitlines() or ["Engine stopped without a result"])[-1]
    return friendly_error(raw)


def friendly_error(raw: str) -> str:
    """A sentence the owner understands, the technical code in [brackets] (shown in small print)."""
    raw = str(raw or "")
    for code, msg in _FRIENDLY.items():
        if code in raw:
            return msg + " [" + raw[:200] + "]"
    return UNKNOWN_FAILURE + " [" + raw[:300] + "]"


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
    _replace_retry(video, vdst)
    _replace_retry(result, rdst)
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
    if not _sql_int(rid):
        return None
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


def revert(pid: int, expect: int | None = None) -> int | None:
    """Move the accepted pointer back to the previously accepted revision (files untouched). expect: the version the
    button was shown for - when it is not the accepted one any more (a double click), nothing changes."""
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("SELECT accepted_revision_id FROM ae_projects WHERE id=?", (int(pid),)).fetchone()
        if not cur:
            con.rollback()
            raise ValueError("Project not found")
        if expect is not None and cur["accepted_revision_id"] != int(expect):
            con.rollback()
            return cur["accepted_revision_id"]
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


_LOOK_FILTERS: dict = {}


def look_filters() -> dict:
    """The engine's colour filters (engine_p11/p13_looks.py): the preview pictures use exactly what the reel gets."""
    if not _LOOK_FILTERS:
        import importlib.util
        spec = importlib.util.spec_from_file_location("medeng_p13_looks", ENGINE_DIR / "p13_looks.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LOOK_FILTERS.update(mod.LOOKS)
    return _LOOK_FILTERS


def look_source_revision(p: dict, rev: dict | None) -> dict | None:
    """The version the colour previews are made from: this one when it has no colours of its own, else the newest
    version of the project without them (colours are never put on top of other colours); None when there is none."""
    if rev and not (rev.get("settings") or {}).get("look"):
        return rev
    plain = [r for r in (p.get("revisions") or []) if not (r.get("settings") or {}).get("look")]
    return plain[-1] if plain else None


def look_preview(rid: int, look: str) -> Path | None:
    """A small picture of a moment of a version in one of the colour looks (to choose before a new version is
    made). Cached next to the project's data; made from the version's own file, never from the videos."""
    r = revision(rid)
    if not r or look not in LOOKS or (r.get("settings") or {}).get("look"):
        return None
    _refuse_private(r)
    vf_look = "" if look == "natural" else look_filters().get(look)
    if vf_look is None:
        return None
    segs = (r.get("result") or {}).get("segments") or []
    dur = float(r.get("duration_s") or (r.get("result") or {}).get("actual_duration_s") or 0)
    seg = segs[1] if len(segs) > 1 else (segs[0] if segs else None)     # (not under the title of the first seconds)
    t = (float(seg["reel_in_s"]) + float(seg["reel_out_s"])) / 2.0 if seg else dur * 0.4
    if t < 3.4 and dur > 4.0:
        t = min(dur - 0.3, 3.6)
    out = _project_dir(r["project_id"]) / "thumbs" / f"r{int(rid)}_look_{look}.jpg"
    if out.is_file() and out.stat().st_size > 0:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part.jpg")
    vf = ("scale=w='if(gte(iw,ih),320,-2)':h='if(gte(iw,ih),-2,320)',setsar=1,scale=out_range=tv,format=yuv420p"
          + ("," + vf_look if vf_look else ""))
    try:
        subprocess.run([_ffmpeg() or "ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(r["video_path"]), "-frames:v", "1",
                        "-vf", vf, "-q:v", "3", str(tmp)], **process_kwargs({"capture_output": True, "timeout": 60}))
        if tmp.is_file() and tmp.stat().st_size > 0:
            os.replace(tmp, out)
            return out
    except Exception:
        pass
    finally:
        tmp.unlink(missing_ok=True)
    return None


def look_preview_of_video(path, look: str) -> Path | None:
    """A small picture of one of the user's videos in a colour look - on the new-reel page, to choose before the first
    build. One frame (an HDR phone video converted to normal colours first, as the reel does), cached by the file's
    name, size and time; the video is only read."""
    if look not in LOOKS:
        return None
    src = Path(str(path or "").strip().strip('"'))
    if not src.is_absolute() or src.suffix.lower() not in SUPPORTED or not src.is_file() or cloud_only(src):
        return None
    _guard_private(src)
    vf_look = "" if look == "natural" else look_filters().get(look)
    if vf_look is None:
        return None
    st = src.stat()
    key = hashlib.sha256(f"{src}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8", "replace")).hexdigest()[:24]
    d = AE_ROOT / "look_previews"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{key}_{look}.jpg"
    if out.is_file() and out.stat().st_size > 0:
        return out
    ff = _ffmpeg() or "ffmpeg"
    base = d / f"{key}.png"
    with _LOOK_LOCK:
        if not (base.is_file() and base.stat().st_size > 0):
            try:
                old = sorted(d.glob("*"), key=lambda x: x.stat().st_mtime)
                for x in old[:-300]:              # a few hundred small pictures at most
                    x.unlink(missing_ok=True)
            except OSError:
                pass
            from .converter import HDR_TO_SDR, _hdr_kind
            hdr = _hdr_kind(ff, src)
            try:
                dur = float(probe_any(src).get("format", {}).get("duration") or 0)
            except Exception:
                dur = 0.0
            vf0 = ([HDR_TO_SDR[hdr]] if hdr in HDR_TO_SDR else []) + \
                  ["scale=w='if(gte(iw,ih),320,-2)':h='if(gte(iw,ih),-2,320)'", "setsar=1", "scale=out_range=tv", "format=yuv420p",
                   "scale=in_range=tv:in_color_matrix=bt709:out_range=pc", "format=rgb24"]      # (back the same way below)
            tmp = base.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part.png")
            try:
                subprocess.run([ff, "-v", "error", "-y", "-ss", f"{max(0.0, dur * 0.4):.3f}", "-i", str(src), "-frames:v", "1",
                                "-vf", ",".join(vf0), str(tmp)], **process_kwargs({"capture_output": True, "timeout": 120}))
                if tmp.is_file() and tmp.stat().st_size > 0:
                    os.replace(tmp, base)
            except Exception:
                pass
            finally:
                tmp.unlink(missing_ok=True)
        if not base.is_file():
            return None
    tmp = out.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part.jpg")
    vf = "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p" + ("," + vf_look if vf_look else "")
    try:
        subprocess.run([ff, "-v", "error", "-y", "-i", str(base), "-frames:v", "1", "-vf", vf, "-q:v", "3", str(tmp)],
                       **process_kwargs({"capture_output": True, "timeout": 60}))
        if tmp.is_file() and tmp.stat().st_size > 0:
            os.replace(tmp, out)
            return out
    except Exception:
        pass
    finally:
        tmp.unlink(missing_ok=True)
    return None


_LOOK_LOCK = threading.Lock()


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
        ("not downloaded yet - 'Download the AI model' below (30 MB); until then only 'Technical only' reels" if ms["reason"] == "MODEL_MISSING"
         else "files changed or incomplete - not used; download the AI model again below"))
    ap = aiplus_status()
    if ap["ready"]:
        add("AI+ model (PE-Core L/14, optional)", True, ap["path"])
    elif ap["reason"] == "AIPLUS_MISSING":           # optional and not there: information, not a warning
        add("AI+ model (PE-Core L/14, optional)", True, "not downloaded yet - see AI+ below", "info")
    else:
        add("AI+ model (PE-Core L/14, optional)", False, "files changed or incomplete - not used")
    try:
        cp = subprocess.run([engine_python(), "-B", "-s", "-E", "-c",
                             "import numpy, cv2, onnxruntime; print('numpy', numpy.__version__, '| opencv', cv2.__version__, '| onnxruntime', onnxruntime.__version__)"],
                            **process_kwargs({"capture_output": True, "text": True, "timeout": 120}))
        add("Engine libraries load (numpy, OpenCV, ONNX Runtime)", cp.returncode == 0,
            cp.stdout.strip() or (cp.stderr.strip().splitlines() or ["failed"])[-1][:300])
    except Exception as exc:
        add("Engine libraries load (numpy, OpenCV, ONNX Runtime)", False, exc)
    add("Processor", True, f"{os.cpu_count() or '?'} logical cores")
    try:
        from . import hwdecode
        gpus = hwdecode.gpu_names_cached()
        if gpus:
            add("Graphics card", True, "; ".join(gpus))
        used, line = hwdecode.summary(hwdecode.saved(), ff)
        add("Video decoding on the graphics card", True, line, "ok" if used else "info")
    except Exception:
        pass
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
    try:                                     # the voice-over add-on (optional, installed with a button)
        from . import voice as _vo
        m = _vo.manifest()
        if _vo.installed():
            add("Voice-over add-on (optional)", True, ("graphics card " + (m.get("gpu") or "")) if m.get("cuda")
                else "on the processor")
        elif m:
            add("Voice-over add-on (optional)", False, "needs to be installed again (Auto Edit → Voice-over)")
        else:
            add("Voice-over add-on (optional)", True, "not installed - Auto Edit → Voice-over", "info")
    except Exception:
        pass
    import platform
    from .config import BUILD, VERSION
    add("MediaEngine version", True, f"{VERSION} {BUILD}".strip())
    add("Windows", True, platform.platform() if os.name == "nt" else platform.system())
    return rows


# (since, text): someone who saw the card before sees only what came after it
WHATS_NEW_ITEMS = [
    ("2026-10-14", "“Save MP4” in one step on any version (no separate Accept)."),
    ("2026-10-14", "A reel for every day of a trip: open a big folder, “A reel for every day”."),
    ("2026-10-14", "Vertical reel from horizontal videos: the whole picture with blurred edges, if you like."),
    ("2026-10-14", "“Small copy for messengers” next to Save MP4."),
    ("2026-10-14", "Library: select videos and press “Make a reel”."),
    ("2026-10-14", "Reels up to 2 minutes; the new reel starts with your last settings."),
    ("2026-10-14", "A reel being made is shown at the top of every page."),
    ("2026-10-15", "AI mode is faster with big videos (4K): several videos are analysed at once, moments are cut quicker."),
    ("2026-10-15", "A new reel from videos that were already analysed (another project, a reel for every day) analyses and cuts nothing again."),
    ("2026-10-15", "While moments are being found: about how many minutes are left."),
    ("2026-10-15", "A Windows notification when a reel that took more than a minute is ready (can be turned off in Settings)."),
    ("2026-10-15b", "AI with 4K videos is faster again: moments are looked at in small copies, the reel is cut from the originals."),
    ("2026-10-15b", "“Prepare in advance” on the new-reel page: the videos are analysed now (for example overnight), the reel is then made in minutes."),
    ("2026-10-15b", "AI+ theme “Aerial view (drone)”: the view from above, without take-off and landing on the ground."),
    ("2026-10-16", "Check this PC can test the graphics card: if it decodes 4K faster with exactly the same picture, the videos are cut with it."),
    ("2026-10-16", "Choosing the moments of a new reel length uses several processor cores (the same choice, found faster)."),
    ("2026-10-16", "“Prepare in advance” for a reel for every day of a big folder too."),
    ("2026-10-17", "Orders from other programs: a program puts an order into the Inbox folder (Auto Edit → Orders), MediaEngine makes the video and puts it into Done."),
    ("2026-10-17b", "MediaEngine is in the tray (next to the clock): click it to open the window, right-click → Quit to close the program."),
    ("2026-10-17b", "A new version takes over from the old one by itself, without the “switch?” question."),
    ("2026-10-18", "The “Update” button at the top: MediaEngine finds a newer version on GitHub and installs it itself (only when you press it)."),
    ("2026-10-18", "Settings: start MediaEngine in the background when you sign in to Windows (off unless you turn it on); reels waiting from before a restart go on."),
    ("2026-10-18", "A reel being made when the PC restarts (or MediaEngine stops without Quit) is made again by itself at the next start, once."),
    ("2026-10-19", "Voice-over (Auto Edit → Voice-over, an add-on installed with a button): a text read by a voice, checked word by word, captions timed to the words, the voice and captions put onto a video."),
    ("2026-10-19", "Captions for your own videos: the speech becomes captions burned into a copy (Auto Edit → Voice-over)."),
    ("2026-10-19b", "Voice-over: your picks from the voice test, the voices 4_4 and 4_2, instead of 3.1."),
    ("2026-10-20", "Text on a video (Auto Edit → Voice-over and text): titles and lines of text at the moments you choose, on a colored stripe, a dark box or in big letters - no add-on needed."),
    ("2026-10-22", "Captions in two more looks: one word at a time, big (like TikTok), and the word being said on a color block."),
    ("2026-10-30e", "Edit by hand (Create): a video put together yourself from pieces of any videos (this PC, the Library, the downloads, found moments) on a time line - cut by the edges, move, split (S), remove, undo; the MP4 in 9:16, 16:9, 1:1 or 4:5, made in the background into the Edits folder."),
    ("2026-10-30d", "Cartoon Studio, a film's page (Change and make again): the film in another language at the top (translated with the same people, voices and look, or retold for a country - made at once or read first; needs the story writer); a picture of every scene; add a line anywhere, remove lines, move or remove scenes, change the title."),
    ("2026-10-30c", "Cartoon Studio: livelier characters - the mouth takes the shape of the sound said (a, o, u, e, closed for m/b/p), the eyes glance about, a nod and raised brows on the words that matter, a new gesture swings a little past and settles, blinks come at uneven times."),
    ("2026-10-30b", "Cartoon Studio: the drawing style - flat (as before), hand-drawn, a whiteboard, paper cut-out or motion graphics, with a little picture of each where the cartoon is made."),
    ("2026-10-30", "Inbox (in the menu, under Home): links and topics to work on - typed there, from other programs, or sent from your phone through your own Telegram bot (Settings → Phone). Settings → Look: the size of everything and ten colour schemes."),
    ("2026-10-29d", "A new look: the menu on the left, grouped by what you do (Create, Videos, Tools); Home shows what to make and the recent work of every part; each kind of work has its own colour (Settings → Look: also “Neon on black” or “Calm night”)."),
    ("2026-10-29c", "Cartoon Studio: an author's style - several studied videos (say, the ones downloaded from one profile) taken together: the middle of their rhythms and their colours; then “Write a story in this style”. The topic of a story may be typed in any language, even in translit."),
    ("2026-10-29b", "Download by a link (Media → Download by a link): a video, or chosen videos of a profile or channel, from YouTube, TikTok and other sites into the Downloaded folder - then study its rhythm, write a story from it, cut clips or convert."),
    ("2026-10-29", "Convert: the size can be as small as 5 MB (for a chat or a messenger with a limit) - the picture is made smaller so the video fits and stays clear."),
    ("2026-10-29", "Cartoon Studio: the story writer uses the viewers' measures - miles, feet and gallons for the United States, kilometres elsewhere; the voices of all characters equally loud."),
    ("2026-10-28h", "Cartoon Studio: add a character before any film and make it “The host of my films” (every new story gets this narrator); the pauses between lines follow the pace (quick or calm); more sounds - a pop for speech bubbles and pictures, a bell for the magnifier."),
    ("2026-10-28g", "Cartoon Studio: close-ups of the one speaking; the story writer can make the cartoon at once and write a whole series (several topics, one per line) while you are away."),
    ("2026-10-28f", "Cartoon Studio: “Study a cartoon you like” - a video on this PC: where its shots change, a picture of each (a storyboard), its colours and, with the voice add-on, how fast and how soon it speaks; then “Write a story with this rhythm”."),
    ("2026-10-28e", "Cartoon Studio: music under the cartoon - made by the program (light, a little suspense or calm), your own music file or none, softer while someone speaks; scenes slide in or open as a circle; new pictures (a share of a whole, a timeline of dates) and places (a hospital, a school, a shop, a block of flats, a building site)."),
    ('2026-10-28c', "Cartoon Studio: the story can be written by a free model on this PC (Qwen3-14B or the smaller Qwen3-4B, installed once with a button) - from a topic, a pasted text or a video on this PC, or a story retold for another country, in English, Russian or Romanian; read it, change it, make the cartoon. Characters keep their look and voice (the Characters page)."),
    ('2026-10-28b', "Cartoon Studio (Auto Edit → Cartoon Studio): a 2D cartoon made by MediaEngine - its own characters, scenes, schemes of money, voices and captions; change a line and make it again."),
    ('2026-10-28', "Clips: \"The one speaking, close up\" - when two or three people stand side by side, the clip shows whoever is talking, close up, and switches when another one talks."),
    ('2026-10-27c', "Clips: the frame goes with someone who walks; people standing side by side all stay in the picture, as big as they fit."),
    ('2026-10-27b', "Clips from a long video (Auto Edit → Clips from a long video): a podcast, stream or interview is listened to once; the parts that make good short clips are listed with their words; the ticked ones become vertical clips with the face in the frame, the sound and captions."),
    ('2026-10-27', "Reel colours: as filmed, brighter and richer, warm or cinematic (a variant shows a small picture of each) - pale drone videos come out livelier. Only the reel is coloured; your videos stay as they are."),
    ('2026-10-26', "Auto Edit with DJI videos: when the camera's small copy (.LRF) lies next to a video, the AI finds the moments in it - a first build much faster; the reel is still cut from the original 4K."),
    ('2026-10-25c', "Auto Edit: each project shows when its last version was made; a project from a camera's own folder (100MEDIA, 100GOPRO …) is named with the days it was filmed; a folder that already has a project says so on the new-reel page."),
    ('2026-10-25c', 'Convert: on a PC with an NVIDIA card that was never tested, the first conversion tests the card by itself first (about two minutes), then converts on whichever was faster with the same picture.'),
    ('2026-10-25c', 'Music for a reel or a video: the window opens in the folder of the music you chose last time.'),
    ('2026-10-25b', 'Composer: remove a moment, take out the moments of videos made Private, delete a composition.'),
    ('2026-10-25b', 'Check this PC: “Remove the older versions” frees the space of old MediaEngine versions (the two newest stay, to go back to).'),
    ('2026-10-25b', 'Voice-over: the word check reads numbers and signs written either way (20% / twenty percent, e-mail / email, 5 p.m. / five PM) - fewer pieces made again; Russian letters with English chosen are refused in words.'),
    ('2026-10-25b', 'Reels from many 4K videos: their moments are cut more at once on a PC with many cores.'),
    ('2026-10-25', "GoPro and DJI videos: the time of filming is the camera's own clock (Library dates, the days of a big folder, the date and time in the corner); the Convert list shows when each video was filmed."),
    ('2026-10-25', 'Convert: the NVIDIA card also for turned videos and the More options (speed, vertical, logo, date and time…) - once “Test converting on the graphics card” made them there with the same picture and faster (press the test once more).'),
    ("2026-10-24j", "Convert: pictures from long videos are saved many times faster (each picture read from its own moment, not the whole video decoded)."),
    ("2026-10-24i", "Convert: Select all / Clear the selection; the preset and the lasting choices (sound, date and time, Brighter, logo, how often pictures are taken) are remembered; a copy shorter than its video (a damaged or half-copied file) says so."),
    ("2026-10-24h", "Convert → More: “Brighter” for videos filmed in the dark."),
    ("2026-10-24g", "Convert: a conversion started while another one runs waits in line and starts by itself after it (“Take out of the line” removes it)."),
    ("2026-10-24f", "Convert: “Save pictures of the selected videos” also makes one PDF of them (A4 pages, each picture with its moment and, when chosen, the date and time; your report title on top) - ready for a report."),
    ("2026-10-24e", "Convert → More: “Date and time in the corner” - when it was filmed, every second, from the camera or phone clock (for reports)."),
    ("2026-10-24d", "Convert → More: slow motion ½× and ¼× (smooth from 60 / 120 fps videos) and “Even out the sound” (quiet speech louder, loud parts softer)."),
    ("2026-10-24c", "Convert: pictures every 5 / 10 / 30 / 60 seconds of the selected videos (photos for a report) and a list of earlier conversions with their buttons."),
    ("2026-10-24b", "Convert → More: speed (2×, 4×, 8× faster), vertical 9:16 for Reels / TikTok (the middle, or the whole picture on a blurred background), your logo in a corner, less wind noise."),
    ("2026-10-24", "Check this PC: “Test converting on the graphics card” - a short 4K test clip made smaller with the processor and with the NVIDIA card; Convert uses the card only if it was faster with the same picture."),
    ("2026-10-23e", "Reels, finished videos and converted copies made from GoPro or phone footage keep normal brightness levels (dark and bright parts as filmed on every screen)."),
    ("2026-10-23d", "Convert: “Turn the picture” - 90° right or left, or upside down (a camera mounted the other way)."),
    ("2026-10-23d", "Convert: “Save this picture” in Cut… - a photo of the moment in the player, at the video's full size, into the folder of converted videos."),
    ("2026-10-23c", "Convert: “Without sound” - the copy has no sound at all (wind, voices on site)."),
    ("2026-10-23c", "Convert: “Cut…” next to a video - only the part between start and end is converted (set with the player or typed as minutes:seconds)."),
    ("2026-10-23b", "Convert: “Change…” - converted videos can go into a folder of yours (not a library folder); “Copy file” next to each one: Ctrl+V pastes it into a folder, an e-mail or a messenger."),
    ("2026-10-23", "Convert: “Join into one video” - parts of one recording (a GoPro splits a long one into files of 4 GB: GX010044, GX020044 …) become one video, in the recording's order; several GoPro recordings - one video each."),
    ("2026-10-23", "Convert: “Choose videos on this PC…” converts any video on the computer without adding it to the library; “Stop” on a running conversion; the time left."),
    ("2026-10-23", "Convert: big videos made smaller on an NVIDIA graphics card (much faster; if the card can't, the processor makes them as before); a Windows notification when a long conversion is ready."),
    ("2026-10-22b", "Convert: “Show in folder” and “Open video” next to each converted file, and “Open the folder” at the top; the last job keeps its list of files until “Remove from the page” (the files stay in the folder)."),
    ("2026-10-21b", "Voice-over: the voice 9_2 is said by a new, livelier engine (Qwen3-TTS - your pick 14_5); an installed voice add-on downloads it with one button (about 4.7 GB)."),
    ("2026-10-21", "Finish a video: several videos at once - the same voice, captions, look, texts and music on each (one new video per video)."),
    ("2026-10-21", "Voice-over: its pace - a bit slower or faster, shorter or longer pauses between sentences (the voice keeps its pitch, the captions follow); a voice from a recording can be kept in the voice list."),
    ("2026-10-20c", "Voice-over: the voice 9_2 (your pick: cleaner; 9_3 lisped on s/sh/ch) - the only ready voice now; every piece of a voice-over is kept at the voice's own pitch."),
    ("2026-10-20b", "Finish a video: a saved reel → “Text, captions, voice-over” - the voice, captions, look and texts on one page, with a preview."),
    ("2026-10-20", "Captions in four looks (the word being said in color like Reels, on a dark box, classic, calm), with a color and a size; Edit text and captions fixes a word and shows a preview picture before the video is made."),
]
WHATS_NEW_ID = max(d for d, _ in WHATS_NEW_ITEMS)
WHATS_NEW = [t for _, t in WHATS_NEW_ITEMS]


def whats_new_items() -> list[str]:
    try:
        seen = str((load_config().get("auto_edit") or {}).get("whats_new_seen") or "")
    except Exception:
        seen = ""
    # the newest first (the list grew in no order of dates; two weeks of changes once came oldest first)
    return [t for d, t in sorted(((d, t) for d, t in WHATS_NEW_ITEMS if d > seen), key=lambda x: x[0], reverse=True)]


def whats_new_seen() -> bool:
    try:
        ae_cfg = load_config().get("auto_edit") or {}
        if ae_cfg.get("whats_new_seen") == WHATS_NEW_ID:
            return True
        if not ae_cfg.get("whats_new_seen"):
            # a first install (no reel made yet): everything is new, a list of changes means nothing - not shown
            ensure_schema()
            with db() as con:
                if not con.execute("SELECT 1 FROM ae_projects LIMIT 1").fetchone():
                    mark_whats_new_seen()
                    return True
        return False
    except Exception:
        return True


def mark_whats_new_seen() -> None:
    try:
        from .config import update_config
        update_config(lambda cfg: cfg.setdefault("auto_edit", {}).__setitem__("whats_new_seen", WHATS_NEW_ID))
    except Exception:
        pass


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
        from .config import update_config

        try:
            first_use = not (load_config().get("auto_edit") or {}).get("selftest_ok_at") and not list_projects(include_archived=True)
        except Exception:
            first_use = False

        def change(cfg):
            a = cfg.setdefault("auto_edit", {})
            a["selftest_ok_at"] = now_iso()
            a["selftest_mode"] = str(res.get("selection_mode") or "")
            if first_use:                 # a new user: everything is new - no "New in this version" list
                a["whats_new_seen"] = WHATS_NEW_ID
        update_config(change)
    except Exception:
        pass


def selftest_video() -> Path | None:
    try:
        vids = sorted((DATA / "selftest").glob("out*/MediaEngine Reel.mp4"), key=lambda p: p.stat().st_mtime)
    except OSError:
        vids = []
    return vids[-1] if vids else None


SELFTEST_RUNNING = threading.Event()      # the Library's AI+ search preparation waits for it (one AI+ model at a time)


_SELFTEST = {"running": False, "mode": "", "started": 0.0, "result": None}
_SELFTEST_LOCK = threading.Lock()


def selftest_start(mode: str, timeout_s: int) -> bool:
    """The test reel of Check this PC in the background: the page can be closed or reloaded meanwhile."""
    import time as _t
    with _SELFTEST_LOCK:
        if _SELFTEST["running"]:
            return False
        _SELFTEST.update(running=True, mode=mode, started=_t.time(), result=None)

    def run():
        t0 = _t.time()
        try:
            t = quick_selftest(mode=mode, timeout_s=timeout_s)
        except Exception as exc:
            t = {"ok": False, "error": friendly_error(str(exc)), "seconds": round(_t.time() - t0, 1)}
        _remember_selftest(t)
        with _SELFTEST_LOCK:
            _SELFTEST.update(running=False, result=t)
    threading.Thread(target=run, daemon=True, name="selftest").start()
    return True


def selftest_state() -> dict:
    import time as _t
    with _SELFTEST_LOCK:
        st = dict(_SELFTEST)
    st["elapsed_s"] = round(_t.time() - st["started"], 1) if st["running"] else 0.0
    return st


def quick_selftest(timeout_s: int = 900, mode: str = "technical") -> dict:
    """Build a 5 s reel from two generated clips with the real engine. mode='semantic' runs the AI model
    (semantic=required, the same pinned check as a normal AI build). Never touches user media."""
    SELFTEST_RUNNING.set()
    try:
        return _quick_selftest(timeout_s, mode)
    finally:
        SELFTEST_RUNNING.clear()


def _quick_selftest(timeout_s: int, mode: str) -> dict:
    import time as _t
    ff = _ffmpeg() or "ffmpeg"
    root = DATA / "selftest"
    shutil.rmtree(root, ignore_errors=True)
    out_dir = root / "out"
    if out_dir.exists():                      # the last test reel still open in the page's player (Windows): a new folder
        out_dir = root / f"out-{int(_t.time())}"
    src = root / "in"; src.mkdir(parents=True, exist_ok=True)
    for i, lav in enumerate(("testsrc2=size=640x360:rate=30", "mandelbrot=size=640x360:rate=30"), 1):
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", lav, "-f", "lavfi", "-i", f"sine=frequency={300 + 100 * i}:sample_rate=48000",
                        "-t", "8", "-vf", f"hue=h=t*{20 * i}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(src / f"test_{i}.mp4")], **process_kwargs({"capture_output": True, "timeout": 120}))
    s = {"length": 5, "format": "vertical", "sound": "auto", "mode": mode if mode in AI_MODES else "technical"}
    cmd = engine_command(src, out_dir, root / "work", root / "progress.json", s)
    t0 = _t.time()
    # same handling as a build: on Windows a job object, so a time-out stops the engine AND every ffmpeg it started
    kw = process_kwargs() if os.name == "nt" else {"start_new_session": True}
    env = _engine_env()
    env.pop("MEDENG_P13_SCOUT_CACHE", None)     # the test reel measures the AI+ speed: always looks at its frames
    env.pop("MEDENG_AI_SHARED_CACHE", None)     # ... and the AI speed; its generated clips stay out of the shared cache
    proc = subprocess.Popen(cmd, env=env, cwd=str(ENGINE_DIR), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)
    _attach_job_object(proc)
    try:
        out, _ = proc.communicate(timeout=timeout_s)
        ok = proc.returncode == 0 and (out_dir / "MediaEngine Reel.mp4").is_file()
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
        r = json.loads((out_dir / "MediaEngine Result.json").read_text(encoding="utf-8"))
        res.update(video=str(out_dir / "MediaEngine Reel.mp4"), duration_s=r.get("actual_duration_s"), stages=r.get("stage_seconds"),
                   selection_mode=r.get("selection_mode"))
        # AI+ speed measured on this PC: seconds per frame the model looked at (model start not included)
        frames = secs = 0.0
        for p in (root / "work" / "semantic_scout_pe").glob("*.json"):
            try:
                inf = json.loads(p.read_text(encoding="utf-8"))["info"]
                frames += float(inf["scout_frame_count"]); secs += float(inf["embed_elapsed_s"])
            except Exception:
                pass
        if frames > 0:
            res["aiplus_s_per_frame"] = round(secs / frames, 3)
    return res


# ---------------------------------------------------------------- disk space

def _tree_bytes(root: Path, own_only: bool = False) -> int:
    """Bytes of the files under root. own_only: without files that have other names too (hard links: a build made
    by the Update button shares its runtime with the build it came from - removing one frees only what is its own)."""
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            try:
                st = (Path(dirpath) / f).stat()
                if own_only and st.st_nlink > 1:
                    continue
                total += st.st_size
            except OSError:
                pass
    return total


BUILD_MARKERS = ("BUILD.txt", "port.txt", "Start MediaEngine.vbs")


# What a release folder holds (tools/build_windows_package.py, the launcher, Windows itself). A folder with anything
# else in it - the owner's clips put there, a Library source, a reel's folder - is never offered for removal: removing
# a version deletes its folder for good (no Recycle Bin).
RELEASE_ENTRIES = {".venv", "app", "app.__new__", "app.__old__", "requirements.txt", "launcher.py", "version.txt", "port.txt", "runtime.txt",
                   "shortcut_name.txt", "start mediaengine.vbs", "mediaengine.ico", "build.txt", "readme.txt", "прочти.txt",
                   "updater_config.json", "__pycache__", "models", "sidecars", "desktop.ini", "thumbs.db"}


def _user_places() -> list[Path]:
    """Folders the owner's own files are in or go to: the Library's sources, the reels' folders and chosen videos,
    the folders reels were saved to."""
    out: list[Path] = []
    try:
        for s_ in load_config().get("sources") or []:
            if s_.get("path"):
                out.append(Path(os.path.expandvars(str(s_["path"]))).expanduser())
    except Exception:
        pass
    try:
        ensure_schema()
        with db() as con:
            for r in con.execute("SELECT folder, files_json FROM ae_projects").fetchall():
                if r["folder"]:
                    out.append(Path(r["folder"]))
                for f in json.loads(r["files_json"] or "null") or []:
                    out.append(Path(f).parent)
            for r in con.execute("SELECT DISTINCT path FROM ae_exports").fetchall():
                out.append(Path(r["path"]).parent)
    except Exception:
        pass
    return out


def _holds_user_data(d: Path) -> bool:
    """Early 3.13 candidates kept projects, database and exports INSIDE the release folder, and the data folder,
    the export folder, the archive, a Library source or a reel's videos may be inside one: such a folder is never
    offered for removal (nor anything that is not exactly a release folder)."""
    if any((d / n).exists() for n in ("data", "Exports", "MediaArchive", "Staging", "Private")):
        return True
    try:
        if any(x.name.lower() not in RELEASE_ENTRIES for x in d.iterdir()):
            return True                   # something of the owner's (or unknown) is in it
        rd = d.resolve()
        places = [HOME, DATA, EXPORTS, default_export_dir()]
        from .config import archive_root
        places.append(archive_root())
        places += _user_places()
        for x in places:
            try:
                rx = Path(x).resolve()
            except (OSError, ValueError):
                continue
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
            hit = _BUILD_BYTES[str(d)] = (mt, _tree_bytes(d, own_only=True))
        try:     # older launchers cannot be asked to take over from here (switching came in 2026-10-11)
            can_switch = "MEDIAENGINE_SWITCH_ANSWER" in (d / "launcher.py").read_text(encoding="utf-8", errors="replace")
        except OSError:
            can_switch = False
        out.append({"name": d.name, "path": str(d), "built": built, "bytes": hit[1], "mtime": mt, "can_switch": can_switch})
    # the newest first, by its build number (by name "b28" came after "b213")
    def newest(b):
        m = re.fullmatch(r"MediaEngine-(\d+(?:\.\d+)*)(?:-rc(\d+))?(?:-b(\d+))?", b["name"])
        if not m:
            return (0, (), 0, 0, 0, b["mtime"])
        ver = tuple(int(x) for x in m.group(1).split("."))
        rc = m.group(2)
        return (1, ver, 0 if rc else 1, int(rc or 0), int(m.group(3) or 0), b["mtime"])
    out.sort(key=newest, reverse=True)
    return out


_BUILD_NAME = re.compile(r"MediaEngine-(\d+(?:\.\d+)*-rc\d+)-b(\d+)")


def old_builds(keep: int = 2, install: Path | None = None) -> list[dict]:
    """The earlier builds of THIS release line (the same version and candidate, a smaller build number), all but the
    newest `keep` - what "Remove the older versions" takes. Never another release (a stable version such as 3.12.42
    is kept whatever happens), never a build newer than this one, never a folder with a name of another form."""
    from .config import INSTALL
    me = _BUILD_NAME.fullmatch(Path(install or INSTALL).resolve().name)
    if not me:
        return []
    same = []
    for b in other_builds(install):
        m = _BUILD_NAME.fullmatch(b["name"])
        if m and m.group(1) == me.group(1) and int(m.group(2)) < int(me.group(2)):
            same.append(b)
    return same[max(0, int(keep)):]               # (other_builds: the newest first)


def remove_old_builds(keep: int = 2, install: Path | None = None) -> tuple[int, int]:
    """old_builds(keep) removed; returns (removed, bytes freed). One that cannot be removed now (a file of it open)
    is left as it is."""
    n = freed = 0
    for b in old_builds(keep, install):
        try:
            freed += int(delete_build(b["name"], install) or 0)
            n += 1
        except Exception:
            pass
    return n, freed


_BUILD_BYTES: dict[str, tuple[float, int]] = {}


def app_busy() -> str:
    """What would make this MediaEngine refuse to quit now (the same rules as its Quit button), or ''."""
    with db() as con:
        if con.execute("SELECT id FROM ae_jobs WHERE status IN ('queued','running') LIMIT 1").fetchone():
            return "A reel is being made. Switch when it is ready."
        try:
            if con.execute("SELECT id FROM jobs WHERE status='running' LIMIT 1").fetchone():
                return "A Library task is running (see Activity). Switch when it has finished."
        except Exception:
            pass
    if aiplus_downloading():
        return "The AI+ model is being downloaded. Switch when it is done."
    try:
        from . import aiplus_library as _al
        if _al.running():
            return "AI+ is being prepared for the Library. Stop it first (it continues next time)."
    except Exception:
        pass
    try:
        from . import orders as _or
        if _or.busy():
            return "An order from another program is being done. Switch when it is ready."
    except Exception:
        pass
    try:
        from . import voice as _vo
        if _vo.busy():
            return ("The story writer is being downloaded (Cartoon Studio). Switch when it is ready."
                    if _vo._writer_installing() and not _vo.busy_kind() else
                    "Clips are being made. Switch when they are ready." if _vo.busy_kind() == "clips" else
                    "A cartoon is being made. Switch when it is ready." if _vo.busy_kind() == "cartoon" else
                    "A voice-over is being made (or the voice add-on installed). Switch when it is ready.")
    except Exception:
        pass
    try:
        from . import composer as _cp
        with _cp._ACTIVE_LOCK:
            if _cp._ACTIVE:
                return "A composition is being rendered (Composer). Switch when it is ready."
    except Exception:
        pass
    try:
        from . import updater as _up
        if _up.installing():
            return "An update is being installed. Wait a minute."
    except Exception:
        pass
    return ""


def use_build(name: str) -> str:
    """Go back (or forward) to another installed version: its launcher is started, asks this one to quit (same as its
    Quit button; refused while a reel is being made) and starts itself on the same port. Projects stay the same."""
    b = next((x for x in other_builds() if x["name"] == str(name or "")), None)
    if not b:
        raise ValueError("That version is not on this PC.")
    if os.name != "nt":
        raise ValueError("Only on Windows.")
    if not b.get("can_switch"):
        raise ValueError("That version is too old to switch to from here. Start it from its folder.")
    busy = app_busy()
    if busy:
        raise ValueError(busy)
    start_build_folder(Path(b["path"]))
    return b["path"]


def start_build_folder(folder: Path) -> None:
    """Start the launcher of another build folder so that it takes over from this one (it asks this one to quit, as
    its Quit button does, and starts itself on the same port). This page's window stays and follows it."""
    folder = Path(folder)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("ARCHIVIST_")}
    env.update(MEDIAENGINE_SWITCH_ANSWER="yes", MEDIAENGINE_NO_BROWSER="1")
    subprocess.Popen(["wscript.exe", str(folder / "Start MediaEngine.vbs")], cwd=str(folder), env=env, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     **process_kwargs(detached=True, below_normal=False))


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
    if install is None:       # a Start-menu / desktop shortcut may have pointed at the removed version: now at this one
        try:
            from .platform_adapter import install_launchers
            install_launchers(INSTALL)
        except Exception:
            pass
    return int(b["bytes"])


def delete_project(pid: int) -> int:
    """An archived project removed for good: its versions and cache (this PC's copies made by MediaEngine). Saved MP4
    files in the user's folders and the original videos are not touched. Returns the bytes freed."""
    p = project(pid)
    if not p:
        raise ValueError("Project not found")
    if not p["archived"]:
        raise ValueError("Archive the project first")
    with _CACHE_LOCK:
        if any(j["status"] in ("queued", "running") for j in (project(pid) or p)["jobs"]):
            raise ValueError("Wait until the current build has finished")
        d = _project_dir(pid)
        freed = _tree_bytes(d)
        gone = d.with_name(d.name + ".deleting")
        if d.exists():
            try:
                shutil.rmtree(gone, ignore_errors=True)
                os.rename(d, gone)        # fails while a version is open in a player: then nothing is half-deleted
            except OSError:
                raise ValueError("A video of this project is open (in a player?). Close it and try again.")
        try:
            with db() as con:
                con.execute("BEGIN IMMEDIATE")
                for t in ("ae_reviews", "ae_accept_log", "ae_exports", "ae_revisions", "ae_jobs"):
                    con.execute(f"DELETE FROM {t} WHERE project_id=?", (int(pid),))
                con.execute("DELETE FROM ae_projects WHERE id=?", (int(pid),))
                con.commit()
        except BaseException:
            try:                          # the project stays as it was: its files back in place
                if gone.exists() and not d.exists():
                    os.rename(gone, d)
            except OSError:
                pass
            raise
    shutil.rmtree(gone, ignore_errors=True)
    return freed


def project_disk_usage(pid: int) -> dict:
    d = _project_dir(pid)
    return {"cache_bytes": _tree_bytes(d / "work"), "versions_bytes": _tree_bytes(d / "revisions")}


SHARED = AE_ROOT / "shared"          # what AI+ saw in each video + its text numbers: used by every project


def shared_cache_bytes() -> int:
    return _tree_bytes(SHARED) if SHARED.exists() else 0


SHARED_CLIPS_MAX = 40 * 1024 ** 3      # moment clips kept for every project (previews: ~0.5 GB per 18 videos)
SHARED_CLIPS_DIRS = ("semantic_previews", "semantic_previews_pe")      # previews of the moments (since b114)
OBSOLETE_CLIP_DIRS = ("semantic_candidates", "semantic_candidates_pe")  # full-size moment clips of b101-b113: never read again


def forget_in_shared(hashes) -> None:
    """What the AI found in these videos leaves the shared cache: what AI+ saw, the AI's reports and the moment clips
    (also those of a stand-in - a camcorder remux - made from one of them: its report and clips name the real file)."""
    want = {str(x).lower() for x in hashes if x}
    if not want or not SHARED.is_dir():
        return
    d = SHARED / "semantic_scout_pe"
    for sha in want:
        for f in [d / (sha + ext) for ext in (".json", ".npy", ".key")] + [SHARED / "semantic_reports" / (sha + ".json")]:
            try:
                f.unlink(missing_ok=True)
            except OSError:
                pass
    rd = SHARED / "semantic_reports"
    for f in rd.glob("*.origin") if rd.is_dir() else []:      # reports of stand-ins name the real file beside them
        try:
            if f.read_text(encoding="utf-8").strip().lower() in want:
                f.with_suffix(".json").unlink(missing_ok=True); f.unlink()
        except OSError:
            pass
    for sub in SHARED_CLIPS_DIRS + OBSOLETE_CLIP_DIRS:
        dd = SHARED / sub
        for meta in dd.glob("*.json") if dd.is_dir() else []:
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                if {str(m.get("source_sha256") or "").lower(), str(m.get("origin_sha256") or "").lower()} & want:
                    meta.with_suffix(".mp4").unlink(missing_ok=True); meta.unlink(missing_ok=True)
            except (OSError, ValueError):
                pass


def tidy_shared_cache(private_hashes=(), max_clip_bytes=None, min_free_bytes=10 * 1024 ** 3, prune_clips=True) -> None:
    """Before a build: what the AI found in videos that are Private now goes (forget_in_shared), temp files of a
    stopped build go, and - prune_clips, only where no build can be using them (the build worker, before it starts the
    engine; never from the AI+ Library preparation, which runs beside a build) - the moment clips used longest ago go
    when there are more than SHARED_CLIPS_MAX of them (or the disk is nearly full): a later reel cuts them again."""
    if not SHARED.is_dir():
        return
    forget_in_shared(private_hashes)
    old = time.time() - 6 * 3600
    for sub in ("semantic_scout_pe", "semantic_reports", "v22_metrics", "camera_drop_rows", "signatures",
                "selection_cache") + SHARED_CLIPS_DIRS:
        dd = SHARED / sub
        if not dd.is_dir():
            continue
        for t in list(dd.glob("*.tmp.*")) + list(dd.glob("*.part")):
            try:
                if t.stat().st_mtime < old:
                    t.unlink()
            except OSError:
                pass
    if not prune_clips:
        return
    for sub in OBSOLETE_CLIP_DIRS:        # 4K clips the engine no longer reads (it keeps small previews): gigabytes back
        shutil.rmtree(SHARED / sub, ignore_errors=True)
    clips = []          # (last use, bytes, clip, meta)
    for sub in SHARED_CLIPS_DIRS:
        dd = SHARED / sub
        if not dd.is_dir():
            continue
        for clip in dd.glob("*.mp4"):         # a clip whose description was never written (a build stopped then)
            try:
                if not clip.with_suffix(".json").exists() and clip.stat().st_mtime < old:
                    clip.unlink()
            except OSError:
                pass
        for meta in dd.glob("*.json"):
            clip = meta.with_suffix(".mp4")
            try:
                clips.append((meta.stat().st_mtime, clip.stat().st_size if clip.is_file() else 0, clip, meta))
            except OSError:
                continue
    cap = SHARED_CLIPS_MAX if max_clip_bytes is None else int(max_clip_bytes)
    try:
        if shutil.disk_usage(SHARED).free < min_free_bytes:      # nearly full disk: keep at most half
            cap = min(cap, sum(c[1] for c in clips) // 2)
    except OSError:
        pass
    total = sum(c[1] for c in clips)
    for _, size, clip, meta in sorted(clips, key=lambda c: c[0]):
        if total <= cap:
            break
        try:
            clip.unlink(missing_ok=True); meta.unlink(missing_ok=True)
            total -= size
        except OSError:
            pass


WORK_CACHE_MAX = 60 * 1024 ** 3          # the full-quality pieces and finished segments of all projects together
# in: stand-ins the analysis made (copies from another drive); manual_trims: the moments cut again after Edit (cut
# again from the source when that reel is built again)
WORK_CACHE_DIRS = ("full_quality", "segment_cache_v2", "in", "manual_trims")


def tidy_work_caches(keep_pid: int | None = None, max_bytes: int | None = None, min_free_bytes: int = 10 * 1024 ** 3) -> int:
    """Before a build: the cut pieces of the OTHER projects (4K pieces: ~100 MB per moment) are kept to WORK_CACHE_MAX
    (less when the disk is nearly full), the oldest first - nothing grows without end. Never the project being built
    and never a project prepared in advance and not built yet (its pieces are what makes its reel quick). A removed
    piece is cut again if that project is built again. Returns the bytes freed."""
    keep = {int(keep_pid)} if keep_pid else set()
    try:
        # (a prepared project the owner archived is not kept: its pieces may go when space is needed)
        keep |= {int(x["id"]) for x in list_projects(include_archived=True)
                 if x["state"] == "PROCESSING" or (prepared_job(x) and not x.get("archived"))}
    except Exception:
        return 0
    files, freed_tmp = [], 0
    for pd in AE_ROOT.glob("p*"):
        if not pd.is_dir() or not pd.name[1:].isdigit() or int(pd.name[1:]) in keep:
            continue
        fin = pd / "work" / "final_v2"           # the last build's temporary files (a reel cut off half-way: a full
        if fin.is_dir():                         # reel's size left there, never used again)
            try:
                gone = sum(x.stat().st_size for x in fin.rglob("*") if x.is_file())
                shutil.rmtree(fin, ignore_errors=True)
                if not fin.exists():
                    freed_tmp += gone
            except OSError:
                pass
        for sub in WORK_CACHE_DIRS:
            for f in (pd / "work" / sub).glob("*.mp4" if sub != "in" else "v_*"):
                if f.suffix.lower() in (".sha256", ".part"):
                    continue
                try:
                    st = f.stat()
                    files.append((st.st_mtime, st.st_size, f))
                except OSError:
                    pass
    total = sum(x[1] for x in files)
    cap = WORK_CACHE_MAX if max_bytes is None else int(max_bytes)
    try:
        if shutil.disk_usage(AE_ROOT).free < min_free_bytes:
            cap = min(cap, total // 2)
    except OSError:
        pass
    freed = 0
    for _, size, f in sorted(files, key=lambda x: x[0]):
        if total - freed <= cap:
            break
        for side in (f, f.with_name(f.name + ".sha256"), f.with_suffix(".json")):
            try:
                side.unlink(missing_ok=True)
            except OSError:
                pass
        freed += size
    return freed + freed_tmp


# A Free (or a project deleted for good) and a build starting at that moment (an order, Retry in another tab): the
# check "nothing is building" and moving the folder aside are one step against start_job; the slow delete comes after.
_CACHE_LOCK = threading.RLock()


def _move_aside(path: Path) -> Path | None:
    """Renames the folder to "<name>.deleting-<n>" (instant) and returns the new path; None when there was nothing
    or it could not be renamed (then it is deleted right here, still under the lock)."""
    if not path.exists():
        return None
    gone = path.with_name(f"{path.name}.deleting-{time.time_ns()}")
    try:
        os.replace(path, gone)
        return gone
    except OSError:
        shutil.rmtree(path, ignore_errors=True)
        return None


def sweep_deleting() -> None:
    """Folders left half-deleted by a Free (or a project deleted for good) when the app was closed meanwhile (at
    start, before any build)."""
    for d in [*AE_ROOT.glob("shared.deleting-*"), *AE_ROOT.glob("p*/work.deleting-*")]:
        shutil.rmtree(d, ignore_errors=True)
    for d in AE_ROOT.glob("p*.deleting"):
        m = re.fullmatch(r"p(\d+)\.deleting", d.name)
        if not m or not d.is_dir():
            continue
        try:     # a project still in the list (its delete failed half-way): its folder goes back, never away
            with db() as con:
                kept = con.execute("SELECT 1 FROM ae_projects WHERE id=?", (int(m.group(1)),)).fetchone() is not None
        except Exception:
            continue
        if kept:
            home_ = d.with_name(f"p{m.group(1)}")
            if not home_.exists():
                try:
                    os.replace(d, home_)
                except OSError:
                    pass
        else:
            shutil.rmtree(d, ignore_errors=True)


def clear_shared_cache() -> int:
    """'Free' on Check this PC: the next AI+ build looks at the frames of its videos again."""
    with _CACHE_LOCK:
        with db() as con:
            try:
                busy = con.execute("SELECT 1 FROM ae_jobs WHERE status IN ('queued','running') LIMIT 1").fetchone()
            except Exception:
                busy = None
        if busy:
            raise ValueError("Wait until the current build has finished")
        try:
            from . import aiplus_library as _al
            if _al.running():
                raise ValueError("AI+ is being prepared for the Library: stop it on the Library page first")
        except ImportError:
            pass
        freed = shared_cache_bytes()
        gone = _move_aside(SHARED)
        for p in list_projects(include_archived=True):      # what was prepared in advance lived there too
            _forget_prepared(p)
    if gone is not None:
        shutil.rmtree(gone, ignore_errors=True)
    return freed


def clear_work_cache(pid: int) -> int:
    """Delete the project's analysis/render cache (versions and exports stay). The next build analyses again."""
    with _CACHE_LOCK:
        p = project(pid)
        if not p:
            raise ValueError("Project not found")
        if any(j["status"] in ("queued", "running") for j in p["jobs"]):
            raise ValueError("Wait until the current build has finished")
        work = _project_dir(pid) / "work"
        freed = _tree_bytes(work)
        gone = _move_aside(work)
        _forget_prepared(p)
    if gone is not None:
        shutil.rmtree(gone, ignore_errors=True)
    return freed


def _forget_prepared(p: dict) -> None:
    """"Prepared in advance" is not true any more (a cache was freed): the page stops saying so, and Prepare again
    really prepares (the old job is no longer "the same request")."""
    for j in p.get("jobs") or []:
        if j["status"] == "done" and is_prepare(j):
            (_project_dir(int(p["id"])) / "jobs" / f"j{int(j['id'])}" / "MediaEngine Prepared.json").unlink(missing_ok=True)
            with db() as con:
                con.execute("UPDATE ae_jobs SET request_key=request_key||':cleared' WHERE id=? AND request_key NOT LIKE '%:cleared'",
                            (int(j["id"]),))
                con.commit()


def all_work_cache_bytes() -> int:
    """Analysis and render caches of every project (versions and exports not counted)."""
    total = 0
    for p in list_projects(include_archived=True):       # the ones Free can free (not while building)
        if not any(j["status"] in ("queued", "running") for j in p["jobs"]):
            total += _tree_bytes(_project_dir(p["id"]) / "work")
    return total


def clear_all_work_caches() -> int:
    """Free the caches of every project that is not building now (versions and exports stay)."""
    freed = 0
    for p in list_projects(include_archived=True):
        if any(j["status"] in ("queued", "running") for j in p["jobs"]):
            continue
        try:
            freed += clear_work_cache(p["id"])
        except ValueError:
            pass
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
    if not _sql_int(review_id):
        return None
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


def last_new_settings() -> dict:
    """Format, sound and how moments are chosen of the last reel made: the next new reel starts with them."""
    try:
        d = dict(load_config().get("auto_edit", {}).get("last_new") or {})
    except Exception:
        return {}
    return {k: d[k] for k, ok in (("format", FORMATS), ("sound", SOUNDS), ("mode", MODES), ("framing", FRAMINGS), ("look", LOOKS))
            if d.get(k) in ok}


def music_folder() -> str | None:
    """Where the music window opens: the folder of the music chosen last time, else Windows' Music folder."""
    try:
        last = Path(str(load_config().get("auto_edit", {}).get("music_dir") or ""))
        if last.is_absolute() and last.is_dir():
            return str(last)
    except Exception:
        pass
    m = _known_music_folder()             # (OneDrive may have moved it: Windows says where it is now)
    return str(m) if m and m.is_dir() else None


def _known_music_folder() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import ctypes, uuid
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
        u = uuid.UUID("{4BD8D571-6D19-48D3-BE97-422220080E43}")            # FOLDERID_Music
        g = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:]))
        out = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) != 0:
            return None
        try:
            return Path(out.value) if out.value else None
        finally:
            ctypes.windll.ole32.CoTaskMemFree(out)
    except Exception:
        return None


def remember_music(path) -> None:
    try:
        d = Path(str(path)).parent
        if d.is_dir():
            from .config import update_config
            update_config(lambda cfg: cfg.setdefault("auto_edit", {}).__setitem__("music_dir", str(d)))
    except Exception:
        pass


def remember_new_settings(settings: dict) -> None:
    try:
        from .config import update_config
        update_config(lambda cfg: cfg.setdefault("auto_edit", {}).__setitem__(
            "last_new", {k: settings.get(k) for k in ("format", "sound", "mode", "framing", "look") if settings.get(k)}))
    except Exception:
        pass


def default_export_dir() -> Path:
    """The folder the user exported to last time (if it still exists), otherwise <data>/Exports."""
    try:
        d = Path(str(load_config().get("auto_edit", {}).get("export_dir") or ""))
        if d.is_absolute() and d.is_dir():
            return d
    except Exception:
        pass
    return EXPORTS


def export_dir_for(p: dict) -> Path:
    """Where Save MP4 of this project goes: the folder used last - unless that is this reel's own source folder
    (the reel would become an input of its next build), then MediaEngine Data\\Exports."""
    d = default_export_dir()
    try:
        return check_export_dir(p, d) if d.is_dir() else d
    except ValueError:
        return Path(EXPORTS)


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
            from .config import update_config
            update_config(lambda cfg: cfg.setdefault("auto_edit", {}).__setitem__("export_dir", str(dest_dir)))
    if not p["accepted_revision_id"]:
        raise ValueError("Accept a revision before exporting")
    r = revision(p["accepted_revision_id"])
    _refuse_private(r)
    src = Path(r["video_path"])
    if sha256_file(src) != r["video_sha256"]:
        raise ValueError("Accepted revision changed on disk; export refused")
    if not dest_dir:
        dest_dir = export_dir_for(p)   # (the remembered folder may be this reel's own source folder: then the usual one)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fmt = format_file_word(r["settings"]["format"])
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
        _replace_retry(tmp, dst)   # replaces only our own empty reservation (a virus scanner may still hold the new file)
    except BaseException:
        tmp.unlink(missing_ok=True)
        dst.unlink(missing_ok=True)
        raise
    return _record_export(pid, r, dst, reused=False)


SMALL_LONG_SIDE = 1280        # a copy for messengers: 720p, about a tenth of the size


def small_copy(pid: int, rid: int) -> Path:
    """A small copy of a version for messengers (WhatsApp, Telegram): long side at most 1280 px, lower bit rate, in the
    export folder next to the saved reels. Made from the finished version in one quick encode (no new build).
    One at a time per project; an existing file is never replaced (another project may have the same title)."""
    with _EXPORT_LOCKS_GUARD:
        lock = _EXPORT_LOCKS.setdefault(int(pid), threading.Lock())
    with lock:
        return _small_copy(pid, rid)


def _small_copy(pid: int, rid: int) -> Path:
    p, r = project(pid), revision(rid)
    if not p or not r or int(r["project_id"]) != int(pid):
        raise ValueError("Revision not found in this project")
    _refuse_private(r)
    src = Path(r["video_path"])
    if sha256_file(src) != r["video_sha256"]:
        raise ValueError("The file of this version changed on disk; build the version again")
    dest_dir = Path(export_dir_for(p))
    dest_dir.mkdir(parents=True, exist_ok=True)
    fmt = format_file_word(r["settings"]["format"])
    base = safe_filename(f"{p['title']} - {fmt} - R{int(r['number']):03d} " + ("маленькая копия" if _ui_ru() else "small"))
    made = AE_ROOT / "small_copies.json"         # which version each small copy was made from (nothing extra in the folder)
    with _SMALL_LOCK:
        try:
            known = json.loads(made.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            known = {}
    n = 1
    while True:                       # the name is reserved first: an existing file (another project's) is never replaced
        dst = dest_dir / (base + (f" ({n})" if n > 1 else "") + ".mp4")
        if dst.is_file() and known.get(str(dst)) == r["video_sha256"]:
            return dst                 # made before from this very version
        try:
            with open(dst, "xb"):
                pass
            break
        except FileExistsError:
            n += 1
    L = SMALL_LONG_SIDE
    tmp = dest_dir / f".{dst.stem}.{os.getpid()}.{threading.get_ident()}.part.mp4"
    cmd = [_ffmpeg() or "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", f"scale='if(gte(iw,ih),min(iw,{L}),-2)':'if(gte(iw,ih),-2,min(ih,{L}))'",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)]
    try:
        cp = subprocess.run(cmd, **process_kwargs({"capture_output": True, "text": True, "encoding": "utf-8",
                                                   "errors": "replace", "timeout": 1800}))
        if cp.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 1000:
            raise RuntimeError("SMALL_COPY_FAILED: " + (cp.stderr or "")[-300:])
        _replace_retry(tmp, dst)      # replaces only our own empty reservation
    except BaseException:
        tmp.unlink(missing_ok=True)
        dst.unlink(missing_ok=True)
        raise
    with _SMALL_LOCK:
        try:
            try:
                known = json.loads(made.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                known = {}
            known[str(dst)] = r["video_sha256"]
            made.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass
    return dst


_SMALL_LOCK = threading.Lock()


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
    if not _sql_int(eid):
        return None
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
        for v, nm in input_names([Path(f) for f in p["files"]]):     # the reel's name for it (DJI_0001 (2).MP4)
            if nm == name and str(v.resolve()) in allowed and v.is_file():
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
          "Choose the folder with the AI+ model files": "Выбери папку с файлами модели ИИ+",
          "Choose music for the reel": "Выбери музыку для ролика",
          "Choose the recording of the voice": "Выбери запись голоса", "Choose a video": "Выбери видео",
          "Choose the videos (Ctrl+click for several)": "Выбери видео (Ctrl+щелчок — несколько)",
          "Choose videos to convert (Ctrl+click for several)": "Выбери видео для конвертации (Ctrl+щелчок — несколько)",
          "Choose a folder for converted videos": "Выбери папку для сжатых видео",
          "Choose your logo (a PNG with a transparent background looks best)": "Выбери свой логотип (лучше всего PNG с прозрачным фоном)",
          "Choose the music": "Выбери музыку"}
    try:
        return ru.get(en, en) if ui_language() == "ru" else en
    except Exception:
        return en


def pick_files(title="Choose videos for one reel", initial: str | None = None, kind: str = "video") -> list[str] | None:
    """Native Windows Open dialog (GetOpenFileNameW): videos with multi-select, or one music file (kind='audio').
    initial = the folder it opens in."""
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
        exts, what = ((MUSIC_EXT, ("Музыка" if ru else "Music")) if kind == "audio" else
                      ({".png", ".jpg", ".jpeg", ".webp", ".bmp"}, ("Картинки" if ru else "Pictures")) if kind == "image" else
                      (SUPPORTED, ("Видео" if ru else "Videos")))
        flt = what + "\0" + ";".join("*" + x for x in sorted(exts)) + "\0" + ("Все файлы" if ru else "All files") + "\0*.*\0\0"
        ofn = OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
        ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
        ofn.lpstrFilter = flt
        ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
        ofn.nMaxFile = size
        ofn.lpstrTitle = _dialog_title(title)
        if initial and Path(initial).is_dir():
            ofn.lpstrInitialDir = str(initial)
        # OFN_ALLOWMULTISELECT (videos only) | OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR
        ofn.Flags = (0x200 if kind == "video" else 0) | 0x80000 | 0x1000 | 0x800 | 0x8
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
