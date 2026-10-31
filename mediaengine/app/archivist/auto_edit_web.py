"""Auto Edit pages for the existing Archivist/MediaEngine Flask UI."""
from __future__ import annotations

import json
import os
import time
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
.ae-state.PREPARED{color:var(--cyan);border-color:var(--line2)}
.ae-choices{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px}.ae-choices label{display:flex;gap:8px;align-items:center;
 padding:10px 14px;border:1px solid var(--line2);border-radius:12px;cursor:pointer;background:var(--card2)}
.ae-choices input{accent-color:var(--orange)}.ae-choices label:has(input:checked){border-color:var(--orange);box-shadow:0 0 0 1px var(--orange) inset}
.ae-choices label.off{opacity:.45;cursor:not-allowed}
.ae-choices label.ae-look{flex-direction:column;align-items:center;padding:8px}.ae-look-pic{display:block;max-height:180px;max-width:220px;border-radius:8px}
.ae-big{font-size:17px;padding:12px 22px}
.ae-bar{height:12px;border-radius:8px;background:#0b1118;border:1px solid var(--line);overflow:hidden}.ae-bar i{display:block;height:100%;background:var(--orange);transition:width .4s}
.ae-player{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:16px}@media(max-width:1000px){.ae-player{grid-template-columns:1fr}}
.ae-video{display:block;margin:0 auto;max-width:100%;max-height:calc(72vh / var(--z,1));background:#000;border-radius:12px}
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


# Back after an error: a page the browser restores from its cache keeps the buttons its form disabled on submit
_REENABLE_JS = """
document.addEventListener('submit',ev=>{ev.target.querySelectorAll('button:not([disabled])').forEach(b=>b.dataset.reen='1')},true);
window.addEventListener('pageshow',ev=>{if(ev.persisted)document.querySelectorAll('button[data-reen]').forEach(b=>{b.disabled=false;delete b.dataset.reen})});"""

_UPDATE_STEP = {"downloading": "Downloading the new version…", "preparing": "Putting the new version next to this one…",
                "switching": "Starting the new version…"}
_AUTO_RESULT = {"newest": "This is the newest version.", "started": "A new version is being installed.",
                "installing": "A new version is being installed.",
                "needs_installer": "A newer version needs the full installer (see Check for updates).",
                "busy": "Work was running: it tries again in a few minutes.",
                "check_failed": "No answer from GitHub: it tries again in a few minutes."}


def _recent_failure(dl: dict) -> bool:
    """A failed download is shown for an hour after it failed (not on every visit until the next try)."""
    import time as _t
    return dl.get("state") == "failed" and bool(dl.get("error")) and _t.time() - float(dl.get("failed_at") or 0) < 3600


def status_pct(s: dict) -> int:
    if s.get("state") != "downloading":
        return 100
    return int(100 * int(s.get("done") or 0) / int(s["total"])) if s.get("total") else 0


_STAGE_SEEN: dict = {}
_RESUMED: list = []
_VOICE_RESUMED: list = []


def whats_new_card(e) -> str:
    """What changed in this version, once (only for someone who already used MediaEngine): the 8 newest, the rest
    folded away. On Home and on Auto Edit; OK hides it on both."""
    wn = [] if (ae.whats_new_seen() or not ae.selftest_passed()) else ae.whats_new_items()
    return "" if not wn else (
        "<div class='card callout' style='margin-bottom:14px'><div class='row space'><b>New in this version</b>"
        "<form method='post' action='/auto/whats-new/seen' style='margin:0'><button class='btn2'>OK</button></form></div>"
        "<ul style='margin:6px 0 0'>" + "".join(f"<li>{e(x)}</li>" for x in wn[:8]) + "</ul>"
        + (f"<details style='margin-top:6px'><summary><span>Earlier changes:</span> {len(wn) - 8}</summary><ul style='margin:6px 0 0'>"
           + "".join(f"<li>{e(x)}</li>" for x in wn[8:]) + "</ul></details>" if len(wn) > 8 else "")
        + "</div>")


def first_time_card() -> str:
    return "" if ae.selftest_passed() else (
        "<div class='card callout' style='margin-bottom:14px'><b>First time on this PC?</b> "
        "<span class='muted'>Check this PC first: it shows whether the AI model and video tools are found and builds a 5-second test reel "
        "(about a minute; your videos are not used).</span>"
        "<div class='row' style='margin-top:8px'><a class='btn' href='/auto/check'>Check this PC</a></div></div>")


def _voice_on_home() -> bool:
    try:
        from . import voice as _vo
        return _vo.SHOW_ON_HOME or _vo.installed()
    except Exception:
        return False


def stage_eta_s(j: dict, now: float | None = None):
    """Seconds left in the current stage (finding moments, cutting) from the real rate since this stage was first seen:
    None until at least one video/piece is done in it and 20 s have passed. Stage-wise because finding moments in 4K
    videos is most of a build (the whole-job percentage made "2 hours left" of a job that needed 34 more minutes)."""
    import time as _t
    now = _t.time() if now is None else now
    jid, st = j.get("id"), j.get("stage")
    done, total = int(j.get("done") or 0), int(j.get("total") or 0)
    if j.get("status") != "running" or st not in ("analyze", "render") or total < 2:
        _STAGE_SEEN.pop(jid, None)
        ae.ENGINE_ETA.pop(jid, None)
        return None
    eng = ae.ENGINE_ETA.get(jid)
    if eng and eng[0] == st:      # the engine knows better (videos analysed before go first and take seconds)
        return None if eng[1] is None else max(0, round(float(eng[1]) - max(0.0, now - eng[2])))
    seen = _STAGE_SEEN.get(jid)
    if not seen or seen[0] != st or done < seen[2]:
        _STAGE_SEEN[jid] = (st, now, done)
        return None
    n = done - seen[2]
    if n < 1 or now - seen[1] < 20 or done >= total:
        return None
    return round((now - seen[1]) / n * (total - done))


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
        x = round(float(x), 1)          # 59.97 s -> 1:00.0, never "0:60.0"
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


MAX_DAYS = 31                                   # "A reel for every day": at most this many reels at once


def _when_label(iso) -> str:
    """A stored time as this PC's local day and time: "16 октября 2026, 18:45" / "16 Oct 2026, 18:45" (the app stores its
    own times as local time without a zone; one with a zone is turned into local time)."""
    try:
        from datetime import datetime
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if t.tzinfo is not None:
            t = t.astimezone()
        return f"{_day_label(t.strftime('%Y-%m-%d'))}, {t:%H:%M}"
    except Exception:
        return ""


def _every_day_form(folder: Path, days: list, e) -> str:
    """A trip or a holiday: one reel for each day at once (built one after another)."""
    usable = [d for d in days if 1 <= len(d["files"]) <= ae.MAX_INPUTS]
    if len(usable) < 2:
        return ""
    if len(usable) > MAX_DAYS:                  # more than one press makes (the button would only be refused)
        return (f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'>A reel for every day</h2>"
                f"<div class='muted'><span>This folder has videos of many days:</span> {len(usable)}. "
                f"<span>A reel for every day is made for at most 31 days at once: choose a day below, or put the videos "
                f"of one trip in a folder of their own.</span></div></div>")
    last = ae.last_new_settings()
    fmt0 = last.get("format", "social_hd")
    lengths = "".join(f"<label><input type='radio' name='length' value='{L}' {'checked' if L == 30 else ''}> {L} s</label>" for L in ae.LENGTHS)
    formats = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if k == fmt0 else ''}> {e(v['short'])}</label>"
                      for k, v in ae.FORMATS.items())
    ms = ae.model_status()
    mode = _mode_choice(ms["ready"], ae.aiplus_status()["ready"], e, current=last.get("mode"), heading=False)
    skipped = len(days) - len(usable)
    return (f"<form method='post' action='/auto/create-days' class='card' style='margin-top:14px' "
            f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\"><h2 style='margin-top:0'>A reel for every day</h2>"
            f"<div class='muted'><span>One reel for each of these days, made one after another:</span> {len(usable)}"
            + (f". <span>Days with more than {ae.MAX_INPUTS} videos are left out (tick their videos below):</span> {skipped}" if skipped else "")
            + "</div>"
            f"<input type='hidden' name='folder' value='{e(str(folder))}'><input type='hidden' name='sound' value='{e(last.get('sound', 'auto'))}'>"
            f"<input type='hidden' name='framing' value='{e(last.get('framing', 'fill'))}'>"
            f"<input type='hidden' name='look' value='{e(last.get('look', 'natural'))}'>"
            f"<div class='ae-choices'>{lengths}</div><div class='ae-choices'>{formats}</div>{mode}"
            f"<div class='row' style='flex-wrap:wrap;gap:10px;align-items:center'><button class='ae-big'>Make {len(usable)} reels</button>"
            f"<button class='btn2 ae-big' name='prepare' value='1'>Prepare in advance</button></div>"
            f"<div class='muted' style='margin-top:6px'>Prepare in advance: the videos of every day are only analysed now (for example "
            f"overnight); each day's reel is then made in minutes.</div></form>")


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
            f"<div class='muted'>The day is taken from the file name (e.g. VID_20260714_…), otherwise from the recording time in the video, otherwise from the file's date.</div>"
            f"<table class='ae-files' style='margin-top:8px'>{''.join(day_rows)}</table></div>"
            + _every_day_form(folder, days, e) +
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


def _json_obj() -> dict:
    """The request's JSON body when it is an object, else {} (a list or a number never reaches .get())."""
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


_PATH_IN_TEXT = None


def _protect_paths(escaped: str) -> str:
    """Paths inside an (escaped) message stay exactly as they are in Russian: "C:\\Music\\Only you.mp3" must not
    become "...\\Всего you.mp3"."""
    import re as _re
    global _PATH_IN_TEXT
    if _PATH_IN_TEXT is None:
        _PATH_IN_TEXT = _re.compile(r"((?<![A-Za-z])[A-Za-z]:[\\/][^<\n]*?|\\\\[^<\n]*?)(?=\s\(|\s\[|$|\n)")
    return _PATH_IN_TEXT.sub(lambda m: "<span translate='no'>" + m.group(1) + "</span>", escaped)


