"""Things in a cartoon: money, coins, documents, stamps, arrows, boxes of a scheme, charts, a road with holes, a
truck, buildings, speech bubbles, a magnifier, a calendar, ticks and crosses - drawn in their own units around (0, 0),
most of them with an "appear" amount (0..1) so they can pop, grow or be written in.
"""
from __future__ import annotations

import math

from .draw import INK, Canvas, arc, back, bezier, ease, lerp, rounded, shade

GREEN, GOLD, RED, BLUE, PAPER = "#4caf6a", "#f2c12e", "#e0533d", "#3f7fd6", "#fbf7ee"


def banknote(cv: Canvas, x, y, s=1.0, rot=0.0, color=GREEN):
    with cv.at(x, y, rot, s):
        cv.rect(-70, -36, 140, 72, color, INK, 4, 8)
        cv.rect(-58, -26, 116, 52, None, shade(color, -0.25), 3, 6)
        cv.circle(0, 0, 18, shade(color, 0.25), shade(color, -0.3), 3)
        cv.text("$", 0, 1, 26, shade(color, -0.45), "black")


def cash_stack(cv: Canvas, x, y, s=1.0, n=5, color=GREEN):
    with cv.at(x, y, 0, s):
        for k in range(n):
            cv.rect(-80, -k * 14 - 16, 160, 26, shade(color, -0.08 * (k % 2)), INK, 4, 6)
            cv.rect(-14, -k * 14 - 16, 28, 26, "#f4e7b8", INK, 3)


def coin(cv: Canvas, x, y, s=1.0, spin=0.0):
    w = abs(math.cos(spin)) * 30 + 4
    with cv.at(x, y, 0, s):
        cv.ellipse(0, 0, w, 30, GOLD, INK, 4)
        if w > 14:
            cv.text("$", 0, 1, 30, shade(GOLD, -0.45), "black")


def money_bag(cv: Canvas, x, y, s=1.0, label="$"):
    with cv.at(x, y, 0, s):
        cv.poly(bezier((-60, 70), (-90, -10), (-40, -50), (-22, -56), 10) + bezier((22, -56), (40, -50), (90, -10), (60, 70), 10),
                "#c7a46a", INK, 4)
        cv.rect(-60, 50, 120, 24, "#c7a46a", INK, 4, 12)
        cv.poly([(-26, -56), (26, -56), (34, -86), (0, -70), (-34, -86)], "#b08f55", INK, 4)
        cv.rect(-30, -62, 60, 12, "#8a6a3a", INK, 3, 4)
        cv.text(label, 0, 12, 52, shade("#c7a46a", -0.5), "black")


def document(cv: Canvas, x, y, s=1.0, title="CONTRACT", lines=6, written=1.0, price: str = "", appear=1.0, rot=0.0):
    """A paper with a title and lines being written (written 0..1); price: a sum in big letters at the bottom."""
    k = back(appear)
    if k <= 0.01:
        return
    with cv.at(x, y, rot, s * k):
        cv.poly(rounded(-150, -200, 300, 400, 10), PAPER, INK, 4)
        cv.poly([(110, -200), (150, -160), (110, -160)], shade(PAPER, -0.12), INK, 3)
        cv.text(title, 0, -158, 30, INK, "black")
        n = int(lines * max(0.0, min(1.0, written)) + 0.999)
        for i in range(n):
            frac = min(1.0, lines * written - i)
            w = (220 if i % 3 != 2 else 150) * frac
            cv.line([(-110, -110 + i * 30), (-110 + w, -110 + i * 30)], "#9aa3b5", 6)
        if price and written > 0.6:
            cv.text(price, 0, 140, 48, RED, "black")


def stamp(cv: Canvas, x, y, s=1.0, text="APPROVED", appear=1.0, color=RED, rot=-14):
    """A rubber stamp landing: big and see-through, then small and solid."""
    if appear <= 0:
        return
    k = 1.0 + (1 - ease(min(1.0, appear * 1.4))) * 1.2
    with cv.at(x, y, rot, s * k):
        cv.rect(-150, -46, 300, 92, None, color, 7, 14)
        cv.text(text, 0, 2, 44, color, "black")


