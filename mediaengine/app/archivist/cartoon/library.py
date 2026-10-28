"""The cartoon characters' library: every character a film has used, kept by its name - its look (drawn the same in
every episode) and its voice (a description, said the same way: the voice made from it is kept too). Changed on the
Characters page; any later film whose story names the character gets that look and voice.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

LOOK = ("female", "build", "height", "skin", "hair", "hair_style", "face", "beard", "glasses", "outfit", "cloth", "tie",
        "pants", "shoes", "hat")
_LOCK = threading.Lock()
_CACHE: dict = {"mtime": None, "data": {}}


def path() -> Path:
    from ..config import HOME
    return HOME / "cartoon" / "characters.json"


def key_of(name: str) -> str:
    """The library's key of a name (the same name in any case, Latin or Cyrillic letters: the same key)."""
    from .textscript import _key
    return _key(re.sub(r"\s+", " ", str(name or "").strip()), {})


def load() -> dict:
    p = path()
    try:
        m = p.stat().st_mtime_ns
    except OSError:
        return {}
    if _CACHE["mtime"] != m:
        try:
            data = json.loads(p.read_text("utf-8"))
            _CACHE.update(mtime=m, data=data if isinstance(data, dict) else {})
        except OSError:                    # (held a moment by a virus check or a sync: the last read, not "empty")
            return _CACHE["data"]
        except ValueError:
            _CACHE.update(mtime=m, data={})
    return _CACHE["data"]


def _fresh() -> dict:
    """The library read now, for a change (OSError when the file is there but cannot be read: never saved over)."""
    p = path()
    for i in range(10):
        if not p.exists():
            return {}
        try:
            data = json.loads(p.read_text("utf-8"))
            return dict(data) if isinstance(data, dict) else {}
        except ValueError:
            return {}
        except OSError:
            if i == 9:
                raise
            time.sleep(0.05 * (i + 1))
    return {}


def _save(data: dict) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    for i in range(20):                    # Windows: a page reading the file (or a virus check) holds it a moment
        try:
            os.replace(tmp, p)
            break
        except PermissionError:
            if i == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (i + 1))
    _CACHE["mtime"] = None


def entry(name: str) -> dict | None:
    e = load().get(key_of(name))
    return e if isinstance(e, dict) else None


def look_of(name: str) -> dict:
    """The look kept for a name ({} when the library does not know it)."""
    e = entry(name) or {}
    return {k: v for k, v in (e.get("look") or {}).items() if k in LOOK}


def voice_of(name: str) -> str:
    return str((entry(name) or {}).get("voice") or "")


def remember(cast: dict, narrator: str = "", lang: str = "") -> None:
    """The characters of a film made: new names kept with the look they had; known ones counted."""
    with _LOCK:
        data = _fresh()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for k, c in (cast or {}).items():
            name = str(c.get("name") or k).strip()
            if not name:
                continue
            key = key_of(name)
            e = data.get(key)
            if e is None:
                v = c.get("voice") or {}
                e = {"name": name[:40], "role": str(c.get("role") or "")[:60], "look": {x: c[x] for x in LOOK if x in c},
                     "voice": str(v.get("text") or "") if v.get("kind") == "describe" else "",
                     "narrator": k == narrator, "films": 0, "added": now}
            e = dict(e, films=int(e.get("films") or 0) + 1, last=now)
            if k == narrator:
                e["narrator"] = True
            if lang and lang not in (e.get("langs") or []):
                e["langs"] = (e.get("langs") or []) + [lang]
            data[key] = e
        _save(data)


def add(name: str, role: str = "", female: bool | None = None) -> str:
    """A character made before any film (its look drawn from its name, changed on its page); its key. An existing
    name: that character's key."""
    from . import chars as ch
    name = re.sub(r"\s+", " ", str(name or "")).strip()[:40]
    if len(name) < 2:
        raise ValueError("Write the character's name.")
    key = key_of(name)
    with _LOCK:
        data = _fresh()
        if key not in data:
            over = {} if female is None else {"female": bool(female)}
            c = ch.make(name, str(role or "")[:60], **over)
            data[key] = {"name": name, "role": str(role or "")[:60], "look": {x: c[x] for x in LOOK if x in c}, "voice": "",
                         "narrator": False, "films": 0, "added": time.strftime("%Y-%m-%dT%H:%M:%S")}
            _save(data)
    return key


def set_host(key: str, on: bool) -> None:
    """The host of the owner's films: the story writer gives every new story this narrator (one host at a time)."""
    with _LOCK:
        data = _fresh()
        if key not in data:
            raise KeyError(key)
        if on:                             # (one host: the one before is not the host any more)
            for k, e in list(data.items()):
                if k != key and isinstance(e, dict) and e.get("host"):
                    data[k] = {kk: vv for kk, vv in e.items() if kk != "host"}
            data[key] = dict(data[key], host=True)
        elif data[key].get("host"):
            data[key] = {kk: vv for kk, vv in data[key].items() if kk != "host"}
        else:
            return
        _save(data)


def _fits(name: str, lang: str) -> bool:
    """A name written in the letters of the language (Cyrillic for Russian, Latin for English and Romanian)."""
    cyr = bool(re.search(r"[А-Яа-яЁё]", name))
    return cyr if lang == "ru" else not cyr


def host(lang: str) -> dict | None:
    """The host chosen on the Characters page, or else the narrator of the earlier films in this language (the one
    used most): the same host for a series."""
    chosen = next((e for e in load().values() if isinstance(e, dict) and e.get("host")), None)
    if chosen and (lang in (chosen.get("langs") or []) or _fits(str(chosen.get("name") or ""), lang)):
        return chosen                      # (a host named in Cyrillic letters hosts Russian films, in Latin ones the others)
    best = None
    for e in load().values():
        if not isinstance(e, dict):
            continue
        if e.get("narrator") and lang in (e.get("langs") or []) and int(e.get("films") or 0) >= 1:
            if best is None or int(e.get("films") or 0) > int(best.get("films") or 0):
                best = e
    return best


def update(key: str, role: str | None = None, look: dict | None = None, voice: str | None = None) -> None:
    with _LOCK:
        data = _fresh()
        e = dict(data.get(key) or {})
        if not e:
            raise KeyError(key)
        if role is not None:
            e["role"] = str(role)[:60]
        if look:
            e["look"] = {**(e.get("look") or {}), **{k: v for k, v in look.items() if k in LOOK}}
        if voice is not None:
            e["voice"] = re.sub(r"[\r\n]+", " ", str(voice)).strip()[:300]
        e["changed"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        data[key] = e
        _save(data)


def forget(key: str) -> None:
    with _LOCK:
        data = _fresh()
        data.pop(key, None)
        _save(data)


def portrait(c: dict, w: int = 240, h: int = 300) -> bytes:
    """A small picture of a character (PNG), standing, a little happy."""
    import cv2
    from . import chars as ch
    from .draw import Canvas
    cv = Canvas(w, h, 420)
    cv.vgradient("#eef3f8", "#dfe7ef")
    ch.draw(cv, c, 210, cv.SH - 18, 0.86 * (cv.SH / 560) * 0.98, 1, "wave", emotion="happy", t=0.4)
    ok, buf = cv2.imencode(".png", cv.img)
    return buf.tobytes() if ok else b""
