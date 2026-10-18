from __future__ import annotations

import os, re, shutil, subprocess, sys, threading, time, webbrowser
from pathlib import Path

from archivist.config import APP_PORT, HOME, INSTALL, SIDE_BY_SIDE, VERSION, ensure_dirs
from archivist.platform_adapter import detach_from_legacy_console_if_needed, install_launchers, set_background_priority

HOST, PORT = "127.0.0.1", APP_PORT


def _launcher_version_from_source(source):
    m=re.search(r'^LAUNCHER_VERSION\s*=\s*["\']([^"\']+)["\']',source,re.MULTILINE)
    return m.group(1) if m else '0.0.0'

def _version_tuple(value):
    out=[]
    for part in str(value).split('.'):
        digits=''.join(c for c in part if c.isdigit())
        out.append(int(digits or 0))
    return tuple((out+[0,0,0])[:3])

def sync_packaged_launcher():
    packaged=Path(__file__).resolve().parent/'archivist'/'launcher_v2.py'
    target=INSTALL/'launcher.py'
    if not packaged.exists():
        raise RuntimeError('Packaged launcher is missing')
    source=packaged.read_text(encoding='utf-8')
    compile(source,str(packaged),'exec')
    packaged_version=_launcher_version_from_source(source)
    current_source=''
    if target.exists():
        current_source=target.read_text(encoding='utf-8',errors='replace')
    current_version=_launcher_version_from_source(current_source)
    if _version_tuple(current_version)>=_version_tuple(packaged_version):
        return {'updated':False,'version':current_version}
    backup_dir=HOME/'data'/'launcher_backups'
    backup_dir.mkdir(parents=True,exist_ok=True)
    if target.exists():
        shutil.copy2(target,backup_dir/f'launcher_{current_version or "unknown"}.py')
    temp=target.with_name('launcher.py.__new__')
    temp.write_text(source,encoding='utf-8')
    compile(temp.read_text(encoding='utf-8'),str(temp),'exec')
    os.replace(temp,target)
    return {'updated':True,'from_version':current_version,'version':packaged_version}


def startup_self_check(app):
    """Render critical routes before opening the HTTP server.

    This catches runtime-only template/f-string failures that a simple /api/ping
    process check cannot detect. If a Media Brain clip exists, its real clip page
    is rendered too. Any failure makes startup exit so the existing updater can
    restore the previous backup instead of accepting a partially broken release.
    """
    with app.test_client() as client:
        startup_headers={"Host":f"127.0.0.1:{PORT}"}
        for path in ("/api/ping", "/", "/media", "/social", "/devices", "/cloud", "/activity", "/settings/connections", "/library", "/search", "/convert", "/jobs", "/best", "/about", "/auto"):
            response = client.get(path,headers=startup_headers)
            if response.status_code != 200:
                raise RuntimeError(f"Startup self-check failed: {path} -> HTTP {response.status_code}")
        # Also prove real Windows FFmpeg thumbnail extraction on the bundled
        # fixture. This catches preview regressions before an update is accepted.
        from archivist.media import make_thumbnail
        fixture = Path(__file__).resolve().parent / "archivist" / "assets" / "browser_fixture_h264.mp4"
        probe_thumb = HOME / "data" / "temp" / "startup_thumb_probe.jpg"
        if fixture.exists():
            probe_thumb.unlink(missing_ok=True)
            if not make_thumbnail(fixture, "video", probe_thumb):
                raise RuntimeError("Startup self-check failed: bundled video thumbnail extraction")
            probe_thumb.unlink(missing_ok=True)
        from archivist.media_brain import best_clips
        clips = best_clips(1)
        if clips:
            clip_id = int(clips[0]["id"])
            path = f"/clip/{clip_id}?back=best"
            response = client.get(path,headers=startup_headers)
            if response.status_code != 200:
                raise RuntimeError(f"Startup self-check failed: {path} -> HTTP {response.status_code}")


def _self_check_known_good(app):
    """The start-up check guards a NEW build (a broken release is refused and the previous one starts). A build that
    has passed it once on this PC is not refused later because of something in the owner's data (one odd Library row
    made a page fail): it starts and says so in the log - otherwise no build at all would start on that data."""
    from archivist.config import BUILD, DATA
    mark = DATA / "startup_checked" / re.sub(r"[^\w.-]", "_", f"{VERSION}-{BUILD}" if BUILD else VERSION)
    try:
        startup_self_check(app)
    except Exception as exc:
        if not mark.is_file():
            raise
        print(f"Startup self-check failed, but this build started on this PC before - starting anyway: {exc}", file=sys.stderr)
        return
    try:
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    except OSError:
        pass


def _bind_fails():
    import socket
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        if os.name!="nt":
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)   # Linux: still refuses a port someone listens on
        s.bind((HOST,PORT)); return False
    except OSError:
        return True
    finally:
        s.close()


def _ping_ok():
    import urllib.request
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f"http://{HOST}:{PORT}/api/ping",timeout=.5) as r: return r.status==200
    except Exception:
        return False


