"""The voice-over add-on for real, through the program's own pages: Install (pip + models from the internet, as the
owner's button does - here with CPU torch), a voice-over in the default voice (9_2) listened to word by word, that voice burned
onto a video with captions, captions for the video's own speech; with --talk, "Clips from a long video" for real: a
9-minute public-domain NASA interview (Wikimedia Commons, pinned below) heard by Whisper, clips found, two made
vertical with the face kept and captions. Slow on a CPU (minutes per sentence).

  python tests/voice_addon_check.py --home <empty dir> --video <a short video> --out <dir> [--talk <work dir>]
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18792
TEXT = ("Okay, so here's the thing. Packing light changed every trip we took. "
        "Three outfits, one good hat, and more time in the water.")


# a crew member of the space station answering a TV show's questions (US government work: public domain)
TALK = {"title": "SPACE STATION ASTRONAUT DISCUSSES LIFE IN SPACE WITH ABC'S GOOD MORNING AMERICA (NASA, 2022)",
        "page": "https://commons.wikimedia.org/wiki/File:SPACE_STATION_ASTRONAUT_DISCUSSES_LIFE_IN_SPACE_WITH_ABC%E2%80%99S_GOOD_MORNING_AMERICA_(iss068m263221454-Expedition_68_Inflight_with_ABC%27s_Good_Morning_America_221118_1723170).webm",
        "url": "https://upload.wikimedia.org/wikipedia/commons/transcoded/4/46/SPACE_STATION_ASTRONAUT_DISCUSSES_LIFE_IN_SPACE_WITH_ABC%E2%80%99S_GOOD_MORNING_AMERICA_%28iss068m263221454-Expedition_68_Inflight_with_ABC%27s_Good_Morning_America_221118_1723170%29.webm/SPACE_STATION_ASTRONAUT_DISCUSSES_LIFE_IN_SPACE_WITH_ABC%E2%80%99S_GOOD_MORNING_AMERICA_%28iss068m263221454-Expedition_68_Inflight_with_ABC%27s_Good_Morning_America_221118_1723170%29.webm.480p.vp9.webm",
        "sha256": "812a2ec9e1bc66c7a6a21d23e2c32b665ac20a98e2bb1b377cad8788dcc63fe7"}


def fetch_talk(folder: Path) -> tuple[Path | None, str]:
    import hashlib, urllib.request
    folder.mkdir(parents=True, exist_ok=True)
    dst = folder / "nasa_interview.webm"
    ua = {"User-Agent": "MediaEngine-CI/1.0 (https://github.com/skynder-dev/projects; automated test, small number of requests)"}
    for k in range(3):
        try:
            if not dst.is_file():
                with urllib.request.urlopen(urllib.request.Request(TALK["url"], headers=ua), timeout=600) as r, \
                        open(str(dst) + ".part", "wb") as fh:
                    shutil.copyfileobj(r, fh, 1 << 20)
                os.replace(str(dst) + ".part", dst)
            got = hashlib.sha256(dst.read_bytes()).hexdigest()
            if got == TALK["sha256"]:
                return dst, ""
            dst.unlink()
            return None, f"the file changed on Commons (SHA-256 {got})"
        except Exception as exc:
            err = str(exc)
            time.sleep(10)
    return None, err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True); ap.add_argument("--video", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--cpu", action="store_true", help="CPU torch even with an NVIDIA card")
    ap.add_argument("--talk", default="", help="a work folder: clips from a real NASA interview (downloaded there)")
    a = ap.parse_args()
    try:                     # Cyrillic in a detail must not stop the check (a Windows console is cp1252)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
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
    # the form's own default language ("Detect by itself"): Qwen3-TTS finds the language itself ('Auto')
    r = c.post("/auto/voice/new", data={"text": TEXT, "voice": vo.DEFAULT_VOICE, "language": ""}, headers=H)
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
    timings["russian"] = {k: rres.get(k) for k in ("engine", "said", "word_errors", "words", "chunks", "error")}
    if (Path(rj["dir"]) / "worker.log").is_file():
        shutil.copy2(Path(rj["dir"]) / "worker.log", out / "worker_ru.log")
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
    if a.talk:
        talk_check(c, H, Path(a.talk).resolve(), out, check, timings, wait)
    c.post("/lang", data={"back": "/auto/voice"}, headers=H)
    ru = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page in Russian with a finished voice-over", "Наложить на видео" in ru and "Все слова сказаны" in ru)
    return finish()


def talk_check(c, H, work: Path, out: Path, check, timings: dict, wait) -> None:
    """5. Clips from a long video, for real: the interview heard by Whisper, clips found, the top two made."""
    from archivist import clips as cl, voice as vo
    talk, why = fetch_talk(work)
    check("clips: the NASA interview downloaded (pinned SHA-256)", talk is not None, why)
    if talk is None:
        return
    t0 = time.time()
    r = c.post("/auto/clips/new", data={"path": str(talk), "length": "short", "language": "en"}, headers=H)
    fid = (r.headers.get("Location") or "").rstrip("/").split("/")[-1]
    check("clips: finding starts", r.status_code == 302 and "/auto/clips/" in (r.headers.get("Location") or "") and bool(fid),
          (r.status_code, r.headers.get("Location")))
    if not fid:
        return
    fj = wait(fid, 3 * 3600)
    timings["clips_find_s"] = round(time.time() - t0)
    cands = cl.candidates(fid) if fj["state"] == "done" else []
    heard = " ".join(str(w.get("w", "")) for w in cl.words_of(fid)).lower()
    (out / "clips_found.json").write_text(json.dumps({"video": TALK, "result": fj.get("result"), "candidates": cands,
                                                      "heard_words": len(heard.split())}, indent=1, ensure_ascii=False), "utf-8")
    check("clips: the 9-minute interview heard (space, station)", "space" in heard and "station" in heard,
          (fj.get("result") or {}).get("error") or heard[:300])
    check("clips: at least five clips found, each 15-30 s with its words and why", len(cands) >= 5 and all(
        14.0 <= x["e"] - x["s"] <= 31.0 and x["text"].strip() and x["first"].strip() for x in cands),
          [(x["s"], x["e"], x["first"][:40]) for x in cands[:8]])
    page = c.get(f"/auto/clips/{fid}", headers=H).get_data(as_text=True)
    check("clips: the page lists them with pictures", all(f"/thumb/{x['id']}.jpg" in page for x in cands[:5]))
    if len(cands) < 2:
        return
    top = cands[:2]
    data = {"pick": [x["id"] for x in top], "format": "vertical", "framing": "face", "captions": "1", "title": "1",
            "position": "bottom"}
    for x in top:
        data[f"s_{x['id']}"], data[f"e_{x['id']}"] = f"{x['s']:.2f}", f"{x['e']:.2f}"
    t0 = time.time()
    r = c.post(f"/auto/clips/{fid}/make", data=data, headers=H)
    mk = next((j for j in vo.list_jobs() if j.get("kind") == "clips_make" and j.get("find") == fid), None)
    check("clips: making starts", r.status_code == 302 and mk is not None, r.status_code)
    if mk is None:
        return
    mj = wait(mk["id"], 3600)
    timings["clips_make_s"] = round(time.time() - t0)
    res = mj.get("result") or {}
    made = res.get("clips") or []
    (out / "clips_made.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    check("clips: two vertical clips made from the interview - the person kept in the frame (crop on the face), captions",
          mj["state"] == "done" and len(made) == 2 and all(m["width"] == 1080 and m["height"] == 1920 and m["faces"]
                                                         and m["layouts"] == ["crop"] and m["captions"] > 0 for m in made), res)
    for m in made:
        f = Path(mj["dir"]) / m["file"]
        if f.is_file():
            shutil.copy2(f, out / f"nasa_{m['file']}")


if __name__ == "__main__":
    sys.exit(main())