def arrow(cv: Canvas, pts: list, progress=1.0, color=INK, width=10, head=26):
    """An arrow along points (a path), drawn up to progress (0..1)."""
    if progress <= 0 or len(pts) < 2:
        return
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg) * min(1.0, progress)
    out, done = [pts[0]], 0.0
    for (a, b), L in zip(zip(pts, pts[1:]), seg):
        if done + L >= total:
            t = (total - done) / max(1e-6, L)
            out.append((lerp(a[0], b[0], t), lerp(a[1], b[1], t)))
            break
        out.append(b)
        done += L
    cv.line(out, color, width)
    if len(out) >= 2:
        (x0, y0), (x1, y1) = out[-2], out[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        tip = [(x1 + math.cos(ang) * 6, y1 + math.sin(ang) * 6),
               (x1 - math.cos(ang - 0.45) * head, y1 - math.sin(ang - 0.45) * head),
               (x1 - math.cos(ang + 0.45) * head, y1 - math.sin(ang + 0.45) * head)]
        cv.poly(tip, color, color, 2)


def curve(a, b, bend=0.25, n=24) -> list:
    """Points of a gentle curve from a to b (bend: how far it bows, a share of the length)."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    c = (mx - dy * bend, my + dx * bend)
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0], (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1])
            for t in (k / n for k in range(n + 1))]


def along(pts: list, t: float) -> tuple:
    """The point a share t of the way along a path."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total, goal = sum(seg), sum(seg) * max(0.0, min(1.0, t))
    for (a, b), L in zip(zip(pts, pts[1:]), seg):
        if goal <= L:
            k = goal / max(1e-6, L)
            return (lerp(a[0], b[0], k), lerp(a[1], b[1], k))
        goal -= L
    return pts[-1] if total else pts[0]


def node(cv: Canvas, x, y, label: str, icon: str = "", color=BLUE, appear=1.0, w=260, h=150, sub: str = ""):
    """A box of a scheme: an icon above a label (a city, a company, an official, a bank ...)."""
    k = back(appear)
    if k <= 0.01:
        return
    with cv.at(x, y, 0, k):
        cv.shadow(0, h / 2 + 10, w * 0.45, 12, 0.18)
        cv.rect(-w / 2, -h / 2, w, h, color, INK, 4, 22)
        if icon:
            ICONS.get(icon, _icon_none)(cv, 0, -h / 2 + 2, 0.62)
        cv.text(label, 0, h / 2 - 42, 38, "#ffffff", "black", outline=INK, stroke=3, width=w - 20)
        if sub:
            cv.text(sub, 0, h / 2 + 36, 28, INK, "extrabold", width=w + 60)


def _icon_none(cv, x, y, s):
    pass


def icon_city(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 0, s):
        cv.poly([(-90, 40), (-90, -40), (-20, -90), (50, -40), (50, 40)], "#f1e3c8", INK, 4)
        cv.poly([(-100, -36), (-20, -96), (60, -36)], "#c2554a", INK, 4)
        for xx in (-66, -36, -6, 24):
            cv.rect(xx - 6, -20, 12, 50, "#ffffff", INK, 3)
        cv.rect(-100, 34, 160, 16, "#d8c7a6", INK, 4)


def icon_company(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 0, s):
        cv.rect(-50, -70, 100, 120, "#cfd8e6", INK, 4, 4)
        for yy in (-54, -26, 2):
            for xx in (-32, -6, 20):
                cv.rect(xx, yy, 14, 18, "#7fa6d9", INK, 2)
        cv.rect(-12, 26, 24, 24, "#8a6a3a", INK, 3)
        cv.poly([(50, -30), (90, -10), (90, 50), (50, 50)], "#b9c4d6", INK, 4)


def icon_person(cv: Canvas, x, y, s=1.0, color="#e9b38f"):
    with cv.at(x, y, 0, s):
        cv.circle(0, -42, 30, color, INK, 4)
        cv.poly(arc(0, 48, 54, 62, 180, 360, 18), "#3c4a66", INK, 4)


def icon_shovel(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 30, s):
        cv.rect(-6, -80, 12, 110, "#9b6b3a", INK, 3)
        cv.poly([(-30, 30), (30, 30), (24, 80), (0, 96), (-24, 80)], "#a8b0bd", INK, 4)


def icon_bank(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 0, s):
        cv.poly([(-90, -40), (0, -90), (90, -40)], "#e6e1d3", INK, 4)
        for xx in (-60, -20, 20, 60):
            cv.rect(xx - 9, -36, 18, 70, "#f4f0e4", INK, 3)
        cv.rect(-96, 34, 192, 16, "#d6cfbd", INK, 4)


def icon_bag(cv: Canvas, x, y, s=1.0):
    money_bag(cv, x, y + 10, s * 0.8)


def icon_road(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 0, s):
        cv.poly([(-30, -80), (30, -80), (90, 50), (-90, 50)], "#5d6270", INK, 4)
        for k in range(3):
            cv.rect(-5, -60 + k * 38, 10, 22, "#f2f2f2")


ICONS = {"city": icon_city, "company": icon_company, "person": icon_person, "shovel": icon_shovel, "bank": icon_bank,
         "bag": icon_bag, "road": icon_road}


def num(v: float) -> str:
    """4.8 -> "4.8", 1200000 -> "1 200 000", 12 -> "12"."""
    if abs(v - round(v)) < 1e-6:
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:,.1f}".replace(",", " ")


