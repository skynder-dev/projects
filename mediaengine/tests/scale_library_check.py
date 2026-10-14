"""A big Library through the app routes: hundreds of videos, like a phone's whole camera folder.

  python tests/scale_library_check.py <work_dir> [--count 600] [--json out.json]

Makes <count> short unique videos (one generated stream cut into 3 s pieces, so it is quick) in one camera folder
with English and Cyrillic names (days in the names), then, like a user: adds the folder on the Import page, waits for the scan, "Import +
analyse" for all of them, opens the Library pages (first, last, grid, search, filters), the item pages, Activity,
Home, Media; prepares AI+ for the whole Library (the search and what reels need; a STAND-IN scorer - the real model is checked
in real_models_check.py) and searches; opens a new reel on the whole folder (more than 64 videos: the day list) and on one day's videos. Reports the time of every
step and the slowest page; fails when a page takes more than --max-page seconds (default 5) or a step fails.
Not part of the regular build (it takes long); runs in .github/workflows/mediaengine-scale.yml.
"""
from __future__ import annotations

import html, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from media_measure import ffmpeg_exe  # noqa: E402


def make_videos(src: Path, count: int, ff: str) -> list[Path]:
    tmp = src.parent / "_cut"
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    secs = 3 * count + 3
    # a little noise: the Library leaves out videos under 256 KB as "noise" (thumbnails, accidental clips)
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25,hue=h=t*9:s=1+sin(t),noise=alls=10:allf=t+u",
                    "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:beep_factor=3", "-t", str(secs),
                    "-c:v", "libx264", "-preset", "ultrafast", "-g", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k",
                    "-f", "segment", "-segment_time", "3", "-reset_timestamps", "1", str(tmp / "p%05d.mp4")], check=True)
    parts = sorted(tmp.glob("p*.mp4"))[:count]
    out = []
    src.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(parts):         # all in one camera folder, like a phone's DCIM/Camera (days in the names)
        name = f"VID_202607{1 + i % 20:02d}_{100000 + i}.mp4" if i % 3 else f"Отпуск 2026-07-{1 + i % 20:02d} {i:04d} пляж.mp4"
        dst = src / name
        os.replace(p, dst)
        out.append(dst)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def main():
    work = Path(sys.argv[1]).resolve()
    count = int(sys.argv[sys.argv.index("--count") + 1]) if "--count" in sys.argv else 600
    max_page = float(sys.argv[sys.argv.index("--max-page") + 1]) if "--max-page" in sys.argv else 5.0
    out_json = Path(sys.argv[sys.argv.index("--json") + 1]) if "--json" in sys.argv else work / "scale_library.json"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ff = ffmpeg_exe()
    src = work / "Телефон" / "Camera"
    t0 = time.time()
    vids = make_videos(src, count, ff)
    timings = {"videos": len(vids), "make_videos_s": round(time.time() - t0, 1)}
    os.environ["ARCHIVIST_HOME"] = str(work / "MediaEngine Data")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist.web import create_app
    from archivist.db import db
    from archivist import service, auto_edit as ae
    app = create_app()
    checks = []

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def n_rows():
        with db() as con:
            return con.execute("SELECT COUNT(*) FROM inventory WHERE path LIKE ?", (str(src) + "%",)).fetchone()[0]

    def wait_job(jid, limit):
        t = time.time()
        j = {}
        while jid and time.time() - t < limit:
            with db() as con:
                row = con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            j = dict(row) if row else {}
            if j.get("status") in ("finished", "partial", "failed", "cancelled"):
                return j
            time.sleep(2)
        return j

    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    pages = {}

    def page(c, url, key=None):
        t = time.perf_counter()
        r = c.get(url, headers=H)
        dt = time.perf_counter() - t
        pages[key or url] = round(dt, 3)
        return r, dt

    with app.test_client() as c:
        # 1. the folder is added on the Import page and scanned
        t0 = time.time()
        c.post("/import/add-source", data={"path": str(work / "Телефон"), "label": "Телефон"}, headers=H)
        while time.time() - t0 < 1200 and (n_rows() < len(vids) or service.DISCOVERY_LOCK.locked()):
            if not service.DISCOVERY_LOCK.locked() and n_rows() < len(vids):
                service.start_discovery()
            time.sleep(2)
        timings["scan_s"] = round(time.time() - t0, 1)
        check("every_video_found", n_rows() == len(vids), (n_rows(), len(vids)))
        r, dt = page(c, "/import?source_kind=fixed", "import_page")
        check("import_page_opens", r.status_code == 200, r.status_code)

        # 2. Import + analyse all of them
        with db() as con:
            ids = [x[0] for x in con.execute("SELECT id FROM inventory WHERE path LIKE ? ORDER BY id", (str(src) + "%",)).fetchall()]
        t0 = time.time()
        r = c.post("/api/selection-action", json={"action": "import_analyze", "ids": ids}, headers=H)
        j = wait_job((r.get_json() or {}).get("job_id"), 5400)
        timings["import_analyse_s"] = round(time.time() - t0, 1)
        timings["import_analyse_s_per_video"] = round((time.time() - t0) / max(1, len(ids)), 2)
        check("import_analyse_finished", j.get("status") == "finished", (j.get("status"), j.get("message"), j.get("error")))
        with db() as con:
            done = con.execute("SELECT COUNT(*) FROM inventory WHERE work_selected=1 AND path LIKE ?", (str(src) + "%",)).fetchone()[0]
        check("all_in_the_library", done == len(vids), (done, len(vids)))

        # 3. the Library and the other pages with hundreds of videos
        r, _ = page(c, "/library", "library_first_page")
        body = r.data.decode("utf-8", "replace")
        check("library_lists_videos", r.status_code == 200 and "/item/" in body, r.status_code)
        last = max(1, -(-len(vids) // 48))
        page(c, f"/library?page={last}", "library_last_page")
        page(c, "/library?view=grid", "library_grid")
        page(c, "/library?q=" + "Отпуск", "library_search_text")
        page(c, "/library?media_type=video&sort=date_asc", "library_filter_sort")
        page(c, f"/item/{ids[len(ids) // 2]}", "item_page")
        for u in ("/", "/media", "/jobs", "/import", "/auto", "/settings"):
            page(c, u)
        r, _ = page(c, "/auto/new?folder=" + str(src), "auto_new_whole_phone")
        body = r.data.decode("utf-8", "replace")
        check("whole_phone_folder_offers_the_day_list", r.status_code == 200 and "id='pickForm'" in body
              and body.count("name='file'") == len(vids), (r.status_code, body.count("name='file'")))
        day_files = [str(v) for v in vids if "20260701" in v.name][:20]
        r, _ = page(c, "/auto/new?" + "&".join("file=" + __import__("urllib.parse").parse.quote(x) for x in day_files), "auto_new_one_day")
        check("reel_setup_for_one_day", r.status_code == 200 and f"{len(day_files)} usable video(s)" in r.data.decode("utf-8", "replace"),
              r.status_code)

        # 4. AI+ search by theme over the whole Library (stand-in model: how the app copes with the size)
        import numpy as np
        from archivist import aiplus_library as al

        class StandIn:
            vision = text = True

            @staticmethod
            def _n(a):
                a = np.asarray(a, np.float32)
                v = np.zeros((a.shape[0], 1024), np.float32); v[:, :a.shape[1]] = a
                return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)

            def encode_images(self, images):
                return self._n([[float(np.asarray(i.convert("RGB"), np.float32).mean() / 255.0), 0.1] for i in images])

            def encode_text(self, texts):
                import p13_event_semantic_pe as hook
                return self._n([[0, 1] if t in hook.NEGATIVE_PROMPTS else [1, 0] for t in texts])

        ae.aiplus_status = lambda: {"ready": True, "reason": "", "path": "STAND-IN", "bytes": 0, "download": {}}
        ae.aiplus_identity = lambda: "STAND_IN_MODEL_KEY"
        al._scorer = lambda: StandIn()
        # the engine step for reels with a stand-in scorer (tests/standin_prepare.py: the real step, no model)
        al._deep_script = lambda: [sys.executable, str(HERE / "standin_prepare.py")]
        t0 = time.time()
        c.post("/api/aiplus/library-index", json={}, headers=H)
        while al.status()["state"] == "running" and time.time() - t0 < 5400:
            time.sleep(2)
        st = al.status()
        timings["theme_index_s"] = round(time.time() - t0, 1)
        check("theme_index_done", st["state"] == "done" and st["indexed"] == st["videos"] == len(vids), st)
        check("prepared_for_reels", st["reels_ready"] == st["reels_videos"] == len(vids), st)
        t = time.perf_counter()
        al.status()
        timings["status_with_prepared_ms"] = round(1000 * (time.perf_counter() - t), 1)
        t = time.perf_counter()
        res = al.search("sea")
        timings["theme_search_ms"] = round(1000 * (time.perf_counter() - t), 1)
        check("theme_search_answers_quickly", len(res) == len(vids) and timings["theme_search_ms"] < 2000, (len(res), timings["theme_search_ms"]))
        page(c, "/library/theme?theme=sea", "theme_results_page")
        t = time.perf_counter()
        r = c.get("/auto/new?library_theme=sea", headers=H)
        pages["reel_from_theme"] = round(time.perf_counter() - t, 3)
        check("reel_from_theme_picks_at_most_64", r.status_code == 200 and r.data.decode("utf-8", "replace").count("name='file'") == ae.MAX_INPUTS,
              r.data.decode("utf-8", "replace").count("name='file'"))

        # 5. the database and the Russian Library
        c.post("/lang", data={"lang": "ru"}, headers=H)
        page(c, "/library", "library_first_page_ru")
        c.post("/lang", data={"lang": "en"}, headers=H)
    from archivist.config import DB_PATH as dbf
    timings["db_mb"] = round(dbf.stat().st_size / 1e6, 1) if dbf.exists() else None
    try:
        import psutil
        timings["app_rss_mb"] = round(psutil.Process().memory_info().rss / 1e6)
    except Exception:
        pass
    # pages that read the videos themselves (the new-reel page checks up to 64 files) get more time
    scans = ("auto_new_one_day", "auto_new_whole_phone", "reel_from_theme")
    slow = {k: v for k, v in pages.items() if v > (max(60.0, max_page) if k in scans else max_page)}
    check("every_page_opens_in_time", not slow, slow)
    service.STOP_EVENT.set()
    out = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "timings": timings, "pages_s": pages, "checks": checks}
    out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("passed", "total", "timings", "pages_s")}, ensure_ascii=False, indent=1))
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