def register(app, layout, e, human_bytes):
    """Attach Auto Edit routes to the existing app (called from web.create_app)."""

    @app.before_request
    def _ids_in_range():
        # /auto/p/99999999999999999999: SQLite cannot even look such a number up (OverflowError -> 500): not found
        for v in (request.view_args or {}).values():
            if isinstance(v, int) and not (-(2 ** 63) <= v < 2 ** 63):
                return "not found", 404
        return None

    @app.before_request
    def _ae_recover():
        # first request served by this process: a build left "running" by a crashed process is marked interrupted
        # (Retry-able), so Quit / Restart / switching builds are not refused for a job that no longer exists.
        # Only the process that actually serves pages does this - a second copy that cannot take the port never does.
        try:
            ae.ensure_schema()
            if not _RESUMED:
                ae.resume_queued()       # builds still waiting from the last run (an overnight set) go on
                _RESUMED.append(1)
                try:
                    from . import aiplus_library as _al
                    _al.resume_after_restart()      # AI+ preparation for the Library the closing interrupted
                except Exception:
                    pass
        except Exception:
            pass
        try:          # voice-overs left unfinished by a closed program: made again (once)
            if not _VOICE_RESUMED:
                _VOICE_RESUMED.append(1)
                from . import voice as _vo
                _vo.resume_after_restart()
        except Exception:
            pass
        try:          # orders from other programs (Orders\\Inbox): watched while the app runs
            from . import orders
            orders.start()
        except Exception:
            pass
        try:          # the owner's phone (his Telegram bot), when he set it up
            from . import telegram_bot
            telegram_bot.start()
        except Exception:
            pass

    def page(title, body, script=""):
        return layout(title, PAGE_CSS + body, script + _REENABLE_JS)      # translated (if Russian) for every page in i18n.install

    def err_page(msg, back="/auto"):
        # Back = the browser's back when possible: the form comes back with everything typed in it
        return page("Auto Edit", f"<div class='card'><h2>Could not continue</h2><div class='errbox' style='margin-bottom:12px'>{_protect_paths(e(msg))}</div>"
                                 f"<a class='btn btn2' href='{e(back)}' onclick='if(history.length>1){{history.back();return false}}'>Back</a></div>"), 400

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
            length = f"{float(ref.get('duration_s') or ref['settings']['length']):.1f} s" if ref else ""   # what the reel really is
            exp = ae.export_row(p["last_export_id"]) if p.get("last_export_id") else None
            n_src = len(ae.project_inputs(p)) if p["source_present"] else 0
            acts = f"<a class='btn btn2' href='/auto/p/{p['id']}'>{'Review' if p['revisions'] else 'Open'}</a>"
            if p["accepted_revision_id"] and not (exp and exp.get("revision_id") == p["accepted_revision_id"]):
                acts += f"<form method='post' action='/auto/p/{p['id']}/export' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\"><button class='btn2'>Save MP4</button></form>"
            if exp:
                acts += (f"<form method='post' action='/auto/export/{exp['id']}/open'><input type='hidden' name='back' value='/auto'><button class='btn2'>Open video</button></form>"
                         f"<form method='post' action='/auto/export/{exp['id']}/reveal'><input type='hidden' name='back' value='/auto'><button class='btn2'>Show in folder</button></form>")
            if p["archived"] or not any(j["status"] in ("queued", "running") for j in p["jobs"]):    # (not while it is being built)
                acts += f"<form method='post' action='/auto/p/{p['id']}/archive'><button class='btn2'>{'Unarchive' if p['archived'] else 'Archive'}</button></form>"
            if p["archived"] and not any(j["status"] in ("queued", "running") for j in p["jobs"]):
                acts += (f"<form method='post' action='/auto/p/{p['id']}/delete' onsubmit=\"return confirm(document.getElementById('delq').textContent)\">"
                         f"<button class='btn2' title='Saved MP4 files and your original videos stay'>Delete</button></form>")
            last_txt = ("Saved: <span translate='no'>" + e(Path(exp["path"]).name) + "</span>") if exp else "Not saved yet"
            cards += (f"<div class='card'><a href='/auto/p/{p['id']}' style='display:block'>"
                      f"<div class='row space'><b style='font-size:17px' translate='no'>{e(p['title'])}</b><span class='ae-state {p['state']}'>{p['state']}</span></div>"
                      f"<div class='muted' style='margin-top:6px'>{' · '.join(x for x in (str(n_src) + (' chosen video(s)' if p.get('files') else ' video file(s) in folder'), e((preset + ' ' + length).strip()), str(len(p['revisions'])) + ' revision(s)') if x)}</div>"
                      f"<div class='muted'>{last_txt}</div>"
                      # (several projects of one folder have one name: when the last version was made tells them apart)
                      + (f"<div class='muted small' translate='no'>{e(when_)}</div>" if (when_ := _when_label(
                          (p["revisions"][-1].get("created_at") if p["revisions"] else None) or p.get("created_at"))) else "")
                      + "</a>"
                      + ("" if p["source_present"] else "<div class='errbox' style='margin-top:6px'>Source videos are not available (drive disconnected?)</div>")
                      + f"<div class='row' style='margin-top:10px;flex-wrap:wrap;gap:6px'>{acts}</div></div>")
        if not cards:
            cards = "<div class='card muted'>No Auto Edit projects yet. Choose a folder with your videos to make the first one.</div>"
        model_note = "" if ms["ready"] else _model_card(ms, e, back="/auto")
        freed = request.args.get("deleted", "")
        deleted_html = (f"<div class='card ae-done' style='margin-bottom:10px'><span>Project deleted. Freed:</span> {human_bytes(int(freed))}</div>"
                        if freed.isascii() and freed.isdigit() else "")
        try:
            exp_dir = ae.default_export_dir()
            has_exports = exp_dir.is_dir() and any(x.suffix.lower() == ".mp4" for x in exp_dir.iterdir())
        except OSError:
            has_exports = False
        try:
            from . import orders
            n_orders = len(orders.inbox()) + len(orders.unfinished())
        except Exception:
            n_orders = 0
        check_btn = ("<div class='row' style='float:right;gap:8px'>"
                     + ("<form method='post' action='/auto/exports/open' style='margin:0'><button class='btn2'>Exported reels</button></form>"
                        if has_exports else "")
                     + (f"<a class='btn btn2' href='/auto/orders'><span>Orders</span> <span class='badge review' translate='no'>{n_orders}</span></a>"
                        if n_orders else "") + "</div>")
        # folders of the last reels (one click to a new reel from the same place)
        recent, seen_f = [], set()
        for rp in ae.list_projects(include_archived=True):
            f_ = str(rp.get("folder") or "")
            if f_ and f_.lower() not in seen_f and not rp.get("files") and ae.folder_available(f_):
                seen_f.add(f_.lower()); recent.append(f_)
            if len(recent) >= 5:
                break
        recent_html = ("<div class='row' style='margin-top:8px;gap:6px;flex-wrap:wrap'><span class='muted'>Recent folders:</span>"
                       + "".join(f"<a class='btn btn2' style='padding:5px 9px;font-size:13px' title='{e(f_)}' "
                                 f"href='/auto/new?folder={urllib.parse.quote(f_)}' translate='no'>{e(Path(f_).name or f_)}</a>" for f_ in recent)
                       + "</div>") if recent else ""
        whats_new, first = whats_new_card(e), first_time_card()
        body = f"""<div class='pagehead'>{check_btn}<div class='eyebrow'>Create</div><h1>Auto Edit</h1>
<div class='lead'>Choose a folder of videos (or single videos), pick length, format and sound, and MediaEngine builds a reel from the best moments.
Your original files are only read, never changed.</div></div>{first}{whats_new}
<div class='card'><h2 style='margin-top:0'>New reel</h2>
<form method='get' action='/auto/new' class='row' style='flex-wrap:wrap' onsubmit="document.getElementById('pickMsg').textContent='Checking the videos… (a few seconds per video)'">
<button type='button' class='ae-big' id='pickBtn'>Choose folder…</button>
<button type='button' class='btn2 ae-big' id='pickFilesBtn'>Choose videos…</button>
<input name='folder' id='folderInput' required placeholder='or paste a folder path, e.g. D:\\Videos\\Trip' style='flex:1;min-width:280px'>
<button class='btn btn2 ae-big'>Continue</button></form>
<div class='muted' id='pickMsg' style='margin-top:6px'></div>{recent_html}</div>{model_note}

<div class='section-title row space'><span>My projects</span><span class='row' style='gap:10px'>{"<input id='projFind' placeholder='Find a project' style='width:200px'>" if len(projects) > 6 else ""}<a class='muted' href='/auto?archived={'0' if request.args.get('archived')=='1' else '1'}'>{'Hide' if request.args.get('archived')=='1' else 'Show'} archived</a></span></div>
<span id='delq' hidden>Delete this project and all its versions for good? Saved MP4 files and your original videos stay.</span>{deleted_html}
<div class='ae-grid'>{cards}</div>"""
        script = """
document.getElementById('pickBtn').onclick=async()=>{const m=document.getElementById('pickMsg');m.textContent='A Windows folder window is open — it may be behind this window.';
 try{const r=await fetch('/api/auto/pick-folder',{method:'POST'});const x=await r.json();
 if(x.path){document.getElementById('folderInput').value=x.path;m.textContent='Checking the videos… (a few seconds per video)';location.href='/auto/new?folder='+encodeURIComponent(x.path)}
 else m.textContent=x.error||'No folder chosen.'}catch(e){m.textContent='Folder window failed: '+e}};
document.getElementById('pickFilesBtn').onclick=async()=>{const m=document.getElementById('pickMsg');m.textContent='A Windows window is open — it may be behind this window. Ctrl+click to choose several videos.';
 try{const r=await fetch('/api/auto/pick-files',{method:'POST'});const x=await r.json();
 if(x.files&&x.files.length){m.textContent='Checking the videos…';location.href='/auto/new?'+x.files.map(f=>'file='+encodeURIComponent(f)).join('&')}
 else if(x.folder){m.textContent=x.error||'';location.href='/auto/new?folder='+encodeURIComponent(x.folder)}
 else m.textContent=x.error||'No videos chosen.'}catch(e){m.textContent='Window failed: '+e}};
const pf=document.getElementById('projFind');if(pf)pf.oninput=()=>{const q=pf.value.trim().toLowerCase();
 document.querySelectorAll('.ae-grid>.card').forEach(c=>{c.style.display=(!q||c.textContent.toLowerCase().includes(q))?'':'none'})};"""
        return page("Auto Edit", body, script)

    @app.route("/auto/check", methods=["GET", "POST"])
    def ae_check():
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return err_page("This page can only be opened from MediaEngine itself.")   # it starts the engine and FFmpeg
        rows = ae.system_check()
        def looks_like_path(t):   # paths, versions, system names: shown exactly as they are
            return ":\\" in t or t.startswith("/") or "version" in t or "|" in t or t.startswith(("Windows-", "Linux", "Darwin", "3.1"))
        table = "".join(f"<tr><td>{('ℹ️' if r.get('level') == 'info' else '✅') if r['ok'] else '⚠️'}</td><td><b>{e(r['name'])}</b></td>"
                        f"<td class='{'ae-path' if looks_like_path(r['detail']) or r['name'] == 'Graphics card' else 'muted'}'>{e(r['detail'])}</td></tr>" for r in rows)
        test_html = ""
        ai_ready = ae.model_status()["ready"]
        ap = ae.aiplus_status()
        if request.method == "POST":
            busy_ = ae.app_busy()
            if busy_ and not ae.selftest_state()["running"]:     # two engines at once: the test would look broken
                return err_page(busy_, "/auto/check")
            from . import hwdecode as _hw
            if _hw.state().get("running"):
                return err_page("The graphics card is being tested (Check this PC). Wait until the test has finished.", "/auto/check")
            want = request.form.get("mode")
            want = want if (want == "semantic" and ai_ready) or (want == "semantic_plus" and ap["ready"]) else "technical"
            ae.selftest_start(want, 1800 if want == "semantic_plus" else 900)
            return redirect("/auto/check")
        st = ae.selftest_state()
        if st["running"]:
            test_html = (f"<div class='card' id='testRun' data-el='{st['elapsed_s']}' style='margin-top:14px'><b>Building the test reel…</b> "
                         f"<span id='testSec'>{int(st['elapsed_s'])}</span> s<div class='muted' style='margin-top:4px'>Up to a few minutes. "
                         f"You can leave this page: the result is shown here when it is ready.</div></div>")
        elif st["result"]:
            test_html = _selftest_html(st["result"], e)
        from .config import INSTALL
        builds = ae.other_builds()
        olds = ae.old_builds(2)
        done = request.args.get("removed", "")
        brows = "".join(f"<tr><td><b translate='no'>{e(b['name'])}</b>{(' · built ' + e(b['built'])) if b['built'] else ''}"
                        f"<div class='muted ae-path'>{e(b['path'])}</div></td>"
                        f"<td>{human_bytes(b['bytes'])}</td><td>"
                        + (f"<form method='post' action='/auto/check/use-build' style='margin-bottom:6px'>"
                           f"<input type='hidden' name='name' value='{e(b['name'])}'><button class='btn2' title='Projects stay the same'>Use this version</button></form>"
                           if b.get("can_switch") else "")
                        + f"<form method='post' action='/auto/check/remove-build' "
                        f"onsubmit=\"return confirm(document.getElementById('rmq').textContent)\">"
                        f"<input type='hidden' name='name' value='{e(b['name'])}'><button class='btn2'>Remove</button></form></td></tr>"
                        for b in builds)
        builds_html = (f"<div class='card' style='margin-top:14px'><b>Other MediaEngine versions on this PC</b>"
                       f"<div class='muted'>This one: <span class='ae-path'>{e(str(INSTALL))}</span>. Older versions are kept so you can go "
                       f"back to one; remove the ones you no longer need (projects and exports stay).</div>"
                       f"<span id='rmq' hidden>Remove this version? Your projects and exports are not affected.</span>"
                       + (f"<form method='post' action='/auto/check/remove-old-builds' style='margin-top:8px' "
                          f"onsubmit=\"return confirm(document.getElementById('rmoq').textContent)\"><button class='btn2'>"
                          f"Remove the older versions</button> <span class='muted'><span>keeps the two newest before this one;"
                          f" frees</span> {human_bytes(sum(b['bytes'] for b in olds))}</span></form>"
                          f"<span id='rmoq' hidden>Remove the older versions of MediaEngine? The two newest before this one stay, "
                          f"so you can still go back. Your projects and exports are not affected.</span>" if olds else "")
                       + f"<table class='ae-files' style='margin-top:8px'>{brows}</table></div>") if builds else ""
        if done:
            builds_html = f"<div class='card ae-done' style='margin-top:14px'>Removed <span translate='no'>{e(done)}</span>.</div>" + builds_html
        sb = ae.shared_cache_bytes()
        shared_html = (f"<div class='card row space' style='margin-top:14px;flex-wrap:wrap'><span class='muted'>What the AI found in your videos "
                       f"and the cut moments (kept for every reel, so the same video is never analysed twice): {human_bytes(sb)}</span>"
                       "<form method='post' action='/auto/check/free-shared' onsubmit=\"return confirm(document.getElementById('freeSharedQ').textContent)\">"
                       "<button class='btn2'>Free</button></form>"
                       "<span id='freeSharedQ' hidden>Free it? Every video is then analysed again - for a reel, for videos prepared in advance "
                       "and for AI+ in the Library (that can take hours for a big Library).</span></div>") if sb else ""
        cb = ae.all_work_cache_bytes()
        if cb:
            shared_html += (f"<div class='card row space' style='margin-top:14px;flex-wrap:wrap'><span class='muted'><span>Analysis and render caches "
                            f"of all projects (versions and saved MP4 stay; the next build of a project makes them again):</span> {human_bytes(cb)}</span>"
                            "<form method='post' action='/auto/check/free-caches'><button class='btn2'>Free</button></form></div>")
        if request.args.get("freed_shared"):
            shared_html = "<div class='card ae-done' style='margin-top:14px'>Freed.</div>" + shared_html
        if request.args.get("freed"):
            shared_html = (f"<div class='card ae-done' style='margin-top:14px'><span>Freed:</span> "
                           f"{human_bytes(int(request.args['freed']) if request.args['freed'].isascii() and request.args['freed'].isdigit() else 0)}</div>") + shared_html
        builds_html = shared_html + builds_html
        hw_html = _hwdecode_html(e) + _convert_gpu_html(e)
        body = (f"<div class='pagehead'><div class='eyebrow'>Tools</div><h1>Check this PC</h1>"
                f"<div class='lead'>What MediaEngine needs, and a 5-second test reel made from generated clips (your videos are not used).</div></div>"
                f"<div class='card'><table class='ae-files'>{table}</table></div>"
                f"<form method='post' class='card' style='margin-top:14px' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                f"<button name='mode' value='technical' {'disabled' if st['running'] else ''}>Build a test reel</button> "
                + (f"<button name='mode' value='semantic' class='btn2' {'disabled' if st['running'] else ''}>Build a test reel with the AI model</button> " if ai_ready else "")
                + (f"<button name='mode' value='semantic_plus' class='btn2' {'disabled' if st['running'] else ''}>Build a test reel with AI+</button> " if ap["ready"] else "")
                + f"<span class='muted'></span></form>{test_html}{hw_html}{_model_card(ae.model_status(), e, back='/auto/check')}{_aiplus_card(ap, e, human_bytes)}{builds_html}"
                f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
        script = """const hc=document.getElementById('hwRun');
if(hc){const t0=Date.now()-Number(hc.dataset.el||0)*1000;const tick=async()=>{try{const r=await fetch('/api/auto/hwtest',{cache:'no-store'});const x=await r.json();if(!x.running){location.href='/auto/check';return}
 document.getElementById('hwStep').textContent=x.step||''}catch(e){}document.getElementById('hwSec').textContent=Math.round((Date.now()-t0)/1000);setTimeout(tick,2000)};setTimeout(tick,0)}
const cg=document.getElementById('cgRun');
if(cg){const t0=Date.now()-Number(cg.dataset.el||0)*1000;const tick=async()=>{try{const r=await fetch('/api/auto/convert-gpu-test',{cache:'no-store'});const x=await r.json();if(!x.running){location.href='/auto/check';return}
 document.getElementById('cgStep').textContent=x.step||''}catch(e){}document.getElementById('cgSec').textContent=Math.round((Date.now()-t0)/1000);setTimeout(tick,2000)};setTimeout(tick,0)}
const tc=document.getElementById('testRun');
if(tc){const t0=Date.now()-Number(tc.dataset.el||0)*1000;const tick=async()=>{try{const r=await fetch('/api/auto/selftest',{cache:'no-store'});const x=await r.json();if(!x.running){location.href='/auto/check';return}}catch(e){}
 document.getElementById('testSec').textContent=Math.round((Date.now()-t0)/1000);setTimeout(tick,2000)};setTimeout(tick,2000)}"""
        return page("Check this PC", body, script)

    @app.post("/auto/check/hwtest")
    def ae_hwtest():
        from . import hwdecode
        if ae.app_busy():
            return err_page("Wait until the current build has finished", "/auto/check")
        if ae.selftest_state()["running"]:     # two speed tests at once measure each other
            return err_page("The test reel of Check this PC is being made. Wait until it is ready.", "/auto/check")
        ff = ae._ffmpeg()
        if not ff:
            return err_page("FFmpeg not found", "/auto/check")
        hwdecode.start(ff, ae.AE_ROOT / "hwtest")
        return redirect("/auto/check")

    @app.post("/auto/check/convert-gpu-test")
    def ae_convert_gpu_test():
        from . import converter as cv, hwdecode
        if ae.app_busy() or ae.selftest_state()["running"] or hwdecode.state().get("running"):
            return err_page("Wait until the current build or test has finished", "/auto/check")
        with ae.db() as con:
            busy = con.execute("SELECT id FROM jobs WHERE status IN ('running','queued') LIMIT 1").fetchone()
        if busy:
            return err_page("Wait until the current job (a conversion or an import) has finished", "/auto/check")
        cv.start_gpu_test(ae.AE_ROOT / "convert_gpu_test")
        return redirect("/auto/check")

    @app.get("/api/auto/convert-gpu-test")
    def ae_convert_gpu_test_state():
        from . import converter as cv
        st = cv.gpu_test_state()
        if request.args.get("full"):
            return jsonify(cv.gpu_test_saved())
        return jsonify(st)

    @app.post("/auto/check/hwtest-use")
    def ae_hwtest_use():
        from . import hwdecode
        r = hwdecode.saved()
        if r:
            r["off"] = request.form.get("on") != "1"
            hwdecode.save(r)
        return redirect("/auto/check")

    @app.get("/api/auto/hwtest")
    def ae_hwtest_state():
        from . import hwdecode
        if request.args.get("full"):       # support: the whole remembered result (times per clip and method)
            return jsonify(hwdecode.saved())
        st = hwdecode.state()
        step = st.get("step") or ""
        if ae.ui_language() == "ru":
            from .auto_edit_ru import PHRASES
            step = " ".join(PHRASES.get(x, x) for x in [step.split(":")[0]]) + (":" + step.split(":", 1)[1] if ":" in step else "")
        return jsonify({"running": st["running"], "elapsed_s": st["elapsed_s"], "step": step})

    @app.get("/api/auto/selftest")
    def ae_selftest_state():
        st = ae.selftest_state()
        return jsonify({"running": st["running"], "elapsed_s": st["elapsed_s"], "ok": bool((st["result"] or {}).get("ok"))})

    @app.post("/auto/check/free-shared")
    def ae_free_shared():
        try:
            ae.clear_shared_cache()
        except Exception as exc:
            return err_page(str(exc), "/auto/check")
        return redirect("/auto/check?freed_shared=1")

    @app.post("/auto/whats-new/seen")
    def ae_whats_new_seen():
        ae.mark_whats_new_seen()
        back = urllib.parse.urlparse(request.referrer or "").path      # (shown on Home and on Auto Edit: back to it)
        return redirect(back if back in ("/", "/auto") else "/auto")

    @app.post("/auto/check/free-caches")
    def ae_free_caches():
        try:
            freed = ae.clear_all_work_caches()
        except Exception as exc:
            return err_page(str(exc), "/auto/check")
        return redirect(f"/auto/check?freed={int(freed)}")

    @app.get("/auto/check/video")
    def ae_check_video():
        v = ae.selftest_video()
        if not v:
            return err_page("The test reel is not there (build it on Check this PC).")
        return send_file(str(v), mimetype="video/mp4", conditional=True)

    @app.post("/auto/check/use-build")
    def ae_use_build():
        name = request.form.get("name", "")
        try:
            target = ae.use_build(name)
        except Exception as exc:
            return err_page(str(exc), "/auto/check")
        body = (f"<div class='card'><h2 style='margin-top:0'><span>Switching to another version…</span> <span translate='no'>{e(name)}</span></h2>"
                f"<div class='muted'>This MediaEngine closes and the other version starts. This page opens it by itself.</div>"
                f"<div class='errbox' id='swMsg' style='margin-top:10px' hidden>The other version did not start. Start it from its folder: "
                f"<span class='ae-path' translate='no'>{e(str(Path(target) / 'Start MediaEngine.vbs'))}</span></div></div>")
        script = ("const want=" + json.dumps(target.replace("/", "\\").lower()) + ";let n=0;"
                  "async function t(){n++;try{const r=await fetch('/api/ping',{cache:'no-store'});const x=await r.json();"
                  "if(String(x.install||'').replace(/\\//g,'\\\\').toLowerCase()===want){location.href='/auto';return}}catch(e){}"
                  "if(n>150)document.getElementById('swMsg').hidden=false;setTimeout(t,n>150?3000:1000)}setTimeout(t,1500);")
        return page("Check this PC", body, script)

    # ------------------------------------------------------------ update (the "Update" button)

    @app.get("/auto/update")
    def ae_update():
        from . import updater as up
        try:
            from .i18n import ui_language
            ru = ui_language() == "ru"
        except Exception:
            ru = False
        s = dict(up.STATE)
        m = s.get("found") or {}
        from .config import BUILD as _B, VERSION as _V
        here = up.build_label(up.INSTALL.name) if up.build_order(up.INSTALL.name) else f"{_V} {_B}".strip()
        why = up.why_not()
        check_btn = ("<form method='post' action='/auto/update/check' style='display:inline' "
                     "onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                     "<button class='{cls}'>Check for updates</button></form>")
        detail = (f"<div class='muted ae-path' translate='no' style='margin-top:6px'>{e(s.get('detail') or '')}</div>"
                  if s.get("detail") else "")
        st = s.get("state")
        if st in ("downloading", "preparing", "switching"):
            body_state = (f"<div class='card' id='upRun'><h2 style='margin-top:0'><span>Updating to</span> <span translate='no'>{e(up.build_label(m.get('pkg')))}</span></h2>"
                          f"<div class='ae-bar'><i id='upBar' style='width:{status_pct(s)}%'></i></div>"
                          f"<div style='margin-top:8px'><span id='upStep'>{e(_UPDATE_STEP.get(st, ''))}</span></div>"
                          f"<div class='muted' style='margin-top:6px'>Do not close this window: MediaEngine restarts by itself and this page "
                          f"then opens the new version.</div>"
                          f"<div class='errbox' id='upSlow' style='margin-top:10px' hidden>The new version is taking long to start. If nothing "
                          f"happens, start MediaEngine from the desktop shortcut.</div>"
                          f"<div class='errbox' id='upBack' style='margin-top:10px' hidden>The new version did not start, so this version is "
                          f"running again. Details for support are in the logs folder.</div></div>")
        elif st in ("check_failed", "error"):
            again = (f"<form method='post' action='/auto/update/apply' style='display:inline;margin-right:8px'><button>Try again</button></form>"
                     if st == "error" and m.get("newer") and m.get("same_runtime") else "")
            body_state = (f"<div class='card'><div class='errbox'>{e(s.get('error') or '')}</div>{detail}"
                          f"<div style='margin-top:12px'>{again}{check_btn.format(cls='btn2')}</div></div>")
        elif st == "checked" and m:
            if not m.get("newer"):
                body_state = (f"<div class='card ae-done'><b>This is the newest version.</b></div>"
                              f"<div style='margin-top:12px'>{check_btn.format(cls='btn2')}</div>")
            elif not m.get("same_runtime"):
                link = (f"<a class='btn' href='{e(m['run_url'])}' target='_blank' rel='noopener'>Open the page with the installer</a>"
                        if m.get("run_url") else "")
                body_state = (f"<div class='card'><h2 style='margin-top:0'><span>A newer version is ready:</span> <span translate='no'>"
                              f"{e(up.build_label(m['pkg']))}</span></h2><div>This time it needs the full installer: Python or its libraries "
                              f"changed. Download its Setup and install it (projects stay the same).</div>"
                              f"<div style='margin-top:12px'>{link}</div></div>")
            else:
                try:
                    seen = str(ae.WHATS_NEW_ID)
                except Exception:
                    seen = ""
                items = [n for n in (m.get("notes") or []) if str(n.get("since") or "") > seen][-15:]
                notes = "".join(f"<li translate='no'>{e((n.get('ru') if ru else '') or n.get('en') or '')}</li>" for n in items)
                notes_html = f"<div style='margin-top:10px'><b>What is new</b><ul style='margin:6px 0 0'>{notes}</ul></div>" if notes else ""
                body_state = (f"<div class='card'><h2 style='margin-top:0'><span>A newer version is ready:</span> <span translate='no'>"
                              f"{e(up.build_label(m['pkg']))}</span></h2>{notes_html}"
                              f"<div class='muted' style='margin-top:10px'><span>Download:</span> {human_bytes(int(m.get('size') or 0))}. "
                              f"<span>It goes into a new folder next to this one; this version stays on the PC (to go back: Check this PC). "
                              f"Projects stay the same. MediaEngine restarts by itself.</span></div>"
                              f"<form method='post' action='/auto/update/apply' style='margin-top:12px' "
                              f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(x=>x.disabled=true),0)\">"
                              f"<button class='ae-big'>Update now</button></form></div>")
        else:
            body_state = (f"<div class='card'><div>MediaEngine looks for a newer version on GitHub only when you press this button; "
                          f"it goes online for nothing else.</div><div style='margin-top:12px'>{check_btn.format(cls='')}</div></div>"
                          if not up.auto_on() else
                          f"<div class='card'><div>Press the button to look for a newer version right now.</div>"
                          f"<div style='margin-top:12px'>{check_btn.format(cls='')}</div></div>")
        if why and st not in ("downloading", "preparing", "switching"):
            body_state = f"<div class='card'><div class='errbox'>{e(why)}</div></div>"
        auto_card = ""
        if not why:
            if up.auto_on():
                said = _AUTO_RESULT.get(up.AUTO.get("result") or "", "")
                last = (f"<div class='muted' style='margin-top:6px'><span>Last automatic check:</span> "
                        f"<span translate='no'>{e(time.strftime('%H:%M', time.localtime(up.AUTO['last'])))}</span> "
                        f"<span>{e(said)}</span></div>") if up.AUTO.get("last") and said else ""
                auto_card = (f"<div class='card' style='margin-top:14px'><b>Automatic updates are on.</b>"
                             f"<div style='margin-top:6px'>Every 30 minutes MediaEngine looks for a newer version on GitHub and installs "
                             f"it by itself when nothing is being made. No window opens; open pages follow the new version.</div>{last}"
                             f"<form method='post' action='/auto/update/auto' style='margin-top:10px'><input type='hidden' name='on' value='0'>"
                             f"<button class='btn2'>Turn automatic updates off</button></form></div>")
            else:
                auto_card = (f"<div class='card' style='margin-top:14px'><b>Automatic updates are off.</b>"
                             f"<form method='post' action='/auto/update/auto' style='margin-top:10px'><input type='hidden' name='on' value='1'>"
                             f"<button class='btn2'>Turn automatic updates on</button></form></div>")
        body = (f"<div class='pagehead'><div class='eyebrow'>MediaEngine</div><h1>Updates</h1>"
                f"<div class='lead'><span>This version:</span> <b translate='no'>{e(here)}</b></div></div>{body_state}{auto_card}"
                f"<div class='row' style='margin-top:14px'><a class='btn btn2' href='/auto'>Back</a></div>")
        script = ""
        if st in ("downloading", "preparing", "switching"):
            steps = json.dumps({k: v for k, v in _UPDATE_STEP.items()})
            script = ("const ST=" + steps + ";let want='';let n=0;let down=false;"
                      "async function t(){n++;"
                      "if(want){try{const r=await fetch('/api/ping',{cache:'no-store'});const x=await r.json();"
                      "const got=String(x.install||'').replace(/\\//g,'\\\\').toLowerCase();"
                      "if(got===want){location.href='/auto';return}"
                      # the old build answers again after it was gone: the new one did not start (its launcher started the old one)
                      "if(down){document.getElementById('upBack').hidden=false;document.getElementById('upSlow').hidden=true;return}"
                      "}catch(e){down=true}}"
                      "try{const r=await fetch('/api/update-status',{cache:'no-store'});const s=await r.json();"
                      "if(s.target)want=String(s.target).replace(/\\//g,'\\\\').toLowerCase();"
                      "if(s.state==='error'||s.state==='ready'||(s.state!=='downloading'&&s.state!=='preparing'&&s.state!=='switching'&&!want)){location.reload();return}"
                      "document.getElementById('upBar').style.width=(s.state==='downloading'?s.percent:100)+'%';"
                      "const el=document.getElementById('upStep');const tx=ST[s.state]||'';el.textContent=window.ME_L?ME_L(tx):tx}catch(e){}"
                      "if(n>240)document.getElementById('upSlow').hidden=false;setTimeout(t,1000)}setTimeout(t,800);")
        return page("Updates", body, script)

    @app.post("/auto/update/check")
    def ae_update_check():
        from . import updater as up
        try:
            up.check()
        except up.UpdateError as exc:
            up.check_failed(exc)
        return redirect("/auto/update")

    @app.post("/auto/update/auto")
    def ae_update_auto():
        from . import updater as up
        up.set_auto(request.form.get("on") == "1")
        return redirect("/auto/update")

    @app.post("/auto/update/apply")
    def ae_update_apply():
        from . import updater as up
        try:
            up.start_apply()
        except up.UpdateError as exc:
            return err_page(str(exc), "/auto/update")
        return redirect("/auto/update")

    @app.get("/api/update-status")
    def ae_update_status():
        from . import updater as up
        s = up.status()
        return jsonify({k: s.get(k) for k in ("state", "percent", "target", "error")})

    @app.post("/auto/check/remove-old-builds")
    def ae_remove_old_builds():
        n, freed = ae.remove_old_builds(2)
        return redirect("/auto/check?removed=" + urllib.parse.quote(f"{n} × MediaEngine ({human_bytes(freed)})"))

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
        path = _json_obj().get("path") or ae.pick_folder("Choose the folder that contains the FAST_LOCAL model",
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
        path = _json_obj().get("path") or ae.pick_folder("Choose the folder with the AI+ model files")
        if not path:
            return jsonify({"ok": False, "error": "No folder chosen."})
        try:
            res = ae.aiplus_import(path)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)})
        return jsonify({"ok": True, **res})

    @app.post("/api/auto/model/download")
    def ae_model_download():
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return jsonify({"ok": False, "error": "Only from MediaEngine itself."}), 400
        return jsonify({"ok": True, "started": ae.model_download_start()})

    @app.get("/api/auto/model")
    def ae_model_state():
        dl = dict(ae._MODEL_DL)
        return jsonify({"ready": ae.model_status()["ready"], **dl})

    @app.post("/api/auto/aiplus/download")
    def ae_aiplus_download():
        if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return jsonify({"ok": False, "error": "Only from MediaEngine itself."}), 400
        if _json_obj().get("cancel"):
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

    @app.post("/api/auto/pick-music")
    def ae_pick_music():
        files = ae.pick_files("Choose music for the reel", initial=ae.music_folder(), kind="audio")
        if files:
            ae.remember_music(files[0])        # the next music window opens there
            return jsonify({"path": files[0]})
        return jsonify({"path": None, "error": "No music chosen. You can also paste the path."})

    @app.post("/api/auto/pick-folder")
    def ae_pick_folder():
        purpose = _json_obj().get("purpose")
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
        site = request.headers.get("Sec-Fetch-Site", "")
        if site not in ("same-origin", "none", ""):
            return err_page("This page can only be opened from MediaEngine itself.")
        folder = request.args.get("folder", "")
        chosen = request.args.getlist("file")
        # a link from outside the app (e-mail, chat, a document) must not make this PC open a network share
        # (Windows would send its sign-in to that server): network paths only from MediaEngine's own pages
        if site != "same-origin" and any(str(x).strip().strip('"').replace("/", "\\").startswith("\\\\") for x in [folder, *chosen]):
            return err_page("Network folders can only be opened from MediaEngine itself: paste the path on the Auto Edit page.")
        lib_theme = request.args.get("library_theme", "")
        if lib_theme:            # "Make a reel about this theme" in the Library: its matching videos, AI+ and the theme
            from . import aiplus_library as al
            if lib_theme not in ae.THEMES or not ae.aiplus_status()["ready"]:
                return err_page("The AI+ model is not on this computer yet. Download it once on 'Check this PC'.")
            chosen = al.reel_files(lib_theme, ae.MAX_INPUTS)
            if not chosen:
                return err_page("No video of this theme is on this PC now.")
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
        last_new = ae.last_new_settings()      # the next reel starts like the last one
        fmt0, snd0 = last_new.get("format", "social_hd"), last_new.get("sound", "auto")
        formats = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if k == fmt0 else ''}> {e(v['label'])}</label>"
                          for k, v in ae.FORMATS.items())
        sounds = "".join(f"<label><input type='radio' name='sound' value='{k}' {'checked' if k == snd0 else ''}> {e(v)}</label>"
                         for k, v in ae.SOUNDS.items())
        plus_ready = ae.aiplus_status()["ready"]
        # from the Library's "Find by theme": AI+ and that theme are already chosen
        want_mode = request.args.get("mode") if request.args.get("mode") in ae.MODES else last_new.get("mode")
        want_theme = request.args.get("theme") or lib_theme
        want_theme = want_theme if plus_ready and want_theme in ae.THEMES else ""
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
        if not scan["files_chosen"]:     # a folder that has its project already: another version there keeps it in one place
            try:
                here_ = os.path.normcase(os.path.abspath(str(scan["folder"])))
                same_ = [p_ for p_ in ae.list_projects() if not p_.get("files") and p_.get("folder")
                         and os.path.normcase(os.path.abspath(str(p_["folder"]))) == here_]
            except Exception:
                same_ = []
            if same_:
                p0_ = same_[0]                 # (the list: the most recently changed first)
                when0_ = _when_label((p0_["revisions"][-1].get("created_at") if p0_["revisions"] else None) or p0_.get("created_at"))
                warn += (f"<div class='callout card' style='margin-top:10px'><span>This folder already has a project:</span> "
                         f"<a href='/auto/p/{int(p0_['id'])}'><b translate='no'>{e(p0_['title'])}</b></a>"
                         + (f" <span class='muted' translate='no'>({e(when0_)})</span>" if when0_ else "")
                         + (f" <span class='muted'><span>and more:</span> {len(same_) - 1}</span>" if len(same_) > 1 else "")
                         + ". <span>Open it to make another length or format as a new version there - everything stays in one "
                           "place (the videos are not analysed again either way).</span></div>")
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
        # analyse the videos now (for example overnight), make the reel later in minutes
        prepare_btn = "<button class='btn2 ae-big' name='prepare' value='1'>Prepare in advance</button>"
        prepare_note = ("<div class='muted' style='margin-top:6px'>Prepare in advance: MediaEngine only analyses the videos now - for example "
                        "overnight. The reel is then made from them in minutes.</div>")
        picked = [Path(x) for x in (scan["files_chosen"] or [])]
        pdays = {ae.video_day(x, 0) for x in picked} if picked and all(ae._DAY_IN_NAME.search(x.stem) for x in picked) else set()
        day_suffix = (" · " + _day_label(next(iter(pdays)))) if len(pdays) == 1 else ""      # "Телефон · 2 августа 2026"
        body = f"""<div class='pagehead'><div class='eyebrow'>Auto Edit · new reel</div><h1 translate='no'>{e(Path(scan['folder']).name or scan['folder'])}{e(day_suffix)}</h1>
<div class='lead'>{where_html}</div></div>
<div class='card'><b>{scan['usable']} usable video(s)</b>, total {_fmt_s(total)} · {human_bytes(scan['total_bytes'])}{(' · ' + str(scan['skipped']) + ' skipped') if scan['skipped'] else ''}
<details style='margin-top:8px'><summary class='muted'>Show files</summary><table class='ae-files'><tr><th>File</th><th>Size</th><th>Length</th><th>Frame</th><th></th></tr>{rows}</table></details>{inside}{warn}</div>
<form method='post' action='/auto/create' class='card' style='margin-top:14px' onsubmit="setTimeout(()=>this.querySelectorAll('button:not([type=button])').forEach(b=>b.disabled=true),0)">
{src_hidden}
<h2 style='margin-top:0'>Length</h2><div class='ae-choices'>{lengths}</div>
<h2>Format</h2><div class='ae-choices'>{formats}</div>{_framing_choice(e, last_new.get("framing", "fill"))}
<h2>Sound</h2><div class='ae-choices'>{sounds}</div>
<h2>Colours</h2>{_look_choice(e, last_new.get("look"), pic_src=_look_video(scan))}{mode_html}
{_dress_fields(e, None, _day_label(next(iter(pdays))) if len(pdays) == 1 else "")}
<div class='row' style='flex-wrap:wrap;gap:10px;align-items:center'><button class='ae-big'>Create reel</button>{prepare_btn}</div>{prepare_note}</form>{back_html}"""
        return page("New reel", body, _FRAMING_JS)

    @app.post("/auto/create-days")
    def ae_create_days():
        f = request.form
        try:
            if not f.get("mode"):
                raise ValueError("Without the AI model, tick 'Build with Technical only' to continue.")
            folder = Path(str(f.get("folder") or "").strip().strip('"'))
            if not folder.is_absolute() or not ae.folder_available(folder):
                raise ValueError("The folder is not available: " + str(folder))
            ae._guard_private(folder)
            settings = {"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound") or "auto",
                        "mode": f.get("mode"), "framing": f.get("framing"), "theme": "", "look": f.get("look") or "natural",
                        **({"prepare": True} if f.get("prepare") == "1" else {})}
            ae.normalize_settings(settings, model_ready=ae.model_status()["ready"])
            ae.check_free_space()
            days = []
            for d in ae.videos_by_day(folder):     # OneDrive files kept only in the cloud are never read
                files = [x["path"] for x in d["files"] if not ae.cloud_only(Path(x["path"]))]
                if 1 <= len(files) <= ae.MAX_INPUTS and len(d["files"]) <= ae.MAX_INPUTS:
                    days.append({**d, "paths": files})
            if not days:
                raise ValueError("No day with videos to use.")
            if len(days) > MAX_DAYS:
                raise ValueError("More than 31 days: choose the days one by one.")
            for d in days:                  # every day checked before anything is made (no half-made set of projects)
                ae.check_files(d["paths"])
            for d in reversed(days):        # the oldest day first: the list then reads newest on top
                # a day prepared before (or a second press) continues its own project: its prepared pieces are used
                pid = ae.project_with_files(d["paths"]) or ae.create_project(str(folder), f"{folder.name} · {_day_label(d['day'])}",
                                                                              files=d["paths"])
                ae.start_job(pid, settings)
            ae.remember_new_settings(settings)
        except Exception as exc:
            return err_page(str(exc))
        return redirect("/auto")

    @app.post("/auto/create")
    def ae_create():
        f = request.form
        try:
            if not f.get("mode"):
                raise ValueError("Without the AI model, tick 'Build with Technical only' to continue.")
            dress = _dress_from_form(f)
            ae.normalize_settings({"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode"),
                                   "framing": f.get("framing"), **dress}, model_ready=ae.model_status()["ready"])
            ae.check_free_space()
            # the same folder / videos prepared in advance before: the reel is made in that project (its pieces are there)
            pid = (ae.prepared_project_for(f.get("folder"), f.getlist("file") or None)
                   or ae.create_project(f.get("folder"), f.get("title"), files=f.getlist("file") or None))
            ae.start_job(pid, {"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode"),
                               "theme": f.get("theme") or "", "framing": f.get("framing"), **dress,
                               **({"prepare": True} if f.get("prepare") == "1" else {})})
            ae.remember_new_settings({"format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode"), "framing": f.get("framing"),
                                      "look": f.get("look")})
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
<form method='post' action='/auto/p/{pid}/open-folder'><button class='btn2' title='Open the folder of the videos in Explorer'>Videos folder</button></form>
<form method='post' action='/auto/p/{pid}/rename' class='row' style='gap:6px'><input name='title' value='{e(p['title'])}' maxlength='80' style='width:200px'><button class='btn2'>Rename</button></form>
{"" if active and not p['archived'] else f"<form method='post' action='/auto/p/{pid}/archive'><button class='btn2'>{'Unarchive' if p['archived'] else 'Archive'}</button></form>"}</div></div>"""]
        if request.args.get("same") and cur:
            parts.append(f"<div class='card callout' style='margin-bottom:12px'>This version already exists: R{int(cur['number']):03d} "
                         f"(the same settings and moments). Change the length, format or sound, or tick “remove” on a moment.</div>")
        if not p["source_present"]:
            parts.append("<div class='errbox'><span>The source videos are not available: the drive is disconnected, or the folder was "
                         "moved, renamed or deleted. Versions and saved MP4 files are kept; new builds are possible when the videos are "
                         "back in their place:</span> <span class='ae-path'>" + e(p.get("folder") or "; ".join(map(str, (p.get("missing_files") or [])[:3]))) + "</span></div>")
        elif p.get("missing_files"):
            gone = p["missing_files"]
            parts.append("<div class='callout card' style='margin-bottom:12px'><span>Some videos of this reel are not there any more (moved or deleted): "
                         f"{len(gone)} of {len(p['files'])}.</span> <span class='muted' translate='no'>"
                         + e(", ".join(Path(x).name for x in gone[:8]) + (" …" if len(gone) > 8 else "")) + "</span> "
                         "<span>New versions are made from the others.</span></div>")
        if active and active["settings"].get("prepare"):
            parts.append(_preparing_html(active, pid, e))
        elif active:
            parts.append(f"""<div class='card' id='jobCard' data-job='{active['id']}'><div class='row space'><b id='jobStage'>{e(ae.STAGE_LABEL.get(active['stage'] or 'queued', ''))}</b>
