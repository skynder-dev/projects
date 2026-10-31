"""In-app update (the "Update" button, and by itself): a newer build of this MediaEngine from the owner's GitHub.

Automatic updates (on unless the owner turns them off on the Updates page; asked for by the owner 2026-10-30, so that
fixes reach his PC without him): a few minutes after the start and then every 30 minutes MediaEngine asks GitHub for
the newest build and installs it the same way as the button - only when nothing is being made (app_busy), only when
the runtime is the same (no full installer), never an older build; the switch opens no window (MEDIAENGINE_NO_BROWSER).
A failed automatic check changes nothing on the page; it is tried again later. Turned off: GitHub is asked only when
the button is pressed. Windows
CI publishes the program of every fully green build to the branch `mediaengine-update` of skynder-dev/projects
(tools/make_update_bundle.py): `latest.json` (what it is, size, SHA-256, what is new) and the program files as one ZIP
of a few MB - the app, its launcher and texts, WITHOUT the runtime (.venv: Python and its libraries, ~400 MB).

Installing it: the ZIP is downloaded into the data folder, its size and SHA-256 checked, unpacked into a new build
folder next to this one (the same layout Setup makes) and the runtime of THIS build is reused there through hard links
(no second copy on the disk) - only when runtime.txt of both says it is the same runtime; when Python or a library
changed, the page says that the full installer is needed this time. Then the usual switch: the new build's launcher
asks this one to quit (refused while a reel is being made) and starts itself on the same port. Projects stay the same;
the old folder stays as the way back ("Check this PC" lists it).

Trust: the files come over HTTPS (certificate checked) from the owner's own repository and must match the size and
SHA-256 written next to them. Whoever could put files into that branch could equally change the program's source in
the same repository - the protection is the access to the owner's GitHub, as for the builds he installs with Setup.
"""
from __future__ import annotations

import hashlib, json, os, re, shutil, subprocess, threading, time, urllib.error, urllib.request, zipfile
from pathlib import Path

from .config import BUILD, DATA, INSTALL, VERSION

BASE_URL = "https://raw.githubusercontent.com/skynder-dev/projects/mediaengine-update/"
FORMAT = "mediaengine.update/1"
MAX_BUNDLE = 300 * 2 ** 20          # bytes of the ZIP (the program is a few MB)
MAX_UNPACKED = 800 * 2 ** 20
REQUIRED = ("BUILD.txt", "port.txt", "Start MediaEngine.vbs", "launcher.py", "version.txt", "runtime.txt", "app/main.py")
_PKG = re.compile(r"MediaEngine-([0-9][0-9A-Za-z.\-]*)-b(\d+)$")
_LOCK = threading.Lock()
_BUSY_STATES = ("downloading", "preparing", "switching")
_APPLY = threading.Event()          # an install thread is alive (one at a time, whatever the page shows)
SWITCH_WAIT_S = 150                 # the new build's launcher stops this one within this time, or the switch failed
STATE: dict = {"state": "idle", "error": "", "detail": "", "found": None, "done": 0, "total": 0, "target": "", "checked_at": 0.0}


class UpdateError(Exception):
    """A reason shown to the owner (a fixed English page text, translated like every page) and, apart from it, a
    detail that stays as it is (a path, an error code)."""

    def __init__(self, msg: str, detail: str = ""):
        super().__init__(msg)
        self.detail = str(detail or "")[:400]


def version_key(v):
    """3.13.0-rc1 < 3.13.0-rc2 < 3.13.0 (same rule as the launcher)."""
    m = re.match(r"\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-.]?(alpha|beta|rc|a|b)(\d*))?", str(v or ""))
    if not m:
        return (0, 0, 0, 0, 0)
    pre = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2}.get((m.group(4) or "").lower(), 3)
    return (int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0), pre, int(m.group(5) or 0))


def build_order(name):
    """Order of a build folder name 'MediaEngine-3.13.0-rc1-b145' (version, then build number); None when unknown."""
    m = _PKG.match(str(name or ""))
    return (version_key(m.group(1)), int(m.group(2))) if m else None


def build_label(name) -> str:
    m = _PKG.match(str(name or ""))
    return f"{m.group(1)} b{m.group(2)}" if m else str(name or "")


def runtime_id(folder) -> str:
    try:
        return (Path(folder) / "runtime.txt").read_text(encoding="utf-8").strip()[:64]
    except OSError:
        return ""


