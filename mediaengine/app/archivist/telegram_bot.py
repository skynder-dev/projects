"""The owner's phone, through his own Telegram bot: what he shares to the bot (a link, a topic, a short video) goes
into the Inbox (inbox.py) on this PC, and the bot says when a download started from it is finished.

Off until the owner pastes his bot's token (Settings → Phone): he makes the bot himself with @BotFather - free, no
other account. MediaEngine then asks Telegram for new messages (long polling, api.telegram.org over HTTPS): nothing on
this PC is opened to the internet. Only ONE chat is served - the one that sent the pairing code shown in Settings;
every other chat is ignored. The token is kept in the Windows credential store (a file in the data folder elsewhere),
never written to a log. Nothing is published; the bot only answers the owner.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("MEDENG_TELEGRAM_API") or "https://api.telegram.org"
SECRET = "telegram/bot_token"
MAX_FILE = 20 * 1024 * 1024           # what Telegram lets a bot download
_TOKEN_RE = re.compile(r"^[0-9]{5,12}:[A-Za-z0-9_-]{30,60}$")
CODE_TTL_S = 15 * 60                  # a pairing code works this long
CODE_TRIES = 5                        # wrong codes before it is changed (900 000 codes: guessing is hopeless)
_STATE: dict = {"thread": None, "stop": threading.Event(), "error": "", "seen_at": "", "running": False}
_LOCK = threading.Lock()


class BotError(Exception):
    pass


# ---------------------------------------------------------------- settings and the token

def _cfg() -> dict:
    from .config import load_config
    try:
        return dict(load_config().get("telegram") or {})
    except Exception:
        return {}


def _set(**kw) -> None:
    from .config import update_config
    update_config(lambda cfg: cfg.setdefault("telegram", {}).update(kw))


def _token_file() -> Path:
    from .config import HOME
    return HOME / "telegram" / "token"


def _windows_store() -> bool:
    """The Windows credential store (MEDENG_TELEGRAM_TOKEN_FILE=1: the checks keep it in the data folder instead)."""
    return os.name == "nt" and not os.environ.get("MEDENG_TELEGRAM_TOKEN_FILE")


def _save_token(token: str) -> None:
    if _windows_store():
        from . import secret_store
        secret_store.set_secret(SECRET, token)
    else:
        p = _token_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(token, "utf-8")
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass


def _load_token() -> str:
    try:
        if _windows_store():
            from . import secret_store
            return str(secret_store.get_secret(SECRET) or "")
        return _token_file().read_text("utf-8").strip()
    except Exception:
        return ""


def _drop_token() -> None:
    try:
        if _windows_store():
            from . import secret_store
            secret_store.delete_secret(SECRET)
        else:
            _token_file().unlink(missing_ok=True)
    except Exception:
        pass


def status() -> dict:
    c = _cfg()
    return {"configured": bool(c.get("bot")) and bool(_load_token()), "bot": c.get("bot") or "",
            "paired": bool(c.get("chat_id")), "chat": c.get("chat_name") or "",
            "code": (c.get("code") or "") if code_valid(c) else "",
            "running": bool(_STATE["running"]), "error": _STATE["error"], "seen_at": _STATE["seen_at"]}


# ---------------------------------------------------------------- talking to Telegram

def _call(method: str, params: dict | None = None, token: str = "", timeout: float = 20) -> object:
    token = token or _load_token()            # (the loop passes its own: a bot changed meanwhile is never answered through)
    if not token:
        raise BotError("The bot is not set up.")
    req = urllib.request.Request(f"{API}/bot{token}/{method}", json.dumps(params or {}).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except Exception:
            data = {"ok": False, "description": f"HTTP {exc.code}"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise BotError("Telegram could not be reached: " + str(getattr(exc, "reason", exc))[:120])
    if not isinstance(data, dict) or not data.get("ok"):
        raise BotError(str((data or {}).get("description") or "Telegram refused the request")[:200])
    return data.get("result")


def _ru() -> bool:
    try:
        from . import i18n
        return i18n.ui_language() == "ru"
    except Exception:
        return False


def _say(key: str, **kw) -> str:
    ru = _ru()
    t = {
        "paired": ("Готово: этот чат подключён к MediaEngine на компьютере. Присылай сюда ссылки на видео, темы и короткие "
                   "видео — всё попадёт во «Входящие».",
                   "Done: this chat is connected to MediaEngine on your PC. Send links to videos, topics and short videos "
                   "here - they go into the Inbox."),
        "need_code": ("Чтобы подключить этот чат, отправь код из MediaEngine (Настройки → Телефон): /start 123456",
                      "To connect this chat, send the code from MediaEngine (Settings → Phone): /start 123456"),
        "help": ("Пришли ссылку на видео или профиль — она попадёт во «Входящие» MediaEngine. Пришли текст — это тема для "
                 "сюжета. Короткое видео (до 20 МБ) — сохранится в «Скачанные». /status — что делает компьютер.",
                 "Send a link to a video or a profile - it goes into MediaEngine's Inbox. Send text - a topic for a story. "
                 "A short video (up to 20 MB) is saved into Downloaded. /status - what the PC is doing."),
        "links": ("Во «Входящих»: {n}. Открой MediaEngine → Входящие.", "In the Inbox: {n}. Open MediaEngine → Inbox."),
        "topic": ("Тема во «Входящих».", "The topic is in the Inbox."),
        "file": ("Видео сохранено и лежит во «Входящих»: {name}", "The video is saved and in the Inbox: {name}"),
        "too_big": ("Это видео больше 20 МБ: Telegram не отдаёт ботам такие файлы. Пришли ссылку на него или перекинь дома.",
                    "This video is over 20 MB: Telegram does not give such files to bots. Send a link to it, or copy it at home."),
        "file_failed": ("Видео не удалось сохранить: {why}", "The video could not be saved: {why}"),
        "dl_done": ("Готово: скачано видео — {n}. MediaEngine → Скачать по ссылке.", "Done: {n} video(s) downloaded. MediaEngine → Download by a link."),
        "dl_failed": ("Не скачалось: {why}", "Not downloaded: {why}"),
        "status": ("Компьютер: {what}", "The PC: {what}"),
        "idle": ("ничего не делает", "nothing running"),
    }[key]
    return (t[0] if ru else t[1]).format(**kw)


def send(text: str, token: str = "") -> bool | None:
    """A message to the owner's paired chat: True sent, False not now (Telegram not reachable), None never (no chat,
    or the owner blocked the bot / the token is gone)."""
    chat = _cfg().get("chat_id")
    if not chat:
        return None
    try:
        _call("sendMessage", {"chat_id": chat, "text": str(text)[:3500], "disable_web_page_preview": True}, token=token)
        return True
    except BotError as exc:
        return None if re.search(r"Forbidden|blocked|Unauthorized|chat not found|deactivated", str(exc)) else False


# ---------------------------------------------------------------- setting up

def set_token(token: str) -> dict:
    """The owner's bot token: checked with Telegram (getMe), kept, a new pairing code made, the bot started."""
    token = str(token or "").strip()
    if not _TOKEN_RE.fullmatch(token):
        raise BotError("This is not a bot token. It looks like 1234567890:AAH... (from @BotFather).")
    me = _call("getMe", token=token)
    if not isinstance(me, dict) or not me.get("is_bot"):
        raise BotError("Telegram did not confirm this token.")
    try:                                       # (a webhook set elsewhere would make getUpdates fail for ever)
        _call("deleteWebhook", {"drop_pending_updates": False}, token=token)
    except BotError:
        pass
    stop()
    _save_token(token)
    _set(bot="@" + str(me.get("username") or ""), bot_id=int(me.get("id") or 0), chat_id=0, chat_name="", offset=0, **_fresh_code())
    start()
    return status()


