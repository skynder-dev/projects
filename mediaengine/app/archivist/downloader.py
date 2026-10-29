"""Download by a link (Media -> Download by a link; the owner asked for it on 2026-10-29): a video, or chosen videos of
a profile, channel or playlist, from YouTube, TikTok, archive.org and the many other sites yt-dlp knows, into a
"Downloaded" folder next to the saved reels - to study a cartoon's rhythm, retell its story, cut clips, convert.

yt-dlp (free, open; Unlicense) and deno (MIT; the JavaScript runtime yt-dlp needs for YouTube) are downloaded once with
a button from their GitHub releases into the data folder - pinned versions, sizes and SHA-256 checked - and run
without a window. Only public videos: no sign-in, no cookies, no passwords. At most MAX_VIDEOS at once, up to 1080p.
Downloads have a line of their own (one at a time, beside the voice-over queue): Stop, Try again, Delete.
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
import zipfile
from pathlib import Path

from .config import HOME
from .db import now_iso

ROOT = HOME / "addons" / "downloader"
JOBS = HOME / "download_jobs"
MAX_VIDEOS = 30
MAX_LIST = 200                    # (a profile's newest videos read for the list)
YTDLP = {"tag": "2026.10.26", "name": "yt-dlp.exe", "size": 23575744,
         "sha256": "f5389d3698ecde4ef06f4e6b1ce0294fe9ac1396228c8990b8d3416d6d177a7d",
         "url": "https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.26/yt-dlp.exe"}
DENO = {"tag": "v2.9.7", "name": "deno-x86_64-pc-windows-msvc.zip", "size": 42630221,
        "sha256": "a0c3101b4158d1dfb7d6a78a7bf0f3de80c96bb423c152beec8beb22786f2238",
        "url": "https://github.com/denoland/deno/releases/download/v2.9.7/deno-x86_64-pc-windows-msvc.zip"}
FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b"
_JOB_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")


class DownloadError(Exception):
    pass


def _no_window() -> dict:
    """No window, below normal priority, and yt-dlp's words in UTF-8 (a Russian Windows would give its own code page:
    a file path with Cyrillic letters read wrong)."""
    from .platform_adapter import process_kwargs
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return process_kwargs({"env": env}, below_normal=True)


# ------------------------------------------------------------------------------------------------ the tools

def _tools() -> tuple[list[str], str] | None:
    """(yt-dlp's command, deno's path ('' when none)) - None when not installed. MEDENG_YTDLP: the checks' stand-in."""
    fake = os.environ.get("MEDENG_YTDLP")
    if fake:
        return fake.split("|"), ""
    y, d = ROOT / YTDLP["name"], ROOT / "deno.exe"
    if y.is_file():
        return [str(y)], (str(d) if d.is_file() else "")
    return None


def installed() -> bool:
    return _tools() is not None and (bool(os.environ.get("MEDENG_YTDLP")) or (ROOT / "deno.exe").is_file())


INSTALL: dict = {"state": "idle", "step": "", "done": 0, "total": 0, "error": ""}
_STOP = threading.Event()
_ILOCK = threading.Lock()


def status() -> dict:
    m = {}
    try:
        m = json.loads((ROOT / "addon.json").read_text("utf-8"))
    except (OSError, ValueError):
        pass
    return dict(INSTALL, installed=installed(), version=m.get("version") or "", size=YTDLP["size"] + int(DENO["size"] or 0))


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def start_install() -> None:
    with _ILOCK:
        if INSTALL["state"] == "running":
            return
        _STOP.clear()
        INSTALL.update(state="running", step="checking", done=0, total=YTDLP["size"] + int(DENO["size"] or 0), error="")
    threading.Thread(target=_install_now, name="downloader-install", daemon=True).start()


def cancel_install() -> None:
    _STOP.set()


