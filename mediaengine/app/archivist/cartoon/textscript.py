"""A cartoon's script in plain text - what a person writes in a minute (or a small language model writes well):

    Title: How a City Loses Millions
    Format: vertical
    Narrator: Kate (woman, narrator)
    Mayor Grant (man, mayor)
    Rick Stone (man, contractor boss, sly)

    == City street | title: How a City Loses Millions / on a simple road contract
    Kate (wave, happy): A road full of holes. Fixing it should be simple, right?

    == Board | flow: City budget -> RoadCo $4.8M; RoadCo -> Cheap crew $1M; RoadCo -> Officials kickback
    Kate: The city pays RoadCo four point eight million.

A scene starts with "==", its background, and after "|" what is shown (title, road, contract, flow, bars, list, counter,
compare, bag, magnifier). Backgrounds: City street, Office, City hall, Road, Bank, Night, Board, Paper, Hospital,
School, Shop, Home (a block of flats), Building site. A line is "Name (gesture, feeling): words"; "Name [bubble]: words" shows it in a speech
bubble. A name not introduced becomes a new character. English or Russian words for backgrounds, gestures, feelings.
"""
from __future__ import annotations

import re

from . import bgs

BG_WORDS = {
    "city": "city", "street": "city", "city street": "city", "улица": "city", "город": "city",
    "office": "office", "офис": "office", "кабинет": "office",
    "city hall": "city_hall", "city_hall": "city_hall", "мэрия": "city_hall", "администрация": "city_hall",
    "road": "road", "дорога": "road", "bank": "bank", "банк": "bank",
    "night": "night", "night street": "night", "ночь": "night", "ночная улица": "night",
    "board": "board", "доска": "board", "схема": "board", "paper": "paper", "бумага": "paper", "тетрадь": "paper",
    # the hospital, the school, the shop and the block of flats; places a story names: the nearest background
    "hospital": "hospital", "clinic": "hospital", "больница": "hospital", "поликлиника": "hospital", "spital": "hospital",
    "clinică": "hospital", "school": "school", "classroom": "school", "школа": "school", "класс": "school",
    "școală": "school", "școala": "school", "scoala": "school", "shop": "shop", "store": "shop", "pharmacy": "shop",
    "supermarket": "shop", "магазин": "shop", "аптека": "shop", "magazin": "shop", "farmacie": "shop",
    "home": "home", "block of flats": "home", "house": "home", "apartment block": "home", "stairwell": "home",
    "дом": "home", "жилой дом": "home", "подъезд": "home", "двор": "home", "bloc": "home", "casă": "home",
    "building site": "site", "construction site": "site", "construction": "site", "builders": "site", "crane": "site",
    "стройка": "site", "стройплощадка": "site", "строительство": "site", "кран": "site", "șantier": "site",
    "șantierul": "site", "santier": "site", "construcție": "site", "constructie": "site",
    "flat": "office", "apartment": "office", "kitchen": "office", "factory": "office", "квартира": "office",
    "кухня": "office", "завод": "office", "birou": "office",
    "court": "city_hall", "ministry": "city_hall", "parliament": "city_hall", "council": "city_hall", "суд": "city_hall",
    "министерство": "city_hall", "primărie": "city_hall", "primăria": "city_hall", "primarie": "city_hall",
    "square": "city", "market": "city", "park": "city", "yard": "home", "площадь": "city", "рынок": "city",
    "stradă": "city", "strada": "city", "oraș": "city", "drum": "road", "bancă": "bank", "noapte": "night", "tablă": "board",
    "street at night": "night", "chart": "board", "charts": "board", "scheme": "board", "end": "board", "finale": "board",
    "lesson": "board", "конец": "board", "итог": "board", "финал": "board",
}
KIND_ALIASES = {                                           # the kinds of pictures written in Russian or Romanian
    "заголовок": "title", "название": "title", "titlu": "title", "поток": "flow", "денежный поток": "flow", "схема": "flow",
    "flux": "flow", "schemă": "flow", "schema": "flow", "договор": "contract", "контракт": "contract", "тендер": "tender",
    "конкурс": "tender", "licitație": "tender", "licitatie": "tender", "график": "bars", "диаграмма": "bars", "столбики": "bars",
    "столбцы": "bars", "grafic": "bars", "diagramă": "bars", "chart": "bars", "список": "list", "listă": "list", "lista": "list",
    "счётчик": "counter", "счетчик": "counter", "сумма": "counter", "contor": "counter", "sumă": "counter", "suma": "counter",
    "сравнение": "compare", "comparație": "compare", "comparatie": "compare", "мешок": "bag", "деньги": "bag", "sac": "bag",
    "лупа": "magnifier", "проверка": "magnifier", "lupă": "magnifier", "lupa": "magnifier", "дорога": "road", "drum": "road",
    "pie": "percent", "share": "percent", "процент": "percent", "доля": "percent", "procent": "percent",
    "хронология": "timeline", "даты": "timeline", "cronologie": "timeline", "dates": "timeline",
}
VISUAL_KINDS = ("title", "flow", "contract", "tender", "bars", "chart", "list", "counter", "compare", "bag", "magnifier", "road",
                "percent", "timeline",
                "заголовок", "схема", "договор", "контракт", "тендер", "график", "диаграмма", "список", "счётчик", "счетчик",
                "сумма", "сравнение", "мешок", "лупа", "проверка", "дорога") + tuple(KIND_ALIASES)
