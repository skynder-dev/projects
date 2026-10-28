"""The page "Cartoon Studio" (Auto Edit -> Cartoon Studio): a 2D cartoon made by MediaEngine from a script - its own
characters, scenes, schemes of money, voices and captions (cartoon/). Make one, watch it, change a line, a background
or a feeling and make it again."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from flask import jsonify, redirect, request, send_file

from . import voice as vo
from .cartoon import bgs, chars as ch, film as F, jobs as cj, stories, textscript as T, writer as W

CSS = """<style>
.ct-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.ct-choices label{display:inline-flex;gap:6px;align-items:center;margin:3px 14px 3px 0}
.ct-film{border-top:1px solid var(--line);padding:12px 0}
.ct-film video{max-width:240px;max-height:320px;border-radius:10px;background:#000}
.ct-scene{border:1px solid var(--line2);border-radius:12px;padding:10px 12px;margin:10px 0}
.ct-line{display:grid;grid-template-columns:150px minmax(0,1fr) 130px 130px;gap:8px;margin:6px 0}
@media(max-width:900px){.ct-line{grid-template-columns:1fr}}
.ct-line input{width:100%}
.ct-big video{max-width:100%;max-height:70vh;border-radius:12px;background:#000}
</style>"""
_JOB_ID = r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}"
_STEP = {"starting": "Starting…", "voices": "The characters are speaking…", "drawing": "Drawing the pictures…",
         "checking": "Checking the film…", "loading": "Starting the story writer…", "writing": "Writing the story…"}
_WR_STEP = {"checking": "Checking the PC…", "program": "Downloading llama.cpp (the program that runs the model)…",
            "model": "Downloading the model (Qwen3-4B, about 4.3 GB)…", "checking_model": "Checking the downloaded model…",
            "testing": "Starting the story writer for a test…"}
LANG_LABELS = {"en": "English", "ru": "Русский", "ro": "Română"}
BG_LABELS = {"city": "City street", "office": "Office", "city_hall": "City hall", "road": "Road", "bank": "Bank",
             "night": "Night street", "board": "Board (schemes, charts)", "paper": "Paper"}
EMO_LABELS = {"": "—", "neutral": "calm", "happy": "happy", "angry": "angry", "sad": "sad", "surprised": "surprised",
              "sly": "sly", "worried": "worried"}
POSE_LABELS = {"": "—", "talk": "talking", "explain": "explaining", "point": "pointing", "point_up": "finger up",
               "shrug": "shrugging", "cross": "arms crossed", "think": "thinking", "wave": "waving", "hands_up": "hands up",
               "count": "rubbing hands", "present": "presenting", "facepalm": "hand to face", "fist": "fist",
               "sneaky": "sneaky", "idle": "standing"}
LEN_LABELS = (("60", "about 1 minute"), ("75", "about 75 seconds"), ("90", "about 1.5 minutes"))
STORY_LABELS = {"road_contract": "How a City Loses Millions on a Simple Road Contract (example, 10 scenes)"}


HELP_EN = ("First lines: <code>Title:</code>, <code>Format: vertical</code> or <code>wide</code>, <code>Narrator: Name (woman)</code>, "
           "then the characters - <code>Name (man, mayor)</code>. A scene starts with <code>==</code> and its background "
           "(City street, Office, City hall, Road, Bank, Night, Board, Paper); after <code>|</code> what it shows: "
           "<code>title: …</code>, <code>road</code>, <code>contract: CONTRACT; price $4 800 000; stamp APPROVED</code>, "
           "<code>flow: City -&gt; Company $4.8M; Company -&gt; Officials kickback</code>, <code>bars: fair 1.2, paid 9.6 M</code>, "
           "<code>list: Red flags; one bidder; rushed deadlines</code>, <code>counter: $4 800 000 spent</code>. "
           "A line: <code>Name (gesture, feeling): words</code>; <code>[bubble]</code> shows it in a speech bubble. "
           "Gestures: talk, explain, point, point up, shrug, cross, think, wave, hands up, rubs hands, present, facepalm, fist, "
           "sneaky. Feelings: calm, happy, angry, sad, surprised, sly, worried. English or Russian.")
HELP_RU = ("Первые строки: <code>Название:</code>, <code>Формат: вертикальный</code> или <code>широкий</code>, "
           "<code>Рассказчик: Имя (женщина)</code>, потом персонажи — <code>Имя (мужчина, мэр)</code>. Сцена начинается с "
           "<code>==</code> и фона (Улица, Офис, Мэрия, Дорога, Банк, Ночь, Доска, Бумага); после <code>|</code> — что в ней "
           "показано: <code>заголовок: …</code>, <code>дорога</code>, <code>договор: ДОГОВОР; цена 4 800 000 ₽; печать УТВЕРЖДЕНО</code>, "
           "<code>схема: Бюджет -&gt; Фирма 4,8 млн; Фирма -&gt; Чиновники откат</code>, <code>график: честно 1.2, заплатили 9.6 млн</code>, "
           "<code>список: Признаки; одна заявка; сжатые сроки</code>, <code>сумма: 4 800 000 ₽ потрачено</code>. Реплика: "
           "<code>Имя (жест, настроение): слова</code>; <code>[пузырь]</code> — показать её в облачке. Жесты: говорит, объясняет, "
           "показывает, палец вверх, пожимает плечами, руки скрещены, думает, машет, руки вверх, потирает руки, представляет, "
           "рука у лица, кулак, крадётся. Настроения: спокойно, радостно, сердито, грустно, удивлённо, хитро, тревожно. "
           "По-русски или по-английски.")


def _help() -> str:
    try:
        from .i18n import ui_language
        ru = ui_language() == "ru"
    except Exception:
        ru = False
    return ("<details style='margin:6px 0'><summary>How to write a story</summary><div class='muted' style='font-size:13px;"
            f"line-height:1.5' translate='no'>{HELP_RU if ru else HELP_EN}</div></details>")


def _label(j: dict) -> str:
    return _STEP.get(str(j.get("step") or "").split(" ")[0], "Working…")


def register(app, page, err_page, e, human_bytes):

    def _bar(j: dict) -> str:
        return (f"<div class='ae-bar' style='margin-top:6px'><i data-bar style='width:{int(100 * float(j.get('progress') or 0))}%'></i></div>"
                f"<div class='muted' style='font-size:13px' data-step>{e(_label(j))}</div>"
                f"<form method='post' action='/auto/cartoon/{j['id']}/stop' style='margin-top:6px'><button class='btn2'>Stop</button></form>")

    def _state_html(j: dict) -> str:
        st, res = j["state"], j.get("result") or {}
        if st == "working":
            return _bar(j)
        if st == "waiting":
            return ("<div class='muted'>Waiting (another voice-over, clip or cartoon job is being made first).</div>"
                    f"<form method='post' action='/auto/cartoon/{j['id']}/stop' style='margin-top:6px'><button class='btn2'>Don't make it</button></form>")
        if st in ("failed", "interrupted"):
            msg = res.get("error") or ("Interrupted (MediaEngine was closed)." if st == "interrupted" else "Failed")
            return (f"<div class='errbox' style='margin-top:6px'>{e(msg)}</div>"
                    f"<form method='post' action='/auto/cartoon/{j['id']}/retry' style='margin-top:6px'><button>Try again</button></form>")
        return ""

    def _block(j: dict, inner: str) -> str:
        return f"<div class='ct-film' data-job='{j['id']}' data-state='{j['state']}'>{inner}</div>"

    def _story_row(j: dict) -> str:
        res = j.get("result") or {}
        when = e(str(j.get("created_at") or "")[:16].replace("T", " "))
        head = (f"<div class='ct-row'><span>Story:</span> <a href='/auto/cartoon/{j['id']}'><b translate='no'>{e(j.get('title') or '')}</b></a>"
                f"<span class='muted' style='font-size:13px' translate='no'>{when} · {e(LANG_LABELS.get(j.get('lang'), ''))}</span></div>")
        if j["state"] == "done":
            body = (f"<div class='muted' style='font-size:13px;margin-top:4px'><span translate='no'>{int(res.get('scenes') or 0)}</span> "
                    f"<span>scenes</span> · <span translate='no'>{int(res.get('words') or 0)}</span> <span>words</span></div>"
                    f"<div class='ct-row' style='margin-top:8px'><a class='btn' href='/auto/cartoon/{j['id']}'>Read it and make the cartoon</a>"
                    + _delete(j) + "</div>")
        else:
            body = _state_html(j) + ("" if j["state"] in ("working", "waiting") else f"<div style='margin-top:6px'>{_delete(j)}</div>")
        return _block(j, head + body)

    def _film_row(j: dict) -> str:
        if j.get("kind") == "cartoon_write":
            return _story_row(j)
        res = j.get("result") or {}
        when = e(str(j.get("created_at") or "")[:16].replace("T", " "))
        head = (f"<div class='ct-row'><a href='/auto/cartoon/{j['id']}'><b translate='no'>{e(j.get('title') or '')}</b></a>"
                f"<span class='muted' style='font-size:13px' translate='no'>{when}</span>"
                + ("<span class='muted' style='font-size:13px'>without voices (a preview)</span>" if not j.get("voices") else "")
                + "</div>")
        body = ""
        if j["state"] == "done":
            body = (f"<div class='ct-row' style='margin-top:8px;align-items:flex-start'>"
                    f"<video controls preload='metadata' src='/auto/cartoon/{j['id']}/film.mp4'></video><div>"
                    f"<div class='muted' style='font-size:13px'><span translate='no'>{round(float(res.get('seconds') or 0))}</span> "
                    f"<span>s</span> · <span translate='no'>{int(res.get('scenes') or 0)}</span> <span>scenes</span></div>"
                    + (f"<div class='muted' style='font-size:13px'><span>Saved in</span> <span class='ae-path' translate='no'>"
                       f"{e(res.get('saved') or '')}</span></div>" if res.get("saved") else "")
                    + f"<div class='ct-row' style='margin-top:8px'><a class='btn' href='/auto/cartoon/{j['id']}'>Change and make again</a>"
                    + (f"<form method='post' action='/auto/cartoon/{j['id']}/reveal' style='margin:0'><button class='btn2'>Show in folder</button></form>"
                       if res.get("saved") else "")
                    + _delete(j) + "</div></div></div>")
        else:
            body = _state_html(j) + ("" if j["state"] in ("working", "waiting") else f"<div style='margin-top:6px'>{_delete(j)}</div>")
        return _block(j, head + body)

    def _delete(j: dict) -> str:
        if j["state"] in ("working", "waiting"):
            return ""
        q = ("Delete this story?" if j.get("kind") == "cartoon_write" else "Delete it? The film saved in the folder stays.")
        return (f"<form method='post' action='/auto/cartoon/{j['id']}/delete' style='margin:0' onsubmit=\"return confirm(window.ME_L?"
                f"ME_L('{q}'):'{q}')\">"
                f"<button class='btn2'>Delete</button></form>")

    def _format_choice(current: str) -> str:
        return "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if k == current else ''}> {e(v)}</label>"
                       for k, v in (("vertical", "Vertical 9:16 (TikTok, Reels, Shorts)"), ("horizontal", "Wide 16:9 (YouTube)")))

    def _captions_choice() -> str:
        styles = "".join(f"<option value='{k}'>{e(v)}</option>" for k, v in
                         (("pop", "Bold capitals, the word said in color"), ("box", "On a dark box"), ("classic", "Classic"),
                          ("minimal", "Calm (business)"), ("single", "One word at a time, big"), ("block", "The word on a color block")))
        return (f"<label style='display:block;margin-top:8px'><input type='checkbox' name='captions' value='1' checked> Captions</label>"
                f"<div class='ct-row' style='margin-top:4px'><span>Look</span><select name='style'>{styles}</select></div>")

    def _voices_choice() -> str:
        have = vo.installed()
        return (f"<label style='display:block;margin-top:8px'><input type='checkbox' name='voices' value='1' {'checked' if have else 'disabled'}> "
                f"The characters speak (the voice add-on; a few minutes)</label>"
                + ("" if have else "<div class='muted' style='font-size:13px'>Without the voice add-on: a quick preview without "
                                   "voices. <a href='/auto/voice'>Install the voice add-on</a></div>"))

    def _lang_select(current: str = "en") -> str:
        return "".join(f"<option value='{k}' {'selected' if k == current else ''} translate='no'>{e(v)}</option>"
                       for k, v in LANG_LABELS.items())

    def _adapt_form(source: str, fmt: str, title: str, lang: str = "") -> str:
        """Retell a story for viewers of another country (and language): a story written by the model."""
        other = next((k for k in ("ru", "en", "ro") if k != lang), "en")
        return (f"<form method='post' action='/auto/cartoon/write' style='margin-top:8px' "
                f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<input type='hidden' name='mode' value='adapt'><input type='hidden' name='format' value='{e(fmt)}'>"
                f"<input type='hidden' name='title' value='{e(title)}'><textarea name='source' hidden>{e(source)}</textarea>"
                f"<div class='ct-row'><span>Language</span><select name='lang'>{_lang_select(other)}</select>"
                f"<span>Viewers in</span><input name='country' maxlength='60' placeholder='(a country)' style='width:180px'>"
                f"<button>Retell the story</button></div>"
                f"<div class='muted' style='font-size:13px;margin-top:4px'>The model translates it and changes the names, the money "
                f"and the offices to the country's own; the scenes and pictures stay. The new story opens to read before the cartoon.</div></form>")

    def _writer_card() -> str:
        s = W.status()
        if s["state"] == "running":
            pct = int(100 * s["done"] / s["total"]) if s.get("total") else 3
            return (f"<div class='card' id='wrInstall'><h2 style='margin-top:0'>Installing the story writer</h2>"
                    f"<div class='ae-bar'><i id='wrBar' style='width:{max(3, pct)}%'></i></div>"
                    f"<div style='margin-top:8px'><span id='wrStep'>{e(_WR_STEP.get(s.get('step'), ''))}</span></div>"
                    f"<div class='muted ae-path' id='wrDetail' translate='no'>{e(s.get('detail') or '')}</div>"
                    f"<div class='muted' style='font-size:13px;margin-top:6px'>From a few minutes to half an hour, depending on the "
                    f"internet. You can use MediaEngine meanwhile; closing it stops the download (it continues where it stopped "
                    f"when you press Install again).</div>"
                    f"<form method='post' action='/auto/cartoon/writer/cancel' style='margin-top:10px'><button class='btn2'>Cancel</button></form></div>")
        if s["installed"]:
            m = s.get("manifest") or {}
            where = (f"<span>the graphics card</span> <span translate='no'>{e(m.get('gpu') or '')}</span>" if m.get("gpu")
                     else "<span>the processor</span>")
            secs = "".join(f"<option value='{k}' {'selected' if k == '75' else ''}>{e(v)}</option>" for k, v in LEN_LABELS)
            return (f"<div class='card' id='writer'><h2 style='margin-top:0'>Write a story</h2>"
                    f"<form method='post' action='/auto/cartoon/write' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                    f"<b>What is it about?</b><div class='muted' style='font-size:13px'>A topic in a few words - or paste a text (an "
                    f"article, notes, what is said in a video): the story retells it with its own characters.</div>"
                    f"<textarea name='about' rows='4' maxlength='5000' style='width:100%' "
                    f"placeholder='Why a city hospital pays three times more for the same medicine'></textarea>"
                    f"<div class='ct-row' style='margin-top:8px'><span>Language</span><select name='lang'>{_lang_select()}</select>"
                    f"<span>Viewers in</span><input name='country' maxlength='60' placeholder='(a country, if it matters)' style='width:200px'>"
                    f"<span>Length</span><select name='secs'>{secs}</select></div>"
                    f"<div class='ct-choices' style='margin-top:8px'><b>Format</b><br>{_format_choice('vertical')}</div>"
                    f"<div style='margin-top:12px'><button class='ae-big'>Write the story</button></div></form>"
                    f"<div class='muted' style='font-size:13px;margin-top:8px'><span>The free model on this PC (Qwen3-4B) writes it on</span> "
                    f"{where}<span>: about a minute on a graphics card, several minutes on the processor. Then read it, change what you "
                    f"like and make the cartoon.</span></div>"
                    f"<details style='margin-top:8px'><summary class='muted'>Remove the story writer</summary>"
                    f"<form method='post' action='/auto/cartoon/writer/remove' style='margin-top:8px' "
                    f"onsubmit=\"return confirm(window.ME_L?ME_L('Remove the story writer?'):'Remove the story writer?')\">"
                    f"<button class='btn2'>Remove</button> <span class='muted' style='font-size:13px'>Frees about 4.4 GB. The stories "
                    f"and cartoons stay.</span></form></details></div>")
        err = f"<div class='errbox' style='margin-bottom:10px'>{e(s.get('error') or '')}</div>" if s["state"] == "failed" else ""
        low = s.get("free", 0) < s.get("size", 0) + 1_500_000_000
        return (f"<div class='card' id='writer'>{err}<h2 style='margin-top:0'>Write a story with a free model on this PC</h2>"
                f"<div>The program can write the story itself: from a topic, from a text, or retold for another country - in "
                f"English, Russian or Romanian. It needs a free language model (Qwen3-4B, Apache-2.0) and llama.cpp (MIT), "
                f"downloaded once: about 4.4 GB, into the data folder:</div>"
                f"<div class='ae-path' translate='no'>{e(str(W.ROOT))}</div>"
                f"<div class='muted' style='font-size:13px;margin-top:6px'>MediaEngine goes online for it only when you press the "
                f"button (github.com, huggingface.co). It runs on this PC; nothing is sent anywhere.</div>"
                + ("<div class='errbox' style='margin-top:8px'>Not enough free space: about 6 GB are needed while installing.</div>" if low else "")
                + f"<form method='post' action='/auto/cartoon/writer/install' style='margin-top:12px' "
                  f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                  f"<button class='ae-big'>{'Try again' if s['state'] == 'failed' else 'Install the story writer'}</button></form></div>")

    @app.get("/auto/cartoon")
    def cartoon_home():
        rows = "".join(_film_row(j) for j in cj.films())
        help_ = _help()
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Cartoon Studio</h1>"
                f"<div class='lead'>A short 2D cartoon made by MediaEngine: its own characters (the same in every episode), "
                f"scenes, schemes of money and charts, the characters' voices and captions - one MP4. Change any line, "
                f"background or feeling and make it again.</div></div>{_READY}{_writer_card()}"
                f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>New cartoon</h2>"
                f"<form method='post' action='/auto/cartoon/new' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<b>Story</b><div class='muted' style='font-size:13px'>The example below - change it or write your own.</div>{help_}"
                f"<textarea name='text' rows='16' style='width:100%;font-family:Consolas,monospace;font-size:13px' translate='no'>"
                f"{e(T.ROAD_TEXT)}</textarea>"
                f"<details style='margin-top:6px'><summary>A script as JSON instead</summary>"
                f"<textarea name='script' rows='6' style='width:100%' placeholder='Paste a script here (only for \"My script\")'></textarea></details>"
                f"<div class='ct-choices' style='margin-top:8px'><b>Format</b><br>{_format_choice('vertical')}</div>"
                f"{_voices_choice()}{_captions_choice()}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the cartoon</button></div></form></div>"
                + (f"<div class='card' id='films' style='margin-top:14px'><h2 style='margin-top:0'>Cartoons and stories</h2>{rows}</div>" if rows else ""))
        return page("Cartoon Studio", body, _POLL_JS)

    def _make(script: dict, f) -> str:
        script = dict(script)
        if f.get("format") in F.FORMATS:
            script["format"] = f.get("format")
        cap = {"style": f.get("style") or "pop"} if f.get("captions") == "1" else None
        return cj.new_make(script, f.get("voices") == "1", cap)

    @app.post("/auto/cartoon/new")
    def cartoon_new():
        f = request.form
        try:
            if f.get("story") == "own" or str(f.get("script") or "").strip():
                try:
                    script = json.loads(f.get("script") or "")
                except ValueError:
                    raise F.FilmError("The script is not valid JSON.")
                if not isinstance(script, dict):
                    raise F.FilmError("The script is not valid JSON.")
            elif str(f.get("text") or "").strip():
                script = T.parse(f.get("text") or "")
                if not script["scenes"]:
                    raise F.FilmError("The story has no scenes: start each scene with == and its background.")
            else:
                script = copy.deepcopy(stories.STORIES.get(f.get("story") or "", stories.ROAD_CONTRACT))
            jid = _make(script, f)
        except (F.FilmError, vo.VoiceError) as exc:
            return err_page(str(exc), "/auto/cartoon")
        return redirect("/auto/cartoon#films" if jid else "/auto/cartoon")

    @app.get("/auto/cartoon/<jid>")
    def cartoon_one(jid):
        if not re.fullmatch(_JOB_ID, jid):
            return err_page("No such job.", "/auto/cartoon")
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return err_page("No such job.", "/auto/cartoon")
        if not str(j.get("kind") or "").startswith("cartoon_"):
            return err_page("No such job.", "/auto/cartoon")
        if j.get("kind") == "cartoon_write":
            return _story_page(j)
        try:
            film = F.check_script(cj.script_of(jid))
        except F.FilmError as exc:
            return err_page(str(exc), "/auto/cartoon")
        who = "".join(f"<option value='{k}' translate='no'>{e(c.get('name') or k)}</option>" for k, c in film["cast"].items())
        scenes = ""
        for i, s in enumerate(film["scenes"]):
            bgsel = "".join(f"<option value='{k}' {'selected' if k == s['bg'] else ''}>{e(v)}</option>" for k, v in BG_LABELS.items())
            lines = ""
            for jn, ln in enumerate(s["lines"]):
                wsel = who.replace(f"value='{ln['who']}'", f"value='{ln['who']}' selected")
                esel = "".join(f"<option value='{k}' {'selected' if k == (ln.get('emotion') or '') else ''}>{e(v)}</option>"
                               for k, v in EMO_LABELS.items())
                psel = "".join(f"<option value='{k}' {'selected' if k == (ln.get('pose') or '') else ''}>{e(v)}</option>"
                               for k, v in POSE_LABELS.items())
                lines += (f"<div class='ct-line'><select name='w_{i}_{jn}'>{wsel}</select>"
                          f"<input name='t_{i}_{jn}' value='{e(ln['text'])}' maxlength='400' translate='no'>"
                          f"<select name='e_{i}_{jn}' title='Feeling'>{esel}</select><select name='p_{i}_{jn}' title='Gesture'>{psel}</select></div>")
            scenes += (f"<div class='ct-scene'><div class='ct-row'><b><span>Scene</span> <span translate='no'>{i + 1}</span></b>"
                       f"<select name='bg_{i}'>{bgsel}</select></div>{lines}</div>")
        res = j.get("result") or {}
        video = (f"<div class='ct-big'><video controls preload='metadata' src='/auto/cartoon/{jid}/film.mp4'></video></div>"
                 if j["state"] == "done" else _block(j, _state_html(j)))
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'><a href='/auto/cartoon'>Cartoon Studio</a></div>"
                f"<h1 translate='no'>{e(j.get('title') or film['title'])}</h1></div>{_READY}"
                f"<div class='card'>{video}"
                + (f"<div class='muted' style='font-size:13px;margin-top:6px'><span>Saved in</span> <span class='ae-path' translate='no'>"
                   f"{e(res.get('saved') or '')}</span></div>" if res.get("saved") else "")
                + f"</div><div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Change and make again</h2>"
                f"<form method='post' action='/auto/cartoon/{jid}/again' data-dirty-watch "
                f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">{scenes}"
                f"<div class='ct-choices' style='margin-top:8px'><b>Format</b><br>{_format_choice(film['format'])}</div>"
                f"{_voices_choice()}{_captions_choice()}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make it again</button></div></form>"
                f"<details style='margin-top:12px'><summary>The whole story as text</summary>"
                f"<form method='post' action='/auto/cartoon/{jid}/again' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<textarea name='text' rows='18' style='width:100%;font-family:Consolas,monospace;font-size:13px' translate='no'>"
                f"{e(T.to_text(cj.script_of(jid)))}</textarea>"
                f"<input type='hidden' name='format' value='{e(film['format'])}'><input type='hidden' name='captions' value='1'>"
                + ("<input type='hidden' name='voices' value='1'>" if j.get("voices") else "")
                + f"<div style='margin-top:8px'><button>Make it again from this text</button></div></form></details>"
                + (f"<details style='margin-top:8px'><summary>Another language or country</summary>"
                   f"{_adapt_form(T.to_text(cj.script_of(jid)), film['format'], film['title'], film.get('language') or 'en')}</details>"
                   if W.installed() else "")
                + f"<details style='margin-top:8px'><summary>The whole script (JSON)</summary>"
                f"<textarea readonly rows='12' style='width:100%' translate='no'>{e(json.dumps(cj.script_of(jid), ensure_ascii=False, indent=1))}</textarea>"
                f"</details></div>")
        return page("Cartoon Studio", body, _POLL_JS)

    def _story_page(j: dict):
        jid, res = j["id"], j.get("result") or {}
        asked = {"topic": "Topic", "text": "Retelling a text", "adapt": "Retelling a story for another country"}.get(j.get("mode"), "")
        what = str(j.get("topic") or j.get("source") or "")
        head = (f"{CSS}<div class='pagehead'><div class='eyebrow'><a href='/auto/cartoon'>Cartoon Studio</a></div>"
                f"<h1><span>Story:</span> <span translate='no'>{e(j.get('title') or '')}</span></h1>"
                f"<div class='muted' style='font-size:13px'><span>{e(asked)}</span> · <span translate='no'>"
                f"{e(LANG_LABELS.get(j.get('lang'), ''))}</span>" + (f" · <span translate='no'>{e(j['country'])}</span>" if j.get("country") else "")
                + f"</div></div>{_READY}")
        if j["state"] != "done":
            body = (f"<div class='card'>{_block(j, _state_html(j) or '')}"
                    f"<details style='margin-top:8px'><summary class='muted'>What was asked</summary><div class='muted' "
                    f"style='white-space:pre-wrap;font-size:13px' translate='no'>{e(what[:1500])}</div></details></div>")
            return page("Cartoon Studio", head + body, _POLL_JS)
        story = W.story_of(jid)
        fmt = j.get("format") or "vertical"
        note = (f"<div class='callout card' style='margin:8px 0'>The model's story is shorter or simpler than asked: read it and "
                f"add what is missing before making the cartoon.</div>" if res.get("note") else "")
        body = (f"<div class='card'><h2 style='margin-top:0'>The story</h2>{note}"
                f"<div class='muted' style='font-size:13px'>Read it, change what you like (the words, the people, the scenes), then "
                f"make the cartoon. How the text is written: see the help below.</div>{_help()}"
                f"<form method='post' action='/auto/cartoon/new' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<textarea name='text' rows='22' style='width:100%;font-family:Consolas,monospace;font-size:13px' translate='no'>{e(story)}</textarea>"
                f"<div class='ct-choices' style='margin-top:8px'><b>Format</b><br>{_format_choice(fmt)}</div>"
                f"{_voices_choice()}{_captions_choice()}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the cartoon</button></div></form></div>"
                f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Not quite right?</h2>"
                f"<div class='ct-row'><form method='post' action='/auto/cartoon/{jid}/rewrite' style='margin:0' "
                f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<button>Write another version</button></form>{_delete(j)}</div>"
                f"<details style='margin-top:10px'><summary>Another language or country</summary>"
                f"{_adapt_form(story, fmt, j.get('title') or '', j.get('lang') or 'en')}</details>"
                f"<details style='margin-top:8px'><summary class='muted'>What was asked</summary><div class='muted' "
                f"style='white-space:pre-wrap;font-size:13px' translate='no'>{e(what[:1500])}</div></details></div>")
        return page("Cartoon Studio", head + body, _POLL_JS)

    @app.post("/auto/cartoon/write")
    def cartoon_write():
        f = request.form
        about = str(f.get("about") or "").strip()
        mode = f.get("mode") if f.get("mode") == "adapt" else ("text" if len(about) > 280 or about.count("\n") >= 2 else "topic")
        try:
            secs = int(f.get("secs") or 75)
        except ValueError:
            secs = 75
        try:
            if mode == "adapt":
                lang = f.get("lang") or "en"
                title = str(f.get("title") or "").strip()[:50]
                jid = W.new_write("adapt", lang, f.get("format") or "vertical", secs, source=f.get("source") or "",
                                  country=f.get("country") or "", title=(f"{title} ({LANG_LABELS.get(lang, lang)})" if title else ""))
            else:
                jid = W.new_write(mode, f.get("lang") or "en", f.get("format") or "vertical", secs,
                                  topic=about if mode == "topic" else "", source=about if mode == "text" else "",
                                  country=f.get("country") or "")
        except (W.WriterError, vo.VoiceError) as exc:
            return err_page(str(exc), "/auto/cartoon")
        return redirect(f"/auto/cartoon/{jid}")

    @app.post("/auto/cartoon/<jid>/rewrite")
    def cartoon_rewrite(jid):
        j = _job(jid)
        if not j or j.get("kind") != "cartoon_write":
            return redirect("/auto/cartoon")
        try:
            new = W.new_write(j.get("mode") or "topic", j.get("lang") or "en", j.get("format") or "vertical", j.get("secs") or 75,
                              topic=j.get("topic") or "", source=j.get("source") or "", country=j.get("country") or "",
                              title=j.get("title") or "")
        except (W.WriterError, vo.VoiceError) as exc:
            return err_page(str(exc), f"/auto/cartoon/{jid}")
        return redirect(f"/auto/cartoon/{new}")

    @app.post("/auto/cartoon/writer/install")
    def cartoon_writer_install():
        try:
            W.start_install()
        except W.WriterError as exc:
            return err_page(str(exc), "/auto/cartoon")
        return redirect("/auto/cartoon")

    @app.post("/auto/cartoon/writer/cancel")
    def cartoon_writer_cancel():
        W.cancel_install()
        return redirect("/auto/cartoon")

    @app.post("/auto/cartoon/writer/remove")
    def cartoon_writer_remove():
        try:
            W.remove()
        except W.WriterError as exc:
            return err_page(str(exc), "/auto/cartoon")
        return redirect("/auto/cartoon")

    @app.get("/api/cartoon/writer")
    def cartoon_writer_status():
        s = W.status()
        step = _WR_STEP.get(s.get("step"), "")
        try:
            from .i18n import ui_language
            if ui_language() == "ru":
                from .auto_edit_ru import PHRASES
                step = PHRASES.get(step, step)
        except Exception:
            pass
        return jsonify({k: s.get(k) for k in ("state", "done", "total", "detail", "error", "installed")} | {"step": step})

    @app.post("/auto/cartoon/<jid>/again")
    def cartoon_again(jid):
        if not re.fullmatch(_JOB_ID, jid):
            return err_page("No such job.", "/auto/cartoon")
        f = request.form
        script = copy.deepcopy(cj.script_of(jid))
        try:
            if str(f.get("text") or "").strip():           # the story as text, changed
                new = T.parse(f.get("text") or "")
                if not new["scenes"]:
                    raise F.FilmError("The story has no scenes: start each scene with == and its background.")
                old_cast = {(c.get("name") or "").lower(): c for c in (script.get("cast") or {}).values()}
                for k, c in new["cast"].items():           # (the characters keep their looks and voices)
                    prev = old_cast.get((c.get("name") or "").lower())
                    if prev:
                        new["cast"][k] = dict(prev)
                new["format"] = script.get("format") or new["format"]
                script = new
            for i, s in enumerate(script.get("scenes") or []):
                if f.get(f"bg_{i}") in bgs.BACKGROUNDS:
                    s["bg"] = f.get(f"bg_{i}")
                kept = [ln for ln in (s.get("lines") or []) if isinstance(ln, dict) and str(ln.get("text") or "").strip()]
                for jn, ln in enumerate(kept):
                    if f.get(f"t_{i}_{jn}") is not None:
                        ln["text"] = str(f.get(f"t_{i}_{jn}"))[:400]
                    if f.get(f"w_{i}_{jn}") in (script.get("cast") or {}):
                        ln["who"] = f.get(f"w_{i}_{jn}")
                    if f.get(f"e_{i}_{jn}") is not None:
                        ln["emotion"] = f.get(f"e_{i}_{jn}") if f.get(f"e_{i}_{jn}") in ch.EMOTIONS else None
                    if f.get(f"p_{i}_{jn}") is not None:
                        ln["pose"] = f.get(f"p_{i}_{jn}") if f.get(f"p_{i}_{jn}") in ch.POSES else None
                s["lines"] = kept
            new = _make(script, f)
        except (F.FilmError, vo.VoiceError) as exc:
            return err_page(str(exc), f"/auto/cartoon/{jid}")
        return redirect(f"/auto/cartoon/{new}")

    def _job(jid: str) -> dict | None:
        if not re.fullmatch(_JOB_ID, jid):
            return None
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return None
        return j if str(j.get("kind") or "").startswith("cartoon_") else None

    @app.get("/auto/cartoon/<jid>/film.mp4")
    def cartoon_file(jid):
        j = _job(jid)
        p = vo._job_dir(jid) / "film.mp4" if j else None
        if not p or not p.is_file():
            return ("", 404)
        return send_file(p, mimetype="video/mp4", conditional=True, max_age=0)

    @app.post("/auto/cartoon/<jid>/stop")
    def cartoon_stop(jid):
        if _job(jid):
            vo.cancel_job(jid)
        return redirect("/auto/cartoon")

    @app.post("/auto/cartoon/<jid>/retry")
    def cartoon_retry(jid):
        if _job(jid):
            try:
                vo.retry_job(jid)
            except vo.VoiceError as exc:
                return err_page(str(exc), "/auto/cartoon")
        return redirect("/auto/cartoon")

    @app.post("/auto/cartoon/<jid>/delete")
    def cartoon_delete(jid):
        j = _job(jid)
        if j and j["state"] not in ("working", "waiting"):
            try:
                vo.delete_job(jid)
            except vo.VoiceError as exc:
                return err_page(str(exc), "/auto/cartoon")
        return redirect("/auto/cartoon")

    @app.post("/auto/cartoon/<jid>/reveal")
    def cartoon_reveal(jid):
        j = _job(jid)
        saved = Path(str((j or {}).get("result", {}).get("saved") or "")) if j else None
        if saved and saved.is_file():
            from . import auto_edit as ae
            ae.open_path(saved, reveal=True)
        return redirect(f"/auto/cartoon/{jid}" if j else "/auto/cartoon")

    @app.get("/api/cartoon/status")
    def cartoon_status():
        out = {}
        for jid in str(request.args.get("ids") or "").split(",")[:50]:
            j = _job(jid)
            if not j:
                out[jid] = {"state": "gone"}
                continue
            lab = _label(j)
            try:
                from .i18n import ui_language
                if ui_language() == "ru":
                    from .auto_edit_ru import PHRASES
                    lab = PHRASES.get(lab, lab)
            except Exception:
                pass
            out[jid] = {"state": j["state"], "progress": float(j.get("progress") or 0), "step": lab}
        return jsonify(out)


_READY = ("<div class='callout card cl-ready' data-ready hidden><b>Ready.</b> <span>Refresh the page to see it.</span> "
          "<a class='btn btn2' href='javascript:location.reload()'>Refresh</a></div>")
_POLL_JS = ("(()=>{let dirty=false;document.querySelectorAll('form').forEach(f=>{f.addEventListener('input',()=>dirty=true);"
            "f.addEventListener('change',()=>dirty=true)});const live=()=>[...document.querySelectorAll('[data-job]')]"
            ".filter(x=>['working','waiting'].includes(x.dataset.state));if(!live().length)return;"
            "const tick=async()=>{const js=live();if(!js.length)return;let r;try{r=await (await fetch('/api/cartoon/status?ids='+"
            "js.map(x=>x.dataset.job).join(','))).json()}catch(e){setTimeout(tick,5000);return}let changed=false;"
            "js.forEach(x=>{const s=r[x.dataset.job];if(!s)return;if(s.state!==x.dataset.state){changed=true;x.dataset.state=s.state;return}"
            "const b=x.querySelector('[data-bar]');if(b)b.style.width=Math.round(100*(s.progress||0))+'%';"
            "const t=x.querySelector('[data-step]');if(t&&s.step)t.textContent=s.step});"
            "if(changed){if(!dirty&&![...document.querySelectorAll('video')].some(v=>!v.paused)){location.reload();return}"
            "const n=document.querySelector('[data-ready]');if(n)n.hidden=false}setTimeout(tick,3000)};setTimeout(tick,3000)})();"
            "(()=>{if(!document.getElementById('wrInstall'))return;const t=async()=>{let x;try{x=await (await fetch('/api/cartoon/writer',"
            "{cache:'no-store'})).json()}catch(e){setTimeout(t,4000);return}if(x.state!=='running'){location.reload();return}"
            "const b=document.getElementById('wrBar');if(b&&x.total)b.style.width=Math.max(3,Math.round(100*x.done/x.total))+'%';"
            "const s=document.getElementById('wrStep');if(s)s.textContent=x.step||'';const d=document.getElementById('wrDetail');"
            "if(d)d.textContent=x.detail||'';setTimeout(t,1500)};setTimeout(t,1500)})();")
