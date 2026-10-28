"""A cartoon film from a script: the scenes one after another (a background, the characters, a visual - a scheme of
money, a contract, a chart, a road ...), the lines said by the characters' voices with their mouths moving, captions
of the words, short sounds, one MP4.

A script is plain data (JSON) - what a person or a language model writes:
  {"title": ..., "language": "en", "format": "vertical" | "horizontal",
   "cast": {"kate": {"name": "Kate", "role": "narrator", "female": true, ...}, ...},
   "narrator": "kate",
   "scenes": [{"bg": "office", "cast": ["ed"], "visual": {"kind": "contract", ...},
               "lines": [{"who": "kate", "text": "...", "pose": "explain", "emotion": "happy"}, ...]}, ...]}
A character not in a scene's cast speaks off screen (the narrator's usual place).
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

from . import bgs, chars as ch, props as P
from .draw import INK, Canvas, back, ease, lerp, rounded

FPS = 30
FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
SR = 48000
GAP = 0.35                    # silence after each line (s)
SCENE_PAD = 0.5               # a little air at the end of every scene (s)


class FilmError(Exception):
    pass


# ------------------------------------------------------------------------------------------------- the script

def check_script(sc: dict) -> dict:
    """The script made safe and complete: known backgrounds, poses, emotions; every speaker in the cast."""
    if not isinstance(sc, dict) or not isinstance(sc.get("scenes"), list) or not sc["scenes"]:
        raise FilmError("The script has no scenes.")
    out = dict(sc)
    out["format"] = sc.get("format") if sc.get("format") in FORMATS else "vertical"
    cast = {}
    for key, spec in (sc.get("cast") or {}).items():
        if not isinstance(spec, dict):
            continue
        key = re.sub(r"[^a-z0-9_]", "", str(key).lower())[:30] or f"c{len(cast)}"
        base = ch.make(str(spec.get("name") or key), str(spec.get("role") or ""), seed=str(spec.get("seed") or spec.get("name") or key),
                       **{k: v for k, v in spec.items() if k in ("female", "build", "skin", "hair", "hair_style", "face", "beard",
                                                                  "glasses", "outfit", "cloth", "tie", "pants", "shoes", "hat",
                                                                  "height")})
        base["voice"] = spec.get("voice") or {}
        if not spec.get("keep_look"):                      # the library's look and voice for this name (Characters page)
            from . import library
            base.update(library.look_of(base["name"]))
            lv = library.voice_of(base["name"])
            if lv:                                         # (the narrator too, when a voice was written for it)
                base["voice"] = {"kind": "describe", "text": lv}
        cast[key] = base
    if not cast:
        raise FilmError("The script has no characters.")
    out["cast"] = cast
    out["narrator"] = sc.get("narrator") if sc.get("narrator") in cast else next(iter(cast))
    scenes = []
    for s in sc["scenes"][:40]:
        if not isinstance(s, dict):
            continue
        lines = []
        for ln in (s.get("lines") or [])[:30]:
            if not isinstance(ln, dict) or not str(ln.get("text") or "").strip():
                continue
            who = ln.get("who") if ln.get("who") in cast else out["narrator"]
            lines.append({"who": who, "text": re.sub(r"\s+", " ", str(ln["text"])).strip()[:400],
                          "pose": ln.get("pose") if ln.get("pose") in ch.POSES else None,
                          "emotion": ln.get("emotion") if ln.get("emotion") in ch.EMOTIONS else None,
                          "bubble": bool(ln.get("bubble"))})
        scenes.append({"bg": s.get("bg") if s.get("bg") in bgs.BACKGROUNDS else "city",
                       "cast": [k for k in (s.get("cast") or []) if k in cast][:4],
                       "visual": s.get("visual") if isinstance(s.get("visual"), dict) else None,
                       "lines": lines, "min": float(s.get("min") or 3.0),
                       "mood": {k: v for k, v in (s.get("mood") or {}).items() if k in cast and v in ch.EMOTIONS},
                       "pose": {k: v for k, v in (s.get("pose") or {}).items() if k in cast and v in ch.POSES}})
    if not scenes:
        raise FilmError("The script has no scenes.")
    out["scenes"] = scenes
    out["title"] = str(sc.get("title") or "Cartoon")[:120]
    out["language"] = str(sc.get("language") or "en")[:5]
    return out


def estimate_words(text: str, start: float, rate: float = 2.6) -> tuple[list, float]:
    """Word times for a line without a voice (a preview): about 2.6 words a second, longer words longer."""
    ws = text.split()
    if not ws:
        return [], 0.0
    per = [0.18 + 0.055 * len(re.sub(r"\W", "", w)) + (0.12 if re.search(r"[.,!?;:]$", w) else 0) for w in ws]
    k = (len(ws) / rate) / max(1e-6, sum(per))
    out, t = [], start
    for w, d in zip(ws, per):
        out.append({"w": w, "s": round(t, 3), "e": round(t + d * k * 0.9, 3)})
        t += d * k
    return out, t - start


def timeline(sc: dict, voices: dict | None = None) -> dict:
    """When every scene and line is: voices = {"<scene>.<line>": {"wav": path, "seconds": s, "words": [...]}}
    (word times from the line's start); without one, the line's length is estimated."""
    t = 0.0
    scenes = []
    for i, s in enumerate(sc["scenes"]):
        start = t
        lines = []
        t += 0.25                                          # (a breath before the first line)
        for j, ln in enumerate(s["lines"]):
            v = (voices or {}).get(f"{i}.{j}")
            if v and v.get("seconds"):
                words = [dict(w, s=round(float(w["s"]) + t, 3), e=round(float(w["e"]) + t, 3)) for w in v.get("words") or []]
                dur = float(v["seconds"])
            else:
                words, dur = estimate_words(ln["text"], t)
            lines.append(dict(ln, s=round(t, 3), e=round(t + dur, 3), words=words, wav=(v or {}).get("wav")))
            t += dur + GAP
        t = max(t + SCENE_PAD, start + s["min"])
        scenes.append(dict(s, s=round(start, 3), e=round(t, 3), lines=lines))
    prev: list = []
    for s in scenes:                                       # who walks in: not in the picture of the scene before
        shown = _shown(sc, s)
        s["enter"] = [k for k in shown if k not in prev] if prev else []
        prev = shown
    return {"scenes": scenes, "seconds": round(t, 3)}


def _shown(sc: dict, scene: dict) -> list:
    """The characters in a scene's picture: its cast, or the narrator presenting a scene nobody else is in."""
    names = list(scene.get("cast") or [])
    if not names and any(x["who"] == sc.get("narrator") for x in scene.get("lines") or []):
        names = [sc["narrator"]]
    return names


WALK_IN = 0.9                  # seconds a character takes to walk in


# ------------------------------------------------------------------------------------------------- the picture

def _layout(cv: Canvas, n: int, visual: bool) -> tuple[list, float, tuple | None]:
    """Where the characters stand (x of each), their size, and the visual's box (cx, cy, w, h)."""
    gy = bgs.ground_y(cv)
    if cv.SW >= cv.SH:                                    # wide: the characters left / around, the visual on the right
        sc = 0.92 if n <= 2 else 0.8
        if visual:
            xs = [cv.SW * (0.2 + 0.18 * k) for k in range(n)] if n > 1 else [cv.SW * 0.22]
            box = (cv.SW * (0.68 if n <= 1 else 0.72), cv.SH * 0.42, cv.SW * 0.5, cv.SH * 0.66)
        else:
            xs = [cv.SW * (k + 1) / (n + 1) for k in range(n)]
            box = None
    else:                                                  # tall: the visual on top, captions, the characters below
        sc = (1.05 if n <= 2 else 0.84) if visual else (1.25 if n <= 2 else 0.95)
        xs = [cv.SW * (k + 1) / (n + 1) for k in range(n)] if n > 1 else [cv.SW * 0.5]
        if n == 2:
            xs = [cv.SW * 0.3, cv.SW * 0.7]
        box = (cv.SW * 0.5, cv.SH * 0.255, cv.SW * 0.98, cv.SH * 0.4) if visual else None
    del gy
    return xs, sc, box


def _speaking(scene: dict, t: float) -> tuple[dict | None, int]:
    for j, ln in enumerate(scene["lines"]):
        if ln["s"] - 0.05 <= t <= ln["e"] + 0.05:
            return ln, j
    return None, -1


def _line_at(scene: dict, t: float) -> int:
    """The index of the line said now or last (-1 before the first)."""
    k = -1
    for j, ln in enumerate(scene["lines"]):
        if t >= ln["s"] - 0.05:
            k = j
    return k


def _appear(scene: dict, at, t: float, dur: float = 0.6) -> float:
    """How far something that appears with line "at" (an index; None = at once) has come (0..1)."""
    if at is None:
        return min(1.0, max(0.0, (t - scene["s"] - 0.15) / dur))
    j = int(at)
    if j < 0 or j >= len(scene["lines"]):
        return 1.0 if j < 0 else 0.0
    return min(1.0, max(0.0, (t - scene["lines"][j]["s"]) / dur))


DARK = {"board", "night"}
INDOOR = {"office", "bank", "hospital", "school", "shop", "paper"}     # (a title there gets a card under it)


def draw_visual(cv: Canvas, v: dict, scene: dict, t: float, box: tuple, cast: dict):
    """The scene's visual in its box: drawn in a 1000 x 760 panel of its own, scaled into the box."""
    cx, cy, bw, bh = box
    ink = "#ffffff" if scene.get("bg") in DARK else INK
    k = min(bw / 1000.0, bh / 760.0)
    kind = v.get("kind")
    st = t - scene["s"]
    with cv.at(cx, cy, 0, k):
        if kind == "title":
            a = back(_appear(scene, None, t, 0.8))
            with cv.at(0, -120, 0, max(0.01, a)):
                cv.text(v.get("title") or "", 0, 0, 96, "#ffffff", "black", outline=INK, stroke=8, width=960)
            if v.get("sub"):
                cv.text(v["sub"], 0, 150, 52, ink, "black", width=900, alpha=ease(_appear(scene, None, t - 0.5, 0.6)))
            P.money_bag(cv, -300 + math.sin(st * 2) * 10, 300, 1.0)
            for i in range(3):
                P.coin(cv, 220 + i * 90, 300 - abs(math.sin(st * 3 + i)) * 60, 1.0, st * 4 + i)
        elif kind == "flow":
            nodes = v.get("nodes") or []
            pos = {}
            n = len(nodes)
            for i, nd in enumerate(nodes):                 # a row, or two rows for more than three
                if n <= 3:
                    pos[nd["id"]] = (-330 + i * 660 / max(1, n - 1) if n > 1 else 0, 0)
                else:                                      # (a square: the first at the top left, round the clock)
                    pos[nd["id"]] = [(-270, -200), (270, -200), (270, 220), (-270, 220), (0, 10)][i % 5]
            for e in v.get("edges") or []:
                if e.get("from") not in pos or e.get("to") not in pos:
                    continue
                a_, b_ = pos[e["from"]], pos[e["to"]]
                path = P.curve((a_[0] + (60 if b_[0] > a_[0] else -60 if b_[0] < a_[0] else 0), a_[1] + (0 if b_[0] != a_[0] else 80)),
                               (b_[0] - (60 if b_[0] > a_[0] else -60 if b_[0] < a_[0] else 0), b_[1] - (0 if b_[0] != a_[0] else 80)),
                               0.22 if e.get("bend", 1) > 0 else -0.22)
                g = _appear(scene, e.get("at"), t, 0.8)
                P.arrow(cv, path, g, e.get("color") or INK, 9, 24)
                if g >= 1 and e.get("label"):
                    mid = P.along(path, 0.5)
                    P.price_tag(cv, mid[0], mid[1] - 64, e["label"], 0.85, e.get("tag", P.GOLD), _appear(scene, e.get("at"), t - 0.4, 0.5), 0)
                if g >= 1 and e.get("money", True):
                    for m in range(2):
                        ph = ((t * 0.55 + m * 0.5) % 1.0)
                        px, py = P.along(path, ph)
                        P.banknote(cv, px, py, 0.5, math.sin(t * 5 + m) * 12)
            for nd in nodes:
                x, y = pos[nd["id"]]
                P.node(cv, x, y, nd.get("label") or "", nd.get("icon") or "", nd.get("color") or P.BLUE,
                       _appear(scene, nd.get("at"), t, 0.5), 300, 170, nd.get("sub") or "")
        elif kind == "contract":
            w_ = _appear(scene, v.get("at"), t, 2.2)
            P.document(cv, -160, 0, 1.25, v.get("title") or "CONTRACT", 7, w_,
                       v.get("price") if _appear(scene, v.get("price_at"), t, 0.4) > 0 else "",
                       _appear(scene, v.get("at"), t, 0.5), -4)
            if v.get("stamp"):
                P.stamp(cv, 60, 250, 1.0, v["stamp"], _appear(scene, v.get("stamp_at"), t, 0.5))
            for i, note in enumerate(v.get("notes") or []):
                a = _appear(scene, note.get("at"), t, 0.4)
                if a > 0:
                    P.tick(cv, 160, -230 + i * 170, 0.9, bool(note.get("ok")), a)
                    cv.text(note.get("text") or "", 370, -230 + i * 170, 40, ink, "black", width=320, alpha=min(1, a * 1.5))
        elif kind == "bars":
            P.bars(cv, 0, 300, [float(x) for x in v.get("values") or [1]], v.get("labels") or [], v.get("colors") or [P.GREEN, P.RED],
                   ease(_appear(scene, v.get("at"), t, 1.6)), 760, 520, v.get("unit") or "", ink=ink)
            if v.get("title"):
                cv.text(v["title"], 0, -330, 56, ink, "black", width=900)
        elif kind == "road":
            holes = _appear(scene, v.get("holes_at"), t, 1.5) if v.get("holes_at") is not None else (0.0 if v.get("fresh") else 1.0)
            patch = _appear(scene, v.get("patch_at"), t, 1.5) if v.get("patch_at") is not None else 0.0
            P.road(cv, 0, 200, 960, holes, patch, t)
            for i, x in enumerate((-430, 430)):
                P.cone(cv, x, 300, 0.8)
            if v.get("truck"):
                tx = lerp(-700, -150, ease(_appear(scene, v.get("truck_at"), t, 2.0)))
                P.truck(cv, tx, 140, 0.6, 1, P.GOLD, t)
            cal = v.get("calendar") or []
            shown = None
            for c in cal:
                if _appear(scene, c[2] if len(c) > 2 else None, t, 0.3) > 0:
                    shown = c
            if shown:
                P.calendar(cv, 330, -180, 0.9, str(shown[0]), str(shown[1]))
        elif kind == "counter":
            g = ease(_appear(scene, v.get("at"), t, 2.0))
            val = lerp(float(v.get("from") or 0), float(v.get("to") or 0), g)
            P.counter(cv, 0, -40, val, 110, v.get("prefix", "$"), v.get("suffix", ""), v.get("color") or P.RED)
            if v.get("label"):
                cv.text(v["label"], 0, 90, 48, ink, "black", width=900)
            P.cash_stack(cv, -260, 300, 1.0, 2 + int(6 * g))
            P.cash_stack(cv, 260, 300, 1.0, 2 + int(5 * g))
        elif kind == "list":
            if v.get("title"):
                cv.text(v["title"], 0, -320, 60, ink, "black", width=900)
            for i, it in enumerate(v.get("items") or []):
                a = _appear(scene, it.get("at"), t, 0.4)
                if a <= 0:
                    continue
                y = -190 + i * 140
                P.tick(cv, -400, y, 0.85, bool(it.get("ok")), a)
                cv.text(it.get("text") or "", -320, y, 50, ink, "black", width=780, anchor="lm", alpha=min(1, a * 1.5))
        elif kind == "compare":
            for i, side in enumerate(v.get("sides") or []):
                a = _appear(scene, side.get("at"), t, 0.5)
                x = -260 + i * 520
                if a > 0:
                    P.price_tag(cv, x, -40, side.get("price") or "", 1.5, side.get("color") or (P.GREEN if i == 0 else P.RED), a, 0)
                    cv.text(side.get("label") or "", x, 110, 46, ink, "black", width=440, alpha=min(1, a * 1.5))
            if len(v.get("sides") or []) == 2:
                cv.text("vs", 0, -40, 60, ink, "black")
        elif kind == "bag":
            P.money_bag(cv, 0, 60, 1.8, v.get("label") or "$")
            if v.get("text"):
                cv.text(v["text"], 0, -300, 56, ink, "black", width=900)
        elif kind == "magnifier":
            P.document(cv, -60, 20, 1.1, v.get("title") or "TENDER", 7, 1.0, v.get("price") or "", 1.0, 3)
            ph = st * 0.9
            P.magnifier(cv, -60 + math.cos(ph) * 110, -40 + math.sin(ph * 1.3) * 120, 1.2)


def _bubble_for(cv: Canvas, ln: dict, x: float, top_y: float, t: float):
    a = min(1.0, max(0.0, (t - ln["s"]) / 0.3)) * min(1.0, max(0.0, (ln["e"] + 0.6 - t) / 0.3))
    if a > 0:
        w = min(cv.SW * 0.42 if cv.SW >= cv.SH else cv.SW * 0.8, 620)
        bx = min(max(x, w / 2 + 20), cv.SW - w / 2 - 20)
        P.bubble(cv, bx, top_y - 130, ln["text"], w, (-1 if bx > x else 1, 1), a, 34)


def draw_frame(cv: Canvas, film: dict, scene: dict, t: float, mouths: dict):
    """One picture of a scene at film time t. mouths: who -> mouth opening now."""
    st = t - scene["s"]
    zoom = 1.0 + 0.045 * min(1.0, st / max(1.0, scene["e"] - scene["s"]))
    cast = film["cast"]
    ln, j = _speaking(scene, t)
    speaker = ln["who"] if ln else None
    with cv.at(cv.SW / 2, cv.SH / 2, 0, zoom):
        with cv.at(-cv.SW / 2, -cv.SH / 2):
            gy = bgs.draw(cv, scene["bg"], t)
            names = _shown(film, scene)                    # (nobody else there: the narrator presents it)
            xs, sc, box = _layout(cv, len(names), bool(scene.get("visual")))
            if scene.get("visual") and box:
                if scene["bg"] not in DARK and (scene["visual"].get("kind") not in ("road", "title")
                                                 or (scene["visual"].get("kind") == "title" and scene["bg"] in INDOOR)):
                    bx, by, bw_, bh_ = box                 # (a light card under a scheme or a paper: it reads on any background)
                    a = ease(min(1.0, (t - scene["s"]) / 0.4))
                    cv.blend("#ffffff", 0.78 * a, rounded(bx - bw_ / 2 + 10, by - bh_ / 2 + 10, bw_ - 20, bh_ - 20, 36))
                draw_visual(cv, scene["visual"], scene, t, box, cast)
            last = scene["lines"][_line_at(scene, t)] if _line_at(scene, t) >= 0 else None
            for k, key in enumerate(names):
                c = cast[key]
                x = xs[k]
                if speaker in names and speaker != key:
                    look = 1 if xs[names.index(speaker)] > x else -1
                elif box and cv.SW >= cv.SH:
                    look = 1 if box[0] > x else -1
                else:
                    look = 1 if x < cv.SW / 2 else -1
                mine = last if last and last["who"] == key else None
                pose = (mine or {}).get("pose") or scene["pose"].get(key) or ("talk" if speaker == key else "idle")
                emo = (mine or {}).get("emotion") or scene["mood"].get(key) or ("happy" if speaker == key else "neutral")
                blink = 1.0 if (t * 0.9 + k * 0.37) % 3.7 < 0.12 else 0.0
                walk = None
                if key in (scene.get("enter") or []) and st < WALK_IN:     # walking in from the nearer side
                    side = -1 if x < cv.SW / 2 else 1
                    x += side * (1 - ease(st / WALK_IN)) * (cv.SW * 0.55)
                    walk, look, pose, emo = st * 9.0, -side, "idle", emo
                ch.draw(cv, c, x, gy, sc, look, pose, None, 0.0, emo, mouths.get(key, 0.0) if speaker == key else 0.0, blink,
                        t + k, walk, (0.6 * look, 0.0))
                if speaker == key and ln.get("bubble"):
                    _bubble_for(cv, ln, x, gy - 600 * sc, t)


# ------------------------------------------------------------------------------------------------- sound

def _read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        n, ch_, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float32)
    a /= 32768.0 if sw == 2 else 2147483648.0
    if ch_ > 1:
        a = a.reshape(-1, ch_).mean(axis=1)
    if sr != SR:                                          # (simple resampling: the voices are 48 kHz already)
        idx = np.arange(0, len(a), sr / SR)
        a = np.interp(idx, np.arange(len(a)), a).astype(np.float32)
    return a


