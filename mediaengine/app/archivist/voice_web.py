"""The Voice-over page (Auto Edit -> Voice-over): install the add-on, text -> voice, captions, voice onto a video."""
from __future__ import annotations

import json
from pathlib import Path

from flask import jsonify, redirect, request, send_file

from . import textfx as tf
from . import voice as vo

_INSTALL_STEP = {"checking": "Checking the PC…", "packages": "Downloading and installing the add-on's Python parts (about 3 GB)…",
                 "models": "Downloading the voice models (about 5 GB)…", "checking_addon": "Starting the add-on for a test…"}
_JOB_STEP = {"starting": "Starting…", "loading": "Loading the voice model…", "speaking": "Speaking…",
             "joining": "Joining the parts…", "listening": "Listening to check every word…", "finishing": "Finishing the sound…",
             "reading": "Reading the sound of the video…", "video": "Making the video…", "checking": "Checking the video…"}
_KIND = {"voiceover": "Voice-over", "captions": "Captions for a video", "dub": "Voice-over on a video",
         "render": "Video with text and captions"}
_STATE = {"waiting": "Waiting", "working": "Working", "done": "Ready", "failed": "Failed",
          "interrupted": "Interrupted (MediaEngine was closed): it is made again at the next start"}
_FILES = {"voice.wav": "audio/wav", "captions.srt": "text/plain", "video.mp4": "video/mp4"}
_LANGS = [("", "Detect by itself"), ("en", "English"), ("ru", "Русский"), ("es", "Español"), ("de", "Deutsch"),
          ("fr", "Français"), ("it", "Italiano"), ("pt", "Português"), ("uk", "Українська")]   # names in their own language

PAGE_CSS = """<style>
.vo-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.vo-voices label{display:block;margin:4px 0}
.vo-job{border-top:1px solid #2a2f37;padding:12px 0}
.vo-job:first-child{border-top:0}
.vo-sub{font-size:13px}
textarea.vo-text{width:100%;min-height:130px;font:15px/1.45 system-ui;box-sizing:border-box;background:#0e131a;color:#fff;
border:1px solid #364150;border-radius:9px;padding:9px 10px;outline:none}
textarea.vo-text:focus{border-color:#5b86d8;box-shadow:0 0 0 3px #4a82f420}
.vo-job form.vo-del{display:inline;margin:0}
input.vo-wide{width:100%;max-width:640px;box-sizing:border-box}
.vo-styles label{display:block;margin:3px 0}
.vo-trow{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:6px 0}
.vo-trow input[name=t_text]{flex:1 1 260px;min-width:200px}
.vo-cues{max-height:420px;overflow:auto;border:1px solid #2a2f37;border-radius:9px;padding:6px 10px}
.vo-cue{display:flex;gap:8px;align-items:center;margin:4px 0}
.vo-cue input{flex:1}
.vo-prev img{max-width:100%;max-height:560px;border-radius:8px;display:block;margin-top:8px}
.vo-edit{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,380px);gap:16px;align-items:start}
@media (max-width:900px){.vo-edit{grid-template-columns:1fr}}
</style>"""


