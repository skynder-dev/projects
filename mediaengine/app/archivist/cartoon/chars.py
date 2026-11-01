"""Cartoon characters: a description (a dict: build, skin, hair, face, clothes, a hat, glasses ...) drawn the same
way every time, so a character looks the same in every scene and every episode; a pose (arms, lean, head), an
emotion (eyes, brows, mouth), a mouth opening and its shape for the sound said (lip sync: "a", "o", "u", "e", lips
closed for m/b/p, teeth on the lip for f/v), blinking and breathing, a direction it looks to, nods and raised brows on the
words that matter, a gesture that swings a little past and settles.

Drawn in the character's own units: its feet at (0, 0), up is negative y, about 560 units tall (a medium build).
"""
from __future__ import annotations

import hashlib
import math
import random
import re

from .draw import INK, Canvas, arc, back, bezier, ease, lerp, rounded, shade

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
    "thumbs_up": dict(a=(18, 72), b=(-8, -6), lean=2, tilt=4),
    "hips": dict(a=(40, -98), b=(-40, 98), lean=-2, tilt=-3),
    "scratch": dict(a=(150, 82), b=(-8, -6), lean=0, tilt=-7),
    "phone": dict(a=(118, 100), b=(-10, -8), lean=0, tilt=-4),
    "money": dict(a=(30, 78), b=(-10, -8), lean=3, tilt=3),
    "paper": dict(a=(22, 96), b=(-10, -8), lean=2, tilt=2),
    "sit": dict(a=(4, -30), b=(-4, 30), lean=0, tilt=0),
}
# a gesture's hands: (the hand on the side it looks to, the other one, a thing held in the first one, the first arm in
# front of the face). Hands: "rest" (relaxed), "open" (fingers apart), "fist", "point" (the index finger out), "thumb"
# (a thumb up), "hold" (closed round what it holds). Things held: "phone" (at the ear), "money" (a fan of notes),
# "paper" (a sheet shown).
HANDS = {
    "idle": ("rest", "rest"), "talk": ("open", "rest"), "explain": ("open", "open"), "point": ("point", "rest"),
    "point_up": ("point", "rest"), "shrug": ("open", "open"), "cross": ("fist", "fist"), "think": ("fist", "rest"),
    "wave": ("open", "rest"), "hands_up": ("open", "open"), "count": ("fist", "fist"), "present": ("open", "rest"),
    "facepalm": ("open", "rest", None, True), "fist": ("fist", "fist"), "sneaky": ("rest", "rest"),
    "thumbs_up": ("thumb", "rest"), "hips": ("fist", "fist"), "scratch": ("open", "rest"),
    "phone": ("hold", "rest", "phone", True), "money": ("hold", "rest", "money"), "paper": ("hold", "rest", "paper"),
    "sit": ("rest", "rest"),
}
SEAT = 0.56                    # a seat's height, a share of the legs' length (sitting: the hips that low)
EMOTIONS = ["neutral", "happy", "angry", "sad", "surprised", "sly", "worried", "laugh", "scared"]


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


def _hands(pose: str, pose2: str | None, m: float) -> tuple:
    """(hand a, hand b, the thing held, how far it has come 0..1, the arm in front of the face) halfway between poses."""
    def of(p):
        h = HANDS.get(p or "idle", HANDS["idle"])
        return h[0], h[1], (h[2] if len(h) > 2 else None), bool(h[3]) if len(h) > 3 else False
    one = of(pose)
    if not pose2 or m <= 0:
        return one[0], one[1], one[2], 1.0, one[3]
    two = of(pose2)
    now = two if m >= 0.5 else one
    if one[2] == two[2]:
        k = 1.0
    elif now is two:
        k = min(1.0, (m - 0.5) * 2.5)                      # (a thing taken: it comes into the hand)
    else:
        k = max(0.0, 1.0 - m * 2.5)
    return now[0], now[1], (two[2] if now is two else one[2]) or (one[2] if now is two else two[2]), k, now[3]


def sit_drop(c: dict) -> float:
    """How much lower a sitting character's head is (its units)."""
    return (1 - SEAT) * _body(c)["leg_h"]