def _sfx(kind: str) -> np.ndarray:
    """Short sounds made here (no files): a whoosh between scenes, a pop when something appears, a stamp, coins."""
    rng = np.random.default_rng(3)
    if kind == "whoosh":
        n = int(SR * 0.45)
        x = rng.standard_normal(n).astype(np.float32)
        env = np.sin(np.linspace(0, math.pi, n)) ** 2
        k = np.linspace(0.02, 0.2, n)                      # (a moving low-pass: one-pole filter, rising cutoff)
        y = np.zeros(n, np.float32)
        acc = 0.0
        for i in range(n):
            acc += k[i] * (x[i] - acc)
            y[i] = acc
        return y * env * 0.5
    if kind == "pop":
        n = int(SR * 0.12)
        tt = np.arange(n) / SR
        return (np.sin(2 * math.pi * (700 + 900 * tt / tt[-1]) * tt) * np.exp(-tt * 30) * 0.35).astype(np.float32)
    if kind == "stamp":
        n = int(SR * 0.25)
        tt = np.arange(n) / SR
        return ((np.sin(2 * math.pi * 90 * tt) * 0.8 + rng.standard_normal(n) * 0.15) * np.exp(-tt * 22) * 0.6).astype(np.float32)
    if kind == "coins":
        n = int(SR * 0.5)
        out = np.zeros(n, np.float32)
        for k in range(6):
            s0 = int(SR * 0.07 * k)
            tt = np.arange(n - s0) / SR
            out[s0:] += (np.sin(2 * math.pi * (2400 + 300 * k) * tt) * np.exp(-tt * 40) * 0.12).astype(np.float32)
        return out
    return np.zeros(1, np.float32)