def _install_now() -> None:
    from . import auto_edit as ae
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(ROOT).free < INSTALL["total"] * 3 + 200_000_000:
            raise DownloadError("Not enough free space on the disk of the data folder.")
        base = 0
        for item, step in ((YTDLP, "ytdlp"), (DENO, "deno")):
            INSTALL.update(step=step)
            part = ROOT / (item["name"] + ".part")
            ae._fetch_resumable(item["url"], part, int(item["size"]), lambda have, b=base: INSTALL.update(done=b + have), stop=_STOP)
            if part.stat().st_size != int(item["size"]) or _sha(part) != item["sha256"]:
                part.unlink(missing_ok=True)
                raise DownloadError(f"The downloaded {item['name']} is not the expected file (its checksum differs).")
            if item is YTDLP:
                os.replace(part, ROOT / item["name"])
            else:
                with zipfile.ZipFile(part) as z:
                    names = [n for n in z.namelist() if n.lower().endswith("deno.exe") and ".." not in n]
                    if not names:
                        raise DownloadError("deno.exe is not in the downloaded archive.")
                    with z.open(names[0]) as src, (ROOT / "deno.exe.new").open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                os.replace(ROOT / "deno.exe.new", ROOT / "deno.exe")
                part.unlink(missing_ok=True)
            base += int(item["size"])
        INSTALL.update(step="testing")
        version = _version(ROOT / YTDLP["name"])
        (ROOT / "addon.json").write_text(json.dumps({"version": version, "ytdlp": [YTDLP["tag"], YTDLP["sha256"]],
                                                     "deno": [DENO["tag"], DENO["sha256"]], "installed_at": now_iso()}, indent=1), "utf-8")
        INSTALL.update(state="done", step="")
    except Exception as exc:
        INSTALL.update(state="failed", step="", error="Installation cancelled." if _STOP.is_set() else str(exc)[:400])


def _version(exe: Path) -> str:
    """yt-dlp's own version: it starts (DownloadError when it does not)."""
    try:
        cp = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=120, **_no_window())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DownloadError(f"The downloader was installed but does not start: {exc}")
    version = (cp.stdout or "").strip()
    if cp.returncode != 0 or not version:
        raise DownloadError("The downloader was installed but does not start: " + (cp.stderr or "").strip()[-200:])
    return version


def remove() -> None:
    if _CUR.get("id"):
        raise DownloadError("A download is running: stop it first.")
    shutil.rmtree(ROOT, ignore_errors=True)
    INSTALL.update(state="idle", step="", error="")


# ------------------------------------------------------------------------------------------------ a link read

def check_url(url: str) -> str:
    u = re.sub(r"\s+", "", str(url or ""))
    if not re.match(r"^https?://[^/\s]+\.[^/\s]+", u, re.I) or len(u) > 600:
        raise DownloadError("Paste a link that starts with https:// (a video, a profile, a channel or a playlist).")
    return u


def _friendly(err: str) -> str:
    e = err.lower()
    if "sign in to confirm" in e or "not a bot" in e:
        return "The site asked to sign in (it took the program for a robot). Try again later, or another link."
    if "private" in e or "login" in e or "logged-in" in e or "cookies" in e or "members-only" in e:
        return "This video is not public (the site asks to sign in): it cannot be downloaded."
    if "unsupported url" in e:
        return "This link has no video the downloader knows."
    if "unavailable" in e or "removed" in e or "404" in e:
        return "This video is not available any more."
    if "geo" in e or "country" in e:
        return "This video is not available in this country."
    last = [ln for ln in err.strip().splitlines() if ln.strip()][-1:] or ["?"]
    return "The link could not be read: " + re.sub(r"^ERROR:\s*", "", last[0])[:300]


def _base(t: tuple[list[str], str]) -> list[str]:
    cmd, deno = t
    return cmd + ["--no-config", "--no-warnings", "--no-cache-dir", "--encoding", "utf-8"] + (["--js-runtimes", f"deno:{deno}"] if deno else [])


def look(url: str) -> dict:
    """What a link holds: {"kind": "video"|"list", "title", "uploader", "entries": [{url, title, duration, views, date}]}."""
    t = _tools()
    if not t:
        raise DownloadError("Install the downloader first.")
    url = check_url(url)
    try:
        cp = subprocess.run(_base(t) + ["--flat-playlist", "--playlist-end", str(MAX_LIST), "-J", url], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=180, **_no_window())
    except subprocess.TimeoutExpired:
        raise DownloadError("The site took too long to answer. Try again.")
    if cp.returncode != 0:
        raise DownloadError(_friendly(cp.stderr or cp.stdout or ""))
    try:
        d = json.loads(cp.stdout or "{}")
    except ValueError:
        raise DownloadError("The site's answer could not be read. Try again.")

    def entry(e: dict) -> dict:
        u = str(e.get("webpage_url") or e.get("url") or "")
        if u and not u.startswith("http"):
            u = f"https://www.youtube.com/watch?v={u}" if e.get("ie_key") == "Youtube" else ""
        return {"url": u, "title": str(e.get("title") or e.get("id") or "")[:200], "id": str(e.get("id") or "")[:80],
                "duration": float(e.get("duration") or 0) or None, "views": int(e.get("view_count") or 0) or None,
                "date": str(e.get("upload_date") or e.get("release_date") or "")[:8]}
    if d.get("_type") in ("playlist", "multi_video") or isinstance(d.get("entries"), list):
        ents = [entry(e) for e in (d.get("entries") or []) if isinstance(e, dict)]
        ents = [e for e in ents if e["url"].startswith("http")]
        return {"kind": "list", "url": url, "title": str(d.get("title") or "")[:200],
                "uploader": str(d.get("uploader") or d.get("channel") or "")[:120], "entries": ents}
    e = entry(d)
    e["url"] = e["url"] or url
    return {"kind": "video", "url": url, "title": e["title"], "uploader": str(d.get("uploader") or d.get("channel") or "")[:120],
            "entries": [e]}