POSE_WORDS = {
    "talk": "talk", "говорит": "talk", "explain": "explain", "объясняет": "explain", "point": "point", "показывает": "point",
    "point up": "point_up", "point_up": "point_up", "палец вверх": "point_up", "shrug": "shrug", "пожимает плечами": "shrug",
    "cross": "cross", "arms crossed": "cross", "руки скрещены": "cross", "think": "think", "думает": "think",
    "wave": "wave", "машет": "wave", "hands up": "hands_up", "руки вверх": "hands_up", "count": "count",
    "rubs hands": "count", "потирает руки": "count", "present": "present", "представляет": "present",
    "facepalm": "facepalm", "рука у лица": "facepalm", "fist": "fist", "кулак": "fist", "sneaky": "sneaky", "крадётся": "sneaky",
    "idle": "idle", "стоит": "idle", "считает": "count", "выступает": "present", "указывает": "point",
    "разводит руками": "shrug", "шепчет": "sneaky", "размышляет": "think", "приветствует": "wave", "приветствие": "wave",
    "указывает вверх": "point_up", "поднимает палец": "point_up", "выговаривает": "talk",
    "talking": "talk", "explaining": "explain", "pointing": "point", "points": "point", "pointing up": "point_up",
    "shrugging": "shrug", "shrugs": "shrug", "crossed arms": "cross", "arms folded": "cross", "thinking": "think",
    "thinks": "think", "waving": "wave", "waves": "wave", "rubbing hands": "count", "rubs his hands": "count",
    "counting": "count", "counts money": "count", "rub hands": "count", "rubs her hands": "count", "presenting": "present", "presents": "present", "hand to face": "facepalm",
    "sneaking": "sneaky", "whispers": "sneaky", "whispering": "sneaky", "standing": "idle", "shows": "point",
    "raises hands": "hands_up", "hands raised": "hands_up",
    # Romanian (a model told to keep the English words sometimes translates them all the same)
    "vorbește": "talk", "explică": "explain", "arată": "point", "își arată": "point", "se arată": "point",
    "arată în sus": "point_up", "își arată sus": "point_up", "ridică din umeri": "shrug", "se întinde": "shrug",
    "brațe încrucișate": "cross", "gândește": "think", "se gândește": "think", "salută": "wave", "face cu mâna": "wave",
    "mâinile sus": "hands_up", "numără": "count", "își freacă mâinile": "count", "prezintă": "present",
    "face palme": "facepalm", "mâna la față": "facepalm", "pumn": "fist", "se strecoară": "sneaky", "stă": "idle",
}
EMO_WORDS = {
    "neutral": "neutral", "calm": "neutral", "спокойно": "neutral", "happy": "happy", "радостно": "happy", "весело": "happy",
    "angry": "angry", "сердито": "angry", "зло": "angry", "sad": "sad", "грустно": "sad", "surprised": "surprised",
    "удивлённо": "surprised", "удивленно": "surprised", "sly": "sly", "хитро": "sly", "worried": "worried",
    "тревожно": "worried", "испуганно": "worried",
    "smile": "happy", "smiling": "happy", "smiles": "happy", "excited": "happy", "proud": "happy", "cheerful": "happy",
    "clear": "neutral", "serious": "neutral", "confident": "neutral", "upset": "sad", "disappointed": "sad",
    "furious": "angry", "annoyed": "angry", "shocked": "surprised", "amazed": "surprised", "nervous": "worried",
    "scared": "worried", "afraid": "worried", "anxious": "worried", "cunning": "sly", "smug": "sly", "greedy": "sly",
    "улыбается": "happy", "серьёзно": "neutral", "серьезно": "neutral", "возмущённо": "angry", "возмущенно": "angry",
    "шокирован": "surprised", "нервно": "worried", "хитрый": "sly", "счастливо": "happy", "счастлив": "happy",
    "с улыбкой": "happy", "улыбка": "happy", "смех": "happy", "смеётся": "happy", "злобно": "angry", "злой": "angry",
    "грустный": "sad", "печально": "sad", "испуган": "worried", "уверенно": "neutral", "строго": "neutral",
    "злится": "angry", "беспокоится": "worried", "смешно": "happy",
    "calmă": "neutral", "fericit": "happy", "fericită": "happy", "vesel": "happy", "veselă": "happy",
    "furios": "angry", "furioasă": "angry", "supărat": "angry", "supărată": "angry", "trist": "sad", "tristă": "sad",
    "surprins": "surprised", "surprinsă": "surprised", "viclean": "sly", "vicleană": "sly", "subtil": "sly",
    "îngrijorat": "worried", "îngrijorată": "worried", "speriat": "worried", "speriată": "worried",
}
FEMALE = {"woman", "female", "she", "girl", "женщина", "девушка", "она", "femeie", "fată", "fata", "ea"}
MALE = {"man", "male", "he", "boy", "мужчина", "парень", "он", "bărbat", "barbat", "băiat", "baiat", "el"}
# a number: thousands in groups of three (4 800 000, 4,800,000) or plain digits, with a decimal part (4.8, 4,8)
NUM = re.compile(r"[-+]?(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:[.,]\d+)?")
NOT_SPEAKERS = {"note", "notes", "visual", "visuals", "scene", "image", "picture", "background", "title", "примечание",
                "сцена", "картинка", "фон", "notă", "nota", "imagine", "fundal"}
