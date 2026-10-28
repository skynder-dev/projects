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
from .cartoon import bgs, chars as ch, film as F, jobs as cj, stories

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
         "checking": "Checking the film…"}
BG_LABELS = {"city": "City street", "office": "Office", "city_hall": "City hall", "road": "Road", "bank": "Bank",
             "night": "Night street", "board": "Board (schemes, charts)", "paper": "Paper"}
EMO_LABELS = {"": "—", "neutral": "calm", "happy": "happy", "angry": "angry", "sad": "sad", "surprised": "surprised",
              "sly": "sly", "worried": "worried"}
POSE_LABELS = {"": "—", "talk": "talking", "explain": "explaining", "point": "pointing", "point_up": "finger up",
               "shrug": "shrugging", "cross": "arms crossed", "think": "thinking", "wave": "waving", "hands_up": "hands up",
               "count": "rubbing hands", "present": "presenting", "facepalm": "hand to face", "fist": "fist",
               "sneaky": "sneaky", "idle": "standing"}
STORY_LABELS = {"road_contract": "How a City Loses Millions on a Simple Road Contract (example, 10 scenes)"}


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

    def _film_row(j: dict) -> str:
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
        return (f"<form method='post' action='/auto/cartoon/{j['id']}/delete' style='margin:0' onsubmit=\"return confirm(window.ME_L?"
                f"ME_L('Delete it? The film saved in the folder stays.'):'Delete it? The film saved in the folder stays.')\">"
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

    @app.get("/auto/cartoon")
    def cartoon_home():
        rows = "".join(_film_row(j) for j in cj.films())
        stories_html = "".join(f"<label><input type='radio' name='story' value='{k}' {'checked' if n == 0 else ''}> {e(v)}</label>"
                               for n, (k, v) in enumerate(STORY_LABELS.items()))
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Cartoon Studio</h1>"
                f"<div class='lead'>A short 2D cartoon made by MediaEngine: its own characters (the same in every episode), "
                f"scenes, schemes of money and charts, the characters' voices and captions - one MP4. Change any line, "
                f"background or feeling and make it again.</div></div>{_READY}"
                f"<div class='card'><h2 style='margin-top:0'>New cartoon</h2>"
                f"<form method='post' action='/auto/cartoon/new' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<b>Story</b><div class='ct-choices' style='margin:4px 0 8px'>{stories_html}"
                f"<label><input type='radio' name='story' value='own'> My script (JSON)</label></div>"
                f"<textarea name='script' rows='6' style='width:100%' placeholder='Paste a script here (only for \"My script\")'></textarea>"
                f"<div class='ct-choices' style='margin-top:8px'><b>Format</b><br>{_format_choice('vertical')}</div>"
                f"{_voices_choice()}{_captions_choice()}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the cartoon</button></div></form>"
                f"<div class='muted' style='font-size:13px;margin-top:10px'>Coming next: a script written from a topic, a text "
                f"or a video, in English, Russian and Romanian.</div></div>"
                + (f"<div class='card' id='films' style='margin-top:14px'><h2 style='margin-top:0'>Cartoons</h2>{rows}</div>" if rows else ""))
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
            if f.get("story") == "own":
                try:
                    script = json.loads(f.get("script") or "")
                except ValueError:
                    raise F.FilmError("The script is not valid JSON.")
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
                f"<details style='margin-top:12px'><summary>The whole script (JSON)</summary>"
                f"<textarea readonly rows='12' style='width:100%' translate='no'>{e(json.dumps(cj.script_of(jid), ensure_ascii=False, indent=1))}</textarea>"
                f"</details></div>")
        return page("Cartoon Studio", body, _POLL_JS)

    @app.post("/auto/cartoon/<jid>/again")
    def cartoon_again(jid):
        if not re.fullmatch(_JOB_ID, jid):
            return err_page("No such job.", "/auto/cartoon")
        f = request.form
        script = copy.deepcopy(cj.script_of(jid))
        try:
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
            "const n=document.querySelector('[data-ready]');if(n)n.hidden=false}setTimeout(tick,3000)};setTimeout(tick,3000)})();")
