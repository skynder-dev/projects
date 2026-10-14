"""Automatic copies of the database and the settings (MediaEngine Data\\data\\backups): once a day and before a
different build first uses the data (an older build after a newer one, or the other way round). Kept: the last 7 daily
copies and the last 5 build copies (2 and 2 when the database is over 300 MB). A quick integrity check runs in the background; a problem is shown on every page.
"""
from __future__ import annotations

import shutil, sqlite3, threading, time
from datetime import datetime
from pathlib import Path

from .config import CONFIG_PATH, DATA, DB_PATH

BACKUPS = DATA / "backups"
DB_PROBLEM: dict = {}
_LOCK = threading.Lock()


def _copy_db(dst: Path) -> None:
    src = sqlite3.connect(str(DB_PATH), timeout=30)
    try:
        out = sqlite3.connect(str(dst))
        try:
            src.backup(out)          # consistent copy while the app may be writing
        finally:
            out.close()
    finally:
        src.close()


def _prune(prefix: str, keep: int) -> None:
    files = sorted(BACKUPS.glob(prefix + "*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    try:     # a big database (AI+ for a large Library: ~200 KB per video) keeps fewer copies
        if files and files[0].stat().st_size > 300 * 1024 * 1024:
            keep = min(keep, 2)
    except OSError:
        pass
    for old in files[keep:]:
        for x in (old, old.with_suffix(".config.json")):
            try:
                x.unlink()
            except OSError:
                pass


def _make(prefix: str, label: str) -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    need = DB_PATH.stat().st_size * 2 + 1024 ** 3
    if shutil.disk_usage(BACKUPS).free < need:          # never fill the disk with a copy
        raise OSError("not enough free disk space for a copy of the database")
    dst = BACKUPS / f"{prefix}{datetime.now().strftime('%Y%m%d-%H%M%S')}{('-' + label) if label else ''}.db"
    tmp = dst.with_suffix(".part")
    try:
        _copy_db(tmp)
        for k in range(8):         # a virus scanner may hold the new file for a moment
            try:
                tmp.replace(dst)
                break
            except PermissionError:
                if k == 7:
                    raise
                time.sleep(0.25 * (k + 1))
    except BaseException:
        tmp.unlink(missing_ok=True)   # never a half copy left behind (a full disk would get fuller at every start)
        raise
    if CONFIG_PATH.is_file():
        try:
            shutil.copyfile(CONFIG_PATH, dst.with_suffix(".config.json"))
        except OSError:
            pass
    return dst


def _clean_parts() -> None:
    for x in BACKUPS.glob("*.part") if BACKUPS.is_dir() else []:
        try:
            x.unlink()
        except OSError:
            pass


def before_new_build(build: str) -> dict:
    """Called at start, before the app opens the database: a copy when a different build used the data last."""
    out = {}
    try:
        if not DB_PATH.is_file():
            return out
        with _LOCK:
            _clean_parts()
            last_build_f = DATA / "last_build.txt"
            try:
                last_build = last_build_f.read_text(encoding="utf-8").strip()
            except OSError:
                last_build = ""
            if build and last_build and last_build != build:
                out["build"] = str(_make("build-", f"before-{build}"))
                _prune("build-", 5)
            if build and last_build != build:
                try:
                    last_build_f.write_text(build, encoding="utf-8")
                except OSError:
                    pass
    except Exception as exc:
        out["error"] = str(exc)[:200]
    return out


def daily_check() -> dict:
    """Integrity check and the daily copy (the app is already running: never in the way of the start)."""
    out = {}
    try:
        if not DB_PATH.is_file():
            return out
        try:
            con = sqlite3.connect(str(DB_PATH), timeout=30)
            try:
                ok = con.execute("PRAGMA quick_check").fetchone()[0]
            finally:
                con.close()
        except sqlite3.DatabaseError as exc:       # "file is not a database", "malformed"
            ok = str(exc)
        if str(ok).lower() != "ok":
            DB_PROBLEM.update(check=str(ok)[:200], backups=str(BACKUPS))
            return out                              # never replace the good copies with a damaged one
        with _LOCK:
            daily = sorted(BACKUPS.glob("daily-*.db"), key=lambda p: p.stat().st_mtime) if BACKUPS.is_dir() else []
            if not daily or time.time() - daily[-1].stat().st_mtime > 20 * 3600:
                out["daily"] = str(_make("daily-", ""))
                _prune("daily-", 7)
    except Exception as exc:
        out["error"] = str(exc)[:200]
    return out


def at_start(build: str) -> dict:
    """Both steps one after another (tests)."""
    return {**before_new_build(build), **daily_check()}


def start_daily_in_background(delay_s: float = 20.0) -> None:
    def run():
        time.sleep(delay_s)
        daily_check()
    threading.Thread(target=run, daemon=True, name="db-backup").start()
