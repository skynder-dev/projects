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
            "mode": "word", "em": 0.064, "outline": 0.18, "shadow": 0.07},
    "box": {"label": "On a dark box, the word being said in color", "font": "extrabold", "upper": False, "words": 4,
            "mode": "word", "em": 0.056, "box": True},
    "classic": {"label": "Classic: white with an outline, the words said turn to the color", "font": "extrabold",
                "upper": False, "words": 4, "mode": "karaoke", "em": 0.06, "outline": 0.13, "shadow": 0.05},
    "minimal": {"label": "Calm: white with a soft shadow, no highlight (business)", "font": "semibold", "upper": False,
                "words": 6, "mode": "plain", "em": 0.05, "outline": 0.05, "shadow": 0.1},
}
DEFAULT_STYLE, DEFAULT_COLOR, DEFAULT_SIZE = "pop", "yellow", "medium"
LOOKS = {"banner": "On a colored stripe", "bold": "Big white letters", "box": "On a dark box"}
ANIMS = {"pop": "Pops in", "slide": "Slides up", "fade": "Fades in", "type": "Typed letter by letter"}
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
def metrics(key: str) -> dict:
    """The font's vertical measures as parts of the renderer's font size. libass makes the size = usWinAscent +
    usWinDescent of the OS/2 table (for Montserrat 1109 + 453 = 1562 units, the em is 1000): measured against its
    rendering, not Pillow's ascent (which would make every box 28% too wide)."""
    import struct
    data = (FONT_DIR / FONTS[key][1]).read_bytes()
    n = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for i in range(n):
        tag, _cs, off, ln = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
        tables[tag] = off
    head, os2 = tables[b"head"], tables[b"OS/2"]
    upem = struct.unpack(">H", data[head + 18:head + 20])[0]
    version = struct.unpack(">H", data[os2:os2 + 2])[0]
    wa, wd = struct.unpack(">HH", data[os2 + 74:os2 + 78])
    cap = struct.unpack(">h", data[os2 + 88:os2 + 90])[0] if version >= 2 else int(upem * 0.7)
    tot = float(max(1, wa + wd))
    return {"em": upem / tot, "asc": wa / tot, "cap": cap / tot}


def text_width(text: str, key: str, size: float) -> float:
    """The width the renderer gives `text` at font size `size` (Pillow at the same em, 4x for precision)."""
    if not text:
        return 0.0
    return float(_pil_font(key, max(4, int(round(size * metrics(key)["em"] * 4)))).getlength(text)) / 4.0


def _ass_size(key: str, em_px: float) -> float:
    """The renderer's font size that gives letters of this em (in pixels)."""
    return em_px / metrics(key)["em"]


class _Block:
    """Lines of one size laid out top-down: where each line's event goes, and the visible height (cap top of the
    first line to the baseline of the last)."""

    def __init__(self, lines: list[str], key: str, size: float, pitch_em: float = 1.28):
        m = metrics(key)
        self.lines, self.key, self.size = lines, key, size
        self.pitch = pitch_em * m["em"] * size
        self.over = (m["asc"] - m["cap"]) * size                   # from the event's y down to the capitals' top
        self.vis_h = (len(lines) - 1) * self.pitch + m["cap"] * size
        self.em = m["em"] * size

    def line_y(self, vis_top: float, i: int) -> float:
        return vis_top - self.over + i * self.pitch

    def width(self) -> float:
        return max(text_width(x, self.key, self.size) for x in self.lines)


def _wrap(paras: list[list[str]], key: str, s: float, maxw: float) -> list[str]:
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
    return lines


