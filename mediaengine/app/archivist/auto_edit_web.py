"""Auto Edit pages for the existing Archivist/MediaEngine Flask UI."""
from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from flask import jsonify, redirect, request, send_file

from . import auto_edit as ae

PAGE_CSS = r"""
<style>
.ae-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.ae-state{font-size:12px;font-weight:700;letter-spacing:.4px;padding:3px 8px;border-radius:999px;border:1px solid var(--line2)}
.ae-state.READY{color:#0b1;border-color:#2c6}.ae-state.REVIEW{color:var(--orange);border-color:var(--orange)}
.ae-state.PROCESSING{color:var(--cyan);border-color:var(--cyan)}.ae-state.ATTENTION{color:var(--red);border-color:var(--red)}
.ae-choices{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px}.ae-choices label{display:flex;gap:8px;align-items:center;
 padding:10px 14px;border:1px solid var(--line2);border-radius:12px;cursor:pointer;background:var(--card2)}
.ae-choices input{accent-color:var(--orange)}.ae-choices label:has(input:checked){border-color:var(--orange);box-shadow:0 0 0 1px var(--orange) inset}
.ae-choices label.off{opacity:.45;cursor:not-allowed}
.ae-big{font-size:17px;padding:12px 22px}
.ae-bar{height:12px;border-radius:8px;background:#0b1118;border:1px solid var(--line);overflow:hidden}.ae-bar i{display:block;height:100%;background:var(--orange);transition:width .4s}
.ae-player{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:16px}@media(max-width:1000px){.ae-player{grid-template-columns:1fr}}
.ae-video{display:block;margin:0 auto;max-width:100%;max-height:72vh;background:#000;border-radius:12px}
.ae-strip{display:flex;height:34px;border-radius:8px;overflow:hidden;margin:10px 0;border:1px solid var(--line)}
.ae-strip button{border:0;border-right:1px solid #0008;border-radius:0;padding:0;font-size:12px;color:#000;background:var(--orange);cursor:pointer}
.ae-strip button:nth-child(even){background:#e8b765}.ae-strip button.on{outline:2px solid #fff;outline-offset:-2px}
.ae-seg{display:grid;grid-template-columns:28px 1fr auto;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}
.ae-seg.on{background:#d7a34a14}
.ae-files td,.ae-files th{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left}
.ae-path{font-family:Consolas,monospace;font-size:13px;word-break:break-all}
.ae-done{border:1px solid var(--orange);box-shadow:0 0 0 1px var(--orange) inset;margin-bottom:14px}
.ae-strip.film{height:64px}.ae-strip.film button{background-size:cover;background-position:center;color:#fff;
 text-shadow:0 1px 3px #000;font-weight:800;display:flex;align-items:flex-end;justify-content:flex-start;padding:3px 5px}
</style>
"""


def _when(iso) -> str:
    """'2026-10-11T08:12:55' -> '2026-10-11 08:12' (local time, as stored)."""
    t = str(iso or "")
    return t[:16].replace("T", " ") if len(t) >= 16 and t[10:11] == "T" else t


def _fmt_s(x) -> str:
    try:
        x = float(x)
    except Exception:
        return "—"
    m, s = divmod(x, 60)
    return f"{int(m)}:{s:04.1f}"


