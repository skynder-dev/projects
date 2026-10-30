"""The Inbox page (/inbox): links, topics and videos to work on - from the owner's phone (Telegram bot), from other
programs (orders of kind "idea") or typed here - each with one-click next steps; and the phone's setup card shown in
Settings (Settings → Phone)."""
from __future__ import annotations

import re
from pathlib import Path

from flask import redirect, request

from . import inbox, telegram_bot as tg

_ID = r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}"
CSS = """<style>
.ib-item{border-top:1px solid var(--line);padding:12px 0}.ib-item:first-child{border-top:0}
.ib-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.ib-row form{margin:0}
.ib-link{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0}.ib-link .ae-path{flex:1;min-width:200px;overflow-wrap:anywhere}
.ib-text{white-space:pre-wrap;margin-top:6px}
</style>"""


def phone_card(e) -> str:
    """Settings → Phone: the owner's Telegram bot - set up in three steps, then paired with his chat."""
    s = tg.status()
    err = f"<div class='errbox' style='margin-top:8px'>{e(s['error'])}</div>" if s.get("error") else ""
    if not s["configured"]:
        body = ("<div>Send links, topics and short videos from your phone straight into MediaEngine's Inbox - through your "
                "own Telegram bot. Free; nothing on this PC is opened to the internet (MediaEngine asks Telegram for new "
                "messages itself).</div>"
                "<ol style='margin:8px 0 0 18px;padding:0'><li><span>In Telegram, open</span> <b translate='no'>@BotFather</b><span>, send</span> "
                "<span class='ae-path' translate='no'>/newbot</span><span>, choose a name and a username for the bot.</span></li>"
                "<li>BotFather answers with a token (like 1234567890:AAH…): copy it.</li>"
                "<li>Paste it here and press Connect.</li></ol>"
                "<form method='post' action='/settings/phone' class='row' style='margin-top:10px'>"
                "<input type='password' name='token' autocomplete='off' placeholder='The bot token from @BotFather' "
                "style='flex:1;min-width:260px' required><button>Connect</button></form>"
                "<div class='muted' style='font-size:13px;margin-top:6px'>The token is kept in the Windows credential "
                "store of this user, never in a file of the program or a log.</div>")
    elif not s["paired"]:
        body = (f"<div><span>Your bot:</span> <b translate='no'>{e(s['bot'])}</b></div>"
                f"<div style='margin-top:6px'>Now, in Telegram, open your bot and send it this message:</div>"
                f"<div class='ae-path' translate='no' style='font-size:20px;margin:6px 0'>/start {e(s['code'])}</div>"
                f"<div class='muted' style='font-size:13px'>Only the chat that sends this code is served; other people "
                f"writing to the bot get no answer. The page shows “Connected” when it is done (refresh it).</div>"
                f"<div class='row' style='margin-top:8px'><form method='post' action='/settings/phone/code' style='margin:0'>"
                f"<button class='btn2'>A new code</button></form><form method='post' action='/settings/phone/forget' style='margin:0'>"
                f"<button class='btn2'>Disconnect the bot</button></form></div>")
    else:
        body = (f"<div><span class='badge safe'>Connected</span> <span>Your bot:</span> <b translate='no'>{e(s['bot'])}</b>"
                f" · <span>chat:</span> <b translate='no'>{e(s['chat'])}</b></div>"
                f"<div class='muted' style='margin-top:6px'><span>Share a link or a video to the bot, or write it a topic - it "
                f"appears in the Inbox.</span> <a href='/inbox'>Open the Inbox</a></div>"
                f"<div class='muted' style='font-size:13px'>The bot says when a download started from the Inbox is done.</div>"
                + (f"<div class='muted' style='font-size:13px'><span>Last contact with Telegram:</span> <span translate='no'>{e(s['seen_at'])}</span></div>"
                   if s.get("seen_at") else "")
                + "<div class='row' style='margin-top:8px'><form method='post' action='/settings/phone/unpair' style='margin:0'>"
                  "<button class='btn2'>Connect another chat</button></form><form method='post' action='/settings/phone/forget' "
                  "style='margin:0'><button class='btn2'>Disconnect the bot</button></form></div>")
    return (f"<div class='section-title' id='phone'>Phone (Telegram bot)</div><div class='card'>{body}{err}</div>")