def _fresh_code() -> dict:
    return {"code": f"{secrets.randbelow(900000) + 100000}", "code_at": time.time(), "code_wrong": 0}


def new_code() -> str:
    c = _fresh_code()
    _set(**c)
    return c["code"]


def code_valid(c: dict | None = None) -> bool:
    c = c if c is not None else _cfg()
    return bool(c.get("code")) and time.time() - float(c.get("code_at") or 0) < CODE_TTL_S


def forget() -> None:
    """The bot switched off here: its token and the paired chat forgotten (the bot itself stays in Telegram)."""
    stop()
    _drop_token()
    _set(bot="", bot_id=0, chat_id=0, chat_name="", code="", offset=0)


def unpair() -> None:
    _set(chat_id=0, chat_name="", **_fresh_code())


# ---------------------------------------------------------------- the messages

_EXT = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm", "video/x-matroska": ".mkv",
        "video/x-msvideo": ".avi", "video/3gpp": ".3gp", "video/mpeg": ".mpg"}
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.I)


def _safe_name(name: str, mime: str = "") -> str:
    """A file name Windows takes, with the extension of what it is (a video: never an .exe sent as a video)."""
    stem = Path(str(name or "")).stem if Path(str(name or "")).suffix.lower() in set(_EXT.values()) | {".m4v"} else str(name or "")
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", stem).strip(" .")[:80].strip(" .") or "video"
    if _RESERVED.match(stem):
        stem = "_" + stem
    return stem + _EXT.get(str(mime or "").lower(), ".mp4")