def fit_lines(text: str, key: str, size: float, maxw: float, max_lines: int = 3) -> tuple[list[str], float]:
    """Wrap at `size`, smaller (down to 55%) while a word is wider than the line or there are too many lines; then
    the lines are evened out (the narrowest width that keeps their number), so no single word hangs on a line."""
    paras = [p.split() for p in text.split("\n") if p.strip()]
    s = size
    while True:
        lines = _wrap(paras, key, s, maxw)
        widest = max((text_width(x, key, s) for x in lines), default=0)
        if (widest <= maxw and len(lines) <= max_lines) or s <= size * 0.55:
            break
        s *= 0.92
    if len(lines) > len(paras):              # balance: the narrowest line width that still gives as many lines
        lo = max(text_width(w, key, s) for p in paras for w in p)
        hi = max(widest, lo)
        for _ in range(14):
            mid = (lo + hi) / 2
            if len(_wrap(paras, key, s, mid)) <= len(lines):
                hi = mid
            else:
                lo = mid
        lines = _wrap(paras, key, s, hi)
    return lines, s


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
    ok = lambda v, d: isinstance(v, str) and v in d          # anything else (a list sent by hand...) = the default
    return {"style": style if ok(style, STYLES) else DEFAULT_STYLE, "color": color if ok(color, COLORS) else DEFAULT_COLOR,
            "size": size if ok(size, SIZES) else DEFAULT_SIZE, "position": position if ok(position, POSITIONS) else "bottom"}


def _secs(v, what: str) -> float | None:
    s = str(v if v is not None else "").strip().replace(",", ".")
    if not s:
        return None
    m = re.fullmatch(r"(?:(\d{1,4}):)?(\d{1,6}(?:\.\d{1,3})?)", s)
    if not m:
        raise TextError(f"{what}: write seconds, for example 2.5 or 0:12.")
    t = int(m.group(1) or 0) * 60 + float(m.group(2))
    if not 0 <= t <= 36000:                      # at most 10 hours (a typo of many digits is not a time)
        raise TextError(f"{what}: write seconds, for example 2.5 or 0:12.")
    return t


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
                "anim": r.get("anim") if r.get("anim") in ANIMS else "pop",
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
    cols = [f.getlist(k) for k in ("t_text", "t_start", "t_end", "t_where", "t_look", "t_anim")]
    n = max((len(c) for c in cols), default=0)
    get = lambda c, i: c[i] if i < len(c) else ""
    return [{"text": get(cols[0], i), "start": get(cols[1], i), "end": get(cols[2], i), "where": get(cols[3], i),
             "anim": get(cols[5], i),
             "look": get(cols[4], i)} for i in range(n)]


def mark_emphasis(words: list[dict]) -> list[dict]:
    """*word* or *a few words* in a script or a caption line: those words stay in the color in the captions (the stars
    are not said and not shown). A lone '*' (5 * 3) marks nothing; a run left open ends with its sentence."""
    out, on = [], False
    for w in words:
        t = str(w.get("w") or "")
        if t.strip("*") == "":                         # a star alone: not a mark (and not a word)
            continue
        core = t.lstrip("«„“\"'([")
        starts = core.startswith("*")
        ends = t.rstrip(".,!?;:…»”\"')]").endswith("*")
        if starts:
            on = True
        em = on
        if ends:
            on = False
        clean = t.replace("*", "")
        if re.search(r"[.!?…]$", clean.rstrip("»”\"')]")):     # a sentence ends: so does an open mark
            on = False
        nw = {k: v for k, v in w.items() if k != "em"}
        out.append({**nw, "w": clean, **({"em": True} if em else {})})
    return out


def shown_words(words: list[dict]) -> str:
    """A caption line as the editor shows it: emphasized words between stars."""
    return " ".join(f"*{w['w']}*" if w.get("em") else str(w["w"]) for w in words)


def retime(cue: dict, text: str) -> dict | None:
    """A caption whose words were edited: the same time span, the new words share it by their length (*stars* mark
    the words shown in the color)."""
    words = clean_text(text, 200).split()
    if not words:
        return None
    old = cue["words"]
    if shown_words(old) == " ".join(words):
        return cue
    if len(words) == len(old):
        return {**cue, "words": mark_emphasis([{**{k: v for k, v in o.items() if k != "em"}, "w": w} for o, w in zip(old, words)])}
    s, e = old[0]["s"], old[-1]["e"]
    total = sum(len(w) + 1 for w in words)
    out, t = [], s
    for w in words:
        d = (e - s) * (len(w) + 1) / total
        out.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
        t += d
    out = mark_emphasis(out)
    return {**cue, "words": out} if out else None


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
    """One ASS document: the captions (cues of timed words) in the chosen style, and the text blocks - a text in the
    captions' place is moved next to them, never over them."""
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
    zone = None
    if cues:
        st = STYLES[o["style"]]
        em = base * st["em"] * SIZES[o["size"]][1]
        two = _Block(["x", "x"], st["font"], _ass_size(st["font"], em))
        zone = (o["position"], two.vis_h + 2 * 0.4 * em)          # the most the captions take (two lines and a box)
        ev += _captions(cues, W, H, base, o, offset)
    for t in texts or []:
        if t.get("start") is not None and t.get("end") is not None:     # 'at the end' ones are resolved first
            ev += _text_block(t, W, H, base, o, zone)
    return head + "\n".join(ev) + "\n"


