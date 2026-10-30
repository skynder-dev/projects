"""The Inbox: links, topics and video files to work on - sent from the owner's phone (the Telegram bot,
telegram_bot.py), handed over by another program (an order of kind "idea", ORDERS.md) or typed on the Inbox page.
MediaEngine itself looks for nothing: the Inbox only keeps what was sent, until the owner works on it (downloads,
studies, writes a story) or removes it. One file per item: <data folder>/inbox/<id>.json.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

KINDS = ("link", "topic", "file", "idea")
MAX_LINKS = 30
MAX_ITEMS = 2000
_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
_LOCK = threading.Lock()


class InboxError(ValueError):
    pass


def root() -> Path:
    from .config import HOME
    return HOME / "inbox"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _clean(text, limit: int) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", str(text or "")).strip()[:limit]


def _write(item: dict) -> None:
    d = root()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{item['id']}.json"
    tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(item, ensure_ascii=False, indent=1), "utf-8")
    for i in range(20):                    # Windows: a page reading the file (or a virus check) holds it a moment
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (i + 1))


def links_in(text: str) -> list[str]:
    """The web addresses in a text (as they are, without a trailing dot or bracket)."""
    out = []
    for m in re.findall(r"https?://[^\s<>\"'«»]+", str(text or "")):
        m = m.rstrip(".,;:!?)]}")
        if m not in out:
            out.append(m)
    return out


def add(kind: str, *, links=(), text: str = "", title: str = "", why: str = "", file: str = "", source: str = "page",
        lang: str = "", order_id: str = "") -> str:
    """A new item; returns its id. links: web addresses (https), checked like Download by a link checks them."""
    from . import downloader as D
    if kind not in KINDS:
        raise InboxError("Unknown kind of item.")
    good = []
    for u in list(links or [])[:MAX_LINKS]:
        try:
            good.append(D.check_url(u))
        except D.DownloadError:
            continue
    text, title, why = _clean(text, 2000), _clean(title, 120), _clean(why, 1000)
    if kind in ("link",) and not good:
        raise InboxError("Paste a link that starts with https://")
    if kind == "topic" and not text:
        raise InboxError("Write a topic or paste a link.")
    if kind == "idea" and not (good or text or title):
        raise InboxError("An idea needs a topic or at least one link.")
    if kind == "file" and not file:
        raise InboxError("No file.")
    with _LOCK:
        iid = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        _write({"id": iid, "kind": kind, "links": good, "text": text, "title": title, "why": why, "file": str(file or ""),
                "source": _clean(source, 60) or "page", "lang": lang if lang in ("en", "ru", "ro") else "",
                "order_id": _clean(order_id, 80), "state": "new", "created_at": _now(), "created_ns": time.time_ns(),
                "jobs": [], "notified": []})
    return iid


def get(iid: str) -> dict:
    if not _ID.fullmatch(str(iid or "")):
        return {}
    try:
        d = json.loads((root() / f"{iid}.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) and d.get("id") == iid else {}


def items(limit: int = 300) -> list[dict]:
    """The items, newest first."""
    try:
        names = sorted((p.stem for p in root().glob("*.json")), reverse=True)[:MAX_ITEMS]
    except OSError:
        return []
    out = [x for x in (get(n) for n in names) if x]
    out.sort(key=lambda x: (int(x.get("created_ns") or 0), x["id"]), reverse=True)
    return out[:limit]


def count_new() -> int:
    return sum(1 for x in items(MAX_ITEMS) if x.get("state") == "new")


def _change(iid: str, fn) -> dict:
    with _LOCK:
        it = get(iid)
        if not it:
            raise InboxError("This item is not there any more.")
        fn(it)
        _write(it)
        return it


def set_state(iid: str, state: str) -> dict:
    if state not in ("new", "done"):
        raise InboxError("Unknown state.")
    return _change(iid, lambda it: it.__setitem__("state", state))


def attach_job(iid: str, job_id: str) -> None:
    """A download started from this item (the phone is told when it is finished)."""
    def fn(it):
        if job_id not in it.setdefault("jobs", []):
            it["jobs"].append(job_id)
    _change(iid, fn)


def mark_notified(iid: str, job_id: str) -> None:
    def fn(it):
        if job_id not in it.setdefault("notified", []):
            it["notified"].append(job_id)
    _change(iid, fn)


def delete(iid: str) -> None:
    """The item forgotten (a file it brought stays in its folder)."""
    if _ID.fullmatch(str(iid or "")):
        with _LOCK:
            (root() / f"{iid}.json").unlink(missing_ok=True)
