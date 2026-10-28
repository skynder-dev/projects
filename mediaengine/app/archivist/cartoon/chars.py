"""Cartoon characters: a description (a dict: build, skin, hair, face, clothes, a hat, glasses ...) drawn the same
way every time, so a character looks the same in every scene and every episode; a pose (arms, lean, head), an
emotion (eyes, brows, mouth), a mouth opening (lip sync), blinking and breathing, a direction it looks to.

Drawn in the character's own units: its feet at (0, 0), up is negative y, about 560 units tall (a medium build).
"""
from __future__ import annotations

import hashlib
import math
import random
import re

from .draw import INK, Canvas, arc, bezier, ease, lerp, rounded, shade

SKINS = ["#f6d3b8", "#efc29f", "#e0a982", "#c98d63", "#a8704c", "#80513a", "#5d3a2a"]
HAIRS = ["#2b211c", "#4a3326", "#7a5232", "#b07a45", "#d6b26e", "#8f8f96", "#e7e2d8", "#a33c2a", "#1d1d24"]
CLOTHES = ["#2f4a7a", "#3f6f5a", "#7a3b3b", "#4b4b5c", "#6a4c8c", "#2d6f8f", "#8a6a2e", "#365c3a", "#5c3a2e", "#28324a"]
HAIR_STYLES = ["short", "side", "spiky", "bob", "curly", "ponytail", "bald", "long", "buzz"]
OUTFITS = ["suit", "shirt", "hoodie", "vest", "dress", "sweater"]

# pose: per arm (the upper arm's direction, how much more the forearm turns) in degrees: 0 = straight down, 90 =
# towards the side the character looks to, 180 = up, -90 = away; the body's lean and the head's tilt. "a" is the arm
# on the side it looks to, "b" the other one.
POSES = {
    "idle": dict(a=(8, 6), b=(-8, -6), lean=0, tilt=0),
    "talk": dict(a=(28, 55), b=(-10, -8), lean=2, tilt=3),
    "explain": dict(a=(38, 70), b=(-38, -70), lean=0, tilt=2),
    "point": dict(a=(98, 6), b=(-10, -8), lean=4, tilt=4),
    "point_up": dict(a=(150, 15), b=(-10, -8), lean=0, tilt=-4),
    "shrug": dict(a=(45, 60), b=(-45, -60), lean=0, tilt=-6),
    "cross": dict(a=(-18, -72), b=(18, 72), lean=-2, tilt=0),
    "think": dict(a=(-25, -135), b=(-10, -8), lean=0, tilt=8),
    "wave": dict(a=(140, 40), b=(-8, -6), lean=0, tilt=4),
    "hands_up": dict(a=(160, 20), b=(-160, -20), lean=0, tilt=0),
    "count": dict(a=(-6, -78), b=(6, 78), lean=4, tilt=6),
    "present": dict(a=(70, 10), b=(-12, -10), lean=3, tilt=2),
    "facepalm": dict(a=(-60, -120), b=(-10, -8), lean=4, tilt=12),
    "fist": dict(a=(60, 100), b=(-30, -40), lean=-3, tilt=-3),
    "sneaky": dict(a=(-6, -78), b=(6, 78), lean=8, tilt=6),
}
EMOTIONS = ["neutral", "happy", "angry", "sad", "surprised", "sly", "worried"]