def register(app, page, err_page, e, human_bytes):

    def _src(it: dict) -> str:
        s = str(it.get("source") or "")
        if s == "telegram":
            return "<span class='badge ready'>From the phone</span>"
        if s.startswith("program:"):
            return f"<span class='badge duplicate'><span>From</span> <span translate='no'>{e(s[8:])}</span></span>"
        return "<span class='badge'>Added here</span>"

    def _item(it: dict) -> str:
        iid = it["id"]
        when = e(str(it.get("created_at") or "")[:16].replace("T", " "))
        head = (f"<div class='ib-row'>{_src(it)}<span class='muted' style='font-size:13px' translate='no'>{when}</span>"
                + (f"<b translate='no'>{e(it['title'])}</b>" if it.get("title") else "") + "</div>")
        body = ""
        text = str(it.get("text") or "")
        if text:
            body += f"<div class='ib-text' translate='no'>{e(text)}</div>"
        if it.get("why"):
            body += f"<div class='muted' style='margin-top:4px'><span>Why:</span> <span translate='no'>{e(it['why'])}</span></div>"
        for u in it.get("links") or []:
            body += (f"<div class='ib-link'><a class='ae-path' translate='no' href='{e(u)}' target='_blank' rel='noopener noreferrer'>{e(u)}</a>"
                     f"<form method='post' action='/media/download/look'><input type='hidden' name='url' value='{e(u)}'>"
                     f"<input type='hidden' name='inbox' value='{iid}'><button class='btn2'>Show the videos</button></form></div>")
        acts = ""
        if text and it.get("kind") in ("topic", "idea"):
            acts += f"<a class='btn btn2' href='/auto/cartoon?about={e(_q(text))}#writer'>Write a story</a>"
        f = str(it.get("file") or "")
        if f:
            ok = Path(f).is_file()
            body += f"<div class='ib-link'><span class='ae-path' translate='no'>{e(f)}</span>" + ("" if ok else "<span class='muted'>(not there any more)</span>") + "</div>"
            if ok:
                acts += (f"<form method='post' action='/auto/cartoon/study'><input type='hidden' name='video' value='{e(f)}'>"
                         f"<input type='hidden' name='listen' value='1'><button class='btn2'>Study its rhythm</button></form>"
                         f"<form method='post' action='/auto/cartoon/write'><input type='hidden' name='video' value='{e(f)}'>"
                         f"<button class='btn2'>Write a story from it</button></form>"
                         f"<form method='post' action='/inbox/{iid}/reveal'><button class='btn2'>Show in folder</button></form>")
        done = it.get("state") == "done"
        acts += (f"<form method='post' action='/inbox/{iid}/{'new' if done else 'done'}'><button class='btn2'>"
                 f"{'Back to new' if done else 'Done'}</button></form>"
                 f"<form method='post' action='/inbox/{iid}/delete'><button class='btn2'>Remove</button></form>")
        return f"<div class='ib-item'>{head}{body}<div class='ib-row' style='margin-top:8px'>{acts}</div></div>"

    def _q(text: str) -> str:
        import urllib.parse
        return urllib.parse.quote(text[:1500])

    @app.get("/inbox")
    def inbox_page():
        all_ = inbox.items()
        new = [x for x in all_ if x.get("state") != "done"]
        old = [x for x in all_ if x.get("state") == "done"]
        s = tg.status()
        phone = ((f"<span class='badge safe'>Phone connected</span> <span translate='no'>{e(s['bot'])}</span>") if s["paired"] else
                 "<a href='/settings#phone'>Connect your phone (a Telegram bot)</a>")
        add = ("<div class='card'><form method='post' action='/inbox/add'>"
               "<textarea name='text' rows='2' maxlength='2000' style='width:100%' placeholder='A link to a video or a profile, or a topic'></textarea>"
               "<div class='ib-row' style='margin-top:8px'><button>Add to the Inbox</button>"
               f"<span class='muted' style='font-size:13px'>{phone}</span></div></form></div>")
        lst = (f"<div class='card' style='margin-top:14px'><h2 style='margin-top:0'><span>New</span> <span translate='no'>({len(new)})</span></h2>"
               + ("".join(_item(x) for x in new) or "<div class='muted'>Nothing new. Links, topics and videos sent from your "
                                                       "phone or by other programs appear here.</div>") + "</div>")
        if old:
            lst += (f"<details class='card' style='margin-top:14px'><summary><span>Done</span> <span translate='no'>({len(old)})</span></summary>"
                    + "".join(_item(x) for x in old[:100]) + "</details>")
        body = (f"{CSS}<div class='pagehead'><div class='eyebrow'>MediaEngine</div><h1>Inbox</h1>"
                f"<div class='lead'>What to work on: links to videos you liked, topics, short videos - from your phone, from "
                f"other programs (Social) or added here. Open a link to choose its videos and study their style, or write a "
                f"story about a topic.</div></div>{add}{lst}")
        return page("Inbox", body)

    @app.post("/inbox/add")
    def inbox_add():
        text = str(request.form.get("text") or "").strip()
        links = inbox.links_in(text)
        try:
            if links:
                rest = text
                for u in links:
                    rest = rest.replace(u, " ")
                inbox.add("link", links=links, text=rest, source="page")
            else:
                inbox.add("topic", text=text, source="page")
        except (inbox.InboxError, OSError) as exc:
            return err_page(str(exc) if isinstance(exc, inbox.InboxError) else "The Inbox could not be saved. Try again.", "/inbox")
        return redirect("/inbox")

    @app.post("/inbox/<iid>/<what>")
    def inbox_act(iid, what):
        if not re.fullmatch(_ID, iid) or what not in ("done", "new", "delete", "reveal"):
            return redirect("/inbox")
        try:
            if what == "delete":
                inbox.delete(iid)
            elif what == "reveal":
                f = Path(str(inbox.get(iid).get("file") or ""))
                if f.is_file():
                    from . import auto_edit as ae
                    ae.open_path(f, reveal=True)
            else:
                inbox.set_state(iid, what)
        except (inbox.InboxError, OSError):
            pass
        return redirect("/inbox")

    # ---- Settings → Phone
    @app.post("/settings/phone")
    def phone_set():
        try:
            tg.set_token(request.form.get("token") or "")
        except tg.BotError as exc:
            return err_page(str(exc), "/settings#phone")
        except OSError:
            return err_page("The token could not be kept (the Windows credential store). Try again.", "/settings#phone")
        return redirect("/settings#phone")

    @app.post("/settings/phone/<what>")
    def phone_act(what):
        if what == "code":
            tg.new_code()
        elif what == "unpair":
            tg.unpair()
        elif what == "forget":
            tg.forget()
        return redirect("/settings#phone")
