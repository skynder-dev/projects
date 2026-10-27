"""The page "Clips from a long video" (Auto Edit -> Clips): listen to a podcast / stream / interview once, tick the
parts worth a clip, get vertical clips with the face in the frame, the sound and captions (clips.py)."""
from __future__ import annotations

import re
from pathlib import Path

from flask import redirect, request, send_file

from . import clips as cl
from . import textfx as tf
from . import voice as vo

CSS = """<style>
.cl-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.cl-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,400px);gap:16px;align-items:start}
@media(max-width:1000px){.cl-grid{grid-template-columns:1fr}}
.cl-side{position:sticky;top:12px}
.cl-c{border-top:1px solid var(--line);padding:12px 0;display:grid;grid-template-columns:28px minmax(0,1fr);gap:8px}
.cl-c:first-child{border-top:0}
.cl-c input[type=checkbox]{width:20px;height:20px;margin-top:2px;accent-color:var(--orange)}
.cl-first{font-weight:700;margin:2px 0 4px}
.cl-text{font-size:14px;line-height:1.45;color:var(--muted)}
.cl-score{font-weight:800;color:var(--orange)}
.cl-why{font-size:12px;border:1px solid var(--line2);border-radius:999px;padding:1px 8px}
.cl-times input{width:76px}
.cl-made video{width:150px;max-height:270px;border-radius:8px;background:#000}
.cl-made .cl-row{align-items:flex-start}
.cl-choices label{display:inline-flex;gap:6px;align-items:center;margin:3px 12px 3px 0}
</style>"""
_STEP = {"starting": "Starting…", "reading": "Reading the sound of the video…", "listening": "Listening to the speech…",
         "checking": "Checking the clips…"}
_WHY = {"a question at the start": "a question at the start", "a strong opening": "a strong opening", "numbers": "numbers",
        "strong words": "strong words", "lively": "lively"}


