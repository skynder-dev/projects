"""Edit by hand (handedit.py): the list of edits and the editor - the material (this PC, the Library, the downloads,
the found moments), the player, the time line (trim by the edges, drag to reorder, split, remove, undo) and the MP4.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from flask import Response, jsonify, redirect, request, send_file

from . import handedit as HE
from . import voice as vo

_MIME = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/mp4", ".webm": "video/webm"}


def _key(src: str) -> str:
    return hashlib.sha1(str(src).encode("utf-8")).hexdigest()[:16]


def _view(e: dict) -> dict:
    """The edit for the page: each piece with its key (the page names videos only by it), name and length."""
    out = []
    for p in e["pieces"]:
        i = HE.info(p["src"])
        out.append(dict(p, k=_key(p["src"]), name=Path(p["src"]).name, dur=float(i.get("seconds") or p["out"]),
                        plays=bool(i.get("plays")), there=Path(p["src"]).is_file()))
    return {"id": e["id"], "title": e["title"], "format": e["format"], "pieces": out, "seconds": HE.seconds(e)}


def _src_of(e: dict, k: str) -> str:
    return next((p["src"] for p in e.get("pieces") or [] if _key(p["src"]) == k), "")


def _renders(eid: str) -> list[dict]:
    """The edit's MP4s: being made, waiting, made (newest first)."""
    out = []
    for j in vo.list_jobs(300):
        if j.get("kind") != "handedit_render" or j.get("edit") != eid:
            continue
        r = j.get("result") or {}
        out.append({"job": j["id"], "state": j.get("state"), "error": r.get("error") or "", "saved": r.get("saved") or "",
                    "seconds": r.get("seconds") or j.get("seconds") or 0, "format": j.get("format") or "",
                    "at": str(j.get("created_at") or "")[:16].replace("T", " "),
                    "step": (vo._CURRENT.get("step") if vo._CURRENT.get("id") == j["id"] else "") or "",
                    "progress": (vo._CURRENT.get("progress") if vo._CURRENT.get("id") == j["id"] else 0) or 0})
        if len(out) >= 10:
            break
    return out


def _sources(kind: str) -> list[dict]:
    """What can be added: Library videos, downloaded videos, found moments (each with what "add" sends)."""
    out = []
    if kind == "library":
        from .converter import _local_path
        from .db import VISIBLE_SQL, db
        try:
            with db() as con:
                rows = con.execute(f"SELECT i.* FROM inventory i WHERE i.media_type='video' AND {VISIBLE_SQL} "
                                   "ORDER BY i.id DESC LIMIT 400").fetchall()
        except Exception:
            rows = []
        for r in rows:
            p = _local_path(r)
            if p:
                out.append({"name": r["filename"], "seconds": round((r["duration_ms"] or 0) / 1000, 1),
                            "thumb": f"/thumb/{int(r['id'])}", "add": {"library": int(r["id"])}})
    elif kind == "downloaded":
        from . import auto_edit as ae, downloader as D
        try:
            files = sorted((x for x in D.folder().iterdir() if x.is_file() and x.suffix.lower() in ae.SUPPORTED),
                           key=lambda x: x.stat().st_mtime, reverse=True)[:300]
        except OSError:
            files = []
        out = [{"name": x.name, "seconds": 0, "add": {"downloaded": x.name}} for x in files]
    elif kind == "moments":
        try:
            from .media_brain import best_clips
            rows = best_clips(300)
        except Exception:
            rows = []
        for r in rows:
            a, b = (r["start_ms"] or 0) / 1000, (r["end_ms"] or 0) / 1000
            out.append({"name": r["filename"], "sub": f"{int(a // 60)}:{int(a % 60):02d}–{int(b // 60)}:{int(b % 60):02d}",
                        "seconds": round(b - a, 1), "thumb": f"/clip-preview/{int(r['id'])}", "add": {"moment": int(r["id"])}})
    return out


def _resolve(d: dict) -> tuple[list, float | None, float | None, str]:
    """What the page asked to add -> (files, start, end, where from)."""
    from .converter import _local_path
    from .db import VISIBLE_SQL, db
    if d.get("library") is not None:
        with db() as con:
            r = con.execute(f"SELECT i.* FROM inventory i WHERE i.id=? AND i.media_type='video' AND {VISIBLE_SQL}",
                            (int(d["library"]),)).fetchone()
        p = _local_path(r) if r else None
        if not p:
            raise HE.EditError("This Library video is not on this PC now (a drive not connected?).")
        return [str(p)], None, None, "library"
    if d.get("downloaded"):
        from . import downloader as D
        name = Path(str(d["downloaded"])).name
        p = D.folder() / name
        if not p.is_file():
            raise HE.EditError("This downloaded video is not there any more.")
        return [str(p)], None, None, "downloaded"
    if d.get("moment") is not None:
        with db() as con:
            r = con.execute(f"""SELECT vc.start_ms, vc.end_ms, i.* FROM virtual_clips vc JOIN inventory i ON i.id=vc.inventory_id
                                WHERE vc.id=? AND {VISIBLE_SQL}""", (int(d["moment"]),)).fetchone()
        p = _local_path(r) if r else None
        if not p:
            raise HE.EditError("This moment's video is not on this PC now.")
        return [str(p)], (r["start_ms"] or 0) / 1000, (r["end_ms"] or 0) / 1000, "moment"
    paths = d.get("paths") if isinstance(d.get("paths"), list) else []
    return [str(x) for x in paths][:50], None, None, ""