NARRATOR_WORDS = {"narrator", "the narrator", "рассказчик", "рассказчица", "ведущий", "ведущая", "narator", "naratoare",
                  "naratorul", "voice over", "voiceover", "закадровый голос"}
MONEY_TAIL = re.compile(r"\s+((?:[$€₽£]\s?)?\d[\d.,\s]*(?:\s?(?:млн|млрд|тыс|million|billion|mln|bn|[MKB]|lei|лей|руб|₽|€|\$)\.?)?"
                        r"|kickback|bribe|откат|взятка|mită|comision)\s*$", re.I)


RO_WORDS = {"este", "și", "si", "sunt", "pentru", "care", "dar", "nu", "mai", "din", "cu", "pe", "la", "un", "o", "ce",
            "lei", "primăria", "primaria", "bani", "drum", "firma", "firmă", "orașul", "orasul", "contractul", "plătit", "platit"}


def _key(name: str, taken: dict) -> str:
    a, b = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "abvgdeejziiklmnoprstufhccss_y_eua"
    base = re.sub(r"[^a-z0-9]", "", name.lower().translate(str.maketrans(a, b)))[:20] or "c"
    k, n = base, 2
    while k in taken:
        k, n = f"{base}{n}", n + 1
    return k


def _attr(a: str) -> tuple[str, str]:
    """(pose, emotion) a word in brackets means: the exact word, else its words one by one ("показывает рукой")."""
    if a in POSE_WORDS:
        return POSE_WORDS[a], ""
    if a in EMO_WORDS:
        return "", EMO_WORDS[a]
    for w in re.findall(r"[^\W\d_]+", a):
        if w in POSE_WORDS:
            return POSE_WORDS[w], ""
        if w in EMO_WORDS:
            return "", EMO_WORDS[w]
    return "", ""


def _to_float(t: str) -> float | None:
    t = t.replace(" ", "").replace("\u00a0", "")
    if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", t):
        t = t.replace(",", "")                             # 4,800,000 / 1,050.5
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return None


def _number(s: str, last: bool = False) -> float | None:
    """The first number in a text (the last one: last=True - "2023 1.2" is 1.2)."""
    ms = list(NUM.finditer(s or ""))
    return _to_float(ms[-1 if last else 0].group(0)) if ms else None


