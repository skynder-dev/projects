"""Drawing on a picture of a cartoon: shapes with smooth edges (OpenCV, sub-pixel), text (Pillow, the program's own
fonts), soft shadows - in "stage" units (a 1920 x 1080 or 1080 x 1920 stage) mapped onto the picture, through a stack
of moves, turns, sizes and mirrorings (a character's arm is drawn in the arm's own units).
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
FONTS = {"black": "Montserrat-Black.ttf", "extrabold": "Montserrat-ExtraBold.ttf", "semibold": "Montserrat-SemiBold.ttf"}
SHIFT = 4                                                  # (sub-pixel precision of OpenCV's shapes: 1/16 pixel)
INK = "#1f2433"                                            # (the outline colour of the whole style)


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

    def __init__(self, width: int, height: int, stage_w: float):
        self.W, self.H = int(width), int(height)
        self.k = self.W / float(stage_w)
        self.SW, self.SH = float(stage_w), self.H / self.k
        self.img = np.zeros((self.H, self.W, 3), np.uint8)
        self._m = [np.array([[self.k, 0, 0], [0, self.k, 0]], np.float64)]

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
        self.img[:] = hexc(color)

    def vgradient(self, top, bottom, y0: float = 0, y1: float | None = None):
        """The whole picture from one colour at the top to another at the bottom (stage y0..y1)."""
        y1 = self.SH if y1 is None else y1
        a, b = np.array(hexc(top), np.float32), np.array(hexc(bottom), np.float32)
        ys = (np.arange(self.H, dtype=np.float32) / self.k - y0) / max(1e-6, (y1 - y0))
        t = np.clip(ys, 0, 1)[:, None]
        self.img[:] = (a * (1 - t) + b * t).astype(np.uint8)[:, None, :]

    def poly(self, pts, fill=None, outline=None, width: float = 0, closed: bool = True):
        if len(pts) < 2:
            return
        p = self._px(pts)
        if fill is not None and len(pts) >= 3:
            cv2.fillPoly(self.img, [p], hexc(fill), cv2.LINE_AA, SHIFT)
        if outline is not None and width > 0:
            t = max(1, int(round(width * self._scale())))
            cv2.polylines(self.img, [p], closed, hexc(outline), t, cv2.LINE_AA, SHIFT)

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