def mix(tl: dict, sounds: bool = True) -> np.ndarray:
    total = int(SR * (tl["seconds"] + 0.5))
    out = np.zeros(total, np.float32)

    def put(a: np.ndarray, at: float, gain: float = 1.0):
        i = int(at * SR)
        if i >= total or len(a) == 0:
            return
        n = min(len(a), total - i)
        out[i:i + n] += a[:n] * gain
    for i, s in enumerate(tl["scenes"]):
        if sounds and i > 0:
            put(_sfx("whoosh"), max(0.0, s["s"] - 0.2), 0.6)
        v = s.get("visual") or {}
        if sounds and v.get("kind") == "contract" and v.get("stamp_at") is not None and int(v["stamp_at"]) < len(s["lines"]):
            put(_sfx("stamp"), s["lines"][int(v["stamp_at"])]["s"] + 0.2, 0.8)
        if sounds and v.get("kind") in ("flow", "counter", "bag", "title"):
            put(_sfx("coins"), s["s"] + 0.6, 0.5)
        for ln in s["lines"]:
            if ln.get("wav") and Path(ln["wav"]).is_file():
                put(_read_wav(ln["wav"]), ln["s"], 1.0)
    peak = float(np.max(np.abs(out))) if len(out) else 0.0
    if peak > 0.98:
        out *= 0.98 / peak
    return out