def base_url() -> str:
    """GitHub, or - for the checks only - a server on this PC (MEDIAENGINE_UPDATE_URL=http://127.0.0.1:<port>/)."""
    o = os.environ.get("MEDIAENGINE_UPDATE_URL", "").strip()
    if o:
        if not re.match(r"^http://127\.0\.0\.1:\d{1,5}/", o):
            raise UpdateError("MEDIAENGINE_UPDATE_URL may only point at this PC (it is for checks).")
        return o
    return BASE_URL


def why_not() -> str:
    """Why this MediaEngine cannot update itself with the button ('' = it can)."""
    if os.environ.get("MEDIAENGINE_UPDATES") == "off":
        return "Updates are turned off here."
    if not (INSTALL / "port.txt").is_file():
        return "Only an installed MediaEngine (Setup or ZIP) updates itself."
    if not runtime_id(INSTALL):
        return "This version cannot update itself yet. Install the new version once with its Setup."
    return ""


def status() -> dict:
    s = dict(STATE)
    f = s.get("found") or {}
    s["found"] = {k: f.get(k) for k in ("pkg", "size", "newer", "same_runtime")} if f else None
    s["percent"] = int(100 * s["done"] / s["total"]) if s.get("total") else 0
    return s


def _get(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": f"MediaEngine/{VERSION} {BUILD}".strip(),
                                               "Cache-Control": "no-cache", "Pragma": "no-cache"})
    if url.startswith("http://127.0.0.1:"):                   # the checks' server on this PC: never through a proxy
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)       # HTTPS: the certificate is checked (Windows' own list)


