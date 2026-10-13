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


_DUR_CACHE: dict = {}


def _source_seconds(pid: int, name: str) -> float:
    """Length of a source video (for checking typed trim times in the page); 0 when unknown. Cached per file state."""
    try:
        src = ae.source_file(pid, name)
        if not src:
            return 0.0
        st = src.stat()
        if ae.cloud_only(src, st):          # never make OneDrive download a file just to check a typed time
            return 0.0
        key = (str(src), st.st_size, st.st_mtime_ns)
        if key not in _DUR_CACHE:
            try:
                _DUR_CACHE[key] = float(ae._probe(src).get("format", {}).get("duration") or 0)
            except Exception:       # a recording without a written length: the build's fixed copy has it (never read
                _DUR_CACHE[key] = ae.fixed_copy_seconds(pid, name)   # the whole original while a page loads)
        return _DUR_CACHE[key]
    except Exception:
        return 0.0


def _error_html(msg: str, e) -> str:
    """A failed build's message in words; the technical code (for support) small underneath, not in the sentence."""
    msg = str(msg or "")
    if msg.endswith("]") and " [" in msg:
        text, code = msg.rsplit(" [", 1)
        return e(text) + f"<div class='muted' translate='no' style='font-size:11px;margin-top:4px'>{e(code[:-1])}</div>"
    return e(msg)


def _skip_reason_html(r: str, e) -> str:
    """Why a file is skipped (already in words); the other file's name in "duplicate of …" stays exactly as it is
    in both languages."""
    r = str(r or "")
    if r.startswith("duplicate of "):
        return "duplicate of <span translate='no'>" + e(r[len("duplicate of "):]) + "</span>"
    return e(r)


def _rel(path: str, base: str) -> str:
    """A folder inside the chosen one, shown from there (DCIM\\100GOPRO)."""
    try:
        return str(Path(path).relative_to(Path(base)))
    except ValueError:
        return Path(path).name


def _fmt_s(x) -> str:
    try:
        x = float(x)
    except Exception:
        return "—"
    m, s = divmod(x, 60)
    if m >= 60:                       # long camera files: 1:05:03.0
        h, m = divmod(int(m), 60)
        return f"{h}:{m:02d}:{s:04.1f}"
    return f"{int(m)}:{s:04.1f}"


_MONTHS_RU = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _day_label(day: str) -> str:
    """2026-07-14 -> "14 июля 2026" / "14 Jul 2026" (in the interface language)."""
    try:
        y, m, d = (int(x) for x in day.split("-"))
        return f"{d} {(_MONTHS_RU if ae.ui_language() == 'ru' else _MONTHS_EN)[m - 1]} {y}"
    except Exception:
        return day