def make(name: str, role: str = "", seed: str | None = None, **over) -> dict:
    """A new character from a name (the same name: the same character), a role suggesting clothes, and overrides."""
    rnd = random.Random(int(hashlib.sha256((seed or name).encode("utf-8")).hexdigest()[:12], 16))
    role = (role or "").lower()
    outfit = ("suit" if any(w in role for w in ("mayor", "official", "boss", "banker", "director", "minister", "lawyer", "ceo",
                                                 "мэр", "чиновник", "депутат", "директор", "министр", "банкир", "юрист", "начальник",
                                                 "primar", "funcționar", "director"))
              else "vest" if any(w in role for w in ("worker", "builder", "foreman", "engineer", "рабоч", "строител", "прораб",
                                                     "инженер", "muncitor", "constructor"))
              else "coat" if re.search(r"\b(doctor|nurse|medics?|surgeon|pharmacist|paramedic|asistent[aă]?|farmacist[aă]?|chirurg)\b"
                                       r"|врач|доктор|медсестр|медбрат|фармацевт|аптекар|хирург", role)
              else "hoodie" if any(w in role for w in ("student", "blogger", "young", "hacker", "студент", "блогер"))
              else rnd.choice(OUTFITS))
    if "female" not in over and re.search(r"(?i)\b(woman|girl|she|mrs|ms|lady|женщин|девушк|она|госпожа|doamna)\b|(?:ова|ева|ина|ская|ая|ка)\b", role + " " + name):
        over["female"] = True
    elif "female" not in over and re.search(r"(?i)\b(man|he|mr|sir|guy|мужчин|парень|он|господин|domnul)\b|(?:ов|ев|ин|ский|ий)\b",
                                            role + " " + name):
        over["female"] = False
    female = over.pop("female", rnd.random() < 0.45)
    style = rnd.choice(["bob", "long", "ponytail", "curly"] if female else ["short", "side", "spiky", "bald", "curly", "buzz"])
    c = {
        "name": name, "role": role, "female": bool(female),
        "build": rnd.choice(["thin", "medium", "medium", "heavy"]),
        "height": round(rnd.uniform(0.94, 1.06), 3),
        "skin": rnd.choice(SKINS), "hair": rnd.choice(HAIRS), "hair_style": style,
        "face": rnd.choice(["round", "oval", "square"]),
        "beard": (rnd.choice(["none", "none", "mustache", "stubble", "full"]) if not female else "none"),
        "glasses": rnd.random() < 0.3,
        "outfit": ("dress" if rnd.random() < 0.4 else "blazer") if female and outfit == "suit" else outfit,
        "cloth": "#f4f6f8" if outfit == "coat" else rnd.choice(CLOTHES), "tie": rnd.choice(["#b8322f", "#d9a72b", "#2f6fb8", "#1f2433"]),
        "pants": rnd.choice(["#2c2f3d", "#3b4256", "#4a3c30", "#24324d", "#5a5f6a"]),
        "shoes": rnd.choice(["#1f1d22", "#4a2f22", "#2c2c34"]),
        "hat": "hardhat" if any(w in role for w in ("worker", "builder", "foreman", "рабоч", "строител", "прораб", "muncitor")) else "none",
    }
    c.update(over)
    return c


def _body(c: dict) -> dict:
    """Sizes of a character's parts (its units)."""
    k = float(c.get("height") or 1.0)
    wide = {"thin": 0.82, "medium": 1.0, "heavy": 1.28}.get(c.get("build"), 1.0)
    return dict(head_w=150 * (1.04 if c.get("face") == "round" else 1.0), head_h=170 * (1.06 if c.get("face") == "oval" else 1.0),
                torso_w=150 * wide, torso_h=180 * k, leg_h=150 * k, arm_u=88 * k, arm_l=82 * k, wide=wide, k=k,
                neck=16)


