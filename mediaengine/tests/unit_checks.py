"""Small, fast checks of helper rules (no video work).

  python tests/unit_checks.py <work_dir>
"""
from __future__ import annotations

import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import auto_edit as ae
    import importlib.util
    spec = importlib.util.spec_from_file_location("launcher_v2", ROOT / "app" / "archivist" / "launcher_v2.py")
    L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))

    def raises(fn, *a):
        try:
            fn(*a)
            return False
        except ValueError:
            return True

    # times typed in the editor
    for raw, want in (("12.5", 12.5), ("12,5", 12.5), ("0:12.5", 12.5), ("1:05", 65.0), ("1:02:03", 3723.0), (" 7 ", 7.0), (3, 3.0)):
        check(f"parse_seconds {raw!r}", abs(ae.parse_seconds(raw) - want) < 1e-9, ae.parse_seconds(raw))
    for raw in ("", "abc", "-1", "nan", "inf", "1:70", "1::2", "1:2:3:4"):
        check(f"parse_seconds rejects {raw!r}", raises(ae.parse_seconds, raw))
    # Windows-safe export names
    for raw in ("CON", "con.mp4", "Trip: day/1?", "a" * 300, "name. . .", "  ", "COM1 - Social HD", "end." + "x" * 116 + "..."):
        n = ae.safe_filename(raw)
        bad = (not n or any(ch in n for ch in '<>:"/\\|?*') or n.endswith((".", " ")) or len(n) > 120
               or n.split(".")[0].strip().upper() in ae._WIN_RESERVED)
        check(f"safe_filename {raw[:20]!r}", not bad, n)
    # adaptive length never asks for more than the footage
    for total, want in ((9.3, 5), (28, 5), (30, 15), (89, 15), (90, 30), (600, 30)):
        check(f"recommend_length {total}", ae.recommend_length(total) == want, ae.recommend_length(total))
    # release ordering incl. pre-releases
    vs = ["3.12.42", "3.13.0-rc1", "3.13.0-rc2", "3.13.0", "3.13.1"]
    check("version_key orders pre-releases", sorted(vs, key=L.version_key) == vs)
    # friendly reasons for skipped files
    for code in ("PRIVATE", "NO_MOMENTS", "STATIC_VIDEO", "TOO_SHORT_FOR_ANALYSIS", "ANALYSIS_TIMEOUT", "ANALYSIS_FAILED:X", "DUPLICATE_OF:a.mp4"):
        check(f"friendly_skip {code}", ae.friendly_skip(code) and "_" not in ae.friendly_skip(code).split(" of ")[0], ae.friendly_skip(code))
    # chosen files: missing, unsupported and same-name files are refused
    d = work / "files"; (d / "x").mkdir(parents=True, exist_ok=True)
    (d / "a.mp4").write_bytes(b"0" * 2048); (d / "x" / "a.mp4").write_bytes(b"1" * 2048); (d / "t.txt").write_text("t")
    check("check_files refuses same names", raises(ae.check_files, [str(d / "a.mp4"), str(d / "x" / "a.mp4")]))
    check("check_files refuses non-video", raises(ae.check_files, [str(d / "t.txt")]))
    check("check_files refuses missing", raises(ae.check_files, [str(d / "nope.mp4")]))
    check("check_files refuses relative", raises(ae.check_files, ["a.mp4"]))
    check("check_files accepts one", [p.name for p in ae.check_files([str(d / "a.mp4")])] == ["a.mp4"])
    # a folder of year folders: the subfolders with videos are offered
    yrs = work / "years"; (yrs / "2023").mkdir(parents=True, exist_ok=True); (yrs / "2024").mkdir(exist_ok=True); (yrs / "docs").mkdir(exist_ok=True)
    (yrs / "2023" / "a.mp4").write_bytes(b"0" * 2048); (yrs / "2024" / "b.MOV").write_bytes(b"0" * 2048); (yrs / "docs" / "c.txt").write_text("c")
    check("subfolders_with_videos", [(Path(x).name, n) for x, n in ae.subfolders_with_videos(yrs)] == [("2023", 1), ("2024", 1)],
          ae.subfolders_with_videos(yrs))
    # a camera card picked at its root: the video folders deeper inside are found (system folders skipped)
    card = work / "card"
    for sub in ("DCIM/100GOPRO", "PRIVATE/AVCHD/BDMV/STREAM", "PRIVATE/M4ROOT/CLIP", "System Volume Information/x"):
        (card / sub).mkdir(parents=True, exist_ok=True)
    (card / "DCIM/100GOPRO/GX010001.MP4").write_bytes(b"0" * 1024)
    (card / "PRIVATE/AVCHD/BDMV/STREAM/00001.MTS").write_bytes(b"0" * 1024)
    (card / "PRIVATE/M4ROOT/CLIP/C0001.MP4").write_bytes(b"0" * 1024)
    (card / "System Volume Information/x/a.mp4").write_bytes(b"0" * 1024)
    found = sorted(Path(x).relative_to(card).as_posix() for x, _ in ae.subfolders_with_videos(card))
    check("camera card: deep video folders found", found == ["DCIM/100GOPRO", "PRIVATE/AVCHD/BDMV/STREAM", "PRIVATE/M4ROOT/CLIP"], found)
    from archivist.config import PRIVATE as _PRIV
    Path(_PRIV).mkdir(parents=True, exist_ok=True)
    (Path(_PRIV) / "secret.mp4").write_bytes(b"0" * 1024)
    listed = [Path(x).name for x, _ in ae.subfolders_with_videos(Path(_PRIV).parent)]
    check("Private folder is never offered as a video folder", Path(_PRIV).name not in listed, listed)
    (Path(_PRIV) / "secret.mp4").unlink()
    # OneDrive cloud-only placeholders: skipped with a reason, never read (reading would download them)
    cloud = work / "cloud"
    cloud.mkdir(exist_ok=True)
    cfiles = [cloud / "VID_1.mp4", cloud / "VID_2.mp4"]
    for f in cfiles:
        f.write_bytes(b"0" * 4096)
    real_cloud = ae.cloud_only
    if os.name == "nt":
        import ctypes
        for f in cfiles:
            ctypes.windll.kernel32.SetFileAttributesW(str(f), 0x1000)     # FILE_ATTRIBUTE_OFFLINE, as a placeholder has
    else:
        ae.cloud_only = lambda p, st=None: Path(p).parent == cloud
    try:
        sc = ae.scan_folder(cloud)
        check("cloud-only files are skipped with their reason, not read",
              sc["usable"] == 0 and all(r["reason"] == ae.CLOUD_ONLY_REASON for r in sc["files"]) and not ae.local_inputs(cfiles),
              [r["reason"] for r in sc["files"]])
    finally:
        ae.cloud_only = real_cloud
        if os.name == "nt":
            for f in cfiles:
                ctypes.windll.kernel32.SetFileAttributesW(str(f), 0x80)
    # a folder with a wrong / partial model is refused with a clear reason and nothing is copied
    fake = work / "fake_archivist" / "sidecars" / "auto_edit" / "models" / "FAST_LOCAL"
    fake.mkdir(parents=True, exist_ok=True)
    (fake / "model_int8.onnx").write_bytes(b"not the model" * 100)
    from archivist.config import HOME as _HOME
    try:
        ae.import_model(str(work / "fake_archivist"))
        refused = False
    except ValueError as exc:
        refused = "No exact FAST_LOCAL model" in str(exc)
    check("wrong model folder refused, nothing copied", refused and not (Path(_HOME) / "models" / "FAST_LOCAL").exists()
          and not ae._model_valid(fake.parent))
    # a browser / screen recording with no length written in the file: measured, used through a fixed copy
    ff = ae._ffmpeg()
    if ff:
        rec = work / "recording"; rec.mkdir(exist_ok=True)
        live = rec / "rec.webm"
        with live.open("wb") as fh:
            subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25", "-t", "4", "-c:v", "libvpx",
                            "-deadline", "realtime", "-b:v", "300k", "-live", "1", "-f", "webm", "pipe:1"], stdout=fh, check=False)
        if live.stat().st_size > 2000:
            orig = live.read_bytes()
            sc = ae.scan_folder(rec)
            check("recording without a length: usable, measured", sc["usable"] == 1 and sc["files"][0].get("length_measured")
                  and 3.5 <= sc["files"][0]["duration_s"] <= 4.1, sc["files"])
            fixed, changed = ae._with_length([live], work / "rec_work")
            again, _ = ae._with_length([live], work / "rec_work")
            check("recording without a length: fixed copy has the length, original untouched, copy reused",
                  changed and fixed[0] != live and 3.5 <= float(ae._probe(fixed[0])["format"]["duration"]) <= 4.1
                  and live.read_bytes() == orig and again == fixed and fixed[0].name == live.name, (fixed, changed))
            real_priv = ae._private_hashes
            ae._private_hashes = lambda: [ae.sha256_file(live)]
            try:
                kept, ch2 = ae._with_length([live], work / "rec_work2")
                check("recording without a length marked Private is never copied", kept == [live] and not ch2, kept)
            finally:
                ae._private_hashes = real_priv
        else:
            print("SKIP recording without a length: this ffmpeg cannot write WebM")
    # times are stored as local wall-clock time: a running job's elapsed time must not be off by the UTC offset
    from datetime import datetime as _dt, timedelta as _td
    from archivist import web as _web
    st75 = (_dt.now() - _td(seconds=75)).isoformat(timespec="seconds")
    check("running job elapsed time is local, not UTC", _web._job_elapsed({"started_at": st75}) in ("1m 15s", "1m 16s")
          and 74 <= ae.job_elapsed_s({"started_at": st75}) <= 77, (_web._job_elapsed({"started_at": st75}), ae.job_elapsed_s({"started_at": st75})))
    import types as _types
    check("cloud-only attribute detected", ae.cloud_only("x", _types.SimpleNamespace(st_file_attributes=0x400000))
          and not ae.cloud_only("x", _types.SimpleNamespace(st_file_attributes=0x20)))
    # a phone camera folder with more videos than one reel takes: grouped by shooting day (name first, else file date)
    cam = work / "camera"; cam.mkdir(parents=True, exist_ok=True)
    for i in range(40):
        (cam / f"VID_20260714_1200{i:02d}.mp4").write_bytes(b"0" * 1024)
    for i in range(30):
        (cam / f"PXL_20260715_1300{i:02d}123.mp4").write_bytes(b"0" * 1024)
    (cam / "clip.mov").write_bytes(b"0" * 1024); os.utime(cam / "clip.mov", (1_600_000_000, 1_600_000_000))
    days = ae.videos_by_day(cam)
    check("videos_by_day groups a big folder, newest day first",
          [(d["day"], len(d["files"])) for d in days] == [("2026-07-15", 30), ("2026-07-14", 40), (ae.video_day(cam / "clip.mov", 1_600_000_000), 1)],
          [(d["day"], len(d["files"])) for d in days])
    names14 = [f["name"] for f in days[1]["files"]]
    check("a day's videos are listed newest first (tick the newest)", names14 == sorted(names14, reverse=True), names14[:3])
    check("big folder is offered as a choice, not refused", len(ae.list_videos(cam)) > ae.MAX_INPUTS and raises(ae.check_folder, str(cam)))
    # a nearly full data drive refuses a new build up front (not half-way)
    old_min = ae.MIN_FREE_BYTES
    ae.MIN_FREE_BYTES = 1 << 62
    check("full drive refuses a build", raises(ae.check_free_space))
    ae.MIN_FREE_BYTES = old_min
    check("normal drive allows a build", not raises(ae.check_free_space))
    # older versions next to this one can be listed and removed; never this one, never the data folder
    base = work / "builds"
    cur, old, other = base / "MediaEngine-3.13.0-b2", base / "MediaEngine-3.13.0-b1", base / "MediaEngine-notes"
    for d in (cur, old, other, base / "MediaEngine Data"):
        d.mkdir(parents=True, exist_ok=True)
    for d in (cur, old):
        for n in ae.BUILD_MARKERS:
            (d / n).write_text(f"MediaEngine {d.name}\n", encoding="utf-8")
    (other / "BUILD.txt").write_text("x", encoding="utf-8")
    lst = ae.other_builds(cur)
    check("other_builds lists only real other builds", [b["name"] for b in lst] == [old.name], lst)
    check("delete_build refuses this build and the data folder", raises(ae.delete_build, cur.name, cur) and raises(ae.delete_build, "MediaEngine Data", cur))
    check("delete_build removes an older build", ae.delete_build(old.name, cur) > 0 and not old.exists() and cur.exists()
          and (base / "MediaEngine Data").exists())
    early = base / "MediaEngine-3.13.0-rc1"          # early candidates kept projects and exports inside the release
    early.mkdir(exist_ok=True)
    for n in ae.BUILD_MARKERS:
        (early / n).write_text("x", encoding="utf-8")
    (early / "data").mkdir(exist_ok=True); (early / "data" / "archivist.db").write_bytes(b"db")
    check("a build folder holding projects is never offered for removal", early.name not in [b["name"] for b in ae.other_builds(cur)]
          and raises(ae.delete_build, early.name, cur) and (early / "data" / "archivist.db").exists())
    # shortcuts keep any characters (WScript.Shell stored "?" for Cyrillic on an English Windows)
    if os.name == "nt":
        from archivist.platform_adapter import read_shell_link, write_shell_link, shell_folder
        d = work / "Видео 視頻 é"
        d.mkdir(parents=True, exist_ok=True)
        tgt = str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe")
        arg = f'"{d / "Start MediaEngine.vbs"}"'
        write_shell_link(d / "Ярлык.lnk", tgt, arg, str(d), "", "проверка")
        back = read_shell_link(d / "Ярлык.lnk")
        check("unicode shortcut round trip", back["arguments"] == arg and back["workdir"] == str(d)
              and back["target"].lower() == tgt.lower(), back)
        check("desktop and start-menu folders found", shell_folder(0x10) is not None and shell_folder(0x02) is not None)
    # Russian: plural forms; native window titles follow the interface language
    from archivist import i18n
    check("ru plural forms", [i18n.ru_plural(n, "версия", "версии", "версий") for n in (1, 2, 5, 11, 21, 22, 112)]
          == ["версия", "версии", "версий", "версий", "версия", "версии", "версий"])
    ae.set_ui_language("ru")
    ru_title = ae._dialog_title("Choose videos for one reel")
    ae.set_ui_language("en")
    check("dialog titles follow the language", ru_title.startswith("Выбери видео") and ae._dialog_title("Choose videos for one reel") == "Choose videos for one reel")
    # Russian page translation never touches user content, values, scripts' logic or protected text
    page = ("<html><head><title>Settings · MediaEngine</title></head><body><a href='/x'>Open Library</a><b translate='no'>Open Library</b>"
            "<div>Library videos.mp4</div><input value='Remove' placeholder='Search Library'><span class='ae-path'>D:\\Videos\\Library</span>"
            "<button onclick=\"if(!confirm('Mark selected Private forever?'))return\">Remove</button>"
            "<script>if(x.status==='done'){toast('Select files first')}</script><span>quality good 81.5</span><span>3 errors</span></body></html>")
    out = i18n.translate_page(page, "/library")
    check("ru page: phrases and patterns translated", "Открыть библиотеку</a>" in out and "<title>Настройки · MediaEngine</title>" in out
          and "качество хорошее 81.5" in out and "ошибок: 3" in out and "placeholder='Поиск в библиотеке'" in out, out[:300])
    check("ru page: user content, values, protected text and code untouched", "<b translate='no'>Open Library</b>" in out
          and "<div>Library videos.mp4</div>" in out and "value='Remove'" in out and "D:\\Videos\\Library" in out
          and "x.status==='done'" in out and "href='/x'" in out)
    check("ru page: confirm texts in handlers; script-made texts via the in-page dictionary",
          "confirm('Отметить выбранное как Private навсегда?')" in out and "window.ME_I18N" in out and "Сначала выбери файлы" in out)
    # a build left "running" by a crashed process is marked interrupted by the first page the new process serves
    # (any page - Quit/Restart/switching builds would otherwise be refused for a job that no longer exists)
    from archivist.db import db as _db, now_iso as _now
    ae.ensure_schema()
    with _db() as con:
        pid_ = con.execute("INSERT INTO ae_projects(title,folder,created_at,updated_at) VALUES('t',?,?,?)", (str(work), _now(), _now())).lastrowid
        jid_ = con.execute("INSERT INTO ae_jobs(project_id,request_key,settings_json,status,stage,created_at,started_at) "
                           "VALUES(?,'k','{}','running','analyze',?,?)", (pid_, _now(), _now())).lastrowid
        con.commit()
    ae._SCHEMA_READY = False                     # as in a freshly started process
    from archivist.web import create_app as _ca
    with _ca().test_client() as _c:
        _c.get("/api/ping", headers={"Host": "127.0.0.1:8765"})
    check("crashed build is marked interrupted by the first request", ae.job(jid_)["status"] == "failed", ae.job(jid_)["status"])
    # the language chosen in a Setup run applies once (also over an older build's saved choice); a later switch in
    # the program is kept until the next Setup run
    from archivist import i18n as _lang
    real_setup = _lang._setup_language
    try:
        _lang.set_ui_language("en")
        _lang._setup_language = lambda: ("ru", "MediaEngine-x-b99")
        first = _lang.ui_language()
        _lang.set_ui_language("en")
        kept = _lang.ui_language()
        _lang._setup_language = lambda: ("ru", "MediaEngine-x-b100")
        again = _lang.ui_language()
        _lang.set_ui_language("ru")
        _lang._setup_language = lambda: ("en", "")          # an older Setup without a build mark
        old_setup = _lang.ui_language()
        check("Setup language applies once per Setup run", (first, kept, again, old_setup) == ("ru", "en", "ru", "ru"),
              (first, kept, again, old_setup))
    finally:
        _lang._setup_language = real_setup
        _lang.set_ui_language("en")
    # every fixed message the engine reports while it works has a Russian text (job line under the progress bar)
    import re as _re
    eng = (Path(__file__).resolve().parents[1] / "app" / "archivist" / "engine_p11" / "p11_folder_to_reel_r3.py").read_text(encoding="utf-8")
    msgs = set()
    for call in _re.findall(r'progress\("\w+",(.*)\)', eng):          # stage first, then the message literals
        msgs |= set(_re.findall(r'(?<!\[)"([A-Za-z][^"]*)"', call))
    from archivist import i18n as _i18n
    missing = sorted(m for m in msgs if _i18n.translate_json({"message": m})["message"] == m)
    check("ru: every engine progress message translated", bool(msgs) and not missing, missing or len(msgs))
    prep = _i18n.translate_json({"message": "Preparing a recording without a length: it's [1] 1.5 s.webm"})["message"]
    check("ru: preparing a recording without a length (file name kept)", prep == "Подготовка записи без длины: it's [1] 1.5 s.webm", prep)
    long = _i18n.translate_text("Requested 15 s, got 9.7 s: there were not enough different moments in this footage for a longer reel.", True)
    check("ru: short-reel note fully Russian", not _re.search(r"[A-Za-z]{3,}", long), long)
    # the Explorer-style folder window (Windows): opens in the given folder, "Select Folder" returns it, Cancel returns
    # nothing; driven by window messages. Without a desktop the window cannot appear: reported, not counted.
    if os.name == "nt":
        import ctypes, threading, time as _t
        user32 = ctypes.windll.user32
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        pick = work / "Папка для выбора"
        pick.mkdir(exist_ok=True)

        def drive(title, wparam, msg=0x0111):          # WM_COMMAND IDOK = "Select Folder"; WM_CLOSE = cancel
            box = {}
            th = threading.Thread(target=lambda: box.update(p=ae.pick_folder(title, initial=str(pick))), daemon=True)
            th.start()
            hwnd = None
            for _ in range(200):
                hwnd = user32.FindWindowW(None, title)
                if hwnd:
                    break
                _t.sleep(0.1)
            if not hwnd:
                return None, False
            _t.sleep(1.0)                               # let it finish opening the folder
            user32.PostMessageW(hwnd, msg, wparam, 0)
            th.join(20)
            return box.get("p"), not th.is_alive()
        chosen, ended = drive("MediaEngine folder test OK", 1)
        if chosen is None and not ended:
            print("SKIP folder window: no window appeared (no interactive desktop)")
        else:
            check("folder window: Select Folder returns the folder it opened in",
                  ended and chosen and Path(chosen).resolve() == pick.resolve(), (chosen, ended))
            cancelled, ended = drive("MediaEngine folder test cancel", 0, msg=0x0010)
            check("folder window: closing it returns nothing", ended and cancelled is None, (cancelled, ended))
            # the file window ("Choose videos…"): opens in the given folder; the name typed into its name box is returned
            vid = pick / "видео 1.mp4"
            vid.write_bytes(b"0" * 2048)
            user32.FindWindowExW.restype = ctypes.c_void_p
            user32.FindWindowExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p]
            user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_wchar_p]
            title = "MediaEngine files test"
            box = {}
            th = threading.Thread(target=lambda: box.update(f=ae.pick_files(title, initial=str(pick))), daemon=True)
            th.start()
            hwnd = None
            for _ in range(200):
                hwnd = user32.FindWindowW(None, title)
                if hwnd:
                    break
                _t.sleep(0.1)
            edit = None
            if hwnd:
                _t.sleep(1.0)
                combo = user32.FindWindowExW(hwnd, None, "ComboBoxEx32", None)
                inner = user32.FindWindowExW(combo, None, "ComboBox", None) if combo else None
                edit = user32.FindWindowExW(inner, None, "Edit", None) if inner else None
                if edit:
                    user32.SendMessageW(edit, 0x000C, 0, '"' + vid.name + '"')     # WM_SETTEXT
                    user32.PostMessageW(hwnd, 0x0111, 1, 0)                         # IDOK = Open
                else:
                    user32.PostMessageW(hwnd, 0x0010, 0, 0)
                th.join(20)
            if not edit:
                print("SKIP file window: name box not found", bool(hwnd))
            else:
                got = box.get("f") or []
                check("file window: opens in the given folder and returns the chosen video",
                      len(got) == 1 and Path(got[0]).resolve() == vid.resolve(), got)
    # Windows must not sleep while a reel is built (no-op elsewhere)
    from archivist.platform_adapter import keep_awake
    with keep_awake() as k:
        check("keep_awake set on Windows", k.ok == (os.name == "nt"), k.ok)
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
