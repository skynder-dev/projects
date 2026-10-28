"""Backgrounds of the scenes, drawn for the stage the film has (wide 16:9 or tall 9:16): a city street, an office,
the city hall, a road being repaired, a bank, a night street, a board for schemes and charts, a hospital, a school,
a shop and a block of flats. Each takes the time
(clouds drift, lights blink) and returns where the floor is (the characters stand on it).
"""
from __future__ import annotations

import math

from . import props as P
from .draw import INK, Canvas, shade


def ground_y(cv: Canvas) -> float:
    return cv.SH * (0.86 if cv.SW >= cv.SH else 0.9)


def _clouds(cv: Canvas, t: float, n: int = 3):
    for k in range(n):
        x = (k * 0.37 * cv.SW + t * (14 + 6 * k)) % (cv.SW + 400) - 200
        y = cv.SH * (0.1 + 0.07 * k)
        for dx, dy, r in ((0, 0, 46), (44, -16, 40), (88, 0, 44), (40, 14, 42)):
            cv.circle(x + dx, y + dy, r, "#ffffff")


def city(cv: Canvas, t: float = 0.0) -> float:
    gy = ground_y(cv)
    cv.vgradient("#bfe3f7", "#eef7fb", 0, gy)
    cv.circle(cv.SW * 0.82, cv.SH * 0.16, 70, "#ffe08a")
    _clouds(cv, t)
    import random
    rnd = random.Random(7)
    x = -40
    while x < cv.SW + 40:                                  # far buildings
        w = rnd.randint(140, 220)
        h = rnd.randint(int(cv.SH * 0.25), int(cv.SH * 0.45))
        cv.rect(x, gy - 90 - h, w, h + 90, "#c9d6e6")
        x += w + rnd.randint(-10, 20)
    x = -60
    cols = ["#e8d5b5", "#d7e2ee", "#f0c9a8", "#cfe0d3", "#e6d0dc"]
    k = 0
    while x < cv.SW + 60:                                  # near buildings
        w = rnd.randint(200, 300)
        h = rnd.randint(int(cv.SH * 0.22), int(cv.SH * 0.36))
        P.building(cv, x + w / 2, gy - 60, w, h, cols[k % len(cols)], "#9ec2e6")
        x += w + rnd.randint(10, 40)
        k += 1
    cv.rect(0, gy - 60, cv.SW, 60, "#cfcabf", INK, 4)     # the pavement
    cv.rect(0, gy, cv.SW, cv.SH - gy, "#7d8290")
    return gy