def draw(cv: Canvas, c: dict, x: float, y: float, scale: float = 1.0, look: int = 1, pose: str = "idle",
         pose2: str | None = None, mix_t: float = 0.0, emotion: str = "neutral", mouth: float = 0.0, blink: float = 0.0,
         t: float = 0.0, walk: float | None = None, gaze: tuple = (0.0, 0.0), alpha_shadow: float = 0.2):
    """A character with its feet at stage (x, y). look: 1 right, -1 left. pose2/mix_t: halfway between two poses.
    mouth: 0 closed .. 1 wide open. t: seconds (breathing). walk: the step's phase (None: standing)."""
    b = _body(c)
    p = dict(POSES.get(pose, POSES["idle"]))
    if pose2 and mix_t > 0:
        q = POSES.get(pose2, POSES["idle"])
        m = ease(mix_t)
        p = {key: (tuple(lerp(u, v, m) for u, v in zip(p[key], q[key])) if isinstance(p[key], tuple) else lerp(p[key], q[key], m))
             for key in p}
    breath = math.sin(t * 2.2) * 2.5
    cv.shadow(x, y + 4 * scale, 120 * scale * b["wide"], 18 * scale, alpha_shadow)
    with cv.at(x, y, 0, scale * look, scale):
        legs = b["leg_h"]
        hip_y = -legs
        _legs(cv, c, b, walk)
        lean = p["lean"] + (math.sin(walk * 2) * 2 if walk is not None else 0)
        bob = -abs(math.sin(walk)) * 8 if walk is not None else breath * 0.4
        with cv.at(0, hip_y + bob, lean):
            top = -b["torso_h"]
            sh_y = top + 26
            sh_x = b["torso_w"] / 2 - 10
            swing = math.sin(walk) * 22 if walk is not None else 0
            # the body, the arm away from the look, the arm on its side (in front)
            _torso(cv, c, b, breath)
            _arm(cv, c, b, -sh_x, sh_y, p["b"][0] - swing, p["b"][1], back=True)
            _arm(cv, c, b, sh_x, sh_y, p["a"][0] + swing, p["a"][1], back=False)
            with cv.at(0, top - b["neck"] + breath * 0.3, p["tilt"] + math.sin(t * 1.3) * 1.2):
                _head(cv, c, b, emotion, mouth, blink, gaze)


def _legs(cv: Canvas, c: dict, b: dict, walk):
    L = b["leg_h"]
    sp = 24 * b["wide"]
    pants, shoe = c.get("pants", "#2c2f3d"), c.get("shoes", "#1f1d22")
    for side, ph in ((-1, 0.0), (1, math.pi)):
        a = math.sin((walk or 0) + ph) * (24 if walk is not None else 0)
        with cv.at(side * sp, -L, a):
            if c.get("outfit") == "dress":
                cv.rect(-11, 0, 22, L - 14, c.get("skin"), INK, 3, 8)
            else:
                cv.rect(-17 * b["wide"] ** 0.4, -6, 34 * b["wide"] ** 0.4, L - 8, pants, INK, 3.5, 10)
            cv.poly(rounded(-20 + 8 * 1, L - 22, 50, 24, 11), shoe, INK, 3.5)


