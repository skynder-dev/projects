"""Library through the app routes, like a user: add a folder, import + analyse its videos, mark one Private.

  python tests/library_flow_check.py <fixtures_dir> <work_dir>

- a folder added on the Import page is scanned: every video in it is listed (names with ' [ ] and Cyrillic);
- "Import + analyse" finishes; the videos are in the Library with thumbnails and an item page; a screen recording
  without a written length gets its real length;
- a video marked Private leaves the Library, its original stays where it was, unchanged (a local folder is only
  read), and a reel built from that folder never uses it;
- the Library pages render in Russian too; no source file is changed by any of this;
- Library search by theme (AI+, with a stand-in scorer here; the real model on Windows CI in real_models_check.py):
  index once, search, Private / rejected never shown, Russian pages, the search waits while a reel is built;
- the data folder itself has Cyrillic letters (as under the Windows user folder of a Cyrillic user name), so previews, caches and the reel
  engine's work folder are all checked under such a path.
"""
from __future__ import annotations

import hashlib, html, json, os, shutil, subprocess, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    fx, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    # the data folder has Cyrillic letters too (C:\Users\Дмитрий\MediaEngine\... on a PC without D:\Archivist):
    # previews, caches and the reel engine's work folder all live under it
    os.environ["ARCHIVIST_HOME"] = str(work / "Данные пользователя")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
    from media_measure import ffmpeg_exe
    src = work / "Мои видео 'тест' [1]"
    src.mkdir()
    for f in sorted((fx / "two").glob("*.mp4"))[:2]:
        shutil.copy2(f, src / f.name)
    phone = fx / "phone" / "IMG_0042.MOV"
    if phone.exists():
        shutil.copy2(phone, src / "Отпуск [пляж] 'день 2'.MOV")
    rec = src / "screen recording.webm"
    with rec.open("wb") as fh:
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25,hue=h=t*40", "-t", "6",
                        "-c:v", "libvpx", "-deadline", "realtime", "-b:v", "500k", "-live", "1", "-f", "webm", "pipe:1"], stdout=fh, check=False)
    if rec.stat().st_size < 2000:
        rec.unlink()
        print("SKIP recording without a length: this ffmpeg cannot write WebM")
    before = {p.name: sha(p) for p in src.iterdir()}
    names = sorted(before)

    from archivist.web import create_app
    from archivist.db import db
    from archivist import service, auto_edit as ae
    app = create_app()
    checks = []

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def rows():
        with db() as con:
            return [dict(r) for r in con.execute("SELECT * FROM inventory WHERE path LIKE ? ORDER BY filename", (str(src) + "%",)).fetchall()]

    def wait_job(jid, limit=900):
        t0 = time.time()
        j = {}
        while jid and time.time() - t0 < limit:
            with db() as con:
                row = con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            if row is None:
                return {}
            j = dict(row)
            if j["status"] in ("finished", "partial", "failed", "cancelled"):
                return j
            time.sleep(1)
        return j

    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}
    with app.test_client() as c:
        r = c.post("/import/add-source", data={"path": str(src), "label": "Мои тестовые видео"}, headers=H)
        check("add_folder_source", r.status_code == 302, r.status_code)
        t0 = time.time()
        while time.time() - t0 < 180 and (len(rows()) < len(names) or service.DISCOVERY_LOCK.locked()):
            if not service.DISCOVERY_LOCK.locked() and len(rows()) < len(names):
                service.start_discovery()
            time.sleep(1)
        found = sorted(r_["filename"] for r_ in rows())
        check("every_video_found", found == names, (found, names))
        r = c.get("/import", query_string={"source_kind": "fixed"}, headers=H)
        page = html.unescape(r.data.decode("utf-8", "replace"))
        check("import_page_lists_them", r.status_code == 200 and all(n in page for n in names), r.status_code)

        ids = [r_["id"] for r_ in rows()]
        r = c.post("/api/selection-action", json={"action": "import_analyze", "ids": ids}, headers=H)
        jid = (r.get_json() or {}).get("job_id")
        check("import_analyse_started", r.status_code == 200 and jid, r.data[:300])
        j = wait_job(jid) if jid else {}
        check("import_analyse_finished", j.get("status") == "finished", (j.get("status"), j.get("message"), j.get("error")))
        inv = {r_["filename"]: r_ for r_ in rows()}
        check("all_in_working_set_and_analysed", all(r_["work_selected"] == 1 and r_.get("analysis_version") == 4 for r_ in inv.values()),
              [(k, v["work_selected"], v.get("analysis_version"), v.get("analysis_status"), v.get("error")) for k, v in inv.items()])
        check("library_knows_every_length", all(int(r_.get("duration_ms") or 0) > 2000 for r_ in inv.values()),
              [(k, v.get("duration_ms")) for k, v in inv.items()])
        if rec.exists():     # a screen recording without a written length: analysed and cut into clips like any video
            rr = inv.get(rec.name, {})
            r = c.post("/api/selection-action", json={"action": "media_brain", "ids": [rr.get("id")]}, headers=H)
            mj = wait_job((r.get_json() or {}).get("job_id") or 0, 600)
            with db() as con:
                spans = [tuple(x) for x in con.execute("SELECT start_ms,end_ms FROM virtual_clips WHERE inventory_id=?", (rr.get("id"),)).fetchall()]
            check("recording_without_length_analysed_and_clipped", rr.get("quality_status") == "ok" and not rr.get("error")
                  and mj.get("status") == "finished" and spans and max(e for _, e in spans) >= 4000,
                  (rr.get("quality_status"), rr.get("error"), mj.get("status"), mj.get("message"), spans))
        r = c.get("/library", headers=H)
        page = html.unescape(r.data.decode("utf-8", "replace"))
        check("library_lists_them", r.status_code == 200 and all(n in page for n in names), r.status_code)
        thumbs_ok = []
        for n, r_ in inv.items():
            ok = False
            for _ in range(60):
                t = c.get(f"/thumb/{r_['id']}", headers=H)
                if t.status_code == 200 and t.mimetype in ("image/jpeg", "image/png", "image/webp") and len(t.data) > 500:
                    ok = True
                    break
                time.sleep(1)
            thumbs_ok.append((n, ok))
        check("thumbnails", all(ok for _, ok in thumbs_ok), thumbs_ok)
        bad_items = [n for n, r_ in inv.items() if c.get(f"/item/{r_['id']}", headers=H).status_code != 200]
        check("item_pages", not bad_items, bad_items)

        # mark one Private: it leaves the Library, the original stays, a reel never uses it
        priv = inv[names[0]]
        r = c.post("/api/selection-action", json={"action": "private", "ids": [priv["id"]]}, headers=H)
        pj = wait_job((r.get_json() or {}).get("job_id") or 0, 300)
        after = {r_["filename"]: r_ for r_ in rows()}.get(names[0], {})
        check("private_job_finished", pj.get("status") == "finished" and after.get("analysis_status") == "private", (pj.get("status"), after.get("analysis_status")))
        page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
        check("private_left_the_library", names[0] not in page and names[1] in page)
        check("private_original_stays_unchanged", (src / names[0]).is_file() and sha(src / names[0]) == before[names[0]])
        # "Make a reel" from videos selected in the Library: the new-reel page with exactly them (never a Private one)
        sel = [inv[n]["id"] for n in names[:3]]
        r = c.get("/auto/from-library", query_string={"ids": ",".join(map(str, sel))}, headers={**H, "Sec-Fetch-Site": "same-origin"})
        loc = urllib.parse.unquote(r.headers.get("Location", ""))
        check("library_selection_makes_a_reel_setup", r.status_code == 302 and "/auto/new?" in loc and names[1] in loc
              and names[0] not in loc, (r.status_code, loc[:300]))
        r = c.post("/auto/create", data={"folder": str(src), "length": "5", "format": "vertical", "sound": "auto", "mode": "technical"}, headers=H)
        okc = r.status_code == 302 and "/auto/p/" in r.headers.get("Location", "")
        check("reel_from_the_same_folder_starts", okc, r.status_code)
        if okc:
            pid = int(r.headers["Location"].rstrip("/").split("/")[-1])
            jid2 = ae.project(pid)["jobs"][0]["id"]
            t0 = time.time()
            while time.time() - t0 < 900 and ae.job(jid2)["status"] in ("queued", "running"):
                time.sleep(1)
            aj = ae.job(jid2)
            rv = ae.revision(aj.get("revision_id") or 0) if aj["status"] == "done" else None
            used = {s["source_name"] for s in (rv or {}).get("result", {}).get("segments", [])}
            check("reel_never_uses_the_private_video", rv and used and names[0] not in used, (aj["status"], aj.get("error"), used))

        # archive a copy (Cyrillic names must survive), reject another: originals stay where they are, unchanged
        from archivist.config import load_config, save_config
        cfg = load_config(); cfg["archive_root"] = str(work / "Архив"); save_config(cfg)
        cyr = next((n for n in names if not n.isascii()), None)
        if cyr:
            r = c.post("/api/selection-action", json={"action": "archive", "ids": [inv[cyr]["id"]]}, headers=H)
            aj = wait_job((r.get_json() or {}).get("job_id") or 0, 300)
            arow = {r_["filename"]: r_ for r_ in rows()}.get(cyr, {})
            ap = Path(arow.get("archive_path") or "")
            check("archive_copy_keeps_the_names", aj.get("status") == "finished" and ap.is_file() and ap.name == cyr
                  and ap.parent.name == "Мои тестовые видео" and sha(ap) == before[cyr] and sha(src / cyr) == before[cyr],
                  (aj.get("status"), str(ap)))
        if rec.exists():
            r = c.post("/api/selection-action", json={"action": "reject", "ids": [inv[rec.name]["id"]]}, headers=H)
            rj = wait_job((r.get_json() or {}).get("job_id") or 0, 300)
            page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
            check("rejected_leaves_the_library_original_kept", rj.get("status") == "finished" and rec.name not in page
                  and sha(rec) == before[rec.name], rj.get("status"))

        # Library search by theme (AI+) with a STAND-IN scorer (the real model: tests/real_models_check.py on Windows CI):
        # index once, search instantly, Private / rejected videos never indexed or shown
        import numpy as np
        from archivist import aiplus_library as al
        from i18n_coverage import english_left, page_texts
        real_status, real_ident, real_scorer, real_deep = ae.aiplus_status, ae.aiplus_identity, al._scorer, al._deep_script

        class StandIn:
            vision = text = True                     # the parts "open" at once

            @staticmethod
            def _n(a):
                a = np.asarray(a, np.float32)
                v = np.zeros((a.shape[0], 1024), np.float32); v[:, :a.shape[1]] = a
                return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)

            def encode_images(self, images):
                return self._n([[float(np.asarray(i.convert("RGB"), np.float32).std(axis=2).mean() / 255.0), 0.05] for i in images])

            def encode_text(self, texts):
                import p13_event_semantic_pe as hook
                return self._n([[0, 1] if t in hook.NEGATIVE_PROMPTS else [1, 0] for t in texts])

        def russian_left(urls):
            c.post("/lang", data={"lang": "ru"}, headers=H)
            left = []
            for u in urls:
                body = c.get(u, headers=H).data.decode("utf-8", "replace")
                left += [f"{u}: {t.strip()[:80]}" for t in page_texts(body) if english_left(html.unescape(t))]
            c.post("/lang", data={"lang": "en"}, headers=H)
            return left

        def index_and_wait(limit=300):
            c.post("/api/aiplus/library-index", json={}, headers=H)
            t0 = time.time()
            while al.status()["state"] == "running" and time.time() - t0 < limit:
                time.sleep(0.5)
            return al.status()

        def frame_ids():
            with db() as con:
                return {int(r[0]) for r in con.execute("SELECT inventory_id FROM aiplus_frames").fetchall()}

        ae.aiplus_status = lambda: {"ready": True, "reason": "", "path": "STAND-IN", "bytes": 0, "download": {}}
        ae.aiplus_identity = lambda: "STAND_IN_MODEL_KEY"
        al._scorer = lambda: StandIn()
        # the engine step "for reels" with a stand-in scorer (tests/standin_prepare.py: the real step, no model)
        al._deep_script = lambda: [sys.executable, str(HERE / "standin_prepare.py")]
        try:
            page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
            check("library_offers_theme_search_with_aiplus", "Find by theme (AI+)" in page and "Prepare AI+ for the whole Library" in page)
            # before the search is prepared: the card's hint and the results page's note, in Russian
            left = russian_left(("/library", "/library/theme?theme=sea", "/library/theme"))
            check("library_theme_search_unprepared_in_russian", not left, left[:10])
            st = index_and_wait()
            check("library_theme_index_done", st["state"] == "done" and st["indexed"] == st["videos"] > 0 and st["texts_missing"] == 0
                  and "eta_s" in st and st["eta_s"] is None, st)
            # ... and what AI+ reels need, for every Library video (the shared cache every AI+ build reads)
            check("library_prepared_for_reels", st["reels_ready"] == st["reels_videos"] > 0 and not al.needs_preparing(st)
                  and len(list(al._scout_dir().glob("*.npy"))) == st["reels_videos"], st)
            page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
            check("library_says_all_prepared", "AI+ is prepared for the whole Library." in page and "id='apIdx'" not in page)
            res = al.search("sea")
            names_found = {x["filename"] for x in res}
            check("library_theme_search_never_shows_private_or_rejected", res and names[0] not in names_found
                  and (not rec.exists() or rec.name not in names_found), names_found)
            r = c.get("/library/theme", query_string={"theme": "sea"}, headers=H)
            check("library_theme_page", r.status_code == 200 and "/item/" in r.data.decode("utf-8", "replace"), r.status_code)
            # "Make a reel about this theme": the new-reel page picks the matching videos itself (no paths in the
            # address), AI+ and the theme already chosen - also when the AI model is there too (AI is listed first)
            tp = r.data.decode("utf-8", "replace")
            real_ms = ae.model_status
            ae.model_status = lambda: {"ready": True, "reason": "", "path": "STAND-IN"}
            try:
                np_ = c.get("/auto/new", query_string={"library_theme": "sea"}, headers={**H, "Sec-Fetch-Site": "same-origin"})
            finally:
                ae.model_status = real_ms
            raw = np_.data.decode("utf-8", "replace")
            npage = html.unescape(raw)
            import re as _re
            files = [html.unescape(x) for x in _re.findall(r"<input type='hidden' name='file' value='([^']*)'>", raw)]
            check("library_theme_makes_a_reel_setup", "/auto/new?library_theme=sea" in tp and np_.status_code == 200 and files
                  and "value='semantic' >" in npage.replace("value='semantic' checked", "x") and "value='semantic_plus' checked" in npage
                  and "<option value='sea' selected>" in npage
                  and all(Path(x).name not in (names[0], rec.name) for x in files), (len(files), np_.status_code, files))
            # a link from outside the app cannot make this PC open a network share; from the app's pages it can
            bad = c.get("/auto/new", query_string={"folder": r"\\192.0.2.1\share"}, headers={**H, "Sec-Fetch-Site": "none"})
            check("network_folder_link_from_outside_refused", "Network folders can only be opened from MediaEngine itself"
                  in bad.data.decode("utf-8", "replace"), bad.status_code)
            # time left while preparing: from the pace of this run
            saved = dict(al._STATE)
            al._STATE.update(state="running", waiting=False, t0=time.time() - 10, n0=0, done=2, total=6)
            eta = al.status()["eta_s"]
            al._STATE.update(saved)
            check("library_theme_index_time_left", eta is not None and 15 <= eta <= 25, eta)
            # while a reel is being built the search waits (one AI+ model in memory at a time), then goes on
            with db() as con:
                reel_job = con.execute("SELECT id,status FROM ae_jobs ORDER BY id DESC LIMIT 1").fetchone()
            st_wait = {}
            if reel_job:
                with db() as con:
                    con.execute("DELETE FROM aiplus_frames"); con.execute("UPDATE ae_jobs SET status='running' WHERE id=?", (reel_job["id"],)); con.commit()
                al.start()
                time.sleep(4)
                st_wait = al.status()
                with db() as con:
                    con.execute("UPDATE ae_jobs SET status=? WHERE id=?", (reel_job["status"], reel_job["id"])); con.commit()
                t0 = time.time()
                while al.status()["state"] == "running" and time.time() - t0 < 300:
                    time.sleep(0.5)
            st = al.status()
            check("library_index_waits_for_a_reel_then_finishes", reel_job and st_wait.get("waiting") and st_wait.get("state") == "running"
                  and st["state"] == "done" and st["indexed"] == st["videos"], (dict(reel_job) if reel_job else None, st_wait, st))
            # the step for reels is ended while a reel is being built (the reel gets the computer) and goes on afterwards
            st_pause = {}
            if reel_job:
                shutil.rmtree(al._scout_dir(), ignore_errors=True)
                os.environ["STANDIN_PREPARE_DELAY"] = "0.5"
                try:
                    al.start()
                    t0 = time.time()
                    while time.time() - t0 < 120 and not (al.status()["phase"] == "reels" and al._PROC.get("p") is not None):
                        time.sleep(0.2)
                    time.sleep(1.5)
                    running_mid = al.status()
                    with db() as con:
                        con.execute("UPDATE ae_jobs SET status='running' WHERE id=?", (reel_job["id"],)); con.commit()
                    t0 = time.time()
                    while time.time() - t0 < 30 and not al.status()["waiting"]:
                        time.sleep(0.2)
                    st_pause = al.status()
                    proc_gone = al._PROC.get("p") is None
                    with db() as con:
                        con.execute("UPDATE ae_jobs SET status=? WHERE id=?", (reel_job["status"], reel_job["id"])); con.commit()
                    t0 = time.time()
                    while al.status()["state"] == "running" and time.time() - t0 < 300:
                        time.sleep(0.5)
                finally:
                    os.environ.pop("STANDIN_PREPARE_DELAY", None)
                st = al.status()
                check("library_prepare_for_reels_pauses_for_a_reel_then_finishes",
                      running_mid["phase"] == "reels" and st_pause.get("waiting") and proc_gone and st["state"] == "done"
                      and st["reels_ready"] == st["reels_videos"] > 0, (running_mid, st_pause, st))
            # Stop: the engine step ends at once, what is done stays done
            shutil.rmtree(al._scout_dir(), ignore_errors=True)
            os.environ["STANDIN_PREPARE_DELAY"] = "0.5"
            try:
                al.start()
                t0 = time.time()
                while time.time() - t0 < 120 and al._PROC.get("p") is None:
                    time.sleep(0.2)
                proc = al._PROC.get("p")
                c.post("/api/aiplus/library-index", json={"stop": True}, headers=H)
                t0 = time.time()
                while al.status()["state"] == "running" and time.time() - t0 < 60:
                    time.sleep(0.2)
            finally:
                os.environ.pop("STANDIN_PREPARE_DELAY", None)
            st = al.status()
            check("library_prepare_stop_ends_the_engine_step", proc is not None and proc.poll() is not None and st["state"] == "stopped"
                  and st["reels_ready"] < st["reels_videos"], st)
            st = index_and_wait()
            check("library_prepare_continues_where_it_stopped", st["state"] == "done" and st["reels_ready"] == st["reels_videos"], st)
            left = russian_left(("/library", "/library/theme?theme=sea", "/library/theme?theme=kids"))
            check("library_theme_search_in_russian", not left, left[:10])
            # a video made Private AFTER it was indexed: never shown, and its row goes on the next preparation
            visible = sorted(frame_ids())
            late = next((r_ for r_ in rows() if r_["id"] in visible and r_["filename"] != cyr), None)
            if late:
                r = c.post("/api/selection-action", json={"action": "private", "ids": [late["id"]]}, headers=H)
                wait_job((r.get_json() or {}).get("job_id") or 0, 300)
                gone_from_search = all(x["inventory_id"] != late["id"] for x in al.search("sea"))
                st = index_and_wait()
                late_sha = str(late.get("sha256") or "").lower()
                check("library_theme_private_after_index_never_shown_and_dropped", gone_from_search and late["id"] not in frame_ids()
                      and st["state"] == "done" and late_sha and not (al._scout_dir() / (late_sha + ".npy")).exists(),
                      (gone_from_search, late["id"], frame_ids(), st))
            # descriptions changed (a new version): the themes are prepared again, the frames are kept
            with db() as con:
                con.execute("UPDATE aiplus_texts SET model_key=model_key||'-old' WHERE theme='sea'"); con.commit()
            st0 = al.status()
            frames_before = frame_ids()
            st = index_and_wait()
            check("library_theme_new_descriptions_prepared_again", st0["texts_missing"] == 1 and al.needs_preparing(st0)
                  and st["texts_missing"] == 0 and frame_ids() == frames_before and al.search("sea") is not None, (st0, st))
        finally:
            ae.aiplus_status, ae.aiplus_identity, al._scorer, al._deep_script = real_status, real_ident, real_scorer, real_deep

        # the same pages in Russian
        c.post("/lang", data={"lang": "ru"}, headers=H)
        ru = {u: c.get(u, headers=H) for u in ("/library", "/import?source_kind=fixed", f"/item/{inv[cyr or names[1]]['id']}", "/jobs", "/media")}
        check("library_pages_in_russian", all(x.status_code == 200 and "<html lang='ru'>" in x.data.decode("utf-8", "replace") for x in ru.values()),
              {u: x.status_code for u, x in ru.items()})
        c.post("/lang", data={"lang": "en"}, headers=H)

        # a copy of a Private video: its moments leave the clip page, Composer and Social too (review 2026-10-17)
        from archivist.db import inventory_visible
        with db() as con:
            vis = [r_ for r_ in rows() if r_["work_selected"] == 1 and r_.get("sha256") and inventory_visible(con, r_["id"])]
        if vis:
            one = vis[0]
            r = c.post("/api/selection-action", json={"action": "media_brain", "ids": [one["id"]]}, headers=H)
            wait_job((r.get_json() or {}).get("job_id") or 0, 600)
            with db() as con:
                oc = con.execute("SELECT id FROM virtual_clips WHERE inventory_id=? ORDER BY id LIMIT 1", (one["id"],)).fetchone()
            from archivist import composer as _cp, social_lab as _sl
            if oc:
                comp_id = _cp.create_composition([int(oc["id"])], "9:16", "copy test")
                with db() as con:
                    con.execute("INSERT OR REPLACE INTO ignored_hashes(sha256,reason,created_at) VALUES(?,?,?)", (one["sha256"], "test-composer", "t"))
                    con.commit()
                try:
                    _cp.create_composition([int(oc["id"])], "9:16", "again")
                    refused = False
                except ValueError:
                    refused = True
                with db() as con:
                    soc = _sl._composition_source_visibility(con, comp_id)
                det = _cp.composition_detail(comp_id)
                check("a_copy_of_a_private_video_no_clip_page_composition_or_social",
                      c.get(f"/clip/{oc['id']}", headers=H).status_code == 404 and c.get(f"/clip-preview/{oc['id']}", headers=H).status_code == 404
                      and refused and not soc["safe"] and det["hidden_items"] == 1 and not det["items"] and not det.get("output_path"),
                      (refused, soc, det.get("hidden_items")))
                with db() as con:      # the next checks need this video as it was
                    con.execute("DELETE FROM ignored_hashes WHERE sha256=? AND reason='test-composer'", (one["sha256"],)); con.commit()
            else:
                print("SKIP copy of a Private video in Composer: no clips were made")
        else:
            print("SKIP copy of a Private video in Composer: no visible video left")
        # QA review 2026-10-17: "Remove from Library" survives a restart; "Make a reel" never takes a removed video; a
        # copy of a Private video is not shown; odd page numbers / ids are refused cleanly
        live = [r_ for r_ in rows() if r_["work_selected"] == 1 and r_["analysis_status"] != "private" and r_.get("sha256")]
        if len(live) < 2:
            print("SKIP library removal checks: fewer than 2 videos left", [r_["filename"] for r_ in live])
        else:
            other, victim = live[0], live[1]
            with db() as con:            # the same content as a Private video (a copy): not shown
                con.execute("INSERT OR REPLACE INTO ignored_hashes(sha256,reason,created_at) VALUES(?,?,?)", (other["sha256"], "test", "t"))
                con.commit()
            page = html.unescape(c.get("/library", headers=H).data.decode("utf-8", "replace"))
            check("a_copy_of_a_private_video_is_not_shown", other["filename"] not in page and victim["filename"] in page, other["filename"])
            r = c.post("/api/selection-action", json={"action": "remove", "ids": [victim["id"]]}, headers=H)
            from archivist.db import init_db
            init_db()                                  # what every app start does
            with db() as con:
                ws = con.execute("SELECT work_selected FROM inventory WHERE id=?", (victim["id"],)).fetchone()[0]
            check("removed_from_library_stays_removed_after_restart", r.status_code == 200 and ws == 0, (r.status_code, ws))
            r = c.get("/auto/from-library", query_string={"ids": str(victim["id"])}, headers={**H, "Sec-Fetch-Site": "same-origin"})
            check("make_a_reel_never_takes_a_removed_video", r.status_code == 400, r.status_code)
        r1 = c.get("/library?page=abc", headers=H)
        r2 = c.post("/api/selection-action", json={"action": "private", "ids": "12"}, headers=H)
        check("odd_page_and_ids_refused_cleanly", r1.status_code == 200 and r2.status_code == 400, (r1.status_code, r2.status_code))

    service.STOP_EVENT.set()
    now = {p.name: sha(p) for p in src.iterdir() if p.is_file()}
    check("sources_unchanged", now == before, sorted(set(now.items()) ^ set(before.items()))[:4])
    out = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks}
    (work / "library_flow.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"passed": out["passed"], "total": out["total"]}))
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    import faulthandler      # a hang on a CI runner prints where every thread is, then the check fails
    faulthandler.dump_traceback_later(2400, exit=True)
    sys.exit(main())
