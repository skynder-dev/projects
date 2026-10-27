"""The page "Clips from a long video" (Auto Edit -> Clips): listen to a podcast / stream / interview once, tick the
parts worth a clip, get vertical clips with the face in the frame, the sound and captions (clips.py)."""
from __future__ import annotations

import re
from pathlib import Path

from flask import jsonify, redirect, request, send_file

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
.cl-thumb{float:right;max-width:160px;max-height:160px;border-radius:8px;margin:0 0 6px 10px}
.cl-made video{width:150px;max-height:270px;border-radius:8px;background:#000}
.cl-made .cl-row{align-items:flex-start}
.cl-choices label{display:inline-flex;gap:6px;align-items:center;margin:3px 12px 3px 0}
.cl-ready{position:sticky;top:8px;z-index:5}
</style>"""
_STEP = {"starting": "Starting…", "reading": "Reading the sound of the video…", "listening": "Listening to the speech…",
         "checking": "Checking the clips…"}
_WHY = {"a question at the start": "a question at the start", "a strong opening": "a strong opening", "numbers": "numbers",
        "strong words": "strong words", "lively": "lively", "laughter": "laughter"}
_JOB_ID = r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}"


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
    """Seconds from 75.5, 1:15.5, 123:45 or 1:02:03.5 (the same reading as the page's player)."""
    parts = str(v if v is not None else "").strip().replace(",", ".").split(":")
    if not 1 <= len(parts) <= 3 or not all(re.fullmatch(r"\d{1,6}(\.\d{1,3})?", p) for p in parts):
        return None
    if any("." in p for p in parts[:-1]):
        return None
    t = 0.0
    for p in parts:
        t = t * 60 + float(p)
    return t if t <= 24 * 3600 else None


def _label(j: dict) -> str:
    step = str(j.get("step") or "")
    key, _, part = step.partition(" ")
    return (f"<span>Clip</span> <span translate='no'>{part}</span>" if key == "clip" else _STEP.get(key, "Working…"))


def register(app, page, err_page, e, human_bytes):

    def _bar(j: dict) -> str:
        return (f"<div class='ae-bar' style='margin-top:6px'><i data-bar style='width:{int(100 * float(j.get('progress') or 0))}%'></i></div>"
                f"<div class='muted' style='font-size:13px' data-step>{_label(j) if '<span>' in _label(j) else e(_label(j))}</div>"
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
            more = "".join(f"<div class='errbox' style='margin-top:4px'>{e(x.get('error') or '')}</div>"
                           for x in (res.get("failed") or [])[1:6])
            again = ("Make the rest" if j.get("kind") == "clips_make" and res.get("clips") else "Try again")
            return (f"<div class='errbox' style='margin-top:6px'>{e(msg)}</div>{more}"
                    f"<form method='post' action='/auto/clips/{j['id']}/retry' style='margin-top:6px'>"
                    f"<input type='hidden' name='back' value='{e(back)}'><button>{again}</button></form>")
        return ""

    def _block(j: dict, inner: str) -> str:
        """A job's part of a page; the page asks every few seconds how far it is (it is never reloaded under the
        user's hands)."""
        return (f"<div class='vo-job' style='border-top:1px solid var(--line);padding:10px 0' data-job='{j['id']}' "
                f"data-state='{j['state']}'>{inner}</div>")

    def _finds() -> list[dict]:
        return [j for j in vo.list_jobs(100000) if j.get("kind") == "clips_find"]

    def _makes(fid: str) -> list[dict]:
        return [j for j in vo.list_jobs(100000) if j.get("kind") == "clips_make" and j.get("find") == fid]

    def _lengths(current: str) -> str:
        return "".join(f"<label><input type='radio' name='length' value='{k}' {'checked' if k == current else ''}> "
                       f"{e(v)}</label>" for k, v in cl.LENGTH_LABELS.items())

    @app.get("/auto/clips")
    def clips_home():
        s = vo.status()
        last = cl.last_choices()
        langs = "".join(f"<option value='{c}'" + (" translate='no'" if c else "") + f">{e(n)}</option>" for c, n in
                        [("", "Detect by itself"), ("en", "English"), ("ru", "Русский"), ("es", "Español"), ("de", "Deutsch"),
                         ("fr", "Français"), ("it", "Italiano"), ("pt", "Português"), ("uk", "Українська")])
        addon = ("" if s.get("installed") else
                 "<div class='callout card' style='margin-bottom:12px'><b>Finding clips needs the voice add-on</b> (it listens "
                 "to the speech). It is installed once, free.<div style='margin-top:8px'><a class='btn' href='/auto/voice'>"
                 "Install the voice add-on</a></div></div>")
        try:
            cl.sweep_orphans()
        except Exception:
            pass
        rows = ""
        for j in _finds():
            res = j.get("result") or {}
            info = (f"<span>clips found:</span> <b translate='no'>{int(res.get('candidates') or 0)}</b>" if j["state"] == "done" else "")
            rows += _block(j, f"<div class='cl-row'>"
                              f"<a href='/auto/clips/{j['id']}'><b translate='no'>{e(j.get('title') or '')}</b></a>"
                              f"<span class='muted' style='font-size:13px' translate='no'>{e(str(j.get('created_at') or '')[:16].replace('T', ' '))}</span>"
                              f"<span class='muted' style='font-size:13px'>{info}</span>"
                              + (f"<a class='btn btn2' href='/auto/clips/{j['id']}'>Open</a>" if j["state"] == "done" else "")
                              + ("" if j["state"] == "working" else
                                 f"<form method='post' action='/auto/clips/{j['id']}/delete' style='margin:0' onsubmit=\"return confirm(window.ME_L?"
                                 f"ME_L('Delete it? The clips saved in the folder stay.'):'Delete it? The clips saved in the folder stay.')\">"
                                 f"<input type='hidden' name='back' value='/auto/clips'><button class='btn2'>Delete</button></form>")
                              + "</div>" + _state_html(j, "/auto/clips"))
        listed = (f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Videos listened to</h2>{rows}</div>" if rows else "")
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Clips from a long video</h1>"
                f"<div class='lead'>A podcast, a stream or an interview: MediaEngine listens to it once and lists the parts that "
                f"make good short clips, with their words - the likeliest first. Tick the ones you want: they are made "
                f"vertical, with the face in the frame, the sound and captions. The video itself is only read.</div></div>"
                f"{_READY}{addon}<div class='card'><h2 style='margin-top:0'>Find clips</h2>"
                f"<form method='post' action='/auto/clips/new' onsubmit=\"setTimeout(()=>this.querySelectorAll('button:not([type=button])').forEach(x=>x.disabled=true),0)\">"
                f"<div class='cl-row'><input class='vo-wide' name='path' required placeholder='The long video, for example a podcast episode' "
                f"style='flex:1;min-width:260px'><button type='button' class='btn2' data-pick='video'>Choose…</button></div>"
                f"<div class='cl-choices' style='margin-top:10px'><b>Length of a clip</b><br>{_lengths(last['length'])}</div>"
                f"<div class='cl-row' style='margin-top:8px'><span>Language of the speech</span><select name='language'>{langs}</select></div>"
                f"<div class='muted' style='font-size:13px;margin-top:8px'>Listening takes about 5-15 minutes for an hour of video. "
                f"You can close this page meanwhile; the PC does not go to sleep.</div>"
                f"<div style='margin-top:10px'><button class='ae-big'>Find clips</button> <span class='muted' data-msg></span></div>"
                f"</form></div>{listed}"
                f"<div class='muted' style='font-size:13px;margin-top:12px'>Use only videos you may cut: your own, or footage a "
                f"clipping campaign gives you to cut.</div>")
        return page("Clips from a long video", body, _PICK_JS + _POLL_JS)

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
        res = j.get("result") or {}
        heard = (vo._job_dir(jid) / "heard.json").is_file()
        head = (f"{CSS}<div class='pagehead'><div class='eyebrow'><a href='/auto/clips'>Clips from a long video</a></div>"
                f"<h1 translate='no'>{e(src.name)}</h1><div class='lead ae-path' translate='no'>{e(str(src))}</div></div>{_READY}")
        cands = cl.candidates(jid) if j["state"] == "done" else []
        length_key = str(j.get("length") or "medium")
        again = (f"<form method='post' action='/auto/clips/{jid}/length' class='cl-row cl-choices' style='margin-top:8px'>"
                 f"<b>Length of a clip</b> {_lengths(length_key)}<button class='btn2'>Find again for this length</button>"
                 f"<span class='muted' style='font-size:13px'>(in a moment: the speech is not listened to again)</span></form>"
                 if heard and j["state"] in ("done", "failed") else "")
        if j["state"] != "done":
            body = head + f"<div class='card'>{_block(j, _state_html(j, f'/auto/clips/{jid}'))}{again}</div>"
            return page("Clips from a long video", body, _POLL_JS)
        last = cl.last_choices()
        rows = ""
        for c in cands:
            cid = e(c["id"])
            why = "".join(f" <span class='cl-why'>{e(_WHY.get(w, w))}</span>" for w in c.get("why") or [])
            rest = c["text"][len(c["first"]):].strip() if c["text"].startswith(c["first"]) else c["text"]
            rows += (f"<div class='cl-c'><input type='checkbox' name='pick' value='{cid}'>"
                     f"<div><img class='cl-thumb' src='/auto/clips/{e(jid)}/thumb/{cid}.jpg' alt='' loading='lazy' onerror=\"this.remove()\">"
                     f"<div class='cl-row' style='gap:8px'><span class='cl-score' title='How likely a good clip'>{int(c['score'])}</span>"
                     f"<span class='cl-times cl-row' style='gap:4px'><input name='s_{cid}' value='{e(_mmss(c['s']))}' title='Start'>"
                     f"<span>–</span><input name='e_{cid}' value='{e(_mmss(c['e']))}' title='End'></span>"
                     f"<span class='muted'><span translate='no'>{round(float(c['e']) - float(c['s']))}</span> <span>s</span></span>"
                     f"<button type='button' class='btn2 vo-mini' data-play='{cid}'>▶ Play</button>{why}</div>"
                     f"<div class='cl-first' translate='no'>{e(c['first'])}</div>"
                     f"<div class='cl-text' translate='no'>{e(rest[:700])}{'…' if len(rest) > 700 else ''}</div>"
                     f"<input name='t_{cid}' maxlength='{tf.TEXT_MAX}' placeholder='Title at the top (optional)' "
                     f"style='margin-top:6px;width:100%;max-width:420px'>"
                     f"<input type='hidden' name='first_{cid}' value='{e(c['first'])}'></div></div>")
        fmts = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if k == last['format'] else ''}> {e(v)}</label>"
                       for k, v in cl.FORMAT_LABELS.items())
        frs = "".join(f"<label><input type='radio' name='framing' value='{k}' {'checked' if k == last['framing'] else ''}> {e(v)}</label>"
                      for k, v in cl.FRAMINGS.items())
        ppl = "".join(f"<label><input type='radio' name='people' value='{k}' {'checked' if k == last['people'] else ''}> {e(v)}</label>"
                      for k, v in cl.PEOPLE.items())
        o = tf.options()
        styles = "".join(f"<label style='display:block'><input type='radio' name='style' value='{k}'{' checked' if k == o['style'] else ''}> "
                         f"{e(v['label'])}</label>" for k, v in tf.STYLES.items())
        colors = "".join(f"<option value='{k}'{' selected' if k == o['color'] else ''}>{e(v[0])}</option>" for k, v in tf.COLORS.items())
        sizes = "".join(f"<option value='{k}'{' selected' if k == o['size'] else ''}>{e(v[0])}</option>" for k, v in tf.SIZES.items())
        pos = "".join(f"<option value='{k}'{' selected' if k == o['position'] else ''}>{e(v)}</option>" for k, v in tf.POSITIONS.items())
        made = ""
        for m in _makes(jid):
            mres = m.get("result") or {}
            vids = ""
            for x in (mres.get("clips") or []):               # (also the ones made before a Stop or a failed clip)
                k = int(x.get("n") or 0)
                if k <= 0:
                    continue
                vids += (f"<div><video controls preload='metadata' src='/auto/clips/{m['id']}/clip/{k}.mp4'></video>"
                         f"<div class='muted' style='font-size:12px' translate='no'>{e(Path(str(x.get('saved') or x.get('file') or '')).name)}</div></div>")
            open_btn = (f"<form method='post' action='/auto/clips/{m['id']}/reveal' style='margin:0'><button class='btn2'>Show in folder</button></form>"
                        if mres.get("clips") else "")
            delete = ("" if m["state"] in ("working", "waiting") else
                      f"<form method='post' action='/auto/clips/{m['id']}/delete' style='margin:0' onsubmit=\"return confirm(window.ME_L?"
                      f"ME_L('Delete it? The clips saved in the folder stay.'):'Delete it? The clips saved in the folder stay.')\">"
                      f"<input type='hidden' name='back' value='/auto/clips/{jid}'><button class='btn2'>Delete</button></form>")
            n = len(m.get("clips") or [])
            made += _block(m, f"<div class='cl-row'><b><span>Clips:</span> <span translate='no'>{n}</span></b>"
                              f"<span class='muted' style='font-size:13px' translate='no'>{e(str(m.get('created_at') or '')[:16].replace('T', ' '))}</span>"
                              f"{open_btn}{delete}</div>"
                              + (f"<div class='muted' style='font-size:13px'><span>Saved in</span> <span class='ae-path' translate='no'>{e(mres.get('folder') or '')}</span></div>"
                                 if mres.get("clips") and mres.get("folder") else "")
                              + _state_html(m, f"/auto/clips/{jid}") + (f"<div class='cl-row cl-made' style='margin-top:8px'>{vids}</div>" if vids else ""))
        made_html = (f"<div class='card' id='made' style='margin-bottom:14px'><h2 style='margin-top:0'>Made clips</h2>{made}</div>" if made else "")
        body = (head + made_html
                + f"<form method='post' action='/auto/clips/{jid}/make' class='cl-grid' data-dirty-watch "
                  f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button:not([type=button])').forEach(x=>x.disabled=true),0)\">"
                  f"<div class='card'><h2 style='margin-top:0'><span>Clips found:</span> <span translate='no'>{len(cands)}</span></h2>"
                  f"<div class='muted' style='font-size:13px'>The likeliest first. Read the words, play a part, tick the ones to make. "
                  f"Start and end can be changed (minutes:seconds).</div>{rows}</div>"
                  f"<div class='cl-side'><div class='card'><video id='clPlayer' controls preload='metadata' "
                  f"src='/auto/clips/{jid}/source' style='width:100%;max-height:300px;background:#000;border-radius:8px'></video>"
                  f"<div class='muted' style='font-size:12px' data-pmsg></div></div>"
                  f"<div class='card' style='margin-top:12px'><b>Format</b><div class='cl-choices'>{fmts}</div>"
                  f"<b>Picture</b><div class='cl-choices'>{frs}</div>"
                  f"<b>Two or more people side by side</b><div class='cl-choices'>{ppl}</div>"
                  f"<label style='display:block;margin-top:6px'><input type='checkbox' name='captions' value='1' {'checked' if last['captions'] else ''}> "
                  f"Captions with the words</label><div class='vo-styles' style='margin:6px 0 0 4px;font-size:14px'>{styles}</div>"
                  f"<div class='cl-row' style='margin-top:6px;font-size:14px'><span>Color</span><select name='color'>{colors}</select>"
                  f"<span>Size</span><select name='size'>{sizes}</select><select name='position'>{pos}</select></div>"
                  f"<label style='display:block;margin-top:6px'><input type='checkbox' name='title' value='1' {'checked' if last['title'] else ''}> "
                  f"The first sentence as a title at the top (3 s) - when a clip has no title of its own</label>"
                  f"<div class='cl-row' style='margin-top:12px'><button class='ae-big'>Make the ticked clips</button>"
                  f"<button class='btn2' name='top' value='5' title='The first five of the list, as they are'>Make the 5 likeliest</button></div>"
                  f"<div class='muted' style='font-size:13px;margin-top:6px'>Saved next to the saved reels, in a folder of this video. "
                  f"The face is kept in the frame (someone walking: the frame goes with them); two people apart: each in a "
                  f"half, one above the other; people side by side or more: all of them, as big as they fit, on blurred edges; "
                  f"a streamer's camera over a game: the camera above, the game below.</div></div></div></form>"
                + f"<div class='card' style='margin-top:14px'>{again}</div>")
        return page("Clips from a long video", body, _PLAYER_JS + _POLL_JS)

    @app.post("/auto/clips/<jid>/length")
    def clips_length(jid):
        try:
            cl.rescore(jid, request.form.get("length", ""))
        except vo.VoiceError as exc:
            return err_page(str(exc), f"/auto/clips/{jid}")
        return redirect(f"/auto/clips/{jid}")

    @app.post("/auto/clips/<jid>/make")
    def clips_make(jid):
        f = request.form
        try:
            ranked = cl.candidates(jid)
            cands = {c["id"]: c for c in ranked}
            chosen = []
            ids = f.getlist("pick")
            if f.get("top"):                               # ("Make the 5 likeliest": no ticking needed)
                n_top = int(f.get("top")) if str(f.get("top")).isdigit() else 5
                ids = [c["id"] for c in ranked[:max(1, min(cl.MAX_CHOSEN, n_top))]]
            for cid in ids:
                if cid not in cands:
                    continue
                s = _secs(f.get(f"s_{cid}")) if f.get(f"s_{cid}") is not None else float(cands[cid]["s"])   # (not sent: as found)
                en = _secs(f.get(f"e_{cid}")) if f.get(f"e_{cid}") is not None else float(cands[cid]["e"])
                if s is None or en is None:
                    raise cl.ClipsError("Start and end: write minutes:seconds, for example 12:30.5.")
                chosen.append({"s": s, "e": en, "first": f.get(f"first_{cid}") or cands[cid]["first"], "title": f.get(f"t_{cid}") or ""})
            chosen.sort(key=lambda c: c["s"])
            cl.new_make(jid, chosen, f.get("format", "vertical"), f.get("framing", "face"), f.get("captions") == "1",
                        {"style": f.get("style"), "color": f.get("color"), "size": f.get("size"), "position": f.get("position")},
                        f.get("title") == "1", f.get("people") or "all")
        except vo.VoiceError as exc:
            return err_page(str(exc), f"/auto/clips/{jid}")
        return redirect(f"/auto/clips/{jid}#made")

    @app.get("/api/clips/status")
    def clips_status():
        """How far the clip jobs shown on a page are (the page asks every few seconds)."""
        out = {}
        for jid in str(request.args.get("ids") or "").split(",")[:50]:
            if not re.fullmatch(_JOB_ID, jid):
                continue
            try:
                j = vo.read_job(jid)
            except vo.VoiceError:
                out[jid] = {"state": "gone"}
                continue
            lab = re.sub(r"<[^>]+>", "", _label(j))
            try:
                from .i18n import ui_language
                if ui_language() == "ru":
                    from .auto_edit_ru import PHRASES
                    lab = PHRASES.get(lab, lab.replace("Clip ", "Клип ", 1))
            except Exception:
                pass
            out[jid] = {"state": j["state"], "progress": float(j.get("progress") or 0), "step": lab}
        return jsonify(out)

    def _back(default="/auto/clips") -> str:
        b = str(request.form.get("back") or "")
        return b if re.fullmatch(rf"/auto/clips(/{_JOB_ID})?", b) else default

    def _parent(jid: str) -> str:
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return "/auto/clips"
        return f"/auto/clips/{j['find']}" if j.get("kind") == "clips_make" and j.get("find") else (
            f"/auto/clips/{jid}" if j.get("kind") == "clips_find" else "/auto/clips")

    def _clips_job(jid: str) -> dict:
        j = vo.read_job(jid)
        if not str(j.get("kind") or "").startswith("clips_"):
            raise vo.VoiceError("No such job.")
        return j

    @app.post("/auto/clips/<jid>/stop")
    def clips_stop(jid):
        back = _parent(jid)
        try:
            _clips_job(jid)
            vo.cancel_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), back)
        return redirect(back)

    @app.post("/auto/clips/<jid>/retry")
    def clips_retry(jid):
        try:
            _clips_job(jid)
            vo.retry_job(jid)
        except vo.VoiceError as exc:
            return err_page(str(exc), _back())
        return redirect(_back(_parent(jid)))

    @app.post("/auto/clips/<jid>/delete")
    def clips_delete(jid):
        back = _back(_parent(jid))
        try:
            j = _clips_job(jid)
            if j.get("kind") == "clips_find":            # its made clips go with it (the files saved in the folder stay)
                makes = _makes(jid)
                if any(m["state"] == "working" for m in makes):
                    raise vo.VoiceError("Clips of this video are being made: stop them first.")
                for m in makes:
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

    @app.get("/auto/clips/<jid>/thumb/<cid>.jpg")
    def clips_thumb(jid, cid):
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return "not found", 404
        try:
            t = cl.thumb(jid, cid)
        except Exception:
            t = None
        if not t:
            return "not found", 404
        return send_file(t, mimetype="image/jpeg", max_age=86400)

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
            res = _clips_job(jid).get("result") or {}
        except vo.VoiceError as exc:
            return err_page(str(exc), back)
        first = next((Path(str(x.get("saved"))) for x in res.get("clips") or [] if x.get("saved") and Path(str(x["saved"])).is_file()), None)
        if first is not None:
            ae.open_path(first, reveal=True)
        elif res.get("folder") and Path(res["folder"]).is_dir():
            ae.open_path(Path(res["folder"]))
        return redirect(back + "#made")


