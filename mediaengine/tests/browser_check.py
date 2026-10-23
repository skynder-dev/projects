"""The app in a real browser (Chromium; Edge on Windows): buttons that post forms, page scripts, no script errors.

The Flask test client sends no browser headers (Origin, Referer, Sec-Fetch-*), so a header rule that makes every
form button fail in a real browser (seen: "Referrer-Policy: no-referrer" -> "Origin: null" -> 403) is only found here.

  python tests/browser_check.py <fixtures_dir> <work_dir> [--channel msedge]

Needs: pip install playwright (on Windows the installed Edge is used; elsewhere Playwright's Chromium).
"""
from __future__ import annotations

import argparse, json, os, shutil, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PORT = 18775


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fixtures"); ap.add_argument("work"); ap.add_argument("--channel", default="")
    a = ap.parse_args()
    work = Path(a.work).resolve(); shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home"); os.environ["ARCHIVIST_PORT"] = str(PORT)
    os.environ["MEDIAENGINE_NO_BROWSER"] = "1"
    src = work / "Мои видео"; shutil.copytree(Path(a.fixtures) / "two", src)
    sys.path.insert(0, str(ROOT / "app"))
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from archivist import auto_edit as ae
    from archivist.web import create_app
    app = create_app()
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=PORT, threaded=True, use_reloader=False), daemon=True).start()
    time.sleep(1.5)
    base = f"http://127.0.0.1:{PORT}"
    checks = []

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": None if ok else str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  " + str(detail)[:600]), flush=True)

    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel=a.channel) if a.channel else p.chromium.launch()
        pg = b.new_page()
        pg.on("pageerror", lambda exc: errors.append("pageerror: " + str(exc)))
        pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        pg.on("response", lambda resp: errors.append(f"HTTP {resp.status}: {resp.url}") if resp.status >= 400 else None)
        r = pg.goto(base + "/auto")
        check("auto_page_opens", r and r.status == 200, r and r.status)
        # a form button (the language switch posts a form)
        with pg.expect_navigation() as nav:
            pg.click("form[action='/lang'] button")
        resp = nav.value
        lang = pg.evaluate("document.documentElement.lang")
        check("form_button_works_in_a_real_browser", resp and resp.status == 200 and lang == "ru", (resp and resp.status, lang))
        with pg.expect_navigation():
            pg.click("form[action='/lang'] button")
        # the rarely used pages behind "More"
        hidden = not pg.is_visible("a.navextra[href='/social']")
        pg.click("a.navmorebtn")
        check("more_shows_the_other_pages", hidden and pg.is_visible("a.navextra[href='/social']"))
        # a new reel through the setup page, like a user
        pg.goto(base + "/auto/new?folder=" + str(src))
        tech = pg.query_selector("input[name=mode][value=technical]")
        if tech and tech.get_attribute("type") == "checkbox":
            tech.check()
        elif tech:
            tech.check()
        pg.check("input[name=length][value='5']")
        pg.check("input[name=format][value='vertical']")
        framing_shown = pg.is_visible(".ae-framing")
        pg.check("input[name=format][value='horizontal']")
        framing_hidden = not pg.is_visible(".ae-framing")
        pg.check("input[name=format][value='vertical']")
        check("framing_choice_only_for_vertical", framing_shown and framing_hidden, (framing_shown, framing_hidden))
        with pg.expect_navigation():
            pg.click("button.ae-big:has-text('Create reel')")
        check("create_reel_in_a_real_browser", "/auto/p/" in pg.url, pg.url)
        pid = int(pg.url.split("/auto/p/")[1].split("?")[0]) if "/auto/p/" in pg.url else 0
        jid = ae.project(pid)["jobs"][0]["id"] if pid else 0
        # the reel being made is shown in the bar at the top of every other page, with a link to it
        pg.goto(base + "/library")
        running_then = ae.job(jid)["status"] in ("queued", "running")
        try:
            pg.wait_for_selector("#jobtext:has-text('Making a reel')", timeout=30_000)
            bar_ok = pg.get_attribute("#jobbar a", "href") == f"/auto/p/{pid}"
        except Exception:
            bar_ok = not running_then and ae.job(jid)["status"] == "done"   # built before the page opened (a fast PC)
        check("reel_progress_on_other_pages", bar_ok, pg.inner_text("#jobbar") if pg.query_selector("#jobbar") else None)
        end = time.time() + 900
        while jid and time.time() < end and ae.job(jid)["status"] in ("queued", "running"):
            time.sleep(2)
        check("reel_built", jid and ae.job(jid)["status"] == "done", jid and ae.job(jid))
        pg.goto(base + f"/auto/p/{pid}")
        with pg.expect_navigation():
            pg.click("#exportForm button.ae-big")
        p_ = ae.project(pid)
        ex = p_["exports"][0] if p_ and p_["exports"] else None
        check("save_mp4_in_a_real_browser", ex and Path(ex["path"]).is_file() and p_["accepted_revision_id"], (pg.url, ex))
        # a small copy for messengers next to the saved reel (one quick encode)
        with pg.expect_navigation(timeout=300_000):
            pg.click("#exportForm button:has-text('Small copy for messengers')")
        small = sorted(Path(ex["path"]).parent.glob("* small.mp4")) if ex else []
        check("small_copy_for_messengers", small and "Small copy saved" in pg.content()
              and small[0].stat().st_size < Path(ex["path"]).stat().st_size, (pg.url, [x.name for x in small]))
        # Check this PC: the test reel is built in the background, the page shows it when ready
        pg.goto(base + "/auto/check")
        with pg.expect_navigation():
            pg.click("button[name=mode][value=technical]")
        building = pg.is_visible("#testRun")
        try:
            pg.wait_for_selector("text=Test reel built", timeout=600_000)
            built = True
        except Exception:
            built = False
        check("check_this_pc_in_the_background", building and built, (building, built))
        # Orders: an order waiting for the owner's OK is run with the page's button (a form posted by a real browser)
        from archivist import orders
        import subprocess as _sp
        orders.set_auto_run(False)
        aside = work / "_order"
        aside.mkdir()
        ff = ae._ffmpeg() or "ffmpeg"
        _sp.run([ff, "-y", "-f", "lavfi", "-i", "color=c=navy:s=540x960", "-frames:v", "1", str(aside / "a.png")], capture_output=True)
        _sp.run([ff, "-y", "-f", "lavfi", "-i", "sine=f=440:d=2", str(aside / "v.wav")], capture_output=True)
        (aside / "order.json").write_text(json.dumps({"schema": orders.SCHEMA, "kind": "render_plan", "title": "Заказ в браузере",
                                                      "plan": {"width": 540, "height": 960, "audio": "v.wav",
                                                               "clips": [{"still": "a.png", "start_s": 0, "end_s": 2}]}}), encoding="utf-8")
        orders.ensure_dirs()
        os.replace(aside, orders.inbox_dir() / "browser-1")
        pg.goto(base + "/auto/orders")
        try:
            pg.wait_for_selector("form[action='/auto/orders/browser-1/run'] button", timeout=60_000)
            with pg.expect_navigation():
                pg.click("form[action='/auto/orders/browser-1/run'] button")
            pg.wait_for_selector("form[action='/auto/orders/browser-1/open']", timeout=180_000)
            ran = True
        except Exception as exc:
            ran = str(exc)[:200]
        done = (orders.done_dir() / "browser-1" / "video.mp4").is_file()
        check("orders_run_button_in_a_real_browser", ran is True and done, (ran, done))
        orders.set_auto_run(True)
        # Finish a video (text on a video needs no add-on): the preview picture, a saved look, the video made, its editor
        from urllib.parse import quote
        from archivist import voice as vo
        clip = sorted(src.glob("*.mp4"))[0]
        pg.goto(base + "/auto/finish?video=" + quote(str(clip)))
        try:
            pg.fill("input[name=t_text]", "Три способа летать дешевле")
            pg.click("[data-preview]:not([data-preview=cover])")
            pg.wait_for_selector("[data-pimg]:not([hidden])", timeout=60_000)
            shown = pg.evaluate("document.querySelector('[data-pimg]').naturalWidth") > 100
        except Exception as exc:
            shown = str(exc)[:200]
        check("finish_page_preview_in_a_real_browser", shown is True, shown)
        try:
            box = pg.locator("[data-looks]").first
            box.locator("[data-look-name]").fill("Мой вид")
            box.locator("[data-look-name]").press("Enter")
            pg.wait_for_function("document.querySelector('[data-look-use]').options.length > 1", timeout=20_000)
            looked = "/auto/finish" in pg.url
        except Exception as exc:
            looked = str(exc)[:200]
        check("finish_page_saves_a_look_without_leaving", looked is True, looked)
        before = {j["id"] for j in vo.list_jobs(500)}
        with pg.expect_navigation():
            pg.click("button.ae-big")
        new = [j["id"] for j in vo.list_jobs(500) if j["id"] not in before]
        end = time.time() + 300
        while new and time.time() < end and vo.read_job(new[0])["state"] not in ("done", "failed"):
            time.sleep(1)
        made = vo.read_job(new[0]) if new else {}
        check("finish_page_makes_the_video", made.get("state") == "done", (new, made.get("result")))
        if made.get("state") == "done":
            pg.goto(base + f"/auto/voice/{made['id']}/edit")
            n0 = pg.locator(".vo-trow").count()
            pg.click("[data-trow-add]")
            pg.click("[data-preview]:not([data-preview=cover])")
            try:
                pg.wait_for_selector("[data-pimg]:not([hidden])", timeout=60_000)
                ed = pg.locator(".vo-trow").count() == n0 + 1
            except Exception as exc:
                ed = str(exc)[:200]
            check("editor_adds_a_text_and_previews", ed is True, ed)
        # converted files: when a running converter job ends, each file gets "Show in folder" / "Open video" (on the
        # Russian page), and a click asks for that file by its job and place - the request is caught here, so no
        # Explorer window opens on the test machine
        from archivist import i18n as _i18n
        from archivist.db import db as _db, now_iso as _now
        with _db() as con:
            cj = con.execute("INSERT INTO jobs(kind,status,created_at,started_at,stage,message,total,done,success,failed,bytes_total,"
                             "bytes_done,options_json) VALUES('convert','running',?,?,'convert','Converting',1,0,0,0,100,10,'{}')",
                             (_now(), _now())).lastrowid
            con.commit()
        _i18n.set_ui_language("ru")
        sent = []

        def _caught(route):
            sent.append(route.request.post_data_json)
            route.fulfill(status=200, content_type="application/json", body='{"ok":true}')
        pg.route("**/api/convert/reveal", _caught)
        pg.goto(base + "/convert")
        outs = [{"source": str(src / "a.mp4"), "output": str(work / "home" / "Converted" / "работа_share_1080p.mp4"),
                 "source_bytes": 50 * 2**20, "output_bytes": 2 * 2**20, "saved_percent": 95.6, "joined": 4}]
        stop_shown = pg.query_selector("[data-cv=stop]") is not None
        with _db() as con:
            con.execute("UPDATE jobs SET status='finished',bytes_done=100,options_json=? WHERE id=?", (json.dumps({"outputs": outs}), cj))
            con.commit()
        try:
            pg.wait_for_selector("[data-cv=reveal]", timeout=15_000)
            pg.wait_for_timeout(300)
            txt = pg.inner_text("#convertResults")
            pg.click("[data-cv=reveal]")
            pg.click("[data-cv=open]")
            pg.wait_for_timeout(800)
            cv = ("Показать в папке" in txt and "Открыть видео" in txt and "меньше на 95,6%" in txt and "МБ" in txt
                  and sent == [{"job": cj, "i": 0, "open": False, "copy": False}, {"job": cj, "i": 0, "open": True, "copy": False}]
                  and "Открыть папку" in pg.inner_text(".pagehead") and "Убрать со страницы" in txt and "95.6" not in txt
                  and "склеено из 4 частей" in txt and stop_shown and pg.query_selector("[data-cv=stop]") is None)
            if cv is True:                      # "Remove from the page": the list goes, and stays gone after a reload
                pg.click("[data-cv=hide]")
                pg.wait_for_timeout(800)
                gone = pg.query_selector("#convertStatus") is None
                pg.goto(base + "/convert")
                cv = gone and pg.query_selector("#convertStatus") is None or f"still shown (gone={gone})"
            if cv is True:                      # join into one / choose on this PC, in Russian; the order of a recording
                order = pg.evaluate("joinOrder(['GX020044.MP4','GX100044.MP4','GX010044.MP4','GOPR0012.MP4','GP010012.MP4'])")
                groups = pg.evaluate("joinGroups(['GX020044.MP4','GX010045.MP4','GX010044.MP4','GX020045.MP4','GX010046.MP4'])")
                singles = pg.evaluate("joinGroups(['GX010045.MP4','GX010044.MP4'])")
                cards = pg.evaluate("joinGroups([{name:'GX020044.MP4',folder:'D:\\\\card2'},{name:'GX010044.MP4',folder:'D:\\\\card1'},"
                                    "{name:'GX010044.MP4',folder:'D:\\\\card2'},{name:'GX020044.MP4',folder:'D:\\\\card1'}])")
                cv = ("Склеить в одно видео" in pg.inner_text("label[title]") and "Выбрать видео на компьютере" in pg.inner_text("#pickConvert")
                      and order == ["GOPR0012.MP4", "GP010012.MP4", "GX010044.MP4", "GX020044.MP4", "GX100044.MP4"]
                      and groups == [["GX010044.MP4", "GX020044.MP4"], ["GX010045.MP4", "GX020045.MP4"], ["GX010046.MP4"]]
                      and singles == [["GX010044.MP4", "GX010045.MP4"]]
                      and cards == [["GX010044.MP4", "GX020044.MP4"], ["GX010044.MP4", "GX020044.MP4"]]) or f"join controls: {order} {groups} {singles} {cards}"
        except Exception as exc:
            cv = str(exc)[:200]
        check("converted_files_show_in_folder_in_a_real_browser", cv is True, (cv, sent, pg.inner_text("#convertResults")[:300] if pg.query_selector("#convertResults") else None))
        pg.unroute("**/api/convert/reveal")
        # Cut…: the player, "Start here" at 2 s, "End here" at 5 s (Russian page) -> the job converts only that part
        clip = sorted(src.glob("*.mp4"))[0]
        with _db() as con:
            vid = con.execute("INSERT INTO inventory(source_key,source_id,source_label,source_kind,path,filename,media_type,size_bytes,"
                              "duration_ms,width,height,mtime,discovered_at,last_seen_at) VALUES('bc-cut','t','t','fixed',?,?,'video',?,14000,640,360,0,?,?)",
                              (str(clip), clip.name, clip.stat().st_size, _now(), _now())).lastrowid
            con.commit()
        try:
            pg.goto(base + f"/convert?ids={vid}")
            pg.click(f"[data-cut-for='{vid}']")
            # Edge plays H.264 (the player is used); Playwright's own Chromium does not (the times are typed, as the page says)
            pg.wait_for_function(f"document.querySelector('#cvCut{vid} video').readyState>=1||"
                                 f"document.querySelector('#cvCut{vid} .cvNoPlay').style.display==='block'", timeout=20_000)
            played = pg.evaluate(f"document.querySelector('#cvCut{vid} video').readyState>=1")
            if played:
                pg.evaluate(f"document.querySelector('#cvCut{vid} video').currentTime=2")
                pg.wait_for_timeout(400)
                pg.click(f"#cvCut{vid} [data-set=s]")
                pg.evaluate(f"document.querySelector('#cvCut{vid} video').currentTime=5")
                pg.wait_for_timeout(400)
                pg.click(f"#cvCut{vid} [data-set=e]")
            else:
                pg.fill(f"#cvCut{vid} .cvS", "0:02")
                pg.dispatch_event(f"#cvCut{vid} .cvS", "change")
                pg.fill(f"#cvCut{vid} .cvE", "5")
                pg.dispatch_event(f"#cvCut{vid} .cvE", "change")
                print("INFO this browser does not play H.264: the cut's times were typed", flush=True)
            note = pg.inner_text(f".convertRow:has(.convertCheck[value='{vid}']) .cvCutNote")
            pg.check("input[name=presetChoice][value=small_720p]")
            pg.click("#startConvert")
            pg.wait_for_url("**/convert", timeout=15_000)
            for _ in range(120):
                with _db() as con:
                    jr = con.execute("SELECT status,options_json FROM jobs WHERE kind='convert' ORDER BY id DESC LIMIT 1").fetchone()
                if jr and jr["status"] in ("finished", "failed", "cancelled"):
                    break
                time.sleep(0.5)
            jo = json.loads(jr["options_json"] or "{}")
            outc = (jo.get("outputs") or [{}])[0]
            from archivist.auto_edit import _probe as _pr
            cdur = float(_pr(Path(outc["output"]))["format"]["duration"]) if outc.get("output") else 0
            cut_ok = (note == "фрагмент 0:02–0:05" and jr["status"] == "finished" and jo.get("cuts") == {str(vid): [2.0, 5.0]}
                      and abs(cdur - 3.0) <= 0.1) or (note, jr["status"], jo.get("cuts"), cdur, outc)
        except Exception as exc:
            cut_ok = str(exc)[:300]
        check("convert_a_part_of_a_video_in_a_real_browser", cut_ok is True, cut_ok)
        # the cut panel open in a narrow window (420 px): nothing wider than the window
        try:
            pn = b.new_page(viewport={"width": 420, "height": 900})
            pn.goto(base + f"/convert?ids={vid}")
            pn.click(f"[data-cut-for='{vid}']")
            pn.wait_for_selector(f"#cvCut{vid}", timeout=10_000)
            pn.wait_for_timeout(1500)
            sw = pn.evaluate("document.documentElement.scrollWidth")
            # a size target too small for the length is said (a 50-minute video in 50 MB)
            pn.check("input[name=presetChoice][value=share_1080p]")
            pn.evaluate(f"(()=>{{const c=document.querySelector(\".convertCheck[value='{vid}']\");c.checked=true;c.dataset.durationMs='3000000';"
                        "const t=document.getElementById('targetMb');t.value='50';t.dispatchEvent(new Event('input'))})()")
            pn.wait_for_timeout(300)
            small_note = pn.inner_text("#estimateNote")
            pn.close()
            if "размытой" not in small_note:
                sw = f"no warning for a small size: {small_note}"
        except Exception as exc:
            sw = str(exc)[:200]
        check("convert_cut_panel_fits_a_narrow_window", isinstance(sw, int) and sw <= 422, sw)
        _i18n.set_ui_language("en")
        # every page without an id fits the window: 1280 px and a narrow 420 px, in Russian (the longer words) and English
        skip = ("/api", "/static", "/media", "/diagnostics", "/auto/exports/open", "/thumb", "/stream", "/file")
        plain = sorted({r.rule for r in app.url_map.iter_rules() if "GET" in r.methods and not r.arguments
                        and not r.rule.startswith(skip) and not r.rule.endswith((".json", ".csv", ".zip", ".png", ".jpg", ".js", ".css", ".ico"))})
        wide = []
        for lang in ("ru", "en"):
            _i18n.set_ui_language(lang)
            for vw in (1280, 420):
                pv = b.new_page(viewport={"width": vw, "height": 900})
                for u in plain:
                    try:
                        rr = pv.goto(base + u, timeout=30_000)
                    except Exception:
                        continue
                    if not rr or not rr.headers.get("content-type", "").startswith("text/html"):
                        continue
                    sw = pv.evaluate("document.documentElement.scrollWidth")
                    if sw > vw + 2:
                        wide.append(f"{lang} {vw}px {u}: {sw}px")
                pv.close()
        _i18n.set_ui_language("en")
        check("pages_fit_the_window_wide_and_narrow", not wide, wide[:10])
        check("no_script_errors", not errors, errors[:5])
        b.close()
    out = {"passed": sum(c["pass"] for c in checks), "total": len(checks), "checks": checks}
    (work / "browser_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"passed": out["passed"], "total": out["total"]}))
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
