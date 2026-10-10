"""Deterministic vertical-video renderer: Pillow frames piped into ffmpeg (H.264 + AAC, 1080x1920).

This is Social's built-in renderer (the "equivalent local adapter" in the DONE definition).
It also writes a MediaEngine handoff folder (stills + per-segment narration + timeline) so the
same package can be re-rendered by MediaEngine on Windows without changing Social.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import ASSETS, PipelineError

W, H, FPS = 1080, 1920, 30
BG_TOP, BG_BOT = (16, 28, 46), (6, 10, 18)
ACCENT = (242, 179, 61)
WHITE = (245, 247, 250)
MUTED = (160, 176, 200)
DIM = (110, 124, 146)
MARGIN = 84
CENTER_Y = 900
FONT = {
    "xbold": ASSETS / "fonts" / "InterDisplay-ExtraBold.otf",
    "bold": ASSETS / "fonts" / "InterDisplay-Bold.otf",
    "semi": ASSETS / "fonts" / "Inter-SemiBold.otf",
    "med": ASSETS / "fonts" / "Inter-Medium.otf",
}
_font_cache: dict = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    k = (kind, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(str(FONT[kind]), size)
    return _font_cache[k]


def _text_w(txt, f):
    return f.getlength(txt)


def wrap(txt: str, f, max_w: int) -> list[str]:
    lines = []
    for para in str(txt).split("\n"):
        words, cur = [], ""
        for w in para.split():                      # split over-long tokens (e.g. IDs) at hyphens
            if _text_w(w, f) <= max_w or "-" not in w:
                words.append(w)
                continue
            part = ""
            for piece in re.split(r"(?<=-)", w):
                if part and _text_w(part + piece, f) > max_w:
                    words.append(part)
                    part = piece
                else:
                    part += piece
            if part:
                words.append(part)
        for w in words:
            t = (cur + " " + w).strip()
            if _text_w(t, f) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def fit(txt, kind, max_w, max_lines, start, minimum):
    size = start
    while size > minimum:
        f = font(kind, size)
        lines = wrap(txt, f, max_w)
        if len(lines) <= max_lines and all(_text_w(l, f) <= max_w for l in lines):
            return f, lines
        size -= 4
    f = font(kind, minimum)
    return f, wrap(txt, f, max_w)


def background() -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W * 0.15, CENTER_Y - 520, W * 1.1, CENTER_Y + 420], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    tint = Image.new("RGB", (W, H), (40, 70, 120))
    return Image.composite(tint, img, glow)


class Block:
    def __init__(self, lines, f, color, spacing=1.12, bullet=False, align="left", gap_after=28, track=0):
        self.lines, self.f, self.color, self.spacing = lines, f, color, spacing
        self.bullet, self.align, self.gap_after, self.track = bullet, align, gap_after, track
        asc, desc = f.getmetrics()
        self.lh = int((asc + desc) * spacing)
        self.h = self.lh * len(lines)

    def render(self) -> Image.Image:
        im = Image.new("RGBA", (W, max(1, self.h)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i, line in enumerate(self.lines):
            y = i * self.lh
            x = MARGIN
            if self.bullet:
                r = int(self.f.size * 0.16)
                cy = y + int(self.lh * 0.5)
                d.ellipse([x, cy - r, x + 2 * r, cy + r], fill=ACCENT)
                x += int(self.f.size * 0.75)
            if self.track:
                for ch in line:
                    d.text((x, y), ch, font=self.f, fill=self.color)
                    x += _text_w(ch, self.f) + self.track
            else:
                d.text((x, y), line, font=self.f, fill=self.color)
        return im


def layout(seg: dict) -> list[Block]:
    s = seg.get("on_screen") or {}
    kind = seg.get("visual", "stat")
    mw = W - 2 * MARGIN
    B: list[Block] = []
    if s.get("kicker"):
        B.append(Block([s["kicker"].upper()], font("semi", 38), ACCENT, gap_after=26, track=3))
    if kind in ("hook", "stat", "date") and s.get("big"):
        f, lines = fit(s["big"], "xbold", mw, 2, 230 if kind != "stat" else 200, 96)
        B.append(Block(lines, f, WHITE if kind != "date" else ACCENT, spacing=1.0, gap_after=18))
        if s.get("headline"):
            f, lines = fit(s["headline"], "bold", mw, 3, 76, 48)
            B.append(Block(lines, f, ACCENT if kind != "date" else WHITE, gap_after=34))
    elif kind == "list":
        items = [x for x in str(s.get("headline", "")).split("\n") if x.strip()]
        size = 64 if len(items) <= 3 else (54 if len(items) <= 5 else 46)
        for it in items:
            f, lines = fit(it, "bold", mw - 60, 2, size, 38)
            B.append(Block(lines, f, WHITE, bullet=True, gap_after=22))
    elif kind == "quote":
        B.append(Block(["“"], font("xbold", 180), ACCENT, spacing=0.62, gap_after=0))
        q = str(s.get("headline", "")).strip("“”\"")
        f, lines = fit(q, "bold", mw, 9, 66, 40)
        B.append(Block(lines, f, WHITE, spacing=1.18, gap_after=34))
    elif kind == "source":
        f, lines = fit(str(s.get("headline", "")), "bold", mw - 120, 2, 72, 40)
        B.append(Block(lines, f, WHITE, gap_after=34))
    else:  # title / fallback
        f, lines = fit(str(s.get("headline", "")), "bold", mw, 8, 88, 46)
        B.append(Block(lines, f, WHITE, spacing=1.1, gap_after=34))
    if s.get("sub"):
        f, lines = fit(s["sub"], "med", mw, 3, 44, 32)
        B.append(Block(lines, f, MUTED, gap_after=0))
    return B


def compose_segment(seg: dict, footer: str):
    """Return (base_without_content, [(layer, y)], hold_frame)."""
    base = background()
    d = ImageDraw.Draw(base)
    chip_f = font("semi", 30)
    label = "FEDERAL FUNDING · GRANTS.GOV"
    tw = _text_w(label, chip_f)
    d.rounded_rectangle([MARGIN, 186, MARGIN + tw + 48, 242], radius=28, outline=ACCENT, width=3)
    d.text((MARGIN + 24, 197), label, font=chip_f, fill=ACCENT)
    ff = font("med", 30)
    for i, line in enumerate(footer.split("\n")[:2]):
        d.text((MARGIN, 1470 + i * 42), line, font=ff, fill=DIM)
    blocks = layout(seg)
    total = sum(b.h + b.gap_after for b in blocks) - (blocks[-1].gap_after if blocks else 0)
    y = int(CENTER_Y - total / 2)
    y = max(300, min(y, 1440 - total))
    placed = []
    for b in blocks:
        placed.append((b.render(), y))
        if seg.get("visual") == "source" and b.color == WHITE:
            pad = 26
            d.rounded_rectangle([MARGIN - 20, y - pad, W - MARGIN + 20, y + b.h + pad], radius=34,
                                fill=(24, 38, 60), outline=(70, 92, 124), width=3)
            cx, cy = W - MARGIN - 40, y + b.h // 2
            d.ellipse([cx - 22, cy - 26, cx + 14, cy + 10], outline=ACCENT, width=6)
            d.line([cx + 8, cy + 4, cx + 26, cy + 22], fill=ACCENT, width=8)
        y += b.h + b.gap_after
    hold = base.copy()
    for layer, ly in placed:
        hold.paste(layer, (0, ly), layer)
    return base, placed, hold


def _ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def draw_progress(img, n, i, frac):
    d = ImageDraw.Draw(img)
    x0, x1, y, h, gap = MARGIN, W - MARGIN, 112, 7, 10
    w = (x1 - x0 - gap * (n - 1)) / n
    for k in range(n):
        a = x0 + k * (w + gap)
        d.rounded_rectangle([a, y, a + w, y + h], radius=3, fill=(70, 82, 104))
        f = 1.0 if k < i else (frac if k == i else 0.0)
        if f > 0:
            d.rounded_rectangle([a, y, a + max(h, w * f), y + h], radius=3, fill=WHITE)


def build_audio(seg_wavs: list[Path], out: Path, lead=0.18, tail=0.42, final_tail=1.1) -> list[float]:
    """Concatenate segment narration with pauses; return each segment's on-screen duration."""
    params = None
    frames_out = []
    durs = []
    for k, p in enumerate(seg_wavs):
        with wave.open(str(p), "rb") as w:
            pr = (w.getnchannels(), w.getsampwidth(), w.getframerate())
            if params and pr != params:
                raise PipelineError(f"segment audio format mismatch: {pr} vs {params}")
            params = pr
            data = w.readframes(w.getnframes())
            speech = w.getnframes() / w.getframerate()
        ch, sw, sr = params
        t = final_tail if k == len(seg_wavs) - 1 else tail
        sil = lambda s: b"\x00" * (int(sr * s) * ch * sw)
        frames_out += [sil(lead), data, sil(t)]
        durs.append(lead + speech + t)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(params[0])
        w.setsampwidth(params[1])
        w.setframerate(params[2])
        w.writeframes(b"".join(frames_out))
    return durs


