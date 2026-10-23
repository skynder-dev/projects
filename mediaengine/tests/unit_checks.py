"""Small, fast checks of helper rules (no video work).

  python tests/unit_checks.py <work_dir>
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys
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
    # a newer build takes over from an older running one without a question (closing the window leaves the old one
    # running in the background, so the owner was asked after every install); an older one or an unknown name asks
    sq = [L.switch_question(r"D:\p\MediaEngine-3.13.0-rc1-b137", r"D:\p\MediaEngine-3.13.0-rc1-b131"),
          L.switch_question("MediaEngine-3.13.0-rc1-b131", "MediaEngine-3.13.0-rc1-b137"),
          L.switch_question("MediaEngine-3.13.0-b2", "MediaEngine-3.13.0-rc1-b140"),
          L.switch_question("MediaEngine-3.13.0-rc1-b9", "MediaEngine-3.13.0-rc1-b10"),
          L.switch_question("MediaEngine Тест 2", "MediaEngine-3.13.0-rc1-b131"),
          L.switch_question("MediaEngine-3.13.0-rc1-b137", ""),
          L.switch_question("MediaEngine-3.13.0-rc1-b137", "MediaEngine-3.13.0-rc1-b137")]
    check("switch_question: newer switches, older or unknown asks", sq == ["switch", "ask_older", "switch", "ask_older", "ask", "ask", "ask"], sq)
    # tray icon: only MediaEngine's own Edge app windows are focused / closed by Open and Quit
    from archivist import tray
    tw = [tray.is_app_window_title(t) for t in ("Auto Edit · MediaEngine", "Автомонтаж · MediaEngine", "Мой ролик · MediaEngine",
                                                "Auto Edit · MediaEngine - Microsoft​ Edge", "Library · Archivist",
                                                "MediaEngine", "· MediaEngine", "skynder-dev/projects · GitHub", "",
                                                "Microsoft demo · MediaEngine")]
    check("tray: own app windows only", tw == [True, True, True, False, False, False, False, False, False, True], tw)
    vk = ["3.13.0-alpha1", "3.13.0-beta1", "3.13.0-beta2", "3.13.0-rc1", "3.13.0-rc2", "3.13.0"]
    check("version order with alpha / beta numbers (launcher)", sorted(reversed(vk), key=L.version_key) == vk, sorted(reversed(vk), key=L.version_key))
    titles = ["Auto Edit · MediaEngine", "Auto Edit · MediaEngine - Microsoft\u200b Edge", "Library · Archivist", "· MediaEngine", ""]
    check("launcher finds the same windows as the tray", [L.is_app_window_title(t) for t in titles] == [tray.is_app_window_title(t) for t in titles])
    check("launcher: nothing to focus or close off Windows", os.name == "nt" or (L.focus_app_window() is False and L.close_app_windows() == 0))
    check("launcher at sign-in: no other build to follow / no data drive to wait for here",
          os.name == "nt" or (L.last_started_build() is None and L.wait_for_data_folder(1) is True))
    if os.name == "nt":      # Win32 structures as Windows lays them out (64-bit): a wrong size = no icon
        import ctypes
        api = tray._api()
        check("tray: NOTIFYICONDATAW / WNDCLASSEXW sizes", (ctypes.sizeof(api["NID"]), ctypes.sizeof(api["WC"])) == (976, 80),
              (ctypes.sizeof(api["NID"]), ctypes.sizeof(api["WC"])))
    else:
        check("tray: nothing to show off Windows", tray.start(url="", icon=Path("x"), version="", ru=lambda: True, status=str,
                                                             busy=str, quit_app=lambda: None) is False)
    # what the tray says runs, and what a Quit would stop: nothing in an empty home; a reel being made is named
    from archivist.db import init_db, db as _db
    from archivist import web as _web
    init_db(); ae.ensure_schema() if hasattr(ae, "ensure_schema") else None
    idle = (_web.busy_reason(), _web.activity_line(True), _web.activity_line(False))
    check("tray: idle home - nothing runs", idle == ("", "", ""), idle)
    try:
        with _db() as con:
            con.execute("INSERT INTO ae_projects(id,title,folder,created_at,updated_at) VALUES(9901,'Поездка & море','x','t','t')")
            con.execute("INSERT INTO ae_jobs(id,project_id,request_key,settings_json,status,stage,done,total,created_at) "
                        "VALUES(9901,9901,'k','{}','running','render',1,2,'t')"); con.commit()
        busy = (_web.busy_reason(), _web.activity_line(True))
        check("tray: a reel being made is named, Quit asks", busy[0].startswith("Auto Edit job #9901") and "«Поездка & море»" in busy[1]
              and busy[1].endswith("%"), busy)
    finally:
        with _db() as con:
            con.execute("DELETE FROM ae_jobs WHERE id=9901"); con.execute("DELETE FROM ae_projects WHERE id=9901"); con.commit()
    # friendly reasons for skipped files
    for code in ("PRIVATE", "NO_MOMENTS", "STATIC_VIDEO", "TOO_SHORT_FOR_ANALYSIS", "ANALYSIS_TIMEOUT", "ANALYSIS_FAILED:X", "DUPLICATE_OF:a.mp4"):
        check(f"friendly_skip {code}", ae.friendly_skip(code) and "_" not in ae.friendly_skip(code).split(" of ")[0], ae.friendly_skip(code))
    # chosen files: missing, unsupported and same-name files are refused
    d = work / "files"; (d / "x").mkdir(parents=True, exist_ok=True)
    (d / "a.mp4").write_bytes(b"0" * 2048); (d / "x" / "a.mp4").write_bytes(b"1" * 2048); (d / "t.txt").write_text("t")
    # two cameras' DJI_0001.MP4 from two folders: both used, the second named apart in the reel; the same file once
    two_ = ae.check_files([str(d / "a.mp4"), str(d / "x" / "a.mp4"), str(d / "a.mp4")])
    names_ = [nm for _, nm in ae.input_names(two_)]
    check("same file names from two folders: both used, named apart", len(two_) == 2 and sorted(names_) == ["a (2).mp4", "a.mp4"]
          and [nm for _, nm in ae.input_names(list(reversed(two_)))] == names_, (two_, names_))
    # the engine's input list: a name with U+2028 (allowed on Windows) is one line; a reel name keeps its leading space
    sys.path.insert(0, str(ROOT / "app" / "archivist" / "engine_p11"))
    import p11_folder_to_reel_r3 as _eng
    lst_ = d / "inputs.txt"
    lst_.write_text(str(d / "a\u2028b.mp4") + "\n" + str(d / "x" / " c.mp4") + "\t c (2).mp4\r\n\n", encoding="utf-8")
    got_ = _eng.read_input_list(lst_)
    check("input list: odd line breaks inside names, leading spaces kept",
          got_ == [str(d / "a\u2028b.mp4"), str(d / "x" / " c.mp4") + "\t c (2).mp4"], got_)
    # Free and a build starting at that moment: the folder is moved aside at once, deleted after; leftovers swept
    aside_ = work / "aside_t" / "work"
    (aside_ / "sub").mkdir(parents=True, exist_ok=True); (aside_ / "sub" / "f.bin").write_bytes(b"1")
    moved_ = ae._move_aside(aside_)
    check("free: the cache folder is moved aside in one step", moved_ is not None and moved_.is_dir() and not aside_.exists()
          and moved_.name.startswith("work.deleting-") and ae._move_aside(aside_) is None, moved_)
    real_ae_root = ae.AE_ROOT
    try:
        ae.AE_ROOT = work / "aside_t"
        (ae.AE_ROOT / "p3").mkdir(exist_ok=True)
        os.replace(moved_, ae.AE_ROOT / "p3" / moved_.name)
        (ae.AE_ROOT / "shared.deleting-1").mkdir()
        (ae.AE_ROOT / "p3" / "work").mkdir()
        ae.sweep_deleting()
        check("free: half-deleted folders are swept at start, nothing else",
              sorted(x.name for x in ae.AE_ROOT.rglob("*")) == ["p3", "work"], sorted(x.name for x in ae.AE_ROOT.rglob("*")))
    finally:
        ae.AE_ROOT = real_ae_root
    # a finished reel deleted outside the app: the same request builds it again
    real_rev = ae.revision
    try:
        ae.revision = lambda rid: {"video_path": str(d / "a.mp4")} if int(rid) == 1 else ({"video_path": str(d / "gone.mp4")} if int(rid) == 2 else None)
        check("a finished reel that is gone is built again", not ae._result_gone({"revision_id": 1}) and ae._result_gone({"revision_id": 2})
              and ae._result_gone({"revision_id": 3}) and not ae._result_gone({"revision_id": None}))
    finally:
        ae.revision = real_rev
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
        # a phone video stored on its side with "rotate 90": listed upright (360x640), a normal one as it is
        rot = work / "rotated"; rot.mkdir(exist_ok=True)
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30", "-t", "3.2", "-c:v", "libx264",
                        str(rot / "flat.mp4")], check=False)
        subprocess.run([ff, "-v", "error", "-y", "-display_rotation", "90", "-i", str(rot / "flat.mp4"), "-c", "copy",
                        str(rot / "side.mp4")], check=False)
        if (rot / "side.mp4").is_file():
            dims = {r["name"]: (r["width"], r["height"]) for r in ae.scan_folder(rot)["files"]}
            check("a video stored on its side is listed upright", dims == {"flat.mp4": (640, 360), "side.mp4": (360, 640)}, dims)
        rec = work / "OBS Output #1"; rec.mkdir(exist_ok=True)       # "Output #" in the path must not confuse the reading
        live = rec / "rec.webm"
        with live.open("wb") as fh:
            subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25", "-t", "4", "-c:v", "libvpx",
                            "-deadline", "realtime", "-b:v", "300k", "-live", "1", "-f", "webm", "pipe:1"], stdout=fh, check=False)
        if live.stat().st_size > 2000:
            orig = live.read_bytes()
            sc = ae.scan_folder(rec)
            check("recording without a length: usable, measured", sc["usable"] == 1 and sc["files"][0].get("length_measured")
                  and 3.5 <= sc["files"][0]["duration_s"] <= 4.1, sc["files"])
            notes = []
            rw = work / "rec_work"
            (rw / "fixed_inputs").mkdir(parents=True, exist_ok=True)
            (rw / "fixed_inputs" / "old removed.webm").write_bytes(b"x")       # a copy of a file no longer used
            fixed, changed = ae._with_length([live], rw, notes.append)
            m1 = fixed[0].stat().st_mtime_ns if fixed[0].is_file() else 0
            again, _ = ae._with_length([live], rw, notes.append)
            check("recording without a length: fixed copy has the length, original untouched, copy reused, old copies gone",
                  changed and fixed[0] != live and 3.5 <= float(ae._probe(fixed[0])["format"]["duration"]) <= 4.1
                  and live.read_bytes() == orig and again == fixed and fixed[0].name == ae._fixed_name(live) and notes == [live.name]
                  and fixed[0].stat().st_mtime_ns == m1 and not (rw / "fixed_inputs" / "old removed.webm").exists(),
                  (fixed, changed, notes))
            (rw / "fixed_inputs" / (ae._fixed_name(live) + ".source.json")).write_text("", encoding="utf-8")   # damaged stamp (disk was full)
            third, _ = ae._with_length([live], rw, notes.append)
            check("recording without a length: a damaged stamp makes a new copy, never a failed build", third == fixed and len(notes) == 2,
                  (third, notes))
            away = rec / "rec.webm.away"
            os.replace(live, away)                      # its card unplugged for now
            gone_, _ = ae._with_length([live], rw, notes.append)
            os.replace(away, live)
            back_, _ = ae._with_length([live], rw, notes.append)
            check("recording without a length: its copy stays while the card is unplugged, reused when it is back",
                  gone_ == [live] and back_ == fixed and len(notes) == 2, (gone_, back_, notes))
            from archivist import media as _media
            ld = _media.probe_duration(live)
            check("recording without a length: Library and Convert get its length too", ld and 3.5 <= ld <= 4.1, ld)
            real_priv = ae._private_hashes
            ae._private_hashes = lambda: [ae.sha256_file(live)]
            try:
                kept, ch2 = ae._with_length([live], rw)
                check("recording without a length marked Private: never copied, the earlier copy deleted",
                      kept == [live] and not ch2 and not list((rw / "fixed_inputs").iterdir()), kept)
            finally:
                ae._private_hashes = real_priv
            ae._CANCEL.add(-7)
            try:
                ae._with_length([live], work / "rec_work3", None, -7)
                stopped = False
            except ae._Stopped:
                stopped = True
            finally:
                ae._CANCEL.discard(-7)
            check("recording without a length: Cancel stops the preparation", stopped)
        else:
            print("SKIP recording without a length: this ffmpeg cannot write WebM")
    # AI+ themes: the app's list is the engine's list; a theme needs AI+; an unknown theme is refused
    sys.path.insert(0, str(ROOT / "app" / "archivist" / "engine_p11"))
    import p13_event_semantic_pe as _hook
    check("AI+ themes: app and engine lists are the same", {k: v[0] for k, v in _hook.THEMES.items()} == ae.THEMES)
    check("AI+ themes: every description is plain English (the model's tokenizer)",
          all(t.isascii() for _, ps in _hook.THEMES.values() for t in ps) and all(t.isascii() for t in _hook.POSITIVE_PROMPTS + _hook.NEGATIVE_PROMPTS))
    check("AI+ themes: the theme's own bad descriptions are plain English and belong to a theme",
          all(t.isascii() for ps in _hook.THEME_NEGATIVES.values() for t in ps) and set(_hook.THEME_NEGATIVES) <= set(_hook.THEMES))
    pos_a, neg_a = _hook.prompts_for("aerial")
    check("aerial theme: take-off / landing frames are bad frames for it, the general bad frames too",
          set(_hook.NEGATIVE_PROMPTS) < set(neg_a) and any("ground" in t for t in neg_a)
          and _hook.prompts_for("sea")[1] == _hook.NEGATIVE_PROMPTS and _hook.prompt_key("aerial") != _hook.prompt_key("sea"), neg_a)
    st = ae.normalize_settings({"length": 15, "format": "social_hd", "sound": "auto", "mode": "technical", "theme": "sea"})
    check("a theme is dropped without AI+", "theme" not in st, st)
    # "Prepare in advance": its own request (never mixed up with a build), analysis-only progress, its own state
    base_ = {"length": 15, "format": "social_hd", "sound": "auto", "mode": "technical"}
    stp = ae.normalize_settings({**base_, "prepare": "1"})
    check("prepare in advance: a flag of its own; not with a hand-made selection",
          stp.get("prepare") is True and "prepare" not in ae.normalize_settings(base_)
          and "prepare" not in ae.normalize_settings({**base_, "prepare": "1", "selection": ["a" * 16]}), stp)
    jp_ = {"status": "running", "stage": "analyze", "done": 5, "total": 10, "settings_json": json.dumps(stp)}
    jb_ = {"status": "running", "stage": "analyze", "done": 5, "total": 10, "settings": base_}
    check("prepare in advance: finding moments is nearly the whole bar", ae.job_percent(jp_) == 50 and ae.job_percent(jb_) == 27
          and ae.is_prepare(jp_) and not ae.is_prepare(jb_), (ae.job_percent(jp_), ae.job_percent(jb_)))
    check("prepare in advance: a prepared project says so", ae.project_state({"jobs": [{"status": "done", "settings": stp}]}) == "PREPARED"
          and ae.project_state({"jobs": [{"status": "done", "settings": base_}]}) == "DRAFT")
    # a build after preparing that was cancelled or failed (or the card unplugged) does not undo the preparing
    prep_ = {"status": "done", "settings": stp}
    canc_ = {"jobs": [{"status": "cancelled", "settings": base_}, prep_]}
    fail_ = {"jobs": [{"status": "failed", "settings": base_}, prep_]}
    unpl_ = {"jobs": [prep_], "source_present": False}
    built_ = {"jobs": [{"status": "done", "settings": base_}, prep_], "revisions": [{"id": 1}]}
    check("prepare in advance: still prepared after a cancelled or failed build",
          ae.project_state(canc_) == "PREPARED" and ae.prepared_job(canc_) is prep_ and ae.prepared_job(fail_) is prep_
          and ae.project_state(fail_) == "ATTENTION" and ae.prepared_job(unpl_) is prep_ and ae.prepared_job(built_) is None,
          (ae.project_state(canc_), ae.project_state(fail_)))
    cmd_ = ae.engine_command(work, work / "o", work / "w", work / "p.json", {**stp, "title": "T"}, work / "e.json", None, None, work / "d.json")
    check("prepare in advance: the engine only analyses (no title / music step)", "--prepare-only" in cmd_ and "--dress" not in cmd_, cmd_[-6:])
    check("an unknown theme is refused", raises(ae.normalize_settings, {"length": 15, "format": "social_hd", "sound": "auto",
                                                                         "mode": "technical", "theme": "moon"}))
    # AI+ download over a bad connection: the connection drops in the middle, the download continues where it stopped
    # (HTTP Range) instead of starting the 650 MB again; a server without Range support restarts the file cleanly
    import http.server, socketserver, threading as _th, hashlib as _hl
    blob = os.urandom(3_000_000)
    seen = []

    class _H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            rng = self.headers.get("Range")
            seen.append(rng)
            ranged = rng and self.path != "/norange"
            start = int(rng.split("=")[1].split("-")[0]) if ranged else 0
            body = blob[start:]
            self.send_response(206 if ranged else 200)
            if ranged:
                self.send_header("Content-Range", f"bytes {start}-{len(blob) - 1}/{len(blob)}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if len(seen) == 1:                        # the first connection drops after 1 MB
                self.wfile.write(body[:1_000_000]); self.wfile.flush()
                self.connection.shutdown(2)
                return
            self.wfile.write(body)

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _H)
    _th.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        part = work / "dl" / "x.part"; part.parent.mkdir(parents=True, exist_ok=True); part.unlink(missing_ok=True)
        ae._AIPLUS_STOP.clear()
        ae._fetch_resumable(f"http://127.0.0.1:{srv.server_address[1]}/m", part, len(blob), lambda n: None)
        check("AI+ download continues after a dropped connection (Range)", part.read_bytes() == blob and len(seen) >= 2
              and seen[0] is None and str(seen[1]).startswith("bytes=1000000-"), seen)
        part.write_bytes(blob[:500_000]); seen.clear(); seen.append("skip-drop")
        ae._fetch_resumable(f"http://127.0.0.1:{srv.server_address[1]}/norange", part, len(blob), lambda n: None)
        check("AI+ download: a server without Range starts the file again", _hl.sha256(part.read_bytes()).digest() == _hl.sha256(blob).digest(), seen)
    finally:
        srv.shutdown()
    # times are stored as local wall-clock time: a running job's elapsed time must not be off by the UTC offset
    from datetime import datetime as _dt, timedelta as _td
    from archivist import web as _web
    st75 = (_dt.now() - _td(seconds=75)).isoformat(timespec="seconds")
    check("running job elapsed time is local, not UTC", _web._job_elapsed({"started_at": st75}) in ("1m 15s", "1m 16s")
          and 74 <= ae.job_elapsed_s({"started_at": st75}) <= 77, (_web._job_elapsed({"started_at": st75}), ae.job_elapsed_s({"started_at": st75})))
    # time left from the real rate of the current stage (finding moments in 4K is most of a build)
    from archivist import auto_edit_web as _aew
    jj = {"id": 991, "status": "running", "stage": "analyze", "done": 2, "total": 18}
    e0 = _aew.stage_eta_s(jj, now=1000.0)                        # first sight: no estimate
    e1 = _aew.stage_eta_s(dict(jj, done=2), now=1100.0)          # nothing finished since: no estimate
    e2 = _aew.stage_eta_s(dict(jj, done=4), now=1600.0)          # 2 videos in 600 s -> 14 left -> 4200 s
    e3 = _aew.stage_eta_s(dict(jj, stage="render", done=0, total=6), now=1700.0)   # a new stage starts again
    e4 = _aew.stage_eta_s(dict(jj, stage="render", done=3, total=6), now=1790.0)   # 3 pieces in 90 s -> 90 s
    e5 = _aew.stage_eta_s(dict(jj, status="done"), now=1800.0)
    check("time left is estimated per stage from its real rate", (e0, e1, e2, e3, e4, e5) == (None, None, 4200, None, 90, None),
          (e0, e1, e2, e3, e4, e5))
    ae.ENGINE_ETA[992] = ("analyze", 600.0, 1000.0)      # the engine's own estimate wins (known videos went first)
    e6 = _aew.stage_eta_s(dict(jj, id=992), now=1100.0)
    ae.ENGINE_ETA[992] = ("analyze", None, 1000.0)
    e7 = _aew.stage_eta_s(dict(jj, id=992), now=1100.0)
    check("the engine's time left is counted down, none before it knows", (e6, e7) == (500, None), (e6, e7))
    # the shared AI cache: Private videos' reports and clips go, the longest unused clips go over the limit
    sh = ae.SHARED; cd_ = sh / "semantic_previews"; rd_ = sh / "semantic_reports"
    (sh / "semantic_candidates").mkdir(parents=True, exist_ok=True); (sh / "semantic_candidates" / "old4k.mp4").write_bytes(b"x")
    cd_.mkdir(parents=True, exist_ok=True); rd_.mkdir(parents=True, exist_ok=True)
    pv, okv = "a" * 64, "b" * 64
    (rd_ / (pv + ".json")).write_text("{}"); (rd_ / (okv + ".json")).write_text("{}")
    for i, src_ in enumerate([pv, okv, okv, okv]):
        (cd_ / f"c{i}.mp4").write_bytes(b"x" * 1000)
        (cd_ / f"c{i}.json").write_text(json.dumps({"source_sha256": src_}))
        os.utime(cd_ / f"c{i}.json", (1000 + i, 1000 + i))
    al = "c" * 64                                   # a stand-in (camcorder remux) of the Private video
    (rd_ / (al + ".json")).write_text("{}"); (rd_ / (al + ".origin")).write_text(pv)
    (cd_ / "c9.mp4").write_bytes(b"x"); (cd_ / "c9.json").write_text(json.dumps({"source_sha256": al, "origin_sha256": pv}))
    (cd_ / "orphan.mp4").write_bytes(b"x"); os.utime(cd_ / "orphan.mp4", (1000, 1000))   # no description: a stopped build
    ae.tidy_shared_cache([pv], max_clip_bytes=2000, min_free_bytes=0, prune_clips=False)    # beside a build: nothing pruned
    kept_ = sorted(x.name for x in cd_.glob("*.mp4"))
    ae.tidy_shared_cache([pv], max_clip_bytes=2000, min_free_bytes=0)
    left_ = sorted(x.name for x in cd_.glob("*.mp4"))
    check("shared AI cache: Private videos (and their stand-ins) go, the longest unused clips go over the limit",
          not (rd_ / (pv + ".json")).exists() and not (rd_ / (al + ".json")).exists() and (rd_ / (okv + ".json")).exists()
          and kept_ == ["c1.mp4", "c2.mp4", "c3.mp4", "orphan.mp4"] and left_ == ["c2.mp4", "c3.mp4"]
          and not (sh / "semantic_candidates").exists(), (kept_, left_))
    shutil.rmtree(sh, ignore_errors=True)
    # decoding on the graphics card: chosen only when identical and clearly faster; stale with another FFmpeg
    from archivist import hwdecode as _hw
    ok_h = {"full": {"error": None}, "preview": {"error": None}}
    ok_h_same = {"full": {"identical": True, "error": None}, "preview": {"identical": True, "error": None}}
    res_ = {"methods": {"d3d11va": {"identical": True, "decoded": 3, "speedup": 2.5, "clips": {"h264_4k.mp4": ok_h}},
                        "cuda": {"identical": False, "decoded": 3, "speedup": 4.0, "clips": {"h264_4k.mp4": ok_h}},
                        "qsv": {"identical": True, "decoded": 3, "speedup": 1.1, "clips": {"h264_4k.mp4": ok_h}}}}
    check("graphics card: the identical and faster method is chosen", _hw.choose(res_) == "d3d11va"
          and _hw.choose({"methods": {"cuda": res_["methods"]["cuda"]}}) == ""
          and _hw.choose({"methods": {"qsv": res_["methods"]["qsv"]}}) == "", _hw.choose(res_))
    check("graphics card: summary lines", _hw.summary({})[0] is False and _hw.summary({**res_, "use": "d3d11va"})[0] is True
          and "not faster" in _hw.summary({"methods": {"qsv": res_["methods"]["qsv"]}})[1]
          and "not exactly the same" in _hw.summary({"methods": {"cuda": res_["methods"]["cuda"]}})[1])
    pk_ = {"methods": {"d3d11va": {"clips": {"h264_4k.mp4": ok_h_same, "hevc_4k.mp4": ok_h_same,
                                              "hevc10_4k.mp4": {"full": {"identical": False, "error": "no 10-bit"}, "preview": {"identical": False, "error": "no 10-bit"}}}}}}
    check("graphics card: only the kinds of video it decoded identically go to it", _hw.proven_kinds(pk_, "d3d11va") == ["h264", "hevc"],
          _hw.proven_kinds(pk_, "d3d11va"))
    # b122 bug (found by review 2026-10-17): the load numbers stored inside a clip's results made every kind "unproven",
    # so a method Check this PC called "used" never reached the engine
    ff_ = ae._ffmpeg() or "ffmpeg"
    old_fmt_ = {"methods": {"d3d11va": {"identical": True, "decoded": 1, "speedup": 2.0,
                                        "clips": {"h264_4k.mp4": {**ok_h_same, "loaded": {"cuts_at_once": 4, "sw_s": 1.0, "hw_s": 0.5}}}}}}
    check("graphics card: a result of the older, weaker test (b122) is never used - test again",
          _hw.proven_kinds(old_fmt_, "d3d11va") == [], _hw.proven_kinds(old_fmt_, "d3d11va"))
    loaded_ = {"methods": {"d3d11va": {"identical": True, "decoded": 1, "speedup": 2.0, "clips": {"h264_4k.mp4": ok_h_same},
                                       "loaded": {"h264_4k.mp4": {"cuts_at_once": 4, "sw_s": 1.0, "hw_s": 0.5, "identical": True}}}}}
    check("graphics card: a result with load numbers proves its kinds", _hw.proven_kinds(loaded_, "d3d11va") == ["h264"],
          _hw.proven_kinds(loaded_, "d3d11va"))
    _hw.save({**loaded_, "use": "d3d11va", "ffmpeg": _hw.ffmpeg_version(ff_), "gpu": _hw.gpu_names_cached()})
    env_ = ae._engine_env()
    check("graphics card: a chosen and proven method reaches the engine", env_.get("MEDENG_HWACCEL") == "d3d11va"
          and env_.get("MEDENG_HWACCEL_KINDS") == "h264", (env_.get("MEDENG_HWACCEL"), env_.get("MEDENG_HWACCEL_KINDS")))
    _hw.save({**res_, "use": "d3d11va", "ffmpeg": "ffmpeg version 0.0-other", "gpu": []})
    check("graphics card: a changed FFmpeg is said on Check this PC", "changed" in _hw.summary(_hw.saved(), ae._ffmpeg() or "ffmpeg")[1])
    check("graphics card: not used after FFmpeg changed (test again)", _hw.method_for_engine(ae._ffmpeg() or "ffmpeg") == ""
          and "MEDENG_HWACCEL" not in ae._engine_env())
    _hw.save({})
    if os.name == "nt" and ae._ffmpeg():     # the real test on this Windows machine (CI: no real graphics card expected)
        r_ = _hw.run_test(ae._ffmpeg(), work / "hwtest")
        print("INFO graphics card test:", json.dumps({k: r_.get(k) for k in ("gpu", "use", "seconds", "error")}),
              {m: (v.get("decoded"), v.get("identical"), v.get("speedup")) for m, v in (r_.get("methods") or {}).items()}, flush=True)
        check("graphics card test runs on Windows and decides", isinstance(r_.get("methods"), dict) and not r_.get("error")
              and len(r_.get("clips") or []) >= 1 and (r_.get("use") == "" or r_["methods"][r_["use"]]["identical"]), r_)
    # a Windows notification after a long build (local only)
    from archivist import notify as _nt
    tx = _nt.toast_xml("A & B", "<x>", 'http://127.0.0.1:8775/auto/p/1?a=1&b="2"')
    check("notification text is escaped", "A &amp; B" in tx and "&lt;x&gt;" in tx and 'a=1&amp;b=&quot;2&quot;' in tx, tx)
    check("no notification after a short build", not _nt.reel_finished("t", True, 10, "http://x", False))
    check("no notification after a short preparation", not _nt.reel_finished("t", True, 10, "http://x", True, prepared=True))
    if os.name == "nt":
        print("INFO a Windows notification could be shown on this PC:", _nt.show("MediaEngine", "unit checks", ""), flush=True)
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
    # a copied video keeps its recording time in its header (mvhd): that day, not the day it was copied
    import time as _tm
    box = lambda t, body: (8 + len(body)).to_bytes(4, "big") + t + body
    ct = 1_720_000_000 + 2082844800
    mvhd0 = box(b"mvhd", bytes(4) + ct.to_bytes(4, "big") + ct.to_bytes(4, "big") + bytes(88))
    mvhd1 = box(b"mvhd", bytes([1, 0, 0, 0]) + ct.to_bytes(8, "big") + ct.to_bytes(8, "big") + bytes(100))
    cam2 = work / "copied"; cam2.mkdir(parents=True, exist_ok=True)
    (cam2 / "trip.mp4").write_bytes(box(b"ftyp", b"isom" + bytes(4) + b"isom") + box(b"mdat", bytes(4000)) + box(b"moov", mvhd0))
    (cam2 / "trip2.mov").write_bytes(box(b"ftyp", b"qt  " + bytes(4) + b"qt  ") + box(b"moov", box(b"udta", bytes(8)) + mvhd1) + box(b"mdat", bytes(500)))
    (cam2 / "nodate.mp4").write_bytes(box(b"ftyp", b"isom" + bytes(4) + b"isom") + box(b"moov", box(b"mvhd", bytes(100))))
    for f in cam2.iterdir():                  # copied in 2025: the file date is the day of the copy
        os.utime(f, (1_760_000_000, 1_760_000_000))
    (cam2 / "kept.mp4").write_bytes(box(b"ftyp", b"isom" + bytes(4) + b"isom") + box(b"moov", mvhd0))
    os.utime(cam2 / "kept.mp4", (1_720_000_000 + 3 * 3600, 1_720_000_000 + 3 * 3600))   # date kept (camera wrote local time)
    check("recording time read from the video header (moov at the end or first, 32/64-bit)",
          ae.shot_time(cam2 / "trip.mp4") == 1_720_000_000.0 and ae.shot_time(cam2 / "trip2.mov") == 1_720_000_000.0
          and ae.shot_time(cam2 / "nodate.mp4") is None and ae.shot_time(cam / "clip.mov") is None,
          (ae.shot_time(cam2 / "trip.mp4"), ae.shot_time(cam2 / "trip2.mov"), ae.shot_time(cam2 / "nodate.mp4")))
    d2 = {d["day"]: len(d["files"]) for d in ae.videos_by_day(cam2)}
    check("a copied video is grouped by the day it was recorded",
          d2 == {_tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000)): 2, _tm.strftime("%Y-%m-%d", _tm.localtime(1_760_000_000)): 1,
                 **({} if _tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000 + 3 * 3600)) == _tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000))
                    else {_tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000 + 3 * 3600)): 1})}
          if _tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000 + 3 * 3600)) != _tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000))
          else d2 == {_tm.strftime("%Y-%m-%d", _tm.localtime(1_720_000_000)): 3, _tm.strftime("%Y-%m-%d", _tm.localtime(1_760_000_000)): 1}, d2)
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
    (old / "launcher.py").write_text("answer=os.environ.get('MEDIAENGINE_SWITCH_ANSWER','')\n", encoding="utf-8")
    can = ae.other_builds(cur)
    check("a build is offered for switching only when its launcher can be asked to", not lst[0]["can_switch"] and can[0]["can_switch"],
          (lst[0].get("can_switch"), can[0].get("can_switch")))
    check("switching to a version that is not there is refused", raises(ae.use_build, "MediaEngine-nope"))
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
    # the owner's clips kept inside an old version's folder (or a Library source there): that version is never removed
    clips_b = base / "MediaEngine-3.13.0-b0"
    (clips_b / "app").mkdir(parents=True, exist_ok=True)
    for n in ae.BUILD_MARKERS:
        (clips_b / n).write_text("x", encoding="utf-8")
    offered_plain = clips_b.name in [b["name"] for b in ae.other_builds(cur)]
    (clips_b / "My clips").mkdir(exist_ok=True); (clips_b / "My clips" / "VID_0001.mp4").write_bytes(b"0" * 4096)
    offered_clips = clips_b.name in [b["name"] for b in ae.other_builds(cur)]
    refused_clips = raises(ae.delete_build, clips_b.name, cur) and (clips_b / "My clips" / "VID_0001.mp4").is_file()
    shutil.move(str(clips_b / "My clips"), str(work / "My clips moved"))
    from archivist.config import update_config as _uc
    _uc(lambda c: c.setdefault("sources", []).append({"path": str(clips_b / "app"), "label": "x", "kind": "fixed", "enabled": True}))
    offered_source = clips_b.name in [b["name"] for b in ae.other_builds(cur)]
    _uc(lambda c: c.update(sources=[x for x in c.get("sources") or [] if x.get("path") != str(clips_b / "app")]))
    check("a version folder with the owner's files in it (or a Library source) is never offered for removal",
          offered_plain and not offered_clips and not offered_source and refused_clips,
          (offered_plain, offered_clips, offered_source, refused_clips))
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
        # a Start-menu entry rewritten by the app keeps the app id Setup gives it (notifications named MediaEngine)
        write_shell_link(d / "Меню.lnk", tgt, arg, str(d), "", "MediaEngine", app_id="MediaEngine.Desktop")
        back = read_shell_link(d / "Меню.lnk")
        check("shortcut carries the app id", "MediaEngine.Desktop".encode("utf-16-le") in (d / "Меню.lnk").read_bytes()
              and back["arguments"] == arg, back)
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
          "confirm('Отметить выбранное как личное навсегда? Оно уйдёт из библиотеки и никогда не попадёт в ролики.')" in out and "window.ME_I18N" in out and "Сначала выбери файлы" in out)
    # a build left "running" by a crashed process is marked interrupted by the first page the new process serves
    # (any page - Quit/Restart/switching builds would otherwise be refused for a job that no longer exists)
    from archivist.db import db as _db, now_iso as _now
    ae.ensure_schema()
    # a restart (Quit, Update, a Windows reboot) during an overnight set: the running build is interrupted, the
    # waiting ones stay waiting (QA review 2026-10-17: every waiting build was failed too)
    with _db() as con:
        pq_ = con.execute("INSERT INTO ae_projects(title,folder,created_at,updated_at) VALUES('q',?,?,?)", (str(work), _now(), _now())).lastrowid
        jr_ = con.execute("INSERT INTO ae_jobs(project_id,request_key,settings_json,status,stage,created_at,started_at) "
                          "VALUES(?,'kr','{}','running','analyze',?,?)", (pq_, _now(), _now())).lastrowid
        jq_ = con.execute("INSERT INTO ae_jobs(project_id,request_key,settings_json,status,stage,created_at) "
                          "VALUES(?,'kq','{}','queued','queued',?)", (pq_, _now())).lastrowid
        con.commit()
    ae._SCHEMA_READY = False
    ae.ensure_schema()
    st_r, st_q = ae.job(jr_)["status"], ae.job(jq_)["status"]
    with _db() as con:                           # never built here (no worker started in this check)
        con.execute("DELETE FROM ae_jobs WHERE id IN (?,?)", (jr_, jq_)); con.execute("DELETE FROM ae_projects WHERE id=?", (pq_,)); con.commit()
    check("restart: the running build is interrupted, waiting builds keep waiting", st_r == "failed" and st_q == "queued", (st_r, st_q))
    # the cut pieces of other projects are kept to a limit, oldest first; never the project being built
    fq_ = ae.AE_ROOT / "p999001" / "work" / "full_quality"; fq_.mkdir(parents=True, exist_ok=True)
    kp_ = ae.AE_ROOT / "p999002" / "work" / "segment_cache_v2"; kp_.mkdir(parents=True, exist_ok=True)
    (fq_ / "a.mp4").write_bytes(b"0" * 1000); (fq_ / "a.mp4.sha256").write_text("x"); (fq_ / "b.mp4").write_bytes(b"0" * 1000)
    (kp_ / "k.mp4").write_bytes(b"0" * 5000)
    os.utime(fq_ / "a.mp4", (1_600_000_000, 1_600_000_000))
    freed_ = ae.tidy_work_caches(keep_pid=999002, max_bytes=1500, min_free_bytes=0)
    check("cut pieces of other projects kept to a limit, oldest first, never the one being built",
          freed_ == 1000 and not (fq_ / "a.mp4").exists() and not (fq_ / "a.mp4.sha256").exists() and (fq_ / "b.mp4").exists()
          and (kp_ / "k.mp4").exists(), (freed_, sorted(x.name for x in fq_.iterdir())))
    shutil.rmtree(ae.AE_ROOT / "p999001", ignore_errors=True); shutil.rmtree(ae.AE_ROOT / "p999002", ignore_errors=True)
    _ph = ae._private_hashes
    try:      # a video marked Private while its reel was being built: that reel is never kept or saved
        ae._private_hashes = lambda: ["aa11"]
        res_p = {"inputs": [{"name": "a.mp4", "sha256": "AA11"}, {"name": "b.mp4", "sha256": "bb22"}],
                 "segments": [{"source_name": "a.mp4"}, {"source_name": "b.mp4"}]}
        hit, miss = ae.private_in_result(res_p), ae.private_in_result({**res_p, "segments": [{"source_name": "b.mp4"}]})
        refused = False
        try:
            ae._refuse_private({"result": res_p})
        except ValueError:
            refused = True
    finally:
        ae._private_hashes = _ph
    check("a reel with a video marked Private since is not kept or saved", hit == ["a.mp4"] and miss == [] and refused, (hit, miss, refused))
    import importlib as _il
    _web_mod = _il.import_module("archivist.auto_edit_web")
    check("times never show 0:60.0", _web_mod._fmt_s(59.97) == "1:00.0" and _web_mod._fmt_s(119.96) == "2:00.0"
          and _web_mod._fmt_s(59.94) == "0:59.9", (_web_mod._fmt_s(59.97), _web_mod._fmt_s(119.96), _web_mod._fmt_s(59.94)))
    check("paths in error messages stay as they are in Russian", "<span translate='no'>C:\\Music\\Only you.mp3</span>"
          in _web_mod._protect_paths("Music file not found: C:\\Music\\Only you.mp3"), _web_mod._protect_paths("Music file not found: C:\\Music\\Only you.mp3"))
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
    for name in ("Дача 15.08 с мамой.webm", "клип 1.5 МБ (копия).mp4"):     # decimal comma never touches a file name
        got = _i18n.translate_json({"message": "Importing " + name})["message"]
        check(f"ru: file name kept exactly ({name})", got.endswith(" " + name), got)
    check("ru: decimal comma with units", _i18n.translate_text("Social HD · 21.9 s (requested 30 s) · sound auto", True)
          == "Social HD · 21,9 с (выбрано 30 с) · звук авто", _i18n.translate_text("Social HD · 21.9 s (requested 30 s) · sound auto", True))
    prep = _i18n.translate_json({"message": "Preparing a recording without a length: it's [1] 1.5 s.webm"})["message"]
    check("ru: preparing a recording without a length (file name kept)", prep == "Подготовка записи без длины: it's [1] 1.5 s.webm", prep)
    long = _i18n.translate_text("Requested 15 s, got 9.7 s: there were not enough different moments in this footage for a longer reel.", True)
    check("ru: short-reel note fully Russian", not _re.search(r"[A-Za-z]{3,}", long), long)
    # copies of the database and settings: one a day, one before a different build uses them; a missing data folder
    # and a damaged database are said on every page
    import sqlite3 as _sq
    from archivist import backup as _bk, config as _cfg, web as _web
    _cfg.ensure_dirs()
    _c = _sq.connect(str(_cfg.DB_PATH)); _c.execute("create table if not exists bk_probe(x)"); _c.commit(); _c.close()
    first = _bk.at_start("unit-1"); again = _bk.at_start("unit-1"); other = _bk.at_start("unit-2")
    check("backup: daily copy once, build copy on a different build", "daily" in first and "daily" not in again and "build" not in again
          and "build" in other and Path(other["build"]).is_file(), (first, again, other))
    _cfg.DATA_ROOT_NOTE.update(missing="E:\\MediaEngine Data", using="D:\\projects\\medeng\\MediaEngine Data")
    try:
        with _web.create_app().test_request_context("/"):
            page = _web.layout("t", "<p>x</p>")
        ru = _i18n.translate_text("Connect that disk (or put the folder back) and restart MediaEngine. Until then an empty folder is used:", True)
        check("missing data folder said on every page", "Your projects are not shown." in page and "E:\\MediaEngine Data" in page
              and not _re.search(r"[A-Za-z]{3,}", ru.replace("MediaEngine", "")), ru)
    finally:
        _cfg.DATA_ROOT_NOTE.clear()
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
    # cuts on the beat (engine_p11/p13_beats.py): a click track's beats to within 10 ms, a jingle or a tone has no
    # beat (and never an error), and moving every cut to a beat keeps the reel within about a beat and a half of
    # its planned length at any tempo, also when the moments cannot get longer
    import wave
    import numpy as np
    sys.path.insert(0, str(ROOT / "app" / "archivist" / "engine_p11"))
    import p13_beats as beats
    bd = work / "beats"; bd.mkdir(parents=True, exist_ok=True)

    def wav(path, x, sr=48000):
        y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(np.stack([y, y], 1).tobytes())
    sr = 48000
    clicks = np.zeros(20 * sr, np.float32)
    truth = [0.31 + k * 0.6 for k in range(32)]
    for t in truth:
        i = int(t * sr); n = np.arange(480)
        clicks[i:i + 480] += 0.8 * np.sin(2 * np.pi * 1500 * n / sr) * np.exp(-n / 96.0)
    wav(bd / "clicks.wav", clicks)
    r = beats.detect(bd / "clicks.wav")
    err = [min(abs(b - t) for b in r["beats"]) for t in truth[2:-2]] if r["beats"] else [1.0]
    check("beats: click track found to within 10 ms", r["clear"] and abs(r["bpm"] - 100) < 1 and max(err) <= 0.01, (r["bpm"], max(err)))
    for name, x in (("a 0.3 s jingle", clicks[: int(0.3 * sr)]), ("a 0.05 s blip", clicks[: int(0.05 * sr)]),
                    ("a 10 s tone", 0.3 * np.sin(2 * np.pi * 440 * np.arange(10 * sr) / sr))):
        wav(bd / "short.wav", x.astype(np.float32))
        try:
            ok = beats.detect(bd / "short.wav")["clear"] is False
        except Exception as exc:
            ok = exc
        check(f"beats: {name} has no beat and is no error", ok is True, ok)
    worst = 0.0
    rng = np.random.default_rng(3)
    for bpm in (55, 70, 100, 118, 140):
        bt = [0.2 + k * 60.0 / bpm for k in range(600)]
        for room in (0.5, 0.0):
            for durs in ([5.0] * 13, list(rng.uniform(2.5, 6.0, 13))):
                tr = [8 / 30] * 12
                pl = beats.plan(durs, tr, [x + room for x in durs], bt)
                worst = max(worst, abs(sum(u for u, _ in pl) - sum(durs)) - beats.max_offset(bt))
    check("beats: the reel stays within a beat and a half of its planned length", worst <= 0.05, worst)
    # a path that cannot even be looked at (locked drive, no permission, name too long) counts as not there - one such
    # Library row made a page fail and the start-up check then refused to start the app
    odd_ = work / ("n" * 300) / "x.mp4"
    check("an unreadable path is simply not there", odd_.exists() is False and odd_.is_file() is False and odd_.is_dir() is False
          and work.is_dir())
    # Settings: sources are added only as existing full folders, once; Remove needs the row's position and path
    from archivist import web as _web
    from archivist.config import load_config, update_config, archive_root
    update_config(lambda c: c.update(sources=[]))
    srcd = work / "Мои видео"; srcd.mkdir(exist_ok=True)
    errs_ = [_web._add_source({"path": str(srcd)}), _web._add_source({"path": str(srcd) + os.sep}),
             _web._add_source({"path": "relative\\folder"}), _web._add_source({"path": str(work / "no such")})]
    got_src = [x["path"] for x in load_config()["sources"]]
    check("settings: a source is an existing full folder, added once", got_src == [str(srcd.resolve())] and errs_[0] == ""
          and errs_[1] == "" and errs_[2] and errs_[3], (got_src, errs_))
    _web._add_source({"path": str(work)})
    _web._remove_source({"index": "0", "path": "something else"})          # a page from before: wrong row, nothing removed
    _web._remove_source({})                                                 # no position: nothing removed
    n_before = len(load_config()["sources"])
    _web._remove_source({"index": "0", "path": str(srcd.resolve())})
    check("settings: Remove takes exactly the row that was shown", n_before == 2
          and [x["path"] for x in load_config()["sources"]] == [str(work.resolve())], load_config()["sources"])
    # the watchdog: a Library task still reading its file, a PC back from sleep, or a reel being made is never "stalled"
    from archivist import watchdog as _wd, media as _md
    t0_ = _md.io_ticks(); _md.sha256_file(work / "files" / "a.mp4")
    check("watchdog: hashing moves the alive counter; late tasks are restarted only when nothing says they live",
          _md.io_ticks() > t0_ and _wd.verdict("import", 10, 300, False, False, lambda: "") == "ok"
          and _wd.verdict("import", 400, 300, True, False, lambda: "") == "touch"
          and _wd.verdict("import", 400, 300, False, True, lambda: "") == "touch"
          and _wd.verdict("import", 400, 300, False, False, lambda: "reel") == "touch"
          and _wd.verdict("import", 400, 300, False, False, lambda: "") == "recover"
          and _wd.verdict("convert", 100, 90, False, True, lambda: "reel") == "recover"
          and _wd.verdict("convert", 100, 90, True, False, lambda: "") == "touch")
    # a swapped card / reset phone: the same path with another file gets a row of its own (never the old one's
    # Rejected / Private / picture); a FAT32 card's hour shift across daylight saving is the same file
    from archivist.db import db as _db, init_db as _init_db, upsert_inventory as _ups
    _init_db()
    key_ = "local:e:\\dcim\\100media\\vid_0001.mp4"
    base_row = {"source_key": key_, "source_kind": "removable", "source_id": "E:\\", "source_label": "SD E:", "path": "E:\\DCIM\\100MEDIA\\VID_0001.MP4",
                "filename": "VID_0001.MP4", "ext": ".mp4", "media_type": "video", "size_bytes": 1000, "mtime": 1700000000.0}
    with _db() as con_:
        _ups(con_, base_row); con_.commit()
        id1 = con_.execute("SELECT id FROM inventory WHERE source_key=?", (key_,)).fetchone()[0]
        con_.execute("UPDATE inventory SET excluded=1, rejected_path='R', analysis_status='rejected' WHERE id=?", (id1,))
        con_.execute("INSERT OR IGNORE INTO ignored_source_keys(source_key, created_at) VALUES(?, '2026-01-01')", (key_,))
        con_.commit()
        _ups(con_, dict(base_row, mtime=1700003600.0)); con_.commit()          # the hour shift: the same file
        same_ = con_.execute("SELECT id FROM inventory WHERE source_key=?", (key_,)).fetchone()[0]
        _ups(con_, dict(base_row, size_bytes=2000, mtime=1710000000.0)); con_.commit()   # another card's VID_0001.MP4
        new_ = dict(con_.execute("SELECT id, excluded, rejected_path, analysis_status FROM inventory WHERE source_key=?", (key_,)).fetchone())
        moved_ = con_.execute("SELECT COUNT(*) FROM ignored_source_keys WHERE source_key=?", (key_,)).fetchone()[0]
    check("swapped card: a new file at a known path is new (not Rejected, not Private); an hour shift is the same file",
          same_ == id1 and new_["id"] != id1 and not new_["excluded"] and not new_["rejected_path"]
          and new_["analysis_status"] != "private" and moved_ == 0, (same_, id1, new_, moved_))
    # Private / Rejected copies: two cards' VID_0001.mp4 never share one name; a move never replaces a different file
    from archivist import service as _sv
    fold_ = work / "priv_names"; fold_.mkdir(exist_ok=True)
    taken_ = []
    for k_ in range(4):
        d_ = _sv._free_name(fold_, "VID_0001.mp4", ["unknown", "unknown_7"])
        d_.write_bytes(bytes([k_]) * 10); taken_.append(d_.name)
    a_ = work / "mv_a.bin"; a_.write_bytes(b"A" * 50)
    try:
        _sv._verified_move(a_, fold_ / "VID_0001.mp4")
        refused_mv = False
    except RuntimeError:
        refused_mv = True
    check("Private / Rejected names never repeat; a move never replaces a different file",
          taken_ == ["VID_0001.mp4", "VID_0001_unknown.mp4", "VID_0001_unknown_7.mp4", "VID_0001_unknown_7_2.mp4"]
          and refused_mv and a_.is_file()
          and (fold_ / "VID_0001.mp4").read_bytes() == bytes([0]) * 10, taken_)
    update_config(lambda c: c.update(archive_root=str(work / "Архив")))
    check("archive folder: one reading for the whole app", archive_root() == work / "Архив")
    # converted files: each one has "Show in folder" / "Open video" (found by its job and place, never by a path from
    # the page), the Convert page opens the Converted folder, and a finished job keeps its list after the page reloads
    import json as _js
    from archivist import auto_edit as _ae2, config as _cfg2
    conv_ = _cfg2.HOME / "Converted"; conv_.mkdir(parents=True, exist_ok=True)
    made_ = conv_ / "работа_share_1080p.mp4"; made_.write_bytes(b"x" * 10)
    outs_ = [{"source": "C:\\work\\работа.mp4", "output": str(made_), "source_bytes": 50 * 2**20, "output_bytes": 2 * 2**20, "saved_percent": 96.0},
             {"source": "C:\\work\\broken.mp4", "error": "Could not read video duration"},
             {"source": "C:\\work\\gone.mp4", "output": str(conv_ / "gone_share_1080p.mp4"), "source_bytes": 9, "output_bytes": 3, "saved_percent": 66.7}]
    with _db() as con:
        cj_ = con.execute("INSERT INTO jobs(kind,status,created_at,finished_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json) "
                          "VALUES('convert','finished',?,?,'done','Finished',3,3,2,1,1,1,?)", (_now(), _now(), _js.dumps({"outputs": outs_}))).lastrowid
        con.commit()
    opened_ = []
    real_open_ = _ae2.open_path
    _ae2.open_path = lambda path, reveal=False: opened_.append((str(path), reveal))
    try:
        H_ = {"Host": "127.0.0.1:8765"}
        with _ca().test_client() as _c:
            r1 = _c.post("/api/convert/reveal", json={"job": cj_, "i": 0}, headers=H_)
            r2 = _c.post("/api/convert/reveal", json={"job": cj_, "i": 0, "open": True}, headers=H_)
            r3 = _c.post("/api/convert/reveal", json={"job": cj_, "i": 1}, headers=H_)        # a failed one: no file
            r4 = _c.post("/api/convert/reveal", json={"job": cj_, "i": 2}, headers=H_)        # the file was deleted
            r5 = _c.post("/api/convert/reveal", json={"job": "x", "i": 0, "path": "C:\\Windows"}, headers=H_)
            r6 = _c.post("/api/convert/reveal", json={"job": cj_, "i": -1}, headers=H_)
            r7 = _c.post("/api/convert/open-folder", headers=H_)
            page_ = _c.get("/convert", headers=H_).get_data(as_text=True)
        check("convert: show a converted file in its folder, play it, open the Converted folder",
              [x.status_code for x in (r1, r2, r3, r4, r5, r6, r7)] == [200, 200, 404, 404, 400, 404, 200]
              and opened_ == [(str(made_), True), (str(made_), False), (str(conv_), False)], ([x.status_code for x in (r1, r2, r3, r4, r5, r6, r7)], opened_))
        check("convert: the last job keeps its files with the buttons after a reload",
              f"data-job='{cj_}' data-done='1'" in page_ and "data-cv='reveal' data-i='0'" in page_ and "data-i='1'" not in page_
              and "data-i='2'" not in page_ and "The file is no longer there." in page_ and "data-cv='folder'" in page_
              and "broken.mp4" in page_ and str(made_) in page_, page_[page_.find("convertStatus") - 40:][:600])
        with _ca().test_client() as _c:
            h1 = _c.post("/api/convert/hide", json={"job": "x"}, headers=H_).status_code
            h2 = _c.post("/api/convert/hide", json={"job": cj_ + 99}, headers=H_).status_code
            h3 = _c.post("/api/convert/hide", json={"job": cj_}, headers=H_).status_code
            gone_ = "data-done='1'" not in _c.get("/convert", headers=H_).get_data(as_text=True)
        check("convert: a finished job's list can be taken off the page (files stay)", (h1, h2, h3, gone_) == (400, 404, 200, True)
              and made_.is_file(), (h1, h2, h3, gone_))
        # "Choose videos on this PC…": the Windows Open window gives the files (never the page); nothing chosen says so;
        # the page's preset, size and "Join into one video" go with them; the order of a GoPro recording; Stop on a
        # running job's card, the join choice and the hint on the page
        from archivist import converter as _cv
        calls_ = []
        real_pick_, real_start_ = _ae2.pick_files, _web.start_convert_job
        try:
            _ae2.pick_files = lambda *a, **k: []
            with _ca().test_client() as _c:
                n1 = _c.post("/api/convert/pick", json={"preset": "small_720p"}, headers=H_).get_json()
            _ae2.pick_files = lambda *a, **k: ["C:\\Work\\GX020044.MP4", "C:\\Work\\GX010044.MP4"]
            _web.start_convert_job = lambda ids, preset, target, paths=None, join=False, cuts=None: calls_.append((ids, preset, target, paths, join)) or 77
            with _ca().test_client() as _c:
                n2 = _c.post("/api/convert/pick", json={"preset": "small_720p", "target_mb": 300, "join": True}, headers=H_).get_json()
                n3 = _c.post("/api/convert/start", json={"ids": [5, 6], "preset": "hq_1080p", "join": "yes"}, headers=H_).get_json()
        finally:
            _ae2.pick_files, _web.start_convert_job = real_pick_, real_start_
        check("convert: files chosen on this PC go with the page's choices; nothing chosen says so",
              n1 == {"ok": False, "error": "No videos chosen."} and n2 == {"ok": True, "job_id": 77} and n3 == {"ok": True, "job_id": 77}
              and calls_ == [([], "small_720p", 300, ["C:\\Work\\GX020044.MP4", "C:\\Work\\GX010044.MP4"], True),
                             ([5, 6], "hq_1080p", None, None, False)], (n1, n2, n3, calls_))
        order_ = sorted(["GX040044.MP4", "GX010044.MP4", "GX030044.MP4", "GX020044.MP4"], key=_cv.part_key)
        check("convert: parts of one GoPro recording in its order (older GoPros too), other files by name",
              order_ == ["GX010044.MP4", "GX020044.MP4", "GX030044.MP4", "GX040044.MP4"]
              and sorted(["GP010012.MP4", "GOPR0012.MP4"], key=_cv.part_key) == ["GOPR0012.MP4", "GP010012.MP4"]
              and sorted(["clip 10.mp4", "clip 2.mp4"], key=_cv.part_key) == ["clip 2.mp4", "clip 10.mp4"]
              and _cv.gopro_recording(order_) == "0044" and _cv.gopro_recording(["GX010044.MP4", "GX010045.MP4"]) is None
              and _cv.gopro_recording(["GX010044.MP4"]) is None, order_)
        # the folder converted videos go into: chosen in the folder window, not in the library, not the program folder
        from archivist import config as _cfg3
        real_pf_ = _ae2.pick_folder
        lib_ = work / "lib_src"; lib_.mkdir(exist_ok=True)
        mine_ = work / "Мои сжатые"
        answers_ = [None, str(lib_ / "sub"), str(_cfg3.INSTALL / "x"), str(mine_)]
        update_config(lambda c: c.update(sources=[{"label": "lib", "path": str(lib_)}]))
        try:
            _ae2.pick_folder = lambda *a, **k: answers_.pop(0)
            with _ca().test_client() as _c:
                f1 = _c.post("/api/convert/output-folder", json={}, headers=H_).get_json()
                f2 = _c.post("/api/convert/output-folder", json={}, headers=H_).get_json()
                f3 = _c.post("/api/convert/output-folder", json={}, headers=H_).get_json()
                f4 = _c.post("/api/convert/output-folder", json={}, headers=H_).get_json()
                pg_ = _c.get("/convert", headers=H_).get_data(as_text=True)
                now_ = _cv.output_folder()
                f5 = _c.post("/api/convert/output-folder", json={"reset": True}, headers=H_).get_json()
                pg2_ = _c.get("/convert", headers=H_).get_data(as_text=True)
        finally:
            _ae2.pick_folder = real_pf_
            update_config(lambda c: c.update(sources=[]))
        check("convert: the output folder is chosen in the folder window, never a library or program folder; back to Converted",
              f1 == {"ok": False, "error": "No folder chosen."} and "in the library" in f2["error"] and "program folder" in f3["error"]
              and f4 == {"ok": True, "path": str(mine_.resolve())} and now_ == mine_.resolve() and str(mine_.resolve()) in pg_
              and "data-cv='outdir-reset'" in pg_ and f5["ok"] and _cv.output_folder() == _cfg3.HOME / "Converted"
              and "data-cv='outdir-reset'" not in pg2_, (f1, f2, f3, f4, now_, f5))
        # "Copy file": the file on the Windows clipboard as Explorer's Ctrl+C puts it (a name with Cyrillic letters)
        okc_ = False
        if os.name == "nt":
            from archivist.platform_adapter import copy_files_to_clipboard, clipboard_files
            okc_ = copy_files_to_clipboard([made_])
            back_ = clipboard_files()
            if okc_:
                check("convert: Copy file puts the file on the Windows clipboard (Ctrl+V pastes it)", back_ == [str(made_.resolve())], back_)
            else:
                print("INFO no clipboard on this machine (no desktop): Copy file not checked here", flush=True)
        with _ca().test_client() as _c:
            cr_ = _c.post("/api/convert/reveal", json={"job": cj_, "i": 0, "copy": True}, headers=H_)
        check("convert: Copy file asks for the file by its job and place (no clipboard: said, not a crash)",
              cr_.status_code == (200 if okc_ else 409), (cr_.status_code, cr_.get_json()))
        sw_ = work / "sweep_mine"; sw_.mkdir(exist_ok=True)
        for n_, data_ in (("a_share_1080p.mp4", b""), ("b_share_1080p.part.mp4", b"x"), ("holiday.mp4", b""), ("c_small_720p_2.mp4", b"x"),
                          ("d_target_300mb.mp4", b"")):
            (sw_ / n_).write_bytes(data_)
        _cv._sweep_ours(sw_)
        check("convert: after a restart only the converter's own leftovers go from a chosen folder",
              sorted(x.name for x in sw_.iterdir()) == ["c_small_720p_2.mp4", "holiday.mp4"], sorted(x.name for x in sw_.iterdir()))
        # a cut (start, end) only for the selected library videos, checked against the video's length
        with _db() as con:
            vid_ = con.execute("INSERT INTO inventory(source_key,source_id,source_label,source_kind,path,filename,media_type,size_bytes,duration_ms,mtime,discovered_at,last_seen_at) "
                               "VALUES('cut-test','t','t','fixed',?,'cutme.mp4','video',1000,60000,0,?,?)", (str(made_), _now(), _now())).lastrowid
            con.commit()
        cc1 = _cv._clean_cuts({str(vid_): [5, 61], "999999": [1, 2]}, [vid_])
        msgs_ = []
        for bad_ in ({str(vid_): [59.8, 70]}, {str(vid_): [10, 10.2]}, {str(vid_): ["x", 3]}, [1, 2]):
            try:
                _cv._clean_cuts(bad_, [vid_]); msgs_.append(None)
            except ValueError as exc:
                msgs_.append(str(exc))
        try:
            _cv.start_convert_job([vid_, vid_ + 1], "small_720p", join=True, cuts={str(vid_): [1, 5]}); jc_ = None
        except ValueError as exc:
            jc_ = str(exc)
        check("convert: a cut is checked (inside the video, half a second at least) and not with a join",
              cc1 == {str(vid_): [5.0, 60.0]} and msgs_ == ["The cut starts after the end of the video: cutme.mp4",
                                                            "The cut must be at least half a second: cutme.mp4", "Unknown cut", "Unknown cut"]
              and jc_ == "A cut works when the videos are converted one by one (not joined into one).", (cc1, msgs_, jc_))
        calls2_ = []
        real_start2_ = _web.start_convert_job
        _web.start_convert_job = lambda ids, preset, target, paths=None, join=False, cuts=None: calls2_.append((ids, cuts)) or 5
        try:
            with _ca().test_client() as _c:
                _c.post("/api/convert/start", json={"ids": [vid_], "preset": "small_720p", "cuts": {str(vid_): [1.5, 7]}}, headers=H_)
                cpage_ = _c.get("/convert", headers=H_).get_data(as_text=True)
        finally:
            _web.start_convert_job = real_start2_
        check("convert: the page's cuts reach the job; a video on the page has Cut…",
              calls2_ == [([vid_], {str(vid_): [1.5, 7]})] and f"data-cut-for='{vid_}'" in cpage_, (calls2_, f"data-cut-for='{vid_}'" in cpage_))
        gp_ = lambda **k: _cv.gpu_plan({"video": "hevc", "pix": "yuvj420p", "size": "3840x2160", "sar": "1:1", "rotation": 0, **k}, "share_1080p")
        check("convert: the NVIDIA way only for what it does surely (8-bit H.264/HEVC made smaller, upright, square pixels)",
              gp_()["size"] == (1920, 1080) and gp_(size="2160x3840")["size"] == (1080, 1920) and gp_(size="2704x1520")["size"] == (1920, 1078)
              and "out_range=tv" in gp_()["vf"] and gp_()["codec"][gp_()["codec"].index("-cq") + 1] == "27"
              and gp_(pix="yuv420p10le") is None and gp_(rotation=90) is None and gp_(sar="4:3") is None and gp_(video="prores") is None
              and gp_(size="1920x1080") is None
              and _cv.gpu_plan({"video": "h264", "pix": "yuv420p", "size": "3840x2160", "sar": "1:1", "rotation": 0}, "keep_resolution") is None
              and _cv.gpu_plan({"video": "h264", "pix": "yuv420p", "size": "3840x2160", "sar": "1:1", "rotation": 0}, "share_1080p", hdr="HLG") is None,
              gp_())
        update_config(lambda c: c.setdefault("convert", {}).update(gpu=False))
        off_ = _cv.gpu_ok()
        update_config(lambda c: c["convert"].pop("gpu", None))
        check("convert: the NVIDIA way can be turned off (convert.gpu = false)", off_ is False, off_)
        try:
            _cv.start_convert_job([], "small_720p", paths=[str(made_)], join=True)
            one_ = None
        except ValueError as exc:
            one_ = str(exc)
        try:
            _cv.start_convert_job([], "small_720p", paths=[str(conv_ / "nothing here.mp4")])
            gone2_ = None
        except ValueError as exc:
            gone2_ = str(exc)
        check("convert: a join needs two videos; a chosen file that is gone is named", one_ == "Choose at least two videos to join into one"
              and gone2_ == "This video is not there: nothing here.mp4", (one_, gone2_))
        with _db() as con:
            rj_ = con.execute("INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,bytes_done,options_json) "
                              "VALUES('convert','running',?,?,'converting','Joining 4 parts · 12%',1,0,0,0,100,12,?)", (_now(), _now(), _js.dumps({"join": True}))).lastrowid
            con.commit()
        with _ca().test_client() as _c:
            page2_ = _c.get("/convert", headers=H_).get_data(as_text=True)
        with _db() as con:
            con.execute("UPDATE jobs SET status='cancelled' WHERE id=?", (rj_,)); con.commit()
        import time as _tm
        from archivist import notify as _nf
        _cv._RUN_START[999] = (_tm.time() - 60, 0)
        eta_ = _cv.eta_seconds({"id": 999, "status": "running", "bytes_total": 1000, "bytes_done": 250})
        eta_new_ = _cv.eta_seconds({"id": 999, "status": "running", "bytes_total": 1000, "bytes_done": 10})
        _cv._RUN_START[999] = (_tm.time() - 5, 0)
        eta_early_ = _cv.eta_seconds({"id": 999, "status": "running", "bytes_total": 1000, "bytes_done": 500})
        _cv._RUN_START.pop(999, None)
        check("convert: time left from this run's pace (not in the first seconds, not before 2%)",
              eta_ is not None and 175 <= eta_ <= 185 and eta_new_ is None and eta_early_ is None, (eta_, eta_new_, eta_early_))
        shown_ = []
        real_show_ = _nf.show
        _nf.show = lambda title, text, url="", timeout_s=20: shown_.append((title, text, url)) or True
        try:
            import threading as _th
            a_ = _nf.convert_finished(4, 0, 0, 300, "http://127.0.0.1:8775/convert", True)
            b_ = _nf.convert_finished(1, 0, 4, 300, "u", False)
            c_ = _nf.convert_finished(4, 0, 0, 20, "u", True)            # under a minute: watched anyway
            update_config(lambda c: c.setdefault("auto_edit", {}).update(notify=False))
            d_ = _nf.convert_finished(4, 0, 0, 300, "u", True)
            update_config(lambda c: c.setdefault("auto_edit", {}).update(notify=True))
            for t_ in _th.enumerate():
                if t_.name == "notify":
                    t_.join(5)
        finally:
            _nf.show = real_show_
        check("convert: a Windows notification when a long conversion ends (off in Settings, not for a short one)",
              (a_, b_, c_, d_) == (True, True, False, False) and ("Конвертация готова", "Видео: 4 · нажми, чтобы открыть", "http://127.0.0.1:8775/convert") in shown_
              and ("Your videos are converted", "4 parts joined into one video · click to open", "u") in shown_, (a_, b_, c_, d_, shown_))
        check("convert: a running job has Stop; the page has Join into one video and Choose videos on this PC",
              f"data-job='{rj_}'" in page2_ and "data-cv='stop'" in page2_ and "id='joinOne'" in page2_ and "id='pickConvert'" in page2_,
              page2_[page2_.find("convertStatus") - 40:][:300])
    finally:
        _ae2.open_path = real_open_
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
