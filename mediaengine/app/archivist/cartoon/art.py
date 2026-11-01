"""Picture characters and backgrounds (Cartoon Studio, stage 2): pictures drawn once - by an AI picture model on this
PC or by a person - that the film moves, instead of the shapes the program draws itself.

A folder <HOME>/cartoon/art holds them:
  backgrounds/<bg>.png|jpg          a scene's background (bgs.BACKGROUNDS names: office, city ...), any size, cut to fit
  characters/<key>/<pose>.png       a character (library.key_of of its name) standing, the whole figure on a plain light
                                    background (cut away here); <pose>_open.png: the same with the mouth open
Poses: base (standing; needed), point, shrug, talk - a gesture without its own picture uses the nearest one (POSE_ART).
Nothing here is needed: without pictures a film is drawn as before.
"""
from __future__ import annotations

import math
import threading
from collections import deque
from pathlib import Path

import cv2
import numpy as np

EXT = (".png", ".jpg", ".jpeg", ".webp")
# our gestures -> the picture used for them, best first
POSE_ART = {
    "point": ("point",), "point_up": ("point",), "present": ("point", "shrug"), "money": ("point",), "paper": ("point",),
    "thumbs_up": ("point",), "wave": ("point",),
    "shrug": ("shrug",), "explain": ("shrug", "talk"), "hands_up": ("shrug",),
    "talk": ("talk",),
}
_lock = threading.Lock()
_cache: dict = {}                                          # path, mtime -> (bgr, alpha) at the picture's own size
_sized: dict = {}                                          # (path, mtime, w, h) -> (bgr, alpha) sized
_order: deque = deque()


def root() -> Path:
    from ..config import HOME
    return HOME / "cartoon" / "art"


def _find(folder: Path, stem: str) -> Path | None:
    for e in EXT:
        p = folder / (stem + e)
        if p.is_file():
            return p
    return None


def background(name: str, base: Path | None = None) -> Path | None:
    """The picture for a background name, if there is one."""
    try:
        return _find((base or root()) / "backgrounds", str(name))
    except OSError:
        return None


def character(name: str, base: Path | None = None) -> Path | None:
    """The folder of a character's pictures (it has a standing one), if there is one."""
    from .library import key_of
    try:
        d = (base or root()) / "characters" / key_of(name)
        return d if _find(d, "base") else None
    except OSError:
        return None


def pose_picture(folder: Path, pose: str, open_mouth: bool) -> Path:
    """The picture for a gesture (the nearest one there is), with the mouth open when asked and drawn."""
    for stem in POSE_ART.get(pose or "", ()) + ("base",):
        p = _find(folder, stem)
        if p:
            if open_mouth:
                q = _find(folder, stem + "_open") or (_find(folder, "talk_open") if stem == "base" else None)
                if q:
                    return q
            return p
    return _find(folder, "base")


def cut(img: np.ndarray, tol: int = 26) -> np.ndarray:
    """An alpha for a figure on a plain light background: what joins the picture's edge in that colour is cut away
    (not the white of a shirt inside the outline), with a soft edge."""
    h, w = img.shape[:2]
    bg = np.median(np.concatenate([img[0], img[-1], img[:, 0], img[:, -1]]), axis=0)
    near = (np.abs(img.astype(np.int16) - bg.astype(np.int16)).max(axis=2) <= tol).astype(np.uint8)
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flood = near.copy()
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if flood[y, x] == 1:
            cv2.floodFill(flood, mask, (x, y), 2)
    for x in range(0, w, 8):                               # (any part of the border in the background's colour)
        for y in (0, h - 1):
            if flood[y, x] == 1:
                cv2.floodFill(flood, mask, (x, y), 2)
    for y in range(0, h, 8):
        for x in (0, w - 1):
            if flood[y, x] == 1:
                cv2.floodFill(flood, mask, (x, y), 2)
    # (the background seen between the legs is closed in by the shoes: a patch of its colour in the lower part of the
    # figure is cut too - not the white of a shirt or a collar higher up)
    n, lab, stats, _c = cv2.connectedComponentsWithStats((flood == 1).astype(np.uint8), 8)
    for i in range(1, n):
        x_, y_, w_, h_, area = stats[i]
        if y_ + h_ > h * 0.75 and area > h * w * 0.0004:
            flood[lab == i] = 2
    alpha = (flood != 2).astype(np.float32)
    alpha = cv2.GaussianBlur(cv2.erode(alpha, np.ones((3, 3), np.uint8)), (3, 3), 0)
    return alpha


