"""Text on video: caption styles and text blocks (a hook, text at a moment, a call to action) as one ASS document that
FFmpeg's subtitle renderer (libass) burns in. The fonts ship with the program (Montserrat, SIL Open Font License 1.1,
Latin + Cyrillic: assets/fonts) so the picture is the same on every PC; nothing here needs the voice add-on.

The lines are laid out here (measured with the same font files through Pillow), not by the renderer: so a box can be
drawn behind exactly the text, a word too long for the line gets a smaller size instead of running off the picture,
and the said word can be highlighted without the line jumping to another wrap.
"""
from __future__ import annotations

import re
import shutil
import unicodedata
from functools import lru_cache
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FONTS = {          # key -> (family name the renderer matches, file)
    "black": ("Montserrat Black", "Montserrat-Black.ttf"),
    "extrabold": ("Montserrat ExtraBold", "Montserrat-ExtraBold.ttf"),
    "semibold": ("Montserrat SemiBold", "Montserrat-SemiBold.ttf"),
}
COLORS = {"yellow": ("Yellow", "FFD60A"), "green": ("Green", "3DDC84"), "pink": ("Pink", "FF4FA3"),
          "blue": ("Blue", "38BDF8"), "orange": ("Orange", "FF9F0A"), "white": ("White", "FFFFFF")}
SIZES = {"small": ("Small", 0.82), "medium": ("Medium", 1.0), "large": ("Large", 1.2)}
POSITIONS = {"bottom": "at the bottom", "middle": "in the middle", "top": "at the top"}
STYLES = {
    "pop": {"label": "Bold capitals, the word being said in color (like Reels)", "font": "black", "upper": True, "words": 3,
            "mode": "word", "size": 0.08, "outline": 0.12, "shadow": 0.05},
    "box": {"label": "On a dark box, the word being said in color", "font": "extrabold", "upper": False, "words": 4,
            "mode": "word", "size": 0.07, "box": True},
    "classic": {"label": "Classic: white with an outline, the words said turn to the color", "font": "extrabold",
                "upper": False, "words": 4, "mode": "karaoke", "size": 0.076, "outline": 0.09, "shadow": 0.03},
    "minimal": {"label": "Calm: white with a soft shadow, no highlight (business)", "font": "semibold", "upper": False,
                "words": 6, "mode": "plain", "size": 0.062, "outline": 0.035, "shadow": 0.07},
}
DEFAULT_STYLE, DEFAULT_COLOR, DEFAULT_SIZE = "pop", "yellow", "medium"
LOOKS = {"banner": "On a colored stripe", "bold": "Big white letters", "box": "On a dark box"}
TEXT_MAX = 120
TEXTS_MAX = 12


class TextError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------------- helpers
def tag_color(hex6: str) -> str:
    """'RRGGBB' -> the colour of an override tag, '&HBBGGRR&'."""
    return f"&H{hex6[4:6]}{hex6[2:4]}{hex6[0:2]}&".upper()


def _t(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def clean_text(t: str, limit: int = TEXT_MAX) -> str:
    """What a font can draw: emoji, pictographs, joiners and control characters are left out (they would be boxes);
    braces and backslashes cannot become renderer commands."""
    keep = []
    for ch in str(t or ""):
        o = ord(ch)
        if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or o in (0x200D, 0xFE0F, 0xFE0E, 0x20E3) \
                or 0xE000 <= o <= 0xF8FF:
            continue
        if ch == "\n":
            keep.append(ch)
            continue
        if unicodedata.category(ch) in ("Cc", "Cf", "Co", "Cs"):
            continue
        keep.append({"\\": "/", "{": "(", "}": ")"}.get(ch, ch))
    lines = [" ".join(x.split()) for x in "".join(keep).split("\n")]
    return "\n".join(x for x in lines if x)[:limit].strip()


@lru_cache(maxsize=64)
def _pil_font(key: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONT_DIR / FONTS[key][1]), size)


@lru_cache(maxsize=8)
def _em_ratio(key: str) -> float:
    """The renderer's font size is the line height (ascent + descent); Pillow's is the em: the factor between them."""
    f = _pil_font(key, 1000)
    asc, desc = f.getmetrics()
    return 1000.0 / max(1, asc + desc)


def text_width(text: str, key: str, size: float) -> float:
    if not text:
        return 0.0
    return float(_pil_font(key, max(4, int(round(size * _em_ratio(key) * 4)))).getlength(text)) / 4.0


def fit_lines(text: str, key: str, size: float, maxw: float, max_lines: int = 3) -> tuple[list[str], float]:
    """Greedy wrap at `size`; smaller (down to 55%) while a word is wider than the line or there are too many lines."""
    paras = [p.split() for p in text.split("\n") if p.strip()]
    s = size
    while True:
        lines: list[str] = []
        for words in paras:
            cur = ""
            for w in words:
                t = (cur + " " + w).strip()
                if not cur or text_width(t, key, s) <= maxw:
                    cur = t
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
        widest = max((text_width(x, key, s) for x in lines), default=0)
        if (widest <= maxw and len(lines) <= max_lines) or s <= size * 0.55:
            return lines, s
        s *= 0.92


