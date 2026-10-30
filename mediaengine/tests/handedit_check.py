"""Checks of Edit by hand (handedit.py, handedit_web.py): videos added (a file, a downloaded video), pieces cut,
moved, without sound, split; the MP4 made in the background in each format with the pieces in their order; only the
edit's own videos served to the page (ranges for seeking), a playable copy made of a video the browser cannot play;
the pages in Russian. With --channel (msedge on Windows): the editor used in a real browser - the video plays,
split, remove, undo, a piece's edge dragged, a piece dragged to the start, the MP4 made from the page.

  python tests/handedit_check.py <work_dir> [--channel msedge]   -> JSON with passed / total; exit 1 when a check fails
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS: list = []


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {str(detail)[:600]}"), flush=True)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--channel", default="")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    shutil.rmtree(work, ignore_errors=True)
    (work / "src").mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    port = 18776 if a.channel else 8765                   # (the browser's own server needs a port of its own)
    os.environ["ARCHIVIST_PORT"] = str(port)
    os.environ.setdefault("MEDIAENGINE_NO_BROWSER", "1")
    os.environ.setdefault("MEDIAENGINE_UPDATES", "off")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import auto_edit as ae, handedit as HE, voice as vo
    ff = str(ae._ffmpeg())
    src = work / "src"
    # the videos: a wide one with sound, a tall one without, an AVI (the browser cannot play it), a long-named one
    made = [
        run([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=1280x720:r=30:d=3", "-f", "lavfi", "-i", "sine=f=440:d=3",
             "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(src / "red.mp4")]),
        run([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=green:s=720x1280:r=25:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             str(src / "green no sound.mp4")]),
        run([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=1920x1080:r=30:d=4", "-f", "lavfi", "-i", "sine=f=660:d=4",
             "-shortest", "-c:v", "mpeg4", "-q:v", "4", "-c:a", "mp3", str(src / "синий файл.avi")])]
    check("fixtures: three videos made", all(x.returncode == 0 for x in made), [x.stderr[-200:] for x in made])
    red, green, blue = src / "red.mp4", src / "green no sound.mp4", src / "синий файл.avi"

    # 1. the edit: added, pieces checked against their videos, a stranger's file refused
    eid = HE.new("Мой монтаж", "16:9")
    e = HE.add(eid, [str(red), str(green), str(blue), str(src / "nope.mp4"), str(src)])
    names = [Path(p["src"]).name for p in e["pieces"]]
    i_blue = HE.info(blue)
    check("add: videos at the end with their whole length, what is not a video said; an AVI is not played by a browser",
          names == ["red.mp4", "green no sound.mp4", "синий файл.avi"] and len(e.get("not_added") or []) == 2
          and abs(e["pieces"][2]["out"] - 4.0) < 0.2 and i_blue.get("plays") is False and HE.info(red).get("plays") is True
          and HE.info(green).get("audio") is False, (names, e.get("not_added"), i_blue))
    P = e["pieces"]
    e = HE.save(eid, "Монтаж: проверка", "9:16", [dict(P[2], **{"in": 1.0, "out": 2.5}), dict(P[0], **{"in": 0.5, "out": 2.0, "mute": True}),
                                                  dict(P[1], **{"in": 0.0, "out": 9.0}), dict(P[0], **{"in": 2.9, "out": 3.0})])
    lens = [round(p["out"] - p["in"], 2) for p in e["pieces"]]
    try:
        HE.save(eid, pieces=[{"src": str(Path(sys.executable)), "in": 0, "out": 1}])
        stranger = "accepted"
    except HE.EditError as exc:
        stranger = str(exc)
    try:
        HE.save(eid, fmt="2:1")
        odd_fmt = "accepted"
    except HE.EditError as exc:
        odd_fmt = str(exc)
    check("save: order, cuts and sound kept; an end past the video's end and a too short piece corrected; a file not "
          "added and an unknown format refused",
          [Path(p["src"]).name for p in e["pieces"]] == ["синий файл.avi", "red.mp4", "green no sound.mp4", "red.mp4"]
          and lens == [1.5, 1.5, 2.0, 0.2] and e["pieces"][1]["mute"] is True and e["format"] == "9:16"
          and "not added" in stranger and "formats" in odd_fmt, (lens, stranger, odd_fmt))

    # 2. the MP4 through the queue (as the page asks for it)
    def made_by(jid, limit=300):
        t0 = time.time()
        while vo.read_job(jid)["state"] in ("waiting", "working") and time.time() - t0 < limit:
            time.sleep(0.3)
        return vo.read_job(jid)

    def probe(p):                                        # (the program's own probe: FFmpeg only, as on the owner's PC)
        try:
            return ae.probe_any(Path(p))
        except Exception:
            return {}

    def colour(p, t):
        raw = subprocess.run([ff, "-v", "error", "-ss", f"{t}", "-i", str(p), "-frames:v", "1", "-vf", "scale=4:4", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=60).stdout
        return tuple(raw[:3]) if len(raw) >= 3 else None

    def loudest(p, a, b):
        cp = run([ff, "-v", "info", "-ss", f"{a}", "-t", f"{b - a}", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"])
        m = re.search(r"max_volume: (-?[\d.]+) dB", cp.stderr or "")
        return float(m.group(1)) if m else None

    jid = HE.new_render(eid)
    j = made_by(jid)
    res = j.get("result") or {}
    out = vo._job_dir(jid) / "edit.mp4"
    pr = probe(out)
    vs = next((s for s in pr.get("streams") or [] if s.get("codec_type") == "video"), {})
    au = next((s for s in pr.get("streams") or [] if s.get("codec_type") == "audio"), {})
    dur = float((pr.get("format") or {}).get("duration") or 0)
    cols = [colour(out, t) for t in (0.7, 2.2, 3.8)]
    want = [(0, 0, 1), (1, 0, 0), (0, 1, 0)]
    order_ok = all(c and all((v > 80) if w else (v < 40) for v, w in zip(c, ww)) for c, ww in zip(cols, want))
    quiet, loud = loudest(out, 1.6, 2.9), loudest(out, 0.1, 1.4)
    saved = Path(str(res.get("saved") or ""))
    check("the MP4: 1080x1920 for 9:16, the pieces in their order (blue, red, green), as long as the pieces, sound where "
          "it was kept and silence where it was turned off or missing; saved in Edits; the edit remembers it",
          j.get("state") == "done" and (vs.get("width"), vs.get("height")) == (1080, 1920) and abs(dur - 5.2) < 0.25
          and order_ok and au.get("codec_name") == "aac" and "stereo" in run([ff, "-hide_banner", "-i", str(out)]).stderr and quiet is not None and quiet < -60 and loud is not None and loud > -40
          and saved.is_file() and saved.parent.name in ("Edits", "Монтаж") and HE.get(eid)["renders"][-1]["job"] == jid,
          (j.get("state"), res, (vs.get("width"), vs.get("height")), dur, cols, quiet, loud))
    sizes = {}
    for fmt in ("16:9", "1:1", "4:5"):
        HE.save(eid, fmt=fmt, pieces=[dict(e["pieces"][1], mute=False)])
        jj = made_by(HE.new_render(eid))
        s2 = next((s for s in probe(vo._job_dir(jj["id"]) / "edit.mp4").get("streams") or [] if s.get("codec_type") == "video"), {})
        sizes[fmt] = (s2.get("width"), s2.get("height"))
    check("the MP4 in every format: 1920x1080, 1080x1080, 1080x1350", sizes == {"16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}, sizes)
    e2 = HE.new("Empty")
    try:
        HE.new_render(e2)
        empty = "accepted"
    except HE.EditError as exc:
        empty = str(exc)
    gone = HE.new("Gone")
    tmpv = src / "moved.mp4"
    shutil.copy2(red, tmpv)
    HE.add(gone, [str(tmpv)])
    tmpv.unlink()
    try:
        HE.new_render(gone)
        moved = "accepted"
    except HE.EditError as exc:
        moved = str(exc)
    check("an empty edit and a moved video are said before anything is made",
          "at least one video" in empty and "not there any more" in moved and "moved.mp4" in moved, (empty, moved))

    # 3. the pages
    from archivist.web import create_app
    from archivist import downloader as D
    import archivist.i18n as I
    app = create_app()
    H = {"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}", "Sec-Fetch-Site": "same-origin"}
    shutil.copy2(green, D.folder() / "downloaded clip.mp4")
    with app.test_client() as c:
        home = c.get("/edit", headers=H)
        nw = c.post("/edit/new", data={"title": "Из страницы", "format": "1:1"}, headers=H)
        pid = (nw.headers.get("Location") or "").rstrip("/").split("/")[-1]
        pg = c.get(f"/edit/{pid}", headers=H)
        added = c.post(f"/api/edit/{pid}/add", json={"paths": [str(red), str(blue)]}, headers=H).get_json() or {}
        srcs = c.get("/api/edit/sources?kind=downloaded", headers=H).get_json() or {}
        dl = next((x for x in srcs.get("items") or [] if x["name"] == "downloaded clip.mp4"), None)
        added2 = c.post(f"/api/edit/{pid}/add", json=dl["add"] if dl else {}, headers=H).get_json() or {}
        bad_add = c.post(f"/api/edit/{pid}/add", json={"downloaded": "..\\..\\secret.mp4"}, headers=H)
        ks = [p["k"] for p in added2.get("pieces") or []]
        full = c.get(f"/edit/{pid}/media?k={ks[0]}", headers=H) if ks else None
        part = c.get(f"/edit/{pid}/media?k={ks[0]}", headers=dict(H, Range="bytes=100-199")) if ks else None
        stranger_k = c.get(f"/edit/{pid}/media?k=0123456789abcdef", headers=H)
        other_edit = c.get(f"/edit/{eid}/media?k={ks[2]}", headers=H) if len(ks) > 2 else None   # (not in that edit)
        fr = c.get(f"/edit/{pid}/frame?k={ks[0]}&t=1", headers=H) if ks else None
        prox, st = None, {}
        if len(ks) > 1:
            t0 = time.time()
            while time.time() - t0 < 120:
                st = c.post(f"/api/edit/{pid}/proxy", json={"k": ks[1]}, headers=H).get_json() or {}
                if st.get("state") in ("done", "failed"):
                    break
                time.sleep(0.5)
            prox = c.get(f"/edit/{pid}/media?k={ks[1]}&proxy=1", headers=H)
        pieces = added2.get("pieces") or []
        sv = c.post(f"/api/edit/{pid}", json={"title": "Из страницы 2", "format": "9:16",
                                              "pieces": [dict(pieces[2], **{"in": 0.5, "out": 1.5}), pieces[0]] if len(pieces) > 2 else []},
                    headers=H).get_json() or {}
        rr = c.post(f"/api/edit/{pid}/render", headers=H).get_json() or {}
        rj = made_by(rr.get("job") or "") if rr.get("job") else {}
        rl = c.get(f"/api/edit/{pid}/renders", headers=H).get_json() or {}
        mp4 = c.get(f"/edit/render/{rr.get('job')}.mp4", headers=H)
        not_mp4 = c.get(f"/edit/render/{jid}x.mp4", headers=H)
    check("pages: the list, a new edit from the form, the editor with its data; videos added by path and from the "
          "downloads; a name with a folder in it refused",
          home.status_code == 200 and b"New edit" in home.data and nw.status_code == 302 and pg.status_code == 200
          and b"id='heData'" in pg.data and b"Choose videos on this PC" in pg.data and len(added.get("pieces") or []) == 2
          and dl is not None and len(added2.get("pieces") or []) == 3 and bad_add.status_code == 400,
          (home.status_code, nw.status_code, pg.status_code, len(added.get("pieces") or []), dl, bad_add.status_code))
    check("pages: only the edit's own videos are given to the page (by their key; ranges for seeking), a frame picture, "
          "a playable copy of the AVI",
          full is not None and full.status_code == 200 and part.status_code == 206 and len(part.data) == 100
          and stranger_k.status_code == 404 and other_edit.status_code == 404 and fr.status_code == 200
          and fr.mimetype == "image/jpeg" and st.get("state") == "done" and prox.status_code == 200 and len(prox.data) > 1000,
          (full and full.status_code, part and part.status_code, stranger_k.status_code, other_edit and other_edit.status_code,
           fr and fr.status_code, st, prox and prox.status_code))
    check("pages: the page's changes saved (title, format, cut, order), its MP4 made from the page and listed, played",
          sv.get("title") == "Из страницы 2" and sv.get("format") == "9:16" and [round(p["out"] - p["in"], 2) for p in sv.get("pieces") or []][:1] == [1.0]
          and rj.get("state") == "done" and any(x["job"] == rr.get("job") and x["state"] == "done" for x in rl.get("renders") or [])
          and mp4.status_code == 200 and mp4.mimetype == "video/mp4" and not_mp4.status_code == 404,
          (sv.get("title"), sv.get("format"), rj.get("state"), mp4.status_code, not_mp4.status_code))
    I.set_ui_language("ru")
    with app.test_client() as c:
        ru = c.get("/edit", headers=H).get_data(as_text=True) + c.get(f"/edit/{pid}", headers=H).get_data(as_text=True)
    I.set_ui_language("en")
    body = re.sub(r"<(script|style|textarea)[^>]*>.*?</\1>", " ", ru, flags=re.S)
    body = re.sub(r"<[^>]*translate=['\"]no['\"][^>]*>.*?</[a-z0-9]+>", " ", body, flags=re.S)
    txt = re.sub(r"<[^>]+>", "\n", body)
    left = sorted({x.strip() for x in txt.split("\n") if re.search(r"[A-Za-z]{3,}", x) and not re.search(r"[А-Яа-я]", x)
                   and x.strip() not in ("MediaEngine", "Social Lab", "Media Brain", "MP4") and "querySelectorAll" not in x})
    attrs = [x for x in re.findall(r"(?:title|placeholder)='([^']*)'", ru) if re.search(r"[A-Za-z]{3,}", x)
             and not re.search(r"[А-Яа-я]", x) and "\\" not in x and "/" not in x]
    check("pages: in Russian, no English left (also in hints)", "Ручной монтаж" in ru and not left and not attrs, (left[:12], attrs[:6]))

    # 4. in a real browser (Edge on Windows): plays, split, remove, undo, an edge dragged, a piece moved, the MP4
    if a.channel:
        browser_part(app, port, red, green, a.channel)
    rep = {"passed": sum(x["ok"] for x in RESULTS), "total": len(RESULTS), "checks": RESULTS}
    (work / "handedit_check.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps({"passed": rep["passed"], "total": rep["total"]}))
    return 0 if rep["passed"] == rep["total"] else 1


def browser_part(app, port, red, green, channel):
    from archivist import handedit as HE, voice as vo
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False), daemon=True).start()
    time.sleep(1.5)
    eid = HE.new("Browser", "16:9")
    HE.add(eid, [str(red), str(green)])
    errs = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel=channel)
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.on("pageerror", lambda exc: errs.append(str(exc)))
        pg.goto(f"http://127.0.0.1:{port}/edit/{eid}")
        pg.wait_for_selector(".he-p")
        pg.click("#hePlay")
        pg.wait_for_timeout(1500)
        t_played = pg.evaluate("document.getElementById('heV').currentTime")
        pg.click("#hePlay")
        box = pg.query_selector("#heTrack").bounding_box()
        pps = pg.evaluate("parseFloat(document.querySelector('.he-p').style.width)/3")
        pg.mouse.click(box["x"] + 1.5 * pps, box["y"] + 30)
        pg.keyboard.press("s")
        n_split = pg.evaluate("document.querySelectorAll('.he-p').length")
        pg.keyboard.press("Delete")
        n_del = pg.evaluate("document.querySelectorAll('.he-p').length")
        pg.keyboard.press("Control+z")
        n_undo = pg.evaluate("document.querySelectorAll('.he-p').length")
        last = pg.query_selector_all(".he-p")[-1].bounding_box()
        pg.mouse.move(last["x"] + last["width"] - 3, last["y"] + 30)
        pg.mouse.down()
        pg.mouse.move(last["x"] + last["width"] - 3 - pps * 0.5, last["y"] + 30, steps=5)
        pg.mouse.up()
        last = pg.query_selector_all(".he-p")[-1].bounding_box()
        pg.mouse.move(last["x"] + last["width"] / 2, last["y"] + 30)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 5, last["y"] + 30, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(1500)
        kept = HE.get(eid)["pieces"]
        pg.click("#heRender")
        t0 = time.time()
        while time.time() - t0 < 120 and "Ready" not in pg.inner_text("#heRenders"):
            pg.wait_for_timeout(1000)
        rendered = "Ready" in pg.inner_text("#heRenders")
        b.close()
    shape = [(Path(x["src"]).name, round(x["in"], 1), round(x["out"], 1)) for x in kept]
    check("in a real browser: the video plays, split (S), remove (Delete), undo (Ctrl+Z), a piece's end dragged, the last "
          "piece dragged to the start, saved by itself; the MP4 made from the page; no script errors",
          t_played > 0.5 and (n_split, n_del, n_undo) == (3, 2, 3)
          and shape == [("green no sound.mp4", 0.0, 1.5), ("red.mp4", 0.0, 1.5), ("red.mp4", 1.5, 3.0)] and rendered and not errs,
          (t_played, (n_split, n_del, n_undo), shape, rendered, errs[:3]))


if __name__ == "__main__":
    sys.exit(main())