def _big_folder_page(folder: Path, days: list, e, human_bytes) -> tuple[str, str]:
    """More videos than one reel takes: choose a day (one click) or tick up to MAX_INPUTS videos."""
    cap = ae.MAX_INPUTS
    total = sum(len(d["files"]) for d in days)
    day_rows, file_rows = [], []
    for d in days:
        n, size = len(d["files"]), human_bytes(sum(f["bytes"] for f in d["files"]))
        use = ("<a class='btn btn2' href='/auto/new?" + "&".join("file=" + urllib.parse.quote(f["path"]) for f in d["files"])
               + "'>Use this day</a>") if n <= cap else f"<span class='muted'>more than {cap} — tick them below</span>"
        day_rows.append(f"<tr><td><b translate='no'>{e(_day_label(d['day']))}</b></td><td>{n} video(s)</td><td>{size}</td><td>{use}</td></tr>")
        file_rows.append(f"<tr><td colspan='3'><label class='muted'><input type='checkbox' data-day='{e(d['day'])}'> "
                         f"<b translate='no'>{e(_day_label(d['day']))}</b> · {n} video(s)</label></td></tr>")
        file_rows += [f"<tr><td><label><input type='checkbox' name='file' value='{e(f['path'])}' data-in='{e(d['day'])}'> "
                      f"<span translate='no'>{e(f['name'])}</span></label></td><td>{human_bytes(f['bytes'])}</td><td></td></tr>"
                      for f in d["files"]]
    body = (f"<div class='pagehead'><div class='eyebrow'>Auto Edit · new reel</div><h1 translate='no'>{e(folder.name or str(folder))}</h1>"
            f"<div class='lead ae-path'>{e(str(folder))}</div></div>"
            f"<div class='card callout'><b>{total} videos in this folder.</b> One reel can use up to {cap} of them: "
            f"pick a day, or tick the videos you want.</div>"
            f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>By day</h2>"
            f"<div class='muted'>The day is taken from the file name (e.g. VID_20260714_…), otherwise from the file's date.</div>"
            f"<table class='ae-files' style='margin-top:8px'>{''.join(day_rows)}</table></div>"
            f"<form method='get' action='/auto/new' class='card' style='margin-top:14px' id='pickForm'>"
            f"<h2 style='margin-top:0'>Tick videos</h2>"
            f"<div style='position:sticky;top:62px;z-index:5;background:#151b24;padding:8px 0;border-bottom:1px solid #2c3744'>"
            f"<div class='row' style='flex-wrap:wrap;gap:8px'><button type='button' class='btn2' id='tickNewest'>Tick the newest {cap}</button>"
            f"<button type='button' class='btn2' id='tickNone'>Untick all</button>"
            f"<span>Ticked: <b id='tickCount' translate='no'>0 / {cap}</b></span>"
            f"<button class='ae-big' id='tickGo' disabled>Use the ticked videos</button></div>"
            f"<div class='errbox' id='tickMax' style='margin-top:8px' hidden>More than {cap} ticked — untick some.</div></div>"
            f"<table class='ae-files' style='margin-top:8px'>{''.join(file_rows)}</table></form>"
            f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
    script = ("const CAP=" + str(cap) + ",boxes=[...document.querySelectorAll('input[name=file]')];"
              "function upd(){const n=boxes.filter(b=>b.checked).length;document.getElementById('tickCount').textContent=n+' / '+CAP;"
              "document.getElementById('tickGo').disabled=!n||n>CAP;document.getElementById('tickMax').hidden=n<=CAP}"
              "boxes.forEach(b=>b.onchange=upd);"
              "document.querySelectorAll('input[data-day]').forEach(d=>d.onchange=()=>{boxes.filter(b=>b.dataset.in===d.dataset.day).forEach(b=>b.checked=d.checked);upd()});"
              "document.getElementById('tickNewest').onclick=()=>{boxes.forEach((b,i)=>b.checked=i<CAP);upd()};"
              "document.getElementById('tickNone').onclick=()=>{boxes.forEach(b=>b.checked=false);document.querySelectorAll('input[data-day]').forEach(d=>d.checked=false);upd()};"
              "document.getElementById('pickForm').onsubmit=()=>{document.getElementById('tickGo').disabled=true};upd();")
    return body, script


def register(app, layout, e, human_bytes):
    """Attach Auto Edit routes to the existing app (called from web.create_app)."""

    @app.before_request
    def _ae_recover():
        # first request served by this process: a build left "running" by a crashed process is marked interrupted
        # (Retry-able), so Quit / Restart / switching builds are not refused for a job that no longer exists.
        # Only the process that actually serves pages does this - a second copy that cannot take the port never does.
        try:
            ae.ensure_schema()
        except Exception:
            pass

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
            length = f"{float(ref.get('duration_s') or ref['settings']['length']):.0f} s" if ref else ""   # what the reel really is
            exp = ae.export_row(p["last_export_id"]) if p.get("last_export_id") else None
            n_src = len(ae.project_inputs(p)) if p["source_present"] else 0
            acts = f"<a class='btn btn2' href='/auto/p/{p['id']}'>{'Review' if p['revisions'] else 'Open'}</a>"
            if p["accepted_revision_id"]:
                acts += f"<form method='post' action='/auto/p/{p['id']}/export' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\"><button class='btn2'>Export</button></form>"
            if exp:
                acts += (f"<form method='post' action='/auto/export/{exp['id']}/open'><input type='hidden' name='back' value='/auto'><button class='btn2'>Open video</button></form>"
                         f"<form method='post' action='/auto/export/{exp['id']}/reveal'><input type='hidden' name='back' value='/auto'><button class='btn2'>Show in folder</button></form>")
            acts += f"<form method='post' action='/auto/p/{p['id']}/archive'><button class='btn2'>{'Unarchive' if p['archived'] else 'Archive'}</button></form>"
            last_txt = ("Last export: <span translate='no'>" + e(Path(exp["path"]).name) + "</span>") if exp else "Not exported yet"
            cards += (f"<div class='card'><a href='/auto/p/{p['id']}' style='display:block'>"
                      f"<div class='row space'><b style='font-size:17px' translate='no'>{e(p['title'])}</b><span class='ae-state {p['state']}'>{p['state']}</span></div>"
                      f"<div class='muted' style='margin-top:6px'>{' · '.join(x for x in (str(n_src) + (' chosen video(s)' if p.get('files') else ' video file(s) in folder'), e((preset + ' ' + length).strip()), str(len(p['revisions'])) + ' revision(s)') if x)}</div>"
                      f"<div class='muted'>{last_txt}</div></a>"
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
        try:
            exp_dir = ae.default_export_dir()
            has_exports = exp_dir.is_dir() and any(x.suffix.lower() == ".mp4" for x in exp_dir.iterdir())
        except OSError:
            has_exports = False
        check_btn = ("<div class='row' style='float:right;gap:8px'>"
                     + ("<form method='post' action='/auto/exports/open' style='margin:0'><button class='btn2'>Exported reels</button></form>"
                        if has_exports else "")
                     + "<a class='btn btn2' href='/auto/check'>Check this PC</a></div>")
        first = "" if ae.selftest_passed() else (
            "<div class='card callout' style='margin-bottom:14px'><b>First time on this PC?</b> "
            "<span class='muted'>Check this PC first: it shows whether the AI model and video tools are found and builds a 5-second test reel "
            "(about a minute; your videos are not used).</span>"
            "<div class='row' style='margin-top:8px'><a class='btn' href='/auto/check'>Check this PC</a></div></div>")
        body = f"""<div class='pagehead'>{check_btn}<div class='eyebrow'>MediaEngine</div><h1>Auto Edit</h1>
<div class='lead'>Choose a folder of videos (or single videos), pick length, format and sound, and MediaEngine builds a reel from the best moments.
Your original files are only read, never changed.</div></div>{first}
<div class='card'><h2 style='margin-top:0'>New reel</h2>
<form method='get' action='/auto/new' class='row' style='flex-wrap:wrap' onsubmit="document.getElementById('pickMsg').textContent='Checking the videos… (a few seconds per video)'">
<button type='button' class='ae-big' id='pickBtn'>Choose folder…</button>
<button type='button' class='btn2 ae-big' id='pickFilesBtn'>Choose videos…</button>
<input name='folder' id='folderInput' required placeholder='or paste a folder path, e.g. D:\\Videos\\Trip' style='flex:1;min-width:280px'>
<button class='btn btn2 ae-big'>Continue</button></form>
<div class='muted' id='pickMsg' style='margin-top:6px'></div></div>{model_note}

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
 else if(x.folder){m.textContent=x.error||'';location.href='/auto/new?folder='+encodeURIComponent(x.folder)}
 else m.textContent=x.error||'No videos chosen.'}catch(e){m.textContent='Window failed: '+e}};"""
        return page("Auto Edit", body, script)

    @app.route("/auto/check", methods=["GET", "POST"])
    def ae_check():
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return err_page("This page can only be opened from MediaEngine itself.")   # it starts the engine and FFmpeg
        rows = ae.system_check()
        def looks_like_path(t):   # paths, versions, system names: shown exactly as they are
            return ":\\" in t or t.startswith("/") or "version" in t or "|" in t or t.startswith(("Windows-", "Linux", "Darwin", "3.1"))
        table = "".join(f"<tr><td>{'✅' if r['ok'] else '⚠️'}</td><td><b>{e(r['name'])}</b></td>"
                        f"<td class='{'ae-path' if looks_like_path(r['detail']) else 'muted'}'>{e(r['detail'])}</td></tr>" for r in rows)
        test_html = ""
        ai_ready = ae.model_status()["ready"]
        ap = ae.aiplus_status()
        if request.method == "POST":
            want = request.form.get("mode")
            want = want if (want == "semantic" and ai_ready) or (want == "semantic_plus" and ap["ready"]) else "technical"
            t = ae.quick_selftest(mode=want, timeout_s=1800 if want == "semantic_plus" else 900)
            ae._remember_selftest(t)
            if t["ok"]:
                sm = str(t.get("selection_mode", ""))
                ai = sm.startswith("FAST_LOCAL") or sm.startswith("PE_CORE")
                st = t.get("stages") or {}
                stage_txt = " · ".join(f"<span>{lbl}</span> {float(st[k]):.1f} s" for k, lbl in
                                       (("analyze", "analysis"), ("render", "cutting"), ("finish", "joining")) if k in st)
                test_html = (f"<div class='card ae-done' style='margin-top:14px'><b>Test reel built</b> · "
                             f"<span>{'with the AI+ model (PE-Core L/14)' if sm.startswith('PE_CORE') else 'with the AI model (FAST_LOCAL)' if ai else 'Technical only'}</span> · {t['seconds']} s"
                             f"<div class='muted' style='margin-top:4px'><span>reel</span> {t.get('duration_s')} s · {stage_txt}</div>"
                             + (f"<div class='muted' style='margin-top:4px'>AI+ speed on this PC: {float(t['aiplus_s_per_frame']):.1f} s per frame. "
                                f"The first analysis looks at up to 48 frames of each video (about one per second): about "
                                f"{max(1, round(48 * float(t['aiplus_s_per_frame'])))} s for a video of a minute or longer. Later builds reuse it.</div>"
                                if t.get("aiplus_s_per_frame") else "")
                             + (("<div style='margin-top:6px'>The AI+ mode works on this PC.</div>" if sm.startswith("PE_CORE") else
                                 "<div style='margin-top:6px'>The AI mode works on this PC.</div>") if ai else "")
                             + (f"<video class='ae-video' style='max-height:320px;margin-top:10px' controls preload='metadata' "
                                f"src='/auto/check/video?t={int(t['seconds'] * 10)}'></video>" if t.get("video") else "")
                             + "<div class='row' style='margin-top:10px'><a class='btn' href='/auto'>Go to Auto Edit</a></div></div>")
            else:
                test_html = (f"<div class='card' style='margin-top:14px'><b>Test reel failed</b> · {t['seconds']} s"
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
            builds_html = f"<div class='card ae-done' style='margin-top:14px'>Removed <span translate='no'>{e(done)}</span>.</div>" + builds_html
        body = (f"<div class='pagehead'><div class='eyebrow'>Auto Edit</div><h1>Check this PC</h1>"
                f"<div class='lead'>What MediaEngine needs, and a 5-second test reel made from generated clips (your videos are not used).</div></div>"
                f"<div class='card'><table class='ae-files'>{table}</table></div>"
                f"<form method='post' class='card' style='margin-top:14px' onsubmit=\"const f=this;f.querySelector('span').textContent='Building the test reel… (up to a few minutes)';setTimeout(()=>f.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<button name='mode' value='technical'>Build a test reel</button> "
                + (f"<button name='mode' value='semantic' class='btn2'>Build a test reel with the AI model</button> " if ai_ready else "")
                + (f"<button name='mode' value='semantic_plus' class='btn2'>Build a test reel with AI+</button> " if ap["ready"] else "")
                + f"<span class='muted'></span></form>{test_html}{_aiplus_card(ap, e, human_bytes)}{builds_html}"
                f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
        return page("Check this PC", body)

    @app.get("/auto/check/video")
    def ae_check_video():
        v = ae.selftest_video()
        if not v:
            return err_page("The test reel is not there (build it on Check this PC).")
        return send_file(str(v), mimetype="video/mp4", conditional=True)

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
        path = (request.get_json(silent=True) or {}).get("path") or ae.pick_folder("Choose the folder that contains the FAST_LOCAL model",
                                                                                  initial=ae.model_folder_hint())
        if not path:
            return jsonify({"ok": False, "error": "No folder chosen."})
        try:
            res = ae.import_model(path)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)})
        return jsonify({"ok": True, **res})

    @app.post("/api/auto/aiplus/import")
    def ae_aiplus_import():
        path = (request.get_json(silent=True) or {}).get("path") or ae.pick_folder("Choose the folder with the AI+ model files")
        if not path:
            return jsonify({"ok": False, "error": "No folder chosen."})
        try:
            res = ae.aiplus_import(path)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)})
        return jsonify({"ok": True, **res})

    @app.post("/api/auto/aiplus/download")
    def ae_aiplus_download():
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return jsonify({"ok": False, "error": "Only from MediaEngine itself."}), 400
        if (request.get_json(silent=True) or {}).get("cancel"):
            ae.aiplus_download_cancel()
            return jsonify({"ok": True})
        started = ae.aiplus_download_start()
        return jsonify({"ok": True, "started": started})

    @app.get("/api/auto/aiplus")
    def ae_aiplus_state():
        st = ae.aiplus_status()
        dl = st["download"]
        return jsonify({"ready": st["ready"], "state": dl["state"], "done": dl["done"], "total": dl["total"] or st["bytes"],
                        "error": dl["error"], "message": ""})

    @app.post("/api/auto/pick-files")
    def ae_pick_files():
        files = ae.pick_files(initial=ae.last_source_folder())
        if files and len(files) > ae.MAX_INPUTS:
            # more than one reel takes: open their folder instead (its day / tick list), not a huge address
            parents = {str(Path(x).parent) for x in files}
            return jsonify({"files": [], "folder": parents.pop() if len(parents) == 1 else None,
                            "error": f"More than {ae.MAX_INPUTS} videos chosen. One reel can use up to {ae.MAX_INPUTS}."})
        if files:
            return jsonify({"files": files})
        return jsonify({"files": [], "error": "No videos chosen."})

    @app.post("/api/auto/pick-folder")
    def ae_pick_folder():
        purpose = (request.get_json(silent=True) or {}).get("purpose")
        path = ae.pick_folder("Choose a folder for the exported reel" if purpose == "export" else
                              "Choose a folder with your videos on this computer (copy phone videos to the computer first)",
                              initial=str(ae.default_export_dir()) if purpose == "export" else ae.last_source_parent())
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
        if folder.strip() and not chosen:
            fp = Path(folder.strip().strip('"'))
            try:
                is_file = fp.is_absolute() and fp.is_file()
            except OSError:
                is_file = False
            if is_file:      # a pasted path to one video: use it as a chosen video
                if fp.suffix.lower() in ae.SUPPORTED:
                    return redirect("/auto/new?file=" + urllib.parse.quote(str(fp)))
                return err_page("That is a file, not a folder. Paste the path of a folder, or press Choose videos….")
        big = Path(folder.strip().strip('"')) if folder.strip() and not chosen else None
        if big is not None and big.is_absolute() and ae.folder_available(big) and len(ae.list_videos(big)) > ae.MAX_INPUTS:
            try:   # a phone camera folder: pick a day or tick videos instead of refusing the folder
                ae._guard_private(big)
            except ValueError as exc:
                return err_page(str(exc))
            return page("New reel", *_big_folder_page(big, ae.videos_by_day(big), e, human_bytes))
        try:
            scan = ae.scan_files(chosen) if chosen else ae.scan_folder(folder)
        except Exception as exc:
            return err_page(str(exc))
        if not scan["usable"]:
            subs = [] if chosen or scan["files"] else ae.subfolders_with_videos(scan["folder"])
            if subs:
                links = "".join(f"<li style='margin:6px 0'><a class='btn btn2' href='/auto/new?folder={urllib.parse.quote(p_)}'>"
                                f"<span translate='no'>{e(_rel(p_, scan['folder']))}</span></a> "
                                f"<span class='muted'>· {n} video(s)</span></li>" for p_, n in subs)
                return page("New reel", f"<div class='pagehead'><div class='eyebrow'>Auto Edit · new reel</div>"
                                        f"<h1 translate='no'>{e(Path(scan['folder']).name or scan['folder'])}</h1>"
                                        f"<div class='lead ae-path'>{e(scan['folder'])}</div></div>"
                                        f"<div class='card'><b>No videos directly in this folder.</b> These folders inside it have videos — "
                                        f"open one (or use Choose videos… on the Auto Edit page to pick from several):"
                                        f"<ul style='margin:8px 0 0;list-style:none;padding:0'>{links}</ul></div>"
                                        f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
            if scan["files"] and all(r["reason"] == ae.CLOUD_ONLY_REASON for r in scan["files"]):
                return err_page("These videos are only in OneDrive, not on this PC. In Explorer right-click the folder → "
                                "'Always keep on this device', wait until the download is done, then choose it again.")
            if scan["files"] and all(r["reason"].startswith("too short") for r in scan["files"]):
                return err_page("All these videos are shorter than 2.5 seconds - too short to find moments in.")
            return err_page("No readable videos " + ("among the chosen files." if chosen else "in this folder."))
        ms = ae.model_status()
        def file_row(r):
            status = (("<span class='badge'>usable</span>" if r["duration_s"] >= 3.5 else
                       "<span class='badge review'>very short — may be skipped</span>") if r["ok"] else
                      "<span class='badge error'>skipped: " + _skip_reason_html(r["reason"], e) + "</span>")
            if r.get("length_measured"):
                status += (" <span class='muted' style='font-size:12px'>length was not written in the file (browser or screen "
                           "recording) — a fixed copy is used, the original is not changed</span>")
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
        plus_ready = ae.aiplus_status()["ready"]
        # from the Library's "Find by theme": AI+ and that theme are already chosen
        want_mode = request.args.get("mode") if request.args.get("mode") in ae.MODES else None
        want_theme = request.args.get("theme") if plus_ready and request.args.get("theme") in ae.THEMES else ""
        if want_theme:
            want_mode = "semantic_plus"
        mode_html = (_mode_choice(ms["ready"], plus_ready, e, current=want_mode)
                     + (_theme_choice(e, want_theme, ms["ready"]) if plus_ready else ""))
        warn = ("<div class='callout card' style='margin-top:10px'>Only "
                f"{_fmt_s(total)} of usable video — a short reel is recommended.</div>" if total < 30 else "")
        if total >= 1800:   # honest note for big folders (no invented time estimate)
            warn = ("<div class='callout card' style='margin-top:10px'>A lot of video. The first build analyses all of it once and "
                    "can take a long time; later builds and variants reuse that analysis. The PC does not go to sleep while "
                    "MediaEngine works, and you can keep using it.</div>")
        src_hidden = ("".join(f"<input type='hidden' name='file' value='{e(x)}'>" for x in scan["files_chosen"]) if scan["files_chosen"]
                      else f"<input type='hidden' name='folder' value='{e(scan['folder'])}'>")
        where_html = (f"{len(scan['files_chosen'])} chosen video(s) · from <span class='ae-path' translate='no'>{e(scan['folder'])}</span>"
                      if scan["files_chosen"] else f"<span class='ae-path' translate='no'>{e(scan['folder'])}</span>")
        subs = [] if scan["files_chosen"] else ae.subfolders_with_videos(scan["folder"], limit=20, depth=2, max_dirs=400)
        parents = {str(Path(x).parent) for x in (scan["files_chosen"] or [])}
        from_big = (len(parents) == 1 and len(ae.list_videos(Path(next(iter(parents))))) > ae.MAX_INPUTS) if parents else False
        up = Path(scan["folder"]).parent
        up_ok = not scan["files_chosen"] and str(up) != str(Path(scan["folder"])) and ae.folder_available(up)
        back_html = ("<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a>"
                     + (f"<a class='btn btn2' href='/auto/new?folder={urllib.parse.quote(next(iter(parents)))}'>Other days of this folder</a>" if from_big else "")
                     + (f"<a class='btn btn2' href='/auto/new?folder={urllib.parse.quote(str(up))}'>Folder above</a>" if up_ok else "")
                     + "</div>")
        inside = (f"<details style='margin-top:6px'><summary class='muted'>Only the videos directly in this folder are used. "
                  f"Folders inside it with videos: {len(subs)}</summary><ul style='margin:6px 0 0'>"
                  + "".join(f"<li><a href='/auto/new?folder={urllib.parse.quote(p_)}' translate='no'>{e(_rel(p_, scan['folder']))}</a> "
                            f"<span class='muted'>· {n} video(s)</span></li>" for p_, n in subs) + "</ul></details>") if subs else ""
        picked = [Path(x) for x in (scan["files_chosen"] or [])]
        pdays = {ae.video_day(x, 0) for x in picked} if picked and all(ae._DAY_IN_NAME.search(x.stem) for x in picked) else set()
        day_suffix = (" · " + _day_label(next(iter(pdays)))) if len(pdays) == 1 else ""      # "Телефон · 2 августа 2026"
        body = f"""<div class='pagehead'><div class='eyebrow'>Auto Edit · new reel</div><h1 translate='no'>{e(Path(scan['folder']).name or scan['folder'])}{e(day_suffix)}</h1>
<div class='lead'>{where_html}</div></div>
<div class='card'><b>{scan['usable']} usable video(s)</b>, total {_fmt_s(total)} · {human_bytes(scan['total_bytes'])}{(' · ' + str(scan['skipped']) + ' skipped') if scan['skipped'] else ''}
<details style='margin-top:8px'><summary class='muted'>Show files</summary><table class='ae-files'><tr><th>File</th><th>Size</th><th>Length</th><th>Frame</th><th></th></tr>{rows}</table></details>{inside}{warn}</div>
<form method='post' action='/auto/create' class='card' style='margin-top:14px' onsubmit="this.querySelector('button').disabled=true">
{src_hidden}
<h2 style='margin-top:0'>Length</h2><div class='ae-choices'>{lengths}</div>
<h2>Format</h2><div class='ae-choices'>{formats}</div>
<h2>Sound</h2><div class='ae-choices'>{sounds}</div>{mode_html}
<button class='ae-big'>Create reel</button></form>{back_html}"""
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
            ae.start_job(pid, {"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode"),
                               "theme": f.get("theme") or ""})
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
<h1 translate='no'>{e(p['title'])}</h1><div class='lead'>{(str(len(p['files'])) + ' chosen video(s) · from ') if p.get('files') else ''}<span class='ae-path' translate='no'>{e(p['folder'])}</span></div></div>
<div class='row' style='flex-wrap:wrap'><a class='btn btn2' href='/auto'>All projects</a>
<form method='post' action='/auto/p/{pid}/rename' class='row' style='gap:6px'><input name='title' value='{e(p['title'])}' maxlength='80' style='width:200px'><button class='btn2'>Rename</button></form>
<form method='post' action='/auto/p/{pid}/archive'><button class='btn2'>{'Unarchive' if p['archived'] else 'Archive'}</button></form></div></div>"""]
        if request.args.get("same") and cur:
            parts.append(f"<div class='card callout' style='margin-bottom:12px'>This version already exists: R{int(cur['number']):03d} "
                         f"(the same settings and moments). Change the length, format or sound, or tick “remove” on a moment.</div>")
        if not p["source_present"]:
            parts.append("<div class='errbox'>The source videos are not available (drive disconnected?). Revisions and exports are kept; "
                         "new builds are possible when they are back.</div>")
        if active:
            parts.append(f"""<div class='card' id='jobCard' data-job='{active['id']}'><div class='row space'><b id='jobStage'>{e(ae.STAGE_LABEL.get(active['stage'] or 'queued', ''))}</b>