def tall(W: int, H: int) -> bool:
    """A vertical video for Reels / TikTok / Shorts (their buttons sit on the right, their text at the bottom)."""
    return H > W * 1.3


def safe_boxes(W: int, H: int) -> list[tuple[int, int, int, int]]:
    """Where Reels, TikTok and Shorts put their own things on a tall video (x, y, w, h; roughly the union of the
    three): the buttons on the right, the name and text at the bottom, the bar at the top."""
    if not tall(W, H):
        return []
    return [(int(W * 0.86), int(H * 0.40), W - int(W * 0.86), int(H * 0.48)), (0, int(H * 0.82), W, H - int(H * 0.82)),
            (0, 0, W, int(H * 0.07))]


def _vis_top(where: str, W: int, H: int, vis_h: float, captions: bool, zone: tuple | None = None) -> float:
    """The top of the visible text of a block: captions at the bottom (a fifth above the edge, clear of the
    platforms' buttons), in the middle or at the top; a text block in the captions' place goes next to them."""
    gap = H * 0.025
    low = H * (0.76 if tall(W, H) else 0.80)     # a tall video: above the platforms' name, text and buttons
    top0 = H * (0.12 if tall(W, H) else 0.08)
    if captions:
        return {"top": top0 + H * 0.02, "middle": H * 0.50 - vis_h / 2}.get(where, low - vis_h)
    cz = zone[0] if zone else None
    if where == "top":
        return top0 + ((zone[1] + gap + H * 0.02) if cz == "top" else 0)
    if where == "middle":
        return (H * 0.50 - zone[1] / 2 - gap - vis_h) if cz == "middle" else H * 0.40 - vis_h / 2
    return (low - zone[1] - gap - vis_h) if cz == "bottom" else low - vis_h


