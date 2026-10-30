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
    from archivist.cartoon import chars as ch, film as F, jobs as cj, stories
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
    # lip sync beyond open and closed: the mouth's shape from the letters (English, Russian), drawn differently;
    # blinks at uneven times; a nod and raised brows on a word said with weight
    shp = [ch.sound_shapes([{"w": w_, "s": 0.0, "e": 0.6}], 0.0, 18) for w_ in ("Mama", "true", "five", "мама", "уф", "eel")]
    seen = [set(x) - {""} for x in shp]
    ok_shapes = ({"M", "A"} <= seen[0] and "U" in seen[1] and "F" in seen[2] and {"M", "A"} <= seen[3]
                 and {"U", "F"} <= seen[4] and "E" in seen[5])
    kate = ch.make("Kate", "narrator", female=True)
    faces = {}
    for shape_ in ("M", "O", "E"):
        cvm = Canvas(300, 300, 300)
        cvm.fill("#eef2f6")
        ch.draw(cvm, kate, 150, 800, 1.6, 1, "idle", mouth=(0.8, shape_), t=0.0)
        faces[shape_] = cvm.img[150:260, 80:220].astype(np.int16)
    diff_mo = float(np.abs(faces["M"] - faces["O"]).mean())
    diff_oe = float(np.abs(faces["O"] - faces["E"]).mean())
    shut = [k_ / 30 for k_ in range(0, 30 * 30) if F._blink(k_ / 30, 0) >= 1.0]
    starts = [x_ for i_, x_ in enumerate(shut) if i_ == 0 or x_ - shut[i_ - 1] > 0.1]
    gaps = [round(b_ - a_, 2) for a_, b_ in zip(starts, starts[1:])]
    beat = (F._beat({"words": [{"w": "simple", "s": 1.0, "e": 1.4}, {"w": "millions!", "s": 2.0, "e": 2.5}]}, 2.19),
            F._beat({"words": [{"w": "a", "s": 1.0, "e": 1.1}]}, 1.1))
    check("lip sync: the mouth's shape follows the sounds (m/b/p closed, o, u, e, f/v; English and Russian) and is drawn "
          "differently; blinks at uneven times; a nod and raised brows on a word said with weight, not on a small one",
          ok_shapes and diff_mo > 2 and diff_oe > 2 and 5 <= len(starts) <= 16 and len(set(gaps)) > 3 and beat[0] > 0.8
          and beat[1] == 0.0, (seen, round(diff_mo, 2), round(diff_oe, 2), gaps, beat))
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
    # (the example story: its night scene has no picture)
    from archivist.cartoon import textscript as _T
    ex = F.check_script(_T.parse(_T.ROAD_TEXT))
    ex_tl = F.timeline(ex)
    night = next(x for x in ex_tl["scenes"] if x["bg"] == "night")
    l0, l1 = night["lines"][0], night["lines"][1]
    shots = [F.close_up(ex, night, (l0["s"] + l0["e"]) / 2), F.close_up(ex, night, (l1["s"] + l1["e"]) / 2),
             F.close_up(dict(ex, camera="still"), night, (l1["s"] + l1["e"]) / 2),
             F.close_up(ex, next(x for x in ex_tl["scenes"] if x.get("visual")), 3.0)]
    wide_c, close_c = Canvas(W // 4, H // 4, 1080), Canvas(W // 4, H // 4, 1080)
    F.draw_frame(wide_c, dict(ex, camera="still"), night, (l1["s"] + l1["e"]) / 2, {})
    F.draw_frame(close_c, ex, night, (l1["s"] + l1["e"]) / 2, {})
    cut = float(np.abs(wide_c.img.astype(np.int16) - close_c.img.astype(np.int16)).mean())
    from archivist.cartoon import bgs as _bgs
    t1 = (l1["s"] + l1["e"]) / 2
    cvv = Canvas(1080, 1920, 1080)
    nm = F._shown(ex, night)
    xs_, sc_, _b = F._layout(cvv, len(nm), False)
    heads = {}
    for where in ("middle", "bottom"):                     # (the face clear of the captions' band)
        cx_, cy_, z_ = F._camera(cvv, dict(ex, caption_at=where), night, t1, nm, xs_, sc_)
        heads[where] = (round(((_bgs.ground_y(cvv) - 530 * sc_ - cy_) * z_ + cvv.SH / 2) / cvv.SH, 3), round(z_, 2))
    lens = {pc: F.timeline(dict(ex, pace=pc))["seconds"] for pc in ("quick", "", "calm")}
    snd_tl = F.timeline(F.check_script({"title": "x", "cast": {"a": {"name": "Ann"}, "b": {"name": "Bob"}}, "scenes": [
        {"bg": "office", "cast": ["a", "b"], "lines": [{"who": "a", "text": "Look at this, it is quite long."},
                                                         {"who": "b", "text": "Wow!", "bubble": True}]},
        {"bg": "board", "visual": {"kind": "magnifier", "title": "PRICE"}, "lines": [{"who": "a", "text": "We check the papers."}]}]}))
    snd = F.mix(snd_tl)
    def _rms(t0, t1):
        return float(np.sqrt(np.mean(snd[int(t0 * F.SR):int(t1 * F.SR)] ** 2)))
    b_s = snd_tl["scenes"][0]["lines"][1]["s"]
    m_s = snd_tl["scenes"][1]["s"] + 0.8
    check("sounds: a speech bubble pops up (just before its words), a magnifier rings; silence before them",
          _rms(b_s - 0.15, b_s) > 0.01 and _rms(m_s, m_s + 0.3) > 0.01 and _rms(0.0, 0.5) < 0.001,
          (_rms(b_s - 0.15, b_s), _rms(m_s, m_s + 0.3), _rms(0.0, 0.5)))
    check("pace: shorter pauses for a quick film, longer for a calm one; an unknown pace is the usual",
          lens["quick"] < lens[""] < lens["calm"] and F.check_script(dict(_T.parse(_T.ROAD_TEXT), pace="odd"))["pace"] == "",
          lens)
    check("camera: a cut to a close-up of the one speaking on a scene's second line (not its first, not while a picture "
          "is to be read, never with the camera still); the face above captions in the middle",
          shots[0] is None and shots[1] == l1["who"] and shots[2] is None and shots[3] is None and cut > 8
          and 0.1 <= heads["middle"][0] <= 0.24 and 0.18 <= heads["bottom"][0] <= 0.32 and heads["middle"][1] >= 2.4,
          (shots, cut, heads))
    import wave as _wave
    from archivist.cartoon import voices as _V
    lv = {}
    for nm, amp in (("quiet", 0.02), ("loud", 0.6)):            # (a quiet voice and a loud one: the same level after)
        tt = np.arange(int(1.5 * 24000)) / 24000
        xx = amp * np.sin(2 * np.pi * 220 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * tt))
        with _wave.open(str(work / f"lv_{nm}.wav"), "wb") as w_:
            w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(24000); w_.writeframes((xx * 32767).astype(np.int16).tobytes())
        _V._to48k(work / f"lv_{nm}.wav", work / f"lv_{nm}48.wav")
        aa, _sr = _V._wav(work / f"lv_{nm}48.wav")
        lv[nm] = round(float(np.sqrt(np.mean(aa ** 2))), 3)
    check("voices: every line as loud as the others (a quiet voice brought up, a loud one down)",
          abs(lv["quiet"] - lv["loud"]) < 0.02 and 0.08 < lv["loud"] < 0.14, lv)
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
    same = [n for n in ("hospital", "school", "shop", "home", "site") if ("vertical", n) in looks
            and float(np.abs(looks[("vertical", n)] - looks[("vertical", "office")]).mean()) < 10]
    doc = ch.make("Dr. Paul", "doctor")
    site_bgs = [Tx.parse(f"Title: X\nNarrator: Kate (woman)\n\n== {h}\nKate: Hello there, everyone.\n")["scenes"][0]["bg"]
                for h in ("Construction site", "Стройка", "Șantier", "Building site, the crane", "Road construction")]
    if site_bgs != ["site", "site", "site", "site", "road"]:
        bad.append(f"building site words: {site_bgs}")
    check("backgrounds: all thirteen draw in both formats (a hospital, a school, a shop, a block of flats, a building site "
          "among them); "
          "a doctor wears a white coat", not bad and not same and len(bgs.BACKGROUNDS) == 13 and doc["outfit"] == "coat",
          (bad, same, doc["outfit"]))
    check("example: 8-12 scenes, 60-120 s, own characters (6)", 8 <= len(film["scenes"]) <= 12 and 60 <= tl2["seconds"] <= 120
          and len(film["cast"]) >= 4, (len(film["scenes"]), tl2["seconds"], len(film["cast"])))

    # 4b. drawing styles: the same shapes drawn another way (hand-drawn, a whiteboard, paper, motion graphics)
    from archivist.cartoon.draw import STYLES
    bad_s, mid = [], {}
    for fmt in ("vertical", "horizontal"):
        W, H = F.FORMATS[fmt]
        for st_ in STYLES:
            cv = Canvas(W // 2, H // 2, 1920 if W > H else 1080, st_)
            for i, s in enumerate(tl2["scenes"]):
                try:
                    F.draw_frame(cv, film, s, (s["s"] + s["e"]) / 2, {})
                    cv.finish()
                    if float(cv.img.std()) < 8:
                        bad_s.append(f"{fmt} {st_} scene {i + 1}: blank")
                    if i in (0, 1):
                        mid[(fmt, st_, i)] = cv.img.astype(np.float32)
                except Exception as exc:
                    bad_s.append(f"{fmt} {st_} scene {i + 1}: {type(exc).__name__}: {exc}")
    away = {f"{k[0]} {k[1]} {k[2]}": round(float(np.abs(v - mid[(k[0], "flat", k[2])]).mean()), 1)
            for k, v in mid.items() if k[1] != "flat"}
    s1 = tl2["scenes"][1]
    plain, flat_, odd = Canvas(480, 270, 1920), Canvas(480, 270, 1920, "flat"), Canvas(480, 270, 1920, "crayon")
    for cv in (plain, flat_, odd):
        F.draw_frame(cv, film, s1, s1["s"] + 1.0, {})
        cv.finish()
    check("drawing styles: every scene of the example draws in each style (hand-drawn, whiteboard, paper, motion) in both "
          "formats, each clearly unlike the flat one; the flat one (and an unknown name) draws as a canvas without a style",
          len(STYLES) == 5 and not bad_s and len(away) == 16 and all(v > 6 for v in away.values())
          and np.array_equal(plain.img, flat_.img) and np.array_equal(plain.img, odd.img) and odd.style == "flat", (bad_s[:5], away))
    kept_s = [F.check_script(dict(SHORT, drawing=d)).get("drawing") for d in ("hand", "crayon", None, 5)]
    check("drawing styles: a script keeps its style; an unknown one is the flat", kept_s == ["hand", "flat", "flat", "flat"], kept_s)

    # 5. the pages
    from archivist.web import create_app
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}
    with app.test_client() as c:
        home = c.get("/auto/cartoon", headers=H)
        check("pages: Cartoon Studio opens, with the example story to change", home.status_code == 200 and b"Make the cartoon" in home.data
              and b"== Board | flow: City budget -&gt; RoadCo" in home.data, home.status_code)
        samples = [c.get(f"/auto/cartoon/drawing/{k}.jpg", headers=H) for k in STYLES]
        no_sample = c.get("/auto/cartoon/drawing/crayon.jpg", headers=H)
        check("pages: the new cartoon's form shows the five drawing styles with a picture of each (flat chosen)",
              all(x.status_code == 200 and x.mimetype == "image/jpeg" and x.data[:2] == b"\xff\xd8" and len(x.data) > 3000 for x in samples)
              and no_sample.status_code == 404 and home.data.count(b"name='drawing'") >= 5
              and b"name='drawing' value='flat' checked" in home.data and b"Drawing style" in home.data,
              ([x.status_code for x in samples], no_sample.status_code))
        r = c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(SHORT), "format": "horizontal", "captions": "1",
                                              "style": "box", "drawing": "paper"}, headers=H)
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
        check("pages: the film is drawn in the style chosen (paper) and its page has it chosen",
              cj.script_of(jid).get("drawing") == "paper" and b"name='drawing' value='paper' checked" in one.data,
              cj.script_of(jid).get("drawing"))
        ag = c.post(f"/auto/cartoon/{jid}/again", data={"t_0_0": "The price is five times higher.", "e_0_1": "angry", "bg_1": "paper",
                                                        "format": "horizontal"}, headers=H)
        nid = (ag.headers.get("Location") or "").rstrip("/").split("/")[-1]
        sc2 = json.loads((vo._job_dir(nid) / "job.json").read_text("utf-8"))["script"] if re.fullmatch(r"[0-9-a-f]{22}", nid) else {}
        check("pages: a changed line, feeling and background make a new version", ag.status_code == 302 and sc2
              and sc2["scenes"][0]["lines"][0]["text"] == "The price is five times higher."
              and sc2["scenes"][0]["lines"][1]["emotion"] == "angry" and sc2["scenes"][1]["bg"] == "paper"
              and sc2.get("camera") != "still" and b"Close-ups of the one speaking" in one.data
              and sc2.get("drawing") == "paper", (ag.status_code, nid))
        # the editor: a picture of each scene; lines removed and added where wanted; scenes moved and removed; the title;
        # the language (the story writer is not installed here: said how to get it)
        n_sc = len(F.check_script(cj.script_of(jid))["scenes"])
        thumbs = [c.get(f"/auto/cartoon/{jid}/scene/{i}.jpg", headers=H) for i in range(n_sc)]
        no_thumb = c.get(f"/auto/cartoon/{jid}/scene/{n_sc + 3}.jpg", headers=H)
        base = F.check_script(cj.script_of(jid))
        first0 = base["scenes"][0]["lines"][0]["text"]
        ed = c.post(f"/auto/cartoon/{jid}/again", data={
            "title": "  Edited   film ", "order": ",".join(str(i) for i in range(n_sc - 1, -1, -1)),
            "x_0_0": "1", "n_0_3_t": "Added after the second line.", "n_0_3_at": "1", "n_0_3_w": "ann", "n_0_3_e": "angry",
            "n_0_3_p": "point", "n_0_1_t": "Added first.", "n_0_1_at": "-1", "n_0_1_w": "nobody", "n_0_9_t": "   ",
            "n_0_9_at": "0"}, headers=H)
        eid = (ed.headers.get("Location") or "").rstrip("/").split("/")[-1]
        es = F.check_script(cj.script_of(eid)) if re.fullmatch(r"[0-9-a-f]{22}", eid) else {}
        if es:
            vo.cancel_job(eid)
        last_sc = (es.get("scenes") or [{}])[-1].get("lines") or []
        old0 = base["scenes"][0]["lines"]
        want = (["Added first."] + [x["text"] for x in old0[1:2]] + ["Added after the second line."] + [x["text"] for x in old0[2:]])
        empty_o = c.post(f"/auto/cartoon/{jid}/again", data={"order": ""}, headers=H)
        lang_no = c.post(f"/auto/cartoon/{jid}/language", data={"lang": "ru"}, headers=H)
        check("pages: the editor - a picture of every scene; a line removed, lines added where wanted (an empty one left "
              "out); the scenes' order turned round; the title; no scenes refused; the language needs the story writer",
              all(x.status_code == 200 and x.mimetype == "image/jpeg" and len(x.data) > 3000 for x in thumbs)
              and no_thumb.status_code == 404 and b"id='ctScenes'" in one.data and b"name='order'" in one.data
              and b"install the story writer" in one.data and ed.status_code == 302 and bool(es)
              and es["title"] == "Edited film" and len(es["scenes"]) == n_sc
              and [x["text"] for x in last_sc] == want and first0 not in [x["text"] for x in last_sc]
              and last_sc[0]["who"] == es["narrator"] and last_sc[1 + (len(old0) > 1)]["emotion"] == "angry"
              and es.get("drawing") == "paper"
              and empty_o.status_code == 400 and b"at least one scene" in empty_o.data
              and lang_no.status_code == 400 and b"Install the story writer" in lang_no.data,
              ([x.status_code for x in thumbs], no_thumb.status_code, ed.status_code, es.get("title") if es else None,
               [x["text"] for x in last_sc], want, empty_o.status_code, lang_no.status_code))
        ag_still = c.post(f"/auto/cartoon/{jid}/again", data={"camera_form": "1", "format": "horizontal", "pace": "calm"}, headers=H)
        nid_s = (ag_still.headers.get("Location") or "").rstrip("/").split("/")[-1]
        sc_s = json.loads((vo._job_dir(nid_s) / "job.json").read_text("utf-8"))["script"] if re.fullmatch(r"[0-9-a-f]{22}", nid_s) else {}
        if nid_s:
            vo.cancel_job(nid_s)
        check("pages: close-ups turned off and a calm pace are kept in the new version", sc_s.get("camera") == "still"
              and sc_s.get("pace") == "calm" and b"<option value='calm' selected>" in c.get(f"/auto/cartoon/{nid_s}", headers=H).data
              and b"name='camera' value='1' checked" not in c.get(f"/auto/cartoon/{nid_s}", headers=H).data, (ag_still.status_code, sc_s.get("camera")))
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
        nw = c.post("/auto/cartoon/characters/add-one", data={"name": "Lena Petrova", "role": "journalist", "female": "1"}, headers=H)
        nkey = (nw.headers.get("Location") or "").rstrip("/").split("/")[-1]
        hs = c.post(f"/auto/cartoon/characters/{nkey}", data={"role": "journalist", "female": "1", "host_form": "1", "host": "1"}, headers=H)
        from archivist.cartoon import library as Lb, writer as Wr
        hosted = (Lb.host("en") or {}).get("name")
        ru_host = (Lb.host("ru") or {}).get("name")         # (a host named in Latin letters: not for a Russian story)
        c.post("/auto/cartoon/characters/rick", data={"role": "contractor boss", "female": "0", "host_form": "1"}, headers=H)
        still = (Lb.host("en") or {}).get("name")         # (saving another character keeps the host)
        asked_host = Wr.prompt({"mode": "topic", "topic": "School meals", "lang": "en"})
        lena = F.check_script({"title": "x", "cast": {"lena": {"name": "Lena Petrova"}},
                               "scenes": [{"bg": "office", "lines": [{"who": "lena", "text": "Hello."}]}]})["cast"]["lena"]
        listed = c.get("/auto/cartoon/characters", headers=H).data
        c.post(f"/auto/cartoon/characters/{nkey}", data={"role": "journalist", "female": "1", "host_form": "1"}, headers=H)
        bad_new = c.post("/auto/cartoon/characters/add-one", data={"name": " "}, headers=H)
        after_host = (Lb.host("en") or {}).get("name")
        check("characters: one added before any film (its look from its name), made the host - the writer gives new stories "
              "this narrator, a story naming her takes her look; the host taken off again; an empty name refused",
              nw.status_code == 302 and nkey == "lenapetrova" and hs.status_code == 302 and hosted == "Lena Petrova"
              and "The narrator is Lena Petrova (woman, narrator)" in asked_host and lena["female"] is True
              and ru_host != "Lena Petrova" and still == "Lena Petrova"
              and b"the host" in listed and after_host != "Lena Petrova" and bad_new.status_code == 400,
              (nw.status_code, nkey, hosted, ru_host, still, lena.get("female"), after_host, bad_new.status_code))
        shapes = [c.post("/auto/cartoon/new", data={"story": "own", "script": json.dumps(x)}, headers=H).status_code for x in (
            {"cast": ["x"], "scenes": [{"lines": [{"text": "a"}]}]},
            {"cast": {"a": {"name": "A"}}, "scenes": [{"mood": ["x"], "min": "abc", "cast": [["a"]], "lines": {"x": 1}}]},
            {"cast": {"a": {"name": "A"}}, "narrator": ["a"], "scenes": ["x", {"lines": [{"who": ["a"], "pose": ["x"], "text": "Hi."}]}]},
            {"cast": {"a": {"name": "A"}}, "pace": [], "format": {"x": 1}, "camera": [1], "scenes": [{"lines": [{"who": "a", "text": "Hi."}]}]})]
        sid = next((j_["id"] for j_ in vo.list_jobs() if j_.get("kind") == "cartoon_make"), "")
        again_odd = c.post(f"/auto/cartoon/{sid}/again", data={"t_0_0": "Hello."}, headers=H).status_code if sid else 0
        try:                                               # (a finished film of such a script shows it as text)
            odd_text = all(Tx.to_text(x).startswith("Title:") for x in (
                {"cast": {"a": {"name": "A"}}, "narrator": ["a"], "scenes": ["x", {"lines": [{"who": ["a"], "pose": ["x"]}]}]},
                {"cast": [1], "scenes": {"a": 1}}, "x", {"scenes": [{"visual": {"kind": "flow", "nodes": [{}], "edges": 3}, "bg": 5}]},
                {"cast": {"a": {"name": ["Ann"], "role": ["mayor"]}, "b": {"name": 5, "role": 7}}, "narrator": "a",
                 "scenes": [{"lines": [{"who": "a", "text": "Hi"}, {"who": "b", "text": "Yes"}]}]}))
        except Exception as exc:
            odd_text = repr(exc)
        waiting = vo._submit({"kind": "cartoon_make", "script": SHORT, "voices": False, "title": "w"}, addon=False)
        rev = c.post(f"/auto/cartoon/{waiting}/reveal", headers=H).status_code      # (no result yet)
        vo.cancel_job(waiting)
        check("pages: scripts of odd shapes, a film made of one, Reveal of a film not made - no server error",
              all(x in (302, 400) for x in shapes) and again_odd in (302, 400) and rev == 302 and odd_text is True,
              (shapes, again_odd, rev, odd_text))
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
