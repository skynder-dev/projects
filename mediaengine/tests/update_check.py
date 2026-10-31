"""The in-app update (the "Update" button) end to end on this PC, without GitHub: a server on 127.0.0.1 publishes what
tools/make_update_bundle.py makes from a "next build", the app's own pages check, download, verify and install it.

  python tests/update_check.py <work_dir>

Covers: found / newest / needs the full installer / nothing published / no connection / turned off / not an installed
build; the new build folder next to the old one with the runtime hard-linked (not copied), the old folder untouched;
a damaged download, a ZIP with a path outside its folder and a size that lies are refused and leave nothing behind;
the pages in Russian. The switch itself (the new build's launcher takes over) is Windows-only: Windows CI.
"""
from __future__ import annotations

import http.server, json, os, re, shutil, socketserver, subprocess, sys, threading, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18781


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    # an installed build (the one running) and the next build as CI makes it
    base = work / "medeng"
    cur = base / "MediaEngine-3.13.0-rc1-b100"
    nxt_src = work / "ci" / "MediaEngine-3.13.0-rc1-b200"

    def make_build(d: Path, main_text: str, runtime: str = "rt1"):
        (d / "app" / "archivist").mkdir(parents=True)
        (d / ".venv" / "Scripts").mkdir(parents=True); (d / ".venv" / "Lib" / "site-packages" / "pkg").mkdir(parents=True)
        (d / ".venv" / "Scripts" / "python.exe").write_bytes(b"MZ runtime " * 1000)
        (d / ".venv" / "Lib" / "site-packages" / "pkg" / "m.py").write_text("x = 1\n")
        (d / "app" / "main.py").write_text(main_text)
        (d / "app" / "archivist" / "auto_edit.py").write_text(
            'WHATS_NEW_ITEMS = [\n    ("2026-10-01", "Old thing."),\n    ("2099-01-01", "A new thing."),\n]\n')
        (d / "app" / "archivist" / "auto_edit_ru.py").write_text('PHRASES = {\n    "A new thing.": "Новая вещь.",\n}\n')
        for n, t in (("port.txt", "8775"), ("runtime.txt", runtime + "\n"), ("version.txt", "3.13.0-rc1"), ("launcher.py", "# launcher\n"),
                     ("BUILD.txt", "MediaEngine 3.13.0-rc1\ncommit abc\nbuilt 2026-10-18\n"), ("Start MediaEngine.vbs", "' vbs\n"),
                     ("README.txt", "readme\n")):
            (d / n).write_text(t, encoding="utf-8")
    make_build(cur, "OLD\n")
    make_build(nxt_src, "NEW\n")
    serve = work / "srv"; serve.mkdir()

    def bundle(src: Path, name: str = "", run_url: str = "https://github.com/skynder-dev/projects/actions/runs/1"):
        for f in serve.iterdir():
            f.unlink()
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_update_bundle.py"), str(src), str(serve)]
                           + (["--name", name] if name else []) + ["--run-url", run_url], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stderr)
        return json.loads((serve / "latest.json").read_text(encoding="utf-8"))

    man = bundle(nxt_src)
    with zipfile.ZipFile(serve / man["file"]) as zf:
        names = zf.namelist()
    check("bundle: the program without the runtime", "app/main.py" in names and not any(n.startswith(".venv") for n in names)
          and man["runtime"] == "rt1" and man["pkg"] == "MediaEngine-3.13.0-rc1-b200", (names[:20], man))
    check("bundle: what is new, with Russian", {"since": "2099-01-01", "en": "A new thing.", "ru": "Новая вещь."} in man["notes"], man["notes"])

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve), **kw)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"

    os.environ.update(ARCHIVIST_HOME=str(work / "home"), ARCHIVIST_PORT=str(PORT), MEDIAENGINE_NO_BROWSER="1",
                      MEDIAENGINE_UPDATE_URL=url, MEDIAENGINE_UPDATE_NO_SWITCH="1")
    os.environ.pop("MEDIAENGINE_UPDATES", None)
    os.environ.pop("MEDIAENGINE_AUTO_UPDATE", None)      # (CI turns them off for the running builds)
    sys.path.insert(0, str(ROOT / "app"))
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from archivist import updater as up
    from archivist.web import create_app
    up.INSTALL = cur; up.DATA = work / "home" / "data"
    app = create_app(); c = app.test_client()
    H = {"Host": f"127.0.0.1:{PORT}", "Origin": f"http://127.0.0.1:{PORT}"}

    def reset():
        up.STATE.update(state="idle", error="", detail="", found=None, done=0, total=0, target="")

    def text(path="/auto/update"):
        r = c.get(path, headers=H)
        return r.status_code, r.get_data(as_text=True)

    def wait_done(sec=60):
        end = time.time() + sec
        while time.time() < end:
            s = c.get("/api/update-status", headers=H).get_json()
            if s["state"] not in ("downloading", "preparing", "switching"):
                return s
            time.sleep(0.2)
        return s

    # automatic updates: on by default, the switch on the page, one tick installs a newer build of the same runtime
    code, page = text()
    check("automatic updates: on by default, said on the page", up.auto_on() and "Automatic updates are on." in page
          and "Turn automatic updates off" in page and up.STATE["state"] == "idle", page[-1500:])
    c.post("/auto/update/auto", data={"on": "0"}, headers=H)
    code, page = text()
    check("automatic updates: turned off on the page (and remembered)", not up.auto_on() and "Automatic updates are off." in page
          and (up.DATA / "update_auto.json").is_file() and up.auto_tick() == "off" and up.STATE["state"] == "idle", page[-1500:])
    os.environ["MEDIAENGINE_UPDATES"] = "off"
    c.post("/auto/update/auto", data={"on": "1"}, headers=H)
    check("automatic updates: nothing happens where updates are turned off", up.auto_tick() == "cannot" and up.STATE["state"] == "idle")
    os.environ.pop("MEDIAENGINE_UPDATES")
    import archivist.updater as _upm
    real_busy = _upm._busy
    _upm._busy = lambda: "A reel is being made. Switch when it is ready."
    r1 = up.auto_tick()
    _upm._busy = real_busy
    check("automatic updates: work running - not installed, tried again later", r1 == "busy" and up.STATE["state"] == "checked"
          and not (base / "MediaEngine-3.13.0-rc1-b200").exists(), (r1, up.STATE))
    os.environ["MEDIAENGINE_UPDATE_URL"] = "http://127.0.0.1:9/"
    reset()
    r2 = up.auto_tick()
    check("automatic updates: no answer from GitHub changes nothing on the page", r2 == "check_failed" and up.STATE["state"] == "idle"
          and "No connection" in up.AUTO["detail"], (r2, up.STATE, up.AUTO))
    os.environ["MEDIAENGINE_UPDATE_URL"] = url
    code, page = text()
    check("automatic updates: the last check is said on the page", "Last automatic check:" in page
          and "No answer from GitHub: it tries again in a few minutes." in page, page[-1500:])
    reset()
    r3 = up.auto_tick()
    s = wait_done()
    auto_tgt = base / "MediaEngine-3.13.0-rc1-b200"
    check("automatic updates: a newer build of the same runtime is installed by itself", r3 == "started" and s["state"] == "ready"
          and (auto_tgt / "app" / "main.py").read_text() == "NEW\n", (r3, s))
    log = (up.DATA / "logs" / "update_auto.log").read_text(encoding="utf-8")
    check("automatic updates: each attempt in its log", all(w in log for w in ("busy", "check_failed", "started")), log)
    shutil.rmtree(auto_tgt, ignore_errors=True)
    reset()
    up.set_auto(False)
    code, page = text()
    check("page: nothing is asked online before the button", code == 200 and "Check for updates" in page and up.STATE["state"] == "idle", code)
    nav = c.get("/auto", headers=H).get_data(as_text=True)
    check("top bar: an Update button only in an installed build", "action='/auto/update/check'" not in nav)   # the source tree here

    # found -> Update now -> new folder next to the old one, runtime hard-linked
    r = c.post("/auto/update/check", headers=H)
    code, page = text()
    check("check: a newer version is found", r.status_code == 302 and "A newer version is ready:" in page and "3.13.0-rc1 b200" in page
          and "A new thing." in page and "Old thing." not in page and "Update now" in page, page[-1500:])
    r = c.post("/auto/update/apply", headers=H)
    code, page = text()
    check("apply: the progress page", r.status_code == 302 and code == 200 and ("Updating to" in page or up.STATE["state"] == "ready"), up.STATE)
    s = wait_done()
    tgt = base / "MediaEngine-3.13.0-rc1-b200"
    venv_old, venv_new = cur / ".venv" / "Scripts" / "python.exe", tgt / ".venv" / "Scripts" / "python.exe"
    check("apply: the new build is installed next to the old one", s["state"] == "ready" and (tgt / "app" / "main.py").read_text() == "NEW\n"
          and (cur / "app" / "main.py").read_text() == "OLD\n", (s, up.STATE))
    check("apply: the runtime is reused (hard links, no second copy)", venv_new.is_file() and os.stat(venv_new).st_ino == os.stat(venv_old).st_ino
          and (tgt / ".venv" / "Lib" / "site-packages" / "pkg" / "m.py").is_file())
    check("apply: nothing half-made is left", not list(base.glob(".update-*")) and (work / "home" / "data" / "updates" / man["file"]).is_file())
    from archivist import auto_edit as ae
    with_rt = ae.RELEASE_ENTRIES
    check("the new folder counts as a MediaEngine version (Check this PC lists it)", all(x.name.lower() in with_rt for x in tgt.iterdir()),
          [x.name for x in tgt.iterdir()])
    # a second Update now with the folder already there: it is reused (e.g. the switch was refused by a reel)
    reset(); c.post("/auto/update/check", headers=H); c.post("/auto/update/apply", headers=H); s = wait_done()
    check("apply again: the finished folder is reused", s["state"] == "ready" and (tgt / "app" / "main.py").read_text() == "NEW\n", s)
    listed = {b["name"]: b for b in ae.other_builds(cur)}
    whole = sum(f.stat().st_size for f in tgt.rglob("*") if f.is_file())
    own = whole - sum(f.stat().st_size for f in (tgt / ".venv").rglob("*") if f.is_file())
    check("Check this PC: the new build is listed with only its own bytes (the shared runtime is not freed by removing it)",
          tgt.name in listed and listed[tgt.name]["bytes"] == own < whole, (listed.get(tgt.name), own, whole))
    shutil.rmtree(tgt)

    # one install at a time: a check that ends while Update now runs does not reset it; Quit / switches wait for it
    reset(); c.post("/auto/update/check", headers=H)
    up._APPLY.set()
    try:
        r = c.post("/auto/update/check", headers=H)
        check("a check while an install runs leaves it alone", up.STATE["state"] == "checked" and r.status_code == 302)
        try:
            up.check(); raced = False
        except up.UpdateError as exc:
            raced = "being installed" in str(exc)
        check("check() refuses while an install thread is alive", raced)
        up.start_apply()
        check("Update now twice: one install thread", up.STATE["state"] == "checked")
    finally:
        up._APPLY.clear()
    from archivist import web as _web
    up.STATE["state"] = "downloading"
    check("Quit / switch / restart wait while an update downloads", _web.busy_reason() == "An update is being installed. Wait a minute."
          and ae.app_busy() == "An update is being installed. Wait a minute.")
    up.STATE["state"] = "switching"
    check("...but not its own last step (the switch)", _web.busy_reason() == "" and ae.app_busy() == "")
    vk = ["3.13.0-alpha1", "3.13.0-beta1", "3.13.0-beta2", "3.13.0-rc1", "3.13.0-rc2", "3.13.0"]
    check("version order with alpha / beta numbers", sorted(reversed(vk), key=up.version_key) == vk)
    # an interrupted earlier attempt (a folder a scanner held) is cleaned and never in the way
    (base / ".update-MediaEngine-3.13.0-rc1-b200-1-1").mkdir(); (base / ".update-MediaEngine-3.13.0-rc1-b200-1-1" / "x").write_text("x")
    reset(); c.post("/auto/update/check", headers=H); c.post("/auto/update/apply", headers=H); s = wait_done()
    check("leftovers of an interrupted attempt are cleaned", s["state"] == "ready" and not list(base.glob(".update-*")), (s, list(base.glob(".update-*"))))
    shutil.rmtree(tgt)

    # newest already / needs the full installer
    bundle(nxt_src, name="MediaEngine-3.13.0-rc1-b050"); reset(); c.post("/auto/update/check", headers=H)
    check("an older build on GitHub: this is the newest", "This is the newest version." in text()[1])
    r = c.post("/auto/update/apply", headers=H)
    check("an older build is never installed", r.status_code == 400 and "This is already the newest version." in r.get_data(as_text=True))
    make_build(work / "ci2" / "MediaEngine-3.13.0-rc1-b300", "NEWER\n", runtime="rt2")
    bundle(work / "ci2" / "MediaEngine-3.13.0-rc1-b300"); reset(); c.post("/auto/update/check", headers=H)
    page = text()[1]
    check("another runtime: the full installer is needed, with its page", "needs the full installer" in page
          and "https://github.com/skynder-dev/projects/actions/runs/1" in page, page[-1200:])
    r = c.post("/auto/update/apply", headers=H)
    check("another runtime: nothing is installed", r.status_code == 400 and not (base / "MediaEngine-3.13.0-rc1-b300").exists())

    # a damaged download, a path outside the folder, a size that lies: refused, nothing left
    man = bundle(nxt_src); reset(); c.post("/auto/update/check", headers=H)
    zp = serve / man["file"]; data = bytearray(zp.read_bytes()); data[len(data) // 2] ^= 0xFF; zp.write_bytes(bytes(data))
    shutil.rmtree(work / "home" / "data" / "updates", ignore_errors=True)
    c.post("/auto/update/apply", headers=H); s = wait_done()
    check("a damaged download is refused", s["state"] == "error" and "checksum differs" in s["error"] and not tgt.exists()
          and not list((work / "home" / "data" / "updates").glob("*")), s)
    evil = work / "evil"; shutil.copytree(nxt_src, evil / "MediaEngine-3.13.0-rc1-b200")
    man = bundle(evil / "MediaEngine-3.13.0-rc1-b200")
    zp = serve / man["file"]
    with zipfile.ZipFile(zp, "a") as zf:
        zf.writestr("../escaped.txt", "x")
    import hashlib
    raw = zp.read_bytes(); man.update(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    (serve / "latest.json").write_text(json.dumps(man), encoding="utf-8")
    reset(); c.post("/auto/update/check", headers=H); c.post("/auto/update/apply", headers=H); s = wait_done()
    check("a file outside its folder is refused", s["state"] == "error" and "outside its folder" in s["error"] and not tgt.exists()
          and not (base / "escaped.txt").exists() and not list(base.glob(".update-*")), s)
    man = bundle(nxt_src); man["size"] = man["size"] - 100
    (serve / "latest.json").write_text(json.dumps(man), encoding="utf-8")
    shutil.rmtree(work / "home" / "data" / "updates", ignore_errors=True)
    reset(); c.post("/auto/update/check", headers=H); c.post("/auto/update/apply", headers=H); s = wait_done()
    check("a download bigger than announced is refused", s["state"] == "error" and "bigger than announced" in s["error"] and not tgt.exists(), s)

    # nothing published / no connection / turned off / not an installed build / a foreign address
    for f in serve.iterdir():
        f.unlink()
    reset(); c.post("/auto/update/check", headers=H)
    check("nothing published yet", "No update has been published yet." in text()[1])
    os.environ["MEDIAENGINE_UPDATE_URL"] = "http://127.0.0.1:9/"
    reset(); c.post("/auto/update/check", headers=H)
    check("no connection", "No connection to GitHub." in text()[1])
    os.environ["MEDIAENGINE_UPDATE_URL"] = "https://example.com/"
    reset(); c.post("/auto/update/check", headers=H)
    check("the address can only be changed to this PC", "may only point at this PC" in text()[1])
    os.environ["MEDIAENGINE_UPDATE_URL"] = url
    os.environ["MEDIAENGINE_UPDATES"] = "off"; reset(); c.post("/auto/update/check", headers=H)
    check("turned off", "Updates are turned off here." in text()[1]); os.environ.pop("MEDIAENGINE_UPDATES")
    (cur / "runtime.txt").rename(cur / "runtime.bak"); reset()
    check("a build without runtime.txt (before the button existed): install once with Setup", "Install the new version once with its Setup." in text()[1])
    (cur / "runtime.bak").rename(cur / "runtime.txt")
    up.INSTALL = work / "not-installed"; (work / "not-installed").mkdir(); reset()
    check("not an installed build", "Only an installed MediaEngine" in text()[1]); up.INSTALL = cur

    # every state of the page in Russian: no English left (names stay)
    from archivist import i18n
    i18n.set_ui_language("ru")
    keep = {"MediaEngine", "Social", "Lab", "GitHub", "logs", "Setup", "ZIP", "Python", "MB", "KB", "rc", "MEDIAENGINE_UPDATE_URL", "b200", "b300", "HTTP"}
    left = []
    up.set_auto(True)          # the automatic-updates card with its last check, in every state below
    up.AUTO.update(last=time.time(), result="busy", detail="")
    man = bundle(nxt_src)
    states = [("idle", None), ("checked-new", "b200"), ("checked-runtime", "b300"), ("checked-newest", "b050"), ("check_failed", ""),
              ("error", "")]
    for label, which in states:
        reset()
        if label.startswith("checked"):
            if which == "b300":
                bundle(work / "ci2" / "MediaEngine-3.13.0-rc1-b300")
            elif which == "b050":
                bundle(nxt_src, name="MediaEngine-3.13.0-rc1-b050")
            else:
                bundle(nxt_src)
            c.post("/auto/update/check", headers=H)
        elif label == "check_failed":
            up.STATE.update(state="check_failed", error="No connection to GitHub. Check the internet connection and try again.", detail="URLError: x")
        elif label == "error":
            bundle(nxt_src); c.post("/auto/update/check", headers=H)
            up.STATE.update(state="error", error="The downloaded file is damaged (its checksum differs), so it is not used. Try again.")
        for st in ([None, "downloading"] if label == "checked-new" else [None]):
            if st:
                up.STATE.update(state=st, done=10, total=100)
            html_ = text()[1]
            body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", html_, flags=re.S)
            body = re.sub(r"<([a-z0-9]+)\b[^>]*translate=['\"]no['\"][^>]*>.*?</\1>", " ", body, flags=re.S)
            body = re.sub(r"""<(?:[^>"']|"[^"]*"|'[^']*')+>""", " ", body)
            words = {w for w in re.findall(r"[A-Za-z][A-Za-z_]+", body) if w not in keep}
            nav_words = {"Restart", "Quit", "Update", "English"}       # the top bar is checked by i18n_coverage
            words -= nav_words
            if words:
                left.append((label, st, sorted(words)[:20]))
    check("Russian: every state of the update page", not left, left)
    i18n.set_ui_language("en")
    srv.shutdown()
    print(json.dumps({"passed": sum(checks), "total": len(checks)}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
