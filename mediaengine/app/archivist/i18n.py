"""Interface language for the whole app (English default, Russian optional).

Translation happens once, on the finished page (Flask after_request): only visible text between tags and the
placeholder/title attributes are replaced, and only quoted UI messages inside page scripts - never URLs, form
values, file names or paths, so every page works exactly the same in both languages.

Matching rules (safe for user content such as file names and titles):
- APP pages: a text is translated only when the WHOLE text of an element equals a known phrase, or when it matches
  one of the PATTERNS (texts with numbers in them). A file called "Library videos.mp4" is never touched.
- Auto Edit pages (/auto...) additionally use the curated phrase-inside-text replacement of auto_edit_ru; there all
  user content is marked translate='no'.
"""
from __future__ import annotations

import html as _html
import json
import re

from .auto_edit_ru import JS_PHRASES as _AE_JS
from .auto_edit_ru import PHRASES as _AE_PHRASES
from .auto_edit_ru import _ORDERED as _AE_ORDERED
from .ru_app import APP_COUNT_SUBS, APP_JS, APP_PATTERNS, APP_PHRASES, APP_UNIT_SUBS

LANGS = ("en", "ru")


def ui_language() -> str:
    from .config import load_config, save_config
    try:
        cfg = load_config()
    except Exception:
        return "en"
    v = str(cfg.get("ui_language") or "").lower()
    setup, build = _setup_language()
    mark = f"{setup}|{build}"
    if setup in LANGS and build and mark != str(cfg.get("setup_language_applied") or ""):
        # each Setup run: the language chosen there becomes the program's language once (also over a language
        # saved by an older build); switching in the program afterwards is kept until the next Setup
        try:
            cfg["ui_language"], cfg["setup_language_applied"] = setup, mark
            save_config(cfg)
        except Exception:
            pass
        return setup
    if v in LANGS:
        return v
    if setup in LANGS:                                 # an older Setup (no build mark): first start only
        return setup
    return "ru" if _windows_is_russian() else "en"     # no choice anywhere yet: the Windows display language