# ------------------------------------------------------------------------------------------------ the jobs

_CUR: dict = {}
_QUEUE: list = []
_QLOCK = threading.Lock()
_THREAD: list = []


def folder() -> Path:
    from . import auto_edit as ae
    try:
        f = ae.default_export_dir() / ("Скачанные" if ae._ui_ru() else "Downloaded")
    except Exception:
        f = HOME / "Downloaded"
    f.mkdir(parents=True, exist_ok=True)
    return f


def _write(d: Path, name: str, data: dict) -> None:
    tmp = d / (name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    os.replace(tmp, d / name)


def read_job(jid: str) -> dict:
    if not _JOB_ID.match(str(jid or "")):
        raise DownloadError("No such download.")
    d = JOBS / jid
    try:
        job = json.loads((d / "job.json").read_text("utf-8"))
    except (OSError, ValueError):
        raise DownloadError("No such download.")
    try:
        res = json.loads((d / "result.json").read_text("utf-8"))
    except (OSError, ValueError):
        res = None
    if _CUR.get("id") == jid:
        state = "working"
    elif jid in _QUEUE:
        state = "waiting"
    elif res is None:
        state = "interrupted"
    else:
        state = res.get("state") or ("done" if res.get("ok") else "failed")
    job.update(state=state, result=res or {}, progress=_CUR.get("progress", 0.0) if state == "working" else (1.0 if state == "done" else 0.0),
               now=_CUR.get("title", "") if state == "working" else "")
    return job


def list_jobs(limit: int = 50) -> list[dict]:
    try:
        ids = [p.name for p in JOBS.iterdir() if _JOB_ID.match(p.name)]
    except OSError:
        return []
    out = []
    for jid in ids:
        try:
            out.append(read_job(jid))
        except DownloadError:
            pass
    out.sort(key=lambda j: (int(j.get("created_ns") or 0), j["id"]), reverse=True)   # (newest first, also within a second)
    return out[:limit]


def new_download(items: list[dict], study: bool = False, source: str = "") -> str:
    """A download job of up to MAX_VIDEOS links ({url, title}); study: each video studied for its rhythm after."""
    if not installed():
        raise DownloadError("Install the downloader first.")
    clean, seen = [], set()
    for it in items or []:
        try:
            u = check_url((it or {}).get("url") or "")
        except DownloadError:
            continue
        if u in seen:
            continue
        seen.add(u)
        clean.append({"url": u, "title": str((it or {}).get("title") or "")[:200]})
    if not clean:
        raise DownloadError("Choose at least one video.")
    if len(clean) > MAX_VIDEOS:
        raise DownloadError(f"At most {MAX_VIDEOS} videos at once.")
    jid = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    d = JOBS / jid
    d.mkdir(parents=True, exist_ok=True)
    _write(d, "job.json", {"id": jid, "items": clean, "study": bool(study), "source": str(source or "")[:600],
                           "title": (clean[0]["title"] if len(clean) == 1 else f"{len(clean)} videos")[:120], "created_at": now_iso(),
                           "created_ns": time.time_ns()})
    _enqueue(jid)
    return jid


def _enqueue(jid: str) -> None:
    with _QLOCK:
        if jid not in _QUEUE:
            _QUEUE.append(jid)
        if not _THREAD or not _THREAD[0].is_alive():
            _THREAD[:] = [threading.Thread(target=_loop, name="downloads", daemon=True)]
            _THREAD[0].start()


def retry(jid: str) -> None:
    j = read_job(jid)
    if j["state"] in ("working", "waiting"):
        return
    try:
        (JOBS / jid / "result.json").unlink()
    except OSError:
        pass
    _enqueue(jid)


def stop(jid: str) -> None:
    with _QLOCK:
        if jid in _QUEUE and _CUR.get("id") != jid:
            _QUEUE.remove(jid)
            _write(JOBS / jid, "result.json", {"ok": False, "state": "stopped", "error": "Stopped.", "files": []})
            return
    if _CUR.get("id") == jid:
        _CUR["cancel"] = True
        p = _CUR.get("proc")
        if p is not None:
            from . import voice as vo
            vo._kill(p)


def delete(jid: str) -> None:
    j = read_job(jid)
    if j["state"] in ("working", "waiting"):
        raise DownloadError("Stop it first.")
    shutil.rmtree(JOBS / jid, ignore_errors=True)            # (the downloaded videos stay in their folder)


def _loop() -> None:
    while True:
        with _QLOCK:
            if not _QUEUE:
                _THREAD.clear()
                return
            jid = _QUEUE[0]
            _CUR.clear()
            _CUR.update(id=jid, progress=0.0, title="")
        try:
            res = _do(jid)
        except Exception as exc:
            res = {"ok": False, "error": str(exc)[:400], "files": []}
        if _CUR.get("cancel"):
            res = dict(res, ok=False, state="stopped", error="Stopped.")
        try:
            _write(JOBS / jid, "result.json", dict(res, finished_at=now_iso()))
        except OSError:
            pass
        with _QLOCK:
            if _QUEUE and _QUEUE[0] == jid:
                _QUEUE.pop(0)
            _CUR.clear()


_PCT = re.compile(r"\[download\]\s+([\d.]+)%")


def _do(jid: str) -> dict:
    from . import auto_edit as ae, voice as vo
    t = _tools()
    if not t:
        return {"ok": False, "error": "The downloader is not installed.", "files": []}
    job = json.loads((JOBS / jid / "job.json").read_text("utf-8"))
    dst = folder()
    items = job["items"]
    files, errors = [], []
    for k, it in enumerate(items):
        if _CUR.get("cancel"):
            break
        _CUR.update(title=it.get("title") or it["url"], progress=round(k / len(items), 3))
        cmd = _base(t) + ["--no-playlist", "-f", FORMAT, "--merge-output-format", "mp4", "--ffmpeg-location", vo._ffmpeg(),
                          "--no-part", "--no-mtime", "--max-filesize", "4G", "--trim-filenames", "120", "--newline",
                          "-o", str(dst / "%(uploader).40s - %(title).70s [%(id)s].%(ext)s"),
                          "--print", "after_move:MEDENG_FILE %(filepath)s", it["url"]]
        log = JOBS / jid / f"item{k:02d}.log"
        got, last_err = "", ""
        started = time.time()
        with log.open("w", encoding="utf-8", errors="replace") as lf:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
                                    encoding="utf-8", errors="replace", **_no_window())
            ae._attach_job_object(proc)                    # (ends with the program; Stop kills it)
            _CUR["proc"] = proc
            if _CUR.get("cancel"):
                vo._kill(proc)
            for line in proc.stdout:
                lf.write(line)
                m = _PCT.search(line)
                if m:
                    _CUR["progress"] = round((k + min(100.0, float(m.group(1))) / 100.0) / len(items), 3)
                if line.startswith("MEDENG_FILE "):
                    got = line[len("MEDENG_FILE "):].strip()
                elif line.startswith("ERROR"):
                    last_err = line
            proc.wait()
            _CUR.pop("proc", None)
        if not (got and Path(got).is_file()) and proc.returncode == 0:   # (its path not read back: the newest video made now)
            new = [p for p in dst.iterdir() if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov") and p.stat().st_mtime >= started - 2]
            got = str(max(new, key=lambda p: p.stat().st_mtime)) if new else ""
        if got and Path(got).is_file():
            files.append({"url": it["url"], "title": it.get("title") or Path(got).stem, "file": got,
                          "size": Path(got).stat().st_size})
        elif not _CUR.get("cancel"):
            errors.append({"url": it["url"], "title": it.get("title") or "", "error": _friendly(last_err or "")})
    studies = []
    if job.get("study") and files and not _CUR.get("cancel"):
        from .cartoon import reference as R               # (each video studied for its rhythm, in the voice-over line)
        for f in files:
            try:
                studies.append(R.new_study(f["file"], listen=True))
            except Exception:
                pass
    ok = bool(files) and not errors
    return {"ok": ok, "state": "done" if files else "failed", "files": files, "errors": errors, "studies": studies,
            "folder": str(dst), "error": "" if files else ((errors[0]["error"] if errors else "Nothing was downloaded."))}


def resume_after_restart() -> None:
    """Downloads left unfinished by a closed program: said as interrupted (Try again continues them)."""
    return None
