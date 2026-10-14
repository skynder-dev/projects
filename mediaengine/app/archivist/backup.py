"""Automatic copies of the database and the settings (MediaEngine Data\\data\\backups): once a day and before a
different build first uses the data (an older build after a newer one, or the other way round). Kept: the last 7 daily
copies and the last 5 build copies. A quick integrity check at start; a problem is shown on every page.
"""
from __future__ import annotations

import shutil, sqlite3, time
from datetime import datetime
from pathlib import Path

from .config import CONFIG_PATH, DATA, DB_PATH

BACKUPS = DATA / "backups"
DB_PROBLEM: dict = {}


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
    for old in files[keep:]:
        for x in (old, old.with_suffix(".config.json")):
            try:
                x.unlink()
            except OSError:
                pass


def _make(prefix: str, label: str) -> Path | None:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    dst = BACKUPS / f"{prefix}{datetime.now().strftime('%Y%m%d-%H%M%S')}{('-' + label) if label else ''}.db"
    tmp = dst.with_suffix(".part")
    _copy_db(tmp)
    tmp.replace(dst)
    if CONFIG_PATH.is_file():
        try:
            shutil.copyfile(CONFIG_PATH, dst.with_suffix(".config.json"))
        except OSError:
            pass
    return dst


def at_start(build: str) -> dict:
    """Called once when the app starts. Never fails the start."""
    out = {}
    try:
        if not DB_PATH.is_file():
            return out
        con = sqlite3.connect(str(DB_PATH), timeout=30)
        try:
            ok = con.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            con.close()
        if str(ok).lower() != "ok":
            DB_PROBLEM.update(check=str(ok)[:200], backups=str(BACKUPS))
        last_build_f = DATA / "last_build.txt"
        try:
            last_build = last_build_f.read_text(encoding="utf-8").strip()
        except OSError:
            last_build = ""
        if build and last_build and last_build != build and not DB_PROBLEM:
            out["build"] = str(_make("build-", f"before-{build}"))
            _prune("build-", 5)
        daily = sorted(BACKUPS.glob("daily-*.db"), key=lambda p: p.stat().st_mtime) if BACKUPS.is_dir() else []
        if not DB_PROBLEM and (not daily or time.time() - daily[-1].stat().st_mtime > 20 * 3600):
            out["daily"] = str(_make("daily-", ""))
            _prune("daily-", 7)
        if build:
            try:
                last_build_f.write_text(build, encoding="utf-8")
            except OSError:
                pass
    except Exception as exc:
        out["error"] = str(exc)[:200]
    return out