<form method='post' action='/auto/job/{active['id']}/cancel'><button class='btn2'>Cancel</button></form></div>
<div class='ae-bar' style='margin:10px 0'><i id='jobBar' style='width:{active['percent']}%'></i></div>
<div class='muted' id='jobMsg'>{e(active.get('message') or '')}</div>
<div class='muted'>{e(ae.FORMATS[active['settings']['format']]['label'])} · {active['settings']['length']} s · sound {e(active['settings']['sound'])}</div>
{"<div style='margin-top:6px'>A new version with your edits.</div>" if active['settings'].get('selection') else ""}
<div class='muted' style='margin-top:6px'>You can close this window: the reel keeps building and the PC does not go to sleep. Open MediaEngine again to see it.</div></div>""")
            for q in queued:
                parts.append(f"<div class='card row space' style='margin-top:8px'><span class='muted'>Waiting: {e(ae.FORMATS[q['settings']['format']]['short'])} · "
                             f"{q['settings']['length']} s · sound {e(q['settings']['sound'])}</span>"
                             f"<form method='post' action='/auto/job/{q['id']}/cancel'><button class='btn2'>Cancel</button></form></div>")
        elif last_job and last_job["status"] in ("failed", "cancelled") and (not revs or last_job["id"] > max(r["job_id"] for r in revs)):
            ls_ = last_job["settings"]
            no_ai = ""
            if last_job["status"] == "failed" and ls_.get("mode") in ae.AI_MODES:
                # an AI-mode failure must not leave the user stuck: offer the clearly labelled technical build
                no_ai = (f"<form method='post' action='/auto/p/{pid}/variant'>"
                         f"<input type='hidden' name='length' value='{ls_['length']}'><input type='hidden' name='format' value='{e(ls_['format'])}'>"
                         f"<input type='hidden' name='sound' value='{e(ls_['sound'])}'><input type='hidden' name='mode' value='technical'>"
                         f"<button class='btn2'>Build without AI (Technical only)</button></form>")
            parts.append(f"""<div class='card'><b>{'Build failed' if last_job['status']=='failed' else 'Build cancelled'}</b>
