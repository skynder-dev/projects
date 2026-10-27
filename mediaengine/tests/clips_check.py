"""Clips from a long video (app/archivist/clips.py, clips_web.py) - without the voice add-on (the words of the speech
are given, as Whisper would give them).

  python tests/clips_check.py <work_dir>

1. Finding: sentences, windows of whole sentences within the chosen length, never overlapping, a question at the
   start ranked above a start in the middle of a thought, speech without stops split.
2. Making (the real FFmpeg): a synthetic 60 s "talking head" video - shot A one face on the right, shot B two faces
   far apart (a podcast's wide shot), shot C three faces, shot D a streamer's camera in a corner of a game - five clips: shot A (the crop follows the face), shot B
   (each face in its own half, one above the other), one across the A|B cut (switched at the cut), shot C (the whole
   picture on blurred edges). Vertical 1080x1920, the length asked, sound,
   captions and the title drawn, copies saved next to the reels. The face finder is the program's YuNet; where
   this OpenCV has none, a stand-in that finds the pictures of the faces (the framing logic is the same).
3. The pages: English and Russian (no English left), a make without ticks refused, deleting a video's job takes its
   made clips' jobs along (the saved files stay).
"""
from __future__ import annotations

import html, json, os, shutil, subprocess, sys, time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHECKS: list[bool] = []


def check(name, ok, detail=None):
    CHECKS.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)


def words_of(text: str, t0: float, wps: float = 2.8) -> tuple[list[dict], float]:
    out, t = [], t0
    for w in text.split():
        d = 0.8 / wps + 0.05 * len(w) / 6
        out.append({"w": w, "s": round(t, 3), "e": round(t + d, 3), "p": 0.95})
        t += 1.0 / wps
    return out, t


def transcript(sents: list[str], t0: float = 0.5, pause: float = 0.35) -> list[dict]:
    words, t = [], t0
    for s in sents:
        w, t = words_of(s, t)
        words += w
        t += pause
    return words


