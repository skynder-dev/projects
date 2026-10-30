"""Edit by hand: one video put together from pieces of any videos - from this PC, the Library, the downloads or the
moments MediaEngine found. A piece is a part of its video (from "in" to "out", seconds), its sound on or off; the
pieces play in the order chosen. The edit is kept as one file (<data folder>/handedit/<id>.json) and can be opened and
changed again; its MP4 is made in the background (the voice-over queue: Activity, Stop) in the format chosen (9:16,
16:9, 1:1, 4:5; the picture fills the frame) into an "Edits" folder next to the saved reels. The originals are never
changed. The page plays the pieces from their own files (a copy the browser can play is made of a file it cannot).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
MAX_PIECES = 200
MAX_SECONDS = 3 * 3600
MIN_PIECE = 0.2
FPS = 30
_ID = re.compile(r"^e[0-9]{8}-[0-9]{6}-[0-9a-f]{4}$")
_LOCK = threading.Lock()
# what a browser plays by itself (else a playable copy is made for the page): codec names as FFmpeg says them
_PLAYS = {"h264", "vp8", "vp9", "av1"}
_PLAYS_IN = {".mp4", ".m4v", ".mov", ".webm"}


class EditError(ValueError):
    pass


def root() -> Path:
    from .config import HOME
    return HOME / "handedit"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _write(e: dict) -> None:
    d = root()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{e['id']}.json"
    tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(e, ensure_ascii=False, indent=1), "utf-8")
    for i in range(20):                                   # (Windows: a page reading it, a virus check holds it a moment)
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (i + 1))


# ------------------------------------------------------------------------------------------------- a video's facts

_INFO: dict = {}


def info(path) -> dict:
    """A video's length, picture size, sound and whether a browser plays it as it is ({} when it cannot be read).
    Asked once per file state."""
    p = Path(str(path))
    try:
        st = p.stat()
    except OSError:
        return {}
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _INFO:
        from . import auto_edit as ae
        if ae.cloud_only(p, st):                          # (never make OneDrive download a file just to look at it)
            return {"cloud": True}
        try:
            pr = ae.probe_any(p)
        except Exception:
            _INFO[key] = {}
            return {}
        vs = next((s for s in pr.get("streams") or [] if s.get("codec_type") == "video"), {})
        has_a = any(s.get("codec_type") == "audio" for s in pr.get("streams") or [])
        try:
            secs = float((pr.get("format") or {}).get("duration") or vs.get("duration") or 0)
        except (TypeError, ValueError):
            secs = 0.0
        w, h = int(vs.get("width") or 0), int(vs.get("height") or 0)
        rot = 0
        for sd in vs.get("side_data_list") or []:
            try:
                rot = int(float(sd.get("rotation") or 0))
            except (TypeError, ValueError):
                pass
        rot = rot or int(float((vs.get("tags") or {}).get("rotate") or 0))
        if abs(rot) % 180 == 90:
            w, h = h, w
        _INFO[key] = {"seconds": round(secs, 3), "width": w, "height": h, "audio": has_a,
                      "plays": str(vs.get("codec_name") or "").lower() in _PLAYS and p.suffix.lower() in _PLAYS_IN
                      and str(vs.get("pix_fmt") or "yuv420p") in ("yuv420p", "yuvj420p")}
    return dict(_INFO[key])


# ------------------------------------------------------------------------------------------------- an edit

def new(title: str = "", fmt: str = "9:16") -> str:
    with _LOCK:
        eid = "e" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
        _write({"id": eid, "title": _title(title), "format": fmt if fmt in FORMATS else "9:16", "pieces": [],
                "created_at": _now(), "updated_at": _now(), "renders": []})
    return eid


def _title(t) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()[:80] or time.strftime("Edit %Y-%m-%d %H:%M")


def _num(v, default: float = 0.0) -> float:
    try:
        x = float(v)
        return x if x == x and abs(x) < 1e7 else default
    except (TypeError, ValueError):
        return default


def _piece(x) -> dict | None:
    """A piece as kept (a hand-edited file never breaks the page): its video, in, out, sound."""
    if not isinstance(x, dict) or not str(x.get("src") or "").strip():
        return None
    a, b = max(0.0, _num(x.get("in"))), _num(x.get("out"))
    if b <= a:
        b = a + 1.0
    return {"src": str(x["src"])[:1000], "in": round(a, 3), "out": round(b, 3), "mute": bool(x.get("mute")),
            **({"from": str(x["from"])[:40]} if x.get("from") else {})}


def get(eid: str) -> dict:
    if not _ID.fullmatch(str(eid or "")):
        return {}
    try:
        d = json.loads((root() / f"{eid}.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(d, dict) or d.get("id") != eid:
        return {}
    pieces = [p for p in (_piece(x) for x in (d.get("pieces") if isinstance(d.get("pieces"), list) else [])) if p]
    return {"id": eid, "title": _title(d.get("title")), "format": d.get("format") if d.get("format") in FORMATS else "9:16",
            "pieces": pieces[:MAX_PIECES], "created_at": str(d.get("created_at") or ""), "updated_at": str(d.get("updated_at") or ""),
            "renders": [r for r in (d.get("renders") if isinstance(d.get("renders"), list) else []) if isinstance(r, dict)][-20:]}


def items(limit: int = 100) -> list[dict]:
    try:
        names = sorted((p.stem for p in root().glob("e*.json")), reverse=True)
    except OSError:
        return []
    return [x for x in (get(n) for n in names[:limit]) if x]


def seconds(e: dict) -> float:
    return round(sum(max(0.0, p["out"] - p["in"]) for p in e.get("pieces") or []), 3)


def save(eid: str, title=None, fmt=None, pieces=None) -> dict:
    """The page's changes: the title, the format, the pieces (each checked against its video's length)."""
    with _LOCK:
        e = get(eid)
        if not e:
            raise EditError("This edit is not there any more.")
        if title is not None:
            e["title"] = _title(title)
        if fmt is not None:
            if fmt not in FORMATS:
                raise EditError("Choose one of the formats.")
            e["format"] = fmt
        if pieces is not None:
            if not isinstance(pieces, list):
                raise EditError("The pieces could not be read.")
            if len(pieces) > MAX_PIECES:
                raise EditError(f"An edit can have up to {MAX_PIECES} pieces.")
            known = {p["src"] for p in e["pieces"]}
            out = []
            for x in pieces:
                p = _piece(x)
                if not p:
                    continue
                if p["src"] not in known:                 # (only videos added through add(): the page cannot name any file)
                    raise EditError("A piece names a video that was not added to this edit.")
                n = info(p["src"]).get("seconds") or 0
                if n:
                    p["out"] = min(p["out"], n)
                    p["in"] = min(p["in"], max(0.0, p["out"] - MIN_PIECE))
                if p["out"] - p["in"] < MIN_PIECE - 1e-6:
                    p["out"] = p["in"] + MIN_PIECE
                out.append(p)
            if sum(p["out"] - p["in"] for p in out) > MAX_SECONDS:
                raise EditError("An edit can be up to three hours long.")
            e["pieces"] = out
        e["updated_at"] = _now()
        _write(e)
        return e


def add(eid: str, paths: list, start: float | None = None, end: float | None = None, origin: str = "") -> dict:
    """Videos added at the end (a whole video, or a part of it: a found moment)."""
    from . import auto_edit as ae
    with _LOCK:
        e = get(eid)
        if not e:
            raise EditError("This edit is not there any more.")
        bad, added = [], 0
        for raw in list(paths or [])[:50]:
            p = Path(str(raw or "").strip().strip('"'))
            if not p.is_file() or p.suffix.lower() not in ae.SUPPORTED:
                bad.append(p.name or str(raw))
                continue
            i = info(p)
            if i.get("cloud"):
                bad.append(p.name + " (only in the cloud: open it once so it downloads)")
                continue
            if not i.get("seconds"):
                bad.append(p.name)
                continue
            if len(e["pieces"]) >= MAX_PIECES:
                raise EditError(f"An edit can have up to {MAX_PIECES} pieces.")
            a = max(0.0, float(start or 0.0))
            b = min(i["seconds"], float(end)) if end else i["seconds"]
            if b - a < MIN_PIECE:
                a, b = 0.0, i["seconds"]
            e["pieces"].append({"src": str(p), "in": round(a, 3), "out": round(b, 3), "mute": False,
                                **({"from": origin[:40]} if origin else {})})
            added += 1
        e["updated_at"] = _now()
        _write(e)
    if bad and not added:
        raise EditError("These could not be used as videos: " + ", ".join(bad[:5]))
    return dict(e, not_added=bad)


def delete(eid: str) -> None:
    """The edit forgotten (its MP4s stay where they were saved)."""
    if _ID.fullmatch(str(eid or "")):
        (root() / f"{eid}.json").unlink(missing_ok=True)


# ------------------------------------------------------------------------------------------------- the page's player

_PROXY: dict = {}                        # (source key) -> {"state": "working" | "done" | "failed", "path": ...}
_PROXY_LOCK = threading.Lock()


def _proxy_file(src: Path) -> Path:
    st = src.stat()
    k = hashlib.sha1(f"{src}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8")).hexdigest()[:20]
    return root() / "proxies" / f"{k}.mp4"


def proxy(src: str, make: bool = True) -> dict:
    """A copy the browser can play (small, H.264) of a video it cannot (HEVC, a camcorder's .MTS, .AVI ...): made
    once in the background; {"state": "done", "path"} when ready."""
    p = Path(src)
    try:
        out = _proxy_file(p)
    except OSError:
        return {"state": "failed"}
    if out.is_file():
        return {"state": "done", "path": str(out)}
    with _PROXY_LOCK:
        cur = _PROXY.get(str(out))
        if cur or not make:
            return dict(cur or {"state": "none"})
        _PROXY[str(out)] = {"state": "working"}
    threading.Thread(target=_make_proxy, args=(p, out), name="handedit-proxy", daemon=True).start()
    return {"state": "working"}


def _make_proxy(src: Path, out: Path) -> None:
    from . import auto_edit as ae
    from .platform_adapter import process_kwargs
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part.mp4")
    try:
        pre = _pre_filters(src)
        vf = ",".join(pre + ["scale='min(960,iw)':-2:force_divisible_by=2", "format=yuv420p"])
        cmd = [str(ae._ffmpeg()), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
               "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-g", "30", "-c:a", "aac", "-b:a", "96k",
               "-ac", "2", "-movflags", "+faststart", str(tmp)]
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=6 * 3600,
                            **process_kwargs())
        if cp.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 1024:
            raise RuntimeError((cp.stderr or "").strip()[-300:])
        os.replace(tmp, out)
        state = {"state": "done", "path": str(out)}
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        state = {"state": "failed", "error": str(exc)[:300]}
    with _PROXY_LOCK:
        _PROXY[str(out)] = state


def _pre_filters(src: Path) -> list[str]:
    """An HDR phone video's colours made normal and a camcorder's fields made whole frames (as the reels do)."""
    try:
        from .clips import _hdr_first
        return _hdr_first(src)
    except Exception:
        return []


def frame(src: str, t: float, width: int = 192) -> bytes:
    """A small picture (JPEG) of a video at t seconds (the pieces on the time line)."""
    from . import auto_edit as ae
    from .platform_adapter import process_kwargs
    key = (src, round(float(t), 1), width)
    if key in _FRAMES:
        return _FRAMES[key]
    pre = _pre_filters(Path(src))
    cmd = [str(ae._ffmpeg()), "-hide_banner", "-nostdin", "-v", "error", "-ss", f"{max(0.0, float(t)):.2f}", "-i", str(src),
           "-frames:v", "1", "-vf", ",".join(pre + [f"scale={int(width)}:-2"]), "-f", "image2", "-c:v", "mjpeg", "-q:v", "5", "-"]
    try:
        cp = subprocess.run(cmd, capture_output=True, timeout=60, **process_kwargs())
        data = cp.stdout if cp.returncode == 0 else b""
    except Exception:
        data = b""
    if data:
        if len(_FRAMES) > 600:
            _FRAMES.pop(next(iter(_FRAMES)))
        _FRAMES[key] = data
    return data


_FRAMES: dict = {}


# ------------------------------------------------------------------------------------------------- the MP4

def folder() -> Path:
    from . import auto_edit as ae
    f = ae.default_export_dir() / ("Монтаж" if ae._ui_ru() else "Edits")
    f.mkdir(parents=True, exist_ok=True)
    return f


def new_render(eid: str) -> str:
    """The edit's MP4 put in the queue (made as the edit is now: later changes do not touch it)."""
    from . import voice as vo
    e = get(eid)
    if not e:
        raise EditError("This edit is not there any more.")
    if not e["pieces"]:
        raise EditError("Add at least one video first.")
    missing = [Path(p["src"]).name for p in e["pieces"] if not Path(p["src"]).is_file()]
    if missing:
        raise EditError("These videos are not there any more (moved, or a drive not connected): " + ", ".join(sorted(set(missing))[:5]))
    return vo._submit({"kind": "handedit_render", "edit": eid, "title": e["title"], "format": e["format"],
                       "pieces": e["pieces"], "seconds": seconds(e), "needs_addon": False}, addon=False)


def _run(cmd: list, timeout: float) -> subprocess.CompletedProcess:
    """FFmpeg for the queue's job: hidden, reachable by Stop and Quit."""
    from . import auto_edit as ae, voice as vo
    from .platform_adapter import process_kwargs
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                            **process_kwargs({}))
    ae._attach_job_object(proc)
    vo._track(proc)
    try:
        _out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        _out, err = proc.communicate()
    finally:
        vo._untrack(proc)
    return subprocess.CompletedProcess(cmd, proc.returncode, "", (err or b"").decode("utf-8", "replace"))


