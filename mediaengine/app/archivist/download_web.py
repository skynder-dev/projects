"""The page "Download by a link" (Media -> Download by a link): a video, or chosen videos of a profile, channel or
playlist, downloaded by yt-dlp into the Downloaded folder (downloader.py); then studied, retold or converted."""
from __future__ import annotations

import re
from pathlib import Path

from flask import jsonify, redirect, request

from . import downloader as D

_STEP = {"checking": "Checking the PC…", "ytdlp": "Downloading yt-dlp (the downloader)…",
         "deno": "Downloading deno (what yt-dlp needs for YouTube)…", "testing": "Starting the downloader for a test…"}
CSS = """<style>
.dl-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.dl-row input[type=url],.dl-row input[name=url]{flex:1;min-width:240px}
.dl-list{width:100%;border-collapse:collapse;font-size:14px}
.dl-list td,.dl-list th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.dl-list td.n{white-space:nowrap;text-align:right}
.dl-job{border-top:1px solid var(--line);padding:12px 0}
.dl-file{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0}
.dl-file form{margin:0}
</style>"""


def _clock(s) -> str:
    try:
        s = int(float(s or 0))
    except (TypeError, ValueError):
        return ""
    if not s:
        return ""
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def _views(v) -> str:
    try:
        v = int(v or 0)
    except (TypeError, ValueError):
        return ""
    if not v:
        return ""
    return f"{v / 1e6:.1f}M" if v >= 1e6 else f"{v / 1e3:.0f}K" if v >= 1e3 else str(v)