def frame(ff, video: Path, t: float) -> np.ndarray:
    cp = subprocess.run([ff, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(cp.stdout, np.uint8).reshape(1920, 1080, 3).astype(np.float32)


def frame_n(ff, video: Path, n: int) -> np.ndarray:
    """Picture number n of a 1080x1920 video (every picture decoded: exact)."""
    cp = subprocess.run([ff, "-v", "error", "-i", str(video), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(cp.stdout, np.uint8).reshape(1920, 1080, 3).astype(np.float32)


def wait(vo, jid, limit=1200):
    t0 = time.time()
    while time.time() - t0 < limit and vo.read_job(jid)["state"] in ("waiting", "working"):
        time.sleep(1)
    return vo.read_job(jid)


def textured_center(img: np.ndarray, rows: slice) -> float:
    """Where across the picture the face picture is (the columns with detail), 0..1."""
    g = img[rows].mean(axis=2)
    col = g.std(axis=0)
    w = np.clip(col - np.percentile(col, 30), 0, None)
    return float((w * np.arange(len(w))).sum() / max(1e-6, w.sum()) / len(w))


class StandInFaces:
    """Finds the face pictures of the synthetic video (detail on a flat background) - only where OpenCV has no face
    finder of its own; the real one is checked on Windows."""
    kind, width = "stand-in", 960

    def find(self, bgr):
        import cv2
        return self.detectMultiScale(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))

    def detectMultiScale(self, gray, scaleFactor=1.1, minNeighbors=5, minSize=(0, 0)):
        g = gray.astype(np.float32)
        h, w = g.shape

        def runs(r0, r1):
            busy = g[int(h * r0):int(h * r1)].std(axis=0) > 12
            out, x = [], 0
            while x < w:
                if busy[x]:
                    x0 = x
                    while x < w and busy[x]:
                        x += 1
                    if x - x0 >= 20:
                        out.append((x0, x))
                x += 1
            return out
        found = [(x0 + ((x1 - x0) - int((x1 - x0) * 0.5)) // 2, int(h * 0.3), int((x1 - x0) * 0.5), int((x1 - x0) * 0.5))
                 for x0, x1 in runs(0.3, 0.6)]
        for x0, x1 in runs(0.04, 0.28):               # (a small camera picture near the top: only where nothing is below)
            if all(x1 <= f[0] - f[2] or x0 >= f[0] + 2 * f[2] for f in found):
                fw = int((x1 - x0) * 0.5)
                found.append((x0 + (x1 - x0 - fw) // 2, int(h * 0.04), fw, fw))
        return tuple(found)


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
    from archivist import clips as cl, voice as vo
    from archivist.web import create_app
    from i18n_coverage import english_left, page_texts
    from media_measure import ffmpeg_exe
    ff = ffmpeg_exe()

    # ---------------------------------------------------------------- 1. finding
    sents = (["And then we went back to the office."] + ["We talked about the plan for the year."] * 2
             + ["Why do people never save money?", "Because nobody shows them how it works.",
                "The secret is simple: you pay yourself first, every month, 10 percent.", "It sounds boring but it works."]
             + ["Then there was lunch and some more talking."] * 6
             + ["And the next part is about the team.", "We had four people and a lot of work."] * 3)
    words = transcript(sents)
    ss = cl.sentences(words)
    check("finding: sentences end at their stops", len(ss) == len(sents) and ss[3]["text"] == "Why do people never save money?",
          [s["text"] for s in ss[:5]])
    found = cl.find_candidates(words, None, 15, 30)
    ok_len = all(15 <= c["e"] - c["s"] <= 30 for c in found)
    over = max((min(a["e"], b["e"]) - max(a["s"], b["s"]) for i, a in enumerate(found) for b in found[i + 1:]), default=0)
    starts = {round(s["s"] - 0.15, 2) for s in ss} | {0.0}
    check("finding: whole sentences within the length, never overlapping", found and ok_len and over <= 1.0
          and all(any(abs(c["s"] - x) < 0.02 for x in starts) for c in found), (len(found), ok_len, over))
    q = next((c for c in found if c["first"].startswith("Why do people")), None)
    check("finding: the question with strong words is the likeliest clip", q is not None and found[0] is q
          and "a question at the start" in q["why"], [(c["first"][:30], c["score"]) for c in found[:4]])
    jw = transcript(["Welcome back to the show, everybody.", "Thanks so much for joining us today.",
                     "This episode is sponsored by Shopwise, use code SAVE for 20 percent off.", "Link in the description.",
                     "We talked about the plan for the year."] * 3
                    + ["How do you get the first thousand people?", "You talk to every one of them yourself.",
                       "Nobody tells you that, but it is the whole secret.", "We did it for a year."] + ["We talked about the plan for the year."] * 6)
    jf = cl.find_candidates(jw, None, 15, 30)
    check("finding: greetings, thanks and adverts make a clip unlikely", jf and jf[0]["first"].startswith("How do you get")
          and all(c["score"] < 30 for c in jf if "sponsored" in c["text"] or "Welcome back" in c["first"]),
          [(c["first"][:30], c["score"]) for c in jf[:4]])
    plain = ["Давайте пройдёмся по коду.", "You can use the code from the last example.", "Спонсором турнира был банк.",
             "Мы подписывали контракт.", "I don't subscribe to that theory.", "Follow me on this one.", "До встречи с ним я жил иначе."]
    check("finding: ordinary speech is not taken for greetings or adverts", not any(
        cl._SMALLTALK.search(x.lower()) or cl._AD.search(x.lower()) for x in plain),
          [x for x in plain if cl._SMALLTALK.search(x.lower()) or cl._AD.search(x.lower())])
    lw = transcript(["We talked about the plan for the year."] * 8 + ["He fell off the chair (laughs) and we all laughed.",
                                                                     "Then we went home."] + ["We talked about the plan for the year."] * 8)
    lf = cl.find_candidates(lw, None, 15, 30)
    check("finding: laughter makes a clip likelier", lf and "laughter" in lf[0]["why"] and "(laughs)" in lf[0]["text"],
          [(c["first"][:30], c["why"]) for c in lf[:3]])
    runon = transcript([" ".join(["word"] * 120)], pause=0)              # speech written without a single stop
    pieces = cl.sentences(runon)
    check("finding: speech without stops is split into pieces", len(pieces) >= 2 and all(p["e"] - p["s"] <= 20.5 for p in pieces),
          [(p["s"], p["e"]) for p in pieces])

    # ---------------------------------------------------------------- 2. making
    src = work / "Подкаст выпуск 1.mp4"
    face = HERE / "assets" / "face_pd.jpg"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x405060:s=1920x1080:r=30:d=20",
                    "-f", "lavfi", "-i", "color=c=0xa08060:s=1920x1080:r=30:d=20",
                    "-f", "lavfi", "-i", "color=c=0x305030:s=1920x1080:r=30:d=20", "-loop", "1", "-i", str(face),
                    "-f", "lavfi", "-i", "sine=f=220:d=80:sample_rate=48000",
                    "-f", "lavfi", "-i", "color=c=0x202830:s=1920x1080:r=30:d=20",
                    # (places on multiples of 4 px: the 480 px wide look at the clip sees every copy alike)
                    "-filter_complex", "[3:v]scale=520:600,split=6[f1][f2][f3][f4][f5][f6];[0:v][f1]overlay=1252:240:shortest=1[a];"
                                       "[1:v][f2]overlay=60:240:shortest=1[b0];[b0][f3]overlay=1300:240:shortest=1[b];"
                                       "[2:v][f4]overlay=32:240:shortest=1[c0];[c0][f5]overlay=700:240:shortest=1[c1];"
                                       "[c1][f6]overlay=1368:240:shortest=1[c];"
                                       # shot D: a "game" (a box running across) with the streamer's camera top left
                                       "[5:v]drawbox=x='mod(t*300,1700)':y=700:w=160:h=160:color=white:t=fill[g0];"
                                       "[3:v]scale=240:276[fc];[g0][fc]overlay=40:40:shortest=1[dd];"
                                       "[a][b][c][dd]concat=n=4:v=1:a=0,format=yuv420p[v]",
                    "-map", "[v]", "-map", "4:a", "-t", "80", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac",
                    str(src)], check=True)
    real = cl.face_finder() is not None
    if os.name == "nt":
        check("making: the face finder is YuNet, the program's own (Windows)", getattr(cl.face_finder(), "kind", "") == "yunet",
              getattr(cl.face_finder(), "kind", None))
    if not real:
        print("NOTE this OpenCV has no face finder: a stand-in finds the face pictures", flush=True)
        cl._FACES["f"] = StandInFaces()
    talk = transcript(["Hello and welcome to the show.", "Today we talk about money and how to keep it.",
                       "Why do people never save money?", "Because nobody shows them how.", "Here is the secret.",
                       "Pay yourself first.", "Every month, before anything else.", "It sounds boring.", "But it works.",
                       "Now the second part.", "Two of us are here today.", "We both tried it for a year.",
                       "And it changed a lot.", "Now three of us.", "We talk about the next year.", "And what comes after it.",
                       "Thank you for listening."], t0=0.4, pause=0.6)
    vo.JOBS.mkdir(parents=True, exist_ok=True)
    fid = vo._new_id()
    d = vo.JOBS / fid
    d.mkdir()
    job = {"kind": "clips_find", "source": str(src), "length": "short", "language": "en", "duration": 80.0, "title": src.name,
           "id": fid, "created_at": "2026-10-27T10:00:00", "created_ns": time.time_ns()}
    (d / "job.json").write_text(json.dumps(job), "utf-8")
    res = cl.save_found(d, job, talk, [], "en")
    (d / "result.json").write_text(json.dumps(res), "utf-8")
    check("making: the found clips are kept with the job", res.get("ok") and cl.candidates(fid) and cl.words_of(fid), res)
    chosen = [{"s": 1.0, "e": 17.0, "first": "Hello and welcome to the show."},
              {"s": 22.0, "e": 38.0, "first": "Two of us are here today."},
              {"s": 12.0, "e": 28.0, "first": "Pay yourself first."},
              {"s": 42.0, "e": 58.0, "first": "Now three of us."},
              {"s": 62.0, "e": 78.0, "first": "Thank you for listening."}]
    mid = cl.new_make(fid, chosen, "vertical", "face", True, {"style": "pop", "color": "yellow"}, True)
    mj = wait(vo, mid)
    mr = mj.get("result") or {}
    made = mr.get("clips") or []
    check("making: five clips made", mj["state"] == "done" and len(made) == 5, (mj["state"], mr.get("error")))
    if len(made) == 5:
        from archivist import auto_edit as ae
        good = True
        for c, x in zip(chosen, made):
            info = ae._probe(d.parent / mid / x["file"])
            vs = next(s for s in info["streams"] if s["codec_type"] == "video")
            dur = float(info["format"]["duration"])
            good &= (int(vs["width"]), int(vs["height"])) == (1080, 1920) and abs(dur - (c["e"] - c["s"])) <= 0.35 \
                and any(s["codec_type"] == "audio" for s in info["streams"])
        check("making: vertical 1080x1920, the length asked, with sound", good, made)
        m1, m2, m3, m4, m5 = (vo.JOBS / mid / x["file"] for x in made)
        f1 = frame(ff, m1, 6.0)
        c1 = textured_center(f1, slice(600, 1300))
        check("making: the crop follows the face (shot with one face on the right)", made[0]["layouts"] == ["crop"]
              and 0.35 <= c1 <= 0.65, (made[0]["plan"], round(c1, 3)))
        f2 = frame(ff, m2, 6.0)
        up, down = textured_center(f2, slice(120, 840)), textured_center(f2, slice(1080, 1800))
        busy = lambda img, rows: float(img[rows].std(axis=1).mean())
        check("making: two people apart - each face in its own half, one above the other", made[1]["layouts"] == ["split"]
              and 0.3 <= up <= 0.7 and 0.3 <= down <= 0.7 and busy(f2, slice(120, 840)) > 8 and busy(f2, slice(1080, 1800)) > 8,
              (made[1]["plan"], round(up, 3), round(down, 3)))
        f3a, f3b = frame(ff, m3, 3.0), frame(ff, m3, 12.0)
        c3 = textured_center(f3a, slice(600, 1300))
        d3 = textured_center(f3b, slice(1080, 1800))
        check("making: a clip across the cut switches at the cut", made[2]["shots"] == 2 and made[2]["layouts"] == ["crop", "split"]
              and 0.35 <= c3 <= 0.65 and 0.3 <= d3 <= 0.7 and busy(f3b, slice(1080, 1800)) > 8, (made[2]["plan"], round(c3, 3), round(d3, 3)))
        # exactly at the cut (source 20.0 s = picture 240 of the clip from 12.0 s): the last picture of the shot before
        # still in its crop, the first of the next already split - no picture in between shows a third framing
        b239, b240 = busy(frame_n(ff, m3, 239), slice(150, 420)), busy(frame_n(ff, m3, 240), slice(150, 420))
        check("making: the framing changes exactly at the cut", b239 < 3 and b240 > 8, (round(b239, 2), round(b240, 2), made[2]["plan"]))
        f4 = frame(ff, m4, 6.0)
        top, middle = busy(f4, slice(100, 500)), busy(f4, slice(700, 1200))
        check("making: three people are shown whole on blurred edges", made[3]["layouts"] == ["fit"] and top < 0.5 * middle,
              (made[3]["plan"], round(top, 1), round(middle, 1)))
        yellow = lambda img: int(((img[..., 0] > 200) & (img[..., 1] > 160) & (img[..., 2] < 110)).sum())
        cap = max(yellow(frame(ff, m1, t)[1100:1750]) for t in (3.4, 4.6, 5.8, 7.0))    # (after the title, under the face)
        mid_cap = max(yellow(frame(ff, m2, t)[760:1160]) for t in (2.2, 3.4, 4.6, 5.8, 7.0))
        check("making: two faces one above the other - the captions between them", mid_cap > 100, mid_cap)
        check("making: captions with the words are drawn", made[0]["captions"] > 3 and cap > 200, (made[0]["captions"], cap))
        t_top = frame(ff, m1, 1.2)[150:500]
        t_late = frame(ff, m1, 8.0)[150:500]
        check("making: the first sentence as a title at the top for 3 s", float(np.abs(t_top - t_late).mean()) > 3.0,
              float(np.abs(t_top - t_late).mean()))
        saved = [Path(x["saved"]) for x in made if x.get("saved")]
        f5 = frame(ff, m5, 6.0)
        th5 = int(1920 * 0.42) // 2 * 2
        check("making: a streamer's camera in a corner - the camera above, the game below", made[4]["layouts"] == ["cam"]
              and 0.3 <= textured_center(f5, slice(60, th5 - 60)) <= 0.7 and busy(f5, slice(60, th5 - 60)) > 8,
              (made[4]["plan"], round(textured_center(f5, slice(60, th5 - 60)), 3)))
        check("making: copies saved next to the reels, named by their words", len(saved) == 5 and all(p.is_file() for p in saved)
              and saved[0].parent.name.startswith("Подкаст выпуск 1 - ") and saved[0].name.startswith("01 - Hello and welcome"),
              [str(p) for p in saved])
        # made again (after a restart, Stop or Try again): the clips made are kept, nothing is made or saved twice
        folder = saved[0].parent if saved else None
        before = sorted(x.name for x in folder.iterdir()) if folder else []
        mjob = json.loads((vo.JOBS / mid / "job.json").read_text("utf-8"))
        t1 = time.time()
        again = cl._do_make(vo.JOBS / mid, mjob)
        check("making: made again, the clips made are kept (nothing made or saved twice)", again.get("ok") and len(again["clips"]) == 5
              and time.time() - t1 < 20 and sorted(x.name for x in folder.iterdir()) == before, (again.get("error"), time.time() - t1))
        # square and as filmed
        msq = cl.new_make(fid, [dict(chosen[0], title="My own title")], "square", "face", False, {}, False)
        mor = cl.new_make(fid, [chosen[0]], "original", "face", False, {}, False)
        sq, orr = wait(vo, msq), wait(vo, mor)
        csq = (sq.get("result") or {}).get("clips") or [{}]
        cor = (orr.get("result") or {}).get("clips") or [{}]
        fsq = None

        def sq_frame(t):
            cp = subprocess.run([ff, "-v", "error", "-ss", str(t), "-i", str(vo.JOBS / msq / csq[0]["file"]), "-frames:v", "1",
                                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
            return np.frombuffer(cp.stdout, np.uint8).reshape(1080, 1080, 3).astype(np.float32)
        if csq[0].get("file"):
            fsq = sq_frame(6)
            own = float(np.abs(sq_frame(1.2)[40:260] - fsq[40:260]).mean())
            check("making: a clip's own title at the top (without the first-sentence choice)", own > 3.0, own)
        check("making: square 1080x1080 (the face kept) and as filmed 1920x1080",
              (csq[0].get("width"), csq[0].get("height")) == (1080, 1080) and (cor[0].get("width"), cor[0].get("height")) == (1920, 1080)
              and fsq is not None and 0.3 <= textured_center(fsq, slice(300, 800)) <= 0.7, (sq.get("result"), orr.get("result")))

    # someone walking across the picture: the crop goes with them (a still crop would lose them)
    walk = work / "walk.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x405060:s=1920x1080:r=30:d=18", "-loop", "1", "-i", str(face),
                    "-f", "lavfi", "-i", "sine=f=220:d=18", "-filter_complex",
                    "[1:v]scale=360:415[f];[0:v][f]overlay=x='80+80*t':y=300:shortest=1,format=yuv420p[v]",
                    "-map", "[v]", "-map", "2:a", "-t", "18", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac",
                    str(walk)], check=True)
    wid = vo._new_id()
    (vo.JOBS / wid).mkdir()
    wjob = dict(job, id=wid, source=str(walk), duration=18.0, title=walk.name, created_ns=time.time_ns())
    (vo.JOBS / wid / "job.json").write_text(json.dumps(wjob), "utf-8")
    wres = cl.save_found(vo.JOBS / wid, wjob, transcript(["We walk along the beach.", "The water is warm today.", "Look at those waves over there.",
                                                                "Why is nobody else here?", "It is still early in the morning.",
                                                                "We will come back tomorrow."], t0=0.4, pause=1.2), [], "en")
    (vo.JOBS / wid / "result.json").write_text(json.dumps(wres), "utf-8")
    check("making: a walk's clips found", wres.get("ok"), wres)
    wm = wait(vo, cl.new_make(wid, [{"s": 0.5, "e": 16.5, "first": "We walk along the beach."}], "vertical", "face", False, {}, False))
    wc = ((wm.get("result") or {}).get("clips") or [{}])[0]
    wpos = [round(textured_center(frame(ff, vo.JOBS / wm["id"] / wc["file"], t), slice(600, 1200)), 3) for t in (1.0, 8.0, 15.0)] \
        if wc.get("file") else []
    check("making: someone walking across - the crop goes with them", wm["state"] == "done" and wc.get("layouts") == ["crop"]
          and bool(wc["plan"][0].get("path")) and len(wpos) == 3 and all(0.25 <= x <= 0.75 for x in wpos),
          (wm["state"], wpos, (wc.get("plan") or [{}])[0].get("path", "")[:6] if wc.get("plan") else wm.get("result")))

    # a long walk (a pan of many points) in a clip of many shots: FFmpeg reads the picture's expressions (they are flat
    # sums - nested ones stop at about 100 brackets); two people found in turns are no walk (no pan between them)
    many = []
    for k in range(150):
        many.append({"s": round(k * 0.4, 6), "e": round(k * 0.4 + 0.4, 6), "layout": "crop", "cx": (k * 37 % 100) / 100})
    many[70]["path"] = [[28.0 + i * 0.003, 0.2 + 0.6 * i / 119] for i in range(120)]
    many[-1]["e"] = 999.0
    g_many, _, _ = cl._graph({"shots": many}, {"w": 1920, "h": 1080, "sar": 1.0}, (540, 960))
    rc_many = subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=61", "-filter_complex",
                              g_many + ";[pv]format=yuv420p[v]", "-map", "[v]", "-f", "null", "-"], capture_output=True, text=True)
    turns = [(i / 3, 0.3 if (i // 4) % 2 else 0.7) for i in range(40)]
    check("making: a long walk in a clip of 150 shots is made; two people found in turns are not panned between",
          rc_many.returncode == 0 and cl._follow(turns, 0.316) is None, (rc_many.returncode, rc_many.stderr[-300:]))

    # two people side by side, close: both in the picture, as big as they fit (not a crop cutting one of them)
    pair = work / "pair.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x405060:s=1920x1080:r=30:d=18", "-loop", "1", "-i", str(face),
                    "-f", "lavfi", "-i", "sine=f=220:d=18", "-filter_complex",
                    "[1:v]scale=300:346,split=2[p1][p2];[0:v][p1]overlay=620:300:shortest=1[q];[q][p2]overlay=1000:300:shortest=1,"
                    "format=yuv420p[v]", "-map", "[v]", "-map", "2:a", "-t", "18", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-c:a", "aac", str(pair)], check=True)
    pid = vo._new_id()
    (vo.JOBS / pid).mkdir()
    pjob = dict(wjob, id=pid, source=str(pair), title=pair.name, created_ns=time.time_ns())
    (vo.JOBS / pid / "job.json").write_text(json.dumps(pjob), "utf-8")
    (vo.JOBS / pid / "result.json").write_text(json.dumps(cl.save_found(vo.JOBS / pid, pjob, transcript(
        ["We walk along the beach.", "The water is warm today.", "Look at those waves over there.", "Why is nobody else here?",
         "It is still early in the morning.", "We will come back tomorrow."], t0=0.4, pause=1.2), [], "en")), "utf-8")
    pm = wait(vo, cl.new_make(pid, [{"s": 0.5, "e": 16.5, "first": "We walk along the beach."}], "vertical", "face", False, {}, False))
    pc = ((pm.get("result") or {}).get("clips") or [{}])[0]
    if pc.get("file"):
        fp = frame(ff, vo.JOBS / pm["id"] / pc["file"], 8.0)
        cols = fp[600:1150].mean(axis=2).std(axis=0)
        detail = int((cols > 12).sum())                  # (columns with a face in them: two faces shown big)
        halves = (float(fp[600:1150, :540].std()), float(fp[600:1150, 540:].std()))
    else:
        detail, halves = 0, (0.0, 0.0)
    check("making: two people side by side - both in the picture, as big as they fit", pm["state"] == "done"
          and pc.get("layouts") == ["fit"] and 0.3 < float(pc["plan"][0].get("box", {}).get("w", 1)) < 0.6 and detail > 600
          and min(halves) > 8, (pm["state"], pc.get("plan") or pm.get("result"), detail, halves))

    # ---------------------------------------------------------------- 3. the pages
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    with app.test_client() as c:
        home = c.get("/auto/clips", headers=H)
        page = c.get(f"/auto/clips/{fid}", headers=H)
        body = page.data.decode("utf-8", "replace")
        check("pages: the clips page and a video's clips", home.status_code == 200 and b"Find clips" in home.data
              and page.status_code == 200 and body.count("name='pick'") == len(cl.candidates(fid)) and "/clip/1.mp4" in body,
              (home.status_code, page.status_code))
        cid0 = cl.candidates(fid)[0]["id"]
        th = c.get(f"/auto/clips/{fid}/thumb/{cid0}.jpg", headers=H)
        th_ok = th.status_code == 200 and th.mimetype == "image/jpeg" and len(th.data) > 500
        th.close()                                       # (Windows: an open picture could not be deleted later)
        bad = c.get(f"/auto/clips/{fid}/thumb/x1.jpg", headers=H)
        check("pages: a small picture of each found clip", th_ok and f"/thumb/{cid0}.jpg" in body and bad.status_code == 404, th.status_code)
        st = c.get("/api/clips/status", query_string={"ids": f"{mid},{fid},bad"}, headers=H).get_json()
        check("pages: how far the jobs are, for the page to ask", st.get(mid, {}).get("state") == "done" and st.get(fid, {}).get("state") == "done"
              and "bad" not in st, st)
        r = c.post(f"/auto/clips/{fid}/length", data={"length": "medium"}, headers=H)
        mids = cl.candidates(fid)
        check("pages: another length found again from the words heard (no listening)", r.status_code == 302 and mids
              and all(30 <= x["e"] - x["s"] <= 60 for x in mids) and vo.read_job(fid)["state"] == "done", (r.status_code, mids[:2]))
        c.post(f"/auto/clips/{fid}/length", data={"length": "short"}, headers=H)
        none = c.post(f"/auto/clips/{fid}/make", data={"format": "vertical"}, headers=H)
        check("pages: making without a tick is refused", none.status_code == 400 and b"Tick the clips" in none.data, none.status_code)
        top = c.post(f"/auto/clips/{fid}/make", data={"format": "vertical", "framing": "face", "top": "5"}, headers=H)
        tj = next((j for j in vo.list_jobs() if j.get("kind") == "clips_make" and j.get("find") == fid), {})
        want = sorted(x["s"] for x in cl.candidates(fid)[:5])
        check("pages: \"Make the 5 likeliest\" makes the first five of the list without ticks", top.status_code == 302
              and sorted(round(x["s"], 2) for x in tj.get("clips") or []) == sorted(round(x, 2) for x in want) and len(want) >= 1,
              (top.status_code, tj.get("clips"), want))
        if tj.get("id"):
            c.post(f"/auto/clips/{tj['id']}/stop", data={"back": f"/auto/clips/{fid}"}, headers=H)
            wait(vo, tj["id"], 120)
        nf = c.post("/auto/clips/new", data={"path": str(work / "nope.mp4")}, headers=H)
        check("pages: finding is refused clearly without the add-on or the file", nf.status_code == 400, nf.status_code)
        c.post("/lang", data={"lang": "ru"}, headers=H)
        left = []
        for u in ("/auto/clips", f"/auto/clips/{fid}"):
            ru = c.get(u, headers=H).data.decode("utf-8", "replace")
            left += [t.strip()[:80] for t in page_texts(ru) if english_left(html.unescape(t))]
        c.post("/lang", data={"lang": "en"}, headers=H)
        check("pages: in Russian, no English left", not left, left[:10])
        saved_before = [Path(x["saved"]) for x in made if x.get("saved")]
        r = c.post(f"/auto/clips/{fid}/delete", data={"back": "/auto/clips"}, headers=H)
        check("pages: deleting a video's clips job takes its made clips' jobs along, the saved files stay",
              r.status_code == 302 and not (vo.JOBS / fid).exists() and not (vo.JOBS / mid).exists()
              and all(p.is_file() for p in saved_before), r.status_code)
    print(json.dumps({"passed": sum(CHECKS), "total": len(CHECKS)}))
    return 0 if all(CHECKS) else 1


if __name__ == "__main__":
    import faulthandler
    faulthandler.dump_traceback_later(2400, exit=True)
    sys.exit(main())
