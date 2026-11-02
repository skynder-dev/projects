"""A web page in a cartoon: the page as one tall picture (Edge or Chrome on this PC, headless - nothing is installed)
and its text (for the story writer); a scene without a visual of its own then shows the page, scrolling down it from
scene to scene while the characters talk about it.

Kept in <HOME>/cartoon/sites/<sha of the address>/ (page.png, page.txt); a page is fetched again after a day.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

WIDTH, TALL = 1000, 7000


class SiteError(Exception):
    pass


def folder(url: str) -> Path:
    from ..config import HOME
    return HOME / "cartoon" / "sites" / hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def browser() -> str:
    """Edge or Chrome on this PC (MEDIAENGINE_BROWSER: another one)."""
    env = os.environ.get("MEDIAENGINE_BROWSER")
    if env and Path(env).is_file():
        return env
    cands = []
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            cands += [Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                      Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"]
    for c in cands:
        if c.is_file():
            return str(c)
    for name in ("msedge", "microsoft-edge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        w = shutil.which(name)
        if w:
            return w
    raise SiteError("Showing a web page needs Microsoft Edge or Google Chrome on this PC.")


def _text(dom: str) -> str:
    dom = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer)\b.*?</\1>", " ", dom)
    dom = re.sub(r"(?i)<(br|p|div|li|h\d|tr)\b[^>]*>", "\n", dom)
    t = html.unescape(re.sub(r"<[^>]+>", " ", dom))
    lines = [re.sub(r"[ \t ]+", " ", x).strip() for x in t.splitlines()]
    return "\n".join(x for x in lines if len(x) > 2)[:12000]


def fetch(url: str, refresh: bool = False) -> dict:
    """{"url", "image", "text"} of a page (from the cache when fresh)."""
    url = str(url or "").strip()
    if not re.match(r"(?i)^https?://[^\s/]+\.[^\s/]+", url):
        raise SiteError("Give the page's full address (https://…).")
    d = folder(url)
    png, txt = d / "page.png", d / "page.txt"
    if not refresh and png.is_file() and txt.is_file() and time.time() - png.stat().st_mtime < 86400:
        return {"url": url, "image": str(png), "text": txt.read_text("utf-8")}
    d.mkdir(parents=True, exist_ok=True)
    exe = browser()
    prof = d / "profile"                                   # (its own empty profile: never the person's signed-in one)
    common = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--disable-extensions",
              f"--user-data-dir={prof}", "--virtual-time-budget=8000"]
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        common.append("--no-sandbox")                      # (a Linux check machine running as root)
    try:
        dom = subprocess.run(common + ["--dump-dom", url], capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
        shot = d / "shot.png"
        subprocess.run(common + [f"--window-size={WIDTH},{TALL}", f"--screenshot={shot}", url], capture_output=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SiteError("The page could not be opened (" + type(exc).__name__ + ").")
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    text = _text(dom)
    if not shot.is_file() or len(text) < 40:
        raise SiteError("The page could not be read (it may need signing in, or block programs).")
    _trim(shot, png)
    txt.write_text(text, "utf-8")
    return {"url": url, "image": str(png), "text": text}


def _trim(src: Path, dst: Path) -> None:
    """The empty bottom of the tall window cut away (a short page leaves blank rows)."""
    import cv2
    import numpy as np
    img = cv2.imdecode(np.fromfile(str(src), np.uint8), cv2.IMREAD_COLOR)
    rows = np.where(np.abs(img.astype(np.int16) - img[-1:].astype(np.int16)).max(axis=(1, 2)) > 8)[0]
    bottom = int(rows[-1]) + 40 if len(rows) else img.shape[0]
    cv2.imencode(".png", img[:max(600, min(img.shape[0], bottom))])[1].tofile(str(dst))
    src.unlink(missing_ok=True)


def draw(cv, path: str, box: tuple, k0: float, k1: float, t: float) -> None:
    """The page in the visual's box: a window onto it, scrolled from k0 to k1 (shares of the page) as t goes 0..1."""
    import math
    import numpy as np
    from . import art
    from .draw import rounded
    cx, cy, bw, bh = box
    img, _a = art._load(Path(path), False)
    ih, iw = img.shape[:2]
    m = cv._m[-1]
    s = math.sqrt(abs(m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0]))
    W, H = max(8, int(bw * 0.92 * s)), max(8, int(bh * 0.92 * s))
    scale = W / iw
    view = int(H / scale)
    e = t * t * (3 - 2 * t)
    top = int((k0 + (k1 - k0) * e) * max(0, ih - view))
    crop = img[top:top + view]
    pic, _ = art._sized_pic(Path(path), W, int(ih * scale), False)
    y0 = int(top * scale)
    pic = pic[y0:y0 + H]
    x = m[0, 0] * cx + m[0, 1] * cy + m[0, 2] - W / 2
    y = m[1, 0] * cx + m[1, 1] * cy + m[1, 2] - H / 2
    cv.blend("#1f2433", 0.25, rounded(cx - bw * 0.46 + 8, cy - bh * 0.46 + 10, bw * 0.92, bh * 0.92, 18))
    cv.paste(pic, np.ones(pic.shape[:2] + (1,), np.float32), int(round(x)), int(round(y)))
    del crop
