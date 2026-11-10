"""Picture characters and backgrounds (Cartoon Studio, stage 2): pictures drawn once - by an AI picture model on this
PC or by a person - that the film moves, instead of the shapes the program draws itself.

A folder <HOME>/cartoon/art holds them:
  backgrounds/<bg>.png|jpg          a scene's background (bgs.BACKGROUNDS names: office, city ...), any size, cut to fit
  characters/<key>/<pose>.png       a character (library.key_of of its name) standing, the whole figure on a plain light
                                    background (cut away here); <pose>_open.png: the same with the mouth open
Poses: base (standing; needed), point, shrug, talk, blink (the eyes shut) - a gesture without its own picture uses the nearest one (POSE_ART).
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


def background(name: str, base: Path | None = None, wide: bool = False) -> Path | None:
    """The picture for a background name, if there is one (for a wide film its wide picture first)."""
    try:
        d = (base or root()) / "backgrounds"
        return (_find(d, str(name) + "_wide") if wide else None) or _find(d, str(name))
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


def forget() -> None:
    """Pictures changed on disk: read them again."""
    with _lock:
        _cache.clear()
        _sized.clear()
        _order.clear()


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


def depth_of(p: Path) -> Path | None:
    """The picture's depth map (<stem>_depth.png, made by the picture add-on: light is near), if there is one."""
    q = p.with_name(p.stem + "_depth.png")
    return q if q.is_file() else None


_DEPTH: dict = {}


