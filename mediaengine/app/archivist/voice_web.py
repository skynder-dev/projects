"""The Voice-over page (Auto Edit -> Voice-over): install the add-on, text -> voice, captions, voice onto a video."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

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
.vo-cue{display:flex;gap:6px;align-items:center;margin:4px 0;flex-wrap:wrap}
.vo-cue input{flex:1 1 200px;min-width:0}
.vo-mini{padding:3px 8px;font-size:13px;min-width:28px}
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
        return (f"<div class='card' id='voNew'><h2 style='margin-top:0'>New voice-over</h2>"
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

    def _captions_form(pre: str = "") -> str:
        langs = _lang_options()
        return (f"<div class='card' id='voCaps'><h2 style='margin-top:0'>Captions for a video</h2>"
                f"<div class='muted vo-sub'>The speech in your video is turned into captions with the words timed to it and "
                f"burned into a copy of the video. The video itself is only read.</div>"
                f"<form method='post' action='/auto/voice/captions' style='margin-top:8px'>"
                f"<div class='vo-row'><input class='vo-wide' name='path' required value='{e(pre)}' placeholder='The video, e.g. D:\\Videos\\talk.mp4'>"
                f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                f"<div class='vo-row' style='margin-top:8px'><span>Language of the speech</span><select name='language'>{langs}</select></div>"
                f"{_style_controls(_last_opts())}{_quick_texts()}"
                f"<div style='margin-top:10px'><button>Make captions</button> <span class='muted vo-sub' data-msg></span></div></form></div>")

    def _last_opts() -> dict:
        try:
            from .config import load_config
            return tf.options(**{k: v for k, v in (load_config().get("text_look") or {}).items() if k in
                                 ("style", "color", "size", "position")})
        except Exception:
            return tf.options()

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
        looks = _saved_looks()
        mine = "".join(f"<option value='{e(json.dumps(v))}' data-name='{e(k)}' translate='no'>{e(k)}</option>" for k, v in looks.items())
        saved = (f"<div class='vo-row vo-sub' style='margin-top:6px' data-looks><span>My looks:</span>"
                 + f"<select data-look-use><option value=''>—</option>{mine}</select>"
                   f"<button type='button' class='btn2 vo-mini' data-look-del title='Delete the chosen look'>×</button>"
                 + f"<input data-look-name maxlength='40' size='16' placeholder='Name for this look'>"
                   f"<button type='button' class='btn2 vo-mini' data-look-save>Save the look</button><span data-look-msg></span></div>")
        return ((f"<div class='vo-styles' style='margin-top:8px'><b>Look of the captions</b>{styles}</div>" if captions else "")
                + f"<div class='vo-row' style='margin-top:6px'><span>Color</span><select name='color'>{colors}</select>"
                  f"<span>Size</span><select name='size'>{sizes}</select>"
                + (f"<span>Captions</span><select name='position'>{pos}</select>" if captions else "") + "</div>" + saved)

    def _saved_looks() -> dict:
        try:
            from .config import load_config
            raw = load_config().get("text_looks_saved") or {}
            return {str(k)[:40]: tf.options(**{x: y for x, y in v.items() if x in ("style", "color", "size", "position")})
                    for k, v in list(raw.items())[:12] if isinstance(v, dict)}
        except Exception:
            return {}

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
        anim = "".join(f"<option value='{k}'{' selected' if k == (t.get('anim') or 'pop') else ''}>{e(v)}</option>"
                       for k, v in tf.ANIMS.items())
        start = "end" if t.get("at_end") else _num(t.get("start"))
        end = "" if t.get("at_end") else _num(t.get("end"))
        return (f"<div class='vo-trow'><input name='t_text' maxlength='{tf.TEXT_MAX}' value='{e(t.get('text') or '')}' "
                f"placeholder='The text, e.g. 3 ways to fly cheaper'>"
                f"<span>from</span><input name='t_start' size='4' value='{e(start)}' placeholder='0'>"
                f"<span>to</span><input name='t_end' size='4' value='{e(end)}' placeholder='3'>"
                f"<select name='t_where'>{where}</select><select name='t_look'>{look}</select><select name='t_anim'>{anim}</select>"
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
                f"<label class='muted vo-sub' style='display:block;margin-top:4px'><input type='checkbox' name='safe' value='1'> "
                f"Show where Reels, TikTok and Shorts put their own buttons and text (red)</label>"
                f"<div class='muted vo-sub' data-pmsg></div><img data-pimg alt='' hidden></div>")

    def _quick_texts() -> str:
        return (f"<div class='vo-row' style='margin-top:6px'><span>Title at the top (first 3 s)</span>"
                f"<input name='hook' maxlength='{tf.TEXT_MAX}' size='34' placeholder='optional'></div>"
                f"<div class='vo-row' style='margin-top:6px'><span>Text at the end (last 3 s)</span>"
                f"<input name='end_text' maxlength='{tf.TEXT_MAX}' size='34' placeholder='optional, e.g. Follow for more'></div>")

    def _text_form(pre: str = "") -> str:
        """Text on any video - no add-on needed."""
        o = _last_opts()
        return (f"<div class='card' id='voText'><h2 style='margin-top:0'>Text on a video</h2>"
                f"<div class='muted vo-sub'>Titles and lines of text on your video, at the moments you choose. The video itself "
                f"is only read; a copy with the text is made.</div>"
                f"<form method='post' action='/auto/text/new' style='margin-top:8px' data-textform>"
                f"<div class='vo-edit'><div>"
                f"<div class='vo-row'><input class='vo-wide' name='video' required value='{e(pre)}' placeholder='The video, e.g. D:\\Exports\\reel.mp4'>"
                f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                f"{_text_rows([], header=False)}{_style_controls(o, captions=False)}"
                f"<div style='margin-top:12px'><button class='ae-big'>Make the video</button> "
                f"<span class='muted vo-sub' data-msg></span></div></div>{_preview_box()}</div></form></div>")

    def _job_html(j: dict, pre: str = "") -> str:
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
                    f"<div class='vo-row'><input class='vo-wide' name='video' required value='{e(pre)}' placeholder='The video, e.g. D:\\Exports\\reel.mp4'>"
                    f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                    f"<label style='display:block;margin-top:6px'><input type='checkbox' name='keep_sound' value='1' checked> "
                    f"Keep the video's own sound (quieter while the voice speaks)</label>"
                    f"<label style='display:block'><input type='checkbox' name='captions' value='1' checked> Captions with the words</label>"
                    f"<div class='vo-row' style='margin-top:6px'><span>The voice starts at</span><input name='start' value='0.3' size='4'><span>s</span></div>"
                    f"{_style_controls(_last_opts())}{_quick_texts()}"
                    f"<input type='hidden' name='voice_from' value='{e(jid)}'><div style='margin-top:10px'>{_preview_box()}</div>"
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
        pre = str(request.args.get("video") or "")         # from a saved reel: its path already in the video fields
        if pre and not Path(pre).is_file():
            pre = ""
        parts = [_install_card(s)]
        if pre:
            parts.insert(0, f"<div class='card'><span>The video:</span> <b class='ae-path' translate='no'>{e(Path(pre).name)}</b>"
                            f"<div class='muted vo-sub'>It is already filled in below: put text on it, make captions of its speech, "
                            f"or put a voice-over on it (Made → a voice-over → Put it on a video).</div></div>")
        if s.get("installed"):
            parts += [_voice_form(), _captions_form(pre)]
        parts.append(_text_form(pre))
        if jobs:
            parts.append("<div class='card' id='voJobs'><h2 style='margin-top:0'>Made</h2>" + "".join(_job_html(j, pre) for j in jobs) + "</div>")
        links = ([("voNew", "New voice-over"), ("voCaps", "Captions for a video")] if s.get("installed") else []) \
            + [("voText", "Text on a video")] + ([("voJobs", "Made")] if jobs else [])
        fin = "/auto/finish" + (("?video=" + quote(pre)) if pre else "")
        jump = ("<div class='vo-row' style='margin:-4px 0 12px'>"
                f"<a class='btn' href='{e(fin)}'>Finish a video - all on one page</a>"
                + "".join(f"<a class='btn btn2' href='#{k}'>{e(t)}</a>" for k, t in links) + "</div>")
        body = ("<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Voice-over and text</h1>"
                "<div class='lead'>A text read by a voice, with captions timed to the words; captions and text for your own videos.</div></div>"
                + jump + "".join(parts) + "<div class='row' id='voBack' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
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
        return page("Voice-over and text", PAGE_CSS + body, script + _EDIT_JS)

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
        """The look chosen in a form; remembered, so the next form starts with it (fields not in this form keep theirs)."""
        last = _last_opts()
        o = tf.options(f.get("style") or last["style"], f.get("color") or last["color"], f.get("size") or last["size"],
                       f.get("position") or last["position"])
        try:
            from .config import update_config
            update_config(lambda c: c.__setitem__("text_look", o))
        except Exception:
            pass
        return o

    def _edited_cues(f, base: dict) -> list[dict]:
        """The captions of the editor. Each line carries its time and its words with theirs (c_s, c_e, c_w), so lines
        can be split, joined, moved and added on the page. Untouched, they are regrouped the way the chosen style shows
        words; a line whose words were changed shares its time among the new words by their length.
        Turned off, they are still kept with the video (so its editor can turn them on again)."""
        src = base.get("cues") or []
        texts, ss, es, ws = f.getlist("c_text"), f.getlist("c_s"), f.getlist("c_e"), f.getlist("c_w")
        joined = lambda c: " ".join(w["w"] for w in c["words"])
        if not ss or len(ss) != len(texts):           # a page without line times: by position, as before
            texts = texts if len(texts) == len(src) else [joined(c) for c in src]
            rows = [(t, c["s"], c["e"], c["words"]) for t, c in zip(texts, src)]
        else:
            rows = []
            for i, t in enumerate(texts):
                try:
                    s_, e_ = float(ss[i]), float(es[i])
                    words = json.loads(ws[i]) if i < len(ws) and ws[i] else []
                    if not isinstance(words, list):
                        words = []
                except (TypeError, ValueError):
                    continue
                rows.append((t, s_, e_, words))
        untouched = len(rows) == len(src) and all(
            " ".join(t.split()) == joined(c) and abs(s_ - c["s"]) < 1e-3 for (t, s_, _e, _w), c in zip(rows, src))
        if untouched:                               # grouped the way the chosen style shows words
            return vo.style_cues([w for c in src for w in c["words"]], _opts(f))
        out = []
        for t, s_, e_, words in rows:
            try:
                same = words and " ".join(str(w.get("w")) for w in words) == " ".join(t.split())
            except AttributeError:
                same = False
            if same:                               # the line's own start leads: its words move with it
                try:
                    shift = s_ - min(float(w["s"]) for w in words)
                    words = [{**w, "s": float(w["s"]) + shift, "e": float(w["e"]) + shift} for w in words]
                except (TypeError, ValueError, KeyError):
                    same = False
            nc = {"s": s_, "e": e_, "words": words} if same else \
                tf.retime({"s": s_, "e": e_, "words": [{"w": "", "s": s_, "e": max(e_, s_ + 0.3)}]}, t)
            if nc:
                out.append(nc)
        return out

    def _payload(f, base: dict | None) -> dict:
        """Everything a render (or its preview) needs, from the editor or the text form."""
        texts = tf.parse_texts(tf.rows_from_form(f))
        if base:
            on = f.get("captions_on") == "1"
            return {"video": base["video"], "cues": _edited_cues(f, base), "captions_on": on, "opts": _opts(f),
                    "texts": texts, "voice_from": base.get("voice_from") or "", "start_s": base.get("start_s") or 0.0,
                    "keep_sound": base.get("keep_sound", True), "title": base.get("title") or ""}
        return {"video": f.get("video", ""), "cues": [], "captions_on": False, "opts": _opts(f), "texts": texts,
                "voice_from": "", "start_s": 0.0, "keep_sound": True, "title": ""}

    def _finish_page(pre: str = "") -> str:
        s_ = vo.status()
        made = [j for j in vo.list_jobs(50) if j.get("kind") == "voiceover" and j["state"] == "done"]
        vopts = "".join(f"<option value='{e(j['id'])}' translate='no'>{e(j.get('title') or '')} · "
                        f"{e(str(j.get('created_at') or '')[:16].replace('T', ' '))}</option>" for j in made)
        voices = "".join(f"<label><input type='radio' name='nvoice' value='{k}'{' checked' if k == vo.DEFAULT_VOICE else ''}> "
                         f"{e(v['label'])}</label>" for k, v in vo.VOICES.items() if k != "own")
        new_ok = bool(s_.get("installed"))
        voice = (f"<div class='vo-styles' style='margin-top:12px'><b>2. The voice</b>"
                 f"<label><input type='radio' name='voice' value='none' checked> No voice (the video's own sound)</label>"
                 + (f"<label><input type='radio' name='voice' value='made'> A voice-over made already</label>"
                    f"<div data-when='voice=made' hidden style='margin:4px 0 0 22px'><select name='voice_from'>{vopts}</select></div>"
                    if made else "")
                 + (f"<label><input type='radio' name='voice' value='new'> A new voice-over (made first, then the video)</label>"
                    f"<div data-when='voice=new' hidden style='margin:4px 0 0 22px'>"
                    f"<textarea class='vo-text' name='text' maxlength='{vo.MAX_TEXT}' placeholder='The text to be said…'></textarea>"
                    f"<div class='vo-voices'>{voices}</div>"
                    f"<input class='vo-wide' name='description' maxlength='400' placeholder='For example: a calm man in his "
                    f"forties with a deep, warm voice, slow pace'>"
                    f"<div class='vo-row' style='margin-top:6px'><span>Language of the text</span><select name='language'>"
                    f"{_lang_options()}</select></div></div>"
                    if new_ok else "")
                 + f"<div data-when='voice=made voice=new' hidden><label style='display:block;margin-top:6px'><input type='checkbox' "
                   f"name='keep_sound' value='1' checked> Keep the video's own sound (quieter while the voice speaks)</label>"
                   f"<div class='vo-row'><span>The voice starts at</span><input name='start' value='0.3' size='4'><span>s</span></div></div>"
                 + ("" if new_ok else "<div class='muted vo-sub'>A new voice-over and captions of the speech need the "
                                      "voice add-on (Voice-over and text → Install the voice add-on).</div>")
                 + "</div>")
        caps = (f"<div class='vo-styles' style='margin-top:12px'><b>3. Captions</b>"
                f"<label><input type='radio' name='captions' value='none' checked> No captions</label>"
                f"<label><input type='radio' name='captions' value='voice'> The words of the voice</label>"
                + (f"<label><input type='radio' name='captions' value='speech'> The speech in the video (heard when it is made)</label>"
                   if new_ok else "") + "</div>")
        return (f"<div class='pagehead'><div class='eyebrow'>Voice-over and text</div><h1>Finish a video</h1>"
                f"<div class='lead'>A voice, captions and text for one video, with their look - on one page.</div></div>"
                f"<form method='post' action='/auto/finish' class='card' data-textform "
                f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button:not([type=button])').forEach(x=>x.disabled=true),0)\">"
                f"<input type='hidden' name='finish' value='1'><div class='vo-edit'><div>"
                f"<b>1. The video</b><div class='vo-row' style='margin-top:4px'><input class='vo-wide' name='video' required "
                f"value='{e(pre)}' placeholder='The video, e.g. D:\\Exports\\reel.mp4'>"
                f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>{_reel_select()}"
                f"{voice}{caps}<div style='margin-top:12px'><b>4. The look</b></div>{_style_controls(_last_opts())}"
                f"<div style='margin-top:6px'><b>5. Text on the video</b></div>{_text_rows([], header=False)}"
                f"<div style='margin-top:14px'><button class='ae-big'>Make the video</button> "
                f"<span class='muted vo-sub' data-msg></span></div></div>{_preview_box()}</div></form>"
                f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto/voice'>Voice-over and text</a></div>")

    @app.get("/auto/finish")
    def finish_page():
        pre = str(request.args.get("video") or "")
        if pre and not Path(pre).is_file():
            pre = ""
        return page("Finish a video", PAGE_CSS + _finish_page(pre), _PICK_JS + _EDIT_JS)

    @app.post("/auto/finish")
    def finish_new():
        f = request.form
        try:
            vo.new_finish(f.get("video", ""), voice=f.get("voice", "none"), voice_from=f.get("voice_from", ""),
                          new_voice={"text": f.get("text", ""), "voice": f.get("nvoice", ""),
                                     "description": f.get("description", ""), "language": f.get("language", "")},
                          captions=f.get("captions", "none"), opts=_opts(f), texts=tf.parse_texts(tf.rows_from_form(f)),
                          start_s=f.get("start", "0.3"), keep_sound=f.get("keep_sound") == "1")
        except (vo.VoiceError, tf.TextError) as exc:
            return err_page(str(exc), "/auto/finish")
        return redirect("/auto/voice#voJobs")

    @app.post("/api/text/looks")
    def text_looks():
        """Save (name + look) or delete (name, delete) one of "My looks"; at most 12, kept in the settings."""
        from .config import update_config
        d = request.get_json(silent=True) or {}
        name = " ".join(tf.clean_text(d.get("name") or "", 40).split())
        if not name:
            return jsonify({"error": "Give the look a name."})
        o = tf.options(d.get("style"), d.get("color"), d.get("size"), d.get("position"))

        def change(c):
            looks = {k: v for k, v in (c.get("text_looks_saved") or {}).items() if isinstance(v, dict)}
            if d.get("delete"):
                looks.pop(name, None)
            else:
                looks.pop(name, None)
                looks[name] = o
                while len(looks) > 12:
                    looks.pop(next(iter(looks)))
            c["text_looks_saved"] = looks
        update_config(change)
        return jsonify({"ok": True, "looks": list(_saved_looks())})

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
            if f.get("finish"):                                    # the one-page form: what is known before making
                o = _opts(f)
                vf = f.get("voice_from", "") if f.get("voice") == "made" else ""
                start = float(str(f.get("start") or "0.3").replace(",", ".") or 0.3)
                cues = vo.style_cues(vo.voiceover_words(vf), o) if vf and f.get("captions") == "voice" else []
                at = float(str(f.get("at") or "1").replace(",", ".") or 1)
                pic = vo.preview_frame(f.get("video", ""), cues, o, tf.parse_texts(tf.rows_from_form(f)),
                                       offset=start, at=at, voice_from=vf, safe=f.get("safe") == "1")
                return jsonify({"url": f"/api/text/preview/{pic.parent.name}.jpg"})
            if f.get("voice_from") and not f.get("jid"):          # the "Put it on a video" form, before it is made
                o = _opts(f)
                words = vo.voiceover_words(f["voice_from"])
                start = float(str(f.get("start") or "0.3").replace(",", ".") or 0.3)
                at = float(str(f.get("at") or "1").replace(",", ".") or 1)
                pic = vo.preview_frame(f.get("video", ""), vo.style_cues(words, o) if f.get("captions") == "1" else [],
                                       o, tf.hook_and_end(f.get("hook", ""), f.get("end_text", "")), offset=start, at=at,
                                       voice_from=f["voice_from"], safe=f.get("safe") == "1")
                return jsonify({"url": f"/api/text/preview/{pic.parent.name}.jpg"})
            base = vo.editor_base(f["jid"]) if f.get("jid") else None
            pl = _payload(f, base)
            at = float(str(f.get("at") or "1").replace(",", ".") or 1)
            pic = vo.preview_frame(pl["video"], pl["cues"] if pl["captions_on"] else [], pl["opts"], pl["texts"],
                                   offset=pl["start_s"], at=at,
                                   voice_from=pl["voice_from"], safe=f.get("safe") == "1")
        except (vo.VoiceError, tf.TextError) as exc:
            return jsonify({"error": str(exc)})
        except ValueError:
            return jsonify({"error": "The start of the voice must be a number of seconds, for example 0.5."})
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
        def cue_row(c) -> str:
            ws_ = json.dumps([{"w": w["w"], "s": round(float(w["s"]), 3), "e": round(float(w["e"]), 3)} for w in c["words"]],
                             ensure_ascii=False)
            return (f"<div class='vo-cue' data-cue><span class='muted vo-sub' translate='no' data-t>"
                    f"{e(_num(round(c['s'] + base['start_s'], 1)))}</span>"
                    f"<input name='c_text' value='{e(' '.join(w['w'] for w in c['words']))}' maxlength='200'>"
                    f"<input type='hidden' name='c_s' value='{c['s']:.3f}'><input type='hidden' name='c_e' value='{c['e']:.3f}'>"
                    f"<input type='hidden' name='c_w' value='{e(ws_)}'>"
                    f"<button type='button' class='btn2 vo-mini' data-cue-act='earlier' title='0.1 s earlier' translate='no'>−0.1</button>"
                    f"<button type='button' class='btn2 vo-mini' data-cue-act='later' title='0.1 s later' translate='no'>+0.1</button>"
                    f"<button type='button' class='btn2 vo-mini' data-cue-act='split' title='Split this line where the cursor is'>✂</button>"
                    f"<button type='button' class='btn2 vo-mini' data-cue-act='join' title='Join with the next line'>⤓</button>"
                    f"<button type='button' class='btn2 vo-mini' data-cue-act='add' title='Add a line after this one'>＋</button></div>")
        rows = "".join(cue_row(c) for c in cues)
        cap = ""
        if cues:
            cap = (f"<label style='display:block;margin-top:8px'><input type='checkbox' name='captions_on' value='1'"
                   f"{' checked' if base.get('captions_on', True) else ''}> Captions with the words</label>"
                   f"<div class='muted vo-sub'>Fix a word right in its line; an emptied line is left out. −0.1 and +0.1 move a line "
                   f"by 0.1 s, ✂ splits it where the cursor is, ⤓ joins it with the next one, ＋ adds a line.</div>"
                   f"<div class='vo-cues' data-offset='{base['start_s']:.3f}'>{rows}</div>{_style_controls(o)}")
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
                          start_s=pl["start_s"], keep_sound=pl["keep_sound"], title=pl["title"],
                          captions_on=pl["captions_on"])
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
    "function meWhen(){document.querySelectorAll('[data-when]').forEach(d=>{const f=d.closest('form');"
    "d.hidden=!d.dataset.when.split(' ').some(c=>{const [n,v]=c.split('=');const r=f.querySelector('input[name='+n+']:checked');"
    "return r&&r.value===v})})}document.addEventListener('change',ev=>{if(ev.target.type==='radio')meWhen()});meWhen();"
    "function cueSet(row,s,e,ws,txt){const q=n=>row.querySelector('[name='+n+']');q('c_s').value=s.toFixed(3);q('c_e').value=e.toFixed(3);"
    "q('c_w').value=ws?JSON.stringify(ws):'';if(txt!==undefined)q('c_text').value=txt;const off=+(row.closest('[data-offset]')||{dataset:{offset:0}}).dataset.offset||0;"
    "row.querySelector('[data-t]').textContent=(Math.round((s+off)*10)/10).toString()}"
    "function cueGet(row){const q=n=>row.querySelector('[name='+n+']');let ws=[];try{ws=q('c_w').value?JSON.parse(q('c_w').value):[]}catch(x){}"
    "const t=q('c_text').value,same=ws.length&&ws.map(w=>w.w).join(' ')===t.trim().split(/\\s+/).join(' ');return{s:+q('c_s').value,e:+q('c_e').value,ws:same?ws:null,t:t}}"
    "document.addEventListener('click',ev=>{const b=ev.target.closest('[data-cue-act]');if(!b)return;const row=b.closest('[data-cue]'),c=cueGet(row),a=b.dataset.cueAct;"
    "if(a==='earlier'||a==='later'){const d=a==='earlier'?-0.1:0.1;if(c.s+d<0)return;cueSet(row,c.s+d,c.e+d,c.ws&&c.ws.map(w=>({w:w.w,s:+(w.s+d).toFixed(3),e:+(w.e+d).toFixed(3)})))}"
    "else if(a==='split'){const inp=row.querySelector('[name=c_text]');const pos=inp.selectionStart||Math.floor(c.t.length/2);"
    "const left=c.t.slice(0,pos).trim(),right=c.t.slice(pos).trim();if(!left||!right)return;const k=left.split(/\\s+/).length;"
    "let mid=c.s+(c.e-c.s)*left.length/(left.length+right.length),w1=null,w2=null;if(c.ws&&left.split(/\\s+/).join(' ')===c.ws.slice(0,k).map(w=>w.w).join(' ')){w1=c.ws.slice(0,k);w2=c.ws.slice(k);mid=w2[0].s}"
    "const nr=row.cloneNode(true);row.after(nr);cueSet(row,c.s,Math.max(c.s+0.05,mid-0.01),w1,left);cueSet(nr,mid,c.e,w2,right)}"
    "else if(a==='join'){const nx=row.nextElementSibling;if(!nx||!nx.matches('[data-cue]'))return;const n=cueGet(nx);"
    "cueSet(row,c.s,n.e,c.ws&&n.ws?c.ws.concat(n.ws):null,(c.t.trim()+' '+n.t.trim()).trim());nx.remove()}"
    "else if(a==='add'){const nx=row.nextElementSibling,ns=nx&&nx.matches('[data-cue]')?cueGet(nx).s:c.e+2;const nr=row.cloneNode(true);row.after(nr);"
    # a pause after this line: the new one fills it; none: this line's time is shared with the new one
    "if(ns-c.e>=0.5)cueSet(nr,c.e+0.01,Math.min(ns-0.01,c.e+2),null,'');else{const mid=(c.s+c.e)/2;cueSet(row,c.s,mid-0.01,null);cueSet(nr,mid,c.e,null,'')}"
    "nr.querySelector('[name=c_text]').focus()}});"
    "document.addEventListener('change',ev=>{const sl=ev.target.closest('[data-look-use]');if(!sl||!sl.value)return;const o=JSON.parse(sl.value),f=sl.closest('form');"
    "const r=f.querySelector('input[name=style][value='+o.style+']');if(r)r.checked=true;"
    "for(const k of ['color','size','position']){const x=f.querySelector('select[name='+k+']');if(x)x.value=o[k]}});"
    "document.addEventListener('click',async ev=>{const b=ev.target.closest('[data-look-save],[data-look-del]');if(!b)return;"
    "const f=b.closest('form'),box=b.closest('[data-looks]'),m=box.querySelector('[data-look-msg]');const v=n=>{const x=f.querySelector('[name='+n+']:checked')||f.querySelector('select[name='+n+']');return x?x.value:''};"
    "let body;if(b.matches('[data-look-del]')){const sl=box.querySelector('[data-look-use]'),op=sl&&sl.selectedOptions[0];if(!op||!op.dataset.name)return;"
    "body={name:op.dataset.name,delete:true}}else body={name:box.querySelector('[data-look-name]').value,style:v('style'),color:v('color'),size:v('size'),position:v('position')};"
    "try{const r=await fetch('/api/text/looks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const x=await r.json();"
    "if(x.error){m.textContent=window.ME_L?ME_L(x.error):x.error;return}"
    "if(body.delete){box.querySelector('[data-look-use]').selectedOptions[0].remove()}else{let sl=box.querySelector('[data-look-use]');"
    "if(sl){[...sl.options].filter(o=>o.dataset.name===body.name).forEach(o=>o.remove());const op=document.createElement('option');"
    "op.value=JSON.stringify({style:body.style||'pop',color:body.color,size:body.size,position:body.position||'bottom'});op.dataset.name=body.name;op.textContent=body.name;sl.appendChild(op);sl.value=op.value}"
    "box.querySelector('[data-look-name]').value='';const t=window.ME_L?ME_L('Saved.'):'Saved.';m.textContent=' '+t}}catch(err){}});"
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

# Choose… (a Windows file window) and the reels saved lately, on pages other than the Voice-over page itself.
_PICK_JS = (
    "document.addEventListener('change',ev=>{const sl=ev.target.closest('select[data-fill]');if(!sl||!sl.value)return;"
    "const i=sl.closest('form').querySelector('input[name=video],input[name=path]');if(i)i.value=sl.value});"
    "document.addEventListener('click',async ev=>{const b=ev.target.closest('[data-pick]');if(!b)return;const f=b.closest('form'),"
    "m=f.querySelector('[data-msg]');if(m)m.textContent=window.ME_L?ME_L('A Windows window is open — it may be behind this window.'):"
    "'A Windows window is open — it may be behind this window.';"
    "try{const r=await fetch('/api/auto/pick-voice-file',{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({kind:b.dataset.pick})});const x=await r.json();if(x.path){b.parentNode.querySelector('input').value=x.path;"
    "if(m)m.textContent=''}else if(m)m.textContent=x.error||''}catch(err){}});"
)