def bars(cv: Canvas, x, y, values: list, labels: list, colors: list, grow=1.0, w=480, h=360, unit="", max_v=None, ink=INK):
    """A bar chart growing up (grow 0..1); values written on top."""
    n = max(1, len(values))
    top = max_v or max(values) or 1
    bw = w / n * 0.6
    cv.line([(x - w / 2, y), (x + w / 2, y)], ink, 5)
    for i, v in enumerate(values):
        g = ease(max(0.0, min(1.0, grow * n - i * 0.6)))
        bh = h * v / top * g
        bx = x - w / 2 + (i + 0.5) * w / n - bw / 2
        if bh > 1:
            cv.rect(bx, y - bh, bw, bh, colors[i % len(colors)], INK, 4, 8)
        if g > 0.9:
            cv.text(num(v) + unit, bx + bw / 2, y - bh - 36, 56, ink, "black")
        cv.text(labels[i] if i < len(labels) else "", bx + bw / 2, y + 44, 40, ink, "black", width=w / n + 40)


def road(cv: Canvas, x, y, w=900, holes=0.0, patch=0.0, t=0.0, perspective=True):
    """A road seen from the side and a little above: asphalt, a dashed middle line, potholes (holes 0..1 appear),
    fresh patches over them (patch 0..1)."""
    h = 150
    cv.poly([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2 + 40, y + h / 2), (x - w / 2 - 40, y + h / 2)],
            "#5d6270", INK, 4)
    for k in range(9):
        xx = x - w / 2 + 40 + k * (w - 80) / 8
        cv.rect(xx - 26, y - 6, 52, 12, "#f2f2f2", None, 0, 4)
    rng = [(-0.33, -0.25, 1.0), (0.05, 0.3, 0.8), (0.3, -0.2, 0.9), (-0.1, 0.22, 0.7), (0.4, 0.28, 0.6)]
    for i, (fx, fy, sz) in enumerate(rng):
        a = ease(max(0.0, min(1.0, holes * len(rng) - i)))
        if a <= 0:
            continue
        px, py = x + fx * w, y + fy * h
        cv.ellipse(px, py, 46 * sz * a, 16 * sz * a, "#2e313a", INK, 3)
        cv.ellipse(px - 6, py - 4, 30 * sz * a, 8 * sz * a, "#3f434e")
        if patch > 0:
            pa = ease(max(0.0, min(1.0, patch * len(rng) - i)))
            if pa > 0:
                cv.ellipse(px, py, 50 * sz * pa, 18 * sz * pa, "#23252b", "#16181d", 3)


def cone(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 0, s):
        cv.poly([(-14, -70), (14, -70), (34, 0), (-34, 0)], "#f08a24", INK, 4)
        cv.rect(-24, -40, 48, 12, "#ffffff")
        cv.rect(-46, -6, 92, 14, "#f08a24", INK, 4, 4)


def truck(cv: Canvas, x, y, s=1.0, look=1, color="#f2c12e", t=0.0):
    with cv.at(x, y, 0, s * look, s):
        cv.rect(-180, -150, 230, 110, color, INK, 4, 10)
        cv.poly([(-180, -150), (50, -150), (30, -190), (-160, -190)], shade(color, -0.12), INK, 4)
        cv.rect(56, -130, 110, 90, shade(color, -0.05), INK, 4, 14)
        cv.rect(90, -118, 60, 40, "#bfe0f2", INK, 3, 6)
        cv.rect(-200, -46, 380, 20, "#4b4f5c", INK, 4, 6)
        for wx in (-120, 110):
            cv.circle(wx, -18, 36, "#2a2c33", INK, 4)
            cv.circle(wx, -18, 14, "#9aa3b5")
            ang = t * 6
            cv.line([(wx, -18), (wx + math.cos(ang) * 14, -18 + math.sin(ang) * 14)], INK, 3)


