"""A story film (Cartoon Studio, "A film from a document"): a film's treatment turned into its pictures one after
another - each drawn by the picture add-on with the story's people drawn once, so they look the same in every scene -
and what the narrator says over them. The camera moves in each picture in depth (art.parallax), the place is heard
(ambient.py), slow music under it. Not an animation: pictures, in depth.

The text (the writer's answer, and what the owner reads and changes before the film is made):
    Title: Promise Keeper
    Format: horizontal
    Story: yes
    Narrator: Narrator (man, narrator)
    Tom (boy, the hero) looks: a quiet 9-year-old boy with messy brown hair, a faded blue sweater and grey shorts
    == Picture: <what one still picture shows> | with: Tom, Dad | sound: birds, wind | word: KEEP | seconds: 12 | move: push
    Narrator: <what is said over it>
Descriptions and looks are in English (the picture model reads English); what is said is in the film's language.
"""
from __future__ import annotations

import re
import zlib

SECTION = re.compile(r"(?i)^==\s*(?:picture|scene|кадр|сцена)\s*:\s*(.*)$")
FEMALE = {"woman", "girl", "mother", "mom", "grandmother", "female", "lady", "женщина", "девочка", "мама", "бабушка"}
WORD_COLORS = {"blue": "#8cc4ff", "grey": "#bbbbbb", "gray": "#bbbbbb", "gold": "#ffd36b", "red": "#ff8a7a"}


def is_story(text: str) -> bool:
    return bool(re.search(r"(?im)^==\s*(?:picture|кадр)\s*:", str(text or ""))) or bool(
        re.search(r"(?im)^story\s*:\s*(yes|on|да)\s*$", str(text or "")))


def _hex(s: str, n: int) -> str:
    return format(zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF, "08x")[:n]


def bg_name(title: str, draw: str, refs: list) -> str:
    """A scene's picture's name: the same words and people - the same picture (kept); other words - drawn anew."""
    return f"s_{_hex(title.strip().lower(), 6)}_{_hex(draw.strip() + '|' + ','.join(refs), 8)}"


def _key(name: str, taken: dict) -> str:
    from .textscript import _key as k
    return k(name, taken)


def _seconds(text: str) -> float:
    w = len(str(text or "").split())
    return max(5.0, min(30.0, w / 2.4 + 2.5)) if w else 6.0