def register(app, layout, e, human_bytes):
    """Attach Auto Edit routes to the existing app (called from web.create_app)."""

    def page(title, body, script=""):
        return layout(title, PAGE_CSS + body, script)      # translated (if Russian) for every page in i18n.install

    def err_page(msg, back="/auto"):
        return page("Auto Edit", f"<div class='card'><h2>Could not continue</h2><div class='errbox' style='margin-bottom:12px'>{e(msg)}</div>"
                                 f"<a class='btn btn2' href='{e(back)}'>Back</a></div>"), 400

    # ------------------------------------------------------------ home

    @app.get("/auto")
    def ae_home():
        ae.ensure_schema()
        ms = ae.model_status()
        projects = ae.list_projects(include_archived=request.args.get("archived") == "1")
        cards = ""
        for p in projects:
            acc = next((r for r in p["revisions"] if r["id"] == p["accepted_revision_id"]), None)
            last = p["revisions"][-1] if p["revisions"] else None
            ref = acc or last
            preset = ae.FORMATS.get(ref["settings"]["format"], {}).get("short", "") if ref else ""
            length = f"{ref['settings']['length']} s" if ref else ""
            exp = ae.export_row(p["last_export_id"]) if p.get("last_export_id") else None
            n_src = len(ae.project_inputs(p)) if p["source_present"] else 0
            acts = f"<a class='btn btn2' href='/auto/p/{p['id']}'>{'Review' if p['revisions'] else 'Open'}</a>"
            if p["accepted_revision_id"]:
                acts += f"<form method='post' action='/auto/p/{p['id']}/export'><button class='btn2'>Export</button></form>"
            if exp:
                acts += (f"<form method='post' action='/auto/export/{exp['id']}/open'><button class='btn2'>Open video</button></form>"
                         f"<form method='post' action='/auto/export/{exp['id']}/reveal'><button class='btn2'>Show in folder</button></form>")
            acts += f"<form method='post' action='/auto/p/{p['id']}/archive'><button class='btn2'>{'Unarchive' if p['archived'] else 'Archive'}</button></form>"
            cards += (f"<div class='card'><a href='/auto/p/{p['id']}' style='display:block'>"
                      f"<div class='row space'><b style='font-size:17px' translate='no'>{e(p['title'])}</b><span class='ae-state {p['state']}'>{p['state']}</span></div>"
                      f"<div class='muted' style='margin-top:6px'>{' · '.join(x for x in (str(n_src) + (' chosen video(s)' if p.get('files') else ' video file(s) in folder'), e((preset + ' ' + length).strip()), str(len(p['revisions'])) + ' revision(s)') if x)}</div>"
                      f"<div class='muted'>{('Last export: ' + e(Path(exp['path']).name)) if exp else 'Not exported yet'}</div></a>"
                      + ("" if p["source_present"] else "<div class='errbox' style='margin-top:6px'>Source videos are not available (drive disconnected?)</div>")
                      + f"<div class='row' style='margin-top:10px;flex-wrap:wrap;gap:6px'>{acts}</div></div>")
        if not cards:
            cards = "<div class='card muted'>No Auto Edit projects yet. Choose a folder with your videos to make the first one.</div>"
        model_note = ("" if ms["ready"] else
                      f"<div class='card callout' style='margin-top:10px'><b>AI model (FAST_LOCAL) not found.</b> "
                      f"<span class='muted'>Without it reels use the clearly labelled <i>Technical only</i> selection. "
                      f"If you have the model (for example in an existing Archivist install), choose its folder: the exact files are verified and copied here.</span>"
                      f"<div class='row' style='margin-top:8px'><button type='button' class='btn2' id='modelBtn'>Choose model folder…</button>"
                      f"<span class='muted' id='modelMsg'></span></div></div>")
        check_btn = "<a class='btn btn2' href='/auto/check' style='float:right'>Check this PC</a>"
        body = f"""<div class='pagehead'>{check_btn}<div class='eyebrow'>MediaEngine</div><h1>Auto Edit</h1>
<div class='lead'>Choose a folder of videos (or single videos), pick length, format and sound, and MediaEngine builds a reel from the best moments.
Your original files are only read, never changed.</div></div>
<div class='card'><h2 style='margin-top:0'>New reel</h2>
<form method='get' action='/auto/new' class='row' style='flex-wrap:wrap' onsubmit="document.getElementById('pickMsg').textContent='Checking the videos… (a few seconds per video)'">
<button type='button' class='ae-big' id='pickBtn'>Choose folder…</button>
<button type='button' class='btn2 ae-big' id='pickFilesBtn'>Choose videos…</button>
<input name='folder' id='folderInput' placeholder='or paste a folder path, e.g. D:\\Videos\\Trip' style='flex:1;min-width:280px'>
<button class='btn btn2 ae-big'>Continue</button></form>
<div class='muted' id='pickMsg' style='margin-top:6px'></div></div>{model_note}
<div class='muted' style='margin-top:8px'><a href='/auto/check'>Check this PC</a> — model, video tools and a 5-second test reel</div>
<div class='section-title row space'><span>My projects</span><a class='muted' href='/auto?archived={'0' if request.args.get('archived')=='1' else '1'}'>{'Hide' if request.args.get('archived')=='1' else 'Show'} archived</a></div>
<div class='ae-grid'>{cards}</div>"""
        script = """
const mb=document.getElementById('modelBtn');
if(mb)mb.onclick=async()=>{const m=document.getElementById('modelMsg');m.textContent='Choose the folder that contains FAST_LOCAL…';
 const r=await fetch('/api/auto/model/import',{method:'POST'});const x=await r.json();m.textContent=x.ok?'Model installed.':(x.error||'Not installed');if(x.ok)setTimeout(()=>location.reload(),800)};
document.getElementById('pickBtn').onclick=async()=>{const m=document.getElementById('pickMsg');m.textContent='A Windows folder window is open — it may be behind this window.';
 try{const r=await fetch('/api/auto/pick-folder',{method:'POST'});const x=await r.json();
 if(x.path){document.getElementById('folderInput').value=x.path;m.textContent='Checking the videos… (a few seconds per video)';location.href='/auto/new?folder='+encodeURIComponent(x.path)}
 else m.textContent=x.error||'No folder chosen.'}catch(e){m.textContent='Folder window failed: '+e}};
document.getElementById('pickFilesBtn').onclick=async()=>{const m=document.getElementById('pickMsg');m.textContent='A Windows window is open — it may be behind this window. Ctrl+click to choose several videos.';
 try{const r=await fetch('/api/auto/pick-files',{method:'POST'});const x=await r.json();
 if(x.files&&x.files.length){m.textContent='Checking the videos…';location.href='/auto/new?'+x.files.map(f=>'file='+encodeURIComponent(f)).join('&')}
 else m.textContent=x.error||'No videos chosen.'}catch(e){m.textContent='Window failed: '+e}};"""
        return page("Auto Edit", body, script)

    @app.route("/auto/check", methods=["GET", "POST"])
    def ae_check():
        rows = ae.system_check()
        def looks_like_path(t):
            return ":\\" in t or t.startswith("/") or "version" in t or "|" in t
        table = "".join(f"<tr><td>{'✅' if r['ok'] else '⚠️'}</td><td><b>{e(r['name'])}</b></td>"
                        f"<td class='{'ae-path' if looks_like_path(r['detail']) else 'muted'}'>{e(r['detail'])}</td></tr>" for r in rows)
        test_html = ""
        ai_ready = ae.model_status()["ready"]
        if request.method == "POST":
            want_ai = request.form.get("mode") == "semantic" and ai_ready
            t = ae.quick_selftest(mode="semantic" if want_ai else "technical")
            if t["ok"]:
                kind = "with the AI model (FAST_LOCAL)" if str(t.get("selection_mode", "")).startswith("FAST_LOCAL") else "Technical only"
                test_html = (f"<div class='card ae-done' style='margin-top:14px'><b>Test reel built {kind} in {t['seconds']} s</b>"
                             f"<div class='muted'>{t.get('duration_s')} s reel from two generated clips · stages: {e(json.dumps(t.get('stages')))}</div></div>")
            else:
                test_html = (f"<div class='card' style='margin-top:14px'><b>Test reel failed after {t['seconds']} s</b>"
                             f"<div class='errbox' style='margin-top:6px'>{e(t['error'])}</div></div>")
        from .config import INSTALL
        builds = ae.other_builds()
        done = request.args.get("removed", "")
        brows = "".join(f"<tr><td><b translate='no'>{e(b['name'])}</b>{(' · built ' + e(b['built'])) if b['built'] else ''}"
                        f"<div class='muted ae-path'>{e(b['path'])}</div></td>"
                        f"<td>{human_bytes(b['bytes'])}</td><td><form method='post' action='/auto/check/remove-build' "
                        f"onsubmit=\"return confirm(document.getElementById('rmq').textContent)\">"
                        f"<input type='hidden' name='name' value='{e(b['name'])}'><button class='btn2'>Remove</button></form></td></tr>"
                        for b in builds)
        builds_html = (f"<div class='card' style='margin-top:14px'><b>Other MediaEngine versions on this PC</b>"
                       f"<div class='muted'>This one: <span class='ae-path'>{e(str(INSTALL))}</span>. Older versions are kept so you can go "
                       f"back to one; remove the ones you no longer need (projects and exports stay).</div>"
                       f"<span id='rmq' hidden>Remove this version? Your projects and exports are not affected.</span>"
                       f"<table class='ae-files' style='margin-top:8px'>{brows}</table></div>") if builds else ""
        if done:
            builds_html = f"<div class='card ae-done' style='margin-top:14px'>Removed {e(done)}.</div>" + builds_html
        body = (f"<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Check this PC</h1>"
                f"<div class='lead'>What MediaEngine needs, and a 5-second test reel made from generated clips (your videos are not used).</div></div>"
                f"<div class='card'><table class='ae-files'>{table}</table></div>"
                f"<form method='post' class='card' style='margin-top:14px' onsubmit=\"const f=this;f.querySelector('span').textContent='Building the test reel… (up to a few minutes)';setTimeout(()=>f.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<button name='mode' value='technical'>Build a test reel</button> "
                + (f"<button name='mode' value='semantic' class='btn2'>Build a test reel with the AI model</button> " if ai_ready else "")
                + f"<span class='muted'></span></form>{test_html}{builds_html}"
                f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
        return page("Check this PC", body)

    @app.post("/auto/check/remove-build")
    def ae_remove_build():
        try:
            freed = ae.delete_build(request.form.get("name", ""))
        except Exception as exc:
            return err_page(str(exc))
        return redirect("/auto/check?removed=" + urllib.parse.quote(request.form.get("name", "") + f" ({human_bytes(freed)})"))

    @app.post("/auto/lang")
    def ae_lang():
        ae.set_ui_language("en" if ae.ui_language() == "ru" else "ru")
        back = request.form.get("back") or "/auto"
        return redirect(back if back.startswith("/auto") else "/auto")

    @app.post("/api/auto/model/import")
    def ae_model_import():
        path = (request.get_json(silent=True) or {}).get("path") or ae.pick_folder("Choose the folder that contains the FAST_LOCAL model")
        if not path:
            return jsonify({"ok": False, "error": "No folder chosen."})
        try:
            res = ae.import_model(path)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)})
        return jsonify({"ok": True, **res})

    @app.post("/api/auto/pick-files")
    def ae_pick_files():
        files = ae.pick_files()
        if files:
            return jsonify({"files": files})
        return jsonify({"files": [], "error": "No videos chosen."})

    @app.post("/api/auto/pick-folder")
    def ae_pick_folder():
        path = ae.pick_folder()
        if path:
            return jsonify({"path": path})
        return jsonify({"path": None, "error": "No folder chosen. You can also paste the path."})

    # ------------------------------------------------------------ setup

    @app.get("/auto/new")
    def ae_new():
        # Only this app's own pages (or a typed URL) may make the server open a folder: a page on another
        # site cannot point it at a network share.
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return err_page("This page can only be opened from MediaEngine itself.")
        folder = request.args.get("folder", "")
        chosen = request.args.getlist("file")
        try:
            scan = ae.scan_files(chosen) if chosen else ae.scan_folder(folder)
        except Exception as exc:
            return err_page(str(exc))
        if not scan["usable"]:
            subs = [] if chosen or scan["files"] else ae.subfolders_with_videos(scan["folder"])
            if subs:
                links = "".join(f"<li><a href='/auto/new?folder={urllib.parse.quote(p_)}' translate='no'>{e(Path(p_).name)}</a> "
                                f"<span class='muted'>· {n} video(s)</span></li>" for p_, n in subs)
                return page("New reel", f"<div class='pagehead'><div class='eyebrow'>Auto Edit · new reel</div>"
                                        f"<h1 translate='no'>{e(Path(scan['folder']).name or scan['folder'])}</h1>"
                                        f"<div class='lead ae-path'>{e(scan['folder'])}</div></div>"
                                        f"<div class='card'><b>No videos directly in this folder.</b> These folders inside it have videos — "
                                        f"open one (or use Choose videos… to pick from several):<ul style='margin:8px 0 0'>{links}</ul></div>")
            return err_page("No readable videos " + ("among the chosen files." if chosen else "in this folder."))
        ms = ae.model_status()
        def file_row(r):
            status = "<span class='badge'>ok</span>" if r["ok"] else "<span class='badge error'>skipped: " + e(r["reason"]) + "</span>"
            dims = (str(r["width"]) + "×" + str(r["height"])) if r["ok"] else ""
            dur = _fmt_s(r["duration_s"]) if r["ok"] else ""
            return f"<tr><td translate='no'>{e(r['name'])}</td><td>{human_bytes(r['bytes'])}</td><td>{dur}</td><td>{dims}</td><td>{status}</td></tr>"
        rows = "".join(file_row(r) for r in scan["files"])
        rec = scan["recommended_length"]
        total = scan["total_s"]
        lengths = "".join(
            f"<label class='{'' if L <= max(rec, total * 0.8) else 'off'}'><input type='radio' name='length' value='{L}' "
            f"{'checked' if L == rec else ''} {'' if L <= max(rec, total * 0.8) else 'disabled'}> {L} s"
            f"{' · recommended' if L == rec else ''}</label>" for L in ae.LENGTHS)
        formats = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if k == 'social_hd' else ''}> {e(v['label'])}</label>"
                          for k, v in ae.FORMATS.items())
        sounds = "".join(f"<label><input type='radio' name='sound' value='{k}' {'checked' if k == 'auto' else ''}> {e(v)}</label>"
                         for k, v in ae.SOUNDS.items())
        mode_html = ("<input type='hidden' name='mode' value='semantic'>" if ms["ready"] else
                     "<div class='callout card' style='margin:6px 0 14px'><b>AI model not available.</b> Without it MediaEngine can only use the "
                     "<b>Technical only</b> selection (sharpness, motion, exposure); it does not understand what happens in the video."
                     "<label style='display:flex;gap:8px;margin-top:8px'><input type='checkbox' name='mode' value='technical' required> "
                     "Build with Technical only</label></div>")
        warn = ("<div class='callout card' style='margin-top:10px'>Only "
                f"{_fmt_s(total)} of usable video — a short reel is recommended (LIMITED_TOTAL_FOOTAGE).</div>" if total < 30 else "")
        src_hidden = ("".join(f"<input type='hidden' name='file' value='{e(x)}'>" for x in scan["files_chosen"]) if scan["files_chosen"]
                      else f"<input type='hidden' name='folder' value='{e(scan['folder'])}'>")
        where = (f"{len(scan['files_chosen'])} chosen video(s) · from {scan['folder']}" if scan["files_chosen"] else scan["folder"])
        body = f"""<div class='pagehead'><div class='eyebrow'>Auto Edit · new reel</div><h1 translate='no'>{e(Path(scan['folder']).name or scan['folder'])}</h1>
<div class='lead ae-path'>{e(where)}</div></div>
<div class='card'><b>{scan['usable']} usable video(s)</b>, total {_fmt_s(total)} · {human_bytes(scan['total_bytes'])}{(' · ' + str(scan['skipped']) + ' skipped') if scan['skipped'] else ''}
<details style='margin-top:8px'><summary class='muted'>Show files</summary><table class='ae-files'><tr><th>File</th><th>Size</th><th>Length</th><th>Frame</th><th></th></tr>{rows}</table></details>{warn}</div>
<form method='post' action='/auto/create' class='card' style='margin-top:14px' onsubmit="this.querySelector('button').disabled=true">
{src_hidden}
<h2 style='margin-top:0'>Length</h2><div class='ae-choices'>{lengths}</div>
<h2>Format</h2><div class='ae-choices'>{formats}</div>
<h2>Sound</h2><div class='ae-choices'>{sounds}</div>{mode_html}
<button class='ae-big'>Create reel</button></form>"""
        return page("New reel", body)

    @app.post("/auto/create")
    def ae_create():
        f = request.form
        try:
            if not f.get("mode"):
                raise ValueError("Without the AI model, tick 'Build with Technical only' to continue.")
            ae.normalize_settings({"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode")},
                                  model_ready=ae.model_status()["ready"])
            ae.check_free_space()
            pid = ae.create_project(f.get("folder"), f.get("title"), files=f.getlist("file") or None)
            ae.start_job(pid, {"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode")})
        except Exception as exc:
            return err_page(str(exc))
        return redirect(f"/auto/p/{pid}")

    # ------------------------------------------------------------ project / review

    @app.get("/auto/p/<int:pid>")
    def ae_project(pid):
        p = ae.project(pid)
        if not p:
            return err_page("Project not found")
        active = next((j for j in p["jobs"] if j["status"] == "running"), None) or next((j for j in reversed(p["jobs"]) if j["status"] == "queued"), None)
        queued = [j for j in p["jobs"] if j["status"] == "queued" and (not active or j["id"] != active["id"])]
        last_job = p["jobs"][0] if p["jobs"] else None
        revs = p["revisions"]
        sel_id = request.args.get("rev", type=int) or p["accepted_revision_id"] or (revs[-1]["id"] if revs else None)
        cur = ae.revision(sel_id) if sel_id else None
        if cur and int(cur["project_id"]) != int(pid):
            cur = None
        parts = [f"""<div class='pagehead row space'><div><div class='eyebrow'>Auto Edit · <span class='ae-state {p['state']}'>{p['state']}</span></div>
<h1 translate='no'>{e(p['title'])}</h1><div class='lead ae-path'>{e((str(len(p['files'])) + ' chosen video(s) · from ' + p['folder']) if p.get('files') else p['folder'])}</div></div>
<div class='row' style='flex-wrap:wrap'><a class='btn btn2' href='/auto'>All projects</a>
<form method='post' action='/auto/p/{pid}/rename' class='row' style='gap:6px'><input name='title' value='{e(p['title'])}' maxlength='80' style='width:200px'><button class='btn2'>Rename</button></form>
<form method='post' action='/auto/p/{pid}/archive'><button class='btn2'>{'Unarchive' if p['archived'] else 'Archive'}</button></form></div></div>"""]
        if not p["source_present"]:
            parts.append("<div class='errbox'>The source videos are not available (drive disconnected?). Revisions and exports are kept; "
                         "new builds are possible when they are back.</div>")
        if active:
            parts.append(f"""<div class='card' id='jobCard' data-job='{active['id']}'><div class='row space'><b id='jobStage'>{e(ae.STAGE_LABEL.get(active['stage'] or 'queued', ''))}</b>
<form method='post' action='/auto/job/{active['id']}/cancel'><button class='btn2'>Cancel</button></form></div>
<div class='ae-bar' style='margin:10px 0'><i id='jobBar' style='width:{active['percent']}%'></i></div>
<div class='muted' id='jobMsg'>{e(active.get('message') or '')}</div>
<div class='muted'>{e(ae.FORMATS[active['settings']['format']]['label'])} · {active['settings']['length']} s · sound {e(active['settings']['sound'])}</div></div>""")
            for q in queued:
                parts.append(f"<div class='card row space' style='margin-top:8px'><span class='muted'>Waiting: {e(ae.FORMATS[q['settings']['format']]['short'])} · "
                             f"{q['settings']['length']} s · sound {e(q['settings']['sound'])}</span>"
                             f"<form method='post' action='/auto/job/{q['id']}/cancel'><button class='btn2'>Cancel</button></form></div>")
        elif last_job and last_job["status"] in ("failed", "cancelled") and (not revs or last_job["id"] > max(r["job_id"] for r in revs)):
            ls_ = last_job["settings"]
            no_ai = ""
            if last_job["status"] == "failed" and ls_.get("mode") == "semantic":
                # an AI-mode failure must not leave the user stuck: offer the clearly labelled technical build
                no_ai = (f"<form method='post' action='/auto/p/{pid}/variant'>"
                         f"<input type='hidden' name='length' value='{ls_['length']}'><input type='hidden' name='format' value='{e(ls_['format'])}'>"
                         f"<input type='hidden' name='sound' value='{e(ls_['sound'])}'><input type='hidden' name='mode' value='technical'>"
                         f"<button class='btn2'>Build without AI (Technical only)</button></form>")
            parts.append(f"""<div class='card'><b>{'Build failed' if last_job['status']=='failed' else 'Build cancelled'}</b>
<div class='{'errbox' if last_job['status']=='failed' else 'muted'}' style='margin:8px 0'>{e(last_job.get('error') or last_job.get('message') or '')}</div>
<div class='row' style='flex-wrap:wrap'><form method='post' action='/auto/job/{last_job['id']}/retry'><button>Retry</button></form>{no_ai}</div></div>""")
        done_x = ae.export_row(request.args.get("exported", type=int) or 0)
        if done_x and int(done_x["project_id"]) == int(pid):
            parts.append(f"""<div class='card ae-done'><div class='eyebrow'>Done</div><h2 style='margin:4px 0'>Your reel is saved</h2>
<div class='ae-path'>{e(done_x['path'])}</div><div class='muted'>{human_bytes(done_x['bytes'])} · checked against the accepted version (SHA-256)</div>
<div class='row' style='margin-top:10px;flex-wrap:wrap'><form method='post' action='/auto/export/{done_x['id']}/open'><button class='ae-big'>Open video</button></form>
<form method='post' action='/auto/export/{done_x['id']}/reveal'><button class='btn2'>Show in folder</button></form>
<button type='button' class='btn2' id='copyDone' data-path='{e(done_x['path'])}'>Copy path</button>
<a class='btn btn2' href='/auto'>All projects</a></div></div>""")
        if cur:
            parts.append(_review_html(p, cur, e))
        elif not active:
            parts.append(_variant_form(pid, None, e, first=True, model_ready=ae.model_status()["ready"]))
        parts.append(_revisions_html(p, cur, e))
        parts.append(_reviews_html(p, e))
        du = ae.project_disk_usage(pid)
        if du["cache_bytes"] or du["versions_bytes"]:
            parts.append(f"<div class='card row space' style='margin-top:14px;flex-wrap:wrap'><span class='muted'>Space used: versions "
                         f"{human_bytes(du['versions_bytes'])} · analysis cache {human_bytes(du['cache_bytes'])}"
                         f"{' (can be freed; the next build then analyses the videos again)' if du['cache_bytes'] else ''}</span>"
                         + (f"<form method='post' action='/auto/p/{pid}/free-cache'><button class='btn2'>Free cache</button></form>" if du["cache_bytes"] else "")
                         + "</div>")
        script = """
const card=document.getElementById('jobCard');
async function pollJob2(){if(!card)return;try{const r=await fetch('/api/auto/job/'+card.dataset.job,{cache:'no-store'});const j=await r.json();
 document.getElementById('jobBar').style.width=j.percent+'%';document.getElementById('jobStage').textContent=j.stage_label+' · '+j.percent+'%';
 const counted=j.total>1&&(j.stage==='render'||j.done>0);const el=Math.round(j.elapsed_s||0);
 // estimate only from real progress, only once there is enough of it (no invented timer)
 let eta='';if(j.status==='running'&&j.percent>=15&&j.percent<100&&el>=20){const left=Math.round(el*(100-j.percent)/j.percent);
  eta=left<60?' · less than a minute left':' · about '+Math.round(left/60)+' min left'}
 document.getElementById('jobMsg').textContent=(counted?(Math.min(j.done+1,j.total)+' of '+j.total+' · '):'')+(j.message||'')+' · '+Math.floor(el/60)+':'+String(el%60).padStart(2,'0')+' elapsed'+eta;
 if(['done','failed','cancelled'].includes(j.status)){location.reload();return}}catch(e){}setTimeout(pollJob2,1000)}
pollJob2();
const v=document.getElementById('reel');
function seekTo(t){if(v){v.currentTime=t;v.play()}}
document.querySelectorAll('[data-seek]').forEach(b=>b.onclick=()=>seekTo(parseFloat(b.dataset.seek)));
if(v){v.ontimeupdate=()=>{document.querySelectorAll('[data-seg]').forEach(x=>{const a=parseFloat(x.dataset.in),b=parseFloat(x.dataset.out);x.classList.toggle('on',v.currentTime>=a&&v.currentTime<b)})}}
document.querySelectorAll('[data-move]').forEach(b=>b.onclick=()=>{const row=b.closest('.ae-edit');const list=row.parentNode;
 if(b.dataset.move==='up'&&row.previousElementSibling)list.insertBefore(row,row.previousElementSibling);
 if(b.dataset.move==='down'&&row.nextElementSibling)list.insertBefore(row.nextElementSibling,row);
 list.querySelectorAll('.ae-edit .pos').forEach((x,i)=>x.textContent=i+1)});
['copyPath','copyDone'].forEach(id=>{const cp=document.getElementById(id);if(cp)cp.onclick=async()=>{const t=cp.dataset.path;try{await navigator.clipboard.writeText(t);cp.textContent='Copied'}catch(e){prompt('Copy this path:',t)}}});
const xb=document.getElementById('exportToBtn');
if(xb)xb.onclick=async()=>{const m=document.getElementById('exportMsg');m.textContent='A Windows folder window is open — it may be behind this window.';
 try{const r=await fetch('/api/auto/pick-folder',{method:'POST'});const x=await r.json();
 if(x.path){document.getElementById('exportDest').value=x.path;document.getElementById('exportForm').submit()}else m.textContent='No folder chosen.'}catch(e){m.textContent='Folder window failed: '+e}};
"""
        return page(p["title"], "".join(parts), script)

    @app.get("/api/auto/job/<int:jid>")
    def ae_job_api(jid):
        j = ae.job(jid)
        if not j:
            return jsonify({"error": "not found"}), 404
        out = {k: j[k] for k in ("id", "status", "stage", "stage_label", "done", "total", "message", "percent", "error", "revision_id")}
        out["elapsed_s"] = ae.job_elapsed_s(j)
        if ae.ui_language() == "ru":
            from .auto_edit_ru import PHRASES
            out["stage_label"] = PHRASES.get(out["stage_label"], out["stage_label"])
        return jsonify(out)

    @app.post("/auto/job/<int:jid>/cancel")
    def ae_cancel(jid):
        j = ae.job(jid)
        ae.cancel_job(jid)
        return redirect(f"/auto/p/{j['project_id']}" if j else "/auto")

    @app.post("/auto/job/<int:jid>/retry")
    def ae_retry(jid):
        j = ae.job(jid)
        if not j:
            return err_page("Job not found")
        try:
            ae.start_job(j["project_id"], j["settings"])
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{j['project_id']}")
        return redirect(f"/auto/p/{j['project_id']}")

    @app.post("/auto/p/<int:pid>/variant")
    def ae_variant(pid):
        f = request.form
        try:
            base = ae.revision(int(f.get("base_revision_id") or f.get("revision_id") or 0))
            if base and int(base["project_id"]) != int(pid):
                base = None
            bs = base["settings"] if base else {}
            mode = bs.get("mode") or f.get("mode") or ("semantic" if ae.model_status()["ready"] else None)
            if not mode:
                raise ValueError("Without the AI model, choose Technical only explicitly on the new-reel screen.")
            settings = {"length": f.get("length") or bs.get("length"), "format": f.get("format") or bs.get("format"),
                        "sound": f.get("sound") or bs.get("sound"), "mode": mode}
            if f.get("rechoose"):
                # "Let MediaEngine choose again": automatic selection without the removed moments
                settings["exclude"] = sorted(set(bs.get("exclude", [])) | set(f.getlist("remove")))
            else:
                # A preset/length/sound variant keeps the base revision's choices (exclusions, manual edits)
                settings.update({k: bs[k] for k in ("exclude", "selection", "trims") if bs.get(k)})
            ae.start_job(pid, settings)
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/edit")
    def ae_edit(pid):
        f = request.form
        removed = set(f.getlist("remove"))
        selection, trims = [], {}
        try:
            base = ae.revision(int(f.get("revision_id") or 0))
            base_trims = (base["settings"].get("trims") or {}) if base and int(base["project_id"]) == int(pid) else {}
            for eid in f.getlist("row"):
                if eid in removed:
                    continue
                rep_id = f.get(f"replace_{eid}") or ""
                use = rep_id or eid
                if use in selection:
                    continue
                selection.append(use)
                if not rep_id:
                    da, db = ae.parse_seconds(f.get(f"def_in_{eid}") or 0), ae.parse_seconds(f.get(f"def_out_{eid}") or 0)
                    ra, rb = (f.get(f"in_{eid}") or "").strip(), (f.get(f"out_{eid}") or "").strip()
                    a = ae.parse_seconds(ra) if ra else da   # an emptied field means "unchanged"
                    b = ae.parse_seconds(rb) if rb else db
                    if abs(a - da) > 0.05 or abs(b - db) > 0.05:
                        trims[use] = [a, b]
                    elif eid in base_trims:
                        trims[use] = base_trims[eid]       # keep an earlier trim the user did not touch
            add = f.get("add") or ""
            if add and add not in selection:
                selection.append(add)
            if not selection:
                return err_page("Keep at least one moment.", f"/auto/p/{pid}")
            settings = {"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode"),
                        "selection": selection, "trims": trims}
            ae.start_job(pid, settings)
        except ValueError as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        except Exception as exc:
            return err_page("Could not apply the edits: " + str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/accept")
    def ae_accept(pid):
        try:
            ae.accept(pid, int(request.form.get("revision_id")))
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/revert")
    def ae_revert(pid):
        try:
            ae.revert(pid)
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/export")
    def ae_export(pid):
        try:
            dest = (request.form.get("dest") or "").strip()
            res = ae.export_accepted(pid, dest or None, remember=bool(dest))
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}?exported={res['export_id']}")

    @app.post("/auto/export/<int:eid>/<action>")
    def ae_export_action(eid, action):
        x = ae.export_row(eid)
        if not x or action not in ("open", "reveal"):
            return err_page("Export not found")
        if not ae.open_path(Path(x["path"]), reveal=(action == "reveal")):
            return err_page("The exported file is not available any more: " + x["path"], f"/auto/p/{x['project_id']}")
        return redirect(f"/auto/p/{x['project_id']}")

    @app.post("/auto/p/<int:pid>/free-cache")
    def ae_free_cache(pid):
        try:
            ae.clear_work_cache(pid)
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/rename")
    def ae_rename(pid):
        try:
            ae.rename_project(pid, request.form.get("title"))
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/archive")
    def ae_archive(pid):
        p = ae.project(pid)
        if p:
            ae.archive_project(pid, not p["archived"])
        return redirect("/auto")

    @app.get("/auto/rev/<int:rid>/video")
    def ae_rev_video(rid):
        r = ae.revision(rid)
        if not r or not Path(r["video_path"]).is_file():
            return "not found", 404
        return send_file(r["video_path"], mimetype="video/mp4", conditional=True)

    # ------------------------------------------------------------ blind comparison

    @app.post("/auto/p/<int:pid>/compare")
    def ae_compare_start(pid):
        try:
            rid = ae.start_review(pid, int(request.form.get("a") or 0), int(request.form.get("b") or 0))
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/review/{rid}")

    @app.get("/auto/review/<int:rid>")
    def ae_review_page(rid):
        rv = ae.review(rid)
        if not rv:
            return err_page("Comparison not found")
        pid = rv["project_id"]
        p = ae.project(pid)
        L, R = ae.revision(rv["left_revision_id"]), ae.revision(rv["right_revision_id"])

        def player(side):
            return (f"<div class='card'><h2 style='margin-top:0'>{'A' if side == 'left' else 'B'}</h2>"
                    f"<video class='ae-video' controls preload='metadata' src='/auto/review/{rid}/video/{side}'></video></div>")
        if rv["decided_at"]:
            def who(r):
                f = ae.FORMATS.get(r["settings"]["format"], {}).get("short", "")
                return f"R{int(r['number']):03d} ({e(f)} · {r['settings']['length']} s · {'edited by you' if r['settings'].get('selection') else 'automatic'})"
            verdict = {"left": f"You preferred A = {who(L)} over B = {who(R)}.", "right": f"You preferred B = {who(R)} over A = {who(L)}.",
                       "same": f"You found them about the same: A = {who(L)}, B = {who(R)}."}[rv["choice"]]
            bottom = (f"<div class='card ae-done' style='margin-top:14px'><b>Result</b><div style='margin-top:6px'>{verdict}</div>"
                      + (f"<div class='muted' style='margin-top:4px'>Note: <span translate='no'>{e(rv['note'])}</span></div>" if rv.get("note") else "")
                      + f"<div class='row' style='margin-top:10px'><a class='btn btn2' href='/auto/p/{pid}'>Back to the project</a></div></div>")
        else:
            bottom = (f"<form method='post' action='/auto/review/{rid}/decide' class='card' style='margin-top:14px'>"
                      f"<div class='muted'>Watch both. Which one would you rather publish? Versions and settings are hidden until you decide.</div>"
                      f"<input name='note' maxlength='500' placeholder='Why? (optional, e.g. better start, fewer shaky shots)' style='width:100%;margin:10px 0'>"
                      f"<div class='row' style='flex-wrap:wrap'><button name='choice' value='left' class='ae-big'>A is better</button>"
                      f"<button name='choice' value='right' class='ae-big'>B is better</button>"
                      f"<button name='choice' value='same' class='btn2'>About the same</button></div></form>")
        body = (f"<div class='pagehead'><div class='eyebrow'>Auto Edit · blind comparison</div><h1 translate='no'>{e(p['title'])}</h1></div>"
                f"<div class='ae-player'>{player('left')}{player('right')}</div>{bottom}")
        return page("Blind comparison", body)

    @app.get("/auto/review/<int:rid>/video/<side>")
    def ae_review_video(rid, side):
        rv = ae.review(rid)
        if not rv or side not in ("left", "right"):
            return "not found", 404
        r = ae.revision(rv["left_revision_id" if side == "left" else "right_revision_id"])
        if not r or not Path(r["video_path"]).is_file():
            return "not found", 404
        return send_file(r["video_path"], mimetype="video/mp4", conditional=True)

    @app.post("/auto/review/<int:rid>/decide")
    def ae_review_decide(rid):
        try:
            ae.decide_review(rid, request.form.get("choice", ""), request.form.get("note", ""))
        except Exception as exc:
            return err_page(str(exc), f"/auto/review/{rid}")
        return redirect(f"/auto/review/{rid}")

    @app.get("/auto/rev/<int:rid>/thumb/<int:pos>.jpg")
    def ae_rev_thumb(rid, pos):
        t = ae.revision_thumb(rid, pos)
        if not t:
            return "not found", 404
        return send_file(t, mimetype="image/jpeg", max_age=86400)

    @app.get("/auto/p/<int:pid>/source")
    def ae_source(pid):
        src = ae.source_file(pid, request.args.get("name", ""))
        if not src:
            return "not found", 404
        return send_file(src, conditional=True)