def _date(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if re.fullmatch(r"\d{8}", str(d or "")) else ""


def register(app, page, err_page, e, human_bytes):

    def _install_card() -> str:
        s = D.status()
        if s["state"] == "running":
            pct = int(100 * s["done"] / s["total"]) if s.get("total") else 3
            return (f"<div class='card' id='dlInstall'><h2 style='margin-top:0'>Installing the downloader</h2>"
                    f"<div class='ae-bar'><i id='dlBar' style='width:{max(3, pct)}%'></i></div>"
                    f"<div style='margin-top:8px' id='dlStep'>{e(_STEP.get(s.get('step'), ''))}</div>"
                    f"<form method='post' action='/media/download/cancel' style='margin-top:10px'><button class='btn2'>Cancel</button></form></div>")
        err = f"<div class='errbox' style='margin-bottom:10px'>{e(s.get('error') or '')}</div>" if s["state"] == "failed" else ""
        mb = s["size"] / 1e6
        return (f"<div class='card'>{err}<h2 style='margin-top:0'>Install the downloader</h2>"
                f"<div>MediaEngine downloads videos with yt-dlp (free, open) and deno (free, open: what yt-dlp needs for "
                f"YouTube), downloaded once from their GitHub pages into the data folder and checked.</div>"
                f"<div class='ae-path' translate='no'>{e(str(D.ROOT))}</div>"
                f"<div class='muted' style='font-size:13px;margin-top:6px'>Only public videos: no sign-in and no passwords. "
                f"MediaEngine goes online only when you press a button.</div>"
                f"<form method='post' action='/media/download/install' style='margin-top:12px'><button class='ae-big'>"
                f"<span>Install</span> <span translate='no'>({mb:.0f}</span> <span>MB)</span></button></form></div>")

    def _studies_line(j: dict) -> str:
        """How far the videos' studies are, and - two or more studied - their common style (an author's)."""
        from .cartoon import reference as R
        from . import voice as vo
        ids = [x for x in (j.get("result") or {}).get("studies") or [] if R.STUDY_ID.fullmatch(str(x))]
        states = []
        for x in ids:
            try:
                states.append(vo.read_job(x).get("state"))
            except Exception:
                states.append("gone")
        done = [x for x, st in zip(ids, states) if st == "done"]
        busy = sum(1 for st in states if st in ("working", "waiting", "queued", "running"))
        made = R.style_of_download(j["id"])
        out = (f"<span>Studied:</span> <span translate='no'>{len(done)}/{len(ids)}</span> "
               f"<a href='/auto/cartoon#films'>Cartoon Studio</a>")
        if made:
            out += (f" · <a href='/auto/cartoon/style/{made['id']}'>Their common style</a>")
        elif len(done) >= 2 and not busy:
            refs = "".join(f"<input type='hidden' name='ref' value='{x}'>" for x in done)
            out += (f"<form method='post' action='/auto/cartoon/style/new' style='margin:6px 0 0'>{refs}"
                    f"<input type='hidden' name='name' value='{e(j.get('author') or '')}'>"
                    f"<input type='hidden' name='source' value='download:{j['id']}'>"
                    f"<button class='btn2'>Make their common style</button></form>")
        return f"<div class='muted' style='font-size:13px;margin-top:4px'>{out}</div>"

    def _job_row(j: dict) -> str:
        res = j.get("result") or {}
        when = e(str(j.get("created_at") or "")[:16].replace("T", " "))
        n_items = len(j.get("items") or [])
        who = (f"<span translate='no'>{e(j['author'])}</span> · " if j.get("author") else "")
        title = (f"<b>{who}<span translate='no'>{n_items}</span> <span>videos</span></b>" if n_items > 1
                 else f"<b translate='no'>{e(j.get('title') or '')}</b>")
        head = (f"<div class='dl-row'>{title}"
                f"<span class='muted' style='font-size:13px' translate='no'>{when}</span></div>")
        st = j["state"]
        if st in ("working", "waiting"):
            body = (f"<div class='ae-bar' style='margin-top:6px'><i data-bar style='width:{int(100 * float(j.get('progress') or 0))}%'></i></div>"
                    f"<div class='muted' style='font-size:13px' data-step translate='no'>{e(j.get('now') or '')}</div>"
                    + ("<div class='muted' style='font-size:13px'>Waiting (another download first).</div>" if st == "waiting" else "")
                    + f"<form method='post' action='/media/download/{j['id']}/stop' style='margin-top:6px'><button class='btn2'>Stop</button></form>")
        else:
            files = ""
            for n, f in enumerate(res.get("files") or []):
                p = str(f.get("file") or "")
                files += (f"<div class='dl-file'><span translate='no'>{e(Path(p).name)}</span>"
                          f"<span class='muted' style='font-size:13px'>{e(human_bytes(int(f.get('size') or 0)))}</span>"
                          f"<form method='post' action='/auto/cartoon/study'><input type='hidden' name='video' value='{e(p)}'>"
                          f"<input type='hidden' name='listen' value='1'><button class='btn2'>Study its rhythm</button></form>"
                          f"<form method='post' action='/auto/cartoon/write'><input type='hidden' name='video' value='{e(p)}'>"
                          f"<button class='btn2'>Write a story from it</button></form>"
                          f"<form method='post' action='/media/download/{j['id']}/reveal/{n}'><button class='btn2'>Show in folder</button></form></div>")
            errs = "".join(f"<div class='errbox' style='margin-top:6px'><span translate='no'>{e(x.get('title') or x.get('url') or '')}</span>"
                           f": <span>{e(x.get('error') or '')}</span></div>" for x in (res.get("errors") or []))
            msg = ""
            if st == "interrupted":
                msg = "<div class='muted' style='margin-top:6px'>Interrupted (MediaEngine was closed).</div>"
            elif st in ("failed", "stopped") and not res.get("errors"):
                msg = f"<div class='errbox' style='margin-top:6px'>{e(res.get('error') or 'Failed')}</div>"
            studies = _studies_line(j) if res.get("studies") else ""
            body = (files + errs + msg + studies
                    + "<div class='dl-row' style='margin-top:6px'>"
                    + (f"<form method='post' action='/media/download/{j['id']}/retry' style='margin:0'><button class='btn2'>Try again</button></form>"
                       if st in ("failed", "stopped", "interrupted") or res.get("errors") else "")
                    + f"<form method='post' action='/media/download/{j['id']}/delete' style='margin:0'><button class='btn2'>Remove from the list</button></form></div>")
        return f"<div class='dl-job' data-job='{j['id']}' data-state='{st}'>{head}{body}</div>"

    @app.get("/media/download")
    def download_home():
        jobs = D.list_jobs()
        rows = "".join(_job_row(j) for j in jobs)
        if D.installed():
            form = (f"<div class='card'><h2 style='margin-top:0'>A link</h2>"
                    f"<form method='post' action='/media/download/look' class='dl-row' "
                    f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                    f"<input name='url' maxlength='600' placeholder='https://… (a video, a profile, a channel or a playlist)' required>"
                    f"<button class='ae-big'>Show the videos</button></form>"
                    f"<div class='muted' style='font-size:13px;margin-top:6px'><span>A profile or a channel: its videos are listed, "
                    f"you choose which to download (at most</span> <span translate='no'>{D.MAX_VIDEOS}</span> <span>at once, up to 1080p). "
                    f"YouTube, TikTok, archive.org and many other sites; only public videos.</span></div>"
                    f"<div class='callout' style='margin-top:10px;font-size:13px'>Download only videos you may use: to study "
                    f"them, watch them or cut your own clips. Putting someone else's video out as your own breaks their "
                    f"rights and the sites' rules.</div></div>")
        else:
            form = _install_card()
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'><a href='/media'>Media</a></div><h1>Download by a link</h1>"
                f"<div class='lead'>A video from the internet onto this PC - or several from a profile - to study its rhythm, "
                f"retell its story as a cartoon, cut clips or convert.</div></div>{form}"
                + (f"<div class='card' id='jobs' style='margin-top:14px'><h2 style='margin-top:0'>Downloads</h2>{rows}"
                   f"<div class='muted' style='font-size:13px;margin-top:8px'><span>Saved in</span> <span class='ae-path' translate='no'>"
                   f"{e(str(D.folder()))}</span></div></div>" if rows else "")
                + (f"<details style='margin-top:14px'><summary class='muted'>Remove the downloader</summary>"
                   f"<form method='post' action='/media/download/remove' style='margin-top:8px'><button class='btn2'>Remove</button> "
                   f"<span class='muted' style='font-size:13px'>The downloaded videos stay.</span></form></details>" if D.installed() else ""))
        return page("Download by a link", body, _JS)

    @app.post("/media/download/look")
    def download_look():
        try:
            r = D.look(request.form.get("url") or "")
        except D.DownloadError as exc:
            return err_page(str(exc), "/media/download")
        ents = r["entries"][:D.MAX_LIST]
        if not ents:
            return err_page("No videos were found at this link.", "/media/download")
        hidden = "".join(f"<input type='hidden' name='u{n}' value='{e(x['url'])}'><input type='hidden' name='t{n}' value='{e(x['title'])}'>"
                         for n, x in enumerate(ents))
        if r["kind"] == "video":
            x = ents[0]
            pick = (f"<input type='hidden' name='pick' value='0'>"
                    f"<div><b translate='no'>{e(x['title'])}</b></div>"
                    f"<div class='muted' style='font-size:13px' translate='no'>{e(r.get('uploader') or '')} {e(_clock(x.get('duration')))}</div>")
        else:
            rowsx = "".join(f"<tr data-views='{int(x.get('views') or 0)}' data-n='{n}'><td><input type='checkbox' name='pick' value='{n}'></td>"
                            f"<td translate='no'>{e(x['title'])}</td><td class='n' translate='no'>{e(_clock(x.get('duration')))}</td>"
                            f"<td class='n' translate='no'>{e(_views(x.get('views')))}</td><td class='n' translate='no'>{e(_date(x.get('date')))}</td></tr>"
                            for n, x in enumerate(ents))
            pick = (f"<div class='dl-row' style='margin-bottom:8px'><button type='button' class='btn2' data-pick='views'>The 10 most viewed</button>"
                    f"<button type='button' class='btn2' data-pick='first'>The first 10</button>"
                    f"<button type='button' class='btn2' data-pick='none'>None</button>"
                    f"<span class='muted' style='font-size:13px'><span>Chosen:</span> <span data-count translate='no'>0</span></span></div>"
                    f"<div style='overflow-x:auto'><table class='dl-list'><tr><th></th><th>Title</th><th class='n'>Length</th>"
                    f"<th class='n'>Views</th><th class='n'>Date</th></tr>{rowsx}</table></div>")
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'><a href='/media/download'>Download by a link</a></div>"
                f"<h1 translate='no'>{e(r.get('title') or r.get('uploader') or r['url'])}</h1>"
                + (f"<div class='lead'><span translate='no'>{len(ents)}</span> <span>videos</span></div>" if r["kind"] == "list" else "")
                + f"</div><div class='card'><form method='post' action='/media/download/start' "
                f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<input type='hidden' name='source' value='{e(r['url'])}'>"
                f"<input type='hidden' name='author' value='{e(r.get('uploader') or '')}'>"
                + (f"<input type='hidden' name='inbox' value='{e(request.form.get('inbox'))}'>"
                   if re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}", str(request.form.get("inbox") or "")) else "")
                + f"{hidden}{pick}"
                f"<label style='display:block;margin-top:10px'><input type='checkbox' name='study' value='1'> Study each one's rhythm after "
                f"(Cartoon Studio: shots, pace, the opening)</label>"
                f"<div style='margin-top:12px'><button class='ae-big'>Download</button></div></form></div>")
        return page("Download by a link", body, _PICK_JS)

    @app.post("/media/download/start")
    def download_start():
        f = request.form
        items = []
        for n in f.getlist("pick")[:D.MAX_VIDEOS + 1]:
            if re.fullmatch(r"\d{1,3}", str(n)):
                items.append({"url": f.get(f"u{n}") or "", "title": f.get(f"t{n}") or ""})
        try:
            jid = D.new_download(items, f.get("study") == "1", f.get("source") or "", f.get("author") or "")
        except D.DownloadError as exc:
            return err_page(str(exc), "/media/download")
        iid = str(f.get("inbox") or "")
        if iid:
            from . import inbox
            try:
                inbox.attach_job(iid, jid)
                inbox.set_state(iid, "done")
            except inbox.InboxError:
                pass
        return redirect("/media/download#jobs")

    @app.post("/media/download/install")
    def download_install():
        D.start_install()
        return redirect("/media/download")

    @app.post("/media/download/cancel")
    def download_cancel():
        D.cancel_install()
        return redirect("/media/download")

    @app.post("/media/download/remove")
    def download_remove():
        try:
            D.remove()
        except D.DownloadError as exc:
            return err_page(str(exc), "/media/download")
        return redirect("/media/download")

    def _act(jid: str, fn):
        try:
            fn(jid)
        except D.DownloadError as exc:
            return err_page(str(exc), "/media/download")
        return redirect("/media/download#jobs")

    @app.post("/media/download/<jid>/stop")
    def download_stop(jid):
        return _act(jid, D.stop)

    @app.post("/media/download/<jid>/retry")
    def download_retry(jid):
        return _act(jid, D.retry)

    @app.post("/media/download/<jid>/delete")
    def download_delete(jid):
        return _act(jid, D.delete)

    @app.post("/media/download/<jid>/reveal/<int:n>")
    def download_reveal(jid, n):
        try:
            files = (D.read_job(jid).get("result") or {}).get("files") or []
        except D.DownloadError:
            return redirect("/media/download")
        if 0 <= n < len(files) and Path(str(files[n].get("file") or "")).is_file():
            from . import auto_edit as ae
            ae.open_path(Path(files[n]["file"]), reveal=True)
        return redirect("/media/download#jobs")

    @app.get("/api/download/status")
    def download_status():
        s = D.status()
        step = _STEP.get(s.get("step"), "")
        try:
            from .i18n import ui_language
            if ui_language() == "ru":
                from .auto_edit_ru import PHRASES
                step = PHRASES.get(step, step)
        except Exception:
            pass
        jobs = {j["id"]: {"state": j["state"], "progress": j.get("progress") or 0, "now": j.get("now") or ""} for j in D.list_jobs(20)}
        return jsonify({"install": {k: s.get(k) for k in ("state", "done", "total", "error")} | {"step": step}, "jobs": jobs})


