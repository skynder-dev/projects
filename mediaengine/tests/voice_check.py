"""Voice-over add-on, everything except the models: text pieces, word times, captions (SRT / ASS), the jobs, the
Voice-over page (English and Russian), its files, and the voice burned onto a real video with FFmpeg - with a stand-in
for the add-on's worker (the real VoxCPM2 / Whisper run is mediaengine-voice-addon.yml).

  python tests/voice_check.py --home <empty dir> [--out report.json]
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18791


def install_flows(home: Path, check) -> None:
    """The add-on's install with pip, Hugging Face and the worker stood in (another folder): the main part whole and
    recorded first, the new engine (Qwen3-TTS) on its own - its failure keeps a working add-on; an installed add-on
    gets only the engine; nothing is downloaded twice."""
    import contextlib, hashlib
    from archivist import voice as vo, auto_edit as ae, platform_adapter as pa
    names = ("ROOT", "SITE", "SITE_QWEN", "MODELS", "MANIFEST", "_pip", "_hf_files", "_run_worker", "_free", "_nvidia_name")
    saved = {k: getattr(vo, k) for k in names}
    saved_fetch, saved_awake, saved_install = ae._fetch_resumable, pa.keep_awake, dict(vo.INSTALL)
    root = home / "addon-flows"
    vo.ROOT, vo.SITE, vo.SITE_QWEN, vo.MODELS, vo.MANIFEST = (root, root / "site", root / "site_qwen", root / "models",
                                                              root / "addon.json")
    log, fail = [], set()
    files = {"voxcpm": [("model.safetensors", 10), ("config.json", 3)], "whisper": [("model.bin", 5)],
             "qwen3tts": [("model.safetensors", 7), ("speech_tokenizer/config.json", 2)]}
    key_of = {vo.VOXCPM_REPO: "voxcpm", vo.WHISPER_REPO: "whisper", vo.QWEN_REPO: "qwen3tts"}

    def data(key, name, size):
        return (key + name).encode()[:size].ljust(size, b"x")

    def pip(site_dir, cpu, logp, packages=None):
        part = "qwen" if packages else "main"
        log.append(("pip", part, cpu))
        if "pip_" + part in fail:
            raise vo.VoiceError("pip failed (test)")
        site_dir.mkdir(parents=True, exist_ok=True)

    def hf(repo, rev):
        k = key_of[repo]
        return [(n, sz, "sha256", hashlib.sha256(data(k, n, sz)).hexdigest()) for n, sz in files[k]]

    def fetch(url, part, size, progress, stop=None, tries=4):
        k = next(v for r, v in key_of.items() if r in url)
        name = url.split("/resolve/")[1].split("/", 1)[1]
        log.append(("fetch", k))
        if "fetch_" + k in fail:
            raise ConnectionError("the internet went away (test)")
        part.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(data(k, name, size))

    def worker(job, work, timeout=3600, on_line=None, track=True):
        eng = job.get("engine") or "main"
        log.append(("selftest", eng))
        if "selftest_" + eng in fail:
            return {"ok": False, "error": "ImportError: test"}
        return {"ok": True, "torch": "2.8.0", "qwen_tts": "0.1.1"} if eng == "qwen" else \
            {"ok": True, "torch": "2.8.0+cu126", "cuda": True, "gpu": "RTX 3060", "vram_gb": 12}

    def run(cpu=False):
        log.clear()
        vo.INSTALL.update(state="running", error="", step="checking", total=0, done=0)
        vo._STOP.clear()
        vo._install_now(cpu)
        return vo.INSTALL["state"]

    vo._pip, vo._hf_files, vo._run_worker, vo._free, vo._nvidia_name = pip, hf, worker, (lambda p: 100 * 10 ** 9), (lambda: "")
    ae._fetch_resumable, pa.keep_awake = fetch, contextlib.nullcontext
    try:
        st = run()
        m = vo.manifest()
        check("install: a fresh install - both parts, recorded, the engine's packages never from the CUDA index",
              st == "done" and vo.installed() and vo.qwen_installed() and m.get("bytes", 0) > 0
              and ("pip", "qwen", True) in log and (vo.SITE_QWEN / "sox" / "__init__.py").is_file(), (st, log, m))
        vo.remove_addon()
        fail.add("pip_qwen")
        st = run()
        check("install: the new engine fails on a fresh install - the main part works (recorded with its size)",
              st == "failed" and vo.installed() and not vo.qwen_installed() and vo.manifest().get("bytes", 0) > 0,
              (st, vo.INSTALL.get("error"), vo.manifest()))
        fail.clear()
        st = run()
        check("install: then only the new engine (the main part kept, no model downloaded twice)",
              st == "done" and vo.qwen_installed() and ("pip", "main", False) not in log
              and [x for x in log if x[0] == "fetch"] == [("fetch", "qwen3tts")] * 2, log)
        m = vo.manifest()
        m.pop("qwen")                            # an add-on from before the pick: no engine, no model yet
        vo._write_manifest(m)
        import shutil as _sh
        _sh.rmtree(vo.SITE_QWEN, ignore_errors=True)
        _sh.rmtree(vo.MODELS / "qwen3tts", ignore_errors=True)
        fail.add("fetch_qwen3tts")
        st = run()
        check("install: the internet gone while the engine downloads - the add-on still works",
              st == "failed" and vo.installed() and not vo.qwen_installed() and "internet" in vo.INSTALL.get("error", ""),
              (st, vo.INSTALL.get("error")))
        fail.clear()
        vo.remove_addon()
        fail.add("selftest_qwen")
        st = run()
        check("install: the engine does not start - the main part kept, said in words", st == "failed" and vo.installed()
              and "new voice engine" in vo.INSTALL.get("error", "") and vo.manifest().get("bytes", 0) > 0,
              vo.INSTALL.get("error"))
        fail.clear()
        vo.remove_addon()
        check("install: Remove takes both parts away", not vo.installed() and not vo.SITE_QWEN.exists()
              and not vo.MODELS.exists())
    finally:
        for k, v in saved.items():
            setattr(vo, k, v)
        ae._fetch_resumable, pa.keep_awake = saved_fetch, saved_awake
        vo.INSTALL.clear()
        vo.INSTALL.update(saved_install)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True); ap.add_argument("--out", default="")
    a = ap.parse_args()
    home = Path(a.home).resolve()
    home.mkdir(parents=True, exist_ok=True)
    os.environ.update(ARCHIVIST_HOME=str(home), ARCHIVIST_PORT=str(PORT), MEDIAENGINE_NO_BROWSER="1", MEDIAENGINE_UPDATES="off")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import voice as vo
    from archivist.media import _ffmpeg_exe
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:400]})
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)

    # 1. text into pieces the model says well
    long_sentence = "This is a sentence that goes on and on, with commas, " * 8 + "and ends here."
    text = "Okay... so here's something nobody tells you. You don't need ten outfits! Really?\n\nA new paragraph. " + long_sentence
    cs = vo.chunks(text)
    check("pieces of at most ~220 characters", cs and all(len(c["text"]) <= 225 for c in cs), [len(c["text"]) for c in cs])
    check("no word lost or doubled in the pieces", re.findall(r"\S+", " ".join(c["text"] for c in cs)) == re.findall(r"\S+", text))
    check("a longer pause after a paragraph", cs[0]["pause_after"] == 0.6, cs[0])
    check("empty text: no pieces", vo.chunks("  \n ") == [])
    check("a sentence that ends in 'no.' ends there", vo._sentences("Just say no. Then we go.") == ["Just say no.", "Then we go."],
          vo._sentences("Just say no. Then we go."))
    check("sentences are not cut after Mr. / e.g. / p.m. / an initial",
          vo._sentences("Mr. Smith came at 5 p.m. today. We met J. R. Smith. See e.g. the photos! Done.")
          == ["Mr. Smith came at 5 p.m. today.", "We met J. R. Smith.", "See e.g. the photos!", "Done."],
          vo._sentences("Mr. Smith came at 5 p.m. today. We met J. R. Smith. See e.g. the photos! Done."))
    sys.path.insert(0, str(ROOT / "app" / "archivist"))
    import voice_worker as vw
    same = [("almost twenty percent cheaper", "Almost 20% cheaper."), ("Write an e-mail at 5 p.m.", "Write an email at five PM."),
            ("Tip #3: okay?", "Tip number three. OK?"), ("It costs 1,000 dollars", "It costs one thousand dollars."),
            ("twenty-five minutes", "25 minutes"), ("two hundred and five", "205"), ("1, 2, 3, go", "one, two, three, go"),
            ("5 and 6", "five and six"), ("the 1st day", "the first day"), ("first-class", "first class"),
            ("well-known", "well known"), ("COVID-19", "COVID 19"), ("at 10:30", "at 10.30"), ("version 2.0", "version 2 0"),
            ("one of the best", "one of the best"), ("no one", "no one")]
    check("the word check: the same words written another way are not errors (20% / twenty percent, e-mail / email ...)",
          all(vw.word_errors(r_, s_) == 0 for r_, s_ in same), [(r_, vw.word_errors(r_, s_)) for r_, s_ in same])
    check("the word check: a missing or wrong word still counts", vw.word_errors("hello world", "hello") == 1
          and vw.word_errors("twenty five", "thirty five") == 1)

    # 2. word times: the script's words as written, times from what was heard
    heard = [{"w": w, "s": s, "e": e} for w, s, e in [("Okay", .1, .4), ("so", .5, .6), ("heres", .6, .9), ("something", .9, 1.3),
             ("nobody", 1.3, 1.7), ("tells", 1.7, 1.9), ("you.", 1.9, 2.1), ("You", 2.4, 2.5), ("don't", 2.5, 2.7),
             ("need", 2.7, 2.9), ("10", 2.9, 3.2), ("outfits!", 3.2, 3.7)]]
    words = vo.align("Okay... so here's something nobody tells you. You don't need ten outfits! Really?", heard)
    check("script words kept as written ('here's', 'ten')", [w["w"] for w in words][2] == "here's" and words[10]["w"] == "ten",
          [w["w"] for w in words])
    check("a word not heard gets a time after its neighbour", words[-1]["w"] == "Really?" and words[-1]["s"] >= 3.7, words[-1])
    check("times never go backwards", all(words[i]["s"] <= words[i + 1]["s"] for i in range(len(words) - 1)))
    check("without a script: what was heard", [w["w"] for w in vo.align("", heard)] == [h["w"] for h in heard])
    cues = vo.cues(words)
    check("captions of at most 4 words, a phrase ends at punctuation", all(len(c["words"]) <= 4 for c in cues)
          and cues[0]["words"][-1]["w"] == "Okay...", [[w["w"] for w in c["words"]] for c in cues])
    check("captions never overlap", all(cues[i]["e"] <= cues[i + 1]["s"] for i in range(len(cues) - 1)))
    s = vo.srt(cues, offset=0.3)
    check("SRT numbered with times (offset added)", s.startswith("1\n00:00:00,400 --> ") and "\n\n2\n" in s, s[:120])
    sa = vo.ass(cues, 1080, 1920, style="classic")
    check("ASS: the frame size, karaoke words (classic)", "PlayResX: 1080" in sa and "PlayResY: 1920" in sa and "{\\k" in sa)
    sp = vo.ass(cues, 1080, 1920)
    check("ASS: the default style shows each word in color in turn, with the program's font",
          sp.count("Dialogue:") >= len([w for c in cues for w in c["words"]]) and "\\fnMontserrat Black" in sp
          and "{\\k" not in sp, sp[-300:])
    from archivist import textfx as tf0
    one = vo.style_cues([{"w": w, "s": i * 0.4, "e": i * 0.4 + 0.35} for i, w in enumerate("one two three four".split())],
                        tf0.options(style="single"))
    sd = tf0.document(1080, 1920, one, [], tf0.options(style="single"), 0.0)
    dl = [x for x in sd.splitlines() if x.startswith("Dialogue:")]
    shown_ = [re.sub(r"\{[^}]*\}", "", x.split(",", 9)[9]).split() for x in dl]
    check("look 'one word at a time': one word per caption, held until the next word", len(one) == 4 and len(dl) == 4
          and all(len(x) == 1 for x in shown_) and dl[0].split(",")[2] == "0:00:00.39", (shown_, dl[:1]))
    multi = tf0.document(1080, 1920, [{"s": 0.0, "e": 1.2, "words": [{"w": w, "s": i * 0.4, "e": i * 0.4 + 0.35}
                                                                     for i, w in enumerate("made in pop".split())]}],
                         [], tf0.options(style="single"), 0.0)
    md_ = [re.sub(r"\{[^}]*\}", "", x.split(",", 9)[9]) for x in multi.splitlines() if x.startswith("Dialogue:")]
    check("look 'one word at a time' on a caption of several words (edited, or made in another look): in turn",
          md_ == ["MADE", "IN", "POP"], md_)
    bd = tf0.document(1080, 1920, vo.style_cues([{"w": w, "s": i * 0.4, "e": i * 0.4 + 0.35} for i, w in
                                                 enumerate("one two three".split())], tf0.options(style="block", color="green")),
                      [], tf0.options(style="block", color="green"), 0.0)
    blocks = [x for x in bd.splitlines() if "\\p1" in x]
    check("look 'word on a color block': a block of the color behind each word as it is said, the word dark on it",
          len(blocks) == 3 and all(tf0.tag_color(tf0.COLORS["green"][1]) in x for x in blocks) and bd.count("\\1c&H101010&") == 3,
          (len(blocks), bd.count("\\1c&H101010&")))
    check("ASS: a brace in the text cannot become a tag", "{x}" not in vo.ass(vo.cues([{"w": "{x}", "s": 0, "e": 1}]), 640, 360))

    # 3. the page and the jobs, with a stand-in worker
    vo.why_not_install = lambda: ""                      # (this test runs on any Python; the add-on needs 3.11)
    from archivist.web import create_app
    app = create_app()
    app.testing = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    c = app.test_client()
    H = {"Host": f"127.0.0.1:{PORT}", "Origin": f"http://127.0.0.1:{PORT}"}
    r = c.get("/auto/voice", headers=H)
    check("page without the add-on: install card", r.status_code == 200 and "Install the voice add-on" in r.get_data(as_text=True))
    r = c.post("/auto/voice/new", data={"text": "Hello there.", "voice": vo.DEFAULT_VOICE}, headers=H)
    check("a voice-over before installing: refused in words", r.status_code == 400 and "Install the voice add-on first" in r.get_data(as_text=True))
    check("the home of Auto Edit links the page only when it is released", ("/auto/voice" in c.get("/auto", headers=H).get_data(as_text=True))
          == vo.SHOW_ON_HOME)
    check("the recordings of the ready voices ship with the program", all((vo.ASSETS / v["ref"]).is_file()
          for v in vo.VOICES.values() if v.get("ref")), vo.ASSETS)

    ff = _ffmpeg_exe()
    (vo.SITE).mkdir(parents=True, exist_ok=True)
    (vo.MODELS / "voxcpm").mkdir(parents=True, exist_ok=True)
    (vo.MODELS / "whisper").mkdir(parents=True, exist_ok=True)
    vo.MANIFEST.write_text(json.dumps({"version": vo.ADDON_VERSION, "python": f"{sys.version_info[0]}.{sys.version_info[1]}",
                                       "cuda": False, "bytes": 123}), "utf-8")
    check("a stand-in add-on counts as installed", vo.installed())

    sent = []                    # what the program asked the worker for (the last one at the end)

    fail_tts = [False]           # a voice-over that fails (to see what waits for it)

    def fake_worker(job, work, timeout=3600, on_line=None, track=True):
        sent.append(job)
        work.mkdir(parents=True, exist_ok=True)
        if job["task"] == "tts" and fail_tts[0]:
            return {"ok": False, "error": "RuntimeError: the graphics card ran out of memory (test)"}
        if on_line:
            on_line({"progress": 0.5, "step": "speaking", "chunk": 1, "chunks": 1})
        if job["task"] == "tts":
            ref = (job.get("voice") or {}).get("ref_wav")
            if ref and not Path(ref).is_file():         # as the real worker: it cannot clone a voice from no recording
                return {"ok": False, "error": f"FileNotFoundError: {ref}"}
            n = sum(len(ch["text"].split()) for ch in job["chunks"])
            secs = max(1.0, 0.35 * n)
            subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f=220:d={secs:.2f}", "-ar", "48000", job["out_wav"]],
                           check=True)
            toks = " ".join(ch["text"] for ch in job["chunks"]).split()
            heard = [{"w": t, "s": round(i * 0.35, 3), "e": round(i * 0.35 + 0.3, 3)} for i, t in enumerate(toks)]
            return {"ok": True, "device": "cpu", "seconds": secs, "words": heard, "said": " ".join(toks), "word_errors": 0,
                    "chunks": [], "steps": 10}
        if job["task"] == "transcribe":
            return {"ok": True, "said": "hello world from the video", "language": "en",
                    "words": [{"w": w, "s": 0.2 + i * 0.4, "e": 0.5 + i * 0.4} for i, w in enumerate("hello world from the video".split())]}
        return {"ok": True}

    vo._run_worker = fake_worker

    def wait(jid, limit=300):
        end = time.time() + limit
        while time.time() < end:
            j = vo.read_job(jid)
            if j["state"] in ("done", "failed"):
                return j
            time.sleep(0.3)
        return vo.read_job(jid)

    n_before = len(vo.list_jobs())
    r = c.post("/auto/voice/new", data={"text": "Привет, это просто проверка.", "voice": vo.DEFAULT_VOICE, "language": "en"}, headers=H)
    check("Russian letters with English chosen: refused in words (not a voice-over of nonsense)", r.status_code == 400
          and "other letters than the chosen language" in r.get_data(as_text=True) and len(vo.list_jobs()) == n_before,
          r.status_code)
    r = c.post("/auto/voice/new", data={"text": "Okay, so here's something. You don't need ten outfits!", "voice": vo.DEFAULT_VOICE,
                                        "language": "en"}, headers=H)
    check("a voice-over is accepted", r.status_code == 302, r.status_code)
    jid = vo.list_jobs()[0]["id"]
    j = wait(jid)
    res = j.get("result") or {}
    d = Path(j["dir"])
    check("the voice-over is made", j["state"] == "done", res)
    check("its WAV, words and captions are there", (d / "voice.wav").is_file() and (d / "captions.srt").is_file()
          and (d / "words.json").is_file())
    job = json.loads((d / "job.json").read_text("utf-8"))
    check("the default voice is used with its own words", job["voice"].get("ref_text") == vo.HOST_REF_TEXT
          and job["voice"].get("key") == vo.DEFAULT_VOICE)
    check("the ready voice goes with its own setting (cfg 1.6)", job["voice"].get("cfg") == 1.6, job["voice"])
    check("loudness finishing only (no 'microphone' option)", "mic" not in job and "name='mic'" not in
          c.get("/auto/voice", headers=H).get_data(as_text=True), job.get("mic"))
    r = c.get(f"/auto/voice/{jid}/file/voice.wav", headers={**H, "Range": "bytes=0-99"})
    check("the player gets the sound in pieces (Range)", r.status_code == 206 and len(r.data) == 100, r.status_code)
    r = c.get(f"/auto/voice/{jid}/file/captions.srt?download=1", headers=H)
    check("captions download with a readable name", r.status_code == 200 and "attachment" in r.headers.get("Content-Disposition", ""),
          r.headers.get("Content-Disposition"))
    check("only the job's own files are served", c.get(f"/auto/voice/{jid}/file/job.json", headers=H).status_code == 404
          and c.get("/auto/voice/..%2F..%2Fx/file/voice.wav", headers=H).status_code == 404)
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page lists it with a player and 'Put it on a video'", f"/auto/voice/{jid}/file/voice.wav" in page and "Put it on a video" in page)
    check("normal pace by default (no speed change, the pieces' own pauses)", job.get("speed") == 1.0 and job.get("pauses") == 1.0
          and "name='speed'" in page and "<option value='normal' selected>normal speed" in page, (job.get("speed"), job.get("pauses")))

    # the pace: a bit faster with long pauses - the voice keeps its pitch, the captions follow the faster voice
    r = c.post("/auto/voice/new", data={"text": "First sentence here. Second one comes next. And a third one.",
                                        "voice": vo.DEFAULT_VOICE, "language": "en", "speed": "faster", "pauses": "long"}, headers=H)
    pj = wait(vo.list_jobs()[0]["id"])
    pd = Path(pj["dir"])
    pjob = json.loads((pd / "job.json").read_text("utf-8"))
    tts_job = [x for x in sent if x["task"] == "tts"][-1]
    plain = vo.chunks("First sentence here. Second one comes next. And a third one.")
    check("pace: a bit faster with long pauses kept with the job", pj["state"] == "done" and pjob.get("speed") == 1.08
          and pjob.get("pauses") == 1.6, (pj["state"], pjob.get("speed"), pjob.get("pauses")))
    check("pace: the pauses between the pieces are longer", [x["pause_after"] for x in tts_job["chunks"]]
          == [round(x["pause_after"] * 1.6, 3) for x in plain], [x["pause_after"] for x in tts_job["chunks"]])
    from archivist import orders as _od
    raw_s = float(_od._decode_info(pd / "voice_raw.wav", timeout=60).get("seconds") or 0)
    fin_s = float(_od._decode_info(pd / "voice.wav", timeout=60).get("seconds") or 0)
    check("pace: the voice is 8% shorter (faster, by time-stretch)", raw_s > 0 and abs(fin_s - raw_s / 1.08) < 0.08, (raw_s, fin_s))
    pw = json.loads((pd / "words.json").read_text("utf-8"))
    check("pace: the captions' times follow the faster voice", pw and abs(pw[-1]["e"] - (0.35 * (len(pw) - 1) + 0.3) / 1.08) < 0.01,
          pw[-1] if pw else None)
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("pace: the next form starts with the pace used last", "<option value='faster' selected>" in page
          and "<option value='long' selected>" in page)
    check("pace: the list says it (normal is not said)", " · <span>a bit faster</span> · <span>long pauses</span>" in page
          and page.count("<span>normal speed</span>") == 0)
    check("pace: anything unknown is the normal pace", vo.pace("x' onload", "") == ("normal", "normal"))

    # the engine the owner picked (14_5, Qwen3-TTS) for voices from a recording; VoxCPM2 for a description
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("an add-on from before the pick offers the new engine (once, a button)", "id='voEngine'" in page
          and "Download the new voice engine" in page and not vo.qwen_installed())
    tts_jobs = lambda: [x for x in sent if x["task"] == "tts"]
    check("without it, the voice 9_2 is said as before (VoxCPM2)", tts_jobs()[-1].get("engine") == "voxcpm")
    started = []
    real_install = vo._install
    vo._install = lambda cpu: (started.append(cpu), vo.INSTALL.update(state="done"))
    try:
        vo.start_install()
        time.sleep(0.3)
        check("the button installs only what is missing (the add-on is there)", started == [False], started)
        man = json.loads(vo.MANIFEST.read_text("utf-8"))
        man["qwen"] = {"version": vo.QWEN_VERSION, "packages": vo.QWEN_PACKAGES, "model": [vo.QWEN_REPO, vo.QWEN_REV]}
        vo.MANIFEST.write_text(json.dumps(man), "utf-8")
        vo.SITE_QWEN.mkdir(parents=True, exist_ok=True)
        (vo.MODELS / "qwen3tts").mkdir(parents=True, exist_ok=True)
        refused = ""
        try:
            vo.start_install()
        except vo.VoiceError as exc:
            refused = str(exc)
        check("with both there: 'already installed'", "already installed" in refused, refused)
    finally:
        vo._install = real_install
        vo.INSTALL.update(state="idle")
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("with the new engine: no offer, the page says which voice goes where", "id='voEngine'" not in page
          and "Voices from a recording (9_2 too): Qwen3-TTS" in page and vo.qwen_installed())
    for text, voice, lang, want, qlang in (("Hello from the new engine.", vo.DEFAULT_VOICE, "en", "qwen", "English"),
                                           ("Привет от нового движка.", vo.DEFAULT_VOICE, "ru", "qwen", "Russian"),
                                           ("Detect it by itself.", vo.DEFAULT_VOICE, "", "qwen", None),
                                           ("Привіт, як справи?", vo.DEFAULT_VOICE, "uk", "voxcpm", None),
                                           ("Привіт, як справи? Їжак.", vo.DEFAULT_VOICE, "", "voxcpm", None),
                                           ("Dzień dobry, jak się masz?", vo.DEFAULT_VOICE, "", "voxcpm", None),
                                           ("Ça va très bien, merci.", vo.DEFAULT_VOICE, "", "qwen", None)):
        c.post("/auto/voice/new", data={"text": text, "voice": voice, "language": lang}, headers=H)
        wj = wait(vo.list_jobs()[0]["id"])
        tj = tts_jobs()[-1]
        check(f"engine: the voice 9_2 in '{lang or 'auto'}' -> {want}", wj["state"] == "done" and tj.get("engine") == want
              and tj.get("qwen_language") == qlang and (wj.get("result") or {}).get("engine") == want,
              (tj.get("engine"), tj.get("qwen_language"), (wj.get("result") or {}).get("engine")))
    by_text = {" ".join(ch["text"] for ch in x["chunks"]): x.get("qwen_icl") for x in tts_jobs() if x.get("engine") == "qwen"}
    check("engine: 9_2 continues its English recording in English, takes only its timbre in Russian (round 15)",
          by_text.get("Hello from the new engine.") is True and by_text.get("Привет от нового движка.") is False
          and by_text.get("Ça va très bien, merci.") is True, by_text)
    check("engine: a voice recorded in Russian continues its recording in Russian",
          vo.qwen_icl("Привет, это я.", "Это моя запись голоса.") and not vo.qwen_icl("Hello there.", "Это запись.")
          and not vo.qwen_icl("Привет.", ""))
    c.post("/auto/voice/new", data={"text": "A described voice says this.", "voice": "describe", "language": "en",
                                    "description": "a calm man in his forties, deep warm voice"}, headers=H)
    wait(vo.list_jobs()[0]["id"])
    check("engine: a voice from a description stays on VoxCPM2", tts_jobs()[-1].get("engine") == "voxcpm"
          and tts_jobs()[-1]["voice"].get("description"))
    vo.INSTALL.update(state="running")          # the new engine being downloaded beside an installed add-on
    try:
        last_vo = vo.list_jobs()[0]["id"]
        keep_res = (vo._job_dir(last_vo) / "result.json").read_bytes()
        (vo._job_dir(last_vo) / "result.json").write_text(json.dumps({"ok": False, "error": "x"}), "utf-8")
        refused = ""
        try:
            vo.retry_job(last_vo)
        except vo.VoiceError as exc:
            refused = str(exc)
        check("Try again waits while the add-on is being installed (the new engine too)", "being installed" in refused
              and vo.read_job(last_vo)["state"] == "failed" and last_vo not in vo._QUEUE, refused)
        (vo._job_dir(last_vo) / "result.json").write_bytes(keep_res)
    finally:
        vo.INSTALL.update(state="idle")

    # a real video (vertical, with sound) and the voice burned onto it
    video = home / "clip.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=540x960:rate=30:duration=2",
                    "-f", "lavfi", "-i", "sine=f=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(video)], check=True)
    import hashlib as _hl0
    video_sha = _hl0.sha256(video.read_bytes()).hexdigest()
    from archivist.db import db, now_iso
    from archivist import auto_edit as ae
    ae.ensure_schema()
    with db() as con:              # a saved reel: offered in the video fields without typing its path
        con.execute("INSERT INTO ae_exports(project_id, revision_id, path, sha256, bytes, created_at) VALUES(1,1,?,?,?,?)",
                    (str(video), "x", 1, now_iso()))
        con.commit()
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("a reel saved lately is offered in the video fields", "select data-fill" in page and "clip.mp4" in page)
    r = c.post("/api/text/preview", data={"voice_from": jid, "video": str(video), "captions": "1", "start": "0.3",
                                          "hook": "Привет", "at": "0.5"}, headers=H)
    check("a preview before the voice is put on the video", bool((r.get_json() or {}).get("url")), r.get_json())
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(video), "keep_sound": "1", "captions": "1", "position": "bottom",
                                               "start": "0.3"}, headers=H)
    check("the voice onto a video is accepted", r.status_code == 302, r.status_code)
    dj = wait(vo.list_jobs()[0]["id"])
    dres = dj.get("result") or {}
    check("the video with the voice is made and checked", dj["state"] == "done" and all(x["pass"] for x in dres.get("checks", [])), dres)
    check("it lasts as long as the voice (the video's last picture held)", dres.get("seconds", 0) >= 0.3 + json.loads(
        (d / "result.json").read_text("utf-8"))["seconds"], dres.get("seconds"))
    check("captions were burned (ASS written)", (Path(dj["dir"]) / "captions.ass").is_file() and dres.get("captions", 0) > 0)

    def frame(path, t):        # the picture at t, small and grey (raw bytes)
        cp = subprocess.run([ff, "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf",
                             "scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True)
        return cp.stdout
    first = json.loads((Path(dj["dir"]) / "job.json").read_text("utf-8"))
    cw = json.loads((d / "words.json").read_text("utf-8"))
    t_cap = 0.3 + (cw[2]["s"] + cw[2]["e"]) / 2        # the second caption ("so here's something.")
    a_, b_ = frame(video, t_cap), frame(Path(dj["dir"]) / "video.mp4", t_cap)
    low = slice(108 * 128, 108 * 162)          # the band of the bottom captions (they sit 20% above the bottom)
    changed = sum(1 for x, y in zip(a_[low], b_[low]) if abs(x - y) > 50) / max(1, len(a_[low])) if a_ and b_ else 0
    check("the captions can be seen in the picture (not only written)", changed > 0.02,            # ~5% with captions, ~0% without (glyphs over a busy test picture)
          f"{100 * changed:.1f}% of the caption band changed ({first.get('position')})")
    check("the original video was only read", video.is_file() and video.stat().st_size > 0)
    check("a copy is saved next to the reels ('<name> - voice.mp4')", dres.get("saved", "").endswith("clip - voice.mp4")
          and Path(dres["saved"]).is_file(), dres.get("saved"))
    check("that copy takes no second place on the same disk (one file, two names)",
          os.stat(dres["saved"]).st_nlink >= 2 if dres.get("saved") else False, dres.get("saved"))

    # the sound of the new video: AAC at 48 kHz (not the 192 kHz of the loudness filter)
    head = subprocess.run([ff, "-hide_banner", "-i", str(Path(dj["dir"]) / "video.mp4")], capture_output=True, text=True).stderr
    rates = re.findall(r"Audio: (\w+).*?(\d+) Hz", head)
    check("its sound is AAC at 48 kHz", rates == [("aac", "48000")], rates)

    # a video with an odd width and height (H.264 needs even ones), a start time written with a comma
    odd = home / "odd size.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=539x959:rate=25:duration=1", "-c:v", "libx264",
                    "-pix_fmt", "yuv444p", str(odd)], check=True)
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(odd), "captions": "1", "start": "0,5"}, headers=H)
    oj = wait(vo.list_jobs()[0]["id"])
    ores = oj.get("result") or {}
    ojob = json.loads((Path(oj["dir"]) / "job.json").read_text("utf-8"))
    check("an odd-sized video without sound gets the voice (made even)", oj["state"] == "done" and ores.get("width") == 538
          and ores.get("height") == 958, ores)
    check("'0,5' is half a second", abs(float(ojob.get("start_s") or 0) - 0.5) < 1e-9, ojob.get("start_s"))
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(odd), "start": "soon"}, headers=H)
    check("a start time that is not a number: refused in words", r.status_code == 400, r.status_code)

    # an HDR phone video (HLG): normal colours in the new video (BT.709), as the converter and the reels make them
    hlg = home / "hdr phone.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=1", "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
                    str(hlg)], check=True)
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(hlg), "captions": "1"}, headers=H)
    hj = wait(vo.list_jobs()[0]["id"])
    hv = Path(hj["dir"]) / "video.mp4"
    head_ = subprocess.run([ff, "-hide_banner", "-i", str(hv)], capture_output=True, text=True).stderr if hv.is_file() else ""
    tags = next((x for x in head_.splitlines() if "Video:" in x), "")   # (no ffprobe in the program: FFmpeg's own text)
    check("an HDR (HLG) phone video gets normal colours (BT.709)", hj["state"] == "done" and "bt709" in tags
          and "arib" not in tags and "bt2020" not in tags and "yuv420p" in tags, (hj.get("result"), tags))

    # Try again: a job that failed is made again in its own folder; the copy saved by an earlier make stays as it was
    import hashlib as _hl
    sha = lambda f: _hl.sha256(Path(f).read_bytes()).hexdigest()
    saved0 = (oj.get("result") or {}).get("saved") or ""
    h0 = sha(saved0) if saved0 and Path(saved0).is_file() else ""
    (Path(oj["dir"]) / "result.json").write_text(json.dumps({"ok": False, "error": "a test failure"}), "utf-8")
    r = c.post(f"/auto/voice/{oj['id']}/retry", headers=H)
    rj = wait(oj["id"])
    check("Try again makes it again", r.status_code == 302 and rj["state"] == "done", rj.get("result"))
    saved1 = (rj.get("result") or {}).get("saved") or ""
    check("the copy saved by the earlier make is not touched (the new video gets its own copy)",
          h0 and sha(saved0) == h0 and saved1 and saved1 != saved0 and Path(saved1).is_file(), (saved0, saved1))
    before_ns = json.loads((Path(oj["dir"]) / "result.json").read_text("utf-8")).get("finished_at")
    r = c.post(f"/auto/voice/{oj['id']}/retry", headers=H)
    time.sleep(1.0)
    check("Try again from an old page on a finished job does nothing", r.status_code == 302 and vo.read_job(oj["id"])["state"] == "done"
          and json.loads((Path(oj["dir"]) / "result.json").read_text("utf-8")).get("finished_at") == before_ns)

    # captions for the video's own speech
    r = c.post("/auto/voice/captions", data={"path": str(video), "language": "", "position": "middle"}, headers=H)
    cj = wait(vo.list_jobs()[0]["id"])
    check("captions for a video's own speech", cj["state"] == "done" and (Path(cj["dir"]) / "video.mp4").is_file(), cj.get("result"))

    # text and captions: text on any video (no add-on), the font really used, a preview picture, the editor
    from archivist import textfx as tf

    def band_changed(a_, b_, r0, r1):          # share of the grey 108x192 picture's rows r0..r1 that changed
        a_, b_ = a_[108 * r0:108 * r1], b_[108 * r0:108 * r1]
        return sum(1 for x, y in zip(a_, b_) if abs(x - y) > 50) / max(1, len(a_)) if a_ and b_ else 0
    real_installed = vo.installed
    vo.installed = lambda: False                # the text needs no add-on
    try:
        r = c.post("/auto/text/new", data={"video": str(video), "t_text": ["Три способа летать дешевле", ""],
                                           "t_start": ["0", ""], "t_end": ["1.5", ""], "t_where": ["top", "top"],
                                           "t_look": ["banner", "banner"], "color": "yellow", "size": "medium"}, headers=H)
        tj = wait(vo.list_jobs()[0]["id"])
        page_wo = c.get("/auto/voice", headers=H).get_data(as_text=True)
    finally:
        vo.installed = real_installed
    tres = tj.get("result") or {}
    check("text on a video without the voice add-on", r.status_code == 302 and tj["state"] == "done"
          and tj.get("kind") == "render" and tres.get("texts") == 1, tres)
    check("the text form is on the page without the add-on", "/auto/text/new" in page_wo and "Install the voice add-on" in page_wo)
    tvid = Path(tj["dir"]) / "video.mp4"
    check("the title can be seen at the top (and is gone after its time)",
          band_changed(frame(video, 0.8), frame(tvid, 0.8), 8, 32) > 0.03
          and band_changed(frame(video, 1.9), frame(tvid, 1.9), 8, 32) < 0.005,
          (band_changed(frame(video, 0.8), frame(tvid, 0.8), 8, 32), band_changed(frame(video, 1.9), frame(tvid, 1.9), 8, 32)))
    fdir = home / "fontcheck"
    fdir.mkdir(exist_ok=True)
    shutil.copy2(Path(tj["dir"]) / "captions.ass", fdir / "c.ass")
    tf.install_fonts(fdir)
    rep = subprocess.run([ff, "-v", "verbose", "-f", "lavfi", "-i", "color=c=gray:s=540x960:d=1", "-vf", "ass=c.ass:fontsdir=fonts",
                          "-frames:v", "25", "-f", "null", "-"], cwd=str(fdir), capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    picked = re.findall(r"fontselect: \(([^,]+),[^)]*\) -> ([^,\s]+)", rep)
    check("the program's own font is the one drawn (Montserrat, with Cyrillic)",
          picked and all(fam.startswith("Montserrat") and f.startswith("Montserrat-") for fam, f in picked), picked or rep[-400:])
    r = c.post("/api/text/preview", data={"video": str(video), "t_text": "Hello there", "t_start": "0", "t_end": "2",
                                          "t_where": "middle", "t_look": "box", "at": "1"}, headers=H)
    url = (r.get_json() or {}).get("url") or ""
    img = c.get(url, headers=H) if url else None
    check("a preview picture of the text", bool(url) and img.status_code == 200 and img.mimetype == "image/jpeg"
          and len(img.data) > 2000, r.get_json())
    # the box is measured right: in the rendered picture it reaches past its text by its padding, not by a quarter more
    bdir = home / "boxcheck"
    bdir.mkdir(exist_ok=True)
    (bdir / "b.ass").write_text(tf.document(1080, 1920, [], [{"text": "Подпишись на канал", "start": 0, "end": 2,
                                                               "where": "middle", "look": "box"}]), "utf-8")
    tf.install_fonts(bdir)
    raw = subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=0x808080:s=1080x1920:d=1", "-vf",
                          "ass=b.ass:fontsdir=fonts,format=gray", "-ss", "0.6", "-frames:v", "1", "-f", "rawvideo", "-"],
                         cwd=str(bdir), capture_output=True).stdout
    if len(raw) == 1080 * 1920:
        rows = [raw[y * 1080:(y + 1) * 1080] for y in range(1920)]
        white = [x for r_ in rows for x in range(1080) if r_[x] > 200]
        dark = [x for r_ in rows for x in range(1080) if r_[x] < 60]
        tw, bw = (max(white) - min(white)) if white else 0, (max(dark) - min(dark)) if dark else 0
    else:
        tw = bw = 0
    em = 1080 * 0.05
    check("a box hugs its text (the renderer's own font size, measured)", tw > 300 and 0.6 * em < bw - tw < 1.8 * em,
          {"text": tw, "box": bw, "pad_expected": round(1.2 * em)})
    # a title at the top with captions at the top: next to them, not over them; odd words do not break a style
    one = [{"s": 0.0, "e": 2.0, "words": [{"w": "first", "s": 0.0, "e": 0.9}, {"w": "line", "s": 1.0, "e": 1.9}]}]
    doc = tf.document(1080, 1920, one, [{"text": "Title", "start": 0, "end": 2, "where": "top", "look": "banner"}],
                      {"style": "pop", "position": "top"})
    ys = lambda layer: [int(m_.group(1)) for m_ in re.finditer(r"Dialogue: %d,.*?\\pos\(\d+,(-?\d+)\)" % layer, doc)]
    check("a title in the captions' place goes next to them", ys(1) and ys(3) and min(ys(3)) > max(ys(1)) + 100,
          {"captions": ys(1), "title": ys(3)})
    odd = [{"s": 0.0, "e": 2.0, "words": [{"w": "a\xa0b", "s": 0.0, "e": 0.5}, {"w": "\U0001F600", "s": 0.5, "e": 1.0},
                                          {"w": "end", "s": 1.0, "e": 1.5}]}]
    try:
        okd = all("A" in tf.document(1080, 1920, odd, None, {"style": st_}) or "a" in tf.document(1080, 1920, odd, None, {"style": st_})
                  for st_ in tf.STYLES)
    except Exception as exc:
        okd = repr(exc)
    check("a word with a no-break space or only an emoji breaks no style", okd is True, okd)
    # a preview past the end of a video whose sound is longer than its picture: its last picture
    longer = home / "longer sound.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=540x960:rate=30:duration=2", "-f", "lavfi",
                    "-i", "sine=f=330:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(longer)], check=True)
    r = c.post("/api/text/preview", data={"video": str(longer), "t_text": "The end", "t_start": "end", "at": "99"}, headers=H)
    check("a preview at the very end (sound longer than the picture)", bool((r.get_json() or {}).get("url")), r.get_json())
    r = c.post("/auto/text/new", data={"video": str(video), "t_text": "Too late", "t_start": "30"}, headers=H)
    check("a text after the end of the video: refused in words", r.status_code == 400 and "after the end" in r.get_data(as_text=True),
          r.status_code)
    from urllib.parse import quote
    pv = c.get("/auto/voice?video=" + quote(str(video)), headers=H).get_data(as_text=True)
    import html as _h0
    check("from a saved reel: its path is filled in the video fields", pv.count("value='" + _h0.escape(str(video), quote=True) + "'") >= 2,
          pv.count(_h0.escape(str(video), quote=True)))
    pv = c.get("/auto/voice?video=" + quote(str(home / "gone.mp4")), headers=H).get_data(as_text=True)
    check("a path that is not a file is not filled in",
          not re.search(r"name='(?:video|path)' required value='[^']*gone\.mp4", pv) and "gone.mp4</b>" not in pv)
    # animations: typed text is not there at its start and complete a second later; sliding text moves up into place
    adir = home / "animcheck"
    adir.mkdir(exist_ok=True)
    (adir / "a.ass").write_text(tf.document(540, 960, [], [
        {"text": "Typed text here", "start": 0, "end": 3, "where": "middle", "look": "bold", "anim": "type"},
        {"text": "Sliding", "start": 0, "end": 3, "where": "top", "look": "banner", "anim": "slide"}]), "utf-8")
    tf.install_fonts(adir)

    def gray_at(t):
        out = subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=0x404040:s=540x960:d=3", "-vf",
                              f"ass=a.ass:fontsdir=fonts,format=gray", "-ss", f"{t:.2f}", "-frames:v", "1", "-f", "rawvideo", "-"],
                             cwd=str(adir), capture_output=True).stdout
        return out if len(out) == 540 * 960 else b""

    def lit(img, r0, r1):               # bright pixels in rows r0..r1
        return sum(1 for x in img[540 * r0:540 * r1] if x > 200) if img else -1
    early, late = gray_at(0.15), gray_at(1.6)
    mid_rows = (300, 480)
    check("typed text: hardly any letters at first, all of them a second later",
          0 <= lit(early, *mid_rows) < lit(late, *mid_rows) * 0.25 and lit(late, *mid_rows) > 500,
          (lit(early, *mid_rows), lit(late, *mid_rows)))
    def first_row(img, color_min=150):   # the top of the stripe (the banner is bright yellow -> light grey)
        for y in range(0, 400):
            if img and sum(1 for x in img[540 * y:540 * y + 540] if x > color_min) > 40:
                return y
        return -1
    check("sliding text comes up into its place", first_row(gray_at(0.18), 110) > first_row(gray_at(1.0), 110) >= 0,
          (first_row(gray_at(0.18), 110), first_row(gray_at(1.0), 110)))
    tall_v = home / "tall.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x3060a0:s=540x960:rate=25:duration=2", "-c:v",
                    "libx264", "-pix_fmt", "yuv420p", str(tall_v)], check=True)
    r = c.post("/api/text/preview", data={"video": str(tall_v), "t_text": "Hello", "safe": "1", "at": "1"}, headers=H)
    purl = (r.get_json() or {}).get("url") or ""
    red = 0
    if purl:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(c.get(purl, headers=H).data)).convert("RGB")
        px = im.getpixel((int(im.width * 0.93), int(im.height * 0.6)))
        red = px[0] - px[2]
    check("the preview can show where the platforms' buttons are", red > 30, (purl, red))
    # "My looks": saved with a name, offered in the forms, deleted
    r = c.post("/api/text/looks", json={"name": "Деловой", "style": "minimal", "color": "white", "size": "small",
                                        "position": "bottom"}, headers=H)
    lp = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("a look saved with a name is offered in the forms", (r.get_json() or {}).get("ok") and "data-name='Деловой'" in lp)
    r = c.post("/api/text/looks", json={"name": "Деловой", "delete": True}, headers=H)
    check("and deleted", "data-name='Деловой'" not in c.get("/auto/voice", headers=H).get_data(as_text=True))
    check("a look without a name: said in words", "error" in (c.post("/api/text/looks", json={"name": " "}, headers=H).get_json() or {}))
    check("odd looks sent by hand: no server error", all(c.post("/api/text/looks", json=x, headers=H).status_code == 200
                                                         for x in ([1, 2], {"name": {"x": 1}}, {"name": "a", "style": ["pop"]})))
    r = c.post("/api/text/preview", data={"video": str(video), "t_text": "Обложка", "t_start": "0", "t_end": "2",
                                          "t_where": "middle", "t_look": "banner", "at": "1", "cover": "1"}, headers=H)
    cov = Path((r.get_json() or {}).get("saved") or "")
    from PIL import Image as _Img
    check("a cover picture, full size, saved next to the reels", cov.suffix == ".jpg" and cov.is_file()
          and _Img.open(cov).size == (540, 960) and ("cover" in cov.name or "обложка" in cov.name), (r.get_json(), cov.name))
    r = c.post("/api/text/preview", data={"video": str(home / "none.mp4"), "t_text": "x"}, headers=H)
    check("a preview of a missing video: said in words", "error" in (r.get_json() or {}), r.get_json())
    r = c.post("/auto/text/new", data={"video": str(video), "t_text": "x", "t_start": "soon"}, headers=H)
    check("a text time that is not a number: refused in words", r.status_code == 400, r.status_code)

    # a video bigger than the platforms show: made at a short side of 1080 (faster), the text laid out for that size
    big = home / "big 2k.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1440x2560:rate=25:duration=1", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-preset", "ultrafast", str(big)], check=True)
    before = {j["id"] for j in vo.list_jobs(500)}
    c.post("/auto/text/new", data={"video": str(big), "t_text": "Big", "t_start": "0", "t_end": "1"}, headers=H)
    bj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    bres = bj.get("result") or {}
    bass = (Path(bj["dir"]) / "captions.ass").read_text("utf-8") if (Path(bj["dir"]) / "captions.ass").is_file() else ""
    check("a 2K video is made at 1080x1920 with its text laid out for it", bj["state"] == "done" and bres.get("width") == 1080
          and bres.get("height") == 1920 and "PlayResX: 1080" in bass, (bres.get("width"), bres.get("height")))

    # an NVIDIA encoder that is reported but fails (a driver problem): the processor makes the video instead
    keep_nv = list(vo._NVENC)
    vo._NVENC[:] = [True]
    try:
        before = {j["id"] for j in vo.list_jobs(500)}
        c.post("/auto/text/new", data={"video": str(video), "t_text": "GPU or not", "t_start": "0", "t_end": "1"}, headers=H)
        gj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    finally:
        vo._NVENC[:] = keep_nv
    glog = (Path(gj["dir"]) / "ffmpeg.log").read_text("utf-8", errors="replace")
    check("a failing graphics-card encoder falls back to the processor", gj["state"] == "done" and "h264_nvenc" in glog
          and "libx264" in glog, (gj.get("result"), glog.count("$ ")))

    # a small copy for messengers of a made video
    r = c.post(f"/auto/voice/{dj['id']}/small", headers=H)
    from urllib.parse import unquote as _unq
    loc = _unq(r.headers.get("Location", "").split("small=", 1)[-1].split("#")[0])
    check("a small copy for messengers, next to the reels", r.status_code == 302 and Path(loc).is_file()
          and Path(loc).stat().st_size > 1000 and Path(loc).suffix == ".mp4", loc)
    check("the page says where it is", "ae-done" in c.get(r.headers.get("Location", ""), headers=H).get_data(as_text=True))

    # the editor on the voice-over video: a word fixed, another style, a text at the end; the voice stays
    r = c.get(f"/auto/voice/{dj['id']}/edit", headers=H)
    ep = r.get_data(as_text=True)
    import html as _html
    lines = [_html.unescape(x) for x in re.findall(r"name='c_text' value='([^']*)'", ep)]     # as a browser sends them
    check("the editor lists the captions", r.status_code == 200 and len(lines) >= 2 and "data-preview" in ep, (r.status_code, lines))
    new_first = "Hey " + " ".join(lines[0].split()[1:]) if lines else "Hey"
    r = c.post(f"/api/text/preview", data={"jid": dj["id"], "captions_on": "1", "c_text": [new_first] + lines[1:],
                                           "style": "box", "color": "green", "at": "0.6"}, headers=H)
    check("the editor's preview", bool((r.get_json() or {}).get("url")), r.get_json())
    r = c.post(f"/auto/voice/{dj['id']}/render", data={"captions_on": "1", "c_text": [new_first] + lines[1:], "style": "box",
                                                         "color": "green", "size": "large", "position": "bottom",
                                                         "t_text": "Follow for more", "t_start": "end", "t_where": "middle",
                                                         "t_look": "banner"}, headers=H)
    ej = wait(vo.list_jobs()[0]["id"])
    eres = ej.get("result") or {}
    eass = (Path(ej["dir"]) / "captions.ass").read_text("utf-8") if (Path(ej["dir"]) / "captions.ass").is_file() else ""
    check("the edited video is made with the voice, checked", r.status_code == 302 and ej["state"] == "done"
          and all(x["pass"] for x in eres.get("checks", [])) and abs(eres.get("seconds", 0) - dres.get("seconds", 0)) < 0.05, eres)
    check("the fixed word, the chosen style and the text at the end are in it", "Hey" in eass and "&#x27;" not in eass
          and "\\fnMontserrat ExtraBold" in eass and "Follow for more" in eass and eres.get("texts") == 1, eass[-500:])
    vp = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the next forms start with the look chosen last", "value='box' checked" in vp and "value='green' selected" in vp
          and "value='large' selected" in vp, re.findall(r"value='(\w+)' (?:checked|selected)", vp)[:12])
    ejob = json.loads((Path(ej["dir"]) / "job.json").read_text("utf-8"))
    check("the end text sits in the last 3 seconds", any(t.get("at_end") for t in ejob.get("texts", [])), ejob.get("texts"))
    r = c.get(f"/auto/voice/{cj['id']}/edit", headers=H)
    check("the editor of a video's own captions (its words kept)", r.status_code == 200 and "name='c_text'" in r.get_data(as_text=True))
    # lines split, moved and added on the page come back with their own times (the page's buttons do this)
    cp_ = r.get_data(as_text=True)
    cs_ = [float(x) for x in re.findall(r"name='c_s' value='([^']*)'", cp_)]
    ce_ = [float(x) for x in re.findall(r"name='c_e' value='([^']*)'", cp_)]
    cw_ = [_html.unescape(x) for x in re.findall(r"name='c_w' value='([^']*)'", cp_)]
    ct_ = [_html.unescape(x) for x in re.findall(r"name='c_text' value='([^']*)'", cp_)]
    if cs_ and len(cs_) == len(ct_) == len(cw_):
        mid = (cs_[0] + ce_[0]) / 2
        rows_ = {"c_text": ["first half", "second half"] + ct_[1:] + ["an added line"],
                 "c_s": [str(cs_[0]), str(mid)] + [str(x + 0.1) for x in cs_[1:]] + [str(ce_[-1] + 0.5)],
                 "c_e": [str(mid - 0.01), str(ce_[0])] + [str(x + 0.1) for x in ce_[1:]] + [str(ce_[-1] + 1.2)],
                 "c_w": ["", ""] + cw_[1:] + [""]}
        r = c.post(f"/auto/voice/{cj['id']}/render", data={"captions_on": "1", "style": "classic", **rows_}, headers=H)
        kj = wait(vo.list_jobs()[0]["id"])
        kc = json.loads((Path(kj["dir"]) / "job.json").read_text("utf-8")).get("cues", [])
        lines_ = [" ".join(w["w"] for w in c_["words"]) for c_ in kc]
        moved = [c_["s"] for c_ in kc if " ".join(w["w"] for w in c_["words"]) == ct_[1]] if len(ct_) > 1 else [cs_[0] + 0.1]
        check("lines split, moved and added keep their own times", r.status_code == 302 and kj["state"] == "done"
              and lines_[:2] == ["first half", "second half"] and "an added line" in lines_
              and moved and abs(moved[0] - (cs_[1] + 0.1 if len(cs_) > 1 else moved[0])) < 0.02, (lines_, kc[:3]))
    else:
        check("lines split, moved and added keep their own times", False, (cs_, ce_, len(cw_), ct_))
    r = c.get(f"/auto/voice/{jid}/edit", headers=H)
    check("a voice-over itself (no video) is not edited here: said in words", r.status_code == 400, r.status_code)

    # my voices: a recording saved once (as a clean mono WAV), then in the list like a ready voice; deleted
    rec = home / "моя запись.m4a"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=200:duration=6", "-c:a", "aac", str(rec)], check=True)
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/voice/new", data={"text": "Hello from my own voice.", "voice": "own", "ref_path": str(rec),
                                        "ref_text": "Some words", "save_as": "Мой голос"}, headers=H)
    mjv = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    mine = {k: v for k, v in vo.my_voices().items()}
    mkey = next(iter(mine), "")
    mjob = json.loads((Path(mjv["dir"]) / "job.json").read_text("utf-8"))
    vp = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("a recording saved as my voice, used at once and listed (chosen next time)", r.status_code == 302 and mjv["state"] == "done"
          and mkey and mjob["voice"].get("key") == mkey and mjob["voice"].get("ref_text") == "Some words"
          and f"value='{mkey}' checked" in vp and "Мой голос" in vp, (mine, mjob.get("voice")))
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/voice/new", data={"text": "Again in my voice.", "voice": mkey}, headers=H)
    mj2 = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    check("my voice is chosen like a ready one", mj2["state"] == "done", mj2.get("result"))
    fpv = c.get("/auto/finish", headers=H).get_data(as_text=True)
    check("my voice on the one-page form too", f"name='nvoice' value='{mkey}'" in fpv)
    r = c.post(f"/auto/voice/my/{mkey}/delete", headers=H)
    check("a saved voice is deleted", r.status_code == 302 and mkey not in vo.my_voices())
    short = home / "short.wav"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=200:duration=1", str(short)], check=True)
    r = c.post("/auto/voice/new", data={"text": "x", "voice": "own", "ref_path": str(short), "save_as": "Short"}, headers=H)
    check("a recording too short to keep: said in words", r.status_code == 400, r.status_code)
    r = c.post("/auto/voice/my/../x/delete", headers=H)
    check("a wrong saved-voice name: no harm", r.status_code in (400, 404), r.status_code)

    # odd input: words, never a server error
    for name, data in [("no text", {"text": "", "voice": vo.DEFAULT_VOICE}), ("unknown voice", {"text": "Hi.", "voice": "x"}),
                       ("short description", {"text": "Hi.", "voice": "describe", "description": "a"}),
                       ("missing recording", {"text": "Hi.", "voice": "own", "ref_path": str(home / "nope.wav")}),
                       ("too long", {"text": "a " * 3000, "voice": vo.DEFAULT_VOICE})]:
        r = c.post("/auto/voice/new", data=data, headers=H)
        check(f"refused in words: {name}", r.status_code == 400 and "errbox" in r.get_data(as_text=True), r.status_code)
    r = c.post("/auto/voice/20990101-000000-abcdef/dub", data={"video": str(video)}, headers=H)
    check("a voice-over that does not exist", r.status_code == 400, r.status_code)
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(home / "none.mp4")}, headers=H)
    check("a video that does not exist", r.status_code == 400, r.status_code)

    # a voice-over made by an older build: its stored recording path is that build's (maybe removed since)
    def old_job(key, ref):                      # (and it failed, so the page offers Try again)
        jj = json.loads((d / "job.json").read_text("utf-8"))
        jj["voice"].update(key=key, ref_wav=ref)
        (d / "job.json").write_text(json.dumps(jj), "utf-8")
        (d / "result.json").write_text(json.dumps({"ok": False, "error": "a test failure"}), "utf-8")
    old_job("friend", str(home / "MediaEngine-b158" / "assets" / "voice" / "friend_3_1.flac"))       # 3.1, gone now
    c.post(f"/auto/voice/{jid}/retry", headers=H)
    fj = wait(jid)
    check("Try again on a voice this version no longer has: said in words", fj["state"] == "failed"
          and "recording of this voice is no longer there" in str((fj.get("result") or {}).get("error")), fj.get("result"))
    old_job(vo.DEFAULT_VOICE, str(home / "MediaEngine-b158" / "assets" / "voice" / vo.VOICES[vo.DEFAULT_VOICE]["ref"]))
    c.post(f"/auto/voice/{jid}/retry", headers=H)
    fj = wait(jid)
    check("Try again after an update: the voice's recording of this build", fj["state"] == "done", fj.get("result"))

    # Finish a video: everything on one page
    fp = c.get("/auto/finish?video=" + quote(str(video)), headers=H).get_data(as_text=True)
    check("the one-page form: the video filled in, a made voice-over offered, a new one possible",
          "value='" + _h0.escape(str(video), quote=True) + "'" in fp and "value='made'" in fp and "value='new'" in fp
          and f"value='{jid}'" in fp and "data-preview" in fp)
    base_f = {"finish": "1", "video": str(video), "voice": "made", "voice_from": jid, "captions": "voice", "start": "0.2",
              "keep_sound": "1", "style": "pop", "color": "pink", "t_text": "Итог недели", "t_start": "0", "t_end": "2",
              "t_where": "top", "t_look": "banner", "at": "0.8"}
    r = c.post("/api/text/preview", data=base_f, headers=H)
    check("its preview shows the voice's captions and the text", bool((r.get_json() or {}).get("url")), r.get_json())
    r = c.post("/auto/finish", data=base_f, headers=H)
    fj = wait(vo.list_jobs()[0]["id"])
    fres, fjob = fj.get("result") or {}, json.loads((Path(fj["dir"]) / "job.json").read_text("utf-8"))
    check("a video with a made voice, its captions and a text, in one go", r.status_code == 302 and fj["state"] == "done"
          and fres.get("captions", 0) > 0 and fres.get("texts") == 1 and all(x["pass"] for x in fres.get("checks", []))
          and fjob.get("cues"), fres)
    check("and it can be edited afterwards", c.get(f"/auto/voice/{fj['id']}/edit", headers=H).status_code == 200)
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={**base_f, "voice": "new", "text": "Hello there, my *friend*. This is new.",
                                     "nvoice": vo.DEFAULT_VOICE, "voice_from": ""}, headers=H)
    new_ids = [j["id"] for j in vo.list_jobs(500) if j["id"] not in before]       # newest first
    jobs_now = [vo.read_job(x) for x in new_ids] + [{}, {}]
    nj, nv = (wait(jobs_now[0]["id"]) if new_ids else {"state": "?"}), (vo.read_job(new_ids[1]) if len(new_ids) > 1 else {})
    n_before = 0
    check("a new voice-over is made first, then the video with it", r.status_code == 302 and len(new_ids) == 2
          and nv.get("kind") == "voiceover" and nv["state"] == "done" and nj["state"] == "done"
          and json.loads((Path(nj["dir"]) / "job.json").read_text("utf-8")).get("voice_from") == nv["id"],
          (nj.get("result"), nv.get("state")))
    before = {j["id"] for j in vo.list_jobs(500)}
    if len(new_ids) > 1:
        nvw = json.loads((vo._job_dir(new_ids[1]) / "words.json").read_text("utf-8"))
        nres = vo.read_job(new_ids[1]).get("result") or {}
        nass = (Path(vo._job_dir(new_ids[0])) / "captions.ass").read_text("utf-8")
        check("*stars* in a script: not said, the word kept in the color in the captions",
              "*" not in str(nres.get("said")) and [w["w"] for w in nvw if w.get("em")] == ["friend."]
              and nass.count("FRIEND.") >= 2 and all("*" not in x for x in re.findall(r"\}([^{}]+)$", nass, re.M)),
              ([w for w in nvw if w.get("em")], nres.get("said")))
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "speech"}, headers=H)
    sj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    check("captions of the video's own speech on the same page", r.status_code == 302 and sj["state"] == "done"
          and (sj.get("result") or {}).get("captions", 0) > 0, sj.get("result"))
    srt_ = (Path(sj["dir"]) / "captions.srt").read_text("utf-8") if (Path(sj["dir"]) / "captions.srt").is_file() else ""
    check("speech captions keep the speech's own times (no voice start added)", "00:00:00,200 -->" in srt_, srt_[:80])
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "none", "t_text": "Hi", "start": "0.3",
                                     "keep_sound": "1"}, headers=H)
    kj2 = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    check("no voice: the video's own sound kept", kj2["state"] == "done"
          and any(x["check"] == "sound" and x["pass"] for x in (kj2.get("result") or {}).get("checks", [])), kj2.get("result"))
    fp2 = c.get("/auto/finish", headers=H).get_data(as_text=True)
    check("'keep the video's own sound' is shown with no voice too (not a hidden field)",
          "data-when='voice=made voice=new' hidden><label" not in fp2 and "name='keep_sound'" in fp2)
    if new_ids and len(new_ids) > 1:                 # a video whose voice-over was interrupted: said so, not 'deleted'
        keep_ = (Path(vo._job_dir(new_ids[1])) / "result.json").read_bytes()
        (Path(vo._job_dir(new_ids[1])) / "result.json").unlink(missing_ok=True)
        keep0 = (Path(vo._job_dir(new_ids[0])) / "result.json").read_bytes()
        (Path(vo._job_dir(new_ids[0])) / "result.json").write_text(json.dumps({"ok": False, "error": "x"}), "utf-8")
        c.post(f"/auto/voice/{new_ids[0]}/retry", headers=H)
        rj_ = wait(new_ids[0])
        (Path(vo._job_dir(new_ids[1])) / "result.json").write_bytes(keep_)     # (made again: no job left interrupted)
        check("a video whose voice-over is not made: said so", rj_["state"] == "failed"
              and "was not made" in str((rj_.get("result") or {}).get("error")), rj_.get("result"))
    r = c.post("/api/text/preview", data={"jid": cj["id"], "captions_on": "1", "c_text": ["line"] * 300,
                                          "c_s": [str(i * 0.5) for i in range(300)], "c_e": [str(i * 0.5 + 0.4) for i in range(300)],
                                          "c_w": [""] * 300, "at": "1"}, headers=H)
    check("a preview with 300 caption lines", bool((r.get_json() or {}).get("url")), r.get_json())
    r = c.post(f"/auto/voice/{cj['id']}/render", data={"captions_on": "1", "c_text": ["a", "b"], "c_s": ["0", "inf"],
                                                         "c_e": ["1e308"], "c_w": ["[" * 5000 + "]" * 5000, ""]}, headers=H)
    check("odd caption times sent to the editor: no server error", r.status_code in (302, 400), r.status_code)
    if r.status_code == 302:
        oj_ = wait(vo.list_jobs()[0]["id"])
        check("and the video is still made", oj_["state"] == "done", oj_.get("result"))
    typed = tf.document(1080, 1920, [], [{"text": "x" * 38, "start": 0, "end": 1, "where": "top", "look": "bold", "anim": "type"}])
    last = max(int(m_) for m_ in re.findall(r"\\t\((\d+),", typed))
    check("typed text is complete while it is shown, its shadow appears with each letter", last < 1000 and "\\4a&HFF&" in typed, last)
    song = home / "song.mp3"                   # a 1-second song: it must loop under the whole video
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=660:duration=1", "-c:a", "libmp3lame", str(song)], check=True)
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={**base_f, "music": str(song), "music_level": "loud"}, headers=H)
    mj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    mres = mj.get("result") or {}
    tail_s = subprocess.run([ff, "-hide_banner", "-nostats", "-sseof", "-0.9", "-i", str(Path(mj["dir"]) / "video.mp4"), "-t", "0.4",
                             "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mv = re.search(r"mean_volume: (-?[\d.]+) dB", tail_s)
    def band660(path):                         # the song's tone (660 Hz) in the last moment, where the voice (220 Hz) is over
        out = subprocess.run([ff, "-hide_banner", "-nostats", "-sseof", "-0.45", "-i", str(path), "-t", "0.3", "-af",
                              "bandpass=f=660:width_type=h:w=60,bandpass=f=660:width_type=h:w=60,volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        m_ = re.search(r"mean_volume: (-?[\d.]+) dB", out)
        return float(m_.group(1)) if m_ else -200.0
    b0 = {j["id"] for j in vo.list_jobs(500)}
    c.post("/auto/finish", data=base_f, headers=H)                  # the same video without the song
    nm = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in b0))
    with_m, without_m = band660(Path(mj["dir"]) / "video.mp4"), band660(Path(nm["dir"]) / "video.mp4")
    check("music under the voice, looped to the end (the song is there at the very end, the 1-s song looped)",
          mj["state"] == "done" and all(x["pass"] for x in mres.get("checks", [])) and with_m > without_m + 20,            # (fading out: quieter at the very end)
          (mres.get("error"), with_m, without_m))
    lu = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(Path(mj["dir"]) / "video.mp4"), "-vn", "-af", "ebur128=peak=true",
                         "-f", "null", "-"], capture_output=True, text=True).stderr
    I_ = [float(x) for x in re.findall(r"I:\s+(-?[\d.]+) LUFS", lu)][-1:] or [0.0]
    TP_ = [float(x) for x in re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lu)][-1:] or [0.0]
    check("a video with a voice is at the platforms' loudness (about -14 LUFS, peaks under -1 dB)",
          -16.0 <= I_[0] <= -12.5 and TP_[0] <= -0.9, (I_, TP_))
    song2 = home / "song moved.mp3"
    song.rename(song2)                         # the song moved after the video was made: it can still be edited
    r = c.post(f"/auto/voice/{mj['id']}/render", data={"captions_on": "", "t_text": "Again", "t_start": "0"}, headers=H)
    check("a video whose song was moved can still be made again (without it)", r.status_code == 302, r.status_code)
    if r.status_code == 302:
        wait(vo.list_jobs()[0]["id"])
    song2.rename(song)

    def music_only(level):
        before_ = {j["id"] for j in vo.list_jobs(500)}
        c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "none", "music": str(song),
                                     "music_level": level}, headers=H)       # (no 'keep sound': only the music)
        j_ = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before_))
        o_ = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(Path(j_["dir"]) / "video.mp4"), "-af", "volumedetect",
                             "-f", "null", "-"], capture_output=True, text=True).stderr
        m_ = re.search(r"mean_volume: (-?[\d.]+) dB", o_)
        return float(m_.group(1)) if m_ else None
    q_, l_ = music_only("quiet"), music_only("loud")
    check("music alone: quiet is quieter than loud", q_ is not None and l_ is not None and l_ - q_ > 4, (q_, l_))
    em2 = tf.mark_emphasis([{"w": x, "s": 0, "e": 1} for x in "«*слово*» 5 * 3 = 15. *open run. next".split()])
    check("emphasis: after a quote; a lone star marks nothing; an open mark ends with its sentence",
          [w["w"] for w in em2 if w.get("em")] == ["«слово»", "open", "run."], [(w["w"], w.get("em")) for w in em2])
    r = c.post("/auto/finish", data={**base_f, "music": str(home / "nope.mp3")}, headers=H)
    check("a music file that is not there: refused in words", r.status_code == 400, r.status_code)
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "speech",
                                     "script": "Hello, world from *this* video."}, headers=H)
    pj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    pw = [w for c_ in json.loads((Path(pj["dir"]) / "job.json").read_text("utf-8")).get("cues", []) for w in c_["words"]]
    check("my text timed to the speech: its own words (and marks), the speech's times",
          [w["w"] for w in pw] == ["Hello,", "world", "from", "this", "video."] and pw[3].get("em") and abs(pw[0]["s"] - 0.2) < 0.01,
          [(w["w"], w["s"], w.get("em")) for w in pw])
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "voice"}, headers=H)
    check("captions of a voice without a voice: refused in words", r.status_code == 400, r.status_code)
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "none"}, headers=H)
    check("nothing to add: refused in words", r.status_code == 400, r.status_code)

    # several videos finished the same way
    v2, v3 = home / "clip two.mp4", home / "clip3.mp4"
    for vv, dur in ((v2, 3), (v3, 2)):
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=480x854:rate=25:duration={dur}",
                        "-f", "lavfi", "-i", f"sine=f=300:duration={dur}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(vv)], check=True)
    fpm = c.get("/auto/finish", headers=H).get_data(as_text=True)
    check("several videos: the form offers more videos (paths, Choose…, saved reels)", "name='videos_more'" in fpm
          and "data-pick='videos'" in fpm and "name='more'" in fpm)
    before = {j["id"] for j in vo.list_jobs(500)}
    n_sent = len(sent)
    many = {"video": str(video), "videos_more": f"{v2}\r\n\r\n{v3}\r\n{video}\r\n{home}/./clip3.mp4", "voice": "none", "captions": "speech",
            "style": "box", "t_text": "Итог недели", "t_start": "0", "t_end": "1.5", "t_where": "top", "t_look": "banner",
            "music": str(song), "music_level": "quiet", "keep_sound": "1"}
    r = c.post("/auto/finish", data=many, headers=H)
    mids = [j["id"] for j in vo.list_jobs(500) if j["id"] not in before][::-1]          # oldest first
    mj = [wait(x) for x in mids]
    mvids = [json.loads((Path(x["dir"]) / "job.json").read_text("utf-8")).get("video") for x in mj]
    check("several videos: one new video each, in order (a video twice, also written another way: once)", r.status_code == 302
          and mvids == [str(video), str(v2), str(v3)], mvids)
    srcs = [Path(x.get("source", "")).name for x in sent[n_sent:] if x["task"] == "transcribe"]
    check("several videos: each video's own speech is heard", srcs == [video.name, v2.name, v3.name], srcs)
    check("several videos: each made with its own speech's captions, the text and the music",
          all(x["state"] == "done" and (x.get("result") or {}).get("captions", 0) > 0 and (x.get("result") or {}).get("texts") == 1
              and all(k["pass"] for k in (x.get("result") or {}).get("checks", [])) for x in mj),
          [(x["state"], (x.get("result") or {}).get("captions")) for x in mj])
    check("several videos: each lasts as long as its own video", len(mj) == 3 and abs(float((mj[1].get("result") or {})
          .get("seconds", 0)) - 3.0) < 0.3 and abs(float((mj[2].get("result") or {}).get("seconds", 0)) - 2.0) < 0.3,
          [(x.get("result") or {}).get("seconds") for x in mj])
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={**many, "videos_more": f"{v2}\n{home / 'gone.mp4'}"}, headers=H)
    check("several videos: one missing - nothing made, said which", r.status_code == 400 and "gone.mp4" in r.get_data(as_text=True)
          and not [j for j in vo.list_jobs(500) if j["id"] not in before], r.status_code)
    r = c.post("/auto/finish", data={**many, "video": str(v2), "t_start": "2.5", "t_end": "2.9", "videos_more": str(v3)}, headers=H)
    check("several videos: a text after the end of one of them - refused, naming it",
          r.status_code == 400 and "clip3.mp4" in r.get_data(as_text=True)
          and not [j for j in vo.list_jobs(500) if j["id"] not in before], r.get_data(as_text=True)[-300:])
    notes = home / "notes.txt"
    notes.write_text("not a video", "utf-8")
    r = c.post("/auto/finish", data={**many, "videos_more": f"{v2}\n{notes}"}, headers=H)
    check("several videos: a file that is not a video - nothing made, said which", r.status_code == 400
          and "notes.txt" in r.get_data(as_text=True) and not [j for j in vo.list_jobs(500) if j["id"] not in before],
          r.get_data(as_text=True)[-300:])
    r = c.post("/auto/finish", data={**many, "videos_more": str(v2), "music": str(home / "nope.mp3")}, headers=H)
    check("several videos: a shared choice wrong - said without blaming a video", r.status_code == 400
          and "music" in r.get_data(as_text=True) and "(clip.mp4)" not in r.get_data(as_text=True))
    r = c.post("/auto/finish", data={**many, "videos_more": str(v2), "script": "Hello world from the video."}, headers=H)
    check("several videos: the exact text of a speech is for one video - refused in words", r.status_code == 400
          and "for one video" in r.get_data(as_text=True))
    r = c.post("/auto/finish", data={**many, "videos_more": "", "more": str(video), "script": "Hello world from the video."},
               headers=H)
    one = [j for j in vo.list_jobs(500) if j["id"] not in before]
    check("one video ticked twice: still one, its exact text kept", r.status_code == 302 and len(one) == 1
          and json.loads((Path(one[0]["dir"]) / "job.json").read_text("utf-8")).get("script") == "Hello world from the video.",
          [x.get("id") for x in one])
    wait(one[0]["id"]) if one else None
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={"video": str(video), "voice": "bogus", "captions": "voice"}, headers=H)
    check("an unknown voice choice: no voice (captions of a voice refused)", r.status_code == 400
          and not [j for j in vo.list_jobs(500) if j["id"] not in before])
    r = c.post("/auto/finish", data={**many, "videos_more": "\n".join(str(home / f"x{i}.mp4") for i in range(40))}, headers=H)
    check("several videos: at most 30 at once", r.status_code == 400 and "At most 30" in r.get_data(as_text=True))
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/finish", data={**many, "voice": "new", "text": "One voice for both.", "nvoice": vo.DEFAULT_VOICE,
                                     "captions": "voice", "videos_more": str(v2), "speed": "slower", "pauses": "short"}, headers=H)
    nids = [j["id"] for j in vo.list_jobs(500) if j["id"] not in before][::-1]
    njobs = [wait(x) for x in nids]
    kinds = [x.get("kind") for x in njobs]
    vfs = [json.loads((Path(x["dir"]) / "job.json").read_text("utf-8")).get("voice_from") for x in njobs[1:]]
    check("several videos with a new voice: made once, then put on each", r.status_code == 302
          and kinds == ["voiceover", "render", "render"] and vfs == [nids[0], nids[0]]
          and all(x["state"] == "done" for x in njobs), (kinds, vfs, [x["state"] for x in njobs]))
    before = {j["id"] for j in vo.list_jobs(500)}
    fail_tts[0] = True
    r = c.post("/auto/finish", data={**many, "voice": "new", "text": "This voice fails first.", "nvoice": vo.DEFAULT_VOICE,
                                     "captions": "voice", "videos_more": str(v2)}, headers=H)
    fids = [j["id"] for j in vo.list_jobs(500) if j["id"] not in before][::-1]
    fjobs = [wait(x) for x in fids]
    fail_tts[0] = False
    check("a shared voice-over that fails: the videos waiting for it say so", len(fjobs) == 3
          and [x["state"] for x in fjobs] == ["failed"] * 3
          and all(str((x.get("result") or {}).get("error", "")).startswith("The voice-over was not made") for x in fjobs[1:]),
          [(x["state"], (x.get("result") or {}).get("error")) for x in fjobs])
    r = c.post(f"/auto/voice/{fids[0]}/retry", headers=H) if fids else None
    again = [wait(x) for x in fids]
    check("one Try again on the voice-over makes it and the videos that waited for it", r is not None and r.status_code == 302
          and [x["state"] for x in again] == ["done"] * 3, [(x["state"], (x.get("result") or {}).get("error")) for x in again])
    nvj = json.loads((Path(njobs[0]["dir"]) / "job.json").read_text("utf-8")) if njobs else {}
    check("the pace chosen on the one-page form goes with the new voice", nvj.get("speed") == 0.92 and nvj.get("pauses") == 0.6,
          (nvj.get("speed"), nvj.get("pauses")))

    check("the original video is byte for byte as it was after everything", _hl0.sha256(video.read_bytes()).hexdigest() == video_sha)

    # a picture that ends before its sound: held to the end, the text at the end on it
    short_pic = home / "short picture.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=540x960:rate=25:duration=2",
                    "-f", "lavfi", "-i", "sine=f=300:duration=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    str(short_pic)], check=True)
    before = {j["id"] for j in vo.list_jobs(500)}
    r = c.post("/auto/text/new", data={"video": str(short_pic), "t_text": "THE END", "t_start": "end", "t_where": "middle",
                                       "t_look": "box"}, headers=H)
    sp = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    out_sp = Path(sp["dir"]) / "video.mp4"
    late, last_pic = frame(out_sp, 5.0), frame(out_sp, 1.95)          # the held last picture, with and without the text
    diff = sum(1 for x, y in zip(late, last_pic) if abs(x - y) > 50) / max(1, len(late)) if late and last_pic else 0
    check("a picture shorter than its sound is held to the end, with the end text on it", sp["state"] == "done"
          and bool(late) and diff > 0.005, (sp.get("result") or {}).get("error") or f"{100 * diff:.1f}%")

    # non-square pixels (a 1440x1080 camcorder video with 4:3 pixels is 1920x1080 on screen)
    hdv = home / "hdv.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1440x1080:rate=25:duration=1",
                    "-vf", "setsar=4/3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(hdv)], check=True)
    before = {j["id"] for j in vo.list_jobs(500)}
    c.post("/auto/text/new", data={"video": str(hdv), "t_text": "Wide", "t_start": "0", "t_end": "1"}, headers=H)
    hj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    hres = hj.get("result") or {}
    head_ = subprocess.run([ff, "-hide_banner", "-i", str(Path(hj["dir"]) / "video.mp4")], capture_output=True, text=True).stderr
    vline = next((x for x in head_.splitlines() if "Video:" in x), "")      # (no ffprobe in the program: FFmpeg's own text)
    check("non-square pixels: made 1920x1080 with square pixels (not stretched)", hj["state"] == "done"
          and (hres.get("width"), hres.get("height")) == (1920, 1080) and "1920x1080" in vline
          and ("SAR" not in vline or "SAR 1:1" in vline), (hres.get("width"), vline[-80:]))

    # odd input that used to break a page or a request
    r = c.post("/auto/text/new", data={"video": str(video), "t_text": "x", "t_start": "0", "t_end": "9" * 400}, headers=H)
    check("a time typed as hundreds of digits: refused in words", r.status_code == 400, r.status_code)
    r = c.post("/api/auto/pick-voice-file", data=json.dumps(["video"]), headers={**H, "Content-Type": "application/json"})
    check("the file picker with an odd request: an answer, not a server error", r.status_code == 200, r.status_code)
    song_only = home / "only sound.mp3"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:duration=2", str(song_only)], check=True)
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(song_only)}, headers=H)
    check("a voice onto a sound file (no picture): refused before anything is made", r.status_code == 400, r.status_code)
    silent = home / "silent.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=1", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(silent)], check=True)
    r = c.post("/auto/voice/captions", data={"path": str(silent)}, headers=H)
    check("captions of a video without sound: refused before listening", r.status_code == 400
          and "no sound" in r.get_data(as_text=True), r.status_code)
    words_b = vo.align("Prices rose (by 20 percent) this week [and more].", [])
    check("words in brackets stay in the captions (they are said)", [w["w"] for w in words_b]
          == ["Prices", "rose", "(by", "20", "percent)", "this", "week", "[and", "more]."], [w["w"] for w in words_b])

    # a long job running: a video waits behind its voice-over; Stop for a waiting job and for the one being made
    big = home / "long.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=40",
                    "-f", "lavfi", "-i", "sine=f=200:duration=40", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(big)], check=True)
    before = {j["id"] for j in vo.list_jobs(500)}
    fail_tts[0] = True
    c.post("/auto/finish", data={"video": str(video), "voice": "new", "text": "Wait for me.", "nvoice": vo.DEFAULT_VOICE,
                                 "captions": "voice"}, headers=H)
    pair = [j["id"] for j in vo.list_jobs(500) if j["id"] not in before][::-1]          # voice-over, video
    for x in pair:
        wait(x)
    fail_tts[0] = False
    long_ids = []
    for _ in range(2):
        b0 = {j["id"] for j in vo.list_jobs(500)}
        c.post("/auto/text/new", data={"video": str(big), "t_text": "Long", "t_start": "0", "t_end": "3"}, headers=H)
        long_ids.append(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in b0))
    t_end = time.time() + 30
    while vo.read_job(long_ids[0])["state"] != "working" and time.time() < t_end:
        time.sleep(0.2)
    if len(pair) == 2:
        c.post(f"/auto/voice/{pair[1]}/retry", headers=H)        # the video first ...
        c.post(f"/auto/voice/{pair[0]}/retry", headers=H)        # ... then its voice-over
    r1 = c.post(f"/auto/voice/{long_ids[1]}/stop", headers=H)
    w2 = vo.read_job(long_ids[1])
    check("Don't make it: a waiting job leaves the queue, said 'Stopped.'", r1.status_code == 302 and w2["state"] == "failed"
          and (w2.get("result") or {}).get("error") == "Stopped.", (w2["state"], w2.get("result")))
    time.sleep(1.0)
    t_stop = time.time()
    r0 = c.post(f"/auto/voice/{long_ids[0]}/stop", headers=H)
    w1 = wait(long_ids[0], 60)
    took = time.time() - t_stop
    flog = (Path(w1["dir"]) / "ffmpeg.log").read_text("utf-8", errors="replace") if (Path(w1["dir"]) / "ffmpeg.log").is_file() else ""
    check("Stop: the video being made stops at once (its FFmpeg killed, not run to the end), said 'Stopped.'",
          r0.status_code == 302 and w1["state"] == "failed" and (w1.get("result") or {}).get("error") == "Stopped."
          and took < 10 and "muxing overhead" not in flog and not (Path(w1["dir"]) / "video.new.mp4").exists(),
          (w1.get("result"), round(took, 1)))
    if len(pair) == 2:
        pv, pr = wait(pair[0]), wait(pair[1])
        check("Try again on the video, then on its voice-over: both made (the video waits for its voice)",
              pv["state"] == "done" and pr["state"] == "done", (pv["state"], pr["state"], (pr.get("result") or {}).get("error")))

    # Stop pressed in the moment before the job's FFmpeg starts: it is stopped as soon as it starts
    vo._CURRENT.update(cancel=True)
    rc_ = vo._run_ffmpeg([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:duration=30", "-f", "null", "-"],
                         home, home / "stop_early.log", 60)
    vo._CURRENT.pop("cancel", None)
    check("Stop before the process starts still stops it", rc_ != 0, rc_)
    covered = home / "with cover.mp4"
    pic = home / "cover.jpg"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=200x100", "-vf", "setsar=2/1", "-frames:v", "1", str(pic)], check=True)
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=1", "-i", str(pic),
                    "-map", "0:v", "-map", "1:v", "-c:v:0", "libx264", "-pix_fmt:v:0", "yuv420p", "-c:v:1", "mjpeg",
                    "-disposition:v:1", "attached_pic", str(covered)], check=True)
    check("pixel shape read from the video itself, not its cover picture", vo.video_size(covered)[:2] == (640, 360),
          vo.video_size(covered))
    song_mp3 = home / "a song.mp3"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:duration=1", str(song_mp3)], check=True)
    said = ""
    try:
        vo.video_size(song_mp3)
    except vo.VoiceError as exc:
        said = str(exc)
    check("a song chosen as the video: said in words (not FFmpeg's code)", said == "This file has no picture: choose a video.", said)

    install_flows(home, check)

    # Russian
    c.post("/lang", data={"back": "/auto/voice"}, headers=H)
    ru = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page in Russian", "Озвучка" in ru and "Наложить на видео" in ru and "Новая озвучка" in ru)
    left = [t for t in ("Put it on a video", "New voice-over", "Make the voice-over", "Captions for a video", "Text on a video",
                        "Look of the captions", "Add a text", "Edit text and captions", "Bold capitals", "On a colored stripe",
                        "Title at the top") if t in re.sub(r"<script.*?</script>|<template.*?</template>", "", ru, flags=re.S)]
    check("no English left of the main texts", not left, left)
    rue = c.get(f"/auto/voice/{dj['id']}/edit", headers=H).get_data(as_text=True)
    rue_vis = re.sub(r"<script.*?</script>", "", rue, flags=re.S)
    left = [t for t in ("Edit text and captions", "Text on the video", "Preview", "One picture of the finished video",
                        "Fix a word right in its line", "A new video is made", "Make the video", "Add a text", "Color")
            if t in rue_vis]
    check("the editor in Russian", "Изменить текст и субтитры" in rue and not left, left)
    ruf = re.sub(r"<script.*?</script>", "", c.get("/auto/finish", headers=H).get_data(as_text=True), flags=re.S)
    left = [t for t in ("Finish a video", "The voice", "No voice", "A voice-over made already", "No captions",
                        "The words of the voice", "The look", "Make the video", "More videos", "or reels saved lately",
                        "Pace", "normal speed", "long pauses") if t in ruf]
    check("the one-page form in Russian", "Доделать видео" in ruf and not left, left)

    # delete
    r = c.post(f"/auto/voice/{jid}/delete", headers=H)
    check("delete removes the job's folder", r.status_code == 302 and not d.exists())
    check("busy is empty when nothing runs", vo.busy() == "", vo.busy())

    rep = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks}
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False), "utf-8")
    print(json.dumps({"passed": rep["passed"], "total": rep["total"]}))
    return 0 if rep["passed"] == rep["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