def _torso(cv: Canvas, c: dict, b: dict, breath: float):
    w, h = b["torso_w"], b["torso_h"]
    cloth = c.get("cloth", "#2f4a7a")
    outfit = c.get("outfit", "shirt")
    top, bot = -h, 6
    if outfit == "dress":
        body = [(-w / 2 + 8, top + 8), (w / 2 - 8, top + 8), (w / 2 + 22, bot + 40), (-w / 2 - 22, bot + 40)]
    else:
        body = [(-w / 2 + 6, top + 6), (w / 2 - 6, top + 6), (w / 2 + 2, bot), (-w / 2 - 2, bot)]
    cv.poly(rounded(-w / 2, top, w, h + 8 + (34 if outfit == "dress" else 0), 34), cloth, INK, 4)
    if outfit == "dress":
        cv.poly([(-w / 2 - 2, bot - 30), (w / 2 + 2, bot - 30), (w / 2 + 26, bot + 46), (-w / 2 - 26, bot + 46)], cloth, INK, 4)
    if outfit == "suit":
        shirt = "#f2f2ee"
        cv.poly([(-26, top + 2), (26, top + 2), (0, top + 92)], shirt, INK, 3)
        tie = c.get("tie", "#b8322f")
        cv.poly([(-8, top + 8), (8, top + 8), (12, top + 74), (0, top + 92), (-12, top + 74)], tie, INK, 3)
        dark = shade(cloth, -0.18)
        cv.poly([(-26, top + 2), (-4, top + 96), (-34, top + 54)], dark, INK, 3)
        cv.poly([(26, top + 2), (4, top + 96), (34, top + 54)], dark, INK, 3)
        for yy in (top + 110, top + 140):
            cv.circle(0, yy, 5, shade(cloth, -0.35))
    elif outfit == "coat":                                 # a doctor's white coat over blue scrubs, a stethoscope
        cv.poly([(-30, top + 2), (30, top + 2), (0, top + 80)], "#5f9fc8", INK, 3)
        cv.poly([(-30, top + 2), (-4, top + 118), (-40, top + 70)], "#e3e8ec", INK, 3)
        cv.poly([(30, top + 2), (4, top + 118), (40, top + 70)], "#e3e8ec", INK, 3)
        cv.line(arc(0, top + 10, 34, 70, 200, 340, 14), "#3a3f4c", 5)
        cv.circle(-22, top + 84, 9, "#9aa4b2", INK, 3)
        cv.rect(w / 2 - 50, top + 100, 30, 34, "#e3e8ec", INK, 3, 4)
        cv.line([(w / 2 - 40, top + 92), (w / 2 - 40, top + 112)], "#2f6fb8", 4)
        for yy in (top + 132, top + 162):
            cv.circle(0, yy, 4, "#9aa4b2")
    elif outfit == "blazer":
        cv.poly([(-30, top + 2), (30, top + 2), (0, top + 70)], "#f2f2ee", INK, 3)
        dark = shade(cloth, -0.18)
        cv.poly([(-30, top + 2), (-6, top + 112), (-38, top + 60)], dark, INK, 3)
        cv.poly([(30, top + 2), (6, top + 112), (38, top + 60)], dark, INK, 3)
        cv.circle(0, top + 128, 5, shade(cloth, -0.35))
    elif outfit == "vest":
        cv.poly([(-w / 2 + 10, top + 30), (-14, top + 30), (-14, bot - 4), (-w / 2 + 6, bot - 4)], "#f08a24", INK, 3)
        cv.poly([(w / 2 - 10, top + 30), (14, top + 30), (14, bot - 4), (w / 2 - 6, bot - 4)], "#f08a24", INK, 3)
        for side in (-1, 1):
            cv.rect(side * w / 2 - (0 if side < 0 else 28) + (6 if side < 0 else -6), top + 92, 28, 10, "#e8e8d0")
    elif outfit == "hoodie":
        cv.poly(arc(0, top + 8, 44, 30, 0, 180, 12), shade(cloth, -0.15), INK, 3)
        cv.line([(-10, top + 30), (-12, top + 70)], "#e8e8e8", 3)
        cv.line([(10, top + 30), (12, top + 70)], "#e8e8e8", 3)
        cv.rect(-40, top + 120, 80, 40, shade(cloth, -0.1), INK, 3, 12)
    elif outfit == "sweater":
        cv.poly(arc(0, top + 4, 30, 18, 0, 180, 10), shade(cloth, 0.25), INK, 3)
        for yy in range(int(top + 40), int(bot - 10), 26):
            cv.line([(-w / 2 + 14, yy), (w / 2 - 14, yy)], shade(cloth, -0.12), 3)
    else:                                                  # a shirt with a collar
        cv.poly([(-24, top + 2), (0, top + 26), (-10, top + 40)], shade(cloth, 0.3), INK, 3)
        cv.poly([(24, top + 2), (0, top + 26), (10, top + 40)], shade(cloth, 0.3), INK, 3)
        for yy in (top + 60, top + 95, top + 130):
            cv.circle(0, yy, 4, shade(cloth, -0.35))