def mouth_tracks(tl: dict) -> dict:
    """Per line: how open the mouth is in each picture (from the voice's loudness; without a voice, from the words)."""
    out = {}
    for i, s in enumerate(tl["scenes"]):
        for j, ln in enumerate(s["lines"]):
            n = max(1, int(math.ceil((ln["e"] - ln["s"]) * FPS)) + 2)
            if ln.get("wav") and Path(ln["wav"]).is_file():
                a = _read_wav(ln["wav"])
                hop = SR // FPS
                env = [float(np.sqrt(np.mean(a[k * hop:(k + 1) * hop] ** 2))) if k * hop < len(a) else 0.0 for k in range(n)]
                top = sorted(env)[int(len(env) * 0.95)] if env else 1.0
                env = [min(1.0, e_ / max(1e-4, top)) for e_ in env]
            else:                                          # syllables: open and close along the words
                env = []
                for k in range(n):
                    tt = ln["s"] + k / FPS
                    on = any(w["s"] <= tt <= w["e"] for w in ln["words"])
                    env.append((0.55 + 0.45 * math.sin(tt * 18.0)) if on else 0.0)
            out[f"{i}.{j}"] = ch.visemes(env, FPS)
    return out


# ------------------------------------------------------------------------------------------------- the film

def captions_ass(tl: dict, width: int, height: int, opts: dict, work: Path) -> Path | None:
    from .. import textfx as tf, voice as vo
    words = [w for s in tl["scenes"] for ln in s["lines"] if not ln.get("bubble") for w in ln["words"]]   # (a bubble shows its own)
    if not words:
        return None
    o = tf.options(**opts)
    cs = vo.style_cues(words, o)
    p = work / "captions.ass"
    p.write_text(tf.document(width, height, cs, [], o, 0.0), "utf-8")
    return p