def _rounded(w: float, h: float, r: float) -> str:
    """An ASS drawing of a rounded rectangle (0,0)-(w,h)."""
    r = max(0.0, min(r, w / 2, h / 2))
    k = r * 0.45                       # bezier handle for a quarter circle (close enough at these sizes)
    n = lambda v: f"{v:.1f}".rstrip("0").rstrip(".")
    return (f"m {n(r)} 0 l {n(w - r)} 0 b {n(w - k)} 0 {n(w)} {n(k)} {n(w)} {n(r)} l {n(w)} {n(h - r)} "
            f"b {n(w)} {n(h - k)} {n(w - k)} {n(h)} {n(w - r)} {n(h)} l {n(r)} {n(h)} b {n(k)} {n(h)} 0 {n(h - k)} 0 {n(h - r)} "
            f"l 0 {n(r)} b 0 {n(k)} {n(k)} 0 {n(r)} 0")


def options(style: str | None = None, color: str | None = None, size: str | None = None,
            position: str | None = None) -> dict:
    return {"style": style if style in STYLES else DEFAULT_STYLE, "color": color if color in COLORS else DEFAULT_COLOR,
            "size": size if size in SIZES else DEFAULT_SIZE, "position": position if position in POSITIONS else "bottom"}


def _secs(v, what: str) -> float | None:
    s = str(v if v is not None else "").strip().replace(",", ".")
    if not s:
        return None
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", s)
    if not m:
        raise TextError(f"{what}: write seconds, for example 2.5 or 0:12.")
    return int(m.group(1) or 0) * 60 + float(m.group(2))


def parse_texts(rows: list[dict]) -> list[dict]:
    """Text blocks from the form: text, from, to (seconds or m:ss; empty 'to' = 3 s later), where, look. 'end' (or
    'конец') as 'from' = the last 3 seconds of the finished video, whatever its length. Empty rows are skipped."""
    out = []
    for r in rows[:TEXTS_MAX * 2]:
        text = clean_text(r.get("text") or "")
        if not text:
            continue
        start_raw = str(r.get("start") or "").strip().lower()
        item = {"text": text, "where": r.get("where") if r.get("where") in POSITIONS else "top",
                "look": r.get("look") if r.get("look") in LOOKS else "banner"}
        if start_raw in ("end", "конец"):
            item.update(at_end=True, start=None, end=None)
        else:
            s = _secs(start_raw, "When the text appears") or 0.0
            e = _secs(r.get("end"), "When the text goes")
            e = s + 3.0 if e is None else e
            if e - s < 0.3:
                raise TextError("A text must be on the screen for at least 0.3 s (check its times).")
            item.update(start=round(s, 2), end=round(e, 2))
        out.append(item)
        if len(out) >= TEXTS_MAX:
            break
    return out


def resolve_texts(texts: list[dict] | None, length: float) -> list[dict]:
    """The blocks with their real times in a video of `length` seconds: 'at the end' = the last 3 s; a block after
    the end is left out, one running past it is cut there."""
    out = []
    for t in texts or []:
        if t.get("at_end"):
            s, e = max(0.0, length - 3.0), length
        else:
            s, e = float(t.get("start") or 0), float(t.get("end") or 0)
        e = min(e, length)
        if e - s >= 0.2 and t.get("text"):
            out.append({**t, "start": s, "end": e})
    return out


def hook_and_end(hook: str = "", end: str = "") -> list[dict]:
    """The two quick texts of the simple forms: a title at the top for the first 3 seconds, a line at the end."""
    rows = []
    if clean_text(hook):
        rows.append({"text": hook, "start": "0", "end": "3", "where": "top", "look": "banner"})
    if clean_text(end):
        rows.append({"text": end, "start": "end", "where": "middle", "look": "banner"})
    return parse_texts(rows)


def rows_from_form(f) -> list[dict]:
    """The text rows of a form (lists t_text, t_start, t_end, t_where, t_look of the same length)."""
    cols = [f.getlist(k) for k in ("t_text", "t_start", "t_end", "t_where", "t_look")]
    n = max((len(c) for c in cols), default=0)
    get = lambda c, i: c[i] if i < len(c) else ""
    return [{"text": get(cols[0], i), "start": get(cols[1], i), "end": get(cols[2], i), "where": get(cols[3], i),
             "look": get(cols[4], i)} for i in range(n)]


