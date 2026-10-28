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


# three crew members side by side, answering in turns (each holds the microphone when talking): who speaks, close up
CREW = {"title": "NASA Astronauts Discuss Life In Space With Fox News (iss073m262461622)",
        "page": "https://commons.wikimedia.org/wiki/File:NASA_Astronauts_Discuss_Life_In_Space_With_Fox_News_(iss073m262461622).webm",
        "url": "https://upload.wikimedia.org/wikipedia/commons/transcoded/0/05/NASA_Astronauts_Discuss_Life_In_Space_With_Fox_News_%28iss073m262461622%29.webm/NASA_Astronauts_Discuss_Life_In_Space_With_Fox_News_%28iss073m262461622%29.webm.480p.vp9.webm",
        "sha256": "b6bd93f217199bade8d9fd1a86c519fc9894fab43d6823d7b3583e664404ffe9"}


def fetch_talk(folder: Path, talk: dict | None = None, name: str = "nasa_interview.webm") -> tuple[Path | None, str]:
    import hashlib, urllib.request
    TALK_ = talk or TALK
    folder.mkdir(parents=True, exist_ok=True)
    dst = folder / name
    ua = {"User-Agent": "MediaEngine-CI/1.0 (https://github.com/skynder-dev/projects; automated test, small number of requests)"}
    for k in range(3):
        try:
            if not dst.is_file():
                with urllib.request.urlopen(urllib.request.Request(TALK_["url"], headers=ua), timeout=600) as r, \
                        open(str(dst) + ".part", "wb") as fh:
                    shutil.copyfileobj(r, fh, 1 << 20)
                os.replace(str(dst) + ".part", dst)
            got = hashlib.sha256(dst.read_bytes()).hexdigest()
            if got == TALK_["sha256"]:
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
        crew_check(c, H, Path(a.talk).resolve(), out, check, timings, wait)
    cartoon_voices_check(c, H, out, check, timings, wait)
    cartoon_romanian_check(c, H, out, check, timings, wait)
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
    (out / "clips_words.json").write_text(json.dumps(cl.words_of(fid), ensure_ascii=False), "utf-8")   # (to tune the scoring)
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