def _visual(spec: str, n_lines: int) -> dict | None:
    """What a scene shows, from "kind: details" after the "|" (the parts appear one per line, in order)."""
    if not spec:
        return None
    spec = re.sub(r"\s*(?:→|=>|—>|–>|->)\s*", " -> ", spec)        # every kind of arrow
    kind, _, rest = spec.partition(":")
    kind, rest = kind.strip().lower(), re.sub(r'["“”«»„]', "", rest).strip()
    kind = KIND_ALIASES.get(kind, kind)
    at = lambda k: min(k, max(0, n_lines - 1)) if n_lines else None       # noqa: E731
    if kind in ("title", "заголовок"):
        t, _, sub = rest.partition("/")
        return {"kind": "title", "title": t.strip(), "sub": sub.strip()}
    if kind in ("road", "дорога"):
        v = {"kind": "road", "holes_at": None}
        low = rest.lower()
        if any(w in low for w in ("repair", "patch", "ремонт", "заплат")):
            v.update(patch_at=at(0), truck=True)
        if any(w in low for w in ("holes back", "ямы вернулись", "again", "снова")):
            v.update(fresh=True, holes_at=at(1))
        return v
    if kind in ("contract", "tender", "договор", "контракт", "тендер"):
        parts = [p.strip() for p in rest.split(";") if p.strip()]
        title = (parts[0] if parts else ("TENDER" if kind in ("tender", "тендер") else "CONTRACT")).upper()[:24]
        v = {"kind": "contract", "title": title, "at": None if kind not in ("tender", "тендер") else at(0)}
        notes = []
        for p in parts[1:]:
            low = p.lower()
            if low.startswith(("price", "цена", "preț", "pret")):
                v.update(price=p.split(" ", 1)[1].strip() if " " in p else "", price_at=at(0))
            elif low.startswith(("stamp", "печать", "ștampilă", "stampila", "штамп")):
                v.update(stamp=(p.split(" ", 1)[1].strip() if " " in p else "APPROVED").upper()[:16], stamp_at=at(1))
            else:
                notes.append({"text": p.lstrip("-+ "), "ok": p.startswith("+"), "at": at(len(notes))})
        if notes:
            v["notes"] = notes[:4]
        return v
    if kind in ("flow", "схема"):
        nodes, edges, ids = [], [], {}
        icons = {"city": "city", "budget": "city", "город": "city", "бюджет": "city", "bank": "bank", "банк": "bank",
                 "official": "person", "чиновник": "person", "депутат": "person", "crew": "shovel", "бригада": "shovel",
                 "worker": "shovel", "company": "company", "компания": "company", "фирма": "company", "ооо": "company"}
        colors = ["#3f7fd6", "#7a3b3b", "#4caf6a", "#8a6a2e", "#6a4c8c"]

        def node(name: str, k: int) -> str:
            name = name.strip()
            if name not in ids:
                ids[name] = f"n{len(ids)}"
                icon = next((v_ for w, v_ in icons.items() if w in name.lower()), "company")
                nodes.append({"id": ids[name], "label": name[:24], "icon": icon, "color": colors[len(nodes) % len(colors)],
                              "at": None if not nodes else at(k)})
            return ids[name]
        for k, part in enumerate(p for p in rest.split(";") if "->" in p):
            a, _, b = part.partition("->")
            b = b.strip()
            label = ""
            m = MONEY_TAIL.search(b)
            if m and m.start() > 0:
                label, b = m.group(1).strip(), b[:m.start()].strip()
            edges.append({"from": node(a, k), "to": node(b, k), "label": label, "at": at(k),
                          **({"tag": "#e0533d"} if label.lower() in ("kickback", "откат", "bribe", "взятка") else {})})
        return {"kind": "flow", "nodes": nodes[:5], "edges": edges[:6]} if nodes else None
    if kind in ("bars", "chart", "график", "диаграмма"):
        unit = ""
        if rest and rest.split()[-1].isalpha() and len(rest.split()[-1]) <= 3:
            unit = rest.split()[-1]
            rest = rest[: -len(unit)].strip()
        values, labels = [], []
        for p in re.split(r"[;,](?!\d)", rest):            # "a 1.2, b 4.8" or "a 80 000; b 240 000"
            ms = list(NUM.finditer(p))
            v = _to_float(ms[-1].group(0)) if ms else None
            if v is None:
                continue
            values.append(v)
            tail = p[ms[-1].end():]
            suf = re.match(r"\s*(M|K|B|bn|mln|mn|млн|млрд|тыс|mil)\b\.?", tail)
            if suf and not unit:
                unit = suf.group(1)
            label = p[:ms[-1].start()] + (tail[suf.end():] if suf else tail)
            labels.append(re.sub(r"[$€₽£]", "", label).strip(" :-")[:20])
        title = ""
        if "/" in rest:
            title = rest.split("/", 1)[0].strip()
        return {"kind": "bars", "values": values[:5], "labels": labels[:5], "unit": unit, "at": at(0),
                "colors": ["#4caf6a", "#e0533d", "#f2c12e", "#3f7fd6", "#6a4c8c"], **({"title": title} if title else {})} if values else None
    if kind in ("list", "список"):
        parts = [p.strip() for p in rest.split(";") if p.strip()]
        if not parts:
            return None
        title, items = parts[0], parts[1:]
        return {"kind": "list", "title": title, "items": [{"text": it.lstrip("-+ "), "ok": it.startswith("+"), "at": at(k)}
                                                          for k, it in enumerate(items[:5])]}
    if kind in ("counter", "счётчик", "счетчик", "sum", "сумма"):
        v = _number(rest) or 0
        cur = "$" if "$" in rest else "€" if "€" in rest else "₽" if "₽" in rest else ""
        label = NUM.sub("", rest).replace("$", "").replace("€", "").replace("₽", "").strip()
        return {"kind": "counter", "from": 0, "to": v, "prefix": cur, "suffix": "" if cur else "", "label": label[:60], "at": at(0)}
    if kind in ("compare", "сравнение"):
        sides = []
        for k, p in enumerate(rest.split(" vs ")[:2] if " vs " in rest else rest.split(";")[:2]):
            words = p.strip().split(" ")
            price = next((w for w in words if re.search(r"\d", w)), "")
            sides.append({"label": " ".join(w for w in words if w != price)[:30], "price": price, "at": at(k)})
        return {"kind": "compare", "sides": sides}
    if kind in ("bag", "мешок", "деньги"):
        return {"kind": "bag", "text": rest[:60], "label": "$"}
    if kind == "percent":                                  # "30% kickback" / "kickback 30%" / "2/3 of the budget"
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", rest)
        frac = None if m else re.search(r"(\d+)\s*/\s*(\d+)", rest)
        if frac:
            m, v_ = frac, 100.0 * float(frac.group(1)) / max(1.0, float(frac.group(2)))
        elif m:
            v_ = _to_float(m.group(1)) or 0.0
        else:
            m = NUM.search(rest)
            if not m:
                return None
            v_ = _to_float(m.group(0)) or 0.0
        label = (rest[:m.start()] + " " + rest[m.end():]).strip(" -:%")
        return {"kind": "percent", "value": round(max(0.0, min(100.0, v_)), 1), "at": at(0), "label": re.sub(r"\s+", " ", label)[:50]}
    if kind == "timeline":                                 # "2021 contract; 2022 repair; 5 марта 2023: holes back"
        steps = []
        month = r"[^\W\d_]{3,12}\.?"
        for k, part in enumerate(p_.strip() for p_ in rest.split(";") if p_.strip()):
            m = (re.match(r"^(\d{1,2}\s+" + month + r"(?:\s+\d{4})?|" + month + r"\s+\d{4}|\d{1,4}(?:[./-]\d{1,4}){0,2})\s*[:\-–—]?\s+(.*)$", part)
                 or re.match(r"^(\S+)\s*[:\-–—]?\s+(.*)$", part))
            when, what = (m.group(1).rstrip(":-–— "), m.group(2)) if m else (part, "")
            bad = bool(re.search(r"(?i)\b(holes?|broken?|broke|again|kickbacks?|bribes?|stolen|fraud)\b|\b(ям|слом|откат|взятк|украл|снова)"
                                 r"|\b(gropi|mită|mita|furat|iar)\b", what))
            steps.append({"when": when[:16], "what": what[:40], "at": at(k), **({"bad": True} if bad else {})})
        return {"kind": "timeline", "steps": steps[:5]} if steps else None
    if kind in ("magnifier", "лупа", "проверка"):
        return {"kind": "magnifier", "title": (rest or "TENDER").upper()[:20]}
    return None


