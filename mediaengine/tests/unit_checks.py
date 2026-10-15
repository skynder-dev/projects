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
                  and live.read_bytes() == orig and again == fixed and fixed[0].name == live.name and notes == [live.name]
                  and fixed[0].stat().st_mtime_ns == m1 and not (rw / "fixed_inputs" / "old removed.webm").exists(),
                  (fixed, changed, notes))
            (rw / "fixed_inputs" / (live.name + ".source.json")).write_text("", encoding="utf-8")   # damaged stamp (disk was full)
            third, _ = ae._with_length([live], rw, notes.append)
            check("recording without a length: a damaged stamp makes a new copy, never a failed build", third == fixed and len(notes) == 2,
                  (third, notes))
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
    st = ae.normalize_settings({"length": 15, "format": "social_hd", "sound": "auto", "mode": "technical", "theme": "sea"})
    check("a theme is dropped without AI+", "theme" not in st, st)
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
    # the shared AI cache: Private videos' reports and clips go, the longest unused clips go over the limit
    sh = ae.SHARED; cd_ = sh / "semantic_candidates"; rd_ = sh / "semantic_reports"
    cd_.mkdir(parents=True, exist_ok=True); rd_.mkdir(parents=True, exist_ok=True)
    pv, okv = "a" * 64, "b" * 64
    (rd_ / (pv + ".json")).write_text("{}"); (rd_ / (okv + ".json")).write_text("{}")
    for i, src_ in enumerate([pv, okv, okv, okv]):
        (cd_ / f"c{i}.mp4").write_bytes(b"x" * 1000)
        (cd_ / f"c{i}.json").write_text(json.dumps({"source_sha256": src_}))
        os.utime(cd_ / f"c{i}.json", (1000 + i, 1000 + i))
    ae.tidy_shared_cache([pv], max_clip_bytes=2000, min_free_bytes=0)
    left_ = sorted(x.name for x in cd_.glob("*.mp4"))
    check("shared AI cache: Private videos go, the longest unused clips go over the limit",
          not (rd_ / (pv + ".json")).exists() and (rd_ / (okv + ".json")).exists() and left_ == ["c2.mp4", "c3.mp4"], left_)
    shutil.rmtree(sh, ignore_errors=True)
    # a Windows notification after a long build (local only)
    from archivist import notify as _nt
    tx = _nt.toast_xml("A & B", "<x>", 'http://127.0.0.1:8775/auto/p/1?a=1&b="2"')
    check("notification text is escaped", "A &amp; B" in tx and "&lt;x&gt;" in tx and 'a=1&amp;b=&quot;2&quot;' in tx, tx)
    check("no notification after a short build", not _nt.reel_finished("t", True, 10, "http://x", False))
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
          "confirm('Отметить выбранное как личное навсегда? Оно уйдёт из библиотеки и никогда не попадёт в ролики.')" in out and "window.ME_I18N" in out and "Сначала выбери файлы" in out)
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
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