def _variant_form(pid, rev, e, first=False, model_ready=True):
    s = rev["settings"] if rev else {"length": 15, "format": "social_hd", "sound": "auto"}
    lengths = "".join(f"<label><input type='radio' name='length' value='{L}' {'checked' if int(s['length']) == L else ''}> {L} s</label>" for L in ae.LENGTHS)
    formats = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if s['format'] == k else ''}> {e(v['short'])}</label>" for k, v in ae.FORMATS.items())
    sounds = "".join(f"<label><input type='radio' name='sound' value='{k}' {'checked' if s['sound'] == k else ''}> {e(k.title())}</label>" for k in ae.SOUNDS)
    base = f"<input type='hidden' name='base_revision_id' value='{rev['id']}'>" if rev else ""
    mode = ""
    if not rev and not model_ready:
        mode = ("<label class='muted' style='display:flex;gap:8px;margin:8px 0'><input type='checkbox' name='mode' value='technical' required> "
                "AI model not available — build with Technical only (sharpness, motion, exposure)</label>")
    note = "" if first else "The current revision stays as it is. It keeps its removed moments and your edits; changing only format or sound reuses the analysis."
    return (f"<form method='post' action='/auto/p/{pid}/variant' class='card' style='margin-top:14px' onsubmit=\"this.querySelector('button').disabled=true\">{base}"
            f"<h2 style='margin-top:0'>{'Build reel' if first else 'Make a variant'}</h2>"
            f"<div class='muted'>{note}</div>"
            f"<div class='ae-choices'>{lengths}</div><div class='ae-choices'>{formats}</div><div class='ae-choices'>{sounds}</div>{mode}"
            f"<button>{'Build' if first else 'Make variant'}</button></form>")


