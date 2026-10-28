"""Cartoon Studio's story writer for real on Windows, through the program's own pages: the Install button (llama.cpp's
release build from GitHub and Qwen3-4B-Instruct-2507 as a Q8_0 GGUF from Hugging Face, pinned, SHA-256 checked),
then stories written by the model on the runner's processor - from a topic in English, from a topic in Romanian,
retold for viewers in Russia - each read back by the program, and the English one made into a cartoon (a preview
without voices) with a picture of every scene. Nothing paid. Results: writer_addon.json, the stories, the film, the
sheet, the server logs.

  python tests/writer_addon_check.py --home <dir> --out <dir>
"""
from __future__ import annotations

import argparse, json, os, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:800]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)


def wait(vo, jid: str, limit: float) -> dict:
    t0 = time.time()
    while vo.read_job(jid)["state"] in ("waiting", "working") and time.time() - t0 < limit:
        time.sleep(2)
    return vo.read_job(jid)


def sheet(film_path: Path, script: dict, out: Path) -> None:
    import cv2, numpy as np
    from archivist.cartoon import film as F
    from archivist.cartoon.draw import Canvas
    film = F.check_script(script)
    tl = F.timeline(film)
    W, H = F.FORMATS[film["format"]]
    w, h = W // 3, H // 3
    tiles = []
    for sc in tl["scenes"]:
        cv = Canvas(w, h, 1920 if W >= H else 1080)
        t = (sc["lines"][-1]["s"] + sc["lines"][-1]["e"]) / 2 if sc["lines"] else sc["e"] - 0.5
        F.draw_frame(cv, film, sc, max(sc["s"] + 0.3, t), {})
        tiles.append(cv.img.copy())
    cols = 4 if W < H else 3
    rows = (len(tiles) + cols - 1) // cols
    grid = np.full((rows * h, cols * w, 3), 255, np.uint8)
    for i, im in enumerate(tiles):
        r, c = divmod(i, cols)
        grid[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
    cv2.imwrite(str(out), grid)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    home, out = Path(a.home).resolve(), Path(a.out).resolve()
    shutil.rmtree(home, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(home)
    os.environ.setdefault("MEDIAENGINE_NO_BROWSER", "1")
    os.environ.setdefault("MEDIAENGINE_UPDATES", "off")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import voice as vo
    from archivist.cartoon import textscript as T, writer as W
    from archivist.web import create_app
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    report = {"llama": dict(W.LLAMA), "model": dict(W.MODEL), "stories": {}}
    with app.test_client() as c:
        t0 = time.time()
        r = c.post("/auto/cartoon/writer/install", headers=H)
        while W.installing() and time.time() - t0 < 3600:
            time.sleep(3)
        s = W.status()
        report["install_s"] = round(time.time() - t0)
        report["manifest"] = W.manifest()
        for name in ("install.log", "selftest.log"):
            if (W.ROOT / name).is_file():
                shutil.copy2(W.ROOT / name, out / f"writer_{name}")
        check("the Install button: llama.cpp and the model downloaded, checked, started for a test",
              r.status_code == 302 and s["installed"] and s["state"] == "done", (s.get("state"), s.get("error"), report["install_s"]))
        if not s["installed"]:
            return finish(out, report)

        asks = [("en_topic", {"about": "Why a city hospital pays three times more for the same medicine", "lang": "en",
                              "secs": "75", "format": "vertical"}),
                ("ro_topic", {"about": "Cum câștigă o firmă de administrare bani pe o renovare a scării blocului care nu s-a făcut niciodată",
                              "lang": "ro", "country": "Moldova", "secs": "75", "format": "vertical"}),
                ("ru_adapt", {"mode": "adapt", "source": T.ROAD_TEXT, "lang": "ru", "country": "Россия", "format": "vertical",
                              "title": "How a City Loses Millions"})]
        made = {}
        for key, form in asks:
            t1 = time.time()
            r = c.post("/auto/cartoon/write", data=form, headers=H)
            jid = (r.headers.get("Location") or "").rstrip("/").split("/")[-1]
            j = wait(vo, jid, 3600) if r.status_code == 302 else {}
            res = j.get("result") or {}
            story = W.story_of(jid) if r.status_code == 302 else ""
            (out / f"story_{key}.txt").write_text(story, "utf-8")
            if r.status_code == 302 and (vo._job_dir(jid) / "server.log").is_file():
                shutil.copy2(vo._job_dir(jid) / "server.log", out / f"server_{key}.log")
            sc = T.parse(story) if story else {"scenes": [], "language": ""}
            info = {"s": round(time.time() - t1), "state": j.get("state"), "result": res, "language": sc.get("language"),
                    "scenes": len(sc["scenes"]), "visuals": [(x.get("visual") or {}).get("kind", "-") for x in sc["scenes"]]}
            report["stories"][key] = info
            made[key] = (jid, sc)
            want_lang = {"en_topic": "en", "ro_topic": "ro", "ru_adapt": "ru"}[key]
            check(f"{key}: a story the program reads (5+ scenes with lines, pictures, the language asked)",
                  j.get("state") == "done" and info["scenes"] >= 5 and sc.get("language") == want_lang
                  and sum(1 for v in info["visuals"] if v != "-") >= 3, info)

        jid, sc = made.get("en_topic", ("", {}))
        if sc and sc.get("scenes"):
            story = W.story_of(jid)
            r = c.post("/auto/cartoon/new", data={"text": story, "format": "vertical", "captions": "1"}, headers=H)
            fid = next((x["id"] for x in vo.list_jobs() if x.get("kind") == "cartoon_make"), "")
            fj = wait(vo, fid, 1800) if fid else {}
            res = fj.get("result") or {}
            if fj.get("state") == "done":
                shutil.copy2(vo._job_dir(fid) / "film.mp4", out / "film_en_topic.mp4")
                try:
                    sheet(out / "film_en_topic.mp4", T.parse(story), out / "sheet_en_topic.png")
                except Exception as exc:
                    report["sheet_error"] = repr(exc)
            report["film"] = res
            check("the English story made into a cartoon (a preview without voices), 40-120 s",
                  r.status_code == 302 and fj.get("state") == "done" and 40 <= float(res.get("seconds") or 0) <= 120,
                  (fj.get("state"), res.get("seconds"), res.get("error")))
    return finish(out, report)


def finish(out: Path, report: dict) -> int:
    rep = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks, **report}
    (out / "writer_addon.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps({"passed": rep["passed"], "total": rep["total"]}))
    return 0 if rep["passed"] == rep["total"] and rep["total"] >= 5 else 1


if __name__ == "__main__":
    sys.exit(main())
