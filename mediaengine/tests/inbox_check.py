"""Checks of the Inbox (inbox.py, inbox_web.py), the order kind "idea" (orders.py) and the phone's Telegram bot
(telegram_bot.py) against a stand-in Telegram server on this PC (no network, no real bot).

  python tests/inbox_check.py <work_dir>   -> JSON with passed / total; exit 1 when a check fails
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS: list = []
TOKEN = "1234567890:AAH" + "x" * 32


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {str(detail)[:600]}"), flush=True)


class FakeTelegram:
    """api.telegram.org's methods the bot uses: getMe, getUpdates (long poll), sendMessage, getFile, file download."""

    def __init__(self, video: bytes):
        self.updates: list = []
        self.sent: list = []
        self.next_id = 1
        self.video = video
        self.lock = threading.Lock()
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, obj, code=200):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                if self.path.startswith(f"/file/bot{TOKEN}/videos/short"):     # a download cut off half-way
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(fake.video)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(fake.video[:1000])
                    self.wfile.flush()
                    self.close_connection = True
                elif self.path.startswith(f"/file/bot{TOKEN}/"):
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(fake.video)))
                    self.end_headers()
                    self.wfile.write(fake.video)
                else:
                    self._json({"ok": False, "description": "Not Found"}, 404)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                m = re.match(r"^/bot([^/]+)/(\w+)$", self.path)
                if not m or m.group(1) != TOKEN:
                    return self._json({"ok": False, "description": "Unauthorized"}, 401)
                meth = m.group(2)
                if meth == "getMe":
                    return self._json({"ok": True, "result": {"id": 1, "is_bot": True, "username": "my_medeng_bot"}})
                if meth == "getUpdates":
                    off = int(body.get("offset") or 0)
                    t0 = time.time()
                    while time.time() - t0 < min(2.0, float(body.get("timeout") or 0)):
                        with fake.lock:
                            ups = [u for u in fake.updates if u["update_id"] >= off]
                        if ups:
                            break
                        time.sleep(0.05)
                    with fake.lock:
                        ups = [u for u in fake.updates if u["update_id"] >= off]
                    return self._json({"ok": True, "result": ups})
                if meth == "sendMessage":
                    with fake.lock:
                        fake.sent.append(body)
                    return self._json({"ok": True, "result": {"message_id": len(fake.sent)}})
                if meth == "getFile":
                    name = "videos/short_1.mp4" if body.get("file_id") == "SHORT" else "videos/file_7.mp4"
                    return self._json({"ok": True, "result": {"file_id": body.get("file_id"), "file_path": name}})
                if meth == "deleteWebhook":
                    return self._json({"ok": True, "result": True})
                return self._json({"ok": False, "description": "Bad Request: unknown method"}, 400)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def message(self, chat: int, text: str = "", chat_type: str = "private", **extra):
        with self.lock:
            uid = self.next_id
            self.next_id += 1
            msg = {"message_id": uid, "chat": {"id": chat, "type": chat_type, "first_name": "Owner"}, "date": int(time.time())}
            if text:
                msg["caption" if extra else "text"] = text
            msg.update(extra)
            self.updates.append({"update_id": uid, "message": msg})
        return uid

    def wait_sent(self, n: int, limit: float = 15):
        t0 = time.time()
        while time.time() - t0 < limit:
            with self.lock:
                if len(self.sent) >= n:
                    return list(self.sent)
            time.sleep(0.05)
        with self.lock:
            return list(self.sent)


