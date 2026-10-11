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

import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

        form = {"folder": str(folder), "length": str(a.length), "format": "social_hd", "sound": "auto", "mode": a.mode, "title": "E2E: Trip/2026?"}
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
        check("progress_has_real_stages", len({s for s, _ in stages}) >= 3 and all(p2 >= p1 for (_, p1), (_, p2) in zip(stages, stages[1:])), stages)
        if j["status"] != "done":
            log = (home / "data" / "auto_edit" / f"p{pid}" / "jobs" / f"j{jid}.log")
            print(log.read_text(errors="replace")[-3000:] if log.exists() else "no log")
            return finish(a, checks, timings, 1)
        p = ae.project(pid)
        rev = ae.revision(p["revisions"][0]["id"])
        pr = probe(rev["video_path"])
        v = [s for s in pr.get("streams", []) if s.get("codec_type") == "video"]
        au = [s for s in pr.get("streams", []) if s.get("codec_type") == "audio"]
        check("revision_is_social_hd_1080x1920", v and int(v[0]["width"]) == 1080 and int(v[0]["height"]) == 1920, v)
        check("revision_has_audio", bool(au))
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
        exports_dir = home / "Exports"
        n_before = len(list(exports_dir.glob("*.mp4")))
        c.post(f"/auto/p/{pid}/export", headers=H)
        check("repeat_export_idempotent", len(list(exports_dir.glob("*.mp4"))) == n_before and not list(exports_dir.glob("*.part")))

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

        # manual override: exclude the first moment and rebuild
        excl = seg0["event_id"]
        r = c.post(f"/auto/p/{pid}/variant", data={"length": a.length, "format": "social_hd", "sound": "auto", "mode": a.mode, "exclude": [excl]}, headers=H)
        jid3 = ae.project(pid)["jobs"][0]["id"]
        j3, _, _ = wait_job(c, jid3)
        check("exclude_rebuild_done", j3["status"] == "done", j3)
        rev3 = ae.revision(ae.project(pid)["revisions"][-1]["id"])
        check("excluded_moment_absent", excl not in [s["event_id"] for s in rev3["result"].get("segments", [])])

        # accept the override, then revert back to R001
        c.post(f"/auto/p/{pid}/accept", data={"revision_id": rev3["id"]}, headers=H)
        c.post(f"/auto/p/{pid}/revert", headers=H)
        check("revert_restores_previous_accept", ae.project(pid)["accepted_revision_id"] == rev["id"], ae.project(pid)["accepted_revision_id"])

        if not a.skip_cancel:
            r = c.post(f"/auto/p/{pid}/variant", data={"length": a.length, "format": "vertical", "sound": "mute", "mode": a.mode}, headers=H)
            jid4 = ae.project(pid)["jobs"][0]["id"]
            t0 = time.time()
            while time.time() - t0 < 600:
                jj = ae.job(jid4)
                if jj["status"] == "running" and jj["stage"] in ("render", "finish", "trim", "select", "analyze", "inputs"):
                    break
                time.sleep(0.2)
            c.post(f"/auto/job/{jid4}/cancel", headers=H)
            j4, _, _ = wait_job(c, jid4, 120)
            n_rev = len(ae.project(pid)["revisions"])
            check("cancel_stops_job", j4["status"] == "cancelled", j4)
            check("cancel_publishes_nothing", n_rev == 3, n_rev)
            r = c.post(f"/auto/job/{jid4}/retry", headers=H)
            jid5 = ae.project(pid)["jobs"][0]["id"]
            j5, _, _ = wait_job(c, jid5)
            check("retry_after_cancel_done", j5["status"] == "done" and jid5 != jid4, j5)

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
        Path(a.out).write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