def building(cv: Canvas, x, y, w=220, h=420, color="#cfd8e6", windows="#7fa6d9", lit: float = 0.0):
    cv.rect(x - w / 2, y - h, w, h, color, INK, 4, 4)
    rows, cols = int(h // 70), max(2, int(w // 60))
    for r in range(rows):
        for c in range(cols):
            wx = x - w / 2 + 18 + c * (w - 36) / cols
            wy = y - h + 24 + r * 66
            cv.rect(wx, wy, (w - 36) / cols - 14, 36, windows if (r * 7 + c * 3) % 5 or lit <= 0 else "#ffe28a", INK, 2.5, 3)


def city_hall(cv: Canvas, x, y, s=1.0):
    with cv.at(x, y, 0, s):
        cv.rect(-300, -300, 600, 300, "#f1e9d8", INK, 4)
        cv.poly([(-330, -300), (0, -440), (330, -300)], "#e2d6bd", INK, 4)
        cv.circle(0, -350, 34, "#ffffff", INK, 4)
        cv.line([(0, -350), (0, -372)], INK, 4)
        cv.line([(0, -350), (16, -350)], INK, 4)
        for k in range(6):
            cx = -250 + k * 100
            cv.rect(cx - 18, -280, 36, 250, "#fbf7ee", INK, 3)
        cv.rect(-340, -34, 680, 34, "#d8ccb2", INK, 4)
        cv.rect(-50, -130, 100, 130, "#8a6a3a", INK, 4, 6)
        cv.line([(200, -440), (200, -560)], INK, 5)
        cv.poly([(200, -560), (290, -540), (200, -515)], "#3f7fd6", INK, 3)


def bubble(cv: Canvas, x, y, text: str, w=420, tail=(-1, 1), appear=1.0, size=34, color="#ffffff"):
    """A speech bubble with its tail towards (tail x, tail y) - the speaker's side and below."""
    k = back(appear)
    if k <= 0.01:
        return
    from .draw import _font, wrap
    lines = wrap(text, _font("extrabold", int(size * 4)), int((w - 50) * 4))
    h = 50 + len(lines) * size * 1.2
    with cv.at(x, y, 0, k):
        cv.poly([(tail[0] * 30, h / 2 - 10), (tail[0] * 90, h / 2 + 60 * tail[1]), (tail[0] * 80, h / 2 - 10)], color, INK, 4)
        cv.rect(-w / 2, -h / 2, w, h, color, INK, 4, 30)
        cv.poly([(tail[0] * 28, h / 2 - 14), (tail[0] * 80, h / 2 - 14), (tail[0] * 80, h / 2 + 2)], color)
        cv.text(text, 0, 0, size, INK, "extrabold", width=w - 50)


def magnifier(cv: Canvas, x, y, s=1.0, rot=-30):
    with cv.at(x, y, rot, s):
        cv.rect(-12, 60, 24, 110, "#6b4a2f", INK, 4, 8)
        cv.circle(0, 0, 70, "#d9eef9", INK, 7)
        cv.blend("#ffffff", 0.5, arc(-22, -22, 26, 16, 0, 360, 20))


def calendar(cv: Canvas, x, y, s=1.0, text="JAN", sub=""):
    with cv.at(x, y, 0, s):
        cv.rect(-90, -90, 180, 180, "#ffffff", INK, 4, 14)
        cv.rect(-90, -90, 180, 52, RED, INK, 4, 14)
        cv.text(text, 0, -64, 32, "#ffffff", "black")
        cv.text(sub, 0, 24, 56, INK, "black")


def tick(cv: Canvas, x, y, s=1.0, ok=True, appear=1.0):
    k = back(appear)
    if k <= 0.01:
        return
    with cv.at(x, y, 0, s * k):
        cv.circle(0, 0, 50, GREEN if ok else RED, INK, 4)
        if ok:
            cv.line([(-24, 2), (-6, 22), (26, -18)], "#ffffff", 12)
        else:
            cv.line([(-20, -20), (20, 20)], "#ffffff", 12)
            cv.line([(-20, 20), (20, -20)], "#ffffff", 12)


def price_tag(cv: Canvas, x, y, text: str, s=1.0, color=GOLD, appear=1.0, rot=-8):
    k = back(appear)
    if k <= 0.01:
        return
    with cv.at(x, y, rot, s * k):
        w = max(180, cv.text_width(text, 44) + 80)
        cv.poly([(-w / 2, -40), (w / 2 - 30, -40), (w / 2, 0), (w / 2 - 30, 40), (-w / 2, 40)], color, INK, 4)
        cv.circle(w / 2 - 34, 0, 8, "#ffffff", INK, 3)
        cv.text(text, -14, 2, 44, INK, "black")


def counter(cv: Canvas, x, y, value: float, size=90, prefix="$", suffix="", color=RED):
    """A number counting up (the caller passes the value of this picture)."""
    v = f"{value:,.0f}".replace(",", " ")
    cv.text(f"{prefix}{v}{suffix}", x, y, size, color, "black", outline=INK, stroke=5)