def parse(text: str) -> dict:
    """The script (a dict for film.check_script) from the plain text."""
    lines = [ln.rstrip() for ln in str(text or "").replace("\r", "").split("\n")]
    sc: dict = {"title": "Cartoon", "language": "en", "format": "vertical", "cast": {}, "scenes": []}
    names: dict = {}                                       # name (lower) -> key

    def add(name: str, attrs: list[str], narrator: bool = False) -> str:
        nm = name.strip()
        low = nm.lower()
        if low in names:
            return names[low]
        k = _key(nm, sc["cast"])
        spec: dict = {"name": nm[:30], "role": "narrator" if narrator else ""}
        roles = []
        for a in attrs:
            al = a.strip().lower()
            words = set(re.findall(r"[^\W\d_]+", al))
            if al in FEMALE or (words & FEMALE and not words & MALE and len(words) <= 3):
                spec["female"] = True                      # ("женщина-ведущая": a woman too)
                rest = " ".join(w for w in re.findall(r"[^\W\d_]+", al) if w not in FEMALE)
                if rest and al not in FEMALE:
                    roles.append(rest)
            elif al in MALE or (words & MALE and not words & FEMALE and len(words) <= 3):
                spec["female"] = False
                rest = " ".join(w for w in re.findall(r"[^\W\d_]+", al) if w not in MALE)
                if rest and al not in MALE:
                    roles.append(rest)
            elif al:
                roles.append(al)
        if roles:
            spec["role"] = ", ".join(roles)[:60]
        if narrator:
            spec["voice"] = {"kind": "host"}
        else:
            gender = "woman" if spec.get("female") else "man"
            spec["voice"] = {"kind": "describe", "text": f"A {gender}, {spec['role'] or 'an ordinary person'}, a clear natural voice."}
        sc["cast"][k] = spec
        names[low] = k
        if narrator:
            sc["narrator"] = k
        return k
    scene = None
    for raw in lines:
        s = re.sub(r"^(?:[-*•]|\d{1,2}[.)])\s+(?=\S)", "", raw.strip())     # ("- Lena (woman)", "1. Mayor (man)")
        if not s or s.startswith("//"):
            continue
        m = re.match(r"(?i)^(title|название|titlu|format|формат|language|язык|limba|limbă)\s*:\s*(.+)$", s)
        if m and scene is None:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key in ("title", "название", "titlu"):
                sc["title"] = val[:120]
            elif key in ("format", "формат"):              # (Romanian "Format" too)
                sc["format"] = "horizontal" if any(w in val.lower() for w in ("wide", "horizontal", "16", "широк", "гориз")) else "vertical"
            else:
                sc["language"] = val[:2].lower()
            continue
        m = re.match(r"(?i)^(narrator|рассказчик|naratoare|narator)\s*:\s*([^(]+)(?:\((.*)\))?$", s)
        if m and scene is None:
            add(m.group(2), (m.group(3) or "").split(","), narrator=True)
            continue
        if s.startswith("=="):
            head = s.strip("= ").strip()
            bg_part, _, vis = head.partition("|")
            bg_low = re.sub(r"\s+", " ", bg_part.strip().lower())
            if not vis and re.match(r"^(" + "|".join(VISUAL_KINDS) + r")\s*:", bg_low):
                bg_low, vis = "board", bg_part                # "== Flow: A -> B" (the picture without a background)
            bg = BG_WORDS.get(bg_low) or (bg_low if bg_low in bgs.BACKGROUNDS else "")
            if not bg:                                         # "Hospital corridor", "City hall, council chamber" ...
                hits = [(m_.start(), -len(k), v) for k, v in BG_WORDS.items() if len(k) > 3
                        for m_ in [re.search(r"\b" + re.escape(k) + r"\b", bg_low)] if m_]
                bg = min(hits)[2] if hits else ""           # (the first place named; the longest name there)
            if not bg:
                kind = vis.partition(":")[0].strip().lower()
                bg = "board" if kind in ("flow", "bars", "chart", "схема", "график", "диаграмма", "counter", "сумма") else "city"
            scene = {"bg": bg, "cast": [], "lines": [], "_vis": vis.strip()}
            sc["scenes"].append(scene)
            continue
        m = re.match(r"^([^:(\[]{1,40}?)\s*(?:\(([^)]*)\))?\s*(\[[^\]]*\])?\s*:\s*(.+)$", s)
        if m and scene is not None:
            spk = re.sub(r"\s+", " ", m.group(1).strip().lower())
            if spk in NOT_SPEAKERS:                        # "Note: ...", "Visual: ..." - not a line said
                continue
            who = sc["narrator"] if spk in NARRATOR_WORDS and sc.get("narrator") else add(m.group(1), [])
            attrs = [a.strip().lower() for a in (m.group(2) or "").split(",") if a.strip()]
            ln = {"who": who, "text": m.group(4).strip()}
            for a in attrs:
                pose, emo = _attr(a)
                if pose and not ln.get("pose"):
                    ln["pose"] = pose
                elif emo:
                    ln["emotion"] = emo
            if m.group(3) and any(w in m.group(3).lower() for w in ("bubble", "пузырь", "облако")):
                ln["bubble"] = True
            scene["lines"].append(ln)
            if who != sc.get("narrator") and who not in scene["cast"]:
                scene["cast"].append(who)
            continue
        m = re.match(r"^([^:(]{1,40}?)\s*\(([^)]*)\)\s*$", s)       # a character introduced: "Mayor Grant (man, mayor)"
        if m and scene is None:
            add(m.group(1), m.group(2).split(","))
    if not any(re.match(r"(?i)^(language|язык|limba|limbă)\s*:", x.strip()) for x in lines):   # from the letters
        said = " ".join(ln["text"] for s_ in sc["scenes"] for ln in s_["lines"])
        cyr, lat = len(re.findall(r"[А-Яа-яЁё]", said)), len(re.findall(r"[A-Za-z]", said))
        words = re.findall(r"[^\W\d_]+", said.lower())
        ro_marks = sum(1 for w in words if re.search(r"[ăâîșşțţ]", w))
        ro_words = sum(1 for w in words if w in RO_WORDS)
        sc["language"] = ("ru" if cyr > lat else
                          "ro" if words and (ro_marks + ro_words) / len(words) >= 0.08 and ro_marks + ro_words >= 3 else "en")
    if not sc.get("narrator") and sc["cast"]:
        first = next(iter(sc["cast"]))
        sc["narrator"] = first
    for s in sc["scenes"]:
        s["visual"] = _visual(s.pop("_vis"), len(s["lines"]))
        if s["visual"] is None:
            s.pop("visual")
        s["cast"] = s["cast"][:3]
    return sc