<div class='{'errbox' if last_job['status']=='failed' else 'muted'}' style='margin:8px 0'>{_error_html(last_job.get('error') or last_job.get('message') or '', e)}</div>
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
            parts.append(_review_html(p, cur, e, building=bool(active)))
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
 let eta='';if(j.status==='running'&&j.stage==='finish')eta=' · final encode and check of the whole reel, can take a few minutes';
 else if(j.status==='running'&&j.percent>=15&&j.percent<100&&el>=20){const left=Math.round(el*(100-j.percent)/j.percent);
  eta=left<60?' · less than a minute left':' · about '+Math.round(left/60)+' min left'}
 document.getElementById('jobMsg').textContent=(counted?(Math.min(j.done+1,j.total)+' of '+j.total+' · '):'')+(j.message||'')+' · '+Math.floor(el/60)+':'+String(el%60).padStart(2,'0')+' elapsed'+eta;
 if(['done','failed','cancelled'].includes(j.status)){location.reload();return}}catch(e){}setTimeout(pollJob2,1000)}
pollJob2();
const ef=document.getElementById('editForm');
function secs(x){x=String(x||'').trim().replace(',','.');if(!x)return null;const m=/^(\\d+):(\\d{1,2}(?:\\.\\d+)?)$/.exec(x);
 if(m)return (+m[1])*60+(+m[2]);return /^\\d+(\\.\\d+)?$/.test(x)?+x:null}