def _mmss(t) -> str:
    try:
        x = max(0.0, float(t))
    except (TypeError, ValueError):
        return ""
    h, rem = int(x // 3600), x - 3600 * int(x // 3600)
    m, s = int(rem // 60), rem - 60 * int(rem // 60)
    sec = f"{s:04.1f}"
    return (f"{h}:{m:02d}:{sec}" if h else f"{m}:{sec}")


def _secs(v) -> float | None:
    s = str(v if v is not None else "").strip().replace(",", ".")
    m = re.fullmatch(r"(?:(\d{1,2}):)?(?:(\d{1,3}):)?(\d{1,5}(?:\.\d{1,3})?)", s)
    if not m:
        return None
    a, b, c = m.group(1), m.group(2), m.group(3)
    if a is not None and b is not None:
        return int(a) * 3600 + int(b) * 60 + float(c)
    if a is not None:
        return int(a) * 60 + float(c)
    return float(c)


def register(app, page, err_page, e, human_bytes):

    def _bar(j: dict) -> str:
        step = str(j.get("step") or "")
        key, _, part = step.partition(" ")
        label = (f"<span>Clip</span> <span translate='no'>{e(part)}</span>" if key == "clip" else e(_STEP.get(key, "Working…")))
        return (f"<div class='ae-bar' style='margin-top:6px'><i style='width:{int(100 * float(j.get('progress') or 0))}%'></i></div>"
                f"<div class='muted' style='font-size:13px'>{label}</div>"
                f"<form method='post' action='/auto/clips/{j['id']}/stop' style='margin-top:6px'><button class='btn2'>Stop</button></form>")

    def _state_html(j: dict, back: str) -> str:
        st, res = j["state"], j.get("result") or {}
        if st == "working":
            return _bar(j)
        if st == "waiting":
            return ("<div class='muted'>Waiting (another voice-over or clip job is being made first).</div>"
                    f"<form method='post' action='/auto/clips/{j['id']}/stop' style='margin-top:6px'><button class='btn2'>Don't make it</button></form>")
        if st in ("failed", "interrupted"):
            msg = res.get("error") or ("Interrupted (MediaEngine was closed)." if st == "interrupted" else "Failed")
            return (f"<div class='errbox' style='margin-top:6px'>{e(msg)}</div>"
                    f"<form method='post' action='/auto/clips/{j['id']}/retry' style='margin-top:6px'>"
                    f"<input type='hidden' name='back' value='{e(back)}'><button>Try again</button></form>")
        return ""

    def _finds() -> list[dict]:
        return [j for j in vo.list_jobs(200) if j.get("kind") == "clips_find"]

    def _makes(fid: str) -> list[dict]:
        return [j for j in vo.list_jobs(400) if j.get("kind") == "clips_make" and j.get("find") == fid]

    def _busy(js) -> bool:
        return any(j["state"] in ("working", "waiting") for j in js)

    @app.get("/auto/clips")
    def clips_home():
        s = vo.status()
        last = cl.last_choices()
        langs = "".join(f"<option value='{c}'" + (" translate='no'" if c else "") + f">{e(n)}</option>" for c, n in
                        [("", "Detect by itself"), ("en", "English"), ("ru", "Русский"), ("es", "Español"), ("de", "Deutsch"),
                         ("fr", "Français"), ("it", "Italiano"), ("pt", "Português"), ("uk", "Українська")])
        lengths = "".join(f"<label><input type='radio' name='length' value='{k}' {'checked' if k == last['length'] else ''}> "
                          f"{e(v)}</label>" for k, v in cl.LENGTH_LABELS.items())
        addon = ("" if s.get("installed") else
                 "<div class='callout card' style='margin-bottom:12px'><b>Finding clips needs the voice add-on</b> (it listens "
                 "to the speech). <a href='/auto/voice'>Install it on the Voice-over page</a> - once, free.</div>")
        jobs = _finds()
        rows = ""
        for j in jobs:
            res = j.get("result") or {}
            info = (f"<span>clips found:</span> <b translate='no'>{int(res.get('candidates') or 0)}</b>" if j["state"] == "done" else "")
            rows += (f"<div class='vo-job' style='border-top:1px solid var(--line);padding:10px 0'><div class='cl-row'>"
                     f"<a href='/auto/clips/{j['id']}'><b translate='no'>{e(j.get('title') or '')}</b></a>"
                     f"<span class='muted' style='font-size:13px' translate='no'>{e(str(j.get('created_at') or '')[:16].replace('T', ' '))}</span>"
                     f"<span class='muted' style='font-size:13px'>{info}</span>"
                     + (f"<a class='btn btn2' href='/auto/clips/{j['id']}'>Open</a>" if j["state"] == "done" else "")
                     + ("" if j["state"] == "working" else
                        f"<form method='post' action='/auto/clips/{j['id']}/delete' style='margin:0' onsubmit=\"return confirm(window.ME_L?"
                        f"ME_L('Delete it? The clips saved in the folder stay.'):'Delete it? The clips saved in the folder stay.')\">"
                        f"<input type='hidden' name='back' value='/auto/clips'><button class='btn2'>Delete</button></form>")
                     + "</div>" + _state_html(j, "/auto/clips") + "</div>")
        listed = (f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Videos listened to</h2>{rows}</div>" if rows else "")
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Clips from a long video</h1>"
                f"<div class='lead'>A podcast, a stream or an interview: MediaEngine listens to it once and lists the parts that "
                f"make good short clips, with their words - the likeliest first. Tick the ones you want: they are made "
                f"vertical, with the face in the frame, the sound and captions. The video itself is only read.</div></div>"
                f"{addon}<div class='card'><h2 style='margin-top:0'>Find clips</h2>"
                f"<form method='post' action='/auto/clips/new' onsubmit=\"setTimeout(()=>this.querySelectorAll('button:not([type=button])').forEach(x=>x.disabled=true),0)\">"
                f"<div class='cl-row'><input class='vo-wide' name='path' required placeholder='The long video, e.g. D:\\Podcasts\\episode 12.mp4' "
                f"style='flex:1;min-width:260px'><button type='button' class='btn2' data-pick='video'>Choose…</button></div>"
                f"<div class='cl-choices' style='margin-top:10px'><b>Length of a clip</b><br>{lengths}</div>"
                f"<div class='cl-row' style='margin-top:8px'><span>Language of the speech</span><select name='language'>{langs}</select></div>"
                f"<div class='muted' style='font-size:13px;margin-top:8px'>Listening takes about 5-15 minutes for an hour of video. "
                f"You can close this page meanwhile; the PC does not go to sleep.</div>"
                f"<div style='margin-top:10px'><button class='ae-big'>Find clips</button> <span class='muted' data-msg></span></div>"
                f"</form></div>{listed}"
                f"<div class='muted' style='font-size:13px;margin-top:12px'>Use only videos you may cut: your own, or footage a "
                f"clipping campaign gives you to cut.</div>")
        script = _PICK_JS + ("setTimeout(()=>location.reload(),4000);" if _busy(jobs) else "")
        return page("Clips from a long video", body, script)

    @app.post("/auto/clips/new")
    def clips_new():
        f = request.form
        try:
            jid = cl.new_find(f.get("path", ""), f.get("length", "medium"), f.get("language", ""))
        except vo.VoiceError as exc:
            return err_page(str(exc), "/auto/clips")
        return redirect(f"/auto/clips/{jid}")

    @app.get("/auto/clips/<jid>")
    def clips_job(jid):
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return err_page("No such job.", "/auto/clips")
        if j.get("kind") != "clips_find":
            return err_page("No such job.", "/auto/clips")
        src = Path(j.get("source") or "")
        head = (f"{CSS}<div class='pagehead'><div class='eyebrow'><a href='/auto/clips'>Clips from a long video</a></div>"
                f"<h1 translate='no'>{e(src.name)}</h1><div class='lead ae-path' translate='no'>{e(str(src))}</div></div>")
        if j["state"] != "done":
            body = head + f"<div class='card'>{_state_html(j, f'/auto/clips/{jid}')}</div>"
            return page("Clips from a long video", body, "setTimeout(()=>location.reload(),3000);" if j["state"] in ("working", "waiting") else "")
        cands = cl.candidates(jid)
        last = cl.last_choices()
        rows = ""
        for c in cands:
            cid = e(c["id"])
            why = "".join(f" <span class='cl-why'>{e(_WHY.get(w, w))}</span>" for w in c.get("why") or [])
            rest = c["text"][len(c["first"]):].strip() if c["text"].startswith(c["first"]) else c["text"]
            rows += (f"<div class='cl-c'><input type='checkbox' name='pick' value='{cid}'>"
                     f"<div><div class='cl-row' style='gap:8px'><span class='cl-score' title='How likely a good clip'>{int(c['score'])}</span>"
                     f"<span class='cl-times cl-row' style='gap:4px'><input name='s_{cid}' value='{e(_mmss(c['s']))}' aria-label='Start'>"
                     f"<span>–</span><input name='e_{cid}' value='{e(_mmss(c['e']))}' aria-label='End'></span>"
                     f"<span class='muted'><span translate='no'>{round(float(c['e']) - float(c['s']))}</span> <span>s</span></span>"
                     f"<button type='button' class='btn2 vo-mini' data-play='{cid}'>▶ Play</button>{why}</div>"
                     f"<div class='cl-first' translate='no'>{e(c['first'])}</div>"
                     f"<div class='cl-text' translate='no'>{e(rest[:700])}{'…' if len(rest) > 700 else ''}</div>"
                     f"<input type='hidden' name='first_{cid}' value='{e(c['first'])}'></div></div>")
        fmts = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if k == last['format'] else ''}> {e(v)}</label>"
                       for k, v in cl.FORMAT_LABELS.items())
        frs = "".join(f"<label><input type='radio' name='framing' value='{k}' {'checked' if k == last['framing'] else ''}> {e(v)}</label>"
                      for k, v in cl.FRAMINGS.items())
        o = tf.options()
        styles = "".join(f"<label style='display:block'><input type='radio' name='style' value='{k}'{' checked' if k == o['style'] else ''}> "
                         f"{e(v['label'])}</label>" for k, v in tf.STYLES.items())
        colors = "".join(f"<option value='{k}'{' selected' if k == o['color'] else ''}>{e(v[0])}</option>" for k, v in tf.COLORS.items())
        sizes = "".join(f"<option value='{k}'{' selected' if k == o['size'] else ''}>{e(v[0])}</option>" for k, v in tf.SIZES.items())
        pos = "".join(f"<option value='{k}'{' selected' if k == o['position'] else ''}>{e(v)}</option>" for k, v in tf.POSITIONS.items())
        made = ""
        makes = _makes(jid)
        for m in makes:
            res = m.get("result") or {}
            vids = ""
            for k, x in enumerate(res.get("clips") or [] if m["state"] == "done" else [], 1):
                vids += (f"<div><video controls preload='metadata' src='/auto/clips/{m['id']}/clip/{k}.mp4'></video>"
                         f"<div class='muted' style='font-size:12px' translate='no'>{e(Path(str(x.get('saved') or x.get('file') or '')).name)}</div></div>")
            open_btn = (f"<form method='post' action='/auto/clips/{m['id']}/reveal' style='margin:0'><button class='btn2'>Show in folder</button></form>"
                        if m["state"] == "done" else "")
            n = len(m.get("clips") or [])
            made += (f"<div class='vo-job' style='border-top:1px solid var(--line);padding:10px 0'><div class='cl-row'>"
                     f"<b><span>Clips:</span> <span translate='no'>{n}</span></b>"
                     f"<span class='muted' style='font-size:13px' translate='no'>{e(str(m.get('created_at') or '')[:16].replace('T', ' '))}</span>{open_btn}"
                     f"<form method='post' action='/auto/clips/{m['id']}/delete' style='margin:0' onsubmit=\"return confirm(window.ME_L?ME_L('Delete it?'):'Delete it?')\">"
                     f"<input type='hidden' name='back' value='/auto/clips/{jid}'><button class='btn2'>Delete</button></form></div>"
                     + (f"<div class='muted' style='font-size:13px'><span>Saved in</span> <span class='ae-path' translate='no'>{e(res.get('folder') or '')}</span></div>"
                        if m["state"] == "done" and res.get("folder") else "")
                     + _state_html(m, f"/auto/clips/{jid}") + (f"<div class='cl-row cl-made' style='margin-top:8px'>{vids}</div>" if vids else "")
                     + "</div>")
        made_html = (f"<div class='card' id='made' style='margin-bottom:14px'><h2 style='margin-top:0'>Made clips</h2>{made}</div>" if made else "")
        body = (head + made_html
                + f"<form method='post' action='/auto/clips/{jid}/make' class='cl-grid' "
                  f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button:not([type=button])').forEach(x=>x.disabled=true),0)\">"
                  f"<div class='card'><h2 style='margin-top:0'><span>Clips found:</span> <span translate='no'>{len(cands)}</span></h2>"
                  f"<div class='muted' style='font-size:13px'>The likeliest first. Read the words, play a part, tick the ones to make. "
                  f"Start and end can be changed (minutes:seconds).</div>{rows}</div>"
                  f"<div class='cl-side'><div class='card'><video id='clPlayer' controls preload='metadata' "
                  f"src='/auto/clips/{jid}/source' style='width:100%;max-height:300px;background:#000;border-radius:8px'></video>"
                  f"<div class='muted' style='font-size:12px' data-pmsg></div></div>"
                  f"<div class='card' style='margin-top:12px'><b>Format</b><div class='cl-choices'>{fmts}</div>"
                  f"<b>Picture</b><div class='cl-choices'>{frs}</div>"
                  f"<label style='display:block;margin-top:6px'><input type='checkbox' name='captions' value='1' {'checked' if last['captions'] else ''}> "
                  f"Captions with the words</label><div class='vo-styles' style='margin:6px 0 0 4px;font-size:14px'>{styles}</div>"
                  f"<div class='cl-row' style='margin-top:6px;font-size:14px'><span>Color</span><select name='color'>{colors}</select>"
                  f"<span>Size</span><select name='size'>{sizes}</select><select name='position'>{pos}</select></div>"
                  f"<label style='display:block;margin-top:6px'><input type='checkbox' name='title' value='1' {'checked' if last['title'] else ''}> "
                  f"The first sentence as a title at the top (3 s)</label>"
                  f"<div style='margin-top:12px'><button class='ae-big'>Make the ticked clips</button></div>"
                  f"<div class='muted' style='font-size:13px;margin-top:6px'>Saved next to the saved reels, in a folder of this video. "
                  f"The face is kept in the frame; two people apart are shown whole on blurred edges.</div></div></div></form>")
        script = _PLAYER_JS + ("setTimeout(()=>location.reload(),4000);" if _busy(makes) else "")
        return page("Clips from a long video", body, script)

    @app.post("/auto/clips/<jid>/make")
    def clips_make(jid):
        f = request.form
        try:
            cands = {c["id"]: c for c in cl.candidates(jid)}
            chosen = []
            for cid in f.getlist("pick"):
                if cid not in cands:
                    continue
                s, en = _secs(f.get(f"s_{cid}")), _secs(f.get(f"e_{cid}"))
                if s is None or en is None:
                    raise cl.ClipsError("Start and end: write minutes:seconds, for example 12:30.5.")
                chosen.append({"s": s, "e": en, "first": f.get(f"first_{cid}") or cands[cid]["first"]})
            chosen.sort(key=lambda c: c["s"])
            mid = cl.new_make(jid, chosen, f.get("format", "vertical"), f.get("framing", "face"), f.get("captions") == "1",
                              {"style": f.get("style"), "color": f.get("color"), "size": f.get("size"), "position": f.get("position")},
                              f.get("title") == "1")
        except vo.VoiceError as exc:
            return err_page(str(exc), f"/auto/clips/{jid}")
        return redirect(f"/auto/clips/{jid}#made")

    def _back(default="/auto/clips") -> str:
        b = str(request.form.get("back") or "")
        return b if re.fullmatch(r"/auto/clips(/[0-9]{8}-[0-9]{6}-[0-9a-f]{6})?", b) else default

    def _parent(jid: str) -> str:
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return "/auto/clips"
        return f"/auto/clips/{j['find']}" if j.get("kind") == "clips_make" and j.get("find") else (
            f"/auto/clips/{jid}" if j.get("kind") == "clips_find" else "/auto/clips")

    @app.post("/auto/clips/<jid>/stop")
    def clips_stop(jid):
        back = _parent(jid)
        try:
            vo.cancel_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), back)
        return redirect(back)

    @app.post("/auto/clips/<jid>/retry")
    def clips_retry(jid):
        try:
            vo.retry_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), _back())
        return redirect(_back(_parent(jid)))

    @app.post("/auto/clips/<jid>/delete")
    def clips_delete(jid):
        back = _back(_parent(jid))
        try:
            j = vo.read_job(jid)
            if not str(j.get("kind") or "").startswith("clips_"):
                raise vo.VoiceError("No such job.")
            if j.get("kind") == "clips_find":            # its made clips go with it (the files saved in the folder stay)
                for m in _makes(jid):
                    if m["state"] != "working":
                        vo.cancel_job(m["id"])
                        vo.delete_job(m["id"])
            vo.delete_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), back)
        return redirect(back if back != f"/auto/clips/{jid}" else "/auto/clips")

    @app.get("/auto/clips/<jid>/source")
    def clips_source(jid):
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return "not found", 404
        p = Path(str(j.get("source") or ""))
        if j.get("kind") != "clips_find" or not p.is_file():
            return "not found", 404
        return send_file(p, mimetype="video/mp4", conditional=True, max_age=0)

    @app.get("/auto/clips/<jid>/clip/<int:n>.mp4")
    def clips_file(jid, n):
        try:
            d = vo._job_dir(jid)
        except vo.VoiceError:
            return "not found", 404
        p = d / f"clip_{int(n):02d}.mp4"
        if not p.is_file():
            return "not found", 404
        return send_file(p, mimetype="video/mp4", conditional=True, max_age=0)

    @app.post("/auto/clips/<jid>/reveal")
    def clips_reveal(jid):
        from . import auto_edit as ae
        back = _parent(jid)
        try:
            res = vo.read_job(jid).get("result") or {}
        except vo.VoiceError as exc:
            return err_page(str(exc), back)
        first = next((Path(str(x.get("saved"))) for x in res.get("clips") or [] if x.get("saved") and Path(str(x["saved"])).is_file()), None)
        if first is not None:
            ae.open_path(first, reveal=True)
        elif res.get("folder") and Path(res["folder"]).is_dir():
            ae.open_path(Path(res["folder"]))
        return redirect(back + "#made")