def _arm(cv: Canvas, c: dict, b: dict, sx: float, sy: float, a_up: float, bend: float, back: bool):
    """An arm from the shoulder (sx, sy): the upper arm a_up degrees from straight down (towards the look), the
    forearm turned bend degrees more."""
    side = 1 if sx > 0 else -1
    cloth = c.get("cloth", "#2f4a7a")
    col = shade(cloth, -0.12) if back else cloth
    if c.get("outfit") == "vest":
        col = shade("#d8d4c8", -0.1) if back else "#d8d4c8"
    thick = 34 * b["wide"] ** 0.5
    with cv.at(sx, sy, -a_up):
        cv.rect(-thick / 2, -8, thick, b["arm_u"] + 14, col, INK, 3.5, thick / 2)
        with cv.at(0, b["arm_u"], -bend):
            cv.rect(-thick / 2 + 2, -8, thick - 4, b["arm_l"] + 6, col, INK, 3.5, thick / 2)
            cv.circle(0, b["arm_l"] + 12, 19, c.get("skin"), INK, 3.5)
            cv.circle(side * 12, b["arm_l"] + 2, 7, c.get("skin"), INK, 2.5)


def _head(cv: Canvas, c: dict, b: dict, emotion: str, mouth: float, blink: float, gaze: tuple):
    hw, hh = b["head_w"], b["head_h"]
    skin = c.get("skin", "#efc29f")
    hair = c.get("hair", "#2b211c")
    style = c.get("hair_style", "short")
    cy = -hh / 2 - 6
    cv.rect(-18, -26, 36, 34, shade(skin, -0.08), INK, 3, 8)              # the neck
    if style in ("long", "ponytail", "bob", "curly"):                       # hair behind the head
        if style == "long":
            cv.rect(-hw / 2 - 26, cy - hh / 2 + 6, hw + 52, hh + 46, hair, INK, 4, 56)
        elif style == "bob":
            cv.rect(-hw / 2 - 26, cy - hh / 2 + 2, hw + 52, hh * 0.98, hair, INK, 4, 64)
        elif style == "ponytail":
            cv.ellipse(-hw / 2 - 10, cy - 6, 30, 48, hair, INK, 4)
        elif style == "curly":
            for k in range(9):
                a = math.radians(-180 + k * 22.5)
                cv.circle(math.cos(a) * hw * 0.55, cy - 4 + math.sin(a) * hh * 0.55, 34, hair, INK, 3.5)
    for side in (-1, 1):                                                   # ears
        cv.ellipse(side * hw / 2, cy + 6, 16, 22, skin, INK, 3.5)
    face = c.get("face", "oval")
    r = {"round": hw / 2, "oval": hw / 2.3, "square": hw / 4}.get(face, hw / 2.4)
    cv.poly(rounded(-hw / 2, cy - hh / 2, hw, hh, r, 8), skin, INK, 4)
    cv.ellipse(-hw * 0.28, cy + hh * 0.17, 14, 8, shade(skin, -0.06))       # cheeks
    cv.ellipse(hw * 0.28, cy + hh * 0.17, 14, 8, shade(skin, -0.06))
    if c.get("beard") == "stubble":
        cv.blend("#3a3030", 0.18, arc(0, cy + hh * 0.24, hw * 0.44, hh * 0.3, 0, 180, 18))
    elif c.get("beard") == "full":
        cv.poly(arc(0, cy + hh * 0.12, hw * 0.5, hh * 0.42, -5, 185, 18), hair, INK, 3.5)
    _hair_front(cv, c, hw, hh, cy, hair, style)
    _eyes(cv, emotion, blink, gaze, hw, hh, cy, c)
    if c.get("female") and blink <= 0.5:                                    # lashes
        for side in (-1, 1):
            ex, ey = side * hw * 0.2, cy - hh * 0.04
            cv.line([(ex + side * 13, ey - 14), (ex + side * 22, ey - 22)], INK, 3.5)
            cv.line([(ex + side * 4, ey - 19), (ex + side * 8, ey - 28)], INK, 3.5)
    cv.poly(bezier((-4, cy + hh * 0.02), (-12, cy + hh * 0.14), (-2, cy + hh * 0.17), (8, cy + hh * 0.15), 8),
            None, shade(skin, -0.35), 3)                                   # the nose
    _mouth(cv, emotion, mouth, hw, hh, cy, skin, "#c4505e" if c.get("female") else None)
    if c.get("beard") == "mustache":
        cv.poly(bezier((-34, cy + hh * 0.25), (-20, cy + hh * 0.14), (20, cy + hh * 0.14), (34, cy + hh * 0.25), 10)
                + [(0, cy + hh * 0.2)], hair, INK, 3)
    if c.get("glasses"):
        for side in (-1, 1):
            cv.rect(side * hw * 0.2 - 24, cy - hh * 0.08, 48, 36, None, INK, 4, 10)
        cv.line([(-hw * 0.2 + 24, cy - hh * 0.01), (hw * 0.2 - 24, cy - hh * 0.01)], INK, 4)
    if c.get("hat") == "hardhat":
        cv.poly(arc(0, cy - hh * 0.32, hw * 0.56, hh * 0.42, 180, 360, 20), "#f2c12e", INK, 4)
        cv.rect(-hw * 0.66, cy - hh * 0.36, hw * 1.32, 18, "#f2c12e", INK, 4, 8)
        cv.rect(-8, cy - hh * 0.72, 16, hh * 0.36, shade("#f2c12e", -0.15))