def office(cv: Canvas, t: float = 0.0) -> float:
    gy = ground_y(cv)
    cv.fill("#e9e2d4")
    cv.rect(0, gy - 30, cv.SW, cv.SH - gy + 30, "#b89a76", INK, 4)
    for k in range(int(cv.SW // 120) + 1):
        cv.line([(k * 120, gy - 30), (k * 120 + 40, cv.SH)], shade("#b89a76", -0.12), 3)
    wx, ww, wh = cv.SW * 0.5, min(700, cv.SW * 0.6), cv.SH * 0.36
    cv.rect(wx - ww / 2, cv.SH * 0.12, ww, wh, "#bfe3f7", INK, 5, 6)
    for k in range(5):
        cv.rect(wx - ww / 2 + 20 + k * ww / 5, cv.SH * 0.12 + wh * 0.4, ww / 5 - 30, wh * 0.6 - 4, "#c9d6e6")
    cv.line([(wx, cv.SH * 0.12), (wx, cv.SH * 0.12 + wh)], INK, 5)
    cv.rect(wx - ww / 2 - 20, cv.SH * 0.12 + wh, ww + 40, 18, "#d8ccb2", INK, 4)
    px = cv.SW * 0.1                                       # a plant
    cv.rect(px - 40, gy - 110, 80, 90, "#c2554a", INK, 4, 8)
    for a in (-40, -15, 15, 40):
        with cv.at(px, gy - 110, a):
            cv.ellipse(0, -60, 22, 62, "#4caf6a", INK, 3)
    cv.rect(cv.SW * 0.82 - 70, cv.SH * 0.16, 140, 100, "#fbf7ee", INK, 4, 4)    # a picture: a graph going up
    cv.line([(cv.SW * 0.82 - 50, cv.SH * 0.16 + 80), (cv.SW * 0.82 - 10, cv.SH * 0.16 + 50), (cv.SW * 0.82 + 10, cv.SH * 0.16 + 60),
             (cv.SW * 0.82 + 50, cv.SH * 0.16 + 20)], P.GREEN, 6)
    return gy


def city_hall(cv: Canvas, t: float = 0.0) -> float:
    gy = ground_y(cv)
    cv.vgradient("#cfe8f6", "#f3f8fa", 0, gy)
    _clouds(cv, t, 2)
    s = min(1.0, cv.SW / 1500)
    P.city_hall(cv, cv.SW * 0.5, gy - 40, s)
    cv.rect(0, gy - 40, cv.SW, 40, "#d8ccb2", INK, 4)
    cv.rect(0, gy, cv.SW, cv.SH - gy, "#a7a196")
    return gy


def road(cv: Canvas, t: float = 0.0) -> float:
    gy = ground_y(cv)
    cv.vgradient("#bfe3f7", "#f2f7ea", 0, gy - 180)
    _clouds(cv, t, 2)
    for k in range(4):
        cx = k * cv.SW / 3
        cv.ellipse(cx, gy - 160, cv.SW * 0.3, 120, "#a8cf8a", None, 0, 180, 360)
    cv.rect(0, gy - 200, cv.SW, cv.SH - gy + 200, "#9cc77a")
    return gy


def bank(cv: Canvas, t: float = 0.0) -> float:
    gy = ground_y(cv)
    cv.fill("#e7e1d6")
    for k in range(5):
        x = cv.SW * (0.1 + 0.2 * k)
        cv.rect(x - 30, 0, 60, gy, "#f3efe6", INK, 3)
    cv.rect(0, gy - 30, cv.SW, cv.SH - gy + 30, "#8f7f6a", INK, 4)
    vx, vy = cv.SW * 0.72, gy - cv.SH * 0.3            # a vault door
    cv.circle(vx, vy, cv.SH * 0.2, "#a9b0bc", INK, 6)
    cv.circle(vx, vy, cv.SH * 0.14, "#c2c8d2", INK, 4)
    for a in range(0, 360, 60):
        cv.line([(vx, vy), (vx + math.cos(math.radians(a + t * 20)) * cv.SH * 0.1,
                            vy + math.sin(math.radians(a + t * 20)) * cv.SH * 0.1)], INK, 8)
    return gy


def night(cv: Canvas, t: float = 0.0) -> float:
    gy = ground_y(cv)
    cv.vgradient("#1d2742", "#3a4a72", 0, gy)
    cv.circle(cv.SW * 0.8, cv.SH * 0.16, 56, "#f5f0d6")
    cv.circle(cv.SW * 0.8 + 22, cv.SH * 0.16 - 12, 50, "#2a365a")
    for k in range(18):
        x = (k * 397) % int(cv.SW)
        y = (k * 211) % int(cv.SH * 0.4)
        if (k + int(t * 2)) % 7:
            cv.circle(x, y, 2.5, "#ffffff")
    x = -40
    k = 0
    while x < cv.SW:
        w = 200 + (k * 53) % 90
        h = cv.SH * (0.22 + ((k * 37) % 30) / 100)
        P.building(cv, x + w / 2, gy - 40, w, h, "#2f3a5c", "#3d4a70", lit=1.0)
        x += w + 20
        k += 1
    lx = cv.SW * 0.18
    cv.rect(lx - 6, gy - 330, 12, 330, "#20242e")
    cv.blend("#ffe9a8", 0.25, [(lx - 20, gy - 320), (lx + 20, gy - 320), (lx + 160, gy), (lx - 160, gy)])
    cv.rect(lx - 30, gy - 340, 60, 22, "#ffe9a8", INK, 3, 6)
    cv.rect(0, gy - 40, cv.SW, cv.SH - gy + 40, "#2b2f3a")
    return gy


def board(cv: Canvas, t: float = 0.0) -> float:
    cv.vgradient("#22315a", "#18213d")
    step = 60
    for x in range(0, int(cv.SW) + step, step):
        cv.line([(x, 0), (x, cv.SH)], "#2a3a66", 2)
    for y in range(0, int(cv.SH) + step, step):
        cv.line([(0, y), (cv.SW, y)], "#2a3a66", 2)
    return ground_y(cv)


def paper(cv: Canvas, t: float = 0.0) -> float:
    cv.fill("#f6f1e6")
    for y in range(80, int(cv.SH), 64):
        cv.line([(0, y), (cv.SW, y)], "#e6dccb", 2)
    cv.line([(110, 0), (110, cv.SH)], "#f0b7a8", 3)
    return ground_y(cv)


def hospital(cv: Canvas, t: float = 0.0) -> float:
    """A hospital corridor: pale green walls, doors with round windows, a red cross, a bench, a drip stand."""
    gy = ground_y(cv)
    cv.fill("#dcefe9")
    cv.rect(0, gy - cv.SH * 0.42, cv.SW, 26, "#b9ddd2")               # a stripe along the wall
    cv.rect(0, gy - 30, cv.SW, cv.SH - gy + 30, "#c9d3d6", INK, 4)
    for k in range(int(cv.SW // 90) + 1):                              # floor tiles
        cv.line([(k * 90, gy - 30), (k * 90 - 30, cv.SH)], "#b6c0c4", 2)
    n = max(2, int(cv.SW // 520))
    for k in range(n):                                                 # doors
        x = cv.SW * (k + 0.5) / n + (90 if k % 2 else -90)
        h, w = cv.SH * 0.36, 200
        cv.rect(x - w / 2, gy - 30 - h, w, h, "#8fc1b3", INK, 5, 6)
        cv.line([(x, gy - 30 - h), (x, gy - 30)], INK, 4)
        for dx in (-w / 4, w / 4):
            cv.circle(x + dx, gy - 30 - h * 0.7, 26, "#d6eef6", INK, 4)
        cv.rect(x - 40, gy - 30 - h - 60, 80, 40, "#ffffff", INK, 3, 6)
        cv.text(str(101 + k), x, gy - 30 - h - 40, 26, INK)
    cx, cy = cv.SW * 0.5, cv.SH * 0.13                                 # the red cross sign
    cv.circle(cx, cy, 64, "#ffffff", INK, 5)
    cv.rect(cx - 16, cy - 44, 32, 88, "#e0533d")
    cv.rect(cx - 44, cy - 16, 88, 32, "#e0533d")
    sx = cv.SW * 0.86                                                  # a drip stand
    cv.line([(sx, gy - 30), (sx, gy - 330)], "#7d8290", 7)
    cv.line([(sx - 50, gy - 330), (sx + 50, gy - 330)], "#7d8290", 6)
    cv.rect(sx - 70, gy - 320, 44, 70, "#e8f4fb", INK, 3, 10)
    cv.line([(sx - 48, gy - 250), (sx - 30, gy - 150 + 6 * math.sin(t))], "#99aabb", 3)
    return gy


def school(cv: Canvas, t: float = 0.0) -> float:
    """A classroom: a green blackboard with chalk, a clock, a globe on a desk, a window."""
    gy = ground_y(cv)
    cv.fill("#f2e6c9")
    cv.rect(0, gy - 30, cv.SW, cv.SH - gy + 30, "#b48a5e", INK, 4)
    for k in range(int(cv.SW // 140) + 1):
        cv.line([(k * 140, gy - 30), (k * 140, cv.SH)], shade("#b48a5e", -0.12), 3)
    bw, bh = min(1000, cv.SW * 0.78), cv.SH * 0.26                     # the blackboard
    bx, by = cv.SW * 0.5 - bw / 2, cv.SH * 0.12
    cv.rect(bx - 16, by - 16, bw + 32, bh + 32, "#8a5a32", INK, 5, 8)
    cv.rect(bx, by, bw, bh, "#2f5d4a")
    cv.text("2 + 2 = 4", bx + bw * 0.28, by + bh * 0.32, min(70, bh * 0.22), "#f4f1e6", "bold")
    cv.line([(bx + bw * 0.55, by + bh * 0.7), (bx + bw * 0.65, by + bh * 0.45), (bx + bw * 0.75, by + bh * 0.6),
             (bx + bw * 0.88, by + bh * 0.3)], "#f4f1e6", 5)
    cv.rect(bx + 20, by + bh + 16, bw - 40, 14, "#d8c9a6", INK, 3)
    kx, ky = cv.SW * 0.9, cv.SH * 0.08                                 # a clock
    cv.circle(kx, ky, 52, "#ffffff", INK, 5)
    cv.line([(kx, ky), (kx + 26 * math.sin(t * 0.5), ky - 26 * math.cos(t * 0.5))], INK, 5)
    cv.line([(kx, ky), (kx, ky - 36)], INK, 4)
    gx = cv.SW * 0.1                                                   # a desk with a globe
    cv.rect(gx - 90, gy - 150, 180, 24, "#9c6b3e", INK, 4)
    cv.rect(gx - 80, gy - 126, 16, 96, "#9c6b3e", INK, 3)
    cv.rect(gx + 64, gy - 126, 16, 96, "#9c6b3e", INK, 3)
    cv.circle(gx, gy - 215, 52, "#5aa9e6", INK, 4)
    cv.ellipse(gx - 14, gy - 230, 22, 16, "#4caf6a")
    cv.ellipse(gx + 18, gy - 196, 16, 12, "#4caf6a")
    cv.line([(gx, gy - 160), (gx, gy - 150)], INK, 6)
    return gy


def shop(cv: Canvas, t: float = 0.0) -> float:
    """A shop or a pharmacy: shelves of coloured boxes, a counter with a till, price tags."""
    gy = ground_y(cv)
    cv.fill("#f4efe6")
    cv.rect(0, gy - 30, cv.SW, cv.SH - gy + 30, "#c7b9a3", INK, 4)
    sw = cv.SW * 0.9
    sx = cv.SW * 0.05
    rows = 4
    top = cv.SH * 0.08
    rh = (gy - 260 - top) / rows
    cols = ["#e0533d", "#3f7fd6", "#f2c12e", "#4caf6a", "#6a4c8c", "#ef8f3a"]
    for r in range(rows):                                              # shelves with boxes
        y = top + (r + 1) * rh
        cv.rect(sx, y, sw, 14, "#a07a52", INK, 3)
        x, k = sx + 10, r
        while x < sx + sw - 70:
            w, h = 50 + (k * 17) % 30, rh * (0.55 + ((k * 13) % 30) / 100)
            cv.rect(x, y - h, w, h, cols[k % len(cols)], INK, 3, 4)
            cv.rect(x + 8, y - h * 0.6, w - 16, h * 0.18, "#ffffff")
            x += w + 8
            k += 1
    cx = cv.SW * 0.74                                                  # the counter and the till
    cv.rect(cx - 260, gy - 230, 520, 200, "#d9c6a5", INK, 5, 8)
    cv.rect(cx + 60, gy - 330, 160, 100, "#5d6472", INK, 4, 8)
    cv.rect(cx + 80, gy - 315, 120, 40, "#bfe8c8", INK, 3)
    return gy


def home(cv: Canvas, t: float = 0.0) -> float:
    """A block of flats: many windows, an entrance with a canopy, a bench, a tree."""
    gy = ground_y(cv)
    cv.vgradient("#bfe3f7", "#eef7fb", 0, gy)
    _clouds(cv, t, 2)
    bw = min(cv.SW * 0.9, 1500)
    bx, top = cv.SW * 0.5 - bw / 2, cv.SH * 0.06
    cv.rect(bx, top, bw, gy - 40 - top, "#e3d9c6", INK, 5)
    n_c = max(4, int(bw // 150))
    n_r = max(4, int((gy - 360 - top) // 150))
    for r in range(n_r):                                               # the windows (some lit)
        for c_ in range(n_c):
            x = bx + bw * (c_ + 0.5) / n_c
            y = top + 40 + r * ((gy - 360 - top) / n_r)
            lit = ((r * 7 + c_ * 3) % 5 == 0)
            cv.rect(x - 38, y, 76, 92, "#fff1b8" if lit else "#9ec2e6", INK, 3, 2)
            cv.line([(x, y), (x, y + 92)], INK, 2)
    ex = cv.SW * 0.5                                                   # the entrance
    cv.rect(ex - 90, gy - 300, 180, 260, "#7a5a3c", INK, 5, 4)
    cv.rect(ex - 130, gy - 330, 260, 30, "#9aa4b2", INK, 4)
    cv.circle(ex + 56, gy - 170, 9, "#f2c12e")
    cv.rect(0, gy - 40, cv.SW, 40, "#cfcabf", INK, 4)
    cv.rect(0, gy, cv.SW, cv.SH - gy, "#8a8f9a")
    tx = cv.SW * 0.12                                                  # a tree
    cv.rect(tx - 14, gy - 220, 28, 180, "#7a5a3c", INK, 3)
    cv.circle(tx, gy - 260, 90, "#6fbf73", INK, 4)
    return gy


BACKGROUNDS = {"city": city, "office": office, "city_hall": city_hall, "road": road, "bank": bank, "night": night,
               "board": board, "paper": paper, "hospital": hospital, "school": school, "shop": shop, "home": home}


def draw(cv: Canvas, name: str, t: float = 0.0) -> float:
    return BACKGROUNDS.get(name, city)(cv, t)

