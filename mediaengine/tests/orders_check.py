"""Orders from other programs, through the running app (Flask test client + the real Inbox watcher + real FFmpeg).

  python tests/orders_check.py --home <empty dir> --videos <folder of test videos> [--out report.json]

A program's view: it writes folders into MediaEngine Data\\Orders\\Inbox and waits for Done\\<id> or Failed\\<id>.
Covers: a video by plan (pictures + a piece of a video + narration) with frame-exact length, a plan given as a file
with extra fields, a one-file order, a reel from a folder (a normal project; the answer is that project's version),
22 kinds of bad orders refused with the right code and nothing made, an order still being copied is not taken,
"Wait for my OK" (Run, Reject, no retry of a rejected one), Stop in the middle and Run again, fix + Try again,
an order interrupted by a restart is done again, Delete, the pages and the API, the test videos unchanged.
Exit code 0 only if every check passes.
"""
from __future__ import annotations

import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True)
    ap.add_argument("--videos", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    home = Path(a.home).resolve()
    home.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(home)
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.web import create_app
    from archivist import auto_edit as ae, orders

    videos = Path(a.videos).resolve()
    vids = sorted(p for p in videos.iterdir() if p.is_file() and p.suffix.lower() in ae.SUPPORTED)
    before = {p.name: sha(p) for p in videos.iterdir() if p.is_file()}
    ff = ae._ffmpeg() or "ffmpeg"
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    checks = []

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def run(cmd):
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    src = home.parent / (home.name + "-src")
    shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    run([ff, "-y", "-f", "lavfi", "-i", "color=c=0x1b2a44:s=1080x1920", "-frames:v", "1", str(src / "a.png")])
    run([ff, "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1350", "-frames:v", "1", str(src / "b.png")])
    run([ff, "-y", "-f", "lavfi", "-i", "sine=f=330:d=9.3", "-ar", "22050", str(src / "voice.wav")])
    (src / "not_a_picture.png").write_text("this is text", encoding="utf-8")
    long_clip = src / "long.mp4"
    run([ff, "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=12", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(long_clip)])
    # files that try to make FFmpeg read something OUTSIDE the order folder (a "Private" video of the owner)
    secret = home.parent / (home.name + "-private") / "secret.mp4"
    secret.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(long_clip, secret)
    (src / "playlist.m3u8").write_text(f"#EXTM3U\n#EXT-X-TARGETDURATION:12\n#EXTINF:12.0,\n{secret.as_posix()}\n#EXT-X-ENDLIST\n",
                                       encoding="utf-8")
    (src / "list.ffconcat").write_text(f"ffconcat version 1.0\nfile '{secret.as_posix()}'\n", encoding="utf-8")
    run([ff, "-y", "-f", "lavfi", "-i", "color=c=gray:s=8000x8000", "-frames:v", "1", str(src / "huge.png")])

    inbox = None

    def put(oid, order, files=(), raw=None, single=False):
        """As a program does it: files first, order.json last (here: built aside, moved in at once)."""
        tmp = home / f"_build_{oid}"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        for rel, srcfile in files:
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(srcfile, tmp / rel)
        text = raw if raw is not None else json.dumps(order, ensure_ascii=False, indent=1)
        if single:
            (inbox / f"{oid}.json").write_text(text, encoding="utf-8")
            shutil.rmtree(tmp)
            return
        (tmp / "order.json").write_text(text, encoding="utf-8")
        os.replace(tmp, inbox / oid)

    def answer(oid, limit=900):
        t0 = time.time()
        while time.time() - t0 < limit:
            for state, d in (("done", orders.done_dir()), ("failed", orders.failed_dir())):
                if (d / oid / "result.json").is_file():
                    return state, json.loads((d / oid / "result.json").read_text(encoding="utf-8"))
            time.sleep(0.5)
        return "timeout", {}

    def frames_of(p):
        cp = subprocess.run([ff, "-hide_banner", "-nostdin", "-i", str(p), "-map", "0:v:0", "-f", "null", "-"],
                            capture_output=True, text=True, errors="replace")
        m = re.findall(r"frame=\s*(\d+)", cp.stderr or "")
        return int(m[-1]) if m else -1

    PLAN = {"schema": orders.SCHEMA, "kind": "render_plan", "from": "orders_check", "title": "Plan with a narration",
            "plan": {"width": 1080, "height": 1920, "fps": 30, "audio": "audio/voice.wav",
                     "clips": [{"still": "stills/a.png", "start_s": 0, "end_s": 2.5},
                               {"video": "clips/long.mp4", "from_s": 4.0, "start_s": 2.5, "end_s": 5.25},
                               {"still": "stills/b.png", "start_s": 5.25, "end_s": 8.016}]}}
    PLAN_FILES = [("stills/a.png", src / "a.png"), ("stills/b.png", src / "b.png"), ("clips/long.mp4", long_clip),
                  ("audio/voice.wav", src / "voice.wav")]

    app = create_app()
    with app.test_client() as c:
        r = c.get("/auto/orders", headers=H)
        check("orders_page_renders_and_starts_watching", r.status_code == 200 and b"Orders" in r.data, r.status_code)
        inbox = orders.inbox_dir()
        check("orders_folders_made", all(d.is_dir() for d in (inbox, orders.received_dir(), orders.done_dir(), orders.failed_dir()))
              and (orders.root() / "README.txt").is_file()
              and (orders.root() / "ORDERS.md").read_bytes() == (ROOT / "app" / "archivist" / "ORDERS.md").read_bytes())
        r = c.get("/auto", headers=H)
        check("auto_home_links_orders", r.status_code == 200 and b"/auto/orders" in r.data)

        # 1. a video by plan
        put("plan-1", PLAN, PLAN_FILES)
        st, res = answer("plan-1")
        out = orders.done_dir() / "plan-1" / "video.mp4"
        check("plan_done", st == "done" and out.is_file(), res.get("error"))
        if st == "done":
            v = res["video"]
            check("plan_receipt_sha_matches_file", v["sha256"] == sha(out), v)
            check("plan_all_checks_pass", all(x["pass"] for x in res["checks"]) and len(res["checks"]) >= 5, res["checks"])
            check("plan_size_1080x1920", (v["width"], v["height"]) == (1080, 1920), v)
            n = frames_of(out)
            check("plan_frame_exact_length", n == round(8.016 * 30), f"{n} frames, planned {round(8.016 * 30)}")
            check("plan_receipt_has_order_identity", res.get("order_sha256") == sha(orders.done_dir() / "plan-1" / "order.json")
                  and res.get("kind") == "render_plan" and res.get("from") == "orders_check", res.get("order_sha256"))
            check("plan_order_files_kept_in_received", (orders.received_dir() / "plan-1" / "stills" / "a.png").is_file())
            check("plan_no_partial_left", not any(p.name.startswith(".") for p in orders.done_dir().iterdir()))

        # 2. plan as a separate file with fields MediaEngine does not know (a timeline made by another program)
        tl = {"preset": "social_hd", "width": 720, "height": 1280, "fps": 25, "target_seconds": 3.0, "audio": "voice.wav",
              "clips": [{"still": "s/a.png", "start_s": 0, "end_s": 1.5, "voice": "x.wav"},
                        {"still": "s/b.png", "start_s": 1.5, "end_s": 3.0}]}
        tlf = home / "_timeline.json"
        tlf.write_text(json.dumps(tl), encoding="utf-8")
        put("plan-file", {"schema": orders.SCHEMA, "kind": "render_plan", "plan": "timeline.json"},
            [("timeline.json", tlf), ("s/a.png", src / "a.png"), ("s/b.png", src / "b.png"), ("voice.wav", src / "voice.wav")])
        st, res = answer("plan-file")
        check("plan_from_file_done_720x1280_audio_cut_to_plan", st == "done" and (res["video"]["width"], res["video"]["height"]) == (720, 1280)
              and abs(res["video"]["duration_s"] - 3.0) < 0.1, res.get("error") or res.get("video"))

        # 3. bad orders: refused with the right code, nothing made
        ok_files = [("a.png", src / "a.png")]
        base = {"schema": orders.SCHEMA, "kind": "render_plan"}
        def plan_of(clips, **kw):
            return dict(base, plan=dict({"clips": clips}, **kw))
        bad = {
            "bad-json": (None, "{not json", ok_files, "ORDER_JSON_INVALID"),
            "bad-array": ([1, 2], None, ok_files, "ORDER_JSON_INVALID"),
            "bad-schema": ({"schema": "x/1", "kind": "render_plan"}, None, ok_files, "ORDER_SCHEMA_UNKNOWN"),
            "bad-kind": ({"schema": orders.SCHEMA, "kind": "upload"}, None, ok_files, "ORDER_KIND_UNKNOWN"),
            "bad-outside": (plan_of([{"still": "../a.png", "start_s": 0, "end_s": 1}]), None, ok_files, "ORDER_PATH_OUTSIDE"),
            "bad-absolute": (plan_of([{"still": str(src / "a.png"), "start_s": 0, "end_s": 1}]), None, ok_files, "ORDER_PATH_OUTSIDE"),
            "bad-network": (plan_of([{"still": "\\\\server\\share\\a.png", "start_s": 0, "end_s": 1}]), None, ok_files, "ORDER_NETWORK_PATH"),
            "bad-missing": (plan_of([{"still": "nope.png", "start_s": 0, "end_s": 1}]), None, ok_files, "ORDER_FILE_MISSING"),
            "bad-gap": (plan_of([{"still": "a.png", "start_s": 0, "end_s": 1}, {"still": "a.png", "start_s": 1.5, "end_s": 2}]), None, ok_files, "PLAN_TIMES_INVALID"),
            "bad-start": (plan_of([{"still": "a.png", "start_s": 0.5, "end_s": 1}]), None, ok_files, "PLAN_TIMES_INVALID"),
            "bad-short": (plan_of([{"still": "a.png", "start_s": 0, "end_s": 0.05}]), None, ok_files, "PLAN_TIMES_INVALID"),
            "bad-both": (plan_of([{"still": "a.png", "video": "a.png", "start_s": 0, "end_s": 1}]), None, ok_files, "ORDER_FIELD_INVALID"),
            "bad-odd": (plan_of([{"still": "a.png", "start_s": 0, "end_s": 1}], width=1081), None, ok_files, "ORDER_FIELD_INVALID"),
            "bad-long": (plan_of([{"still": "a.png", "start_s": 0, "end_s": 601}]), None, ok_files, "PLAN_TOO_LONG"),
            "bad-picture": (plan_of([{"still": "x.png", "start_s": 0, "end_s": 1}]), None, [("x.png", src / "not_a_picture.png")], "PLAN_IMAGE_UNREADABLE"),
            "bad-audio": (plan_of([{"still": "a.png", "start_s": 0, "end_s": 1}], audio="x.png"), None,
                          ok_files + [("x.png", src / "not_a_picture.png")], "PLAN_AUDIO_UNREADABLE"),
            "bad-from": (plan_of([{"video": "v.mp4", "from_s": 99, "start_s": 0, "end_s": 1}]), None, [("v.mp4", long_clip)], "PLAN_TIMES_INVALID"),
            "bad-noclips": (plan_of([]), None, ok_files, "ORDER_FIELD_INVALID"),
            "bad-reel-folder": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": str(home / "no such folder")},
                                 "mode": "technical", "length": 5}, None, (), "VIDEOS_NOT_USABLE"),
            "bad-reel-length": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": str(videos)},
                                 "mode": "technical", "length": 7}, None, (), "ORDER_FIELD_INVALID"),
            "bad-reel-two-sources": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": str(videos), "library_theme": "sea"},
                                      "mode": "technical"}, None, (), "ORDER_FIELD_INVALID"),
            # found by review (2026-10-17): a playlist names any file on the PC; a quoted or // network path
            "bad-hls": (plan_of([{"video": "clip.m3u8", "start_s": 0, "end_s": 1}]), None, [("clip.m3u8", src / "playlist.m3u8")], "PLAN_VIDEO_UNREADABLE"),
            "bad-hls-as-mp4": (plan_of([{"video": "clip.mp4", "start_s": 0, "end_s": 1}]), None, [("clip.mp4", src / "playlist.m3u8")], "PLAN_VIDEO_UNREADABLE"),
            "bad-hls-sound": (plan_of([{"still": "a.png", "start_s": 0, "end_s": 1}], audio="s.m3u8"), None,
                              ok_files + [("s.m3u8", src / "playlist.m3u8")], "PLAN_AUDIO_UNREADABLE"),
            "bad-concat": (plan_of([{"video": "x.mp4", "start_s": 0, "end_s": 1}]), None, [("x.mp4", src / "list.ffconcat")], "PLAN_VIDEO_UNREADABLE"),
            "bad-reel-playlist": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"files": ["v.mp4"]},
                                   "mode": "technical", "length": 5}, None, [("v.mp4", src / "playlist.m3u8")], "VIDEOS_NOT_USABLE"),
            "bad-huge-picture": (plan_of([{"still": "big.png", "start_s": 0, "end_s": 1}]), None, [("big.png", src / "huge.png")], "PLAN_IMAGE_TOO_BIG"),
            "bad-quoted-unc": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": '"\\\\no-such-server\\share"'},
                                "mode": "technical", "length": 5}, None, (), "ORDER_NETWORK_PATH"),
            "bad-slash-unc": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"files": ["//no-such-server/share/a.mp4"]},
                               "mode": "technical", "length": 5}, None, (), "ORDER_NETWORK_PATH"),
            "bad-music-unc": ({"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": str(videos)},
                               "music": "\\\\?\\UNC\\no-such-server\\m.mp3", "mode": "technical", "length": 5}, None, (), "ORDER_NETWORK_PATH"),
        }
        for oid, (order, raw, files, _) in bad.items():
            put(oid, order, files, raw=raw)
        put("-dash", base, ok_files)       # an id that is not allowed
        wrong = {}
        for oid, (_, _, _, code) in bad.items():
            st, res = answer(oid, 120)
            got = (res.get("error") or {}).get("code")
            if st != "failed" or got != code or (orders.done_dir() / oid).exists():
                wrong[oid] = f"{st} {got} (want {code})"
        check(f"bad_orders_refused_with_the_right_code ({len(bad)})", not wrong, wrong)
        st, res = answer("order -dash", 60)
        check("bad_id_refused_kept_aside", st == "failed" and res["error"]["code"] == "ORDER_ID_INVALID" and res.get("can_retry") is False
              and (orders.failed_dir() / "order -dash" / "order" / "order.json").is_file(), res.get("error"))

        # 4. the same id again: refused, the first answer untouched
        first = sha(orders.done_dir() / "plan-1" / "video.mp4")
        put("plan-1", PLAN, PLAN_FILES)
        st, res = answer("plan-1 (2)", 120)
        check("used_id_refused_first_answer_untouched", st == "failed" and res["error"]["code"] == "ORDER_ID_ALREADY_USED"
              and sha(orders.done_dir() / "plan-1" / "video.mp4") == first, res.get("error"))

        # 5. an order still being copied (no order.json yet) is not taken
        (inbox / "arriving").mkdir()
        shutil.copy2(src / "a.png", inbox / "arriving" / "a.png")
        time.sleep(8)
        ov = c.get("/api/auto/orders", headers=H).get_json()
        arr = [x for x in ov["items"] if x["id"] == "arriving"]
        check("order_without_order_json_waits", (inbox / "arriving").is_dir() and arr and arr[0]["state"] == "arriving", arr)
        shutil.rmtree(inbox / "arriving")

        # 6. a one-file order: a reel from a folder of videos (a normal Auto Edit project)
        put("reel-1", {"schema": orders.SCHEMA, "kind": "reel_from_videos", "from": "orders_check", "title": "Ролик по заказу",
                       "videos": {"folder": str(videos)}, "length": 5, "format": "vertical", "mode": "technical",
                       "text": {"title": "Заказ 1"}}, single=True)
        st, res = answer("reel-1", 1800)
        check("reel_order_done", st == "done", res.get("error"))
        if st == "done":
            pid = res["project"]["id"]
            p = ae.project(pid)
            rev = p["revisions"][-1] if p and p["revisions"] else {}
            check("reel_order_is_a_project_with_that_version", p is not None and rev.get("video_sha256") == res["video"]["sha256"]
                  and p["title"] == "Ролик по заказу", (res.get("project"), rev.get("video_sha256")))
            check("reel_order_used_videos_listed", bool(res.get("videos_used")) and set(res["videos_used"]) <= {x.name for x in vids},
                  res.get("videos_used"))
            check("reel_order_checks_pass", all(x["pass"] for x in res["checks"]) and (res["video"]["width"], res["video"]["height"]) == (540, 960),
                  res["checks"])
            check("reel_order_title_kept", (rev.get("settings") or {}).get("title") == "Заказ 1", rev.get("settings"))
            # a file in the order folder posing as MediaEngine's own notes cannot point the order at an existing project
            planted = home / "_planted.json"
            planted.write_text(json.dumps({"project_id": pid, "job_id": 1, "attempts": 0}), encoding="utf-8")
            n_rev = len(p["revisions"])
            put("planted-1", {"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": str(home / "no such folder")},
                              "mode": "technical", "length": 5}, [(".mediaengine_state.json", planted)])
            st2, res2 = answer("planted-1", 300)
            check("planted_state_file_ignored", st2 == "failed" and res2["error"]["code"] == "VIDEOS_NOT_USABLE"
                  and len(ae.project(pid)["revisions"]) == n_rev and not res2.get("project"), (st2, res2.get("error"), res2.get("project")))

        # 6b. a folder with a damaged video: the order is done without it (as a reel in the app), the answer says so
        dmg = home / "_with_damaged"
        dmg.mkdir(exist_ok=True)
        shutil.copy2(vids[0], dmg / vids[0].name)
        (dmg / "broken.mp4").write_bytes(b"this is not a video" * 200)
        put("reel-damaged", {"schema": orders.SCHEMA, "kind": "reel_from_videos", "videos": {"folder": str(dmg)},
                             "length": 5, "format": "vertical", "mode": "technical"}, single=True)
        st, res = answer("reel-damaged", 1800)
        check("damaged_video_left_out_not_refused", st == "done" and res.get("videos_left_out") == ["broken.mp4"]
              and vids[0].name in (res.get("videos_used") or []), (st, res.get("error"), res.get("videos_left_out"), res.get("videos_used")))

        # 6c. chosen videos, one of them gone since (moved, card unplugged): done without it on the first try
        put("reel-gone", {"schema": orders.SCHEMA, "kind": "reel_from_videos",
                          "videos": {"files": [str(dmg / vids[0].name), str(home / "gone since.mp4")]},
                          "length": 5, "format": "vertical", "mode": "technical"}, single=True)
        st, res = answer("reel-gone", 1800)
        check("missing_video_left_out_first_try", st == "done" and res.get("videos_left_out") == ["gone since.mp4"]
              and vids[0].name in (res.get("videos_used") or []), (st, res.get("error"), res.get("videos_left_out")))

        # 7. "Wait for my OK": Run, Reject, a rejected order is not done again
        r = c.post("/auto/orders/settings", data={"auto_run": "0"}, headers=H)
        check("setting_wait_for_ok_saved", r.status_code == 302 and orders.auto_run() is False)
        put("wait-1", PLAN, PLAN_FILES)
        put("wait-2", PLAN, PLAN_FILES)
        time.sleep(9)
        ov = c.get("/api/auto/orders", headers=H).get_json()
        states = {x["id"]: x["state"] for x in ov["items"]}
        check("orders_wait_for_ok", states.get("wait-1") == "new" and states.get("wait-2") == "new", states)
        page = c.get("/auto/orders", headers=H).data.decode("utf-8", "replace")
        check("page_offers_run_and_reject", "/auto/orders/wait-1/run" in page and "/auto/orders/wait-1/reject" in page)
        c.post("/auto/orders/wait-2/reject", headers=H)
        st2, res2 = answer("wait-2", 60)
        check("rejected_order_answered", st2 == "failed" and res2["error"]["code"] == "REJECTED_BY_OWNER" and res2.get("can_retry") is False,
              res2.get("error"))
        r = c.post("/auto/orders/wait-2/retry", headers=H)
        check("rejected_order_not_done_again", r.status_code == 400 and not (orders.done_dir() / "wait-2").exists(), r.status_code)
        c.post("/auto/orders/wait-1/run", headers=H)
        st, res = answer("wait-1", 300)
        check("run_after_ok", st == "done", res.get("error"))
        c.post("/auto/orders/settings", data={"auto_run": "1"}, headers=H)

        # 7b. the program moved its answers away (read them): never done again by itself - also not a rejected one
        _retire_ = home / "_taken_answers"
        _retire_.mkdir(exist_ok=True)
        os.replace(orders.done_dir() / "wait-1", _retire_ / "wait-1")
        os.replace(orders.failed_dir() / "wait-2", _retire_ / "wait-2")
        orders._WAKE.set()
        time.sleep(9)
        check("answers_taken_away_are_not_done_again", not (orders.done_dir() / "wait-1").exists() and not (orders.done_dir() / "wait-2").exists()
              and not (orders.failed_dir() / "wait-2").exists() and orders.busy() not in ("wait-1", "wait-2"), orders.busy())
        ov = c.get("/api/auto/orders", headers=H).get_json()
        taken = {x["id"]: x["state"] for x in ov["items"] if x["id"] in ("wait-1", "wait-2")}
        r = c.post("/auto/orders/wait-1/delete", headers=H)
        check("taken_answers_listed_and_deletable", taken == {"wait-1": "taken", "wait-2": "taken"} and r.status_code == 302
              and not (orders.received_dir() / "wait-1").exists(), (taken, r.status_code))

        # 7c. a folder Windows cannot move now (a file open in it) does not hold up the others
        real_move = orders._move
        def flaky(src_, dst_, tries=40):
            if Path(src_).name == "locked-1":
                raise PermissionError("a file in it is open")
            return real_move(src_, dst_, tries)
        orders._move = flaky
        try:
            put("locked-1", PLAN, PLAN_FILES)
            time.sleep(0.5)
            put("after-1", PLAN, PLAN_FILES)
            st, res = answer("after-1", 300)
            waiting = (inbox / "locked-1").is_dir()
        finally:
            orders._move = real_move
        st2, res2 = answer("locked-1", 300)
        check("an_unmovable_order_does_not_block_others", st == "done" and waiting and st2 == "done", (st, waiting, st2))

        # 8. Stop in the middle, then Run again
        clips, t = [], 0.0
        for k in range(40):
            clips.append({"video": "v.mp4", "from_s": (k % 10) * 1.0, "start_s": round(t, 3), "end_s": round(t + 1.5, 3)})
            t += 1.5
        put("stop-1", {"schema": orders.SCHEMA, "kind": "render_plan", "plan": {"width": 1080, "height": 1920, "clips": clips}},
            [("v.mp4", long_clip)])
        t0 = time.time()
        stopped = False
        while time.time() - t0 < 300:
            ov = c.get("/api/auto/orders", headers=H).get_json()
            if any(x["id"] == "stop-1" and x["state"] == "working" for x in ov["items"]):
                # while it renders: Quit / switching builds ask first, and a button on another order answers at once
                check("busy_while_an_order_is_done", orders.busy() == "stop-1" and "order" in ae.app_busy().lower(), ae.app_busy())
                put("wait-3", PLAN, PLAN_FILES)
                time.sleep(orders.SETTLE_S + 1.5)
                t1 = time.time()
                r = c.post("/auto/orders/wait-3/reject", headers=H)
                dt = time.time() - t1
                still = any(x["id"] == "stop-1" and x["state"] == "working" for x in c.get("/api/auto/orders", headers=H).get_json()["items"])
                check("reject_does_not_wait_for_a_render", r.status_code == 302 and dt < 5 and still, (r.status_code, round(dt, 1), still))
                c.post("/auto/orders/stop-1/stop", headers=H)
                stopped = True
                break
            if (orders.done_dir() / "stop-1").exists():
                break
            time.sleep(0.3)
        st, res = answer("stop-1", 300)
        check("stop_in_the_middle", stopped and st == "failed" and res["error"]["code"] == "STOPPED_BY_OWNER"
              and not (orders.done_dir() / "stop-1").exists(), (stopped, st, res.get("error")))
        page = c.get("/auto/orders", headers=H).data.decode("utf-8", "replace")
        check("page_offers_run_again", "/auto/orders/stop-1/retry" in page)
        r = c.post("/auto/orders/stop-1/retry", headers=H)
        st, res = answer("stop-1", 900)
        check("run_again_after_stop", r.status_code == 302 and st == "done" and abs(res["video"]["duration_s"] - 60.0) < 0.1,
              res.get("error") or res.get("video"))

        # 9. fix a missing file and Try again
        put("fix-1", plan_of([{"still": "late.png", "start_s": 0, "end_s": 1}]), ok_files)
        st, res = answer("fix-1", 120)
        shutil.copy2(src / "a.png", orders.received_dir() / "fix-1" / "late.png")
        r = c.post("/auto/orders/fix-1/retry", headers=H)
        st2, res2 = answer("fix-1", 300)
        check("fix_and_try_again", st == "failed" and r.status_code == 302 and st2 == "done", (st, st2, res2.get("error")))

        # 10. an order interrupted by a restart (taken, no answer yet) is done again
        aside = home / "_interrupted"
        aside.mkdir()
        for rel, f in PLAN_FILES:
            (aside / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, aside / rel)
        (aside / "order.json").write_text(json.dumps(PLAN), encoding="utf-8")
        os.replace(aside, orders.received_dir() / "interrupted-1")
        orders._WAKE.set()
        st, res = answer("interrupted-1", 300)
        check("interrupted_order_done_again", st == "done", res.get("error"))

        # 10b. an order started 3 times without an answer (closed each time) waits for the owner, then Try again
        aside = home / "_stuck"
        aside.mkdir()
        for rel, f in PLAN_FILES:
            (aside / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, aside / rel)
        (aside / "order.json").write_text(json.dumps(PLAN), encoding="utf-8")
        (orders.received_dir() / ".state").mkdir(exist_ok=True)
        (orders.received_dir() / ".state" / "stuck-1.json").write_text(json.dumps({"attempts": orders.MAX_ATTEMPTS}), encoding="utf-8")
        os.replace(aside, orders.received_dir() / "stuck-1")
        orders._WAKE.set()
        time.sleep(8)
        ov = c.get("/api/auto/orders", headers=H).get_json()
        sk = [x for x in ov["items"] if x["id"] == "stuck-1"]
        check("stuck_order_waits_for_owner", sk and sk[0]["state"] == "stuck" and not (orders.done_dir() / "stuck-1").exists(), sk)
        page = c.get("/auto/orders", headers=H).data.decode("utf-8", "replace")
        r = c.post("/auto/orders/stuck-1/retry", headers=H)
        st, res = answer("stuck-1", 300)
        check("stuck_order_try_again", "/auto/orders/stuck-1/retry" in page and r.status_code == 302 and st == "done", (r.status_code, st))

        # 10c. an id with two dots works with every button
        put("v1..2", PLAN, PLAN_FILES)
        st, res = answer("v1..2", 300)
        r = c.post("/auto/orders/v1..2/delete", headers=H)
        check("id_with_two_dots_done_and_deleted", st == "done" and r.status_code == 302 and not (orders.done_dir() / "v1..2").exists(),
              (st, r.status_code))

        # 11. pages, API, Delete
        page = c.get("/auto/orders", headers=H).data.decode("utf-8", "replace")
        check("page_lists_ready_and_failed", "plan-1" in page and "bad-gap" in page and "/auto/orders/plan-1/open" in page)
        ov = c.get("/api/auto/orders", headers=H).get_json()
        check("api_counts", ov["counts"]["done"] >= 6 and ov["counts"]["failed"] >= len(bad), ov["counts"])
        r = c.post("/auto/orders/plan-file/delete", headers=H)
        check("delete_removes_only_order_folders", r.status_code == 302 and not (orders.done_dir() / "plan-file").exists()
              and not (orders.received_dir() / "plan-file").exists() and (orders.done_dir() / "plan-1").exists())
        r = c.post("/auto/orders/..%2F..%2Fdata/delete", headers=H)
        check("delete_refuses_paths", r.status_code in (400, 404) and (home / "data").is_dir(), r.status_code)
        r = c.post("/auto/orders/plan-1/open", headers={"Host": "127.0.0.1:8765", "Origin": "http://evil.example"})
        check("buttons_refuse_other_sites", r.status_code == 403, r.status_code)

    after = {p.name: sha(p) for p in videos.iterdir() if p.is_file()}
    check("test_videos_unchanged", before == after)
    ok = all(x["pass"] for x in checks)
    if a.out:
        Path(a.out).write_text(json.dumps({"pass": ok, "checks": checks}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{sum(x['pass'] for x in checks)}/{len(checks)} checks passed")
    orders.shutdown()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
