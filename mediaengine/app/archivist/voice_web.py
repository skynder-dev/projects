"""The Voice-over page (Auto Edit -> Voice-over): install the add-on, text -> voice, captions, voice onto a video."""
from __future__ import annotations

import json
from pathlib import Path

from flask import jsonify, redirect, request, send_file

from . import voice as vo

_INSTALL_STEP = {"checking": "Checking the PC…", "packages": "Downloading and installing the add-on's Python parts (about 3 GB)…",
                 "models": "Downloading the voice models (about 5 GB)…", "checking_addon": "Starting the add-on for a test…"}
_JOB_STEP = {"starting": "Starting…", "loading": "Loading the voice model…", "speaking": "Speaking…",
             "joining": "Joining the parts…", "listening": "Listening to check every word…", "finishing": "Finishing the sound…",
             "reading": "Reading the sound of the video…", "video": "Making the video…", "checking": "Checking the video…"}
_KIND = {"voiceover": "Voice-over", "captions": "Captions for a video", "dub": "Voice-over on a video"}
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
textarea.vo-text{width:100%;min-height:130px;font:15px system-ui;box-sizing:border-box}
input.vo-wide{width:100%;max-width:640px;box-sizing:border-box}
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
                + f"<form method='post' action='/auto/voice/install' style='margin-top:12px' "
                  f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                  f"<button class='ae-big'>{again}</button></form></div>")

    def _lang_options() -> str:
        return "".join(f"<option value='{c}'" + (" translate='no'" if c else "") + f">{e(n)}</option>" for c, n in _LANGS)

    def _voice_form() -> str:
        radios = "".join(
            f"<label><input type='radio' name='voice' value='{k}'{' checked' if k == 'friend' else ''}> {e(v['label'])}</label>"
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
                f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>"
                f"<div class='vo-row' style='margin-top:8px'><span>Language of the speech</span><select name='language'>{langs}</select>"
                f"<span>Captions</span><select name='position'><option value='bottom'>at the bottom</option>"
                f"<option value='middle'>in the middle</option><option value='top'>at the top</option></select></div>"
                f"<div style='margin-top:10px'><button>Make captions</button> <span class='muted vo-sub' data-msg></span></div></form></div>")

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
        elif st in ("waiting", "interrupted"):
            body = f"<div class='muted vo-sub'>{e(_STATE[st])}</div>"
        elif st == "failed":
            body = f"<div class='errbox' style='margin-top:6px'>{e(res.get('error') or 'Failed')}</div>"
        elif st == "done" and j.get("kind") == "voiceover":
            n, bad = int(res.get("words") or 0), int(res.get("word_errors") or 0)
            check = ("<span>Every word was said (checked by listening).</span>" if bad == 0 else
                     f"<span>Words not clear when listening:</span> <b translate='no'>{bad}</b> <span>of</span> <span translate='no'>{n}</span>")
            dev = "the graphics card" if res.get("device") == "cuda" else "the processor"
            body = (f"<audio controls preload='none' src='/auto/voice/{jid}/file/voice.wav' style='width:100%;max-width:640px;margin-top:6px'></audio>"
                    f"<div class='muted vo-sub'><span translate='no'>{e(str(res.get('seconds') or ''))}</span> <span>s</span> · {check} · "
                    f"<span>made on</span> <span>{dev}</span></div>"
                    f"<div class='vo-row' style='margin-top:6px'><a class='btn btn2' href='/auto/voice/{jid}/file/voice.wav?download=1'>Download WAV</a>"
                    f"<a class='btn btn2' href='/auto/voice/{jid}/file/captions.srt?download=1'>Download captions (SRT)</a></div>"
                    f"<details style='margin-top:8px'><summary>Put it on a video</summary>"
                    f"<form method='post' action='/auto/voice/{jid}/dub' style='margin-top:8px'>"
                    f"<div class='vo-row'><input class='vo-wide' name='video' required placeholder='The video, e.g. D:\\Exports\\reel.mp4'>"
                    f"<button type='button' class='btn2' data-pick='video'>Choose…</button></div>"
                    f"<label style='display:block;margin-top:6px'><input type='checkbox' name='keep_sound' value='1' checked> "
                    f"Keep the video's own sound (quieter while the voice speaks)</label>"
                    f"<label style='display:block'><input type='checkbox' name='captions' value='1' checked> Captions with the words</label>"
                    f"<div class='vo-row' style='margin-top:6px'><span>Captions</span><select name='position'><option value='bottom'>at the bottom</option>"
                    f"<option value='middle'>in the middle</option><option value='top'>at the top</option></select>"
                    f"<span>The voice starts at</span><input name='start' value='0.3' size='4'><span>s</span></div>"
                    f"<div style='margin-top:8px'><button>Make the video</button></div></form></details>")
        elif st == "done":
            body = (f"<video controls preload='metadata' src='/auto/voice/{jid}/file/video.mp4' style='max-width:360px;max-height:420px;margin-top:6px'></video>"
                    f"<div class='muted vo-sub'><span translate='no'>{e(str(res.get('seconds') or ''))}</span> <span>s</span> · "
                    f"<span>checked: plays to the end</span></div>"
                    f"<div class='vo-row' style='margin-top:6px'><form method='post' action='/auto/voice/{jid}/reveal' style='margin:0'>"
                    f"<button class='btn2'>Show in folder</button></form>"
                    + (f"<a class='btn btn2' href='/auto/voice/{jid}/file/captions.srt?download=1'>Download captions (SRT)</a>" if (res.get("files") or {}).get("srt") else "")
                    + "</div>")
        delete = ("" if st == "working" else
                  f"<form method='post' action='/auto/voice/{jid}/delete' style='margin-top:6px' "
                  f"onsubmit=\"return confirm(window.ME_L?ME_L('Delete it?'):'Delete it?')\"><button class='btn2'>Delete</button></form>")
        return f"<div class='vo-job' id='j-{jid}' data-state='{st}'>{head}{body}{delete}</div>"

    @app.get("/auto/voice")
    def voice_page():
        s = vo.status()
        jobs = vo.list_jobs()
        parts = [_install_card(s)]
        if s.get("installed"):
            parts += [_voice_form(), _captions_form()]
        if jobs:
            parts.append("<div class='card'><h2 style='margin-top:0'>Made</h2>" + "".join(_job_html(j) for j in jobs) + "</div>")
        body = ("<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Voice-over</h1>"
                "<div class='lead'>A text read by a voice, with captions timed to the words; captions for your own videos.</div></div>"
                + "".join(parts) + "<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
        steps = json.dumps({**_INSTALL_STEP})
        script = (
            "document.querySelectorAll('input[name=voice]').forEach(r=>r.addEventListener('change',()=>{"
            "document.querySelectorAll('[data-for]').forEach(d=>{d.hidden=!document.querySelector('input[name=voice][value='+d.dataset.for+']:checked')})}));"
            "document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=async()=>{const f=b.closest('form'),m=f.querySelector('[data-msg]');"
            "if(m)m.textContent=window.ME_L?ME_L('A Windows window is open — it may be behind this window.'):'A Windows window is open — it may be behind this window.';"
            "try{const r=await fetch('/api/auto/pick-voice-file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:b.dataset.pick})});"
            "const x=await r.json();if(x.path){b.parentNode.querySelector('input').value=x.path;if(m)m.textContent=''}else if(m)m.textContent=x.error||''}catch(err){}});"
            "const ST=" + steps + ";"
            "let sig=null;async function poll(){try{const r=await fetch('/api/voice/status',{cache:'no-store'});const x=await r.json();"
            "const now=JSON.stringify([x.install.state,x.install.installed,x.jobs.map(j=>j.id+j.state)]);"
            "if(sig!==null&&now!==sig){location.reload();return}sig=now;"
            "const bar=document.getElementById('voBar');if(bar&&x.install.state==='running'){"
            "bar.style.width=(x.install.step==='models'&&x.install.total?Math.round(100*x.install.done/x.install.total):5)+'%';"
            "const s=document.getElementById('voStep'),tx=ST[x.install.step]||'';s.textContent=window.ME_L?ME_L(tx):tx;"
            "document.getElementById('voDetail').textContent=x.install.detail||''}"
            "for(const j of x.jobs){if(j.state!=='working')continue;const el=document.getElementById('j-'+j.id);"
            "if(el){const i=el.querySelector('.ae-bar i');if(i)i.style.width=Math.round(100*j.progress)+'%'}}"
            "}catch(err){}const busy=document.querySelector('#voInstall,[data-state=working],[data-state=waiting]');setTimeout(poll,busy?1500:15000)}"
            "poll();")
        return page("Voice-over", PAGE_CSS + body, script)

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
            vo.new_captions(f.get("path", ""), f.get("language", ""), f.get("position", "bottom"))
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/voice")
        return redirect("/auto/voice")

    @app.post("/auto/voice/<jid>/dub")
    def voice_dub(jid):
        f = request.form
        try:
            vo.new_dub(jid, f.get("video", ""), keep_sound=f.get("keep_sound") == "1", captions=f.get("captions") == "1",
                       position=f.get("position", "bottom"), start_s=f.get("start", "0.3"))
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
        target = d / "video.mp4"
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
        if dl:
            try:
                title = vo.read_job(jid).get("title") or "voice"
            except vo.VoiceError:
                title = "voice"
            from .auto_edit import safe_filename
            nice = safe_filename(Path(title).stem[:40] or "voice", "voice") + ("" if name == "video.mp4" else " - ") + \
                ({"voice.wav": "voice.wav", "captions.srt": "captions.srt", "video.mp4": " voice.mp4"}[name])
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