def render(script: dict, out: Path, work: Path, voices: dict | None = None, captions: dict | None = None,
           progress=None, stop=None, sounds: bool = True, every: int = 1) -> dict:
    """The film as an MP4. captions: the look of the captions (textfx options) or None for none. every: draw only
    every n-th picture (a quick preview); progress(share), stop() -> True ends it."""
    from .. import textfx as tf, voice as vo
    film = check_script(script)
    W, H = FORMATS[film["format"]]
    tl = timeline(film, voices)
    work.mkdir(parents=True, exist_ok=True)
    audio = mix(tl, sounds)
    with wave.open(str(work / "sound.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    vf = []
    if captions is not None:
        ass = captions_ass(tl, W, H, captions, work)
        if ass:
            fonts = tf.install_fonts(work)
            vf.append("ass=captions.ass" + (":fontsdir=fonts" if fonts else ""))
    vf.append("format=yuv420p")
    frames = int(math.ceil(tl["seconds"] * FPS))
    fps_out = FPS / max(1, every)
    enc = (["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"] if vo.nvenc_ok() else
           ["-c:v", "libx264", "-preset", "medium" if every == 1 else "veryfast", "-crf", "19"])
    cmd = [vo._ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{W}x{H}", "-r", f"{fps_out:g}", "-i", "-", "-i", "sound.wav", "-vf", ",".join(vf), *enc,
           "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out.resolve())]
    from .. import auto_edit as ae
    from ..platform_adapter import process_kwargs
    errf = (work / "ffmpeg.log").open("wb")
    proc = subprocess.Popen(cmd, cwd=str(work), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errf,
                            **process_kwargs({}))
    ae._attach_job_object(proc)                            # (closed with the program; Stop and Quit end it)
    vo._track(proc)
    mouths = mouth_tracks(tl)
    cv = Canvas(W, H, 1920 if W >= H else 1080)
    prev_last = None
    try:
        for f in range(0, frames, max(1, every)):
            if stop is not None and f % 30 == 0 and stop():
                raise FilmError("Stopped.")
            t = f / FPS
            si = next((i for i, s in enumerate(tl["scenes"]) if s["s"] <= t < s["e"]), len(tl["scenes"]) - 1)
            scene = tl["scenes"][si]
            m = {}
            for j, ln in enumerate(scene["lines"]):
                if ln["s"] <= t <= ln["e"]:
                    tr = mouths.get(f"{si}.{j}") or []
                    k = int((t - ln["s"]) * FPS)
                    m[ln["who"]] = tr[k] if k < len(tr) else 0.0
            cv.push(0, 0)
            draw_frame(cv, film, scene, t, m)
            cv.pop()
            st = t - scene["s"]
            if si > 0 and st < 0.3 and prev_last is not None:   # a quick cross-fade between scenes
                a = st / 0.3
                cv.img[:] = (cv.img.astype(np.float32) * a + prev_last.astype(np.float32) * (1 - a)).astype(np.uint8)
            if t + 1.0 / FPS * max(1, every) >= scene["e"]:
                prev_last = cv.img.copy()
            try:
                proc.stdin.write(cv.img.tobytes())
            except OSError:                                # (FFmpeg stopped: its own words say why)
                proc.wait(timeout=60)
                tail = (work / "ffmpeg.log").read_text("utf-8", errors="replace").strip().splitlines() or ["?"]
                raise FilmError("The film could not be encoded (" + tail[-1][:200] + ").")
            if progress is not None and f % 30 == 0:
                progress(f / max(1, frames))
        proc.stdin.close()
        rc = proc.wait()
    except BaseException:
        try:
            proc.kill()
            proc.wait(timeout=30)
        except Exception:
            pass
        raise
    finally:
        vo._untrack(proc)
        errf.close()
    err = (work / "ffmpeg.log").read_text("utf-8", errors="replace")
    if rc != 0 or not out.is_file():
        raise FilmError("The film could not be encoded (" + (err.strip().splitlines() or ["?"])[-1][:200] + ").")
    (work / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), "utf-8")
    return {"seconds": tl["seconds"], "scenes": len(tl["scenes"]), "lines": sum(len(s["lines"]) for s in tl["scenes"]),
            "width": W, "height": H, "file": str(out)}