_READY = ("<div class='callout card cl-ready' data-ready hidden><b>Ready.</b> <span>Refresh the page to see it.</span> "
          "<button type='button' class='btn2' onclick='location.reload()'>Refresh</button></div>")

_PICK_JS = ("document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=async()=>{const f=b.closest('form'),"
            "m=f.querySelector('[data-msg]');if(m)m.textContent=(window.ME_L?ME_L('A Windows window is open — it may be behind this window.'):"
            "'A Windows window is open — it may be behind this window.');try{const r=await fetch('/api/auto/pick-voice-file',{method:'POST',"
            "headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'video'})});const x=await r.json();"
            "if(x.path){f.querySelector('input[name=path]').value=x.path;if(m)m.textContent=''}else if(m)m.textContent=x.error||''}"
            "catch(e){if(m)m.textContent=String(e)}});")

# the jobs of a page asked every 3 s: their bars move; when one is finished the page is reloaded - unless something was
# typed or ticked on it (then a "Ready - refresh" note: nothing the user did is lost)
_POLL_JS = ("(()=>{let dirty=false;document.querySelectorAll('form').forEach(f=>{f.addEventListener('input',()=>dirty=true);"
            "f.addEventListener('change',()=>dirty=true)});const live=()=>[...document.querySelectorAll('[data-job]')]"
            ".filter(x=>['working','waiting'].includes(x.dataset.state));if(!live().length)return;"
            "const tick=async()=>{const js=live();if(!js.length)return;let r;try{r=await (await fetch('/api/clips/status?ids='+"
            "js.map(x=>x.dataset.job).join(','))).json()}catch(e){setTimeout(tick,5000);return}let changed=false;"
            "js.forEach(x=>{const s=r[x.dataset.job];if(!s)return;if(s.state!==x.dataset.state){changed=true;x.dataset.state=s.state;return}"
            "const b=x.querySelector('[data-bar]');if(b)b.style.width=Math.round(100*(s.progress||0))+'%';"
            "const t=x.querySelector('[data-step]');if(t&&s.step)t.textContent=s.step});"
            "if(changed){if(!dirty&&![...document.querySelectorAll('video')].some(v=>!v.paused)){location.reload();return}"
            "const n=document.querySelector('[data-ready]');if(n)n.hidden=false}setTimeout(tick,3000)};setTimeout(tick,3000)})();")

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