def draw(cv: Canvas, c: dict, x: float, y: float, scale: float = 1.0, look: int = 1, pose: str = "idle",
         pose2: str | None = None, mix_t: float = 0.0, emotion: str = "neutral", mouth: float = 0.0, blink: float = 0.0,
         t: float = 0.0, walk: float | None = None, gaze: tuple = (0.0, 0.0), alpha_shadow: float = 0.2,
         nod: float = 0.0, brow: float = 0.0, snap: bool = False, sit: float | None = None):
    """A character with its feet at stage (x, y). look: 1 right, -1 left. pose2/mix_t: halfway between two poses
    (snap: a new gesture - it swings a little past and settles). mouth: 0 closed .. 1 wide open, or (opening, the
    sound's shape: SHAPES). t: seconds (breathing, shifting the weight). walk: the step's phase (None: standing).
    nod: the head dips (0..1); brow: the brows go up (0..1). sit: 0 standing .. 1 sitting (None: the "sit" pose sits);
    hands, a thing held and the arm in front of the face come with the pose (HANDS)."""
    b = _body(c)
    p = dict(POSES.get(pose, POSES["idle"]))
    m = 0.0
    if pose2 and mix_t > 0:
        q = POSES.get(pose2, POSES["idle"])
        m = back(mix_t, 1.25) if snap else ease(mix_t)
        p = {key: (tuple(lerp(u, v, m) for u, v in zip(p[key], q[key])) if isinstance(p[key], tuple) else lerp(p[key], q[key], m))
             for key in p}
    hand_a, hand_b, held, held_k, front = _hands(pose, pose2, min(1.0, max(0.0, mix_t)) if pose2 else 0.0)
    if sit is None:
        sit = 1.0 if pose == "sit" and not (pose2 and mix_t >= 0.5 and pose2 != "sit") else 0.0
    sit = max(0.0, min(1.0, float(sit)))
    breath = math.sin(t * 2.2) * 2.5
    shake = 0.0
    if emotion == "laugh":                                 # (laughing: the shoulders bounce, the head goes back)
        shake = abs(math.sin(t * 13.0)) * 6
    elif emotion == "scared":                              # (scared: a small tremble)
        x += math.sin(t * 47.0) * 1.6 * scale
    cv.shadow(x, y + 4 * scale, 120 * scale * b["wide"], 18 * scale, alpha_shadow)
    with cv.at(x, y, 0, scale * look, scale):
        legs = b["leg_h"]
        hip_y = -legs + (1 - SEAT) * legs * sit
        _legs(cv, c, b, walk, sit)
        lean = p["lean"] + (math.sin(walk * 2) * 2 if walk is not None else math.sin(t * 0.8) * 1.1)   # (the weight shifts)
        if emotion == "laugh":
            lean -= 3
        elif emotion == "scared":
            lean -= 4
        bob = -abs(math.sin(walk)) * 8 if walk is not None else breath * 0.4 - shake
        with cv.at(0, hip_y + bob, lean):
            top = -b["torso_h"]
            sh_y = top + 26
            sh_x = b["torso_w"] / 2 - 10
            swing = math.sin(walk) * 22 if walk is not None else 0
            # the body, the arm away from the look, the arm on its side (in front; in front of the face too: a hand
            # on the face, a phone at the ear)
            _torso(cv, c, b, breath)
            _arm(cv, c, b, -sh_x, sh_y, p["b"][0] - swing, p["b"][1], back=True, hand=hand_b)
            arm_a = lambda: _arm(cv, c, b, sh_x, sh_y, p["a"][0] + swing, p["a"][1], back=False, hand=hand_a, held=held,
                                 held_k=held_k)
            if not front:
                arm_a()
            tilt = p["tilt"] + math.sin(t * 1.3) * 1.2 + nod * 2.5 - (4 if emotion == "laugh" else 0)
            with cv.at(0, top - b["neck"] + breath * 0.3 + nod * 7 - shake * 0.5, tilt):
                _head(cv, c, b, emotion, mouth, blink, gaze, brow)
            if front:
                arm_a()