def _save_file(f: dict, caption: str, token: str = "") -> str:
    """A video sent to the bot: into Downloaded\\Telegram, and an Inbox item. All of it or nothing (a cut-off download
    never stays as a video)."""
    from . import downloader as D, inbox
    size = int(f.get("file_size") or 0)
    if size > MAX_FILE:
        return _say("too_big")
    part = None
    try:
        info = _call("getFile", {"file_id": f.get("file_id")}, token=token)
        path = str((info or {}).get("file_path") or "")
        size = size or int((info or {}).get("file_size") or 0)
        if not path or ".." in path:
            raise BotError("Telegram gave no file.")
        if size > MAX_FILE:
            return _say("too_big")
        dst_dir = D.folder() / "Telegram"
        dst_dir.mkdir(parents=True, exist_ok=True)
        name = _safe_name(f.get("file_name") or Path(path).name, f.get("mime_type") or "video/mp4")
        dst = dst_dir / name
        k = 2
        while dst.exists():
            dst = dst_dir / f"{Path(name).stem} ({k}){Path(name).suffix}"
            k += 1
        part = dst.with_name(dst.name + ".part")
        url = f"{API}/file/bot{token or _load_token()}/{urllib.parse.quote(path)}"
        got = 0
        with urllib.request.urlopen(url, timeout=120) as r, open(part, "wb") as out:
            want = size or int(r.headers.get("Content-Length") or 0)
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                got += len(chunk)
                if got > MAX_FILE:
                    raise BotError("the file is bigger than 20 MB")
                out.write(chunk)
        if not got or (want and got != want):
            raise BotError("the download was cut off")
        os.replace(part, dst)
        part = None
    except Exception as exc:                       # (a short read, a lost connection, a full disk: said, never kept)
        msg = str(exc) if isinstance(exc, BotError) else type(exc).__name__
        return _say("file_failed", why=msg[:120])
    finally:
        if part is not None:
            try:
                part.unlink(missing_ok=True)
            except OSError:
                pass
    inbox.add("file", file=str(dst), text=caption, source="telegram")
    return _say("file", name=dst.name)


def _what_runs() -> str:
    parts = []
    try:
        from . import downloader as D
        n = sum(1 for j in D.list_jobs(20) if j.get("state") in ("working", "waiting"))
        if n:
            parts.append(("загрузки: " if _ru() else "downloads: ") + str(n))
    except Exception:
        pass
    try:
        from . import voice as vo
        b = vo.busy()
        if b:
            j = vo.read_job(b) if b != "install" else {}
            parts.append(str(j.get("title") or j.get("kind") or b))
    except Exception:
        pass
    return ", ".join(parts) or _say("idle")


def handle(msg: dict, token: str = "") -> str | None:
    """One message: what the bot answers (None: no answer). Only the paired chat is served - a private chat with the
    owner that sent the pairing code while it was valid."""
    from . import inbox
    if not isinstance(msg, dict) or not isinstance(msg.get("chat"), dict):
        return None
    if msg["chat"].get("type") != "private":           # (never a group: everyone in it could send things to the PC)
        return None
    c = _cfg()
    chat = msg["chat"].get("id")
    text = str(msg.get("text") or msg.get("caption") or "").strip()
    paired = c.get("chat_id")
    if not paired:
        if not text.startswith("/start"):
            return None
        m = re.match(r"^/start(?:@\w+)?\s+([0-9]{6})$", text)
        if m and code_valid(c) and secrets.compare_digest(m.group(1), str(c.get("code"))):
            who = " ".join(str(msg["chat"].get(k) or "") for k in ("first_name", "last_name")).strip() or str(msg["chat"].get("username") or "")
            _set(chat_id=chat, chat_name=who[:60], code="", code_wrong=0)
            return _say("paired")
        if m and code_valid(c):                          # a wrong code: after a few the code changes
            wrong = int(c.get("code_wrong") or 0) + 1
            if wrong >= CODE_TRIES:
                _set(**_fresh_code())
            else:
                _set(code_wrong=wrong)
        return _say("need_code")
    if chat != paired:
        return None                                   # (someone else's chat: never answered)
    if re.match(r"^/(start|help)\b", text):
        return _say("help")
    if re.match(r"^/status\b", text):
        return _say("status", what=_what_runs())
    f = msg.get("video") or msg.get("animation") or msg.get("video_note")
    doc = msg.get("document") or {}
    if not f and str(doc.get("mime_type") or "").startswith("video/"):
        f = doc
    if f:
        return _save_file(f, text, token)
    links = inbox.links_in(text)
    if links:
        rest = text
        for u in links:
            rest = rest.replace(u, " ")
        try:
            inbox.add("link", links=links, text=rest, source="telegram")
        except inbox.InboxError as exc:
            return str(exc)
        return _say("links", n=len(links))
    if text and not text.startswith("/"):
        inbox.add("topic", text=text, source="telegram")
        return _say("topic")
    return None