def _segment(src: Path, a: float, b: float, mute: bool, fmt: str, out: Path) -> None:
    from . import auto_edit as ae
    W, H = FORMATS[fmt]
    dur = max(0.05, b - a)
    vf = ",".join(_pre_filters(src) + [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
                                       f"crop={W}:{H}", "setsar=1", f"fps={FPS}", "format=yuv420p"])
    has_a = bool(info(src).get("audio")) and not mute
    cmd = [str(ae._ffmpeg()), "-hide_banner", "-nostdin", "-y", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", str(src)]
    if has_a:
        cmd += ["-map", "0:v:0", "-map", "0:a:0", "-af", "aresample=48000:async=1:first_pts=0,apad"]
    else:                                                 # (no sound, or turned off: silence, so the pieces join)
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-map", "0:v:0", "-map", "1:a:0"]
    cmd += ["-vf", vf, "-ac", "2", "-ar", "48000", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", "-movflags", "+faststart", str(out)]
    cp = _run(cmd, max(120, dur * 10 + 60))
    if cp.returncode != 0 or not out.is_file() or out.stat().st_size < 1024:
        raise EditError("A piece could not be made (" + ((cp.stderr or "").strip().splitlines() or ["?"])[-1][:200] + ").")


def do(jid: str, d: Path, job: dict) -> dict:
    """voice._do for the edit's MP4 (in the queue's thread): every piece made in the format, then joined."""
    from . import auto_edit as ae, voice as vo
    fmt = job.get("format") if job.get("format") in FORMATS else "9:16"
    pieces = [p for p in (_piece(x) for x in job.get("pieces") or []) if p]
    if not pieces:
        return {"ok": False, "error": "The edit has no pieces."}
    work = d / "parts"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    total = sum(p["out"] - p["in"] for p in pieces) or 1.0
    done_s, parts = 0.0, []
    try:
        for n, p in enumerate(pieces):
            if vo._CURRENT.get("cancel"):
                return {"ok": False, "error": "Stopped."}
            src = Path(p["src"])
            if not src.is_file():
                return {"ok": False, "error": "The video is not there any more: " + str(src)}
            vo._CURRENT.update(step=f"piece {n + 1}/{len(pieces)}", progress=round(0.9 * done_s / total, 3))
            out = work / f"p{n:04d}.mp4"
            _segment(src, p["in"], p["out"], p["mute"], fmt, out)
            parts.append(out)
            done_s += p["out"] - p["in"]
        if vo._CURRENT.get("cancel"):
            return {"ok": False, "error": "Stopped."}
        vo._CURRENT.update(step="joining", progress=0.92)
        lst = work / "list.txt"
        lst.write_text("".join("file '" + x.resolve().as_posix().replace("'", "'\\''") + "'\n" for x in parts), "utf-8")
        made = d / "edit.mp4"
        cp = _run([str(ae._ffmpeg()), "-hide_banner", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                   "-c", "copy", "-movflags", "+faststart", str(made)], 600)
        if cp.returncode != 0 or not made.is_file() or made.stat().st_size < 1024:
            return {"ok": False, "error": "The pieces could not be joined (" + (cp.stderr or "").strip()[-200:] + ")."}
    except EditError as exc:
        return {"ok": False, "error": "Stopped." if vo._CURRENT.get("cancel") else str(exc)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    W, H = FORMATS[fmt]
    secs = info(made).get("seconds") or round(total, 3)
    saved = ""
    try:
        f = folder()
        base = ae.safe_filename(str(job.get("title") or "")[:80], "Edit")
        dst = f / f"{base}.mp4"
        k = 2
        while dst.exists():
            dst = f / f"{base} ({k}).mp4"
            k += 1
        try:
            os.link(made, dst)
        except OSError:
            shutil.copy2(made, dst)
        saved = str(dst)
    except Exception:
        pass
    eid = str(job.get("edit") or "")
    with _LOCK:
        e = get(eid)
        if e:
            e["renders"] = (e["renders"] + [{"job": jid, "saved": saved, "seconds": secs, "format": fmt, "at": _now()}])[-20:]
            _write(e)
    vo._CURRENT.update(step="checking", progress=1.0)
    return {"ok": True, "file": "edit.mp4", "saved": saved, "seconds": secs, "width": W, "height": H, "pieces": len(pieces)}