def _setup_language() -> tuple[str, str]:
    """(language, build) that the last Setup run wrote; ("", "") when not installed with Setup or not on Windows."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\MediaEngine") as k:
            lang = str(winreg.QueryValueEx(k, "Language")[0] or "").lower()
            try:
                build = str(winreg.QueryValueEx(k, "LanguageBuild")[0] or "")
            except OSError:
                build = ""
            return lang, build
    except Exception:
        return "", ""


def set_ui_language(lang: str) -> None:
    from .config import load_config, save_config
    cfg = load_config()
    cfg["ui_language"] = "ru" if lang == "ru" else "en"
    save_config(cfg)


def _windows_is_russian() -> bool:
    try:
        import ctypes
        return (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x19    # LANG_RUSSIAN
    except Exception:
        return False


# ---------------------------------------------------------------- dictionaries
def _with_escaped(d: dict) -> dict:
    out = dict(d)
    for en, ru in d.items():
        esc = _html.escape(en, quote=True)
        if esc != en:
            out.setdefault(esc, _html.escape(ru, quote=True))
    return out


EXACT = _with_escaped({**_AE_PHRASES, **APP_PHRASES})
PATTERNS = [(re.compile(p), r) for p, r in APP_PATTERNS]
COUNT_SUBS = [(re.compile(p), r) for p, r in APP_COUNT_SUBS]
UNIT_SUBS = [(re.compile(p), r) for p, r in APP_UNIT_SUBS]


def _quoted(d: dict) -> dict:
    """APP_JS holds bare texts: replace them only as complete quoted literals ('…', "…" or `…`)."""
    out = {}
    for en, ru in d.items():
        for q in ("'", '"', "`"):
            if q not in ru:
                out[q + en + q] = q + ru + q
    return out


JS = {**_AE_JS, **_quoted(APP_JS)}

# Text that page scripts put on the page later (toasts, badges, progress lines) is translated in the browser with
# the same whole-text dictionary and patterns (MutationObserver), so no script has to know about languages.
_CLIENT = None


def _client_script() -> str:
    global _CLIENT
    if _CLIENT is None:
        d = {k: v for k, v in {**_AE_PHRASES, **APP_PHRASES}.items() if len(k) <= 400}
        pats = [[p, re.sub(r"\\(\d)", r"$\1", r)] for p, r in APP_PATTERNS]
        data = json.dumps({"d": d, "p": pats}, ensure_ascii=False).replace("</", "<\\/")
        _CLIENT = ("<script>window.ME_I18N=" + data + ";(function(){const D=ME_I18N.d,P=ME_I18N.p.map(x=>[new RegExp('^(?:'+x[0]+')$'),x[1]]);"
                   "function tr(s){const m=/^(\\s*)([\\s\\S]*?)(\\s*)$/.exec(s),c=m[2];if(!c||!/[A-Za-z]/.test(c))return null;"
                   "if(Object.prototype.hasOwnProperty.call(D,c))return m[1]+D[c]+m[3];for(const [r,x] of P){if(r.test(c))return m[1]+c.replace(r,x).replace(/⟦([^⟧]*)⟧/g,(a,b)=>Object.prototype.hasOwnProperty.call(D,b)?D[b]:b).replace(/⟪(\\d+)\\|([^|⟫]*)\\|([^|⟫]*)\\|([^|⟫]*)⟫/g,(a,n,o,f,m2)=>{n=+n;return (n%10==1&&n%100!=11)?o:((n%10>=2&&n%10<=4&&!(n%100>=12&&n%100<=14))?f:m2)})+m[3]}return null}"
                   "function skip(n){const p=n.parentElement;return !p||!!p.closest(\"[translate='no'],.ae-path,.path,.mono,script,style,textarea,code,pre\")}"
                   "function one(t){if(skip(t))return;const r=tr(t.data);if(r!==null&&r!==t.data)t.data=r}"
                   "function walk(root){const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);const a=[];let n;while(n=w.nextNode())a.push(n);a.forEach(one)}"
                   "window.ME_L=s=>(s!=null&&Object.prototype.hasOwnProperty.call(D,s))?D[s]:s;"
                   "new MutationObserver(ms=>{for(const m of ms){if(m.type==='characterData')one(m.target);else for(const n of m.addedNodes){if(n.nodeType===3)one(n);else if(n.nodeType===1)walk(n)}}})"
                   ".observe(document.documentElement,{childList:true,subtree:true,characterData:true});walk(document.body)})();</script>")
    return _CLIENT

# a tag may hold ">" inside a quoted attribute (onclick="...=>..."): match quoted values as a whole
_TAG = r"""<(?:[^>"']|"[^"]*"|'[^']*')+>"""
_SPLIT = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<textarea\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>.*?</textarea>|" + _TAG + ")", re.S | re.I)
_ATTR = re.compile(r"""(\b(?:placeholder|title|aria-label)=)(['"])(.*?)\2""", re.S)
_PROTECT = re.compile(r"""<(\w+)\b[^>]*(?:translate=['"]no['"]|class=['"][^'"]*\b(?:ae-path|path|mono)\b[^'"]*['"])[^>]*>.*?</\1>""", re.S)
_WS = re.compile(r"^(\s*)(.*?)(\s*)$", re.S)
_ON = re.compile(r"""(\bon[a-z]+=)(["'])(.*?)\2""", re.S)
_LOOKUP = re.compile("⟦([^⟧]*)⟧")


def translate_text(t: str, substring: bool = False) -> str:
    m = _WS.match(t)
    lead, core, tail = m.group(1), m.group(2), m.group(3)
    if not core or not re.search(r"[A-Za-z]", core):
        return t
    if core in EXACT:
        return lead + EXACT[core] + tail
    if core.endswith(" · MediaEngine") and core != " · MediaEngine":   # page titles
        inner = translate_text(core[:-14], False)          # a project title in the window title stays as typed unless it is a page name
        return lead + inner + " · MediaEngine" + tail
    for rx, rep in PATTERNS:
        mm = rx.fullmatch(core)
        if mm:   # ⟦x⟧ in a replacement = look x up too ("quality good" -> "качество хорошее")
            return lead + _expand(mm, rep) + tail
    if substring:
        for rx, rep in COUNT_SUBS:            # counted nouns first, with Russian plural forms
            t = rx.sub(rep, t)
        for en, ru in _AE_ORDERED:
            if en in t:
                t = t.replace(en, ru)
        for rx, rep in UNIT_SUBS:
            t = rx.sub(rep, t)
        t = _finish(t)
    return t


_PLURAL = re.compile(r"⟪(\d+)\|([^|⟫]*)\|([^|⟫]*)\|([^|⟫]*)⟫")


def ru_plural(n: int, one: str, few: str, many: str) -> str:
    """1 версия, 2 версии, 5 версий, 11 версий, 21 версия."""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# Russian writes a decimal comma: "5,00 с", "16,8 МБ". Only a number with a unit right after it and then the end of
# the text or a separator (· , ; ) ( / — →, or a full stop at the end), so times like 0:04.2, versions like 3.13.0
# and file names ("Дача 15.08 с мамой.mp4", "клип 1.5 с.webm") stay exactly as they are.
_DEC = re.compile(r"(?<![\d.:,])(\d+)\.(\d+)(?=\s?(?:с|сек|Б|КБ|МБ|ГБ|ТБ)(?:\s*$|\s*[·,;:()/—–→]|\.(?=\s|$)))")
_KEEP = re.compile("\ue000(\\d+)\ue001")


def _finish(text: str) -> str:
    text = _LOOKUP.sub(lambda k: EXACT.get(k.group(1), k.group(1)), text)
    text = _PLURAL.sub(lambda k: ru_plural(int(k.group(1)), k.group(2), k.group(3), k.group(4)), text)
    return _DEC.sub(r"\1,\2", text)


def _expand(mm, rep: str) -> str:
    """A pattern's Russian text with the captured parts put in. A captured part that is not a plain number (a file
    or folder name, a title, an error text) is put in exactly as it is: the decimal comma never touches it."""
    kept = []

    def part(k):
        v = mm.group(int(k.group(1))) or ""
        if re.fullmatch(r"\d+(?:\.\d+)?", v):
            return v
        return keep(v)

    def keep(v):
        kept.append(v)
        return "\ue000%d\ue001" % (len(kept) - 1)

    def look(k):     # ⟦…⟧: a known text is translated, anything else is put in as it is (and stays protected)
        key = _KEEP.sub(lambda q: kept[int(q.group(1))], k.group(1))
        return EXACT[key] if key in EXACT else keep(key)

    text = re.sub(r"\\(\d)", part, rep)
    text = _LOOKUP.sub(look, text)
    text = _PLURAL.sub(lambda k: ru_plural(int(k.group(1)), k.group(2), k.group(3), k.group(4)), text)
    text = _DEC.sub(r"\1,\2", text)
    return _KEEP.sub(lambda k: kept[int(k.group(1))], text)


def translate_script(block: str) -> str:
    for en, ru in JS.items():
        if en in block:
            block = block.replace(en, ru)
    return block


def translate_page(page: str, path: str = "/") -> str:
    substring = path.startswith("/auto")
    kept = []

    def hold(m):
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"
    page = _PROTECT.sub(hold, page)
    out = []
    for part in _SPLIT.split(page):
        if not part:
            continue
        if part.startswith("<"):
            low = part[:9].lower()
            if low.startswith("<script"):
                out.append(translate_script(part))
            elif low.startswith("<style"):
                out.append(part)
            elif low.startswith("<textarea"):          # typed text stays; only the hint (placeholder) is translated
                head = re.match(_TAG, part, re.S).group(0)
                out.append(_ATTR.sub(lambda m: m.group(1) + m.group(2) + translate_text(m.group(3), substring) + m.group(2), head) + part[len(head):])
            else:
                part = _ON.sub(lambda m: m.group(1) + m.group(2) + translate_script(m.group(3)) + m.group(2), part)   # onclick="…confirm('…')"
                out.append(_ATTR.sub(lambda m: m.group(1) + m.group(2) + translate_text(m.group(3), substring) + m.group(2), part))
        else:
            out.append(translate_text(part, substring))
    page = "".join(out)
    page = page.replace("<html>", "<html lang='ru'>", 1)
    if "</body>" in page:
        page = page.replace("</body>", _client_script() + "</body>", 1)
    return re.sub("\x00(\\d+)\x00", lambda m: kept[int(m.group(1))], page)


def translate_json(data):
    """Messages the page scripts show (error / message fields of API answers)."""
    if isinstance(data, dict):
        return {k: (translate_text(v) if k in ("error", "message", "detail", "label") and isinstance(v, str) else translate_json(v))
                for k, v in data.items()}
    if isinstance(data, list):
        return [translate_json(x) for x in data]
    return data


def install(app) -> None:
    """Translate every HTML page (and API messages) after it is made, when the interface language is Russian."""
    from flask import request

    @app.after_request
    def _ru(resp):
        try:
            if resp.direct_passthrough or resp.status_code in (204, 304) or ui_language() != "ru":
                return resp
            if resp.mimetype == "text/html":
                resp.set_data(translate_page(resp.get_data(as_text=True), request.path))
            elif resp.mimetype == "application/json" and request.path.startswith("/api/"):
                data = json.loads(resp.get_data(as_text=True))
                resp.set_data(json.dumps(translate_json(data), ensure_ascii=False))
        except Exception:
            pass
        return resp