def _sound_label(requested, res):
    audio = (res or {}).get("audio") or {}
    applied, reason = audio.get("applied"), str((audio.get("decision") or {}).get("reason") or "")
    if requested == "auto" and applied == "source":
        return "Auto → original sound"
    if requested == "auto" and applied == "mute":
        if "mixed" in reason:
            # accepted P11 rule: no jumps between sound and silence; the user can force the sound
            return "Auto → muted (some moments have no sound; choose Source to keep the sound)"
        return "Auto → muted (no useful sound found)"
    return requested.title()


def _review_html(p, rev, e):
    res = rev.get("result") or {}
    segs = res.get("segments") or []
    total = float(rev.get("duration_s") or res.get("actual_duration_s") or 1) or 1
    is_acc = p["accepted_revision_id"] == rev["id"]
    fmt = ae.FORMATS.get(rev["settings"]["format"], {})
    strip = "".join(
        f"<button data-seek='{s['reel_in_s']}' data-seg data-in='{s['reel_in_s']}' data-out='{s['reel_out_s']}' "
        f"style=\"flex:{max(0.2, s['reel_out_s'] - s['reel_in_s']):.3f};background-image:url('/auto/rev/{rev['id']}/thumb/{s['position']}.jpg')\" "
        f"title='{e(s['source_name'])} {_fmt_s(s['source_in_s'])}–{_fmt_s(s['source_out_s'])}'>{s['position']}</button>"
        for s in segs)
    in_reel = {s["event_id"] for s in segs}
    pool = [c for c in (res.get("candidate_pool") or []) if c["event_id"] not in in_reel][:40]
    opts = "".join(f"<option value='{e(c['event_id'])}' translate='no'>{e(c['source_name'])} {_fmt_s(c['start_s'])}–{_fmt_s(c['end_s'])} · score {float(c['score']):.2f}</option>" for c in pool)

    def edit_row(s):
        eid = e(s["event_id"])
        badge = " · edge trimmed" if s.get("camera_drop_trim") else (" · your trim" if s.get("manual_trim") else "")
        repl = (f"<label class='muted'>replace with <select name='replace_{eid}' style='max-width:260px'><option value=''>— keep —</option>{opts}</select></label>"
                if opts else "")
        return (f"<div class='ae-seg ae-edit' data-seg data-in='{s['reel_in_s']}' data-out='{s['reel_out_s']}'><b class='pos'>{s['position']}</b>"
                f"<div><div><span translate='no'>{e(s['source_name'])}</span> <span class='muted'>· source {_fmt_s(s['source_in_s'])}–{_fmt_s(s['source_out_s'])}{badge}</span></div>"
                f"<div class='row' style='gap:8px;margin-top:4px;flex-wrap:wrap'><button type='button' class='btn2' data-seek='{s['reel_in_s']}'>Play in reel</button>"
                f"<a class='btn btn2' style='font-size:13px' target='_blank' href='/auto/p/{p['id']}/source?name={e(urllib.parse.quote(s['source_name']))}#t={s['source_in_s']},{s['source_out_s']}'>View in source</a></div>"
                f"<div class='row' style='gap:8px;margin-top:6px;flex-wrap:wrap'><label class='muted'>from <input name='in_{eid}' value='{s['source_in_s']:.1f}' inputmode='decimal' style='width:72px'></label>"
                f"<label class='muted'>to <input name='out_{eid}' value='{s['source_out_s']:.1f}' inputmode='decimal' style='width:72px'> s</label>{repl}</div>"
                f"<input type='hidden' name='row' value='{eid}'><input type='hidden' name='def_in_{eid}' value='{s['source_in_s']:.1f}'><input type='hidden' name='def_out_{eid}' value='{s['source_out_s']:.1f}'></div>"
                f"<div class='row' style='gap:4px'><button type='button' class='btn2' data-move='up' title='Move up'>↑</button>"
                f"<button type='button' class='btn2' data-move='down' title='Move down'>↓</button>"
                f"<label class='muted'><input type='checkbox' name='remove' value='{eid}'> remove</label></div></div>")
    rows = "".join(edit_row(s) for s in segs)
    add_html = (f"<div class='row' style='margin-top:10px;flex-wrap:wrap'><label class='muted'>add a moment <select name='add' style='max-width:320px'>"
                f"<option value=''>—</option>{opts}</select></label></div>") if opts else ""
    target = float(rev["settings"].get("length") or 0)
    short_html = (f"<div class='callout card' style='margin-top:8px'>Requested {target:.0f} s, got {total:.1f} s: "
                  f"there were not enough different moments in this footage for a longer reel.</div>") if target and total < target - 1.0 else ""
    skipped = res.get("skipped_inputs") or []
    skipped_html = ("<div class='muted' style='margin-top:6px'>Skipped: " + e(", ".join(f"{x['name']} ({ae.friendly_skip(x['reason'])})" for x in skipped)) + "</div>") if skipped else ""
    mode = "AI moments (FAST_LOCAL)" if res.get("selection_mode", "").startswith("FAST_LOCAL") else "Technical only (no AI)"
    notes = []
    for w in res.get("warnings") or []:
        if w.startswith("OVERLAPPING_MOMENTS_DROPPED"):
            notes.append(f"{w.split(':')[-1]} overlapping moment(s) of the same video were left out so nothing repeats")
        elif w.startswith("SELECTION_SEARCH_TOP_"):
            notes.append(f"for this length the best {w.rsplit('_', 1)[-1]} moments were compared")
        elif w.startswith("PREVIEW_QUALITY_USED:"):
            notes.append("lower quality (analysis preview) used for: " + w.split(":", 1)[1].replace(",", ", ")
                         + " - the original could not be re-cut")
        elif w == "HDR_NOT_CONVERTED":
            notes.append("HDR video could not be converted on this PC: colours may look grey")
    if res.get("hdr_sources"):
        notes.append("HDR video converted to normal colours: " + ", ".join(res["hdr_sources"]))
    if res.get("deinterlaced_sources"):
        notes.append("camcorder video de-interlaced: " + ", ".join(res["deinterlaced_sources"]))
    if res.get("widened_sources"):
        notes.append("wide picture stored in narrow pixels shown in its real shape: " + ", ".join(res["widened_sources"]))
    skipped_html_extra = ("<div class='muted' style='margin-top:4px'>" + e(" · ".join(notes)) + "</div>") if notes else ""
    exp_html = ""
    if is_acc:
        last = next((x for x in p["exports"] if x["revision_id"] == rev["id"]), None)
        exp_html = (f"<form method='post' action='/auto/p/{p['id']}/export' id='exportForm' style='margin-top:10px'>"
                    f"<input type='hidden' name='dest' id='exportDest' value=''>"
                    f"<div class='row' style='flex-wrap:wrap'><button class='ae-big'>Export MP4</button>"
                    f"<button type='button' class='btn2' id='exportToBtn'>Export to another folder…</button></div>"
                    f"<div class='muted' style='margin-top:4px'>Saves to {e(str(ae.default_export_dir()))}</div>"
                    f"<div class='muted' id='exportMsg'></div></form>")
        if last:
            exp_html += (f"<div class='card' style='margin-top:10px'><b>Exported</b><div class='ae-path'>{e(last['path'])}</div>"
                         f"<div class='row' style='margin-top:8px;flex-wrap:wrap'><form method='post' action='/auto/export/{last['id']}/open'><button>Open video</button></form>"
                         f"<form method='post' action='/auto/export/{last['id']}/reveal'><button class='btn2'>Show in folder</button></form>"
                         f"<button type='button' class='btn2' id='copyPath' data-path='{e(last['path'])}'>Copy path</button></div></div>")
    actions = (f"<span class='badge ready'>Accepted</span><form method='post' action='/auto/p/{p['id']}/revert'><button class='btn2'>Revert</button></form>" if is_acc else
               f"<form method='post' action='/auto/p/{p['id']}/accept'><input type='hidden' name='revision_id' value='{rev['id']}'><button class='ae-big'>Accept this version</button></form>")
    excl_hidden = "".join(f"<input type='hidden' name='exclude' value='{e(x)}'>" for x in rev["settings"].get("exclude", []))
    others = [r for r in p["revisions"] if r["id"] != rev["id"]]
    compare_html = ""
    if others:
        default_other = p["accepted_revision_id"] if p["accepted_revision_id"] and p["accepted_revision_id"] != rev["id"] else others[-1]["id"]
        opts_c = "".join(f"<option value='{r['id']}' {'selected' if r['id'] == default_other else ''}>R{int(r['number']):03d}</option>" for r in others)
        compare_html = (f"<form method='post' action='/auto/p/{p['id']}/compare' class='row' style='margin-top:10px;gap:6px;flex-wrap:wrap'>"
                        f"<input type='hidden' name='a' value='{rev['id']}'><span class='muted'>Compare blind with</span>"
                        f"<select name='b'>{opts_c}</select><button class='btn2'>Compare</button></form>")
    return f"""<div class='ae-player' style='margin-top:14px'>
<div class='card'><video id='reel' class='ae-video' controls preload='metadata' src='/auto/rev/{rev['id']}/video'></video>
<div class='ae-strip film'>{strip}</div>
<div class='muted'>Revision R{int(rev['number']):03d} · {e(fmt.get('short',''))} {rev['width']}×{rev['height']} · {total:.2f} s · sound {e(_sound_label(rev['settings']['sound'], res))} · {e(mode)}</div>{short_html}{skipped_html}{skipped_html_extra}
<div class='row' style='margin-top:12px;flex-wrap:wrap'>{actions}</div>{compare_html}{exp_html}</div>
<form class='card' method='post' action='/auto/p/{p['id']}/edit' id='editForm'><h2 style='margin-top:0'>Moments in this reel</h2>
<input type='hidden' name='revision_id' value='{rev['id']}'><input type='hidden' name='base_revision_id' value='{rev['id']}'>
<input type='hidden' name='length' value='{rev['settings']['length']}'><input type='hidden' name='format' value='{e(rev['settings']['format'])}'>
<input type='hidden' name='sound' value='{e(rev['settings']['sound'])}'><input type='hidden' name='mode' value='{e(rev['settings']['mode'])}'>{excl_hidden}
<div id='segList'>{rows or "<div class='muted'>No segment details for this revision.</div>"}</div>{add_html}
<div class='muted' style='margin-top:8px'>Times are in the source file. Every change makes a new version; this one stays as it is.</div>
<div class='row' style='margin-top:10px;flex-wrap:wrap'><button>Apply my edits</button>
<button class='btn2' formaction='/auto/p/{p['id']}/variant' name='rechoose' value='1'>Let MediaEngine choose again without removed moments</button></div></form></div>
{_variant_form(p['id'], rev, e)}"""