def _hair_front(cv, c, hw, hh, cy, hair, style):
    top = cy - hh / 2
    if style == "bald":
        cv.rect(-hw / 2 - 4, cy - hh * 0.12, 22, hh * 0.32, hair, INK, 3, 10)
        cv.rect(hw / 2 - 18, cy - hh * 0.12, 22, hh * 0.32, hair, INK, 3, 10)
        cv.ellipse(-hw * 0.18, top + hh * 0.18, 26, 10, shade(c.get("skin"), 0.25))
        return
    if style == "buzz":
        cv.poly(arc(0, top + hh * 0.36, hw * 0.52, hh * 0.42, 190, 350, 18), hair, INK, 3)
        return
    if style == "spiky":
        pts = []
        for k in range(8):
            x0 = -hw / 2 + k * hw / 7
            pts += [(x0, top + 30), (x0 + hw / 14, top - 26 - (k % 2) * 10)]
        cv.poly([(-hw / 2 - 2, top + 54)] + pts + [(hw / 2 + 2, top + 30), (hw / 2 + 2, top + 54)], hair, INK, 3.5)
        return
    if style == "curly":
        for k in range(7):
            cv.circle(-hw / 2 + 12 + k * (hw - 24) / 6, top + 14, 26, hair, INK, 3)
        return
    if style == "side":
        cv.poly(bezier((-hw / 2 - 4, top + 70), (-hw / 2 - 10, top - 26), (hw / 2 + 14, top - 30), (hw / 2 + 4, top + 60), 16)
                + [(hw * 0.1, top + 28)], hair, INK, 4)
        return
    if style in ("bob", "long", "ponytail"):
        cv.poly(bezier((-hw / 2 - 6, top + 90), (-hw / 2 - 12, top - 30), (hw / 2 + 12, top - 30), (hw / 2 + 6, top + 90), 16)
                + [(hw * 0.3, top + 34), (-hw * 0.1, top + 50), (-hw * 0.4, top + 40)], hair, INK, 4)
        return
    cv.poly(bezier((-hw / 2 - 2, top + 50), (-hw / 2 - 4, top - 24), (hw / 2 + 4, top - 24), (hw / 2 + 2, top + 50), 16)
            + [(hw * 0.25, top + 24), (-hw * 0.2, top + 30)], hair, INK, 4)