def parse(text: str) -> dict:
    """The script (for film.check_script) from a story's text."""
    sc: dict = {"title": "Story", "language": "en", "format": "horizontal", "cast": {}, "scenes": [], "on_screen": False,
                "story": True}
    names: dict = {}
    pending: list = []

    def person(name: str, spec: str, looks: str = "", narrator: bool = False) -> str:
        low = name.strip().lower()
        if low in names:
            k = names[low]
            if looks:
                sc["cast"][k]["looks"] = looks.strip()[:300]
            return k
        k = _key(name, sc["cast"])
        words = set(re.findall(r"[^\W\d_]+", spec.lower()))
        role = ", ".join(x.strip() for x in spec.split(",")[1:] if x.strip())[:60]
        sc["cast"][k] = {"name": name.strip()[:30], "role": "narrator" if narrator else role, "female": bool(words & FEMALE),
                         **({"looks": looks.strip()[:300]} if looks.strip() else {}), "keep_look": True}
        names[low] = k
        return k

    for raw in str(text or "").replace("\r", "").split("\n"):
        ln = raw.strip()
        if not ln:
            continue
        m = SECTION.match(ln)
        if m:
            parts = [p.strip() for p in m.group(1).split("|")]
            scene: dict = {"draw": parts[0], "lines": [], "with_names": [], "sound": [], "visual": None, "min": 0.0}
            for p in parts[1:]:
                k, _, v = p.partition(":")
                k, v = k.strip().lower(), v.strip()
                if k in ("with", "people", "кто"):
                    scene["with_names"] = [x.strip() for x in re.split(r"[,;]| and ", v) if x.strip()]
                elif k in ("sound", "sounds", "звук"):
                    scene["sound"] = [x.strip().lower() for x in re.split(r"[,;]", v) if x.strip()]
                elif k in ("word", "words", "слово"):
                    col = "#ffffff"
                    cm = re.search(r"\(([a-z]+)\)\s*$", v)
                    if cm and cm.group(1) in WORD_COLORS:
                        col, v = WORD_COLORS[cm.group(1)], v[:cm.start()].strip()
                    if v:
                        scene["visual"] = {"kind": "word", "text": v.strip('"«»')[:60], "color": col}
                elif k in ("seconds", "secs", "секунд"):
                    try:
                        scene["min"] = max(3.0, min(30.0, float(v)))
                    except ValueError:
                        pass
                elif k in ("move", "camera"):
                    scene["move"] = v.lower()
            sc["scenes"].append(scene)
            continue
        hm = re.match(r"(?i)^(title|format|language|story|narrator)\s*:\s*(.*)$", ln)
        if hm and not sc["scenes"]:
            key, val = hm.group(1).lower(), hm.group(2).strip()
            if key == "title":
                sc["title"] = val[:120] or "Story"
            elif key == "format":
                sc["format"] = "vertical" if val.lower().startswith("vert") else "horizontal"
            elif key == "language":
                sc["language"] = val[:5].lower() or "en"
            elif key == "narrator":
                nm = re.match(r"^(.+?)\s*\(([^)]*)\)\s*$", val)
                sc["narrator"] = person(nm.group(1) if nm else (val or "Narrator"), nm.group(2) if nm else "man", narrator=True)
            continue
        cm = re.match(r"^([^:=(]{1,40}?)\s*\(([^)]*)\)\s*(?:looks\s*:\s*(.*))?$", ln)
        if cm and not sc["scenes"]:
            person(cm.group(1), cm.group(2), cm.group(3) or "")
            continue
        sm = re.match(r"^([^:]{1,40}?)\s*(?:\([^)]*\))?\s*:\s*(.+)$", ln)
        if sm and sc["scenes"]:
            who = names.get(sm.group(1).strip().lower())
            if who is None:
                who = sc.get("narrator") or person("Narrator", "man", narrator=True)
                if not sc.get("narrator"):
                    sc["narrator"] = who
            sc["scenes"][-1]["lines"].append({"who": who, "text": sm.group(2).strip()[:400]})
            continue
        pending.append(ln)
    if not sc.get("narrator"):
        sc["narrator"] = person("Narrator", "man", narrator=True)
    for s in sc["scenes"]:
        s["with"] = [names[n.lower()] for n in s.pop("with_names") if n.lower() in names][:4]
        refs = [sc["cast"][k].get("looks") or "" for k in s["with"]]
        s["bg"] = bg_name(sc["title"], s["draw"], refs)
        said = " ".join(x["text"] for x in s["lines"])
        s["min"] = s["min"] or _seconds(said)
        if s["visual"]:
            s["visual"]["from"] = round(min(2.0, s["min"] * 0.3), 1)
        s["sound"] = [x for x in s["sound"] if x]
        if not s["sound"]:
            s.pop("sound")
    return sc