def render_video(segments: list[dict], durations: list[float], narration: Path, out_mp4: Path,
                 footer: str, stills_dir: Path) -> dict:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise PipelineError("ffmpeg not installed")
    stills_dir.mkdir(parents=True, exist_ok=True)
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(narration),
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-r", str(FPS), "-g", str(FPS * 2),
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", "-shortest", str(out_mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    n = len(segments)
    total_frames = 0
    stills = []
    try:
        for i, (seg, dur) in enumerate(zip(segments, durations)):
            base, placed, hold = compose_segment(seg, footer)
            sp = stills_dir / f"segment_{i + 1:02d}.png"
            hold.save(sp, optimize=True)
            stills.append(sp)
            nf = max(1, round(dur * FPS))
            anim_frames = int(0.55 * FPS)
            for fidx in range(nf):
                t = fidx / FPS
                if fidx < anim_frames:
                    img = base.copy()
                    for bi, (layer, ly) in enumerate(placed):
                        p = _ease((t - bi * 0.07) / 0.35)
                        if p <= 0:
                            continue
                        lay = layer if p >= 1 else _fade(layer, p)
                        img.paste(lay, (0, ly + int((1 - p) * 40)), lay)
                else:
                    img = hold.copy()
                draw_progress(img, n, i, (fidx + 1) / nf)
                proc.stdin.write(img.tobytes())
                total_frames += 1
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        rc = proc.wait()
    except BrokenPipeError:
        err = proc.stderr.read().decode(errors="replace")
        rc = proc.wait()
    if rc != 0:
        raise PipelineError(f"ffmpeg failed ({rc}): {err[-800:]}")
    return {"frames": total_frames, "fps": FPS, "width": W, "height": H, "stills": [s.name for s in stills],
            "encoder": "libx264 veryfast crf20 yuv420p + aac 160k 48kHz, loudnorm I=-16"}


def _fade(layer: Image.Image, p: float) -> Image.Image:
    a = layer.getchannel("A").point(lambda v: int(v * p))
    out = layer.copy()
    out.putalpha(a)
    return out
