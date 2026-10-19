"""Voice-over add-on, everything except the models: text pieces, word times, captions (SRT / ASS), the jobs, the
Voice-over page (English and Russian), its files, and the voice burned onto a real video with FFmpeg - with a stand-in
for the add-on's worker (the real VoxCPM2 / Whisper run is mediaengine-voice-addon.yml).

  python tests/voice_check.py --home <empty dir> [--out report.json]
"""
from __future__ import annotations

import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 18791


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
    sa = vo.ass(cues, 1080, 1920)
    check("ASS: the frame size, karaoke words", "PlayResX: 1080" in sa and "PlayResY: 1920" in sa and "{\\k" in sa)
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
    r = c.post("/auto/voice/new", data={"text": "Hello there.", "voice": "friend"}, headers=H)
    check("a voice-over before installing: refused in words", r.status_code == 400 and "Install the voice add-on first" in r.get_data(as_text=True))
    check("the home of Auto Edit links the page only when it is released", ("/auto/voice" in c.get("/auto", headers=H).get_data(as_text=True))
          == vo.SHOW_ON_HOME)
    check("the recording of voice 3.1 ships with the program", (vo.ASSETS / vo.VOICES["friend"]["ref"]).is_file(), vo.ASSETS)

    ff = _ffmpeg_exe()
    (vo.SITE).mkdir(parents=True, exist_ok=True)
    (vo.MODELS / "voxcpm").mkdir(parents=True, exist_ok=True)
    (vo.MODELS / "whisper").mkdir(parents=True, exist_ok=True)
    vo.MANIFEST.write_text(json.dumps({"version": vo.ADDON_VERSION, "python": f"{sys.version_info[0]}.{sys.version_info[1]}",
                                       "cuda": False, "bytes": 123}), "utf-8")
    check("a stand-in add-on counts as installed", vo.installed())

    def fake_worker(job, work, timeout=3600, on_line=None):
        work.mkdir(parents=True, exist_ok=True)
        if on_line:
            on_line({"progress": 0.5, "step": "speaking", "chunk": 1, "chunks": 1})
        if job["task"] == "tts":
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

    r = c.post("/auto/voice/new", data={"text": "Okay, so here's something. You don't need ten outfits!", "voice": "friend",
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
    check("voice 3.1 is used with its own words", job["voice"].get("ref_text") == vo.FRIEND_REF_TEXT)
    r = c.get(f"/auto/voice/{jid}/file/voice.wav", headers={**H, "Range": "bytes=0-99"})
    check("the player gets the sound in pieces (Range)", r.status_code == 206 and len(r.data) == 100, r.status_code)
    r = c.get(f"/auto/voice/{jid}/file/captions.srt?download=1", headers=H)
    check("captions download with a readable name", r.status_code == 200 and "attachment" in r.headers.get("Content-Disposition", ""),
          r.headers.get("Content-Disposition"))
    check("only the job's own files are served", c.get(f"/auto/voice/{jid}/file/job.json", headers=H).status_code == 404
          and c.get("/auto/voice/..%2F..%2Fx/file/voice.wav", headers=H).status_code == 404)
    page = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page lists it with a player and 'Put it on a video'", f"/auto/voice/{jid}/file/voice.wav" in page and "Put it on a video" in page)

    # a real video (vertical, with sound) and the voice burned onto it
    video = home / "clip.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=540x960:rate=30:duration=2",
                    "-f", "lavfi", "-i", "sine=f=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(video)], check=True)
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

    # Try again: a finished job made again in its own folder
    r = c.post(f"/auto/voice/{oj['id']}/retry", headers=H)
    rj = wait(oj["id"])
    check("Try again makes it again", r.status_code == 302 and rj["state"] == "done", rj.get("result"))

    # captions for the video's own speech
    r = c.post("/auto/voice/captions", data={"path": str(video), "language": "", "position": "middle"}, headers=H)
    cj = wait(vo.list_jobs()[0]["id"])
    check("captions for a video's own speech", cj["state"] == "done" and (Path(cj["dir"]) / "video.mp4").is_file(), cj.get("result"))

    # odd input: words, never a server error
    for name, data in [("no text", {"text": "", "voice": "friend"}), ("unknown voice", {"text": "Hi.", "voice": "x"}),
                       ("short description", {"text": "Hi.", "voice": "describe", "description": "a"}),
                       ("missing recording", {"text": "Hi.", "voice": "own", "ref_path": str(home / "nope.wav")}),
                       ("too long", {"text": "a " * 3000, "voice": "friend"})]:
        r = c.post("/auto/voice/new", data=data, headers=H)
        check(f"refused in words: {name}", r.status_code == 400 and "errbox" in r.get_data(as_text=True), r.status_code)
    r = c.post("/auto/voice/20990101-000000-abcdef/dub", data={"video": str(video)}, headers=H)
    check("a voice-over that does not exist", r.status_code == 400, r.status_code)
    r = c.post(f"/auto/voice/{jid}/dub", data={"video": str(home / "none.mp4")}, headers=H)
    check("a video that does not exist", r.status_code == 400, r.status_code)

    # Russian
    c.post("/lang", data={"back": "/auto/voice"}, headers=H)
    ru = c.get("/auto/voice", headers=H).get_data(as_text=True)
    check("the page in Russian", "Озвучка" in ru and "Наложить на видео" in ru and "Новая озвучка" in ru)
    left = [t for t in ("Put it on a video", "New voice-over", "Make the voice-over", "Captions for a video") if t in
            re.sub(r"<script.*?</script>", "", ru, flags=re.S)]
    check("no English left of the main texts", not left, left)

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