_PICK_JS = ("document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=async()=>{const f=b.closest('form'),"
            "m=f.querySelector('[data-msg]');if(m)m.textContent=(window.ME_L?ME_L('A Windows window is open — it may be behind this window.'):"
            "'A Windows window is open — it may be behind this window.');try{const r=await fetch('/api/auto/pick-voice-file',{method:'POST',"
            "headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'video'})});const x=await r.json();"
            "if(x.path){f.querySelector('input[name=path]').value=x.path;if(m)m.textContent=''}else if(m)m.textContent=x.error||''}"
            "catch(e){if(m)m.textContent=String(e)}});")

_PLAYER_JS = ("(()=>{const v=document.getElementById('clPlayer');if(!v)return;let end=null;"
              "const sec=s=>{const p=String(s||'').trim().replace(',','.').split(':').map(Number);if(p.some(isNaN))return null;"
              "return p.reduce((a,x)=>a*60+x,0)};"
              "document.querySelectorAll('[data-play]').forEach(b=>b.onclick=()=>{const id=b.dataset.play,"
              "f=b.closest('form'),s=sec(f.querySelector('[name=\"s_'+id+'\"]').value),e=sec(f.querySelector('[name=\"e_'+id+'\"]').value);"
              "if(s===null)return;end=e;v.currentTime=s;v.play().catch(()=>{});});"
              "v.addEventListener('timeupdate',()=>{if(end!==null&&v.currentTime>=end){v.pause();end=null}});"
              "v.addEventListener('error',()=>{const m=document.querySelector('[data-pmsg]');if(m)m.textContent=(window.ME_L?"
              "ME_L('This video cannot be played in the page (its format); the clips are made all the same.'):"
              "'This video cannot be played in the page (its format); the clips are made all the same.')});})();")