def register(app, page, err_page, e, human_bytes):
    def _json():
        d = request.get_json(silent=True)
        return d if isinstance(d, dict) else {}

    @app.get("/edit")
    def edit_home():
        rows = ""
        for x in HE.items():
            secs = HE.seconds(x)
            rows += (f"<a class='card jobrow' href='/edit/{x['id']}'><b translate='no'>{e(x['title'])}</b>"
                     f"<span class='muted'><span translate='no'>{len(x['pieces'])}</span> <span>pieces</span> · "
                     f"<span translate='no'>{int(secs // 60)}:{int(secs % 60):02d}</span> · <span translate='no'>{e(x['format'])}</span></span>"
                     f"<span class='muted' translate='no'>{e(x['updated_at'][:16].replace('T', ' '))}</span></a>")
        body = (f"<div class='pagehead'><div class='eyebrow'>Create</div><h1>Edit by hand</h1><div class='lead'>Put a video "
                f"together yourself from pieces of any videos - from this PC, the Library, the downloads or the moments "
                f"MediaEngine found: cut them, put them in order, choose the format and save the MP4. The originals are "
                f"never changed; an edit can be opened and changed again.</div></div>"
                f"<div class='card'><form method='post' action='/edit/new' class='row' style='gap:8px;flex-wrap:wrap;margin:0'>"
                f"<input name='title' placeholder='Name of the edit' maxlength='80' style='min-width:220px'>"
                f"<select name='format'><option value='9:16'>Vertical 9:16</option><option value='16:9'>Wide 16:9</option>"
                f"<option value='1:1'>Square 1:1</option><option value='4:5'>4:5</option></select>"
                f"<button>New edit</button></form></div>"
                + (f"<div class='section-title'>My edits</div><div class='jobs'>{rows}</div>" if rows else "")
                + "<div class='muted' style='margin-top:14px;font-size:13px'><a href='/composer'>Compositions from found moments</a> "
                  "<span>(the earlier way: only moments MediaEngine found)</span></div>")
        return page("Edit by hand", body)

    @app.post("/edit/new")
    def edit_new():
        eid = HE.new(request.form.get("title") or "", request.form.get("format") or "9:16")
        return redirect(f"/edit/{eid}")

    @app.get("/edit/<eid>")
    def edit_page(eid):
        ed = HE.get(eid)
        if not ed:
            return err_page("This edit is not there any more.", "/edit")
        data = json.dumps(_view(ed), ensure_ascii=False).replace("</", "<\\/")
        fmts = "".join(f"<option value='{k}' {'selected' if k == ed['format'] else ''}>{e(v)}</option>"
                       for k, v in (("9:16", "Vertical 9:16"), ("16:9", "Wide 16:9"), ("1:1", "Square 1:1"), ("4:5", "4:5")))
        body = (CSS + f"<script type='application/json' id='heData'>{data}</script>"
                f"<div class='pagehead'><div class='eyebrow'><a href='/edit'>Edit by hand</a></div>"
                f"<div class='he-top'><input id='heTitle' value='{e(ed['title'])}' maxlength='80' translate='no' title='Name of the edit'>"
                f"<select id='heFmt' title='Format'>{fmts}</select>"
                f"<span class='muted' id='heSaved'></span><span style='flex:1'></span>"
                f"<button id='heRender'>Save MP4</button></div></div>"
                f"<div class='he-main'>"
                f"<div class='card he-src'><div class='he-tabs'>"
                f"<button type='button' class='btn2 on' data-tab='pc'>This PC</button>"
                f"<button type='button' class='btn2' data-tab='library'>Library</button>"
                f"<button type='button' class='btn2' data-tab='downloaded'>Downloaded</button>"
                f"<button type='button' class='btn2' data-tab='moments'>Found moments</button></div>"
                f"<div data-pane='pc'><button type='button' id='hePick'>Choose videos on this PC</button>"
                f"<div class='muted' style='font-size:13px;margin:8px 0 4px'>Or paste a video's full path:</div>"
                f"<div class='row' style='gap:6px'><input id='hePath' placeholder='D:\\\\Videos\\\\clip.mp4' style='flex:1;min-width:0' translate='no'>"
                f"<button type='button' class='btn2' id='hePathAdd'>Add</button></div></div>"
                f"<div data-pane='library' hidden></div><div data-pane='downloaded' hidden></div><div data-pane='moments' hidden></div>"
                f"<div class='muted' id='heMsg' style='font-size:13px;margin-top:8px'></div></div>"
                f"<div class='card he-view'><div class='he-frame' id='heFrame'><video id='heV' playsinline preload='auto'></video>"
                f"<div class='he-empty' id='heEmpty'>Add videos: they go to the end of the time line below.</div>"
                f"<div class='he-wait' id='heWait' hidden>Preparing a copy the browser can play…</div></div>"
                f"<div class='he-ctl'><button type='button' class='btn2' id='heHome' title='To the start'>⏮</button>"
                f"<button type='button' id='hePlay' title='Play / pause (Space)'>▶</button>"
                f"<span id='heTime' translate='no'>0:00.0 / 0:00.0</span><span style='flex:1'></span>"
                f"<button type='button' class='btn2' id='heSplit' title='Cut the piece where the line is (S)'>✂ Split</button>"
                f"<button type='button' class='btn2' id='heUndo' title='Undo (Ctrl+Z)'>↶ Undo</button></div></div>"
                f"<div class='card he-prop' id='heProp'><b>Piece</b><div class='muted' id='heNone' style='font-size:13px;margin-top:6px'>"
                f"Click a piece on the time line.</div><div id='heOne' hidden>"
                f"<div class='he-name' id='heName' translate='no'></div>"
                f"<label>Start <input id='heIn' inputmode='decimal' translate='no'></label>"
                f"<label>End <input id='heOut' inputmode='decimal' translate='no'></label>"
                f"<div class='muted' style='font-size:13px'><span>Length</span> <span id='heLen' translate='no'></span></div>"
                f"<label class='he-chk'><input type='checkbox' id='heMute'> Without its sound</label>"
                f"<div class='row' style='gap:6px;margin-top:8px;flex-wrap:wrap'>"
                f"<button type='button' class='btn2' id='heLeft' title='Move it earlier'>←</button>"
                f"<button type='button' class='btn2' id='heRight' title='Move it later'>→</button>"
                f"<button type='button' class='btn2' id='heDup'>Repeat</button>"
                f"<button type='button' class='btn2' id='heDel' title='Remove the piece (Delete)'>Remove</button></div></div></div>"
                f"</div>"
                f"<div class='card he-tlbox'><div class='row' style='gap:8px;align-items:center'><b>Time line</b>"
                f"<span class='muted' style='font-size:13px'>Drag a piece's edge to cut it, the piece to move it; click to see that moment.</span>"
                f"<span style='flex:1'></span><button type='button' class='btn2' id='heZoomOut' title='Smaller'>−</button>"
                f"<button type='button' class='btn2' id='heZoomIn' title='Bigger'>+</button></div>"
                f"<div class='he-tl' id='heTL'><div class='he-ruler' id='heRuler'></div><div class='he-track' id='heTrack'></div>"
                f"<div class='he-head' id='heHead'></div></div></div>"
                f"<div class='card' style='margin-top:12px'><b>Saved MP4s</b><div id='heRenders' class='muted' style='font-size:13px;margin-top:6px'>"
                f"None yet.</div></div>"
                f"<form method='post' action='/edit/{eid}/delete' style='margin-top:12px' "
                f"onsubmit=\"return confirm(window.ME_L?ME_L('Delete this edit? Its saved MP4s stay.'):'Delete this edit? Its saved MP4s stay.')\">"
                f"<button class='btn2'>Delete this edit</button></form>")
        return page("Edit by hand", body, JS)

    @app.post("/edit/<eid>/delete")
    def edit_delete(eid):
        HE.delete(eid)
        return redirect("/edit")

    @app.post("/api/edit/<eid>")
    def edit_save(eid):
        d = _json()
        try:
            ed = HE.save(eid, d.get("title"), d.get("format"), d.get("pieces"))
        except HE.EditError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(_view(ed))

    @app.post("/api/edit/<eid>/add")
    def edit_add(eid):
        try:
            files, a, b, origin = _resolve(_json())
            if not files:
                raise HE.EditError("No video chosen.")
            ed = HE.add(eid, files, a, b, origin)
        except HE.EditError as exc:
            return jsonify({"error": str(exc)}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "This could not be added."}), 400
        v = _view(ed)
        if ed.get("not_added"):
            v["error"] = "These could not be used as videos: " + ", ".join(ed["not_added"][:5])
        return jsonify(v)

    @app.post("/api/edit/<eid>/pick")
    def edit_pick(eid):
        from . import auto_edit as ae
        if not HE.get(eid):
            return jsonify({"error": "This edit is not there any more."}), 404
        files = ae.pick_files("Choose videos for the edit", initial=ae.last_source_folder())
        if not files:
            return jsonify({"error": "No videos chosen. You can also paste a path."}), 400
        try:
            ed = HE.add(eid, files)
        except HE.EditError as exc:
            return jsonify({"error": str(exc)}), 400
        v = _view(ed)
        if ed.get("not_added"):
            v["error"] = "These could not be used as videos: " + ", ".join(ed["not_added"][:5])
        return jsonify(v)

    @app.get("/api/edit/sources")
    def edit_sources():
        return jsonify({"items": _sources(str(request.args.get("kind") or ""))})

    @app.get("/edit/<eid>/media")
    def edit_media(eid):
        ed = HE.get(eid)
        src = _src_of(ed, str(request.args.get("k") or "")) if ed else ""
        if not src or not Path(src).is_file():
            return ("", 404)
        if request.args.get("proxy") == "1":
            pr = HE.proxy(src, make=False)
            if pr.get("state") != "done":
                return ("", 404)
            return send_file(pr["path"], mimetype="video/mp4", conditional=True, max_age=0)
        return send_file(src, mimetype=_MIME.get(Path(src).suffix.lower(), "video/mp4"), conditional=True, max_age=0)

    @app.post("/api/edit/<eid>/proxy")
    def edit_proxy(eid):
        ed = HE.get(eid)
        src = _src_of(ed, str(_json().get("k") or "")) if ed else ""
        if not src:
            return jsonify({"state": "failed"}), 404
        pr = HE.proxy(src)
        return jsonify({"state": pr.get("state"), "error": pr.get("error") or ""})

    @app.get("/edit/<eid>/frame")
    def edit_frame(eid):
        ed = HE.get(eid)
        src = _src_of(ed, str(request.args.get("k") or "")) if ed else ""
        if not src or not Path(src).is_file():
            return ("", 404)
        try:
            t = float(request.args.get("t") or 0)
        except ValueError:
            t = 0.0
        data = HE.frame(src, t)
        if not data:
            return ("", 404)
        return Response(data, mimetype="image/jpeg", headers={"Cache-Control": "max-age=3600"})

    @app.post("/api/edit/<eid>/render")
    def edit_render(eid):
        try:
            jid = HE.new_render(eid)
        except (HE.EditError, vo.VoiceError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"job": jid, "renders": _renders(eid)})

    @app.get("/api/edit/<eid>/renders")
    def edit_renders(eid):
        return jsonify({"renders": _renders(eid)})

    def _render_job(jid: str) -> dict:
        if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}", str(jid or "")):
            return {}
        try:
            j = vo.read_job(jid)
        except vo.VoiceError:
            return {}
        return j if j.get("kind") == "handedit_render" else {}

    @app.get("/edit/render/<jid>.mp4")
    def edit_render_file(jid):
        j = _render_job(jid)
        p = vo._job_dir(jid) / "edit.mp4" if j else None
        if not p or not p.is_file():
            return ("", 404)
        return send_file(p, mimetype="video/mp4", conditional=True, max_age=0)

    @app.post("/api/edit/render/<jid>/stop")
    def edit_render_stop(jid):
        if _render_job(jid):
            vo.cancel_job(jid)
        return jsonify({"ok": True})

    @app.post("/api/edit/render/<jid>/reveal")
    def edit_render_reveal(jid):
        j = _render_job(jid)
        saved = Path(str((j.get("result") or {}).get("saved") or "")) if j else None
        if saved and saved.is_file():
            from . import auto_edit as ae
            ae.open_path(saved, reveal=True)
            return jsonify({"ok": True})
        return jsonify({"error": "The MP4 is not there any more."}), 404