def register(app, page, err_page, e, human_bytes):

    def _ru() -> bool:
        try:
            from .i18n import ui_language
            return ui_language() == "ru"
        except Exception:
            return False

    def _gb(n) -> str:
        return f"{(int(n or 0)) / 1e9:.1f} GB"

    def _install_card(s: dict) -> str:
        why = vo.why_not_install()
        if s["state"] == "running":
            pct = int(100 * s["done"] / s["total"]) if s.get("total") else 0
            return (f"<div class='card' id='voInstall'><h2 style='margin-top:0'>Installing the voice add-on</h2>"
                    f"<div class='ae-bar'><i id='voBar' style='width:{pct if s.get('step') == 'models' else 5}%'></i></div>"
                    f"<div style='margin-top:8px'><span id='voStep'>{e(_INSTALL_STEP.get(s.get('step'), ''))}</span></div>"
                    f"<div class='muted ae-path vo-sub' id='voDetail' translate='no'>{e(s.get('detail') or '')}</div>"
                    f"<div class='muted vo-sub' style='margin-top:6px'>This takes from a few minutes to an hour, depending on the "
                    f"internet. You can use MediaEngine meanwhile; closing it stops the installation (it continues "
                    f"where it stopped when you press Install again).</div>"
                    f"<form method='post' action='/auto/voice/install/cancel' style='margin-top:10px'><button class='btn2'>Cancel</button></form></div>")
        if s.get("installed"):
            m = s.get("manifest") or {}
            where = (f"<span>the graphics card</span> <span translate='no'>{e(m.get('gpu') or '')}</span>" if m.get("cuda")
                     else "<span>the processor (slow)</span>")
            return (f"<div class='card'><div><b>The voice add-on is installed.</b> <span>It works on</span> {where}. "
                    f"<span class='muted'>Size:</span> <span>{e(_gb(m.get('bytes')))}</span></div>"
                    f"<details style='margin-top:8px'><summary class='muted'>Remove the add-on</summary>"
                    f"<div class='muted vo-sub'>Frees the disk space. The voice-overs and videos made with it stay.</div>"
                    f"<form method='post' action='/auto/voice/remove' style='margin-top:8px' "
                    f"onsubmit=\"return confirm(window.ME_L?ME_L('Remove the voice add-on?'):'Remove the voice add-on?')\">"
                    f"<button class='btn2'>Remove the add-on</button></form></details></div>")
        gpu = s.get("nvidia") or ""
        gpu_line = (f"<div><span>Graphics card:</span> <b translate='no'>{e(gpu)}</b> <span>— the voice is made on it (fast).</span></div>"
                    if gpu else "<div>No NVIDIA graphics card was found: the voice is made on the processor (slow: about a "
                                "minute for every sentence).</div>")
        err = ""
        if s["state"] == "failed":
            err = f"<div class='errbox' style='margin-bottom:10px'>{e(s.get('error') or '')}</div>"
        again = "Try again" if s["state"] == "failed" else "Install the voice add-on"
        cpu_btn = ""
        if s["state"] == "failed" and s.get("nvidia"):     # the graphics card version did not start: the processor one
            cpu_btn = ("<form method='post' action='/auto/voice/install' style='display:inline;margin-left:8px'>"
                       "<input type='hidden' name='cpu' value='1'><button class='btn2'>Install for the processor (slower)</button></form>")
        if s.get("needs_reinstall"):
            err += "<div class='errbox' style='margin-bottom:10px'>This MediaEngine uses another Python: install the add-on again.</div>"
        if why:
            return f"<div class='card'><div class='errbox'>{e(why)}</div></div>"
        low = s.get("free", 0) < vo.NEED_FREE
        return (f"<div class='card'>{err}<div><b>The voice add-on is not installed.</b></div>"
                f"<div style='margin-top:6px'>It is downloaded once: about 8 GB (the add-on's Python parts and two models: "
                f"VoxCPM2 for the voice, Whisper for checking the words and for captions). It goes into the data folder:</div>"
                f"<div class='ae-path' translate='no'>{e(str(vo.ROOT))}</div>"
                f"<div class='muted vo-sub' style='margin-top:6px'>MediaEngine goes online for it only when you press the button "
                f"(pypi.org, download.pytorch.org, huggingface.co). Free and open models; nothing is sent anywhere.</div>"
                f"<div style='margin-top:8px'>{gpu_line}</div>"
                f"<div class='muted vo-sub'><span>Free space there:</span> <span>{e(_gb(s.get('free')))}</span></div>"
                + ("<div class='errbox' style='margin-top:8px'>Not enough free space: about 20 GB are needed while installing.</div>" if low else "")
                + f"<div style='margin-top:12px'><form method='post' action='/auto/voice/install' style='display:inline' "
                  f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                  f"<button class='ae-big'>{again}</button></form>{cpu_btn}</div></div>")

    def _recent_reels(limit: int = 12) -> list[str]:
        """The reels saved last (that are still there): one click instead of typing a path."""
        from .db import db
        out, seen = [], set()
        try:
            with db() as con:
                rows = con.execute("SELECT path FROM ae_exports ORDER BY id DESC LIMIT 80").fetchall()
        except Exception:
            rows = []
        for r in rows:
            p = str(r["path"] or "")
            if not p or p.lower() in seen:
                continue
            seen.add(p.lower())
            if Path(p).is_file():
                out.append(p)
                if len(out) >= limit:
                    break
        return out

    def _reel_select() -> str:
        reels = _recent_reels()
        if not reels:
            return ""
        opts = "".join(f"<option value='{e(p)}' translate='no'>{e(Path(p).name)}</option>" for p in reels)
        return (f"<div class='vo-row' style='margin-top:6px'><span>or a reel saved lately:</span>"
                f"<select data-fill><option value=''>—</option>{opts}</select></div>")

    def _lang_options() -> str:
        return "".join(f"<option value='{c}'" + (" translate='no'" if c else "") + f">{e(n)}</option>" for c, n in _LANGS)

    def _voice_form() -> str:
        radios = "".join(
            f"<label><input type='radio' name='voice' value='{k}'{' checked' if k == vo.DEFAULT_VOICE else ''}> {e(v['label'])}</label>"
            for k, v in vo.VOICES.items())
        langs = _lang_options()
        return (f"<div class='card'><h2 style='margin-top:0'>New voice-over</h2>"
                f"<form method='post' action='/auto/voice/new' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<textarea class='vo-text' name='text' maxlength='{vo.MAX_TEXT}' required placeholder='The text to be said…'></textarea>"
                f"<div class='muted vo-sub'>Write it the way it is said: short sentences, commas and dots where the pauses are.</div>"
                f"<div class='vo-voices' style='margin-top:10px'><b>Voice</b>{radios}</div>"
                f"<div data-for='describe' hidden style='margin:6px 0 0 22px'><input class='vo-wide' name='description' maxlength='400' "
                f"placeholder='For example: a calm man in his forties with a deep, warm voice, slow pace'></div>"
                f"<div data-for='own' hidden style='margin:6px 0 0 22px'><div class='vo-row'><input class='vo-wide' name='ref_path' "
                f"placeholder='The recording: 5-30 seconds of one person speaking, e.g. D:\\Voice\\anna.wav'>"
                f"<button type='button' class='btn2' data-pick='audio'>Choose…</button></div>"
                f"<input class='vo-wide' name='ref_text' maxlength='1000' style='margin-top:6px' "
                f"placeholder='The exact words said in the recording (optional: the voice is copied more closely)'>"
                f"<div class='muted vo-sub'>Use only the voice of a person who agreed to it.</div></div>"
                f"<div class='vo-row' style='margin-top:10px'><span>Language of the text</span><select name='language'>{langs}</select></div>"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the voice-over</button> "
                f"<span class='muted vo-sub' data-msg></span></div></form></div>")

    def _captions_form() -> str:
        langs = _lang_options()
        return (f"<div class='card'><h2 style='margin-top:0'>Captions for a video</h2>"
                f"<div class='muted vo-sub'>The speech in your video is turned into captions with the words timed to it and "
                f"burned into a copy of the video. The video itself is only read.</div>"
                f"<form method='post' action='/auto/voice/captions' style='margin-top:8px'>"
                f"<div class='vo-row'><input class='vo-wide' name='path' required placeholder='The video, e.g. D:\\Videos\\talk.mp4'>"
                f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                f"<div class='vo-row' style='margin-top:8px'><span>Language of the speech</span><select name='language'>{langs}</select></div>"
                f"{_style_controls(tf.options())}{_quick_texts()}"
                f"<div style='margin-top:10px'><button>Make captions</button> <span class='muted vo-sub' data-msg></span></div></form></div>")

    def _style_controls(o: dict, captions: bool = True) -> str:
        """Captions style (when there are captions), color, size and where the captions go."""
        styles = "".join(f"<label><input type='radio' name='style' value='{k}'{' checked' if k == o['style'] else ''}> "
                         f"{e(v['label'])}</label>" for k, v in tf.STYLES.items())
        colors = "".join(f"<option value='{k}'{' selected' if k == o['color'] else ''}>{e(v[0])}</option>"
                         for k, v in tf.COLORS.items())
        sizes = "".join(f"<option value='{k}'{' selected' if k == o['size'] else ''}>{e(v[0])}</option>"
                        for k, v in tf.SIZES.items())
        pos = "".join(f"<option value='{k}'{' selected' if k == o['position'] else ''}>{e(v)}</option>"
                      for k, v in tf.POSITIONS.items())
        return ((f"<div class='vo-styles' style='margin-top:8px'><b>Look of the captions</b>{styles}</div>" if captions else "")
                + f"<div class='vo-row' style='margin-top:6px'><span>Color</span><select name='color'>{colors}</select>"
                  f"<span>Size</span><select name='size'>{sizes}</select>"
                + (f"<span>Captions</span><select name='position'>{pos}</select>" if captions else "") + "</div>")

    def _num(v) -> str:
        """Seconds as typed back into a field: 3, 2.5, 1:05, 1:05.5."""
        if v is None or v == "":
            return ""
        x = round(float(v), 1)
        if x < 60:
            return f"{x:g}"
        m = int(x // 60)
        sec = f"{x - 60 * m:04.1f}"
        return f"{m}:{sec[:-2] if sec.endswith('.0') else sec}"

    def _text_row(t: dict) -> str:
        where = "".join(f"<option value='{k}'{' selected' if k == (t.get('where') or 'top') else ''}>{e(v)}</option>"
                        for k, v in tf.POSITIONS.items())
        look = "".join(f"<option value='{k}'{' selected' if k == (t.get('look') or 'banner') else ''}>{e(v)}</option>"
                       for k, v in tf.LOOKS.items())
        start = "end" if t.get("at_end") else _num(t.get("start"))
        end = "" if t.get("at_end") else _num(t.get("end"))
        return (f"<div class='vo-trow'><input name='t_text' maxlength='{tf.TEXT_MAX}' value='{e(t.get('text') or '')}' "
                f"placeholder='The text, e.g. 3 ways to fly cheaper'>"
                f"<span>from</span><input name='t_start' size='4' value='{e(start)}' placeholder='0'>"
                f"<span>to</span><input name='t_end' size='4' value='{e(end)}' placeholder='3'>"
                f"<select name='t_where'>{where}</select><select name='t_look'>{look}</select>"
                f"<button type='button' class='btn2' data-trow-del title='Remove this text'>×</button></div>")

    def _text_rows(texts: list[dict], header: bool = True) -> str:
        rows = "".join(_text_row(t) for t in texts) or _text_row({"start": 0, "end": 3})
        return (f"<div class='vo-texts' style='margin-top:10px'>{'<b>Text on the video</b>' if header else ''}"
                f"<div class='muted vo-sub'>From and to: seconds of the finished video (2.5 or 0:12). “end” in “from” = the "
                f"last 3 seconds; an empty “to” = 3 seconds later. An empty text is left out.</div>"
                f"<div data-trows>{rows}</div><template data-trow-tpl>{_text_row({})}</template>"
                f"<button type='button' class='btn2' data-trow-add>Add a text</button></div>")

    def _preview_box() -> str:
        return (f"<div class='vo-prev card' style='margin:0'><b>Preview</b>"
                f"<div class='muted vo-sub'>One picture of the finished video, with the captions and texts as they will be.</div>"
                f"<div class='vo-row' style='margin-top:6px'><span>At</span><input name='at' value='1' size='4'><span>s</span>"
                f"<button type='button' class='btn2' data-preview>Show</button></div>"
                f"<div class='muted vo-sub' data-pmsg></div><img data-pimg alt='' hidden></div>")

    def _quick_texts() -> str:
        return (f"<div class='vo-row' style='margin-top:6px'><span>Title at the top (first 3 s)</span>"
                f"<input name='hook' maxlength='{tf.TEXT_MAX}' size='34' placeholder='optional'></div>"
                f"<div class='vo-row' style='margin-top:6px'><span>Text at the end (last 3 s)</span>"
                f"<input name='end_text' maxlength='{tf.TEXT_MAX}' size='34' placeholder='optional, e.g. Follow for more'></div>")

    def _text_form() -> str:
        """Text on any video - no add-on needed."""
        o = tf.options()
        return (f"<div class='card'><h2 style='margin-top:0'>Text on a video</h2>"
                f"<div class='muted vo-sub'>Titles and lines of text on your video, at the moments you choose. The video itself "
                f"is only read; a copy with the text is made.</div>"
                f"<form method='post' action='/auto/text/new' style='margin-top:8px' data-textform>"
                f"<div class='vo-edit'><div>"
                f"<div class='vo-row'><input class='vo-wide' name='video' required placeholder='The video, e.g. D:\\Exports\\reel.mp4'>"
                f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                f"{_text_rows([], header=False)}{_style_controls(o, captions=False)}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the video</button> "
                f"<span class='muted vo-sub' data-msg></span></div></div>{_preview_box()}</div></form></div>")

    def _job_html(j: dict) -> str:
        jid, st, res = j["id"], j["state"], j.get("result") or {}
        head = (f"<div class='vo-row'><b>{e(_KIND.get(j.get('kind'), ''))}</b><span class='muted' translate='no'>{e(j.get('title') or '')}</span>"
                f"<span class='muted vo-sub' translate='no'>{e(str(j.get('created_at') or '')[:16].replace('T', ' '))}</span></div>")
        body = ""
        if st == "working":
            step = str(j.get("step") or "")
            key, _, part = step.partition(" ")
            label = e(_JOB_STEP.get(key, "Working…"))
            if part:
                label += f" <span translate='no'>{e(part)}</span>"
            body = (f"<div class='ae-bar' style='margin-top:6px'><i style='width:{int(100 * float(j.get('progress') or 0))}%'></i></div>"
                    f"<div class='muted vo-sub'>{label}</div>")
        elif st == "interrupted" and j.get("resumed"):
            body = (f"<div class='errbox' style='margin-top:6px'>Interrupted again (MediaEngine was closed).</div>"
                    f"<form method='post' action='/auto/voice/{jid}/retry' style='margin-top:6px'><button>Try again</button></form>")
        elif st in ("waiting", "interrupted"):
            body = f"<div class='muted vo-sub'>{e(_STATE[st])}</div>"
        elif st == "failed":
            body = (f"<div class='errbox' style='margin-top:6px'>{e(res.get('error') or 'Failed')}</div>"
                    f"<form method='post' action='/auto/voice/{jid}/retry' style='margin-top:6px'><button class='btn2'>Try again</button></form>")
        elif st == "done" and j.get("kind") == "voiceover":
            n, bad = int(res.get("words") or 0), int(res.get("word_errors") or 0)
            check = ("<span>Every word was said (checked by listening).</span>" if bad == 0 else
                     f"<span>Words not clear when listening:</span> <b translate='no'>{bad}</b> <span>of</span> <span translate='no'>{n}</span>")
            dev = "the graphics card" if res.get("device") == "cuda" else "the processor"
            body = (f"<audio controls preload='none' src='/auto/voice/{jid}/file/voice.wav' style='width:100%;max-width:640px;margin-top:6px'></audio>"
                    f"<div class='muted vo-sub'><span translate='no'>{e(str(res.get('seconds') or ''))}</span> <span>s</span> · {check} · "
                    f"<span>made on</span> <span>{dev}</span></div>"
                    f"<div class='vo-row' style='margin-top:6px'><a class='btn btn2' href='/auto/voice/{jid}/file/voice.wav?download=1'>Download WAV</a>"
                    f"<a class='btn btn2' href='/auto/voice/{jid}/file/captions.srt?download=1'>Download captions (SRT)</a><!--actions--></div>"
                    f"<details style='margin-top:8px'><summary>Put it on a video</summary>"
                    f"<form method='post' action='/auto/voice/{jid}/dub' style='margin-top:8px'>"
                    f"<div class='vo-row'><input class='vo-wide' name='video' required placeholder='The video, e.g. D:\\Exports\\reel.mp4'>"
                    f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                    f"<label style='display:block;margin-top:6px'><input type='checkbox' name='keep_sound' value='1' checked> "
                    f"Keep the video's own sound (quieter while the voice speaks)</label>"
                    f"<label style='display:block'><input type='checkbox' name='captions' value='1' checked> Captions with the words</label>"
                    f"<div class='vo-row' style='margin-top:6px'><span>The voice starts at</span><input name='start' value='0.3' size='4'><span>s</span></div>"
                    f"{_style_controls(tf.options())}{_quick_texts()}"
                    f"<div style='margin-top:8px'><button>Make the video</button></div></form></details>")
        elif st == "done":
            body = (f"<video controls preload='metadata' src='/auto/voice/{jid}/file/video.mp4' style='max-width:360px;max-height:420px;margin-top:6px'></video>"
                    f"<div class='muted vo-sub'><span translate='no'>{e(str(res.get('seconds') or ''))}</span> <span>s</span> · "
                    f"<span>checked: plays to the end</span></div>"
                    + (f"<div class='muted vo-sub'><span>Saved:</span> <span class='ae-path' translate='no'>{e(res['saved'])}</span></div>"
                       if res.get("saved") else "")
                    +
                    f"<div class='vo-row' style='margin-top:6px'><a class='btn' href='/auto/voice/{jid}/edit'>Edit text and captions</a>"
                    f"<form method='post' action='/auto/voice/{jid}/reveal' style='margin:0'>"
                    f"<button class='btn2'>Show in folder</button></form>"
                    + (f"<a class='btn btn2' href='/auto/voice/{jid}/file/captions.srt?download=1'>Download captions (SRT)</a>" if (res.get("files") or {}).get("srt") else "")
                    + "<!--actions--></div>")
        delete = ("" if st == "working" else
                  f"<form method='post' action='/auto/voice/{jid}/delete' class='vo-del' "
                  f"onsubmit=\"return confirm(window.ME_L?ME_L('Delete it?'):'Delete it?')\"><button class='btn2'>Delete</button></form>")
        if delete and "<!--actions-->" in body:
            body = body.replace("<!--actions-->", delete)
        elif delete:
            body += f"<div class='vo-row' style='margin-top:6px'>{delete}</div>"
        return f"<div class='vo-job' id='j-{jid}' data-state='{st}'>{head}{body}</div>"

    @app.get("/auto/voice")
    def voice_page():
        s = vo.status()
        jobs = vo.list_jobs()
        parts = [_install_card(s)]
        if s.get("installed"):
            parts += [_voice_form(), _captions_form()]
        parts.append(_text_form())
        if jobs:
            parts.append("<div class='card' id='voJobs'><h2 style='margin-top:0'>Made</h2>" + "".join(_job_html(j) for j in jobs) + "</div>")
        body = ("<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Voice-over</h1>"
                "<div class='lead'>A text read by a voice, with captions timed to the words; captions and text for your own videos.</div></div>"
                + "".join(parts) + "<div class='row' id='voBack' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
        steps = json.dumps({**_INSTALL_STEP})
        script = (
            "let dirty=false;document.addEventListener('input',ev=>{if(ev.target.closest('form'))dirty=true});"
            "document.addEventListener('change',ev=>{const sl=ev.target.closest('select[data-fill]');if(!sl||!sl.value)return;"
            "const i=sl.closest('form').querySelector('input[name=video],input[name=path]');if(i){i.value=sl.value;dirty=true}});"
            "document.querySelectorAll('input[name=voice]').forEach(r=>r.addEventListener('change',()=>{"
            "document.querySelectorAll('[data-for]').forEach(d=>{d.hidden=!document.querySelector('input[name=voice][value='+d.dataset.for+']:checked')})}));"
            "document.addEventListener('click',async ev=>{const b=ev.target.closest('[data-pick]');if(!b)return;const f=b.closest('form'),m=f.querySelector('[data-msg]');"
            "if(m)m.textContent=window.ME_L?ME_L('A Windows window is open — it may be behind this window.'):'A Windows window is open — it may be behind this window.';"
            "try{const r=await fetch('/api/auto/pick-voice-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:b.dataset.pick})});"
            "const x=await r.json();if(x.path){b.parentNode.querySelector('input').value=x.path;dirty=true;if(m)m.textContent=''}else if(m)m.textContent=x.error||''}catch(err){}});"
            "const ST=" + steps + ";"
            "let sig=null;async function poll(){try{const r=await fetch('/api/voice/status',{cache:'no-store'});const x=await r.json();"
            "const now=JSON.stringify([x.install.state,x.install.installed,x.jobs.map(j=>j.id+j.state)]);"
            # a finished job: the page is shown again - but never over something being typed (only the list is renewed then)
            "if(sig!==null&&now!==sig){if(!dirty){location.reload();return}"
            "try{const h=await (await fetch('/auto/voice',{cache:'no-store'})).text();const n=new DOMParser().parseFromString(h,'text/html').getElementById('voJobs');"
            "const o=document.getElementById('voJobs');const busyIn=o&&(o.contains(document.activeElement)||[...o.querySelectorAll('details[open] input')].some(i=>i.value&&i.name!=='start'));"
            "if(n&&o&&!busyIn)o.replaceWith(n);"
            "else if(n){const back=document.getElementById('voBack');if(back)back.before(n)}}catch(err){}}sig=now;"
            "const bar=document.getElementById('voBar');if(bar&&x.install.state==='running'){"
            "bar.style.width=(x.install.step==='models'&&x.install.total?Math.round(100*x.install.done/x.install.total):5)+'%';"
            "const s=document.getElementById('voStep'),tx=ST[x.install.step]||'';s.textContent=window.ME_L?ME_L(tx):tx;"
            "document.getElementById('voDetail').textContent=x.install.detail||''}"
            "for(const j of x.jobs){if(j.state!=='working')continue;const el=document.getElementById('j-'+j.id);"
            "if(el){const i=el.querySelector('.ae-bar i');if(i)i.style.width=Math.round(100*j.progress)+'%'}}"
            "}catch(err){}const busy=document.querySelector('#voInstall,[data-state=working],[data-state=waiting]');setTimeout(poll,busy?1500:15000)}"
            "poll();")
        return page("Voice-over", PAGE_CSS + body, script + _EDIT_JS)

    @app.get("/api/voice/status")
    def voice_status():
        s = vo.status()
        jobs = []
        for j in vo.list_jobs(20):
            jobs.append({"id": j["id"], "state": j["state"], "progress": float(j.get("progress") or 0)})
        return jsonify({"install": {k: s.get(k) for k in ("state", "step", "done", "total", "detail", "error", "installed")},
                        "jobs": jobs})

    @app.post("/auto/voice/install")
    def voice_install():
        try:
            vo.start_install(cpu=request.form.get("cpu") == "1")
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/install/cancel")
    def voice_install_cancel():
        vo.cancel_install()
        return redirect("/auto/voice")

    @app.post("/auto/voice/remove")
    def voice_remove():
        try:
            vo.remove_addon()
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/new")
    def voice_new():
        f = request.form
        try:
            vo.new_voiceover(f.get("text", ""), f.get("voice", ""), f.get("description", ""), f.get("ref_path", ""),
                             f.get("ref_text", ""), f.get("language", ""))
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/captions")
    def voice_captions():
        f = request.form
        try:
            vo.new_captions(f.get("path", ""), f.get("language", ""), f.get("position", "bottom"), opts=_opts(f),
                            texts=tf.hook_and_end(f.get("hook", ""), f.get("end_text", "")))
        except (vo.VoiceError, tf.TextError) as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/<jid>/dub")
    def voice_dub(jid):
        f = request.form
        try:
            vo.new_dub(jid, f.get("video", ""), keep_sound=f.get("keep_sound") == "1", captions=f.get("captions") == "1",
                       position=f.get("position", "bottom"), start_s=f.get("start", "0.3"), opts=_opts(f),
                       texts=tf.hook_and_end(f.get("hook", ""), f.get("end_text", "")))
        except (vo.VoiceError, tf.TextError) as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    def _opts(f) -> dict:
        return tf.options(f.get("style"), f.get("color"), f.get("size"), f.get("position"))

    def _edited_cues(f, base: dict) -> list[dict]:
        """The captions of the editor: unchanged ones regrouped for the chosen style; edited ones keep their time."""
        if f.get("captions_on") != "1":
            return []
        src = base.get("cues") or []
        texts = f.getlist("c_text")
        if len(texts) != len(src):                # the page was made for other captions: keep them as they were
            texts = [" ".join(w["w"] for w in c["words"]) for c in src]
        edited = any(" ".join(t.split()) != " ".join(w["w"] for w in c["words"]) for t, c in zip(texts, src))
        if not edited:                              # untouched: grouped the way the chosen style shows words
            words = [w for c in src for w in c["words"]]
            return vo.style_cues(words, _opts(f))
        out = []
        for t, c in zip(texts, src):
            nc = tf.retime(c, t)
            if nc:
                out.append(nc)
        return out

    def _payload(f, base: dict | None) -> dict:
        """Everything a render (or its preview) needs, from the editor or the text form."""
        texts = tf.parse_texts(tf.rows_from_form(f))
        if base:
            return {"video": base["video"], "cues": _edited_cues(f, base), "opts": _opts(f), "texts": texts,
                    "voice_from": base.get("voice_from") or "", "start_s": base.get("start_s") or 0.0,
                    "keep_sound": base.get("keep_sound", True), "title": base.get("title") or ""}
        return {"video": f.get("video", ""), "cues": [], "opts": _opts(f), "texts": texts, "voice_from": "",
                "start_s": 0.0, "keep_sound": True, "title": ""}

    @app.post("/auto/text/new")
    def text_new():
        try:
            pl = _payload(request.form, None)
            vo.new_render(pl["video"], [], pl["opts"], pl["texts"])
        except (vo.VoiceError, tf.TextError) as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/api/text/preview")
    def text_preview():
        f = request.form
        try:
            base = vo.editor_base(f["jid"]) if f.get("jid") else None
            pl = _payload(f, base)
            at = float(str(f.get("at") or "1").replace(",", ".") or 1)
            pic = vo.preview_frame(pl["video"], pl["cues"], pl["opts"], pl["texts"], offset=pl["start_s"], at=at,
                                   voice_from=pl["voice_from"])
        except (vo.VoiceError, tf.TextError) as exc:
            return jsonify({"error": str(exc)})
        except Exception:                              # a picture is a convenience: never a server error page
            return jsonify({"error": "The picture could not be made."})
        return jsonify({"url": f"/api/text/preview/{pic.parent.name}.jpg"})

    @app.get("/api/text/preview/<name>.jpg")
    def text_preview_file(name):
        import re as _re
        p = vo.PREVIEWS / name / "frame.jpg"
        if not _re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", name) or not p.is_file():
            return "not found", 404
        return send_file(p, mimetype="image/jpeg", max_age=0)

    @app.get("/auto/voice/<jid>/edit")
    def voice_edit(jid):
        try:
            base = vo.editor_base(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        o = base["opts"]
        cues = base.get("cues") or []
        rows = "".join(f"<div class='vo-cue'><span class='muted vo-sub' translate='no'>{e(_num(round(c['s'] + base['start_s'], 1)))}</span>"
                       f"<input name='c_text' value='{e(' '.join(w['w'] for w in c['words']))}' maxlength='200'></div>"
                       for c in cues)
        cap = ""
        if cues:
            cap = (f"<label style='display:block;margin-top:8px'><input type='checkbox' name='captions_on' value='1'"
                   f"{' checked' if base.get('captions_on', True) else ''}> Captions with the words</label>"
                   f"<div class='muted vo-sub'>Fix a word right in its line; an emptied line is left out. The times stay.</div>"
                   f"<div class='vo-cues'>{rows}</div>{_style_controls(o)}")
        else:
            cap = _style_controls(o, captions=False)
        body = (f"<div class='pagehead'><div class='eyebrow'>Voice-over</div><h1>Edit text and captions</h1>"
                f"<div class='lead'><span translate='no'>{e(Path(base['video']).name)}</span></div></div>"
                f"<form method='post' action='/auto/voice/{jid}/render' class='card' data-textform>"
                f"<input type='hidden' name='jid' value='{e(jid)}'>"
                f"<div class='vo-edit'><div>{cap}{_text_rows(base.get('texts') or [])}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the video</button> "
                f"<span class='muted vo-sub'>A new video is made; this one stays.</span></div></div>{_preview_box()}</div></form>"
                f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto/voice'>Back</a></div>")
        return page("Edit text and captions", PAGE_CSS + body, _EDIT_JS)

    @app.post("/auto/voice/<jid>/render")
    def voice_render(jid):
        try:
            base = vo.editor_base(jid)
            pl = _payload(request.form, base)
            vo.new_render(pl["video"], pl["cues"], pl["opts"], pl["texts"], voice_from=pl["voice_from"],
                          start_s=pl["start_s"], keep_sound=pl["keep_sound"], title=pl["title"])
        except (vo.VoiceError, tf.TextError) as exc:
            return err_page(str(exc), f"/auto/voice/{jid}/edit")
        return redirect("/auto/voice")

    @app.post("/auto/voice/<jid>/retry")
    def voice_retry(jid):
        try:
            vo.retry_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/<jid>/delete")
    def voice_delete(jid):
        try:
            vo.delete_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/<jid>/reveal")
    def voice_reveal(jid):
        from . import auto_edit as ae
        try:
            d = vo._job_dir(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        try:
            saved = Path(str((vo.read_job(jid).get("result") or {}).get("saved") or ""))
        except vo.VoiceError:
            saved = Path("")
        target = saved if saved.name and saved.is_file() else d / "video.mp4"
        ae.open_path(target if target.is_file() else d, reveal=target.is_file())
        return redirect("/auto/voice")

    @app.get("/auto/voice/<jid>/file/<name>")
    def voice_file(jid, name):
        if name not in _FILES:
            return "not found", 404
        try:
            p = vo._job_dir(jid) / name
        except vo.VoiceError:
            return "not found", 404
        if not p.is_file():
            return "not found", 404
        dl = request.args.get("download") == "1"
        nice = None
        if dl:                                   # "<title> - voice.wav": the first words of the text, or the video's name
            try:
                title = vo.read_job(jid).get("title") or "voice"
            except vo.VoiceError:
                title = "voice"
            from .auto_edit import safe_filename
            nice = f"{safe_filename(Path(title).stem[:40], 'voice')} - {name}"
        return send_file(p, mimetype=_FILES[name], as_attachment=dl, download_name=nice, conditional=True, max_age=0)

    @app.post("/api/auto/pick-voice-file")
    def voice_pick():
        from . import auto_edit as ae
        kind = (request.get_json(silent=True) or {}).get("kind")
        if kind == "audio":
            files = ae.pick_files("Choose the recording of the voice", kind="audio")
        else:
            files = ae.pick_files("Choose a video", initial=str(ae.default_export_dir()))
        if files:
            return jsonify({"path": files[0]})
        return jsonify({"path": None, "error": "Nothing chosen. You can also paste the path."})


# The editor's and the text form's script: add / remove text rows, the preview picture (the form as it is now).
_EDIT_JS = (
    "document.addEventListener('click',async ev=>{"
    "const add=ev.target.closest('[data-trow-add]');if(add){const box=add.closest('.vo-texts');"
    "box.querySelector('[data-trows]').appendChild(box.querySelector('template[data-trow-tpl]').content.cloneNode(true));return}"
    "const del=ev.target.closest('[data-trow-del]');if(del){del.closest('.vo-trow').remove();return}"
    "const pv=ev.target.closest('[data-preview]');if(!pv)return;const f=pv.closest('form'),m=f.querySelector('[data-pmsg]'),"
    "img=f.querySelector('[data-pimg]');const say=t=>{m.textContent=window.ME_L?ME_L(t):t};"
    "say('Making the picture…');pv.disabled=true;"
    "try{const r=await fetch('/api/text/preview',{method:'POST',body:new FormData(f)});const x=await r.json();"
    "if(x.url){img.src=x.url+'?'+Date.now();img.hidden=false;m.textContent=''}else say(x.error||'The picture could not be made.')}"
    "catch(err){say('The picture could not be made.')}pv.disabled=false});"
)