def seat(cv: Canvas, c: dict, x: float, y: float, scale: float = 1.0, kind: str = "chair"):
    """What a character sits on, drawn before the character (it is behind): a chair indoors, a bench outdoors; seen
    from the front, so it stays the same whichever way the character looks. Its feet at stage (x, y)."""
    b = _body(c)
    h = SEAT * b["leg_h"]
    w = b["torso_w"] + 64
    with cv.at(x, y - 6 * scale, 0, scale, scale):
        if kind == "bench":
            wood, dark = "#b07c45", "#7d5530"
            for sx in (-w * 0.78, w * 0.78):               # the posts, the back's planks, the seat
                cv.rect(sx - 9, -h - 170, 18, h + 170, dark, INK, 3)
            for yy in (-h - 160, -h - 104):
                cv.rect(-w * 0.95, yy, w * 1.9, 36, wood, INK, 3.5, 7)
            cv.rect(-w, -h - 8, w * 2, 28, wood, INK, 3.5, 7)
        else:
            col = "#5b6475"
            for sx in (-w / 2 + 10, w / 2 - 24):           # the legs, the back, the seat
                cv.rect(sx, -h, 14, h, shade(col, -0.25), INK, 3)
            cv.rect(-w / 2 + 10, -h - 210, w - 20, 172, col, INK, 4, 30)
            cv.rect(-w / 2 + 34, -h - 44, 14, 40, shade(col, -0.25), INK, 3)
            cv.rect(w / 2 - 48, -h - 44, 14, 40, shade(col, -0.25), INK, 3)
            cv.rect(-w / 2, -h - 12, w, 28, shade(col, 0.15), INK, 4, 12)


def _capsule(x0, y0, x1, y1, r, n: int = 7) -> list:
    """A rounded bar from (x0, y0) to (x1, y1), r wide each side (a finger, a bent leg)."""
    a = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1 + r * math.cos(a - math.pi / 2 + math.pi * k / n), y1 + r * math.sin(a - math.pi / 2 + math.pi * k / n))
           for k in range(n + 1)]
    return pts + [(x0 + r * math.cos(a + math.pi / 2 + math.pi * k / n), y0 + r * math.sin(a + math.pi / 2 + math.pi * k / n))
                  for k in range(n + 1)]


def _legs(cv: Canvas, c: dict, b: dict, walk, sit: float = 0.0):
    L = b["leg_h"]
    sp = 24 * b["wide"]
    pants, shoe = c.get("pants", "#2c2f3d"), c.get("shoes", "#1f1d22")
    dress = c.get("outfit") == "dress"
    if sit > 0:                                            # sitting, seen from the front: the thighs come towards us
        hip = -L + (1 - SEAT) * L * sit                    # (shorter), the shins go down to the floor
        thigh = lerp(L * 0.5, L * 0.24, sit)
        lw = 34 * b["wide"] ** 0.4 if not dress else 22
        col = c.get("skin") if dress else pants
        for side in (-1, 1):
            kx, ky = side * sp * (1 + 0.6 * sit), hip + thigh
            fx = side * sp * (1 + 0.2 * sit)
            cv.poly(_capsule(kx, ky, fx, -16, lw / 2), col, INK, 3.5)
            cv.poly(rounded(fx - 12, -22, 50, 24, 11), shoe, INK, 3.5)
        for side in (-1, 1):
            kx, ky = side * sp * (1 + 0.6 * sit), hip + thigh
            cv.poly(_capsule(side * sp, hip, kx, ky, lw / 2 + (6 if not dress else 2) * sit), col, INK, 3.5)
        return
    for side, ph in ((-1, 0.0), (1, math.pi)):
        a = math.sin((walk or 0) + ph) * (24 if walk is not None else 0)
        with cv.at(side * sp, -L, a):
            if dress:
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


def _arm(cv: Canvas, c: dict, b: dict, sx: float, sy: float, a_up: float, bend: float, back: bool, hand: str = "rest",
         held: str | None = None, held_k: float = 1.0):
    """An arm from the shoulder (sx, sy): the upper arm a_up degrees from straight down (towards the look), the
    forearm turned bend degrees more; its hand (HANDS) and what it holds."""
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
            hy = b["arm_l"] + 12
            if held and held_k > 0:
                _held(cv, held, 0, hy, held_k)
            _hand(cv, c, hand, 0, hy, side)