<form method='post' action='/auto/job/{active['id']}/cancel'><button class='btn2'>Cancel</button></form></div>
<div class='ae-bar' style='margin:10px 0'><i id='jobBar' style='width:{active['percent']}%'></i></div>
<div class='muted' id='jobMsg'>{e(active.get('message') or '')}</div>
<div class='muted'>{e(ae.FORMATS[active['settings']['format']]['label'])} · {active['settings']['length']} s · sound {e(active['settings']['sound'])}</div>
{"<div style='margin-top:6px'>A new version with your edits.</div>" if active['settings'].get('selection') else ""}{_waiting_html(active, pid, e)}
<div class='muted' style='margin-top:6px'>{'You can close this window: the reel keeps building and the PC does not go to sleep. When it is ready, Windows shows a notification - click it to see the reel.' if _notify_on() else 'You can close this window: the reel keeps building and the PC does not go to sleep. Open MediaEngine again to see it.'}</div></div>""")
        if active:
            for q in queued:
                what = (f"<span>Prepare in advance</span> · {_mode_name(q['settings'], e)}" if q["settings"].get("prepare") else
                        f"{e(ae.FORMATS[q['settings']['format']]['short'])} · {q['settings']['length']} s · sound {e(q['settings']['sound'])}")
                parts.append(f"<div class='card row space' style='margin-top:8px'><span class='muted'><span>Waiting:</span> {what}</span>"
                             f"<form method='post' action='/auto/job/{q['id']}/cancel'><button class='btn2'>Cancel</button></form></div>")
        elif last_job and last_job["status"] in ("failed", "cancelled") and (not revs or last_job["id"] > max(r["job_id"] for r in revs)):
            ls_ = last_job["settings"]
            no_ai = ""
            was_prep = bool(ls_.get("prepare"))
            interrupted = str(last_job.get("error") or "").startswith("Interrupted")
            if last_job["status"] == "failed" and ls_.get("mode") in ae.AI_MODES and not was_prep and not interrupted:
                # an AI-mode failure must not leave the user stuck: offer the clearly labelled technical build
                no_ai = (f"<form method='post' action='/auto/p/{pid}/variant'>"
                         f"<input type='hidden' name='length' value='{ls_['length']}'><input type='hidden' name='format' value='{e(ls_['format'])}'>"
                         f"<input type='hidden' name='sound' value='{e(ls_['sound'])}'><input type='hidden' name='mode' value='technical'>"
                         + "".join(f"<input type='hidden' name='{fld}' value='{e(ls_.get(key) or '')}'>" for fld, key in
                                   (("reel_title", "title"), ("reel_subtitle", "subtitle"), ("music", "music"), ("music_mode", "music_mode"),
                                    ("framing", "framing"), ("look", "look")))
                         + "<input type='hidden' name='beat_sync_shown' value='1'>"
                         + ("<input type='hidden' name='beat_sync' value='1'>" if ls_.get("beat_sync") is not False else "")
                         + "<button class='btn2'>Build without AI (Technical only)</button></form>")
            head_ = (("Preparing failed" if last_job["status"] == "failed" else "Preparing cancelled") if was_prep else
                     ("Build failed" if last_job["status"] == "failed" else "Build cancelled"))
            why_ = last_job.get('error') or last_job.get('message') or ''
            if last_job["status"] == "cancelled" and why_ == "Cancelled by user":      # (the words of what was cancelled)
                why_ = "You cancelled the preparing." if was_prep else "You cancelled the build."
            parts.append(f"""<div class='card'><b>{head_}</b>
