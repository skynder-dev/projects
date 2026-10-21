"""The voice-over add-on for real, through the program's own pages: Install (pip + models from the internet, as the
owner's button does - here with CPU torch), a voice-over in the default voice (9_2) listened to word by word, that voice burned
onto a video with captions, captions for the video's own speech. Slow on a CPU (minutes per sentence).

  python tests/voice_addon_check.py --home <empty dir> --video <a short video> --out <dir>
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18792
TEXT = ("Okay, so here's the thing. Packing light changed every trip we took. "
        "Three outfits, one good hat, and more time in the water.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True); ap.add_argument("--video", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--cpu", action="store_true", help="CPU torch even with an NVIDIA card")
    a = ap.parse_args()
    home, out = Path(a.home).resolve(), Path(a.out).resolve()
    home.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    os.environ.update(ARCHIVIST_HOME=str(home), ARCHIVIST_PORT=str(PORT), MEDIAENGINE_NO_BROWSER="1", MEDIAENGINE_UPDATES="off")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import voice as vo
    from archivist.web import create_app
    app = create_app()
    app.testing = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    c = app.test_client()
    H = {"Host": f"127.0.0.1:{PORT}", "Origin": f"http://127.0.0.1:{PORT}"}
    checks = []
    timings = {}

    def check(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    def finish():
        rep = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks, "timings": timings,
               "manifest": vo.manifest()}
        (out / "voice_addon.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), "utf-8")
        for name in ("install.log", "worker.log"):
            if (vo.ROOT / name).is_file():
                shutil.copy2(vo.ROOT / name, out / name)
        print(json.dumps({"passed": rep["passed"], "total": rep["total"]}))
        return 0 if rep["passed"] == rep["total"] else 1

    # 1. Install, as the button does
    t0 = time.time()
    r = c.post("/auto/voice/install", data={"cpu": "1"} if a.cpu else {}, headers=H)
    check("Install starts", r.status_code == 302, r.status_code)
    last = ""
    while time.time() - t0 < 2 * 3600:
        s = c.get("/api/voice/status", headers=H).get_json()["install"]
        line = f"{s['state']} {s['step']} {s.get('detail') or ''} {s['done'] // 10 ** 6}/{s['total'] // 10 ** 6} MB"
        if line != last:
            print(time.strftime("%H:%M:%S"), line, flush=True); last = line
        if s["state"] in ("done", "failed"):
            break
        time.sleep(5)
    timings["install_s"] = round(time.time() - t0)
    st = vo.status()
    check("the add-on is installed", st["installed"], st.get("error"))
    if not st["installed"]:
        return finish()
    m = vo.manifest()
    check("its manifest: version, Python, torch, models", m.get("version") == vo.ADDON_VERSION and m.get("torch")
          and m.get("models", {}).get("voxcpm", [None, None])[1] == vo.VOXCPM_REV, m)
    check("the new engine (Qwen3-TTS, the owner's pick 14_5) is installed with it", vo.qwen_installed()
          and (m.get("qwen") or {}).get("model", [None, None])[1] == vo.QWEN_REV, m.get("qwen"))
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page shows the forms once installed", "New voice-over" in page and "Captions for a video" in page)

    def wait(jid, limit):
        t1 = time.time()
        last = ""
        while time.time() - t1 < limit:
            j = vo.read_job(jid)
            line = f"{j['state']} {j.get('step') or ''} {int(100 * float(j.get('progress') or 0))}%"
            if line != last:
                print(time.strftime("%H:%M:%S"), jid, line, flush=True); last = line
            if j["state"] in ("done", "failed"):
                return j
            time.sleep(3)
        return vo.read_job(jid)

    # 2. a voice-over in the default voice
    t0 = time.time()
    r = c.post("/auto/voice/new", data={"text": TEXT, "voice": vo.DEFAULT_VOICE, "language": "en"}, headers=H)
    check("a voice-over is accepted", r.status_code == 302, r.status_code)
    jid = vo.list_jobs()[0]["id"]
    j = wait(jid, 3 * 3600)
    timings["voiceover_s"] = round(time.time() - t0)
    res = j.get("result") or {}
    check("the voice-over is made", j["state"] == "done", res.get("error") or res)
    if j["state"] != "done":
        if (Path(j["dir"]) / "worker.log").is_file():
            shutil.copy2(Path(j["dir"]) / "worker.log", out / "worker.log")
        return finish()
    check("every word said (listened to)", int(res.get("word_errors") or 0) <= 1, res.get("said"))
    check("a plausible length", 5 <= float(res.get("seconds") or 0) <= 30, res.get("seconds"))
    check("said by the new engine (Qwen3-TTS) in the voice 9_2", res.get("engine") == "qwen", res.get("engine"))
    d = Path(j["dir"])
    shutil.copy2(d / "voice.wav", out / "voice.wav")
    shutil.copy2(d / "captions.srt", out / "voice.srt")
    timings["voiceover"] = {k: res.get(k) for k in ("device", "seconds", "load_s", "steps", "chunks")}

    # 2b. Russian (the words go through the worker's output in UTF-8 whatever the Windows code page)
    t0 = time.time()
    c.post("/auto/voice/new", data={"text": "Привет! Это короткая проверка голоса.", "voice": vo.DEFAULT_VOICE, "language": "ru",
                                    "speed": "faster", "pauses": "long"}, headers=H)       # with a pace: a bit faster
    rj = wait(vo.list_jobs()[0]["id"], 3 * 3600)
    timings["russian_s"] = round(time.time() - t0)
    rres = rj.get("result") or {}
    said = str(rres.get("said") or "")
    import re as _re
    check("a Russian voice-over in the same voice, heard back in Cyrillic", rj["state"] == "done"
          and len(_re.findall(r"[а-яё]+", said.lower())) >= 3 and int(rres.get("word_errors") or 0) <= 2, rres.get("said") or rres.get("error"))
    if rj["state"] == "done":
        shutil.copy2(Path(rj["dir"]) / "voice.wav", out / "voice_ru.wav")
        from archivist import orders as _od
        raw_s = float(_od._decode_info(Path(rj["dir"]) / "voice_raw.wav", timeout=120).get("seconds") or 0)
        fin_s = float(_od._decode_info(Path(rj["dir"]) / "voice.wav", timeout=120).get("seconds") or 0)
        rw = json.loads((Path(rj["dir"]) / "words.json").read_text("utf-8"))
        check("its pace: a bit faster (8% shorter), the captions within the faster voice",
              raw_s > 0 and abs(fin_s - raw_s / 1.08) < 0.1 and rw and rw[-1]["e"] <= fin_s + 0.05, (raw_s, fin_s, rw[-1:] if rw else None))
        timings["russian_pace"] = {"raw_s": raw_s, "final_s": fin_s}

    # 2c. a voice from a description: still VoxCPM2 (its own packages, not the new engine's)
    t0 = time.time()
    c.post("/auto/voice/new", data={"text": "This voice was made from a description.", "voice": "describe", "language": "en",
                                    "description": "a calm woman in her thirties, warm clear voice"}, headers=H)
    xj = wait(vo.list_jobs()[0]["id"], 3 * 3600)
    timings["described_s"] = round(time.time() - t0)
    xres = xj.get("result") or {}
    check("a voice from a description is still made (VoxCPM2)", xj["state"] == "done" and xres.get("engine") == "voxcpm"
          and int(xres.get("word_errors") or 0) <= 1, xres.get("said") or xres.get("error"))

    # 3. onto a video, with captions
    t0 = time.time()
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": a.video, "keep_sound": "1", "captions": "1", "position": "bottom",
                                               "start": "0.3"}, headers=H)
    dj = wait(vo.list_jobs()[0]["id"], 3600)
    timings["dub_s"] = round(time.time() - t0)
    dres = dj.get("result") or {}
    check("the voice onto the video, captions burned, checked", dj["state"] == "done"
          and all(x["pass"] for x in dres.get("checks", [])), dres)
    if dj["state"] == "done":
        shutil.copy2(Path(dj["dir"]) / "video.mp4", out / "voice_on_video.mp4")

        # 4. captions for that video's own speech (it now speaks): the words come back
        t0 = time.time()
        c.post("/auto/voice/captions", data={"path": str(out / "voice_on_video.mp4"), "language": "en"}, headers=H)
        cj = wait(vo.list_jobs()[0]["id"], 3600)
        timings["captions_s"] = round(time.time() - t0)
        cres = cj.get("result") or {}
        heard = str(cres.get("said") or "").lower()
        check("captions from the video's own speech hear the voice-over", cj["state"] == "done" and "packing" in heard
              and "water" in heard, cres.get("said") or cres.get("error"))
        if cj["state"] == "done":
            shutil.copy2(Path(cj["dir"]) / "video.mp4", out / "captions_video.mp4")
    c.post("/lang", data={"back": "/auto/voice"}, headers=H)
    ru = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page in Russian with a finished voice-over", "Наложить на видео" in ru and "Все слова сказаны" in ru)
    return finish()


if __name__ == "__main__":
    sys.exit(main())