def crew_check(c, H, work: Path, out: Path, check, timings: dict, wait) -> None:
    """6. "The one speaking, close up" for real: three crew members side by side answering in turns - found clips made
    with the crop on whoever talks; a sheet of each clip (the original with the chosen one marked, the clip) to look at."""
    import subprocess
    from archivist import clips as cl, voice as vo
    from PIL import Image, ImageDraw
    vid, why = fetch_talk(work, CREW, "nasa_crew.webm")
    check("speaker: the crew video downloaded (pinned SHA-256)", vid is not None, why)
    if vid is None:
        return
    t0 = time.time()
    r = c.post("/auto/clips/new", data={"path": str(vid), "length": "short", "language": "en"}, headers=H)
    fid = (r.headers.get("Location") or "").rstrip("/").split("/")[-1]
    fj = wait(fid, 3 * 3600) if fid else {"state": "failed"}
    cands = cl.candidates(fid) if fj.get("state") == "done" else []
    timings["crew_find_s"] = round(time.time() - t0)
    if len(cands) < 3:
        check("speaker: clips found in the crew video", False, fj.get("result"))
        return
    t0 = time.time()
    r = c.post(f"/auto/clips/{fid}/make", data={"top": "3", "format": "vertical", "framing": "face", "captions": "1",
                                                "position": "bottom", "people": "speaker"}, headers=H)
    mk = next((j for j in vo.list_jobs() if j.get("kind") == "clips_make" and j.get("find") == fid), None)
    mj = wait(mk["id"], 3600) if mk else {"state": "failed"}
    timings["crew_make_s"] = round(time.time() - t0)
    res = mj.get("result") or {}
    made = res.get("clips") or []
    (out / "crew_made.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), "utf-8")
    spk = [m for m in made if any(x.get("speaker") for x in m.get("plan") or [])]
    check("speaker: three clips of the crew made, at least one with the crop on whoever talks", mj.get("state") == "done"
          and len(made) == 3 and spk and mk.get("people") == "speaker", [(m.get("layouts"), m.get("talk")) for m in made])
    ff = vo._ffmpeg()
    rows = []
    for m in made:
        f = Path(mj["dir"]) / m["file"]
        if not f.is_file():
            continue
        shutil.copy2(f, out / f"crew_{m['file']}")
        tiles = []
        for k in range(6):
            t = m["seconds"] * (k + 0.5) / 6
            sp, vp = out / "_s.png", out / "_v.png"
            subprocess.run([ff, "-v", "error", "-y", "-ss", f"{m['s'] + t:.3f}", "-i", str(vid), "-frames:v", "1", str(sp)], check=True)
            subprocess.run([ff, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(f), "-frames:v", "1", str(vp)], check=True)
            im = Image.open(sp).convert("RGB")
            im = im.resize((320, int(round(im.height * 320 / im.width))))
            sh = next((x for x in m["plan"] if x["s"] <= t < x["e"]), m["plan"][-1])
            d = ImageDraw.Draw(im)
            if sh.get("speaker"):
                d.rectangle([sh["cx"] * 320 - 28, 4, sh["cx"] * 320 + 28, im.height - 4], outline=(60, 230, 90), width=3)
            d.text((4, 4), f"{t:.1f} s", fill=(255, 255, 255))
            tiles.append((im, Image.open(vp).convert("RGB").resize((101, 180))))
        rows.append((m, tiles))
        for x in ("_s.png", "_v.png"):
            (out / x).unlink(missing_ok=True)
    if rows:
        sheet = Image.new("RGB", (6 * (320 + 101 + 8), len(rows) * 210 + 10), (18, 20, 26))
        d = ImageDraw.Draw(sheet)
        for r_, (m, tiles) in enumerate(rows):
            y = r_ * 210 + 22
            d.text((6, y - 18), f"{m['file']} from {m['s']:.0f} s: " + ", ".join(
                (f"{x['cx']:.2f}@{x['s']:.1f}" if x.get("speaker") else f"{x['layout']}@{x['s']:.1f}") for x in m["plan"])[:180],
                   fill=(230, 230, 230))
            for k, (im, v) in enumerate(tiles):
                sheet.paste(im, (k * (320 + 101 + 8), y + (180 - im.height) // 2))
                sheet.paste(v, (k * (320 + 101 + 8) + 320, y))
        sheet.save(out / "crew_speaker.png")


def cartoon_voices_check(c, H, out: Path, check, timings: dict, wait) -> None:
    """7. Cartoon Studio with voices: the narrator in the program's own voice, a character in a voice from a
    description (kept with the character for the next episode); the film heard back by Whisper."""
    from archivist import voice as vo
    from archivist.config import HOME
    script = {"title": "Voices test", "language": "en", "format": "vertical", "narrator": "kate",
              "cast": {"kate": {"name": "Kate", "role": "narrator", "female": True, "voice": {"kind": "host"}},
                       "rick": {"name": "Rick", "role": "contractor boss", "female": False,
                                "voice": {"kind": "describe", "text": "A confident, raspy businessman in his forties, low and smooth."}}},
              "scenes": [{"bg": "office", "cast": ["rick"], "visual": {"kind": "contract", "price": "$4 800 000", "price_at": 0,
                                                                      "stamp": "APPROVED", "stamp_at": 1},
                          "lines": [{"who": "kate", "text": "The price is four times higher than the market."},
                                    {"who": "rick", "pose": "count", "emotion": "sly", "text": "And the contract is approved."}]},
                         {"bg": "board", "cast": [], "visual": {"kind": "bars", "values": [1.2, 4.8], "labels": ["fair", "paid"],
                                                                "unit": "M", "at": 0},
                          "lines": [{"who": "kate", "text": "Taxpayers pay the whole difference."}]}]}
    t0 = time.time()
    r = c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(script), "format": "vertical", "voices": "1",
                                          "captions": "1", "style": "pop"}, headers=H)
    jid = next((j["id"] for j in vo.list_jobs() if j.get("kind") == "cartoon_make"), "")
    j = wait(jid, 3 * 3600) if jid else {"state": "failed"}
    timings["cartoon_voices_s"] = round(time.time() - t0)
    res = j.get("result") or {}
    lines = sorted((vo._job_dir(jid) / "voices").glob("line_*.wav")) if jid else []
    kept = (HOME / "cartoon" / "voices" / "rick" / "voice.wav").is_file()
    check("cartoon: a film with voices made (the narrator's own voice, a voice from a description), checked",
          r.status_code == 302 and j.get("state") == "done" and res.get("voices") and len(lines) == 3, (j.get("state"), res))
    check("cartoon: the described voice kept with the character (the same voice in the next episode)", kept)
    if j.get("state") != "done":
        return
    film = vo._job_dir(jid) / "film.mp4"
    shutil.copy2(film, out / "cartoon_voices.mp4")
    c.post("/auto/voice/captions", data={"path": str(film), "language": "en"}, headers=H)
    cj = wait(vo.list_jobs()[0]["id"], 3600)
    heard = str((cj.get("result") or {}).get("said") or "").lower()
    check("cartoon: the film's voices heard back by Whisper (the lines are said)", cj.get("state") == "done"
          and "price" in heard and "approved" in heard and "taxpayers" in heard, heard[:300] or cj.get("result"))



def cartoon_romanian_check(c, H, out: Path, check, timings: dict, wait) -> None:
    """8. A cartoon in Romanian (Cartoon Studio's third language): Qwen3-TTS does not speak it, so the narrator's own
    voice and a described voice are both said by VoxCPM2; heard back by Whisper in Romanian."""
    import unicodedata
    from archivist import voice as vo
    script = {"title": "Voci in romana", "language": "ro", "format": "vertical", "narrator": "ana",
              "cast": {"ana": {"name": "Ana", "role": "narrator", "female": True, "voice": {"kind": "host"}},
                       "radu": {"name": "Radu", "role": "director de firma", "female": False,
                                "voice": {"kind": "describe", "text": "A confident businessman in his forties, low and smooth."}}},
              "scenes": [{"bg": "office", "cast": ["radu"], "visual": {"kind": "contract", "price": "4 800 000 lei", "price_at": 0},
                          "lines": [{"who": "ana", "text": "Prețul este de patru ori mai mare decât pe piață."},
                                    {"who": "radu", "pose": "count", "emotion": "sly", "text": "Și contractul este aprobat."}]},
                         {"bg": "board", "cast": [], "lines": [{"who": "ana", "text": "Contribuabilii plătesc toată diferența."}]}]}
    t0 = time.time()
    r = c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(script), "format": "vertical", "voices": "1",
                                          "captions": "1"}, headers=H)
    jid = next((j["id"] for j in vo.list_jobs() if j.get("kind") == "cartoon_make"), "")
    j = wait(jid, 3 * 3600) if jid else {"state": "failed"}
    timings["cartoon_ro_s"] = round(time.time() - t0)
    check("cartoon in Romanian: made with voices", r.status_code == 302 and j.get("state") == "done", (j.get("state"), j.get("result")))
    if j.get("state") != "done":
        return
    film = vo._job_dir(jid) / "film.mp4"
    shutil.copy2(film, out / "cartoon_voices_ro.mp4")
    c.post("/auto/voice/captions", data={"path": str(film), "language": "ro"}, headers=H)
    cj = wait(vo.list_jobs()[0]["id"], 3600)
    heard = str((cj.get("result") or {}).get("said") or "").lower()
    plain = "".join(ch for ch in unicodedata.normalize("NFD", heard) if unicodedata.category(ch) != "Mn")
    want = ["pretul", "patru", "piata", "contractul", "aprobat", "platesc", "diferenta"]
    got = [w for w in want if w in plain]
    check("cartoon in Romanian: Whisper hears the Romanian words (5 of 7 at least)", len(got) >= 5, (got, heard[:300]))


if __name__ == "__main__":
    sys.exit(main())