def retime(cue: dict, text: str) -> dict | None:
    """A caption whose words were edited: the same time span, the new words share it by their length."""
    words = clean_text(text, 200).split()
    if not words:
        return None
    old = cue["words"]
    if [w["w"] for w in old] == words:
        return cue
    if len(words) == len(old):
        return {**cue, "words": [{**o, "w": w} for o, w in zip(old, words)]}
    s, e = old[0]["s"], old[-1]["e"]
    total = sum(len(w) + 1 for w in words)
    out, t = [], s
    for w in words:
        d = (e - s) * (len(w) + 1) / total
        out.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
        t += d
    return {**cue, "words": out}


def install_fonts(d: Path) -> bool:
    """The program's fonts copied next to the subtitles (d/fonts; FFmpeg is given 'fontsdir=fonts' with cwd d - a
    relative path, no drive letter to escape)."""
    try:
        (d / "fonts").mkdir(parents=True, exist_ok=True)
        n = 0
        for _fam, f in FONTS.values():
            if (FONT_DIR / f).is_file():
                shutil.copy2(FONT_DIR / f, d / "fonts" / f)
                n += 1
        return n > 0
    except OSError:
        return False


# ------------------------------------------------------------------------------------------------- the document
def document(width: int, height: int, cues: list[dict] | None = None, texts: list[dict] | None = None,
             opts: dict | None = None, offset: float = 0.0) -> str:
    """One ASS document: the captions (cues of timed words) in the chosen style, and the text blocks."""
    o = options(**(opts or {}))
    W, H = int(width), int(height)
    base = min(W, H)
    head = ("[Script Info]\nScriptType: v4.00+\nWrapStyle: 2\nScaledBorderAndShadow: yes\nYCbCr Matrix: TV.709\n"
            f"PlayResX: {W}\nPlayResY: {H}\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            "Style: Base,Montserrat ExtraBold,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,"
            "5,0,0,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ev: list[str] = []
    if cues:
        ev += _captions(cues, W, H, base, o, offset)
    for t in texts or []:
        if t.get("start") is not None and t.get("end") is not None:     # 'at the end' ones are resolved first
            ev += _text_block(t, W, H, base, o)
    return head + "\n".join(ev) + "\n"


def _block_y(where: str, H: int, block_h: float, captions: bool) -> float:
    """The top of a block of height block_h."""
    if where == "top":
        return H * 0.09
    if where == "middle":
        return H * (0.50 if captions else 0.40) - block_h / 2
    return H * 0.80 - block_h


def _captions(cues: list[dict], W: int, H: int, base: int, o: dict, offset: float) -> list[str]:
    st = STYLES[o["style"]]
    key = st["font"]
    fam = FONTS[key][0]
    accent = COLORS[o["color"]][1]
    size0 = base * st["size"] * SIZES[o["size"]][1]
    maxw = W * 0.84
    out = []
    for cue in cues:
        words = [w for w in cue["words"] if str(w.get("w") or "").strip()]
        if not words:
            continue
        shown = [clean_text(w["w"], 60) for w in words]
        shown = [x.upper() if st["upper"] else x for x in shown]
        lines, size = fit_lines(" ".join(shown), key, size0, maxw, max_lines=2 if st["mode"] != "plain" else 3)
        # which words are on which line (the wrap works on the same words, so they map in order)
        per_line, i = [], 0
        for ln in lines:
            n = len(ln.split())
            per_line.append(list(range(i, i + n)))
            i += n
        line_h = size
        block_h = line_h * len(lines)
        top = _block_y(o["position"], H, block_h, captions=True)
        s0, e0 = cue["s"] + offset, cue["e"] + offset
        bord = max(1.0, size * st.get("outline", 0))
        shad = max(0.0, size * st.get("shadow", 0))
        common = (f"\\an8\\pos({W / 2:.0f},{top:.0f})\\fn{fam}\\fs{size:.0f}\\bord{bord:.1f}\\shad{shad:.1f}"
                  f"\\1c&HFFFFFF&\\3c&H000000&\\4c&H000000&\\4a&H{'60' if st['mode'] == 'plain' else '30'}&")
        if st.get("box"):              # one rounded dark box behind exactly these lines (layer 0), the words on layer 1
            pad_x, pad_y = size * 0.38, size * 0.16
            lw = max(text_width(ln, key, size) for ln in lines)
            bx, by = W / 2 - lw / 2 - pad_x, top - pad_y
            out.append(f"Dialogue: 0,{_t(s0)},{_t(e0)},Base,,0,0,0,,{{\\an7\\pos({bx:.0f},{by:.0f})\\p1\\bord0\\shad0"
                       f"\\1c&H000000&\\1a&H40&\\fad(80,0)}}{_rounded(lw + 2 * pad_x, block_h + 2 * pad_y, size * 0.28)}{{\\p0}}")
            common = common.replace(f"\\bord{bord:.1f}\\shad{shad:.1f}", "\\bord0\\shad0")
        if st["mode"] == "karaoke":        # one line of the whole cue: words fill with the color as they are said
            parts, t = [], cue["s"]
            for li, idx in enumerate(per_line):
                for j in idx:
                    w = words[j]
                    gap = max(0.0, w["s"] - t)
                    if gap > 0.005:
                        parts.append("{\\k%d}" % round(gap * 100))
                    parts.append("{\\k%d}%s" % (max(1, round((w["e"] - max(w["s"], t)) * 100)), shown[j]))
                    parts.append(" " if j != idx[-1] else "")
                    t = max(t, w["e"])
                if li < len(per_line) - 1:
                    parts.append("\\N")
            out.append(f"Dialogue: 1,{_t(s0)},{_t(e0)},Base,,0,0,0,,{{{common}\\1c{tag_color(accent)}"
                       f"\\2c&HFFFFFF&\\fad(80,0)}}{''.join(parts)}")
            continue
        if st["mode"] == "plain":
            body = "\\N".join(lines)
            out.append(f"Dialogue: 1,{_t(s0)},{_t(e0)},Base,,0,0,0,,{{{common}\\fad(120,80)}}{body}")
            continue
        # "word": the cue shown once per word, that word in the color (and popping a little in 'pop')
        marks = [cue["s"]] + [w["s"] for w in words[1:]] + [cue["e"]]
        for j in range(len(words)):
            a, b = max(marks[j], cue["s"]), max(marks[j + 1], marks[j] + 0.01)
            pieces = []
            for li, idx in enumerate(per_line):
                row = []
                for k in idx:
                    if k == j:
                        pop = ("\\fscx112\\fscy112\\t(0,120,\\fscx104\\fscy104)" if o["style"] == "pop" else "")
                        row.append(f"{{\\1c{tag_color(accent)}{pop}}}{shown[k]}{{\\1c&HFFFFFF&\\fscx100\\fscy100}}")
                    else:
                        row.append(shown[k])
                pieces.append(" ".join(row))
            fade = "\\fad(80,0)" if j == 0 else ""
            out.append(f"Dialogue: 1,{_t(a + offset)},{_t(b + offset)},Base,,0,0,0,,{{{common}{fade}}}" + "\\N".join(pieces))
    return out


def _text_block(t: dict, W: int, H: int, base: int, o: dict) -> list[str]:
    look = t.get("look") if t.get("look") in LOOKS else "banner"
    key = "black" if look in ("banner", "bold") else "extrabold"
    size0 = base * {"banner": 0.062, "bold": 0.082, "box": 0.056}[look] * SIZES[o["size"]][1]
    lines, size = fit_lines(t["text"], key, size0, W * (0.80 if look != "bold" else 0.86), max_lines=3)
    line_h = size * (1.08 if look != "bold" else 1.0)
    block_h = line_h * len(lines)
    top = _block_y(t.get("where") or "top", H, block_h, captions=False)
    s, e = float(t["start"]), float(t["end"])
    accent = COLORS[o["color"]][1]
    fam = FONTS[key][0]
    anim = "\\fad(120,150)\\fscx86\\fscy86\\t(0,160,\\fscx100\\fscy100)"
    out = []
    if look in ("banner", "box"):
        pad_x, pad_y = size * 0.45, size * 0.22
        fill, alpha = (tag_color(accent), "&H00&") if look == "banner" else ("&H000000&", "&H38&")
        lw = max(text_width(ln, key, size) for ln in lines)     # one box for the whole block
        bx, by = W / 2 - lw / 2 - pad_x, top - pad_y
        out.append(f"Dialogue: 2,{_t(s)},{_t(e)},Base,,0,0,0,,{{\\an7\\pos({bx:.0f},{by:.0f})\\p1\\bord0\\shad0"
                   f"\\1c{fill}\\1a{alpha}\\fad(120,150)}}{_rounded(lw + 2 * pad_x, block_h + 2 * pad_y, size * 0.3)}{{\\p0}}")
        ink = "&H101010&" if look == "banner" else "&HFFFFFF&"     # dark on the colored stripe, white on the dark box
        anim = "\\fad(120,150)"           # a box and its words appear together (a scaled word would leave its box)
        style = f"\\bord0\\shad0\\1c{ink}"
    else:
        style = f"\\bord{size * 0.11:.1f}\\shad{size * 0.05:.1f}\\1c&HFFFFFF&\\3c&H000000&\\4c&H000000&\\4a&H30&"
    for li, ln in enumerate(lines):          # one line per event: each sits exactly on its own box
        out.append(f"Dialogue: 3,{_t(s)},{_t(e)},Base,,0,0,0,,{{\\an8\\pos({W / 2:.0f},{top + li * line_h:.0f})"
                   f"\\fn{fam}\\fs{size:.0f}{style}{anim}}}{ln}")
    return out
