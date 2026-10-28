"""Cartoon Studio: the 2D engine and its pages, without the voice add-on (the voices are checked in
voice_addon_check.py). Characters drawn the same every time, scripts checked, a short film in both formats (its
length, picture, sound, captions, mouths moving), the example film's scenes, the pages in both languages.

  python tests/cartoon_check.py <work_dir>        -> JSON with passed / total; exit 1 when a check fails
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"), flush=True)


SHORT = {
    "title": "Test film", "language": "en", "format": "vertical", "narrator": "kate",
    "cast": {"kate": {"name": "Kate", "role": "narrator", "female": True},
             "rick": {"name": "Rick", "role": "contractor boss", "female": False}},
    "scenes": [
        {"bg": "office", "cast": ["rick"], "visual": {"kind": "contract", "price": "$4 800 000", "price_at": 0, "stamp": "APPROVED",
                                                       "stamp_at": 1},
         "lines": [{"who": "kate", "text": "The price is four times higher."},
                   {"who": "rick", "pose": "count", "emotion": "sly", "text": "And it is approved!"}]},
        {"bg": "board", "cast": [], "visual": {"kind": "bars", "values": [1.2, 4.8], "labels": ["fair", "paid"], "unit": "M", "at": 0},
         "lines": [{"who": "kate", "text": "Taxpayers pay the difference."}]},
    ],
}


def probe(ff: str, p: Path) -> dict:
    """The program's own probe (FFmpeg only: a Windows MediaEngine has no ffprobe)."""
    from archivist import auto_edit as ae
    try:
        return ae._probe(p) or {}
    except Exception:
        return {}