<div class='{'errbox' if last_job['status']=='failed' else 'muted'}' style='margin:8px 0'>{_error_html(why_, e)}</div>
<div class='row' style='flex-wrap:wrap'><form method='post' action='/auto/job/{last_job['id']}/retry'><button>Retry</button></form>{no_ai}</div></div>""")
        done_x = ae.export_row(request.args.get("exported", type=int) or 0)
        if done_x and int(done_x["project_id"]) == int(pid):
            parts.append(f"""<div class='card ae-done'><div class='eyebrow'>Done</div><h2 style='margin:4px 0'>Your reel is saved</h2>
<div class='ae-path'>{e(done_x['path'])}</div><div class='muted'>{human_bytes(done_x['bytes'])} · checked: an exact copy of the version</div>
<div class='row' style='margin-top:10px;flex-wrap:wrap'><form method='post' action='/auto/export/{done_x['id']}/open'><button class='ae-big'>Open video</button></form>
<form method='post' action='/auto/export/{done_x['id']}/reveal'><button class='btn2'>Show in folder</button></form>
<button type='button' class='btn2' id='copyDone' data-path='{e(done_x['path'])}'>Copy path</button>
{_text_link(done_x['path'], e)}<a class='btn btn2' href='/auto'>All projects</a></div></div>""")
        prep_job = ae.prepared_job(p) if not active else None
        if prep_job:
            parts.append(_prepared_html(prep_job, e))
        if cur:
            parts.append(_review_html(p, cur, e, building=bool(active)))
        elif not active:
            parts.append(_variant_form(pid, None, e, first=True, model_ready=ae.model_status()["ready"],
                                       prefill=last_job["settings"] if last_job else None))
        parts.append(_revisions_html(p, cur, e))
        parts.append(_reviews_html(p, e))
        du = ae.project_disk_usage(pid)
        if du["cache_bytes"] or du["versions_bytes"]:
            parts.append(f"<div class='card row space' style='margin-top:14px;flex-wrap:wrap'><span class='muted'>Space used: versions "
                         f"{human_bytes(du['versions_bytes'])} · analysis cache {human_bytes(du['cache_bytes'])}"
                         f"{' (can be freed; the next build makes it again - what the AI found in the videos is kept for every project)' if du['cache_bytes'] else ''}</span>"
                         + (f"<form method='post' action='/auto/p/{pid}/free-cache'><button class='btn2'>Free cache</button></form>" if du["cache_bytes"] and not active else "")
                         + "</div>")
        script = """