def _hand(cv: Canvas, c: dict, kind: str, x: float, y: float, side: int):
    """A hand at the forearm's end (the forearm comes from -y): three fingers and a thumb, as cartoons draw them."""
    skin = c.get("skin")
    if kind == "open":                                     # fingers apart, the palm over their roots
        for ang in (-30, 0, 30):
            r = math.radians(ang)
            cv.poly(_capsule(x, y, x + math.sin(r) * 31, y + math.cos(r) * 31, 7.5), skin, INK, 2.5)
        cv.poly(_capsule(x, y - 4, x + side * 27, y - 12, 7.5), skin, INK, 2.5)
        cv.ellipse(x, y, 18, 17, skin, INK, 3)
        return
    if kind in ("fist", "hold", "point", "thumb"):
        if kind == "point":                                # the index finger out, along the arm
            cv.poly(_capsule(x - side * 4, y, x - side * 4, y + 44, 7.5), skin, INK, 2.5)
        if kind == "thumb":                                # a fist turned sideways, the thumb up (upright, whatever
            with cv.upright(x, y):                         # the arm does): curled fingers stacked, a short thick thumb
                cv.poly(_capsule(-6, -14, 4, -44, 9.5), skin, INK, 3)
                cv.poly(rounded(-20, -18, 38, 40, 14), skin, INK, 3.5)
                dark = shade(skin, -0.3)
                for yy in (-6, 4, 13):
                    cv.line([(4, yy), (17, yy)], dark, 2.5)
            return
        cv.circle(x, y, 19, skin, INK, 3.5)
        dark = shade(skin, -0.3)
        for k in (-1, 1):                                  # (the fingers folded)
            cv.line([(x + k * 7, y + 7), (x + k * 7, y + 16)], dark, 2.5)
        if kind != "thumb":
            cv.poly(_capsule(x + side * 12, y - 6, x - side * 2, y + 2, 6.5), skin, INK, 2.5)
        return
    cv.circle(x, y, 19, skin, INK, 3.5)                    # (relaxed)
    cv.circle(x + side * 12, y - 10, 7, skin, INK, 2.5)


def _held(cv: Canvas, kind: str, x: float, y: float, k: float = 1.0):
    """A thing in a hand, upright whatever the arm does (drawn before the hand: the fingers close over it)."""
    with cv.upright(x, y):
        with cv.at(0, 0, 0, max(0.01, back(k, 1.4) if k < 1 else 1.0)):
            if kind == "phone":                            # held to the ear
                with cv.at(4, -6, 12):
                    cv.poly(rounded(-20, -62, 40, 96, 10), "#262b36", INK, 4)
                    cv.rect(-14, -50, 28, 70, "#8cc3f2", None, 0, 4)
                    cv.rect(-7, -58, 14, 4, "#5a6070", None, 0, 2)
                    cv.circle(0, 27, 3.5, "#5a6070")
            elif kind == "money":                          # a fan of notes
                for rot in (-26, -8, 10):
                    with cv.at(0, 6, rot):
                        cv.poly(rounded(-19, -84, 38, 82, 5), "#86c97f", INK, 3)
                        cv.ellipse(0, -44, 10, 14, "#5ea85a")
                        cv.rect(-13, -78, 26, 6, "#5ea85a", None, 0, 2)
            elif kind == "paper":                          # a sheet shown, held at its lower corner
                cv.poly([(-14, -168), (96, -168), (96, -4), (-14, -4)], "#ffffff", INK, 3.5)
                for j in range(6):
                    cv.line([(2, -146 + 24 * j), (80 - (34 if j == 5 else 0), -146 + 24 * j)], "#9aa4b2", 4)


def _head(cv: Canvas, c: dict, b: dict, emotion: str, mouth, blink: float, gaze: tuple, brow: float = 0.0):
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
    _eyes(cv, emotion, blink, gaze, hw, hh, cy, c, brow)
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