CSS = """<style>
.he-top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px}
.he-top #heTitle{font-size:20px;font-weight:700;min-width:200px;flex:0 1 420px}
.he-main{display:grid;grid-template-columns:260px minmax(0,1fr) 230px;gap:12px;align-items:start}
@media(max-width:1100px){.he-main{grid-template-columns:minmax(0,1fr) 230px}.he-src{grid-column:1/-1}}
@media(max-width:700px){.he-main{grid-template-columns:minmax(0,1fr)}}
.he-tabs{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px}.he-tabs .btn2{padding:4px 9px;margin:0}
.he-tabs .on{outline:2px solid var(--acc,#7aa2ff)}
.he-list{max-height:360px;overflow:auto;display:flex;flex-direction:column;gap:6px}
.he-item{display:grid;grid-template-columns:56px minmax(0,1fr) auto;gap:8px;align-items:center;font-size:13px}
.he-item img{width:56px;height:32px;object-fit:cover;border-radius:5px;background:#0004}
.he-item .n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.he-view{display:flex;flex-direction:column;gap:8px;align-items:center}
.he-frame{position:relative;background:#000;border-radius:10px;overflow:hidden;height:min(calc(52vh / var(--z,1)),560px);max-width:100%}
.he-frame video{width:100%;height:100%;object-fit:cover;display:block}
.he-empty,.he-wait{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;
 padding:18px;color:#cfd6e4;font-size:14px;background:#0009}
.he-empty[hidden],.he-wait[hidden]{display:none}
.he-ctl{display:flex;gap:8px;align-items:center;width:100%;flex-wrap:wrap}
.he-ctl #hePlay{min-width:54px}
.he-prop label{display:flex;gap:6px;align-items:center;margin-top:8px;font-size:14px}
.he-prop label input:not([type=checkbox]){width:100px}
.he-name{font-size:13px;margin-top:6px;overflow-wrap:anywhere}
.he-tlbox{margin-top:12px}
.he-tl{position:relative;overflow-x:auto;overflow-y:hidden;margin-top:8px;padding-bottom:6px;user-select:none;touch-action:pan-x}
.he-ruler{position:relative;height:18px;font-size:11px;color:var(--muted,#9aa)}
.he-ruler span{position:absolute;top:0;border-left:1px solid #ffffff30;padding-left:3px;height:18px}
.he-track{position:relative;height:74px;background:#ffffff08;border-radius:8px}
.he-p{position:absolute;top:4px;height:66px;border-radius:7px;background:#2c3550 center/auto 100% repeat-x;
 border:2px solid #ffffff30;box-sizing:border-box;cursor:grab;overflow:hidden}
.he-p.sel{border-color:var(--acc,#7aa2ff);box-shadow:0 0 0 2px var(--acc,#7aa2ff)}
.he-p.drag{opacity:.75;z-index:3;cursor:grabbing}
.he-p.gone{border-color:#e05a5a}
.he-p .lb{position:absolute;left:8px;right:8px;bottom:3px;font-size:11px;color:#fff;text-shadow:0 1px 2px #000;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none}
.he-p .mu{position:absolute;right:8px;top:3px;font-size:12px;pointer-events:none}
.he-p .h{position:absolute;top:0;bottom:0;width:9px;background:#ffffff40;cursor:ew-resize}
.he-p .h.l{left:0}.he-p .h.r{right:0}.he-p .h:hover{background:var(--acc,#7aa2ff)}
.he-mark{position:absolute;top:0;bottom:0;width:3px;background:var(--acc,#7aa2ff);z-index:4;pointer-events:none}
.he-head{position:absolute;top:0;bottom:0;width:2px;background:#ff5a5a;pointer-events:none;z-index:5}
.he-r{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid var(--line,#ffffff14)}
.he-r .bar{width:120px;height:6px;background:#ffffff18;border-radius:3px;overflow:hidden}.he-r .bar i{display:block;height:100%;background:var(--acc,#7aa2ff)}
</style>"""

