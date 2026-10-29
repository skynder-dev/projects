"""The Orders page: what other programs ordered, what is being done, what is ready (see orders.py, ORDERS.md)."""
from __future__ import annotations

import json

from flask import jsonify, redirect, request

from . import auto_edit as ae
from . import orders

KIND_LABEL = {"reel_from_videos": "Reel from videos", "render_plan": "Video by plan"}

# what each answer code means, in words (the exact detail is shown small underneath, as it is)
ERROR_TEXT = {
    "ORDER_JSON_INVALID": "The order file is not valid JSON.",
    "ORDER_FILE_MISSING": "A file named in the order is not there.",
    "ORDER_SCHEMA_UNKNOWN": "The order is not in the MediaEngine order format.",
    "ORDER_KIND_UNKNOWN": "MediaEngine does not know this kind of order.",
    "ORDER_FIELD_INVALID": "Something in the order is wrong.",
    "ORDER_PATH_OUTSIDE": "The order points to a file outside its folder.",
    "ORDER_NETWORK_PATH": "The order points to a network folder: not used.",
    "ORDER_ID_INVALID": "The order's name is not allowed.",
    "ORDER_ID_ALREADY_USED": "An order with this name was already received.",
    "PLAN_TIMES_INVALID": "The times in the plan do not fit together.",
    "PLAN_TOO_LONG": "The plan is longer than 10 minutes.",
    "PLAN_TOO_MANY_CLIPS": "The plan has too many clips.",
    "PLAN_IMAGE_UNREADABLE": "A picture of the plan cannot be read.",
    "PLAN_VIDEO_UNREADABLE": "A video of the plan cannot be read.",
    "PLAN_AUDIO_UNREADABLE": "The sound of the plan cannot be read.",
    "RENDER_FAILED": "The video could not be made.",
    "OUTPUT_CHECK_FAILED": "The finished video did not pass its checks.",
    "OUTPUT_COPY_FAILED": "The finished video could not be copied (disk full?).",
    "VIDEOS_NOT_USABLE": "The videos of the order cannot be used.",
    "NO_VIDEOS": "No video of this theme is on this PC.",
    "AIPLUS_NOT_READY": "The AI+ model is not on this PC yet.",
    "REEL_NOT_STARTED": "The reel could not be started.",
    "REEL_FAILED": "The reel could not be built.",
    "REJECTED_BY_OWNER": "You rejected this order.",
    "STOPPED_BY_OWNER": "You stopped this order.",
    "INTERNAL_ERROR": "MediaEngine had an internal error with this order.",
    "INTERRUPTED": "This order was started several times and never finished (MediaEngine was closed each time).",
    "PLAN_IMAGE_TOO_BIG": "A picture of the plan is too big.",
    "PLAN_PRIVATE_MEDIA": "The plan uses a video or picture marked Private: it is never used.",
}


def _when(iso) -> str:
    t = str(iso or "")
    return t[:16].replace("T", " ") if len(t) >= 16 and t[10:11] == "T" else t


def _secs(x) -> str:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return ""
    m, s = divmod(x, 60)
    return f"{int(m)}:{s:04.1f}"