const card=document.getElementById('jobCard');
async function pollJob2(){if(!card)return;try{const r=await fetch('/api/auto/job/'+card.dataset.job,{cache:'no-store'});const j=await r.json();
 document.getElementById('jobBar').style.width=j.percent+'%';document.getElementById('jobStage').textContent=j.stage_label+' · '+j.percent+'%';
 if(!window.ME_T0)window.ME_T0=document.title;document.title=j.percent+'% · '+window.ME_T0;   // progress visible on the tab
 const counted=j.total>1&&(j.stage==='render'||j.done>0);const el=Math.round(j.elapsed_s||0);
 // estimate only from the real rate of the current stage, once there is enough of it (no invented timer)
 let eta='';if(j.status==='running'&&j.stage==='finish')eta=' · final encode and check of the whole reel, can take a few minutes';
 else if(j.status==='running'&&j.eta_s!=null){const an=j.stage==='analyze';
  eta=(an?' · finding moments: ':' · ')+(j.eta_s<60?'less than a minute left':'about '+Math.max(1,Math.round(j.eta_s/60))+' min left')+(an&&!card.dataset.prepare?', then cutting and joining':'')}
 document.getElementById('jobMsg').textContent=(counted?(Math.min(j.done+1,j.total)+' of '+j.total+' · '):'')+(j.message||'')+' · '+Math.floor(el/60)+':'+String(el%60).padStart(2,'0')+' elapsed'+eta;
 if(j.status==='done'&&j.revision_id){location.href=location.pathname+'?rev='+j.revision_id;return}   // the new version, not the old accepted one
 if(['done','failed','cancelled'].includes(j.status)){location.reload();return}}catch(e){}setTimeout(pollJob2,1000)}
pollJob2();
const ef=document.getElementById('editForm');
function secs(x){x=String(x||'').trim().replace(',','.');if(!x)return null;const m=/^(?:(\\d+):)?(\\d+):(\\d{1,2}(?:\\.\\d+)?)$/.exec(x);
 if(m)return ((+m[3])>=60||(m[1]!==undefined&&(+m[2])>=60))?null:(+(m[1]||0))*3600+(+m[2])*60+(+m[3]);return /^\\d+(\\.\\d+)?$/.test(x)?+x:null}