def parse_manifest(raw: bytes) -> dict:
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        raise UpdateError("The update description on GitHub is damaged. Try again later.")
    if not isinstance(d, dict) or d.get("format") != FORMAT:
        raise UpdateError("This version does not understand the new update. Install the new version once with its Setup.")
    pkg, f = str(d.get("pkg") or ""), str(d.get("file") or "")
    try:
        size = int(d.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    sha = str(d.get("sha256") or "").lower()
    if (not _PKG.match(pkg) or not re.fullmatch(r"[A-Za-z0-9._\-]{1,150}\.zip", f) or not 0 < size <= MAX_BUNDLE
            or not re.fullmatch(r"[0-9a-f]{64}", sha)):
        raise UpdateError("The update description on GitHub is damaged. Try again later.")
    run_url = str(d.get("run_url") or "")
    notes = []
    for n in (d.get("notes") or [])[:80] if isinstance(d.get("notes"), list) else []:
        if isinstance(n, dict) and n.get("en"):
            notes.append({"since": str(n.get("since") or "")[:12], "en": str(n.get("en"))[:500], "ru": str(n.get("ru") or "")[:500]})
    return {"pkg": pkg, "file": f, "size": size, "sha256": sha, "runtime": str(d.get("runtime") or "")[:64],
            "version": str(d.get("version") or "")[:40], "commit": str(d.get("commit") or "")[:40],
            "run_url": run_url if run_url.startswith("https://github.com/") else "",
            "created_at": str(d.get("created_at") or "")[:40], "notes": notes}


def check() -> dict:
    """Ask GitHub what the newest build is (the button was pressed). Raises UpdateError with a reason to show."""
    why = why_not()
    if why:
        raise UpdateError(why)
    with _LOCK:
        if STATE["state"] in _BUSY_STATES or _APPLY.is_set():
            raise UpdateError("An update is being installed right now.")
    try:
        with _get(base_url() + f"latest.json?t={int(time.time())}", 20) as r:      # (not an old copy from a cache)
            raw = r.read(2_000_001)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("No update has been published yet.")
        raise UpdateError("GitHub answered with an error. Try again later.", f"HTTP {exc.code}")
    except UpdateError:
        raise
    except Exception as exc:
        raise UpdateError("No connection to GitHub. Check the internet connection and try again.", f"{type(exc).__name__}: {exc}")
    if len(raw) > 2_000_000:
        raise UpdateError("The update description on GitHub is damaged. Try again later.")
    m = parse_manifest(raw)
    mine, theirs = build_order(INSTALL.name), build_order(m["pkg"])
    m["newer"] = bool(theirs and (mine is None or theirs > mine))
    m["same_runtime"] = bool(m["runtime"]) and m["runtime"] == runtime_id(INSTALL)
    with _LOCK:
        if STATE["state"] in _BUSY_STATES or _APPLY.is_set():     # Update now was pressed while this check ran
            raise UpdateError("An update is being installed right now.")
        STATE.update(state="checked", found=m, error="", detail="", checked_at=time.time(), done=0, total=0, target="")
    return m


AUTO_FIRST_S = 240                  # the first automatic check after the start (the start itself first)
AUTO_EVERY_S = 30 * 60
AUTO_RETRY_S = 5 * 60               # work was running or GitHub did not answer: again sooner
AUTO: dict = {"last": 0.0, "result": "", "detail": ""}
_AUTO_STARTED = threading.Event()


def _auto_file() -> Path:
    return DATA / "update_auto.json"


def auto_on() -> bool:
    """Automatic updates are on unless the owner turned them off (or MEDIAENGINE_AUTO_UPDATE=off)."""
    if os.environ.get("MEDIAENGINE_AUTO_UPDATE") == "off":
        return False
    try:
        return bool(json.loads(_auto_file().read_text(encoding="utf-8")).get("on", True))
    except Exception:
        return True


def set_auto(on: bool) -> None:
    f = _auto_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps({"on": bool(on), "at": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
    os.replace(tmp, f)


def _auto_log(line: str) -> None:
    try:
        p = DATA / "logs" / "update_auto.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_text(encoding="utf-8").splitlines()[-199:] if p.is_file() else []
        p.write_text("\n".join(old + [time.strftime("%Y-%m-%d %H:%M:%S ") + line]) + "\n", encoding="utf-8")
    except Exception:
        pass


def auto_tick() -> str:
    """One automatic attempt. Returns what happened: off / cannot / installing / newest / needs_installer / busy /
    check_failed / started (an install began)."""
    detail = ""
    if not auto_on():
        r = "off"
    elif why_not():
        r, detail = "cannot", why_not()
    elif STATE["state"] in _BUSY_STATES or _APPLY.is_set():
        r = "installing"
    else:
        try:
            m = check()
        except UpdateError as exc:      # the page keeps what it showed: this was not asked for
            r, detail = "check_failed", f"{exc} {exc.detail}".strip()
        else:
            if not m.get("newer"):
                r = "newest"
            elif not m.get("same_runtime"):
                r, detail = "needs_installer", str(m.get("pkg") or "")
            else:
                busy = _busy()
                if busy:
                    r, detail = "busy", busy
                else:
                    try:
                        start_apply()
                        r, detail = "started", str(m.get("pkg") or "")
                    except UpdateError as exc:
                        r, detail = "busy", str(exc)
    AUTO.update(last=time.time(), result=r, detail=detail[:300])
    if r != "off":
        _auto_log(r + (f" {detail}" if detail else ""))
    return r


def start_auto() -> None:
    """The background loop of automatic updates (once per process; it does nothing while they are off)."""
    if _AUTO_STARTED.is_set():
        return
    _AUTO_STARTED.set()
    try:
        first = float(os.environ.get("MEDIAENGINE_AUTO_UPDATE_FIRST") or AUTO_FIRST_S)
        every = float(os.environ.get("MEDIAENGINE_AUTO_UPDATE_EVERY") or AUTO_EVERY_S)
    except ValueError:
        first, every = AUTO_FIRST_S, AUTO_EVERY_S

    def loop():
        time.sleep(first)
        while True:
            try:
                r = auto_tick()
            except Exception as exc:
                r = "check_failed"
                _auto_log(f"error {type(exc).__name__}: {exc}")
            time.sleep(min(every, AUTO_RETRY_S) if r in ("busy", "check_failed") else every)
    threading.Thread(target=loop, daemon=True, name="update-auto").start()


def installing() -> bool:
    """An update is being downloaded or put next to this build (a Quit or a restart now would waste it)."""
    return STATE.get("state") in ("downloading", "preparing")


def check_failed(exc: Exception) -> None:
    with _LOCK:
        if STATE["state"] not in _BUSY_STATES and not _APPLY.is_set():     # never over an install that runs
            STATE.update(state="check_failed", error=str(exc), detail=getattr(exc, "detail", ""), checked_at=time.time())


def _busy() -> str:
    try:
        from .auto_edit import app_busy
        return app_busy()
    except Exception:
        return ""


def start_apply() -> None:
    """Download and install the build found by check() (in the background), then switch to it."""
    with _LOCK:
        if STATE["state"] in _BUSY_STATES or _APPLY.is_set():
            return
        m = STATE.get("found")
        if not m or STATE["state"] not in ("checked", "error"):
            raise UpdateError("Press Check for updates first.")
        if not m.get("newer"):
            raise UpdateError("This is already the newest version.")
        if not m.get("same_runtime"):
            raise UpdateError("This update needs the full installer this time (Python or its libraries changed).")
        busy = _busy()
        if busy:
            raise UpdateError(busy)
        STATE.update(state="downloading", error="", detail="", done=0, total=int(m["size"]), target="")
        _APPLY.set()
    threading.Thread(target=_apply, args=(dict(m),), daemon=True, name="update").start()


def _apply(m: dict) -> None:
    try:
        z = _download(m)
        with _LOCK:
            STATE.update(state="preparing")
        target = _prepare(z, m)
        with _LOCK:
            STATE.update(state="switching", target=str(target))
        _switch(target)
    except UpdateError as exc:
        with _LOCK:
            STATE.update(state="error", error=str(exc), detail=exc.detail)
    except Exception as exc:
        with _LOCK:
            STATE.update(state="error", error="The update could not be installed.", detail=f"{type(exc).__name__}: {exc}")
    finally:
        _APPLY.clear()


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _download(m: dict) -> Path:
    d = DATA / "updates"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.iterdir():                      # earlier downloads: only the one being fetched is kept
        if old.is_file() and old.name not in (m["file"], m["file"] + ".part"):
            try:
                old.unlink()
            except OSError:
                pass
    final = d / m["file"]
    if final.is_file() and final.stat().st_size == m["size"] and _sha256(final) == m["sha256"]:
        STATE["done"] = m["size"]
        return final
    try:
        free = shutil.disk_usage(INSTALL.parent).free
    except OSError:
        free = 1 << 40
    if free < 3 * m["size"] + 300 * 2 ** 20:
        raise UpdateError("Not enough free space on the disk with MediaEngine for the update.")
    part = d / (m["file"] + ".part")
    h, n = hashlib.sha256(), 0
    try:
        with _get(base_url() + m["file"] + "?sha=" + m["sha256"][:16], 60) as r, open(part, "wb") as out:   # (never a cached older ZIP)
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                n += len(b)
                if n > m["size"]:
                    raise UpdateError("The download is bigger than announced, so it is not used.")
                h.update(b)
                out.write(b)
                STATE["done"] = n
    except UpdateError:
        part.unlink(missing_ok=True)
        raise
    except urllib.error.HTTPError as exc:
        part.unlink(missing_ok=True)
        if exc.code == 404:
            raise UpdateError("A newer version was published in the meantime. Press Check for updates again.")
        raise UpdateError("GitHub answered with an error. Try again later.", f"HTTP {exc.code}")
    except Exception as exc:
        part.unlink(missing_ok=True)
        raise UpdateError("The download was interrupted. Check the internet connection and try again.", f"{type(exc).__name__}: {exc}")
    if n != m["size"] or h.hexdigest() != m["sha256"]:
        part.unlink(missing_ok=True)
        raise UpdateError("The downloaded file is damaged (its checksum differs), so it is not used. Try again.")
    os.replace(part, final)
    return final


def _complete(folder: Path) -> bool:
    return all((folder / n).is_file() for n in REQUIRED) and (folder / ".venv").is_dir()


def _link_tree(src: Path, dst: Path) -> tuple[int, int]:
    """The runtime of this build into the new folder: hard links (no second copy on the disk), a copy where the
    disk cannot link (FAT/exFAT, a network drive)."""
    linked = copied = 0
    for dirpath, _dirs, files in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        out = dst if rel == "." else dst / rel
        out.mkdir(parents=True, exist_ok=True)
        for f in files:
            s, t = Path(dirpath) / f, out / f
            try:
                os.link(s, t)
                linked += 1
            except OSError:
                try:                              # copied instead: it must fit (and leave room for the program)
                    free = shutil.disk_usage(dst).free
                except OSError:
                    free = 1 << 40
                if free < s.stat().st_size + 200 * 2 ** 20:
                    raise UpdateError("Not enough free space on the disk with MediaEngine for the update.")
                shutil.copy2(s, t)
                copied += 1
    return linked, copied


def _rename_patiently(src: Path, dst: Path) -> None:
    """A folder full of new files can be held for a moment by a virus scanner: try again for ~30 s."""
    for k in range(16):
        try:
            os.rename(src, dst)
            return
        except PermissionError:
            if k == 15:
                raise
            time.sleep(min(4.0, 0.5 * (k + 1)))


def _prepare(zip_path: Path, m: dict) -> Path:
    parent = INSTALL.parent
    target = parent / m["pkg"]
    if target.exists():
        if _complete(target) and runtime_id(target) == runtime_id(INSTALL):
            return target                        # already here (an earlier update, or its Setup)
        raise UpdateError("A folder with the new version's name is already there, but it is not a complete MediaEngine. "
                          "Remove that folder or install the new version with its Setup.", str(target))
    for left in parent.glob(".update-MediaEngine-*"):
        shutil.rmtree(left, ignore_errors=True)   # earlier attempts that were interrupted (one install at a time)
    # not "MediaEngine-...": never listed as a version while unfinished; unique: a folder a scanner still holds
    # from an earlier attempt is never in the way
    stage = parent / f".update-MediaEngine-{os.getpid() % 10000}-{int(time.time() * 1000) % 10 ** 6}"   # (short: long runtime paths)
    try:
        stage.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as zf:
            total = 0
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                parts = [p for p in name.split("/") if p not in ("", ".")]
                if (not parts or name.startswith("/") or ".." in parts or ":" in name
                        or parts[0].lower() == ".venv"):
                    raise UpdateError("The update contains a file outside its folder, so it is not used.")
                total += max(0, int(info.file_size))
                if total > MAX_UNPACKED:
                    raise UpdateError("The update is much bigger than expected, so it is not used.")
            zf.extractall(stage)
        missing = [n for n in REQUIRED if not (stage / n).is_file()]
        if missing:
            raise UpdateError("The update is incomplete, so it is not used.", ", ".join(missing))
        if runtime_id(stage) != runtime_id(INSTALL):
            raise UpdateError("This update needs the full installer this time (Python or its libraries changed).")
        try:
            same_port = (stage / "port.txt").read_text(encoding="utf-8-sig").strip() == (INSTALL / "port.txt").read_text(encoding="utf-8-sig").strip()
        except OSError:
            same_port = False
        if not same_port:
            raise UpdateError("The update is for another kind of MediaEngine, so it is not used.")
        _link_tree(INSTALL / ".venv", stage / ".venv")
        _rename_patiently(stage, target)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return target


def _launcher_status() -> tuple[float, str]:
    p = DATA / "update_status.json"           # what the launchers of the builds last did (launcher_v2.write_status)
    try:
        return p.stat().st_mtime, str(json.loads(p.read_text(encoding="utf-8")).get("status") or "")
    except Exception:
        return 0.0, ""


def _switch(target: Path) -> None:
    """The usual switch to another version: its launcher asks this one to quit and starts itself. The folder just
    checked is started directly (not looked up among the versions this build knows: a newer build may hold a file
    this one has never heard of). Still running after SWITCH_WAIT_S: the switch did not happen - say why."""
    if os.name != "nt" or os.environ.get("MEDIAENGINE_UPDATE_NO_SWITCH") == "1":
        with _LOCK:
            STATE.update(state="ready")
        return
    busy = _busy()
    if busy:                     # e.g. a reel was started meanwhile: the folder is ready, Update now switches later
        raise UpdateError(busy, str(target))
    from .auto_edit import start_build_folder
    before, _ = _launcher_status()
    start_build_folder(target)
    end = time.time() + SWITCH_WAIT_S
    while time.time() < end:     # normally this process is stopped by the new build before the loop ends
        time.sleep(1)
        at, st = _launcher_status()
        if at > before and st in ("switch_refused_busy", "switch_failed_still_running"):
            break
    at, st = _launcher_status()
    if at > before and st == "switch_refused_busy":
        raise UpdateError("Work started in the meantime. The new version is ready: press Update now again when the work has finished.",
                          str(target))
    raise UpdateError("The new version is ready in its folder, but it did not take over. Press Update now to try again.",
                      f"{target} ({st or 'no answer from its launcher'})")
