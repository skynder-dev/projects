"""End-to-end Auto Edit check through the real app routes (Flask test client + real engine subprocess).

Usage:  python tests/e2e_auto_edit.py --folder <videos> --home <empty temp dir> [--mode technical|semantic]
        [--out report.json] [--length 15]

Covers: folder scan (skips broken/duplicate), Create reel from the UI form, honest progress, review page,
Accept, Export (one MP4, Windows-safe name, idempotent repeat), Make variant (format change reuses analysis),
Rebuild without an excluded moment, Revert, Cancel mid-render, Retry after cancel, idempotent repeat request,
source files unchanged (SHA before/after), app restart keeps projects.
Exit code 0 only if every check passes.
"""
from __future__ import annotations

import argparse, html, urllib.parse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def probe(p):
    """ffmpeg-only probe (same backend the app uses; Windows has no ffprobe)."""
    from archivist import auto_edit as ae
    try:
        return ae._probe(Path(p))
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--home", required=True)
    ap.add_argument("--mode", default="technical", choices=("technical", "semantic"))
    ap.add_argument("--length", default="auto", help="seconds or auto (= the length the app recommends)")
    ap.add_argument("--out", default="")
    ap.add_argument("--skip-cancel", action="store_true")
    ap.add_argument("--files-check", action="store_true", help="also build a reel from two individually chosen files")
    a = ap.parse_args()
    home = Path(a.home).resolve()
    home.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(home)
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.web import create_app
    from archivist import auto_edit as ae

    folder = Path(a.folder).resolve()
    before = {p.name: sha(p) for p in folder.iterdir() if p.is_file()}
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    checks = []
    timings = {}

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def wait_job(c, jid, limit=3600):
        t0 = time.time()
        seen = []
        while time.time() - t0 < limit:
            j = c.get(f"/api/auto/job/{jid}", headers=H).get_json()
            if not seen or seen[-1] != (j["stage"], j["percent"]):
                seen.append((j["stage"], j["percent"]))
            if j["status"] in ("done", "failed", "cancelled"):
                return j, seen, time.time() - t0
            time.sleep(0.5)
        return {"status": "timeout"}, seen, time.time() - t0

    app = create_app()
    with app.test_client() as c:
        r = c.get("/auto", headers=H)
        check("auto_home_renders", r.status_code == 200 and b"Auto Edit" in r.data)
        r = c.get("/auto/new", query_string={"folder": str(folder)}, headers=H)
        page = r.data.decode("utf-8", "replace")
        check("setup_page_renders", r.status_code == 200 and "Create reel" in page, r.status_code)
        scan = ae.scan_folder(folder)
        a.length = int(scan["recommended_length"]) if str(a.length) == "auto" else int(a.length)
        print("length:", a.length, "usable:", scan["usable"], "total_s:", scan["total_s"], flush=True)
        bad = {f["name"]: f["reason"] for f in scan["files"] if not f["ok"]}
        dups = [n for n in before if " copy" in n]
        ok_broken = all(n in bad for n in before if n.startswith("broken"))
        ok_dups = all(sum(1 for m in (d, d.replace(" copy", "")) if m in bad and bad[m].startswith("duplicate")) == 1 for d in dups)
        check("scan_skips_broken_and_one_of_each_duplicate", ok_broken and ok_dups, bad)
        check("setup_shows_only_length_format_sound", all(x in page for x in ("Length", "Format", "Sound")) and "semantic=required" not in page)
        # a folder with only subfolders of videos (D:\\Videos\\2023, 2024 ...) points to them instead of a dead end
        parent = home / "parent_of_videos"
        (parent / "2024 trip").mkdir(parents=True, exist_ok=True)
        first = next(p for p in sorted(folder.iterdir()) if p.suffix.lower() == ".mp4")
        shutil.copyfile(first, parent / "2024 trip" / first.name)
        r = c.get("/auto/new", query_string={"folder": str(parent)}, headers=H)
        check("folder_with_subfolders_lists_them", r.status_code == 200 and b"No videos directly in this folder" in r.data
              and urllib.parse.quote(str(parent / "2024 trip")).encode() in r.data, r.data[-400:])
        # a phone camera folder with more videos than one reel takes: pick a day (one click) instead of an error
        cam = home / "camera_roll"
        cam.mkdir(parents=True, exist_ok=True)
        good = folder / next(f["name"] for f in scan["files"] if f["ok"])      # a readable video (not "broken.mp4")
        for i in range(ae.MAX_INPUTS + 2):
            shutil.copyfile(good, cam / f"VID_2026071{4 + i % 2}_1200{i:02d}.mp4")
        r = c.get("/auto/new", query_string={"folder": str(cam)}, headers=H)
        cam_page = r.data.decode("utf-8", "replace")
        day_links = re.findall(r"href='(/auto/new\?file=[^']+)'", cam_page)
        check("big_folder_offers_days_and_ticks", r.status_code == 200 and "Use this day" in cam_page and len(day_links) == 2
              and cam_page.count("name='file'") == ae.MAX_INPUTS + 2, (r.status_code, len(day_links)))
        if day_links:
            r = c.get(html.unescape(day_links[0]), headers=H)
            check("big_folder_day_opens_reel_setup", r.status_code == 200 and b"Create reel" in r.data, r.status_code)
        r = c.get("/auto/new", query_string={"folder": str(folder)}, headers={**H, "Sec-Fetch-Site": "cross-site"})
        check("setup_refuses_other_sites", r.status_code == 400, r.status_code)
        if not ae.model_status()["ready"]:
            n_proj = len(ae.list_projects(include_archived=True))
            r = c.post("/auto/create", data={"folder": str(folder), "length": "15", "format": "social_hd", "sound": "auto"}, headers=H)
            check("no_silent_technical_fallback", r.status_code == 400 and len(ae.list_projects(include_archived=True)) == n_proj, r.status_code)

        form = {"folder": str(folder), "length": str(a.length), "format": "social_hd", "sound": "auto", "mode": a.mode}
        r = c.post("/auto/create", data=form, headers=H)
        check("create_redirects_to_project", r.status_code == 302 and "/auto/p/" in r.headers.get("Location", ""), r.status_code)
        pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
        p = ae.project(pid)
        jid = p["jobs"][0]["id"]
        r = c.get(f"/auto/p/{pid}", headers=H)
        check("progress_page_renders", r.status_code == 200 and b"jobBar" in r.data)
        j, stages, dt = wait_job(c, jid)
        timings["first_build_s"] = round(dt, 1)
        check("first_build_done", j["status"] == "done", j)
        check("job_reports_elapsed_time", float(j.get("elapsed_s") or 0) > 0, j.get("elapsed_s"))
        check("progress_has_real_stages", len({s for s, _ in stages}) >= 3 and all(p2 >= p1 for (_, p1), (_, p2) in zip(stages, stages[1:])), stages)
        if j["status"] != "done":
            log = (home / "data" / "auto_edit" / f"p{pid}" / "jobs" / f"j{jid}.log")
            print(log.read_text(errors="replace")[-3000:] if log.exists() else "no log")
            return finish(a, checks, timings, 1)
        p = ae.project(pid)
        rev = ae.revision(p["revisions"][0]["id"])
        timings["first_build_stage_s"] = rev["result"].get("stage_seconds")
        pr = probe(rev["video_path"])
        v = [s for s in pr.get("streams", []) if s.get("codec_type") == "video"]
        au = [s for s in pr.get("streams", []) if s.get("codec_type") == "audio"]
        check("revision_is_social_hd_1080x1920", v and int(v[0]["width"]) == 1080 and int(v[0]["height"]) == 1920, v)
        check("revision_has_audio", bool(au))
        if v and au:
            from media_measure import av_durations
            vd, ad = av_durations(rev["video_path"])
            check("audio_video_same_length", vd > 1 and ad is not None and abs(vd - ad) <= 0.1, (vd, ad))
        dur = float(pr.get("format", {}).get("duration") or 0)
        r_short = c.get(f"/auto/p/{pid}", headers=H).data.decode("utf-8", "replace")
        check("duration_near_target_or_shortfall_shown", abs(dur - a.length) <= 1.5 or (dur < a.length and f"Requested {a.length} s" in r_short), dur)
        check("revision_has_segments_for_review", len(rev["result"].get("segments", [])) >= 1, len(rev["result"].get("segments", [])))
        check("selection_mode_matches_request",
              rev["result"].get("selection_mode", "").startswith("FAST_LOCAL") == (a.mode == "semantic"), rev["result"].get("selection_mode"))

        r = c.get(f"/auto/p/{pid}", headers=H)
        check("review_page_has_player", r.status_code == 200 and b"<video id='reel'" in r.data)
        r = c.get(f"/auto/rev/{rev['id']}/video", headers={**H, "Range": "bytes=0-99"})
        check("video_served_with_range", r.status_code == 206 and len(r.data) == 100, r.status_code)
        seg0 = rev["result"]["segments"][0]
        r = c.get(f"/auto/p/{pid}/source", query_string={"name": seg0["source_name"]}, headers={**H, "Range": "bytes=0-9"})
        check("source_preview_served", r.status_code == 206, r.status_code)
        r = c.get(f"/auto/p/{pid}/source", query_string={"name": "../../etc/passwd"}, headers=H)
        check("source_preview_path_safe", r.status_code == 404, r.status_code)

        r = c.post(f"/auto/p/{pid}/export", headers=H)
        check("export_refused_before_accept", r.status_code == 400)
        r = c.post(f"/auto/p/{pid}/accept", data={"revision_id": rev["id"]}, headers=H)
        check("accept", r.status_code == 302 and ae.project(pid)["accepted_revision_id"] == rev["id"])
        r = c.post(f"/auto/p/{pid}/export", headers=H)
        p = ae.project(pid)
        ex = p["exports"][0] if p["exports"] else None
        check("export_one_mp4", r.status_code == 302 and ex and Path(ex["path"]).is_file() and sha(ex["path"]) == rev["video_sha256"], ex)
        check("export_name_windows_safe", ex and not any(ch in Path(ex["path"]).name for ch in '<>:"/\\|?*'), ex and Path(ex["path"]).name)
        r = c.get("/auto", headers=H)
        check("exported_reels_button_after_export", b"/auto/exports/open" in r.data and b"Exported reels" in r.data)
        exports_dir = home / "Exports"
        n_before = len(list(exports_dir.glob("*.mp4")))
        c.post(f"/auto/p/{pid}/export", headers=H)
        check("repeat_export_idempotent", len(list(exports_dir.glob("*.mp4"))) == n_before and not list(exports_dir.glob("*.part")))
        r = c.get(f"/auto/p/{pid}?exported={ex['export_id'] if 'export_id' in ex else ex['id']}", headers=H)
        check("completion_screen", r.status_code == 200 and b"Your reel is saved" in r.data and b"Show in folder" in r.data)
        # export to a folder the user chooses; it becomes the default; never into the source folder
        mine = home / "My reels Мои"
        mine.mkdir(exist_ok=True)
        r = c.post(f"/auto/p/{pid}/export", data={"dest": str(mine)}, headers=H)
        got_mine = list(mine.glob("*.mp4"))
        check("export_to_chosen_folder", r.status_code == 302 and len(got_mine) == 1 and sha(got_mine[0]) == rev["video_sha256"]
              and ae.default_export_dir().resolve() == mine.resolve(), [x.name for x in got_mine])
        r = c.post(f"/auto/p/{pid}/export", data={"dest": str(folder)}, headers=H)
        check("export_into_source_folder_refused", r.status_code == 400 and not [x for x in folder.iterdir() if x.name not in before], r.status_code)
        # the remembered export folder is this reel's own source folder: plain "Export MP4" falls back to Exports
        from archivist.config import load_config, save_config
        cfg_ = load_config(); cfg_.setdefault("auto_edit", {})["export_dir"] = str(folder); save_config(cfg_)
        r = c.post(f"/auto/p/{pid}/export", headers=H)
        check("default_export_never_into_source_folder", r.status_code == 302 and not [x for x in folder.iterdir() if x.name not in before],
              [x.name for x in folder.iterdir() if x.name not in before])
        cfg_ = load_config(); cfg_["auto_edit"]["export_dir"] = str(mine); save_config(cfg_)
        r = c.get(f"/auto/rev/{rev['id']}/thumb/1.jpg", headers=H)
        check("filmstrip_frame", r.status_code == 200 and r.mimetype == "image/jpeg" and len(r.data) > 500, (r.status_code, len(r.data)))

        # same request again -> no new job
        again = ae.start_job(pid, {"length": a.length, "format": "social_hd", "sound": "auto", "mode": a.mode})
        check("repeat_request_reuses_job", again == jid, (again, jid))

        # variant: only the format changes -> analysis cache reused, accepted revision untouched
        t0 = time.time()
        r = c.post(f"/auto/p/{pid}/variant", data={"length": a.length, "format": "horizontal", "sound": "auto", "mode": a.mode}, headers=H)
        jid2 = ae.project(pid)["jobs"][0]["id"]
        j2, _, dt2 = wait_job(c, jid2)
        timings["format_variant_s"] = round(dt2, 1)
        check("variant_done", j2["status"] == "done", j2)
        p = ae.project(pid)
        rev2 = ae.revision(p["revisions"][-1]["id"])
        v2 = [s for s in probe(rev2["video_path"]).get("streams", []) if s.get("codec_type") == "video"]
        check("variant_is_960x540", v2 and int(v2[0]["width"]) == 960 and int(v2[0]["height"]) == 540, v2)
        check("variant_same_moments", [s["event_id"] for s in rev2["result"]["segments"]] == [s["event_id"] for s in rev["result"]["segments"]])
        check("variant_faster_than_first_build", dt2 < timings["first_build_s"], (dt2, timings["first_build_s"]))
        check("accepted_pointer_unchanged_by_variant", p["accepted_revision_id"] == rev["id"] and sha(rev["video_path"]) == rev["video_sha256"])
        # blind comparison: versions hidden until the person decides, then revealed and listed on the project
        r = c.post(f"/auto/p/{pid}/compare", data={"a": rev2["id"], "b": rev["id"]}, headers=H)
        okr = r.status_code == 302 and "/auto/review/" in r.headers.get("Location", "")
        check("blind_compare_starts", okr, r.status_code)
        if okr:
            rvid = int(r.headers["Location"].rstrip("/").split("/")[-1])
            page_ = c.get(f"/auto/review/{rvid}", headers=H).data.decode("utf-8", "replace")
            vids = [c.get(f"/auto/review/{rvid}/video/{sd}", headers={**H, "Range": "bytes=0-9"}).status_code for sd in ("left", "right")]
            check("blind_compare_hides_versions", "A is better" in page_ and "R00" not in page_ and f"/auto/rev/{rev['id']}/" not in page_
                  and vids == [206, 206], vids)
            c.post(f"/auto/review/{rvid}/decide", data={"choice": "left", "note": "steadier start"}, headers=H)
            page_ = c.get(f"/auto/review/{rvid}", headers=H).data.decode("utf-8", "replace")
            again = c.post(f"/auto/review/{rvid}/decide", data={"choice": "right"}, headers=H).status_code
            proj_ = c.get(f"/auto/p/{pid}", headers=H).data.decode("utf-8", "replace")
            check("blind_compare_reveals_and_records", "You preferred A" in page_ and "R00" in page_ and again == 400
                  and "Blind comparisons" in proj_ and "steadier start" in proj_, again)

        # manual override: exclude the first moment and rebuild
        excl = seg0["event_id"]
        r = c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev["id"], "rechoose": "1", "remove": [excl],
                                                     "length": a.length, "format": "social_hd", "sound": "auto", "mode": a.mode}, headers=H)
        jid3 = ae.project(pid)["jobs"][0]["id"]
        j3, _, _ = wait_job(c, jid3)
        check("exclude_rebuild_done", j3["status"] == "done", j3)
        rev3 = ae.revision(ae.project(pid)["revisions"][-1]["id"])
        check("excluded_moment_absent", excl not in [s["event_id"] for s in rev3["result"].get("segments", [])])
        # a format variant of the override keeps the removed moment out (no silent loss of the user's choice)
        r = c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": rev3["id"], "length": a.length, "format": "horizontal", "sound": "auto"}, headers=H)
        j3b, _, _ = wait_job(c, ae.project(pid)["jobs"][0]["id"])
        rev3b = ae.revision(ae.project(pid)["revisions"][-1]["id"])
        check("variant_keeps_removed_moments", j3b["status"] == "done" and excl in rev3b["settings"].get("exclude", [])
              and excl not in [s["event_id"] for s in rev3b["result"].get("segments", [])] and rev3b["settings"]["mode"] == rev3["settings"]["mode"],
              (j3b.get("status"), rev3b["settings"]))

        # accept the override (double click: twice), then revert back to R001
        c.post(f"/auto/p/{pid}/accept", data={"revision_id": rev3["id"]}, headers=H)
        c.post(f"/auto/p/{pid}/accept", data={"revision_id": rev3["id"]}, headers=H)
        c.post(f"/auto/p/{pid}/revert", headers=H)
        check("revert_restores_previous_accept", ae.project(pid)["accepted_revision_id"] == rev["id"], ae.project(pid)["accepted_revision_id"])

        # manual editor: reverse order, trim the (new) first moment, replace one, remove one, add one
        segs = rev["result"]["segments"]
        pool = [c for c in rev["result"].get("candidate_pool", []) if not c["selected"]]
        rows = [s_["event_id"] for s_ in reversed(segs)]
        form = {"revision_id": rev["id"], "length": a.length, "format": "social_hd", "sound": "auto", "mode": a.mode, "row": rows}
        for s_ in segs:
            form[f"in_{s_['event_id']}"] = f"{s_['source_in_s']:.1f}"; form[f"out_{s_['event_id']}"] = f"{s_['source_out_s']:.1f}"
            form[f"def_in_{s_['event_id']}"] = f"{s_['source_in_s']:.1f}"; form[f"def_out_{s_['event_id']}"] = f"{s_['source_out_s']:.1f}"
        first = rows[0]
        src_first = next(s_ for s_ in segs if s_["event_id"] == first)
        t_in = round(max(0.0, src_first["source_in_s"] - 0.5), 1); t_out = round(t_in + 3.0, 1)
        form[f"in_{first}"] = f"{t_in:.1f}"; form[f"out_{first}"] = f"{t_out:.1f}"
        expected = list(rows)
        replaced = removed = added = None
        if len(rows) >= 2 and pool:
            replaced = (rows[-1], pool[0]["event_id"]); form[f"replace_{rows[-1]}"] = pool[0]["event_id"]; expected[-1] = pool[0]["event_id"]
        if len(rows) >= 3:
            removed = rows[1]; form["remove"] = [removed]; expected.remove(removed)
        if len(pool) >= 2:
            added = pool[1]["event_id"]; form["add"] = added; expected.append(added)
        r = c.post(f"/auto/p/{pid}/edit", data=form, headers=H)
        check("edit_submits", r.status_code == 302, r.status_code)
        jid_e = ae.project(pid)["jobs"][0]["id"]
        je, _, _ = wait_job(c, jid_e)
        check("edit_build_done", je["status"] == "done", je)
        if je["status"] == "done":
            reve = ae.revision(ae.project(pid)["revisions"][-1]["id"])
            got = [s_["event_id"] for s_ in reve["result"]["segments"]]
            check("edit_order_and_membership_as_requested", got == expected, (got, expected))
            tseg = next((s_ for s_ in reve["result"]["segments"] if s_["event_id"] == first), None)
            check("edit_trim_applied_in_source_time", tseg and abs((tseg["source_out_s"] - tseg["source_in_s"]) - (t_out - t_in)) <= 0.15
                  and abs(tseg["source_in_s"] - t_in) <= 0.15, tseg)
            if replaced:
                check("edit_replacement_used", replaced[0] not in got and replaced[1] in got)
            if removed:
                check("edit_removed_absent", removed not in got)
            check("edit_keeps_accepted_pointer", ae.project(pid)["accepted_revision_id"] == rev["id"])
            r = c.get(f"/auto/p/{pid}?rev={reve['id']}", headers=H)
            check("edited_revision_reviewable", r.status_code == 200 and b"your trim" in r.data)
            # sound-only variant of the edited version keeps order, membership and the trim
            r = c.post(f"/auto/p/{pid}/variant", data={"base_revision_id": reve["id"], "length": a.length, "format": "social_hd", "sound": "mute"}, headers=H)
            jv, _, _ = wait_job(c, ae.project(pid)["jobs"][0]["id"])
            revv = ae.revision(ae.project(pid)["revisions"][-1]["id"])
            gotv = [s_["event_id"] for s_ in revv["result"]["segments"]]
            tv = next((s_ for s_ in revv["result"]["segments"] if s_["event_id"] == first), None)
            check("variant_keeps_manual_edits", jv["status"] == "done" and gotv == got and tv and abs(tv["source_in_s"] - t_in) <= 0.15, (gotv, got, tv))
            # editing the edited version again (remove one more) keeps the earlier trim the user did not touch
            rows2 = [s_["event_id"] for s_ in reve["result"]["segments"]]
            if len(rows2) >= 3:
                f2 = {"revision_id": reve["id"], "length": a.length, "format": "social_hd", "sound": "auto", "mode": reve["settings"]["mode"], "row": rows2,
                      "remove": [rows2[-1]]}
                for s_ in reve["result"]["segments"]:
                    for k in ("in", "out"):
                        f2[f"{k}_{s_['event_id']}"] = f2[f"def_{k}_{s_['event_id']}"] = f"{s_['source_' + k + '_s']:.1f}"
                c.post(f"/auto/p/{pid}/edit", data=f2, headers=H)
                j6, _, _ = wait_job(c, ae.project(pid)["jobs"][0]["id"])
                rev6 = ae.revision(ae.project(pid)["revisions"][-1]["id"])
                t6 = next((s_ for s_ in rev6["result"]["segments"] if s_["event_id"] == first), None)
                check("re_edit_keeps_earlier_trim", j6["status"] == "done" and t6 and abs(t6["source_in_s"] - t_in) <= 0.15
                      and rows2[-1] not in [s_["event_id"] for s_ in rev6["result"]["segments"]], t6)
        # a revision of another project is never shown here
        other = ae.create_project(str(folder), "other")
        r = c.get(f"/auto/p/{other}?rev={rev['id']}", headers=H)
        check("rev_param_scoped_to_project", r.status_code == 200 and f"/auto/rev/{rev['id']}/video".encode() not in r.data)

        if not a.skip_cancel:
            n_before_cancel = len(ae.project(pid)["revisions"])
            r = c.post(f"/auto/p/{pid}/variant", data={"length": a.length, "format": "vertical", "sound": "mute", "mode": a.mode}, headers=H)
            jid4 = ae.project(pid)["jobs"][0]["id"]
            t0 = time.time()
            while time.time() - t0 < 600:
                jj = ae.job(jid4)
                if jj["status"] == "running" and jj["stage"] in ("render", "finish", "trim", "select", "analyze", "inputs"):
                    break
                time.sleep(0.2)
            import archivist.web as web_mod
            exits = []
            real_exit, real_spawn = web_mod._exit_soon, web_mod._spawn_launcher
            web_mod._exit_soon, web_mod._spawn_launcher = (lambda: exits.append("exit")), (lambda m: exits.append(m))
            try:
                r = c.post("/api/app-control", json={"mode": "restart"}, headers=H)
                time.sleep(0.2)
                check("restart_refused_while_reel_builds", r.status_code == 409 and not exits, (r.status_code, exits))
            finally:
                web_mod._exit_soon, web_mod._spawn_launcher = real_exit, real_spawn
            c.post(f"/auto/job/{jid4}/cancel", headers=H)
            j4, _, _ = wait_job(c, jid4, 120)
            n_rev = len(ae.project(pid)["revisions"])
            check("cancel_stops_job", j4["status"] == "cancelled", j4)
            check("cancel_publishes_nothing", n_rev == n_before_cancel, (n_rev, n_before_cancel))
            r = c.post(f"/auto/job/{jid4}/retry", headers=H)
            jid5 = ae.project(pid)["jobs"][0]["id"]
            j5, _, _ = wait_job(c, jid5)
            check("retry_after_cancel_done", j5["status"] == "done" and jid5 != jid4, j5)

        # a file marked Private in the library is never used, and the old build is not reused for it
        from archivist.db import db as _db, now_iso as _now
        src_name = seg0["source_name"]
        with _db() as con:
            con.execute("INSERT OR REPLACE INTO ignored_hashes(sha256,reason,created_at) VALUES(?,?,?)", (sha(folder / src_name), "private_forever", _now()))
            con.commit()
        jp = ae.start_job(pid, {"length": a.length, "format": "social_hd", "sound": "auto", "mode": a.mode})
        check("private_change_forces_new_build", jp != jid, (jp, jid))
        jpd, _, _ = wait_job(c, jp)
        revp = ae.revision(jpd.get("revision_id") or 0) if jpd["status"] == "done" else None
        check("private_file_never_used", revp and src_name not in [s_["source_name"] for s_ in revp["result"]["segments"]]
              and any(x["name"] == src_name and x["reason"] == "PRIVATE" for x in revp["result"].get("skipped_inputs", [])), jpd if not revp else revp["result"].get("skipped_inputs"))

        # free the analysis cache: versions and exports stay playable
        before_cache = ae.project_disk_usage(pid)["cache_bytes"]
        r = c.post(f"/auto/p/{pid}/free-cache", headers=H)
        r2v = c.get(f"/auto/rev/{rev['id']}/video", headers={**H, "Range": "bytes=0-9"})
        check("free_cache", r.status_code == 302 and before_cache > 0 and ae.project_disk_usage(pid)["cache_bytes"] == 0
              and r2v.status_code == 206, (r.status_code, before_cache))

        # Russian interface: same pages, same forms, Russian text; user content untouched
        c.post("/auto/lang", headers=H)
        ru = {u: c.get(u, headers=H) for u in ("/auto", f"/auto/p/{pid}", f"/auto/new?folder={urllib.parse.quote(str(folder))}")}
        okru = all(x.status_code == 200 for x in ru.values())
        txt = {u: x.data.decode("utf-8", "replace") for u, x in ru.items()}
        check("russian_interface", okru and "Мои проекты" in txt["/auto"] and "Создать ролик" in list(txt.values())[2]
              and "value='social_hd'" in list(txt.values())[2] and "Моменты в ролике" in txt[f"/auto/p/{pid}"]
              and ae.project(pid)["title"] in html.unescape(txt[f"/auto/p/{pid}"]), {u: x.status_code for u, x in ru.items()})
        c.post("/auto/lang", headers=H)
        check("english_again", b"My projects" in c.get("/auto", headers=H).data)
        # the language switch is on every page (top bar) and the whole app follows it; Check this PC is on Home
        home_en = c.get("/", headers=H).data.decode("utf-8", "replace")
        r = c.post("/lang", data={"lang": "ru", "back": "/settings"}, headers=H)
        pages_ru = {u: c.get(u, headers=H).data.decode("utf-8", "replace") for u in ("/", "/settings", "/library", "/jobs")}
        c.post("/lang", data={"lang": "en", "back": "/"}, headers=H)
        check("language_switch_everywhere", r.status_code == 302 and r.headers.get("Location", "").endswith("/settings")
              and "action='/lang'" in home_en and "href='/auto/check'" in home_en
              and "Проверка компьютера" in pages_ru["/"] and "Язык интерфейса" in pages_ru["/settings"]
              and "Библиотека" in pages_ru["/library"] and "<html lang='ru'>" in pages_ru["/jobs"]
              and b"Your footage" in c.get("/", headers=H).data, {u: len(t) for u, t in pages_ru.items()})

        r = c.get("/auto/check", headers=H)
        check("check_this_pc_page", r.status_code == 200 and b"Engine libraries load" in r.data and "⚠️</td><td><b>Engine".encode() not in r.data)

        if a.files_check:
            banner_before = b"First time on this PC?" in c.get("/auto", headers=H).data
            r = c.post("/auto/check", headers=H)
            check("check_this_pc_test_reel", r.status_code == 200 and b"Test reel built" in r.data, r.data[-600:])
            check("first_time_banner_until_test_passes", banner_before and b"First time on this PC?" not in c.get("/auto", headers=H).data)
            usable = [f["name"] for f in scan["files"] if f["ok"]][:2]
            chosen = [str(folder / n) for n in usable]
            r = c.get("/auto/new", query_string=[("file", x) for x in chosen], headers=H)
            check("files_setup_renders", r.status_code == 200 and "2 chosen video(s)" in r.data.decode("utf-8", "replace"), r.status_code)
            r = c.post("/auto/create", data={"file": chosen, "length": "5", "format": "vertical", "sound": "auto", "mode": a.mode}, headers=H)
            okc = r.status_code == 302 and "/auto/p/" in r.headers.get("Location", "")
            check("files_create", okc, r.status_code)
            if okc:
                fpid = int(r.headers["Location"].rstrip("/").split("/")[-1])
                fj, _, _ = wait_job(c, ae.project(fpid)["jobs"][0]["id"])
                frev = ae.revision(fj.get("revision_id") or 0) if fj["status"] == "done" else None
                srcs = {s_["source_name"] for s_ in (frev or {}).get("result", {}).get("segments", [])}
                check("files_reel_uses_only_chosen", frev and srcs and srcs <= set(usable), (fj.get("status"), srcs, usable))
                fv = [x for x in probe(frev["video_path"]).get("streams", []) if x.get("codec_type") == "video"] if frev else []
                check("vertical_is_540x960", fv and (int(fv[0]["width"]), int(fv[0]["height"])) == (540, 960), fv[:1])
                r = c.get(f"/auto/p/{fpid}/source", query_string={"name": usable[0]}, headers={**H, "Range": "bytes=0-9"})
                check("files_source_preview", r.status_code == 206, r.status_code)
                others = [x.name for x in folder.iterdir() if x.is_file() and x.name not in usable]
                if others:
                    r = c.get(f"/auto/p/{fpid}/source", query_string={"name": others[0]}, headers=H)
                    check("files_other_file_not_served", r.status_code == 404, r.status_code)
            # a browser / screen recording without a written length (like Chrome's MediaRecorder): used, not "damaged";
            # folder and file names with characters that need care in ffmpeg lists and filters (' [ ] % & ! # ; = ,)
            rec_dir = home.parent / "Mom's recordings [2026] 100% & co!; =,#"
            rec_dir.mkdir(exist_ok=True)
            live = rec_dir / "it's a 'screen' recording [1] %d #2.webm"
            with live.open("wb") as fh:
                subprocess.run([ae._ffmpeg() or "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30,hue=h=t*45",
                                "-f", "lavfi", "-i", "sine=frequency=520:sample_rate=48000", "-t", "9", "-c:v", "libvpx-vp9", "-deadline",
                                "realtime", "-cpu-used", "8", "-b:v", "1M", "-c:a", "libopus", "-live", "1", "-f", "webm", "pipe:1"],
                               stdout=fh, check=False)
            if live.stat().st_size > 10000:
                live_sha = sha(live)
                r = c.get("/auto/new", query_string={"folder": str(rec_dir)}, headers=H)
                page_ = r.data.decode("utf-8", "replace")
                check("no_length_recording_offered", r.status_code == 200 and "Create reel" in page_ and "a fixed copy is used" in page_,
                      r.data[-400:])
                r = c.post("/auto/create", data={"folder": str(rec_dir), "length": "5", "format": "social_hd", "sound": "auto",
                                                 "mode": a.mode}, headers=H)
                if r.status_code == 302 and "/auto/p/" in r.headers.get("Location", ""):
                    lpid = int(r.headers["Location"].rstrip("/").split("/")[-1])
                    lj, _, _ = wait_job(c, ae.project(lpid)["jobs"][0]["id"])
                    lrev = ae.revision(lj.get("revision_id") or 0) if lj["status"] == "done" else None
                    lsrc = {s_["source_name"] for s_ in (lrev or {}).get("result", {}).get("segments", [])}
                    check("no_length_recording_used", lrev and lsrc == {live.name} and sha(live) == live_sha,
                          (lj.get("status"), lj.get("error"), lsrc))
                else:
                    check("no_length_recording_used", False, r.status_code)
            else:
                print("SKIP no_length_recording: this ffmpeg cannot write VP9/Opus WebM")

    after = {p.name: sha(p) for p in folder.iterdir() if p.is_file()}
    check("sources_unchanged", before == after)
    # restart: a fresh app process sees the same projects and accepted revision
    code = ("import os,sys;sys.path.insert(0,%r);from archivist import auto_edit as ae;"
            "p=ae.project(%d);print(p['accepted_revision_id'],len(p['revisions']),p['state'])") % (str(ROOT / "app"), pid)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**os.environ, "ARCHIVIST_HOME": str(home)})
    parts = out.stdout.split()
    check("restart_keeps_project", parts[:1] == [str(rev["id"])] and parts[-1:] == ["READY"], out.stdout + out.stderr[-500:])
    return finish(a, checks, timings, 0 if all(x["pass"] for x in checks) else 1)


def finish(a, checks, timings, code):
    rep = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "timings": timings, "checks": checks}
    print(json.dumps({k: rep[k] for k in ("passed", "total", "timings")}))
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=2, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o)),
                               encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