if(ef)ef.addEventListener('submit',ev=>{if(ev.submitter&&ev.submitter.name==='rechoose')return;const errs=[];
 ef.querySelectorAll('.ae-edit').forEach(row=>{const a=row.querySelector('input[name^="in_"]'),b=row.querySelector('input[name^="out_"]'),rm=row.querySelector('input[name="remove"]');
  if(!a||!b||(rm&&rm.checked))return;const n=(row.querySelector('.pos')||{}).textContent||'?',x=secs(a.value),y=secs(b.value);
  const d=parseFloat(row.dataset.dur||'0'),m='Moment '+n+': ';
  if(x===null||y===null)errs.push(m+'write the time as seconds (12.5) or minutes (1:05)');
  else if(d>0&&y>d+0.05)errs.push(m+'the video is only '+d.toFixed(1)+' s long - “to” cannot be later');
  else if(y-x<0.5)errs.push(m+'“to” must be at least 0.5 s after “from”');
  else if(y-x>60)errs.push(m+'one moment can be at most 60 s long')});
 const box=document.getElementById('editErr');if(errs.length){ev.preventDefault();box.textContent=errs.join('\\n');box.hidden=false;box.scrollIntoView({block:'center'})}else box.hidden=true});
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
 try{const r=await fetch('/api/auto/pick-folder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({purpose:'export'})});const x=await r.json();
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
            # the form's explicit choice first: an AI-built reel can get a Technical-only variant when the model is gone
            mode = f.get("mode") or bs.get("mode") or ("semantic" if ae.model_status()["ready"] else None)
            if not mode:
                raise ValueError("Without the AI model, choose Technical only explicitly on the new-reel screen.")
            settings = {"length": f.get("length") or bs.get("length"), "format": f.get("format") or bs.get("format"),
                        "sound": f.get("sound") or bs.get("sound"), "mode": mode,
                        "theme": f.get("theme") if "theme" in f else (bs.get("theme") or "")}
            if f.get("rechoose"):
                # "Let MediaEngine choose again": automatic selection without the removed moments
                settings["exclude"] = sorted(set(bs.get("exclude", [])) | set(f.getlist("remove")))
            else:
                # A format/sound variant keeps the base revision's choices (exclusions, manual edits). A new LENGTH
                # needs other moments: they are chosen again (removed ones stay out) - a hand-made selection would
                # silently keep the old length.
                same_len = not bs or str(settings["length"]) == str(bs.get("length"))
                same_mode = not bs or (settings["mode"] == bs.get("mode")    # AI, AI+ and each theme have their own moments
                                       and (settings.get("theme") or "") == (bs.get("theme") or ""))
                keep = (("exclude", "selection", "trims") if same_len else ("exclude",)) if same_mode else ()
                settings.update({k: bs[k] for k in keep if bs.get(k)})
            before = {j["id"] for j in ae.project(pid)["jobs"]}
            jid = ae.start_job(pid, settings)
            j = ae.job(jid)
            if jid in before and j and j["status"] == "done" and j.get("revision_id"):
                same = ae.revision(j["revision_id"])         # nothing changed: say so instead of silently reloading
                return redirect(f"/auto/p/{pid}?rev={same['id']}&same=1" if same else f"/auto/p/{pid}")
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
            before = {j["id"] for j in ae.project(pid)["jobs"]}
            jid = ae.start_job(pid, settings)
            j = ae.job(jid)
            if jid in before and j and j["status"] == "done" and j.get("revision_id"):
                return redirect(f"/auto/p/{pid}?rev={int(j['revision_id'])}&same=1")      # nothing was changed
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

    @app.post("/auto/exports/open")
    def ae_exports_open():
        if not ae.open_path(ae.default_export_dir()):
            return err_page("The folder for exported reels is not there yet.")
        return redirect("/auto")

    @app.post("/auto/export/<int:eid>/<action>")
    def ae_export_action(eid, action):
        x = ae.export_row(eid)
        if not x or action not in ("open", "reveal"):
            return err_page("Export not found")
        if not ae.open_path(Path(x["path"]), reveal=(action == "reveal")):
            return err_page("The exported file is not available any more: " + x["path"], f"/auto/p/{x['project_id']}")
        back = request.form.get("back") or ""
        return redirect(back if back in ("/auto", "/auto?archived=1") else f"/auto/p/{x['project_id']}")

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
                secs = float(r.get("duration_s") or r["settings"]["length"])
                return f"R{int(r['number']):03d} ({e(f)} · {secs:.0f} s · {'edited by you' if r['settings'].get('selection') else 'automatic'})"
            verdict = {"left": f"You preferred A = {who(L)} over B = {who(R)}.", "right": f"You preferred B = {who(R)} over A = {who(L)}.",
                       "same": f"You found them about the same: A = {who(L)}, B = {who(R)}."}[rv["choice"]]
            bottom = (f"<div class='card ae-done' style='margin-top:14px'><b>Result</b><div style='margin-top:6px'>{verdict}</div>"
                      + (f"<div class='muted' style='margin-top:4px'>Note: <span translate='no'>{e(rv['note'])}</span></div>" if rv.get("note") else "")
                      + "<div class='row' style='margin-top:10px;flex-wrap:wrap'>"
                      + (lambda w: (f"<form method='post' action='/auto/p/{pid}/accept'><input type='hidden' name='revision_id' value='{w['id']}'>"
                                    f"<button>Accept R{int(w['number']):03d}</button></form>")
                         if w and p["accepted_revision_id"] != w["id"] else "")({"left": L, "right": R}.get(rv["choice"]))
                      + f"<a class='btn btn2' href='/auto/p/{pid}'>Back to the project</a></div></div>")
        else:
            bottom = (f"<form method='post' action='/auto/review/{rid}/decide' class='card' style='margin-top:14px'>"
                      f"<div class='muted'>Watch both. Which one would you rather publish? Versions and settings are hidden until you decide.</div>"
                      f"<input name='note' maxlength='500' placeholder='Why? (optional, e.g. better start, fewer shaky shots)' style='width:100%;margin:10px 0'>"
                      f"<div class='row' style='flex-wrap:wrap'><button name='choice' value='left' class='ae-big'>A is better</button>"
                      f"<button name='choice' value='right' class='ae-big'>B is better</button>"
                      f"<button name='choice' value='same' class='btn2'>About the same</button>"
                      f"<a class='btn btn2' href='/auto/p/{pid}'>Back</a></div></form>")
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


AI_LABEL = "AI — as before (fast)"
AIPLUS_LABEL = "AI+ — stronger model, first analysis slower"
AIPLUS_HINT = ("AI+ (a stronger model, PE-Core L/14) can be added once on <a href='/auto/check#aiplus'>Check this PC</a> "
               "(about 650 MB, free).")


def _aiplus_card(ap, e, human_bytes):
    """Check this PC: the optional AI+ model - state, one-time download (with progress), or copy from a folder."""
    if ap["ready"]:
        return ("<div class='card' id='aiplus' style='margin-top:14px'><b>AI+ model is installed</b>"
                "<div class='muted'>PE-Core L/14 (Meta, Apache-2.0), every file is checked. Choose AI+ when you make a reel or a variant, "
                "and compare it with AI using Compare blind.</div>"
                f"<div class='muted ae-path' style='margin-top:4px'>{e(ap['path'])}</div></div>")
    dl = ap["download"]
    running = dl["state"] == "running"
    return ("<div class='card' id='aiplus' style='margin-top:14px'><b>AI+ — a stronger model (optional)</b>"
            "<div class='muted'>PE-Core L/14 (Meta, Apache-2.0) understands people, places and events much better than the built-in AI "
            "model. It works on this PC without internet; the first analysis of new videos is slower (about 1–2 s per checked frame). "
            f"Download once: {human_bytes(ap['bytes'])}, from huggingface.co (free); every file is checked.</div>"
            "<div class='row' style='margin-top:10px'>"
            f"<button type='button' id='apDl' {'disabled' if running else ''}>Download AI+ model</button>"
            f"<button type='button' class='btn2' id='apCancel' {'' if running else 'hidden'}>Stop</button>"
            "<button type='button' class='btn2' id='apImport'>Copy from a folder…</button>"
            "<span class='muted' id='apMsg'></span></div>"
            "<div class='progress' style='margin-top:8px'><i id='apBar' style='width:0%'></i></div>"
            + (f"<div class='errbox' style='margin-top:8px'>{e(dl['error'])}</div>" if dl["state"] == "failed" and dl["error"] else "")
            + "</div>"
            "<script>(function(){const m=document.getElementById('apMsg'),b=document.getElementById('apBar'),d=document.getElementById('apDl'),"
            "c=document.getElementById('apCancel');"
            "async function poll(){try{const r=await fetch('/api/auto/aiplus',{cache:'no-store'});const x=await r.json();"
            "if(x.ready){location.href='/auto/check?aiplus='+Date.now()+'#aiplus';return}const p=x.total?Math.floor(100*x.done/x.total):0;b.style.width=p+'%';"
            "if(x.state==='running'){m.textContent=p+' %';d.disabled=true;c.hidden=false;setTimeout(poll,1000)}"
            "else{d.disabled=false;c.hidden=true;if(x.state==='failed')m.textContent=x.error||'Failed';}}catch(e){setTimeout(poll,2000)}}"
            "d.onclick=async()=>{d.disabled=true;m.textContent='Starting…';await fetch('/api/auto/aiplus/download',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});poll()};"
            "c.onclick=async()=>{await fetch('/api/auto/aiplus/download',{method:'POST',headers:{'Content-Type':'application/json'},body:'{\"cancel\":1}'})};"
            "document.getElementById('apImport').onclick=async()=>{m.textContent='A Windows folder window is open — it may be behind this window.';"
            "const r=await fetch('/api/auto/aiplus/import',{method:'POST'});const x=await r.json();m.textContent=x.ok?'Installed.':(x.error||'Not installed');if(x.ok)setTimeout(()=>{location.href='/auto/check?aiplus='+Date.now()+'#aiplus'},800)};"
            + ("poll();" if running else "") + "})();</script>")


def _theme_choice(e, current="", ai_ready=True):
    """AI+ only: an optional theme. Hidden while another mode is ticked (a theme needs AI+)."""
    opts = "".join(f"<option value='{k}' {'selected' if k == current else ''}>{e(v)}</option>" for k, v in ae.THEMES.items())
    return (f"<div class='ae-theme' data-theme-box style='margin-bottom:14px' {'hidden' if ai_ready and current == '' else ''}>"
            f"<h2>Theme (AI+)</h2><select name='theme'><option value=''>No theme — the best moments</option>{opts}</select>"
            "<div class='muted' style='margin-top:4px;font-size:13px'>With a theme, AI+ looks through all the videos for moments that "
            "match it (for example only the sea).</div></div>"
            "<script>(function(){const box=document.currentScript.previousElementSibling,f=box.closest('form');if(!f)return;"
            "function upd(){const r=f.querySelector(\"input[name=mode]:checked\")||f.querySelector(\"input[type=hidden][name=mode]\");"
            "box.hidden=!(r&&r.value==='semantic_plus')}f.querySelectorAll('input[name=mode]').forEach(x=>x.addEventListener('change',upd));upd()})();</script>")


def _mode_choice(ai_ready, plus_ready, e, current=None, allow_technical=False, heading=True):
    """How moments are chosen: AI (accepted), AI+ (optional stronger model), or - only without any model, or for a
    variant whose model is gone - Technical only. The checked option is always one that can be built."""
    if not ai_ready and not plus_ready:
        return ("<div class='callout card' style='margin:6px 0 14px'><b>AI model not available.</b> Without it MediaEngine can only use the "
                "<b>Technical only</b> selection (sharpness, motion, exposure); it does not understand what happens in the video."
                "<label style='display:flex;gap:8px;margin-top:8px'><input type='checkbox' name='mode' value='technical' required> "
                "Build with Technical only</label></div>")
    offered = [m for m, ok in (("semantic", ai_ready), ("semantic_plus", plus_ready)) if ok] + (["technical"] if allow_technical else [])
    want = current if current in offered else offered[0]
    if offered == ["semantic"]:
        return f"<input type='hidden' name='mode' value='semantic'><div class='muted' style='margin:4px 0 10px;font-size:13px'>{AIPLUS_HINT}</div>"
    labels = {"semantic": AI_LABEL, "semantic_plus": AIPLUS_LABEL, "technical": "Technical only (sharpness, motion, exposure)"}
    radios = "".join(f"<label><input type='radio' name='mode' value='{m}' {'checked' if m == want else ''}> {e(labels[m])}</label>" for m in offered)
    return (f"<h2>How moments are chosen</h2>" if heading else "") + f"<div class='ae-choices'>{radios}</div>"


def _variant_form(pid, rev, e, first=False, model_ready=True):
    s = rev["settings"] if rev else {"length": 15, "format": "social_hd", "sound": "auto"}
    lengths = "".join(f"<label><input type='radio' name='length' value='{L}' {'checked' if int(s['length']) == L else ''}> {L} s</label>" for L in ae.LENGTHS)
    formats = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if s['format'] == k else ''}> {e(v['short'])}</label>" for k, v in ae.FORMATS.items())
    short_sound = {"auto": "Auto", "source": "Source sound", "mute": "Mute"}     # the same words as on the new-reel page
    sounds = "".join(f"<label><input type='radio' name='sound' value='{k}' {'checked' if s['sound'] == k else ''}> {e(short_sound.get(k, k.title()))}</label>" for k in ae.SOUNDS)
    base = f"<input type='hidden' name='base_revision_id' value='{rev['id']}'>" if rev else ""
    mode = ""
    plus_ready = ae.aiplus_status()["ready"]
    cur = (rev["settings"].get("mode") if rev else None)
    cur_ok = (cur == "semantic" and model_ready) or (cur == "semantic_plus" and plus_ready)
    if not model_ready and not plus_ready:
        if not rev or cur in ae.AI_MODES:
            mode = ("<label class='muted' style='display:flex;gap:8px;margin:8px 0'><input type='checkbox' name='mode' value='technical' required> "
                    "Build without AI (Technical only: sharpness, motion, exposure)</label>")
    elif not (rev and cur_ok and not (model_ready and plus_ready)):     # more than one way, or the revision's model is gone
        mode = _mode_choice(model_ready, plus_ready, e, cur, allow_technical=bool(rev) and (cur == "technical" or not cur_ok), heading=False)
    if plus_ready:
        if not mode and cur:              # one way only (the revision's): say so, so the theme box knows the mode
            mode = f"<input type='hidden' name='mode' value='{e(cur)}'>"
        mode += _theme_choice(e, (rev["settings"].get("theme") or "") if rev else "", model_ready)
    note = "" if first else ("The current revision stays as it is. Format and sound variants keep its removed moments and your edits "
                             "and reuse the analysis; a new length chooses the moments again (removed ones stay out).")
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


def _review_html(p, rev, e, building=False):
    res = rev.get("result") or {}
    segs = res.get("segments") or []
    total = float(rev.get("duration_s") or res.get("actual_duration_s") or 1) or 1
    is_acc = p["accepted_revision_id"] == rev["id"]
    fmt = ae.FORMATS.get(rev["settings"]["format"], {})
    strip = "".join(
        f"<button data-seek='{s['reel_in_s']}' data-seg data-in='{s['reel_in_s']}' data-out='{s['reel_out_s']}' "
        f"style=\"flex:{max(0.2, s['reel_out_s'] - s['reel_in_s']):.3f};background-image:url('/auto/rev/{rev['id']}/thumb/{s['position']}.jpg')\" "
        f"title='{e(s['source_name'])} {_fmt_s(s['source_in_s'])}–{_fmt_s(s['source_out_s'])}' translate='no'>{s['position']}</button>"
        for s in segs)
    in_reel = {s["event_id"] for s in segs}
    pool = [c for c in (res.get("candidate_pool") or []) if c["event_id"] not in in_reel][:40]
    score_word = "оценка" if ae.ui_language() == "ru" else "score"      # options are not translated (file names in them)
    opts = "".join(f"<option value='{e(c['event_id'])}' translate='no'>{e(c['source_name'])} {_fmt_s(c['start_s'])}–{_fmt_s(c['end_s'])} · {score_word} {float(c['score']):.2f}</option>" for c in pool)

    durs = {str(sg["source_name"]): _source_seconds(p["id"], str(sg["source_name"])) for sg in (res.get("segments") or [])}

    def edit_row(s):
        eid = e(s["event_id"])
        badge = " · edge trimmed" if s.get("camera_drop_trim") else (" · your trim" if s.get("manual_trim") else "")
        repl = (f"<label class='muted'>replace with <select name='replace_{eid}' style='max-width:260px'><option value=''>— keep —</option>{opts}</select></label>"
                if opts else "")
        return (f"<div class='ae-seg ae-edit' data-seg data-in='{s['reel_in_s']}' data-out='{s['reel_out_s']}' "
                f"data-dur='{durs.get(str(s['source_name']), 0):.2f}'><b class='pos'>{s['position']}</b>"
                f"<div><div><span translate='no'>{e(s['source_name'])}</span> <span class='muted' style='white-space:nowrap'>· source {_fmt_s(s['source_in_s'])}–{_fmt_s(s['source_out_s'])}{badge}</span></div>"
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
    if rev["settings"].get("selection"):      # the user's own choice of moments: that is why it is shorter
        short_html = (f"<div class='callout card' style='margin-top:8px'>The reel is shorter than {target:.0f} s because you removed or "
                      f"trimmed moments. Add a moment below or let MediaEngine choose again.</div>") if target and total < target - 1.0 else ""
    else:
        short_html = (f"<div class='callout card' style='margin-top:8px'>Requested {target:.0f} s, got {total:.1f} s: "
                      f"there were not enough different moments in this footage for a longer reel.</div>") if target and total < target - 1.0 else ""
    skipped = res.get("skipped_inputs") or []
    skipped_html = ("<div class='muted' style='margin-top:6px'>Skipped: " + ", ".join(f"<span translate='no'>{e(x['name'])}</span> ({_skip_reason_html(ae.friendly_skip(x['reason']), e)})" for x in skipped) + "</div>") if skipped else ""
    sm = str(res.get("selection_mode", ""))
    mode = ("AI moments (FAST_LOCAL)" if sm.startswith("FAST_LOCAL") else "AI+ moments (PE-Core L/14)" if sm.startswith("PE_CORE")
            else "Technical only (no AI)")
    theme_name = ae.THEMES.get(str(res.get("theme") or ""), "")
    notes = []          # html pieces; file names stay exactly as they are in both languages

    def names(xs):
        return ", ".join(f"<span translate='no'>{e(str(x).strip())}</span>" for x in xs if str(x).strip())
    for w in res.get("warnings") or []:
        if w.startswith("OVERLAPPING_MOMENTS_DROPPED"):
            notes.append(f"{w.split(':')[-1]} overlapping moment(s) of the same video were left out so nothing repeats")
        elif w.startswith("SELECTION_SEARCH_TOP_"):
            notes.append(f"for this length the best {w.rsplit('_', 1)[-1]} moments were compared")
        elif w.startswith("PREVIEW_QUALITY_USED:"):
            notes.append(e("lower quality (analysis preview) used for: ") + names(w.split(":", 1)[1].split(","))
                         + e(" - the original could not be re-cut"))
        elif w == "HDR_NOT_CONVERTED":
            notes.append("HDR video could not be converted on this PC: colours may look grey")
        elif w.startswith("THEME_FEW_MATCHES"):
            notes.append("few moments match the theme, so the reel also uses other good moments")
        elif w.startswith("THEME:") and w.endswith("_MATCHING_MOMENTS"):
            n = w.split(":")[-1].split("_")[0]
            notes.append(f"moments that match the theme: {int(n) if n.isdigit() else 0}")
    if res.get("hdr_sources"):
        notes.append(e("HDR video converted to normal colours: ") + names(res["hdr_sources"]))
    if res.get("deinterlaced_sources"):
        notes.append(e("camcorder video de-interlaced: ") + names(res["deinterlaced_sources"]))
    if res.get("widened_sources"):
        notes.append(e("wide picture stored in narrow pixels shown in its real shape: ") + names(res["widened_sources"]))
    skipped_html_extra = ("<div class='muted' style='margin-top:4px'>" + " · ".join(notes) + "</div>") if notes else ""
    exp_html = ""
    if is_acc:
        last = next((x for x in p["exports"] if x["revision_id"] == rev["id"]), None)
        exp_html = (f"<form method='post' action='/auto/p/{p['id']}/export' id='exportForm' style='margin-top:10px' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\">"
                    f"<input type='hidden' name='dest' id='exportDest' value=''>"
                    f"<div class='row' style='flex-wrap:wrap'><button class='ae-big'>Export MP4</button>"
                    f"<button type='button' class='btn2' id='exportToBtn'>Export to another folder…</button></div>"
                    f"<div class='muted' style='margin-top:4px'>Saves to <span class='ae-path' translate='no'>{e(str(ae.default_export_dir()))}</span></div>"
                    f"<div class='muted' id='exportMsg'></div></form>")
        if last:
            exp_html += (f"<div class='card' style='margin-top:10px'><b>Exported</b><div class='ae-path'>{e(last['path'])}</div>"
                         f"<div class='row' style='margin-top:8px;flex-wrap:wrap'><form method='post' action='/auto/export/{last['id']}/open'><button>Open video</button></form>"
                         f"<form method='post' action='/auto/export/{last['id']}/reveal'><button class='btn2'>Show in folder</button></form>"
                         f"<button type='button' class='btn2' id='copyPath' data-path='{e(last['path'])}'>Copy path</button></div></div>")
    undo = "Revert" if ae.previous_accepted(p["id"]) else "Undo accept"     # with no earlier one, Revert just un-accepts
    actions = (f"<span class='badge ready'>Accepted</span><form method='post' action='/auto/p/{p['id']}/revert'><button class='btn2'>{undo}</button></form>" if is_acc else
               f"<form method='post' action='/auto/p/{p['id']}/accept' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\"><input type='hidden' name='revision_id' value='{rev['id']}'><button class='ae-big'>Accept this version</button></form>")
    excl_hidden = "".join(f"<input type='hidden' name='exclude' value='{e(x)}'>" for x in rev["settings"].get("exclude", []))
    # only versions of the same format: a vertical reel next to a horizontal one is not a blind comparison
    others = [r for r in p["revisions"] if r["id"] != rev["id"] and r["settings"].get("format") == rev["settings"].get("format")]
    compare_html = ""
    if others:
        acc_ok = p["accepted_revision_id"] in [r["id"] for r in others]
        default_other = p["accepted_revision_id"] if acc_ok else others[-1]["id"]
        opts_c = "".join(f"<option value='{r['id']}' {'selected' if r['id'] == default_other else ''}>R{int(r['number']):03d}</option>" for r in others)
        compare_html = (f"<form method='post' action='/auto/p/{p['id']}/compare' class='row' style='margin-top:10px;gap:6px;flex-wrap:wrap'>"
                        f"<input type='hidden' name='a' value='{rev['id']}'><span class='muted'>Compare blind with</span>"
                        f"<select name='b'>{opts_c}</select><button class='btn2'>Compare</button></form>")
    if building:          # a new version is being made: the editor of this one would look like edits were lost
        editor = ("<div class='card'><h2 style='margin-top:0'>Moments in this reel</h2><div class='muted'>A new version is being "
                  "built from your choice. Editing is possible again when it is ready.</div></div>")
        variant = ""
    else:
        editor = f"""<form class='card' method='post' action='/auto/p/{p['id']}/edit' id='editForm'><h2 style='margin-top:0'>Moments in this reel</h2>
<input type='hidden' name='revision_id' value='{rev['id']}'><input type='hidden' name='base_revision_id' value='{rev['id']}'>
<input type='hidden' name='length' value='{rev['settings']['length']}'><input type='hidden' name='format' value='{e(rev['settings']['format'])}'>
<input type='hidden' name='sound' value='{e(rev['settings']['sound'])}'><input type='hidden' name='mode' value='{e(rev['settings']['mode'])}'>{excl_hidden}
<div id='segList'>{rows or "<div class='muted'>No segment details for this revision.</div>"}</div>{add_html}
<div class='muted' style='margin-top:8px'>Times are in the source file. Every change makes a new version; this one stays as it is.</div>
<div class='errbox' id='editErr' style='margin-top:8px' hidden></div>
<div class='row' style='margin-top:10px;flex-wrap:wrap'><button>Apply my edits</button>
<button class='btn2' formaction='/auto/p/{p['id']}/variant' name='rechoose' value='1'>Let MediaEngine choose again without removed moments</button></div></form>"""
        variant = _variant_form(p['id'], rev, e, model_ready=ae.model_status()['ready'])
    return f"""<div class='ae-player' style='margin-top:14px'>
<div class='card'><video id='reel' class='ae-video' controls preload='metadata' src='/auto/rev/{rev['id']}/video'></video>
<div class='ae-strip film'>{strip}</div>
<div class='muted'>Revision R{int(rev['number']):03d} · {e(fmt.get('short',''))} {rev['width']}×{rev['height']} · {total:.2f} s · sound {e(_sound_label(rev['settings']['sound'], res))} · <span>{e(mode)}</span>{(" · <span>theme</span> <span>" + e(theme_name) + "</span>") if theme_name else ""}</div>{short_html}{skipped_html}{skipped_html_extra}
<div class='row' style='margin-top:12px;flex-wrap:wrap'>{actions}</div>{compare_html}{exp_html}</div>
{editor}</div>
{variant}"""


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
        req = int(r["settings"]["length"])
        got = float(r.get("duration_s") or req)
        length_txt = f"{req} s" if abs(got - req) <= 1.0 else f"{got:.1f} s (requested {req} s)"   # what the reel really is
        rows += (f"<a class='ae-seg' style='grid-template-columns:70px 1fr auto' href='/auto/p/{p['id']}?rev={r['id']}'><b>R{int(r['number']):03d}</b>"
                 f"<span>{e(f)} · {length_txt} · sound {e(r['settings']['sound'])}{(' · ' + str(ex) + ' excluded') if ex else ''}{' · edited by you' if r['settings'].get('selection') else ''}"
                 f" <span class='muted'>· {e(_when(r['created_at']))}</span></span><span>{tag}{here}</span></a>")
    return f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>Revisions</h2>{rows}</div>"
