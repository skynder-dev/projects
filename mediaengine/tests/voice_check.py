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
    sa = vo.ass(cues, 1080, 1920, style="classic")
    check("ASS: the frame size, karaoke words (classic)", "PlayResX: 1080" in sa and "PlayResY: 1920" in sa and "{\\k" in sa)
    sp = vo.ass(cues, 1080, 1920)
    check("ASS: the default style shows each word in color in turn, with the program's font",
          sp.count("Dialogue:") >= len([w for c in cues for w in c["words"]]) and "\\fnMontserrat Black" in sp
          and "{\\k" not in sp, sp[-300:])
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

    def fake_worker(job, work, timeout=3600, on_line=None):
        work.mkdir(parents=True, exist_ok=True)
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

    # a real video (vertical, with sound) and the voice burned onto it
    video = home / "clip.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=540x960:rate=30:duration=2",
                    "-f", "lavfi", "-i", "sine=f=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(video)], check=True)
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
    r = c.post("/api/text/preview", data={"video": str(home / "none.mp4"), "t_text": "x"}, headers=H)
    check("a preview of a missing video: said in words", "error" in (r.get_json() or {}), r.get_json())
    r = c.post("/auto/text/new", data={"video": str(video), "t_text": "x", "t_start": "soon"}, headers=H)
    check("a text time that is not a number: refused in words", r.status_code == 400, r.status_code)

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
    r = c.get(f"/auto/voice/{jid}/edit", headers=H)
    check("a voice-over itself (no video) is not edited here: said in words", r.status_code == 400, r.status_code)

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
    def old_job(key, ref):
        jj = json.loads((d / "job.json").read_text("utf-8"))
        jj["voice"].update(key=key, ref_wav=ref)
        (d / "job.json").write_text(json.dumps(jj), "utf-8")
    old_job("friend", str(home / "MediaEngine-b158" / "assets" / "voice" / "friend_3_1.flac"))       # 3.1, gone now
    c.post(f"/auto/voice/{jid}/retry", headers=H)
    fj = wait(jid)
    check("Try again on a voice this version no longer has: said in words", fj["state"] == "failed"
          and "recording of this voice is missing" in str((fj.get("result") or {}).get("error")), fj.get("result"))
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
    r = c.post("/auto/finish", data={**base_f, "voice": "new", "text": "Hello there, my friend. This is new.",
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
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "speech"}, headers=H)
    sj = wait(next(j["id"] for j in vo.list_jobs(500) if j["id"] not in before))
    check("captions of the video's own speech on the same page", r.status_code == 302 and sj["state"] == "done"
          and (sj.get("result") or {}).get("captions", 0) > 0, sj.get("result"))
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "voice"}, headers=H)
    check("captions of a voice without a voice: refused in words", r.status_code == 400, r.status_code)
    r = c.post("/auto/finish", data={"video": str(video), "voice": "none", "captions": "none"}, headers=H)
    check("nothing to add: refused in words", r.status_code == 400, r.status_code)

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
                        "The words of the voice", "The look", "Make the video") if t in ruf]
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