JS = r"""(()=>{
const D=JSON.parse(document.getElementById('heData').textContent);const id=D.id;
let P=D.pieces,sel=-1,T=0,pps=20,playing=false,cur=-1,hist=[],saveT=null,useProxy={};
const $=x=>document.getElementById(x),V=$('heV'),track=$('heTrack'),tl=$('heTL'),head=$('heHead'),ruler=$('heRuler');
const L=s=>window.ME_L?ME_L(s):s;
const fmtT=s=>{s=Math.max(0,s);const m=Math.floor(s/60);return m+':'+(s-m*60).toFixed(1).padStart(4,'0')};
const len=p=>Math.max(0,p.out-p.in),total=()=>P.reduce((a,p)=>a+len(p),0);
const startOf=i=>P.slice(0,i).reduce((a,p)=>a+len(p),0);
const at=t=>{let a=0;for(let i=0;i<P.length;i++){const l=len(P[i]);if(t<a+l||i==P.length-1)return [i,Math.min(l,Math.max(0,t-a))];a+=l}return [-1,0]};
function msg(s,bad){const m=$('heMsg');m.textContent=s?L(s):'';m.style.color=bad?'#ff8a8a':''}
function snap(){hist.push(JSON.stringify(P));if(hist.length>60)hist.shift()}
function setFrame(){const f=$('heFmt').value.split(':');const fr=$('heFrame');fr.style.aspectRatio=f[0]+'/'+f[1]}
function save(now){clearTimeout(saveT);$('heSaved').textContent=L('Saving…');saveT=setTimeout(async()=>{
 try{const r=await fetch('/api/edit/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('heTitle').value,
 format:$('heFmt').value,pieces:P.map(p=>({src:p.src,in:+p.in.toFixed(3),out:+p.out.toFixed(3),mute:!!p.mute,from:p.from||undefined}))})});
 const x=await r.json();if(x.error){$('heSaved').textContent='';msg(x.error,true);return}
 $('heSaved').textContent=L('Saved')}catch(e){$('heSaved').textContent=L('Not saved: MediaEngine is not answering')}},now?0:500)}
function useServer(x){if(x.error)msg(x.error,true);else msg('');if(x.pieces){P=x.pieces;draw();show(T)}}
function fit(){const w=tl.clientWidth-20,t=total();if(t>0)pps=Math.max(2,Math.min(160,w/t))}
function draw(){
 track.innerHTML='';const t=total();const w=Math.max(tl.clientWidth-4,t*pps+40);track.style.width=w+'px';ruler.style.width=w+'px';
 let a=0;P.forEach((p,i)=>{const d=document.createElement('div');d.className='he-p'+(i==sel?' sel':'')+(p.there===false?' gone':'');
  d.style.left=(a*pps)+'px';d.style.width=Math.max(10,len(p)*pps)+'px';d.dataset.i=i;
  d.style.backgroundImage="url('/edit/"+id+"/frame?k="+p.k+"&t="+p.in.toFixed(1)+"')";
  d.innerHTML="<div class='h l'></div><div class='h r'></div><div class='lb'></div>"+(p.mute?"<div class='mu'>🔇</div>":'');
  d.querySelector('.lb').textContent=fmtT(len(p))+' · '+p.name;track.appendChild(d);a+=len(p)});
 ruler.innerHTML='';const step=[1,2,5,10,15,30,60,120,300,600].find(s=>s*pps>=70)||600;
 for(let s=0;s<=t+step;s+=step){const m=document.createElement('span');m.style.left=(s*pps)+'px';m.textContent=fmtT(s).replace(/\.0$/,'');ruler.appendChild(m)}
 $('heEmpty').hidden=P.length>0;prop();moveHead()}
function moveHead(){head.style.left=(T*pps)+'px';$('heTime').textContent=fmtT(T)+' / '+fmtT(total())}
function prop(){const p=P[sel];$('heOne').hidden=!p;$('heNone').hidden=!!p;if(!p)return;
 $('heName').textContent=p.name;if(document.activeElement!==$('heIn'))$('heIn').value=p.in.toFixed(2);
 if(document.activeElement!==$('heOut'))$('heOut').value=p.out.toFixed(2);$('heLen').textContent=fmtT(len(p));$('heMute').checked=!!p.mute}
function srcUrl(p){return '/edit/'+id+'/media?k='+p.k+(useProxy[p.k]?'&proxy=1':'')}
function show(t){T=Math.max(0,Math.min(t,total()));moveHead();if(!P.length){V.removeAttribute('src');return}
 const [i,off]=at(T);const p=P[i];if(!p)return;if(cur!==i||V.dataset.k!==p.k+(useProxy[p.k]?'p':'')){cur=i;V.dataset.k=p.k+(useProxy[p.k]?'p':'');
 V.src=srcUrl(p);V.muted=!!p.mute;V.addEventListener('loadedmetadata',()=>{V.currentTime=p.in+off;if(playing)V.play().catch(()=>{})},{once:true})}
 else{V.muted=!!p.mute;if(Math.abs(V.currentTime-(p.in+off))>0.08)V.currentTime=p.in+off}}
function play(on){playing=on;$('hePlay').textContent=on?'⏸':'▶';if(on){if(T>=total()-0.05)T=0;show(T);V.play().catch(()=>{})}else V.pause()}
V.addEventListener('timeupdate',()=>{if(!playing||cur<0||!P[cur])return;const p=P[cur];
 if(V.currentTime>=p.out-0.04){if(cur>=P.length-1){play(false);T=total();moveHead();return}T=startOf(cur+1);show(T);return}
 T=startOf(cur)+Math.max(0,V.currentTime-p.in);moveHead()});
V.addEventListener('error',async()=>{const p=P[cur];if(!p||useProxy[p.k])return;$('heWait').hidden=false;
 for(let n=0;n<1800;n++){try{const r=await fetch('/api/edit/'+id+'/proxy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({k:p.k})});
 const x=await r.json();if(x.state==='done'){useProxy[p.k]=1;$('heWait').hidden=true;cur=-1;show(T);return}
 if(x.state==='failed'){$('heWait').hidden=true;msg('This video cannot be shown here (it is still used in the MP4).',true);return}}catch(e){}
 await new Promise(r=>setTimeout(r,2000))}});
$('hePlay').onclick=()=>play(!playing);$('heHome').onclick=()=>{play(false);show(0)};
// the time line: click to see a moment; drag an edge to cut; drag a piece to move it
let drag=null;
track.addEventListener('pointerdown',ev=>{const d=ev.target.closest('.he-p');const x0=ev.clientX;
 const rect=track.getBoundingClientRect();const tAt=(ev.clientX-rect.left)/pps;
 if(!d){play(false);show(tAt);return}
 const i=+d.dataset.i;const edge=ev.target.classList.contains('h')?(ev.target.classList.contains('l')?'l':'r'):'';
 sel=i;drag={i,edge,x0,in0:P[i].in,out0:P[i].out,moved:false,el:d,tAt};snap();d.setPointerCapture(ev.pointerId);
 track.querySelectorAll('.he-p').forEach(x=>x.classList.toggle('sel',x===d));prop()});
track.addEventListener('pointermove',ev=>{if(!drag)return;const dx=ev.clientX-drag.x0;const p=P[drag.i];
 if(drag.edge){const ds=dx/pps;if(drag.edge==='l'){p.in=Math.min(Math.max(0,drag.in0+ds),p.out-0.2);show(startOf(drag.i))}
  else{p.out=Math.max(Math.min(p.dur||1e9,drag.out0+ds),p.in+0.2);show(startOf(drag.i)+len(p)-0.05)}
  const a=startOf(drag.i);drag.el.style.left=(a*pps)+'px';drag.el.style.width=Math.max(10,len(p)*pps)+'px';
  drag.el.querySelector('.lb').textContent=fmtT(len(p))+' · '+p.name;prop();drag.moved=true;return}
 if(!drag.moved&&Math.abs(dx)<6)return;drag.moved=true;drag.el.classList.add('drag');drag.el.style.transform='translateX('+dx+'px)';
 const rect=track.getBoundingClientRect(),xm=(ev.clientX-rect.left)/pps;let to=P.length-1,a=0;
 for(let k=0;k<P.length;k++){if(xm<a+len(P[k])/2){to=k;break}a+=len(P[k])}drag.to=to;
 let mk=track.querySelector('.he-mark');if(!mk){mk=document.createElement('div');mk.className='he-mark';track.appendChild(mk)}
 mk.style.left=(startOf(to>drag.i?to+1:to)*pps-1)+'px'});
function endDrag(){if(!drag)return;const g=drag;drag=null;track.querySelector('.he-mark')?.remove();
 if(g.edge){draw();save();return}
 if(!g.moved){hist.pop();play(false);show(g.tAt);draw();return}
 const to=g.to??g.i;if(to!==g.i){const [p]=P.splice(g.i,1);P.splice(to,0,p);sel=to}else hist.pop();draw();show(startOf(sel));save()}
track.addEventListener('pointerup',endDrag);track.addEventListener('pointercancel',endDrag);
// the piece's own settings
function setTimes(){const p=P[sel];if(!p)return;const a=parseFloat(($('heIn').value||'').replace(',','.')),b=parseFloat(($('heOut').value||'').replace(',','.'));
 if(isNaN(a)||isNaN(b))return;snap();p.in=Math.max(0,Math.min(a,(p.dur||1e9)-0.2));p.out=Math.min(p.dur||1e9,Math.max(b,p.in+0.2));draw();show(startOf(sel));save()}
$('heIn').onchange=setTimes;$('heOut').onchange=setTimes;
$('heMute').onchange=()=>{const p=P[sel];if(!p)return;snap();p.mute=$('heMute').checked;draw();show(T);save()};
function remove(){if(sel<0)return;snap();P.splice(sel,1);sel=Math.min(sel,P.length-1);draw();show(Math.min(T,total()));save()}
function split(){const [i,off]=at(T);const p=P[i];if(!p||off<0.2||len(p)-off<0.2){msg('Put the red line inside a piece, not at its edge, to split it.');return}
 snap();const q=Object.assign({},p);q.in=p.in+off;p.out=p.in+off;P.splice(i+1,0,q);sel=i+1;draw();save()}
function move(d){const i=sel,j=sel+d;if(i<0||j<0||j>=P.length)return;snap();[P[i],P[j]]=[P[j],P[i]];sel=j;draw();show(startOf(sel));save()}
$('heDel').onclick=remove;$('heSplit').onclick=split;$('heLeft').onclick=()=>move(-1);$('heRight').onclick=()=>move(1);
$('heDup').onclick=()=>{if(sel<0)return;snap();P.splice(sel+1,0,Object.assign({},P[sel]));sel++;draw();save()};
function undo(){if(!hist.length)return;P=JSON.parse(hist.pop());sel=Math.min(sel,P.length-1);draw();show(Math.min(T,total()));save()}
$('heUndo').onclick=undo;
$('heZoomIn').onclick=()=>{pps=Math.min(240,pps*1.5);draw()};$('heZoomOut').onclick=()=>{pps=Math.max(1,pps/1.5);draw()};
document.addEventListener('keydown',ev=>{const tag=(ev.target.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||tag==='select')return;
 if(ev.key===' '){ev.preventDefault();play(!playing)}else if(ev.key==='s'||ev.key==='S'||ev.key==='ы'||ev.key==='Ы'){split()}
 else if(ev.key==='Delete'||ev.key==='Backspace'){ev.preventDefault();remove()}else if((ev.ctrlKey||ev.metaKey)&&(ev.key==='z'||ev.key==='я')){ev.preventDefault();undo()}
 else if(ev.key==='ArrowLeft'){play(false);show(T-(ev.shiftKey?1:1/30))}else if(ev.key==='ArrowRight'){play(false);show(T+(ev.shiftKey?1:1/30))}});
$('heTitle').oninput=()=>save();$('heFmt').onchange=()=>{setFrame();save(true)};
// the material
async function add(body){msg('Adding…');try{const r=await fetch('/api/edit/'+id+'/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const x=await r.json();const was=P.length;useServer(x);if(x.pieces&&x.pieces.length>was){fit();sel=x.pieces.length-1;draw();show(startOf(sel));if(!x.error)msg('Added at the end of the time line.')}}catch(e){msg('MediaEngine is not answering.',true)}}
$('hePick').onclick=async()=>{msg('A window to choose videos is open (it may be behind this one).');try{const r=await fetch('/api/edit/'+id+'/pick',{method:'POST'});
 const x=await r.json();const was=P.length;useServer(x);if(x.pieces&&x.pieces.length>was){fit();sel=x.pieces.length-1;draw();show(startOf(sel));if(!x.error)msg('Added at the end of the time line.')}}catch(e){msg('MediaEngine is not answering.',true)}};
$('hePathAdd').onclick=()=>{const v=$('hePath').value.trim().replace(/^"|"$/g,'');if(v)add({paths:[v]})};
const loaded={};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=async()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('on',x===b));
 document.querySelectorAll('[data-pane]').forEach(x=>x.hidden=x.dataset.pane!==b.dataset.tab);const k=b.dataset.tab;if(k==='pc'||loaded[k])return;loaded[k]=1;
 const pane=document.querySelector("[data-pane='"+k+"']");pane.textContent=L('Loading…');
 try{const r=await fetch('/api/edit/sources?kind='+k);const x=await r.json();pane.textContent='';
 if(!x.items.length){pane.textContent=L(k==='library'?'No videos in the Library on this PC yet.':k==='downloaded'?'Nothing downloaded yet (Download by a link).':'No moments found yet (Library: tick videos, then Media Brain).');return}
 const list=document.createElement('div');list.className='he-list';x.items.forEach(it=>{const row=document.createElement('div');row.className='he-item';
 row.innerHTML=(it.thumb?"<img loading='lazy' alt=''>":"<span></span>")+"<div class='n' translate='no'></div><button type='button' class='btn2'>+</button>";
 if(it.thumb)row.querySelector('img').src=it.thumb;row.querySelector('.n').textContent=it.name+(it.sub?' · '+it.sub:'')+(it.seconds?' · '+fmtT(it.seconds).replace(/\.\d$/,''):'');
 row.querySelector('button').onclick=()=>add(it.add);list.appendChild(row)});pane.appendChild(list)}catch(e){pane.textContent=L('MediaEngine is not answering.')}});
// the MP4s
async function renders(){try{const r=await fetch('/api/edit/'+id+'/renders');const x=await r.json();showR(x.renders||[])}catch(e){}}
function showR(rs){const box=$('heRenders');if(!rs.length){box.textContent=L('None yet.');return}box.innerHTML='';let busy=false;
 rs.forEach(r=>{const row=document.createElement('div');row.className='he-r';const st=r.state;
  if(st==='working'||st==='waiting'){busy=true;row.innerHTML="<b></b><div class='bar'><i></i></div><span class='s'></span><button type='button' class='btn2'>Stop</button>";
   row.querySelector('b').textContent=L(st==='working'?'Being made':'Waiting');row.querySelector('i').style.width=Math.round(100*(r.progress||0))+'%';
   row.querySelector('.s').textContent=r.at;row.querySelector('button').onclick=async()=>{await fetch('/api/edit/render/'+r.job+'/stop',{method:'POST'});renders()}}
  else if(st==='done'){row.innerHTML="<b></b><span class='s' translate='no'></span><a class='btn btn2' target='_blank'>Play</a><button type='button' class='btn2'>Show in folder</button>";
   row.querySelector('b').textContent=L('Ready');row.querySelector('.s').textContent=r.at+' · '+fmtT(r.seconds||0)+' · '+r.format+(r.saved?' · '+r.saved:'');
   row.querySelector('a').href='/edit/render/'+r.job+'.mp4';row.querySelector('button').onclick=()=>fetch('/api/edit/render/'+r.job+'/reveal',{method:'POST'})}
  else{row.innerHTML="<b></b><span class='s'></span>";row.querySelector('b').textContent=L(r.error==='Stopped.'?'Stopped':'Failed');row.querySelector('.s').textContent=r.at+(r.error?' · '+L(r.error):'')}
  box.appendChild(row)});if(busy)setTimeout(renders,1500)}
$('heRender').onclick=async()=>{clearTimeout(saveT);$('heRender').disabled=true;
 try{await fetch('/api/edit/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('heTitle').value,format:$('heFmt').value,
 pieces:P.map(p=>({src:p.src,in:+p.in.toFixed(3),out:+p.out.toFixed(3),mute:!!p.mute,from:p.from||undefined}))})});
 const r=await fetch('/api/edit/'+id+'/render',{method:'POST'});const x=await r.json();if(x.error)msg(x.error,true);else{msg('The MP4 is being made in the background; you can go on editing.');showR(x.renders||[])}}
 catch(e){msg('MediaEngine is not answering.',true)}$('heRender').disabled=false};
window.addEventListener('resize',()=>{draw()});
setFrame();fit();draw();show(0);renders();
})();"""