def _depth(q: Path, w: int, h: int) -> np.ndarray:
    """A depth map sized to (w, h), 0 far .. 1 near, smoothed (a sharp step in it tore the picture apart when it moved)."""
    key = (str(q), q.stat().st_mtime_ns, w, h)
    with _lock:
        if key in _DEPTH:
            return _DEPTH[key]
    d = cv2.imdecode(np.fromfile(str(q), np.uint8), cv2.IMREAD_UNCHANGED)
    if d is None:
        raise OSError(f"not a depth map: {q.name}")
    if d.ndim == 3:
        d = d[..., 0]
    d = cv2.resize(d.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    d = np.clip((d - lo) / max(1e-6, hi - lo), 0.0, 1.0)
    d = cv2.GaussianBlur(d, (0, 0), max(2.0, w / 160.0))
    with _lock:
        if len(_DEPTH) > 6:
            _DEPTH.pop(next(iter(_DEPTH)))
        _DEPTH[key] = d
    return d


_GRID: dict = {}
MOVES = ("push", "left", "right", "rise", "pull")
MARGIN = 1.07                                              # (the picture a little bigger than the screen: room to move)


def parallax(pic: np.ndarray, d: np.ndarray, p: float, move: str, amount: float = 1.0, size: tuple | None = None) -> np.ndarray:
    """The picture seen by a camera that moves a little through it (p: 0 .. 1 through the scene): what is near (light
    in the depth map) moves more than what is far - depth, not a flat picture sliding. pic is MARGIN times the screen."""
    h, w = pic.shape[:2]
    W, H = size or (int(round(w / MARGIN)), int(round(h / MARGIN)))
    p = p * p * (3 - 2 * p)                                # (eased: starts and stops softly)
    if _GRID.get("size") != (W, H):
        _GRID.update(size=(W, H), g=np.mgrid[0:H, 0:W].astype(np.float32))
    ys, xs = _GRID["g"]
    dd = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR) if d.shape[:2] != (H, W) else d
    near = 0.15 + 0.85 * dd
    cx, cy = W / 2.0, H / 2.0
    a = 0.028 * amount
    sx = sy = 1.0
    dx = dy = 0.0
    if move in ("push", "pull"):
        k = p if move == "push" else 1 - p
        s_ = 1.0 + 0.05 * amount * k * near                # (the near grows more than the far)
        sx = sy = s_
        dy = -0.006 * amount * k * near * H
    elif move in ("left", "right"):
        dx = (1 if move == "left" else -1) * a * W * (p - 0.5) * 2 * near
    elif move == "rise":
        dy = a * H * (p - 0.5) * 2 * near
    mx = (xs - cx) / sx + cx + dx + (w - W) / 2.0
    my = (ys - cy) / sy + cy + dy + (h - H) / 2.0
    return cv2.remap(pic, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def draw_background(cv, p: Path, move: tuple | None = None) -> None:
    """A background picture over the whole stage, cut to fit (its middle kept), through the camera's transform.
    move: (share of the scene gone 0 .. 1, how the camera moves, amount) - with a depth map the picture is seen in depth."""
    img, _a = _load(p, False)
    m = cv._m[-1]
    x0, y0 = m[0, 2], m[1, 2]                              # (stage (0, 0) and (SW, SH) in pixels)
    x1, y1 = m[0, 0] * cv.SW + m[0, 2], m[1, 1] * cv.SH + m[1, 2]
    W, H = max(1, int(round(x1 - x0))), max(1, int(round(y1 - y0)))
    ih, iw = img.shape[:2]
    q = depth_of(p) if move else None
    if q:
        try:
            WW, HH = int(round(W * MARGIN)), int(round(H * MARGIN))
            k = max(WW / iw, HH / ih)
            w, h = max(WW, int(math.ceil(iw * k))), max(HH, int(math.ceil(ih * k)))
            pic, _ = _sized_pic(p, w, h, False)
            ox, oy = (w - WW) // 2, (h - HH) // 2
            pic = pic[oy:oy + HH, ox:ox + WW]
            d = _depth(q, WW, HH)
            out = parallax(pic, d, float(move[0]), str(move[1]), float(move[2]) if len(move) > 2 else 1.0, (W, H))
            cv.paste(out, np.ones(out.shape[:2] + (1,), np.float32), int(round(x0)), int(round(y0)))
            return
        except (OSError, cv2.error, ValueError):
            pass                                           # (a broken depth map: the picture as it is)
    k = max(W / iw, H / ih)
    w, h = max(W, int(math.ceil(iw * k))), max(H, int(math.ceil(ih * k)))
    pic, _ = _sized_pic(p, w, h, False)
    ox, oy = (w - W) // 2, (h - H) // 2
    pic = pic[oy:oy + H, ox:ox + W]
    cv.paste(pic, np.ones(pic.shape[:2] + (1,), np.float32), int(round(x0)), int(round(y0)))


OPEN_MOUTHS = False
HEIGHT = 700.0                                             # (a picture character as tall as a drawn one: its units)


_MOUTH: dict = {}


def _mouth_state(key: str, opening: float, t: float, hold: float = 0.11) -> bool:
    """Open or shut, held at least a moment (a mouth flipping every picture looked like a twitch); open from 0.35,
    shut under 0.15 (between: as it was)."""
    was, since = _MOUTH.get(key, (False, -1.0))
    if t < since or t - since > 5:                         # (a new film or a jump: start again)
        was, since = False, t - hold
    want = True if opening > 0.35 else False if opening < 0.15 else was
    if want != was and t - since >= hold:
        _MOUTH[key] = (want, t)
        return want
    _MOUTH[key] = (was, since)
    return was


def draw_character(cv, folder: Path, x: float, y: float, scale: float, look: float, pose: str, mouth: float, t: float,
                   walk: float | None = None, nod: float = 0.0, height: float = 1.0, blink: float = 0.0) -> None:
    """A picture character with its feet at stage (x, y): the gesture's picture, the mouth open on the loud parts of a
    word, breathing, a step's bounce when walking, turned by look (-1: mirrored; between: narrower while turning)."""
    # (the mouth stays shut: a drawn picture swapped for its open-mouthed one looked cheap - the owner: "better shut")
    m_open = OPEN_MOUTHS and _mouth_state(str(folder), (mouth[0] if isinstance(mouth, (tuple, list)) else float(mouth or 0.0)), t)
    p = pose_picture(folder, pose, m_open)
    if blink > 0.5 and not m_open and walk is None and p.stem == "base":   # (eyes shut a moment: its own picture)
        p = _find(folder, "blink") or p
    img, _a = _load(p, True)
    ih, iw = img.shape[:2]
    m = cv._m[-1]
    s = math.sqrt(abs(m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0]))
    # (the picture's size never changes from frame to frame - resizing by a pixel made it shiver; breathing and a nod
    # are a small move up and down instead)
    bob = -abs(math.sin(walk)) * 10 if walk is not None else 2.5 * math.sin(t * 2.2) + 6 * nod
    h_px = max(4, int(round(HEIGHT * height * scale * s)))
    w_px = max(4, int(round(iw * h_px / ih * max(0.15, abs(look)))))
    pic, a = _sized_pic(p, w_px, h_px, True)
    if look < 0:
        pic, a = pic[:, ::-1], a[:, ::-1]
    fx, fy = m[0, 0] * x + m[0, 1] * (y + bob * scale) + m[0, 2], m[1, 0] * x + m[1, 1] * (y + bob * scale) + m[1, 2]
    sh = np.zeros((max(2, h_px // 40), max(4, int(w_px * 0.9)), 3), np.uint8)   # (a soft shadow under the feet)
    sa = cv2.GaussianBlur(np.pad(np.ones(sh.shape[:2], np.float32), 4), (0, 0), 3)[..., None] * 0.22
    cv.paste(np.zeros(sa.shape[:2] + (3,), np.uint8), sa, int(round(fx - sa.shape[1] / 2)), int(round(fy - sa.shape[0] / 2)))
    cv.paste(pic, a, int(round(fx - w_px / 2)), int(round(fy - h_px)))