def _check_downloads(token: str = "") -> None:
    """Tell the phone once when a download started from an Inbox item is finished (a download that was removed, or a
    bot the owner blocked: given up, never asked again)."""
    from . import downloader as D, inbox
    for it in inbox.items(100):
        for jid in it.get("jobs") or []:
            if jid in (it.get("notified") or []):
                continue
            try:
                j = D.read_job(jid)
            except Exception:
                j = None
            if j is not None and j.get("state") in ("working", "waiting", "interrupted"):
                continue                             # (interrupted: made again at the next start)
            sent = True
            if j is not None and j.get("state") in ("done", "failed"):
                res = j.get("result") or {}
                text = (_say("dl_done", n=len(res.get("files") or [])) if j.get("state") == "done" else
                        _say("dl_failed", why=str(res.get("error") or "")[:200]))
                sent = send(text, token)
            if sent is False:
                continue                             # (Telegram not reachable now: told later)
            try:
                inbox.mark_notified(it["id"], jid)
            except inbox.InboxError:
                pass


# ---------------------------------------------------------------- the loop

def _loop(stop_ev: threading.Event, token: str, bot_id: int) -> None:
    _STATE["running"] = True
    wait = 2.0
    try:
        while not stop_ev.is_set():
            try:
                c = _cfg()
                off = int(c.get("offset") or 0) if int(c.get("bot_id") or 0) == bot_id else 0
                ups = _call("getUpdates", {"offset": off, "timeout": 25, "allowed_updates": ["message"]}, token=token, timeout=40) or []
                if stop_ev.is_set():
                    break                                  # (stopping: these messages are for the next loop)
                _STATE["seen_at"] = time.strftime("%Y-%m-%d %H:%M")
                _STATE["error"] = ""
                for u in ups if isinstance(ups, list) else []:
                    if not isinstance(u, dict):
                        continue
                    off = max(off, int(u.get("update_id") or 0) + 1)
                    _set(offset=off, bot_id=bot_id)        # (a message is never handled twice, even after a crash)
                    try:
                        answer = handle(u.get("message") or {}, token)
                    except Exception as exc:              # never let one odd message stop the bot
                        answer = None
                        _STATE["error"] = type(exc).__name__ + ": " + str(exc)[:160]
                    if answer:
                        chat = (u.get("message") or {}).get("chat", {}).get("id")
                        try:
                            _call("sendMessage", {"chat_id": chat, "text": answer[:3500], "disable_web_page_preview": True}, token=token)
                        except BotError:
                            pass
                try:
                    _check_downloads(token)
                except Exception as exc:                  # (an odd Inbox file never slows the bot down)
                    _STATE["error"] = type(exc).__name__ + ": " + str(exc)[:160]
                wait = 2.0
            except BotError as exc:
                _STATE["error"] = str(exc)
                if "Unauthorized" in str(exc) or "Not Found" in str(exc):
                    stop_ev.wait(300)                      # (a revoked token: try rarely)
                else:
                    stop_ev.wait(wait)
                    wait = min(120.0, wait * 2)
            except Exception as exc:
                _STATE["error"] = type(exc).__name__ + ": " + str(exc)[:160]
                stop_ev.wait(wait)
                wait = min(120.0, wait * 2)
    finally:
        if _STATE.get("stop") is stop_ev:                 # (an older loop ending late does not hide the new one)
            _STATE["running"] = False


def start() -> None:
    """The bot's loop, when it is set up (at the app's start and after the token is pasted)."""
    with _LOCK:
        t = _STATE.get("thread")
        if t and t.is_alive() and not _STATE["stop"].is_set():
            return                                         # (one still stopping is replaced: it handles nothing more)
        c, token = _cfg(), _load_token()
        if not (c.get("bot") and token):
            return
        ev = threading.Event()
        _STATE["stop"] = ev
        t = threading.Thread(target=_loop, args=(ev, token, int(c.get("bot_id") or 0)), daemon=True, name="telegram")
        _STATE["thread"] = t
        t.start()


def stop(wait: float = 3.0) -> None:
    with _LOCK:
        _STATE["stop"].set()
        t = _STATE.get("thread")
    if t and t.is_alive():
        t.join(wait)
