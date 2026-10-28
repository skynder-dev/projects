"""Backgrounds of the scenes, drawn for the stage the film has (wide 16:9 or tall 9:16): a city street, an office,
the city hall, a road being repaired, a bank, a night street, a board for schemes and charts. Each takes the time
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


BACKGROUNDS = {"city": city, "office": office, "city_hall": city_hall, "road": road, "bank": bank, "night": night,
               "board": board, "paper": paper}


def draw(cv: Canvas, name: str, t: float = 0.0) -> float:
    return BACKGROUNDS.get(name, city)(cv, t)

