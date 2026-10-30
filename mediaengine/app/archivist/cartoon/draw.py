"""Drawing on a picture of a cartoon: shapes with smooth edges (OpenCV, sub-pixel), text (Pillow, the program's own
fonts), soft shadows - in "stage" units (a 1920 x 1080 or 1080 x 1920 stage) mapped onto the picture, through a stack
of moves, turns, sizes and mirrorings (a character's arm is drawn in the arm's own units).

The drawing style (Canvas(style=...)): "flat" - clean shapes with dark outlines, as always; the others draw the very
same shapes another way - "hand" (wobbly marker lines on paper), "board" (black marker on a whiteboard, a few colours),
"paper" (cut-out paper shapes with shadows, no outlines), "motion" (bright shapes on a deep blue, soft glow).
"""
from __future__ import annotations

import colorsys
import math
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
FONTS = {"black": "Montserrat-Black.ttf", "extrabold": "Montserrat-ExtraBold.ttf", "semibold": "Montserrat-SemiBold.ttf"}
SHIFT = 4                                                  # (sub-pixel precision of OpenCV's shapes: 1/16 pixel)
INK = "#1f2433"                                            # (the outline colour of the whole style)
STYLES = ("flat", "hand", "board", "paper", "motion")
_WOBBLE = {"hand": (14.0, 2.4, 0.045), "board": (14.0, 1.2, 0.05), "paper": (9.0, 1.3, 0.11)}   # (step px, size px, waves)


def hexc(c) -> tuple:
    """A colour as OpenCV wants it (blue, green, red) from "#rrggbb" or (r, g, b)."""
    if isinstance(c, str):
        c = c.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    else:
        r, g, b = c[:3]
    return (int(b), int(g), int(r))


def mix(c1, c2, t: float) -> str:
    """A colour between two (t = 0: the first, 1: the second)."""
    a, b = hexc(c1), hexc(c2)
    v = [int(round(a[k] + (b[k] - a[k]) * t)) for k in range(3)]
    return "#%02x%02x%02x" % (v[2], v[1], v[0])


def shade(c, t: float) -> str:
    """Darker (t < 0) or lighter (t > 0)."""
    return mix(c, "#000000" if t < 0 else "#ffffff", abs(t))


def bezier(p0, p1, p2, p3, n: int = 16) -> list:
    out = []
    for k in range(n + 1):
        t = k / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def arc(cx, cy, rx, ry, a0: float, a1: float, n: int = 24) -> list:
    """Points along an ellipse from angle a0 to a1 (degrees, 0 = right, 90 = down)."""
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def rounded(x, y, w, h, r, n: int = 6) -> list:
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        pts += arc(cx, cy, r, r, a0, a0 + 90, n)
    return pts


@lru_cache(maxsize=64)
def _font(key: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONT_DIR / FONTS.get(key, FONTS["extrabold"])), max(6, int(size)))


@lru_cache(maxsize=512)
def _text_image(text: str, size: int, color: str, font: str, outline: str, stroke: int, width: int):
    """The text as a picture with its own transparency (cached: the same caption in every picture of a scene)."""
    from PIL import Image, ImageDraw
    f = _font(font, size)
    lines = wrap(text, f, width) if width else [text]
    tmp = ImageDraw.Draw(Image.new("L", (4, 4)))
    boxes = [tmp.textbbox((0, 0), ln or " ", font=f, stroke_width=stroke) for ln in lines]
    lh = int(size * 1.18)
    w = max(b[2] - b[0] for b in boxes) + 2 * stroke + 4
    h = lh * (len(lines) - 1) + (boxes[-1][3] - min(0, boxes[0][1])) + 2 * stroke + 4
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rgb = tuple(reversed(hexc(color)))
    orgb = tuple(reversed(hexc(outline))) if outline else None
    for k, ln in enumerate(lines):
        lw = boxes[k][2] - boxes[k][0]
        d.text(((w - lw) / 2 - boxes[k][0], stroke + 2 + k * lh), ln, font=f, fill=rgb + (255,),
               stroke_width=stroke if outline else 0, stroke_fill=(orgb + (255,)) if orgb else None)
    a = np.asarray(im)
    return np.ascontiguousarray(a[:, :, 2::-1]), (a[:, :, 3:4].astype(np.float32) / 255.0)