def main() -> int:
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    os.environ["MEDENG_TELEGRAM_TOKEN_FILE"] = "1"         # (the token in the data folder: no Windows credential written)
    sys.path.insert(0, str(HERE.parent / "app"))
    from archivist import voice as vo
    ff = vo._ffmpeg()
    clip = work / "clip.mp4"
    subprocess.run([ff, "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x568:d=3:r=25", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(clip)], check=True, capture_output=True, timeout=120)
    fake = FakeTelegram(clip.read_bytes())
    os.environ["MEDENG_TELEGRAM_API"] = fake.url
    from archivist import downloader as D, inbox, orders, telegram_bot as tg
    tg.API = fake.url
    from archivist.web import create_app
    app = create_app()
    H = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}

    with app.test_client() as c:
        # 1. the Inbox page; a link and a topic added by hand
        p0 = c.get("/inbox", headers=H).get_data(as_text=True)
        r1 = c.post("/inbox/add", data={"text": "look at this https://www.youtube.com/@fakecartoons/videos style"}, headers=H)
        r2 = c.post("/inbox/add", data={"text": "Why a school pays twice for the same laptops"}, headers=H)
        bad = c.post("/inbox/add", data={"text": "   "}, headers=H)
        its = inbox.items()
        p1 = c.get("/inbox", headers=H).get_data(as_text=True)
        home = c.get("/", headers=H).get_data(as_text=True)
        check("the Inbox: a link and a topic added by hand, each with its next step (show the videos, write a story); an "
              "empty one refused; the menu and Home show the new ones",
              "Nothing new" in p0 and r1.status_code == 302 and r2.status_code == 302 and bad.status_code == 400 and len(its) == 2
              and its[1]["kind"] == "link" and its[1]["links"] == ["https://www.youtube.com/@fakecartoons/videos"]
              and its[0]["kind"] == "topic" and "Show the videos" in p1 and "/auto/cartoon?about=Why%20a%20school" in p1
              and "navbadge' translate='no'>2<" in p1 and "Inbox:</b>" in home, [(x["kind"], x.get("links")) for x in its])
        from archivist.cartoon import writer as W
        real_inst, real_status = W.installed, W.status
        W.installed = lambda: True                                    # (the writer's form is shown when it is installed)
        W.status = lambda: {**real_status(), "which": real_status()["recommend"]}
        try:
            prefill = c.get("/auto/cartoon?about=Why%20a%20school%20pays%20twice", headers=H).get_data(as_text=True)
        finally:
            W.installed, W.status = real_inst, real_status
        check("Write a story from the Inbox: the story writer's form comes with the topic",
              "medicine'>Why a school pays twice</textarea>" in prefill, prefill.split("name='about'", 1)[-1][:300])

        # 2. an order of kind "idea" from another program goes into the Inbox; a bad one is refused
        orders.ensure_dirs()
        (orders.inbox_dir() / "trend-1.json").write_text(json.dumps({
            "schema": orders.SCHEMA, "kind": "idea", "from": "social", "title": "Cartoons about city money",
            "idea": {"topic": "How a city pays twice for one road", "why": "3 channels grew 40% this week with it",
                     "links": ["https://www.youtube.com/watch?v=abc123", "https://www.tiktok.com/@x/video/1"], "lang": "en"}}), "utf-8")
        (orders.inbox_dir() / "trend-2.json").write_text(json.dumps({
            "schema": orders.SCHEMA, "kind": "idea", "from": "social", "idea": {"links": ["file:///C:/x.mp4"]}}), "utf-8")
        old = time.time() - 10
        for n in ("trend-1.json", "trend-2.json"):
            os.utime(orders.inbox_dir() / n, (old, old))
        for _ in range(3):
            orders.process_next()
        r_ok = json.loads((orders.done_dir() / "trend-1" / "result.json").read_text("utf-8")) if (orders.done_dir() / "trend-1").is_dir() else {}
        r_bad = json.loads((orders.failed_dir() / "trend-2" / "result.json").read_text("utf-8")) if (orders.failed_dir() / "trend-2").is_dir() else {}
        idea = inbox.get(r_ok.get("inbox_item") or "")
        p2 = c.get("/inbox", headers=H).get_data(as_text=True)
        op = c.get("/auto/orders", headers=H).get_data(as_text=True)
        check("an order of kind idea (from Social): into the Inbox with its topic, why and links, answered done without a "
              "video; a link that is not a web address refused",
              r_ok.get("status") == "done" and "video" not in r_ok and idea.get("source") == "program:social"
              and idea.get("why", "").startswith("3 channels") and len(idea.get("links") or []) == 2
              and r_bad.get("error", {}).get("code") == "IDEA_LINK_INVALID" and "From</span> <span translate='no'>social" in p2
              and "in the Inbox" in op, (r_ok, r_bad.get("error")))

        # 3. the phone: the bot's token checked, a pairing code; only the chat with the code is served
        bad_tok = c.post("/settings/phone", data={"token": "not a token"}, headers=H)
        c.post("/settings/phone", data={"token": TOKEN}, headers=H)
        st = tg.status()
        s1 = c.get("/settings", headers=H).get_data(as_text=True)
        tok_file = (work / "home" / "telegram" / "token").read_text("utf-8").strip() == TOKEN
        cfg_text = (work / "home" / "config.json").read_text("utf-8") if (work / "home" / "config.json").is_file() else ""
        check("the bot set up: a wrong token refused, the right one checked with Telegram (its name shown) and kept outside "
              "the settings file; a pairing code to send",
              bad_tok.status_code == 400 and st["configured"] and st["bot"] == "@my_medeng_bot" and re.fullmatch(r"\d{6}", st["code"] or "")
              and f"/start {st['code']}" in s1 and tok_file and TOKEN not in cfg_text, (st, bad_tok.status_code))
        fake.message(-100, f"/start {st['code']}", chat_type="group")  # a group, even with the right code: never
        cfg_p = work / "home" / "config.json"
        for _ in range(tg.CODE_TRIES):                                # wrong codes: the code changes after a few
            tg.handle({"chat": {"id": 999, "type": "private"}, "text": "/start 111111"})
        changed = tg.status()["code"] != st["code"]
        from archivist.config import update_config
        update_config(lambda cfg: cfg["telegram"].update(code_at=time.time() - tg.CODE_TTL_S - 5))
        expired = tg.handle({"chat": {"id": 999, "type": "private"}, "text": "/start " + str(tg._cfg().get("code"))})
        st = dict(st, code=tg.new_code())
        check("pairing: never a group; a code expires and changes after a few wrong tries",
              changed and "/start 123456" in (expired or "") and not tg.status()["paired"], (changed, expired))
        fake.message(555, "/start 000000")                          # a stranger with a wrong code
        fake.message(777, f"/start {st['code']}")                    # the owner
        sent = fake.wait_sent(2)
        time.sleep(0.5)
        st2 = tg.status()
        fake.message(555, "https://www.youtube.com/watch?v=spam")    # the stranger again: ignored
        fake.message(777, "смотри https://www.youtube.com/watch?v=one001 и https://www.threads.com/share/xyz")
        fake.message(777, "kak gorod platit dvazhdy za dorogu")
        fake.message(777, "my video", video={"file_id": "F1", "file_size": len(fake.video), "file_name": "trip.mp4", "mime_type": "video/mp4"})
        fake.message(777, "", video={"file_id": "F2", "file_size": 25 * 1024 * 1024, "file_name": "big.mp4"})
        fake.message(777, "", document={"file_id": "SHORT", "file_size": len(fake.video), "file_name": "cut.mp4", "mime_type": "video/mp4"})
        fake.message(777, "", document={"file_id": "F3", "file_size": len(fake.video), "file_name": "invoice.exe", "mime_type": "video/mp4"})
        sent = fake.wait_sent(8, 20)
        time.sleep(0.5)
        its = inbox.items()
        tele = [x for x in its if x.get("source") == "telegram"]
        saved = [x for x in tele if x["kind"] == "file" and Path(x["file"]).name.startswith("trip")]
        to = [m.get("chat_id") for m in sent]
        tdir = D.folder() / "Telegram"
        names = sorted(x.name for x in tdir.iterdir()) if tdir.is_dir() else []
        check("the phone: only the chat that sent the code is paired and answered; its links, its topic and a short video "
              "go into the Inbox (the video into Downloaded\\Telegram), a video over 20 MB refused politely",
              st2["paired"] and st2["chat"] == "Owner" and to.count(555) == 1 and 555 not in to[1:] and to.count(777) >= 5
              and any(x["kind"] == "link" and len(x["links"]) == 2 and "смотри" in x["text"] for x in tele)
              and any(x["kind"] == "topic" and x["text"].startswith("kak gorod") for x in tele)
              and len(saved) == 1 and Path(saved[0]["file"]).is_file() and Path(saved[0]["file"]).parent.name == "Telegram"
              and Path(saved[0]["file"]).stat().st_size == len(fake.video) and any("20 MB" in m.get("text", "") for m in sent),
              ([m.get("text", "")[:60] for m in sent], [(x["kind"], x.get("source")) for x in its], st2))
        check("a video cut off half-way is not kept (no file, no .part); a file sent as a video never keeps another kind's "
              "extension (invoice.exe -> invoice.exe.mp4)",
              any("cut off" in m.get("text", "") for m in sent) and not any(n.startswith("cut") for n in names)
              and "invoice.exe.mp4" in names and len(saved) == 1, (names, [m.get("text", "")[:50] for m in sent[-3:]]))

        # 4. a download started from an Inbox item: the phone hears when it is done
        os.environ["MEDENG_YTDLP"] = f"{sys.executable}|{HERE / 'fake_ytdlp.py'}"
        os.environ["FAKE_YTDLP_VIDEO"] = str(clip)
        D.ROOT.mkdir(parents=True, exist_ok=True)                     # (the stand-in yt-dlp: "installed")
        (D.ROOT / "addon.json").write_text(json.dumps({"version": "test"}), "utf-8")
        link_item = next(x for x in tele if x["kind"] == "link")
        look = c.post("/media/download/look", data={"url": "https://www.youtube.com/watch?v=one001", "inbox": link_item["id"]}, headers=H)
        lt = look.get_data(as_text=True)
        st_ = c.post("/media/download/start", data={"pick": ["0"], "u0": "https://www.youtube.com/watch?v=one001", "t0": "One",
                                                    "inbox": link_item["id"], "source": "x"}, headers=H)
        n0 = len(fake.sent)
        t0 = time.time()
        while time.time() - t0 < 60 and not any("1" in m.get("text", "") and m.get("chat_id") == 777 for m in fake.sent[n0:]):
            time.sleep(0.2)
        done_msgs = [m.get("text", "") for m in fake.sent[n0:]]
        it2 = inbox.get(link_item["id"])
        check("a download started from an Inbox item: the item done, the phone told once when the video is downloaded",
              look.status_code == 200 and f"name='inbox' value='{link_item['id']}'" in lt and st_.status_code == 302
              and it2.get("state") == "done" and len(it2.get("jobs") or []) == 1 and len(done_msgs) == 1
              and it2.get("notified") == it2.get("jobs"), (done_msgs, it2))

        bad_item = inbox.root() / "20990101-000000-abcdef.json"
        bad_item.write_text(json.dumps({"id": "20990101-000000-abcdef", "kind": "link", "links": 5, "jobs": 5, "created_ns": "x",
                                        "text": {"a": 1}}), "utf-8")
        odd = c.get("/inbox", headers=H)
        bad_item.unlink()
        check("an item file edited by hand never breaks the Inbox page; an idea's item is found again by its order "
              "(an order done again is not filed twice)", odd.status_code == 200
              and inbox.find_order("trend-1").get("id") == r_ok.get("inbox_item"), odd.status_code)

        # 5. the pages in Russian: no English left
        c.post("/lang", data={"lang": "ru"}, headers=H)
        st_ru = c.get("/settings", headers=H).get_data(as_text=True)
        ru = c.get("/inbox", headers=H).get_data(as_text=True) + st_ru[st_ru.find("id='phone'"):st_ru.find("<div class='about-grid'>")]
        body = re.sub(r"<(script|style|textarea)[^>]*>.*?</\1>", " ", ru, flags=re.S)
        body = re.sub(r"<[^>]*translate=['\"]no['\"][^>]*>.*?</[a-z0-9]+>", " ", body, flags=re.S)
        txt = re.sub(r"<[^>]+>", "\n", body)
        left = sorted({x.strip() for x in txt.split("\n") if re.search(r"[A-Za-z]{3,}", x) and not re.search(r"[А-Яа-я]", x)
                       and x.strip() not in ("MediaEngine", "Social Lab", "JSON", "YouTube", "TikTok", "Telegram")
                       and "querySelectorAll" not in x})
        ph = [p for p in re.findall(r"placeholder='([^']*)'", ru) if not re.search(r"[А-Яа-я]", p)]
        check("pages: the Inbox and Settings (the phone) in Russian, no English left", not left and not ph, (left[:12], ph))
        c.post("/lang", data={"lang": "en"}, headers=H)

        # 6. the bot disconnected: its token gone, the loop stopped; an item removed (its file stays)
        f_item = saved[0]
        c.post(f"/inbox/{f_item['id']}/delete", headers=H)
        c.post("/settings/phone/forget", headers=H)
        time.sleep(1)
        st3 = tg.status()
        check("disconnect: the token forgotten and the bot stopped; a removed item's video stays in its folder",
              not st3["configured"] and not (work / "home" / "telegram" / "token").exists() and not inbox.get(f_item["id"])
              and Path(f_item["file"]).is_file(), st3)
        tg.stop(1)

    passed = sum(1 for r in RESULTS if r["ok"])
    out = {"passed": passed, "total": len(RESULTS)}
    (work / "inbox_check.json").write_text(json.dumps({**out, "checks": RESULTS}, indent=1), "utf-8")
    print(json.dumps(out))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