def _n(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f == int(f) else f"{f:g}"


def vis_text(v: dict) -> str:
    """What a scene shows, written back the way parse() reads it."""
    k = v.get("kind")
    if k == "title":
        return f"title: {v.get('title') or ''}" + (f" / {v['sub']}" if v.get("sub") else "")
    if k == "road":
        return "road" + (": holes back" if v.get("fresh") else ": repair" if v.get("patch_at") is not None else "")
    if k == "contract":
        title = v.get("title") or "CONTRACT"
        parts = [title] + ([f"price {v['price']}"] if v.get("price") else []) + ([f"stamp {v['stamp']}"] if v.get("stamp") else [])
        parts += [("+" if n.get("ok") else "") + str(n.get("text") or "") for n in v.get("notes") or []]
        return ("tender" if title.upper() == "TENDER" else "contract") + ": " + "; ".join(parts)
    if k == "flow":
        names = {n["id"]: n.get("label") or n["id"] for n in v.get("nodes") or []}
        return "flow: " + "; ".join(f"{names.get(e['from'], e['from'])} -> {names.get(e['to'], e['to'])}" + (f" {e['label']}" if e.get("label") else "")
                                    for e in v.get("edges") or [])
    if k == "bars":
        return "bars: " + ", ".join(f"{lab} {_n(val)}" for lab, val in zip(v.get("labels") or [], v.get("values") or [])) + \
            (f" {v['unit']}" if v.get("unit") else "")
    if k == "list":
        return "list: " + "; ".join([v.get("title") or ""] + [("+" if it.get("ok") else "") + str(it.get("text") or "") for it in v.get("items") or []])
    if k == "counter":
        return f"counter: {v.get('prefix') or ''}{_n(v.get('to') or 0)} {v.get('label') or ''}".rstrip()
    if k == "compare":
        return "compare: " + " vs ".join(f"{sd.get('label') or ''} {sd.get('price') or ''}".strip() for sd in v.get("sides") or [])
    if k == "bag":
        return f"bag: {v.get('text') or ''}".rstrip(": ")
    if k == "magnifier":
        return f"magnifier: {v.get('title') or ''}".rstrip(": ")
    if k == "percent":
        return f"percent: {_n(v.get('value') or 0)}% {v.get('label') or ''}".rstrip()
    if k == "timeline":
        return "timeline: " + "; ".join(f"{st.get('when') or ''} {st.get('what') or ''}".strip() for st in v.get("steps") or [])
    return ""


def to_text(sc: dict) -> str:
    """A script back as plain text (to change it the same way)."""
    sc = sc if isinstance(sc, dict) else {}                # (a script of odd shapes: what can be read of it)
    out = [f"Title: {sc.get('title') or 'Cartoon'}", f"Format: {sc.get('format') or 'vertical'}"]
    cast = {k: c for k, c in (sc.get("cast") or {}).items() if isinstance(c, dict)} if isinstance(sc.get("cast"), dict) else {}
    nar = sc.get("narrator") if isinstance(sc.get("narrator"), str) else None
    for k, c in cast.items():
        gender = "woman" if c.get("female") else "man"
        role = c.get("role") if isinstance(c.get("role"), str) else ""
        name = c.get("name") if isinstance(c.get("name"), str) and c.get("name") else str(k)
        if k == nar:
            out.append(f"Narrator: {name} ({gender}{', ' + role if role and role != 'narrator' else ''})")
        else:
            out.append(f"{name} ({gender}{', ' + role if role else ''})")
    rbg = {"city": "City street", "office": "Office", "city_hall": "City hall", "road": "Road", "bank": "Bank",
           "night": "Night street", "board": "Board", "paper": "Paper", "hospital": "Hospital", "school": "School",
           "shop": "Shop", "home": "Home", "site": "Building site"}
    scenes = sc.get("scenes") if isinstance(sc.get("scenes"), list) else []
    for s in (x for x in scenes if isinstance(x, dict)):
        try:
            vis = vis_text(s.get("visual") if isinstance(s.get("visual"), dict) else {})
        except (TypeError, KeyError, AttributeError, ValueError):
            vis = ""                                       # (a picture of an odd shape: left out of the text)
        vis = f" | {vis}" if vis else ""
        bg = s.get("bg") if isinstance(s.get("bg"), str) else "city"
        out.append("")
        out.append(f"== {rbg.get(bg, bg or 'city').capitalize()}{vis}")
        lines = s.get("lines") if isinstance(s.get("lines"), list) else []
        for ln in (x for x in lines if isinstance(x, dict)):
            w = ln.get("who") if isinstance(ln.get("who"), str) else ""
            nm = lambda key: (cast.get(key) or {}).get("name") if isinstance((cast.get(key) or {}).get("name"), str) else ""  # noqa: E731
            who = nm(w) or w or nm(nar) or nar or "Narrator"
            attrs = [x for x in (ln.get("pose"), ln.get("emotion")) if x and isinstance(x, str)]
            out.append(f"{who}" + (f" ({', '.join(attrs)})" if attrs else "") + (" [bubble]" if ln.get("bubble") else "")
                       + f": {ln.get('text') or ''}")
    return "\n".join(out) + "\n"


ROAD_TEXT = """Title: How a City Loses Millions on a Simple Road Contract
Format: vertical
Narrator: Kate (woman, narrator)
Mayor Grant (man, mayor)
Deputy Ed (man, official)
Rick Stone (man, contractor boss)
Bob (man, road worker)
Lena (woman, journalist)

== City street | title: How a City Loses Millions / on a simple road contract
Kate (wave, happy): A road full of holes. Fixing it should be simple, right?
Kate (explain, sly): Let's see how it ends up costing millions.

== Road | road
Lena (shrug, angry) [bubble]: This road is a disaster!
Kate: The city announces a tender to repair two kilometers of road.
Kate: A fair price is about one point two million dollars.

== Office | tender: TENDER; 10 years of experience; special asphalt brand; 5 days to apply
Kate: But Deputy Ed writes the tender for one company only.
Kate: Ten years of experience. A special asphalt brand.
Kate: And just five days to apply.
Deputy Ed (present, sly): Perfectly normal requirements!

== Night
Rick Stone (count, sly) [bubble]: We win, and you will be thanked.
Deputy Ed (sneaky, happy): I like being thanked.
Kate: Only Rick's company, RoadCo, fits the rules. What a surprise.

== Office | contract: CONTRACT; price $4 800 000; stamp APPROVED
Kate: RoadCo wins with a price four times higher. Four point eight million.
Mayor Grant (point up, happy): Approved! Our city deserves the best!

== Board | flow: City budget -> RoadCo $4.8M; RoadCo -> Cheap crew $1M; RoadCo -> Officials kickback
Kate: The city pays RoadCo four point eight million.
Kate: RoadCo hires a cheap crew for one million to do the work.
Kate: And part of the difference quietly goes back to the officials who signed.

== Road | road: repair
Bob (shrug, worried) [bubble]: Half the asphalt, the boss said. Saves money.
Kate: The holes are covered with a thin layer. It looks fine. For now.

== Road | road: holes back
Kate: Six months and one winter later...
Lena (facepalm, sad): The holes are back. All of them.
Kate (sly): Time for a new repair contract. Guess who wins it.

== Board | bars: fair price 1.2, paid twice 9.6 M
Kate: One road. Paid four times the fair price. Twice.
Kate: And every dollar of it came from taxpayers.

== City hall | list: Red flags; Only one bidder; Rushed deadlines; Price far above the market
Lena (explain, angry): How to spot it?
Lena (point): One bidder and rushed deadlines.
Lena (point up): And a price far above the market.
Kate (wave, happy): Follow the money. And ask who wrote the tender.
"""