@lru_cache(maxsize=4096)
def _hsv(c) -> tuple:
    b, g, r = hexc(c)
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def _from_hsv(h: float, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


@lru_cache(maxsize=4096)
def _look_fill(style: str, c: str, big: bool) -> str:
    """A shape's colour in a drawing style (big: a sky, a wall, the ground - the scenery)."""
    h, s, v = _hsv(c)
    if style == "hand":
        return _from_hsv(h, s * 0.35, 0.95) if big else _from_hsv(h, s * 0.78, v * 0.97 + 0.04)
    if style == "board":
        return _from_hsv(h, s * 0.9, v * 1.05) if (s > 0.42 and v > 0.45 and not big) else "#fbfbf8"
    if style == "paper":
        return _from_hsv(h, s * 0.85 + 0.05, v * 0.93) if big else _from_hsv(h, s * 1.1 + (0.06 if s > 0.1 else 0), v * 0.95)
    if style == "motion":
        if big:
            return _from_hsv(0.68 + (h - 0.6) * 0.15, 0.55, 0.16 + v * 0.18)
        if h < 0.13 or h > 0.95:                           # (skin and hair stay as they are)
            return c
        if s < 0.18 and v > 0.7:
            return _from_hsv(0.64, 0.18, 0.86)
        if s > 0.35:
            return _from_hsv(h, s * 1.25, v * 1.08 + 0.04)
    return c


def _dense(p: np.ndarray, closed: bool, step: float) -> np.ndarray:
    """More points along a shape's edges (one every step units): its lines can wobble."""
    pts = np.vstack([p, p[:1]]) if closed else p
    seg = pts[1:] - pts[:-1]
    if not len(seg):
        return p
    n = np.clip((np.hypot(seg[:, 0], seg[:, 1]) / max(1e-6, step)).astype(np.int64), 1, 400)
    idx = np.repeat(np.arange(len(seg)), n)
    frac = (np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n)) / np.repeat(n, n)
    q = pts[:-1][idx] + seg[idx] * frac[:, None]
    return q if closed else np.vstack([q, pts[-1:]])


def _wave(ph: np.ndarray, amp: float, freq: float, seed: float) -> np.ndarray:
    """A smooth wobble (pixels, in OpenCV's sub-pixel units) for points at places ph."""
    x, y = ph[:, 0], ph[:, 1]
    dx = np.sin(x * freq + seed * 1.7) * np.cos(y * freq * 0.83 + seed) + 0.5 * np.sin((x + y) * freq * 2.1 + seed * 3.1)
    dy = np.cos(x * freq * 0.91 + seed * 2.3) * np.sin(y * freq * 1.07 + seed * 0.7) + 0.5 * np.cos((x - y) * freq * 1.9 + seed)
    return (np.stack([dx, dy], 1) * amp * (1 << SHIFT)).astype(np.int32)