def frame(ff: str, p: Path, t: float, w: int, h: int) -> np.ndarray:
    cp = subprocess.run([ff, "-v", "error", "-ss", f"{t:.3f}", "-i", str(p), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        capture_output=True)
    return np.frombuffer(cp.stdout, np.uint8).reshape(h, w, 3).astype(np.float32)


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    os.environ.setdefault("MEDIAENGINE_NO_BROWSER", "1")
    os.environ.setdefault("MEDIAENGINE_UPDATES", "off")
    sys.path.insert(0, str(ROOT / "app"))
    sys.path.insert(0, str(HERE))
    from archivist import voice as vo
    from archivist.cartoon import chars as ch, film as F, stories
    from archivist.cartoon.draw import Canvas
    ff = vo._ffmpeg()

    # 1. characters: the same name -> the same character, drawn identically; poses and feelings change the picture
    a, b = ch.make("Mayor Grant", "mayor"), ch.make("Mayor Grant", "mayor")
    c1, c2 = Canvas(540, 960, 1080), Canvas(540, 960, 1080)
    for cv in (c1, c2):
        cv.fill("#eef2f6")
        ch.draw(cv, a if cv is c1 else b, 540, 1700, 1.2, 1, "point", emotion="happy", mouth=0.5, t=1.0)
    c3 = Canvas(540, 960, 1080)
    c3.fill("#eef2f6")
    ch.draw(c3, a, 540, 1700, 1.2, 1, "cross", emotion="angry", mouth=0.0, t=1.0)
    check("characters: the same name is the same character, drawn the same every time", a == b and np.array_equal(c1.img, c2.img)
          and float(np.abs(c1.img.astype(np.float32) - c3.img.astype(np.float32)).mean()) > 1.0)
    check("characters: a man's role gets a suit, a worker's a vest and a hard hat",
          ch.make("X", "official")["outfit"] in ("suit", "dress", "blazer") and ch.make("Y", "road worker")["hat"] == "hardhat")

    # 2. scripts: refused clearly when empty; unknown parts made safe
    bad = []
    for sc in ({}, {"scenes": []}, {"scenes": [{"lines": []}], "cast": {}}):
        try:
            F.check_script(sc)
        except F.FilmError as exc:
            bad.append(str(exc))
    odd = F.check_script({"cast": {"Kate!": {"name": "Kate"}}, "scenes": [{"bg": "moon", "lines": [{"who": "nobody", "text": "Hi.",
                                                                                                  "pose": "dance", "emotion": "x"}]}]})
    check("scripts: empty ones refused with a reason; an unknown background, speaker, pose or feeling made safe",
          len(bad) == 3 and odd["scenes"][0]["bg"] == "city" and odd["scenes"][0]["lines"][0]["who"] == "kate"
          and odd["scenes"][0]["lines"][0]["pose"] is None, (bad, odd["scenes"]))

    # 3. a short film, tall: length, picture, sound, captions, mouths
    tl = F.timeline(F.check_script(SHORT))
    out = work / "short_v.mp4"
    t0 = time.time()
    r = F.render(SHORT, out, work / "rv", None, {"style": "pop", "color": "yellow", "position": "middle"})
    took = time.time() - t0
    info = probe(ff, out)
    vs = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    dur = float((info.get("format") or {}).get("duration") or 0)
    check("film: a tall 1080x1920 MP4 of the script's length, with sound", (vs.get("width"), vs.get("height")) == (1080, 1920)
          and abs(dur - tl["seconds"]) < 0.4 and any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
          (vs.get("width"), vs.get("height"), dur, tl["seconds"]))
    print(f"NOTE {tl['seconds']:.1f} s of film drawn in {took:.1f} s", flush=True)
    l0 = tl["scenes"][0]["lines"][0]
    f_talk = frame(ff, out, (l0["s"] + l0["e"]) / 2, 1080, 1920)
    yellow = int(((f_talk[..., 0] > 200) & (f_talk[..., 1] > 160) & (f_talk[..., 2] < 110)).sum())
    check("film: captions of the words drawn in the colour chosen", yellow > 300, yellow)
    mouths = F.mouth_tracks(tl)
    m0 = mouths.get("0.1") or []
    check("film: the speaker's mouth opens and closes along the words", m0 and max(m0) > 0.5 and min(m0) < 0.1, (max(m0 or [0]), min(m0 or [1])))
    f_end = frame(ff, out, tl["scenes"][1]["s"] + 1.5, 1080, 1920)
    check("film: the second scene (a chart on the board) is drawn", float(f_end.std()) > 20 and float(np.abs(f_end - f_talk).mean()) > 10,
          (float(f_end.std()), float(np.abs(f_end - f_talk).mean())))
    # a wide one
    wide = copy.deepcopy(SHORT)
    wide["format"] = "horizontal"
    out_w = work / "short_h.mp4"
    F.render(wide, out_w, work / "rh", None, None)
    vs2 = next((s for s in probe(ff, out_w).get("streams", []) if s.get("codec_type") == "video"), {})
    check("film: a wide 1920x1080 MP4, without captions when none are asked", (vs2.get("width"), vs2.get("height")) == (1920, 1080), vs2)

    # 4. the example film: every scene of it draws (one picture each), its length is 60-120 s without voices
    film = F.check_script(stories.ROAD_CONTRACT)
    tl2 = F.timeline(film)
    errs = []
    for fmt in ("vertical", "horizontal"):
        W, H = F.FORMATS[fmt]
        cv = Canvas(W // 2, H // 2, 1920 if W > H else 1080)
        for i, s in enumerate(tl2["scenes"]):
            try:
                F.draw_frame(cv, film, s, (s["s"] + s["e"]) / 2, {})
                if float(cv.img.std()) < 8:
                    errs.append(f"{fmt} scene {i + 1}: blank")
            except Exception as exc:
                errs.append(f"{fmt} scene {i + 1}: {type(exc).__name__}: {exc}")
    check("example: every scene of 'How a City Loses Millions' draws in both formats", not errs, errs)
    enter = [x["enter"] for x in tl2["scenes"]]
    s3 = tl2["scenes"][2]
    W, H = F.FORMATS["vertical"]
    early, late = Canvas(W // 4, H // 4, 1080), Canvas(W // 4, H // 4, 1080)
    F.draw_frame(early, film, s3, s3["s"] + 0.05, {})
    F.draw_frame(late, film, s3, s3["s"] + 1.2, {})
    lower = slice(int(H // 4 * 0.6), H // 4)
    moved = float(np.abs(early.img[lower].astype(np.int16) - late.img[lower].astype(np.int16)).mean())
    s5 = tl2["scenes"][4]
    l_up = next(x for x in s5["lines"] if x.get("pose") == "point_up")
    grow = F._pose_mix(s5, l_up["who"], l_up["s"] + 0.1, 0)
    held = F._pose_mix(s5, l_up["who"], l_up["s"] + 1.0, 0)
    check("animation: a character not in the scene before walks in (the first scene's people are just there); a new "
          "gesture grows out of the one before; a speaker's arms move a little",
          enter[0] == [] and enter[2] == ["ed"] and moved > 3 and grow[1] == "point_up" and 0 < grow[2] < 1
          and held[0] == "point_up", (enter[:4], moved, grow, held))
    from archivist.cartoon.voices import spoken
    sp = (spoken("The city pays $4.8M, the crew gets $300K - 30% of it.", "en"),
          spoken("Город платит 480 млн ₽, бригада получает 1,2 млн. Это $300 и 21 млн рублей.", "ru"))
    sp2 = (spoken("$300 million, $5 each; it cost $1,000, then 2,000 laptops in 2024.", "en"),
           spoken("$5 тысяч, €3 тысячи, 1% и 21%, в 2024 году.", "ru"))
    check("voices: money written short is said in full (dollars, millions, roubles, percent), nothing else touched",
          sp[0] == "The city pays 4.8 million dollars, the crew gets 300 thousand dollars - 30 percent of it."
          and sp[1] == "Город платит 480 миллионов рублей, бригада получает 1,2 миллиона. Это 300 долларов и 21 миллион рублей."
          and sp2[0] == "300 million dollars, 5 dollars each; it cost 1,000 dollars, then 2,000 laptops in 2024."
          and sp2[1] == "5 тысяч долларов, 3 тысячи евро, 1 процент и 21 процент, в 2024 году.", (sp, sp2))
    a_, b_ = np.zeros((96, 54, 3), np.uint8), np.full((96, 54, 3), 200, np.uint8)
    tr = {k: F.transition(a_, b_, 0.15, same, i) for k, same, i in (("fade", True, 2), ("slide", False, 1), ("iris", False, 2))}
    check("transitions: a cross-fade in the same place; a slide or an opening circle to another place; then the new scene",
          abs(float(tr["fade"].mean()) - 100) < 10 and float(tr["slide"][:, :10].mean()) < 5 and float(tr["slide"][:, -10:].mean()) > 195
          and float(tr["iris"][48, 27].mean()) > 195 and float(tr["iris"][0, 0].mean()) < 5
          and np.array_equal(F.transition(a_, b_, 1.0, False, 1), b_), {k: float(v.mean()) for k, v in tr.items()})
    pv = Tx_ = None
    from archivist.cartoon import textscript as Tx_
    pv = Tx_.parse("Title: X\nNarrator: Kate (woman)\n\n== Board | percent: 30% kickback\nKate: Thirty percent.\n\n"
                   "== Paper | timeline: 2021 contract; 2022 repair; 2023 holes back\nKate: a\nKate: b\nKate: c\n")
    pfilm = F.check_script(pv)
    ptl = F.timeline(pfilm)
    drawn = []
    for s_ in ptl["scenes"]:
        cvp = Canvas(270, 480, 1080)
        F.draw_frame(cvp, pfilm, s_, s_["e"] - 0.3, {})
        drawn.append(float(cvp.img.std()))
    check("pictures: a share of a whole (a pie) and a timeline, read from a story and drawn",
          pv["scenes"][0]["visual"]["kind"] == "percent" and pv["scenes"][0]["visual"]["value"] == 30
          and [x["when"] for x in pv["scenes"][1]["visual"]["steps"]] == ["2021", "2022", "2023"]
          and pv["scenes"][1]["visual"]["steps"][2].get("bad") and all(d > 15 for d in drawn)
          and Tx_.to_text(pv).count("percent: 30% kickback") == 1, (pv["scenes"], drawn))
    from archivist.cartoon import music as Mu
    beds = {m: Mu.made(12, m) for m in Mu.MOODS}
    v = np.zeros(48000 * 12, np.float32)
    v[48000 * 4:48000 * 7] = 0.3 * np.sin(np.arange(48000 * 3) / 48000 * 2 * np.pi * 200)
    d = Mu.duck(Mu.made(12), v)
    rms = lambda a: float(np.sqrt(np.mean(a ** 2)))     # noqa: E731
    music_film = work / "music_v.mp4"
    F.render(SHORT, music_film, work / "rm", None, None, music={"kind": "made", "mood": "suspense"})
    quiet = c_ = None
    try:
        raw = subprocess.run([ff, "-v", "error", "-i", str(music_film), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                             capture_output=True).stdout
        snd = np.frombuffer(raw, np.float32)
        quiet = rms(snd[-48000:-24000]) if len(snd) > 48000 else 0.0      # (the scene's air at the end: music only)
    except Exception as exc:
        c_ = exc
    check("music: the program's own bed in three moods, quiet, lowered under a voice, mixed into a film",
          all(len(b) == 12 * 48000 and 0.4 < float(np.abs(b).max()) <= 0.5 for b in beds.values())
          and rms(d[48000:48000 * 3]) > 2.5 * rms(d[48000 * 5:48000 * 7]) and quiet is not None and quiet > 0.002,
          (quiet, c_, rms(d[48000:48000 * 3]), rms(d[48000 * 5:48000 * 7])))
    from archivist.cartoon import textscript as Tx
    nums = [Tx._visual(x, 2) for x in ("counter: $4,800,000 spent", "bars: 2023 1.2, 2024 4.8 M", "bars: pharmacy 30, hospital 1,050")]
    odd_story = Tx.parse("Title: X\nNarrator: Kate (woman, narrator)\n- Lena (woman, journalist)\n\n== City hall corridor\n"
                         "Narrator (explain): Hello.\nNote: all names are invented.\nLena: Hi.\n")
    check("stories: numbers in pictures (4,800,000; a year before a value; 1,050), the narrator named 'Narrator', "
          "a bulleted cast, a note that is not a line, a place named in more words",
          nums[0]["to"] == 4800000 and nums[1]["values"] == [1.2, 4.8] and nums[1]["labels"] == ["2023", "2024"]
          and nums[2]["values"] == [30, 1050] and sorted(odd_story["cast"]) == ["kate", "lena"]
          and [ln["who"] for ln in odd_story["scenes"][0]["lines"]] == ["kate", "lena"] and odd_story["scenes"][0]["bg"] == "city_hall"
          and Tx.parse("Title: X\nNarrator: Kate (woman)\n\n== City\nKate: We fly to Timișoara and the price is high.\n")["language"] == "en"
          and Tx.parse("Title: X\nNarrator: Ana (woman)\n\n== City\nAna: Primaria a platit patru milioane de lei pentru un drum.\n")["language"] == "ro",
          (nums, odd_story["cast"], odd_story["scenes"]))
    from archivist.cartoon import bgs
    bad, looks = [], {}
    for fmt in ("vertical", "horizontal"):
        W, H = F.FORMATS[fmt]
        for name in bgs.BACKGROUNDS:
            cv = Canvas(W // 4, H // 4, 1920 if W > H else 1080)
            try:
                gy = bgs.draw(cv, name, 1.0)
                if float(cv.img.std()) < 6 or not (cv.SH * 0.6 < gy < cv.SH):
                    bad.append(f"{fmt} {name}: blank or no floor")
                looks[(fmt, name)] = cv.img.astype(np.int16)
            except Exception as exc:
                bad.append(f"{fmt} {name}: {type(exc).__name__}: {exc}")
    same = [n for n in ("hospital", "school", "shop", "home") if ("vertical", n) in looks
            and float(np.abs(looks[("vertical", n)] - looks[("vertical", "office")]).mean()) < 10]
    doc = ch.make("Dr. Paul", "doctor")
    check("backgrounds: all twelve draw in both formats (a hospital, a school, a shop, a block of flats among them); "
          "a doctor wears a white coat", not bad and not same and len(bgs.BACKGROUNDS) == 12 and doc["outfit"] == "coat",
          (bad, same, doc["outfit"]))
    check("example: 8-12 scenes, 60-120 s, own characters (6)", 8 <= len(film["scenes"]) <= 12 and 60 <= tl2["seconds"] <= 120
          and len(film["cast"]) >= 4, (len(film["scenes"]), tl2["seconds"], len(film["cast"])))

    # 5. the pages
    from archivist.web import create_app
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    with app.test_client() as c:
        home = c.get("/auto/cartoon", headers=H)
        check("pages: Cartoon Studio opens, with the example story to change", home.status_code == 200 and b"Make the cartoon" in home.data
              and b"== Board | flow: City budget -&gt; RoadCo" in home.data, home.status_code)
        r = c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(SHORT), "format": "horizontal", "captions": "1",
                                              "style": "box"}, headers=H)
        jid = next((j["id"] for j in vo.list_jobs() if j.get("kind") == "cartoon_make"), "")
        t0 = time.time()
        while jid and vo.read_job(jid)["state"] in ("waiting", "working") and time.time() - t0 < 900:
            time.sleep(1)
        j = vo.read_job(jid) if jid else {}
        res = j.get("result") or {}
        check("pages: my script made as a cartoon (a preview without voices), checked, saved in Cartoons",
              r.status_code == 302 and j.get("state") == "done" and res.get("width") == 1920 and res.get("saved")
              and Path(res["saved"]).is_file() and Path(res["saved"]).parent.name == "Cartoons", (r.status_code, j.get("state"), res))
        one = c.get(f"/auto/cartoon/{jid}", headers=H)
        fm = c.get(f"/auto/cartoon/{jid}/film.mp4", headers=H)
        check("pages: the film's page plays it and shows its lines to change", one.status_code == 200 and fm.status_code == 200
              and fm.mimetype == "video/mp4" and b"t_0_0" in one.data and b"Make it again" in one.data, (one.status_code, fm.status_code))
        ag = c.post(f"/auto/cartoon/{jid}/again", data={"t_0_0": "The price is five times higher.", "e_0_1": "angry", "bg_1": "paper",
                                                        "format": "horizontal"}, headers=H)
        nid = (ag.headers.get("Location") or "").rstrip("/").split("/")[-1]
        sc2 = json.loads((vo._job_dir(nid) / "job.json").read_text("utf-8"))["script"] if re.fullmatch(r"[0-9-a-f]{22}", nid) else {}
        check("pages: a changed line, feeling and background make a new version", ag.status_code == 302 and sc2
              and sc2["scenes"][0]["lines"][0]["text"] == "The price is five times higher."
              and sc2["scenes"][0]["lines"][1]["emotion"] == "angry" and sc2["scenes"][1]["bg"] == "paper", (ag.status_code, nid))
        if nid:
            t0 = time.time()
            while vo.read_job(nid)["state"] in ("waiting", "working") and time.time() - t0 < 900:
                time.sleep(1)
        story = ("Title: Text test\nNarrator: Kate (woman)\nRick (man, contractor boss)\n\n== Office | contract: CONTRACT; price $4 800 000; "
                 "stamp APPROVED\nKate: The price is four times higher.\nRick (count, sly) [bubble]: Approved!\n\n"
                 "== Board | bars: fair 1.2, paid 4.8 M\nKate: Taxpayers pay the difference.\n")
        tx = c.post("/auto/cartoon/new", data={"text": story, "format": "vertical", "captions": "1"}, headers=H)
        tid = next((j["id"] for j in vo.list_jobs() if j.get("kind") == "cartoon_make"), "")
        t0 = time.time()
        while tid and vo.read_job(tid)["state"] in ("waiting", "working") and time.time() - t0 < 900:
            time.sleep(1)
        tsc = json.loads((vo._job_dir(tid) / "job.json").read_text("utf-8"))["script"] if tid else {}
        check("pages: a story written as plain text becomes a cartoon (scenes, characters, a contract, a chart, a bubble)",
              tx.status_code == 302 and vo.read_job(tid)["state"] == "done" and len(tsc.get("scenes") or []) == 2
              and tsc["scenes"][0]["visual"]["kind"] == "contract" and tsc["scenes"][1]["visual"]["values"] == [1.2, 4.8]
              and tsc["scenes"][0]["lines"][1].get("bubble") and tsc["title"] == "Text test", (tx.status_code, tsc))
        page_t = c.get(f"/auto/cartoon/{tid}", headers=H).get_data(as_text=True)
        changed = page_t.split("name='text'", 1)[-1].split(">", 1)[-1].split("</textarea>", 1)[0]
        import html as _html
        changed = _html.unescape(changed).replace("four times higher", "five times higher")
        ag2 = c.post(f"/auto/cartoon/{tid}/again", data={"text": changed, "format": "vertical", "captions": "1"}, headers=H)
        nid2 = (ag2.headers.get("Location") or "").rstrip("/").split("/")[-1]
        sc3 = json.loads((vo._job_dir(nid2) / "job.json").read_text("utf-8"))["script"] if nid2 and vo._job_dir(nid2).exists() else {}
        check("pages: the film's story changed as text makes a new version (the rest kept)", ag2.status_code == 302 and sc3
              and sc3["scenes"][0]["lines"][0]["text"] == "The price is five times higher."
              and sc3["scenes"][0]["visual"] == tsc["scenes"][0]["visual"] and F.check_script(sc3)["cast"] == F.check_script(tsc)["cast"], (ag2.status_code, nid2))
        if nid2:
            t0 = time.time()
            while vo.read_job(nid2)["state"] in ("waiting", "working") and time.time() - t0 < 900:
                time.sleep(1)
        from archivist.cartoon import library as Lb
        lib = Lb.load()
        cl = c.get("/auto/cartoon/characters", headers=H)
        png = c.get("/auto/cartoon/characters/rick.png", headers=H)
        ed = c.get("/auto/cartoon/characters/rick", headers=H)
        sv = c.post("/auto/cartoon/characters/rick", data={"role": "contractor boss", "female": "0", "skin": ch.SKINS[2],
                                                          "hair": ch.HAIRS[4], "hair_style": "curly", "beard": "full", "outfit": "suit",
                                                          "cloth": ch.CLOTHES[0], "glasses": "1",
                                                          "voice": "A low, smooth, sly businessman."}, headers=H)
        again = F.check_script({"title": "x", "cast": {"rick": {"name": "Rick", "role": "builder"}},
                                "scenes": [{"bg": "office", "lines": [{"who": "rick", "text": "Hello."}]}]})["cast"]["rick"]
        check("characters' library: the film's people kept (look, voice); the page lists them with a picture; a changed "
              "look and voice are used by the next film naming them",
              "rick" in lib and "kate" in lib and cl.status_code == 200 and b"/auto/cartoon/characters/rick.png" in cl.data
              and png.status_code == 200 and png.mimetype == "image/png" and len(png.data) > 2000 and ed.status_code == 200
              and sv.status_code == 302 and again["hair"] == ch.HAIRS[4] and again["glasses"] is True and again["beard"] == "full"
              and again["voice"] == {"kind": "describe", "text": "A low, smooth, sly businessman."},
              (sorted(lib), cl.status_code, png.status_code, again.get("hair"), again.get("voice")))
        shapes = [c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(x)}, headers=H).status_code for x in (
            {"cast": ["x"], "scenes": [{"lines": [{"text": "a"}]}]},
            {"cast": {"a": {"name": "A"}}, "scenes": [{"mood": ["x"], "min": "abc", "cast": [["a"]], "lines": {"x": 1}}]},
            {"cast": {"a": {"name": "A"}}, "narrator": ["a"], "scenes": ["x", {"lines": [{"who": ["a"], "pose": ["x"], "text": "Hi."}]}]})]
        sid = next((j_["id"] for j_ in vo.list_jobs() if j_.get("kind") == "cartoon_make"), "")
        again_odd = c.post(f"/auto/cartoon/{sid}/again", data={"t_0_0": "Hello."}, headers=H).status_code if sid else 0
        waiting = vo._submit({"kind": "cartoon_make", "script": SHORT, "voices": False, "title": "w"}, addon=False)
        rev = c.post(f"/auto/cartoon/{waiting}/reveal", headers=H).status_code      # (no result yet)
        vo.cancel_job(waiting)
        check("pages: scripts of odd shapes, a film made of one, Reveal of a film not made - no server error",
              all(x in (302, 400) for x in shapes) and again_odd in (302, 400) and rev == 302, (shapes, again_odd, rev))
        no_file = c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(SHORT), "music": "file",
                                                    "music_path": str(work / "nope.mp3")}, headers=H)
        check("pages: a music file that is not there is refused clearly", no_file.status_code == 400
              and b"Choose the music file" in no_file.data, no_file.status_code)
        # a film without music made again (a form that says nothing about music): still without; its page shows it so
        quiet_id = next((j_["id"] for j_ in vo.list_jobs() if j_.get("kind") == "cartoon_make" and not j_.get("music")), "")
        again_q = c.post(f"/auto/cartoon/{quiet_id}/again", data={"t_0_0": "Hello again."}, headers=H) if quiet_id else None
        new_q = (again_q.headers.get("Location") or "").rstrip("/").split("/")[-1] if again_q is not None else ""
        page_q = c.get(f"/auto/cartoon/{quiet_id}", headers=H).get_data(as_text=True) if quiet_id else ""
        check("music: a film without music made again stays without; its page has 'No music' chosen",
              again_q is not None and again_q.status_code == 302 and new_q and not vo.read_job(new_q).get("music")
              and "value='none' checked" in page_q, (quiet_id, new_q))
        if new_q:
            vo.cancel_job(new_q)
        bad_json = c.post("/auto/cartoon/new", data={"story": "own", "script": "{not json"}, headers=H)
        no_voice = c.post("/auto/cartoon/new", data={"story": "road_contract", "voices": "1"}, headers=H)
        check("pages: a broken script and voices without the add-on are refused clearly",
              bad_json.status_code == 400 and b"not valid JSON" in bad_json.data
              and (vo.installed() or (no_voice.status_code == 400 and b"voice add-on" in no_voice.data)),
              (bad_json.status_code, no_voice.status_code))
        st = c.get(f"/api/cartoon/status?ids={jid},{nid},x", headers=H).get_json() or {}
        check("pages: how far the films are, for the page to ask", st.get(jid, {}).get("state") == "done" and st.get("x", {}).get("state") == "gone", st)
        c.post("/lang", data={"lang": "ru"}, headers=H)
        ru = (c.get("/auto/cartoon", headers=H).get_data(as_text=True) + c.get(f"/auto/cartoon/{jid}", headers=H).get_data(as_text=True)
              + c.get("/auto/cartoon/characters", headers=H).get_data(as_text=True)
              + c.get("/auto/cartoon/characters/rick", headers=H).get_data(as_text=True))
        body = re.sub(r"<(script|style|textarea)[^>]*>.*?</\1>", " ", ru, flags=re.S)
        body = re.sub(r"<[^>]*translate=['\"]no['\"][^>]*>.*?</[a-z0-9]+>", " ", body, flags=re.S)
        txt = re.sub(r"<[^>]+>", "\n", body)
        left = sorted({x.strip() for x in txt.split("\n") if re.search(r"[A-Za-z]{3,}", x) and not re.search(r"[А-Яа-я]", x)
                       and x.strip() not in ("MediaEngine", "Social Lab", "JSON", "YouTube") and "querySelectorAll" not in x})
        check("pages: in Russian, no English left", "Мультстудия" in ru and not left, left[:12])
        dl = c.post(f"/auto/cartoon/{nid}/delete", headers=H)
        check("pages: a film's job deleted, its saved file stays", dl.status_code == 302 and not vo._job_dir(nid).exists()
              and Path(res.get("saved") or "/x").is_file(), dl.status_code)
    rep = {"passed": sum(x["pass"] for x in checks), "total": len(checks), "checks": checks}
    (work / "cartoon_check.json").write_text(json.dumps(rep, indent=1), "utf-8")
    print(json.dumps({"passed": rep["passed"], "total": rep["total"]}))
    return 0 if rep["passed"] == rep["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