def port_taken(wait_s=20.0):
    """True if another copy of the app (or another program) holds our port. A port that is only briefly busy
    (the previous copy is still closing during a restart) is waited for."""
    end=time.time()+wait_s
    while True:
        if not _bind_fails(): return False
        if _ping_ok() or time.time()>=end: return True
        time.sleep(.5)


_INSTANCE: list = []


def hold_instance_lock(wait_s: float = 20.0) -> bool:
    """One app per port (and so per data folder) from the very start to the end of the process. The port alone was
    not enough: a second copy started while the first was still checking itself (before it took the port) touched the
    same database - resumed the same waiting builds, marked the other's running build interrupted (review
    2026-10-17). A copy that is closing (a restart) is waited for; a running one wins."""
    end = time.time() + wait_s
    while True:
        if os.name == "nt":
            import ctypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.CreateMutexW.restype = ctypes.c_void_p
            h = k32.CreateMutexW(None, False, f"Local\\MediaEngineApp-{PORT}")
            if not h:
                return True                      # cannot tell: as before (the port still decides)
            if ctypes.get_last_error() != 183:   # not ERROR_ALREADY_EXISTS: ours for the life of this process
                _INSTANCE.append(h)
                return True
            k32.CloseHandle(ctypes.c_void_p(h))
        else:
            try:
                import fcntl
                f = open(HOME / f".mediaengine-app-{PORT}.lock", "w")
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    _INSTANCE.append(f)
                    return True
                except OSError:
                    f.close()
            except (ImportError, OSError):
                return True
        if _ping_ok() or time.time() >= end:
            return False
        time.sleep(0.5)


def main():
    import faulthandler
    try:
        faulthandler.enable()          # a hard crash leaves its trace in the console log (the launcher keeps it)
    except Exception:
        pass
    ensure_dirs(); set_background_priority(); sync_packaged_launcher()
    if detach_from_legacy_console_if_needed(HOME): return
    if port_taken():
        # Never start a second set of workers on the same database: the running copy keeps serving.
        raise SystemExit(f"Port {PORT} is already in use (MediaEngine already running?)")
    if not hold_instance_lock():
        raise SystemExit("MediaEngine is already starting or running")
    try:     # a copy of the database and settings before a different build opens them (it may change them)
        from archivist.backup import before_new_build, start_daily_in_background
        from archivist.config import BUILD
        before_new_build(f"{VERSION}-{BUILD}" if BUILD else VERSION)
        start_daily_in_background()     # integrity check + daily copy, after the start
    except Exception:
        pass
    try:
        import logging, mimetypes
        # one line per request (the pages ask for progress every second) filled the console log: errors only
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        # some Windows PCs register .js as text/plain; with nosniff the browser would refuse the page script
        mimetypes.add_type("text/javascript", ".js")
    except Exception:
        pass
    from archivist.service import start_workers
    from archivist.converter import recover_convert_jobs
    from archivist.watchdog import start_watchdog
    from archivist.web import create_app
    try:
        from archivist.clip_export import sweep_exports
        sweep_exports()                   # empty reserved names / .part files of renders the app was closed during
    except Exception:
        pass
    start_workers(); recover_convert_jobs(); start_watchdog(); app=create_app(); _self_check_known_good(app); url=f"http://{HOST}:{PORT}/"+("auto" if SIDE_BY_SIDE else "")
    # (the old Remote Lab diagnostics upload is gone: MediaEngine sends nothing anywhere)
    suppress=os.environ.get("ARCHIVIST_SUPPRESS_BROWSER")=="1" or "--no-browser" in sys.argv
    if not suppress:
        threading.Thread(target=lambda:(time.sleep(1.0),webbrowser.open(url)),daemon=True).start()
    def _shortcuts_when_up():
        # the desktop / Start-menu shortcuts follow this build only once it really serves: a build that fails its
        # start (after a switch) must not leave both shortcuts pointing at it (review 2026-10-17)
        for _ in range(240):
            if _ping_ok():
                try: install_launchers(INSTALL)
                except Exception: pass
                return
            time.sleep(0.5)
    threading.Thread(target=_shortcuts_when_up,daemon=True,name="shortcuts").start()
    try:     # the icon in the notification area: Open / Quit (closing the window does not stop MediaEngine)
        from archivist import tray
        from archivist.config import BUILD
        from archivist.i18n import ui_language
        from archivist.web import activity_line, busy_reason, quit_soon
        tray.start(url=url, icon=INSTALL/"MediaEngine.ico", version=f"{VERSION} {BUILD}".strip(),
                   ru=lambda: ui_language()=="ru", status=activity_line, busy=busy_reason, quit_app=quit_soon,
                   hint_flag=HOME/"data"/"tray_hint_shown.txt")
    except Exception:
        pass
    if os.name=="nt":
        # Windows SO_REUSEADDR lets a second copy bind the same port silently (two servers, one database).
        # Without it a second start fails cleanly and the launcher just opens the running one.
        import werkzeug.serving
        werkzeug.serving.BaseWSGIServer.allow_reuse_address=False
    app.run(host=HOST,port=PORT,debug=False,threaded=True,use_reloader=False)

if __name__=="__main__": main()