def to_text(sc: dict) -> str:
    """A story's script back as its text (to read and change it the same way)."""
    cast = sc.get("cast") if isinstance(sc.get("cast"), dict) else {}
    nar = sc.get("narrator")
    out = [f"Title: {sc.get('title') or 'Story'}", f"Format: {sc.get('format') or 'horizontal'}"]
    if sc.get("language") and sc["language"] != "en":
        out.append(f"Language: {sc['language']}")
    out.append("Story: yes")
    for k, c in cast.items():
        g = "woman" if c.get("female") else "man"
        if k == nar:
            out.append(f"Narrator: {c.get('name') or 'Narrator'} ({g}, narrator)")
    for k, c in cast.items():
        if k != nar:
            role = f", {c['role']}" if c.get("role") and c.get("role") != "narrator" else ""
            g = "woman" if c.get("female") else "man"
            out.append(f"{c.get('name') or k} ({g}{role})"
                       + (f" looks: {c['looks']}" if c.get("looks") else ""))
    for s in sc.get("scenes") or []:
        parts = [f"== Picture: {s.get('draw') or ''}"]
        if s.get("with"):
            parts.append("with: " + ", ".join((cast.get(k) or {}).get("name") or k for k in s["with"]))
        if s.get("sound"):
            parts.append("sound: " + ", ".join(s["sound"]))
        v = s.get("visual") or {}
        if v.get("kind") == "word" and v.get("text"):
            col = next((n for n, h in WORD_COLORS.items() if h == v.get("color")), "")
            parts.append("word: " + v["text"] + (f" ({col})" if col else ""))
        if s.get("move"):
            parts.append("move: " + s["move"])
        out.append("")
        out.append(" | ".join(parts))
        for ln in s.get("lines") or []:
            out.append(f"{(cast.get(ln.get('who')) or {}).get('name') or 'Narrator'}: {ln.get('text') or ''}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------------------- the writer's part

SYSTEM = ("You are a storyboard artist for animated films. You turn a film's treatment into its storyboard: the pictures "
          "of the film one after another and what the narrator says over each. You answer with the storyboard only, in "
          "the fixed plain-text format, nothing before or after it, no markdown.")

FORMAT = """THE FORMAT (keep the English keywords exactly as written here):
Title: <the film's title>
Format: {fmt}
Story: yes
Narrator: <name> (woman or man, narrator)
<Name> (boy, girl, woman or man, <role>) looks: <age, face, hair, clothes - 12 to 25 English words, always the same>
   <- the 1 to 4 people seen most, one per line

== Picture: <ONE still picture in English: the place, the time of day and light, who does what, the camera (wide shot, close-up, from behind...)> | with: <the names of the people seen in it> | sound: <one or two of: wind, birds, stream, sea, rain, night, room, town, fire> | word: <a word or short phrase written big on the picture, only where the treatment has one>
Narrator: <one or two short sentences said over this picture>"""

RULES = """RULES:
- Follow the TREATMENT in its order, beat by beat. Do not invent new events, people or endings; do not leave out its key moments.
- {lo} to {hi} pictures. Every picture shows something new: another place, another moment or another camera.
- Each picture's description stands alone (the painter sees one at a time): name the place and the light again every time; use the people's names only in "with:".
- Describe only what can be drawn and is in the treatment's world: its time, its things (no phones or cars if it is set long ago).
- Nothing frightening for children (no ropes like nooses, no weapons pointed, no blood); no text or letters in the pictures except a "word:".
- "looks:" in English; the descriptions in English; what the narrator says in {lang}.
- The narrator tells it simply, about {words} words in all; a quiet picture may have no line at all.
- "word:" at most 5 times in the film, only for words the treatment itself shows on the screen."""


def prompt(job: dict) -> str:
    from .writer import LANGS
    lang = LANGS.get(job.get("lang") or "en", "English")
    secs = int(job.get("secs") or 300)
    n = max(10, min(32, round(secs / 12)))
    return "\n\n".join([
        "Make the storyboard of the film described in the TREATMENT below.",
        f"TREATMENT:\n\"\"\"\n{str(job.get('source') or '').strip()[:MAX_SOURCE]}\n\"\"\"",
        FORMAT.format(fmt=job.get("format") or "horizontal"),
        RULES.format(lo=max(8, n - 4), hi=n + 4, lang=lang, words=int(secs * 1.6)),
        "Now write the whole storyboard."])


MAX_SOURCE = 9000


def judge(text: str, secs: int = 300) -> tuple[dict, str]:
    """What the program reads from a storyboard, and what is wrong with it ('' when it is fine)."""
    sc = parse(text)
    scenes = [s for s in sc["scenes"] if len(s.get("draw") or "") >= 15]
    people = [c for c in sc["cast"].values() if c.get("looks")]
    words = sum(len(ln["text"].split()) for s in scenes for ln in s["lines"])
    info = {"title": sc.get("title"), "scenes": len(scenes), "lines": sum(len(s["lines"]) for s in scenes), "words": words,
            "cast": len(people), "visuals": sum(1 for s in scenes if s.get("visual"))}
    if len(scenes) < 6:
        return info, f"it has only {len(scenes)} pictures (each starts with '== Picture:' and describes the picture)"
    if not people:
        return info, "no person has 'looks:' (how they look, in English) - the pictures need it to draw them the same"
    if sum(1 for s in scenes if s.get("with")) < len(scenes) // 3 and len(people) > 0:
        return info, "almost no picture says who is in it ('with:' and the names)"
    return info, ""