@lru_cache(maxsize=4)
def _grain(w: int, h: int, amp: float) -> tuple:
    """Paper: fine grain and soft fibres (the same in every picture), as what is added and what is taken away."""
    r = np.random.default_rng(5)
    g = cv2.GaussianBlur(r.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.0)
    fib = cv2.resize(cv2.GaussianBlur(r.normal(0, 1, (max(1, h // 5), max(1, w // 5))).astype(np.float32), (0, 0), 1.6), (w, h))
    n = g * amp + fib * amp * 0.8
    up, down = np.clip(n, 0, 255).astype(np.uint8), np.clip(-n, 0, 255).astype(np.uint8)
    return cv2.merge([up, up, up]), cv2.merge([down, down, down])


@lru_cache(maxsize=2)
def _vignette(w: int, h: int) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - 0.45 * (((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2) * 2
    v = np.clip(v * 255, 0, 255).astype(np.uint8)
    return cv2.merge([v, v, v])


def wrap(text: str, font, width: int) -> list:
    out = []
    for para in str(text).split("\n"):
        words, cur = para.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if cur and font.getlength(t) > width:
                out.append(cur)
                cur = w
            else:
                cur = t
        out.append(cur)
    return out


class Canvas:
    """One picture of the film. Stage units -> pixels by k; shapes through the current transform."""

    def __init__(self, width: int, height: int, stage_w: float, style: str = "flat"):
        self.W, self.H = int(width), int(height)
        self.k = self.W / float(stage_w)
        self.SW, self.SH = float(stage_w), self.H / self.k
        self.img = np.zeros((self.H, self.W, 3), np.uint8)
        self._m = [np.array([[self.k, 0, 0], [0, self.k, 0]], np.float64)]
        self.style = style if style in STYLES else "flat"
        self.lens = 1.0                                    # (the camera's zoom now: the wobble of a line keeps its place)
        self.seed = 3.0

    # ------------------------------------------------------------------ transforms
    def push(self, x: float = 0, y: float = 0, rot: float = 0, sx: float = 1, sy: float | None = None):
        """Further shapes: moved to (x, y), turned by rot degrees, sized sx, sy (sy < 0 or sx < 0 mirrors)."""
        sy = sx if sy is None else sy
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        local = np.array([[c * sx, -s * sy, x], [s * sx, c * sy, y], [0, 0, 1]], np.float64)
        self._m.append(self._m[-1] @ local)
        return self

    def pop(self):
        if len(self._m) > 1:
            self._m.pop()
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.pop()

    def at(self, x=0, y=0, rot=0, sx=1, sy=None):
        """with canvas.at(...): shapes in a part's own units."""
        return self.push(x, y, rot, sx, sy)

    def _px(self, pts) -> np.ndarray:
        p = np.asarray(pts, np.float64).reshape(-1, 2)
        m = self._m[-1]
        q = p @ m[:, :2].T + m[:, 2]
        return np.round(q * (1 << SHIFT)).astype(np.int32)

    def _scale(self) -> float:
        m = self._m[-1]
        return math.sqrt(abs(m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0]))

    # ------------------------------------------------------------------ shapes
    def fill(self, color):
        color = {"hand": "#f3ecdf", "board": "#fbfbf8", "motion": "#141432"}.get(self.style, color)
        self.img[:] = hexc(color)

    def vgradient(self, top, bottom, y0: float = 0, y1: float | None = None):
        """The whole picture from one colour at the top to another at the bottom (stage y0..y1)."""
        if self.style in ("hand", "board", "motion"):
            top, bottom = {"hand": ("#f4eee2", "#efe6d6"), "board": ("#fdfdfb", "#f6f6f2"),
                           "motion": ("#1b1446", "#0c1b3a")}[self.style]
        elif self.style == "paper":
            (h, s, v), (h2, s2, v2) = _hsv(top), _hsv(bottom)
            top, bottom = _from_hsv(h, s * 0.7, v), _from_hsv(h2, s2 * 0.7, v2)
        y1 = self.SH if y1 is None else y1
        a, b = np.array(hexc(top), np.float32), np.array(hexc(bottom), np.float32)
        ys = (np.arange(self.H, dtype=np.float32) / self.k - y0) / max(1e-6, (y1 - y0))
        t = np.clip(ys, 0, 1)[:, None]
        self.img[:] = (a * (1 - t) + b * t).astype(np.uint8)[:, None, :]

    def poly(self, pts, fill=None, outline=None, width: float = 0, closed: bool = True):
        if len(pts) < 2:
            return
        if self.style != "flat":
            return self._poly_look(pts, fill, outline, width, closed)
        p = self._px(pts)
        if fill is not None and len(pts) >= 3:
            cv2.fillPoly(self.img, [p], hexc(fill), cv2.LINE_AA, SHIFT)
        if outline is not None and width > 0:
            t = max(1, int(round(width * self._scale())))
            cv2.polylines(self.img, [p], closed, hexc(outline), t, cv2.LINE_AA, SHIFT)

    def _wobbly(self, pts, closed: bool) -> tuple:
        """A shape's points with wobbling edges (and where they are, for a second wobble). The wobble belongs to the
        shape: it moves with it and stays the same while the camera slowly comes closer."""
        step, amp, freq = _WOBBLE[self.style]
        loc = np.asarray(pts, np.float64).reshape(-1, 2)
        sc = self._scale()
        dense = _dense(loc, closed, step / max(1e-6, sc))
        ph = dense * (sc / max(1e-6, self.lens))
        return self._px(dense) + _wave(ph, amp, freq, self.seed), ph

    def _poly_look(self, pts, fill, outline, width: float, closed: bool):
        """A shape in the drawing style (not "flat")."""
        st, sc = self.style, self._scale()
        p = self._px(pts)
        span = ((p.max(axis=0) - p.min(axis=0)) >> SHIFT) / np.array([self.W, self.H], np.float64)
        big = fill is not None and (span[0] * span[1] > 0.18 or span[0] > 0.6)       # (scenery: a sky, a wall, the ground)
        quiet = not closed and (span[0] > 0.55 or span[1] > 0.55)                   # (a long line: a grid, a horizon)
        shape = fill is not None and len(pts) >= 3
        aa = cv2.LINE_AA

        def thick(f: float) -> int:
            return max(1, int(round(width * sc * f)))

        if st == "motion":
            if shape:
                col = _look_fill(st, str(fill), big)
                cv2.fillPoly(self.img, [p], hexc(col), aa, SHIFT)
                if outline is not None and width > 0 and not big:
                    h, s, v = _hsv(col)
                    cv2.polylines(self.img, [p], True, hexc(_from_hsv(h, s + 0.1, v * 0.62)), thick(0.5), aa, SHIFT)
            elif outline is not None and width > 0:      # (a grid: deep blue; an arrow: light; a face's lines: dark)
                small = max(span[0] * self.W, span[1] * self.H) < 0.06 * max(self.W, self.H)
                col = "#2c3a78" if quiet else "#262b4a" if (closed or small) else "#7dd3fc"
                cv2.polylines(self.img, [p], closed, hexc(col), thick(0.6 if quiet else 0.5 if closed else 0.7), aa, SHIFT)
            return
        if st == "paper":
            if shape:
                q, _ph = self._wobbly(pts, closed)
                if not big and max(span[0] * self.W, span[1] * self.H) > 60 * self.k:   # (a soft shadow under a paper shape)
                    off = np.array([int(5 * self.k * (1 << SHIFT)), int(8 * self.k * (1 << SHIFT))], np.int32)
                    sh = q + off
                    x0, y0 = np.maximum((sh.min(axis=0) >> SHIFT) - 12, 0)
                    x1, y1 = np.minimum((sh.max(axis=0) >> SHIFT) + 14, [self.W, self.H])
                    if x1 > x0 and y1 > y0:
                        roi = self.img[y0:y1, x0:x1]
                        m = np.zeros(roi.shape[:2], np.uint8)
                        cv2.fillPoly(m, [sh - np.array([x0 << SHIFT, y0 << SHIFT], np.int32)], 255, aa, SHIFT)
                        m = cv2.GaussianBlur(m, (0, 0), 5 * self.k).astype(np.float32) * (0.42 / 255)
                        roi[:] = (roi.astype(np.float32) * (1 - m[..., None])).astype(np.uint8)
                cv2.fillPoly(self.img, [q], hexc(_look_fill(st, str(fill), big)), aa, SHIFT)
            elif outline is not None and width > 0 and not quiet:                # (a thin paper strip: glasses, a line)
                h, s, v = _hsv(str(outline))
                cv2.polylines(self.img, [p], closed, hexc(_from_hsv(h, s, max(v, 0.35))), thick(0.8), aa, SHIFT)
            return
        if quiet:                                          # hand, board: a faint pencil line
            q, _ph = self._wobbly(pts, closed)
            col, t = ("#d6ccba", thick(0.7)) if st == "hand" else ("#e4e4e0", 1)
            cv2.polylines(self.img, [q], False, hexc(col), t, aa, SHIFT)
            return
        soft = (shape and outline is None and max(span[0] * self.W, span[1] * self.H) < 0.04 * max(self.W, self.H)
                and _hsv(str(fill))[2] > 0.8 and _hsv(str(fill))[1] < 0.45)          # (a blush, a glint: no line)
        if soft and st == "board":
            return
        q, ph = self._wobbly(pts, closed)
        if shape:
            cv2.fillPoly(self.img, [q], hexc(_look_fill(st, str(fill), big)), aa, SHIFT)
        if st == "hand":
            if outline is not None and width > 0:
                cv2.polylines(self.img, [q + _wave(ph, 1.2, 0.09, self.seed + 5)], closed, hexc("#2b2622"), thick(1.15), aa, SHIFT)
            elif shape and not big and not soft:
                cv2.polylines(self.img, [q + _wave(ph, 1.5, 0.08, self.seed + 7)], closed, hexc("#3a332d"),
                              max(1, int(round(2 * self.k))), aa, SHIFT)
            return
        if outline is not None or shape:                   # board: black marker (grey on the scenery)
            w = max(width, 2.2)
            cv2.polylines(self.img, [q], closed, hexc("#9a9a9a" if big else "#222222"),
                          max(1, int(round(w * sc * (0.6 if big else 1.0)))), aa, SHIFT)

    def finish(self):
        """The picture's last touch in the drawing style: the paper's grain, the glow of motion graphics."""
        if self.style in ("hand", "paper", "board"):
            up, down = _grain(self.W, self.H, {"hand": 6.0, "paper": 13.0, "board": 2.5}[self.style])
            cv2.add(self.img, up, dst=self.img)
            cv2.subtract(self.img, down, dst=self.img)
        elif self.style == "motion":
            small = cv2.resize(self.img, (max(1, self.W // 4), max(1, self.H // 4)), interpolation=cv2.INTER_AREA)
            glow = cv2.resize(cv2.GaussianBlur(small, (0, 0), 4.5), (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            cv2.addWeighted(self.img, 1.0, glow, 0.18, 0, dst=self.img)
            cv2.multiply(self.img, _vignette(self.W, self.H), dst=self.img, scale=1 / 255)
        return self

    def line(self, pts, color, width: float):
        self.poly(pts, None, color, width, closed=False)

    def circle(self, x, y, r, fill=None, outline=None, width: float = 0):
        self.poly(arc(x, y, r, r, 0, 360, max(16, min(72, int(r * self._scale() / 2)))), fill, outline, width)

    def ellipse(self, x, y, rx, ry, fill=None, outline=None, width: float = 0, a0: float = 0, a1: float = 360):
        n = max(16, min(72, int(max(rx, ry) * self._scale() / 2)))
        pts = arc(x, y, rx, ry, a0, a1, n)
        if a1 - a0 < 360:
            pts = [(x, y)] + pts
        self.poly(pts, fill, outline, width)

    def rect(self, x, y, w, h, fill=None, outline=None, width: float = 0, r: float = 0):
        self.poly(rounded(x, y, w, h, r), fill, outline, width)

    def blend(self, color, alpha: float, pts):
        """A see-through shape (a shadow, a highlight): drawn on a copy of its box and mixed in."""
        if self.style in ("board", "hand"):
            alpha *= 0.5
        elif self.style == "motion":
            if str(color).lower() in ("#000000", "#000"):
                alpha = min(1.0, alpha * 1.3)
            elif _hsv(str(color))[1] < 0.2 and _hsv(str(color))[2] > 0.75:     # (a light card: frosted glass)
                color, alpha = "#dfe4ff", alpha * 0.72
        p = self._px(pts)
        x0, y0 = np.maximum(p.min(axis=0) >> SHIFT, 0)
        x1, y1 = np.minimum((p.max(axis=0) >> SHIFT) + 2, [self.W, self.H])
        if x1 <= x0 or y1 <= y0:
            return
        roi = self.img[y0:y1, x0:x1]
        layer = roi.copy()
        q = p - np.array([x0 << SHIFT, y0 << SHIFT], np.int32)
        cv2.fillPoly(layer, [q], hexc(color), cv2.LINE_AA, SHIFT)
        cv2.addWeighted(layer, alpha, roi, 1 - alpha, 0, dst=roi)

    def shadow(self, x, y, rx, ry, alpha: float = 0.22):
        self.blend("#000000", alpha, arc(x, y, rx, ry, 0, 360, 36))

    def text(self, text: str, x: float, y: float, size: float, color="#ffffff", font: str = "extrabold",
             outline: str | None = None, stroke: float = 0, width: float = 0, anchor: str = "mm", alpha: float = 1.0):
        """Text at a stage point (anchor: l/m/r + t/m/b), size and wrap width in stage units (no turning)."""
        m = self._m[-1]
        sc = self._scale()
        px = int(round(size * sc))
        if px < 4 or not str(text).strip():
            return
        if self.style == "board":                          # (marker: black, or a colour that stands out)
            _h, s, v = _hsv(str(color))
            color, outline, stroke = ("#222222" if s < 0.4 or v < 0.5 else color), None, 0
        rgb, a = _text_image(str(text), px, str(color), font, str(outline or ""), int(round(stroke * sc)), int(width * sc))
        h, w = rgb.shape[:2]
        cx, cy = m[0, 0] * x + m[0, 1] * y + m[0, 2], m[1, 0] * x + m[1, 1] * y + m[1, 2]
        x0 = int(round(cx - (w / 2 if anchor[0] == "m" else (w if anchor[0] == "r" else 0))))
        y0 = int(round(cy - (h / 2 if anchor[1] == "m" else (h if anchor[1] == "b" else 0))))
        self.paste(rgb, a * alpha, x0, y0)

    def paste(self, rgb: np.ndarray, a: np.ndarray, x0: int, y0: int):
        h, w = rgb.shape[:2]
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(self.W, x0 + w), min(self.H, y0 + h)
        if X1 <= X0 or Y1 <= Y0:
            return
        sub = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0))
        roi = self.img[Y0:Y1, X0:X1].astype(np.float32)
        aa = a[sub]
        self.img[Y0:Y1, X0:X1] = (rgb[sub].astype(np.float32) * aa + roi * (1 - aa)).astype(np.uint8)

    def text_width(self, text: str, size: float, font: str = "extrabold") -> float:
        return _font(font, int(round(size * 4))).getlength(str(text)) / 4.0


def ease(t: float) -> float:
    """Smooth start and end (0..1 -> 0..1)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def back(t: float, s: float = 1.6) -> float:
    """An ease that overshoots a little and settles (things that pop in)."""
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