def _reviews_html(p, e):
    done = [r for r in p.get("reviews", []) if r.get("decided_at")]
    if not done:
        return ""
    num = {r["id"]: int(r["number"]) for r in p["revisions"]}
    rows = ""
    for r in done:
        a, b = num.get(r["left_revision_id"], 0), num.get(r["right_revision_id"], 0)
        txt = (f"R{a:03d} preferred over R{b:03d}" if r["choice"] == "left" else
               f"R{b:03d} preferred over R{a:03d}" if r["choice"] == "right" else f"R{a:03d} and R{b:03d} about the same")
        note = (" · <span translate='no'>" + e(r["note"]) + "</span>") if r.get("note") else ""
        rows += (f"<a class='ae-seg' style='grid-template-columns:1fr auto' href='/auto/review/{r['id']}'><span>{txt}"
                 f"{note}</span><span class='muted'>{e(_when(r['decided_at']))}</span></a>")
    return f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Blind comparisons</h2>{rows}</div>"


def _revisions_html(p, cur, e):
    if not p["revisions"]:
        return ""
    rows = ""
    for r in reversed(p["revisions"]):
        f = ae.FORMATS.get(r["settings"]["format"], {}).get("short", "")
        tag = " <span class='badge ready'>accepted</span>" if r["id"] == p["accepted_revision_id"] else ""
        here = " <span class='badge'>viewing</span>" if cur and r["id"] == cur["id"] else ""
        ex = len(r["settings"].get("exclude", []))
        rows += (f"<a class='ae-seg' style='grid-template-columns:70px 1fr auto' href='/auto/p/{p['id']}?rev={r['id']}'><b>R{int(r['number']):03d}</b>"
                 f"<span>{e(f)} · {r['settings']['length']} s · sound {e(r['settings']['sound'])}{(' · ' + str(ex) + ' excluded') if ex else ''}{' · edited by you' if r['settings'].get('selection') else ''}"
                 f" <span class='muted'>· {e(_when(r['created_at']))}</span></span><span>{tag}{here}</span></a>")
    return f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Revisions</h2>{rows}</div>"
