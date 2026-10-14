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
        try:
            pg.wait_for_selector("#jobtext:has-text('Making a reel')", timeout=120_000)
            bar_ok = pg.get_attribute("#jobbar a", "href") == f"/auto/p/{pid}"
        except Exception:
            bar_ok = ae.job(jid)["status"] == "done"          # already built (a fast PC): nothing to show
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
        check("no_script_errors", not errors, errors[:5])
        b.close()
    out = {"passed": sum(c["pass"] for c in checks), "total": len(checks), "checks": checks}
    (work / "browser_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"passed": out["passed"], "total": out["total"]}))
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