def _eyes(cv, emotion, blink, gaze, hw, hh, cy, c, brow: float = 0.0):
    ey = cy - hh * 0.04
    big = 1.25 if emotion == "surprised" else 1.3 if emotion == "scared" else 1.0
    gx, gy = gaze
    for side in (-1, 1):
        ex = side * hw * 0.2
        if emotion == "laugh":                             # (laughing: the eyes squeezed shut, smiling)
            cv.line(arc(ex, ey + 6, 16, 12, 195, 345, 10), INK, 5)
        elif blink > 0.5:
            cv.line(arc(ex, ey + 2, 15, 7, 10, 170, 10), INK, 4)
        else:
            open_k = 1.0 - blink * 1.6
            if emotion == "sly":
                open_k *= 0.55
            elif emotion in ("angry",):
                open_k *= 0.8
            cv.ellipse(ex, ey, 16 * big, 21 * big * max(0.15, open_k), "#ffffff", INK, 3)
            cv.circle(ex + 5 + gx * 6, ey + 2 + gy * 6, (5.0 if emotion == "scared" else 8.5 * big) * max(0.4, min(1, open_k + 0.2)),
                      "#20232e")
            cv.circle(ex + 8 + gx * 6, ey - 2 + gy * 6, 3, "#ffffff")
        # brows
        by = ey - 30 * big - 9 * max(0.0, min(1.0, brow))
        if emotion == "angry":
            pts = [(ex - 22, by - 6 if side < 0 else by + 10), (ex + 20, by + 10 if side < 0 else by - 6)]
        elif emotion in ("sad", "worried", "scared"):
            pts = [(ex - 20, by + 6 if side < 0 else by - 8), (ex + 20, by - 8 if side < 0 else by + 6)]
        elif emotion == "surprised":
            pts = [(ex - 20, by - 8), (ex, by - 16), (ex + 20, by - 8)]
        elif emotion == "sly":
            pts = [(ex - 20, by - (12 if side > 0 else 0)), (ex + 20, by - (16 if side > 0 else -4))]
        elif emotion in ("happy", "laugh"):
            pts = [(ex - 20, by - 2), (ex, by - 9), (ex + 20, by - 2)]
        else:
            pts = [(ex - 20, by), (ex, by - 4), (ex + 20, by)]
        cv.line(pts, c.get("hair") if c.get("hair_style") != "bald" else INK, 7)


def _mouth(cv, emotion, mouth, hw, hh, cy, skin, lips=None):
    my = cy + hh * 0.3
    w = 44
    shape = ""
    if isinstance(mouth, (tuple, list)):
        mouth, shape = (mouth[0], mouth[1]) if len(mouth) > 1 else (mouth[0], "")
    o = max(0.0, min(1.0, float(mouth or 0.0)))
    curve = {"happy": 10, "laugh": 12, "sly": 6, "angry": -6, "sad": -9, "worried": -5, "scared": -7, "surprised": 0}.get(emotion, 3)
    if emotion == "surprised":
        o = max(o, 0.45)
    elif emotion == "laugh":                               # (a laugh: the mouth wide open, whatever the sound)
        o, shape = max(o, 0.75), ""
    elif emotion == "scared":
        o = max(o, 0.3)
    line_c, line_w = lips or INK, (5.5 if lips else 4.5)
    if shape == "M" and o >= 0.08:                       # lips pressed together (m, b, p)
        cv.line(bezier((-w * 0.42, my - curve * 0.15), (-w / 5, my + 2 + curve * 0.4), (w / 5, my + 2 + curve * 0.4),
                       (w * 0.42, my - curve * 0.15), 10), line_c, line_w + 1.5)
        return
    if shape == "F" and o >= 0.08:                       # the top teeth on the lower lip (f, v)
        ow = w * 0.78
        cv.poly(rounded(-ow / 2, my - 7, ow, 13, 6), "#6b2430", line_c, 4)
        cv.rect(-ow * 0.36, my - 7, ow * 0.72, 7, "#ffffff", None, 0, 2)
        return
    if shape in ("O", "U") and o >= 0.08:                # round lips: "o" open, "u" small and pushed out
        rx = w * (0.3 if shape == "O" else 0.2)
        ry = (9 + 15 * o) if shape == "O" else (8 + 6 * o)
        cv.ellipse(0, my + ry * 0.35, rx, ry, "#6b2430", line_c, 4.5 if lips else 4)
        if shape == "O" and o > 0.3:
            cv.ellipse(0, my + ry * 0.95, rx * 0.55, ry * 0.3, "#e2737c")
        return
    if shape in ("E", "C") and o >= 0.08:                # wide and flat, the teeth showing ("e", "i"; most consonants)
        o = o * (0.45 if shape == "E" else 0.6)
        ow = w * (1.08 if shape == "E" else 0.9)
        oh = 5 + 22 * o
        pts = bezier((-ow / 2, my - curve * 0.3), (-ow / 3, my - oh * 0.2), (ow / 3, my - oh * 0.2), (ow / 2, my - curve * 0.3), 8) + \
            bezier((ow / 2, my - curve * 0.3), (ow / 3, my + oh), (-ow / 3, my + oh), (-ow / 2, my - curve * 0.3), 12)[1:]
        cv.poly(pts, "#6b2430", line_c, 4.5 if lips else 4)
        cv.rect(-ow * 0.34, my - oh * 0.15, ow * 0.68, max(4, oh * 0.38), "#ffffff", None, 0, 3)
        return
    if o < 0.08:
        if emotion == "sly":
            cv.line(bezier((-w / 2, my), (-6, my + 4), (10, my + 2), (w / 2 + 6, my - 10), 10), INK, 4.5)
        else:
            cv.line(bezier((-w / 2, my - curve * 0.2), (-w / 4, my + curve), (w / 4, my + curve), (w / 2, my - curve * 0.2), 12),
                    lips or INK, 5.5 if lips else 4.5)
        return
    ow = w * (0.7 + 0.3 * (1 - o)) * (1.15 if emotion in ("happy", "laugh") else 0.8 if emotion == "scared" else 1.0)
    oh = 6 + 30 * o
    pts = bezier((-ow / 2, my - curve * 0.25), (-ow / 3, my - oh * 0.25), (ow / 3, my - oh * 0.25), (ow / 2, my - curve * 0.25), 8) + \
        bezier((ow / 2, my - curve * 0.25), (ow / 3, my + oh), (-ow / 3, my + oh), (-ow / 2, my - curve * 0.25), 12)[1:]
    cv.poly(pts, "#6b2430", lips or INK, 4.5 if lips else 4)
    if o > 0.35:
        cv.ellipse(0, my + oh * 0.62, ow * 0.26, oh * 0.22, "#e2737c")
    if emotion in ("happy", "laugh") or o > 0.5:
        cv.rect(-ow * 0.32, my - oh * 0.2, ow * 0.64, max(4, oh * 0.22), "#ffffff", None, 0, 3)