def _captions(cues: list[dict], W: int, H: int, base: int, o: dict, offset: float) -> list[str]:
    st = STYLES[o["style"]]
    key = st["font"]
    fam = FONTS[key][0]
    accent = COLORS[o["color"]][1]
    size0 = _ass_size(key, base * st["em"] * SIZES[o["size"]][1])
    maxw = W * (0.70 if tall(W, H) else 0.86)          # a tall video: clear of the buttons on the right (0.86 W on)
    if st.get("box"):                                  # the box's padding is inside that width too
        maxw -= 2 * 0.55 * base * st["em"] * SIZES[o["size"]][1]
    out = []
    for cue in cues:
        pairs = []                           # each word as one token the wrap cannot split (a no-break space, ...)
        for w in cue["words"]:
            sh = "".join(clean_text(str(w.get("w") or "").replace("*", ""), 60).split())
            if sh:
                pairs.append((w, sh.upper() if st["upper"] else sh))
        if not pairs:
            continue
        words, shown = [p[0] for p in pairs], [p[1] for p in pairs]
        lines, size = fit_lines(" ".join(shown), key, size0, maxw, max_lines=2 if st["mode"] != "plain" else 3)
        per_line, i = [], 0                  # which words are on which line (the wrap keeps the tokens in order)
        for ln in lines:
            n = len(ln.split())
            per_line.append(list(range(i, i + n)))
            i += n
        blk = _Block(lines, key, size)
        vis_top = _vis_top(o["position"], W, H, blk.vis_h, captions=True)
        s0, e0 = cue["s"] + offset, cue["e"] + offset
        bord = max(1.0, blk.em * st.get("outline", 0))
        shad = max(0.0, blk.em * st.get("shadow", 0))
        look = (f"\\fn{fam}\\fs{size:.0f}\\bord{bord:.1f}\\shad{shad:.1f}\\1c&HFFFFFF&\\3c&H000000&\\4c&H000000&"
                f"\\4a&H{'60' if st['mode'] == 'plain' else '30'}&")
        if st.get("box"):              # one rounded dark box behind exactly these lines (layer 0), the words on layer 1
            pad_x, pad_y = blk.em * 0.55, blk.em * 0.42
            lw = blk.width()
            out.append(f"Dialogue: 0,{_t(s0)},{_t(e0)},Base,,0,0,0,,{{\\an7\\pos({W / 2 - lw / 2 - pad_x:.0f},"
                       f"{vis_top - pad_y:.0f})\\p1\\bord0\\shad0\\1c&H000000&\\1a&H40&\\fad(80,0)}}"
                       f"{_rounded(lw + 2 * pad_x, blk.vis_h + 2 * pad_y, blk.em * 0.4)}{{\\p0}}")
            look = look.replace(f"\\bord{bord:.1f}\\shad{shad:.1f}", "\\bord0\\shad0")
        at = lambda li: f"\\an8\\pos({W / 2:.0f},{blk.line_y(vis_top, li):.0f})"
        if st["mode"] == "karaoke":        # each line: its words fill with the color as they are said
            for li, idx in enumerate(per_line):
                parts, t = [], cue["s"]
                for j in idx:
                    w = words[j]
                    gap = max(0.0, w["s"] - t)
                    if gap > 0.005:
                        parts.append("{\\k%d}" % round(gap * 100))
                    em_ = "{\\2c%s}" % tag_color(accent) if w.get("em") else ""    # emphasized: in the color before too
                    parts.append("{\\k%d}%s%s%s" % (max(1, round((w["e"] - max(w["s"], t)) * 100)), em_, shown[j],
                                                      "{\\2c&HFFFFFF&}" if em_ else ""))
                    parts.append(" " if j != idx[-1] else "")
                    t = max(t, w["e"])
                out.append(f"Dialogue: 1,{_t(s0)},{_t(e0)},Base,,0,0,0,,{{{at(li)}{look}\\1c{tag_color(accent)}"
                           f"\\2c&HFFFFFF&\\fad(80,0)}}{''.join(parts)}")
            continue
        if st["mode"] == "plain":
            for li, idx in enumerate(per_line):
                ln = " ".join(f"{{\\1c{tag_color(accent)}}}{shown[k]}{{\\1c&HFFFFFF&}}" if words[k].get("em") else shown[k]
                              for k in idx)
                out.append(f"Dialogue: 1,{_t(s0)},{_t(e0)},Base,,0,0,0,,{{{at(li)}{look}\\fad(120,80)}}{ln}")
            continue
        # "word": the cue shown once per word, that word in the color (and popping a little in 'pop')
        marks = [cue["s"]] + [w["s"] for w in words[1:]] + [cue["e"]]
        for j in range(len(words)):
            a, b = max(marks[j], cue["s"]), max(marks[j + 1], marks[j] + 0.01)
            fade = "\\fad(80,0)" if j == 0 else ""
            for li, idx in enumerate(per_line):
                row = []
                for k in idx:
                    if k == j:
                        pop = ("\\fscx112\\fscy112\\t(0,120,\\fscx104\\fscy104)" if o["style"] == "pop" else "")
                        row.append(f"{{\\1c{tag_color(accent)}{pop}}}{shown[k]}{{\\1c&HFFFFFF&\\fscx100\\fscy100}}")
                    elif words[k].get("em"):          # emphasized: in the color all the time
                        row.append(f"{{\\1c{tag_color(accent)}}}{shown[k]}{{\\1c&HFFFFFF&}}")
                    else:
                        row.append(shown[k])
                out.append(f"Dialogue: 1,{_t(a + offset)},{_t(b + offset)},Base,,0,0,0,,{{{at(li)}{look}{fade}}}"
                           + " ".join(row))
    return out


