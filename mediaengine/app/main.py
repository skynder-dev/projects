from __future__ import annotations

import os, re, shutil, subprocess, sys, threading, time, webbrowser
from pathlib import Path

from archivist.config import HOME, VERSION, ensure_dirs
from archivist.platform_adapter import detach_from_legacy_console_if_needed, install_launchers, set_background_priority

HOST, PORT = "127.0.0.1", 8765


def _launcher_version_from_source(source):
    m=re.search(r'^LAUNCHER_VERSION\\s*=\\s*["\\\']([^"\\\']+)["\\\']',source,re.MULTILINE)
    return m.group(1) if m else '0.0.0'

def _version_tuple(value):
    out=[]
    for part in str(value).split('.'):
        digits=''.join(c for c in part if c.isdigit())
        out.append(int(digits or 0))
    return tuple((out+[0,0,0])[:3])

def sync_packaged_launcher():
    packaged=Path(__file__).resolve().parent/'archivist'/'launcher_v2.py'
    target=HOME/'launcher.py'
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
        startup_headers={"Host":"127.0.0.1:8765"}
        for path in ("/api/ping", "/", "/media", "/social", "/devices", "/cloud", "/activity", "/settings/connections", "/library", "/search", "/convert", "/jobs", "/best", "/about"):
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


def main():
    ensure_dirs(); set_background_priority(); install_launchers(HOME); sync_packaged_launcher()
    if detach_from_legacy_console_if_needed(HOME): return
    from archivist.service import start_workers
    from archivist.converter import recover_convert_jobs
    from archivist.watchdog import start_watchdog
    from archivist.web import create_app
    start_workers(); recover_convert_jobs(); start_watchdog(); app=create_app(); startup_self_check(app); url=f"http://{HOST}:{PORT}/"
    from archivist.diagnostics import run_once_and_report
    threading.Thread(target=lambda:(time.sleep(2.0),run_once_and_report()),daemon=True).start()
    suppress=os.environ.get("ARCHIVIST_SUPPRESS_BROWSER")=="1" or "--no-browser" in sys.argv
    if not suppress:
        threading.Thread(target=lambda:(time.sleep(1.0),webbrowser.open(url)),daemon=True).start()
    app.run(host=HOST,port=PORT,debug=False,threaded=True,use_reloader=False)

if __name__=="__main__": main()