SHAPES = ("A", "E", "O", "U", "M", "F", "C")             # (the mouth for a sound: a, e/i, o, u, m/b/p, f/v, the rest)
_SOUND: dict = {}
for _shape, _letters in (("A", "аяaáâăàäæ"), ("O", "оёoóôöò"), ("U", "уюuúùüûw"), ("E", "еэиыeéèêëiíîïyй"),
                         ("M", "мбпmbp"), ("F", "фвfv")):
    for _ch in _letters:
        _SOUND[_ch] = _shape


def sound_shapes(words: list, start: float, n: int, fps: int = 30) -> list:
    """The mouth's shape in each of n pictures from start (seconds), from the letters of the words said then (a word's
    time shared among its letters, vowels longer); "" between words. A shape lasts at least two pictures."""
    spans = []
    for w in words:
        letters = [ch_ for ch_ in str(w.get("w") or "").lower() if ch_.isalpha() and ch_ not in "ьъ"]
        if not letters:
            letters = ["a", "t"]                           # (a number said: the mouth moves anyway)
        shapes = [_SOUND.get(ch_, "C") for ch_ in letters]
        merged = []                                        # (the same shape twice in a row: one longer sound)
        for sh in shapes:
            wt = 1.7 if sh in ("A", "E", "O", "U") else 1.2 if sh in ("M", "F") else 1.0
            if merged and merged[-1][0] == sh:
                merged[-1][1] += wt
            else:
                merged.append([sh, wt])
        s0, e0 = float(w["s"]), float(w["e"])
        tot = sum(x[1] for x in merged)
        t0 = s0
        for sh, wt in merged:
            t1 = t0 + (e0 - s0) * wt / tot
            spans.append((t0, t1, sh))
            t0 = t1
    out, j = [], 0
    for k in range(n):
        tt = start + k / fps
        while j < len(spans) and spans[j][1] < tt:
            j += 1
        out.append(spans[j][2] if j < len(spans) and spans[j][0] <= tt <= spans[j][1] else "")
    for k in range(1, len(out) - 1):                       # (one picture of a shape is not seen: held for two)
        if out[k] != out[k - 1] and out[k] != out[k + 1] and out[k - 1] == out[k + 1] and out[k]:
            out[k + 1] = out[k]
    return out


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