def register(app, page, err_page, e, error_html):
    """Attach the Orders routes (called from auto_edit_web.register)."""

    def ok_id(oid: str) -> bool:
        if not oid or "/" in oid or "\\" in oid or oid in (".", ".."):
            return False
        return orders.valid_id(oid) or oid.startswith("order ")

    @app.get("/api/auto/orders")
    def ord_api():
        orders.start()
        return jsonify(orders.overview())

    @app.get("/auto/orders")
    def ord_page():
        orders.start()
        ov = orders.overview()
        items = ov["items"]

        def head(it):
            kind = KIND_LABEL.get(it.get("kind") or "", "")
            title = it.get("title") or ""
            bits = []
            if it.get("from"):
                bits.append("<span>ordered by</span> <b translate='no'>" + e(it["from"]) + "</b>")
            if kind:
                bits.append("<span>" + e(kind) + "</span>")
            return (f"<div class='row space'><b style='font-size:16px' translate='no'>{e(title or it['id'])}</b>"
                    f"<span class='muted ae-path' style='font-size:12px'>{e(it['id'])}</span></div>"
                    + (f"<div class='muted' style='margin-top:3px'>{' · '.join(bits)}</div>" if bits else ""))

        def btn(oid, action, label, cls="btn2", confirm=""):
            onsub = f" onsubmit=\"return confirm(document.getElementById('{confirm}').textContent)\"" if confirm else ""
            return (f"<form method='post' action='/auto/orders/{e(_q(oid))}/{action}' style='margin:0'{onsub}>"
                    f"<button class='{cls}'>{e(label)}</button></form>")

        def proj(it):
            pid = it.get("project_id")
            return f"<a class='btn btn2' href='/auto/p/{int(pid)}'>Open project</a>" if pid else ""

        cards = {"working": [], "new": [], "failed": [], "done": []}
        for it in items:
            st, oid = it["state"], it["id"]
            acts = ""
            if st in ("working", "waiting"):
                if st == "working":
                    prog = it.get("progress") or ""
                    line = "<span>Working on it</span>" + (f" · <span translate='no'>{e(prog)}</span>" if prog else "")
                else:
                    line = "Waiting for its turn"
                acts = (btn(oid, "stop", "Stop", "btn2", "stopq") if st == "working" else "") + proj(it)
                cards["working"].append(f"<div class='card'>{head(it)}<div style='margin-top:6px'>{line}</div>"
                                        f"<div class='row' style='margin-top:8px;gap:6px'>{acts}</div></div>")
            elif st in ("new", "arriving"):
                if st == "new":
                    acts = btn(oid, "run", "Run", "btn") + btn(oid, "reject", "Reject", "btn2", "rejectq")
                    busy_now = any(x["state"] in ("working", "waiting") for x in items)
                    line = ("Waiting for your OK" if not ov["auto_run"] else
                            "Waiting for its turn" if busy_now else "Starts in a moment")
                else:
                    line = ("Still arriving (order.json is not there yet)" if it.get("waiting_for") == "order.json" else
                            "Still arriving (its files are still being written)")
                cards["new"].append(f"<div class='card'>{head(it)}<div class='muted' style='margin-top:6px'>{line}</div>"
                                    f"<div class='row' style='margin-top:8px;gap:6px'>{acts}</div></div>")
            elif st in ("failed", "stuck"):
                err = it.get("error") or {}
                code = str(err.get("code") or "")
                if code == "REEL_FAILED":
                    why = error_html(err.get("message") or "", e)
                else:
                    why = (e(ERROR_TEXT.get(code, "The order could not be done."))
                           + f"<div class='muted' translate='no' style='font-size:11px;margin-top:4px'>{e(code)}: {e(err.get('message') or '')}</div>")
                acts = ((btn(oid, "retry", "Try again", "btn") if it.get("can_retry") and code not in ("STOPPED_BY_OWNER",) else "")
                        + (btn(oid, "retry", "Run again", "btn") if it.get("can_retry") and code == "STOPPED_BY_OWNER" else "")
                        + btn(oid, "reveal", "Show in folder") + proj(it) + btn(oid, "delete", "Delete", "btn2", "delq"))
                cards["failed"].append(f"<div class='card'>{head(it)}<div class='errbox' style='margin-top:8px'>{why}</div>"
                                       f"<div class='muted' style='margin-top:6px'>{e(_when(it.get('finished_at')))}</div>"
                                       f"<div class='row' style='margin-top:8px;gap:6px;flex-wrap:wrap'>{acts}</div></div>")
            elif st == "taken":
                acts = proj(it) + btn(oid, "delete", "Delete", "btn2", "delq")
                cards["done"].append(f"<div class='card'>{head(it)}<div class='muted' style='margin-top:6px'>The program took the answer.</div>"
                                     f"<div class='row' style='margin-top:8px;gap:6px;flex-wrap:wrap'>{acts}</div></div>")
            else:
                v = it.get("video") or {}
                info = " · ".join(x for x in (f"{v.get('width')}×{v.get('height')}" if v.get("width") else "",
                                              _secs(v.get("duration_s")), _when(it.get("finished_at"))) if x)
                acts = (btn(oid, "open", "Open video", "btn") + btn(oid, "reveal", "Show in folder") + proj(it)
                        + btn(oid, "delete", "Delete", "btn2", "delq"))
                cards["done"].append(f"<div class='card'>{head(it)}<div class='muted' style='margin-top:6px'>"
                                     f"<span class='badge safe'>video ready</span> <span translate='no'>{e(info)}</span></div>"
                                     f"<div class='row' style='margin-top:8px;gap:6px;flex-wrap:wrap'>{acts}</div></div>")

        def section(title, key):
            return (f"<div class='section-title'>{title}</div><div class='ae-grid'>{''.join(cards[key])}</div>"
                    if cards[key] else "")

        listing = (section("Orders in work", "working") + section("New orders", "new") + section("Orders not done", "failed")
                   + section("Ready orders", "done"))
        if not items:
            listing = ("<div class='card muted' style='margin-top:14px'>No orders yet. When another program puts an order "
                       "into the Inbox folder, it appears here.</div>")
        auto = ov["auto_run"]
        settings = (f"<form method='post' action='/auto/orders/settings' class='card' style='margin-top:14px'>"
                    f"<b>New orders</b><div class='ae-choices' style='margin-bottom:6px'>"
                    f"<label><input type='radio' name='auto_run' value='1' {'checked' if auto else ''}> Start at once</label>"
                    f"<label><input type='radio' name='auto_run' value='0' {'' if auto else 'checked'}> Wait for my OK</label></div>"
                    f"<button class='btn2'>Save setting</button></form>")
        example_plan = {"schema": orders.SCHEMA, "kind": "render_plan", "from": "my program", "title": "Example",
                        "plan": {"width": 1080, "height": 1920, "fps": 30, "audio": "voice.wav",
                                 "clips": [{"still": "frames/01.png", "start_s": 0, "end_s": 4.5},
                                           {"video": "clips/sea.mp4", "from_s": 12, "start_s": 4.5, "end_s": 9}]}}
        example_reel = {"schema": orders.SCHEMA, "kind": "reel_from_videos", "from": "my program", "title": "Sea trip",
                        "videos": {"folder": "D:\\Videos\\Trip"}, "length": 30, "format": "social_hd", "mode": "semantic"}
        howto = ("<details class='card' style='margin-top:14px'><summary><b>How another program sends an order</b></summary>"
                 "<div class='muted' style='margin-top:8px'>It makes a folder in Inbox (the folder name is the order's name), "
                 "puts its files there and writes order.json last. MediaEngine takes the order, makes the video and puts the "
                 "answer into Done (video.mp4 and result.json) or into Failed (result.json with the reason). "
                 "Nothing is published or sent anywhere. The full format: ORDERS.md in the Orders folder.</div>"
                 "<div class='muted' style='margin-top:8px'>A video by plan (pictures, pieces of videos and a sound track):</div>"
                 f"<pre class='ae-path' style='white-space:pre-wrap'>{e(json.dumps(example_plan, indent=2, ensure_ascii=False))}</pre>"
                 "<div class='muted'>A reel from videos (MediaEngine chooses the moments):</div>"
                 f"<pre class='ae-path' style='white-space:pre-wrap'>{e(json.dumps(example_reel, indent=2, ensure_ascii=False))}</pre></details>")
        body = (f"<div class='pagehead'><div class='eyebrow'>Tools</div><h1>Orders</h1>"
                f"<div class='lead'>Other programs on this PC can order a video: they put an order into the Inbox folder, "
                f"MediaEngine makes the video and puts it into Done with a receipt. Nothing is published.</div>"
                f"<div class='row' style='margin-top:10px;gap:6px'>"
                f"<form method='post' action='/auto/orders/open-inbox' style='margin:0'><button class='btn2'>Inbox folder</button></form>"
                f"<form method='post' action='/auto/orders/open-done' style='margin:0'><button class='btn2'>Done folder</button></form>"
                f"<a class='btn btn2' href='/auto'>Auto Edit</a></div>"
                f"<div class='muted ae-path' style='margin-top:6px'>{e(ov['inbox'])}</div></div>"
                f"<span id='delq' hidden>Delete this order's folders in Orders (with the files it brought)? Your own videos elsewhere and your projects stay.</span>"
                f"<span id='rejectq' hidden>Reject this order? It will not be done.</span>"
                f"<span id='stopq' hidden>Stop this order?</span>"
                f"{listing}{settings}{howto}")
        busy = any(it["state"] in ("working", "waiting", "new", "arriving") for it in items)
        script = ("setTimeout(()=>{if(!document.querySelector('details[open]'))location.reload()},5000);" if busy else "")
        return page("Orders", body, script)

    @app.post("/auto/orders/settings")
    def ord_settings():
        orders.set_auto_run(request.form.get("auto_run") == "1")
        return redirect("/auto/orders")

    @app.post("/auto/orders/open-inbox")
    def ord_open_inbox():
        orders.ensure_dirs()
        ae.open_path(orders.inbox_dir())
        return redirect("/auto/orders")

    @app.post("/auto/orders/open-done")
    def ord_open_done():
        orders.ensure_dirs()
        ae.open_path(orders.done_dir())
        return redirect("/auto/orders")

    @app.post("/auto/orders/<path:oid>/<action>")
    def ord_action(oid, action):
        if not ok_id(oid) or action not in ("run", "reject", "retry", "stop", "delete", "open", "reveal"):
            return err_page("Order not found", "/auto/orders")
        if action == "run":
            orders.run_now(oid)
        elif action == "reject":
            orders.reject(oid)
        elif action == "retry":
            if not orders.retry(oid):
                return err_page("This order cannot be done again.", "/auto/orders")
        elif action == "stop":
            orders.stop(oid)
        elif action == "delete":
            try:
                if not orders.delete(oid):
                    return err_page("This order cannot be deleted now.", "/auto/orders")
            except orders.OrderBusy as exc:
                return err_page(str(exc), "/auto/orders")
        elif action == "open":
            v = orders.result_video(oid)
            if not v or not ae.open_path(v):
                return err_page("The video of this order is not there.", "/auto/orders")
        elif action == "reveal":
            f = orders.order_folder(oid)
            target = (f / "video.mp4") if f and (f / "video.mp4").is_file() else f
            if not target or not ae.open_path(target, reveal=(target != f)):
                return err_page("The folder of this order is not there.", "/auto/orders")
        return redirect("/auto/orders")


def _q(oid: str) -> str:
    import urllib.parse
    return urllib.parse.quote(oid, safe="")
