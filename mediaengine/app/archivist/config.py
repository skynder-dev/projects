from __future__ import annotations
from .platform_adapter import default_archive_root

import json
import os
import threading
import time
from pathlib import Path

_SAVE_LOCK = threading.Lock()

APP_DIR = Path(__file__).resolve().parents[1]
INSTALL = APP_DIR.parent.resolve()      # program files: app/, .venv/, launcher.py, version.txt, port.txt
# A side-by-side release (it ships port.txt next to app/) is one folder per build; the user's data lives outside it.
SIDE_BY_SIDE = (INSTALL / "port.txt").exists()


def _pointer_file() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "MediaEngine" / "data_root.txt"


DATA_ROOT_NOTE: dict = {}      # {missing, using}: the remembered data folder is not there right now


def data_root_for(install: Path) -> Path:
    """Where a side-by-side release keeps projects, database, caches and exports.

    Every release is a new folder (never extracted over the old one), so data must not live inside it.
    First start: "<folder that holds the release>\\MediaEngine Data", remembered in %LOCALAPPDATA%\\MediaEngine\\data_root.txt,
    so a later release extracted anywhere finds the same projects. MEDIAENGINE_DATA overrides (tests).
    The launcher (launcher_v2.py) repeats this logic because it must work even when app/ is broken."""
    env = os.environ.get("MEDIAENGINE_DATA")
    if env:
        return Path(env).resolve()
    ptr = _pointer_file()
    try:
        remembered = Path(ptr.read_text(encoding="utf-8-sig").strip())
        if remembered.is_absolute() and remembered.is_dir():
            return remembered.resolve()
        if remembered.is_absolute():
            # remembered drive not connected right now: use the default without forgetting the old place - and SAY
            # so on every page (projects are not lost, they are on the other disk)
            fallback = (Path(install).resolve().parent / "MediaEngine Data").resolve()
            DATA_ROOT_NOTE.update(missing=str(remembered), using=str(fallback))
            return fallback
    except Exception:
        pass
    root = (Path(install).resolve().parent / "MediaEngine Data").resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        # the release sits somewhere read-only (e.g. Program Files): keep the data in the user's profile
        root = (ptr.parent / "Data").resolve()
        root.mkdir(parents=True, exist_ok=True)
    try:
        ptr.parent.mkdir(parents=True, exist_ok=True)
        ptr.write_text(str(root), encoding="utf-8")
    except Exception:
        pass
    return root


def _home() -> Path:
    if SIDE_BY_SIDE:
        # never another install's data, whatever ARCHIVIST_HOME says (for example the stable D:\\Archivist)
        return data_root_for(INSTALL)
    env = os.environ.get("ARCHIVIST_HOME")
    return Path(env).resolve() if env else INSTALL


HOME = _home()     # user data root (equals INSTALL for the stable single-folder install)
DATA = HOME / "data"
DB_PATH = DATA / "archivist.db"
CACHE = DATA / "cache"
THUMBS = CACHE / "thumbnails"
STORYBOARDS = CACHE / "storyboards"
TEMP = DATA / "temp"
STAGING = HOME / "Staging"
PRIVATE = HOME / "Private"
REJECTED = HOME / "Rejected"
LOGS = DATA / "logs"
CONFIG_PATH = HOME / "config.json"


def _app_port() -> int:
    """Local UI port. 8765 for the stable install; a side-by-side candidate ships port.txt (e.g. 8775).

    Fails closed: a present but unreadable port.txt stops the app instead of silently taking the stable
    install's port 8765 (which would mix the two installs)."""
    raw = os.environ.get("ARCHIVIST_PORT")
    if not raw and SIDE_BY_SIDE:
        raw = (INSTALL / "port.txt").read_text(encoding="utf-8-sig").strip()
        if not raw.isdigit() or not 1024 <= int(raw) <= 65535:
            raise SystemExit(f"Invalid port.txt in {INSTALL}: {raw[:20]!r}")
    if not raw:
        return 8765
    try:
        port = int(raw)
    except Exception:
        return 8765
    return port if 1024 <= port <= 65535 else 8765


APP_PORT = _app_port()
VERSION = "3.13.0-rc1"
# Build number of this release folder ("MediaEngine-3.13.0-rc1-b21" -> "b21"); every CI build of one version is its
# own folder, so the build is what tells two of them apart. Empty when run from source.
_bm = __import__("re").search(r"-b(\d+)$", INSTALL.name)
BUILD = f"b{_bm.group(1)}" if _bm else ""


def _default_archive_root() -> str:
    # A side-by-side install (it ships port.txt) keeps its own archive so it never mixes with the stable one.
    if SIDE_BY_SIDE:
        return str(HOME / "MediaArchive")
    return default_archive_root()

DEFAULT_CONFIG = {
    "config_version": 3,
    "installation": {"profile_version": 1, "product_mode": "desktop_local_first"},
    "connections": {"cloud_vault": {"enabled": False}, "social": {"enabled": False, "providers": {"youtube": {"client_id": ""}}}, "online_ai": {"enabled": False}},
    "archive_root": _default_archive_root(),
    "sources": [],
    "auto_removable": True,
    "android": {"enabled": True},
    "filters": {
        "ignore_noise": True,
        "min_image_bytes": 120 * 1024,
        "min_video_bytes": 256 * 1024,
    },
    "privacy": {
        "enabled": True,
        "review_threshold": 0.42,
        "video_samples": 10,
    },
    "ingest": {
        "min_free_gb": 10,
        "keep_failed_partials": False,
        "analyze_after_import": True,
        "keep_rejected": True,
    },
    "analysis": {
        "technical_quality": True,
        "quality_review_below": 55,
        "ffmpeg_threads": 2,
        "storyboard_frames": 8,
    },
}


def ensure_dirs() -> None:
    for p in (HOME, DATA, CACHE, THUMBS, STORYBOARDS, TEMP, STAGING, PRIVATE, REJECTED, LOGS):
        p.mkdir(parents=True, exist_ok=True)


def _deep_defaults(dst: dict, src: dict) -> dict:
    for key, value in src.items():
        if key not in dst:
            dst[key] = value
        elif isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_defaults(dst[key], value)
    return dst


def load_config() -> dict:
    ensure_dirs()
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg = _deep_defaults(cfg, json.loads(json.dumps(DEFAULT_CONFIG)))
    if cfg.get("config_version", 1) < 3:
        cfg["config_version"] = 3
    return cfg


def save_config(cfg: dict) -> None:
    ensure_dirs()
    cfg = _deep_defaults(cfg, json.loads(json.dumps(DEFAULT_CONFIG)))
    cfg["config_version"] = 3
    # one writer at a time, each with its own temporary file (a reel being created and the PC check finishing at
    # the same moment wrote the same .tmp)
    with _SAVE_LOCK:
        tmp = CONFIG_PATH.with_name(f"{CONFIG_PATH.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:      # on disk before it replaces the old one (a power cut left 0 bytes)
                fh.write(json.dumps(cfg, indent=2, ensure_ascii=False))
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except OSError:
                    pass
            for k in range(8):                          # a virus scanner may hold config.json for a moment
                try:
                    tmp.replace(CONFIG_PATH)
                    break
                except PermissionError:
                    if k == 7:
                        raise
                    time.sleep(0.2 * (k + 1))
        finally:
            tmp.unlink(missing_ok=True)