def _eyes(cv, emotion, blink, gaze, hw, hh, cy, c):
    ey = cy - hh * 0.04
    big = 1.25 if emotion == "surprised" else 1.0
    gx, gy = gaze
    for side in (-1, 1):
        ex = side * hw * 0.2
        if blink > 0.5:
            cv.line(arc(ex, ey + 2, 15, 7, 10, 170, 10), INK, 4)
        else:
            open_k = 1.0 - blink * 1.6
            if emotion == "sly":
                open_k *= 0.55
            elif emotion in ("angry",):
                open_k *= 0.8
            cv.ellipse(ex, ey, 16 * big, 21 * big * max(0.15, open_k), "#ffffff", INK, 3)
            cv.circle(ex + 5 + gx * 6, ey + 2 + gy * 6, 8.5 * big * max(0.4, min(1, open_k + 0.2)), "#20232e")
            cv.circle(ex + 8 + gx * 6, ey - 2 + gy * 6, 3, "#ffffff")
        # brows
        by = ey - 30 * big
        if emotion == "angry":
            pts = [(ex - 22, by - 6 if side < 0 else by + 10), (ex + 20, by + 10 if side < 0 else by - 6)]
        elif emotion in ("sad", "worried"):
            pts = [(ex - 20, by + 6 if side < 0 else by - 8), (ex + 20, by - 8 if side < 0 else by + 6)]
        elif emotion == "surprised":
            pts = [(ex - 20, by - 8), (ex, by - 16), (ex + 20, by - 8)]
        elif emotion == "sly":
            pts = [(ex - 20, by - (12 if side > 0 else 0)), (ex + 20, by - (16 if side > 0 else -4))]
        elif emotion == "happy":
            pts = [(ex - 20, by - 2), (ex, by - 9), (ex + 20, by - 2)]
        else:
            pts = [(ex - 20, by), (ex, by - 4), (ex + 20, by)]
        cv.line(pts, c.get("hair") if c.get("hair_style") != "bald" else INK, 7)


def _mouth(cv, emotion, mouth, hw, hh, cy, skin, lips=None):
    my = cy + hh * 0.3
    w = 44
    o = max(0.0, min(1.0, mouth))
    curve = {"happy": 10, "sly": 6, "angry": -6, "sad": -9, "worried": -5, "surprised": 0}.get(emotion, 3)
    if emotion == "surprised":
        o = max(o, 0.45)
    if o < 0.08:
        if emotion == "sly":
            cv.line(bezier((-w / 2, my), (-6, my + 4), (10, my + 2), (w / 2 + 6, my - 10), 10), INK, 4.5)
        else:
            cv.line(bezier((-w / 2, my - curve * 0.2), (-w / 4, my + curve), (w / 4, my + curve), (w / 2, my - curve * 0.2), 12),
                    lips or INK, 5.5 if lips else 4.5)
        return
    ow = w * (0.7 + 0.3 * (1 - o)) * (1.15 if emotion == "happy" else 1.0)
    oh = 6 + 30 * o
    pts = bezier((-ow / 2, my - curve * 0.25), (-ow / 3, my - oh * 0.25), (ow / 3, my - oh * 0.25), (ow / 2, my - curve * 0.25), 8) + \
        bezier((ow / 2, my - curve * 0.25), (ow / 3, my + oh), (-ow / 3, my + oh), (-ow / 2, my - curve * 0.25), 12)[1:]
    cv.poly(pts, "#6b2430", lips or INK, 4.5 if lips else 4)
    if o > 0.35:
        cv.ellipse(0, my + oh * 0.62, ow * 0.26, oh * 0.22, "#e2737c")
    if emotion == "happy" or o > 0.5:
        cv.rect(-ow * 0.32, my - oh * 0.2, ow * 0.64, max(4, oh * 0.22), "#ffffff", None, 0, 3)


def visemes(env: list, fps: int = 30) -> list:
    """How open the mouth is in each picture, from the voice's loudness per picture (0..1): quick to open, a little
    slower to close, never frozen half open on a long sound (it flutters)."""
    out, cur = [], 0.0
    for k, v in enumerate(env):
        target = max(0.0, min(1.0, v))
        if target > 0.08:
            target *= 0.75 + 0.25 * math.sin(k * 1.7)          # (talking mouths move, they do not hold a shape)
        cur = target if target > cur else lerp(cur, target, 0.55)
        out.append(cur)
    return out