def _text_block(t: dict, W: int, H: int, base: int, o: dict, zone: tuple | None = None) -> list[str]:
    look = t.get("look") if t.get("look") in LOOKS else "banner"
    key = "black" if look in ("banner", "bold") else "extrabold"
    em0 = base * {"banner": 0.054, "bold": 0.07, "box": 0.05}[look] * SIZES[o["size"]][1]
    pad_x_em, pad_y_em = 0.6, 0.48
    side = W * (0.70 if tall(W, H) and t.get("where") in ("middle", "bottom") else 0.88)   # the buttons' height
    maxw = side - (2 * pad_x_em * em0 if look != "bold" else 0)
    lines, size = fit_lines(t["text"], key, _ass_size(key, em0), maxw, max_lines=3)
    blk = _Block(lines, key, size)
    vis_top = _vis_top(t.get("where") or "top", W, H, blk.vis_h + (2 * pad_y_em * blk.em if look != "bold" else 0),
                       captions=False, zone=zone) + (pad_y_em * blk.em if look != "bold" else 0)
    s, e = float(t["start"]), float(t["end"])
    accent = COLORS[o["color"]][1]
    fam = FONTS[key][0]
    kind = t.get("anim") if t.get("anim") in ANIMS else "pop"
    rise = blk.em * 0.9
    move = lambda x, y: (f"\\move({x:.0f},{y + rise:.0f},{x:.0f},{y:.0f},0,260)" if kind == "slide" else f"\\pos({x:.0f},{y:.0f})")
    fade = "\\fad(260,180)" if kind in ("fade", "slide") else "\\fad(120,150)"
    anim = fade + ("\\fscx86\\fscy86\\t(0,160,\\fscx100\\fscy100)" if kind == "pop" else "")
    out = []
    if look in ("banner", "box"):
        pad_x, pad_y = blk.em * pad_x_em, blk.em * pad_y_em
        fill, alpha = (tag_color(accent), "&H00&") if look == "banner" else ("&H000000&", "&H38&")
        lw = blk.width()                     # one box for the whole block
        out.append(f"Dialogue: 2,{_t(s)},{_t(e)},Base,,0,0,0,,{{\\an7{move(W / 2 - lw / 2 - pad_x, vis_top - pad_y)}"
                   f"\\p1\\bord0\\shad0\\1c{fill}\\1a{alpha}{fade}}}"
                   f"{_rounded(lw + 2 * pad_x, blk.vis_h + 2 * pad_y, blk.em * 0.45)}{{\\p0}}")
        ink = "&H101010&" if look == "banner" else "&HFFFFFF&"     # dark on the colored stripe, white on the dark box
        anim = fade                       # a box and its words appear together (a scaled word would leave its box)
        style = f"\\bord0\\shad0\\1c{ink}"
    else:
        style = (f"\\bord{blk.em * 0.17:.1f}\\shad{blk.em * 0.07:.1f}\\1c&HFFFFFF&\\3c&H000000&\\4c&H000000&"
                 f"\\4a&H30&")
    total = sum(len(x) for x in lines)
    per = min(0.06, min(1.0, 0.6 * (e - s)) / max(1, total))   # typing: done within a second and while it is shown
    sh_a = "&H30&" if look == "bold" else "&H00&"
    done = 0
    for li, ln in enumerate(lines):          # one line per event: each sits exactly where its box was measured
        body = ln
        if kind == "type":                   # each letter appears in turn (invisible until its moment: no re-wrap)
            body = "".join("{\\1a&HFF&\\3a&HFF&\\4a&HFF&\\t(%d,%d,\\1a&H00&\\3a&H00&\\4a%s)}%s"
                           % (int(1000 * per * (done + k)) + 120, int(1000 * per * (done + k)) + 121, sh_a, ch)
                           for k, ch in enumerate(ln))
            done += len(ln)
        out.append(f"Dialogue: 3,{_t(s)},{_t(e)},Base,,0,0,0,,{{\\an8{move(W / 2, blk.line_y(vis_top, li))}"
                   f"\\fn{fam}\\fs{size:.0f}{style}{anim if kind != 'type' else fade}}}{body}")
    return out