_JS = ("(()=>{const live=()=>[...document.querySelectorAll('[data-job]')].filter(x=>['working','waiting'].includes(x.dataset.state));"
       "const inst=document.getElementById('dlInstall');if(!live().length&&!inst)return;const t=async()=>{let r;try{r=await (await "
       "fetch('/api/download/status',{cache:'no-store'})).json()}catch(e){setTimeout(t,4000);return}"
       "if(inst){if(r.install.state!=='running'){location.reload();return}const b=document.getElementById('dlBar');"
       "if(b&&r.install.total)b.style.width=Math.max(3,Math.round(100*r.install.done/r.install.total))+'%';"
       "const s=document.getElementById('dlStep');if(s)s.textContent=r.install.step||''}"
       "let changed=false;live().forEach(x=>{const s=r.jobs[x.dataset.job];if(!s)return;if(s.state!==x.dataset.state){changed=true;return}"
       "const b=x.querySelector('[data-bar]');if(b)b.style.width=Math.round(100*(s.progress||0))+'%';"
       "const n=x.querySelector('[data-step]');if(n)n.textContent=s.now||''});if(changed){location.reload();return}"
       "setTimeout(t,2000)};setTimeout(t,2000)})();")
_PICK_JS = ("(()=>{const boxes=[...document.querySelectorAll('input[name=pick][type=checkbox]')];const c=document.querySelector('[data-count]');"
            "const upd=()=>{if(c)c.textContent=boxes.filter(b=>b.checked).length};boxes.forEach(b=>b.addEventListener('change',upd));"
            "document.querySelectorAll('[data-pick]').forEach(btn=>btn.onclick=()=>{boxes.forEach(b=>b.checked=false);"
            "const rows=[...document.querySelectorAll('tr[data-n]')];let pick=[];"
            "if(btn.dataset.pick==='views')pick=rows.filter(r=>+r.dataset.views>0).sort((a,b)=>b.dataset.views-a.dataset.views).slice(0,10);"
            "else if(btn.dataset.pick==='first')pick=rows.slice(0,10);pick.forEach(r=>{const b=r.querySelector('input');if(b)b.checked=true});upd()});upd()})();")