def _load(p: Path, figure: bool) -> tuple:
    key = (str(p), p.stat().st_mtime_ns, figure)
    with _lock:
        if key in _cache:
            return _cache[key]
    img = cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise OSError(f"not a picture: {p.name}")
    alpha = cut(img) if figure else np.ones(img.shape[:2], np.float32)
    if figure:                                             # (the figure's own box: feet at the bottom edge)
        ys, xs = np.where(alpha > 0.5)
        if len(ys):
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            img, alpha = img[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
    with _lock:
        _cache[key] = (img, alpha)
        if len(_cache) > 64:
            _cache.pop(next(iter(_cache)))
    return img, alpha


def _sized_pic(p: Path, w: int, h: int, figure: bool) -> tuple:
    key = (str(p), p.stat().st_mtime_ns, figure, w, h)
    with _lock:
        if key in _sized:
            return _sized[key]
    img, alpha = _load(p, figure)
    interp = cv2.INTER_AREA if w < img.shape[1] else cv2.INTER_CUBIC
    out = (cv2.resize(img, (w, h), interpolation=interp), cv2.resize(alpha, (w, h), interpolation=cv2.INTER_LINEAR)[..., None])
    with _lock:
        _sized[key] = out
        _order.append(key)
        while len(_order) > 48:
            _sized.pop(_order.popleft(), None)
    return out


def draw_background(cv, p: Path) -> None:
    """A background picture over the whole stage, cut to fit (its middle kept), through the camera's transform."""
    img, _a = _load(p, False)
    m = cv._m[-1]
    x0, y0 = m[0, 2], m[1, 2]                              # (stage (0, 0) and (SW, SH) in pixels)
    x1, y1 = m[0, 0] * cv.SW + m[0, 2], m[1, 1] * cv.SH + m[1, 2]
    W, H = max(1, int(round(x1 - x0))), max(1, int(round(y1 - y0)))
    ih, iw = img.shape[:2]
    k = max(W / iw, H / ih)
    w, h = max(W, int(math.ceil(iw * k))), max(H, int(math.ceil(ih * k)))
    pic, _ = _sized_pic(p, w, h, False)
    ox, oy = (w - W) // 2, (h - H) // 2
    pic = pic[oy:oy + H, ox:ox + W]
    cv.paste(pic, np.ones(pic.shape[:2] + (1,), np.float32), int(round(x0)), int(round(y0)))


HEIGHT = 700.0                                             # (a picture character as tall as a drawn one: its units)


def draw_character(cv, folder: Path, x: float, y: float, scale: float, look: float, pose: str, mouth: float, t: float,
                   walk: float | None = None, nod: float = 0.0, height: float = 1.0) -> None:
    """A picture character with its feet at stage (x, y): the gesture's picture, the mouth open on the loud parts of a
    word, breathing, a step's bounce when walking, turned by look (-1: mirrored; between: narrower while turning)."""
    m_open = (mouth[0] if isinstance(mouth, (tuple, list)) else float(mouth or 0.0)) > 0.28
    p = pose_picture(folder, pose, m_open)
    img, _a = _load(p, True)
    ih, iw = img.shape[:2]
    m = cv._m[-1]
    s = math.sqrt(abs(m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0]))
    breath = 1.0 + 0.008 * math.sin(t * 2.2)
    bob = -abs(math.sin(walk)) * 10 if walk is not None else 0.0
    h_px = max(4, int(round(HEIGHT * height * scale * s * breath * (1 - 0.012 * nod))))
    w_px = max(4, int(round(iw * h_px / ih * max(0.15, abs(look)))))
    pic, a = _sized_pic(p, w_px, h_px, True)
    if look < 0:
        pic, a = pic[:, ::-1], a[:, ::-1]
    fx, fy = m[0, 0] * x + m[0, 1] * (y + bob * scale) + m[0, 2], m[1, 0] * x + m[1, 1] * (y + bob * scale) + m[1, 2]
    sh = np.zeros((max(2, h_px // 40), max(4, int(w_px * 0.9)), 3), np.uint8)   # (a soft shadow under the feet)
    sa = cv2.GaussianBlur(np.pad(np.ones(sh.shape[:2], np.float32), 4), (0, 0), 3)[..., None] * 0.22
    cv.paste(np.zeros(sa.shape[:2] + (3,), np.uint8), sa, int(round(fx - sa.shape[1] / 2)), int(round(fy - sa.shape[0] / 2)))
    cv.paste(pic, a, int(round(fx - w_px / 2)), int(round(fy - h_px)))
