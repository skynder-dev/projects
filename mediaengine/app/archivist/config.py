from __future__ import annotations
from .platform_adapter import default_archive_root

import json
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


def _home() -> Path:
    pkg = APP_DIR.parent.resolve()
    env = os.environ.get("ARCHIVIST_HOME")
    # A side-by-side package (it ships port.txt next to app/) always runs on its own folder: a stray
    # ARCHIVIST_HOME (for example pointing at the stable D:\\Archivist) must never make it use another install's data.
    if (pkg / "port.txt").exists():
        return pkg
    return Path(env).resolve() if env else pkg


HOME = _home()
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
    if not raw and (HOME / "port.txt").exists():
        raw = (HOME / "port.txt").read_text(encoding="utf-8-sig").strip()
        if not raw.isdigit() or not 1024 <= int(raw) <= 65535:
            raise SystemExit(f"Invalid port.txt in {HOME}: {raw[:20]!r}")
    if not raw:
        return 8765
    try:
        port = int(raw)
    except Exception:
        return 8765
    return port if 1024 <= port <= 65535 else 8765


APP_PORT = _app_port()
VERSION = "3.13.0-rc1"


def _default_archive_root() -> str:
    # A side-by-side install (it ships port.txt) keeps its own archive so it never mixes with the stable one.
    if (HOME / "port.txt").exists():
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
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONFIG_PATH)