if(ef)ef.addEventListener('submit',ev=>{if(ev.submitter&&ev.submitter.name==='rechoose')return;const errs=[];
 ef.querySelectorAll('.ae-edit').forEach(row=>{const a=row.querySelector('input[name^="in_"]'),b=row.querySelector('input[name^="out_"]'),rm=row.querySelector('input[name="remove"]');
  if(!a||!b||(rm&&rm.checked))return;const n=(row.querySelector('.pos')||{}).textContent||'?',x=secs(a.value),y=secs(b.value);
  const d=parseFloat(row.dataset.dur||'0'),m='Moment '+n+': ';
  if(x===null||y===null)errs.push(m+'write the time as seconds (12.5), minutes (1:05) or hours (1:05:03)');
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
        return page(p["title"], "".join(parts), script + "\n" + _FRAMING_JS)

    @app.get("/api/auto/job/<int:jid>")
    def ae_job_api(jid):
        j = ae.job(jid)
        if not j:
            return jsonify({"error": "not found"}), 404
        out = {k: j[k] for k in ("id", "status", "stage", "stage_label", "done", "total", "message", "percent", "error", "revision_id")}
        out["elapsed_s"] = ae.job_elapsed_s(j)
        out["eta_s"] = stage_eta_s(j)
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
                        "framing": f.get("framing") if "framing" in f else bs.get("framing"),
                        "theme": f.get("theme") if "theme" in f else (bs.get("theme") or ""), **_dress_from_form(f, bs)}
            if f.get("rechoose"):
                # "Let MediaEngine choose again": automatic selection without the removed moments
                settings["exclude"] = sorted(set(bs.get("exclude", [])) | set(f.getlist("remove")))
            else:
                # A format/sound variant keeps the base revision's choices (exclusions, manual edits). A new LENGTH
                # needs other moments: they are chosen again (removed ones stay out) - a hand-made selection would
                # silently keep the old length.
                same_len = not bs or str(settings["length"]) == str(bs.get("length"))
                # (a theme counts with AI+ only - as the build reads it: a theme left in the form of another mode
                # must not throw away the hand-made choices)
                theme_of = lambda x: (x.get("theme") or "") if x.get("mode") == "semantic_plus" else ""
                same_mode = not bs or (settings["mode"] == (bs.get("mode") or "semantic")  # AI, AI+ and each theme
                                       and theme_of(settings) == theme_of(bs))              # have their own moments
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
        # while the new version builds, the page keeps showing the version it was made from (not the accepted one)
        return redirect(f"/auto/p/{pid}?rev={int(base['id'])}" if base else f"/auto/p/{pid}")

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
            bset = base["settings"] if base and int(base["project_id"]) == int(pid) else {}
            # what the user took out (removed or replaced) stays out of later automatic choices (another length,
            # "Let MediaEngine choose again")
            gone = {x for x in f.getlist("row") if x in removed or f.get(f"replace_{x}")}
            exclude = sorted((set(bset.get("exclude") or []) | gone) - set(selection))
            settings = {"length": f.get("length"), "format": f.get("format"), "sound": f.get("sound"), "mode": f.get("mode"),
                        "selection": selection, "trims": trims, "framing": bset.get("framing"), "exclude": exclude,
                        # an edit keeps the version's theme, music and title (the moments come from its pool)
                        "theme": f.get("theme") if "theme" in f else (bset.get("theme") or ""), **_dress_from_form(f, bset)}
            base_seq = [str(sg.get("event_id")) for sg in ((base or {}).get("result") or {}).get("segments") or []]
            ns = ae.normalize_settings(settings, model_ready=ae.model_status()["ready"])
            rest = lambda d: {k: v for k, v in d.items() if k not in ("selection", "trims", "exclude")}
            if (bset and selection == base_seq and not add and not gone and not ae.private_in_result(base.get("result") or {})
                    and (ns.get("trims") or {}) == {k: v for k, v in (bset.get("trims") or {}).items() if k in selection}
                    and rest(ns) == rest(bset)):
                return redirect(f"/auto/p/{pid}?rev={int(base['id'])}&same=1")      # nothing was changed: no new version
            before = {j["id"] for j in ae.project(pid)["jobs"]}
            jid = ae.start_job(pid, settings)
            j = ae.job(jid)
            if jid in before and j and j["status"] == "done" and j.get("revision_id"):
                return redirect(f"/auto/p/{pid}?rev={int(j['revision_id'])}&same=1")      # nothing was changed
        except ValueError as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        except Exception as exc:
            return err_page("Could not apply the edits: " + str(exc), f"/auto/p/{pid}")
        ok_base = base and int(base["project_id"]) == int(pid)
        return redirect(f"/auto/p/{pid}?rev={int(base['id'])}" if ok_base else f"/auto/p/{pid}")

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
            raw = str(request.form.get("from_revision") or "")
            was = (ae.project(pid) or {}).get("accepted_revision_id")
            # the version the button was shown for: a second click (or an old page) does not go back once more
            prev = ae.revert(pid, expect=int(raw) if raw.isascii() and raw.isdigit() else None)
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        show = prev or was                          # "Undo accept": stay on the version just un-accepted
        return redirect(f"/auto/p/{pid}?rev={int(show)}" if show else f"/auto/p/{pid}")

    @app.post("/auto/p/<int:pid>/export")
    def ae_export(pid):
        try:
            dest = (request.form.get("dest") or "").strip()
            rid = request.form.get("revision_id") or ""
            if rid.isascii() and rid.isdigit():
                pr = ae.project(pid)
                if pr and dest:
                    ae.check_export_dir(pr, dest)    # a refused folder must not change the chosen version
                rv_ = ae.revision(int(rid))
                if pr and rv_ and int(rv_["project_id"]) == int(pid):
                    ae._refuse_private(rv_)          # nor a version with a video marked Private since
                if pr and pr["accepted_revision_id"] != int(rid):
                    ae.accept(pid, int(rid))         # "Save MP4" on a version that was not chosen yet: choose it
            res = ae.export_accepted(pid, dest or None, remember=bool(dest))
        except Exception as exc:
            return err_page(str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}?exported={res['export_id']}")

    @app.post("/auto/p/<int:pid>/small")
    def ae_small(pid):
        try:
            rid = int(request.form.get("revision_id") or 0)
            dst = ae.small_copy(pid, rid)
        except Exception as exc:
            return err_page(ae.friendly_error(str(exc)) if "SMALL_COPY_FAILED" in str(exc) else str(exc), f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}?rev={rid}&small=" + urllib.parse.quote(dst.name))

    @app.post("/auto/p/<int:pid>/open-folder")
    def ae_open_folder(pid):
        p = ae.project(pid)
        if not p:
            return err_page("Project not found")
        if not ae.open_path(Path(p["folder"])):
            return err_page("The source videos are not available (disconnected drive?)", f"/auto/p/{pid}")
        return redirect(f"/auto/p/{pid}")

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

    @app.post("/auto/p/<int:pid>/delete")
    def ae_delete(pid):
        try:
            freed = ae.delete_project(pid)
        except Exception as exc:
            return err_page(str(exc), "/auto?archived=1")
        return redirect("/auto?archived=1&deleted=" + str(int(freed)))

    @app.post("/auto/p/<int:pid>/archive")
    def ae_archive(pid):
        p = ae.project(pid)
        if p and not p["archived"] and any(j["status"] in ("queued", "running") for j in p["jobs"]):
            return err_page("Wait until the current build has finished, then archive the project.", f"/auto/p/{pid}")
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
                return f"R{int(r['number']):03d} ({e(f)} · {secs:.1f} s · {'edited by you' if r['settings'].get('selection') else 'automatic'})"
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
            bottom = (f"<form method='post' action='/auto/review/{rid}/decide' class='card' style='margin-top:14px' "
                      f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\">"
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

    @app.get("/auto/new/look/<look>.jpg")
    def ae_new_look(look):
        # a picture of one of the user's videos: only for this app's own page (an <img> there), never a network path
        src = str(request.args.get("src", "")).strip().strip('"')
        if request.headers.get("Sec-Fetch-Site", "") != "same-origin" or src.replace("/", "\\").startswith("\\\\"):
            return "not found", 404
        try:
            t = ae.look_preview_of_video(src, look)
        except Exception:
            t = None
        if not t:
            return "not found", 404
        return send_file(t, mimetype="image/jpeg", max_age=3600)

    @app.get("/auto/rev/<int:rid>/look/<look>.jpg")
    def ae_rev_look(rid, look):
        try:
            t = ae.look_preview(rid, look)
        except Exception:
            t = None
        if not t:
            return "not found", 404
        return send_file(t, mimetype="image/jpeg", max_age=86400)

    @app.get("/auto/p/<int:pid>/source")
    def ae_source(pid):
        src = ae.source_file(pid, request.args.get("name", ""))
        if not src:
            return "not found", 404
        return send_file(src, conditional=True)

    from . import orders_web       # orders from other programs
    orders_web.register(app, page, err_page, e, _error_html)
    from . import voice_web        # voice-over and captions (an add-on installed with a button)
    voice_web.register(app, page, err_page, e, human_bytes)
    from . import clips_web        # clips from a long video (clipping)
    clips_web.register(app, page, err_page, e, human_bytes)
    from . import cartoon_web      # cartoon films made by the program (cartoon/)
    cartoon_web.register(app, page, err_page, e, human_bytes)
    from . import download_web     # videos downloaded by a link (yt-dlp, installed with a button)
    download_web.register(app, page, err_page, e, human_bytes)
    from . import inbox_web        # the Inbox (links and topics from the phone's bot, other programs, typed) and the phone
    inbox_web.register(app, page, err_page, e, human_bytes)
    from . import handedit_web     # Edit by hand: pieces of any videos on a time line, one MP4
    handedit_web.register(app, page, err_page, e, human_bytes)


AI_LABEL = "AI — as before (fast)"
AIPLUS_LABEL = "AI+ — stronger model, first analysis slower"
AIPLUS_HINT = ("AI+ (a stronger model, PE-Core L/14) can be added once on <a href='/auto/check#aiplus'>Check this PC</a> "
               "(about 650 MB, free).")


def _model_card(ms, e, back="/auto/check"):
    """The AI model (FAST_LOCAL): kept in MediaEngine's own data folder, downloaded once with a button (30 MB)."""
    if ms["ready"]:
        return ("<div class='card' id='aimodel' style='margin-top:14px'><b>AI model is installed</b>"
                f"<div class='muted ae-path' style='margin-top:4px'>{e(str(Path(ms['path']).parent))}</div></div>")
    dl = dict(ae._MODEL_DL)
    running = dl["state"] == "running"
    return ("<div class='card callout' id='aimodel' style='margin-top:14px'><b>The AI model is not downloaded yet</b>"
            "<div class='muted'>Without it reels use the clearly labelled <i>Technical only</i> selection (sharpness, motion, light). "
            "Download once: 30 MB from huggingface.co (free); it is kept in MediaEngine's own folder and every file is checked.</div>"
            "<div class='row' style='margin-top:10px'>"
            f"<button type='button' id='mdDl' {'disabled' if running else ''}>Download the AI model</button>"
            "<button type='button' class='btn2' id='mdImport'>Copy from a folder…</button><span class='muted' id='mdMsg'></span></div>"
            "<div class='progress' style='margin-top:8px'><i id='mdBar' style='width:0%'></i></div>"
            + (f"<div class='errbox' style='margin-top:8px'>{e(dl['error'])}</div>" if _recent_failure(dl) else "")
            + "</div>"
            "<script>(function(){const m=document.getElementById('mdMsg'),b=document.getElementById('mdBar'),d=document.getElementById('mdDl');"
            "async function poll(){try{const r=await fetch('/api/auto/model',{cache:'no-store'});const x=await r.json();"
            f"if(x.ready){{location.href='{back}?model='+Date.now();return}}const p=x.total?Math.floor(100*x.done/x.total):0;b.style.width=p+'%';"
            "if(x.state==='running'){m.textContent=p+' %';d.disabled=true;setTimeout(poll,700)}"
            "else{d.disabled=false;if(x.state==='failed')m.textContent=x.error||'Failed';}}catch(e){setTimeout(poll,2000)}}"
            "d.onclick=async()=>{d.disabled=true;m.textContent='Starting…';await fetch('/api/auto/model/download',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});poll()};"
            "document.getElementById('mdImport').onclick=async()=>{m.textContent='A Windows folder window is open — it may be behind this window.';"
            f"const r=await fetch('/api/auto/model/import',{{method:'POST'}});const x=await r.json();m.textContent=x.ok?'Installed.':(x.error||'Not installed');if(x.ok)setTimeout(()=>{{location.href='{back}?model='+Date.now()}},800)}};"
            + ("poll();" if running else "") + "})();</script>")


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
            "<div class='muted'>PE-Core L/14 (Meta, Apache-2.0) understands people, what they do and the things around them much better than the "
            "built-in AI model (tested on public photos: it finds the right photo for a description in 86 of 100 cases, the built-in "
            "model in 60); for plain landscapes the difference is small. It works on this PC without internet; the first analysis "
            "of new videos is slower (about 1–2 s per checked frame). "
            f"Download once: {human_bytes(ap['bytes'])}, from huggingface.co (free); every file is checked.</div>"
            "<div class='row' style='margin-top:10px'>"
            f"<button type='button' id='apDl' {'disabled' if running else ''}>{'Continue the download' if ap.get('partial') else 'Download AI+ model'}</button>"
            f"<button type='button' class='btn2' id='apCancel' {'' if running else 'hidden'}>Stop</button>"
            "<button type='button' class='btn2' id='apImport'>Copy from a folder…</button>"
            "<span class='muted' id='apMsg'></span></div>"
            "<div class='progress' style='margin-top:8px'><i id='apBar' style='width:0%'></i></div>"
            + (f"<div class='errbox' style='margin-top:8px'>{e(dl['error'])}</div>" if _recent_failure(dl) else "")
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


def _waiting_html(active, pid, e):
    if active["status"] != "queued":
        return ""
    other = ae.running_elsewhere(pid)
    if not other:
        return ""
    return (f"<div style='margin-top:6px'><span>Reels are made one at a time. This one starts when this reel is ready:</span> "
            f"<a href='/auto/p/{int(other['id'])}' translate='no'>{e(other['title'])}</a></div>")


def _selftest_html(t, e):
    if not t.get("ok"):
        return (f"<div class='card' style='margin-top:14px'><b>Test reel failed</b> · {t.get('seconds', 0)} s"
                f"<div class='errbox' style='margin-top:6px'>{e(t.get('error') or '')}</div></div>")
    sm = str(t.get("selection_mode", ""))
    ai = sm.startswith("FAST_LOCAL") or sm.startswith("PE_CORE")
    st = t.get("stages") or {}
    stage_txt = " · ".join(f"<span>{lbl}</span> {float(st[k]):.1f} s" for k, lbl in
                           (("analyze", "analysis"), ("render", "cutting"), ("finish", "joining")) if k in st)
    return (f"<div class='card ae-done' style='margin-top:14px'><b>Test reel built</b> · "
            f"<span>{'with the AI+ model (PE-Core L/14)' if sm.startswith('PE_CORE') else 'with the AI model (FAST_LOCAL)' if ai else 'Technical only'}</span> · <span>built in</span> {t['seconds']} s"
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


def _text_link(path, e) -> str:
    """From a saved reel to text, captions and a voice-over on it (the Voice-over page with this video filled in)."""
    from urllib.parse import quote
    from . import voice as vo
    if not vo.SHOW_ON_HOME:
        return ""
    return f"<a class='btn btn2' href='/auto/finish?video={e(quote(str(path)))}'>Text, captions, voice-over</a>"


def _dress_fields(e, s=None, date_hint=""):
    """Music and title (optional) on the new-reel page and for a variant: closed unless the reel has them."""
    s = s or {}
    has = bool(s.get("title") or s.get("subtitle") or s.get("music"))
    mode = s.get("music_mode") or "mix"
    date_btn = (f"<button type='button' class='btn2' data-date='{e(date_hint)}' "
                f"onclick=\"this.form.reel_subtitle.value=this.dataset.date\">Insert the date</button>") if date_hint else ""
    return (f"<details class='ae-dress' {'open' if has else ''} style='margin:6px 0 14px'><summary><b>Music and title</b> "
            "<span class='muted'>(optional)</span></summary>"
            "<div style='display:grid;gap:10px;margin-top:10px;max-width:760px'>"
            f"<label>Title at the start<br><input name='reel_title' maxlength='80' value='{e(s.get('title') or '')}' "
            "placeholder='For example: Summer at the sea' style='width:100%'></label>"
            f"<label>Second line<br><span class='row' style='gap:6px'><input name='reel_subtitle' maxlength='80' value='{e(s.get('subtitle') or '')}' "
            f"placeholder='{e(date_hint or 'For example: July 2026')}' style='flex:1'>{date_btn}</span></label>"
            "<label>Music (your own audio file: mp3, m4a, wav, flac, ogg)<br><span class='row' style='gap:6px'>"
            f"<input name='music' class='ae-path' translate='no' value='{e(s.get('music') or '')}' placeholder='C:\\Music\\song.mp3' style='flex:1'>"
            "<button type='button' class='btn2' data-pick-music>Choose music…</button>"
            "<button type='button' class='btn2' onclick=\"this.form.music.value=''\">No music</button></span></label>"
            "<div class='ae-choices'>"
            f"<label><input type='radio' name='music_mode' value='mix' {'checked' if mode != 'music' else ''}> Music and the videos' sound (quieter)</label>"
            f"<label><input type='radio' name='music_mode' value='music' {'checked' if mode == 'music' else ''}> Only music</label></div>"
            f"<label><input type='checkbox' name='beat_sync' value='1' {'checked' if s.get('beat_sync') is not False else ''}> "
            "Cuts on the beat of the music</label> <span class='muted' style='font-size:13px'>(when the music has a clear beat)</span>"
            "<input type='hidden' name='beat_sync_shown' value='1'>"
            "<div class='muted' style='font-size:13px'>The title is shown for the first 3 seconds. The music starts softly and fades out "
            "at the end; a short song is repeated. Changing music or title later makes a new version quickly, without a new analysis.</div>"
            "<span class='muted' data-music-msg></span></div></details>"
            "<script>(function(){const d=document.currentScript.previousElementSibling,b=d.querySelector('[data-pick-music]'),"
            "m=d.querySelector('[data-music-msg]');if(!b)return;b.onclick=async()=>{m.textContent='A Windows window is open — it may be behind this window.';"
            "try{const r=await fetch('/api/auto/pick-music',{method:'POST'});const x=await r.json();"
            "if(x.path){d.querySelector('input[name=music]').value=x.path;m.textContent=''}else m.textContent=x.error||''}"
            "catch(e){m.textContent='Window failed: '+e}}})();</script>")


def _dress_from_form(f, base_settings=None):
    """The form's music / title, or - when the form has no such fields - the base revision's."""
    bs = base_settings or {}
    pick = lambda field, key: (f.get(field) or "") if field in f else (bs.get(key) or "")
    return {"title": pick("reel_title", "title"), "subtitle": pick("reel_subtitle", "subtitle"), "music": pick("music", "music"),
            "music_mode": (f.get("music_mode") if "music_mode" in f else bs.get("music_mode")) or "mix",
            # a checkbox is not sent when it is off: the hidden field says the form had it
            "beat_sync": ("beat_sync" in f) if "beat_sync_shown" in f else bs.get("beat_sync") is not False,
            "look": (f.get("look") if "look" in f else bs.get("look")) or "natural"}


def _variant_form(pid, rev, e, first=False, model_ready=True, prefill=None):
    s = {"length": 15, "format": "social_hd", "sound": "auto"}
    if rev:
        s = rev["settings"]
    elif prefill and int(prefill.get("length") or 0) in ae.LENGTHS:      # a failed / cancelled first build: its own choices
        s = {**s, **{k: prefill[k] for k in ("length", "format", "sound", "mode", "theme", "framing") if prefill.get(k)}}
        if s["format"] not in ae.FORMATS:
            s["format"] = "social_hd"
    lengths = "".join(f"<label><input type='radio' name='length' value='{L}' {'checked' if int(s['length']) == L else ''}> {L} s</label>" for L in ae.LENGTHS)
    formats = "".join(f"<label><input type='radio' name='format' value='{k}' {'checked' if s['format'] == k else ''}> {e(v['short'])}</label>" for k, v in ae.FORMATS.items())
    short_sound = {"auto": "Auto", "source": "Source sound", "mute": "Mute"}     # the same words as on the new-reel page
    sounds = "".join(f"<label><input type='radio' name='sound' value='{k}' {'checked' if s['sound'] == k else ''}> {e(short_sound.get(k, k.title()))}</label>" for k in ae.SOUNDS)
    base = f"<input type='hidden' name='base_revision_id' value='{rev['id']}'>" if rev else ""
    mode = ""
    plus_ready = ae.aiplus_status()["ready"]
    cur = (rev["settings"].get("mode") if rev else s.get("mode"))
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
        mode += _theme_choice(e, (s.get("theme") or ""), model_ready)
    pic_ = ae.look_source_revision(ae.project(pid) or {}, rev) if rev else None     # the colours shown on a moment
    pic_rid = pic_["id"] if pic_ else None
    note = "" if first else ("The current revision stays as it is. Format, sound and colour variants keep its removed moments and your edits "
                             "and reuse the analysis; a new length chooses the moments again (removed ones stay out).")
    return (f"<form method='post' action='/auto/p/{pid}/variant' class='card' style='margin-top:14px' onsubmit=\"this.querySelector('button:not([type=button])').disabled=true\">{base}"
            f"<h2 style='margin-top:0'>{'Build reel' if first else 'Make a variant'}</h2>"
            f"<div class='muted'>{note}</div>"
            f"<div class='ae-choices'>{lengths}</div><div class='ae-choices'>{formats}</div>{_framing_choice(e, s.get('framing'))}<div class='ae-choices'>{sounds}</div>{_look_choice(e, s.get('look'), label=True, pic_rid=pic_rid)}{mode}"
            f"{_dress_fields(e, rev['settings'] if rev else prefill)}"
            f"<button>{'Build' if first else 'Make variant'}</button></form>")


def _look_choice(e, current=None, label=False, pic_rid=None, pic_src=None):
    """The reel's colours: as filmed (the default) or a look; only the reel is coloured, never the videos. pic_rid: a
    version to show each look on (a small picture of one of its moments, made when the page asks for it); pic_src:
    else one of the chosen videos (the new-reel page)."""
    cur = current if current in ae.LOOKS else "natural"
    url = ((lambda k: f"/auto/rev/{int(pic_rid)}/look/{k}.jpg") if pic_rid else
           (lambda k: f"/auto/new/look/{k}.jpg?src={urllib.parse.quote(str(pic_src))}") if pic_src else None)
    pic = lambda k: (f"<img class='ae-look-pic' src='{e(url(k))}' alt='' loading='lazy' onerror=\"this.remove()\">") if url else ""
    pic_rid = pic_rid or pic_src
    radio = lambda k, v: f"<input type='radio' name='look' value='{k}' {'checked' if k == cur else ''}> {e(v)}"
    radios = "".join((f"<label class='ae-look'>{pic(k)}<span class='row' style='gap:8px'>{radio(k, v)}</span></label>" if pic_rid
                      else f"<label>{radio(k, v)}</label>") for k, v in ae.LOOKS.items())
    return (("<div class='muted' style='margin:6px 0 4px;font-size:13px'>Colours:</div>" if label else "")
            + "<div class='ae-choices'>" + radios + "</div>"
            + ("" if label else "<div class='muted' style='margin:4px 0 0;font-size:13px'>Only the reel is coloured; "
                                "your videos stay as they are.</div>"))


def _look_video(scan) -> str | None:
    """The video the colours are shown on, on the new-reel page: the longest usable one."""
    try:
        ok = [r for r in scan["files"] if r.get("ok")]
        if not ok:
            return None
        best = max(ok, key=lambda r: float(r.get("duration_s") or 0))
        if scan.get("files_chosen"):
            return next((str(x) for x in scan["files_chosen"] if Path(x).name == best["name"]), None)
        return str(Path(scan["folder"]) / best["name"])
    except Exception:
        return None


def _framing_choice(e, current="fill"):
    """Horizontal videos in a vertical reel: cropped (default) or the whole picture on blurred edges."""
    radios = "".join(f"<label><input type='radio' name='framing' value='{k}' {'checked' if k == (current or 'fill') else ''}> {e(v)}</label>"
                     for k, v in ae.FRAMINGS.items())
    return (f"<div class='ae-framing'><div class='muted' style='margin:6px 0 4px;font-size:13px'>Horizontal videos in a vertical reel:</div>"
            f"<div class='ae-choices'>{radios}</div></div>")


_FRAMING_JS = ("(()=>{const V=%s;const upd=()=>{document.querySelectorAll('form').forEach(f=>{const b=f.querySelector('.ae-framing');"
               "const c=f.querySelector('input[name=format]:checked');if(b)b.style.display=(!c||V.includes(c.value))?'':'none'})};"
               "document.querySelectorAll('input[name=format]').forEach(r=>r.addEventListener('change',upd));upd()})();"
               % json.dumps([k for k, v in ae.FORMATS.items() if v["profile"] == "9x16"]))


def _mode_name(st: dict, e) -> str:
    """HTML: the way of choosing moments, and the theme (each its own element: translated separately)."""
    mode = {"semantic": "Moments: AI", "semantic_plus": "Moments: AI+", "technical": "Moments: Technical only"}.get(st.get("mode") or "", "")
    theme = ae.THEMES.get(st.get("theme") or "", "")
    return f"<span>{e(mode)}</span>" + (f" · <span>{e(theme)}</span>" if theme else "")


def _preparing_html(active, pid, e) -> str:
    """The card of a running "Prepare in advance" job (same ids as the build card: the same progress script)."""
    note = ("You can close this window: the videos keep being analysed and the PC does not go to sleep. When it is done, "
            + ("Windows shows a notification and " if _notify_on() else "") + "the reel is made here in minutes.")
    return (f"<div class='card' id='jobCard' data-job='{active['id']}' data-prepare='1'><div class='eyebrow'>Preparing in advance</div>"
            f"<div class='row space'><b id='jobStage'>{e(ae.STAGE_LABEL.get(active['stage'] or 'queued', ''))}</b>"
            f"<form method='post' action='/auto/job/{active['id']}/cancel'><button class='btn2'>Cancel</button></form></div>"
            f"<div class='ae-bar' style='margin:10px 0'><i id='jobBar' style='width:{active['percent']}%'></i></div>"
            f"<div class='muted' id='jobMsg'>{e(active.get('message') or '')}</div>"
            f"<div class='muted'>{_mode_name(active['settings'], e)}</div>{_waiting_html(active, pid, e)}"
            f"<div class='muted' style='margin-top:6px'>{e(note)}</div></div>")


def _prepared_html(j, e) -> str:
    """After "Prepare in advance": what was analysed; the build form below makes the reel."""
    info = ae.prepared_info(int(j["id"])) or {}
    n, skipped = int(info.get("input_count") or 0), len(info.get("skipped_inputs") or [])
    took = float(info.get("elapsed_s") or ae.job_elapsed_s(j) or 0)
    took_txt = (f"{took:.0f} <span>s</span>" if took < 90 else f"{took / 60:.0f} <span>min</span>")
    import html as _h
    data = _h.escape(json.dumps({"stages": info.get("stage_seconds") or {}, "ai": info.get("semantic_timing") or {},
                                 "hw": info.get("hw_decode")}), quote=True)
    return (f"<div class='card ae-done ae-prepared' data-timing='{data}' style='margin-bottom:12px'><div class='eyebrow'>Prepared in advance</div>"
            f"<div><span>Videos analysed:</span> {n}" + (f" · <span>skipped:</span> {skipped}" if skipped else "")
            + f" · <span>took</span> {took_txt} · {_mode_name(j['settings'], e)}</div>"
            f"<div class='muted' style='margin-top:4px'>Now press Build: the reel is made from the prepared videos in minutes. "
            f"Videos added to the folder later are analysed during the build.</div></div>")


def _convert_gpu_html(e) -> str:
    """Check this PC: converting on the graphics card (Convert page) - a test with a 4K clip and its result."""
    from . import converter as cv
    st = cv.gpu_test_state()
    if st["running"]:
        return (f"<div class='card' id='cgRun' data-el='{st['elapsed_s']}' style='margin-top:14px'><b>Testing converting on the graphics "
                f"card…</b> <span id='cgSec'>{int(st['elapsed_s'])}</span> s · <span class='muted' id='cgStep'>{e(st.get('step') or '')}</span>"
                f"<div class='muted' style='margin-top:4px'>About two minutes. You can leave this page.</div></div>")
    r = cv.gpu_test_saved()
    when = f" <span class='muted'>· tested {e(r['tested_at'])}</span>" if r.get("tested_at") else ""
    return (f"<div class='card' style='margin-top:14px'><b>Converting on the graphics card</b>{when}"
            f"<div class='muted' style='margin:4px 0 8px'>{e(cv.gpu_test_summary(r))}</div>"
            f"<div class='muted' style='margin-bottom:8px;font-size:13px'>The test makes a short 4K test clip smaller with the processor "
            f"and with the graphics card (NVIDIA) and compares the time and the picture. Convert uses the card only if it was faster "
            f"with the same picture. Your videos are not used.</div>"
            f"<form method='post' action='/auto/check/convert-gpu-test' style='margin:0'><button class='btn2'>"
            f"{'Test again' if r else 'Test converting on the graphics card'}</button></form></div>")


def _hwdecode_html(e) -> str:
    """Check this PC: the graphics-card decoding test (runs in the background) and its result."""
    from . import hwdecode
    st = hwdecode.state()
    if st["running"]:
        return (f"<div class='card' id='hwRun' data-el='{st['elapsed_s']}' style='margin-top:14px'><b>Testing the graphics card…</b> "
                f"<span id='hwSec'>{int(st['elapsed_s'])}</span> s · <span class='muted' id='hwStep'>{e(st.get('step') or '')}</span>"
                f"<div class='muted' style='margin-top:4px'>About a minute or two. You can leave this page.</div></div>")
    r = hwdecode.saved()
    used, line = hwdecode.summary(r, ae._ffmpeg())
    toggle = ""
    if r and (r.get("use") or r.get("off")):
        if r.get("off") and r.get("use"):
            toggle = ("<form method='post' action='/auto/check/hwtest-use' style='margin:0'><input type='hidden' name='on' value='1'>"
                      "<button class='btn2'>Use the graphics card</button></form>")
        elif used:
            toggle = ("<form method='post' action='/auto/check/hwtest-use' style='margin:0'><button class='btn2'>Do not use the graphics card"
                      "</button></form>")
    when = f" <span class='muted'>· tested {e(r['tested_at'])}</span>" if r.get("tested_at") else ""
    return (f"<div class='card' style='margin-top:14px'><b>Video decoding on the graphics card</b>{when}"
            f"<div class='muted' style='margin:4px 0 8px'>{e(line)}</div>"
            f"<div class='muted' style='margin-bottom:8px;font-size:13px'>The test cuts short 4K test clips with the processor and with the "
            f"graphics card and compares every frame. The graphics card is used only if the picture is exactly the same and it is clearly "
            f"faster. Your videos are not used.</div>"
            f"<div class='row' style='gap:8px;flex-wrap:wrap'><form method='post' action='/auto/check/hwtest' style='margin:0'>"
            f"<button class='btn2'>{'Test again' if r else 'Test the graphics card'}</button></form>{toggle}</div></div>")


def _notify_on() -> bool:
    try:
        from . import notify
        return os.name == "nt" and notify.enabled()
    except Exception:
        return False


def _build_time_html(res) -> str:
    """How long this version took and where the time went (a 4K folder can take long: the user sees why)."""
    try:
        st = res.get("stage_seconds") or {}
        total = float(res.get("elapsed_s") or sum(float(v) for v in st.values()))
    except (TypeError, ValueError, AttributeError):
        return ""
    if total < 1:
        return ""

    def d(x):
        x = float(x)
        return (f"{x:.0f} <span>s</span>" if x < 90 else f"{x / 60:.0f} <span>min</span>")
    parts = []
    for keys, lbl in ((("inputs", "analyze", "select"), "analysis"), (("render", "trim"), "cutting"), (("finish",), "joining")):
        v = sum(float(st.get(k) or 0) for k in keys)
        if v >= 0.5:
            parts.append(f"<span>{lbl}</span> {d(v)}")
    import html as _h
    tm = res.get("semantic_timing") or {}
    data = f" data-timing='{_h.escape(json.dumps({'stages': st, 'ai': tm, 'hw': res.get('hw_decode')}), quote=True)}'"   # for support: where the AI time went
    hw = res.get("hw_decode") or {}
    gpu = " · <span>cut with the graphics card</span>" if int(hw.get("cuts") or 0) > 0 else ""
    try:      # the camera's own small copies (DJI .LRF) looked at instead of the 4K videos
        nprox = int(tm.get("proxies") or 0)
    except (TypeError, ValueError, AttributeError):
        nprox = 0
    if nprox:
        gpu += f" · <span>moments found in the camera's small copies (.LRF):</span> {nprox}"
    return (f"<div class='muted ae-buildtime' style='font-size:13px'{data}><span>Built in</span> {d(total)}"
            + (" (" + " · ".join(parts) + ")" if parts else "") + gpu + "</div>")


def _sound_label(requested, res):
    audio = (res or {}).get("audio") or {}
    applied, reason = audio.get("applied"), str((audio.get("decision") or {}).get("reason") or "")
    if requested == "auto" and applied == "source":
        return "Auto → original sound"
    if requested == "auto" and applied == "mute":
        if "mixed" in reason:
            # accepted P11 rule: no jumps between sound and silence; the user can force the sound
            return "Auto → muted (some moments have no sound; choose “Source sound” to keep the sound)"
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
    pool, shown = [], set()
    for c in res.get("candidate_pool") or []:
        # the AI can rank the same window of a video twice (a short video's start): one line for it
        k = (str(c.get("source_name")), _fmt_s(c["start_s"]), _fmt_s(c["end_s"]))
        if c["event_id"] in in_reel or k in shown:
            continue
        shown.add(k); pool.append(c)
        if len(pool) == 40:
            break
    score_word = "оценка" if ae.ui_language() == "ru" else "score"      # options are not translated (file names in them)
    def _score(v):
        t = f"{float(v):.2f}"
        return t.replace(".", ",") if score_word == "оценка" else t
    opts = "".join(f"<option value='{e(c['event_id'])}' translate='no'>{e(c['source_name'])} {_fmt_s(c['start_s'])}–{_fmt_s(c['end_s'])} · {score_word} {_score(c['score'])}</option>" for c in pool)

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
                + (f"<a class='btn btn2' style='font-size:13px' target='_blank' href='/auto/p/{p['id']}/source?name={e(urllib.parse.quote(s['source_name']))}#t={s['source_in_s']},{s['source_out_s']}'>View in source</a>"
                   if p.get("source_present") and str(s["source_name"]) not in {Path(str(x)).name for x in (p.get("missing_files") or [])} else "")
                + "</div>"
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
        # cuts on the beat may end a reel up to about a beat and a half early (the engine then says nothing)
        beat_short = bool(res.get("beat_sync")) and "SHORTER_THAN_REQUESTED" not in (res.get("warnings") or []) \
            and "LIMITED_TOTAL_FOOTAGE" not in (res.get("warnings") or [])
        short_html = (f"<div class='callout card' style='margin-top:8px'>Requested {target:.0f} s, got {total:.1f} s: "
                      f"there were not enough different moments in this footage for a longer reel.</div>") if target and total < target - 1.0 and not beat_short else ""
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
            notes.append(f"moments that match the theme: {int(n) if n.isascii() and n.isdigit() else 0}")
        elif w == "TITLE_FONT_MISSING":
            notes.append("the title could not be drawn: no suitable font on this PC")
        elif w == "TITLE_CHARACTERS_LEFT_OUT":
            notes.append("emoji and symbols the font cannot draw were left out of the title")
        elif w == "MUSIC_NO_CLEAR_BEAT":
            notes.append("the music has no clear beat, so the cuts were left where they were")
    dress = res.get("dress") or {}
    if dress.get("title_shown") and (dress.get("title") or dress.get("subtitle")):
        notes.append(e("title: ") + "<span translate='no'>" + e(" / ".join(x for x in (dress.get("title"), dress.get("subtitle")) if x)) + "</span>")
    if dress.get("music"):
        notes.append(e("music: ") + names([dress["music"]["name"]])
                     + e(" (only music)" if dress["music"].get("mode") == "music" else " (with the videos' sound)"))
    bs_ = res.get("beat_sync") or {}
    if bs_.get("clear") and bs_.get("cuts"):
        in_time = int(bs_.get("cuts_on_beat") or 0) + int(bs_.get("cuts_half_way_between_beats") or 0)
        notes.append(e("cuts on the beat of the music: ") + f"{in_time}/{int(bs_['cuts'])} "
                     + f"({int(round(float(bs_.get('bpm') or 0)))} " + e("beats per minute") + ")")
    if res.get("hdr_sources"):
        notes.append(e("HDR video converted to normal colours: ") + names(res["hdr_sources"]))
    if res.get("deinterlaced_sources"):
        notes.append(e("camcorder video de-interlaced: ") + names(res["deinterlaced_sources"]))
    if res.get("widened_sources"):
        notes.append(e("wide picture stored in narrow pixels shown in its real shape: ") + names(res["widened_sources"]))
    skipped_html_extra = ("<div class='muted' style='margin-top:4px'>" + " · ".join(notes) + "</div>") if notes else ""
    # one step to a file: "Save MP4" on any finished version (it also becomes the chosen one - Accept is not a
    # separate chore before saving)
    last = next((x for x in p["exports"] if x["revision_id"] == rev["id"]), None) if is_acc else None
    exp_html = (f"<form method='post' action='/auto/p/{p['id']}/export' id='exportForm' style='margin-top:10px' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\">"
                f"<input type='hidden' name='dest' id='exportDest' value=''><input type='hidden' name='revision_id' value='{rev['id']}'>"
                f"<div class='row' style='flex-wrap:wrap'><button class='ae-big'>Save MP4</button>"
                f"<button type='button' class='btn2' id='exportToBtn'>Save to another folder…</button>"
                f"<button class='btn2' formaction='/auto/p/{p['id']}/small' title='About 720p, a much smaller file'>Small copy for messengers</button></div>"
                f"<div class='muted' style='margin-top:4px'>Saves to <span class='ae-path' translate='no'>{e(str(ae.export_dir_for(p)))}</span></div>"
                f"<div class='muted' id='exportMsg'></div></form>")
    small = request.args.get("small", "")
    if small:
        exp_html += (f"<div class='card ae-done' style='margin-top:10px'><span>Small copy saved:</span> <span class='ae-path' translate='no'>{e(small)}</span>"
                     f"<form method='post' action='/auto/exports/open' style='display:inline;margin-left:8px'><button class='btn2'>Exported reels</button></form></div>")
    if is_acc:
        if last:
            exp_html += (f"<div class='card' style='margin-top:10px'><b>Exported</b><div class='ae-path'>{e(last['path'])}</div>"
                         f"<div class='row' style='margin-top:8px;flex-wrap:wrap'><form method='post' action='/auto/export/{last['id']}/open'><button>Open video</button></form>"
                         f"<form method='post' action='/auto/export/{last['id']}/reveal'><button class='btn2'>Show in folder</button></form>"
                         f"<button type='button' class='btn2' id='copyPath' data-path='{e(last['path'])}'>Copy path</button>"
                         f"{_text_link(last['path'], e)}</div></div>")
    undo = "Revert" if ae.previous_accepted(p["id"]) else "Undo accept"     # with no earlier one, Revert just un-accepts
    actions = (f"<span class='badge ready'>Accepted</span><form method='post' action='/auto/p/{p['id']}/revert' "
               f"onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\">"
               f"<input type='hidden' name='from_revision' value='{int(rev['id'])}'><button class='btn2'>{undo}</button></form>" if is_acc else
               f"<form method='post' action='/auto/p/{p['id']}/accept' onsubmit=\"setTimeout(()=>this.querySelectorAll('button').forEach(b=>b.disabled=true),0)\"><input type='hidden' name='revision_id' value='{rev['id']}'><button class='btn2' title='Mark it as the chosen version without saving a file'>Accept this version</button></form>")
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
    sound_btn = ""
    if (not building and rev["settings"].get("sound") == "auto" and ((res.get("audio") or {}).get("applied") == "mute")):
        # Auto muted the reel: one click for the same reel with the videos' own sound
        sound_btn = (f"<form method='post' action='/auto/p/{p['id']}/variant' style='margin-top:6px'>"
                     f"<input type='hidden' name='base_revision_id' value='{rev['id']}'><input type='hidden' name='sound' value='source'>"
                     f"<button class='btn2' style='font-size:13px;padding:5px 10px'>The same reel with the original sound</button></form>")
        if "mixed" not in str(((res.get("audio") or {}).get("decision") or {}).get("reason") or "") and not rev["settings"].get("music"):
            # no useful sound at all (drone, action camera): a reel with own music is the usual answer
            sound_btn += ("<div class='row' style='margin-top:6px;gap:8px;align-items:center;flex-wrap:wrap'>"
                          "<span class='muted'>The videos have no useful sound - a reel with your own music?</span>"
                          "<button type='button' class='btn2' style='font-size:13px;padding:5px 10px' onclick=\"(()=>{const d=[...document.querySelectorAll('details.ae-dress')].pop();"
                          "if(!d)return;d.open=true;d.scrollIntoView({behavior:'smooth',block:'center'});"
                          "const b=[...d.querySelectorAll('button')].find(x=>x.dataset.pickMusic!==undefined);if(b)b.focus({preventScroll:true})})()\">Add music…</button></div>")
    return f"""<div class='ae-player' style='margin-top:14px'>
<div class='card'><video id='reel' class='ae-video' controls preload='metadata' src='/auto/rev/{rev['id']}/video'></video>
<div class='ae-strip film'>{strip}</div>
<div class='muted'>Revision R{int(rev['number']):03d} · {e(fmt.get('short',''))} {rev['width']}×{rev['height']}{" · <span>blurred edges</span>" if rev['settings'].get('framing') == 'fit_blur' else ""}{(" · <span>Colours:</span> <span>" + e(ae.LOOKS[rev['settings']['look']]) + "</span>") if rev['settings'].get('look') in ae.LOOKS else ""} · {total:.2f} s · sound {e(_sound_label(rev['settings']['sound'], res))} · <span>{e(mode)}</span>{(" · <span>theme</span> <span>" + e(theme_name) + "</span>") if theme_name else ""}</div>{_build_time_html(res)}{sound_btn}{short_html}{skipped_html}{skipped_html_extra}
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
